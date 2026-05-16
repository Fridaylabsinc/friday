# 42 — Phase One Authority Contract

> **Purpose:** Establish the single source of truth for Friday v0.1 / Phase 1 scope. Where older documents describe a broader Phase 1, this contract wins.

---

## 1. Authority

This document resolves the Phase 1 contradictions identified in `40-gap-analysis-and-resolution-plan.md`.

Implementation priority:

1. `39-friday-framework-strategy.md` — framework identity and fork discipline
2. `41-porting-strategy-hermes-erpnext-raven.md` — Hermes / ERPNext / Raven translation
3. This document — v0.1 scope authority
4. `06-phase-one-scope.md`, `10-agent-execution-guide.md`, `11-agent-validation-checklist.md`
5. Other design documents as roadmap context

If any older document says "Phase 1" and conflicts with this contract, read it as roadmap context unless this document explicitly includes it.

---

## 2. Phase 1 Goal

Phase 1 proves the governed framework loop and Friday product feel.

The required proof:

> A user can create or send work into Friday, Friday resolves an Agent Profile, loads governed Skills from DocTypes, checks permissions, executes one approved skill in a sandboxed path, records immutable logs, updates an Agent Task through a configurable workflow, and shows the result in the Control Room.

This is the foundation. ERPNext Purchase Order automation remains inside the Phase 1 program as the flagship dogfood track, but it starts after the governed framework loop is green. The mistake to avoid is making PO automation the first thing we code before the framework has identity, permissions, workflow, and audit.

---

## 3. In Scope For v0.1

### Framework Shell

- Frappe-derived Friday repository and product identity
- bench remains available for operations
- Friday-facing agent commands or bench command group
- Friday Control Room workspace
- minimal, documented core divergence only where app/module hooks are insufficient

### Agent Kernel

- `Agent Profile`
- `Agent Role Profile` if Frappe Role Profile is insufficient after spike
- `Skill`
- `Execution Log`
- `Permission Decision Log`
- `Workflow Request` schema
- `Agent Project`
- `Agent Task`
- `Agent Task Event` or equivalent timeline/event record

### Workflow And Board

- configurable `Agent Task` workflow
- first workflow template may be simple
- Kanban renders workflow states as columns
- states can be marked dispatchable
- dispatcher claims only dispatchable tasks
- blocked / completed / failed outcomes are explicit

### Execution

- one end-to-end skill, such as `create_note`
- permission check before skill execution
- sandboxed execution path
- structured result capture
- immutable Execution Log
- immutable Permission Decision Log

### Product Surface

- Control Room shows at minimum:
  - active tasks
  - active / suspended agents
  - recent executions
  - permission denials
  - task state changes
  - pause / suspend path for agents

### Raven

Raven is optional for v0.1 unless the technical feasibility spike proves it is low-risk to include.

If included, Raven is a War Room bridge only:

- conversation surface
- task / execution event posting
- message actions routed through Friday permission checks

Raven does not own task truth, execution truth, permissions, or audit.

---

## 4. Out Of Scope For v0.1

- autopilot
- autonomous profile activation
- autonomous skill activation
- autonomous workflow activation
- learning loop that changes active skills
- semantic memory / wiki / knowledge graph
- cross-site agent communication
- multi-platform adapters beyond CLI or Raven if included
- deep Raven fork
- full ERPNext domain-agent suite
- production-grade multi-host scaling

---

## 5. Sandbox Minimum Bar

Phase 1 must not be unsafe, but it does not need the final production sandbox.

Required:

- non-root container user
- resource limits
- timeout handling
- OOM handling
- no host source or Docker socket mounts
- scoped credentials
- structured stdout/stderr/result capture
- cleanup / janitor path
- Execution Log for every attempt

Phase 1.5 / hardening:

- warm pool
- egress proxy / allowlist enforcement
- read-only rootfs for every runtime
- full automated security attack suite
- multi-host orchestration
- gVisor / Firecracker backend

---

## 6. ERPNext PO Flagship Track

ERPNext PO automation remains the first named business use case of Phase 1.

It begins after v0.1 proves the framework loop:

1. Agent Project / Agent Task orchestration works.
2. Agent Profile and Skill governance works.
3. Permission and execution logs are reliable.
4. The dispatcher handles configurable workflows.
5. The Control Room lets a human understand and stop the system.

Only then should Friday attempt the PO track.

The PO dogfood is the **Phase 1 flagship validation**, not the **first engineering slice**.

Minimum PO track:

- Procurement Agent profile
- Inventory read-only support or alerts
- Coordinator Agent basic oversight
- Operations Policy DocType
- PO draft / supplier follow-up / GRN matching / variance flagging
- human approval for high-risk or financially binding actions
- zero unsafe actions
- full audit traceability

---

## 7. Completion Gate

v0.1 is complete when:

- A Friday site installs and migrates cleanly.
- Control Room exists.
- Agent Profile, Skill, Agent Project, Agent Task, Execution Log, and Permission Decision Log exist.
- A user can create or submit a task.
- Dispatcher claims a dispatchable task once and only once.
- Agent executes one approved skill through the governed path.
- Denied skill calls are logged and rejected.
- Task state changes are visible in list/report/Kanban views.
- Execution and permission logs are sufficient to reconstruct what happened.
- Tests cover permission checks, dispatcher claim safety, and the first end-to-end skill.

After this, Friday starts the ERPNext PO flagship track with a stable foundation.

---

## 8. Summary

Phase 1 is not "build all of Friday."

Phase 1 is:

> Build the smallest Friday that proves agents can operate inside a typed, permissioned, auditable Frappe-derived framework.
