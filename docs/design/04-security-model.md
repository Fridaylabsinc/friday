# 04 — Security Model

## Why This Matters

Both Hermes and OpenClaw have a documented history of severe security issues:

**OpenClaw (selected):**
- Token exfiltration via crafted webpages (CVE class)
- Privilege escalation through token scope misuse (CVE-2026-32922, CVSS 9.9)
- Prompt-injection-driven tool call chains without admin approval
- Data exfiltration via malicious skills
- January 2026 audit: 512 vulnerabilities, 8 critical

**Hermes (selected):**
- Default Allow-All security posture in fresh installs
- Path traversal in WeChat adapter (CVE-2026-7396)
- Memory poisoning (issue #496)
- Supply chain risk via LiteLLM dependency

The root cause across both: **security is treated as configuration**, not as architecture. Friday inverts this — Frappe's role-based permission system enforces access at the gateway layer before any skill executes.

## Threat Model

Friday assumes a hostile environment:

1. **Compromised prompts** — user input or external content may attempt prompt injection.
2. **Compromised skills** — community-contributed skills may be malicious.
3. **Compromised agents** — one agent profile may be hijacked and attempt lateral movement.
4. **Compromised dependencies** — third-party libraries may be backdoored (LiteLLM-style attacks).
5. **Insider threat** — operators may misconfigure or abuse the system.

## Defense Layers

### Layer 1 — Frappe Role-Based Permissions (Foundation)

- Every DocType has explicit read / write / create / delete / submit / cancel permissions per role.
- Agent Profiles are mapped to one or more roles.
- Skills declare which DocTypes and operations they require.
- The gateway resolves: `agent_profile → roles → permitted DocTypes → allowed skills`.
- A skill that touches a DocType the agent's role doesn't permit is rejected **before queueing**.

### Layer 2 — Gateway-Level Pre-Check

Before any skill execution job is queued:

```
1. Resolve calling Agent Profile
2. Load assigned roles (cached in Redis, TTL 60s)
3. Build permission matrix in memory
4. Validate: requested_skill.required_doctypes ⊆ profile.permitted_doctypes
5. Validate: requested_skill.required_operations ⊆ profile.permitted_operations
6. Check skill status: must be Active (not Draft / Retired / Archived)
7. Check approval requirement: if skill.requires_approval → create Workflow Request
8. If all pass → queue job. Otherwise → reject + log to Execution Log
```

This pre-check is synchronous and fast (<10ms with Redis cache). No job ever reaches a worker without permission validation.

### Layer 3 — Sandboxed Execution (Docker)

Each Agent Profile execution runs in a Docker container:

- **Network namespace** — container reaches only the Frappe REST API endpoint and explicitly whitelisted external endpoints (e.g. specific LLM provider).
- **Read-only filesystem** — skill definitions mounted read-only; ephemeral scratch space is in-memory tmpfs.
- **Resource caps** — CPU, memory, disk, file descriptors via cgroups.
- **Scoped credentials** — container receives only the tokens needed for the current skill, scoped to the agent's role.
- **No host access** — no mounts from host filesystem, no SSH, no host process visibility.
- **Ephemeral lifetime** — destroyed after skill completes; persistent state is in Frappe.

Compromise of a skill = compromise of one container, scoped to one agent's permissions. Lateral movement is structurally blocked.

### Layer 4 — Frappe API as Security Boundary

Containers cannot reach PostgreSQL or Redis directly. All reads and writes flow through Frappe's REST API, which:

- Authenticates the request against an agent-scoped API key.
- Re-validates permissions server-side (defense in depth).
- Logs every API call to a queryable audit trail.
- Applies rate limits per agent.

Even if a container is fully compromised, it cannot bypass the Frappe permission engine.

### Layer 5 — Inter-Agent Communication

Agents never call each other directly. Inter-agent collaboration flows through:

```
Agent A → Redis pubsub channel → Gateway → permission check
       → Spawn / route to Agent B's container → result back via channel
```

Permissions on inter-agent delegation are explicit: Agent A must have permission to invoke Agent B's profile, which is a separate DocType-level permission, not implicit.

### Layer 6 — Approval Workflows

High-risk skills are flagged `requires_approval = true`. Invocation:

1. Gateway creates a `Workflow Request` DocType with skill, parameters, agent ID, risk level.
2. Agent execution **pauses** (no resources held).
3. Frappe Workflow routes the request to the appropriate approver role.
4. Approver reviews in Frappe Desk and approves / rejects.
5. Gateway resumes (or rejects) based on the decision.
6. Decision is logged immutably.

This mirrors Hermes' approval buttons but uses Frappe's mature workflow engine instead of a custom system.

### Layer 7 — Tirith Integration (Inherited)

For shell-style commands, Friday inherits Hermes' Tirith integration:

- Pattern matching against curl-pipe-bash, homograph URLs, exfiltration patterns.
- Runs **after** Frappe permission check, **before** container execution.
- Findings logged and surfaced to approvers.

### Layer 8 — Audit Trail

Every meaningful event is a DocType row:

- `Execution Log` — every skill invocation: agent, skill, params, result, duration.
- `Permission Decision Log` — every permission grant/deny: agent, requested resource, decision, reason.
- `Workflow Request` — every approval request and its outcome.
- `Chat Message` — every inbound and outbound message.
- `Agent Session` — every conversation, queryable by user / agent / time.

All logs are append-only (DocType `submitted` state prevents modification) and queryable via Frappe Desk, REST API, or reports.

## Agent Profile Anatomy

A minimal Agent Profile DocType has:

| Field | Type | Purpose |
|---|---|---|
| `profile_name` | Data | Unique identifier |
| `assigned_roles` | Table (Link → Role) | Maps to Frappe roles |
| `permitted_skills` | Table (Link → Skill) | Explicit skill whitelist (or "all from role") |
| `model_provider` | Link | Which LLM provider to use |
| `model_name` | Data | Specific model |
| `resource_quota_*` | Int / Float | CPU, memory, requests-per-hour |
| `requires_approval_above_risk` | Select | Auto-route to approval above this risk threshold |
| `network_allowlist` | Table | External hosts the container may reach |
| `status` | Select | Active / Suspended / Retired |

## Resource Quotas

Per Agent Profile:

- Max concurrent executions
- Max executions per hour / day
- Max tokens per execution
- Max wall-clock seconds per execution
- Max external API calls per minute

Enforced by Frappe rate limiter + container cgroups. Quota exhaustion → graceful rejection + alert.

## Secret Management

- API keys stored as Frappe `Password` fields (encrypted at rest using Frappe's site encryption key).
- Containers receive secrets via short-lived environment variables, never written to disk inside the container.
- Secret rotation is a Frappe DocType update — propagates to new container spawns automatically.
- Optional integration with external secret managers (HashiCorp Vault, AWS Secrets Manager) via Frappe integration framework.

## What This Buys Us

Compared to Hermes / OpenClaw, Friday provides:

- **Structural** rather than configurational security — permission misconfigurations are caught by Frappe's permission engine, not silently ignored.
- **Auditability** at the DocType level — every decision is queryable.
- **Defense in depth** — six independent layers between user input and host compromise.
- **Compliance-ready** — audit trails are immutable, queryable, and exportable. Suitable for SOC 2 / ISO 27001 environments.

This is the single biggest reason Friday exists. The agentic ecosystem has agent capabilities. It does not yet have agentic governance.
