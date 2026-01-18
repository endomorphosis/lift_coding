# PR-054: Agent delegation real dispatch defaults + correlation

## Goal
Make MVP4 "delegate to an agent" work end-to-end without manual provider tweaking.

## Current gap
- `agent.delegate` defaults to provider `copilot` which is stubbed.
- A real dispatch path exists (`github_issue_dispatch`) but is not the default.
- The plan expects: delegate → task lifecycle tracking → notify on PR creation/completion.

## Scope
- Add env-driven default provider (e.g. `HANDSFREE_AGENT_DEFAULT_PROVIDER`).
- Prefer `github_issue_dispatch` in non-dev environments when configured.
- Improve correlation logic so a PR opened by an agent is linked to the originating task.
- Ensure status transitions update DB state and emit notifications.

## Acceptance criteria
- With `HANDSFREE_AGENT_DEFAULT_PROVIDER=github_issue_dispatch` and `HANDSFREE_AGENT_DISPATCH_REPO` set, `agent.delegate` creates a dispatch issue and returns a running task.
- When a PR is opened containing the metadata marker, task transitions to `completed` and emits a notification.

## References
- src/handsfree/agent_providers.py
- src/handsfree/agents/service.py
- src/handsfree/api.py
