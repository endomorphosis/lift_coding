# PR-005: GitHub integration (read-only inbox + PR summary)

## Goal
Deliver MVP read paths: list attention items and summarize a PR with short, spoken-friendly output.

## Why (from the plan)
- `docs/05-integrations-github.md`: list PRs, fetch details/checks/reviews, careful with diffs
- `docs/01-requirements.md`: R1/R2 + MVP scope (inbox + PR summary)
- `docs/10-mvp-checklists.md`: MVP1 + MVP2

## Scope
- GitHub “provider” abstraction (real + fixture-backed)
- Inbox implementation for `inbox.list`:
  - requested reviews / assigned PRs
  - failing checks + mentions (as available)
- PR summary implementation for `pr.summarize`:
  - title/description highlights
  - diff stats (no raw code excerpts by default)
  - checks status + last review state
- Fixture-first:
  - add `tests/fixtures/github/api/*.json`
  - golden tests for `spoken_text`

## Out of scope
- GitHub App installation and token minting (can be a follow-on issue if not ready)
- Write actions (PR-007)

## Issues this PR should close (create these issues)
- GitHub: define provider interface + fixture provider
- Inbox: implement PR inbox response + spoken summarization
- PR summary: implement spoken summary + “next/repeat” navigation hooks
- Tests: golden output tests for summaries

## Acceptance criteria
- With fixture data only, `POST /v1/command` for "inbox" returns consistent, short `spoken_text`
- `summarize pr <n>` works using fixture PR details
- Summaries respect privacy mode defaults (no code snippets)

## Dependencies
- PR-004 (intent routing)
- PR-001 (fixtures + CI)
