# Agentic Workflow — 04 Validation Checklist

> **Purpose:** Concrete, testable criteria the agent (and the human reviewer) use to confirm each Phase One slice is complete and correct.

This document is the **gate** between slices. The agent does not proceed to slice N+1 until every box in slice N is green and human-acknowledged.

---

## How to Use This Checklist

For each slice:

1. The agent implements (per the Execution Guide).
2. The agent self-checks against the boxes below, ticking what's done.
3. The agent reports outcomes in its progress format, with the checklist filled in.
4. The human reviews the checklist, runs spot-check tests, and either acknowledges (slice merged) or sends back for fixes.
5. Only after human acknowledgement does the agent start the next slice.

If a box cannot be ticked, the agent produces a blocker report (Execution Guide §4) — it does not tick the box dishonestly.

---

## Global (Apply Every Slice)

- [ ] All new code has the GPL v3 file header.
- [ ] Any code adapted from Hermes has a "this file adapts logic from..." comment and a `NOTICE` entry.
- [ ] No new lines have hard-coded paths (`~/.hermes`, `/tmp/x`, etc.).
- [ ] No new lines bypass `frappe.permissions` or `friday.permissions.matrix`.
- [ ] No new lines silently swallow exceptions.
- [ ] `pre-commit run --all-files` passes.
- [ ] `bench --site friday.localhost migrate` runs clean on a fresh site.
- [ ] All new tests pass: `bench --site friday.localhost run-tests --app friday`.
- [ ] No secrets, API keys, or tokens are committed (verify with `git secrets` or equivalent).
- [ ] Commit history follows conventional commits.

---

## Slice 1 — Foundations & DocType Skeletons

### Structural
- [ ] `friday/` app exists at the bench level.
- [ ] `friday/modules.txt` lists: Gateway, Agents, Skills, Tasks, Messaging, Permissions.
- [ ] Each module has an `__init__.py` and a `doctype/` subfolder.

### DocTypes Created
- [ ] Agent Profile (Agents module)
- [ ] Skill (Skills module)
- [ ] Agent Task (Tasks module)
- [ ] Agent Project (Tasks module)
- [ ] Chat Message (Messaging module)
- [ ] Chat Platform (Messaging module)
- [ ] Execution Log (Agents module, **is_submittable = 1**)
- [ ] Permission Decision Log (Permissions module, **is_submittable = 1**)

### Schema Conformance
- [ ] Field names match `05-module-design.md` §"Core DocTypes" exactly.
- [ ] Mandatory fields marked `reqd=1`.
- [ ] Link fields point to correct target DocTypes.
- [ ] Submittable DocTypes have submit/cancel permissions configured.

### Verification
- [ ] Each DocType is creatable via the Frappe Desk UI without errors.
- [ ] `test_doctypes_exist.py` passes.

---

## Slice 2 — Permission Engine

### Behaviour
- [ ] `friday.permissions.matrix.check(profile, skill)` returns a structured `Decision` (allowed, reason).
- [ ] Allow case: profile with all required roles is permitted.
- [ ] Deny case: missing role → denied with specific reason.
- [ ] Deny case: skill `status != Active` → denied regardless of permissions.
- [ ] Every call writes one Permission Decision Log row (submitted).

### Caching
- [ ] Permission matrix cached in Redis at `friday:perm_matrix:{profile_name}`.
- [ ] TTL respected (60s default).
- [ ] Agent Profile update invalidates that profile's cache.
- [ ] Role update invalidates all cached matrices.

### Test Coverage
- [ ] Line coverage ≥ 80% on `friday/permissions/matrix.py`.
- [ ] Branch coverage = 100% on `matrix.check()`.
- [ ] At least one test asserts the Permission Decision Log row is submitted (not draft).

### Performance
- [ ] Cold check (no cache): < 50ms on local dev.
- [ ] Warm check (cache hit): < 5ms on local dev.

---

## Slice 3 — Skill Loader

### Behaviour
- [ ] `load_for_profile(name)` returns only Skills where `status = Active`.
- [ ] Returns only Skills the profile has permission to execute.
- [ ] Output is a list of dicts conforming to OpenAPI-style tool schema (name, description, parameters).
- [ ] `to_tool_definition()` produces valid JSON Schema for each Skill.

### Caching
- [ ] Cached in Redis at `friday:skills:{profile_name}` with TTL 300s.
- [ ] Skill `after_insert` / `on_update` / `on_trash` invalidates cache.
- [ ] Cache miss results in DocType query; cache hit does not.

### Tests
- [ ] Active + permitted Skill appears.
- [ ] Active + unpermitted Skill does **not** appear.
- [ ] Draft / Retired / Archived / Experimental Skills do **not** appear.
- [ ] Cache invalidation test passes.

