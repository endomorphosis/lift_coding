# PR-003: Database migrations + persistence primitives

## Goal
Turn `db/schema.sql` into a migration-based schema and provide minimal persistence helpers used by commands, pending actions, audit logs, and webhook storage.

## Why (from the plan)
- `docs/04-backend.md`: DuckDB as system of record; Redis for sessions/dedupe
- `docs/06-command-system.md`: pending action tokens with expiry
- `docs/08-security-privacy.md`: audit log + retention discipline
- `db/schema.sql`: defines baseline tables for users, policies, commands, pending_actions, action_logs, webhook_events, agent_tasks

## Scope
- Add migrations tooling (e.g., Alembic/Flyway/Prisma/etc.) and convert schema
- Add DB connection configuration for local dev (docker compose)
- Implement minimal persistence APIs:
  - create/read pending actions by token (with expiry)
  - write action_logs entries with idempotency_key
  - store webhook_events with signature_ok flag
  - store commands history (with privacy toggle for transcript)

## Out of scope
- Full policy evaluation logic (PR-007)
- Any GitHub API interaction (PR-005)

## Issues this PR should close (create these issues)
- DB: introduce migration framework + initial migration
- DB: persistence layer for pending actions + audit logs
- Privacy: transcript storage flag (don’t store by default)

## Acceptance criteria
- `docker compose up -d` + migration command brings DB to latest
- Pending actions can be created and then confirmed/expired deterministically
- Action logs are written with idempotency_key and are queryable

## Dependencies
- PR-001 (dev deps running)
- Optionally PR-002 if you want to wire persistence into endpoints immediately
