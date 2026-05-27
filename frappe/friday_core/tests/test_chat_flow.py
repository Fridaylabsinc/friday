# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
Tests for the Slice 4 chat flow (CLI ↔ DB ↔ stub agent).

PLAIN ENGLISH
=============

These tests prove the chat turn handler does what it claims:

  1. Writes an inbound Chat Message row when a user types something.
  2. Calls the stub agent runner (which calls Slice 3's loader).
  3. Writes an outbound Chat Message row with the agent's reply.
  4. Returns the reply text to the caller (the REPL).
  5. Both rows share the same `session_id`.
  6. The 'cli' Chat Platform record gets created on first use.

We do NOT test the REPL loop's stdin/stdout directly — that's a
prompt-driven loop and testing it requires either input mocking or a
subprocess. Instead we test `handle_user_message` (the function the
REPL calls per turn) and `run_turn` (the function the handler calls).
Same coverage, no flaky I/O.

TEST DATA
=========

We reuse the Slice 2/3 test Role + a profile with permitted_skills.
That way the stub's `load_for_profile()` call returns a non-empty
list and we can verify the reply mentions tool count.

HOW TO RUN
==========

    bench --site friday.localhost run-tests \\
        --module frappe.friday_core.tests.test_chat_flow
"""

from __future__ import annotations

import unittest
import uuid

import frappe

from frappe.friday_core.agent_runner.runner import run_turn
from frappe.friday_core.cli.chat import (
	CLI_PLATFORM_NAME,
	handle_user_message,
)

TARGET_DOCTYPE = "Note"
TEST_ROLE = "Friday Test Reader"
PROFILE_WITH_TOOLS = "FRIDAY-SLICE4-PROFILE-TOOLS"
PROFILE_NO_TOOLS = "FRIDAY-SLICE4-PROFILE-NO-TOOLS"
SKILL_NAME = "slice4-skill"


def _ensure_role():
	"""Same Role + DocPerm pattern as Slice 2 / Slice 3 tests."""
	if not frappe.db.exists("Role", TEST_ROLE):
		frappe.get_doc({"doctype": "Role", "role_name": TEST_ROLE}).insert(ignore_permissions=True)
	if not frappe.db.exists("Custom DocPerm", {"parent": TARGET_DOCTYPE, "role": TEST_ROLE}):
		frappe.get_doc(
			{
				"doctype": "Custom DocPerm",
				"parent": TARGET_DOCTYPE,
				"parenttype": "DocType",
				"parentfield": "permissions",
				"role": TEST_ROLE,
				"read": 1,
				"permlevel": 0,
			}
		).insert(ignore_permissions=True)


def _ensure_skill():
	"""Active skill that needs read on Note."""
	if frappe.db.exists("Skill", SKILL_NAME):
		skill = frappe.get_doc("Skill", SKILL_NAME)
		skill.status = "Active"
		skill.required_doctypes = []
		skill.append("required_doctypes", {"target_doctype": TARGET_DOCTYPE, "operation": "read"})
		skill.save(ignore_permissions=True)
		return
	frappe.get_doc(
		{
			"doctype": "Skill",
			"skill_name": SKILL_NAME,
			"description": "Slice 4 test skill",
			"risk_level": "low",
			"status": "Active",
			"required_doctypes": [{"target_doctype": TARGET_DOCTYPE, "operation": "read"}],
		}
	).insert(ignore_permissions=True)


def _ensure_profile(name: str, with_skill: bool):
	"""Profile with the test role and (optionally) the test skill on its allow-list."""
	skills = [SKILL_NAME] if with_skill else []
	if frappe.db.exists("Agent Profile", name):
		profile = frappe.get_doc("Agent Profile", name)
		profile.status = "Active"
		profile.assigned_roles = []
		profile.permitted_skills = []
		profile.append("assigned_roles", {"role": TEST_ROLE})
		for s in skills:
			profile.append("permitted_skills", {"skill": s})
		profile.save(ignore_permissions=True)
		return
	frappe.get_doc(
		{
			"doctype": "Agent Profile",
			"profile_name": name,
			"status": "Active",
			"requires_approval_above_risk": "high",
			"assigned_roles": [{"role": TEST_ROLE}],
			"permitted_skills": [{"skill": s} for s in skills],
		}
	).insert(ignore_permissions=True)


class TestChatFlow(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		_ensure_role()
		_ensure_skill()
		_ensure_profile(PROFILE_WITH_TOOLS, with_skill=True)
		_ensure_profile(PROFILE_NO_TOOLS, with_skill=False)
		frappe.db.commit()

	def setUp(self):
		# Cold caches so test order doesn't matter.
		frappe.cache().delete_keys("friday:skills:")
		frappe.cache().delete_keys("friday:perm_matrix:")

	# ------- the stub runner -------

	def test_run_turn_pure_function_returns_reply_with_tool_count(self):
		"""`run_turn` is pure: no DB writes, deterministic reply."""
		before = frappe.db.count("Chat Message")
		reply = run_turn(PROFILE_WITH_TOOLS, "session-pure", "hello")
		after = frappe.db.count("Chat Message")

		self.assertEqual(before, after, "run_turn must NOT write Chat Message rows")
		self.assertIn("tool(s) available", reply)
		self.assertIn(SKILL_NAME, reply)
		self.assertIn("echo: hello", reply)

	def test_run_turn_with_no_tools_says_none(self):
		reply = run_turn(PROFILE_NO_TOOLS, "session-empty", "hi")
		self.assertIn("0 tool(s) available", reply)
		self.assertIn("(none)", reply)

	# ------- the turn handler -------

	def test_handle_user_message_writes_inbound_row(self):
		session_id = str(uuid.uuid4())
		handle_user_message(PROFILE_WITH_TOOLS, session_id, "alpha")

		rows = frappe.get_all(
			"Chat Message",
			filters={"session_id": session_id, "direction": "inbound"},
			fields=["name", "content", "agent_profile", "platform"],
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["content"], "alpha")
		self.assertEqual(rows[0]["agent_profile"], PROFILE_WITH_TOOLS)
		self.assertEqual(rows[0]["platform"], CLI_PLATFORM_NAME)

	def test_handle_user_message_writes_outbound_row(self):
		session_id = str(uuid.uuid4())
		reply = handle_user_message(PROFILE_WITH_TOOLS, session_id, "beta")

		rows = frappe.get_all(
			"Chat Message",
			filters={"session_id": session_id, "direction": "outbound"},
			fields=["name", "content", "sender_id"],
		)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["content"], reply)
		self.assertEqual(rows[0]["sender_id"], PROFILE_WITH_TOOLS)
		self.assertIn("echo: beta", reply)

	def test_handle_user_message_session_id_shared_across_directions(self):
		session_id = str(uuid.uuid4())
		handle_user_message(PROFILE_WITH_TOOLS, session_id, "gamma")

		count = frappe.db.count("Chat Message", filters={"session_id": session_id})
		self.assertEqual(count, 2, "one turn should produce exactly one inbound + one outbound row")

	def test_handle_user_message_creates_cli_platform_record_on_first_use(self):
		# Force-delete the platform row if a prior test created it, so we
		# exercise the create branch. `force=1` bypasses the LinkExistsError
		# that would otherwise fire because existing Chat Message rows
		# reference this platform — for test isolation, that's exactly
		# the cascade we want.
		if frappe.db.exists("Chat Platform", CLI_PLATFORM_NAME):
			frappe.delete_doc(
				"Chat Platform",
				CLI_PLATFORM_NAME,
				ignore_permissions=True,
				force=1,
			)
		self.assertFalse(frappe.db.exists("Chat Platform", CLI_PLATFORM_NAME))

		handle_user_message(PROFILE_WITH_TOOLS, str(uuid.uuid4()), "first-call")

		self.assertTrue(frappe.db.exists("Chat Platform", CLI_PLATFORM_NAME))
		platform = frappe.get_doc("Chat Platform", CLI_PLATFORM_NAME)
		self.assertEqual(platform.adapter_module, "frappe.friday_core.cli.chat")
		self.assertEqual(platform.enabled, 1)

	def test_handle_user_message_returns_reply_text(self):
		"""The return value is the same string written to the outbound row."""
		session_id = str(uuid.uuid4())
		reply = handle_user_message(PROFILE_WITH_TOOLS, session_id, "delta")
		# Sanity: returned string equals the persisted outbound content.
		stored = frappe.db.get_value(
			"Chat Message",
			{"session_id": session_id, "direction": "outbound"},
			"content",
		)
		self.assertEqual(reply, stored)

	def test_handle_user_message_round_trip_under_one_second(self):
		"""Latency budget: <1s on local dev. Stub runner should be ~10ms."""
		import time

		session_id = str(uuid.uuid4())
		start = time.perf_counter()
		handle_user_message(PROFILE_WITH_TOOLS, session_id, "perf check")
		elapsed = time.perf_counter() - start

		self.assertLess(elapsed, 1.0, f"round-trip should be <1s, got {elapsed:.3f}s")
