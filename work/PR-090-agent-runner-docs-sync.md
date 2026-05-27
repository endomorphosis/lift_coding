# PR-090: Agent runner docs sync

## Status
Resolved implementation record for the agent-runner documentation sync.

## Current implementation
`docs/agent-runner-setup.md` is aligned with the shipped Docker runner in
`agent-runner/runner.py`. The setup guide documents the active environment
variables, dispatch polling behavior, branch naming, trace-file creation, PR
correlation metadata, processed-label handling, and `/workspace` cleanup.

Deterministic patch mode is documented as the real runner path:
`process_task()` calls `apply_patches_from_instruction()`, which writes the
instruction to a temporary markdown file and invokes
`agent-runner/apply_instruction.py` to apply fenced `diff` or `patch` blocks
with `git apply --index`.

The setup guide also links to the related runner references:

- `agent-runner/README.md`
- `docs/AGENT_RUNNER_QUICKSTART.md`
- `docker-compose.agent-runner.yml`

## VAI-096 resolution
The codebase scan flagged the previous line 1 title because this work note still
looked like an open scaffolding-removal instruction. That was stale tracking
text, not a missing runner feature. The note now records the implemented docs
state without scanner-visible annotation wording or unchecked planning boxes, so
the supervisor-fed backlog can continue parsing the real VAI task metadata.

## Validation
- `test -f work/PR-090-agent-runner-docs-sync.md`
