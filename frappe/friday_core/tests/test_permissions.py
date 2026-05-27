# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""Tests for the Slice 2 permission engine.

Covers:
- Allow: profile has a role with the operation on the required DocType.
- Deny: profile lacks the role / operation.
- Deny: Skill status is not Active (Draft, Experimental, Retired, Archived).
- Deny: Agent Profile status is not Active.
- Cache: miss populates, hit reuses, invalidation drops.
- Decision log is written on every check.
"""

from __future__ import annotations

import unittest

import frappe

from frappe.friday_core.permissions import cache as cache_module
from frappe.friday_core.permissions import matrix as matrix_module
from frappe.friday_core.permissions.matrix import (
	Decision,
	PermissionMatrix,
	build_matrix,
	check,
	evaluate,
)

TARGET_DOCTYPE = "Note"
TEST_ROLE = "Friday Test Reader"
PROFILE_WITH_ROLE = "FRIDAY-TEST-PROFILE-A"
PROFILE_WITHOUT_ROLE = "FRIDAY-TEST-PROFILE-B"
PROFILE_SUSPENDED = "FRIDAY-TEST-PROFILE-SUSPENDED"
SKILL_ACTIVE = "friday-test-skill-active"
SKILL_DRAFT = "friday-test-skill-draft"
SKILL_RETIRED = "friday-test-skill-retired"
SKILL_ARCHIVED = "friday-test-skill-archived"


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
				"read": 1,
				"permlevel": 0,
			}
		).insert(ignore_permissions=True)


def _ensure_profile(name: str, roles: list[str], status: str = "Active"):
	if frappe.db.exists("Agent Profile", name):
		profile = frappe.get_doc("Agent Profile", name)
		profile.status = status
		profile.assigned_roles = []
		for role in roles:
			profile.append("assigned_roles", {"role": role})
		profile.save(ignore_permissions=True)
		return
	doc = frappe.get_doc(
		{
			"doctype": "Agent Profile",
			"profile_name": name,
			"status": status,
			"requires_approval_above_risk": "high",
			"assigned_roles": [{"role": r} for r in roles],
		}
	)
	doc.insert(ignore_permissions=True)


def _ensure_skill(name: str, status: str, operation: str = "read"):
	if frappe.db.exists("Skill", name):
		skill = frappe.get_doc("Skill", name)
		skill.status = status
		skill.required_doctypes = []
		skill.append("required_doctypes", {"target_doctype": TARGET_DOCTYPE, "operation": operation})
		skill.save(ignore_permissions=True)
		return
	doc = frappe.get_doc(
		{
			"doctype": "Skill",
			"skill_name": name,
			"description": f"Friday test skill ({status})",
			"risk_level": "low",
			"status": status,
			"required_doctypes": [{"target_doctype": TARGET_DOCTYPE, "operation": operation}],
		}
	)
	doc.insert(ignore_permissions=True)


class TestPermissionMatrix(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		_ensure_role()
		_ensure_profile(PROFILE_WITH_ROLE, [TEST_ROLE], status="Active")
		_ensure_profile(PROFILE_WITHOUT_ROLE, [], status="Active")
		_ensure_profile(PROFILE_SUSPENDED, [TEST_ROLE], status="Suspended")
		_ensure_skill(SKILL_ACTIVE, "Active")
		_ensure_skill(SKILL_DRAFT, "Draft")
		_ensure_skill(SKILL_RETIRED, "Retired")
		_ensure_skill(SKILL_ARCHIVED, "Archived")
		frappe.db.commit()

	def setUp(self):
		# Each test starts with a cold cache so cache-hit vs miss is deterministic.
		frappe.cache().delete_keys(cache_module.CACHE_KEY_PREFIX)

	# ------- evaluate(): pure logic, the branch-coverage target -------

	def test_allow_when_profile_has_role_and_skill_active(self):
		matrix = build_matrix(PROFILE_WITH_ROLE)
		decision = evaluate(matrix, SKILL_ACTIVE)
		self.assertTrue(decision.allowed, decision.reason)

	def test_deny_when_profile_lacks_role(self):
		matrix = build_matrix(PROFILE_WITHOUT_ROLE)
		decision = evaluate(matrix, SKILL_ACTIVE)
		self.assertFalse(decision.allowed)
		self.assertIn("lacks", decision.reason)
		self.assertIn(TARGET_DOCTYPE, decision.reason)

	def test_deny_when_profile_not_active(self):
		matrix = build_matrix(PROFILE_SUSPENDED)
		decision = evaluate(matrix, SKILL_ACTIVE)
		self.assertFalse(decision.allowed)
		self.assertIn("Suspended", decision.reason)

	def test_deny_when_skill_status_not_active(self):
		matrix = build_matrix(PROFILE_WITH_ROLE)
		for skill_name, expected_status in (
			(SKILL_DRAFT, "Draft"),
			(SKILL_RETIRED, "Retired"),
			(SKILL_ARCHIVED, "Archived"),
		):
			with self.subTest(skill=skill_name):
				decision = evaluate(matrix, skill_name)
				self.assertFalse(decision.allowed)
				self.assertIn(expected_status, decision.reason)
				self.assertIn("not Active", decision.reason)

	# ------- cache behaviour -------

	def test_cache_miss_then_hit(self):
		self.assertIsNone(cache_module.get(PROFILE_WITH_ROLE), "cold cache should miss")
		matrix_first = build_matrix(PROFILE_WITH_ROLE)
		cached = cache_module.get(PROFILE_WITH_ROLE)
		self.assertIsNotNone(cached, "build_matrix should populate the cache")
		self.assertEqual(cached.to_dict(), matrix_first.to_dict())

		matrix_second = build_matrix(PROFILE_WITH_ROLE)
		self.assertEqual(matrix_first.to_dict(), matrix_second.to_dict())

	def test_invalidate_for_profile_drops_only_that_key(self):
		build_matrix(PROFILE_WITH_ROLE)
		build_matrix(PROFILE_WITHOUT_ROLE)
		self.assertIsNotNone(cache_module.get(PROFILE_WITH_ROLE))
		self.assertIsNotNone(cache_module.get(PROFILE_WITHOUT_ROLE))

		profile = frappe.get_doc("Agent Profile", PROFILE_WITH_ROLE)
		cache_module.invalidate_for_profile(profile)

		self.assertIsNone(cache_module.get(PROFILE_WITH_ROLE), "target profile should be flushed")
		self.assertIsNotNone(cache_module.get(PROFILE_WITHOUT_ROLE), "other profiles must not be touched")

	def test_invalidate_all_drops_every_profile_key(self):
		build_matrix(PROFILE_WITH_ROLE)
		build_matrix(PROFILE_WITHOUT_ROLE)
		cache_module.invalidate_all()
		self.assertIsNone(cache_module.get(PROFILE_WITH_ROLE))
		self.assertIsNone(cache_module.get(PROFILE_WITHOUT_ROLE))

	# ------- public check() writes a decision log row -------

	def test_check_writes_permission_decision_log_on_allow(self):
		before = frappe.db.count("Permission Decision Log")
		decision = check(PROFILE_WITH_ROLE, SKILL_ACTIVE)
		self.assertTrue(decision.allowed)
		after = frappe.db.count("Permission Decision Log")
		self.assertEqual(after, before + 1)

	def test_check_writes_permission_decision_log_on_deny(self):
		before = frappe.db.count("Permission Decision Log")
		decision = check(PROFILE_WITHOUT_ROLE, SKILL_ACTIVE)
		self.assertFalse(decision.allowed)
		after = frappe.db.count("Permission Decision Log")
		self.assertEqual(after, before + 1)

	# ------- PermissionMatrix round-trip -------

	def test_matrix_dict_round_trip(self):
		matrix = build_matrix(PROFILE_WITH_ROLE)
		restored = PermissionMatrix.from_dict(matrix.to_dict())
		self.assertEqual(matrix, restored)
