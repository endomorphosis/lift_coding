# PR-001 follow-ups: Repo foundation polish

This is a placeholder *draft* PR to enable later execution via Copilot coding agents.

- Source spec: implementation_plan/prs/PR-001-repo-foundation.md
- Stack note: docs/specs assume DuckDB (embedded) + Redis.

## Why this exists
PR-001 (repo foundation) is already implemented/merged, but there are typical follow-up tasks that are useful to batch separately without blocking other PR tracks.

## Candidate follow-ups (pick a minimal set)
- [ ] Add security baseline docs (redaction + secret handling) and link from top-level README
- [ ] Add `make compose-up`/`compose-down` guidance in README
- [ ] Add CI caching and/or pip cache (optional)
- [ ] Add a short CONTRIBUTING guide (optional)

## Acceptance criteria
- CI remains green
- Docs are consistent with DuckDB + Redis
