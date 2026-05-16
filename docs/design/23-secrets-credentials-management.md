# 23 — Secrets & Credentials Management

> **Purpose:** Define how Friday stores, accesses, masks, rotates, and audits credentials — API keys, database passwords, deployment tokens, SSH keys — used by agents during skill execution.

This is one of the most security-sensitive subsystems. A leaked credential is worse than a leaked document because it grants ongoing access. The design errs strongly toward least-privilege, short-lived access, and audit.

---

## 1. Threat Model

What we're defending against:
1. **Compromised agent prompt** that tries to exfiltrate credentials
2. **Compromised skill** that logs credentials
3. **Insider operator** who can read Frappe documents but shouldn't see raw secrets
4. **Compromised LLM provider** that sees the prompt context
5. **Compromised host** — secrets at rest must be encrypted
6. **Log/telemetry leak** — credentials accidentally captured in audit trail
7. **Memory dump** of a long-running process
8. **Credential reuse across agents** — one compromised agent shouldn't expose another's secrets

---

## 2. Storage Architecture

### 2.1 Three tiers of secret store

| Tier | Where | Use case |
|---|---|---|
| **Frappe Password field** | Encrypted in Frappe DB using site encryption key | Default; sufficient for most secrets |
| **External Vault** (HashiCorp Vault, AWS Secrets Manager, etc.) | External service via plugin | High-value secrets requiring rotation, HSM-backing, or regulatory compliance |
| **Per-execution short-lived token** | Issued at skill dispatch time, expires when container exits | Friday-internal API access from sandboxed containers |

### 2.2 Credential Profile DocType

A single secret isn't enough; a credential is a bundle (e.g. "AWS account X = access_key + secret + region + role").

| Field | Type | Notes |
|---|---|---|
| `credential_code` | Data (unique) | e.g. `aws_prod_devops`, `erpnext_finance_user` |
| `description` | Text |  |
| `category` | Select | API Key / DB / SSH / Cloud / ERPNext User / Service Token |
| `storage_backend` | Select | Frappe / Vault / Other |
| `vault_path` | Data (nullable) | When storage_backend = Vault |
| `secret_fields` | Table | Field name → encrypted value (each row uses Password type) |
| `non_secret_metadata` | JSON | Region, account ID, etc. (not sensitive) |
| `permitted_role_profiles` | Table → Agent Role Profile | Which profiles may use this credential |
| `permitted_skills` | Table → Skill | Which skills may invoke it (further narrows scope) |
| `requires_approval` | Check | If true, any use generates a Workflow Request |
| `rotation_interval_days` | Int | 0 = no rotation policy |
| `last_rotated_at` | Datetime |  |
| `rotation_status` | Select | Healthy / Due / Overdue / Failed |
| `status` | Select | Active / Suspended / Retired |

---

## 3. Access Pattern

Agents do not load credentials into their LLM context. Credentials reach the container, not the prompt.

### 3.1 Skill declaration

A skill that needs a credential declares it in its parameters_schema:

```yaml
# Skill: deploy_to_aws
required_credentials:
  - credential_code: aws_prod_devops
    bind_as_env:
      access_key: AWS_ACCESS_KEY_ID
      secret_key: AWS_SECRET_ACCESS_KEY
      region: AWS_DEFAULT_REGION
```

### 3.2 Permission gate at dispatch

```
Agent invokes deploy_to_aws skill
  → Gateway checks: agent's role_profile permits this skill? (skill-level permission)
  → Gateway checks: agent's role_profile in credential.permitted_role_profiles? (credential-level permission)
  → Gateway checks: this skill in credential.permitted_skills? (skill+credential pairing)
  → If credential.requires_approval: create Workflow Request, pause
  → Otherwise: fetch credential, inject into container env, run
```

### 3.3 Container receives secrets

The container is spawned with credential values bound to environment variables specified in the skill manifest. The agent's LLM context never contains the raw values. Inside the container, the skill's code reads from env.

### 3.4 Cleanup

When the container exits, the env vars die with it. No persistent file containing the credential is written.

---

## 4. Masking in Logs and War Room

Every code path that writes user-visible output passes through a masker:

```python
def mask(text: str) -> str:
    """Replace known secret patterns with ***REDACTED***"""
    # Pattern-based: AWS keys, JWT, generic API keys (32+ char alphanum), passwords
    # Plus: lookup table of currently-issued credential values
    ...
```

Mask is applied to:
- Execution Log `parameters` and `result` fields (on save)
- Chat Message content (on write)
- Frappe Communication content (on write)
- War Room messages via Raven hook (on post)
- Error messages surfaced to users
- LLM prompt history retained for memory (the credential value is replaced with a placeholder before storage)

If a credential is accidentally embedded in a string the agent constructed, it gets masked before persistence. The original cleartext exists only in the live container; once that's gone, only the masked form remains.

**⚠️ Engineering note:** masking is defence-in-depth, not the primary control. The primary control is: don't put credentials in agent context in the first place.

---

## 5. Rotation

For credentials with `rotation_interval_days > 0`, a scheduled job runs nightly:

```python
def rotation_tick():
    overdue = frappe.get_all('Credential Profile',
        filters={'status': 'Active', 'rotation_status': 'Due'})

    for cred in overdue:
        # Strategy depends on category
        if cred.category == 'AWS':
            rotate_aws_access_key(cred)
        elif cred.category == 'API Key':
            notify_admin_to_rotate_manually(cred)
        # ...

        if rotation_succeeded:
            cred.last_rotated_at = now()
            cred.rotation_status = 'Healthy'
        else:
            cred.rotation_status = 'Failed'
            escalate(cred)
```

