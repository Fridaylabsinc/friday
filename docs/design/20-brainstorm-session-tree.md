# 20 — Brainstorm Session Tree

> **Purpose:** Map the ideation flow of the entire Friday brainstorming session as a visual tree. Captures how ideas branched, evolved, and locked into the architecture. Later usable as input for graph visualisations of the conceptual lineage.

This is a snapshot of the conversation that produced documents 01–38. Not exhaustive transcription — a structural map.

---

## Root

```
FRIDAY
  └─ "Agentic framework, inspired by Hermes Agent and OpenClaw,
      powered by Frappe Framework, governed for the enterprise"
```

---

## Branch 1 — Foundation

```
1. SEED IDEA
   └─ Take Hermes Agent's gateway/agent loop
      └─ Decouple from its backend
         └─ Re-engineer on Frappe Framework
            └─ Inherit Frappe's CMS-like robustness:
               role-based permissions, PostgreSQL/MySQL,
               Redis, workers, notifications, integrations

2. RESEARCH PHASE
   ├─ What is Frappe Framework?
   │  └─ Full-stack, batteries-included, Python+JS, MariaDB-default
   │     └─ Document-centric (DocTypes), low-code, GPL v3
   │
   ├─ How does Hermes Agent work?
   │  ├─ Three-layer: Connectors → Gateway → Agent Runtime
   │  ├─ Skills as markdown files (progressive disclosure L0/L1/L2)
   │  ├─ Sessions like OS processes
   │  ├─ Tool registry (built-in + MCP + LSP)
   │  └─ Cron + Memory + Configuration files (USER/SOUL/AGENTS/TOOLS.md)
   │
   └─ Security issues in both Hermes and OpenClaw
      ├─ Hermes: allow-all default, WeChat path traversal, memory poisoning
      └─ OpenClaw: 512 vulnerabilities, prompt injection, token exfiltration
         └─ INSIGHT: governance is the gap. That's Friday's moat.
```

---

## Branch 2 — Architecture Layers Lock In

```
3. PERMISSION-FIRST DESIGN
   └─ Use Frappe's role-based permission system
      └─ Agent Profile linked to a Frappe User
         └─ Roles cascade through to skill execution
            └─ Permission check at the gateway, BEFORE queueing
               └─ Every decision logged to Permission Decision Log

4. ISOLATION
   └─ Docker container per agent execution
      ├─ Scoped credentials (short-lived API tokens)
      ├─ Network namespace + allowlist
      ├─ Resource caps via cgroups
      └─ Frappe REST API as the security boundary

5. INTER-AGENT COMMUNICATION
   └─ Redis pubsub + Gateway permission check
      └─ Agents never call each other directly
         └─ Delegation Request DocType tracks every cross-agent call

6. DATA LAYER DECISIONS
   ├─ PostgreSQL over MariaDB (pgvector, better JSON, FTS)
   ├─ Redis for cache, queues, real-time pubsub
   ├─ pgvector for semantic memory
   └─ Docker for sandbox
```

---

## Branch 3 — Integration Stack Emerges

```
7. RAVEN DISCOVERED
   └─ Open-source Slack-like, built on Frappe
      └─ Channels = War Rooms (one per Agent Project)
         ├─ Message Actions → trigger Friday workflows
         ├─ Document sharing with embedded previews
         ├─ Custom emoji as status indicators
         └─ Timeline integration for audit

8. ERPNext PROJECT/TASK/ISSUE PORTED
   └─ Don't depend on ERPNext, port the DocTypes
      ├─ Agent Project (from ERPNext Project)
      ├─ Agent Task (from ERPNext Task) + assigned_to_profile, required_skills
      └─ Agent Issue (from ERPNext Issue) for blockers
         └─ Native Frappe Workflow + Kanban view replaces Hermes fixed Kanban

9. FOUR LAYERS LOCKED
   ├─ Frappe Framework (foundation)
   ├─ Raven (collaboration)
   ├─ Ported ERPNext Project/Task/Issue (orchestration)
   └─ Friday Core (gateway, skills, dispatcher, isolation) — new code
```

```
9A. REAL-WORLD HERMES KANBAN FAILURE
    └─ Asked Hermes to create profiles, board, and tasks
       ├─ Basic bounded tasks worked
       ├─ Multi-agent setup repeatedly failed
       ├─ Profiles and skills were wrongly built
       ├─ Fixed columns did not match real business workflows
       └─ INSIGHT: agents should not improvise the operating model;
          they should operate inside typed, validated, governable DocTypes
```

---

## Branch 4 — Agent Governance Deepens

