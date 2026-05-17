# Friday — An Agentic Framework Built on Frappe, Made in India

> **Tagline:** Enterprise agentic intelligence, powered by a Frappe v16 engine — for Indian growing businesses, by Indian builders.

Friday is an open-source agentic framework that runs on a hard fork of Frappe v16 stable, re-engineering proven agent patterns (Hermes by Nous Research, OpenClaw) into an enterprise application substrate. Agent-native primitives — actor identity, execution trace, governed skill dispatch, sandboxed execution — are built directly into framework core, not bolted on as apps. The goal is enterprise-grade agent governance — role-based permissions, audit trails, sandboxing, structured skill schemas — that today's agent frameworks lack out of the box.

**The mission:** every Indian SMB owner gets a back-office team that never sleeps, runs on their ERPNext, and operates within auditable boundaries.

---

## Document Index

### Foundation (Architecture & Vision)

| # | Document | Purpose |
|---|----------|---------|
| 01 | [Vision & Architecture](./01-vision-and-architecture.md) | High-level vision, design principles, system architecture |
| 02 | [Feature Comparison](./02-feature-comparison.md) | Hermes vs OpenClaw vs Friday — what we keep, replace, and add |
| 03 | [Technical Stack](./03-technical-stack.md) | Frappe, PostgreSQL + pgvector, Redis, Docker — why each choice |
| 04 | [Security Model](./04-security-model.md) | Permissions, isolation, sandboxing, agent profiles |
| 05 | [Module Design](./05-module-design.md) | Proposed DocTypes, gateway internals, dispatcher logic |
| 06 | [Phase One Scope](./06-phase-one-scope.md) | MVP scope, milestones, deliverables |
| 07 | [Legal & Branding](./07-legal-and-branding.md) | GPL v3 / AGPL v3, trademark, open-source strategy |
| 39 | [Friday Framework Strategy](./39-friday-framework-strategy.md) | Framework-first direction: Frappe-derived substrate, Friday-native product feel |

### Implementation Guides (Specification-Driven Development)

Documents that guide any AI coding agent (Claude Code, Cursor, Aider, etc.) through implementing Phase 1.

| # | Document | Purpose |
|---|----------|---------|
| 08 | [Agent Setup Guide](./08-agent-setup-guide.md) | Context sources, environment, conventions, authoritative hierarchy |
| 09 | [Agent Evaluation Guide](./09-agent-evaluation-guide.md) | How the agent decides REUSE / ADAPT / REWRITE for each component |
| 10 | [Agent Execution Guide](./10-agent-execution-guide.md) | Slice-by-slice implementation order with micro-loop discipline |
| 11 | [Agent Validation Checklist](./11-agent-validation-checklist.md) | Concrete checkboxes for completing each slice |

### Refinements & External Inspirations

| # | Document | Purpose |
|---|----------|---------|
| 12 | [Agent Roles and Features Refinement](./12-refinement-agent-roles-and-features.md) | Agent Role Profiles, 7 standard profiles, delegation rules |
| 13 | [Frappe v16 Leverage Strategy](./13-frappe-v16-leverage-strategy.md) | How to use v16 features when available, forward-compatibility |
| 14 | [Integrated Architecture](./14-integrated-architecture.md) | Full integration of Frappe + Raven + ERPNext + Friday Core |
| 15 | [OpenClaw Insights → Friday Refinements](./15-openclaw-insights-friday-refinements.md) | Memory as tools, skill ceilings, heartbeat, LLM-as-policy |
| 16 | [Raven Integration Strategy](./16-raven-integration-strategy.md) | War Room per project, channel auto-creation, Message Actions |

### Launch, GTM, Process

| # | Document | Purpose |
|---|----------|---------|
| 17 | [Open Source Launch Playbook](./17-open-source-launch-playbook.md) | Repository setup, license sequence, community kickoff |
| 18 | [Go-to-Market Strategy](./18-go-to-market-strategy.md) | India-first, FridayLabs SaaS, contributor revenue share |
| 19 | [Phase One Success Metrics](./19-phase-one-success-metrics.md) | KPIs for the governed framework loop and first flagship validation |
| 20 | [Brainstorm Session Tree](./20-brainstorm-session-tree.md) | Visual tree of all ideation branches from design sessions |

