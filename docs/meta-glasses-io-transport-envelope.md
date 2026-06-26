# Meta Glasses I/O Transport Bridge Envelope

MGW-366 defines the Swissknife app-level envelope used when Meta glasses I/O reaches MCP++ through a phone app or display webapp bridge.

The contract does not claim raw Bluetooth or raw Wi-Fi is IPFS, libp2p, or MCP++. Bluetooth and Wi-Fi are represented as device routes into a bridge. IPFS CIDs, libp2p peer/session IDs, and MCP++ receipt IDs are only bridge metadata when the phone app, display webapp, or simulator explicitly provides that layer.

## Envelope Fields

Each `MetaGlassesIOBridgeEnvelope` carries:

- `identity`: device ID, device session ID, app binding ID, app ID, and correlation ID.
- `route`: raw route (`bluetooth` or `wifi`), bridge provider, bridge route, route decision ID, control-plane route, readiness, and capability.
- `route.raw_transport_is_ipfs_libp2p_or_mcp`: always `false`.
- `permission`: permission state plus required, granted, and denied Meta glasses scopes.
- `flow_control`: latency, optional jitter, backpressure state, queued bytes, and dropped messages.
- `payload_limits`: maximum payload bytes, maximum CID count, chunking threshold, and inline payload policy.
- `content`: content-addressed payload references using `sha256:` CIDs.
- `app_layers`: IPFS, libp2p, and MCP++ availability as bridge-provided app layers.
- `receipts`: MCP++ tool receipt ID, event receipt ID, envelope CID, and policy receipt ID.
- `policy`: policy decision metadata shared with the I/O profile contract.
- `privacy`: redaction strategy, redacted fields, optional metadata CID, and reason.

## Bluetooth Boundary

Bluetooth envelopes model route state such as audio input/output through the phone app. A phone-app Bluetooth envelope may include IPFS CIDs or MCP++ receipts because the app bridge produced those artifacts. It must not include local or remote libp2p peer IDs unless the bridge declares `app_layers.libp2p = "provided_by_bridge"`.

## Wi-Fi Boundary

Wi-Fi envelopes model app-level handoff through a phone app local network path or display webapp browser bridge. A Wi-Fi route can include local and remote libp2p peer IDs plus a libp2p session ID when the bridge owns the libp2p layer and records `app_layers.libp2p = "provided_by_bridge"`.

## Validation Rules

The TypeScript validator in `swissknife/src/services/meta-glasses-io-transport.ts` rejects envelopes that:

- omit device/session/app binding identity fields;
- omit control-plane route decisions, permission state, latency, backpressure, payload limits, content CIDs, receipts, policy decisions, or privacy redaction metadata;
- pair a raw Bluetooth or Wi-Fi route with an incompatible bridge provider or bridge route;
- set `route.raw_transport_is_ipfs_libp2p_or_mcp` to anything other than `false`;
- attach libp2p peer/session IDs when the bridge did not provide libp2p;
- claim bridge-provided libp2p without local peer, remote peer, and session IDs.

This keeps raw device transport separate from IPFS/libp2p/MCP++ semantics while still allowing the bridge to publish content-addressed, receipt-bearing MCP++ envelopes.

## MGW-420 Compatibility Proof Matrix

The bridge-envelope proof is split across the Python integration test and the Swissknife MCP++ Jest conformance test:

- `tests/integration/test_meta_glasses_io_bridge_envelope.py` builds hardware-free camera, microphone audio, Neural Band, captouch, motion/orientation, phone GPS, and display envelopes. Each accepted envelope carries IPFS-style `sha256:` CIDs, app binding IDs, route decision IDs, MCP++ tool/event/policy receipts, policy decisions, latency and backpressure metadata, payload limits, redaction metadata, and fallback-ready route state.
- `swissknife/test/mcp-plus-plus/meta-glasses-io-conformance.test.ts` routes those surfaces through the Swissknife control-plane router and proves the routed decisions preserve payload CIDs, libp2p peer/session IDs when the bridge provides libp2p, MCP++ receipt CIDs, policy handoff CIDs, replay keys, privacy redaction, and app binding IDs.

The positive proof covers these app-layer flows:

- Camera capture: Wi-Fi/display-webapp bridge, IPFS payload reference, libp2p session metadata, MCP++ capture and control-route receipts.
- Audio capture and playback routes: phone-app Bluetooth bridge, no raw Bluetooth claim, content-reference redaction, MCP++ audio receipts.
- Neural Band and captouch input: display-webapp bridge, normalized intent routing, route receipts, replay keys, and metadata-only payload references.
- Motion/orientation and phone GPS context: privacy-filtered or metadata-only context descriptors without raw sensor samples, precise latitude, or longitude.
- Display output: mock widget/display payload CID, browser bridge route, route decision receipt, and unsupported-route fallback.

The deterministic failure proof covers:

- malformed envelopes with invalid CIDs or invalid profile/identity/route metadata;
- missing policy decisions or missing MCP++ tool, event, envelope, or policy receipts;
- unauthorized relays, including bridge-provided libp2p without peer/session IDs and denied policy handoffs;
- claims that raw Bluetooth or raw Wi-Fi is itself IPFS, libp2p, or MCP++;
- payload-limit violations when content CID count exceeds the envelope limit;
- replayed control-plane events, hard backpressure, stale or unsupported route readiness, and denied policy outcomes.

Raw Bluetooth and Wi-Fi remain transport facts. IPFS, libp2p, and MCP++ remain bridge-provided app-layer facts with explicit receipts and policy decisions.
