# Agentic Workflow — 02 Evaluation Guide

> **Purpose:** Define the criteria the agent uses to decide whether a Hermes Agent component is **reusable as-is**, **adaptable to Frappe**, or **must be rewritten from scratch** for Friday.

This is the heart of specification-driven development on top of an existing reference codebase. The agent does not copy Hermes blindly, and does not reinvent unnecessarily. It evaluates.

---

## 1. Three Verdicts

For every Hermes component the agent considers using, it assigns one of three verdicts:

### REUSE
The code can be used in Friday with **minimal changes** — typically only license headers, import paths, and connection of inputs/outputs to Frappe equivalents.

### ADAPT
The **design and structure** are valuable, but the implementation must be rewritten to use Frappe primitives (DocTypes, permissions, hooks, RQ workers, real-time pubsub) instead of Hermes' own (markdown files, JSON state, SQLite, custom dispatcher, etc.).

### REWRITE
The Hermes implementation does not map to Friday's architecture. The feature must be designed and built from scratch, with Hermes serving only as a high-level reference for *what* the feature does, not *how*.

---

## 2. Decision Criteria

The agent applies the following questions, in order, to every Hermes component:

### Q1 — Does it touch persistent state?

- **No** (pure logic, prompt assembly, parsing, formatting) → likely **REUSE**.
- **Yes** → go to Q2.

### Q2 — Does the state map cleanly to a DocType?

- **Yes** → **ADAPT**. Replace file/SQLite reads with `frappe.get_doc` / `frappe.get_all`; replace writes with DocType save/submit.
- **No** (e.g. ephemeral conversation buffer) → keep state in Redis; **ADAPT** or **REUSE**.

### Q3 — Does it bypass or weaken permission boundaries?

