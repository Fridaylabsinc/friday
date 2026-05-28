# 05 — Module Design

> See `00-glossary.md` for term definitions.
> See `45-fork-policy.md` for the one-repo kernel model and `39-friday-framework-strategy.md` for the fork-not-app framing.
> See `14-integrated-architecture.md` for request flow and runtime architecture (this doc covers structure, not flow).
> See `42-phase-one-authority-contract.md` for v0.1 scope.

---

## Layering

| Layer | Owns |
|---|---|
| Friday Framework Core | Frappe v16 fork — runtime, bench/site/app lifecycle, Desk shell, auth, DocTypes, ORM, permissions, workflows, scheduler, RQ, Socket.io, REST API, agent-native core primitives |
| Friday Core (agent kernel) | Agent Profile, Agent Role Profile, Skill, Execution Log, Permission Decision Log, Workflow Request, Gateway, Dispatcher, Sandbox runtime, LLM Provider adapters — built into the framework, not an installable app |
| Friday Apps | ERPNext operations (ported), Raven bridge, memory/wiki, analytics, specialist agents, auto-research, multi-site communication — installable on top |

Friday Core is part of the fork. Removing or disabling it is not supported. Friday Apps are installable and optional.

---

## Module layout

Agent kernel modules live inside the Frappe source tree per `45-fork-policy.md` (one-repo kernel model). Conceptual paths:

```
frappe/friday_core/
├── gateway/                ← session orchestrator, prompt builder, response delivery
│   └── doctype/agent_session, chat_message
├── agents/                 ← profile + execution
│   └── doctype/agent_profile, agent_role_profile, agent_execution
├── skills/                 ← schema, loader, curator, learner
│   └── doctype/skill, skill_draft, skill_version, skill_usage_metric
├── tasks/                  ← agent project / task / dispatcher
│   └── doctype/agent_project, agent_task, task_dependency
├── messaging/              ← platform adapters (CLI Phase 1; Telegram/Discord/Slack/etc. Phase 2)
│   └── doctype/chat_platform, message_attachment
├── approvals/              ← human-in-the-loop
│   └── doctype/workflow_request
├── memory/                 ← long-term store, pgvector retrieval
│   └── doctype/memory_entry, user_model
├── tools/                  ← non-skill capabilities (browser, vision, image gen, MCP)
│   └── doctype/mcp_server, browser_task, vision_task, image_generation_task
├── permissions/            ← gateway permission engine + decision log
│   └── doctype/permission_decision_log
├── sandbox/                ← Docker runner, cgroups, network isolation
└── api/v1/                 ← REST endpoints used by sandbox containers
```

Phase 2 and later modules (browser, vision, image gen, MCP, multi-platform messaging) ship the DocTypes but enter active development per `42-phase-one-authority-contract.md` staging.

---

## Phase 1 DocTypes

### Agent Profile

| Field | Type | Notes |
|---|---|---|
| `profile_name` | Data | Unique |
| `description` | Text | |
| `agent_role_profile` | Link → Agent Role Profile | Governance bundle |
| `assigned_roles` | Table → Role | Resolved from role profile or set explicitly |
| `model_provider` | Link → LLM Provider | Phase 1: Minimax; pluggable via provider adapter interface |
| `model_name` | Data | Specific model identifier |
| `system_prompt` | Long Text | Persona / SOUL |
| `permitted_skills` | Table → Skill | Explicit whitelist; defaults to role profile grant |
| `resource_quota` | Section | CPU, memory, requests-per-hour, tokens, wall-clock |
| `network_allowlist` | Table | External hosts the sandbox may reach |
| `requires_approval_above_risk` | Select | low / medium / high / always |
| `status` | Select | Active / Suspended / Retired |

### Skill

| Field | Type | Notes |
|---|---|---|
| `skill_name` | Data | Unique |
| `description` | Text | Used for L0 matching |
| `when_to_use` | Long Text | L1 disclosure |
| `instructions` | Long Text | L2 disclosure |
| `parameters_schema` | JSON | OpenAPI-compatible |
| `required_doctypes` | Table | Permission inputs |
| `required_operations` | Table | read / write / submit / cancel |
| `risk_level` | Select | low / medium / high / critical |
| `requires_approval` | Check | Auto-creates Workflow Request when set |
| `status` | Select | Active / Draft / Experimental / Retired / Archived |
| `current_version` | Link → Skill Version | Active version pointer (rollback target) |
| `usage_count` | Int | Read-only, updated by hook |
| `last_used` | Datetime | Read-only |
| `created_by_agent` | Link → Agent Profile | Set when learned |

### Agent Task

