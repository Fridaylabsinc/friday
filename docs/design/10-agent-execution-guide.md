# Agentic Workflow — 03 Execution Guide

> **Purpose:** Step-by-step implementation order for Phase One. The agent follows this guide after the Setup and Evaluation phases are complete.

This guide deliberately interleaves building, testing, and review. The agent **does not** build Phase One in one giant pass and ask for review at the end. It builds in vertical slices, each slice deliverable and reviewable on its own.

---

## 1. Working Method

For **every** step below, the agent follows the same micro-loop:

1. **Read** the relevant Friday spec sections and the `hermes-audit.md` entry.
2. **Plan** the change — list files to create or modify, tests to write.
3. **Implement** the smallest functional unit.
4. **Write tests** alongside (not after) implementation.
5. **Run tests + pre-commit + bench migrate**.
6. **Commit** with a conventional commit message (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`).
7. **Report** progress using the format in the Setup Guide §6.
8. **Wait for human acknowledgement** before moving to the next slice, unless explicitly told to chain.

This rhythm keeps reviewability high and prevents large untested deltas.

---

## 2. Implementation Order (Vertical Slices)

Each slice corresponds roughly to a week in `06-phase-one-scope.md`. Slices build on each other; do not start a slice until the previous one is reviewed and merged.

### Slice 1 — Foundations & DocType Skeletons

**Goal:** App scaffolded, DocTypes exist as empty rows you can create manually in the Desk.

**Tasks:**

1. Verify Setup Guide §7 checklist is fully green.
2. Create the module folders inside `friday/`: `gateway`, `agents`, `skills`, `tasks`, `messaging`, `permissions`. Each gets an `__init__.py`.
3. Register modules in `friday/modules.txt`.
4. Create the following DocTypes via `bench`:
   - `Agent Profile` (in module `Agents`)
   - `Skill` (in module `Skills`)
   - `Agent Task` (in module `Tasks`)
   - `Agent Project` (in module `Tasks`)
   - `Chat Message` (in module `Messaging`)
   - `Chat Platform` (in module `Messaging`)
   - `Execution Log` (in module `Agents`, **submittable**)
   - `Permission Decision Log` (in module `Permissions`, **submittable**)
5. Define field schemas exactly as specified in `05-module-design.md` §"Core DocTypes (Phase 1)".
6. Add controllers (`{doctype}.py`) with empty class bodies — to be filled later.
7. Run `bench --site friday.localhost migrate`.
8. Verify each DocType is creatable from the Frappe Desk UI.

**Deliverable:** A migration produces all eight DocTypes; you can create one row of each in the Desk by hand.

**Tests:** A single `test_doctypes_exist.py` that opens each DocType meta and asserts required fields exist.

---

### Slice 2 — Permission Engine

**Goal:** Given an Agent Profile and a Skill, a function returns `(allowed: bool, reason: str)` and logs a `Permission Decision Log` row.

**Tasks:**

1. Implement `friday/permissions/matrix.py`:
   - `build_matrix(agent_profile_name: str) -> PermissionMatrix`
   - `check(matrix, skill_name: str) -> Decision`
2. Implement `friday/permissions/cache.py`:
   - Redis cache keyed by `friday:perm_matrix:{profile_name}`, TTL 60s.
   - Invalidation hook on Agent Profile or Role updates.
3. Implement `friday/permissions/decisions.py`:
   - Persist decision to `Permission Decision Log` (submittable).
4. Register cache invalidation hooks in `hooks.py`:
   ```python
   doc_events = {
       "Agent Profile": {"on_update": "friday.permissions.cache.invalidate_for_profile"},
       "Role": {"on_update": "friday.permissions.cache.invalidate_all"},
   }
   ```
5. Tests:
   - Allow case: profile with matching role permitted on DocType referenced by Skill.
   - Deny case: profile lacks required role.
   - Status check: skill in `Draft`/`Retired` always denied.
   - Cache hit vs miss.
   - **Coverage target: 80% lines, 100% branches on `matrix.py`.**

**Deliverable:** `bench execute friday.permissions.matrix.check --args "['profile_a', 'create_note']"` returns a structured decision and logs it.

---

### Slice 3 — Skill Loader

**Goal:** Active Skills for a given profile are loaded into Redis and convertible to LLM tool definitions.

**Tasks:**

1. Implement `friday/skills/loader.py`:
   - `load_for_profile(profile_name) -> list[SkillDefinition]`
   - Filters Skills by status = "Active" and profile permission.
   - Caches in Redis at `friday:skills:{profile_name}` with TTL 300s.
2. Implement `to_tool_definition(skill) -> dict` — converts a Skill DocType row into OpenAPI-style tool schema.
3. Register invalidation hooks on Skill updates.
4. Tests:
   - Loader returns only Active, permitted skills.
   - Cache returns identical output on repeat call.
   - Status change invalidates cache.

**Deliverable:** Calling the loader from `bench console` returns a list of tool definitions ready to pass to an LLM.

---

### Slice 4 — Gateway: CLI Adapter + Chat Message Flow

**Goal:** A CLI command writes a Chat Message; the gateway sees it via real-time event; it writes back an outbound message.

**Tasks:**

1. Implement `friday/messaging/adapters/cli.py`:
   - `friday chat --profile <name>` opens a REPL-style prompt.
   - Each input writes a Chat Message (direction=inbound) to Frappe via REST.
   - Polls / subscribes for outbound Chat Messages on the same session.
2. Implement `friday/gateway/session_manager.py`:
   - Subscribe to Frappe real-time event `chat_message.after_insert`.
   - On event: resolve Agent Profile, hand off to (stubbed) agent runner.
3. The agent runner in this slice is a **stub** — it just writes a Chat Message with content `"echo: <inbound content>"` to verify the round trip.
4. Tests:
   - Inbound message creates a row.
   - Outbound message appears in CLI.
   - Round-trip latency < 1s on local dev.

**Deliverable:** A user can run `friday chat`, type a message, see the echo reply.

---

### Slice 5 — LLM Integration (Single Provider)

**Goal:** Replace the echo stub with a real LLM call. No tool calling yet — just chat.

**Tasks:**

1. Implement `friday/gateway/prompt_builder.py`:
   - Assembles system prompt from `Agent Profile.system_prompt` + recent session history.
2. Implement `friday/agents/runner.py` first iteration:
   - Calls the chosen LLM provider directly (no LiteLLM).
   - Returns the model's reply as a Chat Message.
3. Provider API key stored as a Frappe `Password` field on Agent Profile or in `Agent Settings` (singleton DocType).
4. Tests:
   - Mock the provider API.
   - Verify prompt assembly is deterministic given the same inputs.
   - Verify reply Chat Message has correct `agent_profile` and `direction=outbound`.

**Deliverable:** `friday chat` produces a real LLM reply, not an echo.

---

### Slice 6 — First Real Skill: `create_note`

**Goal:** End-to-end skill execution with full permission validation. The agent receives a message, the LLM emits a tool call, the gateway validates permission, executes the skill, persists the result, and replies.

**Tasks:**

1. Create a `Note` DocType (or use Frappe's built-in `Note` if present) as the target of the skill.
2. Create a `Skill` row named `create_note` with:
   - `parameters_schema`: title, content.
   - `required_doctypes`: Note (create).
   - `risk_level`: low.
   - `status`: Active.
3. Create an Agent Profile (`note_taker`) with a role that grants Note create permission.
4. Extend `friday/agents/runner.py` to:
   - Include tool definitions in the LLM call.
   - When the LLM emits a tool call: route to `friday/agents/dispatcher.py`.
5. Implement `friday/agents/dispatcher.py`:
   - Call permission engine.
   - On deny: write rejection result to Execution Log, reply with error.
   - On allow: execute skill (Slice 7 will move this into Docker; for now in-process is acceptable for this slice **only**).
6. Persist every execution to `Execution Log` (submitted on completion).
7. Tests:
   - Allowed profile creates a Note successfully.
   - Denied profile gets a clear rejection with no Note created.
   - Execution Log has one submitted row per attempt.

**Deliverable:** `friday chat --profile note_taker` then "make a note titled X about Y" — Note is created, reply confirms.

---

### Slice 7 — Docker Sandboxing for Skill Execution

**Goal:** Move skill execution from in-process to a Docker container with resource caps.

**Tasks:**

1. Build a minimal Friday-worker Docker image: Python 3.11, no host mounts, pinned dependencies.
2. Implement `friday/agents/isolation.py`:
   - `spawn_worker(profile, skill, params) -> result`
   - Uses Docker SDK for Python.
   - Sets CPU + memory caps via `host_config`.
   - Network: bridge mode with allowlist of Frappe API host only.
   - Passes a short-lived API token to the container as an env var.
3. Container entrypoint:
   - Authenticates back to Frappe REST API.
   - Performs the skill action via API call.
   - Exits with structured JSON result.
4. Gateway captures stdout JSON, writes Execution Log, replies to user.
5. Tests:
   - Container spawn + teardown integration test.
   - Resource caps actually enforced (exceed memory → container killed → graceful failure recorded).
   - Network isolation: container cannot reach an external host not in allowlist (test with a deliberate attempt).

**Deliverable:** Slice 6 still works end-to-end, but the skill now runs inside Docker.

---

### Slice 8 — Agent Task + Dispatcher + Native Kanban

**Goal:** Tasks can be created manually, the dispatcher claims them, an agent executes them.

**Tasks:**

1. Define a Frappe Workflow on Agent Task:
   - States: Pending, Assigned, Executing, Blocked, Review, Completed, Cancelled.
   - Transitions with role-based permissions (any agent supervisor can move Blocked → Review).
2. Implement `friday/tasks/workflow.py` hook on Task `on_update` for state transitions.
3. Implement `friday/tasks/dispatcher.py`:
   - Scheduled job every 60 seconds via `hooks.py`.
   - Query tasks in dispatchable workflow states without assigned profile.
   - Match required skills against available profiles.
   - Atomic claim: `update Agent Task set assigned_to_profile = ?, workflow_state = ? where name = ? and assigned_to_profile is null` (use `frappe.db.sql` with `FOR UPDATE SKIP LOCKED` for safety).
4. On task assigned → emit real-time event → agent runner picks up.
5. Enable native Kanban view on Agent Task grouped by `workflow_state`.
6. Tests:
   - Two dispatcher invocations cannot double-claim the same task (concurrency test).
   - Task moves through states correctly.
   - Kanban view loads in the Desk with cards in correct columns.

**Deliverable:** Create a Task in the Desk, watch it move across the Kanban board as the dispatcher and agent process it.

---

### Slice 9 — Polish & Hardening

**Goal:** Phase 1 quality bar.

**Tasks:**

1. Audit and complete unit + integration test coverage to the targets in Setup Guide §3.5.
2. Add logging via Frappe's logger; ensure every permission decision, execution, and dispatcher action is logged.
3. Write `docs/install.md`, `docs/quickstart.md`, `docs/architecture.md` (the latter linking to the seven specs).
4. Add `make` targets (or `nox`) for: `setup`, `test`, `lint`, `migrate`, `run-gateway`.
5. Sanity-check the LICENSE, README, NOTICE, SECURITY.md.
6. Run a one-week dogfood: use Friday to track Friday's own remaining Phase 1 work.

**Deliverable:** Public-ready repo state. Open-source launch can proceed (Phase 2 entry).

---

## 3. Cross-Slice Rules

### 3.1 No Skipping Permission Checks
Every code path that invokes a skill must go through `friday.permissions.matrix.check`. The agent must add a test for the "denied" case for every new skill it introduces.

### 3.2 No Direct Database Writes Bypassing Frappe
Use `frappe.get_doc(...).insert()` / `.save()` / `.submit()`. Raw SQL is reserved for read-only analytics or pgvector queries — never for state changes.

### 3.3 No Hard-Coded Paths
No `~/.hermes`, no `/tmp/whatever`, no hard-coded site names. Use `frappe.local.site`, `frappe.get_site_path()`, `tempfile`.

### 3.4 No Silent Failures
Any caught exception either: (a) recovers cleanly and logs at WARNING+, or (b) is re-raised. Never silently `pass`.

### 3.5 No Breaking the Migration Path
Every DocType change includes a migration patch in `friday/patches.txt`. The agent must be able to `bench migrate` from an empty site to current state without manual intervention.

### 3.6 Conventional Commits
- `feat(permissions): add role-based matrix builder`
- `fix(gateway): handle missing session id gracefully`
- `test(skills): cover Skill loader cache invalidation`
- `docs(install): add PostgreSQL extension setup`
- `refactor(agents): extract runner provider interface`

### 3.7 PR Size
Each slice maps to one or two PRs. PRs > 800 lines diff get broken up.

---

## 4. When the Agent Is Stuck

If after one full micro-loop the agent cannot proceed (ambiguous spec, missing information, contradiction with Hermes that hasn't been resolved), it stops and produces a **blocker report**:

```
## Blocker

### Context
[what slice, what task]

### What I tried
[approaches attempted, why they failed]

### Conflict
[which spec sections or Hermes patterns conflict]

### Options
[concrete proposals A / B / C with tradeoffs]

### Recommendation
[the agent's preferred option, with reasoning]

### Decision needed by
[immediate / by next slice]
```

The agent waits for a human decision before proceeding. It does **not** silently pick an option to keep moving.

---

## 5. Exit Criteria for Phase One

When all nine slices are complete:

- All "Definition of MVP Complete" checkboxes in `06-phase-one-scope.md` are green.
- All tests pass on a fresh `bench install-app friday`.
- A dogfood week has produced no critical issues.
- Documentation is complete enough that a new developer can install and run Friday from the README alone.

At that point, hand control back to the human for the open-source launch decision (Phase 2 entry).
