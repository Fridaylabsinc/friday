# 24 — Sandbox Architecture & Implementation

> **Purpose:** Specify the container-based sandbox runtime that executes skills in isolation. Covers container lifecycle, resource limits, network policy, filesystem mounts, credential injection, cleanup, observability, and the failure-recovery model.

This document operationalises the isolation layer outlined in doc 04 (Security Model).

---

## 1. Goals

- **Strong isolation** — a compromised skill cannot read other agents' data, the host, or another container
- **Predictable resources** — each execution gets defined CPU, memory, disk, and time budgets; no noisy-neighbour effects
- **Acceptable startup latency** — under 200ms median for a warm pool, under 1.5s for cold
- **Safe-by-default** — operator does not need to harden network or capabilities; Friday does it
- **Observable** — every container start, exit, kill, OOM logged and queryable

Non-goals: defeating a kernel-level attacker, full multi-tenant compliance (separate documents).

---

## 2. Architecture Overview

```
        Gateway dispatcher
              │
              ▼
       ┌──────────────────┐
       │   Sandbox        │
       │   Orchestrator   │  ← Friday Python module
       └──────────────────┘
              │
   ┌──────────┴──────────┐
   ▼                     ▼
Container Pool        Container Spawner
(pre-warmed,          (cold start when
 size 5–20)            pool empty)
              │
              ▼
       Docker daemon
              │
   ┌──────────┴──────────────────┐
   ▼            ▼                ▼
Container A  Container B  ...  Container N
(skill A)    (skill B)         (skill N)

Each container:
  - read-only rootfs (overlay)
  - tmpfs scratch
  - no host mounts
  - network = friday-execution-net (egress allowlist)
  - cgroups: CPU 2 cores, mem 512MB, pid limit, IO weight
  - capabilities: dropped to minimal set
  - user: nonroot (UID 65532)
  - env: scoped API token + skill credentials
```

---

## 3. Container Image

A single Friday-managed image used for skill execution:

```dockerfile
FROM python:3.11-slim AS runtime

# Pinned dependencies for skill runtime
RUN pip install --no-cache-dir \
    requests==2.32.3 \
    pydantic==2.7.1 \
    frappe-client==1.0.0

# Nonroot user
RUN useradd --no-create-home --uid 65532 friday
USER friday
WORKDIR /home/friday

# Entrypoint: reads task JSON from stdin or arg, executes, exits
COPY --chown=friday:friday entrypoint.py /home/friday/entrypoint.py
ENTRYPOINT ["python", "/home/friday/entrypoint.py"]
```

Image is built reproducibly. Pinned digests are recorded in Friday's `friday-images.lock`. Image scan with `trivy` runs on every release; no critical or high-severity CVEs may ship.

---

## 4. Container Spawn Lifecycle

### 4.1 Request

```python
result = sandbox.execute(
    skill=skill,
    parameters=parameters,
    agent_profile=agent_profile,
    credentials=resolved_credentials,
    timeout_seconds=300,
    cpu_cores=2,
    memory_mb=512,
)
```

### 4.2 Pool check

The orchestrator maintains a warm pool of running idle containers (configurable, default 10). If a free one is available, it's reset (env vars cleared, scratch dir wiped) and reused. Otherwise, cold spawn.

### 4.3 Configuration applied

| Setting | Value |
|---|---|
| Image | `friday/skill-runtime:vX.Y.Z` (pinned digest) |
| Network | `friday-execution-net` (custom bridge with egress allowlist) |
| CPUs | `cpu_cores` (cgroup quota) |
| Memory | `memory_mb` (cgroup limit, swap disabled) |
| PIDs | 256 |
| Read-only rootfs | yes |
| tmpfs mount | `/tmp` (64MB, noexec, nosuid) |
| Capabilities | drop ALL; add nothing |
| User | UID 65532 (nonroot) |
| Seccomp | `default` (Docker default seccomp profile) |
| AppArmor / SELinux | `docker-default` when available |
| no-new-privileges | yes |
| Env vars | scoped API token, credential bindings, task metadata |

### 4.4 Task payload

The orchestrator writes a JSON payload to the container's stdin:

```json
{
  "skill_name": "send_invoice",
  "skill_version": 4,
  "parameters": {"invoice_id": "INV-001"},
  "frappe_base_url": "http://frappe:8000",
  "execution_id": "uuid...",
  "trace_id": "uuid..."
}
```

### 4.5 Execution