- **Yes** (Hermes' allow-all defaults, direct file access, unscoped shell exec) → **REWRITE**. Friday requires gateway-level permission validation.
- **No** → continue.

### Q4 — Does it depend on Hermes-specific runtime conventions?

Examples: `HERMES_HOME`, `~/.hermes/`, `profile_override`, Hermes' own session format, Hermes' SQLite schema.

- **Yes** → **ADAPT**. Replace conventions with Frappe site context (`frappe.local.site`), Frappe sessions, Frappe DocTypes.
- **No** → likely **REUSE**.

### Q5 — Is there a Frappe-native primitive that already does this?

Examples: Frappe Workflow vs. Hermes' approval routing; Frappe Scheduler vs. Hermes' cron; Frappe socketio vs. Hermes' WebSocket dispatcher; Frappe Kanban view vs. Hermes' Kanban dashboard.

- **Yes** → **REWRITE** to use Frappe primitive. Document the mapping.
- **No** → consider **ADAPT**.

### Q6 — Does it carry security risk that has been publicly disclosed?

Examples: Hermes' WeChat path traversal (CVE-2026-7396), LiteLLM supply chain risk.

- **Yes** → **REWRITE**, learning from the disclosed mitigation but not inheriting the implementation.
- **No** → continue with prior verdict.

---

## 3. Component-by-Component Audit (Phase 1 scope)

The agent walks through each Phase-1-relevant Hermes area and records a verdict.

### 3.1 Agent Loop (`AIAgent.run_conversation`)

- **Hermes location:** `agent/run_agent.py`
- **Question outcomes:**
  - Q1: Yes, touches conversation state — go to Q2.
  - Q2: Conversation buffer maps well to a Redis-backed structure + DocType for persistence — ADAPT path.
  - Q3: The loop itself is permission-agnostic; permission checks are inserted *around* it — no rewrite needed here.
  - Q4: Uses Hermes profile_override and session format — must rewire.
  - Q5: No direct Frappe equivalent.
- **Verdict: ADAPT.** Keep the loop structure (perceive → plan → tool call → execute → result → repeat); replace state plumbing with Frappe + Redis.

### 3.2 Prompt Builder (`agent/prompt_builder.py`)

- Q1: No persistent state (reads, doesn't write) — REUSE candidate.
- Q4: Pulls from SOUL.md, MEMORY.md, USER.md, skill files — these are file-based.
- Q5: Friday stores persona, memory, user model, and skills as DocTypes.
- **Verdict: ADAPT.** Keep the assembly logic and section ordering. Replace file reads with DocType queries.

### 3.3 Tool Registry / Skill Loading

- Hermes loads markdown skills from `~/.hermes/skills/` and bundled `.hub/`.
- Q5: Friday's `Skill` DocType replaces the entire file-based loader.
- **Verdict: REWRITE.** Reference Hermes' progressive disclosure model (L0/L1/L2) but build the loader against Frappe DocTypes from scratch.

### 3.4 GatewayRunner

- **Hermes location:** `gateway/run.py`
- Q1: Manages per-session AIAgent cache — Redis-backed LRU.
- Q2: Maps to an in-memory cache, no DocType needed for the cache itself (sessions persist as DocTypes).
- Q3: Permission checks must be added at the dispatch boundary.
- Q4: Uses Hermes session ID conventions.
- **Verdict: ADAPT.** Keep LRU cache shape, idle TTL, auto-resume logic. Replace session resolution with Frappe sessions; insert permission check at dispatch.

### 3.5 Platform Adapters

- **Hermes location:** `gateway/platforms/`
- Each adapter translates platform events ↔ agent messages.
- Q3: At least one adapter (WeChat) has had a CVE. Inspect others for similar patterns.
- Q4: Adapters write to Hermes' message format.
- **Verdict: ADAPT** for CLI (Phase 1 only). Pattern is sound; rewrite the message-writing side to create `Chat Message` DocTypes. Defer other adapters to Phase 2; **REWRITE** WeChat adapter when introduced (do not inherit the CVE'd code).

### 3.6 Skill Management Tool (`skill_manage`)

- Allows the agent to author/edit/delete skills.
- Q3: In Hermes, skills are files the agent can write directly — this is also a security concern (agent self-mutation).
- Q5: Friday gates skill changes through DocType permissions; agents propose `Skill Draft` rows, humans approve.
- **Verdict: REWRITE.** Replace direct skill mutation with a DocType-based draft/review workflow.

### 3.7 Permission Layer

- Hermes does **not** have a structured permission layer; settings are config-driven.
- **Verdict: REWRITE.** Build from scratch on top of Frappe roles. No Hermes code is useful here, but Hermes' Tirith pattern (post-permission, pre-execution command scanning) is conceptually adopted.

### 3.8 Approval Routing

- **Hermes location:** Slack/Telegram approval buttons.
- Q5: Frappe Workflow does this generically.
- **Verdict: REWRITE.** Use Frappe Workflow on `Workflow Request` DocType.

### 3.9 Cron / Scheduler

- Hermes ticks `jobs.json` every 60s.
- Q5: Frappe Scheduler is mature and integrates with the workflow engine.
- **Verdict: REWRITE.** Use Frappe Scheduler hooks in `hooks.py`.

### 3.10 Session Storage / FTS

- Hermes uses SQLite + FTS5.
- Q4 + Q5: Friday stores sessions as DocTypes in PostgreSQL with FTS via `pg_trgm` and `tsvector`.
- **Verdict: REWRITE.** Session model is fundamentally different.

### 3.11 Memory / Vector Search

- Hermes has optional vector plugins.
- Q5: Friday uses pgvector natively, no plugin abstraction needed (yet).
- **Verdict: REWRITE** (but defer to Phase 2; Phase 1 uses basic FTS only).

### 3.12 Multi-Agent Kanban

- Hermes has a custom Kanban (SQLite-backed) with `kanban_*` tools.
- Q5: Frappe has native Kanban view on any DocType with a Workflow.
- **Verdict: REWRITE.** Tools like `kanban_claim`, `kanban_update_state` become thin wrappers around Frappe REST API calls.

### 3.13 Tirith Command Scanning

- Standalone Go binary distributed by Hermes.
- Q1: Pure analysis, no state.
- Q5: No Frappe equivalent.
- **Verdict: REUSE** as an external dependency in Phase 2 (deferred from Phase 1). Invoke via subprocess from the permission engine.

### 3.14 LLM Provider Adapters

- Hermes supports many providers via a unified interface.
- Q1: Stateless API clients.
- Q5: No Frappe equivalent.
- **Verdict: REUSE** the interface design. Phase 1 implements a single provider (OpenAI or Anthropic); the interface should be wide enough for Phase 2 to add more without redesign.

---

## 4. License Compliance Checks

For every component marked REUSE or ADAPT:

- [ ] Confirm the original Hermes file's license header.
- [ ] Verify it is GPL v3 / AGPL v3 / compatible.
- [ ] Preserve attribution in the Friday file's header:
  ```python
  # This file adapts logic from NousResearch/hermes-agent (GPL v3).
  # Original source: [path in Hermes repo]
  # See NOTICE for full attribution.
  ```
- [ ] Add the original file path to the project's `NOTICE` file.

The agent **must not** REUSE or ADAPT a file without recording attribution. License compliance is a blocker, not a polish item.

---

## 5. Producing the Audit Report

At the end of evaluation, the agent produces a single `docs/hermes-audit.md` file with the following structure for each component:

```markdown
### [Component Name]

- **Hermes source:** [path or paths]
- **Verdict:** REUSE / ADAPT / REWRITE
- **Reasoning:** [which Q1–Q6 outcomes drove the verdict]
- **Mapping to Friday:** [which Friday module / DocType / file owns this]
- **License notes:** [attribution requirements]
- **Phase:** 1 / 2 / 3+
```

This audit report becomes the **execution plan** for the Execution Guide.

---

## 6. Anti-Patterns the Agent Must Reject

Regardless of how convenient or well-written, the agent must refuse to adopt Hermes patterns that contradict Friday's design:

| Pattern | Why Rejected |
|---|---|
| Default allow-all permissions | Violates Friday's permission-first principle |
| Skills as files the agent can write directly | Bypasses approval workflow |
| Session state in flat files outside the database | Breaks audit trail |
| Running tools in the host process by default | Breaks sandboxing |
| Hard-coded `~/.hermes/` paths | Breaks multi-tenant Frappe sites |
| LiteLLM as a default dependency | Supply chain risk; use direct provider SDKs |
| Markdown-only skill discovery | Breaks DocType-based skill governance |

If the agent encounters one of these in Hermes and is tempted to import it, it stops and flags the conflict for human review.

---

## 7. When the Spec Disagrees with Hermes

If a Hermes implementation contradicts a Friday spec, the **spec wins**. Always.

The agent should not "improve" Friday's design to match Hermes. The agent may, however, propose spec amendments in writing — explaining what Hermes does, why it might be better, and what the tradeoff is. Humans decide.

---

## 8. Output of the Evaluation Phase

When evaluation is complete, the agent has produced:

1. `docs/hermes-audit.md` — verdict per component with reasoning.
2. `NOTICE` file populated with attribution for all REUSE/ADAPT entries.
3. A prioritised list of components for Phase 1 implementation (carried forward to the Execution Guide).
4. A list of flagged conflicts and proposed resolutions for human review.

When these four artefacts are produced and reviewed, proceed to the **Execution Guide**.