### Agent Intelligence

| # | Document | Purpose |
|---|----------|---------|
| 21 | [Auto-Research Integration Strategy](./21-auto-research-integration-strategy.md) | When and how agents trigger research, governance |
| 22 | [Hermes Learning Loop Deep Dive](./22-hermes-learning-loop-deep-dive.md) | Governed learning: Skill Draft + Version + supervisor approval + rollback |
| 23 | [Secrets & Credentials Management](./23-secrets-credentials-management.md) | Credential Profile DocType, one ERPNext user per agent |
| 24 | [Sandbox Architecture Implementation](./24-sandbox-architecture-implementation.md) | Docker hardening, warm pool, egress allowlist |
| 25 | [Domain-Specialized Agent Profiles](./25-domain-specialized-agent-profiles.md) | React Dev, K8s Specialist, PostgreSQL DBA, etc. |

### Framework, Documentation, Learning

| # | Document | Purpose |
|---|----------|---------|
| 26 | [Dynamic Framework Version Management](./26-dynamic-framework-version-management.md) | Skills versioned per framework version; doc injection |
| 27 | [Infrastructure Specialist Sub-Agents](./27-infrastructure-specialist-subagents.md) | K8s, Terraform, Ansible, Docker Compose, Linux specialists + coordinator |
| 28 | [GitHub-Driven Documentation Sync](./28-github-driven-documentation-sync.md) | Monitor GitHub releases, auto-update framework docs |
| 29 | [Domain-Specific Self-Learning](./29-domain-specific-self-learning.md) | Hermes learning loop scoped per domain to prevent contamination |

### Autonomous Operations

| # | Document | Purpose |
|---|----------|---------|
| 30 | [Autonomous Business Operations Architecture](./30-autonomous-business-operations-architecture.md) | ERPNext 6-layer design; Procurement, Sales, Finance, HR, Production agents |
| 31 | [Cache Buffer Management System](./31-cache-buffer-management-system.md) | Redis hot cache, pre-load, invalidation, monitoring |
| 35 | [Autopilot Mode — Autonomous Execution](./35-autopilot-mode-autonomous-execution.md) | Confidence-gated autonomy, demotion, circuit breaker |
| 36 | [Analytical & Predictive Agents](./36-analytical-predictive-agents.md) | Trend, demand forecast, cash flow, performance insights |

### Memory & Knowledge

| # | Document | Purpose |
|---|----------|---------|
| 32 | [Memory Association & Neural Linking](./32-memory-association-neural-linking.md) | Concept graph, association strength, decay |
| 33 | [Knowledge Graph & Wiki Integration](./33-knowledge-graph-wiki-integration.md) | Frappe Wiki as agent knowledge base; decision logs |
| 34 | [Efficient Multi-Layer Memory System](./34-efficient-multilayer-memory-system.md) | Hot/warm/cold tiers; episodic, semantic, procedural, reflective |

### Multi-Site & Performance

| # | Document | Purpose |
|---|----------|---------|
| 37 | [Multi-Site Inter-Agent Communication](./37-multi-site-inter-agent-communication.md) | ACP protocol, partner sites, service discovery, mTLS |
| 38 | [Performance Optimization & Bottleneck Analysis](./38-performance-optimization-bottleneck-analysis.md) | LLM latency, pgvector tuning, warm pool, monitoring |
| 40 | [Gap Analysis & Resolution Plan](./40-gap-analysis-and-resolution-plan.md) | Contradictions, missing decisions, and pre-implementation resolution order |
| 41 | [Porting Strategy: Hermes, ERPNext, Raven](./41-porting-strategy-hermes-erpnext-raven.md) | Real-world Hermes Kanban lessons translated into Friday's workflow, profile, skill, and War Room strategy |
| 42 | [Phase One Authority Contract](./42-phase-one-authority-contract.md) | Single source of truth for Friday v0.1 scope |
| 43 | [Control Room Product Spec](./43-control-room-product-spec.md) | Operator-facing trust UX: live activity, approvals, replay, pause/revoke |
| 44 | [Technical Feasibility Spike](./44-technical-feasibility-spike.md) | Timeboxed stack decisions before Phase 1 implementation |
| 45 | [Fork Policy](./45-fork-policy.md) | Hard fork of Frappe v16: what lives in core, patch discipline, manual upstream policy |

