# 34. Efficient Multi-Layer Memory System

## Memory is Tools, Not Context

Per the OpenClaw insight (doc 15): memory must be **searchable via skills**, not stuffed into every prompt. Naive context-injection of memory:
- Blows up token budgets
- Includes irrelevant content (distraction)
- Doesn't scale (memory grows unbounded, context doesn't)

Friday treats memory as a backend the agent queries deliberately, just like it queries a database.

## Three-Tier Memory Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ HOT — Redis (in-memory)                                         │
│   - Recent execution context (last N steps)                     │
│   - Active task scratchpad                                      │
│   - Recently accessed concepts                                  │
│   - TTL: minutes to hours                                       │
│   - Size: ~50MB per active agent                                │
├─────────────────────────────────────────────────────────────────┤
│ WARM — PostgreSQL + pgvector                                    │
│   - Memory Entries (full content + embeddings)                  │
│   - Memory Concepts + Links (doc 32)                            │
│   - Recent (last 90 days) execution logs                        │
│   - Indexed for fast retrieval                                  │
│   - Size: ~1-10GB per business after 1 year                     │
├─────────────────────────────────────────────────────────────────┤
│ COLD — Archive Storage (S3 / MinIO / local disk)                │
│   - Compressed execution logs > 90 days                         │
│   - Memory entries flagged "archive" by curator                 │
│   - Periodic snapshots                                          │
│   - Retrievable on demand (slow path)                           │
└─────────────────────────────────────────────────────────────────┘
```

## Memory Categories

Independent of tier, memory entries are categorized:

### 1. Episodic
"What happened" — events, observations, interactions.
- "On March 5, Customer X placed an order for 50 units."
- "Procurement Agent retried PO-001 three times due to supplier timeout."

### 2. Semantic
"What is true" — facts, configurations, relationships.
- "Customer X's payment terms: Net 30."
- "Supplier S is preferred vendor for Item A."

### 3. Procedural
"How to do" — patterns and methods.
- "When invoice is 7 days overdue, send reminder email; 14 days, escalate."
- Typically codified as Skills, not memory entries.

### 4. Reflective
"What we learned" — meta-observations.
- "Following up with Customer X via WhatsApp is more effective than email."
- "Supplier S misses deadlines in March due to seasonal factors."

Each memory entry carries a `category` field. Search can filter by category.

## DocType: Memory Entry (Full Schema)

Building on prior docs, the complete schema:

- `entry_id` (Data, auto-named)
- `domain` (Link to Domain)
- `category` (Select: Episodic, Semantic, Procedural, Reflective)
- `content` (Long Text)
- `embedding_vector` (stored in pgvector column on companion table)
- `mentioned_concepts` (child table)
- `primary_concept` (Link to Memory Concept)
- `source_type` (Select: Agent Execution, Human Annotation, ERPNext Event, Wiki, External)
- `source_reference` (Data) — link back to original
- `created_by` (Link to User) — agent or human
- `created_at` (Datetime)
- `accessed_at` (Datetime) — last time this entry was returned by a search
- `access_count` (Int)
- `tier` (Select: Hot, Warm, Cold)
- `importance` (Float, 0.0-1.0) — curator-set
- `verified` (Check) — supervisor confirmed accuracy
- `sensitive` (Check) — requires elevated permission to read
- `archive_at` (Date) — auto-archive date if set

## Tier Management

Memory entries promote and demote between tiers:

### Hot → Warm
Automatic on agent execution end. Hot tier holds only active context.

### Warm → Cold
Nightly job moves entries to cold when:
- Not accessed in 90 days, AND
- `importance` < 0.5, AND
- Not flagged `verified`

Cold storage uses S3-compatible object storage. Each archive object is a compressed JSONL of ~1000 entries.

### Cold → Warm (Restore)
When a `memory_search` query has unusually low hit rate, the search expands into cold storage:
1. Search executes a cold-tier scan with looser thresholds.
2. If matches found, those entries are restored to warm tier.
3. Restored entries get `accessed_at = now` and remain warm.

Cold scan is slow (10-30 seconds) and bounded — used as a fallback.

## Hot Memory Structure

Within Redis, hot memory is organized per-agent-execution:

```
agent:{agent_id}:exec:{exec_id}:
  - steps: list of recent step records (last 20)
  - scratchpad: free-form key-value working memory
  - recent_concepts: set of concept IDs recently mentioned
  - cached_skill_results: result cache for current execution