Some categories (AWS access keys, generated service tokens) can be rotated automatically. Others (vendor-specific keys) require a human to fetch the new value and update. The system tracks status either way.

---

## 6. Audit

Three log surfaces:

### 6.1 Credential Access Log (new DocType)

Submittable; one row per credential read.

| Field | Type |
|---|---|
| `credential` | Link → Credential Profile |
| `accessed_by_agent` | Link → Agent Profile |
| `for_skill` | Link → Skill |
| `for_execution` | Link → Execution Log |
| `accessed_at` | Datetime |
| `purpose` | Text (auto-generated: "skill X requested AWS credentials") |
| `result` | Select (granted / denied / approval_pending) |

### 6.2 Workflow Request rows

When a credential's `requires_approval` triggers, the request and decision are captured here (per doc 05).

### 6.3 Rotation log

Each rotation attempt logged with outcome, included in the Credential Profile's history.

These three combined: every fetch, every approval, every rotation is queryable. Auditor can reconstruct: "On date D, agent A accessed credential C for execution E, approved by user U."

---

## 7. ERPNext-Specific Pattern: One User Per Agent

A critical case for Friday's Phase 1 ERPNext PO flagship validation after the v0.1 framework loop is proven.

Naive setup: one ERPNext API user shared across all Friday agents. Audit trail in ERPNext says "API User created Purchase Order #123" — useless for forensics.

Friday's pattern (per doc 31):

1. **System Manager Agent** has elevated permissions (System Manager role in ERPNext) and a corresponding Credential Profile.
2. On project setup, the System Manager Agent **creates one ERPNext user per agent**: `procurement.agent@friday.local`, `finance.agent@friday.local`, etc.
3. Each ERPNext user gets:
   - The appropriate ERPNext role (Purchase Manager, Finance Manager, etc.)
   - An API key + API secret
   - These are stored as a Credential Profile in Friday, scoped to that specific agent profile
4. The corresponding Friday Agent Profile is linked to its ERPNext user via the `linked_user` field
5. When the agent invokes an ERPNext skill, it uses **its own** credentials, not a shared service account

ERPNext audit trail now correctly shows "procurement.agent created Purchase Order #123" — full forensic clarity.

---

## 8. Multi-Tenancy & Per-Site Isolation

In a multi-site Frappe deployment (each site is a separate Friday tenant), credentials are strictly site-scoped:

- Each site has its own encryption key
- Credential Profiles in site A are not readable from site B
- Cross-site agent communication (doc 37) uses **inter-site tokens** issued through a separate trust establishment, not shared secrets
- If FridayLabs hosts multiple tenants, no shared credential vault — each tenant has its own

---

## 9. Bootstrapping Secrets at Install Time

Friday needs some initial secrets to function (LLM provider key, optional Vault address). These are configured via:

| Method | Use case |
|---|---|
| `bench set-config` | Local dev; encrypted in site config |
| Environment variables read at startup | Container deployments (Docker Compose, Kubernetes) |
| Vault auto-fetch | Production; site authenticates to Vault, fetches initial secrets |
| Frappe Desk UI for first-run wizard | Operator types/pastes; immediately encrypted as Password field |

The bootstrap secrets themselves (e.g. the Vault token used to fetch other secrets) are the weakest link by definition. Minimise their scope, rotate them often, and store them with the same care as production keys.

---

## 10. Risk Acceptance & Open Issues

Even with all of the above, residual risks remain:

| Risk | Status |
|---|---|
| A compromised container can read its own env vars | Accepted — only that one execution's credentials at risk; container is short-lived |
| LLM prompt with embedded credential reaches the model | Mitigated by never putting credentials in prompt; not eliminable if a buggy skill ignores this rule |
| Frappe encryption key compromise | Mitigated by Vault for high-value secrets; full compromise still possible at OS level |
| Memory dump of running container | Accepted — same risk class as any production system |
| Social engineering of approval flow | Mitigated by multi-supervisor approval on high-risk skills |
| Insider with DB access bypasses Frappe permissions | Mitigated by Vault for high-value secrets; database-only access does not yield Vault contents |

---

## 11. Operator Hardening Checklist

For deployments to production:

- [ ] Site encryption key stored outside the Frappe site (env var or external KMS)
- [ ] Vault integration enabled for credentials marked `Critical` risk
- [ ] All credentials with rotation policies enabled (no infinite-lived keys)
- [ ] Network egress from worker containers restricted to known target hosts
- [ ] Frappe Desk access to Credential Profile DocType restricted to a single `Credential Admin` role
- [ ] Credential Access Log retention: minimum 1 year for compliance
- [ ] Quarterly review of credential usage — identify and retire unused credentials
- [ ] Backup encryption keys separately from data backups
- [ ] Disaster recovery plan for vault unavailability documented

---

## 12. Phasing

| Phase | Secrets Scope |
|---|---|
| 1 (MVP) | Frappe Password fields; per-execution scoped tokens for ERPNext; basic masking |
| 2 | Vault integration plugin; Credential Access Log; rotation for AWS-style credentials |
| 3 | Auto-rotation across more categories; calibration of masking patterns; KMS integration for site encryption keys |
| 4 | HSM support; multi-region vault replication; compliance attestations |

Phase 1 must include masking and per-execution tokens. Vault is optional but recommended for production.
