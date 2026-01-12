SUB-PR: PR-006 DB-backed webhook event store

Base: draft/pr-006-github-webhook-ingestion-and-replay (PR #7)
Goal: Align webhook ingestion with the implementation plan by persisting webhook_events and replay protection keys to DuckDB (instead of in-memory only).

Background
- PR #7 implements webhook endpoint, signature verification, replay protection, normalization, fixtures, and replay tests.
- The DuckDB migrations + persistence primitives exist in PR #12 (DB schema + src/handsfree/db/webhook_events.py etc.).

Agent checklist (keep scope tight)
- [ ] Cherry-pick/rebase the minimal DB webhook_events persistence code from PR #12.
- [ ] Replace/augment the in-memory webhook store with a DB-backed store:
  - persist raw event payload + event_type + delivery_id + signature_ok
  - implement replay protection/dedup keyed by delivery_id via DB
- [ ] Keep existing tests passing; add DB-backed tests where needed.
- [ ] Keep dev mode working without external DB service (DuckDB embedded; Redis optional).
- [ ] Keep CI green: make fmt-check, make lint, make test, make openapi-validate.

Out of scope
- Full inbox state projection from normalized events (follow-up)
- Mobile notifications
