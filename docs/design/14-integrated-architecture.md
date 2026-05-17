# 14 — Integrated Architecture: Friday Framework + Frappe Substrate + Raven + ERPNext Project/Task + Hermes

> **Purpose:** Define how the foundational layers of Friday — **Frappe v16 fork as the framework engine**, **Raven**, **ported ERPNext Project/Task/Issue**, and **Hermes' gateway/agent loop patterns** — fit together as one coherent system.

This document supersedes any earlier assumptions that Friday builds Project/Task/Issue from scratch or builds chat from scratch. The unified stack reuses battle-tested Frappe-ecosystem apps wherever possible and reserves custom code for what's genuinely new (the agentic layer).

---

## 1. The Four Layers

| Layer | Source | Role in Friday |
|---|---|---|
| **Friday Framework Core** | Hard fork of Frappe v16 stable | Foundation: DocTypes, permissions, workflows, real-time, scheduler, RQ, REST API, bench ecosystem, Friday agent commands, agent-native core primitives, control-room shell |
| **Raven** | `The-Commit-Company/raven` | Communication and War Room workspaces |
| **Project + Task + Issue** | Ported from `frappe/erpnext` | Orchestration backbone for multi-agent work |
| **Friday Core (Hermes-derived)** | New code, inspired by `NousResearch/hermes-agent` | Agent loop, gateway, skills, dispatcher, isolation |

Friday is the framework. The Friday repository is a hard fork of Frappe v16 stable — Frappe is the engine underneath. Upstream Frappe patches are absorbed manually when relevant (security, bug fixes, improvements). Agent-native primitives are built into core; domain features live in Friday apps.

---

## 2. Why This Composition

We arrived here by elimination, not assumption:

- **Chat from scratch?** Rejected — Raven already exists, is GPL-compatible, has Slack-grade UX, integrates with Frappe natively, supports document sharing and message actions. Building chat ourselves would be reinvention.
- **Project/Task from scratch?** Rejected — ERPNext's Project, Task, and Issue DocTypes are mature, support time tracking, dependencies, and Kanban natively. Porting (rather than depending on full ERPNext) keeps Friday self-contained while inheriting that maturity.
- **Hermes' backend?** Rejected — file-based skills, SQLite sessions, ad-hoc permissions don't meet enterprise requirements. The agent loop and skill ideas are kept; the storage and governance are replaced.
- **Hermes' fixed Kanban lifecycle?** Rejected — real business workflows need configurable states and transitions. Friday keeps durable coordination but renders Frappe Workflow states as Kanban columns.
- **Custom permission engine?** Rejected — Frappe's role-based system is mature and battle-tested. Friday extends it; it does not replace it.

The result: Friday focuses its custom engineering effort on the **agentic layer** — gateway, dispatcher, sandbox, permission gating — and reuses the rest.

---

## 3. Layer Responsibilities

### 3.1 Friday Framework Core (Frappe-Derived Foundation)

