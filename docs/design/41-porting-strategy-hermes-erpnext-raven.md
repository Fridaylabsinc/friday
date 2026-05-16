# 41 — Porting Strategy: Hermes Core, ERPNext Work Objects, Raven War Room

> **Purpose:** Convert the lived Hermes Kanban failure case into Friday's porting strategy. Hermes proves the multi-agent coordination pattern, but Friday must rebuild that pattern on Frappe's typed DocTypes, workflows, validations, permissions, and views.

---

## 1. Origin Story

The practical test was simple: ask Hermes Agent to create profiles, create a board, create tasks, and run a multi-agent workflow.

The result was useful but not reliable enough for a real framework:

- Basic bounded tasks worked, such as analysing a file.
- Multi-agent setup failed repeatedly.
- Profiles and skills were built incorrectly.
- The board structure was too rigid.
- The agent was forced to invent too much of the operating model from loose text.

This is the product insight:

> Agents should not improvise the operating model. They should operate inside one.

Hermes shows the right orchestration shape. The failure mode shows why Friday needs Frappe.

---

## 2. What We Keep From Hermes

Friday should keep these ideas:

- durable task coordination instead of fragile in-context subagent swarms;
- named agent profiles instead of anonymous subagents;
- dispatcher-driven claiming of ready work;
- worker lanes by profile or capability;
- task dependencies and dependency promotion;
- block / unblock loops for human input;
- heartbeat and stale-claim recovery;
- per-task run history;
- circuit breaker after repeated failures;
- orchestrator agents that decompose work without doing every task themselves.

These are architectural patterns, not storage decisions.

---

## 3. What We Reject From Hermes

Friday should not inherit these assumptions:

- file / SQLite state as the authority for enterprise workflows;
- agent-created profiles becoming executable without schema validation;
- agent-created skills becoming active without review and tests;
- fixed Kanban columns as the workflow model;
- dashboard state as the source of truth;
- permissive profile/tool wiring that depends on prompt discipline;
- task orchestration that is hard to audit through business records.

Hermes is a strong personal/local agent runtime. Friday is a framework for governed business agents.

---

## 4. Friday Translation

| Hermes Concept | Friday Translation | Source of Truth |
|---|---|---|
| Kanban board | Agent Project / Workflow Board | Frappe DocTypes |
| Kanban task | Agent Task | Frappe DocType |
| Fixed columns | Workflow states rendered as Kanban columns | Frappe Workflow |
| Profile | Agent Profile | Frappe DocType linked to User |
| Profile lane | Agent Role Profile / Dispatcher lane | Frappe DocTypes |
| `kanban_*` tools | `task_*`, `execution_*`, `approval_*` tools | Friday gateway |
| Worker process | Agent Execution / Sandbox Execution | Execution Log |
| Comments | Task comments + Raven messages | Frappe Timeline / Raven mirror |
| Runs | Agent Execution rows | Frappe DocType |
| Board isolation | Project / site / tenant permission boundary | Frappe permissions |

The rule:

> Agent Project, Agent Task, Workflow, Execution Log, and Permission Decision Log own the truth. Raven reflects and enriches collaboration. Agents act through governed tools.

---

## 5. Flexible Workflow, Not Fixed Columns

Hermes' default lifecycle is useful:

`Triage -> Todo -> Ready -> In Progress -> Blocked -> Done`

Friday should not hardcode it.

Real businesses need different flows:

- Procurement: `Draft -> Supplier Follow-up -> Internal Review -> Approval Needed -> PO Drafted -> Completed`
- Engineering: `Idea -> Spec Needed -> Build -> Review Required -> Changes Requested -> Merged`
- Support: `Reported -> Triage -> Investigation -> Waiting on Customer -> Escalated -> Resolved`
- Research: `Question -> Source Gathering -> Synthesis -> Review -> Published`

Friday's principle:

> Kanban is a view, not the workflow.

The workflow is defined through Frappe Workflow, Agent Task Type, and validation rules. The Kanban board renders whichever states are configured for that task or project type.

Minimum model:

- `Agent Task.workflow_state` stores the current state.
- `Agent Task Type` determines the workflow template.
- Workflow states can be marked `kanban_visible`.
- Workflow states can be marked `dispatchable`.
- Workflow transitions can require role, approval, or risk checks.
- Dispatcher only claims tasks in dispatchable states.
- Agents can only move tasks through allowed transitions.

---

## 6. Profile And Skill Governance

Hermes lets profiles and skills be lightweight and flexible. That flexibility is also where the real-world failure happened.

Friday should treat profiles and skills as governed records:

