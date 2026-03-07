# P2P Bluetooth + py-libp2p Improvement Plan (Berty-inspired port blueprint)

## Goal
Define a concrete, phased plan to evolve HandsFree from server-centric mobile audio routing to direct handset-to-handset peer communication over Bluetooth-backed py-libp2p transport, so smart glasses users can communicate with each other when backend connectivity is constrained.

## Why now
- The mobile stack already includes native Bluetooth audio modules, but not peer data transport.
- The backend now has an experimental `handsfree.transport.libp2p_bluetooth` scaffold and provider selection path.
- Berty’s network architecture offers a proven layered model (driver abstraction + libp2p + protocol envelopes) that can be adapted to Python and this repo’s provider patterns.
- The problem statement now explicitly requires using `berty/berty/tree/v1/network` as a porting template toward `py-libp2p`.

## Source inspirations
- Berty v1 network stack and Bluetooth + go-libp2p layering:
  - https://github.com/berty/berty/tree/v1/network
- Python libp2p target runtime:
  - https://github.com/libp2p/py-libp2p

## Current state (verified in-repo)
- Mobile Bluetooth support exists for audio integration (`mobile/modules/expo-glasses-audio`).
- Backend has transport provider abstraction with stub fallback and experimental libp2p Bluetooth wrapper (`src/handsfree/transport/`).
- No end-to-end handset discovery/session/message protocol is implemented yet.

## Target outcomes
1. Handsets discover and connect to nearby peers over Bluetooth links.
2. Peers exchange encrypted libp2p messages with explicit identity and session lifecycle.
3. Glasses voice messages can be relayed peer-to-peer when policy allows.
4. The system gracefully degrades to existing backend-mediated flows.

## Guiding principles (adapted from Berty-style networking)
- **Layered boundaries**: Bluetooth driver, libp2p transport, protocol/session layers stay isolated.
- **Pluggable runtimes**: keep optional dependency and safe fallback behavior (`stub` provider).
- **Deterministic envelopes**: explicit framing + schema versioning for wire compatibility.
- **Offline-first safety**: queue/retry/idempotency before eventual synchronization.
- **Observability-first**: structured traces without exposing sensitive payload contents.

## Porting charter: Berty (Go) -> HandsFree (Python)
This plan is a **conceptual port**, not a line-by-line code translation. We preserve Berty’s architecture patterns and runtime behavior while implementing them with Python-native interfaces and py-libp2p extension points.

### Component mapping matrix
| Berty v1 network concept (Go) | HandsFree py-libp2p target | Porting notes |
|---|---|---|
| Bluetooth driver wrappers around native platform APIs | Mobile module Bluetooth data-channel bridge | Keep native iOS/Android adapter boundaries and expose minimal JS events/API |
| go-libp2p transport integration for BLE links | `handsfree.transport.libp2p_bluetooth` provider implementation | Preserve provider factory + stub fallback contract |
| Multiaddr-based peer addressing | py-libp2p-compatible peer addressing abstraction | Define canonical peer addressing and conversion at transport boundary |
| Secure/multiplexed libp2p streams over non-TCP links | py-libp2p stream/session management | Reuse py-libp2p security and mux primitives where available |
| Protocol envelopes for session/message flows | Versioned envelope codec in Python transport layer | Enforce schema validation + backward compatibility strategy |
| Offline-first peer lifecycle and retry behavior | Session state machine + retry/ack/idempotency | Keep deterministic reconnect behavior and explicit error states |

## Proposed architecture

### A) Mobile edge layer (new)
- Add a Bluetooth data channel abstraction (not only audio route controls) in native modules:
  - iOS: CoreBluetooth peripheral/central data service wrappers
  - Android: BLE GATT + optional classic RFCOMM fallback (if needed)
- Expose a unified JS bridge API:
  - `scanPeers()`, `advertiseIdentity()`, `connectPeer(peerRef)`, `sendFrame(peerRef, bytes)`
  - events: `peerDiscovered`, `peerConnected`, `peerDisconnected`, `frameReceived`

