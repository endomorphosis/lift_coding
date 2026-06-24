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

Bluetooth envelopes model route state such as audio input/output through the phone app. A phone-app Bluetooth envelope may include IPFS CIDs or MCP++ receipts because the app bridge produced those artifacts. It must not include libp2p peer IDs unless the bridge declares `app_layers.libp2p = "provided_by_bridge"`.

## Wi-Fi Boundary

Wi-Fi envelopes model app-level handoff through a phone app local network path or display webapp browser bridge. A Wi-Fi route can include libp2p peer/session IDs when the bridge owns the libp2p layer and records `app_layers.libp2p = "provided_by_bridge"`.

## Validation Rules

The TypeScript validator in `swissknife/src/services/meta-glasses-io-transport.ts` rejects envelopes that:

- omit device/session/app binding identity fields;
- omit control-plane route decisions, permission state, latency, backpressure, payload limits, content CIDs, receipts, policy decisions, or privacy redaction metadata;
- set `route.raw_transport_is_ipfs_libp2p_or_mcp` to anything other than `false`;
- attach libp2p peer/session IDs when the bridge did not provide libp2p;
- claim bridge-provided libp2p without peer and session IDs.

This keeps raw device transport separate from IPFS/libp2p/MCP++ semantics while still allowing the bridge to publish content-addressed, receipt-bearing MCP++ envelopes.
