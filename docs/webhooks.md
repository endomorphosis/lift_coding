# GitHub Webhook Ingestion

This directory contains the GitHub webhook ingestion system with signature verification, replay protection, and event normalization.

## Features

- **Signature Verification**: Verifies `X-Hub-Signature-256` headers using HMAC-SHA256
  - Dev mode: accepts `"dev"` signature for local testing
  - Production mode: requires valid webhook secret
- **Replay Protection**: Prevents duplicate webhook deliveries using delivery ID tracking
- **Event Storage**: Stores raw webhook events with metadata
- **Event Normalization**: Normalizes GitHub events to a common format for:
  - `pull_request` (opened, synchronize, reopened, closed)
  - `check_suite` (completed)
  - `check_run` (completed)
  - `pull_request_review` (submitted)

## Endpoint

```
POST /v1/webhooks/github
```

**Headers:**
- `X-GitHub-Event`: GitHub event type (e.g., `pull_request`)
- `X-GitHub-Delivery`: Unique delivery ID for replay protection
- `X-Hub-Signature-256`: HMAC signature or `"dev"` for local testing

**Response:**
- `202 Accepted`: Webhook ingested successfully
- `400 Bad Request`: Invalid signature or duplicate delivery

## Local Development

### Replay Fixtures

Use `dev/replay_webhook.py` to replay webhook fixtures locally:

```bash
# Basic usage (event type inferred from filename)
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json

# With explicit event type
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json --event-type pull_request

# With custom delivery ID
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json --delivery-id my-test-001

# To a different endpoint
python dev/replay_webhook.py tests/fixtures/github/webhooks/pull_request.opened.json --url http://localhost:3000/v1/webhooks/github
```

The script will:
- Infer the event type from the filename (e.g., `pull_request.opened.json` → `pull_request`)
- Generate a unique delivery ID if not provided
- Send the webhook with dev signature

### Fixtures

Webhook fixtures are stored in `tests/fixtures/github/webhooks/`:

- `pull_request.opened.json` - New PR created
- `pull_request.synchronize.json` - PR updated with new commits
- `check_suite.completed.json` - Check suite finished
- `check_run.completed.json` - Individual check run finished
- `pull_request_review.submitted.json` - PR review submitted

## Deduplication

Duplicate deliveries are detected using the `X-GitHub-Delivery` header:

1. First webhook with delivery ID `abc123` → `202 Accepted`
2. Second webhook with same delivery ID → `400 Bad Request` with `"Duplicate delivery ID"` error

This prevents processing the same event multiple times if GitHub retries delivery.

## Testing

Run webhook tests:

```bash
make test
```

The test suite includes:
- Fixture replay tests for all event types
- Signature verification tests
- Duplicate delivery rejection tests
- Event normalization tests

## Implementation Notes

- **Storage**: Currently uses in-memory store; will be replaced with database in PR-003
- **Secrets**: Dev mode (webhook_secret=None) allows `"dev"` signature
- **Normalization**: Unsupported event types/actions are stored but not normalized
- **Notifications**: Normalized events are logged; inbox/notification updates will be added in future PRs
