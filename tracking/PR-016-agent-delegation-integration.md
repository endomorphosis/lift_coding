# PR-016: Implement real agent delegation integration (dispatcher + correlation)

## Status: ✅ COMPLETED

## Goal
Replace placeholder agent provider behavior with a real, end-to-end delegation path that creates an external work item and can be correlated back into `agent_tasks` lifecycle.

## Background
The plan's MVP4 expects: delegate to an agent, track lifecycle, and notify when a PR is opened or the task is completed. The repo currently has task persistence and dev-only lifecycle endpoints, but the provider itself is stubbed.

## Scope
- ✅ Add a production-capable `AgentProvider` implementation that dispatches work to GitHub as a durable work item.
- ✅ Store external references (issue URL / PR URL) in the task trace.
- ✅ Add minimal correlation logic using existing GitHub webhook ingestion so that when a PR is opened referencing the dispatched work item, the task can be marked `completed` (or `needs_input`/`failed` as appropriate).
- ✅ Add unit tests using fixtures.

## Implementation Summary

### 1. GitHubIssueDispatchProvider (agent_providers.py)
- Production-ready `AgentProvider` implementation
- Creates GitHub issues on task delegation with structured metadata
- Stores issue URL/number in task trace
- Graceful error handling for misconfiguration
- Token provider support for flexible authentication

### 2. GitHub API Integration (github/client.py)
- `create_issue` function with full error handling
- httpx-based implementation with timeouts
- Supports labels and structured body content
- Returns issue URL and number for tracking

### 3. PR Correlation Logic (api.py)
- `_correlate_pr_with_agent_tasks` function
- Integrated into webhook processing pipeline (line 412)
- Two correlation methods:
  - Via `agent_task_metadata` JSON comment in PR body
  - Via issue references (`Fixes #N`, `Closes #N`, `Resolves #N`)
- Updates task state to `completed` on correlation
- Stores PR URL and metadata in trace
- Emits completion notifications

### 4. Configuration (.env.example)
- Added agent delegation configuration examples
- Environment variables:
  - `HANDSFREE_AGENT_PROVIDER=github_issue_dispatch`
  - `HANDSFREE_AGENT_DISPATCH_REPO=owner/repo`
  - Uses `GITHUB_TOKEN` for authentication

### 5. Comprehensive Testing
- 12 tests for GitHubIssueDispatchProvider (test_github_issue_dispatch_provider.py)
- 9 tests for PR correlation logic (test_pr_correlation.py)
- All edge cases covered:
  - Misconfiguration scenarios
  - API failures
  - Multiple issue references
  - Malformed metadata
  - Different repositories
  - Task state filtering

## Dispatch approach (implemented)
- On `agent.delegate`, creates a GitHub Issue in configured repository with:
  - Title: derived from instruction (truncated to 100 chars)
  - Body: includes structured metadata (task_id, user_id, target repo, instruction)
  - Labels: `copilot-agent`
  - Hidden JSON metadata comment for correlation

## Correlation approach (implemented)
- When receiving `pull_request` opened webhooks:
  - Extracts task_id from `agent_task_metadata` JSON comment
  - Extracts issue references from PR body (Fixes/Closes/Resolves #N)
  - Matches against running/created tasks
  - Updates task to `completed` and stores PR URL in trace
  - Emits completion notification

## Non-goals
- Running code modifications inside this backend.
- Automatic merging.

## Acceptance criteria
- ✅ Delegation creates a durable external work item and records its URL in `agent_tasks.trace`.
- ✅ A PR webhook referencing that work item updates the task to `completed` and records the PR URL.
- ✅ Clear configuration via env vars; graceful errors when misconfigured.
- ✅ CI remains green (944 tests passing, 0 security alerts).

## Test Results
- ✅ 944 tests passing, 75 skipped
- ✅ All linting checks passing
- ✅ Code formatting validated
- ✅ OpenAPI validation passing
- ✅ CodeQL security scan: 0 alerts

## Config
- `HANDSFREE_AGENT_PROVIDER=github_issue_dispatch`
- `HANDSFREE_AGENT_DISPATCH_REPO=owner/repo`
- `GITHUB_TOKEN=ghp_...` (for authentication)
