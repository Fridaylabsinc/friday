# Copyright (c) 2026, Friday Labs and contributors
# License: MIT. See license.txt

"""
Task runner — executes assigned Agent Tasks inside Docker sandboxes.

Consumes ``agent_task.assigned`` real-time events emitted by the
workflow hook and the task dispatcher.  Transitions task state through
Executing → Review (success) or Executing → Blocked (failure).

Registration
------------
Call ``register_task_runner()`` once during Frappe app initialisation
(e.g. from ``after_migrate`` or via a startup hook) to wire up the
real-time subscription.  The runner persists across requests as part
of the Frappe worker process.

Architecture note
-----------------
This is the async counterpart to the synchronous skill dispatcher in
``friday_core.agent_runner.dispatcher``.  Both share the same sandbox
runner (``friday_core.sandbox.runner``) but differ in lifecycle:
- Chat flow: synchronous, in-process, per-message.
- Task flow: event-driven, cron-dispatched, persistent.
"""

import frappe
from frappe.utils import now_datetime


_logger = frappe.logger("friday.tasks.runner")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def register_task_runner() -> None:
	"""
	Subscribe to ``agent_task.assigned`` real-time events.

	Call this once from a Frappe startup hook (``after_migrate`` or a
	custom ``on_worker_init`` hook) to register the handler.  Safe to
	call multiple times — Frappe's realtime layer deduplicates handlers.
	"""
	frappe.realtime.on("agent_task.assigned", on_agent_task_assigned)


def on_agent_task_assigned(message: dict) -> None:
	"""
	Handle an ``agent_task.assigned`` real-time event.

	Executed asynchronously by the Frappe realtime worker after the
	``agent_task.assigned`` pub/sub message is published by the workflow
	hook or the dispatcher.

	Args:
		message: Dict with keys ``task_name``, ``assigned_to_profile``,
		          ``workflow_state``.
	"""
	task_name = message.get("task_name")
	profile_name = message.get("assigned_to_profile")

	if not task_name or not profile_name:
		_logger.error(
			"Malformed agent_task.assigned message: %s", message
		)
		return

	try:
		_run_task(task_name, profile_name)
	except Exception:
		_logger.exception(
			"Task runner failed for task %s on profile %s",
			task_name,
			profile_name,
		)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _run_task(task_name: str, profile_name: str) -> None:
	"""
	Load a task, execute its required skills, and update the task state.

	Args:
		task_name: ``Agent Task`` document name.
		profile_name: ``Agent Profile`` name to execute the task under.
	"""
	task = frappe.get_doc("Agent Task", task_name)

	# Transition to Executing (workflow action).
	_task_transition(task, "Executing")
	task.started_at = now_datetime()
	task.save(ignore_permissions=True)
	frappe.db.commit()

	# Execute each required skill in sequence.
	results = []
	skills = [row.skill for row in task.required_skills if row.skill]

	for skill_name in skills:
		result = _execute_skill_in_sandbox(skill_name, task, profile_name)
		results.append(result)

		if result.status != "success":
			_block_task(task, results)
			return

	# All skills succeeded — transition to Review.
	task.result = frappe.as_json(_build_result_envelope(results, "success"))
	_task_transition(task, "Review")
	task.save(ignore_permissions=True)
	frappe.db.commit()


def _execute_skill_in_sandbox(
	skill_name: str, task: "AgentTask", profile_name: str
) -> "SandboxResult":
	"""
	Execute one skill from a task's required_skills in a Docker sandbox.

	Uses the warm container pool (via ``sandbox.runner``) with credentials
	resolved from ``skill_name + profile_name``.

	Args:
		skill_name: Name of the skill to execute.
		task: The ``Agent Task`` document.
		profile_name: The executing ``Agent Profile`` name.

	Returns:
		``SandboxResult`` dataclass from sandbox.runner.
	"""
	from frappe.friday_core.sandbox import runner as sandbox_runner
	from frappe.friday_core.sandbox import credentials as sandbox_creds

	parameters = _parse_task_parameters(task, skill_name)
	creds = sandbox_creds.resolve_credentials(profile_name, skill_name)

	execution_id = f"{task.name}:{skill_name}"
	token = sandbox_creds.generate_scoped_token(profile_name, execution_id)

	return sandbox_runner.execute(
		skill_name=skill_name,
		parameters=parameters,
		agent_profile=profile_name,
		api_key=token,
		credentials=creds,
	)


def _parse_task_parameters(task: "AgentTask", skill_name: str) -> dict:
	"""
	Extract parameters for ``skill_name`` from the task document.

	Phase 1: uses the task's ``description`` field as a plain-text hint
	passed to the sandbox entrypoint.  Phase 1.5 will support structured
	parameters stored in a child table.

	Args:
		task: The ``Agent Task`` document.
		skill_name: Name of the skill whose parameters are needed.

	Returns:
		Dict of parameters to pass to the skill handler.
	"""
	# Phase 1 — unstructured description as parameters.
	# The skill handler decides how to parse it.
	return {"description": task.description or ""}


def _block_task(task: "AgentTask", results: list) -> None:
	"""
	Mark a task as blocked after a skill execution failure.

	Args:
		task: The ``Agent Task`` document.
		results: List of ``SandboxResult`` from executed skills.
	"""
	task.result = frappe.as_json(_build_result_envelope(results, "failed"))
	_task_transition(task, "Blocked")
	task.save(ignore_permissions=True)
	frappe.db.commit()


def _build_result_envelope(results: list, status: str) -> dict:
	"""
	Build the JSON result envelope written to ``Agent Task.result``.

	Args:
		results: List of ``SandboxResult`` from skill executions.
		status: Overall status string (``"success"`` or ``"failed"``).

	Returns:
		Envelope dict with ``status``, ``skills``, ``started_at``, etc.
	"""
	return {
		"status": status,
		"skills": [
			{
				"skill": r.skill,
				"status": r.status,
				"result": r.result,
				"logs": r.logs,
				"duration_ms": r.duration_ms,
			}
			for r in results
		],
		"completed_at": frappe.utils.now_datetime(),
	}


def _task_transition(task: "AgentTask", target_state: str) -> None:
	"""
	Transition an Agent Task to a new workflow state.

	Calls the Frappe Workflow action if the workflow document defines
	a valid transition.  Silently no-ops if no workflow is configured
	or if the transition is not defined — this allows the runner to work
	both with and without a Frappe Workflow on the DocType.

	Args:
		task: The ``Agent Task`` document.
		target_state: The target state name string.
	"""
	try:
		if hasattr(task, "transition") and callable(task.transition):
			task.transition(target_state)
	except Exception:
		# Workflow not configured or transition not allowed — set directly.
		task.workflow_state = target_state