Owns:
- DocType schema and ORM
- Role-based permissions (foundation for Friday's gateway permission gate)
- Workflow engine (used for Task state machine and approval routing)
- Real-time pubsub (used by Raven, gateway, and Kanban live updates)
- Background workers / RQ (used for skill executions, dispatcher tick, curator)
- Scheduler (used for periodic jobs)
- REST API (used by agent containers and external integrations)
- User accounts and authentication (every Agent Profile links to a User)

Friday adds framework identity and agent-native extension points where needed:
- bench remains the operational CLI; Friday adds agent-facing command groups or wrappers
- Friday Control Room workspace defaults
- actor/trace context propagation for agent execution
- framework-level audit hooks where app hooks are insufficient
- agent-aware defaults for jobs, workflows, and execution logs

Core divergence must follow `39-friday-framework-strategy.md`: minimal, documented, and only when a module/app cannot safely provide the behavior.

### 3.2 Raven (Communication)

Owns:
- Channels (public / private)
- Direct messages
- Message reactions (custom emojis for agent status)
- File and image sharing
- Message Actions (right-click → create DocType)
- Document sharing with previews
- Timeline integration on Frappe documents

Friday adds:
- Auto-create one Raven Channel per Agent Project (the **War Room**)
- Auto-join the project's assigned Agent Profiles and supervisors
- Custom Message Actions: escalate, log decision, approve skill, import skill
- A standard emoji set indicating agent state (executing, blocked, completed, review)
- Hooks that surface critical agent events (permission denial, skill failure, escalation) as channel messages

### 3.3 Ported Project / Task / Issue (Orchestration)

Owns (after porting):
- `Agent Project` (renamed from ERPNext Project) — container for related agent tasks
- `Agent Task` (renamed from ERPNext Task) — unit of work, assignable to Agent Profile
- `Agent Issue` (renamed from ERPNext Issue) — blocker, escalation, or bug report
- Native Kanban view on Agent Task
- Native Gantt view on Agent Project
- Task dependencies and predecessor relationships
- Time tracking on tasks

Friday adds:
- `assigned_to_profile` field on Agent Task (linking to Agent Profile)
- `required_skills` table on Agent Task
- Workflow templates tuned for agentic execution; the default may be Pending → Assigned → Executing → Blocked → Review → Completed → Cancelled, but projects can define different states
- Dispatcher integration (claims unassigned tasks)
- Real-time event emission on state changes

The ported DocTypes are **not** ERPNext dependencies — they live inside the Friday app, are renamed to avoid name clashes if ERPNext is installed alongside, and are maintained by the Friday team going forward.

### 3.4 Friday Core (Agentic Layer)

Owns (this is the genuinely new code):
- `Agent Profile` DocType — links to a Frappe User, references an Agent Role Profile
- `Agent Role Profile` DocType — predefined bundles of roles + skill permissions
- `Skill` DocType — structured skill schema with dual storage (DB + file backup)
- `Execution Log` (submittable) — every skill invocation
- `Permission Decision Log` (submittable) — every permission check
- `Workflow Request` — approval routing for high-risk skills
- Gateway orchestrator service (long-running process)
- Dispatcher (scheduled job)
- Permission engine (gates every skill at runtime)
- Skill loader and cache
- Docker-based isolation runtime
- LLM provider adapters
- Platform message adapters (CLI in Phase 1; more in Phase 2)

---

## 4. End-to-End Request Flow (Integrated Stack)

A real example tracing through all four layers:

```
1. Supervisor opens the Frappe Desk
   → creates an Agent Project ("Customer Onboarding Sprint")
   → adds Tasks, each tagged with required_skills and target Agent Profiles

2. Frappe hook fires on Agent Project after_insert
   → Friday creates a Raven Channel named "war-room/customer-onboarding-sprint"
   → adds assigned Agent Profiles' linked Users to the channel
   → posts a pinned message with the project brief and emoji legend

3. Dispatcher (Frappe scheduled job, runs every 60s)
   → queries Agent Task where workflow_state is dispatchable AND assigned_to_profile is null
   → matches each task to eligible Agent Profile based on required_skills ⊆ profile's permitted skills
   → atomically claims the task: SELECT ... FOR UPDATE SKIP LOCKED
   → updates workflow_state='Assigned'
   → emits Frappe real-time event 'agent_task.assigned'

4. Gateway (listening on Redis pubsub)
   → receives 'agent_task.assigned'
   → posts a status update to the War Room: "@agent-name picked up task X 🚀"
   → spawns or routes to the agent's Docker container

5. Agent runs the agent loop
   → reads its system prompt + permitted skills (cached in Redis)
   → calls the LLM with skill definitions
   → LLM emits a tool call → e.g. send_welcome_email(customer_id=...)

6. Permission engine gates the call (BEFORE any execution)
   → loads matrix from Redis (cache hit on warm path)
   → verifies the agent's role permits Email + write
   → logs a Permission Decision Log row (submitted)
   → on allow: proceeds. On deny: rejects with reason and posts ❌ in War Room

7. Skill executes inside Docker
   → container calls Frappe REST API with scoped token
   → Email DocType row is created
   → result returned to gateway as JSON

8. Gateway records the outcome
   → submits an Execution Log row
   → updates the Agent Task state machine (e.g. → Review or → Completed)
   → posts a status update in War Room ("Task X completed ✅" with link to Email document)

9. Raven Timeline integration
   → the message is pushed to the Agent Task's Frappe Timeline
   → the project record now shows the full conversation as audit history

10. Supervisor reviews
    → opens the War Room or the Agent Task
    → right-clicks on the agent's "completed" message
    → uses Raven Message Action "Approve & close task"
    → action creates / updates the Task to workflow_state='Completed'
```

Every step is auditable. Every step is permission-checked. Every step is queryable from Frappe.

---

## 5. Data Model Map

How DocTypes relate across the four layers:

```
User (Frappe)
  ↑ linked_user
Agent Profile (Friday)
  ↓ uses
Agent Role Profile (Friday) ──── grants ────→ Roles (Frappe)
                                              ↓ permit
                                              DocTypes (Frappe + ported)

Agent Project (ported ERPNext)
  ↓ has many
Agent Task (ported ERPNext + Friday fields)
  ↓ has many
  • Execution Log (Friday)
  • Permission Decision Log (Friday)
  • Workflow Request (Friday)
  • Raven Channel (one per project → War Room)
  • Raven Messages (in that channel)

Skill (Friday, dual storage)
  ↓ referenced by
Agent Task.required_skills (link table)
Agent Profile.permitted_skills (link table)
```

---

## 6. Dual-Storage Skills (DocType + File)

Skills live in two places:

1. **Authoritative for governance:** `Skill` DocType in PostgreSQL — queryable, permission-aware, audit-trailed.
2. **Authoritative for portability and DR:** A file in a Friday-managed directory (`{site}/private/files/skills/{skill_name}.json` or `.yaml`).

Sync rules:
- DocType save → write file (post-commit hook).
- File change detected (manual edit or git pull) → flagged for human review in a `Skill Sync Conflict` DocType, never auto-imported.
- Import flow: validate file → create/update DocType via the standard insert path so permissions and hooks fire.

**Why both?**
- Files are portable: easy to share across teams, version in Git, distribute through the Friday community.
- DocTypes are governable: permission checks, audit, status flags, usage metrics.
- They back each other up: a corrupted database row can be restored from file; a deleted file can be regenerated from the DocType.

**⚠️ Engineering Note — to refine later:**
Caching strategy still needs depth. Open questions:
- Where does the gateway read skills from on the hot path — Redis cache (populated from DocType) or Redis cache (populated from file)?
- How do we resolve concurrent edits to the same skill from two channels (Desk edit + Git pull)?
- What's the conflict-resolution UI for `Skill Sync Conflict` rows?
- Should the file format be JSON, YAML, or markdown-with-frontmatter (Hermes-style)?

These need a deeper engineering pass before Slice 3 of Phase One implementation. **Marked as a TODO; conceptually agreed; deferred to a dedicated design spike.**

---

## 7. Frappe File Manager Integration

Friday uses Frappe's built-in File DocType and file manager for:

- **Skill file storage** — under `private/files/skills/`, permission-aware.
- **Execution attachments** — agents may produce files (PDFs, images, transcripts); they're attached to Execution Log rows via the File DocType.
- **Skill import/export bundles** — collections of skills exported as a single zip/tar for distribution.
- **War Room file sharing** — Raven already wraps Frappe's file system; uploads there inherit the same permissions and lifecycle.

No custom file storage layer needed. Frappe's permissions on the File DocType govern who can read/write each artifact.

---

## 8. Skill Import / Export Pipeline

### Export
1. Supervisor selects one or more `Skill` rows in Friday.
2. Triggers "Export Skills" action.
3. Friday packages them as a zip containing:
   - One JSON/YAML file per skill (full schema)
   - A `manifest.json` with version, author, license (GPL v3 by default)
   - Optional README
4. File is saved to Frappe's File Manager, downloadable via REST.

### Import
1. Supervisor uploads a skill bundle (zip or single file).
2. Friday parses the manifest, validates each skill against the JSON schema.
3. For each skill:
   - Check if a Skill with the same name exists.
   - If yes → create a `Skill Draft` for review (never silent overwrite).
   - If no → create as `Skill` with `status='Experimental'`.
4. Supervisor reviews drafts in the Desk, promotes to Active when satisfied.
5. Audit log records who imported what, when, from where.

**Human intervention is mandatory at:**
- Conflict resolution (existing skill vs imported skill)
- Promotion from Experimental → Active
- Deletion of any Active skill (grace period via Retire → Archive → Delete flow)

---

## 9. War Room Workspace (Project Hub)

The War Room is not just a chat channel — it's the project's command center.

**Components:**
| Element | Backed by |
|---|---|
| Real-time conversation | Raven channel |
| Active task list | Frappe List View on Agent Task filtered by project |
| Kanban board | Frappe Kanban View on Agent Task |
| Agent status panel | Custom Vue component, reads Agent Profile + recent Execution Logs |
| Document feed | Raven document sharing |
| Quick action buttons | Raven Message Actions + Frappe form actions |
| Pinned project brief | Raven pinned message |
| Audit timeline | Frappe Timeline on Agent Project |

**Composition pattern:** a Frappe Workspace (the v16 redesigned workspace) configured for each Agent Project, pulling Raven channel embed, Kanban, list view, and custom panels into one screen.

---

## 10. Hermes Mapping (What Stays, What Goes)

| Hermes piece | Verdict in integrated stack |
|---|---|
| AIAgent loop | ADAPT — keep loop, replace state plumbing |
| Prompt builder | ADAPT — replace file reads with DocType reads |
| Skill markdown system | REWRITE — replaced by Skill DocType + file mirror |
| Kanban dashboard | REWRITE — replaced by Frappe Workflow + Kanban View on Agent Task |
| Platform adapters | ADAPT for CLI (Phase 1); Raven becomes the "chat platform" for human interaction |
| Cron / scheduler | REWRITE — replaced by Frappe Scheduler |
| Session storage (SQLite + FTS5) | REWRITE — replaced by PostgreSQL + tsvector |
| Approval routing | REWRITE — replaced by Frappe Workflow + Raven Message Actions |
| Memory / vector | REWRITE — replaced by pgvector (Phase 2) |
| Tirith command scanner | REUSE as external dependency (Phase 2) |
| LLM provider abstraction | REUSE pattern, build minimal version Phase 1 |
| Inter-agent dispatching | REWRITE — replaced by dispatcher querying Agent Task |

Hermes is now best understood as a **reference implementation of the agentic ideas**, not a codebase to fork. Friday is a fresh implementation of those ideas on the Frappe + Raven + ported-ERPNext substrate.

The specific Hermes Kanban lesson is captured in `41-porting-strategy-hermes-erpnext-raven.md`: agents may propose profiles, skills, tasks, and workflows, but they do not silently activate safety-critical structure. Validated DocTypes and Frappe Workflow own the operating model.

---

## 11. Phase Mapping Update

This integrated architecture refines the Phase One scope as follows. Where this document conflicts with `39-friday-framework-strategy.md`, the framework strategy wins for product identity and fork discipline.

**Phase 1 (unchanged scope, clarified dependencies):**
- Establish Friday Framework shell from selected Frappe source substrate
- Preserve bench for operations; add Friday-facing agent commands and Friday Control Room workspace
- Install Raven (used for War Room from day one)
- Port Agent Project, Agent Task, Agent Issue from ERPNext into Friday app
- Build Friday core: Agent Profile, Agent Role Profile, Skill (with file mirror), Execution Log, Permission Decision Log, Workflow Request
- Implement gateway, dispatcher, permission engine, Docker isolation
- CLI adapter for direct agent interaction
- One real skill (`create_note`) end-to-end with War Room status updates

**Phase 2 (additions to scope):**
- Additional platform adapters (Telegram, Slack, etc.) alongside Raven
- Memory module with pgvector
- Skill import/export pipeline
- Voice, vision, browser automation
- Tirith integration
- v16 migration (if Phase 1 was on v15)

---

## 12. Engineering TODOs Captured Here

The following items have conceptual agreement but require dedicated engineering design spikes before implementation:

| TODO | Rationale | Suggested Owner / Phase |
|---|---|---|
| Skill DocType ↔ file sync strategy and conflict resolution UI | Hybrid system needs concrete semantics | Phase 1, week 3 design spike |
| Skill cache: file-vs-DocType source of truth on hot path | Performance vs governance tradeoff | Phase 1, week 3 design spike |
| War Room channel archive / retention policy | Aligning Raven retention with Frappe lifecycle | Phase 2 |
| Concurrency between Raven message stream and Execution Log writes | Avoiding torn audit trails | Phase 1, slice 8 |
| Fine-grained Message Action permissions in Raven | Restrict who can trigger which action | Phase 2 |
| Agent Role Profile schema details (inherits Frappe Role Profile?) | Need to test whether Frappe Role Profile is sufficient or we need a new DocType | Phase 1, slice 1 design spike |
| ERPNext port: which fields to drop, which to keep | Avoid carrying ERP-specific clutter | Phase 1, slice 1 |

These TODOs are noted explicitly to prevent silent guesses during implementation. The agent following the Execution Guide should treat each as a blocker and produce a design proposal before proceeding.

---

## 13. Summary

Friday is the **assembly** of:

- **Friday Framework Core** for the Frappe v16 fork engine: data, permission, workflow, bench operations, Friday agent commands, workspace, real-time, and agent-native core primitives
- **Raven** for human-agent and agent-agent collaboration via War Rooms
- **Ported Project / Task / Issue** for orchestration scaffolding
- **Friday Core** for the agentic layer (gateway, dispatcher, skills, isolation, permission gate)

This is an **integrated architecture record**. The framework-first direction in `39-friday-framework-strategy.md` is the higher-level product identity record.
