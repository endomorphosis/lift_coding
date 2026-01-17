# PR-032: Agent runner — create real PRs from dispatch issues

## Goal
Upgrade the example/custom agent runner so it can actually:
- claim a dispatch issue
- create a working branch in the target repo
- commit changes
- open a PR containing correlation metadata the backend can parse

## Background
The repo contains a custom runner scaffold in `agent-runner/runner.py` and a Docker Compose example (`docker-compose.agent-runner.yml`). Today, the runner logs + comments but does not create PRs.

The backend already supports webhook correlation (PR opened -> task updated), so a functional runner completes the loop.

## Scope
- Implement PR creation end-to-end in `agent-runner/runner.py`:
  - clone target repo into `/workspace`
  - create a branch per task (`agent-task-<task_id_prefix>`)
  - write a small trace file (e.g., `agent-tasks/<task_id_prefix>.md`) including:
    - task_id
    - instruction
    - timestamps
    - correlation metadata comment: `<!-- agent_task_metadata {"task_id": "..."} -->`
  - commit + push
  - open a PR referencing the dispatch issue
- Add idempotency / dedupe:
  - if branch or PR already exists, update instead of failing
- Ensure the container image has needed tools (git, ssh/https auth)
- Update docs with a smoke test procedure.

## Non-goals
- Full LLM-powered code generation.
- Auto-merging PRs.

## Acceptance criteria
- Runner can process a labeled dispatch issue and open a PR in the target repo.
- PR body includes correlation metadata and references the dispatch issue.
- Runner marks the dispatch issue with a “processed” label and/or comment.

## Agent checklist
- [ ] Implement PR creation path in `agent-runner/runner.py`
- [ ] Update `agent-runner/README.md` + `docs/agent-runner-setup.md` with smoke test
- [ ] Keep Python tests green