- `Agent Profile` defines identity, linked user, model, status, quotas, allowed roles, allowed skills, memory scope, and execution policy.
- `Agent Role Profile` defines reusable bundles of roles, skill permissions, risk thresholds, delegation rules, and approval rules.
- `Skill` defines name, description, input schema, output schema, allowed DocTypes, allowed operations, risk level, runtime, tests, and status.
- `Skill Version` tracks changes and rollback.
- `Skill Draft` captures agent-proposed skills before review.

Agents may propose profiles, skills, tasks, and workflows. They may not silently activate safety-critical structure.

Promotion gates:

| Object | Agent May Propose | Human / Supervisor Must Approve |
|---|---:|---:|
| Agent Profile | Yes | Before active |
| Agent Role Profile | Yes | Before active |
| Skill | Yes | Before active |
| Skill Version | Yes | Before default |
| Workflow | Yes | Before dispatchable |
| High-risk Task | Yes | Before execution |

---

## 7. ERPNext Project / Task / Issue Porting Strategy

Friday should selectively port ERPNext's mature work objects, not depend on the whole ERPNext app for Phase 1.

Port as renamed Friday-native DocTypes:

- `Agent Project` from ERPNext Project
- `Agent Task` from ERPNext Task
- `Agent Issue` from ERPNext Issue

Keep:

- project container semantics;
- task assignment;
- priorities;
- dependencies / predecessor relationships;
- status and workflow support;
- Kanban / list / report / calendar / Gantt compatibility where useful;
- comments, timeline, attachments, and activity history.

Drop or defer:

- ERP-specific fields that are not needed for agent orchestration;
- billing or timesheet coupling unless it supports a concrete Phase 1 use case;
- customer/project accounting assumptions;
- any field that makes the object feel like ERPNext rather than Friday.

Add:

- `assigned_to_profile`;
- `required_skills`;
- `risk_level`;
- `approval_policy`;
- `dispatchable_state`;
- `current_execution`;
- `last_execution_status`;
- `blocked_reason`;
- `war_room_channel`;
- `automation_mode`;
- `evidence_required`;
- `completion_contract`.

---

## 8. Raven War Room Strategy

Raven should be integrated before it is deeply forked.

Raven owns:

- conversation;
- channels;
- human comments;
- message actions;
- file sharing;
- real-time collaboration.

Friday owns:

- workflow truth;
- task state;
- execution truth;
- permissions;
- audit;
- approvals;
- sandboxing;
- dispatcher decisions.

War Room behavior:

- one Raven channel can be created per Agent Project;
- important Agent Task events are posted to the channel;
- message actions can request approval, block a task, create an issue, or attach evidence;
- every action routes through Friday permission checks;
- Raven messages are mirrored to Frappe Timeline where audit relevance exists;
- Execution Log remains the legal / operational proof.

Raven is the room where people and agents talk. Friday is the system that decides what is true and what is allowed.

---

## 9. Dispatcher Contract

The dispatcher should not infer the world from text. It should query validated records.

Dispatcher selection rule:

1. Find tasks whose workflow state is dispatchable.
2. Exclude tasks with incomplete dependencies.
3. Exclude tasks with pending approvals.
4. Exclude tasks whose required skills are not active.
5. Exclude inactive or over-quota profiles.
6. Match candidate Agent Profiles by skills, roles, risk threshold, and project membership.
7. Atomically claim a task.
8. Create an Agent Execution row.
9. Spawn the worker with scoped context.
10. Require terminal outcome: complete, block, fail, timeout, or cancelled.

This is where Friday becomes more reliable than prompt-led orchestration.

---

## 10. Phase 1 Implication

Phase 1 does not need every future workflow feature. It does need the foundation that prevents Hermes-style brittleness.

Required for v0.1:

- validated Agent Profile;
- validated Skill;
- Agent Project / Agent Task;
- configurable workflow states, even if the first template is simple;
- Kanban rendered from workflow state;
- dispatcher claiming only dispatchable tasks;
- Execution Log per run;
- task event history;
- basic block / unblock path;
- manual approval for high-risk transitions if present;
- War Room event posting if Raven is included in the selected stack.

Deferred:

- autonomous profile generation;
- autonomous workflow generation;
- autopilot;
- complex memory;
- cross-site agent communication;
- deep Raven fork;
- full ERPNext purchase automation.

---

## 11. Summary

Hermes proves that durable multi-agent Kanban is better than fragile subagent swarms.

The real-world failure proves the missing layer: typed, validated, governable business structure.

Friday's answer is:

> Hermes-style agent coordination rebuilt on Frappe DocTypes, flexible workflows, ERPNext-derived work objects, and Raven War Rooms, where agents execute inside a governed operating model instead of inventing one at runtime.
