# PR-066: Plan vs code gap matrix + prioritized backlog

## Goal
Produce the authoritative plan-vs-code gap matrix that maps:
- `implementation_plan/docs/*` and `spec/openapi.yaml`
- to the current backend/mobile implementation in `src/handsfree/*`

…then turn the gaps into a prioritized backlog (MVP1 → MVP4) with a recommended PR sequence.

## Scope
Docs-only.

## Deliverables
- New doc: `docs/plan-vs-code-gap-matrix.md`
  - Section 1: OpenAPI path-by-path coverage (Implemented / Partial / Missing)
  - Section 2: MVP checklist items coverage (Implemented / Partial / Missing)
  - Section 3: Biggest demo blockers for iOS + Ray-Ban Meta (ranked)
  - Section 4: Proposed PR breakdown (5–10 PRs) with dependencies

## Acceptance criteria
- Every OpenAPI endpoint has a row in the matrix with:
  - status
  - primary implementation file(s)
  - any configuration requirements (env vars)
  - any missing end-to-end pieces (esp. mobile)
- Clear MVP1 “demo critical path” identified.
- No code changes.

## Notes
- Prefer links to repo files over long inline excerpts.
- Be explicit about what is fixture-only vs live.
