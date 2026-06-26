# Meta Glasses Mobile Bridge Routes

MGW-417 defines the mobile-side route contract for camera, audio, and display
events emitted by `mobile/src/native/metaWearablesIoBridge.js`.

The contract is an app-level bridge envelope. It does not claim raw Bluetooth or
Wi-Fi packets are IPFS, libp2p, or MCP++ transports. Bluetooth and Wi-Fi labels
describe phone-to-glasses or display-webapp routes. Payload CIDs, libp2p session
metadata, and MCP++ receipts are bridge metadata only when an app layer creates
them.

## Event Types

`META_WEARABLES_IO_BRIDGE_EVENT_TYPES` contains:

| Event type | Purpose |
| --- | --- |
| `camera` | Camera photo or video reference readiness from DAT camera access. |
| `microphone_route` | Phone OS Bluetooth microphone route readiness. |
| `speaker_route` | Phone OS Bluetooth speaker output route readiness. |
| `headphone_route` | Phone OS Bluetooth headphone output route readiness. |
| `display` | DAT native display or display-webapp render route readiness. |
| `permission` | Permission denial or permission state changes. |
| `unsupported` | Unsupported capability or unsupported DAT/Web Apps surface. |
| `disconnected` | Selected glasses/device route disconnected. |
| `stale_session` | Device or display session generation is stale. |
| `degraded_route` | Route is usable but degraded by latency, queueing, or backpressure. |
| `firmware_update` | Glasses firmware update blocks the requested route. |
| `dat_app_update` | DAT app, DAM metadata, or release-channel update blocks the route. |
| `fallback` | Mobile card, display-webapp, or alternate route fallback was selected. |

## Envelope Fields

Each normalized event includes:

- `contract`: `handsfree.meta-glasses/mobile-io-bridge-routes@0.1.0`.
- `profile`: `swissknife.mcp++/mobile-bridge-route-event@0.1.0`.
- `eventType`, `capability`, and `readiness`.
- `appBindingId` and `correlationId`.
- `bridgeRoute`: provider, route, route ID, route generation, Bluetooth route
  label, Wi-Fi route label, and `rawTransportIsIpfsLibp2pOrMcp: false`.
- `policyDecision`: outcome, reason, source, decision ID, and scopes.
- `controlPlaneDecision`: route, operation, decision ID, capability, and allow
  state for the mobile control plane.
- `payload`: redacted payload CIDs when content addressing is enabled.
- `privacy`: redaction strategy, redacted fields, retention, metadata CID, and
  whether any raw payload was included.
- `flowControl`: latency, backpressure, queue depth, and dropped message count.
- `receipts`: MCP++ route receipts with optional parent receipt CIDs.

## Route Labels

The default labels separate physical routes from bridge metadata:

| Event type | Bridge route | Bluetooth label | Wi-Fi label |
| --- | --- | --- | --- |
| `camera` | `dat-native-camera` | none | `mobile-app-control-plane` |
| `microphone_route` | `phone-os-audio-input` | `bluetooth-hfp-input` | none |
| `speaker_route` | `phone-os-audio-output` | `bluetooth-a2dp-output` | none |
| `headphone_route` | `phone-os-audio-output` | `bluetooth-a2dp-output` | none |
| `display` | `dat-native-display` | none | `display-webapp-handoff` |
| failure and fallback events | mobile/DAT gates | route-specific when applicable | route-specific when applicable |

## Invariants

- Every event must include an app binding ID.
- Every event must include a policy decision, a control-plane route decision,
  privacy redaction metadata, flow-control metadata, and at least one MCP++
  receipt.
- Payload CIDs are optional, but when present they refer to redacted app-layer
  payloads or metadata. Inline raw payloads remain redacted by contract.
- `bridgeRoute.rawTransportIsIpfsLibp2pOrMcp` is always `false`.
- Bluetooth labels identify phone OS audio or device routes only.
- Wi-Fi labels identify app-level handoff routes only.
- Unsupported, permission, disconnected, stale-session, degraded-route,
  firmware-update, DAT-app-update, and fallback events are first-class route
  outcomes, not thrown-away errors.

## Example

```js
normalizeMetaWearablesIoBridgeEvent({
  eventType: 'camera',
  appBindingId: 'app-binding-camera',
  correlationId: 'corr-camera',
  payloadCid: 'sha256:redacted-camera-photo',
  policyDecision: {
    outcome: 'allow',
    reason: 'foreground_camera_consent',
    decisionId: 'policy-camera',
  },
  privacy: {
    redactionStrategy: 'faces_and_screens_redacted',
    redactedFields: ['faces', 'screens', 'raw_payload'],
    retention: 'session',
  },
  receipts: ['sha256:camera-mcp-receipt'],
});
```

This produces a route event with a DAT camera bridge route, redacted payload CID,
policy and control-plane decisions, latency/backpressure defaults, privacy
metadata, and an MCP++ receipt while keeping raw radio transport out of
IPFS/libp2p/MCP++ claims.
