# PR-041: GitHub live read-paths for inbox + PR summary

## Goal
Move beyond fixture-only GitHub reads for the core intents:
- `inbox.list`
- `pr.summarize`

## Scope
- Implement live mode in the GitHub provider when auth is available (GitHub App or OAuth)
- Keep fixture mode as default/fallback

## Acceptance criteria
- With a configured GitHub auth token for the user:
  - `POST /v1/command` with "inbox" returns real PRs requested/assigned for that user
  - `POST /v1/command` with "summarize pr <n>" returns real title/checks/reviews stats
- In fixture/no-auth mode:
  - behavior remains deterministic and tests stay green
- Strict privacy mode remains the default (no code excerpts)

## Notes
- Prefer GitHub App auth where possible; OAuth acceptable for dev.