---

## Quick Summary

**What Friday is:**
- An agentic framework running on a hard fork of Frappe v16 stable, made in India
- Re-implements Hermes/OpenClaw patterns inside a governed enterprise substrate
- Framework-first from day one: bench-aware Friday agent commands, Friday Control Room, agent-native primitives
- Turns Hermes-style multi-agent Kanban into flexible Frappe workflows: Kanban is a view, not the workflow
- Permission-first: every action gated through Frappe role matrix BEFORE queueing
- Audit-everything: every decision, escalation, skill call logged
- Multi-agent collaboration via Frappe Projects/Tasks + Raven War Rooms

**What Friday is not:**
- A fork of Hermes or OpenClaw
- A thin "AI app installed on Frappe" with no framework identity
- A proprietary product (open-source under GPL v3, with AGPL v3 under consideration for launch)
- Tied to a single LLM provider (provider-agnostic)
- Built only for tech-savvy users — built for SMB operators

**Core differentiators:**
1. Hermes and OpenClaw treat security as configuration; Friday treats it as a first-class architectural concern, inherited from Frappe's role and permission system.
2. Friday is Indian-built and India-first in design priorities (INR pricing, regional compliance, English + regional language ops).
3. The hosted FridayLabs SaaS splits net revenue with contributors via a transparent, public score (40/30/20/10 split).

**Phase 1 North Star:**
Friday proves the governed framework loop, then uses it for the ERPNext Purchase Order flagship dogfood. The order matters: first profile, skill, permission check, sandboxed execution, logs, task workflow, and Control Room; then PO automation on that foundation. See documents 19, 30, and 42.

---

## How to Read This Documentation

**If you want the vision and why-Friday-exists:** Read 01, 02, 18, 39.

**If you're an engineer implementing Phase 1:** Read 39, 40, 41, 42, 43, 44, and 45 first, then 06, then 08-11 in order, then 14, 24, 30.

**If you're a security reviewer:** Read 04, 23, 24, 37.

**If you're evaluating for adoption:** Read 02, 06, 19, 30, 35.

**If you're building agent profiles or skills:** Read 12, 15, 22, 25, 27.

**If you're tuning performance:** Read 31, 34, 38.

**If you want the full design exploration:** Read everything in numerical order. Document 20 (the Brainstorm Session Tree) is the entry point to the original ideation if you want to understand where each idea came from.

---

## Document Status

All documents in this set are design specifications, not implementation manuals. They describe what Friday should be, how its parts fit together, and what trade-offs were considered. Implementation will inevitably surface details that require revisions; these documents will be updated as design contact with reality refines them.

Documents 39, 40, 41, 42, 43, 44, 45, 06, 11, and 19 are the most operationally precise (framework strategy, gap resolution, porting strategy, Phase 1 authority, Control Room, feasibility spike, fork policy, scope, validation, metrics). Documents 12 onward represent design depth that informs Phase 1 priorities but extends into Phase 2-4 as noted in each.

**Total content:** 45 design documents, ~10,000+ lines of markdown.

---

## Made In India 🇮🇳

Friday is built in India, for Indian growing businesses, by an Indian founder who believes the next great open-source enterprise framework should come from this side of the world. We're standing on the shoulders of Frappe (Mumbai), Raven (The Commit Company), and the global Hermes / OpenClaw communities — and adding the governance, accessibility, and economic alignment that the next chapter requires.
