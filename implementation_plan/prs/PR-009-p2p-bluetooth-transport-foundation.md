# PR-009: P2P Bluetooth transport foundation (Berty v1 network port)

## Goal
Deliver the first production-grade slice of handset peer networking by hardening the backend libp2p bluetooth transport path and defining a versioned protocol contract compatible with future mobile data-channel work.

## Why (from the plan)
- `implementation_plan/docs/12-p2p-bluetooth-libp2p.md`: phased roadmap and architecture.
- Berty-inspired layering: driver abstraction + libp2p + protocol/session separation.
- Existing scaffold in `src/handsfree/transport/` provides safe provider fallback and needs protocol/session hardening.

## Scope
- Add a Berty-parity mapping appendix for this slice:
  - which Berty networking behaviors are matched in PR-009
  - which behaviors remain for PR-010+
- Define and document wire envelopes:
  - handshake, message, ack, error
  - version fields + compatibility rules
- Harden backend transport module:
  - envelope validation and explicit error taxonomy
  - lifecycle hooks for session start/close/failure
  - deterministic test fixtures for invalid and valid frames
- Add observability hooks:
  - connection attempt outcomes
  - protocol rejection reasons (redacted)

## Concrete implementation contract
Backend transport module must provide:
- protocol ID: `/handsfree/bluetooth/1.0.0`
- envelope kinds: `handshake`, `message`, `ack`, `error`
- session states: `new`, `handshaking`, `established`, `degraded`, `closed`
- driver bridge contract:
  - `start()`
  - `send_frame(peer_ref, frame)`
  - `set_frame_handler(handler)`

Validation requirements:
- reject mismatched major protocol versions
- reject malformed or oversized frames
- reject message/ack/error frames for unknown sessions
- auto-ack valid inbound message frames

py-libp2p integration requirement:
- runtime must stay optional at import time and only activate when `HANDSFREE_TRANSPORT_PROVIDER=libp2p_bluetooth`
- foundation code should detect py-libp2p capabilities, but not assume upstream Bluetooth transport support exists

## Out of scope
- Mobile native Bluetooth data-channel implementation.
- Full two-device pairing UX in the mobile app.
- Final cryptographic key-exchange protocol for production.

## Issues this PR should close (create these issues)
- Transport: define versioned peer envelope schema + compatibility behavior.
- Transport: add lifecycle callbacks and explicit error categories.
- Tests: add frame fixture suite for malformed/unsupported envelope cases.
- Observability: add transport-level structured telemetry fields.

## Acceptance criteria
- `libp2p_bluetooth` validates envelopes using an explicit schema contract.
- Protocol major-version mismatch is rejected safely with clear diagnostics.
- Unit tests cover success path + malformed frame + unsupported version.
- Stub fallback remains default and unchanged when libp2p runtime is unavailable.

## Dependencies
- Existing transport abstraction: `src/handsfree/transport/__init__.py`.
- Existing transport tests: `tests/test_transport_providers.py`.
