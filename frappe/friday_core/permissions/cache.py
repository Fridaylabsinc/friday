# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""Redis-backed cache for permission matrices.

Key shape:    friday:perm_matrix:{profile_name}
TTL:          60 seconds
Invalidation: Agent Profile.on_update flushes that profile;
              Role.on_update flushes every profile (broad change in role perms).
"""

from __future__ import annotations

import json

import frappe

from frappe.friday_core.permissions.matrix import PermissionMatrix

CACHE_KEY_PREFIX = "friday:perm_matrix:"
CACHE_TTL_SECONDS = 60


def _key(profile_name: str) -> str:
	return f"{CACHE_KEY_PREFIX}{profile_name}"


def get(profile_name: str) -> PermissionMatrix | None:
	raw = frappe.cache().get_value(_key(profile_name))
	if raw is None:
		return None
	try:
		data = json.loads(raw) if isinstance(raw, str | bytes | bytearray) else raw
		return PermissionMatrix.from_dict(data)
	except (json.JSONDecodeError, KeyError, TypeError) as exc:
		# Corrupt entry: drop it and treat as miss. Log so we notice if it's frequent.
		frappe.logger().warning(f"friday.permissions.cache: dropping corrupt entry for {profile_name!r}: {exc}")
		frappe.cache().delete_value(_key(profile_name))
		return None


def set(profile_name: str, matrix: PermissionMatrix) -> None:
	frappe.cache().set_value(
		_key(profile_name),
		json.dumps(matrix.to_dict()),
		expires_in_sec=CACHE_TTL_SECONDS,
	)


def invalidate_for_profile(doc, method=None) -> None:
	"""Hook target on Agent Profile.on_update — flush this profile's matrix."""
	profile_name = getattr(doc, "name", None) or str(doc)
	frappe.cache().delete_value(_key(profile_name))


def invalidate_all(doc=None, method=None) -> None:
	"""Hook target on Role.on_update — a role-perm change can affect every profile."""
	frappe.cache().delete_keys(CACHE_KEY_PREFIX)
