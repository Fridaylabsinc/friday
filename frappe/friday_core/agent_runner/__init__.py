# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
The Friday agent runner — the brain that takes a user message and produces a reply.

PLAIN ENGLISH
=============

This package is where the agent's *thinking* happens. Given an Agent
Profile and an inbound message, it produces an outbound reply.

In Slice 4 the runner is a **stub**: it loads the agent's tool menu
(via Slice 3) and echoes the message back with a count of available
tools. This proves the pipeline end-to-end without dragging in an LLM
dependency yet.

In Slice 5 the body of `run_turn` gets replaced with a real LLM call —
the function signature stays the same, the seam is at the function
boundary on purpose. The CLI, the chat-flow tests, and the Chat Message
writer don't need to change.

In Slice 7 and beyond, the runner gets wrapped in a sandbox (Docker),
async-ified, parallelized across profiles, etc. The signature still
holds.

MODULES
=======

  - `runner.py` — `run_turn(profile_name, session_id, inbound_content) -> str`.
    The seam. Slices 5+ replace the body.

DESIGN NOTE: WHY A PACKAGE, NOT JUST A FUNCTION
================================================

A bare module would work today. A package gives us room to grow:
provider adapters, system-prompt builders, tool-dispatch helpers, the
ReAct loop. All of those will live here when they exist.

The Hermes equivalent is `run_agent.py:AIAgent.run_conversation` — a
single class with many helpers. We'll mirror that structure when we
need it; for now there's one stub function.
"""
