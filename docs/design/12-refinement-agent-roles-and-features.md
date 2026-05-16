# 12 — Refinement: Agent Role Profiles, Multi-Agent Hierarchies, Delegation, Escalation

> **Purpose:** Refine documents 01–11 to address agent governance more deeply. Introduces **Agent Role Profiles** (pre-provisioned permission bundles), multi-agent hierarchies, delegation chains, and escalation workflows. Targets Frappe v15 stable, forward-compatible with v16.

---

## 1. Why This Refinement

The original module design (`05-module-design.md`) assumed roles get assigned to Agent Profiles manually, one by one. In practice, agents are created in bulk for projects, and each agent type (task worker, supervisor, data processor) has a recurring set of permissions.

Manual assignment is:
- Error-prone (forgetting a permission breaks the agent or opens a hole)
- Inconsistent across agents of the same type
- Hard to update fleet-wide

Frappe already solves this for humans via **Role Profile**. Friday adopts the same idea, specialised for agentic permissions.

---

## 2. Agent Role Profile DocType

A new DocType that bundles roles, permitted skills, and execution constraints for a type of agent.

### Fields

| Field | Type | Notes |
|---|---|---|
| `profile_code` | Data (unique) | e.g. `task_worker`, `data_processor`, `supervisor`, `qa_agent` |
| `display_name` | Data | Human-readable name |
| `description` | Text | Purpose, capabilities, restrictions |
| `base_role_profile` | Link → Role Profile (Frappe native) | Optional inheritance from Frappe Role Profile |
| `roles` | Table → Role | Roles granted to agents using this profile |
| `permitted_skills` | Table → Skill | Skill whitelist (overrides role-only matching) |
| `default_resource_quota` | Section + fields | CPU, memory, requests/hr, max concurrent execs |
| `default_network_allowlist` | Table | External hosts agents may reach by default |
| `requires_approval_above_risk` | Select | low / medium / high / always |
| `can_delegate_to` | Table → Agent Role Profile | Which profiles this agent may delegate to |
| `can_escalate_to` | Table → Agent Role Profile | Which profiles handle escalations |
| `status` | Select | Active / Deprecated |

### Relationship to Agent Profile

The `Agent Profile` DocType from doc 05 gets a new field:

| Field | Type | Notes |
|---|---|---|
| `role_profile` | Link → Agent Role Profile | The profile this agent inherits from |

The `assigned_roles` field on Agent Profile becomes **derived** — populated from the linked Agent Role Profile, with optional per-agent additions. Resource quotas, network allowlist, and approval thresholds inherit similarly with per-agent override allowed.

### Why a New DocType vs. Reusing Frappe Role Profile

