# HandsFree Package Guide

This guide documents the current package structure, runtime behavior, API surface, and operational usage for the HandsFree Dev Companion backend.

## Who This Is For

- Contributors who need a practical map of the codebase.
- Mobile developers integrating against the backend API.
- Operators deploying and troubleshooting the service.
- Agents and automation tooling that need reliable entry points.

## Package Overview

The backend package lives under `src/handsfree/` and is organized by functional domains:

- `api.py`: FastAPI app construction and all HTTP endpoint handlers.
- `models.py`: Pydantic request/response models shared across endpoints.
- `auth.py`: auth-mode selection and current user resolution.
- `commands/`: command parsing, routing, pending action handling, profiles.
- `actions/`: shared direct-action orchestration (rate limits, policy, idempotency, audit logging).
- `agents/`: delegation service, runner integration points, task result views.
- `github/`: GitHub API/auth/execution adapters and live/fixture behavior.
- `ai/`: AI capability request/response orchestration and policy routing.
- `db/`: DuckDB schema migrations and persistence modules.
- `notifications/`: notification provider plumbing and delivery helpers.
- `transport/` and `peer_chat.py`: dev transport and peer chat features.
- `tts/`, `stt/`, `ocr/`: media/text conversion provider layers.
- `rate_limit.py`, `policy.py`, `security.py`: abuse prevention and policy gates.

## Core Runtime Flows

### 1. Command Flow

- Entry point: `POST /v1/command`
- Pipeline:
  - Input normalization (`text`, `audio`, `image`)
  - Intent parse
  - Router dispatch or direct intent handlers
  - Policy/rate-limit/confirmation gating for side effects
  - Structured `CommandResponse` with cards, `pending_action`, and optional `follow_on_task`
- Idempotency:
  - Command idempotency is endpoint-scoped to avoid collisions with other API contracts.

### 2. Confirmation Flow

- Entry points:
  - `POST /v1/commands/confirm`
  - `POST /v1/commands/action` (structured action execution)
- Behavior:
  - Destructive or policy-gated operations create a pending token.
  - Confirmation executes exactly once and is audit-logged.

### 3. Agent Task Flow

- Creation paths:
  - Natural language delegation (`agent.delegate` intent)
  - Structured action commands
- Task lifecycle:
  - `created -> running -> completed|failed`
  - Additional pause/resume/cancel states via control endpoints
- Data retrieval:
  - `GET /v1/agents/tasks`
  - `GET /v1/agents/tasks/{task_id}`
  - `GET /v1/agents/results`

### 4. Direct Side-Effect Actions

- Endpoints:
  - `POST /v1/actions/request-review`
  - `POST /v1/actions/rerun-checks`
  - `POST /v1/actions/comment`
  - `POST /v1/actions/merge`
- Shared enforcement:
  - User/repo policy evaluation
  - Burst + window rate limits
  - Idempotency key replay protection
  - Action/audit log writes

### 5. AI Capability Execution

- Unified endpoint:
  - `POST /v1/ai/execute`
- Compatibility endpoints:
  - Copilot summary/explain, accelerated/rag workflows, stored output reads
- Admin visibility:
  - AI backend policy report/history/snapshots under `/v1/admin/ai/*`

## API Surface by Capability

Canonical source of truth: `spec/openapi.yaml`.

Major endpoint groups:

- Commands and confirmations:
  - `/v1/command`, `/v1/commands/confirm`, `/v1/commands/action`
- Inbox and status:
  - `/v1/inbox`, `/v1/status`, `/v1/metrics`
- GitHub webhooks:
  - `/v1/webhooks/github`, retry endpoints
- Side-effect actions:
  - `/v1/actions/*`
- AI capabilities:
  - `/v1/ai/*`
- Audio/media/dev input:
  - `/v1/tts`, `/v1/dev/audio`, `/v1/dev/media`
- Peer chat and transport dev endpoints:
  - `/v1/dev/peer-chat/*`, `/v1/dev/peer-envelope`, `/v1/dev/transport-sessions*`
- Notifications and subscriptions:
  - `/v1/notifications*`, `/v1/repos/subscriptions*`
- Agent tasks and results:
  - `/v1/agents/tasks*`, `/v1/agents/results`
- GitHub OAuth connections:
  - `/v1/github/oauth/*`, `/v1/github/connections*`
- Admin APIs:
  - `/v1/admin/api-keys*`, `/v1/admin/ai/*`

## Authentication and Access Modes

Primary auth configuration is in `src/handsfree/auth.py`:

- `HANDSFREE_AUTH_MODE=dev`:
  - local/dev mode, `X-User-Id` support.
- `HANDSFREE_AUTH_MODE=jwt`:
  - bearer JWT validation.
- `HANDSFREE_AUTH_MODE=api_key`:
  - API key validation against DuckDB.

GitHub auth behavior is in `src/handsfree/github/auth.py`:

- Fixture-first behavior by default.
- Live mode from env token or explicit CLI-enabled flows.
- GitHub App token support for installation-based auth.

## Storage and State

- Primary DB: DuckDB (`DUCKDB_PATH`).
- Optional cache/queue layer: Redis.
- In-memory maps exist for compatibility and request-level optimization.
- Migrations are applied on startup; see `migrations/` and `docs/database-schema.md`.

## Testing and Validation

Common workflows:

```bash
# Full suite
.venv/bin/pytest -q

# Focused module test run
.venv/bin/pytest -q tests/test_agent_workflow.py

# Syntax validation
.venv/bin/python -m py_compile src/handsfree/api.py
```

Recommended contributor workflow:

1. Implement minimal change.
2. Run targeted tests for touched behavior.
3. Run full suite before merge.
4. Confirm OpenAPI and docs remain consistent.

## Recent Capability Areas to Be Aware Of

- Expanded agent task APIs (list/detail/results/media/control).
- Unified direct-action processing with shared policy/rate-limit/idempotency enforcement.
- AI policy reporting and snapshots under admin routes.
- Stronger command idempotency scoping to prevent cross-endpoint collisions.
- Provider selection and fallback logic updates for GitHub live/fixture behavior.

## Related Documentation

- `README.md`
- `GETTING_STARTED.md`
- `CONFIGURATION.md`
- `ARCHITECTURE.md`
- `docs/configuration-reference.md`
- `docs/mobile-client-integration.md`
- `docs/agent-runner-setup.md`
- `docs/AUTHENTICATION.md`
- `spec/openapi.yaml`
