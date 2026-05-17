# 05 — Module Design

## Build Strategy

Friday is a framework built on a **hard fork of Frappe v16 stable**. The Friday repository starts from Frappe v16 and develops agent-native primitives directly in core. The full bench ecosystem is retained. Domain capabilities live in Friday apps.

The strategy is:

- Fork Frappe v16 stable as the starting point. Friday develops on that fork.
- Build agent-native primitives (actor context, trace, audit hooks, sandboxed execution) directly into framework core — not as bolt-on apps.
- Keep domain capabilities (ERPNext operations, Raven, memory, analytics) as Friday apps so core stays focused.
- Manually absorb upstream Frappe patches when relevant — security releases within 48 hours, other improvements as needed.

See `39-friday-framework-strategy.md` for fork discipline, `41-porting-strategy-hermes-erpnext-raven.md` for the workflow/Kanban translation, and `42-phase-one-authority-contract.md` for v0.1 scope.

## Framework Layers

| Layer | Owns |
|---|---|
| Friday Framework Core | Frappe v16 fork — runtime, bench/site/app lifecycle, Desk shell, auth, DocTypes, permissions, workflows, jobs, files, realtime, agent-native primitives |
| Friday Agent Kernel | Agent Profile, Agent Role Profile, Skill, Execution Log, Permission Decision Log, Workflow Request, Gateway, Dispatcher, Sandbox, LLM Provider |
| Friday Apps | ERPNext operations, Raven bridge, memory/wiki, analytics, specialist agents, auto-research, multi-site communication |

## App Layout

```
friday/                                  ← framework repo root
├── framework/                           ← Frappe v16 fork (Friday develops here; agent-native patches documented in docs/core-divergences.md)
├── friday/
│   ├── __init__.py
│   ├── hooks.py                         ← app-level hooks (events, scheduler, fixtures)
│   ├── modules.txt                      ← list of Friday modules
│   │
│   ├── gateway/                         ← orchestrator
│   │   ├── doctype/
│   │   │   ├── agent_session/
│   │   │   └── chat_message/
│   │   ├── dispatcher.py
│   │   ├── session_manager.py
│   │   ├── permission_check.py
│   │   └── prompt_builder.py
│   │
│   ├── agents/                          ← agent profile + execution
│   │   ├── doctype/
│   │   │   ├── agent_profile/
│   │   │   ├── agent_execution_log/
│   │   │   └── agent_memory/
│   │   ├── runner.py                    ← spawns Docker container
│   │   ├── isolation.py                 ← cgroups, networking, mounts
│   │   └── lifecycle.py
│   │
│   ├── skills/                          ← skill schema + curation
│   │   ├── doctype/
│   │   │   ├── skill/
│   │   │   ├── skill_draft/
│   │   │   └── skill_usage_metric/
│   │   ├── loader.py                    ← caches skills into Redis
│   │   ├── curator.py                   ← autonomous curator job
│   │   └── learner.py                   ← drafts skills from execution logs
│   │
│   ├── tasks/                           ← Kanban / project orchestration
│   │   ├── doctype/
│   │   │   ├── agent_project/
│   │   │   ├── agent_task/
│   │   │   └── task_dependency/
│   │   └── workflow.py                  ← state transitions
│   │
│   ├── messaging/                       ← platform adapters
│   │   ├── doctype/
│   │   │   ├── chat_platform/           ← Telegram, Discord, etc. config
│   │   │   └── message_attachment/
│   │   ├── adapters/
│   │   │   ├── telegram.py
│   │   │   ├── discord.py
│   │   │   ├── slack.py
│   │   │   ├── cli.py
│   │   │   └── email.py
│   │   └── delivery.py
│   │
│   ├── approvals/                       ← human-in-the-loop
│   │   ├── doctype/
│   │   │   └── workflow_request/
│   │   └── router.py
│   │
│   ├── memory/                          ← long-term store + vector search
│   │   ├── doctype/
│   │   │   ├── memory_entry/
│   │   │   └── user_model/
│   │   ├── vector_store.py              ← pgvector interface
│   │   └── retrieval.py
│   │
│   ├── tools/                           ← non-skill capabilities
│   │   ├── doctype/
│   │   │   ├── mcp_server/
│   │   │   ├── browser_task/
│   │   │   ├── vision_task/
│   │   │   └── image_generation_task/
│   │   └── workers/
│   │
│   ├── permissions/                     ← gateway permission engine
│   │   ├── matrix.py
│   │   ├── cache.py
│   │   └── decisions.py
│   │
│   └── api/                             ← REST endpoints for agents
│       ├── v1/
│       │   ├── skills.py
│       │   ├── tasks.py
│       │   ├── messages.py
│       │   └── permissions.py
│       └── auth.py
│
├── setup.py
├── pyproject.toml
├── LICENSE                              ← GPL v3
├── README.md
└── docs/
```

