# GitHub Webhook Development Guide

This guide explains how to develop and test GitHub webhook ingestion locally.

## Quick Start

### 1. Install Dependencies

```bash
make deps
```

This installs all required Python packages and the handsfree package in editable mode.

### 2. Run the Server

```bash
make dev
```

The server will start on `http://localhost:8080` with auto-reload enabled.

### 3. Replay a Webhook Fixture

In another terminal:

```bash
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json
```

You should see:
```
Replaying webhook:
  File: tests/fixtures/github/webhooks/pull_request.opened.json
  Event type: pull_request
  Delivery ID: replay-<uuid>
  URL: http://localhost:8080/v1/webhooks/github

Response: 202
{
  "event_id": "<uuid>",
  "message": "Webhook accepted"
}
```

## Available Fixtures

All fixtures are located in `tests/fixtures/github/webhooks/`:

- `pull_request.opened.json` - New PR created
- `pull_request.synchronize.json` - PR updated with new commits
- `check_suite.completed.json` - Check suite finished
- `check_run.completed.json` - Individual check run finished
- `pull_request_review.submitted.json` - PR review submitted

## Replay Script Options

The `dev/replay_webhook.py` script supports several options:

```bash
# Basic usage (event type inferred from filename)
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json

# Specify event type explicitly
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json \
  --event-type pull_request

# Use a specific delivery ID
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json \
  --delivery-id my-test-001

# Send to a different endpoint
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json \
  --url http://localhost:3000/v1/webhooks/github

# View all options
python dev/replay_webhook.py --help
```

## Testing

Run all tests:

```bash
make test
```

Run only webhook tests:

```bash
python3 -m pytest tests/test_webhooks.py -v
```

Run a specific test:

```bash
python3 -m pytest tests/test_webhooks.py::TestWebhookIngestion::test_duplicate_delivery_rejected -v
```

## Code Quality Checks

```bash
# Format code
make fmt

# Check formatting
make fmt-check

# Run linter
make lint

# Validate OpenAPI spec
make openapi-validate

# Run all checks
make fmt-check lint test openapi-validate
```

## How It Works

### Signature Verification

In dev mode (default), the webhook endpoint accepts the special signature `"dev"`:

```python
X-Hub-Signature-256: dev
```

In production, you would configure a webhook secret and the endpoint would verify the HMAC-SHA256 signature.

### Replay Protection

Each webhook must have a unique `X-GitHub-Delivery` header. If the same delivery ID is sent twice, the second request is rejected with a 400 error:

```json
{
  "detail": "Duplicate delivery ID"
}
```

### Event Normalization

Webhooks are normalized to a common format. For example, a `pull_request` opened event becomes:

```python
{
    "event_type": "pull_request",
    "action": "opened",
    "repo": "testorg/testrepo",
    "pr_number": 123,
    "pr_title": "Add webhook ingestion feature",
    "pr_author": "testuser",
    "base_ref": "main",
    "head_ref": "feature-branch",
    "head_sha": "abc123def456",
    # ...
}
```

This normalized format makes it easier to process events consistently.

### Event Storage

All webhook events are stored with metadata:

- `id`: Unique event ID (UUID)
- `source`: Always "github"
- `event_type`: GitHub event type (e.g., "pull_request")
- `delivery_id`: GitHub delivery ID for replay protection
- `signature_ok`: Whether signature verification passed
- `payload`: Raw webhook payload (JSON)

Currently stored in-memory; will be persisted to database in PR-003.

## Adding New Fixtures

1. Trigger the webhook on GitHub (or use GitHub's webhook redelivery feature)
2. Copy the payload to a new file in `tests/fixtures/github/webhooks/`
3. Name it following the pattern: `{event_type}.{action}.json`
4. Add a test case in `tests/test_webhooks.py` if needed

Example:

```bash
# Create new fixture
cat > tests/fixtures/github/webhooks/pull_request.closed.json << 'EOF'
{
  "action": "closed",
  "pull_request": { ... },
  ...
}
EOF

# Replay it
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.closed.json
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'handsfree'"

Run `make deps` to install the package in editable mode.

### "Connection refused" when replaying webhooks

Make sure the server is running with `make dev`.

### Duplicate delivery ID error

Each replay generates a unique delivery ID by default. If you're specifying `--delivery-id`, make sure to use a different value each time, or restart the server to clear the in-memory store.

### Port 8080 already in use

The server runs on port 8080 by default. If this port is in use, you can either:
- Stop the process using that port
- Modify `src/handsfree/server.py` to use a different port
- Use the `--url` option with `dev/replay_webhook.py` to point to a different port

## Next Steps

- **PR-003**: Replace in-memory store with DuckDB database
- **Inbox updates**: Use normalized events to update user inbox/notifications
- **Production deployment**: Configure webhook secret for signature verification
- **More event types**: Add normalization for additional GitHub event types as needed
