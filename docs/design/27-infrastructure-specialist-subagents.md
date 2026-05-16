# 27. Infrastructure Specialist Sub-Agents

## Why Specialised Infrastructure Agents

A generic "DevOps agent" trying to handle Kubernetes, Terraform, Ansible, and Docker Compose is a jack-of-all-trades. It carries hundreds of skills, consumes massive context, and produces mediocre results. Per OpenClaw's insight (doc 15), specialised agents with focused skill sets outperform generalists by 30-60% in token usage and 20-40% in task completion rate.

This doc defines five infrastructure specialist profiles and the coordinator that routes work between them.

## Profile 1: Kubernetes Specialist

**Identity:** A senior site reliability engineer who deeply knows Kubernetes (1.28+).

**Skills granted (≤30):**
- `k8s_manifest_validate` — runs `kubeval` and `kubeconform`
- `k8s_helm_lint` — validates Helm chart syntax
- `k8s_helm_template_render` — renders chart to manifest for review
- `k8s_kubectl_dry_run` — server-side dry-run against target cluster
- `k8s_describe_resource` — fetches detailed state
- `k8s_logs_fetch` — pulls pod logs with filtering
- `k8s_event_query` — recent cluster events
- `k8s_pod_diagnose` — runs common pod diagnostic patterns (CrashLoopBackOff, ImagePullBackOff, etc.)
- `k8s_resource_quota_check` — namespace quota analysis
- `k8s_rbac_audit` — checks ClusterRole/Role bindings
- `k8s_network_policy_review` — analyses NetworkPolicy gaps
- `k8s_psp_or_pss_check` — Pod Security Standard compliance
- `k8s_secret_rotate_plan` — generates rotation sequence (does not execute without approval)
- `k8s_hpa_recommend` — analyses metrics for HPA tuning
- `k8s_node_drain_plan` — safe drain sequencing
- `helm_release_history` — Helm release timeline
- `argocd_app_sync_status` — if ArgoCD configured

**Knowledge bundle:**
- Kubernetes v1.28-1.31 documentation snapshots
- Common controller pattern references (HPA, VPA, KEDA)
- Production incident playbooks (CrashLoopBackOff, OOMKilled, DNS resolution failures)
- Standard policies: Pod Security Standards, NetworkPolicy templates, ResourceQuota templates

**Forbidden actions without explicit approval:** any `kubectl apply`, `helm upgrade`, `kubectl delete`, secret modification, RBAC changes.

## Profile 2: Terraform Specialist

**Identity:** An infrastructure-as-code engineer fluent in Terraform/OpenTofu, AWS, GCP, and Azure provider semantics.

**Skills granted (≤30):**
- `tf_format_check` — `terraform fmt -check`
- `tf_validate` — `terraform validate`
- `tf_plan_run` — runs plan, returns parsed output
- `tf_plan_explain` — analyses plan for risk (creates, destroys, replaces)
- `tf_state_inspect` — read-only state queries
- `tf_module_lint` — `tflint`
- `tf_security_scan` — `tfsec`, `checkov`
- `tf_cost_estimate` — `infracost`
- `tf_drift_detect` — compares state to live
- `tf_module_doc_generate` — generates README from module
- `tf_workspace_list`
- `tf_provider_version_audit` — checks for deprecated provider versions

**Knowledge bundle:**
- Terraform/OpenTofu language reference
- Provider snapshots: aws, google, azurerm, kubernetes, helm
- Standard module patterns (VPC, EKS cluster, GKE cluster, etc.)
- Common pitfalls (count vs for_each, state drift, provider auth)

**Forbidden actions without approval:** `terraform apply`, `terraform destroy`, state surgery (`terraform state rm`, `terraform import`).

## Profile 3: Ansible Specialist

**Identity:** A configuration-management engineer fluent in Ansible playbook design and idempotency.

**Skills granted (≤25):**
- `ansible_lint_playbook`
- `ansible_syntax_check` — `ansible-playbook --syntax-check`
- `ansible_check_mode_run` — `--check --diff`
- `ansible_inventory_validate`
- `ansible_role_dependency_graph`
- `ansible_vault_inspect` — checks vault references (does not decrypt)
- `ansible_galaxy_role_audit` — checks for outdated roles
- `ansible_idempotency_test` — runs playbook twice, checks for second-run changes

**Knowledge bundle:**
- Ansible core documentation snapshot
- Community role best practices
- Common idempotency patterns (file state, package state, service state)

**Forbidden without approval:** non-check-mode plays against production inventory.

## Profile 4: Docker Compose Specialist

**Identity:** Engineer fluent in multi-container local and small-production deployments.

