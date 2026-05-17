# 06 — Phase One Scope (MVP)

## Strategy Recap

| Phase | Duration | Goal | Visibility |
|---|---|---|---|
| **1 — Foundation** | 2–3 months | Working prototype, single-platform | Private |
| **2 — Open Source Launch** | Months 3–6 | Public repo, contribution-ready, multi-platform | Public on GitHub |
| **3 — Community Iteration** | Months 6–12 | Feature parity with Hermes, real users, hardening | Active OSS project |
| **4 — Ecosystem Integration** | Year 2+ | Mature Friday as a Frappe-derived agentic framework and collaborate upstream where useful | Frappe community engagement |

This document focuses on **Phase 1**.

`42-phase-one-authority-contract.md` is the authority for v0.1 scope. Where this document conflicts with doc 42, doc 42 wins.

## Phase 1 Goal

A working Friday framework installation on a single site that demonstrates the core thesis:

> **An LLM-powered agent can receive a message, look up its permitted skills from Frappe, execute one in a sandboxed environment, and write the result back as a Frappe document — with every step audited and permission-checked.**

If that single loop works end-to-end with governance intact, the architecture is proven. Everything else is breadth, not depth.

Phase 1 must also establish the product feel: bench remains the operational CLI, while Friday adds agent-facing commands, a Friday Control Room workspace, and agent-native primitives. It should not feel like a generic Frappe site with an AI app bolted on.

## In Scope (MVP)

### Infrastructure
- Frappe bench + Frappe Framework v15 with PostgreSQL backend
- pgvector extension installed
- Redis configured
- Docker installed on host with the minimum sandbox bar from doc 42
- A single Frappe site dedicated to Friday

### Friday Framework Shell
- Friday repository forked from Frappe v16 stable, with Friday-facing README, LICENSE, and CONTRIBUTING.md
- Friday-facing agent commands (`friday` entrypoint or bench command group); `bench` retained for site/framework operations
- Friday Control Room workspace as the default operator surface
- Agent Kernel modules created: `gateway`, `agents`, `skills`, `tasks`, `messaging`, `permissions`
- Agent-native primitives built into framework core; every divergence documented in `docs/core-divergences.md`

### DocTypes (minimum viable set)
1. **Agent Profile** — name, assigned_roles, model_provider, model_name, system_prompt, status
2. **Skill** — name, description, parameters_schema, required_doctypes, required_operations, risk_level, status
3. **Agent Task** — title, project, assigned_to_profile, required_skills, workflow_state, priority
4. **Chat Message** — session_id, platform, direction, sender_id, agent_profile, content, timestamp
5. **Execution Log** — agent_profile, skill, parameters, result, status, permission_decision, duration_ms (submittable)
6. **Permission Decision Log** — agent_profile, requested_resource, decision, reason, timestamp

### Gateway
- Subscribes to Frappe pubsub for new Chat Messages
- Resolves Agent Profile from sender
- Loads cached skill set from Redis (falls back to Frappe on miss)
- Runs the basic agent loop (prompt → LLM → tool call → execute → respond)
- Writes outbound response as a Chat Message

### Permission Engine
- Reads Agent Profile assigned roles
- Builds permission matrix in memory
- Pre-checks every skill invocation against required DocTypes / operations
- Logs every decision to Permission Decision Log
- Rejects with audit trail on denial

### Skill Execution
- Single execution path: in-process for trusted skills, Docker container for untrusted
- Container spawn uses the doc 42 minimum sandbox bar: non-root user, resource limits, timeout/OOM handling, no host or Docker socket mounts, scoped credentials, structured result capture, and cleanup path
- Result written back via Frappe REST API
- Execution Log row submitted on completion

### Messaging
- **One platform adapter only**: CLI adapter (simplest, no external dependencies)
- A CLI command (`friday chat`) writes to Chat Message and polls for responses
- Telegram / Discord / Slack adapters deferred to Phase 2

### Task / Workflow
- Agent Project + Agent Task DocTypes with a basic Workflow:
  `Pending → Assigned → Executing → Completed` (also `Blocked`, `Cancelled`)
- Native Frappe Kanban view on Agent Task, rendering workflow states as columns
- Dispatcher runs as a Frappe scheduled job every minute, claims tasks in dispatchable workflow states

### LLM Integration
- Single provider initially (OpenAI or Anthropic — pick the one with simplest API key flow)
- Provider switchable via Agent Profile field, but only one backend implemented
- Multi-provider fallback deferred to Phase 2

## Out of Scope (Phase 1)

Defer to Phase 2 or later:

