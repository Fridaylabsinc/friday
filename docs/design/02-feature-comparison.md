# 02 — Feature Comparison

A capability map across Hermes Agent, OpenClaw, and Friday, identifying what we **keep**, what we **replace**, and what we **add** when re-engineering on Frappe.

## Core Agent Capabilities

| Feature | Hermes | OpenClaw | Friday (target) |
|---|---|---|---|
| Agent loop (perceive → plan → act) | ✅ AIAgent class | ✅ | ✅ Inherited from Hermes pattern |
| Skill system | ✅ Markdown + manifests | ✅ Skill registry | ✅ Structured Skill DocType |
| Learning loop / self-improving skills | ✅ Autonomous Curator | ⚠️ Limited | ✅ Skill Draft DocType + review workflow |
| Multi-agent / sub-agents | ✅ Kanban dispatcher | ✅ | ✅ Frappe Project + Task + Kanban view |
| Cron / scheduled jobs | ✅ jobs.json + 60s tick | ✅ | ✅ Frappe Scheduler + background workers |
| Memory (persistent) | ✅ FTS5 + optional vector | ✅ Markdown + optional vector | ✅ PostgreSQL + pgvector |
| User modeling | ✅ Honcho integration | ❌ | ✅ User Model DocType |
| Skill curation | ✅ Autonomous Curator | ❌ | ✅ Background job + status flags |

## Messaging & Platforms

| Feature | Hermes | OpenClaw | Friday (target) |
|---|---|---|---|
| Telegram | ✅ | ✅ | ✅ Adapter writes Chat Message DocType |
| Discord | ✅ | ✅ | ✅ |
| Slack | ✅ | ✅ | ✅ |
| WhatsApp | ✅ | ✅ | ✅ |
| Signal | ✅ | ✅ | ✅ |
| Email (IMAP/SMTP) | ✅ | ⚠️ | ✅ Frappe has native email integration |
| MS Teams / Google Chat | ✅ | ❌ | ✅ |
| CLI / TUI | ✅ | ✅ | ✅ |
| Web UI | ⚠️ Third-party | ✅ Native | ✅ Frappe Desk + custom views |
| Voice input/output | ✅ Whisper + TTS | ⚠️ | ✅ Voice via attachment workflow |

## Tooling

| Feature | Hermes | OpenClaw | Friday (target) |
|---|---|---|---|
| Terminal/shell execution | ✅ Multiple backends | ✅ | ✅ Sandboxed in Docker |
| Browser automation | ✅ Browserbase, CDP, etc. | ✅ | ✅ Browser Task DocType + worker |
| Web search | ✅ | ✅ | ✅ |
| Vision (image analysis) | ✅ | ✅ | ✅ Vision Task DocType |
| Image generation | ✅ FAL.ai | ⚠️ | ✅ Image Generation Task DocType |
| File I/O | ✅ | ✅ | ✅ |
| MCP server support | ✅ | ⚠️ | ✅ MCP Server DocType registration |

## Governance & Security

| Concern | Hermes | OpenClaw | Friday (target) |
|---|---|---|---|
| Role-based permissions | ❌ Config only | ❌ Config only | ✅ **Frappe role matrix, enforced at gateway** |
| Agent profile isolation | ⚠️ HERMES_HOME folder | ⚠️ | ✅ DocType + Docker container per profile |
| Audit trail | ⚠️ Log files | ⚠️ Log files | ✅ Execution Log DocType (immutable) |
| Approval workflows | ✅ Slack/Telegram buttons | ⚠️ | ✅ Workflow Request DocType + Frappe Workflow |
| Sandboxing | ⚠️ Process-level | ⚠️ Process-level | ✅ Docker + network isolation + scoped credentials |
| Secret management | ⚠️ .env files | ⚠️ .env files | ✅ Frappe's Password field type + integrations |
| Command-level threat scanning | ✅ Tirith | ⚠️ | ✅ Inherit Tirith; add permission pre-check |
| Resource quotas / rate limits | ⚠️ Limited | ⚠️ | ✅ Frappe rate limiter + cgroups |

## Persistence & Data

| Feature | Hermes | OpenClaw | Friday (target) |
|---|---|---|---|
| Session storage | SQLite + FTS5 | SQLite | PostgreSQL (via Frappe) |
| Vector embeddings | Optional, plugin-based | Optional | pgvector native |
| Skill storage | Markdown files | Registry + files | Skill DocType (queryable, structured) |
| Real-time pubsub | Custom | Custom | Frappe socketio + Redis |
| Background jobs | Custom scheduler | Custom | Frappe RQ workers |

## Notable Hermes Features We Inherit

- Multi-platform unified gateway pattern (adapters + GatewayRunner)
- Skills with progressive disclosure (L0/L1/L2) — but stored as DocType fields, not separate files
- Cron with natural-language scheduling
- Approval routing for dangerous commands
- Tirith for command-level security scanning
- Model fallback / provider switching
- Sub-agent spawning for parallel workstreams
- Honcho-style user modeling
- MCP server integration
- FTS-based session search (PostgreSQL FTS instead of SQLite FTS5)

## What We Drop / Replace

- **Custom Kanban + SQLite** → Frappe Project/Task with native Kanban view
- **Markdown skill files in `~/.hermes/skills/`** → Skill DocType
- **`jobs.json` cron** → Frappe Scheduler
- **`HERMES_HOME` profile folders** → Agent Profile DocType + scoped database access
- **Log files for audit** → Execution Log DocType
- **Custom WebSocket for live dashboards** → Frappe's real-time pubsub
- **`.env` for secrets** → Frappe Password fields + integration tokens

## What We Add (net-new vs. Hermes)

- Permission enforcement **at gateway level**, gating skill execution before queueing
- Structured Skill schema with status flags (Active / Draft / Experimental / Retired)
- Frappe Workflow-based approval chains (multi-step, multi-role)
- Resource quotas per Agent Profile (Frappe rate limiter)
- Native multi-tenant support (one Frappe site can host multiple isolated agentic deployments)
- Reusable across any Frappe site (eventually as a core Frappe module)
