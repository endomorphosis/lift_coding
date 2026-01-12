# Fixtures

This repo is fixture-first.

## Layout

- `tests/fixtures/transcripts/clean/` — clean command transcripts
- `tests/fixtures/transcripts/noisy/` — noisy/ambiguous transcripts
- `tests/fixtures/github/api/` — GitHub REST API fixture payloads
- `tests/fixtures/github/webhooks/` — GitHub webhook payloads (raw)
- `tests/fixtures/api/` — request/response samples for the public API

## Guidelines

- Fixtures must not contain secrets.
- Keep fixtures small and focused.
- Prefer adding a new fixture over debugging against live external services.
