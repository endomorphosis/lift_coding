# PR-079: Minimal working agent runner

## Goal
Turn the documented agent runner skeleton into a minimal working implementation that can pick up agent tasks and drive them through completion/failure, suitable for demo / dev.

## Context
PR-079 is implemented as a shipped dev/demo runner. The repo includes a minimal local runner in `src/handsfree/agents/runner.py`, a CLI entrypoint in `scripts/minimal_agent_runner.py`, usage docs in `docs/MINIMAL_AGENT_RUNNER.md`, and focused coverage in `tests/test_minimal_runner.py`. The minimal runner:
- can read queued tasks
- executes a stubbed “do work” routine
- updates task state and emits progress/notifications (where available)

## Scope
- Implement a simple runner process (Python) that:
  - polls for tasks in `created` state (or the appropriate state used by the backend)
  - transitions tasks: `created -> running -> completed` (or `failed` on exceptions)
  - supports `needs_input` (optional: leave as TODO, but don’t crash)
  - logs progress clearly
- Provide a CLI entrypoint for local use.
- Keep the runner safe by default:
  - no real GitHub write actions unless explicitly enabled via env
  - default behavior can be “no-op” work that just marks completed

## Non-goals
- Full production-grade queueing.
- GitHub Actions deployment.
- Sophisticated scheduling.

## Acceptance criteria
- Running the runner locally can pick up a task and mark it completed.
- Failure path marks task as failed and records a reason.
- Includes basic unit test coverage for the task processing loop (mocking backend calls).
- Documentation includes: how to run, required env vars, and a sample flow.

## Suggested files
- `docs/agent-runner-setup.md` (update to remove TODO or point to implementation)
- New runner module under `src/handsfree/agents/runner.py` (or similar)
- Optional: `scripts/agent_runner.py`
- Tests under `tests/`

## Validation
- Run `python -m pytest -q`.
- Optional manual demo: create a task, start runner, observe completion + notification.
