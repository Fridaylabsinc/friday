# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
Tests for the runner's tool-call detection and dispatching logic.

These tests verify the Slice 6 integration between runner.py and
dispatcher.py — specifically that the runner correctly:
  1. Detects tool_calls in the LLM response.
  2. Dispatches the first tool call to the dispatcher.
  3. Returns the dispatch result's content as the agent reply.
  4. Falls back to plain text when no tool calls are present.
  5. Handles multiple tool calls by dispatching only the first.
  6. Propagates errors from the dispatcher in the reply text.

These are UNIT tests with the LLM provider fully mocked. The tests
exercise the runner's logic without making any real LLM API calls.
"""

import unittest
from unittest.mock import patch, MagicMock

import frappe
from frappe.friday_core.agent_runner.runner import run_turn
from frappe.friday_core.agent_runner.dispatcher import DispatchResult

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_ROLE = "Friday Slice6 Runner Test Role"
SKILL_NAME = "slice6-create-note"
PROFILE_NAME = "FRIDAY-SLICE6-RUNNER-TEST-PROFILE"
LLM_PROVIDER_NAME = "friday-slice6-runner-test-provider"
TARGET_DOCTYPE = "Note"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _ensure_role():
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
                "create": 1,
                "permlevel": 0,
            }
        ).insert(ignore_permissions=True)


def _ensure_skill():
    if frappe.db.exists("Skill", SKILL_NAME):
        skill = frappe.get_doc("Skill", SKILL_NAME)
        skill.status = "Active"
        skill.risk_level = "low"
        skill.required_doctypes = []
        skill.append("required_doctypes", {"target_doctype": TARGET_DOCTYPE, "operation": "create"})
        skill.save(ignore_permissions=True)
        return
    frappe.get_doc(
        {
            "doctype": "Skill",
            "skill_name": SKILL_NAME,
            "description": "Slice 6 runner test skill",
            "risk_level": "low",
            "status": "Active",
            "required_doctypes": [{"target_doctype": TARGET_DOCTYPE, "operation": "create"}],
        }
    ).insert(ignore_permissions=True)


def _ensure_profile():
    if frappe.db.exists("Agent Profile", PROFILE_NAME):
        profile = frappe.get_doc("Agent Profile", PROFILE_NAME)
        profile.status = "Active"
        profile.assigned_roles = []
        profile.permitted_skills = []
        profile.append("assigned_roles", {"role": TEST_ROLE})
        profile.append("permitted_skills", {"skill": SKILL_NAME})
        profile.save(ignore_permissions=True)
        return
    frappe.get_doc(
        {
            "doctype": "Agent Profile",
            "profile_name": PROFILE_NAME,
            "status": "Active",
            "requires_approval_above_risk": "high",
            "assigned_roles": [{"role": TEST_ROLE}],
            "permitted_skills": [{"skill": SKILL_NAME}],
        }
    ).insert(ignore_permissions=True)


def _ensure_llm_provider():
    if frappe.db.exists("LLM Provider", LLM_PROVIDER_NAME):
        return
    frappe.get_doc(
        {
            "doctype": "LLM Provider",
            "provider_name": LLM_PROVIDER_NAME,
            "provider_type": "minimax",
            "is_active": 1,
            "api_key": "test-runner-key",
        }
    ).insert(ignore_permissions=True, ignore_mandatory=True)


def _link_provider_to_profile():
    profile = frappe.get_doc("Agent Profile", PROFILE_NAME)
    profile.llm_provider = LLM_PROVIDER_NAME
    profile.save(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestRunnerToolCallDetection(unittest.TestCase):
    """runner.py correctly detects tool_calls and dispatches to dispatcher."""

    @classmethod
    def setUpClass(cls):
        frappe.db.rollback()
        _ensure_role()
        _ensure_llm_provider()
        _ensure_skill()
        _ensure_profile()
        _link_provider_to_profile()
        frappe.db.commit()

    def setUp(self):
        frappe.db.sql("DELETE FROM `tabExecution Log` WHERE agent_profile=%s", (PROFILE_NAME,))
        frappe.db.sql("DELETE FROM `tabNote` WHERE title LIKE 'slice6-runner-%'")
        # Don't invalidate the loader cache here — we want the profile's
        # cached matrix to persist so the permission check finds our role.
        # frappe.db.commit()

    @classmethod
    def tearDownClass(cls):
        from frappe.friday_core.skills.loader import invalidate_for_profile
        invalidate_for_profile(PROFILE_NAME)
        frappe.db.sql("DELETE FROM `tabExecution Log` WHERE agent_profile=%s", (PROFILE_NAME,))
        frappe.db.sql("DELETE FROM `tabNote` WHERE title LIKE 'slice6-runner-%'")
        frappe.db.commit()

    def test_no_tool_calls_returns_content_directly(self):
        """When LLM response has no tool_calls, runner returns content as-is."""
        fake_response = {
            "content": "Hello! How can I help you today?",
            "finish_reason": "stop",
            "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18},
            "tool_calls": None,
        }

        mock_provider = MagicMock()
        mock_provider.chat.return_value = fake_response

        with patch(
            "frappe.friday_core.agent_runner.runner.get_provider_for_profile",
            return_value=mock_provider,
        ):
            result = run_turn(
                profile_name=PROFILE_NAME,
                session_id="sess-runner-001",
                inbound_content="Hello there",
            )

        self.assertEqual(result, "Hello! How can I help you today?")

    def test_tool_call_triggers_dispatch_and_returns_result(self):
        """When LLM returns tool_calls, runner dispatches first one and returns result."""
        fake_response = {
            "content": "",
            "finish_reason": "tool_calls",
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            "tool_calls": [
                {
                    "id": "call_abc123",
                    "name": SKILL_NAME,
                    "arguments": '{"title": "slice6-runner-note", "content": "Dispatched via runner"}',
                }
            ],
        }

        mock_provider = MagicMock()
        mock_provider.chat.return_value = fake_response

        with patch(
            "frappe.friday_core.agent_runner.runner.get_provider_for_profile",
            return_value=mock_provider,
        ):
            result = run_turn(
                profile_name=PROFILE_NAME,
                session_id="sess-runner-002",
                inbound_content="Create a note about the meeting",
            )

        # The dispatcher creates a Note and returns the note title in content.
        self.assertIn("slice6-runner-note", result)
        # Verify the Note was actually created in DB.
        exists = frappe.db.exists("Note", {"title": "slice6-runner-note"})
        self.assertTrue(exists, "Note should have been created by the create_note handler")

    def test_dispatch_success_returns_note_title(self):
        """When dispatch succeeds, runner returns the result content."""
        tool_call = {
            "id": "call_xyz",
            "name": SKILL_NAME,
            "arguments": '{"title": "slice6-runner-my-note", "content": "Test"}',
        }

        fake_response = {
            "content": "",
            "finish_reason": "tool_calls",
            "usage": {"total_tokens": 50},
            "tool_calls": [tool_call],
        }

        mock_provider = MagicMock()
        mock_provider.chat.return_value = fake_response

        with patch(
            "frappe.friday_core.agent_runner.runner.get_provider_for_profile",
            return_value=mock_provider,
        ):
            result = run_turn(
                profile_name=PROFILE_NAME,
                session_id="sess-runner-003",
                inbound_content="Create a note",
            )

        # The dispatcher should have created the note and runner returns the result.
        self.assertIn("slice6-runner-my-note", result)
        exists = frappe.db.exists("Note", {"title": "slice6-runner-my-note"})
        self.assertTrue(exists)

    def test_permission_denied_returns_denial_message(self):
        """When permission is denied, runner returns the denial message."""
        fake_response = {
            "content": "",
            "finish_reason": "tool_calls",
            "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
            "tool_calls": [
                {
                    "id": "call_denied_001",
                    "name": SKILL_NAME,
                    "arguments": '{"title": "should-not-be-created"}',
                }
            ],
        }

        mock_provider = MagicMock()
        mock_provider.chat.return_value = fake_response

        # Revoke the role from the profile so permission is denied.
        profile = frappe.get_doc("Agent Profile", PROFILE_NAME)
        profile.assigned_roles = []
        profile.save(ignore_permissions=True)
        from frappe.friday_core.skills.loader import invalidate_for_profile
        invalidate_for_profile(PROFILE_NAME)

        try:
            with patch(
                "frappe.friday_core.agent_runner.runner.get_provider_for_profile",
                return_value=mock_provider,
            ):
                result = run_turn(
                    profile_name=PROFILE_NAME,
                    session_id="sess-runner-004",
                    inbound_content="Create a note",
                )

            self.assertIn("permission", result.lower())
            # Note should NOT have been created.
            exists = frappe.db.exists("Note", {"title": "should-not-be-created"})
            self.assertFalse(exists)
        finally:
            # Restore the role so subsequent tests still have permissions.
            profile.reload()
            profile.append("assigned_roles", {"role": TEST_ROLE})
            profile.save(ignore_permissions=True)
            invalidate_for_profile(PROFILE_NAME)

    def test_multiple_tool_calls_dispatches_first_only(self):
        """When LLM returns multiple tool calls, runner dispatches only the first."""
        call_log = []

        fake_response = {
            "content": "",
            "finish_reason": "tool_calls",
            "usage": {"prompt_tokens": 50, "completion_tokens": 20, "total_tokens": 70},
            "tool_calls": [
                {
                    "id": "call_first",
                    "name": SKILL_NAME,
                    "arguments": '{"title": "slice6-runner-first-note"}',
                },
                {
                    "id": "call_second",
                    "name": SKILL_NAME,
                    "arguments": '{"title": "slice6-runner-second-note"}',
                },
            ],
        }

        mock_provider = MagicMock()
        mock_provider.chat.return_value = fake_response

        def track_dispatch(**kwargs):
            call_log.append(kwargs)
            return DispatchResult(
                success=True,
                content="OK",
                execution_log_name="log-multi",
                tool_call_name=kwargs["tool_call"]["name"],
                tool_call_id=kwargs["tool_call"]["id"],
            )

        with patch(
            "frappe.friday_core.agent_runner.runner.get_provider_for_profile",
            return_value=mock_provider,
        ):
            with patch(
                "frappe.friday_core.agent_runner.dispatcher.dispatch",
                side_effect=track_dispatch,
            ):
                result = run_turn(
                    profile_name=PROFILE_NAME,
                    session_id="sess-runner-005",
                    inbound_content="Create two notes",
                )

        # Only one dispatch should have happened.
        self.assertEqual(len(call_log), 1, "Only the first tool call should be dispatched")
        # The dispatched tool call should be the first one.
        self.assertEqual(call_log[0]["tool_call"]["id"], "call_first")

    def test_dispatch_error_returns_error_content(self):
        """When the dispatcher returns an error result, runner propagates it."""
        fake_response = {
            "content": "",
            "finish_reason": "tool_calls",
            "usage": {"prompt_tokens": 50, "completion_tokens": 15, "total_tokens": 65},
            "tool_calls": [
                {
                    "id": "call_err",
                    "name": "nonexistent-skill-xyz",
                    "arguments": "{}",
                }
            ],
        }

        mock_provider = MagicMock()
        mock_provider.chat.return_value = fake_response

        with patch(
            "frappe.friday_core.agent_runner.runner.get_provider_for_profile",
            return_value=mock_provider,
        ):
            result = run_turn(
                profile_name=PROFILE_NAME,
                session_id="sess-runner-006",
                inbound_content="Do something impossible",
            )

        self.assertIn("doesn't exist", result)


if __name__ == "__main__":
    unittest.main()