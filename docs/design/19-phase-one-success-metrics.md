# 19 — Phase One Success Metrics

> **Purpose:** Define the concrete, measurable criteria by which Phase 1 succeeds or fails. These metrics override personal feelings about progress. If they aren't green, Phase 1 is not done.

This document complements doc 06 (Phase One Scope), doc 11 (Validation Checklist), and doc 42 (Phase One Authority Contract). Where this document conflicts with doc 42, doc 42 wins.

---

## 1. The North-Star Metric

> **Friday proves the governed framework loop end-to-end: profile, skill, permission check, sandboxed execution, immutable logs, configurable task workflow, and Control Room visibility.**

If this single metric is green, v0.1 succeeded. If it is not green, no amount of feature breadth compensates.

The ERPNext Purchase Order workflow remains the first Phase 1 flagship dogfood after the governed loop is green. It is not removed; it is sequenced behind the framework proof.

---

## 2. Tier 1 Metrics (Must Hit — Phase 1 fails without these)

### M1.1 — End-to-end governed framework loop
- [ ] User creates or submits work into Friday
- [ ] Friday resolves the correct Agent Profile
- [ ] Active Skills are loaded from governed DocTypes
- [ ] Skill invocation is permission-checked before execution
- [ ] Denied calls are rejected and logged
- [ ] Permitted call executes through the sandboxed path
- [ ] Execution Log and Permission Decision Log are written
- [ ] Agent Task moves through configurable workflow states
- [ ] Control Room shows the task, agent, execution, and audit trail

### M1.2 — Zero unsafe actions
- [ ] No permission boundary violations across the dogfood week
- [ ] No skill executed without prior permission decision logged
- [ ] No agent action taken outside its Agent Role Profile's scope
- [ ] No credential leaked into logs or War Room messages

### M1.3 — Full audit trail
- [ ] Every skill invocation has an Execution Log row (submitted, immutable)
- [ ] Every permission decision has a Permission Decision Log row
- [ ] Every approval has a Workflow Request row with decision and reason
- [ ] An external auditor (or someone playing one) can trace any agent action to: who, what, why, when, with what credentials

### M1.4 — All Phase 1 Validation Checklist boxes green
Every checkbox in doc 11 (slices 1–9) must be ticked and human-acknowledged. No exceptions, no "we'll fix this in Phase 2".

---

## 3. Tier 2 Metrics (Should Hit — strong signals of architectural soundness)

### M2.1 — Latency
- [ ] Permission check median: < 5ms (warm cache)
- [ ] Skill loader cold-cache load: < 100ms for an agent with 50 permitted skills
- [ ] Gateway dispatch from inbound message to LLM call: < 200ms
- [ ] End-to-end skill execution (CLI → Docker → reply, excluding LLM time): < 3 seconds median, < 10 seconds p95

### M2.2 — Throughput
- [ ] Dispatcher handles 500 Tasks/minute on a single worker without backpressure
- [ ] Permission engine handles 1000 checks/second with warm cache
- [ ] System sustains 10 concurrent agents on a single 8-core / 16GB host

### M2.3 — Reliability
- [ ] No silent failures across the dogfood week (every error visible in logs and a Frappe error log)
- [ ] Skill execution success rate ≥ 95% for skills marked `Active` (excluding LLM-attributable failures)
- [ ] Docker container clean shutdown rate ≥ 99% (no leftover containers polluting the host)
- [ ] Dispatcher concurrency: 0 double-claims across 10,000 simulated task claims

### M2.4 — Test coverage
- [ ] Overall coverage ≥ 70%
- [ ] Critical modules (`permissions`, `gateway`, `agents/isolation`, `tasks/dispatcher`) ≥ 85%
- [ ] No skipped or xfailed tests without a tracked issue

---

## 4. Tier 3 Metrics (Nice to Hit — quality-of-life and operability)

### M3.1 — Developer experience
- [ ] Time-to-first-running-agent for a new developer (cold install): < 30 minutes
- [ ] `bench migrate` from empty site to current state: < 60 seconds
- [ ] CI green-build wall-clock: < 10 minutes

### M3.2 — Documentation
- [ ] README install steps work verbatim on a fresh Ubuntu 22.04 VM
- [ ] Quickstart walks a developer from clone → first running agent in < 30 minutes
- [ ] Every public function in `friday/permissions/` and `friday/gateway/` has a docstring
- [ ] Architecture diagram is current with the code (not aspirational)

