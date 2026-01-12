#!/usr/bin/env bash
set -euo pipefail

# Creates GitHub Issues (recommended for Copilot agents) from the tracking PR specs.
#
# Why Issues instead of draft PRs?
# - A PR requires a code diff; a placeholder PR with no real change is awkward.
# - Copilot coding agents can be invoked on Issues and will open a PR automatically.
#
# Note: This uses the GitHub API via `gh`. If you hit API rate limits, wait and re-run.

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO_ROOT"

# Optional label to make agent-ready work easy to find.
gh label create copilot-agent --color 5319e7 --description "Work items queued for Copilot agents" || true

for body_file in tracking/PR-00*.md; do
  title=$(sed -n '1s/^# //p' "$body_file")
  echo "---"
  echo "Creating issue: $title"

  # Skip if an open issue with exact title already exists.
  if gh issue list --state open --search "\"$title\" in:title" --json title --jq '.[].title' | grep -Fxq "$title"; then
    echo "Issue already exists; skipping."
    continue
  fi

  gh issue create \
    --title "$title" \
    --body-file "$body_file" \
    --label copilot-agent

done

echo "Done."
