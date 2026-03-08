# PR-012: Peer messaging UX + command integration

## Goal
Integrate peer session transport into the user-facing command and glasses interaction paths so smart glasses users can communicate with each other over peer links.

## Why (from the plan)
- `implementation_plan/docs/12-p2p-bluetooth-libp2p.md`: Phase 4 (glasses communication UX).
- Prior PRs establish transport/session mechanics; this PR makes them product-usable.

## Scope
- Add peer messaging command intents and routing integration.
- Add consent-first controls:
  - first-connection approval
  - peer allow-list management hooks
- Add voice/notification feedback for:
  - message sent
  - delivery failure
  - reconnect/retry status
- Integrate policy checks for when peer mode is allowed vs blocked.

## Out of scope
- Deep reliability tuning and rollout cohorting (PR-013).
- Additional transport protocols beyond Bluetooth/libp2p path.

## Issues this PR should close (create these issues)
- Commands: add peer-send and peer-session status intents.
- UX: add concise spoken confirmations and failure prompts.
- Policy: enforce consent and allow-list gating for peer communication.

## Acceptance criteria
- A user can initiate peer communication through existing command pathways.
- User receives deterministic spoken/visual status for send success/failure.
- Policy-denied actions fail safe with actionable user messaging.

## Dependencies
- PR-011 session handshake and identity validation.
- Existing command/policy infrastructure in backend and mobile surfaces.
