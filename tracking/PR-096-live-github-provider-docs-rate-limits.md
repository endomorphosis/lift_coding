# PR-096: Live GitHub provider docs update (rate limits)

## Goal
Update `docs/live-github-provider.md` so it no longer claims rate limit handling is “not yet implemented”, once PR-077 lands.

## Context
`docs/live-github-provider.md` currently includes:
- “(Not yet implemented) Will handle GitHub API rate limits gracefully…”

…but we have an open PR implementing rate limit handling: https://github.com/endomorphosis/lift_coding/pull/289 (PR-077).

This PR keeps the documentation aligned with the codebase and reduces confusion for demo operators.

## Scope
- Update the “Rate Limiting” section in `docs/live-github-provider.md`:
  - remove “not yet implemented” language
  - briefly describe the implemented behavior (retry/backoff, graceful fallback, caching if applicable)
  - link to PR-077 for details

## Non-goals
- Implementing rate limiting logic (handled by PR-077).

## Acceptance criteria
- The doc accurately reflects the current behavior after PR-077.
- Doc changes are minimal and focused.

## Suggested files
- `docs/live-github-provider.md`

## Validation
- Doc review for accuracy vs `src/handsfree/github/provider.py` after PR-077.
