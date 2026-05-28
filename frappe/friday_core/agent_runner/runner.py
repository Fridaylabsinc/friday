# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
The agent runner — produces a reply for one chat turn.

PLAIN ENGLISH
============

Given an Agent Profile, a session ID, and the user's message, this
function returns the agent's reply text. The reply is produced by calling
the LLM configured for that profile, with:

  - The agent's system prompt + conversation history (built by prompt_builder)
  - The list of permitted tools (loaded by the Slice 3 skill loader)

Errors are intentionally not handled here — they propagate to the gateway
which catches them and writes a system-error outbound Chat Message row.
This keeps the runner a pure function: in → LLM → out.

HERMES MAPPING
=============

This corresponds to `Hermes/run_agent.py:AIAgent.run_conversation`.
Friday's version is radically simpler because Frappe's DocType rows
(Chat Message for history, Skill for tools, Agent Profile for config)
replace the Hermes in-memory equivalents.

The function signature `run_turn(profile, session, content) -> str`
is intentionally preserved from the Slice 4 stub — the caller (the
gateway) does not need to change when this replaces the echo stub.

WHAT THIS MODULE DOES NOT DO
============================

- Does not write Chat Message rows. The gateway does that.
- Does not check permissions. The gateway calls `permissions.matrix.check`
  before calling the runner.
- Does not execute skills. That's Slice 6's dispatcher.
- Does not run in a sandbox. That's Slice 7's Docker wrapper.
- Does not stream tokens. Deferred to when a real-time surface lands.
"""

from __future__ import annotations

import frappe

from frappe.friday_core.llm import get_provider_for_profile
from frappe.friday_core.llm.prompt_builder import build
from frappe.friday_core.llm.provider import LLMError
from frappe.friday_core.skills.loader import load_for_profile


def run_turn(profile_name: str, session_id: str, inbound_content: str) -> str:
	"""Produce one agent reply for one user message.

	Arguments:
	  - `profile_name`: the Agent Profile name (Frappe primary key).
	  - `session_id`: the conversation's session UUID.
	  - `inbound_content`: the user's message text.

	Returns the reply text the gateway will write to the outbound
	Chat Message row.

	Errors propagate to the gateway (caller). The gateway catches them
	and writes a system-error outbound row. This function does not write
	any DB rows of its own.

	Raises:
	  - `frappe.DoesNotExistError` if the profile does not exist.
	  - `LLMError` (or subclass) if the LLM call fails after retries.
	"""
	# 1. Load the tool menu (permitted + active + matrix-allowed).
	skill_definitions = load_for_profile(profile_name)

	# 2. Build the full prompt (system prompt + history + current message).
	prompt = build(
		profile_name=profile_name,
		session_id=session_id,
		inbound_content=inbound_content,
		tools=skill_definitions,
	)

	# 3. Resolve the provider and call the LLM.
	provider = get_provider_for_profile(profile_name)
	response = provider.chat(
		messages=prompt["messages"],
		tools=prompt["tools"],
		model=prompt["model"],
	)

	return response["content"]
