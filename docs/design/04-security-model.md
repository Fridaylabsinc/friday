# 04 — Security Model

> See `00-glossary.md` for term definitions.
> See `46-security-claims-audit.md` for the verifiability rules behind the framing below — every claim about upstream agentic frameworks is architectural-pattern language, not unsourced CVE numbers.

---

## Why a security model exists at all

Current-generation agentic frameworks (Hermes, OpenClaw, and most of the field) share a common security shape: permissions are runtime configuration rather than architectural invariants, default postures lean permissive, and tool/skill execution boundaries are enforced inside the agent process rather than at a separate trust boundary. Public discussion of the category has surfaced examples of token exfiltration via untrusted web content, prompt-injection-driven tool-call chains, malicious-skill data exfiltration, permissive defaults in fresh installs, adapter-level input-handling bugs, memory-channel poisoning, and supply-chain exposure through shared LLM-routing dependencies.

The root cause is the same across the category, not unique to any one project: **security is treated as configuration, not as architecture.** Friday inverts this. Frappe's role-based permission system enforces access at the gateway before any skill executes. Misconfiguration cannot silently widen authority — the engine rejects requests that exceed the agent's permitted scope.

---

## Threat model

Friday assumes a hostile environment:

1. **Compromised prompts.** User input or external content may attempt prompt injection.
2. **Compromised skills.** Community-contributed skills may be malicious.
3. **Compromised agents.** An Agent Profile may be hijacked and attempt lateral movement.
4. **Compromised dependencies.** Third-party libraries may be backdoored, particularly LLM-routing layers.
5. **Insider threat.** Operators may misconfigure or abuse the system.

---

## Defence layers

Seven enforced layers in v0.1, one deferred to Phase 2.

### Layer 1 — Frappe role-based permissions

- Every DocType has explicit read / write / create / delete / submit / cancel permissions per role.
- Agent Profiles map to one or more roles.
- Skills declare the DocTypes and operations they require.
- The gateway resolves `Agent Profile → roles → permitted DocTypes → allowed Skills`.
- A skill that touches a DocType the agent's role does not permit is rejected **before queueing**.

### Layer 2 — Gateway pre-check

Before any skill execution job is queued:

```
1. Resolve calling Agent Profile.
2. Load assigned roles (Redis-cached, TTL 60s).
3. Build the permission matrix in memory.
4. Validate: requested_skill.required_doctypes ⊆ profile.permitted_doctypes.
5. Validate: requested_skill.required_operations ⊆ profile.permitted_operations.
6. Check Skill status: must be Active (not Draft / Retired / Archived).
7. Check approval requirement: if skill.requires_approval → create Workflow Request.
8. If all pass → queue. Otherwise → reject and write a Permission Decision Log row.
```

Synchronous and fast (<10ms with Redis cache). No job reaches a worker without this validation.

### Layer 3 — Docker sandbox

Each skill invocation runs in a fresh container:

- **Network namespace** restricts egress to the Frappe REST API and explicitly whitelisted external endpoints.
- **Read-only filesystem** for skill content; scratch space is an in-memory tmpfs.
- **cgroups** cap CPU, memory, disk, file descriptors.
- **Scoped credentials** — only the tokens the current skill needs, scoped to the agent's role.
- **No host access** — no host mounts, no SSH, no host process visibility.
- **Ephemeral** — destroyed after execution; persistent state lives in Frappe.

A compromised skill compromises one container, scoped to one agent's permissions. Lateral movement is structurally blocked.

### Layer 4 — Frappe REST API as the trust boundary

Containers cannot reach PostgreSQL or Redis directly. All reads and writes flow through the Frappe REST API, which:

- Authenticates against an agent-scoped API key.
- Re-validates permissions server-side (defence in depth).
- Logs every call to a queryable audit trail.
- Rate-limits per agent.

A fully compromised container cannot bypass the Frappe permission engine.

### Layer 5 — Inter-agent communication

Agents do not call each other directly. Collaboration flows through Redis pub/sub → gateway → permission check → target agent's container → result back via channel.

Permission to invoke another Agent Profile is a separate, explicit DocType-level grant. It is not implicit in being able to run skills.

### Layer 6 — Approval workflows

High-risk skills carry `requires_approval = true`. Invocation:

1. Gateway creates a Workflow Request with skill, parameters, agent ID, risk level.
2. Agent execution **pauses** (no resources held).
3. Frappe Workflow routes the request to the appropriate approver role.
4. Approver decides in the Framework Console.
5. Gateway resumes or rejects based on the decision.
6. The outcome is recorded immutably in Workflow Request and Permission Decision Log.

### Layer 7 — Shell-command policy engine (Phase 2)

For shell-style commands invoked by skills, Friday will integrate a pattern-matching policy engine (curl-pipe-bash, homograph URLs, exfiltration patterns) ahead of container execution. **Phase 1 disallows shell-style skills entirely.** The policy engine is the prerequisite to re-enabling them. Tirith is the reference implementation under evaluation; final adoption is decided in the Phase 1 spike (`44-technical-feasibility-spike.md`). Deferred per `41-porting-strategy-hermes-erpnext-raven.md`.

### Layer 8 — Audit trail

Every meaningful event is a DocType row:

- **Execution Log** — every skill invocation: agent, skill, params (masked), result, duration.
- **Permission Decision Log** — every grant or deny: agent, requested resource, decision, reason.
- **Workflow Request** — every approval request and its outcome.
- **Chat Message** — every inbound and outbound message across adapters.
- **Agent Session** — every conversation, queryable by user / agent / time.

All logs are submittable DocTypes — immutable once submitted. Queryable via the Framework Console, REST API, and standard Frappe reports.

---

## Agent Profile anatomy

| Field | Type | Purpose |
|---|---|---|
| `profile_name` | Data | Unique identifier |
| `assigned_roles` | Table → Role | Maps the agent to Frappe roles |
| `permitted_skills` | Table → Skill | Explicit Skill whitelist (or "all from role") |
| `model_provider` | Link | LLM provider adapter |
| `model_name` | Data | Specific model identifier |
| `resource_quota_*` | Int / Float | CPU, memory, requests-per-hour |
| `requires_approval_above_risk` | Select | Threshold above which Workflow Request is auto-created |
| `network_allowlist` | Table | External hosts the container may reach |
| `status` | Select | Active / Suspended / Retired |

---

## Resource quotas

Per Agent Profile, enforced by Frappe rate limiter and container cgroups:

- Max concurrent executions.
- Max executions per hour and per day.
- Max tokens per execution.
- Max wall-clock seconds per execution.
- Max external API calls per minute.

Quota exhaustion produces a graceful rejection plus an alert. Never a silent stall.

---

## Secret management

- API keys live in Frappe `Password` fields, encrypted at rest with the site's encryption key.
- Containers receive secrets as short-lived environment variables; secrets are never written to the container's filesystem.
- Rotation is a DocType update — new container spawns pick up the new value automatically.
- External secret managers (HashiCorp Vault, AWS Secrets Manager) integrate via the Frappe integration framework when needed.

---

## Net effect

- **Structural, not configurational, security.** A misconfiguration cannot quietly grant authority the role does not have — the permission engine rejects on every path.
- **Auditability at the DocType level.** Every decision is a queryable row.
- **Defence in depth.** Seven independent enforcement layers between user input and host compromise.
- **Compliance-ready.** Audit trails are immutable, queryable, and exportable. Suitable for SOC 2 and ISO 27001 environments.

The agentic ecosystem has agent capabilities. It does not yet have agentic governance. That gap is why Friday exists.
