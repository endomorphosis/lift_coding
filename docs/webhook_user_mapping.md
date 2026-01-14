# Webhook User Mapping Configuration

This document describes how to configure webhook user mapping and production secrets.

## Overview

Webhook events from GitHub are now routed to the appropriate user(s) based on:
1. **Repository subscriptions**: Users explicitly subscribed to a repository
2. **GitHub App installations**: Users connected via a GitHub App installation_id

If no mapping exists, the webhook is accepted but no notification is created (logged for debugging).

## Environment Configuration

### Development/Test Mode

By default (when `GITHUB_WEBHOOK_SECRET` is not set), the webhook endpoint accepts the special signature `"dev"` for testing:

```bash
# No environment variable needed - dev mode is default
curl -X POST http://localhost:8000/v1/webhooks/github \
  -H "X-GitHub-Event: pull_request" \
  -H "X-GitHub-Delivery: test-12345" \
  -H "X-Hub-Signature-256: dev" \
  -H "Content-Type: application/json" \
  -d @webhook_payload.json
```

### Production Mode

Set the `GITHUB_WEBHOOK_SECRET` environment variable to enable real signature verification:

```bash
export GITHUB_WEBHOOK_SECRET="your-webhook-secret-from-github"
```

With this set:
- The special `"dev"` signature is **rejected**
- Only valid HMAC-SHA256 signatures are accepted
- Signatures are computed as: `sha256=HMAC_SHA256(secret, payload_bytes)`

## Setting Up User Subscriptions

### Via Database

To receive webhook notifications for a repository, users need a subscription:

```python
from handsfree.db.repo_subscriptions import create_repo_subscription

# Subscribe user to a repository
create_repo_subscription(
    conn=db,
    user_id="user-uuid-here",
    repo_full_name="owner/repo",
    installation_id=12345  # optional: GitHub App installation ID
)
```

### Via GitHub App Installation

Users connected via GitHub App automatically receive notifications for repositories in that installation:

```python
from handsfree.db.github_connections import create_github_connection

# Create connection for GitHub App installation
create_github_connection(
    conn=db,
    user_id="user-uuid-here",
    installation_id=12345,
    token_ref="secret-manager-ref",
    scopes="repo,read:org"
)
```

## Webhook Payload Requirements

Webhook payloads should include:
- `repository.full_name` - Used to look up subscribed users
- `installation.id` (optional) - Used to look up users by GitHub App installation

Example:
```json
{
  "action": "opened",
  "pull_request": { ... },
  "repository": {
    "full_name": "owner/repo"
  },
  "installation": {
    "id": 12345
  }
}
```

## Migration

The `repo_subscriptions` table is created automatically by migration `003_add_repo_subscriptions.sql`.

Run migrations on startup:
```python
from handsfree.db.migrations import run_migrations

run_migrations(db_connection)
```

## Testing

### Unit Tests

See `tests/test_webhook_user_mapping.py` for comprehensive examples:
- Secret verification in dev/prod modes
- User routing by repository subscription
- User routing by installation_id
- Multiple users per webhook
- No-op behavior for unsubscribed repos

### Integration Testing

```bash
# Run webhook-specific tests
make test tests/test_webhook_user_mapping.py

# Run all webhook tests
make test tests/test_webhooks.py tests/test_notifications_api.py
```

## Troubleshooting

### Webhooks accepted but no notifications created

Check logs for:
```
No users subscribed to repo 'owner/repo' (installation_id=12345), skipping notification
```

Solution: Add a repo subscription or GitHub connection for the user.

### Signature verification fails in production

Verify:
1. `GITHUB_WEBHOOK_SECRET` matches your GitHub webhook secret
2. Payload is sent as raw bytes (not pre-parsed JSON)
3. `X-Hub-Signature-256` header format is `sha256=<hex_digest>`

### Dev signature rejected

Check that `GITHUB_WEBHOOK_SECRET` is **not** set in your environment. The `"dev"` signature only works when no secret is configured.
