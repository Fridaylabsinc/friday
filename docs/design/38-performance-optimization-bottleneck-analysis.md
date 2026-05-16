# 38. Performance Optimization & Bottleneck Analysis

## Performance Goals

Friday must feel responsive under realistic load:
- Single-agent task completion: p50 < 5 seconds, p99 < 30 seconds for simple tasks
- Concurrent agents: 50+ agents executing in parallel on a single 8-core Friday node
- Memory search: p50 < 200ms, p99 < 800ms
- Skill dispatch (selection + validation): < 100ms
- War Room message → agent pickup: < 2 seconds end-to-end

If these targets miss, agents feel sluggish, supervisors lose trust, and the autonomous experience degrades.

## Known Bottleneck Categories

1. LLM provider latency (largest, often external)
2. Vector search on pgvector (with poor indexing)
3. Frappe ORM overhead on hot queries
4. Container startup for skill execution (cold start)
5. Permission gate evaluation
6. Cross-process synchronization for Raven War Room

We address each.

## Category 1: LLM Provider Latency

**Observation:** A single LLM call to a frontier model takes 1-8 seconds. Agents that make 5 calls in series feel slow.

**Strategies:**

### Parallel LLM Calls
Where independent reasoning steps exist, run them concurrently. Skills like "classify these 10 emails" or "validate these 5 documents" launch parallel calls.

### Streaming
Stream LLM responses where the agent can act on partial output. For final user-visible summaries, stream to Raven in chunks.

### Smaller Model Fallback
For deterministic, simple sub-tasks (classification, extraction, validation), use a cheaper/faster model (Haiku-class). Reserve frontier models for complex reasoning.

The Skill DocType has a `recommended_model_tier` field (Light/Standard/Heavy). Dispatcher uses this to route LLM calls appropriately.

### Provider Failover
Two configured LLM providers (e.g. Anthropic + a local OSS model). If primary times out beyond threshold, fail over to secondary. Recovers gracefully from provider incidents.

### Batched LLM Calls
For analytics tasks evaluating dozens of items, batch into a single prompt with structured output. One call replaces ten.

## Category 2: Vector Search

**Observation:** A naive pgvector scan over millions of rows is slow. With proper indexing, sub-second p99 is achievable.

**Strategies:**

### HNSW Index
```sql
CREATE INDEX idx_memory_embedding ON memory_entry_embeddings
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);
```

Tuning: `ef_search` parameter at query time. Higher = better recall, slower. Start at 40, profile.

### Partial Indexes per Domain
Most queries are domain-scoped (doc 29). Domain-partial indexes keep working set small.

```sql
CREATE INDEX idx_memory_embedding_procurement ON memory_entry_embeddings
USING hnsw (embedding vector_cosine_ops)
WHERE domain_id = 'erpnext-procurement';
```

### Pre-filtered Search
Apply metadata filters (domain, time range, concept) BEFORE vector search where possible. PostgreSQL's planner can sometimes do this; explicit query hints help.

### Cold Tier Bypass
Cold tier never scanned synchronously. Only async on explicit request (doc 34).

### Dimension Choice
1536-dimensional embeddings: high quality but slower than 768-dim. Profile and choose per workload.

## Category 3: Frappe ORM Overhead

**Observation:** `frappe.get_doc` performs role permission checks, link field resolution, and hook firing on every call. For hot read paths, this adds 50-100ms.

**Strategies:**

### Bulk Reads
Replace 10 `frappe.get_doc` calls with one `frappe.get_all` or one direct SQL query.

### Direct SQL for Hot Paths
Where role checks aren't needed (admin-context background tasks), use `frappe.db.sql` or `frappe.db.get_value` instead of full doc load.

### Caching Layer
The cache layer (doc 31) intercepts hot reads before they hit ORM.

### Hook Audit
Identify and disable unnecessary doc_events hooks for Friday-internal DocTypes that don't need them.

## Category 4: Container Cold Start

**Observation:** Spinning up a Docker container for skill execution takes 1-3 seconds. If every skill call did this, agents would crawl.

**Strategies:**

### Warm Pool
Maintain 5-20 pre-started containers in an idle pool. When a skill needs to execute, grab one from the pool, run, return (or recycle) the container.

### Per-Profile Pools
Different agent profiles need different container images. Pool is segmented per image. Common images get larger pools.

### Container Reuse Within Execution
Within a single agent execution, the same container handles multiple skill calls if isolation requirements permit. Reduces overhead dramatically.

### Async Container Fill
A background job keeps the pool topped up. When usage spikes, pool grows; when usage drops, idle containers exit.

## Category 5: Permission Gate

**Observation:** Every skill call passes through the permission gate (doc 04). Naive evaluation of complex permission matrices can take 20-50ms.

**Strategies:**

### Permission Decision Cache
A Redis cache of (user_id, skill, target_doctype) → allow/deny. TTL: 5 minutes. Invalidated on role / profile changes.

### Pre-compute Permission Sets
For each Agent Role Profile, compute and cache the full set of (skill, target_doctype, action) tuples it can perform. Skill calls become O(1) set membership tests.

