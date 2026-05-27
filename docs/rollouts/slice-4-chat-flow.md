# Slice 4 Rollout — The Chat Flow

> **Slice:** 4 of 9 — see `docs/design/10-agent-execution-guide.md`
> **PR:** (this PR)
> **Author:** `fridaylabs` / sponsor `@Fridaylabsinc`
> **Audience:** Anyone — engineer, product owner, or a high schooler.

---

## In one sentence

**Friday now talks.** You can run `bench --site friday.localhost friday chat --profile "My Agent"`, type a message, and get a reply — with both sides of the conversation recorded as immutable audit rows.

---

## What it actually does (in plain terms)

Until now Friday was a system you could *read* (the gatekeeper, the menu) but not *use* — there was no surface to actually send it a message. Slice 4 fixes that with the simplest possible surface: a command-line prompt.

You start the chat:

    $ bench --site friday.localhost friday chat --profile "My Agent"
    Friday chat — profile 'My Agent', session b7a4-…
    Type 'exit', 'quit', or press Ctrl+D to leave.

    > hello

…and you get a reply. For Slice 4 the "intelligence" is a placeholder — the reply lists the tools the agent has available (proving Slice 3 is hooked up) and echoes your message back. Slice 5 swaps the placeholder for a real LLM call without changing anything else.

Every line you type and every reply you get becomes a `Chat Message` row in the database, tagged with a session ID, the platform ("cli"), the direction (inbound/outbound), and the timestamp. Auditors can replay the conversation any time.

---

## What scenarios it now covers

| Scenario | Outcome |
|---|---|
| You type a line in the REPL | One inbound `Chat Message` row written. |
| The stub agent runs and produces a reply | One outbound `Chat Message` row written. |
| Both rows for the same turn | Share the same `session_id` (UUID per REPL invocation). |
| Profile doesn't exist | Clean error, REPL exits with code 1 before opening a session. |
| You type a blank line | Skipped; loop continues. |
| You type `exit` / `quit` / Ctrl+D / Ctrl+C | REPL exits cleanly. |
| A turn raises an exception | Logged to Frappe Error Log; user sees `[error] …`; loop continues. The conversation does not die from a single bad turn. |
| First-ever call after `bench new-site` | "cli" Chat Platform record is auto-created. Zero manual setup. |
| Agent has skills permitted | Reply says `"You have N tool(s) available: a, b, c."` followed by `echo: <your line>`. |
| Agent has no skills permitted | Reply says `"You have 0 tool(s) available: (none)."` |

All of these are proven by the 8 tests in `frappe/friday_core/tests/test_chat_flow.py`.

---

## What it means for friday-core

**Before Slice 4:** friday-core had the gatekeeper and the menu, but nothing called either of them in a user-driven flow. It was a system on paper.

**After Slice 4:** friday-core has its first **end-to-end loop**. A user action triggers a recorded inbound message, which triggers the stub agent runner, which calls into the Slice 3 loader (which calls into the Slice 2 matrix), which returns text, which is recorded as an outbound message, which is displayed back to the user. Six pieces talking to each other for one human-readable purpose.

Three things this lets us truthfully claim today:

1. **"Every user message is recorded."** Verified by `test_handle_user_message_writes_inbound_row`.
2. **"Every agent reply is recorded."** Verified by `test_handle_user_message_writes_outbound_row`.
3. **"The agent's reply path uses the same permission matrix that gates every action."** The stub calls `load_for_profile()` → which calls Slice 2's `evaluate()` → so the menu the user sees in the reply is filtered by exactly the rules a real action would face.

This is the moment Friday becomes demonstrable. You can hand someone a terminal and show them the loop.

---

## How friday-core gets along with the Frappe ecosystem

| Friday concept | Frappe reality |
|---|---|
| The `friday chat` command | A click Group registered alongside Frappe's own bench subcommands via `frappe/commands/__init__.py:get_commands()`. Behaves like `bench migrate`, `bench run-tests`, etc. |
| Audit rows | A `Chat Message` DocType. Queryable in Desk, REST API, reports. |
| `cli` platform identity | A `Chat Platform` row (auto-created on first use). Future platforms (Telegram, Slack, Raven) will be peers in the same table. |
| Site context | Standard `bench --site <name>` wrapping. The CLI inherits the site connection the same way `bench execute` does. |
| Error reporting on a bad turn | `frappe.log_error(...)` — goes to the standard Frappe Error Log. |

Frappe-native end to end. An admin doing audit work can query Chat Messages in Desk's report builder; no Friday-specific tooling needed.