---

## Slice 4 — Gateway + CLI Adapter

### CLI
- [ ] `friday chat --profile <name>` opens an interactive prompt.
- [ ] Each user line creates a Chat Message (direction=inbound, content set, session_id set).
- [ ] The CLI prints any outbound Chat Message on the same session.

### Gateway
- [ ] Gateway subscribes to Frappe real-time `chat_message.after_insert`.
- [ ] On inbound event, gateway resolves the Agent Profile (no error on first message).
- [ ] Stub runner emits an outbound Chat Message containing `"echo: <inbound content>"`.

### Round Trip
- [ ] User types "hello" → sees "echo: hello".
- [ ] Round-trip latency < 1000ms on local dev (excluding LLM, which is not in this slice).
- [ ] Both messages persisted in Chat Message DocType (verifiable in Desk).

### Tests
- [ ] Integration test simulates an inbound message and asserts an outbound reply within 2s.

---

## Slice 5 — LLM Integration

### Configuration
- [ ] LLM API key stored as a Frappe `Password` field (encrypted at rest), not in `.env` committed to the repo.
- [ ] Provider and model selectable per Agent Profile.

### Prompt Assembly
- [ ] System prompt includes the Agent Profile's `system_prompt` field.
- [ ] System prompt includes the last N session messages (configurable).
- [ ] Prompt is deterministic given identical inputs (golden-file test).

### Reply Flow
- [ ] LLM reply written as Chat Message (direction=outbound, agent_profile set, session_id preserved).
- [ ] Stub echo is fully removed.
- [ ] Error handling: provider 429 / 5xx → graceful retry with backoff (max 3); final failure → error message to user.

### Tests
- [ ] Mocked provider returns a canned reply → reply Chat Message exists.
- [ ] Mocked 429 → retried → success.
- [ ] Mocked 5xx persistent → error Chat Message emitted, not silent failure.

---

## Slice 6 — First Skill `create_note`

### Setup
- [ ] Skill row `create_note` exists with correct schema, `required_doctypes = [Note]`, `risk_level = low`, `status = Active`.
- [ ] Agent Profile `note_taker` exists with a role that permits Note creation.

### Permitted Flow
- [ ] User asks the note_taker profile to create a note.
- [ ] LLM emits a tool call.
- [ ] Permission engine returns allowed.
- [ ] Skill executes (in-process for this slice — acceptable).
- [ ] A Note DocType row is created with correct title and content.
- [ ] Execution Log row submitted with status `success`, result populated, duration_ms set, tokens_used set.
- [ ] User receives a confirmation message.

### Denied Flow
- [ ] An Agent Profile without Note-create permission attempts the same.
- [ ] Permission engine returns denied with specific reason.
- [ ] No Note row is created.
- [ ] Execution Log row submitted with status `rejected`, linked to a Permission Decision Log row.
- [ ] User receives a clear denial message.

### Tests
- [ ] Allowed flow integration test.
- [ ] Denied flow integration test.
- [ ] Both flows produce exactly one Execution Log row each.

---

## Slice 7 — Docker Sandboxing

### Image
- [ ] Friday-worker Docker image builds cleanly.
- [ ] Image has Python 3.11, pinned dependencies, no host mounts in the Dockerfile.
- [ ] Image entrypoint reads a single JSON command from stdin/env, returns JSON on stdout.

### Spawn / Teardown
- [ ] `friday.agents.isolation.spawn_worker(profile, skill, params)` returns a structured result.
- [ ] Container is destroyed after execution (`docker ps -a` shows no leftover containers after 10 consecutive runs).
- [ ] CPU cap enforced (verify by spinning a busy loop and observing throttle).
- [ ] Memory cap enforced (verify a `[0]*N` allocation beyond limit → container killed → graceful failure).

### Network Isolation
- [ ] Container can reach Frappe REST API endpoint.
- [ ] Container **cannot** reach an arbitrary external host (test with `curl https://example.com` — expect failure).
- [ ] Allowlist is configurable per Agent Profile.

### Credentials
- [ ] Container receives a short-lived API token, not a long-lived one.
- [ ] Token scope is limited to the Agent Profile's permissions (server-side re-check).
- [ ] No host credentials, no `.aws/`, no SSH keys, no host `/etc/passwd` visible.

### End-to-End
- [ ] Slice 6's `create_note` flow still works, but now inside Docker.

### Tests
- [ ] Spawn + teardown integration test.
- [ ] Resource cap enforcement test (memory).
- [ ] Network allowlist test (deny case).

---

