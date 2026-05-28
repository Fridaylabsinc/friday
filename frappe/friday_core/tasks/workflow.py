# Copyright (c) 2026, Friday Labs and contributors
# License: MIT. See license.txt

"""
Task workflow state-machine hook for Agent Task documents.

Registered as ``doc_events["Agent Task"]["on_update"]`` in ``hooks.py``.

Responsibilities
----------------
1. Derive ``dispatchable`` from the current ``workflow_state``.
   dispatchable = True when workflow_state ∈ {Pending, Assigned}.
2. Record ``started_at`` when entering the Executing state.
3. Record ``completed_at`` when entering Completed or Cancelled.
4. Clear ``assigned_to_profile`` when entering Cancelled.
5. Emit ``agent_task.assigned`` on Frappe Redis pub/sub when
   transitioning Pending → Assigned so the task runner can pick it up
   outside the save transaction (avoids holding a DB lock while the
   worker runs).
"""

import frappe


# States that make a task available for the dispatcher to claim.
DISPATCHABLE_STATES = frozenset({"Pending", "Assigned"})


def on_state_change(doc: "AgentTask", method: str) -> None:
	"""
	Recompute dispatchable; record timestamps; emit Redis event.

	Called by Frappe's doc_events system after every save of an
	Agent Task document.  Runs inside the same transaction as the
	save, so all DB writes are atomic with it.

	Args:
		doc: The saved Agent Task document.
		method: The Frappe hook method name (``"on_update"``).
	"""
	# 1. dispatchable is a derived field — always recompute from live state.
	doc.dispatchable = doc.workflow_state in DISPATCHABLE_STATES

	# Only act on actual workflow state transitions, not unrelated field saves.
	if doc.has_value_changed("workflow_state"):
		_watch_transition(doc)

	# Persist the updated dispatchable flag inside the same transaction.
	doc.save(ignore_permissions=True)


def _watch_transition(doc: "AgentTask") -> None:
	"""
	Handle side-effects that depend on the specific state transition.

	Runs inside the save transaction — keep DB writes minimal.
	Long-running work (Docker execution) happens in the runner, which
	picks up the ``agent_task.assigned`` pub/sub event.
	"""
	state = doc.workflow_state

	# --- timestamps -------------------------------------------------------
	if state == "Executing" and doc.started_at is None:
		doc.started_at = frappe.utils.now_datetime()

	if state in ("Completed", "Cancelled") and doc.completed_at is None:
		doc.completed_at = frappe.utils.now_datetime()

	# --- clear assignment on cancellation ---------------------------------
	if state == "Cancelled" and doc.assigned_to_profile:
		doc.assigned_to_profile = None

	# --- emit Redis pub/sub for task runner -------------------------------
	# Only emit when we are moving INTO Assigned AND the profile actually
	# changed (avoids duplicate events on re-save without assignment change).
	if state == "Assigned" and doc.has_value_changed("assigned_to_profile"):
		_emit_assigned_event(doc.name, doc.assigned_to_profile)


def _emit_assigned_event(task_name: str, assigned_to_profile: str) -> None:
	"""
	Publish an ``agent_task.assigned`` real-time event.

	The task runner subscribes to this event and resumes a warm container
	to execute the task.  Publishing happens after the save transaction
	commits via ``doctype=True`` so it is outside the DB write path.

	Args:
		task_name: Agent Task document name (e.g. ``AT-000042``).
		assigned_to_profile: The agent profile assigned to the task.
	"""
	message = {
		"task_name": task_name,
		"assigned_to_profile": assigned_to_profile,
		"workflow_state": "Assigned",
	}
	frappe.publish_realtime(
		event="agent_task.assigned",
		message=message,
		doctype="Agent Task",
		after_commit=True,
	)