# PR-040: Agent runner operationalization (create/update PRs from dispatch issues)

## Goal
Turn the existing agent-runner scaffolding into a usable, documented automation path:
- A GitHub Actions workflow (or container runner) that reacts to issues labeled `copilot-agent`
- Extracts task metadata (task_id + instruction)
- Creates/updates a PR branch and posts progress back to the issue

## Scope
- `agent-runner/` code + docs
- `.github/workflows/agent-runner-example.yml` -> enable as real workflow (or add a new enabled workflow)

## Acceptance criteria
- A maintainer can follow docs to:
  - add required secrets
  - create an issue with `copilot-agent`
  - see the workflow run and produce a PR with at least a placeholder commit
  - see status comments posted back to the issue
- Workflow is disabled by default unless secrets are present (avoid surprise runs).

## Notes
- Keep least privilege tokens.
- Do not hardcode secrets; use GitHub Actions secrets.
