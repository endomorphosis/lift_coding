#!/usr/bin/env bash
set -euo pipefail

# Creates one branch per implementation_plan PR spec with a tiny placeholder change,
# so a draft PR can be opened later (once GitHub API rate limits reset).

REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$REPO_ROOT"

git fetch origin

default_branch=main

for spec in implementation_plan/prs/PR-00*.md; do
  base=$(basename "$spec")
  num=$(echo "$base" | cut -d- -f2)
  slug=${base#PR-${num}-}
  slug=${slug%.md}

  # PR-001 is already implemented/merged in this repo.
  if [[ "$num" == "001" ]]; then
    continue
  fi

  branch="draft/pr-${num}-${slug}"
  workfile="work/PR-${num}-${slug}.md"

  echo "---"
  echo "Preparing $branch"

  # Create branch from origin/main (idempotent).
  if git show-ref --verify --quiet "refs/heads/$branch"; then
    git checkout "$branch" >/dev/null
    git reset --hard "origin/$default_branch" >/dev/null
  else
    git checkout -b "$branch" "origin/$default_branch" >/dev/null
  fi

  mkdir -p work

  title=$(sed -n '1s/^# //p' "$spec")
  {
    echo "$title"
    echo
    echo "This branch exists to host a draft PR for Copilot agents."
    echo
    echo "- Spec: implementation_plan/prs/$base"
    echo "- Tracking: tracking/$base"
    echo
    echo "## Agent checklist"
    echo "- [ ] Implement spec"
    echo "- [ ] Add fixtures + tests"
    echo "- [ ] Keep OpenAPI contract green"
    echo
  } > "$workfile"

  git add "$workfile"
  git commit -m "Queue draft work for $base" >/dev/null || true
  git push -u origin "$branch" >/dev/null

done

git checkout "$default_branch" >/dev/null

echo "Done. Branches are pushed; create PRs after rate limit reset."
