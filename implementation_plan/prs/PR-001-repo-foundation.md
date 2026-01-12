# PR-001: Repo foundation (dev loop + CI gates)

## Goal
Stand up a tight local + CI dev loop aligned with the implementation plan: fixtures-first development, OpenAPI validation, and reproducible local dependencies.

## Why (from the plan)
- `docs/11-devloop-vscode.md`: deterministic fixtures + replay + CI gates
- `docs/01-requirements.md`: contract tests + fixtures are “critical”
- `docs/09-observability.md` / `docs/08-security-privacy.md`: structured logs, redaction, token safety

## Scope
- Add baseline repo tooling (format/lint/test placeholders wired to real commands)
- Add OpenAPI validation in CI (fail PRs if `spec/openapi.yaml` is invalid)
- Add fixture directory structure and guidance in-tree
- Add docker compose + Makefile targets that actually work (bring up Redis; DuckDB is embedded)

## Out of scope
- Implementing the backend endpoints themselves (PR-002)
- Implementing GitHub auth/integration (PR-005/006)

## Issues this PR should close (create these issues)
- Repo: add CI workflow running `fmt`, `lint`, `test`, and OpenAPI validation
- Dev loop: make `make dev` / `make test` run locally with Docker deps
- Fixtures: add canonical fixture layout (transcripts + GitHub webhooks + API samples)
- Security baseline: add logging redaction policy + secret handling guidelines (docs)

## Acceptance criteria
- `docker compose up -d` starts Redis (DuckDB is embedded)
- CI runs on PRs and fails on OpenAPI spec errors
- A contributor can run `make fmt`, `make lint`, `make test` (even if minimal) without guessing

## Dependencies
None (should be first).

## Notes
This PR is intentionally stack-agnostic; follow-on PRs can choose a backend stack (Python/Node/etc) while keeping these gates stable.
