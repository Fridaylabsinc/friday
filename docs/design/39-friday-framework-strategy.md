# 39 — Friday Framework Strategy

> **Purpose:** Clarify the architectural direction after the initial dossier: Friday is not merely a Frappe app. Friday is a Frappe-derived agentic framework that uses Frappe's source and primitives as its starting substrate, then reshapes the developer and operator experience around governed AI agents.

---

## 1. Decision

Friday should feel like a framework from day one.

The project may begin from Frappe Framework source code, but the product identity is Friday:

- The CLI should be Friday-facing for agentic workflows, while respecting that Frappe already has `bench` as the mature operational CLI.
- The default workspace should be a Friday Control Room, not a generic Frappe Desk.
- Agent Profile, Skill, Execution Log, Permission Decision, Sandbox Execution, and Workflow Request should be treated as native platform primitives.
- Frappe remains the technical substrate: DocTypes, permissions, ORM, scheduler, workers, auth, files, realtime, and workflows.

This is a deliberate framework strategy, not a casual fork.

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

Friday may diverge from upstream Frappe where needed for framework identity and agent-native behavior, but divergence must be intentional.

Core modifications are allowed when they:

- make agents first-class actors in permission, audit, workflow, or job execution;
- provide framework-level hooks that apps cannot safely add;
- improve the Friday control-room experience at the platform shell level;
- simplify the developer/operator experience with Friday-facing commands where they add meaning beyond raw `bench`.

Core modifications should be avoided when the behavior can live cleanly in a Friday app/module.

Examples that belong in core:

- actor context propagation across requests, jobs, and workflows;
- trace IDs linking gateway event -> job -> sandbox -> audit row;
- framework-level audit hooks;
- bench command wrappers, aliases, or extensions that make Friday workflows coherent without hiding Frappe's operational model.

Examples that belong in apps/modules:

- ERPNext Purchase Order automation;
- Raven War Room integration;
- pgvector memory and knowledge graph;
- auto-research;
- analytical agents;
- multi-site ACP;
- industry-specific templates.

---

## 5. Upstream Relationship

Friday should treat Frappe as an upstream source of proven engineering, not as a product boundary.

The project should periodically review upstream Frappe releases and selectively merge or reimplement improvements that affect:

- security;
- permissions;
- DocType engine;
- workflow;
- scheduler/workers;
- Desk/Workspace shell;
- database support;
- realtime;
- performance.

Friday does not need to remain a drop-in-compatible Frappe distribution if that blocks the framework vision. However, every divergence should be documented with rationale so future engineers know whether to keep, revise, or remove it.

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
2. Which upstream Frappe version is the initial substrate: v15 for ecosystem stability or v16 for longer support and newer architecture?
3. What is the minimum core patch set needed to make agents first-class without scattering Friday logic across the framework?
4. What compatibility promise does Friday make to existing Frappe apps?
5. Should the public name be "Friday Framework" while the hosted product remains "FridayLabs"?

---

## 9. Summary

Friday is a Frappe-derived agentic framework.

Frappe supplies the proven enterprise substrate. Hermes and OpenClaw supply agentic runtime patterns. Friday's job is to fuse them into a coherent framework where agents are governed business actors, not loose scripts with chat attached.
