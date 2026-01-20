# PR-077: GitHub rate limit handling (live provider)

## Goal
Make live GitHub API mode degrade gracefully under rate limiting, using correct GitHub rate-limit signals, and providing a clean fallback behavior for the demo.

## Context
`LiveGitHubProvider` makes real HTTP calls via `httpx`. GitHub rate limiting typically returns **403** with `X-RateLimit-Remaining: 0` (not 429). For the demo, when rate-limited we should:
- Return a user-friendly error OR
- Fall back to cached/fixture results (preferred for read-only endpoints)

## Scope
- Improve rate-limit detection in the GitHub HTTP client:
  - Detect 403 with `X-RateLimit-Remaining: 0`
  - Use `X-RateLimit-Reset` to compute a human-readable retry time
- Add a small retry policy for transient errors:
  - 502/503/504: bounded retries with jitter
  - do **not** retry 401/403 auth/permission errors
- Ensure existing behavior remains: if live mode fails, provider falls back to fixtures.

## Non-goals
- Implementing a full persistent cache.
- Adding write APIs.

## Acceptance criteria
- When GitHub responds with a rate-limit error, the provider:
  - logs a clear message without leaking tokens
  - raises a helpful `RuntimeError` OR triggers fixture fallback (consistent with existing wrapper behavior)
- Unit tests cover at least:
  - 403 + `X-RateLimit-Remaining=0` treated as rate limit
  - transient 503 retries occur within bounds

## Suggested files
- `src/handsfree/github/provider.py`
- Tests under `tests/` (new)

## Validation
- Run `python -m pytest -q`.
