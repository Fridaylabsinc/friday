# Agentic Workflow — 01 Setup Guide

> **Purpose:** Prepare any agentic coding framework (Claude Code, OpenClaw, Cursor, Aider, etc.) with the context, sources, and environment needed to implement Friday Phase One.

This document is **framework-agnostic**. The instructions assume an agent capable of reading remote repositories, understanding multi-file specifications, writing code, and executing shell commands in a sandboxed development environment.

---

## 1. Agent Context Sources

Before writing any code, the agent must ingest the following sources, **in this order**:

### 1.1 Friday Specification Documents (primary, authoritative)

These define **what** Friday is and **what** Phase One must deliver. Load all of them:

| Document | Path | Purpose |
|---|---|---|
| Vision & Architecture | `00-README.md`, `01-vision-and-architecture.md` | High-level intent and system design |
| Feature Comparison | `02-feature-comparison.md` | Hermes → Friday capability map |
| Technical Stack | `03-technical-stack.md` | Required tech and rationale |
| Security Model | `04-security-model.md` | Permission and isolation requirements |
| Module Design | `05-module-design.md` | App layout, DocTypes, gateway internals |
| Phase One Scope | `06-phase-one-scope.md` | What to build now, what to defer |
| Legal & Branding | `07-legal-and-branding.md` | License headers, naming |
| Friday Framework Strategy | `39-friday-framework-strategy.md` | Framework-first direction, fork discipline, product feel |
| Porting Strategy | `41-porting-strategy-hermes-erpnext-raven.md` | Hermes Kanban lessons, flexible workflow, Raven/ERPNext boundaries |
| Phase One Authority Contract | `42-phase-one-authority-contract.md` | Single source of truth for v0.1 scope |

**Rule:** If anything in any other source contradicts these documents, the Friday specs win.

### 1.2 Hermes Agent Source Code (reference, selective)

The agent should have **read-only** access to the Hermes Agent repository:

- **Repository:** `https://github.com/NousResearch/hermes-agent`
- **Branch:** `main`
- **License:** Verify on first access; assume copyleft-compatible.

The agent uses Hermes as a **reference implementation**, not as code to copy verbatim. See the Evaluation Guide for criteria on what's reusable vs. what must be rewritten.

Key Hermes directories to study:

| Hermes Path | What to Learn From It |
|---|---|
| `gateway/run.py` | GatewayRunner lifecycle, session caching |
| `agent/run_agent.py` | AIAgent loop, tool execution, retries |
| `agent/prompt_builder.py` | System prompt assembly |
| `skills/` | Skill manifest format, progressive disclosure |
| `gateway/platforms/` | Platform adapter pattern |
| `agent/tools/` | Tool registry, MCP integration |
| `hermes_cli/commands.py` | Slash command resolution |
| `gateway/builtin_hooks/` | Lifecycle hooks |
| `kanban/` (if present) | Multi-agent dispatcher |
| `AGENTS.md`, `SECURITY.md` | Design rules and security boundaries |

### 1.3 Frappe Framework Documentation

- **Main docs:** `https://docs.frappe.io/framework`
- **DocType guide:** `https://docs.frappe.io/framework/user/en/basics/doctypes`
- **Permissions:** `https://docs.frappe.io/framework/user/en/permissions`
- **Hooks:** `https://docs.frappe.io/framework/user/en/python-api/hooks`
- **Background jobs:** `https://docs.frappe.io/framework/user/en/background_jobs`
- **Workflow:** `https://docs.frappe.io/framework/user/en/workflows`
- **DeepWiki (deep code reference):** `https://deepwiki.com/frappe/frappe`

### 1.4 OpenClaw (anti-pattern reference)

- **Repository:** `https://github.com/openclaw/openclaw` (read-only, for what *not* to do regarding default-permissive security).
- Use only as a contrast case in design decisions. Do not copy code.

---

## 2. Development Environment Requirements

The agent must verify or set up the following before any code is written:

### 2.1 System Prerequisites

```
Python:        3.11 or higher
Node.js:       18 LTS or higher
PostgreSQL:    15 or higher with pgvector extension
Redis:         7 or higher
Docker:        24 or higher with running daemon
Git:           2.40 or higher
```

### 2.2 Frappe Bench

```bash
pip install frappe-bench
bench init friday-bench --frappe-branch version-16 --python python3.11 --db-type postgres
cd friday-bench
bench new-site friday.localhost --db-type postgres --admin-password [secure]
bench --site friday.localhost set-config developer_mode 1
```

### 2.3 PostgreSQL Extensions

```sql
-- Run on the Friday site database as superuser
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- for fuzzy search
```

### 2.4 Friday Framework Scaffold

```bash
# Start from the selected Frappe source substrate.
# Keep Frappe internals close to upstream unless a deliberate Friday core patch is needed.
# Add the Friday Agent Kernel modules and Friday-facing agent commands/workspace defaults.
# Do not remove bench; bench remains the operational CLI for site/app lifecycle.
```

