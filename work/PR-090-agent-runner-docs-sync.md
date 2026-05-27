# PR-090: Agent runner docs sync

## Status
- [x] Complete

## Checklist
- [x] Read `agent-runner/runner.py` to establish current behavior
- [x] Verified `docs/agent-runner-setup.md` matches the shipped runner behavior
- [x] Verified deterministic patch mode is documented (fenced `diff` / `patch` blocks)
- [x] Verified the doc references `docs/AGENT_RUNNER_QUICKSTART.md` + `docker-compose.agent-runner.yml`
- [x] Quick read for consistency with `agent-runner/README.md`

## Notes / Log
- HAO-169 resolution: line 1 was a stale tracking annotation, not a runner behavior bug. The work note now records the current evidence instead of carrying unresolved scaffold wording.
- Evidence checked: `agent-runner/runner.py`, `agent-runner/apply_instruction.py`, `docs/agent-runner-setup.md`, `docs/AGENT_RUNNER_QUICKSTART.md`, `agent-runner/README.md`, and `docker-compose.agent-runner.yml`.
- Validation: `test -f work/PR-090-agent-runner-docs-sync.md`.