### B) Backend transport runtime (expand existing scaffold)
- Keep `TransportProvider` factory model with env-based selection.
- Expand `libp2p_bluetooth` from envelope shim to session-aware transport:
  - identity bootstrap
  - stream multiplexing/topic routing
  - frame validation + replay protection

### C) Protocol layer (new)
- Define protocol envelopes and versioning:
  - handshake, capability exchange, message, ack, error
- Include metadata:
  - protocol version, sender peer id, conversation id, nonce, timestamp
- Add compatibility strategy:
  - reject unsupported major versions, tolerate newer optional fields

### D) Product integration layer (new)
- Add “peer mode” policy controls:
  - allow-list peers/conversations
  - explicit user consent for first connection
- Integrate peer message flow with existing command/notification paths.

## Incremental delivery plan

### Phase 0 — Foundations and RFCs
- Document frame schema and handshake flow.
- Decide BLE-only vs BLE + classic fallback per platform.
- Define threat model for local peer traffic.
- Produce a Berty-to-py-libp2p parity checklist (discovery, dial, secure session, stream, ack/retry, teardown).

### Phase 1 — Transport hardening (backend)
- Upgrade `libp2p_bluetooth` wrapper with:
  - strict envelope schema validation
  - session lifecycle callbacks
  - error taxonomy + metrics hooks
- Add deterministic fixtures for transport frames.

### Phase 2 — Mobile Bluetooth data channel MVP
- Implement native data-channel APIs in Expo modules.
- Add dev simulator hooks to emulate peer discovery and inbound frames.
- Add permission/state diagnostics for iOS/Android edge cases.

### Phase 3 — End-to-end peer session MVP
- Implement pairing handshake and authenticated session establishment.
- Add message send/receive path across two local devices.
- Add retry/ack behavior for transient disconnects.

### Phase 4 — Glasses communication UX
- Add push-to-talk “peer message” intent path.
- Add concise spoken confirmations and failure prompts.
- Add profile-aware controls for gym/walk/commute contexts.

### Phase 5 — Reliability, security, rollout
- Add chaos tests (disconnect/reconnect, duplicate frames, clock skew).
- Add encrypted payload validation and key-rotation plan.
- Roll out with feature flags and staged cohorts.

## Work breakdown (PR-oriented)
- **PR-009**: transport protocol/spec + backend transport hardening.
- **PR-010**: mobile native Bluetooth data channel bridge.
- **PR-011**: peer session handshake + identity exchange.
- **PR-012**: peer messaging UX + command integration.
- **PR-013**: resilience/security hardening + rollout controls.

## Acceptance criteria
- Two handsets can discover and establish a peer session locally.
- Peer messages are exchanged with validated envelopes and acknowledgments.
- Unsupported protocol versions fail safely with actionable diagnostics.
- Feature can be toggled off with no impact to existing backend flows.
- Telemetry can explain connection failures without leaking payloads.

## Test strategy
- Unit tests:
  - envelope codec, schema validation, version compatibility
  - provider selection and fallback behavior
- Integration tests:
  - simulated two-peer session lifecycle
  - reconnect/retry/idempotency behavior
- Device tests:
  - iOS↔iOS, Android↔Android, iOS↔Android matrix
  - background/foreground transitions and Bluetooth permission edge cases
- Security tests:
  - replay attempts, malformed frames, unauthorized peer attempts

## Risks and mitigations
- **Bluetooth platform fragmentation** -> capability matrix + per-platform fallbacks.
- **py-libp2p API drift** -> pin versions and gate upgrades with compatibility tests.
- **Battery/latency concerns** -> bounded scan windows + adaptive reconnect strategy.
- **Privacy concerns** -> consent-first pairing and minimal metadata exposure.

## Dependencies
- Existing provider abstraction (`src/handsfree/transport/__init__.py`).
- Mobile native module extension points in `mobile/modules/expo-glasses-audio`.
- Policy and notifications for user-visible safety controls.

## Operational rollout
- Feature flag: `HANDSFREE_TRANSPORT_PROVIDER=libp2p_bluetooth`.
- Add progressive enablement by profile/environment.
- Publish runbook for pairing diagnostics and failure recovery.
