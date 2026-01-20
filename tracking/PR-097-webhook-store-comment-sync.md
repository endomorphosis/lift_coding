# PR-097: Webhook store comment sync (DB-backed store is live)

## Why
`src/handsfree/webhooks.py` still refers to the in-memory webhook store as a “stub for PR-003 database” and claims it “will be replaced with DB in PR-003”, but the repo already contains a DB-backed webhook event store (`handsfree.db.webhook_events.DBWebhookStore`) and the API path uses it.

These stale comments are confusing during debugging and onboarding.

## Scope
- Update comments/docstrings in `src/handsfree/webhooks.py` to reflect current reality.
- No behavior changes.

## Acceptance Criteria
- Remove/replace stale “stub for PR-003 database” wording in `src/handsfree/webhooks.py`.
- Keep semantics unchanged (comment-only change).
- Tests continue to pass.

## Notes
- DB store implementation exists in `src/handsfree/db/webhook_events.py`.
- API uses DB store in `src/handsfree/api.py` via `get_db_webhook_store()`.