---

## Hermes comparison (per the project rule)

For every architectural choice we now compare against the Hermes upstream. Here's the audit:

| Decision | Hermes does | Friday does | Justification |
|---|---|---|---|
| **CLI ↔ agent communication** | In-process function call (`cli.py:11773` calls `self.agent.run_conversation(...)`); SQLite session storage | In-process function call (`chat.py:handle_user_message` calls `runner.run_turn`); DocType session storage | **Same pattern**, different storage backend. Storage swap is forced by Frappe's DocType-or-nothing model. |
| **REPL input** | `prompt_toolkit` TUI (rich, mouse-aware, history) | Plain `input()` | **Deferred polish.** Add `prompt_toolkit` later if needed; doesn't affect data flow. |
| **Session lifecycle** | Per CLI invocation, file-backed | Per CLI invocation, DB-backed | Same: ephemeral, single-process. |
| **Real-time event for outbound delivery to CLI** | Hermes **does not have this**. Local CLI is in-process. | Friday also does not have this in Slice 4. | The slice spec said "via real-time event"; this contradicts the Hermes pattern. We picked the Hermes-faithful in-process flow and deferred the eventing layer to whichever later slice introduces multi-platform delivery (likely Slice 8 or a Raven integration). |
| **Multi-platform queue + edit-message streaming** | Hermes has it (`gateway/stream_consumer.py`, `gateway/platforms/*`). Used for Telegram, Slack, Signal, etc. | Not in Slice 4. Will be ported when Friday adds its first external platform adapter. | Future slice; not needed for the CLI. |

The audit confirms: **no architectural divergence in Slice 4 that lacks a justification.** We chose the Hermes pattern for the local CLI, with platform-eventing explicitly deferred to the slice that needs it.

---

## What the project can say truthfully today

- **"You can have a conversation with a Friday agent."** Run the command, type a message, see a reply.
- **"Every message is audited."** Two immutable Chat Message rows per turn, queryable in Frappe Desk.
- **"The reply path exercises the same permission machinery as a real action."** Verified by the stub calling `load_for_profile()`.
- **"Round-trip latency is well under a second on local dev."** Verified by `test_handle_user_message_round_trip_under_one_second`.

---

## Risks and limits a product head should hold

- **No real intelligence yet.** Slice 4 ships a stub. The agent's reply is templated. Real LLM call is Slice 5.
- **No skill execution yet.** The agent's reply mentions tools but cannot call them. Skill calls are Slice 6.
- **Single-user, single-session.** The CLI is one process. Multi-user / multi-session lives in later slices (RQ-worker model, Slice 8).
- **No streaming.** Replies are returned as a single string. Hermes's progressive-edit streaming is deferred.
- **No platform abstraction beyond the row.** A `Chat Platform` record exists for "cli"; the actual cross-platform layer that turns inbound messages into agent turns regardless of source is a later slice.
- **REPL UX is plain.** No history, no completion, no syntax highlighting. `prompt_toolkit` polish is a one-day add when we want it.

---

## What this unlocks

- **Slice 5 (LLM integration)** can replace `runner.run_turn`'s body with a real OpenAI / Anthropic call. The CLI, the audit-row writer, and all 8 tests keep working unchanged.
- **Slice 6 (first real skill)** can take a tool call the LLM emits and route it through the gatekeeper → execute → return.
- **Slice 8 (Agent Task + Dispatcher)** can re-target the chat flow at an async RQ worker model when single-process becomes the bottleneck.
- **Future platform adapters** (Raven, Telegram, etc.) can write Chat Message rows from their own surfaces and reuse `handle_user_message` directly — same audit, same agent loop.

---

## Numbers for the record

- 7 files added/modified:
  - `frappe/friday_core/cli/__init__.py`, `chat.py`, `commands.py`
  - `frappe/friday_core/agent_runner/__init__.py`, `runner.py`
  - `frappe/friday_core/tests/test_chat_flow.py`
  - `frappe/commands/__init__.py` (registered the friday click Group)
- **8/8 chat-flow tests green**
- Regression: Slice 1 → 2/2, Slice 2 → 10/10, Slice 3 → 8/8
- Deliverables verified:
  - `bench --site friday.localhost friday --help` lists the `chat` subcommand.
  - `bench --site friday.localhost friday chat --help` shows the `--profile` option.
  - `bench --site friday.localhost execute frappe.friday_core.cli.chat.handle_user_message --args "['FRIDAY-SLICE4-PROFILE-TOOLS', 'demo-session-1', 'hello world']"` returns the stub's templated reply.
