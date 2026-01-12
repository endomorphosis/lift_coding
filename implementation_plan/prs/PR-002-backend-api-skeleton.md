# PR-002: Backend API skeleton (OpenAPI-aligned)

## Goal
Implement a minimal backend that conforms to `spec/openapi.yaml` and supports the text-first simulator flows.

## Why (from the plan)
- `implementation_plan/README.md`: start with `POST /v1/command` and `GET /v1/inbox`
- `docs/04-backend.md`: modular monolith, idempotency, webhook verification, confirmation model
- `docs/06-command-system.md`: command pipeline + pending actions

## Scope
- Implement endpoints:
  - `POST /v1/command`
  - `POST /v1/commands/confirm`
  - `GET /v1/inbox` (can be fixture-backed initially)
  - `POST /v1/webhooks/github` (accept + store raw payload, verify stub ok in dev)
  - `POST /v1/actions/request-review` and/or `POST /v1/actions/rerun-checks` as *stubbed* (real behavior in PR-007)
- Implement request/response schema validation against `spec/openapi.yaml`
- Add minimal health/status endpoint if desired (not currently in OpenAPI; either add to spec or skip)

## Out of scope
- Real GitHub API calls (PR-005)
- Real policy enforcement (PR-007)
- Mobile app (future)

## Issues this PR should close (create these issues)
- Backend: create server skeleton implementing OpenAPI routes
- Contract: add contract tests ensuring responses match schemas
- Simulator: make `dev/simulator_cli.md` commands work end-to-end

## Acceptance criteria
- Running locally on `http://localhost:8080`
- `curl` examples in `dev/simulator_cli.md` return a valid `CommandResponse`
- OpenAPI contract tests pass in CI

## Dependencies
- PR-001 (CI/dev loop)

## Notes
Choose a backend stack (Python FastAPI / Node / Go) before coding; keep the API behavior deterministic and fixture-driven.
