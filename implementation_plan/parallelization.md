# Parallelization plan (tracks + PRs)

This document maps the implementation plan into parallel work tracks and draft pull requests.

## Track A — Foundation (can start immediately)
**PR-001**: Repo foundation (dev loop + CI gates)
- CI with OpenAPI validation, fixture layout, reproducible dev deps (Postgres/Redis)

## Track B — Backend contract surface (unblocks everything)
**PR-002**: Backend API skeleton (OpenAPI-aligned)
- Implements OpenAPI routes, schema validation, simulator CLI compatibility

## Track C — Storage & durability (needed for confirmations/audit/webhooks/agents)
**PR-003**: DB migrations + persistence primitives
- Pending actions, action logs, webhook event store, agent tasks

## Track D — Command system (can proceed with fixture-only providers)
**PR-004**: Command router + profiles + confirmation tokens
- Intent parsing (grammar-driven), confirmation flow, deterministic tests

## Track E — GitHub read paths (MVP1 + MVP2)
**PR-005**: GitHub read-only inbox + PR summary
- Fixture-backed provider first; golden tests for spoken summaries

## Track F — Webhooks (event-driven updates)
**PR-006**: Webhook ingestion + replay
- Signature verification (dev-mode supported), replay protection, normalization, fixture replay tests

## Track G — Safety & one write action (MVP3)
**PR-007**: Policy engine + safe write action
- Repo policies, confirmations, idempotency, audit log; implements one side effect end-to-end

## Track H — Agent delegation (MVP4 foundation)
**PR-008**: Agent orchestration stub
- Task lifecycle, provider abstraction, user-facing progress summaries

## Suggested parallel execution
1) Do PR-001, PR-002, PR-003 in sequence.
2) Then run PR-004, PR-005, PR-006 in parallel.
3) Finish with PR-007 and PR-008 (these can overlap once dependencies land).

## Notes
- Keep everything fixture-first: you can ship MVP behavior without real GitHub auth initially.
- Bake in security defaults early: redaction, least privilege tokens, audit logs, and confirmation gates.
