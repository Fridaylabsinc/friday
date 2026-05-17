# 39 — Friday Framework Strategy

> **Purpose:** Clarify the architectural direction: Friday is a framework. Under the hood it runs on a hard fork of Frappe v16 stable, retaining the full bench ecosystem while building agent-native primitives directly into core.

---

## 1. Decision

Friday is a framework. It runs on a hard fork of Frappe v16 stable.

This is not conditional on a spike outcome. The Friday repository **is** a fork of Frappe v16 stable. Agent-native primitives are built into framework core. The full Frappe bench ecosystem is retained — `bench init`, `bench new-site`, apps, migrations, site operations — because it is excellent operational infrastructure.

The product identity is Friday:

- The CLI is Friday-facing for agentic workflows; `bench` remains available and documented for site/framework operations.
- The default workspace is the Friday Control Room, not generic Frappe Desk.
- Agent Profile, Skill, Execution Log, Permission Decision, Sandbox Execution, and Workflow Request are native framework primitives — built into core, not installed as a removable app.
- Frappe provides the engine: DocTypes, ORM, permissions, workflows, scheduler, workers, auth, files, realtime.

Users and developers interact with Friday. Frappe is the engine.

---

## 2. Why Frappe Source Is the Right Substrate

Hermes Agent and OpenClaw prove useful agentic runtime patterns: gateway, session loop, skills, memory, tool execution, scheduling, and multi-platform interaction. But they store much of the agent's world as files, config, local session logs, and runtime services.

Frappe already provides the enterprise application substrate those systems would otherwise need to build:

| Agentic Need | Frappe Primitive |
|---|---|
| Structured agent state | DocTypes |
| Human and agent identity | User + Role |
| Runtime permissions | Role permission matrix |
| Durable audit records | Submittable DocTypes |
| Approval flows | Workflow |
| Background execution | RQ workers |
| Scheduled autonomy | Scheduler |
| Realtime events | Redis pubsub + socket.io |
| Files and artifacts | File DocType |
| Operator UI | Desk / Workspace |
| Operational CLI | `bench` for site/app operations; `friday` wrapper or commands for agent workflows |

The Friday insight is to move agent architecture from "developer-tool state" into "enterprise-record state."

---

## 3. Framework Shape

Friday should be organized into three layers:

1. **Friday Framework Core**
   - Frappe-derived runtime, bench/site/app lifecycle, Desk shell, auth, DocTypes, permissions, workflows, jobs, files, realtime, and Friday-facing agent commands.

2. **Friday Agent Kernel**
   - Agent-native primitives: Agent Profile, Agent Role Profile, Skill, Skill Version, Execution Log, Permission Decision Log, Workflow Request, Sandbox Execution, LLM Provider, Gateway, Dispatcher.

3. **Friday Apps**
   - Domain products built on the kernel: ERPNext operations, Raven bridge, memory/wiki, analytics, specialist agents, auto-research, multi-site communication.

The user experiences one framework. Internally, boundaries remain strict so Friday does not become an unmaintainable monolith.

---

## 4. Fork Discipline

Friday develops directly on the Frappe v16 fork. Core modifications are made freely wherever agent-native behavior requires it — no "earn the right" gating.

The line is not "can an app do this?" The line is **framework vs domain**:

**Core (modify freely):**
- Agent identity as a first-class actor across requests, jobs, and workflows
- Trace ID propagation from gateway → execution → audit
- Framework-level audit hooks for Permission Decision Log and Execution Log
- Agent-scoped API key authentication baked into the auth layer
- Friday shell: control-room workspace, CLI entrypoint, navigation

**Friday apps (never in core):**
- ERPNext Purchase Order automation
- Raven War Room integration
- pgvector memory and knowledge graph
- Auto-research agents
- Analytical and predictive agents
- Multi-site ACP
- Industry-specific skill templates

Every core modification is documented in `docs/core-divergences.md`, tagged `[friday-core]` in git, and covered by a test. See `45-fork-policy.md` for the full discipline.

---

## 5. Upstream Relationship

Friday treats upstream Frappe as a source of proven engineering to cherry-pick from, not a release train to track.

Upstream patches are absorbed **manually**:

- **Security releases** — reviewed within 48 hours; cherry-picked into `friday/main` if Friday is affected.
- **Bug fixes** — cherry-picked when Friday hits the same bug.
- **Improvements** — reviewed quarterly; incorporated if they benefit Friday's substrate without conflicting with agent-native architecture.
- **Major releases** (v17+) — project-level decision: plan migration, stay, or skip.

There is no automatic sync. The Frappe bench ecosystem core moves slowly. Most upstream Frappe activity is in ERPNext and community apps, which Friday does not track.

Every divergence is documented in `docs/core-divergences.md` so future engineers know what Friday changed and why.

---

## 6. Product Feel Requirements

From first install, Friday should feel like Friday:

- `bench` remains available and documented for framework/site operations.
- `friday` CLI entrypoint or bench plugin commands exist for agent-specific workflows (`friday chat`, `friday agent`, `friday skill`, etc.).
- The first workspace is "Friday Control Room."
- Default modules are Agents, Skills, Tasks, Control Room, Logs, Settings.
- New projects are agentic by default: they have tasks, agents, permissions, and audit.
- Operators see what agents can do, what they are doing, what they did, and how to stop them.
- Developers build "Friday apps" using Frappe-derived primitives.

The control room is the product surface. The agent runtime is the engine.

---

## 7. Phase-One Implication

Phase 1 should establish the framework shell and one governed execution path:

1. Friday-derived repo, bench-aware operational setup, and Friday-facing agent command identity.
2. Friday Control Room workspace.
3. Core agent DocTypes.
4. Permission-gated Skill execution.
5. Execution and Permission Decision logs.
6. Sandboxed execution path.
7. One simple end-to-end skill proving the loop.

ERPNext autonomous operations remains the north-star use case, but the first engineering milestone is the governed framework loop.

---

## 8. Open Questions

1. Which workflows deserve `friday` commands versus remaining plain `bench` commands?
2. ~~Which upstream Frappe version is the initial substrate?~~ **Decided: Frappe v16 stable.**
3. What is the minimum core patch set needed to make agents first-class without scattering Friday logic across the framework?
4. What compatibility promise does Friday make to existing Frappe apps?
5. Should the public name be "Friday Framework" while the hosted product remains "FridayLabs"?

---

## 9. Summary

Friday is an agentic framework. Under the hood it runs on a hard fork of Frappe v16 stable, retaining the full bench ecosystem. Agent-native primitives — actor context, execution trace, governed skill dispatch, sandbox execution — are built directly into framework core. Frappe supplies the proven enterprise substrate. Friday adds the governed-agent layer the enterprise ecosystem doesn't yet have.
