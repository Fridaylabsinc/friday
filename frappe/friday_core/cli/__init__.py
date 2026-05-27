# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
The Friday CLI — `bench friday chat`, the first interactive surface.

This package is where the local interactive surfaces of Friday live. For
v0.1 there is exactly one: an in-process REPL that lets you converse
with an Agent Profile from the terminal.

PLAIN ENGLISH
=============

Right now, to interact with Friday you'd have to write Python or hit
its REST API. That's fine for engineers and unacceptable for everyone
else. This package gives you a normal command-line prompt:

    $ bench --site friday.localhost friday chat --profile "My Agent"
    Friday chat — profile 'My Agent', session abc-123
    > hello
    You have 0 tool(s) available: (none).
    echo: hello
    >

Every line you type is recorded as a Chat Message DocType row
(direction=inbound). Every reply is also recorded (direction=outbound).
The audit trail is automatic.

DESIGN: IN-PROCESS, HERMES-FAITHFUL
====================================

Like the Hermes upstream project (`https://github.com/NousResearch/hermes-agent`,
see `cli.py:11773` calling `self.agent.run_conversation(...)`),
**the agent runs in the same process as the REPL**. The CLI does NOT
publish a message to a queue and then poll a database to hear back.
It just calls a Python function.

Why this matches Hermes and why it's right for v0.1:

  - Hermes is the working reference and it never uses IPC for its own
    local CLI. Inventing IPC where Hermes doesn't is unjustified
    divergence — see project memory `feedback-compare-with-hermes`.
  - Real-time eventing matters for multi-platform delivery (Telegram,
    Slack, Raven War Room). For a single local CLI talking to a single
    agent, it's machinery without payoff.
  - In-process is testable. We can call the same function the REPL
    calls and assert on its output.

When multi-platform lands in a later slice, we'll add the queue-and-
edit pattern from Hermes's `gateway/stream_consumer.py`. Not before.

WHAT GETS RECORDED
==================

Every turn writes two Chat Message rows:

  - inbound: the user line, `sender_id` = OS user, `direction` =
    "inbound", `platform` = "cli"
  - outbound: the agent reply, `sender_id` = profile_name,
    `direction` = "outbound", `platform` = "cli"

Both share the same `session_id` (a UUID4 generated at REPL start).
Sessions are ephemeral — closing the CLI ends the session. The
messages persist in Frappe for audit.

MODULES
=======

  - `chat.py`     — the REPL function `run_repl`, the turn handler
                    `handle_user_message`, and helpers.
  - `commands.py` — the `click` registration that lets bench find
                    `friday chat` as a subcommand.
"""