## Slice 8 — Tasks, Dispatcher, Kanban

### Workflow
- [ ] Frappe Workflow on Agent Task with states: Pending, Assigned, Executing, Blocked, Review, Completed, Cancelled.
- [ ] Transitions configured with role-based permissions.

### Dispatcher
- [ ] Runs every 60s via `hooks.py` scheduler.
- [ ] Queries Pending, unassigned Tasks.
- [ ] Matches Tasks to Agent Profiles based on `required_skills` ⊆ profile's permitted skills.
- [ ] Atomic claim — concurrent dispatcher invocations cannot double-claim (proven by test).
- [ ] Emits real-time event when a Task is claimed.

### Agent Pickup
- [ ] On real-time event, the gateway routes the Task to the assigned Agent Profile's runner.
- [ ] Runner executes the task (skill calls go through Docker as in Slice 7).
- [ ] Task state transitions: Assigned → Executing → Completed (or Blocked / Review on failure).
- [ ] Result stored on Task DocType.

### Kanban
- [ ] Native Frappe Kanban view enabled on Agent Task grouped by `workflow_state`.
- [ ] Live updates: state changes reflect in the Desk Kanban view in real time.

### Tests
- [ ] Concurrency test: 100 Tasks, 5 concurrent dispatcher runs, each Task claimed exactly once.
- [ ] State machine test: every transition is permitted or denied per the Workflow definition.
- [ ] End-to-end: create a Task → dispatcher claims → agent executes → state reaches Completed.

---

## Slice 9 — Polish & Hardening

### Tests
- [ ] Overall line coverage ≥ 70% on `friday/`.
- [ ] Critical modules (`permissions`, `gateway`, `agents/isolation`, `tasks/dispatcher`) ≥ 85%.
- [ ] No `xfail` or skipped tests without a tracked issue.

### Logging
- [ ] All permission decisions logged (Permission Decision Log).
- [ ] All skill executions logged (Execution Log).
- [ ] All dispatcher actions logged (frappe.logger).
- [ ] Log levels appropriate: INFO for state changes, WARNING for retries, ERROR for failures.

### Documentation
- [ ] `README.md` — concise overview, install commands, quickstart.
- [ ] `docs/install.md` — full prerequisites and setup.
- [ ] `docs/quickstart.md` — first agent + skill in 10 minutes.
- [ ] `docs/architecture.md` — high-level, links to the seven Friday specs.
- [ ] `docs/hermes-audit.md` — produced in the Evaluation phase, kept current.
- [ ] `SECURITY.md` — how to report vulnerabilities privately.
- [ ] `CONTRIBUTING.md` — DCO, conventional commits, PR process.
- [ ] `CODE_OF_CONDUCT.md` — Contributor Covenant 2.1.

### Repo Hygiene
- [ ] `LICENSE` is the unmodified GPL v3 text.
- [ ] `NOTICE` includes all Hermes attributions.
- [ ] `.github/ISSUE_TEMPLATE/` populated (bug, feature, security).
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` present.
- [ ] `.pre-commit-config.yaml` runs on every commit.
- [ ] CI workflow (`.github/workflows/test.yml`) runs tests on PR.

### Dogfood
- [ ] Friday has tracked at least 20 of its own remaining tasks in its own Kanban for 5+ days.
- [ ] No critical bugs found during dogfood that haven't been fixed.

### Performance
- [ ] Permission check median latency < 5ms with warm cache.
- [ ] End-to-end skill execution (CLI → Docker → reply) median < 3s (excluding LLM time).
- [ ] Dispatcher handles 500 Tasks/minute on a single worker.

---

## Phase One Exit (All Slices Complete)

When every box above is green, the agent produces a **Phase One Completion Report**:

```markdown
# Phase One Completion Report

## Slices Completed
- [ ] 1 — Foundations
- [ ] 2 — Permission Engine
- [ ] 3 — Skill Loader
- [ ] 4 — Gateway + CLI
- [ ] 5 — LLM Integration
- [ ] 6 — First Skill
- [ ] 7 — Docker Sandboxing
- [ ] 8 — Tasks & Kanban
- [ ] 9 — Polish

## Metrics
- Total commits: ___
- Total tests: ___
- Coverage: ___%
- Open issues: ___
- Hermes audit: ___ REUSE, ___ ADAPT, ___ REWRITE entries

## Known Limitations
- [list each, with link to deferred-to-Phase-2 issue]

## Recommendation
Ready / Not ready for open-source launch (Phase 2).

## Decisions Awaiting Human
- [any open spec amendments or scope changes proposed during build]
```

The human reviews the report, decides on the Phase 2 launch, and the agentic workflow continues.
