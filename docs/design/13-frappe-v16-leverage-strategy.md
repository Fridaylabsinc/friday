# 13 — Frappe v16 Leverage Strategy

> **Purpose:** Map Frappe v16's new capabilities to specific Friday features so the design takes maximum advantage of the framework's December 2025 release. Friday targets v15 for Phase 1 stability and is forward-compatible with v16; this document defines what changes when v16 is adopted.

---

## 1. Frappe v16 Headline Improvements

Based on the v16 release announcements (Dec 2025) and migration notes:

| Area | v16 Change | Significance for Friday |
|---|---|---|
| Performance | ~2× faster via Caffeine cache, leaner request lifecycle, ~30% server-load reduction | Lower dispatcher latency, faster permission checks, more agents per host |
| Workspace | Redesigned, persistent sidebar, embeddable views | War Room workspace layout |
| Workflow | State transition **actions** that fire automatically | Auto-trigger agent skills on state changes without custom hooks |
| Permissions | Faster matrix resolution, field-level masking | Sensitive credentials, PII protection in War Room |
| UI | Scrollable child tables with sticky columns, unlimited list columns | Kanban + execution log UX |
| Background jobs | Better RQ monitoring, async control, retry observability | Agent execution observability |
| Naming | UUID-based DocType naming | Globally unique agent IDs across sites |
| API | REST improvements, type-safer signatures | Cleaner agent → Frappe REST contract |
| Real-time | Improved socket.io handling, lower overhead | Faster War Room and Kanban updates |
| Developer tools | Automated linting, simplified app deps | Smoother Friday CI/CD |
| Evaluations | Eval expressions for dynamic fields, date/time expressions | Smarter Skill parameter validation |

---

## 2. Performance Wins Mapped to Friday Bottlenecks

Friday's hot paths (see doc 38 / performance) all benefit:

| Friday Bottleneck | v16 Win |
|---|---|
| Permission check on every skill invocation | Faster matrix resolution → tighter latency budget |
| Skill loader cache warm-up | Lower DB round-trip cost |
| Dispatcher tick query (scan pending tasks) | Caffeine cache + leaner SQL |
| Real-time event publishing (War Room, Kanban) | Lower socket.io overhead |
| Concurrent agent runs in same site | ~30% less server load → headroom for 30% more concurrent agents on the same host |

**Target:** with v16, the gateway should sustain ~1000 skill executions per minute on a single 8-core / 16GB host, vs. the ~500 baseline on v15.

---

## 3. Workflow State Transition Actions

v15 requires custom `on_update` hooks to trigger side effects on Agent Task state changes. v16 lets us declare them in the Workflow definition itself:

```yaml
# Conceptual v16 workflow action declaration
workflow: Agent Task
states:
  - name: Pending
    transitions:
      - to: Assigned
        actions:
          - call: friday.dispatcher.notify_assigned_agent
  - name: Assigned
    transitions:
      - to: Executing
        actions:
          - call: friday.gateway.spawn_runner
      - to: Blocked
        actions:
          - call: friday.escalation.start
  - name: Blocked
    transitions:
      - to: Review
        actions:
          - call: friday.workroom.post_blocker_to_warroom
```

**Benefit:** the workflow itself is the source of truth for what fires when, vs. scattered Python hooks. Easier to audit, easier to change without redeploy.

---

## 4. Field-Level Permission Masking

v16 supports per-field masking based on role. Useful for:

| Friday DocType | Field | Masked from |
|---|---|---|
| Agent Profile | API token, LLM provider key | Any role except `Friday Admin` |
| Execution Log | `parameters.password`, `parameters.secret_*` | Even admins (always masked in audit trail unless explicitly unmasked) |
| Chat Message | Content matching credit-card / SSN regex | Roles without `PII Reader` |
| Workflow Request | Justification with embedded secrets | Re-masked after read |

This eliminates one entire class of accidental disclosure: an operator looking at an Execution Log row in the Desk no longer sees raw API tokens, even if they have read access to the document.

---

## 5. UUID Naming for Agents and Tasks

v15 default naming uses incrementing IDs scoped per site. v16 supports UUIDs at DocType level.

