# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""Permission matrix and decision engine for the Friday gateway pre-check.

Public entrypoints:
- build_matrix(profile_name) -> PermissionMatrix
- check(profile_name, skill_name) -> Decision    # logs the decision
- evaluate(matrix, skill_name) -> Decision       # pure, no side effects

See docs/design/04-security-model.md Layer 2 and
docs/design/10-agent-execution-guide.md Slice 2 for the specification.
"""

from __future__ import annotations

from dataclasses import dataclass

import frappe

# Mapping of Skill Required DocType.operation values to DocPerm column names.
_OP_TO_PERM_FIELD = {
	"read": "read",
	"write": "write",
	"create": "create",
	"submit": "submit",
	"cancel": "cancel",
	"delete": "delete",
}


@dataclass(frozen=True)
class Decision:
	allowed: bool
	reason: str

	def to_dict(self) -> dict:
		return {"allowed": self.allowed, "reason": self.reason}

	# Honored by frappe.utils.response.json_handler so `bench execute` can serialize.
	def __json__(self) -> dict:
		return self.to_dict()


@dataclass(frozen=True)
class PermissionMatrix:
	profile_name: str
	profile_status: str
	roles: tuple[str, ...]
	# {doctype_name: frozenset of permitted operation names}
	permitted_ops: dict[str, frozenset[str]]

	def ops_for(self, doctype: str) -> frozenset[str]:
		return self.permitted_ops.get(doctype, frozenset())

	def to_dict(self) -> dict:
		return {
			"profile_name": self.profile_name,
			"profile_status": self.profile_status,
			"roles": list(self.roles),
			"permitted_ops": {dt: sorted(ops) for dt, ops in self.permitted_ops.items()},
		}

	def __json__(self) -> dict:
		return self.to_dict()

	@classmethod
	def from_dict(cls, data: dict) -> PermissionMatrix:
		return cls(
			profile_name=data["profile_name"],
			profile_status=data["profile_status"],
			roles=tuple(data["roles"]),
			permitted_ops={dt: frozenset(ops) for dt, ops in data["permitted_ops"].items()},
		)


def build_matrix(profile_name: str) -> PermissionMatrix:
	"""Return the permission matrix for an Agent Profile, cache-aware.

	Reads from the Redis-backed cache when present; otherwise resolves the
	profile + assigned roles + DocPerm rows and stores the result.
	"""
	from frappe.friday_core.permissions import cache

	cached = cache.get(profile_name)
	if cached is not None:
		return cached

	matrix = _build_matrix_uncached(profile_name)
	cache.set(profile_name, matrix)
	return matrix


def _build_matrix_uncached(profile_name: str) -> PermissionMatrix:
	profile = frappe.get_doc("Agent Profile", profile_name)
	roles = tuple(sorted({row.role for row in (profile.assigned_roles or []) if row.role}))
	return PermissionMatrix(
		profile_name=profile.name,
		profile_status=profile.status,
		roles=roles,
		permitted_ops=_resolve_permitted_ops(roles),
	)


def _resolve_permitted_ops(roles: tuple[str, ...]) -> dict[str, frozenset[str]]:
	"""Aggregate {doctype: {operations}} across DocPerm + Custom DocPerm for the role set."""
	if not roles:
		return {}

	per_doctype: dict[str, set[str]] = {}
	for table in ("DocPerm", "Custom DocPerm"):
		rows = frappe.get_all(
			table,
			filters={"role": ("in", roles)},
			fields=["parent", *_OP_TO_PERM_FIELD.values()],
		)
		for row in rows:
			doctype = row["parent"]
			ops = per_doctype.setdefault(doctype, set())
			for op_name, perm_field in _OP_TO_PERM_FIELD.items():
				if row.get(perm_field):
					ops.add(op_name)

	return {dt: frozenset(ops) for dt, ops in per_doctype.items()}


def evaluate(matrix: PermissionMatrix, skill_name: str) -> Decision:
	"""Pure permission decision. No I/O, no side effects. The branch-coverage target."""
	if matrix.profile_status != "Active":
		return Decision(False, f"Agent Profile is {matrix.profile_status!r}, not Active")

	skill = frappe.get_doc("Skill", skill_name)
	if skill.status != "Active":
		return Decision(False, f"Skill is {skill.status!r}, not Active")

	for req in skill.required_doctypes or []:
		op = req.operation
		permitted = matrix.ops_for(req.target_doctype)
		if op not in permitted:
			return Decision(
				False,
				f"Profile lacks {op!r} on {req.target_doctype!r} (roles={list(matrix.roles)})",
			)

	return Decision(True, "Allowed")


def check(profile_name: str, skill_name: str) -> Decision:
	"""Public gateway pre-check. Builds matrix, evaluates, logs the decision.

	The deliverable command:
	    bench execute frappe.friday_core.permissions.matrix.check \
	        --args "['profile_a', 'create_note']"
	"""
	from frappe.friday_core.permissions import decisions

	matrix = build_matrix(profile_name)
	decision = evaluate(matrix, skill_name)
	decisions.record(profile_name, skill_name, decision, matrix)
	return decision
