# 29. Domain-Specific Self-Learning

## The Problem with Global Learning

If every agent learns from every other agent's execution, knowledge contaminates across domains. A pattern that works for "send email follow-up" should not bleed into "approve purchase orders." A skill that fits a React frontend project should not surface for a Kubernetes infrastructure task.

We scope the learning loop (doc 22) **per domain** so each domain becomes its own specialist over time.

## What is a Domain?

A Domain in Friday is a tag attached to:
- Agent Role Profiles
- Skills
- Agent Projects
- Memory entries
- Skill Drafts

Standard domains shipped in Phase 1:
- `erpnext-procurement`
- `erpnext-sales`
- `erpnext-finance`
- `erpnext-hr`
- `erpnext-production`
- `erpnext-inventory`
- `frontend-react`
- `infra-kubernetes`
- `infra-terraform`
- `db-postgres`
- `general`

Custom domains can be created by supervisors with appropriate permissions.

## DocType: Domain

Fields:
- `domain_name` (Data, unique)
- `description` (Text)
- `parent_domain` (Link to Domain) — supports hierarchy, e.g. `erpnext-procurement` is child of `erpnext`
- `enabled` (Check)
- `governance_supervisor` (Link to User) — who approves Skill Drafts in this domain
- `learning_loop_active` (Check) — whether the loop is on for this domain (Phase 1: all off)
- `success_threshold_for_autopilot` (Float, default 0.95) — see doc 35
- `min_samples_for_promotion` (Int, default 20) — see below

## Scoped Learning Loop

When an Execution Log completes successfully, the curator (doc 22) considers it for skill promotion:

1. **Identify domain** of the execution from the Agent Role Profile.
2. **Cluster similar executions within that domain** using embeddings of (task description + skill called + outcome).
3. If a cluster has ≥ `min_samples_for_promotion` executions with ≥90% success, propose a Skill Draft scoped to that domain.
4. The draft is only visible to supervisors of that domain.
5. Approval is required from the `governance_supervisor` of that specific domain.

A pattern proven in `erpnext-procurement` does not auto-propagate to `erpnext-sales`, even if the underlying logic looks similar. If we want it shared, a supervisor explicitly promotes it (see "Cross-Domain Promotion" below).

## Memory Scoping

Memory entries (doc 32, 34) carry a `domain` field. The `memory_search` skill defaults to filtering by the calling agent's domain. Cross-domain queries require an explicit `include_domains` parameter and may require approval based on memory sensitivity.

This protects against accidental data leakage: an `erpnext-finance` agent doesn't surface customer purchase patterns to an `infra-kubernetes` agent.

## Skill Resolution Within Domain

When the dispatcher resolves skills for a task:

1. First pass: filter skills tagged with the project's domain.
2. Second pass: include skills tagged `general` (cross-domain utilities like `memory_search`, `time_query`).
3. Third pass (only if first two return nothing): consider skills from sibling domains under the same parent.

This produces tight, focused skill sets per agent execution — supporting the OpenClaw skill-ceiling guidance (doc 15).

## Cross-Domain Promotion

Sometimes a pattern really does belong everywhere. Example: a "validate ISO date format" skill discovered in `erpnext-procurement` is genuinely general.

Promotion flow:
1. Domain supervisor flags a Skill Version with "Propose for cross-domain promotion."
2. A meta-supervisor (default: Friday admin) reviews.
3. Promotion creates a new Skill record tagged `general` with a copy of the implementation.
4. Original domain-scoped skill remains; it may be marked Superseded by the general version after a stability window.
5. Audit trail records the promotion source.

Promotion is never automatic. The friction is intentional to prevent contamination.

## Domain Specialisation Metrics

Each Domain tracks:
- `total_executions` (Int)
- `success_rate` (Float, rolling 30 days)
- `avg_task_duration` (Duration, rolling 30 days)
- `unique_skill_count` (Int)
- `skill_promotion_rate` (Float) — drafts approved / drafts created
- `human_intervention_rate` (Float) — escalations per 100 executions

These metrics show whether a domain is "maturing" (intervention rate falling, success rate rising) or "regressing" (rates worsening).

Supervisors review domain metrics weekly in a Raven `#domain-health` channel.

## Domain-Scoped Auto-Research

When an agent encounters an unknown pattern, it may trigger auto-research (doc 21). Research results are stored as memory entries scoped to the domain — preventing a research note about K8s networking from polluting the procurement agent's memory.

## Phase 1 vs Phase 2

Phase 1:
- Domain DocType
- Domain tags on Skills, Profiles, Memory, Projects
- Memory and skill resolution filtered by domain
- Manual skill authoring per domain (no learning loop yet)

Phase 2:
- Curator scoped per domain
- Skill Draft + Skill Version per domain
- Domain metrics dashboard
- Cross-domain promotion workflow

Phase 3:
- Sub-domains nested deeper (e.g. `erpnext-procurement-import` vs `erpnext-procurement-local`)
- Domain-specific evaluation harnesses
- Domain-level performance budgets

## Domain Naming Discipline

Rules for adding domains:
1. Domain names use kebab-case with at most two segments.
2. No more than 20 active domains in Phase 1 (avoid fragmentation).
3. A domain must have at least one Agent Role Profile and one Skill before being created.
4. Adding a new domain requires admin approval via War Room.

This discipline prevents domain proliferation that would defeat the specialisation goal.

## Edge Case: Multi-Domain Projects

Some Agent Projects span domains (e.g. "Build an internal ops dashboard" needs frontend-react + erpnext-finance). The project's `domains` field is a child table, not a single Link.

When an Agent Task is created inside such a project, the supervisor (or System Manager Agent) assigns the task a primary domain. Skill resolution and memory access scope to that primary domain. If the task needs cross-domain skills, it must split into sub-tasks, each with its own primary domain.

This forces clarity at task boundaries instead of producing confused agents juggling multiple contexts.

## Open Questions

1. Should `governance_supervisor` be a role (so backup is automatic) or a single user (so accountability is clear)? Lean: role with primary + backup field.
2. How to migrate skills between domains when boundaries shift? Migration tool with audit trail in Phase 2.
3. What about cross-tenant domain sharing in the SaaS edition (doc 18)? Each tenant has private domains by default; opt-in to shared community domain library.
