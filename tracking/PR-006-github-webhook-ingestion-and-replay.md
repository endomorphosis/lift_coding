PR-006: GitHub webhook ingestion + fixture replay

This is a placeholder *draft* PR to enable later execution via Copilot coding agents.

- Source spec: implementation_plan/prs/PR-006-github-webhook-ingestion-and-replay.md
- Stack note: docs/specs assume DuckDB (embedded) + Redis.

## Task checklist
- [ ] Implement the work described in the source spec
- [ ] Add/extend fixture-first tests
- [ ] Ensure CI passes (fmt/lint/test/openapi)

---

# PR-006: GitHub webhook ingestion + fixture replay

## Goal
Ingest GitHub webhooks, verify signatures, normalize events, and drive inbox/notification updates in a fixture-driven way.

## Why (from the plan)
- `docs/05-integrations-github.md`: minimum webhook set
- `docs/04-backend.md`: webhook verification + replay protection + event store
- `dev/replay_webhook.py`: local replay harness
- `docs/11-devloop-vscode.md`: never debug live webhooks if avoidable

## Scope
- Implement `POST /v1/webhooks/github` with:
  - signature verification (dev mode can accept `dev` signature)
  - replay protection keyed by delivery id
  - raw event storage in `webhook_events`
- Event normalization layer (at least):
  - pull_request opened/synchronize
  - check_suite/check_run completed
  - pull_request_review submitted
- Fixture set under `tests/fixtures/github/webhooks/*.json` + replay tests
- Improve `dev/replay_webhook.py`:
  - infer `X-GitHub-Event` header from filename or CLI flag
  - optionally send delivery id header

## Out of scope
- Real push notifications to mobile (can be mocked to logs initially)

## Issues this PR should close (create these issues)
- Webhooks: implement verification + replay protection
- Webhooks: add normalization for PR/check/review events
- Dev tool: make replay script support multiple event types
- Tests: webhook fixture replay test suite

## Acceptance criteria
- Posting a stored fixture returns `202` and writes a `webhook_events` record
- Duplicate deliveries are rejected/deduped
- Normalized events can be queried/used to update inbox state (even if minimal)

## Dependencies
- PR-002 (API endpoint)
- PR-003 (event store) strongly recommended
