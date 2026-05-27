# PR-090: Agent runner docs sync

## Status
- [x] Completed

## Checklist
- [x] Read `agent-runner/runner.py` to establish current behavior
- [x] Verified `docs/agent-runner-setup.md` matches the shipped Docker runner behavior
- [x] Verified deterministic patch mode is documented for fenced `diff` / `patch` blocks
- [x] Verified the setup guide references `docs/AGENT_RUNNER_QUICKSTART.md` and `docker-compose.agent-runner.yml`
- [x] Checked consistency with `agent-runner/README.md`

## Notes / Log
- HAO-169 resolution: line 1 was a stale tracking annotation, not a runner behavior bug. The work note now records the current evidence instead of carrying unresolved scaffold wording.
- `docs/agent-runner-setup.md` documents the active runner environment variables:
  `GITHUB_TOKEN`, `DISPATCH_REPO`, `POLL_INTERVAL_SECONDS`, `AGENT_NAME`, and
  `LOG_LEVEL`.
- The setup guide describes polling for `copilot-agent` issues, branch naming as
  `agent-task-<task_id_prefix>`, PR correlation metadata, the `processed` label,
  the in-memory processed issue cache, and `/workspace` cleanup.
- Deterministic patch mode is anchored to
  `apply_patches_from_instruction()` in `agent-runner/runner.py` and
  `agent-runner/apply_instruction.py`, which extracts fenced `diff` / `patch`
  blocks and applies them with `git apply --index`.

## MGW-113 Resolution
- The scanner matched stale line-1 wording from this work note, not an open
  docs-sync task. The referenced setup guide and runner README already describe
  the current `agent-runner/runner.py` workflow.
- This note now records the implemented state directly so the backlog parser
  does not re-ingest the old open-work wording as active follow-up.

## Validation
- `test -f work/PR-090-agent-runner-docs-sync.md`
