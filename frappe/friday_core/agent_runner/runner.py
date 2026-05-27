# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
The agent runner — produces a reply for one chat turn.

PLAIN ENGLISH
=============

Slice 4 ships a STUB version of the agent. Given an Agent Profile and
an inbound user message, it:

  1. Loads the tool menu for that profile (via the Slice 3 loader).
  2. Returns a string saying "you have N tools available: …" followed
     by "echo: <inbound>".

That's the entire intelligence right now. No LLM call. No tool
execution. Just enough to prove the pipeline from CLI → DB → loader
→ runner → reply → DB → CLI is end-to-end wired up.

WHEN DOES THIS BECOME REAL?
===========================

**Slice 5** (LLM integration, single provider) replaces the body of
`run_turn` with a real OpenAI / Anthropic call. The function signature
does not change — chat.py, the tests, and any future caller all keep
working.

**Slice 6** (first real skill) lets the agent reply by calling a tool
the LLM picked from the menu.

**Slice 7** wraps the runner in a Docker sandbox per skill invocation.

**Slice 8** moves the runner out of the CLI process and into RQ
workers so multiple agents can run in parallel.

The signature `run_turn(profile, session, content) -> str` survives
all of these. That's by design — it's the contract between the chat
surface and the brain.

HERMES MAPPING
==============

This stub corresponds to `Hermes/run_agent.py:AIAgent.run_conversation`,
but radically simplified — Hermes's real version is ~500 lines with
provider abstraction, tool dispatch, retry logic, streaming callbacks,
and trajectory compression. We'll inherit that shape over Slices 5–8;
for now we just need a function that returns a string.

The "tool menu in the reply" trick is Friday-specific (not in Hermes)
and only here for v0.1 to prove Slice 3 connects. Drop it in Slice 5
when the LLM gets the real menu via the OpenAI tools parameter.
"""

from __future__ import annotations

from frappe.friday_core.skills.loader import load_for_profile


def run_turn(profile_name: str, session_id: str, inbound_content: str) -> str:
	"""Produce one agent reply for one user message.

	Arguments:
	  - `profile_name`: the Agent Profile name (Frappe primary key).
	  - `session_id`: the conversation's session UUID. Currently
	    unused by the stub — kept in the signature because real LLM
	    integrations (Slice 5+) need it to scope conversation history.
	  - `inbound_content`: the user's message text.

	Returns the reply text the chat surface should display and write
	to the outbound Chat Message row.

	Errors propagate. The caller (chat.py:handle_user_message) is
	responsible for whether to crash, retry, or print-and-continue.
	This function does not write any DB rows of its own.
	"""
	skills = load_for_profile(profile_name)

	if skills:
		names = ", ".join(s.name for s in skills)
		menu_line = f"You have {len(skills)} tool(s) available: {names}."
	else:
		menu_line = "You have 0 tool(s) available: (none)."

	return f"{menu_line}\necho: {inbound_content}"
