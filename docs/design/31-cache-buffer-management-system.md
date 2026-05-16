# 31. Cache Buffer Management System

## Why Caching Matters for Friday

A Friday agent answering "what's the credit limit for customer X?" should not hit ERPNext's PostgreSQL every time. With dozens of agents acting in parallel and hundreds of queries per minute, naive direct queries:
- Add 30-80ms latency per query
- Increase PostgreSQL load and lock contention
- Risk rate-limiting or connection-pool exhaustion

A well-designed cache layer dramatically improves Friday's responsiveness and protects ERPNext from agent-induced load.

## Cache Layers

### Layer A — Redis Hot Cache

For frequently accessed reference data:
- ERPNext masters: Customer, Supplier, Item, Warehouse, Account, Employee
- Operations Policy thresholds
- Active Agent Role Profile configurations
- Permission matrices (rolescope per user)
- Currency exchange rates
- Tax templates

TTL: 5 minutes default, configurable per data type. Invalidated on document change events.

### Layer B — Process-Local Cache

For within-execution memoization:
- Same skill calling `customer_get(X)` twice → second call hits process local
- LRU cache (Python `functools.lru_cache` or equivalent)
- Bounded to ~10MB per execution
- Cleared at execution end

### Layer C — Embedding Result Cache

For repeated embedding queries:
- Hash query text → cached embedding vector
- Avoids redundant LLM provider embedding calls
- Stored in Redis with 24h TTL
- Significant cost saver: ~30-50% of embedding calls in a typical day are duplicates

### Layer D — LLM Response Cache (Selective)

For deterministic, idempotent prompts where input fully determines output:
- Skill-internal helper prompts (e.g. "classify this customer email as urgent/non-urgent")
- NOT for open-ended agent reasoning (which should always be fresh)
- Hash full prompt + model + temperature → cached completion
- TTL: 1 hour, configurable per skill

Skills must opt in to LLM response caching via `cache_enabled = True` in their metadata. Off by default to avoid stale reasoning.

## DocType: Cache Policy

A configuration DocType for cache tuning:

Fields:
- `cache_layer` (Select: Redis Hot, Process Local, Embedding, LLM Response)
- `data_type` (Data) — e.g. "Customer", "Item", "Supplier"
- `ttl_seconds` (Int)
- `max_size_mb` (Int) — for memory budgeting
- `invalidation_strategy` (Select: TTL only, Event-based, Both)
- `enabled` (Check)

Admins tune cache behavior without code changes.

## Pre-load Strategy

On Friday startup or on a scheduled refresh (every 30 minutes):

1. Determine the "warm set" of ERPNext records each domain agent commonly references.
2. Bulk-fetch in one query per DocType.
3. Populate Redis with a single MSET pipeline.
4. Record fill time for monitoring.

The warm set is data-driven: a background job examines Execution Logs over the last 7 days, identifies the most-accessed records per domain, and updates the warm set definition weekly.

Example warm set for Procurement Agent:
- All active Suppliers
- All Items with `is_stock_item=1`
- All Warehouses
- Current PO statuses for last 30 days
- Operations Policy thresholds for procurement

This pre-load takes ~5-30 seconds depending on data size and primes the cache before agents need it.

## Invalidation

Two strategies, used together:

### TTL-Based
Every cached entry has an absolute expiry. Worst case staleness = TTL value. Suitable for slow-changing data.

### Event-Based
Frappe's `doc_events` hook fires on document save/submit/cancel. A Friday handler:
```python
def on_doctype_change(doc, method):
    cache_key = f"frappe:{doc.doctype}:{doc.name}"
    redis_client.delete(cache_key)
    # Also invalidate related caches (e.g. list views of this DocType)
    redis_client.delete(f"frappe:list:{doc.doctype}")
```

Critical for data where staleness matters (e.g. customer credit limit, current stock).

## Cache Read Path

A skill calling `frappe_get("Customer", "CUST-001")` goes through:

