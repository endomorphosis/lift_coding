# PR-090: Agent runner docs sync

## Goal
Keep the agent-runner documentation accurately aligned with the current
implementation in `agent-runner/runner.py`.

## Context
PR-090 is implemented in `docs/agent-runner-setup.md`. The setup guide now
describes the shipped Docker runner behavior from `agent-runner/runner.py`,
including polling, branch creation, deterministic patch application, trace file
creation, PR correlation metadata, the `processed` visibility label, and
workspace cleanup.

## Scope
- Maintain `docs/agent-runner-setup.md` so it matches the real behavior of `agent-runner/runner.py`:
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
- `docs/agent-runner-setup.md` describes the shipped Docker runner workflow in
  `agent-runner/runner.py`, including the deterministic patch path through
  `apply_patches_from_instruction()` and `agent-runner/apply_instruction.py`.
- The setup guide documents deterministic patch mode, correlation metadata,
  `/workspace` cleanup, and the distinction between the in-memory processed
  issue cache and the `processed` issue label.
- A reader can follow the doc and understand what the runner does today.

## Implementation status
- `docs/agent-runner-setup.md` links directly to `agent-runner/README.md`,
  `docs/AGENT_RUNNER_QUICKSTART.md`, and `docker-compose.agent-runner.yml`.
- The Docker runner section documents the active environment variables read by
  `runner.py`: `GITHUB_TOKEN`, `DISPATCH_REPO`, `POLL_INTERVAL_SECONDS`,
  `AGENT_NAME`, and `LOG_LEVEL`.
- The deterministic patch section now points to
  `apply_patches_from_instruction()` and `agent-runner/apply_instruction.py`
  instead of an example processing stub.

## Resolution notes
VAI-091 resolved the line 29 scan follow-up by confirming
`docs/agent-runner-setup.md` no longer carries the divergent `process_task`
sample and by anchoring the deterministic patch section to
`apply_patches_from_instruction` plus `agent-runner/apply_instruction.py`.

HAO-164 resolved the stale scanner finding at line 1 by changing this tracker
from an open docs-sync instruction into a current implementation record. The
tracking note and setup guide now point at the shipped runner behavior, so the
supervisor-fed backlog can parse the remaining metadata without re-ingesting the
old docs-sync title as active work.

HAO-165 resolved the duplicate scanner finding at the original line 29 by
verifying that `docs/agent-runner-setup.md` now documents the shipped
deterministic patch path through `apply_patches_from_instruction()` and
`agent-runner/apply_instruction.py`. The stale example-processing acceptance
wording is no longer present in this tracker, so no runner behavior change is
needed for this follow-up.

## Suggested files
- `docs/agent-runner-setup.md`
- (optional) `agent-runner/README.md` for minor alignment / cross-links

## Validation
- Doc review: verify every described behavior exists in `agent-runner/runner.py`.
- `test -f tracking/PR-090-agent-runner-docs-sync.md`