**Why this matters for Friday:**
- Multi-site agent-to-agent communication (doc 37) needs globally unique agent IDs.
- Cross-site delegation references avoid collisions without prefixing.
- Audit logs exported from multiple sites concatenate cleanly.

**Plan:** flip `Agent Profile`, `Agent Task`, `Execution Log`, `Permission Decision Log` to UUID naming on the v16 migration.

---

## 6. Real-Time Improvements for War Room

Frappe v16's socket.io handling is leaner. War Room (doc 16 / Raven integration) benefits:

- Lower per-event latency (target <50ms end-to-end from skill completion → message visible in War Room)
- More concurrent subscribers per site without server saturation
- Better reconnection semantics for flaky mobile clients

The Kanban view also picks this up — Task state changes propagate to the live board in near-real-time.

---

## 7. Background Job Observability

v15 RQ visibility is functional but spare. v16 adds:
- Job-level retry observability
- Queue depth and processing rate metrics
- Per-job tracing IDs

**Friday application:**
- Surface RQ metrics into a Friday dashboard for agent execution monitoring.
- Use tracing IDs to correlate: gateway request → RQ job → Docker container → result.
- Alert when queue depth or retry rate exceeds thresholds.

---

## 8. Workspace Layout for War Room

v16's redesigned workspace with embeddable views lets us compose the War Room as a single workspace page:

```
[ War Room Workspace for Project X ]
┌─────────────────────────────────────────────────────────┐
│ Pinned project brief (Raven message)                    │
├──────────────────────┬──────────────────────────────────┤
│ Kanban view          │ Active Raven channel             │
│ (Agent Task by state)│ (embedded chat)                  │
├──────────────────────┴──────────────────────────────────┤
│ Agent status panel (Vue component)                      │
├─────────────────────────────────────────────────────────┤
│ Recent Execution Logs (filterable list view)            │
└─────────────────────────────────────────────────────────┘
```

No custom shell needed — the workspace primitive handles layout, persistence, and per-user customisation.

---

## 9. Eval Expressions for Dynamic Skill Parameters

v16 lets DocType fields use eval expressions for visibility, defaults, and validation. Friday Skills use this for parameter schemas that depend on runtime context:

```
# Skill: "send_invoice"
parameters_schema = {
  "invoice_id": {"type": "Link", "options": "Sales Invoice"},
  "include_pdf": {"type": "Check", "default": "eval: frappe.db.get_single_value('Friday Settings', 'attach_pdf_default')"},
  "send_to": {"type": "Data", "depends_on": "eval: doc.invoice_id != null"}
}
```

This makes Skills more dynamic without inflating their LLM-facing schema.

---

## 10. Migration Plan: v15 → v16

Friday targets v15 for Phase 1. The v16 migration plan:

1. **Compatibility audit** — verify every Friday DocType, hook, and Workflow under v16.
2. **UUID switchover** — Phase 2 migration: rename naming series on key DocTypes.
3. **Workflow Actions migration** — move custom `on_update` hooks into declared workflow actions.
4. **Field masking** — enable for sensitive Agent Profile and Execution Log fields.
5. **Workspace refresh** — rebuild War Room as a v16 workspace.
6. **RQ observability dashboard** — surface new metrics in Friday admin views.
7. **Performance re-benchmark** — quantify gains; expect ~2× headroom.

**Estimated effort:** 2–3 weeks of focused engineering, mostly mechanical.

---

## 11. What v16 Does **Not** Solve

To keep expectations honest:

- v16 does not introduce native vector search → pgvector is still the right call.
- v16 does not change the agent-loop architecture → Hermes-derived agent runtime remains custom.
- v16 does not provide LLM provider abstractions → Friday still owns this layer.
- v16 does not eliminate the need for Docker sandboxing → security model in doc 04 unchanged.
- v16 does not solve multi-site coordination → doc 37 still applies.

v16 is an excellent foundation upgrade. It is not a substitute for Friday's agentic layer.

---

## 12. Decision

**Phase 1: target Frappe v15 stable.** Newer is not always better; v15 is battle-tested by the entire ERPNext community.

**Phase 2: migrate to v16** once stable for ~6 months and our DocTypes are settled. Use the v16 migration as a forcing function to also audit and tighten Phase 1 design decisions.

**No Friday code should be locked to v15-only patterns** — write defensively so the v16 migration is mechanical.
