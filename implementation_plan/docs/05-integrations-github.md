# GitHub Integration

## Auth model (recommended)
Use a GitHub App:
- Per-org installation
- Fine-grained repository permissions
- Webhook delivery for PRs/checks/reviews

Fallback:
- OAuth + user tokens for personal use (higher risk and harder to govern)

## Capabilities
### Read
- List PRs where user is requested reviewer / assignee
- Fetch PR details: title, description, labels, checks, approvals
- Fetch diffs (careful with size)
- Fetch review comments and latest updates

### Write (guarded)
- Post a comment
- Request reviewers
- Rerun checks (depending on CI)
- Merge PR if policies satisfied

## Webhooks (minimum)
- pull_request
- pull_request_review
- issue_comment
- check_suite / check_run

## Fixture-driven development (important)
Keep a `tests/fixtures/github/` directory with:
- webhook payload samples (JSON)
- API response samples (JSON)
Use these fixtures for:
- unit tests for normalization/summarization
- contract tests for webhook ingestion
- local dev replay (see `dev/replay_webhook.py` skeleton)