| Field | Type | Notes |
|---|---|---|
| `title` | Data | |
| `description` | Long Text | |
| `project` | Link → Agent Project | |
| `assigned_to_profile` | Link → Agent Profile | Set by dispatcher |
| `required_skills` | Table → Skill | Dispatcher matching input |
| `workflow_state` | Link → Workflow State | Per Frappe Workflow |
| `dispatchable` | Check | True only when current state is in the dispatchable set |
| `priority` | Select | low / normal / high / urgent |
| `dependencies` | Table → Agent Task | Blocking dependencies |
| `current_execution` | Link → Execution Log | Active run, if any |
| `result` | Long Text / JSON | |
| `started_at`, `completed_at` | Datetime | |

### Chat Message

| Field | Type | Notes |
|---|---|---|
| `session_id` | Link → Agent Session | |
| `platform` | Link → Chat Platform | CLI (Phase 1); Telegram/Discord/Slack/etc. (Phase 2) |
| `direction` | Select | inbound / outbound |
| `sender_id` | Data | Platform-specific |
| `agent_profile` | Link → Agent Profile | Set for outbound |
| `content` | Long Text | |
| `attachments` | Table | |
| `timestamp` | Datetime | |
| `processed` | Check | |

### Execution Log

| Field | Type | Notes |
|---|---|---|
| `agent_profile` | Link | |
| `skill` | Link | |
| `task` | Link → Agent Task | Optional |
| `parameters` | JSON | Masked at the boundary |
| `result` | JSON | |
| `status` | Select | success / failed / rejected / timeout |
| `permission_decision` | Link → Permission Decision Log | |
| `duration_ms` | Int | |
| `tokens_used` | Int | |
| Submittable | Yes | Append-only audit trail |

### Permission Decision Log

| Field | Type | Notes |
|---|---|---|
| `agent_profile` | Link | |
| `skill` | Link | |
| `decision` | Select | allowed / denied |
| `reason` | Text | Free-text explanation from the permission engine |
| `matrix_snapshot` | JSON | Permission matrix at decision time |
| `decided_at` | Datetime | |
| Submittable | Yes | Append-only audit trail |

### Workflow Request

| Field | Type | Notes |
|---|---|---|
| `agent_profile` | Link | |
| `skill` | Link | |
| `parameters` | JSON | |
| `risk_level` | Select | |
| `requested_at` | Datetime | |
| `approved_by` | Link → User | |
| `decision` | Select | approved / rejected / expired |
| `decision_reason` | Text | |

---

## Background jobs

The runtime architecture and request flow are in `14-integrated-architecture.md`. The jobs below are scheduled work that does not appear there.

### Curator (daily)

```
1. Skill where status='Experimental' and created_at < 30 days ago
   - usage_count > threshold and success_rate > 80% → promote to 'Active'
   - else → 'Archived'
2. Skill where status='Active' and last_used < 90 days ago
   → 'Retired'
3. Detect overlapping skills (description embedding similarity)
   → flag for human consolidation
4. Write curator run report as a DocType row
```

### Learner (every 6 hours)

```
1. Successful Execution Logs from the last 6 hours
2. Cluster by similar task patterns (embedding similarity)
3. Per cluster:
   - no Skill covers it → create Skill Draft
   - more efficient pattern emerged → propose Skill Draft edit
4. Notify supervisor role to review Skill Drafts
```

Skill Drafts never activate without supervisor approval.

---

## REST API surface

All endpoints under `/api/method/friday.api.v1.*`. Used by sandbox containers and external integrations. Every endpoint authenticates with a Frappe API key scoped to one Agent Profile and re-runs the permission check server-side.

| Endpoint | Purpose |
|---|---|
| `skills.list` | Paginated, filtered by the calling agent's permissions |
| `skills.invoke` | Execute a skill (synchronous) or queue and return `job_id` |
| `tasks.claim` | Atomic claim of the next dispatchable task for this profile |
| `tasks.update_state` | Workflow state transition |
| `messages.send` | Outbound message — writes a Chat Message row |
| `memory.search` | Semantic search via pgvector |
| `permissions.check` | Explicit permission probe for agent planning |

---

## Hooks wiring (`hooks.py`)

```python
scheduler_events = {
    "hourly": ["friday.skills.curator.tick"],
    "daily":  ["friday.skills.learner.run"],
    "cron":   {"*/1 * * * *": ["friday.tasks.dispatcher.tick"]},
}

doc_events = {
    "Chat Message": {
        "after_insert": "friday.gateway.session_manager.on_new_message",
    },
    "Agent Task": {
        "on_update": "friday.tasks.workflow.on_state_change",
    },
    "Skill": {
        "after_insert": "friday.skills.loader.invalidate_cache",
        "on_update":    "friday.skills.loader.invalidate_cache",
    },
}
```

The dispatcher fires every 60 seconds. The curator runs hourly (with daily promotion/retirement logic). The learner runs every six hours.

---

## What this module list is not

- It is not a runtime architecture diagram — see `14`.
- It is not an end-to-end request flow — see `14` §request flow.
- It is not a port-plan — see `41-porting-strategy-hermes-erpnext-raven.md`.
- It is not v0.1 scope — see `42-phase-one-authority-contract.md`.

This document defines what modules exist and what DocTypes they own. Everything else has a canonical home.
