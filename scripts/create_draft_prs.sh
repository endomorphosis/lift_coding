#!/usr/bin/env bash
set -euo pipefail

# Creates draft PRs for the placeholder branches created from implementation_plan/prs/.
#
# Note: This uses the GitHub API via `gh`. If you hit API rate limits, wait and re-run.

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO_ROOT"

# Optional label to make agent-ready PRs easy to find.
gh label create copilot-agent --color 5319e7 --description "Work items queued for Copilot agents" || true

branches=(
  pr-002-backend-api-skeleton
  pr-003-db-migrations-and-models
  pr-004-command-router-and-confirmations
  pr-005-github-readonly-inbox-and-summary
  pr-006-github-webhook-ingestion-and-replay
  pr-007-policy-engine-and-safe-action
  pr-008-agent-orchestration-stub
)

start_branch=$(git branch --show-current)

for branch in "${branches[@]}"; do
  echo "---"
  echo "Creating draft PR for: $branch"

  git checkout "$branch" >/dev/null

  body_file=$(ls -1 tracking/PR-*.md | head -n 1)
  title=$(sed -n '1s/^# //p' "$body_file")

  # If PR already exists for this head branch, skip.
  if gh pr view --head "$branch" --json number >/dev/null 2>&1; then
    echo "PR already exists for $branch; skipping."
    continue
  fi

  gh pr create --draft \
    --base main \
    --head "$branch" \
    --title "$title" \
    --body-file "$body_file" \
    --label copilot-agent

done

git checkout "$start_branch" >/dev/null

echo "Done."