### Approval Threshold Lookup
Threshold checks (e.g. "PO ≤ ₹50,000 → autopilot") use indexed lookups, not table scans.

## Category 6: Raven War Room

**Observation:** When 20 agents post simultaneously to War Room channels, the chat backend can lag.

**Strategies:**

### Async Posting
Agents fire-and-forget War Room posts to an internal queue. A worker consumer flushes to Raven.

### Batching
Multiple posts within a 100ms window from the same agent batch into a single Raven message.

### Channel Pagination Optimization
War Room read APIs paginate efficiently. Default page size 50 messages; older messages on-demand only.

### Bot Account Pool
Each Friday agent has a Frappe user, but Raven message authoring uses a small pool of "bot" identities to reduce per-account overhead. The original agent author is preserved in message metadata.

## Performance Testing

A standardized benchmark suite ships with Friday:

### benchmark_simple_task.py
Runs 100 simple PO-create tasks sequentially. Reports p50, p95, p99 latencies.

### benchmark_concurrent_agents.py
Spawns 50 concurrent agents each running a 5-step task. Reports wall-clock completion and resource utilization.

### benchmark_memory_search.py
100K memory entries pre-loaded. Runs 1000 vector searches. Reports p50/p99 latency.

### benchmark_war_room_throughput.py
500 messages/second sustained for 2 minutes. Reports lag distribution.

These run in CI on every Friday core PR. Regressions block merge.

## Profiling Tools

- **Python profiling:** py-spy, cProfile + snakeviz for hot path analysis
- **PostgreSQL:** auto_explain, pg_stat_statements, EXPLAIN ANALYZE on slow queries
- **Redis:** SLOWLOG, latency monitor
- **Container metrics:** cAdvisor, Prometheus
- **End-to-end traces:** OpenTelemetry instrumentation; Jaeger or Tempo backend

Every agent execution emits a trace. Slow executions are auto-flagged for review.

## Optimization Priorities

By Phase:

### Phase 1
- pgvector HNSW indexes
- Basic permission cache
- Frappe ORM bulk reads
- Single container warm pool
- Skill latency monitoring

### Phase 2
- Streaming LLM responses
- Domain-partial indexes
- Per-profile container pools
- Async Raven posting
- End-to-end OpenTelemetry tracing

### Phase 3
- Parallel LLM call orchestration
- Provider failover
- Pre-computed permission sets
- Memory tier optimization
- ML-based query plan tuning

## Capacity Planning

For a small business (≤50 employees, ≤10K monthly transactions):
- 1 Friday node: 8 CPU, 16GB RAM, 100GB SSD
- Handles 50 concurrent agents comfortably
- LLM cost dominates (typically ₹15-50K/month for moderate usage)

For mid-size (≤500 employees, ≤100K monthly transactions):
- 2-3 Friday nodes behind a load balancer
- Shared PostgreSQL primary + read replica
- Redis cluster
- Costs scale roughly linearly with transaction volume

For enterprise (>500 employees):
- Multi-node Friday cluster
- Dedicated PostgreSQL with WAL replication
- Multi-region Redis
- Custom optimization per workload

## Cost Optimization

LLM cost is the largest variable cost. Reduce by:
1. Use Haiku/Light tier for simple sub-tasks (see Category 1)
2. Cache LLM responses for idempotent prompts (doc 31)
3. Batch related calls
4. Prefer smaller context: pass only relevant skill descriptions (skill ceiling per doc 15)
5. Trim memory search results to top N actually needed
6. Use embedding cache aggressively

Track cost per task type. Surface in Performance Insights Agent report (doc 36). Identify outliers.

## SLA Targets

For the hosted FridayLabs SaaS:

| Metric | Target | Hard SLA |
|---|---|---|
| Agent task completion p99 | < 30s | < 90s |
| Memory search p99 | < 800ms | < 2s |
| Uptime (excluding maintenance) | 99.5% | 99.0% |
| War Room post latency | < 2s | < 10s |

Self-hosted deployments are not bound by SLA but the same targets serve as quality goals.

## Phase 1 Scope

Phase 1 ships:
- HNSW indexes on memory tables
- Permission decision cache
- Basic container warm pool (5 containers per image)
- Latency monitoring with simple histogram
- Standardized benchmark suite

Phase 2 adds:
- Domain-partial indexes
- Streaming LLM responses with War Room chunked delivery
- OpenTelemetry tracing
- Async Raven posting
- Per-profile pools

Phase 3 adds:
- Parallel LLM orchestration
- Provider failover
- Pre-computed permission sets
- ML-tuned query plans
- Cost attribution dashboard

## Open Questions

1. Should we ship Friday with Prometheus + Grafana pre-configured? Probably yes Phase 2 — most operators don't know what to monitor.
2. How much performance can we sacrifice for safety guarantees (sandbox, permission gate)? Hard cap: safety overhead < 10% of task time.
3. What is acceptable cold start latency for first agent of the day? < 2 seconds via warm pool.
4. Optimal embedding dimension for our use cases? Profile both 768 and 1536 in Phase 1; pick based on quality/cost trade-off.
