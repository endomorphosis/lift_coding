# PR-060: iOS + Ray-Ban Meta implementation queue (docs-only)

## Goal
Create a single, ordered implementation queue for **iOS + Ray-Ban Meta MVP1** so we can execute work in the right dependency order.

This is docs-only, and is meant to drive subsequent implementation PRs.

## Why
We already have a lot of mobile/glasses work tracked across multiple PRs. The missing piece is a crisp "do these in this order" plan with clear gates:
- what unlocks the first end-to-end demo
- what can be deferred
- what to verify after each step

## Scope
- Add a doc that lists:
  - the recommended PR execution order
  - dependency edges (backend vs mobile vs infra)
  - demo gates: MVP1-ready, MVP2-ready, MVP3-ready, MVP4-ready
  - the minimum smoke test for each stage

## Non-goals
- Implementing any mobile or backend features.

## Deliverables
- `docs/ios-rayban-implementation-queue.md`

## Acceptance criteria
- The queue is explicit and executable by a dev team.
- Each step has a verification checklist.
- The queue references existing tracking PRs instead of duplicating their content.

## Related tracking PRs
- PR-029 (client integration contract)
- PR-033 (Bluetooth audio routing guidance)
- PR-037 (audio capture + dev upload)
- PR-047 (iOS route monitor)
- PR-048 (iOS recorder)
- PR-049 (iOS player)
- PR-059 (MVP1 runbook)
