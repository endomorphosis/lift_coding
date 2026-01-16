# PR-018: Implement API key authentication (DB-backed)

## Goal
Complete the plan’s production auth story by implementing API key authentication using DuckDB storage.

## Background
`api_key` auth mode exists but is explicitly not implemented. For mobile clients, a simple API key mode can be a pragmatic first production auth layer (with later upgrades to device-bound sessions).

## Scope
- Add DuckDB table(s) for API keys (hashed) and metadata (user_id, label, created_at, revoked_at).
- Implement validation in `handsfree.auth` for `HANDSFREE_AUTH_MODE=api_key`.
- Add dev/admin endpoints to create/revoke keys (dev-only guarded), or provide a CLI script.
- Add tests for auth behavior.

## Non-goals
- Full OAuth flow.
- Device attestation.

## Acceptance criteria
- In `api_key` mode, requests without a key are rejected.
- Valid keys authenticate to the correct `user_id`.
- Revoked keys are rejected.
- Keys are stored as hashes (never plaintext) and never logged.
- CI remains green.

