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
  - backend transport-envelope validation and local ack replay for bring-up
  - local advertising state and discoverability controls
  - optional auto-validation of inbound frames against backend dev ingress
- Add development simulation hooks for local testing without two physical devices.

## Concrete bridge contract
JS/native API surface:
- `scanPeers(timeoutMs?: number): Promise<PeerInfo[]>`
- `advertiseIdentity({ peerId, displayName? })`
- `connectPeer(peerRef)`
- `disconnectPeer(peerRef, reason?)`
- `sendFrame(peerRef, payloadBase64)`

Developer simulation helpers:
- `simulatePeerDiscovery(peer)`
- `simulatePeerConnection(peerRef)`
- `simulateFrameReceived(peerRef, payloadBase64, peerId?)`
- `resetPeerSimulation()`

Bridge note:
- use base64 strings for frame payloads at the Expo JS/native boundary in PR-010
- keep fragmentation, MTU handling, and raw byte transport inside native platform implementations
- current native scaffolding uses:
  - iOS: CoreBluetooth central + peripheral managers with a dedicated service UUID and frame characteristic, carrying advertised identity through discovery payloads
  - Android: Bluetooth LE scan plus GATT connection/service discovery toward the same service/characteristic IDs, with BLE advertiser bring-up behind `advertiseIdentity()`

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
- Diagnostics screen can submit a captured frame to `/v1/dev/peer-envelope` and display or replay the returned ack.
- Diagnostics screen can advertise a local identity and expose adapter readiness during handset-to-handset bring-up.
- Diagnostics screen can optionally auto-ack inbound `message` envelopes by round-tripping them through backend dev ingress.
- API surface is stable and documented for PR-011 session integration.

## Dependencies
- PR-009 transport protocol contract and envelope expectations.
- Existing module extension points under `mobile/modules/expo-glasses-audio`.