Inside the container, `entrypoint.py`:
1. Reads payload from stdin
2. Validates the JSON shape
3. Loads the skill module by name (skills bundled into the image OR fetched read-only from a skill repo if not bundled)
4. Calls the skill's `run(parameters, frappe_client)` function with a Frappe client authenticated using the scoped API token
5. Captures stdout and stderr
6. Writes result JSON to a known stdout marker line: `>>>FRIDAY_RESULT_BEGIN<<<\n{...}\n>>>FRIDAY_RESULT_END<<<`
7. Exits with code 0 on success, nonzero on failure

### 4.6 Result capture and exit

The orchestrator reads container stdout, parses the result envelope, captures any logs before/after, and stops the container. On normal exit, the container is destroyed (cold mode) or returned to the pool reset (warm mode).

### 4.7 Timeout enforcement

If wall clock exceeds `timeout_seconds`, the orchestrator sends SIGTERM, waits 5s, then SIGKILL. The execution is recorded as `timeout`.

### 4.8 OOM

The Docker daemon kills containers exceeding memory limit. The orchestrator detects exit code 137 and records `oom`.

### 4.9 Cleanup verification

Periodic janitor (every 5 minutes) scans for any container labeled `friday=true` older than `MAX_EXECUTION_AGE` (default 30 min) and force-removes it. No orphans accepted.

---

## 5. Network Policy

Custom Docker bridge `friday-execution-net`:
- No DNS resolution beyond an allowlist via dnsmasq sidecar OR a per-skill iptables egress allowlist
- Default deny on egress
- Per-skill or per-agent allowlist appended at spawn time:
  - Frappe API host always allowed (so the skill can call back)
  - Hosts declared in `agent_profile.network_allowlist` allowed
  - Additional hosts in `skill.network_allowlist` allowed

Implementation detail: rather than reconfigure iptables per spawn, Friday uses a sidecar HTTP egress proxy. Containers reach the outside world only through the proxy, which enforces the allowlist based on the container's labels.

**⚠️ Engineering note:** Docker bridge networking has known limits at scale. For >1000 concurrent containers per host, consider Kubernetes-based isolation instead. Phase 1 targets single-host with <50 concurrent containers, well within Docker capability.

---

## 6. Filesystem Isolation

- Container root filesystem is **read-only** (Docker `--read-only`)
- `/tmp` is the only writeable location, backed by tmpfs (no disk persistence)
- No host paths bind-mounted
- No Docker socket exposed
- Logs streamed via container stdout/stderr to orchestrator, not written to disk

If a skill needs to produce a persistent artifact (e.g. a generated PDF), it must:
1. Write the artifact to `/tmp` first
2. Upload via the Frappe File API (with proper permissions)
3. Return the resulting File DocType reference in its result JSON

This funnels artifact creation through Frappe's permission and audit system.

---

## 7. Credential Injection

Per doc 23:
- Credentials are passed as environment variables at container start
- The container has read-only access to env from inside; no way to mutate the host's view
- Friday's masker scans the container's stdout/stderr stream for credential values and redacts before they reach the Execution Log
- Container's `linkmode` is configured so env vars are not exposed to peer containers

---

## 8. Pool Management

```
Warm Pool
├── min_idle = 5
├── max_idle = 20
├── max_age_per_container = 1 hour
└── reset_on_release: clear env vars, wipe /tmp, re-stat capabilities

Scaling rules:
- If queue depth > 0 AND idle pool < max_idle → keep them warm
- If queue idle for > 60s AND idle pool > min_idle → drain to min_idle
- If a container exits with error → don't return to pool; spawn fresh
```

Pool containers are spawned in a **suspended** state (sleeping on stdin read). When dispatched, the orchestrator just writes the task payload to its stdin. Effective cold-start cost: <50ms typical.

---

## 9. Per-Agent Resource Quotas

Beyond per-container limits, Friday tracks per-agent budgets:

- Max concurrent containers (from `agent_role_profile.default_resource_quota`)
- Max executions per hour
- Max CPU-seconds per day
- Max memory-MB-seconds per day

When an agent exceeds its budget:
- Soft cap: subsequent skill invocations queued, not denied (operator gets notified)
- Hard cap: invocations rejected with a clear error and an Execution Log row of status `quota_exceeded`

---

## 10. Observability

Per execution, the orchestrator emits structured logs and metrics:

