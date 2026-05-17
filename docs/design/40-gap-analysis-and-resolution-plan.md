# 40 — Gap Analysis & Resolution Plan

> **Purpose:** Capture the gaps, contradictions, and missing decisions discovered after reading the full Friday dossier. This document is not a new feature spec. It is a control document for deciding what must be clarified before implementation begins.

---

## 1. Executive Summary

Friday's core thesis is strong: use a Frappe-derived framework substrate to make AI agents governed, auditable, permission-bound business actors.

The current dossier has one major issue: several documents define different versions of "Phase 1." If implementation starts without resolving this, a coding agent will bounce between incompatible targets.

The immediate resolution is to establish a **Phase 1 Authority Contract** that decides which capabilities are required for v0.1 and which are vision/roadmap.

---

## 2. Highest-Priority Gaps

### Gap 1 — Competing Phase 1 Definitions

There are three Phase 1 shapes in the docs:

| Source | Phase 1 Meaning |
|---|---|
| `06`, `10`, `11` | Governed runtime MVP: CLI, Agent Profile, Skill, permission check, Docker execution, logs |
| `14`, `16`, `24` | Integrated platform: Raven, ported ERPNext Project/Task/Issue, Agent Role Profile, file-mirrored skills, hardened sandbox |
| `19`, `30`, `35` | ERPNext business autonomy: 7-day Purchase Order workflow with Procurement/Inventory/Coordinator agents |

**Resolution:** Created `42-phase-one-authority-contract.md`.

**Recommended decision:** Phase 1 proves the governed framework loop and Friday product feel. ERPNext PO automation becomes the first flagship demo/use case after the runtime is proven, not the definition of v0.1 completion.

---

### Gap 2 — Product Surface Is Under-Specified

The architecture is strong, but the product surface is not yet described sharply enough.

Friday should not merely expose records. Operators need a control-room experience:

- What can this agent access?
- What is it doing now?
- What did it do?
- Why did it do that?
- What will happen if I approve?
- How do I pause or revoke it?

**Resolution needed:** Add a Control Room product spec.

**Recommended decision:** The Control Room is the primary product surface. The agent runtime is the engine.

---

### Gap 3 — Frappe-Derived Framework Strategy Needs Implementation Rules

Doc `39` now states the strategy, but implementation needs concrete fork rules:

- Which upstream Frappe branch is the substrate?
- What files/modules may be changed in core?
- How are divergences documented?
- How often are upstream releases reviewed?
- What compatibility promise exists for existing Frappe apps?

**Resolution needed:** Add `FORK_POLICY.md` or a dedicated section in the Phase 1 contract.

**Recommended decision:** Thin core divergence, app/module-heavy implementation. Modify framework core only for agent-native identity, audit, permission, workflow, job, trace, or product-shell behavior that cannot be safely implemented as modules.

---

### Gap 4 — Tech Stack Version Decision Is Still Open

The docs target Frappe v15, while research shows v16 is real and has longer support, but also raises setup requirements and compatibility risk.

Open decisions:

- Frappe v15 vs v16 substrate
- PostgreSQL from day one vs MariaDB first
- Raven from day one vs later
- ERPNext dependency vs ported DocTypes vs runtime-only first

**Resolution needed:** Run a technical feasibility spike before coding product features.

**Recommended decision:** Test Frappe v16 + PostgreSQL + Raven + minimal Friday DocTypes. If smooth, choose v16. If rough, use v15 or a reduced stack for v0.1.

---

### Gap 5 — Raven Scope Conflicts

Docs `06` and `10` define CLI-first messaging. Docs `14` and `16` bring Raven and War Rooms into Phase 1.

**Resolution needed:** Decide whether Raven is part of v0.1 or v0.2.

**Recommended decision:** Control Room first. Raven is included only if it directly supports the first trust experience. Otherwise, start with Frappe Workspace/Desk + CLI and add Raven bridge next.

---

### Gap 6 — Memory / pgvector Scope Conflicts

Doc `06` defers pgvector memory. Docs `26`, `28`, `33`, and `34` include pgvector-backed docs/wiki/memory in Phase 1.

**Resolution needed:** Separate "PostgreSQL chosen for future vector capability" from "memory feature shipped in Phase 1."

**Recommended decision:** Phase 1 may install PostgreSQL/pgvector if the stack uses it, but no semantic memory, wiki search, framework doc lookup, or knowledge graph is required for v0.1.

---

### Gap 7 — Sandbox Scope Conflicts

Doc `06` says Phase 1 uses basic Docker resource caps and defers full network isolation. Doc `24` requires hardened Docker, egress allowlist, warm pool, janitor, observability, and security tests in Phase 1.

**Resolution needed:** Define a minimum sandbox bar for v0.1.

**Recommended decision:** Phase 1 must include non-root container execution, resource limits, timeout/OOM handling, no host mounts, structured result capture, and Execution Log recording. Warm pool, egress proxy, and full security test suite can be Phase 1.5 unless needed for trust demo.

---

### Gap 8 — Approval / Autopilot Scope Conflicts

Doc `06` defers approval workflows except schema. Docs `19`, `30`, and `35` require approval gates and discuss autopilot-style behavior.

**Resolution needed:** Distinguish approval infrastructure from autopilot.

**Recommended decision:** Phase 1 supports manual approval records/workflow requests only for high-risk skill calls if needed. No autopilot. Autopilot remains Phase 2+ after real execution evidence exists.

---

### Gap 9 — Security Claims Need Evidence

Docs `04` and `20` make strong claims about Hermes/OpenClaw CVEs and vulnerability counts.

**Resolution needed:** Either add citations from primary sources or soften the claims before public release.

**Recommended decision:** Replace uncited competitor-specific security claims with broader architectural risk statements until sources are verified.

---

### Gap 10 — Legal / License Decision Remains Open

Docs say GPL v3 now, AGPL v3 under consideration later.

**Resolution needed:** Pick launch license before public release.

**Recommended decision:** Keep GPL v3 for private/internal Phase 1 while evaluating AGPL v3 before public release, especially if hosted/SaaS protection matters.

---

## 3. Missing Documents

The dossier has added the main authority documents. Remaining pre-implementation gap:

1. `docs/security-claims-audit.md`
   - Source verification for public claims about Hermes/OpenClaw/security posture.

Completed:

- `42-phase-one-authority-contract.md` — single source of truth for v0.1 scope.
- `43-control-room-product-spec.md` — operator-facing trust UX: permissions, live activity, approvals, audit replay, pause/revoke.
- `44-technical-feasibility-spike.md` — Frappe version, DB, Raven, ERPNext, bench/Friday command strategy.
- `45-fork-policy.md` — core divergence rules and upstream update discipline.

---

## 4. Recommended Order of Work

1. Run the technical feasibility spike using doc 44.
2. Record spike decisions in `docs/decisions/spike-results.md`.
3. Update doc 42 if the spike changes Raven, ERPNext, database, or fork assumptions.
4. Audit public security claims.
5. Update downstream docs (`14`, `16`, `19`, `24`, `26`, `30`, `34`, `35`) if the spike or authority contract changes them.
6. Only then start implementation.

---

## 5. Current Architectural Take

Friday should be understood as:

> A Frappe-derived framework for governed AI agents, with a control-room product surface and ERPNext operations as the first flagship use case.

This framing preserves the ambition while giving implementation a sane starting point.