The tree above is conceptual. Implementation may retain Frappe's internal package layout while exposing Friday-facing CLI, docs, workspace defaults, and module names.

## Core DocTypes (Phase 1)

### Agent Profile
| Field | Type | Notes |
|---|---|---|
| `profile_name` | Data | Unique |
| `description` | Text | |
| `assigned_roles` | Table → Role | |
| `model_provider` | Link | OpenAI, Anthropic, OpenRouter, local |
| `model_name` | Data | |
| `system_prompt` | Long Text | Persona / SOUL |
| `permitted_skills` | Table → Skill | Optional explicit whitelist |
| `resource_quota` | Section break with quota fields | |
| `network_allowlist` | Table | |
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
| `required_doctypes` | Table | For permission check |
| `required_operations` | Table | read / write / submit etc. |
| `risk_level` | Select | low / medium / high / critical |
| `requires_approval` | Check | |
| `status` | Select | Active / Draft / Experimental / Retired / Archived |
| `usage_count` | Int | Read-only, updated by hook |
| `last_used` | Datetime | Read-only |
| `created_by_agent` | Link → Agent Profile | If learned |

### Agent Task
| Field | Type | Notes |
|---|---|---|
| `title` | Data | |
| `description` | Long Text | |
| `project` | Link → Agent Project | |
| `assigned_to_profile` | Link → Agent Profile | |
| `required_skills` | Table → Skill | For dispatcher matching |
| `workflow_state` | Link → Workflow State | Configurable; first template may include Pending / Assigned / Executing / Blocked / Review / Completed |
| `dispatchable` | Check / derived | True only when the current workflow state can be claimed by dispatcher |
| `priority` | Select | low / normal / high / urgent |
| `dependencies` | Table → Agent Task | Blocking dependencies |
| `result` | Long Text / JSON | |
| `started_at`, `completed_at` | Datetime | |

### Chat Message
| Field | Type | Notes |
|---|---|---|
| `session_id` | Link → Agent Session | |
| `platform` | Link → Chat Platform | telegram, discord, etc. |
| `direction` | Select | inbound / outbound |
| `sender_id` | Data | Platform-specific |
| `agent_profile` | Link → Agent Profile | For outbound |
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
| `parameters` | JSON | |
| `result` | JSON | |
| `status` | Select | success / failed / rejected / timeout |
| `permission_decision` | Link → Permission Decision Log | |
| `duration_ms` | Int | |
| `tokens_used` | Int | |
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

## Gateway Internals

The gateway is a long-running Python process (a Frappe background worker variant or standalone service). It:

1. Subscribes to Frappe's Redis pubsub for `chat_message.new` and `agent_task.new` events.
2. On event → resolves session, agent profile, intent.
3. Calls Permission Check module — fail-fast if denied.
4. Routes to Dispatcher if multi-agent task; otherwise spawns single agent runner.
5. Maintains an LRU cache of active `AIAgent` instances per session (TTL ~1 hour, max 128 — Hermes pattern).
6. Streams responses back via platform adapters.

