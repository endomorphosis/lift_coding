# PR-016: Implement real agent delegation integration (dispatcher + correlation)

## Goal
Replace placeholder agent provider behavior with a real, end-to-end delegation path that creates an external work item and can be correlated back into `agent_tasks` lifecycle.

## Background
The plan’s MVP4 expects: delegate to an agent, track lifecycle, and notify when a PR is opened or the task is completed. The repo currently has task persistence and dev-only lifecycle endpoints, but the provider itself is stubbed.

## Scope
- Add a production-capable `AgentProvider` implementation that dispatches work to GitHub as a durable work item.
- Store external references (issue URL / PR URL) in the task trace.
- Add minimal correlation logic using existing GitHub webhook ingestion so that when a PR is opened referencing the dispatched work item, the task can be marked `completed` (or `needs_input`/`failed` as appropriate).
- Add unit tests using fixtures.

## Dispatch approach (proposed)
- On `agent.delegate`, create a GitHub Issue in a configured repository (could be the same repo) with:
  - Title: derived from instruction (truncated)
  - Body: includes structured metadata (task_id, user_id, target repo, instruction)
  - Labels: `copilot-agent` (or a dedicated label)
- Optionally, create a draft PR tracking branch/commit via GitHub Contents API (future enhancement).

## Correlation approach (proposed)
- When receiving `pull_request` webhooks, detect references to the issue (e.g., “Fixes #123”) or task metadata in PR body.
- If correlated, update the corresponding `agent_task` to `completed` and store `pr_url` in trace.

## Non-goals
- Running code modifications inside this backend.
- Automatic merging.

## Acceptance criteria
- Delegation creates a durable external work item and records its URL in `agent_tasks.trace`.
- A PR webhook referencing that work item updates the task to `completed` and records the PR URL.
- Clear configuration via env vars; graceful errors when misconfigured.
- CI remains green.

## Config
- `HANDSFREE_AGENT_PROVIDER=github_issue_dispatch`
- `HANDSFREE_AGENT_DISPATCH_REPO=owner/repo`
- `HANDSFREE_AGENT_DISPATCH_TOKEN_REF=...` (via secret manager)

