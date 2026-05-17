# 01 — Vision & Architecture

## Vision

Friday is an open-source agentic framework that runs on a hard fork of Frappe v16 stable, combining:
- **Hermes Agent's agentic capabilities** — agent loop, skills system, learning loop, multi-platform messaging, Kanban orchestration, voice, vision, browser automation, MCP integration.
- **Frappe Framework's enterprise backbone** — role-based permissions, structured DocTypes, workflows, real-time notifications, background workers, audit trails.

The goal: an agentic framework that enterprises can actually deploy because governance is built in, not bolted on. Friday should feel like its own framework from day one, while using Frappe source and primitives as the proven substrate.

## Design Principles

1. **Frappe as the source of truth.** Every agent, skill, task, permission, and execution log is a DocType. No scattered markdown files, no ad-hoc JSON state.
2. **Permission-first.** Every skill invocation passes through Frappe's role-based permission matrix before it ever hits a queue.
3. **Sandboxed execution.** Every agent runs in an isolated Docker container with scoped credentials and resource quotas.
4. **Structured over freeform.** Skills, profiles, and task states are defined by schemas — agents work with structured data, not loose prompts.
5. **Framework-first product feel.** Friday owns the CLI, default workspace, agent primitives, and control-room experience; Frappe remains the substrate, not the product boundary.
6. **Kanban is a view, not the workflow.** Business workflows are defined through Frappe Workflow and task types; Kanban renders those states instead of hardcoding a universal board.
7. **Open-source by default.** Friday is GPL v3 / AGPL v3 from day one, developed in public.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  PLATFORM ADAPTERS                                              │
│  Telegram · Discord · Slack · WhatsApp · CLI · Email · Web      │
└────────────────────────────┬────────────────────────────────────┘
                             │ (incoming messages → Chat Message DocType)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  FRIDAY GATEWAY (orchestrator)                                  │
│  ─ Session management                                           │
│  ─ Dispatcher (matches tasks → agent profiles)                  │
│  ─ Permission validation (against Frappe role matrix)           │
│  ─ Real-time event handling (Frappe pubsub)                     │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
        ┌──────────┐   ┌──────────┐   ┌──────────┐
        │ Agent A  │   │ Agent B  │   │ Agent N  │   ← Docker-isolated
        │ (Docker) │   │ (Docker) │   │ (Docker) │     agent runners
        └────┬─────┘   └────┬─────┘   └────┬─────┘
             │              │              │
             └──────────────┼──────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  FRIDAY FRAMEWORK BACKEND (Frappe v16 fork — agent-native core)  │
│  ─ DocTypes: Agent Profile, Skill, Task, Chat Message, etc.     │
│  ─ Role-based permissions                                       │
│  ─ Workflows (Pending → Assigned → Executing → Review → Done)   │
│  ─ Native Kanban view on Tasks                                  │
│  ─ Background workers (RQ)                                      │
│  ─ Real-time notifications                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
       ┌────────────┐  ┌──────────┐  ┌──────────────┐
       │ PostgreSQL │  │  Redis   │  │   Docker     │
       │ + pgvector │  │ (cache + │  │   runtime    │
       │ (durable + │  │  queues+ │  │ (sandboxing) │
       │  semantic) │  │  pubsub) │  │              │
       └────────────┘  └──────────┘  └──────────────┘
```

## Request Flow (end-to-end)

1. **Inbound message** — a user sends a message via Telegram (or any adapter).
2. **Adapter → Frappe** — the adapter creates a `Chat Message` DocType row.
3. **Notification fires** — Frappe's real-time pubsub wakes the Gateway.
4. **Dispatcher matches** — Gateway loads the user/session, identifies the right Agent Profile based on intent + role permissions.
5. **Skill resolution** — Gateway pulls cached Skill definitions from Redis (falling back to Frappe DocTypes on cache miss).
6. **Permission check** — Gateway verifies the agent's role has access to the requested Skill/DocType. Rejects immediately if not.
7. **Sandboxed execution** — Gateway spawns (or routes to) a Docker container scoped to that Agent Profile. The container only sees the API endpoints and data it is permitted to access.
8. **Skill runs** — Agent invokes Frappe's REST API (or `bench execute` for trusted internal calls) to perform the work.
9. **Result persisted** — Execution Log DocType records inputs, outputs, agent ID, timestamp, success/failure.
10. **Response back** — Agent's reply written as a new Chat Message; adapter delivers it back to the user platform.
11. **Audit trail** — Every step is queryable in Frappe for compliance and debugging.

## Framework Positioning

Friday is a framework. The Friday repository is a hard fork of Frappe v16 stable:

- Frappe supplies the engine: DocTypes, ORM, permissions, users, workflows, scheduler, workers, files, realtime, bench ecosystem, and Desk.
- Friday builds agent-native primitives directly into framework core: agent identity, execution trace, governed skill dispatch, sandboxed execution.
- Friday-native DocTypes (Agent Profile, Skill, Execution Log, Permission Decision Log, Workflow Request, Sandbox Execution) are core framework concepts, not a removable app.
- The control room is the product surface; the agent runtime is the engine.

See `39-friday-framework-strategy.md` for the framework strategy and fork discipline.
See `41-porting-strategy-hermes-erpnext-raven.md` for the Hermes Kanban lessons and the Friday translation.

## Multi-Agent Collaboration

Instead of reimplementing Hermes' fixed Kanban, Friday leverages Frappe's native Project / Task / Workflow / Kanban stack:

- **Project DocType** = an agentic workflow (e.g. "Q4 Customer Onboarding").
- **Task DocType** = a unit of work, linked to an Agent Profile and a Workflow.
- **Workflow states** are fully customisable per project (e.g. `Pending → Assigned → Executing → Blocked → Review → Completed`).
- **Frappe's Kanban view** renders workflow states as columns.
- **Real-time notifications** push state changes to agents and supervisors.

The Dispatcher is a query against validated Frappe records: dispatchable workflow state, complete dependencies, active skills, eligible Agent Profile, permission pass, and quota availability. It does not ask an agent to invent the operating model at runtime.

## Learning Loop

- Successful executions logged to `Execution Log` get analysed by a periodic background job.
- The job extracts patterns and drafts new Skill suggestions as `Skill Draft` DocTypes.
- A human (or supervisor agent) reviews drafts in Frappe's standard UI.
- Approved drafts promote to active `Skill` DocTypes.
- Each Skill carries a `status` field (Active, Draft, Experimental, Retired, Archived) and a usage counter — unused skills auto-archive over time.

## What Makes Friday Different

| Concern | Hermes / OpenClaw | Friday |
|---|---|---|
| Skill storage | Markdown files on disk | Structured DocTypes |
| Permissions | Per-tool config, easy to misconfigure | Frappe role matrix, enforced at gateway |
| Multi-agent board | Custom Kanban + SQLite | Frappe Project/Task/Workflow/Kanban |
| Audit trail | Log files | DocType-level immutable history |
| Isolation | Process-level | Docker + Frappe API boundary |
| Memory | File-based + optional vector | PostgreSQL + pgvector, queryable |
| Real-time | Custom WebSocket | Frappe's built-in pubsub |
| Background jobs | Custom cron + scheduler | Frappe RQ workers |
