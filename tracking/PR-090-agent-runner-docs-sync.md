# PR-090: Agent runner docs sync (remove outdated TODO scaffolding)

## Goal
Make the agent-runner documentation accurately reflect the current implementation in `agent-runner/runner.py`.

## Context
`docs/agent-runner-setup.md` currently contains an older/example code path with placeholder TODOs that does not match the shipped runner in `agent-runner/runner.py`.

This creates confusion when someone tries to stand up the agent runner and validate the GitHub-issue dispatch + correlation loop.

## Scope
- Update `docs/agent-runner-setup.md` so it matches the real behavior of `agent-runner/runner.py`:
  - required env vars (`GITHUB_TOKEN`, `DISPATCH_REPO`, etc.)
  - polling behavior + labels (`copilot-agent`, `processed`)
  - branch naming (`agent-task-<task_id_prefix>`)
  - correlation metadata comment and PR body format
  - deterministic patch mode (fenced `diff` / `patch` blocks via `apply_instruction.py`)
  - workspace usage (`/workspace`) and cleanup
- Ensure the setup guide clearly points to:
  - `agent-runner/README.md`
  - `docs/AGENT_RUNNER_QUICKSTART.md`
  - `docker-compose.agent-runner.yml`

## Non-goals
- Implementing LLM-backed code generation.
- Adding new provider integrations.

## Acceptance criteria
- `docs/agent-runner-setup.md` no longer includes placeholder “TODO: implement your actual task processing logic here” flows that diverge from `agent-runner/runner.py`.
- A reader can follow the doc and understand what the runner actually does today (including deterministic patch mode).

## Suggested files
- `docs/agent-runner-setup.md`
- (optional) `agent-runner/README.md` for minor alignment / cross-links

## Validation
- Doc review: verify every described behavior exists in `agent-runner/runner.py`.
