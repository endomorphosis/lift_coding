# Database Schema Reference

This document is the database-oriented companion to [ARCHITECTURE.md](../ARCHITECTURE.md#database-schema).

The source of truth for schema shape is:
- SQL migrations in [migrations/](../migrations/)
- DB access modules in [src/handsfree/db/](../src/handsfree/db/)

## Storage

- Engine: DuckDB
- Default path: `data/handsfree.db`
- Connection and migration entrypoint: [src/handsfree/db/connection.py](../src/handsfree/db/connection.py)

## Table Inventory

### Core identity and policy

- `users` (migrations/001_initial_schema.sql)
- `github_connections` (migrations/001_initial_schema.sql)
- `repo_policies` (migrations/001_initial_schema.sql)
- `repo_subscriptions` (migrations/003_add_repo_subscriptions.sql)

### Command execution and safety

- `commands` (migrations/001_initial_schema.sql)
- `pending_actions` (migrations/001_initial_schema.sql)
- `action_logs` (migrations/001_initial_schema.sql)
- `idempotency_keys` (migrations/004_add_idempotency_keys_table.sql)

### Notifications and delivery

- `notifications` (migrations/002_add_notifications_table.sql)
- `notification_subscriptions` (migrations/004_add_notification_subscriptions.sql)

Notable notification-related schema evolution:
- throttling/dedupe fields (migrations/006_add_notification_throttling_dedupe.sql)
- delivery tracking fields (migrations/009_add_notification_delivery_tracking.sql)
- platform field expansion (migrations/008_add_platform_to_notification_subscriptions.sql)

### Webhooks and agent orchestration

- `webhook_events` (migrations/001_initial_schema.sql)
- `agent_tasks` (migrations/001_initial_schema.sql)
- `api_keys` (migrations/007_add_api_keys_table.sql)
- `oauth_states` (migrations/010_add_oauth_state_table.sql)

Notable webhook schema evolution:
- webhook processing fields (migrations/006_add_webhook_processing_fields.sql)

### AI and transport features

- `ai_history_index` (migrations/013_add_ai_history_index.sql)
- `ai_backend_policy_snapshots` (migrations/015_add_ai_backend_policy_snapshots.sql)
- `peer_chat_messages` (migrations/011_add_peer_chat_messages.sql)
- `transport_session_cursors` (migrations/014_add_transport_session_cursors.sql)

Notable peer chat schema evolution:
- priority field (migrations/012_add_peer_chat_priority.sql)
- task snapshot field (migrations/013_add_peer_chat_task_snapshot.sql)

## Operational Notes

- Migrations run at backend startup through `run_migrations(...)`.
- For local development and tests, schema migration order is important and encoded by numeric filename prefixes.
- New features should include migration files and corresponding DB access helpers in [src/handsfree/db/](../src/handsfree/db/).

## Related Docs

- [ARCHITECTURE.md](../ARCHITECTURE.md#database-schema)
- [docs/persistent-database.md](persistent-database.md)
- [migrations/README.md](../migrations/README.md)