1. Check process-local cache. Hit? Return. Miss → continue.
2. Check Redis hot cache. Hit? Populate process-local, return. Miss → continue.
3. Fetch from PostgreSQL via Frappe ORM.
4. Populate Redis (with TTL) and process-local.
5. Return.

This pattern is implemented in a single `friday.cache.get_doc(doctype, name)` helper used by all skills.

## Cache Write Path

When an agent modifies a document:

1. Write to ERPNext via Frappe ORM (always).
2. On success, invalidate Redis cache for that record AND related list caches.
3. The `doc_events` handler also fires, providing belt-and-suspenders invalidation.

We do NOT do write-through caching — writes always go to PostgreSQL first.

## Memory Budget

Total Redis budget for caching: configurable, default 2GB per Friday instance.

Per-layer allocation:
- Hot cache: 70% (~1.4GB)
- Embedding cache: 20% (~400MB)
- LLM response cache: 10% (~200MB)

When budget is exceeded, Redis evicts using LRU policy (`maxmemory-policy allkeys-lru`).

## Cache Stampede Prevention

If many agents request the same uncached key simultaneously, naive logic causes a stampede on PostgreSQL.

Mitigation: a per-key lock pattern.

```python
def get_doc(doctype, name):
    cache_key = f"frappe:{doctype}:{name}"
    cached = redis.get(cache_key)
    if cached:
        return cached
    
    lock_key = f"lock:{cache_key}"
    with redis_lock(lock_key, timeout=5):
        # Re-check after lock acquired
        cached = redis.get(cache_key)
        if cached:
            return cached
        
        doc = frappe.get_doc(doctype, name)
        redis.setex(cache_key, ttl, serialize(doc))
        return doc
```

Only one process fetches; others wait briefly and read from cache.

## Monitoring

A Friday Cache Dashboard tracks:
- Hit rate per layer (target: >85% for hot cache)
- Avg latency hit vs miss
- Evictions per minute
- Top miss keys (candidates for pre-load addition)
- Memory utilization

Alerts:
- Hit rate < 70% for 15 minutes → page on-call
- Memory > 90% for 5 minutes → page on-call
- Eviction rate spike → investigate stampede or pre-load misconfiguration

## Cache Bypass

Some operations must always read fresh:
- Stock quantity checks during PO submission (race conditions risk)
- Account balance during Payment Entry
- Bank statement reconciliation source data

Skills mark these reads with `bypass_cache=True`. The helper ignores cache and reads directly from PostgreSQL.

## Cache Warm-up on Deployment

When Friday is deployed or restarted:
1. Application starts
2. Pre-load job runs as a background task (not blocking startup)
3. Health check returns `degraded` until cache fill is complete
4. Agents starting before fill receive uncached reads (slower but correct)
5. Health check returns `healthy` when fill completes (~30 seconds)

## Multi-Tenant Considerations (Phase 4 SaaS)

In the hosted SaaS, each tenant has its own Redis namespace prefix. Cache keys include tenant ID: `tenant:{tid}:frappe:{doctype}:{name}`. No cross-tenant cache sharing — privacy and isolation.

## Phase 1 Scope

Phase 1 ships:
- Redis hot cache for top 10 ERPNext DocTypes
- Event-based invalidation via doc_events
- Pre-load on startup for warm set
- Basic monitoring (hit rate, latency)

Phase 2 adds:
- Process-local cache
- Embedding cache
- Cache Policy DocType + admin tuning
- Stampede prevention with locks
- Comprehensive dashboard

Phase 3:
- LLM response cache for selected skills
- Per-tenant cache namespacing
- Cache warm set learning from usage patterns

## Open Questions

1. Should we use Redis or KeyDB or DragonflyDB? Stick with Redis for ecosystem familiarity; revisit if memory or performance becomes a bottleneck.
2. Cache serialization format: JSON or msgpack? Lean msgpack for size and speed; profile in Phase 1.
3. Cross-instance cache coherence in multi-node Friday deployments — pub/sub invalidation channel? Yes, in Phase 3 when we support multi-node.
