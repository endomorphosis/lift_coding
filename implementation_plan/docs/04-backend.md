# Backend Services

## Suggested service layout (start as a modular monolith)
- API Gateway (REST/GraphQL)
- Command Service
- Integration Service(s)
- Policy Service
- Event/Webhook Service
- Notification Service
- Storage (Postgres + Redis)

## Storage
- Postgres: users, repos, installs, policies, action logs, command history
- Redis: short-lived sessions, rate limits, dedupe keys
- Object store: optional audio snippets (avoid unless needed)

## API endpoints (example)
- POST /v1/command
  - input: {text} OR audio blob
  - output: {spoken_text, cards?, actions?}
- POST /v1/commands/confirm
- POST /v1/webhooks/github
- GET /v1/inbox
- POST /v1/actions/request-review
- POST /v1/actions/rerun-checks
- POST /v1/actions/merge (guarded by policy)

## Operational concerns
- Idempotency keys for side-effecting actions
- Rate limiting per user + per integration
- Webhook verification and replay protection
- Multi-tenant isolation for org use