### 2.5 Project Repository

```
friday/                                  ← Friday framework repo
├── framework/                           ← Frappe-derived substrate, if split from app modules
├── LICENSE                              ← GPL v3 (full text)
├── README.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── NOTICE
├── CHANGELOG.md
├── pyproject.toml
├── .pre-commit-config.yaml
├── .github/
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   └── design/
├── tests/
└── friday/                              ← Friday Agent Kernel and framework modules
```

---

## 3. Code Conventions

The agent must follow these conventions for **all** generated code:

### 3.1 Python

- Python 3.11+, type-hinted where reasonable
- `black` formatter (line length 100)
- `ruff` linter
- `mypy` for type checking on `friday/permissions/`, `friday/gateway/` (strictest modules)
- Docstrings: Google style
- All public functions must have docstrings
- All DocType controllers inherit from `frappe.model.document.Document`

### 3.2 File Headers

Every Python file begins with:

```python
# Copyright (c) [year] Friday contributors
# Licensed under GNU GPL v3 or later. See LICENSE.
```

### 3.3 DocType Naming

- DocType names: Title Case with spaces (`Agent Profile`, `Skill`)
- Python class names: PascalCase (`AgentProfile`, `Skill`)
- DocType folder names: snake_case (`agent_profile/`, `skill/`)
- Field names: snake_case (`assigned_roles`, `risk_level`)

### 3.4 Module Boundaries

- No cross-module imports except through clearly defined interfaces in each module's `__init__.py`.
- Permission checks always go through `friday.permissions.matrix`, never inline.
- Database access always through Frappe ORM (`frappe.db`, `frappe.get_doc`), never raw SQL except for pgvector queries that must use parameterised raw SQL via `frappe.db.sql`.

### 3.5 Testing

- Every module has a `tests/` subdirectory.
- Use `pytest` and `frappe.tests.utils.FrappeTestCase`.
- Permission engine: **80% line coverage minimum**.
- Gateway and dispatcher: integration tests required.

---

## 4. Authoritative Hierarchy

When the agent encounters a conflict or ambiguity, resolve in this order:

1. Friday authority documents (`39`, `41`, `42`), then core specs (`01`–`07`)
2. Frappe Framework conventions (DocType API, hooks, permissions)
3. Hermes Agent patterns (architectural guidance only)
4. General Python / web best practices

The agent should **never** silently choose a pattern that contradicts the Friday specs. If the specs are ambiguous, the agent flags it for human review rather than guessing.

---

## 5. Tooling the Agent May Use

| Tool | Use For |
|---|---|
| `bench` CLI | Site, app, migration, build operations |
| `bench execute` | Running Python functions in site context for testing |
| `bench console` | Interactive Python in site context |
| Git | All version control |
| Docker | Building and running isolated agent containers |
| `pytest` | All test execution |
| `pre-commit` | Run before any commit |
| `psql` | Direct PostgreSQL inspection (read-only preferred) |
| `redis-cli` | Inspecting cache and pubsub state |

The agent **may not**:

- Disable security features to make development easier
- Skip permission checks "temporarily"
- Hard-code credentials anywhere, including in tests (use `.env.test` patterns)
- Push to a public remote without explicit human approval
- Modify Frappe Framework source code (only override via hooks)

---

## 6. Communication Format

When the agent reports progress, it uses this structure:

```
## Milestone: [name]

### Completed
- [bullet list of done items, with file paths]

### In Progress
- [what's being worked on now]

### Blockers / Questions for Human
- [explicit questions or unresolved ambiguities]

### Next Steps
- [planned next actions]

### Decisions Made
- [significant design decisions taken during this work, with rationale]
```

This keeps the human in the loop on every significant decision without requiring constant micro-management.

---

## 7. Definition of "Ready to Start"

Setup is complete when:

- [ ] All core Friday spec documents are loaded in the agent's context.
- [ ] `39-friday-framework-strategy.md` is loaded and understood as the framework identity guide.
- [ ] `41-porting-strategy-hermes-erpnext-raven.md` is loaded and understood as the Hermes/ERPNext/Raven translation guide.
- [ ] `42-phase-one-authority-contract.md` is loaded and understood as the v0.1 scope authority.
- [ ] Hermes repository is accessible to the agent (read-only).
- [ ] Frappe bench is provisioned with PostgreSQL + pgvector and Redis.
- [ ] Friday framework shell is scaffolded with LICENSE, README, bench-aware setup, Friday-facing agent commands, Control Room workspace, and Agent Kernel structure.
- [ ] Pre-commit hooks are installed and passing on empty repo.
- [ ] Initial commit is made on a `main` branch.
- [ ] The agent confirms understanding by producing a written summary of Phase One's goal in its own words.

When all checkboxes are green, proceed to the **Evaluation Guide**.
