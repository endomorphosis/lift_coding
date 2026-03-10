# PR-100: Dev README GitHub mode sync (fixtures vs live)

## Why
`dev/README.md` currently says “Real GitHub API calls are planned but not yet implemented (falls back to fixtures)”.

The codebase already supports live GitHub calls when configured (e.g., via `GITHUB_TOKEN` and/or GitHub App installation token minting). Default fixture mode is still supported.

This doc should reflect the current behavior and the knobs to control it.

## Scope
- Update `dev/README.md` to describe fixture vs live GitHub modes accurately.
- Mention the relevant environment variables (`GITHUB_TOKEN`, `HANDS_FREE_GITHUB_MODE`, `GITHUB_LIVE_MODE`, and `HANDSFREE_GH_CLI_ENABLED`).
- Doc-only change.

## Acceptance Criteria
- `dev/README.md` no longer claims live GitHub is “not yet implemented”.
- `dev/README.md` documents how to enable live mode, how to force fixture mode, and when CLI fallback applies.
- No behavior changes.
- Tests continue to pass.
