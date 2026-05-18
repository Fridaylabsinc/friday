#!/usr/bin/env bash
# Create the 11 Friday milestones via gh API.
# Idempotent — if a milestone with the same title exists, the API returns 422 and we skip.
#
# Usage:  ./scripts/setup-milestones.sh

set -euo pipefail

REPO="${FRIDAY_REPO:-Friday-Labs-Inc/friday}"

create_ms() {
  local title="$1" desc="$2"
  if gh api "repos/$REPO/milestones" -f title="$title" -f state=open -f description="$desc" 2>/dev/null | grep -q '"number"'; then
    echo "Created: $title"
  else
    echo "Skipped (likely already exists): $title"
  fi
}

echo "Creating milestones on $REPO ..."

create_ms "Slice 1 — Foundations & DocType Skeletons" "App scaffold and 8 core DocTypes creatable from the Desk."
create_ms "Slice 2 — Permission Engine"               "friday.permissions.matrix.check returns Decisions, logs every check."
create_ms "Slice 3 — Skill Loader"                    "Active Skills loaded per profile, cached, exposed as LLM tool defs."
create_ms "Slice 4 — Gateway + CLI"                   "bench friday chat round-trip via Chat Message DocType."
create_ms "Slice 5 — LLM Integration"                 "Provider-agnostic LLM interface, Minimax first, real replies."
create_ms "Slice 6 — First Skill: create_note"        "Full governed execution end-to-end with Execution Log."
create_ms "Slice 7 — Docker Sandboxing"               "Skill execution moves into resource-capped Docker containers."
create_ms "Slice 8 — Tasks, Dispatcher, Kanban"       "Dispatcher claims tasks atomically; Kanban renders states."
create_ms "Slice 9 — Polish & Hardening"              "Tests, docs, CI, dogfood — public-ready repo."
create_ms "Phase 1.5 — Production Hardening"          "Warm pool, egress proxy, attack suite, multi-host."
create_ms "Phase 2 — Public Launch & Raven"           "Raven War Rooms, additional adapters, semantic memory."

echo "Done. Verify at https://github.com/$REPO/milestones"