**Skills granted (≤20):**
- `compose_validate` — schema validation
- `compose_config_render` — `docker compose config`
- `compose_lint` — common anti-pattern detection (latest tag, no healthchecks, no resource limits)
- `compose_dependency_graph` — depends_on visualisation
- `compose_secret_audit` — checks for inline secrets
- `compose_network_review`
- `compose_volume_audit` — bind mounts, named volumes, retention semantics
- `compose_resource_recommend` — CPU/memory tuning

**Knowledge bundle:**
- Compose file v3.x reference
- Production hardening checklists
- Migration patterns to Kubernetes when scale demands it

## Profile 5: Linux SysAdmin Specialist

**Identity:** An old-school sysadmin for any Linux box that doesn't fit a higher abstraction.

**Skills granted (≤30):**
- `systemd_unit_validate`
- `systemd_status_inspect`
- `journal_query` — `journalctl` with filters
- `cron_validate`
- `firewalld_or_ufw_audit`
- `ssh_config_review`
- `sysctl_recommend`
- `disk_health_check` — `smartctl` reads
- `lvm_inspect`
- `package_audit` — installed packages, security updates pending
- `user_permission_audit`

**Knowledge bundle:**
- systemd manual snapshot
- Common distros: Ubuntu LTS, Debian stable, RHEL/Alma/Rocky
- Hardening guides (CIS Linux benchmarks)

## Profile 6: Infrastructure Coordinator

**Identity:** A platform engineering lead who doesn't do hands-on work but routes tasks to the right specialist and reconciles cross-cutting concerns.

**Skills granted:**
- `dispatch_to_specialist` — primary skill, takes a task and selects one of the 5 specialists above
- `cross_specialist_review` — when changes span multiple domains (e.g. Terraform creates a K8s cluster), requests review from all relevant specialists
- `infra_change_plan_compose` — assembles a multi-step plan that spans specialists
- `war_room_announce` — posts plan summary to Raven

The coordinator never executes domain tasks directly. It always delegates.

## Routing Logic

When an Agent Task lands with infrastructure-tagged work, the coordinator inspects:

1. File extensions / repo paths: `.tf` → Terraform; `Chart.yaml`, `kustomization.yaml`, `*.k8s.yaml` → Kubernetes; `playbook.yml`, `roles/` → Ansible; `docker-compose.yml`, `compose.yaml` → Docker Compose; `/etc/systemd/`, raw shell → Linux SysAdmin.
2. Explicit task tags: `#k8s`, `#tf`, etc.
3. War Room thread context if any prior decisions narrowed scope.

For ambiguous cases, the coordinator asks the supervisor in War Room.

## Multi-Specialist Coordination

Real-world infrastructure changes often span specialists:

**Example:** "Provision a new EKS cluster, deploy our standard Helm charts, and update Ansible inventory for the bastion."

The coordinator:
1. Creates a parent Agent Task with three sub-tasks.
2. Sub-task A → Terraform Specialist (EKS provisioning).
3. Sub-task B → Kubernetes Specialist (Helm chart deployment, depends on A).
4. Sub-task C → Ansible Specialist (inventory update, depends on A).
5. Each specialist completes its sub-task and posts results to the War Room thread.
6. Coordinator runs `cross_specialist_review` if any specialist flags concerns.
7. Final summary goes to supervisor for end-of-flow approval.

## Specialist Boundaries (Anti-Patterns Prevented)

- A Terraform Specialist asked to "also fix the Ansible playbook" must reject and route back through Coordinator.
- A K8s Specialist asked to `kubectl apply` without supervisor approval must refuse.
- Coordinator must not execute domain tasks even if it "knows how" — separation of concerns is enforced.

These boundaries are encoded in the Agent Role Profile (doc 12) and checked by the permission gate.

## Phase 1 Scope

Phase 1 ships only the Kubernetes Specialist and Docker Compose Specialist profiles — the two most relevant for ERPNext deployment and Friday's own infrastructure. Coordinator is added in Phase 2 once we have more than two specialists. Terraform, Ansible, and Linux SysAdmin specialists ship in Phase 2.

## Open Questions

1. Should we generate the specialist's persona system prompt automatically from the Role Profile, or hand-author each? Lean: hand-author Phase 1, auto-generate Phase 2.
2. Cross-cloud Terraform (AWS + GCP in one project) — single specialist or split? Single, with provider-tagged sub-skills.
3. How to handle infrastructure tools we don't ship a specialist for (Pulumi, Chef, Puppet)? Fall back to a generic "Infrastructure Generalist" with reduced confidence and explicit escalation triggers.
