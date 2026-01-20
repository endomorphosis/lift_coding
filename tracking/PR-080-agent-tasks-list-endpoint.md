# PR-080: Agent tasks list endpoint (backend)

## Goal
Add a backend endpoint to list a user’s agent tasks so mobile can display task status without relying on notifications or dev-only transitions.

## Context
The backend already supports agent task lifecycle and dev-only transition endpoints:
- `POST /v1/agents/tasks/{task_id}/start`
- `POST /v1/agents/tasks/{task_id}/complete`
- `POST /v1/agents/tasks/{task_id}/fail`

Mobile task status UI benefits from a simple read endpoint.

## Scope
- Add `GET /v1/agents/tasks` that returns tasks for the authenticated user.
- Support optional filters (keep minimal):
  - `status` (or `state`) filter
  - `limit` + `offset` (or `page`)
  - default sort: newest first
- Ensure auth scoping (no cross-user leakage).
- Update OpenAPI spec (`spec/openapi.yaml`) and any contract tests.

## Non-goals
- Admin endpoint to view all users’ tasks.
- Complex query language.

## Acceptance criteria
- `GET /v1/agents/tasks` returns a list of tasks for the current user.
- Supports basic filtering/pagination.
- OpenAPI contract updated and tests pass.
- Adds tests for:
  - user scoping
  - filter behavior

## Suggested files
- `src/handsfree/api.py`
- `src/handsfree/db/agent_tasks.py`
- `spec/openapi.yaml`
- Tests under `tests/` (new or extend existing agent tests)

## Validation
- Run `python -m pytest -q`.
