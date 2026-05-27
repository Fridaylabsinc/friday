# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""Permission Decision Log writer.

Every permission check — allow or deny — produces one immutable row.
The matrix snapshot is captured so the decision is reproducible even after
roles or skills change later.
"""

from __future__ import annotations

import frappe

from frappe.friday_core.permissions.matrix import Decision, PermissionMatrix


def record(
	profile_name: str,
	skill_name: str,
	decision: Decision,
	matrix: PermissionMatrix,
) -> str:
	"""Insert and submit a Permission Decision Log row. Returns the docname."""
	doc = frappe.get_doc(
		{
			"doctype": "Permission Decision Log",
			"agent_profile": profile_name,
			"skill": skill_name,
			"decision": "allowed" if decision.allowed else "denied",
			"reason": decision.reason,
			"matrix_snapshot": frappe.as_json(matrix.to_dict()),
			"decided_at": frappe.utils.now_datetime(),
		}
	)
	doc.insert(ignore_permissions=True)
	doc.submit()
	return doc.name
