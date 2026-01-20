# PR-078: API key auth mode implementation

## Goal
Complete `HANDSFREE_AUTH_MODE=api_key` so the backend can authenticate requests using API keys created via the existing admin API key endpoints.

## Context
Docs state API key mode is not fully implemented and currently returns `501 Not Implemented`. The backend already has API key CRUD endpoints (`/v1/admin/api-keys`). This PR wires the auth dependency to validate incoming keys.

## Scope
- Implement API key auth dependency:
  - Accept `Authorization: Bearer <api_key>` (and optionally `X-API-Key` as a fallback if already used anywhere)
  - Validate against stored API keys (including revoked keys)
  - Associate the request with the owning `user_id`
- Ensure dev mode and JWT mode behavior remains unchanged.
- Update docs to reflect the implemented behavior.

## Non-goals
- Building an API key UI.
- Rotating keys automatically.

## Acceptance criteria
- With `HANDSFREE_AUTH_MODE=api_key`:
  - requests without a key return `401`
  - requests with an invalid key return `401`
  - requests with a revoked key return `401`
  - requests with a valid key succeed and are scoped to that user
- Tests cover the above cases.

## Suggested files
- Auth module (where `HANDSFREE_AUTH_MODE` is handled)
- `src/handsfree/db/api_keys.py`
- Docs: `docs/AUTHENTICATION.md`
- Tests under `tests/`

## Validation
- Run `python -m pytest -q`.