```
10. AGENT ROLE PROFILES
    └─ Pre-provisioned bundles of (roles + skills + quota + approval threshold)
       ├─ Ship 7 standard profiles (task_worker, data_processor, qa,
       │  supervisor_agent, integration_agent, dev_agent, read_only_agent)
       ├─ Multi-agent hierarchy via can_delegate_to / can_escalate_to
       └─ Permission inheritance with invariant: child ⊆ parent

11. DELEGATION & ESCALATION
    ├─ Delegation Request DocType (peer/downward)
    ├─ Escalation DocType (upward when stuck)
    └─ War Room as fallback escalation surface

12. SECRETS MANAGEMENT
    └─ Frappe Password field + Vault integration
       ├─ Masked in logs and War Room
       ├─ Short-lived scoped tokens to containers
       └─ Per-agent access audited
```

---

## Branch 5 — OpenClaw Insights

```
13. ALEX KRENTSEL'S TALK (UC Berkeley, March 2026)
    ├─ Three-layer architecture confirmed
    ├─ Heartbeat session pattern (every 30min self-check)
    ├─ Memory as TOOLS, not context injection — FLIP THE DESIGN
    ├─ Skill ceiling: 150 max, 30k chars max, intelligent filter
    ├─ Auto-configuration via BOOTSTRAP conversation
    └─ LLM-as-policy — don't over-prescribe architecture
```

---

## Branch 6 — Specialised Intelligence

```
14. DOMAIN-SPECIALISED AGENTS
    └─ Not "Full Stack Developer" generic
       └─ React Developer, Database Engineer, DevOps, Security
          (token-efficient via narrow expertise)

15. DYNAMIC FRAMEWORK VERSIONING
    └─ Skills versioned per framework version
       ├─ React 19 ≠ React 17
       └─ Latest doc injection on task assignment

16. INFRASTRUCTURE SPECIALIST SUB-AGENTS
    ├─ Kubernetes specialist
    ├─ Terraform specialist
    ├─ Docker Compose specialist
    ├─ Ansible specialist
    └─ Coordinator routes to the right specialist

17. GITHUB-DRIVEN DOC SYNC
    └─ User specifies GitHub release URLs
       └─ System fetches, parses markdown, generates skill updates
          └─ Auto-promotion through Skill Draft → Active

18. DOMAIN-SPECIFIC SELF-LEARNING
    └─ Hermes learning loop, scoped per domain
       └─ Kubernetes specialist learns K8s patterns
          └─ Cross-agent sharing of validated learnings
```

---

## Branch 7 — Autonomy & Memory

```
19. AUTONOMOUS BUSINESS OPS (ERPNext)
    └─ 6-layer architecture
       ├─ L1 Data integration (REST API to ERPNext)
       ├─ L2 Domain agents (Procurement, Sales, Finance, HR, Production)
       ├─ L3 Decision rules (configurable thresholds)
       ├─ L4 Approval gates (Workflow Request)
       ├─ L5 Audit & compliance
       └─ L6 Learning loop
          └─ One ERPNext user PER agent (audit trail by agent identity)
             └─ System Manager Agent bootstraps other agent users

20. CACHE BUFFER MANAGEMENT
    └─ Optional, configurable per project
       ├─ Pre-load suppliers, customers, items, pricing into Redis
       └─ TTL-based, agent queries cache first

21. MEMORY ARCHITECTURE
    ├─ Multi-layer: hot (Redis) / warm (PostgreSQL) / cold (archive)
    ├─ Semantic via pgvector + FTS hybrid
    ├─ Memory as TOOLS not context (per OpenClaw insight)
    └─ Compression for old memories (summarise, keep embedding)

22. NEURAL LINKING / MEMORY ASSOCIATION
    └─ Concepts tagged; cross-concept association tracked
       └─ "Surveillance" + "Automation" auto-link
          └─ Query one, surface related memories

23. KNOWLEDGE GRAPH / WIKI INTEGRATION
    └─ Frappe Wiki hosts curated domain knowledge
       └─ Agents query as a reasoning aid
          └─ Updated as agents learn (with human approval)
```

---

## Branch 8 — Operations & Scale

