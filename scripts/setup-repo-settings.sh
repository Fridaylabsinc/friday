#!/usr/bin/env bash
# Configure repository description, topics, and feature toggles.
# Idempotent — safe to re-run.
#
# Usage:  ./scripts/setup-repo-settings.sh

set -euo pipefail

REPO="${FRIDAY_REPO:-Friday-Labs-Inc/friday}"

echo "Configuring $REPO ..."

gh repo edit "$REPO" \
  --description "Governed agentic framework on Frappe v16 — where AI agents are first-class contributors. Made in India." \
  --enable-issues=true \
  --enable-discussions=true \
  --enable-projects=true \
  --enable-wiki=false \
  --enable-merge-commit=true \
  --enable-squash-merge=true \
  --enable-rebase-merge=false \
  --delete-branch-on-merge=true

# Topics — additive, won't remove existing ones
gh repo edit "$REPO" \
  --add-topic frappe \
  --add-topic agentic-framework \
  --add-topic ai-agents \
  --add-topic open-source \
  --add-topic india \
  --add-topic governance \
  --add-topic gpl-v3 \
  --add-topic erpnext \
  --add-topic frappe-v16

echo "Repo settings applied. Verify at https://github.com/$REPO/settings"
