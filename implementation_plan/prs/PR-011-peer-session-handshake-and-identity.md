# PR-011: Peer session handshake + identity exchange

## Goal
Establish authenticated peer sessions on top of the Bluetooth/libp2p transport so two handsets can negotiate capabilities and safely exchange messages.

## Why (from the plan)
- `implementation_plan/docs/12-p2p-bluetooth-libp2p.md`: Phase 3 (end-to-end peer session MVP).
- PR-010 provides link connectivity; this PR provides session-level trust and lifecycle.

## Scope
- Implement handshake and capability exchange envelopes.
- Add session state machine:
  - new, handshaking, established, degraded, closed
- Implement identity bootstrap and validation rules for peer metadata.
- Add ack/retry semantics for transient disconnects.
- Add structured diagnostics for failed handshakes and authorization failures.

## Out of scope
- End-user conversation UX and command integration (PR-012).
- Full key-rotation and advanced cryptographic policy hardening (PR-013).

## Issues this PR should close (create these issues)
- Transport/session: implement authenticated handshake flow.
- Identity: validate peer identity metadata and session admission checks.
- Reliability: add reconnect + retry behavior for short disconnects.

## Acceptance criteria
- Two local peers can establish an authenticated session and exchange at least one validated message envelope.
- Session failure states are explicit and actionable.
- Tests cover success path, unsupported capability, and retry after disconnect.

## Dependencies
- PR-009 envelope and protocol compatibility rules.
- PR-010 mobile data-channel bridge.