```
24. SANDBOX ARCHITECTURE
    └─ Container lifecycle: spawn, scope, execute, teardown
       ├─ Pre-warmed pool to amortise startup
       ├─ Network namespace + allowlist
       └─ Cleanup verification

25. AUTOPILOT MODE
    └─ Confidence-gated autonomous execution
       ├─ Build confidence through observed runs
       ├─ Above threshold (95% success): autopilot for that task type
       ├─ Exception → pause + escalate to War Room
       └─ Always-on monitoring and rollback

26. ANALYTICAL & PREDICTIVE AGENTS
    └─ Beyond operational agents
       ├─ Forecast demand
       ├─ Optimise supply chain
       └─ Need ML models, real-time data, optimisation algorithms

27. MULTI-SITE INTER-AGENT COMMUNICATION
    └─ Agent-to-Agent Protocol (ACP) extended cross-site
       ├─ Service discovery (DNS / registry)
       ├─ WebSocket / Redis Streams transport
       ├─ Mutual TLS authentication
       └─ Cross-site permission verification

28. PERFORMANCE OPTIMISATION
    ├─ pgvector indexes (IVFFlat, HNSW)
    ├─ Permission cache tuning
    ├─ Container pool to amortise Docker startup
    ├─ Batched LLM calls
    └─ Distributed tracing across gateway → RQ → container
```

---

## Branch 9 — Sustainability

```
29. OPEN-SOURCE LAUNCH PLAYBOOK
    ├─ Repo hygiene (LICENSE, CONTRIBUTING, SECURITY, CoC)
    ├─ CI/CD pipelines
    ├─ Documentation site
    ├─ Launch sequence (T-30, T-14, T-7, T-0)
    └─ T+90 success criteria

30. GO-TO-MARKET — INDIA-FIRST, MADE-IN-INDIA
    ├─ Target: Indian SMBs on ERPNext
    ├─ Positioning vs UiPath, LangChain, OpenClaw, vanilla ERPNext
    ├─ Phasing: build → quiet release → public launch → growth
    └─ Mission: open-source, governed, India-first

31. FRIDAYLABS (separate project, Phase 4)
    └─ Hosted/managed Friday
       ├─ Subscription tiers (Starter / Growth / Enterprise)
       ├─ Indian-hosted infrastructure
       └─ One-click export to self-hosted

32. CONTRIBUTOR REVENUE SHARE
    └─ FridayLabs net revenue distributed:
       ├─ 40% operations + reserves
       ├─ 30% core maintainers
       ├─ 20% broader contributors
       └─ 10% community fund
          └─ Distribution based on contribution score
             └─ Public, auditable, annually-reviewed
```

---

## Branch 10 — Future / Deferred

```
33. FUTURE USE CASES (parked, not Phase 1)
    ├─ Campus surveillance / vision-based monitoring
    ├─ Wiki + LLM knowledge segregation
    ├─ Software development workflow automation
    ├─ Healthcare patient intake
    ├─ Legal contract review
    └─ Customer service ticket triage

34. PHASE 1 FLAGSHIP BUSINESS VALIDATION
    └─ Autonomous ERPNext PO workflow, end-to-end, one week, zero unsafe actions
       └─ Runs after the governed framework loop is proven, not removed from Phase 1
```

---

## Cross-Cutting Concerns Identified

```
DECISION INVARIANTS (apply across all branches)
├─ Permission-first (every action gated through Frappe roles)
├─ Audit by default (every decision a submittable DocType)
├─ No external vector DB (pgvector inside Postgres)
├─ Dual-storage Skills (DocType authoritative for governance, file for portability)
├─ Human-in-the-loop at critical junctures (approvals, escalations, skill changes)
├─ Kanban is a view, not the workflow
├─ Agents may propose operating-model changes, but validation/approval activates them
└─ Open-source GPL v3 / AGPL v3 — no proprietary trap doors

ENGINEERING TODOs FLAGGED (deferred to Phase 1 design spikes)
├─ Skill DocType ↔ file sync conflict resolution
├─ Skill cache: file-vs-DocType source of truth on hot path
├─ War Room channel archive/retention semantics
├─ Concurrent Raven message + Execution Log writes
├─ Fine-grained Message Action permissions in Raven
├─ Agent Role Profile vs Frappe Role Profile inheritance
└─ ERPNext port: which fields to drop, which to keep
```

---

## How to Use This Tree

1. **Onboarding new contributors:** read root to leaves to follow how each major decision was reached.
2. **Architecture review:** any new feature proposal should attach to a branch and respect the decision invariants.
3. **Visualisation:** the indentation maps to a tree; can be rendered as Mermaid, D2, or a force-directed graph by parsing the structure.
4. **Roadmap input:** Phase 1 = Branches 2, 3, 4, plus the Tier 1 metric in doc 19. Branches 5–10 are Phase 2+.

---

## Snapshot Date

This tree reflects the brainstorm session ending in May 2026, producing documents 01–38. Future ideation should extend rather than rewrite this tree.
