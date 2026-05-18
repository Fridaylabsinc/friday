#!/usr/bin/env bash
# Create the Friday label taxonomy on GitHub.
# Requires `gh` CLI authenticated with write access to the repo.
# Idempotent — uses --force so re-running updates existing labels.
#
# Usage:  ./scripts/setup-labels.sh

set -euo pipefail

REPO="${FRIDAY_REPO:-Friday-Labs-Inc/friday}"

create() {
  local name="$1" colour="$2" desc="$3"
  gh label create "$name" --repo "$REPO" --color "$colour" --description "$desc" --force
}

echo "Creating labels on $REPO ..."

# Type
create "type:bug"              "d73a4a" "Something is broken"
create "type:feature"          "a2eeef" "New capability"
create "type:proposal"         "7057ff" "Spec-before-code proposal"
create "type:blocker"          "b60205" "Contributor is stuck, decision needed"
create "type:ai-registration"  "5319e7" "AI contributor sponsor registration"
create "type:docs"             "0075ca" "Documentation work"
create "type:security"         "000000" "Security concern"
create "type:chore"            "cfd3d7" "Maintenance, refactor, dependency bumps"

# Slice
for n in 1-foundations 2-permissions 3-skills 4-gateway 5-llm 6-first-skill 7-sandbox 8-dispatcher 9-polish; do
  create "slice:$n" "fbca04" "Phase 1 vertical slice"
done

# Phase
create "phase:v0.1"             "0e8a16" "Phase 1 — governed framework loop"
create "phase:1-po-flagship"    "216e39" "Phase 1 — ERPNext PO dogfood"
create "phase:1.5-hardening"    "bfdadc" "Phase 1.5 — production-grade hardening"
create "phase:2-public-launch"  "c5def5" "Phase 2 — open source launch"
create "phase:future"           "e4e669" "Beyond Phase 2"

# Area
for area in agent-kernel workflow sandbox control-room cli llm permissions ci framework-core; do
  create "area:$area" "bfd4f2" "Subsystem area"
done

# Status
create "status:needs-triage"   "e99695" "New, not yet reviewed"
create "status:needs-decision" "fbca04" "Decision required"
create "status:in-progress"    "0e8a16" "Actively being worked on"
create "status:blocked"        "b60205" "Cannot progress"
create "status:review"         "5319e7" "Awaiting human review"
create "status:done"           "0e8a16" "Merged or resolved"

# Difficulty
create "good-first-task"       "7057ff" "Well-scoped for new contributors"
create "difficulty:medium"     "fbca04" "Requires project context"
create "difficulty:hard"       "b60205" "Architectural — needs maintainer pairing"

# Contributor
create "for:humans"            "0e8a16" "Open to human contributors"
create "for:ai-agents"         "5319e7" "Open to registered AI contributors"
create "for:human-ai-pair"     "7057ff" "Best done as a pair"
create "maintainer-only"       "b60205" "Reserved for maintainers"

echo "Done. Visit https://github.com/$REPO/labels to verify."
