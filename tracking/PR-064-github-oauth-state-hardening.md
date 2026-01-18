# PR-064: GitHub OAuth state hardening

## Goal
Add CSRF protection to the GitHub OAuth flow by implementing `state` generation + validation.

## Why
Current OAuth endpoints intentionally omit `state` for minimal implementation. For production readiness (and safer demos), we should implement `state`.

## Scope
Backend code + tests.

## Deliverables
- `GET /v1/github/oauth/start` returns a `state` value.
- `GET /v1/github/oauth/callback` validates the provided `state` and rejects invalid/expired state.
- State storage with short TTL (e.g., 10 minutes) in DuckDB (preferred) or Redis if configured.
- Tests covering:
  - state is generated
  - callback rejects missing/invalid state
  - callback accepts valid state and consumes it (one-time use)

## Acceptance criteria
- Passing test suite: `python -m pytest -q`.
- State is not logged in plaintext at info level.
- Works in dev mode without extra setup (DB-based storage).

## Notes
- Keep changes scoped to OAuth only.
