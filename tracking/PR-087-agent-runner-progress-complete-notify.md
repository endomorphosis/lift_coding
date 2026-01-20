# PR-087: Agent runner — progress/complete transitions + notifications

## Goal
Extend the built-in agent runner loop to provide demo-meaningful progress updates and completion/failure transitions, and emit user notifications when tasks change state.

## Context
The current runner ([src/handsfree/agents/runner.py](src/handsfree/agents/runner.py)) only auto-transitions `created -> running`. There’s already a `simulate_progress_update()` helper but it is unused.

For demo readiness, we want:
- visible task progress moving forward
- tasks that complete/fail automatically (for stub mode)
- notifications created/delivered on key transitions

## Scope
- Runner behavior (when `HANDSFREE_AGENT_RUNNER_ENABLED=true`):
  - `created -> running`
  - `running -> completed` after a short deterministic delay OR based on trace markers
  - optionally simulate a failure path (configurable) for testing
  - periodic progress updates while running
- Notifications:
  - on transition to `running`: create a notification (optional)
  - on `completed` / `failed`: create a notification with a short summary
  - ensure this uses the existing notifications subsystem and respects rate limits/dedupe policies
- API/UX support:
  - ensure task trace includes enough info for UI to display meaningful status

## Non-goals
- Actually performing real code changes (LLM/tool execution).
- Full GitHub issue/PR automation.

## Acceptance criteria
- With the runner enabled, creating an agent task results in:
  - automatic transition to `running`
  - at least one progress update in trace
  - automatic transition to `completed` (or `failed` when configured)
  - a persisted notification for completion/failure
- Tests cover runner behavior deterministically (no sleeps in unit tests).

## Suggested files
- `src/handsfree/agents/runner.py`
- `src/handsfree/db/agent_tasks.py`
- `src/handsfree/db/notifications.py` and notification creation helpers
- Tests under `tests/`

## Validation
- Run `python -m pytest -q`.