### M3.3 — Operability
- [ ] Health-check endpoint returns green when all subsystems are nominal
- [ ] Frappe error log has zero unhandled exceptions after the dogfood week
- [ ] Disk usage growth predictable: < 1 MB/day per active agent in steady state (excluding skill outputs)
- [ ] Restart safety: gateway can be killed and restarted mid-execution without data loss

### M3.4 — Security posture
- [ ] No hard-coded credentials anywhere in the codebase (verified via `git secrets` or `trufflehog`)
- [ ] All Friday DocTypes with sensitive fields use Frappe `Password` type
- [ ] Docker images built from pinned base, scanned with `trivy`, no critical CVEs
- [ ] Dependency audit (`pip-audit`, `npm audit`) clean

---

## 5. Anti-Metrics — What We Don't Measure (Yet)

To prevent vanity:

- **Not measured in Phase 1:** GitHub stars, Twitter followers, blog traffic
- **Not measured in Phase 1:** LLM tokens used, cost per execution
- **Not measured in Phase 1:** Number of skills in the library (quality > quantity at this stage)
- **Not measured in Phase 1:** Number of agents instantiated (one well-behaved agent > ten flaky ones)

These matter in Phase 2 and beyond. In Phase 1 they're noise.

---

## 6. Measurement Mechanism

### Continuous (during build)
- CI captures test coverage and latency benchmarks on every PR
- Pre-commit hooks enforce code quality gates
- Dependency audit runs nightly

### Per-slice gate (during Phase 1)
- Doc 11 Validation Checklist green before merging the slice
- Human acknowledgement (one approving reviewer) required

### End-of-Phase
- Run the governed framework loop repeatedly through the validation checklist
- After v0.1 is green, run the ERPNext PO flagship dogfood as the Phase 1 business validation
- Operators check in daily; record any intervention
- At end of week, compile a **Phase 1 Completion Report** (template in §7)

### External review
- Optional: an external developer (not on the build team) tries to install and run Friday from the README only. Time spent + friction points recorded.

---

## 7. Phase 1 Completion Report Template

When all metrics are evaluated, produce:

```markdown
# Friday Phase 1 — Completion Report

## Dates
- Build started: ___
- Phase 1 complete: ___
- Dogfood week: ___ to ___

## Tier 1 (Must-Hit)
- [ ] M1.1 End-to-end governed framework loop — evidence: ___
- [ ] M1.2 Zero unsafe actions — evidence: ___
- [ ] M1.3 Full audit trail — evidence: ___
- [ ] M1.4 Validation checklist green — evidence: link to checklist

## Tier 2 (Should-Hit)
- [ ] M2.1 Latency — measured: ___
- [ ] M2.2 Throughput — measured: ___
- [ ] M2.3 Reliability — measured: ___
- [ ] M2.4 Coverage — measured: ___

## Tier 3 (Nice-to-Hit)
- [ ] M3.1 DX — measured: ___
- [ ] M3.2 Docs — measured: ___
- [ ] M3.3 Operability — measured: ___
- [ ] M3.4 Security posture — measured: ___

## Known Limitations
- [list each with planned Phase 2 resolution]

## Deferred to Phase 2
- [list with issue links]

## Decision
- [ ] Phase 1 complete. Proceed to open-source launch (doc 17).
- [ ] Phase 1 incomplete. Re-scoping required: ___
```

---

## 8. Failure Modes and Responses

### If M1.1 (end-to-end) fails
The framework loop is not coherent enough. Identify whether the break is profile resolution, skill loading, permission gating, sandbox execution, task workflow, logging, or Control Room visibility. Architectural gaps block v0.1 completion.

### If M1.2 (unsafe actions) fails
Stop everything. A safety incident is a critical bug. Root-cause analysis required, fix shipped, dogfood week restarted.

### If M1.3 (audit trail) fails
This is a design failure, not a coverage gap. Audit isn't a feature — it's a property of every action. If actions slipped past audit, the gateway/permission integration is wrong. Block launch.

### If Tier 2 metrics fail
Document the gap, set a Phase 2 target, ship Phase 1 anyway **if** Tier 1 is fully green and the gap is performance/scale rather than correctness.

### If Tier 3 metrics fail
Ship anyway. Track as Phase 2 items.

---

## 9. The Honest Question

At the end of Phase 1, ask:

> **Would I run my own business on this?**

If the founder answers no, the launch is premature regardless of what the metrics say. Build until the honest answer is yes.
