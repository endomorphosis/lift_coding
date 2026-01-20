# PR-075: Agent notification integration (MVP4)

## Goal
Emit notifications when agent tasks complete or fail, so the user reliably gets a push update without polling.

## Context
Agent tasks exist in the backend (dev-only endpoints for start/complete/fail). The notifications system and push subscription infrastructure also exist. This PR connects them.

## Scope
- When an agent task transitions:
  - `running` → `completed`
  - `running` → `failed`
  - (optionally) `created` → `running`
  create a notification record and dispatch via the configured notification provider.
- Notification payload should include:
  - task id
  - new status
  - a human-readable message
  - optional PR URL (if available)
  - optional failure reason

## Non-goals
- New mobile UI (mobile already handles incoming notifications).
- Implementing a full agent runner; just backend integration points.

## Acceptance criteria
- Completing a task via the existing endpoint triggers a notification.
- Failing a task via the existing endpoint triggers a notification.
- Notifications include enough data for mobile to speak: title/message + optional PR URL.
- Tests validate notification creation for both completed and failed transitions.

## Suggested files
- `src/handsfree/agents/service.py` (task state transitions)
- `src/handsfree/api.py` (task endpoints if they need to pass through notification context)
- `src/handsfree/db/notifications.py` (if helpers exist)
- Tests under `tests/` (new or extend existing agent/notification tests)

## Validation
- Run `python -m pytest -q`.

