# PR-028: External agent runner setup guide — execution plan

This PR is intended for a Copilot agent.

## Goal
Ship clear documentation + runnable examples so an external runner can process dispatched agent tasks created by the backend.

## What already exists
- Backend dispatch provider creates issues with `<!-- agent_task_metadata {...} -->` and the label `copilot-agent`.
- Example custom runner exists in `agent-runner/`.
- Existing doc: `docs/agent-runner-setup.md` (validate completeness).

## Deliverables
1) Documentation
- Ensure `docs/agent-runner-setup.md` covers:
  - runner options (GitHub Actions vs custom docker runner)
  - required permissions + secrets
  - correlation metadata expectations
  - smoke test steps that a user can follow

2) GitHub Actions example (disabled)
- Add `.github/workflows/agent-runner-example.yml` (disabled by default):
  - triggers on issues labeled `copilot-agent` in dispatch repo
  - comments status back and/or opens a PR in the target repo
  - includes minimal required permissions documentation

3) Docker compose example (if needed)
- Ensure `docker-compose.agent-runner.yml` is documented and matches the repo’s current runner.

## Acceptance criteria
- A reader can follow the doc and successfully run *one* of:
  - the GitHub Actions example OR
  - the dockerized `agent-runner/` example
- The runner opens a PR that includes `<!-- agent_task_metadata {"task_id": "..."} -->` in its body or a committed trace file.
- No Python backend tests change/fail.
