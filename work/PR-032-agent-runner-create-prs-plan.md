# PR-032: Agent runner — create real PRs from dispatch issues — execution plan

This PR is intended for a Copilot agent.

## Goal
Make the example runner in `agent-runner/runner.py` reliably:
- claim a dispatch issue labeled `copilot-agent`
- clone the target repo
- create/update a branch per task
- commit a trace file containing correlation metadata
- push and open a PR referencing the dispatch issue
- mark the dispatch issue processed (comment + label)

## What exists today
- `agent-runner/runner.py` has a PR-creation path, but it needs to be validated against current tracking requirements and made idempotent.
- `agent-runner/README.md` and `docs/agent-runner-setup.md` exist.

## Required behavior
- Idempotency:
  - If branch exists: checkout and update.
  - If PR exists for the branch: update body/comment rather than failing.
- Correlation:
  - Ensure PR body includes `<!-- agent_task_metadata {"task_id": "..."} -->`.
  - Ensure PR references the dispatch issue (e.g., `Fixes owner/repo#123`).
- Safety:
  - Never log tokens.
  - Keep the runner’s default action minimal (trace-file PR only).

## Smoke test
- Create a dispatch issue with label `copilot-agent` and a valid `agent_task_metadata` block.
- Confirm runner opens a PR in the target repo with the metadata comment.
- Confirm the dispatch issue is labeled/commented as processed.

## Acceptance criteria
- Runner can process at least one issue end-to-end and open a PR.
- Re-running the runner does not create duplicate PRs/branches.
- Docs include a copy/pasteable smoke test.
