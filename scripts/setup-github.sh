#!/usr/bin/env bash
# One-shot GitHub project setup for Friday.
# Runs all the file-based / API-driven setup steps in order.
# Items that require web UI (Projects v2 board, Discussions categories,
# branch protection) are listed at the end.
#
# Prereqs:
#   - gh CLI installed and authenticated with write access:  gh auth login
#   - Run from the repo root.
#
# Usage:  ./scripts/setup-github.sh

set -euo pipefail

REPO="${FRIDAY_REPO:-Friday-Labs-Inc/friday}"
export FRIDAY_REPO="$REPO"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "================================================================"
echo "  Friday GitHub setup — repo: $REPO"
echo "================================================================"

# Verify gh CLI authed
if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: gh CLI is not authenticated. Run 'gh auth login' first."
  exit 1
fi

echo
echo "[1/4] Repository settings (description, topics, features) ..."
bash "$SCRIPT_DIR/setup-repo-settings.sh"

echo
echo "[2/4] Labels ..."
bash "$SCRIPT_DIR/setup-labels.sh"

echo
echo "[3/4] Milestones ..."
bash "$SCRIPT_DIR/setup-milestones.sh"

echo
echo "[4/4] Slice 1 seed issues ..."
bash "$SCRIPT_DIR/setup-seed-issues.sh"

echo
echo "================================================================"
echo "  Automated setup done."
echo "================================================================"
echo
echo "Remaining manual steps (require GitHub web UI):"
echo
echo "  1. Branch protection on 'main':"
echo "     https://github.com/$REPO/settings/branches"
echo "     - Require PR before merging (1 approval)"
echo "     - Require linear history"
echo "     - Dismiss stale approvals on new commits"
echo
echo "  2. Create the Projects v2 board:"
echo "     https://github.com/$REPO/projects"
echo "     - Name: 'Friday Phase 1 — Fundamentals'"
echo "     - Columns: Backlog, Ready, In Progress, Review, Done"
echo "     - Custom fields: Slice, Area, Phase, Risk, Contributor type"
echo "     - Spec in docs/project/GITHUB_PROJECT_PLAN.md"
echo
echo "  3. Configure Discussions categories:"
echo "     https://github.com/$REPO/discussions"
echo "     - Announcements, Q&A, Show and tell, Ideas, AI Contributors"
echo "     - Pin a welcome post in Announcements"
echo
echo "  4. Code security and analysis:"
echo "     https://github.com/$REPO/settings/security_analysis"
echo "     - Enable Dependabot alerts and security updates"
echo "     - Enable secret scanning and push protection"
echo
echo "Full checklist: docs/project/GITHUB_SETUP_CHECKLIST.md"
