# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
The chat REPL and one-turn handler — thin adapter over the unified gateway.

PLAIN ENGLISH
=============

This module is the CLI surface. It is INTENTIONALLY THIN. The actual
agent work happens in the gateway (`friday_core.gateway.service`).
The CLI's only jobs are:

  1. Read a line from the user.
  2. Write an inbound Chat Message row (this synchronously triggers
     the gateway via `doc_events.after_insert`).
  3. Read the outbound Chat Message row the gateway just wrote.
  4. Print it to stdout.
  5. Loop.

The CLI does NOT import `agent_runner`. The CLI does NOT call permission
or skill code. Everything happens through the Chat Message DocType and
the gateway's hook. This is the chokepoint pattern (see
`docs/design/47-gateway-design-decisions.md` §3 and §9).

TWO PUBLIC FUNCTIONS
====================

- `handle_user_message(profile, session_id, content) -> str`
      Process one turn end-to-end: write inbound, read the outbound the
      gateway produced, return the reply text. Tests call this directly
      so they don't need a REPL.

- `run_repl(profile)`
      The interactive loop. Opens a session, reads stdin lines, calls
      `handle_user_message`, prints replies, exits on EOF/Ctrl+D/`exit`.
      The `bench friday chat` command calls this.

WHY WE READ THE OUTBOUND ROW DIRECTLY (not via publish_realtime)
================================================================

Per §4 Q2 of the design doc. The "cli" Chat Platform has
`dispatch_mode="sync"`, so the gateway runs INSIDE the inbound row's
insert() call. By the time insert() returns, the outbound row exists.
A direct DB read finishes the round trip with zero extra moving parts.

The gateway still fires `publish_realtime("chat.outbound", ...)` so
future Telegram/Slack/Raven adapters can subscribe to outbound events.
CLI doesn't subscribe.
"""

from __future__ import annotations

import getpass
import sys
import uuid

import frappe

# The Chat Platform record's primary key for CLI-originated messages.
# Created on first use by `_ensure_cli_platform_record` so a fresh site
# Just Works without manual setup.
CLI_PLATFORM_NAME = "cli"
CLI_ADAPTER_MODULE = "frappe.friday_core.cli.chat"


# ---------------------------------------------------------------------------
# Public turn handler — the thing tests call
# ---------------------------------------------------------------------------


def handle_user_message(profile_name: str, session_id: str, content: str) -> str:
	"""Process one turn: write inbound, let gateway run, read outbound, return.

	This is the single source of truth for "what happens in a CLI turn".
	The REPL is just a loop around this function plus stdin/stdout.

	Returns the outbound reply text so the REPL can print it.

	The actual agent work happens in `friday_core.gateway.service.handle_inbound`
	(which fires synchronously via `doc_events.after_insert` while we're
	inside `insert()` below). By the time `insert()` returns, the gateway
	has already written the outbound row.
	"""
	_ensure_cli_platform_record()

	inbound = _write_inbound(
		profile_name=profile_name,
		session_id=session_id,
		content=content,
	)

	# Commit so the gateway's outbound write and our subsequent read
	# both see the consistent state. Frappe defers commits to request
	# boundaries; in a long-lived CLI we have to commit explicitly.
	frappe.db.commit()

	# The gateway ran sync during insert() above and wrote the outbound
	# row. Read it back. Filter by session + direction + "created after
	# our inbound" so we always pick THIS turn's outbound, not a prior
	# one in the same session.
	outbound_content = _read_latest_outbound(session_id, after_creation=inbound.creation)
	if outbound_content is None:
		# Shouldn't happen — the gateway always writes either a real
		# reply or a system-error outbound. If we somehow got here,
		# surface a clear error.
		return "(no reply was produced — check the Frappe Error Log)"
	return outbound_content


# ---------------------------------------------------------------------------
# Public REPL — the thing `bench friday chat` calls
# ---------------------------------------------------------------------------


def run_repl(profile_name: str) -> None:
	"""Run the interactive chat REPL until EOF, Ctrl+D, or `exit`.

	Each line of input becomes one inbound Chat Message. The gateway
	processes it and writes an outbound row. The REPL reads and prints
	the outbound.

	A session_id is generated at REPL start and reused for the lifetime
	of this REPL invocation. Sessions are ephemeral — closing the CLI
	ends the session. The messages persist in Frappe for audit.

	Errors during a turn (gateway crash, DB failure) are caught and
	printed inline — we don't want a single bad turn to kill the whole
	conversation.
	"""
	# Validate the profile exists upfront so the user gets a clean
	# error before we open a session and prompt them.
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
			frappe.log_error(title="friday chat turn failure")
			print(f"[error] {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _ensure_cli_platform_record() -> None:
	"""Idempotently create the 'cli' Chat Platform row on first use.

	A fresh `bench new-site` has no Chat Platform records. Rather than
	require an install step, we check-and-create on the first chat
	turn. Subsequent turns find it and skip.

	The "cli" record has `dispatch_mode="sync"` so the gateway runs
	in-line with the inbound row's insert() call.
	"""
	if frappe.db.exists("Chat Platform", CLI_PLATFORM_NAME):
		return
	frappe.get_doc(
		{
			"doctype": "Chat Platform",
			"platform_name": CLI_PLATFORM_NAME,
			"adapter_module": CLI_ADAPTER_MODULE,
			"enabled": 1,
			"dispatch_mode": "sync",
			# CLI doesn't use the default — `--profile` is always provided.
			"default_agent_profile": None,
			# CLI doesn't batch — flush immediately. (Field unused by the
			# v0.1 batching stub; reserved for when real batching lands.)
			"batch_idle_ms": 0,
		}
	).insert(ignore_permissions=True)


def _write_inbound(profile_name: str, session_id: str, content: str):
	"""Insert one inbound Chat Message row. Returns the inserted doc.

	The gateway's `doc_events.after_insert` hook fires synchronously
	inside this call (because the platform's dispatch_mode is "sync").
	By the time this returns, the outbound row already exists.

	`ignore_permissions=True` for the same reason the gateway uses it:
	this is system plumbing recording its own state.
	"""
	doc = frappe.get_doc(
		{
			"doctype": "Chat Message",
			"session_id": session_id,
			"platform": CLI_PLATFORM_NAME,
			"direction": "inbound",
			"sender_id": _current_user_label(),
			"agent_profile": profile_name,
			"content": content,
			"timestamp": frappe.utils.now_datetime(),
			"processed": 0,  # gateway flips to 1 after writing outbound
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def _read_latest_outbound(session_id: str, after_creation) -> str | None:
	"""Read the outbound Chat Message produced for this turn.

	Filters by session + direction=outbound + creation > the inbound's
	creation. Returns the content, or None if no outbound was found
	(which shouldn't happen — the gateway always writes one).
	"""
	rows = frappe.get_all(
		"Chat Message",
		filters={
			"session_id": session_id,
			"direction": "outbound",
			"creation": (">=", after_creation),
		},
		fields=["content"],
		order_by="creation desc",
		limit=1,
	)
	return rows[0]["content"] if rows else None


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
