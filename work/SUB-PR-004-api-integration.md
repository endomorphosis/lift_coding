SUB-PR: PR-004 API integration (command router wiring)

Base: draft/pr-004-command-router-and-confirmations (PR #5)
Goal: Make the PR-004 command system reachable from the HTTP API and satisfy the PR-004 acceptance criteria end-to-end.

Background
- PR #5 implemented the command system modules + transcript fixture tests.
- The FastAPI/OpenAPI server implementation is currently in PR #11 (not on this branch).

Agent checklist (keep scope tight)
- [ ] Cherry-pick/rebase the minimal API surface from PR #11 needed to run a server on http://localhost:8080.
- [ ] Wire POST /v1/command to:
  - parse transcript text -> ParsedIntent
  - route via CommandRouter
  - return deterministic CommandResponse including spoken_text
- [ ] Wire POST /v1/commands/confirm to CommandRouter confirmation flow.
- [ ] Session support for system.repeat:
  - accept session_id via header (or request field if spec requires)
  - store/replay last spoken_text per session
- [ ] Ensure side-effect intents (e.g. pr.request_review) return needs_confirmation + pending_action token.
- [ ] Add/extend tests:
  - API contract tests still pass
  - minimal integration tests for /v1/command and /v1/commands/confirm
- [ ] Keep CI green: make fmt-check, make lint, make test, make openapi-validate.

Out of scope
- Real GitHub reads/writes (PR-005/PR-007)
- DB-backed persistence (PR-003)