```

This expires at execution end (or after 1 hour idle). Long-running heartbeat sessions persist hot memory across heartbeat boundaries.

## Memory Write Path

When an agent records a memory:

1. Agent calls `memory_save(content, category, ...)` skill.
2. Skill creates a Memory Entry (warm tier by default) in PostgreSQL.
3. Embedding computed via embedding service (LLM provider or local model).
4. Concept extraction runs (doc 32).
5. Mentioned concepts updated.
6. Entry indexed in pgvector.
7. Hot memory also updated with `recent_concepts` set.
8. Execution Log records the write.

Latency target: <500ms for the full pipeline.

## Memory Read Path

When an agent calls `memory_search(query, ...)`:

1. Query embedded.
2. pgvector similarity search in warm tier (top K, with metadata filters).
3. Hot tier scratchpad scanned for recent matches.
4. Concept graph walked (doc 32) for associated context.
5. Results merged and ranked:
   - Direct vector matches (high weight)
   - Hot tier hits (high weight, very recent)
   - Associated concept results (lower weight)
6. Return top N with metadata.

If hit count below threshold, optionally extend to cold tier (slow path, only on agent's explicit request or supervisor opt-in).

Latency target: <300ms (warm tier only).

## Memory Compression

Old episodic memories compress into summary form:

Example: 50 individual entries about "Procurement Agent processed PO-X with supplier follow-up" → one summary "In Q1 2025, Procurement Agent processed 50 POs averaging 3.2 days to completion."

Compression rules:
- Run nightly on entries > 30 days old in episodic category
- Group by concept and time window
- LLM-generated summary
- Original entries archived to cold; summary stays in warm
- Summary tagged `category = Reflective`, `source_type = Compression`

This keeps warm tier from bloating while preserving aggregate knowledge.

## Memory Sharing

Within a Domain, all agents share memory access. Cross-domain access controlled per doc 29.

For multi-business SaaS:
- Each business has its own memory namespace
- No cross-business sharing by default
- Opt-in to anonymized community memory pool (Phase 4 feature)

## Memory Quality Curation

A weekly background job (the "memory curator") runs:
1. Identifies duplicate entries (high embedding similarity, same domain).
2. Proposes merges to supervisors via Raven.
3. Identifies low-importance, low-access entries → suggests archive.
4. Identifies high-access entries that lack `verified` flag → suggests review.
5. Identifies entries contradicting each other → flags for supervisor.

Curator does not modify memory autonomously in Phase 1; only proposes.

## Memory Permissions

Three permission levels per memory entry:
- **Public** within domain — any agent in the domain can read
- **Restricted** — only specific Agent Role Profiles can read (e.g. salary memories visible to HR agents only)
- **Sensitive** — supervisor approval required for each read

Sensitive memories: encrypted at rest with per-tenant key, audited on every access.

## Forgetting

Some memories should be deleted, not archived:
- GDPR/DPDPA right-to-be-forgotten requests
- Memories about ex-employees, ex-customers (with retention policy expiry)
- Erroneous memories flagged by supervisor

Skill `memory_forget(entry_id, reason)`:
- Requires supervisor approval
- Logs the deletion event with reason (immutable)
- Removes from warm and hot tiers
- Marks cold archive object for purge on next cold-storage maintenance

## Performance Tuning

pgvector indexes:
- HNSW index on embedding column with M=16, ef_construction=64 (defaults)
- Re-index when entry count crosses 100K, 500K, 1M thresholds
- Partial indexes per domain to keep search scope tight

Query patterns to optimize:
- Domain-filtered vector search: index on `domain_id` + vector index, query planner uses both
- Concept-filtered: pre-fetch concept's linked entry IDs, then filter

## Monitoring

Track:
- Total entries per tier
- Read latency p50, p99
- Write latency p50, p99
- Cold tier scan frequency (should be rare)
- Curator queue depth
- Memory growth rate per business

Alert if:
- Read p99 > 1 second
- Cold scans > 10/hour
- Growth rate suggests bloat (>1GB/week sustained)

## Phase 1 Scope

Phase 1 ships:
- Memory Entry DocType (warm tier only)
- pgvector similarity search
- `memory_save`, `memory_search`, `memory_get` skills
- Domain scoping
- Basic permissions (public/restricted)

NOT in Phase 1:
- Concept graph (doc 32 — Phase 2)
- Compression
- Curator job
- Cold tier / archive
- Sensitive memory encryption

## Phase 2

Phase 2 adds:
- Hot tier (Redis)
- Concept extraction + graph
- Compression job
- Cold tier with S3-compatible storage
- Memory curator with proposal workflow

## Phase 3

Phase 3 adds:
- Sensitive memory encryption
- Forgetting workflow with audit trail
- Cross-tenant anonymized community pool (opt-in)
- Advanced curation with anomaly detection

## Open Questions

1. Embedding model choice — provider API (OpenAI/Anthropic) vs local (BGE, E5)? Lean: configurable; local models for cost and privacy at scale.
2. Vector dimension trade-off — 768 vs 1536 vs 3072? 1536 is good default; 768 for cost-sensitive deployments.
3. How to handle embedding model changes (when we upgrade)? Maintain old + new for 30 days, dual-index, then drop old. Designed in Phase 2.