Frappe's native Role Profile bundles only roles. Agent Role Profiles must also bundle:
- Skill whitelists (concept doesn't exist on Frappe Role Profile)
- Resource quotas (agent-specific)
- Network allowlist (sandbox-specific)
- Approval thresholds (agentic governance)
- Delegation and escalation routing

So Agent Role Profile is a **superset**. It can optionally inherit from a Frappe Role Profile via `base_role_profile` to reuse role bundles already defined for human users.

**⚠️ Engineering TODO:** Verify Frappe Role Profile's update propagation semantics work for agent contexts (cache invalidation, hook timing). Confirmed in Phase 1 slice 1 design spike.

---

## 3. Standard Agent Role Profiles (Ship with Friday)

Friday ships with a default set every installation gets. Users can extend, disable, or override these.

| Profile | Purpose | Typical Roles | Typical Skills | Approval Threshold |
|---|---|---|---|---|
| `task_worker` | Executes individual Agent Tasks | Friday Agent, Task Executor | Skills tagged "low-risk", "task_execution" | `high` |
| `data_processor` | Reads, transforms, writes data documents | Friday Agent, Data Reader, Data Writer | Skills tagged "data_io" | `high` |
| `qa_agent` | Reviews completed work, flags issues | Friday Agent, QA Reviewer | Read-only skills + Comment write | `always` (for any write) |
| `supervisor_agent` | Oversees other agents, approves escalations | Friday Agent, Supervisor | Workflow Request decisions, agent delegation | `high` |
| `integration_agent` | Talks to external APIs / MCP servers | Friday Agent, Integration | External-call skills | `medium` |
| `dev_agent` | Authors / edits skills (drafts only) | Friday Agent, Skill Author | `skill_draft.create`, `skill.read` | `always` |
| `read_only_agent` | Observation / reporting only | Friday Agent, Read Only | All read skills, no write | n/a |

These are starting points. A real deployment will customise them.

---

## 4. Multi-Agent Hierarchies

Agents form a hierarchy via two relationships:

### 4.1 Delegation (peer or downward)
An agent of profile X may invoke an agent of profile Y if Y is in X's `can_delegate_to` list.

Example: `supervisor_agent` may delegate to `task_worker` and `data_processor`. `task_worker` may not delegate at all.

### 4.2 Escalation (upward)
When an agent encounters a blocker, it escalates to a profile listed in its `can_escalate_to`.

Example: `task_worker.can_escalate_to = [supervisor_agent, human_supervisor]`.

### 4.3 No Implicit Hierarchy
The system has **no implicit "everyone reports to admin"** rule. All paths are explicit, audited, and revocable by changing the role profile.

---

## 5. Delegation Chains

### Flow

```
Agent A (profile X) → wants to invoke Agent B's skill
1. Gateway checks: is profile Y in X.role_profile.can_delegate_to?
2. If yes → check B's permission for the requested skill
3. If both pass → create a Delegation Request DocType
4. Spawn or route to an instance of profile Y
5. Y executes with its own permissions, not X's (no privilege escalation)
6. Result returned through the gateway, logged with delegation chain noted
```

### Delegation Request DocType

| Field | Type |
|---|---|
| `from_agent_profile` | Link |
| `to_agent_profile` | Link |
| `requested_skill` | Link → Skill |
| `parameters` | JSON |
| `parent_task` | Link → Agent Task |
| `parent_execution_log` | Link → Execution Log |
| `status` | Select (Pending / Running / Completed / Failed / Denied) |
| `result_execution_log` | Link → Execution Log |
| Submittable | Yes |

### Anti-Pattern Guards

- A delegation loop (A → B → A) is detected and rejected.
- Maximum chain depth configurable (default 5). Exceeding it returns an error and logs.
- Delegation does not transfer credentials. Y always uses Y's scoped token, never X's.

---

## 6. Escalation Workflows

### Trigger
An agent encounters one of:
- A skill it doesn't have permission for (and the task requires it)
- Repeated failure (configurable: e.g. 3 retries exhausted)
- An LLM-emitted explicit escalation tool call ("I need human or supervisor help")
- A timeout exceeding the task's wall-clock budget

### Flow

```
1. Agent emits an Escalation Event (programmatic or LLM-decided)
2. Gateway creates an Escalation DocType row
3. Looks up the agent's role_profile.can_escalate_to
4. For each target profile, notify in priority order:
   - First: route as a Workflow Request to the highest-priority target
   - On no-response timeout: cascade to next target
   - Final fallback: post to the project's War Room with @here mention
5. Resolver (agent or human) makes a decision:
   - Approve + take over → resolver executes
   - Approve + return → agent retries with new context
   - Reject → task marked Blocked, awaiting human review
6. Decision logged immutably
```

### Escalation DocType

| Field | Type |
|---|---|
| `originating_agent_profile` | Link |
| `originating_task` | Link → Agent Task |
| `reason_code` | Select (permission_denied / repeated_failure / explicit / timeout) |
| `details` | Long Text |
| `attempted_targets` | Table |
| `resolved_by` | Link → User or Agent Profile |
| `resolution` | Select (taken_over / returned_to_agent / blocked / cancelled) |
| `resolved_at` | Datetime |
| Submittable | Yes |

### Integration with War Room

When an escalation cascades to "post to War Room", Raven receives a structured message:

```
⚠️ Escalation from @agent-name on Task #1234
Reason: permission_denied (skill `transfer_funds`)
Suggested resolver: any @supervisor_agent
[Approve in Frappe →]  [Take Over →]  [Decline →]
```

The buttons are Raven Message Actions that trigger Workflow Request decisions.

---

## 7. Permission Inheritance Rules

When an Agent Profile is instantiated:

```
effective_roles =
  (Agent Role Profile.base_role_profile.roles  if set else ∅)
  ∪ Agent Role Profile.roles
  ∪ Agent Profile.additional_roles   ← per-agent override (optional)

effective_skills =
  (Agent Role Profile.permitted_skills)
  ∩ skills_permitted_by(effective_roles)
  ∪ Agent Profile.additional_skills   ← per-agent override (⊆ role-permitted)

effective_quota =
  Agent Profile.quota_override  if set
  else Agent Role Profile.default_resource_quota
```

**Invariant:** an Agent Profile can never have **more** permission than its Agent Role Profile permits (additional_roles must be a subset of role-profile-permitted, validated on save).

---

## 8. Lifecycle: Creating a New Agent

The common path:

1. Pick an Agent Role Profile from the standard set (or create custom).
2. Create an Agent Profile with `role_profile` set and a `linked_user` (Frappe User to act as).
3. Optionally add `additional_skills` or `quota_override`.
4. Save → Friday auto-derives effective_roles, effective_skills, effective_quota and caches them in Redis.

No manual permission assignment per agent. Onboarding 50 task workers is a single profile selection per agent (or bulk import).

---

## 9. Worked Example: Customer Onboarding Sprint

**Setup:**
- Agent Role Profiles: `task_worker`, `data_processor`, `supervisor_agent`
- One project: "Customer Onboarding Sprint" (Agent Project)
- Tasks created with required_skills tagged

**Agents instantiated:**
- 5 × `task_worker` agents (each linked to a dedicated Frappe User)
- 2 × `data_processor` agents
- 1 × `supervisor_agent`

**Permissions flow:**
- Each `task_worker` inherits permissions for low-risk task execution skills only.
- Each `data_processor` inherits read/write on Customer DocType + tagged skills.
- The `supervisor_agent` inherits delegation rights to both other profiles and is in their `can_escalate_to`.

**Runtime:**
- Dispatcher claims 5 tasks → assigns one to each task_worker.
- Task_worker #3 hits permission_denied trying to call `update_customer_credit_score` (data scope it doesn't have).
- Auto-escalation → goes to supervisor_agent (first in escalate_to list).
- Supervisor sees the escalation in War Room, decides to delegate to a data_processor.
- Data_processor executes successfully.
- Original task_worker resumes with the updated data.
- All chains logged in Delegation Request and Escalation DocTypes.

---

## 10. Migration Path from Doc 05

For installations that already created Agent Profiles per doc 05:
1. Install Agent Role Profile DocType.
2. Create a default profile per existing agent "type" (inferred from role overlap).
3. Migration patch sets `role_profile` on each Agent Profile by best-match.
4. Operators review and adjust in the Desk.

Non-breaking: an Agent Profile without `role_profile` continues to work using its `assigned_roles` directly.

---

## 11. Forward Compatibility with Frappe v16

Frappe v16 introduces UUID naming, faster permission resolution, and workflow state transition actions. Friday's Agent Role Profile will benefit from these without redesign:
- UUID naming on Agent Profile makes cross-site references safer (see doc 37 / multi-site).
- Faster permission resolution reduces the gateway permission-check latency budget.
- State transition actions can auto-trigger delegation/escalation routing.

No design changes needed for v16 — the model is forward-compatible.
