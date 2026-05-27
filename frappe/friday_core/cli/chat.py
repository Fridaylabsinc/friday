# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
The chat REPL and one-turn handler.

PLAIN ENGLISH
=============

This module has two public functions you'll actually call:

  - `handle_user_message(profile, session_id, content) -> str`
        Process one turn end-to-end: write the inbound row, ask the
        agent for a reply, write the outbound row, return the reply
        text. Tests call this directly so they don't need a REPL.

  - `run_repl(profile)`
        The interactive loop. Opens a session, reads stdin lines,
        passes each to `handle_user_message`, prints replies, exits
        cleanly on EOF / Ctrl+D / `exit`. The bench command calls
        this.

Both write Chat Message rows for audit. Both run synchronously in the
same Python process — see the package docstring for why.

WHY NOT THE GATEWAY EVENTING PATTERN
====================================

The Slice 4 spec in `docs/design/10-agent-execution-guide.md` says
"the gateway sees it via real-time event." We deliberately deferred
that to a later slice. Reasoning is in `docs/rollouts/slice-4-chat-flow.md`
under "Spec deviation." The TL;DR: Hermes's local CLI is in-process;
multi-platform delivery uses async queueing; Slice 4 only needs the
former.
"""

from __future__ import annotations

import getpass
import sys
import uuid

import frappe

from frappe.friday_core.agent_runner.runner import run_turn

# The Chat Platform record's primary key for CLI-originated messages.
# Created on first use by `_ensure_cli_platform_record` so a fresh site
# Just Works without manual setup.
CLI_PLATFORM_NAME = "cli"
CLI_ADAPTER_MODULE = "frappe.friday_core.cli.chat"


# ---------------------------------------------------------------------------
# Public turn handler — the thing tests call
# ---------------------------------------------------------------------------


def handle_user_message(profile_name: str, session_id: str, content: str) -> str:
	"""Process one turn: write inbound row, run agent, write outbound row, return reply.

	This is the single source of truth for "what happens in a chat turn".
	The REPL is just a loop around this function plus stdin/stdout.

	Returns the outbound reply text so the REPL can print it. The fact
	that the reply was also written to a Chat Message row is the side
	effect callers usually want but the return value is what they use
	to render.
	"""
	_ensure_cli_platform_record()

	_write_chat_message(
		profile_name=profile_name,
		session_id=session_id,
		direction="inbound",
		sender_id=_current_user_label(),
		content=content,
	)

	reply = run_turn(profile_name=profile_name, session_id=session_id, inbound_content=content)

	_write_chat_message(
		profile_name=profile_name,
		session_id=session_id,
		direction="outbound",
		sender_id=profile_name,
		content=reply,
	)

	# Frappe defers DB commits to request boundaries; here we're in a
	# long-lived CLI, not a request. Without an explicit commit the rows
	# wouldn't persist across the REPL's process exit OR be visible to
	# concurrent readers.
	frappe.db.commit()

	return reply


# ---------------------------------------------------------------------------
# Public REPL — the thing `bench friday chat` calls
# ---------------------------------------------------------------------------


def run_repl(profile_name: str) -> None:
	"""Run the interactive chat REPL until EOF, Ctrl+D, or `exit`.

	Each line of input becomes one inbound Chat Message. Each agent
	reply becomes one outbound Chat Message. They share a session_id
	that exists for the lifetime of this REPL invocation only.

	Errors during a turn (DB write failure, agent crash) are caught
	and printed inline — we don't want a single bad turn to kill the
	whole conversation. The Chat Message row may or may not have been
	written depending on where the error happened; the row state is
	the truth.
	"""
	# Validate the profile exists upfront so the user gets a clean
	# error before we open a session and prompt them. Frappe raises
	# DoesNotExistError; we let it propagate (clear traceback) rather
	# than mask it.
	if not frappe.db.exists("Agent Profile", profile_name):
		print(f"error: Agent Profile {profile_name!r} not found", file=sys.stderr)
		sys.exit(1)

	session_id = str(uuid.uuid4())
	print(f"Friday chat — profile {profile_name!r}, session {session_id}")
	print("Type 'exit', 'quit', or press Ctrl+D to leave.\n")

	while True:
		try:
			line = input("> ")
		except (EOFError, KeyboardInterrupt):
			print("\nbye.")
			return

		line = line.strip()
		if line in ("exit", "quit"):
			print("bye.")
			return
		if not line:
			continue

		try:
			reply = handle_user_message(profile_name, session_id, line)
			print(reply)
		except Exception as exc:  # noqa: BLE001 — REPL: surface, don't crash
			# Log full traceback to the Frappe error log AND show a
			# short line to the user. Crashing the REPL on a single
			# bad turn is worse than a printed error.
			frappe.log_error(title="friday chat turn failure")
			print(f"[error] {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _ensure_cli_platform_record() -> None:
	"""Idempotently create the 'cli' Chat Platform row on first use.

	A fresh `bench new-site friday.localhost` has no Chat Platform
	records. Rather than require an install step, we just check-and-
	create on the first chat turn. Subsequent turns find it and skip.
	"""
	if frappe.db.exists("Chat Platform", CLI_PLATFORM_NAME):
		return
	doc = frappe.get_doc(
		{
			"doctype": "Chat Platform",
			"platform_name": CLI_PLATFORM_NAME,
			"adapter_module": CLI_ADAPTER_MODULE,
			"enabled": 1,
		}
	)
	doc.insert(ignore_permissions=True)


def _write_chat_message(
	profile_name: str,
	session_id: str,
	direction: str,
	sender_id: str,
	content: str,
) -> str:
	"""Insert one Chat Message row, return its docname.

	`ignore_permissions=True` here for the same reason as in the
	permission decisions writer: this code is the system recording
	its own state. There's no user role that "may create Chat
	Message" — Chat Message is plumbing, not user data.
	"""
	doc = frappe.get_doc(
		{
			"doctype": "Chat Message",
			"session_id": session_id,
			"platform": CLI_PLATFORM_NAME,
			"direction": direction,
			"sender_id": sender_id,
			"agent_profile": profile_name,
			"content": content,
			"timestamp": frappe.utils.now_datetime(),
			"processed": 1 if direction == "outbound" else 0,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _current_user_label() -> str:
	"""Best-effort identifier for who's typing.

	Tries the OS login user; falls back to "cli-user". Used for the
	`sender_id` field on inbound messages so audit logs say *who*,
	not just "some CLI process".
	"""
	try:
		return getpass.getuser() or "cli-user"
	except Exception:  # noqa: BLE001
		return "cli-user"
