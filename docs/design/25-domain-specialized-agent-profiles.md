# 25 — Domain-Specialised Agent Profiles

> **Purpose:** Move from generic agent profiles (Full-Stack Developer, DevOps Engineer) to narrow domain experts (React Developer, Kubernetes Specialist, PostgreSQL DBA). Specialised agents waste fewer tokens, execute faster, and produce higher-quality work because their context is focused.

This document refines doc 12 (Agent Role Profiles) and complements docs 26 (Dynamic Framework Versions) and 27 (Infrastructure Specialist Sub-Agents).

---

## 1. Why Specialisation Matters

A generic Full-Stack Developer agent has to **discover** which framework it's working in, which version is in use, what conventions the codebase follows. That discovery burns tokens and time, and produces mediocre output because the agent's training data is averaged across many ecosystems.

A React Developer agent **starts** with React-specific context: hooks, JSX patterns, current React 19 conventions, common pitfalls. No discovery. Focused execution. Better output.

The same logic applies across every domain:

| Generic Profile | Specialised Equivalents |
|---|---|
| Full-Stack Developer | React Dev, Vue Dev, Svelte Dev, Django Dev, FastAPI Dev |
| DBA | PostgreSQL DBA, MySQL DBA, MongoDB Engineer, ClickHouse Engineer |
| DevOps | Kubernetes Specialist, Terraform Specialist, Ansible Specialist, Docker Compose Specialist, AWS Specialist, GCP Specialist |
| Data Engineer | Airflow Engineer, dbt Engineer, Spark Engineer, Snowflake Specialist |
| Tester | E2E Test Author (Playwright), Unit Test Author (pytest/jest), Load Test Engineer (k6/Locust) |
| Writer | Technical Writer, Marketing Copywriter, Release-Notes Author |

---

## 2. Specialisation Mechanics

A specialised Agent Role Profile differs from a generic one in four ways:

### 2.1 Narrow skill set
Instead of all "development" skills, only the skills relevant to the domain are permitted. A React Developer doesn't have access to `query_database` skills; that's the DBA's job. This isn't just permission, it's **focus** — the LLM's prompt is shorter and more coherent.

### 2.2 Domain-tuned system prompt
The Agent Role Profile carries a `domain_system_prompt` field — a domain-specific addendum to the base system prompt. Example for React Developer:

```
You are a React developer specialising in React 19 with TypeScript.
Conventions:
- Functional components only; class components are legacy.
- Prefer Server Components when running on Next.js 15+; mark client components with "use client" directive.
- State: useState for local; useReducer for complex; Context API for cross-tree; Zustand or Redux Toolkit for global.
- Side effects: useEffect with explicit dependency arrays; no missing deps.
- Suspense and ErrorBoundary patterns expected for async UI.
- Accessibility (ARIA, keyboard nav) is not optional.
- Styling: Tailwind preferred unless project uses CSS-in-JS or modules.
```

### 2.3 Domain-tuned knowledge bundle
A reference of current, curated knowledge available to the agent via tools, not auto-injected (per OpenClaw insight, doc 15). The bundle is updated as the framework evolves (see doc 28 GitHub-driven doc sync).

### 2.4 Domain-tuned learning loop
The autonomous curator (doc 22) operates within domain scope. A React Developer's learning improves React skills; it doesn't pollute the broader skill library.

---

## 3. Agent Role Profile Extensions

Building on doc 12, add fields:

| Field | Type | Notes |
|---|---|---|
| `domain` | Link → Domain | The specialisation area |
| `domain_system_prompt` | Long Text | Domain-specific prompt addendum |
| `knowledge_bundle` | Link → Knowledge Bundle (doc 33) | Curated docs for this domain |
| `framework_versions` | Table | Pinned framework versions (e.g. React=19, TS=5.4) |
| `parent_generic_profile` | Link → Agent Role Profile (nullable) | If this is a specialised child of a generic profile, for fallback |

### Domain DocType (new)

| Field | Type |
|---|---|
| `domain_code` | Data (unique) | e.g. `react`, `kubernetes`, `postgresql` |
| `display_name` | Data |
| `category` | Select | Frontend / Backend / Database / Infra / Data / Testing / Writing |
| `description` | Text |
| `current_stable_version` | Data |
| `documentation_sources` | Table | URLs Friday monitors for updates (see doc 28) |

---

## 4. Coordinator Pattern

Specialised agents are too narrow to handle full features. A coordinator routes work:

```
Operator: "Build a React component with a PostgreSQL-backed API endpoint and Kubernetes deployment."

Coordinator Agent receives the request.
  ├─ Decomposes: UI / API / DB / Deploy
  ├─ Delegates UI work → React Developer
  ├─ Delegates API work → FastAPI Developer
  ├─ Delegates DB schema → PostgreSQL DBA
  └─ Delegates deployment → Kubernetes Specialist

Each specialist works in parallel where possible, sequentially where dependent.
Coordinator integrates results and reports back.
```

The Coordinator profile has:
- Broad context (knows the high-level shape of full-stack work)
- No execution skills of its own
- Delegation rights to many specialist profiles (per `can_delegate_to`)
- A skill `decompose_and_route` that uses the LLM to plan the breakdown

