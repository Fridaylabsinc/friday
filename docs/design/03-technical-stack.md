# 03 — Technical Stack

## Stack Overview

| Layer | Technology | Why |
|---|---|---|
| Application framework | Frappe Framework (v15+) | Battle-tested DocType + permission system, Python-based, GPL-aligned |
| Primary database | PostgreSQL | Native vector support via pgvector, superior JSON + FTS vs MariaDB |
| Vector search | pgvector extension | Semantic search on agent memory and execution logs, no external vector DB |
| In-memory layer | Redis (Redis Stack optional) | Cache, queues, pubsub; Redis Stack adds vector similarity in RAM for hot paths |
| Job queue | Frappe RQ (Redis-backed) | Native to Frappe, handles retries, scheduling, background workers |
| Real-time | Frappe socketio + Redis pubsub | Live notifications, gateway events, Kanban updates |
| Container runtime | Docker | Agent sandboxing, resource quotas, network isolation |
| Language (server) | Python 3.11+ | Frappe's runtime |
| Language (client / UI) | JavaScript + Frappe UI | Frappe Desk + custom Vue components |
| LLM access | Provider-agnostic (OpenAI, Anthropic, OpenRouter, local) | Inherited from Hermes pattern; switchable per Agent Profile |

## Why PostgreSQL over MariaDB

Frappe defaults to MariaDB, but the developer release supports PostgreSQL. For Friday we go straight to PostgreSQL because:

- **pgvector** gives us native vector similarity search — no external vector database (Pinecone, Weaviate) needed.
- **Better JSON handling** (`jsonb`, GIN indexes) for storing skill schemas and tool call payloads.
- **Superior full-text search** vs MariaDB, removing the need for SQLite FTS5 (which Hermes uses).
- **Stronger concurrency** for multi-agent writes.

Tradeoff: slightly higher resource footprint than MariaDB. Acceptable for enterprise-grade workloads.

## Why Redis Stays Central

- **Cache layer** in front of PostgreSQL — skill definitions, permission matrices, session metadata.
- **Job queues** via Frappe RQ — skill executions, learning jobs, curator runs.
- **Pubsub** for real-time gateway events — incoming messages, task state changes, approval requests.
- **Optional Redis Stack** — in-memory vector similarity for hot agent memories, with spillover to pgvector for cold storage.

## Why Docker for Sandboxing

Each Agent Profile execution runs in a Docker container with:

- **Resource limits** (cgroups) — CPU, memory, disk quotas per agent.
- **Network namespace isolation** — container can only reach Frappe REST API + permitted external endpoints.
- **Scoped credentials** — container receives only the DB/API tokens needed for its Agent Profile's permitted scope.
- **Ephemeral filesystem** — read-only mounts for skill definitions; writes go through Frappe API.
- **Teardown after execution** — no persistent container state; everything important lives in Frappe.

This raises the security floor significantly versus Hermes' process-level isolation, where a compromised skill can read anything the host user can.

## Why Frappe Framework Specifically

Compared to alternatives (FastAPI from scratch, Django, Flask + custom permission layer):

- **DocType system** — declarative schema with automatic CRUD, validation, hooks, UI.
- **Role-based permission engine** — fine-grained, multi-role, per-document permissions. Years of production hardening.
- **Workflow engine** — native multi-state, multi-role approval chains.
- **Native Kanban view** — no need to build a board UI.
- **Real-time notifications** — out of the box via socketio.
- **Background workers** — Frappe RQ ready to use.
- **REST API auto-generated** — every DocType is queryable via REST without writing endpoints.
- **`bench execute`** — built-in CLI to invoke Python functions in the site context (useful for internal admin operations and trusted skill execution paths).
- **Multi-tenant** — one bench can host many sites, each with isolated Friday deployments.

## Optional / Future Components

| Component | Purpose | Status |
|---|---|---|
| Tirith | Command-level security scanning (inherited from Hermes) | Phase 2 |
| Whisper (local or API) | Voice transcription | Phase 2 |
| TTS service | Spoken replies | Phase 2 |
| Browser automation backends | Browserbase, Playwright, CDP | Phase 2 |
| Image generation | FAL.ai or local SD | Phase 3 |
| MCP server clients | External tool integration | Phase 2 |

## What We Explicitly Avoid

- **MongoDB / schema-less databases** — we lose transactional guarantees and Frappe's permission integration.
- **External vector DBs (Pinecone, Weaviate)** — adds cost, complexity, and a second source of truth. pgvector is sufficient.
- **Heavy message brokers (RabbitMQ, Kafka)** — overkill for our throughput; Redis + RQ is sufficient until proven otherwise.
- **Reinventing Frappe's primitives** — if Frappe already does it (workflows, permissions, scheduler, Kanban, real-time), we use it.