The agent loop itself is inherited conceptually from Hermes' `AIAgent.run_conversation()`:

```
loop:
  prompt = prompt_builder.build(session, profile, skills, memory)
  response = llm.complete(prompt)
  if response.has_tool_call:
    skill = resolve_skill(response.tool_call.name)
    permission_check(profile, skill)              ← gateway gate
    result = execute_in_sandbox(skill, args)      ← Docker
    append_to_session(result)
  else:
    deliver(response.text)
    break
```

## Dispatcher Logic

Given a new task:

```
1. Query Agent Task where workflow_state is dispatchable and assigned_to_profile is null
2. For each task:
   a. Find Agent Profiles where assigned_roles can satisfy task.required_skills
   b. Filter to profiles within resource quota
   c. Rank by load, specialisation, success rate (from Execution Log)
   d. Atomically claim: update task.assigned_to_profile + state = next assigned/running state
3. Emit Frappe notification → agent's gateway listener wakes up
```

## Skill Loading

On gateway startup, or on `Skill` DocType change event:

```
1. Query all Skills where status = 'Active'
2. Filter by current agent profile's permissions
3. Convert each Skill into LLM tool definition:
   - description (L0)
   - parameters_schema (JSON Schema)
   - required permissions metadata
4. Cache in Redis: key = f"skills:{profile_id}", TTL 300s
5. Inject into agent's system prompt at run_conversation time
```

## Curator Job (Periodic)

Runs every 24 hours via Frappe Scheduler:

```
1. Query Skill where status = 'Experimental' and created_at < 30 days ago
   - If usage_count > threshold and success_rate > 80% → promote to 'Active'
   - Else → 'Archived'
2. Query Skill where status = 'Active' and last_used < 90 days ago
   - Move to 'Retired'
3. Detect overlapping skills (similar description embeddings)
   - Flag for human consolidation
4. Write curator run report as a DocType row
```

## Learning Loop

Runs every 6 hours:

```
1. Query successful Execution Logs from last 6 hours
2. Cluster by similar task patterns (embedding similarity)
3. For each cluster:
   - If no Skill covers it, draft a Skill Draft DocType
   - If a Skill exists but a more efficient pattern emerged, propose edit
4. Notify supervisor role to review Skill Drafts
```

## REST API Surface (for agents)

All endpoints under `/api/method/friday.api.v1.*`:

- `skills.list` — paginated, filtered by agent's permissions
- `skills.invoke` — execute a skill (or queue + return job_id)
- `tasks.claim` — atomic claim of next task
- `tasks.update_state` — Kanban transition
- `messages.send` — outbound message (writes to Chat Message)
- `memory.search` — semantic search via pgvector
- `permissions.check` — explicit permission probe (for agent planning)

Every endpoint authenticates via Frappe API key + applies role permissions automatically.

## Hooks Configuration (`hooks.py`)

Key wiring points:

```python
# Scheduler
scheduler_events = {
    "hourly": ["friday.skills.curator.tick"],
    "daily": ["friday.skills.learner.run"],
    "cron": {
        "*/1 * * * *": ["friday.tasks.dispatcher.tick"],
    },
}

# DocType hooks
doc_events = {
    "Chat Message": {
        "after_insert": "friday.gateway.session_manager.on_new_message",
    },
    "Agent Task": {
        "on_update": "friday.tasks.workflow.on_state_change",
    },
    "Skill": {
        "after_insert": "friday.skills.loader.invalidate_cache",
        "on_update": "friday.skills.loader.invalidate_cache",
    },
}

# Real-time event allowlist
website_route_rules = []
override_whitelisted_methods = {}
```

## Module Boundaries

Each module is independently usable. A site can install Friday and use only the `messaging` + `agents` + `skills` modules without enabling the `tools` (vision, browser, image gen) module, for example. This matches the plugin-style flexibility Hermes offers but enforces it at the module-import level.