Why this works: the LLM excels at planning when given clear options. Coordinators provide the planning context; specialists provide the execution depth.

---

## 5. Standard Specialised Profiles (Ship with Friday)

Initial set, contributable later:

### Frontend
- `frontend.react` — React 19 + TypeScript
- `frontend.vue` — Vue 3 + TypeScript
- `frontend.next` — Next.js 15 + App Router
- `frontend.tailwind` — Styling-focused

### Backend
- `backend.fastapi` — FastAPI + Pydantic
- `backend.django` — Django 5
- `backend.frappe` — Frappe Framework app development
- `backend.node` — Node.js + TypeScript

### Database
- `db.postgresql` — PostgreSQL 16, pgvector
- `db.mysql` — MySQL 8
- `db.mongodb` — MongoDB 7

### Infrastructure (see doc 27 for the sub-agent pattern)
- `infra.kubernetes` — K8s 1.30+
- `infra.terraform` — Terraform 1.8+
- `infra.ansible` — Ansible 10
- `infra.docker-compose` — Compose v2

### Cloud
- `cloud.aws` — AWS Solutions Architect Associate-level
- `cloud.gcp` — GCP equivalent
- `cloud.azure` — Azure equivalent

### Testing
- `test.playwright` — E2E testing
- `test.pytest` — Python unit testing
- `test.k6` — Load testing

### Writing
- `write.technical` — Technical documentation
- `write.marketing` — Marketing copy
- `write.release-notes` — Release notes

### Coordinator
- `coordinator.fullstack` — Decomposes full-stack work
- `coordinator.devops` — Decomposes infrastructure work
- `coordinator.research` — Decomposes research projects (doc 21)

Each ships with a tested system prompt, a starter knowledge bundle, and explicit `can_delegate_to` for coordinators.

---

## 6. Knowledge Bundle Lifecycle

Each specialised profile has a Knowledge Bundle (doc 33) — curated reference material kept current via doc 28 (GitHub-driven sync).

Bundle contents for `frontend.react`:
- Current React major-version reference (auto-updated from React docs)
- Current TypeScript reference
- Top 50 React patterns (with examples) — curated, versioned
- Common pitfalls list — community-contributed
- Migration guides between recent versions

Bundles are **versioned**. When React 20 ships, the bundle gets a new version; existing React 19 projects pin to the older bundle until ready to migrate.

---

## 7. Cross-Specialisation Coordination

Specialists must speak the same language at boundaries. Friday enforces this via **interface contracts**:

```
React Developer produces a component that calls an API.
  → Contract: OpenAPI schema for the API endpoint, supplied by the Coordinator
  → React Developer generates the client code matching the schema
  → FastAPI Developer implements the endpoint matching the same schema
  → Coordinator verifies both sides match
```

Contracts are shared in the War Room. Mismatches surface as Issues, blocking task completion.

---

## 8. When Generic Profiles Are Appropriate

Specialisation isn't always better:
- **Exploratory tasks** where the framework isn't known yet → generic profile
- **Trivial tasks** (write a script to count lines) → generic is fine
- **Cross-cutting concerns** (project setup, README writing) → generic
- **Small teams** with limited skill variety → generic may suffice

Friday defaults to generic profiles for new installations. Operators specialise as their workload demands.

---

## 9. Performance Implications

Empirical expectation (to be validated in Phase 2):
- Specialised React Developer agent uses **30–60% fewer tokens** per task vs. generic Full-Stack agent
- Specialised agent's task completion rate **20–40% higher**
- Specialised agent's response time **2–4× faster** on framework-specific questions

The cost trade: more profiles to maintain. Mitigated by:
- Ship a strong default set (§5)
- Knowledge bundles auto-update (doc 28)
- Community contributes new profiles

---

## 10. Phasing

| Phase | Specialisation Scope |
|---|---|
| 1 (MVP) | Generic profiles only (per doc 12) |
| 2 | Specialised profiles for `frontend.react`, `backend.fastapi`, `infra.kubernetes`, `db.postgresql` (the most common stack) |
| 3 | Full standard set (§5) |
| 4 | Community-contributed profiles via Skills Marketplace |

---

## 11. Engineering TODOs

- [ ] Knowledge Bundle storage and versioning — extend doc 33 with version semantics
- [ ] Token-budget accounting per profile — empirically validate the efficiency claim
- [ ] Coordinator decomposition skill: how to teach an LLM to break down work cleanly without over-specifying
- [ ] Conflict resolution between specialists who disagree (e.g. React Dev says use Server Components, Next.js Dev says client components — escalate to architect coordinator?)
- [ ] Bundle update cadence — how aggressively to pull from upstream sources without breaking pinned projects

---

## 12. Open Questions

- **How many specialised profiles is too many?** A library of 200 niche profiles becomes harder to navigate than a library of 20 well-tuned ones. We start with §5's ~25 and let usage data guide expansion.
- **Should specialised profiles auto-fall-back to parents?** If a React Developer is asked something React-adjacent (e.g. browser performance), should it delegate to a Frontend Generalist? Probably yes via `parent_generic_profile`.
- **How do specialists handle deprecation?** When React 19 reaches end-of-life, what happens to projects still pinned to it? Mark the bundle as `legacy`, require operator opt-in, surface migration prompts.
