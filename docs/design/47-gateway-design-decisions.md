# 47 — Gateway Design Decisions

> **Status:** Authoritative. The contract Slice 4 (and every later slice touching message flow) implements against.
> **Scope:** Single-tenant Friday deployment. NOT a multi-tenant SaaS platform.
> **Audience:** Anyone — engineer, product owner, or a high schooler curious about how Friday's message flow works.

---

## 1. Scope and what this document is

Friday v0.1 is **one customer's Frappe site running Friday code.** Not infrastructure that hosts many customers. Not "agenting platform for the world." This document defines how messages flow through that one-customer deployment from any surface (CLI, Telegram, Slack, Raven, agent-to-agent) to the agent and back.

It records every decision we made about that flow, the alternatives we rejected, and — importantly — the design for pieces we have **deliberately deferred** because they don't have a user yet in v0.1. When those users land in later slices, the deferred designs become the spec.

**Why this doc exists:** because architecture-by-chat-history is a recipe for drift. Every Q1–Q5 answer we worked through is captured here in one place, so future contributors don't have to reconstruct intent.

---

## 2. The big picture

```
SURFACES (all on the same path)
══════════════════════════════════════════════════════════
  [bench friday chat]   [Telegram webhook]   [Slack webhook]   [A2A]   [Raven]
        │                     │                    │            │        │
        │  (each adapter resolves agent_profile, sets fields,             │
        │   writes Chat Message row direction=inbound)                    │
        └────────────────────────┬───────────────────────────────────────┘
                                 │
                                 ▼
            ┌────────────────────────────────────────────┐
            │   Chat Message INSERT (Postgres DocType)   │
            │   single source of truth for audit + state │
            └─────────────────────┬──────────────────────┘
                                  │  doc_events.after_insert
                                  ▼
            ╔════════════════════════════════════════════╗
            ║  friday_core.gateway.service.handle_inbound║
            ║  ────────────────────────────────────────  ║
            ║  reads Chat Platform.dispatch_mode:        ║
            ║    "sync"  ─► run in-line, this process    ║
            ║    "async" ─► enqueue RQ job, return       ║
            ╚═════════════════════╤══════════════════════╝
                                  │
                                  ▼
            ┌────────────────────────────────────────────┐
            │  GATEWAY PIPELINE (same code, both paths)  │
            │                                            │
            │  1. dedup check (DEFERRED — stub today)    │
            │  2. acquire session lock (Redis)           │
            │  3. join/start batch (DEFERRED — stub)     │
            │  4. permissions.matrix.check  ← Slice 2    │
            │  5. skills.loader.load_for_profile ← S3    │
            │  6. agent_runner.run_turn(...)             │
            │  7. write outbound Chat Message row        │
            │  8. publish_realtime("chat.outbound", ...) │
            │  9. mark inbound.processed = 1             │
            │ 10. release session lock                   │
            └─────────────────────┬──────────────────────┘
                                  │
                                  ▼
        ┌────────────────────────────────────────────────┐
        │ outbound row exists + publish_realtime fired   │
        └────────────────────────────────────────────────┘
                                  │
       ┌──────────────────────────┼──────────────────────────┐
       │ direct DB read           │ subscribe                │
       │ (sync surfaces; CLI)     │ (async surfaces;         │
       │                          │  Telegram, Raven later)  │
       ▼                          ▼                          ▼
   [CLI prints]            [Telegram sends]          [Raven delivers]


RECOVERY (scheduled every minute):
┌──────────────────────────────────────────────────────────────────┐
│ friday_core.gateway.recovery.sweep_orphans                       │
│  - find Chat Message processed=0 AND age > 5 min                 │
│  - re-enqueue (max 3 retries)                                    │
│  - after 3 fails: write system-error outbound, mark processed    │
└──────────────────────────────────────────────────────────────────┘
```

**Plain English:** Every surface writes an inbound Chat Message row. Frappe's `after_insert` hook fires the gateway. The gateway does all the work (permissions → menu → agent → outbound row → realtime broadcast). Subscribers (or direct DB readers) get the reply back to the user.

---

## 3. The chokepoint pattern

Every message in Friday — from any surface, to any agent, returning to any surface — flows through **one function**: `friday_core.gateway.service.handle_inbound`.

**Why one chokepoint:**
- Permission checks happen in one place, not N places.
- Audit logging happens in one place.
- Session locking happens in one place.
- Batching, dedup, recovery — all in one place.
- Adapters never import `agent_runner`. Ever. If you find yourself doing that, you've broken the rule.

