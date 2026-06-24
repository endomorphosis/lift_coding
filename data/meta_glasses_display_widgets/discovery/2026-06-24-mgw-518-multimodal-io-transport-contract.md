# MGW-518 Meta Glasses Multimodal IO Transport Contract

Date: 2026-06-24

MGW-518 defines the first hardware-free Swissknife control-plane contract for
Meta glasses camera, microphone, headphones, display, captouch, and Neural Band
inputs:

- Contract: `handsfree.meta-glasses/multimodal-io-control-plane@0.1.0`
- Mock boundary: `handsfree.meta-glasses/mock-multimodal-io-boundary@0.1.0`
- MCP++ envelope profile: `swissknife.mcp++/event-envelope@0.1.0`
- Control plane route: `swissknife.mobile_orb.publish_glasses_event`

The event boundary is intentionally above native hardware APIs. Hardware-free
mocks, mobile fixtures, and later native DAT/Web Apps adapters all emit the same
envelope fields: contract, profile, event type, device, source, edge session ID,
app binding ID, correlation ID, payload, transport metadata, handoff metadata,
fallback state, control-plane route, policy decision, and receipts.

Covered event families:

- `camera.photo_ref` and `camera.video_frame_ref` for content-addressed camera
  payload references.
- `microphone.route_state` and `microphone.transcript_ref` for Bluetooth
  microphone route state and optional transcript references without raw-audio
  leakage.
- `headphones.route_state` and `headphones.playback_state` for speaker/headphone
  output state.
- `display.lifecycle_state` and `display.action` for display session and widget
  action state.
- `captouch.intent` and `Neural Band.intent` for normalized Arrow/Enter style
  input events.
- `permission.state` and `transport.handoff` for DAT availability fallbacks and
  IPFS/libp2p/MCP++ handoff metadata.

Transport assumptions:

- Bluetooth is modeled as phone-to-glasses audio route and capability state.
- Wi-Fi is modeled as app-level reachability through mobile edge or Web App
  handoff.
- Raw Bluetooth or Wi-Fi sockets are not described as IPFS or libp2p transport.
- IPFS CIDs, libp2p peer IDs, libp2p session IDs, latency, backpressure, policy
  decisions, control-plane route decisions, and MCP++ receipts live in envelope
  metadata.
- DAT camera/display package availability is optional; `dat_unavailable`,
  `permission_denied`, `unsupported_capability`, `route_degraded`, and
  `route_lost` are expected fallback states, not test failures.

Implementation evidence:

- Backend builder and constants:
  `src/handsfree/meta_glasses_multimodal_io_transport_contract.py`
- Swissknife app-facing TypeScript contract:
  `swissknife/src/services/meta-glasses-multimodal-io-transport-contract.ts`
- Mobile mock boundary helper:
  `mobile/src/utils/metaGlassesMultimodalIoTransportContract.js`
- Focused tests:
  `tests/test_meta_glasses_multimodal_io_transport_contract.py`
  `mobile/src/utils/__tests__/metaGlassesMultimodalIoTransportContract.test.js`

Validation commands:

```bash
PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py tests/test_meta_glasses_multimodal_io_transport_contract.py
rg -n "MGW-518|camera|microphone|headphones|Neural Band|captouch|IPFS|libp2p|MCP\\+\\+|control plane" implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md data/meta_glasses_display_widgets/discovery swissknife mobile tests
```
