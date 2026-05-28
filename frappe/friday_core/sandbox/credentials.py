# Copyright (c) 2026, Friday Labs and contributors
# For license information, please see license.txt

"""
Scoped credential management for sandbox execution.

Phase 1 (this module): _generate_scoped_token() returns a UUID;
the container uses it as a bearer token for the Frappe REST API.
Frappe does not yet verify the token — this is Phase 1.5.

Phase 1.5 wiring (per DOC 23 §2):
- Generate a Frappe API Key + Secret for the agent profile
  via frappe.api.add_api_key (or equivalent)
- Set expiry to the container's wall-clock timeout
- Pass as FRIDAY_API_KEY env var
- Container uses it as Bearer token against /api/method endpoints
- Frappe validates expiry and scope server-side
  before executing any skill

Skill-level credentials (per DOC 23 Table §2):
- For skills requiring external credentials (e.g. SMTP for email),
  read Skill Credential DocType rows linked to the (Agent Profile, Skill)
  combination
- Inject resolved values as prefixed env vars (FRIDAY_CREDS_<name>)
- Never write credentials to disk; container env is the only channel
"""

import os
import time
import secrets
import hashlib


def generate_scoped_token(agent_profile: str, execution_id: str) -> str:
    """
    Generate a short-lived, scoped bearer token for one execution.

    Phase 1: returns a random UUID tied to the (agent_profile, execution_id).
    Phase 1.5: replaces with a real Frappe API Key that Frappe can validate.
    """
    raw_parts = (
        agent_encoding(agent_profile),
        execution_id,
        str(int(time.time())),
        secrets.token_hex(16),
    )
    return hashlib.sha256(".".join(raw_parts).encode()).hexdigest()


def agent_encoding(profile: str) -> str:
    """Normalise an Agent Profile name to a safe token component."""
    return hashlib.sha256(profile.encode()).hexdigest()[:16]


def resolve_credentials(agent_profile: str, skill_name: str) -> dict[str, str]:
    """
    Resolve all credential bindings for a (profile, skill) pair.

    Phase 1: returns {} — no external credentials wired yet.
    Phase 1.5: reads Skill Credential DocType rows.

    Returns a dict of env-var names → values injected into the container.
    """
    # TODO Phase 1.5: load Skill Credential rows linked to (agent_profile, skill_name)
    return {}


def redact_credentials_from_logs(logs: str, credentials: dict[str, str]) -> str:
    """
    Remove credential values from container logs before writing to Execution Log.

    Phase 1: pass-through (Phase 1 credentials are UUIDs; not sensitive).

    Phase 1.5: replace known credential values with [REDACTED]
    to prevent accidental credential leakage in audit logs.
    """
    return logs


__all__ = [
    "generate_scoped_token",
    "resolve_credentials",
    "redact_credentials_from_logs",
]