This is the same shape as Hermes's `_handle_message_with_agent` (`gateway/run.py:8139`) but reimplemented on Frappe primitives (DocType row + `doc_events` hook instead of Python `MessageEvent` + executor).

---

## 4. Decision log

Each decision below names: the question, the option we picked, the alternatives we rejected, the Hermes equivalent (per project memory rule), and any deferred sub-design.

### Q1 — Sync vs async gateway execution

**Picked: Hybrid via `Chat Platform.dispatch_mode` field.**

- New field: `Chat Platform.dispatch_mode` — Select ("sync" | "async"). Default: "sync".
- CLI's "cli" platform record: `dispatch_mode="sync"`. Gateway runs inline; CLI reads outbound row after `insert()` returns.
- Future Telegram / Slack / A2A platform records: `dispatch_mode="async"`. Gateway enqueues RQ job; webhook responds 200 immediately so Telegram doesn't time out.

**Rejected:** sync-everywhere (breaks for webhooks); async-everywhere (adds ~200ms overhead to CLI for no benefit).

**Hermes equivalent:** Hermes is **all async** in its gateway daemon — every platform is an async task that pushes sync agent work to an executor pool. Friday's "sync for CLI" is a divergence forced by Frappe's bench-command model (a bench command is one-shot; it can't sit waiting on an async event loop).

### Q2 — How the CLI receives outbound

**Picked: Direct DB read after `insert()` returns, while gateway *always* fires `publish_realtime("chat.outbound", …)` for future subscribers.**

Specifically:
- CLI writes inbound row → `insert()` triggers sync gateway → by the time `insert()` returns, outbound row exists.
- CLI queries: `frappe.db.get_value("Chat Message", {session_id, direction=outbound, creation>inbound.creation}, "content")` → prints.
- The gateway *also* fires `publish_realtime("chat.outbound", {session_id, content, outbound_name})` after writing the outbound row. **Nobody subscribes today** — that's fine; it costs ~1ms and means future Telegram/Slack/Raven adapters just subscribe to the already-fired event without any gateway changes.

**Rejected:**
- Pure `publish_realtime` subscription via socket.io client in the CLI — adds `python-socketio` dependency, API key auth setup, threading.Event coordination, ~30 LOC of CLI overhead, all for delivery to one user's terminal where a 1-line DB read works.
- Short-poll loop — pointless when the gateway is sync.
- Per-session Redis BLPOP — duplicates state between DB and Redis.

**Hermes equivalent:** Hermes's local CLI doesn't have this problem — it calls AIAgent in-process and prints to stdout. Hermes's *platforms* use an internal queue + edit-message pattern. Our Q2 choice is the Frappe-native analogue of Hermes's CLI behavior (in-process delivery) plus the publish_realtime broadcast that prepares for the Hermes platform-adapter pattern when our equivalents land.

**Auth note (locked but unused today):** when a Python surface eventually subscribes to socket.io, it authenticates via Frappe API key + secret (standard Frappe pattern, same as `frappe-client`). Not via cookie, not via localhost bypass.

### Q3 — Agent Profile resolution

**Picked: Adapter-local resolution. Gateway validates. `Chat Platform.default_agent_profile` field for fallback. Stub `friday_core.routing` package as future seam.**

Specifically:
- Every adapter MUST set `Chat Message.agent_profile` before insert. Gateway validates (raises if empty).
- New field: `Chat Platform.default_agent_profile` (Link → Agent Profile). For non-CLI surfaces that need a default.
- `friday_core.routing.resolve.resolve_profile(platform, sender_id=None, chat_id=None, content=None)` exists as a stub that today returns `Chat Platform.default_agent_profile`. Future adapters that want richer routing call this; CLI doesn't.

**Rejected:**
- Adapter-local with no shared helper — risks divergent logic per adapter.
- Full central resolver + `Platform Profile Mapping` DocType today — premature; we'll know what rules people want when first webhook adapter lands.

**Hermes equivalent:** Hermes hardcodes "one bot per profile" per platform adapter — essentially adapter-local with no central helper. Our stub helper is a small forward-looking improvement.

### Q4 — Per-session concurrency

This was three sub-questions (B = lock, C = batching, D = dedup). We accepted full B+C+D originally, then revised under the single-tenant lens:

**Q4-B Picked: Redis per-session lock.** Full implementation now.
- Key: `friday:session_lock:{session_id}`
- TTL: 300s (5 min — survives a stuck worker)
- Wait timeout: 30s — if a second inbound waits >30s, gateway writes a "session busy" outbound and gives up.
- Cheap, prevents race conditions, sets the contract early.

**Q4-C Batching: DEFERRED with documented design.**
- Today: stub `friday_core.gateway.batching.flush_batch(session_id)` exists; returns the single inbound row unchanged. No queue, no timer.
- Documented design (when first bursty surface lands):
  - `Chat Platform.batch_idle_ms` Int field, default 0. CLI=0 (flush immediately). Telegram=500. Per-platform.
  - Max batch size: 5 messages (hardcoded for first version; configurable later if needed).
  - `agent_runner.run_turn(profile, session, messages: list[InboundMessage]) -> str` — signature evolves to accept a list. **Backwards compatible** with today's `content: str` via overload or by always wrapping a single string in a single-element list at call site.
  - Mid-run inbound: buffer for next batch (Option B from Q4-C sub-decisions). Predictable; no mid-LLM-cancel mess.

**Q4-D Dedup: DEFERRED.**
- No code in Slice 4.
- Documented API shape when first webhook adapter lands: `friday_core.routing.dedup.is_duplicate(platform, sender_id, content, time_window_secs=5) -> bool`. Adapter-side check before writing inbound row. Hash key in Redis `friday:dedup:{hash}` with 5s TTL.

**Hermes equivalent:** Hermes does per-session lock (`SessionStore._lock` threading.Lock; we use Redis because we're multi-process). Hermes does dedup per-platform (`_quick_key` in `_handle_message_with_agent`; we deferred this). Hermes doesn't have batching (single-user assumed); ours is a Friday-specific deferred addition.

### Q5 — Idempotency and crash recovery

**Picked: Half-step — at-least-once recovery now; per-tool idempotency framework deferred.**

Specifically:
- **Now in Slice 4:**
  - `Chat Message.processed` (existing field) — gateway sets to 1 after outbound row written.
  - `Chat Message.retry_count` (new Int field, default 0) — incremented by recovery sweeper.
  - `Chat Message.failure_reason` (new Small Text field) — set after final give-up.
  - `friday_core.gateway.recovery.sweep_orphans()` — scheduled task every minute. Finds inbound rows where `processed=0` AND age > 5 min AND platform is async; re-enqueues up to 3 times; after 3 fails, writes system-error outbound.
  - `Skill.idempotent` (new Check field) — reserved seam. Tools self-declare from day one.
  - `Skill.idempotency_strategy` (new Select field: "key-only" | "payload-hash" | "external-id-callback" | "manual") — reserved seam.
- **Deferred to Slice 6** (when first real tool lands):
  - Tool execution cache (Redis or Postgres — decided when we know tool result sizes).
  - Idempotency key derivation (depends on whether tools run parallel within a turn).
  - Tool author contract for retry semantics.

**Rejected:** Full per-tool idempotency framework now — designs blind without real tools; framework will be wrong; rebuild guaranteed in Slice 6.

**Hermes equivalent:** Hermes does per-tool idempotency (not a framework — each tool implements its own). Hermes does NOT have a recovery sweeper because Hermes's gateway is one process; if it dies mid-turn, user just sees timeout. Our recovery is forced by multi-process.

**Sync mode bonus:** Frappe's `after_insert` hook runs inside the inbound row's transaction. If the gateway raises, the inbound row's insert is rolled back automatically. **Sync mode (CLI) gets atomic recovery for free** — no orphan rows possible.

---

## 5. Schema changes summary

Six new DocType fields total:

| DocType | Field | Type | Purpose |
|---|---|---|---|
| `Chat Platform` | `dispatch_mode` | Select (sync \| async) | Q1 — controls gateway execution model per platform |
| `Chat Platform` | `default_agent_profile` | Link → Agent Profile | Q3 — fallback profile when adapter doesn't resolve one |
| `Chat Platform` | `batch_idle_ms` | Int (default 0) | Q4-C — per-platform batching window (today only consumed by stub) |
| `Chat Message` | `retry_count` | Int (default 0) | Q5 — incremented by recovery sweeper |
| `Chat Message` | `failure_reason` | Small Text | Q5 — populated after final give-up |
| `Skill` | `idempotent` | Check | Q5 — tool author self-declaration (reserved seam) |
| `Skill` | `idempotency_strategy` | Select | Q5 — reserved seam |

Single migration. No data loss; all new fields are nullable / defaulted.

---

## 6. Hermes comparison (per project memory rule)

| Concern | Hermes does | Friday does | Justification |
|---|---|---|---|
| Process model | One async daemon | Frappe multi-process (gunicorn + RQ + bench) | **Forced** by Frappe |
| Message coordination | `MessageEvent` Python dataclass | `Chat Message` DocType row | **Forced** by multi-process; bonus: free audit |
| CLI ↔ agent path | Direct in-process call (CLI bypasses gateway) | Same gateway path as platforms (unified chokepoint) | **Strategic choice** — single-tenant but multi-surface |
| Session lock | `threading.Lock` in SessionStore | Redis lock | **Forced** by multi-process |
| Dedup | Adapter-side `_quick_key` | Adapter-side helper (deferred) | **Same pattern**, deferred until needed |
| Batching | None (single-user assumed) | Per-platform `batch_idle_ms` (deferred) | **Friday-only**; deferred today |
| Streaming | `GatewayStreamConsumer` sync→async queue | Will port the same pattern when streaming lands | **Same intent**, not in Slice 4 |
| Agent caching | In-process LRU 128, TTL 1h | Per-RQ-worker cache (Slice 8) | **Different** — multi-process forces per-worker cache instead of shared |
| Permission engine | None | `friday_core.permissions` | **Friday-only addition** |
| Recovery | Per-tool retry inside agent | Cross-process sweeper | **Forced** by multi-process |
| Tool execution | Inline `concurrent.futures` | RQ workers (Slice 6+) with idempotency | **Forced** by sandbox + process isolation requirements |

---

## 7. What we lose vs Hermes (honest accounting)

Worth knowing as we build:

- **Per-turn baseline latency ~10ms** before agent runs (DB roundtrip + doc_events + publish_realtime). Hermes is <1ms. Negligible vs LLM call times.
- **Long-conversation memory** loaded per turn (Slice 5/6 will need context summarization, à la Hermes's `trajectory_compressor.py`).
- **Streaming will be ~150 LOC heavier** when we build it (process boundary crossing).
- **Tool authoring complexity** — tools may run in different processes than callers; idempotency contract applies (lands Slice 6).
- **Distributed debugging** — every log line must include `session_id` from day 1.
- **Postgres becomes a bottleneck** at high message rates — index `Chat Message` on `(session_id, direction, creation)` from the start.
- **Operations playbook** has more parts (gunicorn + RQ + Redis + Postgres + socketio).

What we gain in return: multi-surface uniformity, queryable audit, admin-configurable runtime, permission engine, crash recovery, multi-agent within one tenant.

---

## 8. Deferred subsystems — when they land

These are NOT in Slice 4. Their designs are committed above so the slice that activates them can move fast.

| Subsystem | Activates in slice | Source of truth in this doc |
|---|---|---|
| Q4-C batching (queue + timer + list signature) | First bursty surface (likely Slice 7/8 with Telegram or A2A real use) | §4 Q4-C |
| Q4-D dedup helper | First webhook adapter (likely Slice 7) | §4 Q4-D |
| Q5 per-tool idempotency cache | First real tool (Slice 6) | §4 Q5 |
| publish_realtime CLI subscriber | If/when a use case for out-of-band delivery to CLI appears | §4 Q2 |
| Streaming (send + progressively edit) | First streaming-capable surface | §6 "Streaming" row |
| Agent cache | Slice 8 RQ-worker model | §6 "Agent caching" row |

---

## 9. Operating principle

**One chokepoint. Many surfaces. Same code path for every message.**

Every Friday slice that touches message flow must respect this. If a future feature wants a surface to call the agent directly, **say no** and route it through the gateway. The chokepoint is the whole reason the architecture is coherent.

---

## 10. Status

This document is the **authoritative contract** for gateway behavior as of Slice 4. Subsequent slices that modify gateway behavior must:

1. Update this document in the SAME PR as the code change.
2. Append a dated decision-log entry to §4 with the question, options, and rationale.
3. Honor §9 (the chokepoint principle).

Single-tenant scope (`feedback_single-tenant-not-saas`) governs every reading of this doc. Re-examine if/when Friday explicitly becomes multi-tenant.