| Metric | Type |
|---|---|
| `friday_container_spawn_total` | counter, label: cold_or_warm |
| `friday_container_duration_seconds` | histogram, label: skill_name, status |
| `friday_container_exit_code` | counter, label: code |
| `friday_container_oom_total` | counter |
| `friday_container_timeout_total` | counter |
| `friday_container_pool_size` | gauge |
| `friday_container_queue_depth` | gauge |

Logs include the `trace_id` so an end-to-end trace from gateway → orchestrator → container → result is reconstructable.

---

## 11. Failure Modes

| Mode | Detection | Recovery |
|---|---|---|
| Container crash | nonzero exit | Record `failed`, mark Execution Log, free pool slot |
| Container OOM | exit code 137 | Record `oom`, suggest increasing memory in skill config |
| Wall-clock timeout | orchestrator timer | Record `timeout`, SIGKILL, free pool slot |
| Docker daemon unresponsive | spawn API timeout | Circuit-break: stop dispatching for N seconds, alert operator |
| Network egress denied | skill HTTP error | Record in Execution Log; surface in War Room |
| Skill module not found | entrypoint error | Record `invalid_skill`, mark Skill row degraded |
| Result envelope missing | parse failure | Record `protocol_error`, retain stdout for debugging |
| Janitor finds orphan | scheduled scan | Force-remove, log warning |

Every failure mode produces an Execution Log row. Silent failures are not acceptable.

---

## 12. Security Hardening Checklist

Per host running the orchestrator:

- [ ] Docker daemon socket not exposed over network (Unix socket only)
- [ ] Host kernel patched; weekly automated update window
- [ ] Apparmor or SELinux enforcing on the host
- [ ] Image registry uses signed manifests (Docker Content Trust)
- [ ] Friday image rebuilt and rescanned weekly
- [ ] No skill is included in the base image; skills loaded from Frappe at runtime
- [ ] Container runtime updates monitored (CVE feeds for Docker)
- [ ] Egress allowlist regularly reviewed
- [ ] Audit log of all `docker run` invocations retained for 1 year

---

## 13. Multi-Host & Scaling

Phase 1 targets a single host. Phase 2 scales horizontally:

- Multiple sandbox-orchestrator workers per Frappe site
- Job queue (Frappe RQ) load-balances dispatches across workers
- Each worker maintains its own pool; no cross-worker pool sharing
- Eventually: optional Kubernetes-backed mode where each skill execution is a Pod

The Phase 2 transition is mechanical; the API (`sandbox.execute(...)`) does not change.

---

## 14. Alternatives Considered

| Alternative | Why Not Chosen for Phase 1 |
|---|---|
| Firecracker microVMs | Stronger isolation; more operational complexity. Phase 3 consideration. |
| gVisor | Stronger syscall isolation; performance hit. Phase 3 consideration. |
| Process-level sandbox (no container) | Too weak; rejected per doc 04 threat model |
| Per-skill Kubernetes Pod | Too heavy for sub-second dispatch latency target |
| Wasm sandbox | Insufficient skill ecosystem; LLM-generated Wasm is impractical |

Docker with hardened defaults strikes the right balance for Phase 1.

---

## 15. Testing Strategy

| Test type | Scope |
|---|---|
| Unit | Orchestrator logic (pool management, payload serialisation) |
| Integration | Real Docker spawn/teardown; verify resource limits enforced |
| Security | Try to break out: egress to disallowed host, mount Docker socket, OOM the host, fork bomb (pid limit), DNS amplification, infinite loop with timeout |
| Load | 100 concurrent executions; pool drains correctly; no orphans |
| Chaos | Kill containers mid-execution; verify orchestrator detects and records |

The security test suite is **automated and runs in CI**. A regression here is a release blocker.

---

## 16. Phasing

| Phase | Sandbox Capability |
|---|---|
| 1 (MVP) | Minimum safe sandbox: non-root, resource limits, timeout/OOM handling, no host or Docker socket mounts, scoped credentials, structured result capture, cleanup path |
| 1.5 | Hardened single-host sandbox: warm pool, egress allowlist/proxy, read-only rootfs everywhere, full observability, automated attack suite |
| 2 | Multi-host orchestration via RQ; cross-host pool-aware dispatch |
| 3 | Optional gVisor/Firecracker backend for high-risk skills |
| 4 | Kubernetes-backed mode for cloud deployments |

Phase 1 must include the minimum safe sandbox defined in doc 42. The hardened controls above move into Phase 1.5 unless a specific trust demo requires pulling them forward.
