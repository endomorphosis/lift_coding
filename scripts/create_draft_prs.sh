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
  "draft/pr-001-repo-foundation-followups"
  "draft/pr-002-backend-api-skeleton"
  "draft/pr-003-db-migrations-and-models"
  "draft/pr-004-command-router-and-confirmations"
  "draft/pr-005-github-readonly-inbox-and-summary"
  "draft/pr-006-github-webhook-ingestion-and-replay"
  "draft/pr-007-policy-engine-and-safe-action"
  "draft/pr-008-agent-orchestration-stub"
)

start_branch=$(git branch --show-current)

for branch in "${branches[@]}"; do
  echo "---"
  echo "Creating draft PR for: $branch"

  git checkout "$branch" >/dev/null

  base=$(basename "$branch")
  if [[ "$base" == "pr-001-repo-foundation-followups" ]]; then
    body_file="tracking/PR-001-repo-foundation-followups.md"
  else
    num=$(echo "$base" | cut -d- -f2)
    slug=${base#pr-${num}-}
    body_file="tracking/PR-${num}-${slug}.md"
  fi
  # Title: use first non-empty line; strip a leading "# " if present.
  title=$(awk 'NF { print; exit }' "$body_file" | sed 's/^# //')

  # If PR already exists for this head branch, skip.
  existing_url=$(gh pr list --head "$branch" --state all --json url --jq '.[0].url' 2>/dev/null || true)
  if [[ -n "${existing_url}" ]]; then
    echo "PR already exists for $branch; skipping: ${existing_url}"
    continue
  fi

  if ! gh pr create --draft \
    --base main \
    --head "$branch" \
    --title "$title" \
    --body-file "$body_file" \
    --label copilot-agent; then
    echo "Failed to create PR for $branch; continuing."
  fi

done

git checkout "$start_branch" >/dev/null

echo "Done."
