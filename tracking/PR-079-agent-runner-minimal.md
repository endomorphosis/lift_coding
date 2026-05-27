# PR-079: Minimal working agent runner

## Goal
Turn the documented agent runner plan into a minimal working implementation that can pick up agent tasks and drive them through completion/failure, suitable for demo / dev.

## Context
The repo now includes a minimal local runner implementation in `src/handsfree/agents/runner.py`, a CLI entrypoint in `scripts/minimal_agent_runner.py`, and focused coverage in `tests/test_minimal_runner.py`. Keep this tracking note aligned with that shipped behavior so stale setup wording does not get re-ingested as unresolved work. The minimal runner:
- can read queued tasks
- simulates task work with trace/progress updates
- updates task state and emits progress/notifications (where available)

## Scope
- Implement a simple runner process (Python) that:
  - polls for tasks in `created` state (or the appropriate state used by the backend)
  - transitions tasks: `created -> running -> completed` (or `failed` on exceptions)
  - leaves `needs_input` tasks untouched without crashing the local loop
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
- `docs/agent-runner-setup.md` (keep setup docs pointed at the shipped implementation)
- New runner module under `src/handsfree/agents/runner.py` (or similar)
- Optional: `scripts/agent_runner.py`
- Tests under `tests/`

## References
- `src/handsfree/agents/runner.py` - minimal local runner loop.
- `scripts/minimal_agent_runner.py` - local CLI entrypoint.
- `tests/test_minimal_runner.py` - focused unit coverage for the minimal runner.
- `docs/MINIMAL_AGENT_RUNNER.md` - local usage, environment variables, and sample flow.

## Resolution notes
The earlier scanner finding matched stale wording that described this work as
example task-processing wording. The tracker now points at the shipped local
runner artifacts and describes the current simulated-work behavior directly.

## Validation
- Run `python -m pytest -q`.
- Optional manual demo: create a task, start runner, observe completion + notification.
