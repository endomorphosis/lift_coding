PR-010: Mobile Bluetooth data-channel bridge (iOS + Android)

Placeholder branch for a future draft PR.

- Source spec: implementation_plan/prs/PR-010-mobile-bluetooth-data-channel-bridge.md
- Stack note: docs/specs assume DuckDB (embedded) + Redis.

## Task checklist
- [ ] Implement the work described in the source spec
- [ ] Add/extend fixture-first tests
- [ ] Ensure CI passes (fmt/lint/test/openapi)

---

# PR-010: Mobile Bluetooth data-channel bridge (iOS + Android)

## Goal
Implement the first production-usable mobile Bluetooth data-channel APIs needed for handset-to-handset peer transport, while preserving existing audio behavior.

## Why (from the plan)
- `implementation_plan/docs/12-p2p-bluetooth-libp2p.md`: Phase 2 (mobile Bluetooth data channel MVP).
- PR-009 establishes protocol/runtime expectations that mobile links must satisfy.

## Scope
- Add native module APIs for peer data transport primitives:
  - `scanPeers()`, `advertiseIdentity()`, `connectPeer(peerRef)`, `sendFrame(peerRef, bytes)`
  - events: `peerDiscovered`, `peerConnected`, `peerDisconnected`, `frameReceived`
- Implement platform adapters:
  - iOS CoreBluetooth data service wrappers
  - Android BLE GATT data channel wrappers
- Add diagnostics surfaces:
  - permission state
  - adapter/bluetooth enabled state
  - connection error reasons (redacted)
- Add development simulation hooks for local testing without two physical devices.

## Out of scope
- End-to-end authenticated session handshake logic (PR-011).
- UX-level peer messaging flows (PR-012).
- Final battery/performance optimization pass (PR-013).

## Issues this PR should close (create these issues)
- Mobile: implement Bluetooth data-channel bridge API parity across iOS/Android.
- Mobile: emit normalized peer lifecycle events to JS layer.
- Mobile: add diagnostics and developer simulation hooks.

## Acceptance criteria
- App can discover nearby peers and open/close Bluetooth data links on both iOS and Android.
- App can send and receive binary frames over the data channel.
- API surface is stable and documented for PR-011 session integration.

## Dependencies
- PR-009 transport protocol contract and envelope expectations.
- Existing module extension points under `mobile/modules/expo-glasses-audio`.
