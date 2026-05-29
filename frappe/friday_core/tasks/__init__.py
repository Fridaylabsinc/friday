# Copyright (c) 2026, Friday Labs and contributors
# License: MIT. See license.txt

"""
Friday Tasks Module

Orchestrates asynchronous execution of Agent Tasks via the warm container pool.

Sub-modules
-----------
workflow : Workflow state-machine hook for Agent Task documents.
dispatcher : Cron-scheduled task fetcher and profile matcher.
runner : Event-driven task executor that resumes paused containers.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from frappe.friday_core.doctype.agent_task.agent_task import AgentTask
	from frappe.friday_core.doctype.agent_profile.agent_profile import AgentProfile

__all__ = ["workflow", "dispatcher", "runner", "warroom"]