- ❌ Multi-platform adapters (Telegram, Discord, Slack, WhatsApp, etc.)
- ❌ Voice transcription / TTS
- ❌ Browser automation
- ❌ Vision / image generation
- ❌ MCP server integration
- ❌ Memory module with pgvector semantic search (use simple FTS for now)
- ❌ User modeling (Honcho-style)
- ❌ Autonomous Curator job
- ❌ Learning loop (Skill Draft generation)
- ❌ Inter-agent communication / sub-agent spawning
- ❌ Tirith command scanning
- ❌ Full production sandbox hardening: warm pool, egress proxy, full attack suite, multi-host orchestration
- ❌ Approval workflows (Phase 1 has the DocType but no UI flow)
- ❌ Batch processing

These are intentionally deferred. Phase 1 must prove the **governance loop**, not feature breadth.

## Milestones

| Week | Milestone | Definition of Done |
|---|---|---|
| 1 | Frappe bench + site provisioned with PostgreSQL + pgvector | `bench start` runs; site reachable; pgvector queries work |
| 2 | Friday framework shell scaffolded; DocTypes 1–4 created | bench setup works; Friday-facing agent command exists; Control Room workspace exists; DocTypes visible in Desk |
| 3 | Permission engine + Execution Log + Permission Decision Log | Programmatic permission check passes/fails with audit |
| 4 | Basic gateway service running; CLI adapter writes Chat Message | Sending a CLI message creates a Chat Message DocType row |
| 5 | LLM call path + simple no-op skill | Gateway picks up message, calls LLM, writes outbound message |
| 6 | First real skill: "create_note" — writes a Note DocType | End-to-end: CLI message → permission check → skill exec → Note created → reply |
| 7 | Docker-isolated execution for `create_note` | Skill runs in container, not in-process |
| 8 | Agent Task workflow + dispatcher | Manually create a Task, dispatcher assigns it, agent executes it |
| 9 | Native Kanban view + real-time updates | Kanban board shows task moving through states live |
| 10 | Polish, tests, documentation pass | README, install guide, architecture doc, 80%+ coverage on permission engine |
| 11 | Internal demo + dogfood | Use Friday to manage Friday's own task list for a week |
| 12 | Open-source launch prep | Public repo ready: LICENSE, CONTRIBUTING, SECURITY, CODE_OF_CONDUCT, docs site stub |

## Definition of "MVP Complete"

All of the following must be true:

- [ ] A user can send a message via CLI.
- [ ] bench remains available for site/app operations.
- [ ] Agent workflows are exposed through a Friday-facing command or bench command group.
- [ ] A Friday Control Room workspace exists as the default operator surface.
- [ ] The Gateway picks it up via Frappe real-time pubsub.
- [ ] The correct Agent Profile is resolved.
- [ ] Skills are loaded and cached from Frappe DocTypes.
- [ ] The LLM is called with a structured prompt and tool definitions.
- [ ] Tool calls are pre-checked against the agent's role permissions.
- [ ] Denied tool calls are logged to Permission Decision Log and rejected with a clear error.
- [ ] Permitted tool calls execute inside a Docker container.
- [ ] Results are written back to Frappe via REST API.
- [ ] An Execution Log row is submitted (immutable) with full audit data.
- [ ] The agent's reply is delivered back to the CLI as a Chat Message.
- [ ] An Agent Task can be created, claimed by the dispatcher from a dispatchable workflow state, executed, and completed — all visible in list/report/Kanban views.

If those checkboxes are green, Phase 1 is done.

## What Phase 1 Validates

By the end of Phase 1, you should be able to answer **yes** to:

1. Does Frappe's permission system work for agent governance at runtime speeds?
2. Is the gateway latency acceptable (<200ms permission check + dispatch)?
3. Does Docker isolation actually work without breaking the agent loop?
4. Is the developer experience of authoring skills as DocTypes pleasant or painful?
5. Do real LLMs handle the structured skill schema well, or do they hallucinate calls?
6. Is the architecture obviously extensible to multi-platform, multi-agent, learning loop?

A "no" on any of these is a signal to redesign **before** open-sourcing.

## Tooling & Dev Setup

- Python 3.11+, Node 18+
- Frappe bench installed locally
- PostgreSQL 15+ with pgvector
- Redis 7+
- Docker
- VS Code or PyCharm with Frappe-aware plugins
- Pre-commit hooks (black, ruff, mypy)
- pytest for tests
- GitHub repo (private during Phase 1, flip to public at Phase 2)

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Frappe permission engine is too slow under agent load | Aggressive Redis caching; benchmark early in week 3 |
| Docker spawn overhead is too high | Pre-warmed container pool; benchmark in week 7 |
| LLM tool-calling is unreliable with our schema | Iterate on schema design; consider structured-output models |
| Frappe app lifecycle clashes with long-running gateway | Run gateway as separate process (not Frappe worker); communicate via REST + pubsub |
| Scope creep | Strict adherence to "out of scope" list; everything else is Phase 2 |
| Fork drift from Frappe engine | Document every core divergence in `docs/core-divergences.md`; tag all core commits `[friday-core]`; domain features stay in Friday apps not core |
