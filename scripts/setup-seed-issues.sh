#!/usr/bin/env bash
# Create the seed issues for Slice 1 so first contributors have things to grab.
# Each issue is labelled, assigned to milestone "Slice 1 — Foundations & DocType Skeletons".
# Idempotent at the level of "does an issue with this exact title already exist?" — re-running creates duplicates if you change titles.
#
# Usage:  ./scripts/setup-seed-issues.sh

set -euo pipefail

REPO="${FRIDAY_REPO:-Friday-Labs-Inc/friday}"
MILESTONE="Slice 1 — Foundations & DocType Skeletons"
SLICE_LABEL="slice:1-foundations"
PHASE_LABEL="phase:v0.1"
STATUS_LABEL="status:needs-triage"

create_issue() {
  local title="$1" area_label="$2" body="$3" extra_labels="${4:-}"
  local labels="$SLICE_LABEL,$PHASE_LABEL,$STATUS_LABEL,type:feature,$area_label"
  if [ -n "$extra_labels" ]; then labels="$labels,$extra_labels"; fi

  # Skip if exact title already exists
  if gh issue list --repo "$REPO" --search "$title in:title" --state open --json title --jq '.[].title' | grep -Fxq "$title"; then
    echo "Skipped (exists): $title"
    return
  fi

  gh issue create --repo "$REPO" \
    --title "$title" \
    --body "$body" \
    --milestone "$MILESTONE" \
    --label "$labels"
}

BODY_PREFIX="**Slice:** 1 — Foundations & DocType Skeletons

**References:**
- \`CODEX.md\` §5 Slice 1
- \`docs/design/05-module-design.md\` §\"Core DocTypes (Phase 1)\" — field schemas
- \`docs/design/11-agent-validation-checklist.md\` Slice 1 — done criteria

**Done when:** all relevant boxes in the Slice 1 section of the validation checklist are ticked."

create_issue \
  "Slice 1 — Scaffold friday app and modules.txt" \
  "area:framework-core" \
  "$BODY_PREFIX

Create the friday app inside the bench, set up modules.txt with: Gateway, Agents, Skills, Tasks, Messaging, Permissions. Each module needs __init__.py and a doctype/ subfolder." \
  "good-first-task,for:humans"

create_issue \
  "Slice 1 — Create Agent Profile DocType" \
  "area:agent-kernel" \
  "$BODY_PREFIX

Define Agent Profile per the schema in 05-module-design.md. Fields include profile_name, description, assigned_roles (table), model_provider, model_name, system_prompt, permitted_skills, resource_quota, network_allowlist, requires_approval_above_risk, status."

create_issue \
  "Slice 1 — Create Skill DocType" \
  "area:agent-kernel" \
  "$BODY_PREFIX

Define Skill per the schema in 05-module-design.md. Fields include skill_name, description, when_to_use, instructions, parameters_schema, required_doctypes, required_operations, risk_level, requires_approval, status, usage_count, last_used, created_by_agent."

create_issue \
  "Slice 1 — Create Agent Task and Agent Project DocTypes" \
  "area:workflow" \
  "$BODY_PREFIX

Define Agent Task with: title, description, project (link), assigned_to_profile, required_skills, workflow_state, dispatchable, priority, dependencies, result, started_at, completed_at. Define Agent Project as the container."

create_issue \
  "Slice 1 — Create Chat Message and Chat Platform DocTypes" \
  "area:cli" \
  "$BODY_PREFIX

Define Chat Message: session_id, platform, direction, sender_id, agent_profile, content, attachments, timestamp, processed. Define Chat Platform for adapter registration (CLI first)."

create_issue \
  "Slice 1 — Create Execution Log (submittable) DocType" \
  "area:agent-kernel" \
  "$BODY_PREFIX

Define Execution Log per 05-module-design.md. Must be **is_submittable=1**. Fields: agent_profile, skill, task, parameters, result, status, permission_decision, duration_ms, tokens_used."

create_issue \
  "Slice 1 — Create Permission Decision Log (submittable) DocType" \
  "area:permissions" \
  "$BODY_PREFIX

Define Permission Decision Log. Must be **is_submittable=1**. This is the audit trail of every permission check the engine performs in Slice 2."

create_issue \
  "Slice 1 — Migration runs clean on a fresh site" \
  "area:ci" \
  "$BODY_PREFIX

\`bench --site friday.localhost migrate\` must run clean. Add a patch to friday/patches.txt if needed. Document the verified migration sequence in IMPLEMENTATION_LOG.md."

create_issue \
  "Slice 1 — test_doctypes_exist.py covering all 8 DocTypes" \
  "area:ci" \
  "$BODY_PREFIX

Write the first real test: open each DocType meta and assert required fields exist. This is the foundation of the test suite — keep it tight and deterministic." \
  "good-first-task,for:humans"

echo "Seed issues created. View at https://github.com/$REPO/issues"
