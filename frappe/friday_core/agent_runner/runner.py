# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
The agent runner — produces a reply for one chat turn.

PLAIN ENGLISH
=============

Given an Agent Profile, a session ID, and the user's message, this
function returns the agent's reply text. The reply is produced by calling
the LLM configured for that profile, with:

  - The agent's system prompt + conversation history (built by prompt_builder)
  - The list of permitted tools (loaded by the Slice 3 skill loader)

If the LLM returns a tool call, the runner dispatches it via the
Slice 6 dispatcher and returns the skill result as the reply text.

Errors that occur during dispatch are caught and returned as part of
the reply text — the runner never crashes.

WHAT THIS MODULE DOES NOT DO
============================

- Does not write Chat Message rows. The gateway does that.
- Does not check permissions. The dispatcher calls `permissions.matrix.check`
  before executing any skill.
- Does not run in a Docker sandbox. That's Slice 7's Docker wrapper.
- Does not stream tokens. Deferred to when a real-time surface lands.
"""

from __future__ import annotations

import json
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

	Dispatch flow:
	  1. Load the tool menu (permitted + active + matrix-allowed).
	  2. Build the full prompt (system prompt + history + current message).
	  3. Call the LLM.
	  4. If the LLM returns a tool call → dispatch it and return the result.
	     If the LLM returns plain text → return it directly.

	Errors are caught and returned as part of the reply text — this
	function does not write any DB rows of its own (the gateway owns
	all Chat Message writes).
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

	# 4. Check for tool calls.
	tool_calls = response.get("tool_calls")
	if not tool_calls:
		# Plain text reply — no tool execution needed.
		return response["content"]

	# 5. Dispatch the tool call. We take the first tool call only
	# (Slice 6 is single-dispatch; multi-step loop is Slice 8).
	if len(tool_calls) > 1:
		# Future: support multi-call. For now, just take the first.
		frappe.logger().warning(
			f"friday.agent_runner.runner: received {len(tool_calls)} tool calls "
			f"in one response — only the first will be dispatched"
		)

	tool_call = tool_calls[0]
	skill_name = tool_call.get("name", "")

	# Parse the tool call arguments.
	raw_args = tool_call.get("arguments", "{}")
	try:
		parameters = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
	except json.JSONDecodeError:
		return (
			f"I tried to use the '{skill_name}' tool but its arguments were "
			f"malformed. Please try rephrasing your request."
		)

	# 6. Dispatch via the Slice 6 dispatcher.
	from frappe.friday_core.agent_runner.dispatcher import dispatch

	tokens_used = None
	usage = response.get("usage", {})
	if usage:
		tokens_used = usage.get("total_tokens", 0)

	result = dispatch(
		tool_call=tool_call,
		agent_profile=profile_name,
		session_id=session_id,
		tokens_used=tokens_used,
	)

	# 7. Return the human-readable content from the dispatch result.
	return result.content
