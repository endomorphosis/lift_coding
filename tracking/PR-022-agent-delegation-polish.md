# PR-022: Agent delegation end-to-end polish

## Goal
Finish the MVP4 “agent delegation” path so it works end-to-end with real users:
- `agent.*` intents use the authenticated `user_id` (no placeholders)
- Delegation actually dispatches work when using `github_issue_dispatch`
- Task state/trace updates are consistent and observable

## Background
The repo already supports:
- Agent task persistence (`agent_tasks`)
- A GitHub issue-based dispatcher provider (`github_issue_dispatch`)
- Webhook correlation to mark tasks completed when a PR is opened referencing the dispatch work item

However, some command-path wiring is still placeholder-oriented and the delegation flow should be tightened to ensure real dispatch occurs and state transitions are recorded.

## Scope
- Remove any hard-coded placeholder user IDs for agent intents.
- Thread `user_id` (and where needed, `session_id`) through the router/handlers for `agent.delegate`, `agent.status`, `agent.pause`, `agent.resume`.
- Update `AgentService.delegate()` to:
  - start the selected provider (call `start_task()` when appropriate)
  - transition task state to `running` on successful dispatch
  - store provider trace updates (issue URL/number, dispatch repo, etc.)
  - emit consistent notifications for created/running/completed states
- Ensure `github_issue_dispatch` provider can be selected and exercised via env/config.

## Non-goals
- Adding new agent providers beyond existing ones.
- Building a full UI/client delegation experience.

## Acceptance criteria
- `agent.*` intents never use a hard-coded `"default-user"`; they respect authenticated `user_id`.
- `agent.delegate` with provider `github_issue_dispatch` creates a dispatch issue and updates the task state/trace.
- Webhook PR correlation still marks the task `completed` and emits a completion notification.
- Tests remain green.

## Notes / Pointers
- Router wiring: `src/handsfree/commands/router.py`
- Service: `src/handsfree/agents/service.py`
- Provider: `src/handsfree/agent_providers.py`
- Correlation: `src/handsfree/api.py` (`_correlate_pr_with_agent_tasks`)
