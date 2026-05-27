# PR-090: Agent runner docs sync

## Status
Resolved implementation record for the agent-runner documentation sync.

## Current implementation
`docs/agent-runner-setup.md` is aligned with the shipped Docker runner in
`agent-runner/runner.py`. The verified runner behavior is recorded below.

- Active runner environment variables: `GITHUB_TOKEN`, `DISPATCH_REPO`,
  `POLL_INTERVAL_SECONDS`, `AGENT_NAME`, and `LOG_LEVEL`.
- Dispatch polling for `copilot-agent` issues, branch naming as
  `agent-task-<task_id_prefix>`, trace-file creation, PR correlation metadata,
  the `processed` label, the in-memory processed issue cache, and `/workspace`
  cleanup.
- Deterministic patch mode is anchored to `apply_patches_from_instruction()` in
  `agent-runner/runner.py` and `agent-runner/apply_instruction.py`, which
  extracts fenced `diff` / `patch` blocks and applies them with
  `git apply --index`.

The setup guide also links to the related runner references:

- `agent-runner/README.md`
- `docs/AGENT_RUNNER_QUICKSTART.md`
- `docker-compose.agent-runner.yml`

## Completed verification
- Read `agent-runner/runner.py` to establish current behavior.
- Verified `docs/agent-runner-setup.md` matches the shipped Docker runner
  behavior.
- Verified deterministic patch mode is documented for fenced `diff` / `patch`
  blocks.
- Verified the setup guide references `docs/AGENT_RUNNER_QUICKSTART.md` and
  `docker-compose.agent-runner.yml`.
- Checked consistency with `agent-runner/README.md`.

## Resolution notes
- HAO-169 resolution: line 1 was stale tracking text, not a runner behavior bug.
  The work note now records the current evidence instead of carrying unresolved
  scaffold wording.
- MGW-113 resolution: the scanner matched stale line-1 wording from this work
  note, not an open docs-sync task. The referenced setup guide and runner README
  already describe the current `agent-runner/runner.py` workflow.
- VAI-096 resolution: the codebase scan flagged the previous line 1 title
  because this work note still looked like an open planning instruction. That
  was stale tracking text, not a missing runner feature.
- This note now records the implemented state directly so the backlog parser
  does not re-ingest the old open-work wording as active follow-up.

## Validation
- `test -f work/PR-090-agent-runner-docs-sync.md`
