# SwissKnife Mobile ORB Bridge Plan

## Goal

Use the local `swissknife` package, MCP-IDL interface descriptors, the SwissKnife Object Request Broker, and MCP++ service adapters as the bridge layer on the mobile phone between Meta Ray-Ban glasses and external services.

The phone should behave as an ORB edge node:

- It terminates the glasses/DAT/Web App side of the world.
- It normalizes glasses events into interface-described operations.
- It invokes approved local or remote services through the ORB.
- It routes service results back to glasses display, Web App display, audio, mobile card, or notification fallbacks.
- It keeps descriptors, receipts, correlation IDs, policy decisions, and provenance visible across every hop.

## Current Repo Anchors

Use these existing pieces instead of introducing a parallel bridge protocol:

- SwissKnife package: `swissknife@0.0.53`
- MCP-IDL implementation: `swissknife/src/services/mcp-idl.ts`
- ORB implementation: `swissknife/src/services/mcp-orb-capability-router.ts`
- Meta glasses ORB adapter: `swissknife/src/services/meta-glasses-display-orb-adapter.ts`
- Display widget compiler: `swissknife/src/services/meta-glasses-widget-compiler.ts`
- Display profile: `swissknife/src/services/meta-glasses-display-profile.ts`
- Existing display bridge descriptor: `spec/meta_glasses_display_widget_orb_interface.json`
- Existing display bridge mapping: `spec/meta_glasses_display_widget_orb_mapping.md`
- New phone edge descriptor: `spec/meta_glasses_mobile_orb_bridge_interface.json`
- Mobile action mapping: `mobile/src/utils/metaWearablesDatDisplayWidgetContract.js`
- Mobile DAT bridge wrapper: `mobile/src/native/wearablesBridge.js`
- Backend widget models: `src/handsfree/models.py`
- MCP++ client scaffold: `src/handsfree/mcp/client.py`

## Target Architecture

```text
Meta Ray-Ban glasses
  DAT session / Web App / Neural Band / captouch / audio / camera
        |
        v
Mobile phone as ORB edge node
  - DAT native bridge
  - Web App bridge
  - local SwissKnife ORB handlers
  - descriptor registry cache
  - policy and receipt envelope cache
        |
        v
SwissKnife MCP-IDL + ORB
  - interface CID selection
  - bind/discover/invoke/stream/recover
  - local/http/websocket/mcp-server transports
        |
        v
HandsFree backend control plane
  - policy
  - command routing
  - audit
  - MCP++ runtime
  - provider adapters
        |
        v
External services
  - GitHub
  - IPFS/IPLD services
  - ipfs_datasets
  - ipfs_kit
  - ipfs_accelerate
  - model/tool providers
```

## Contract Split

Use two descriptors.

### 1. Display Widget Descriptor

`spec/meta_glasses_display_widget_orb_interface.json` remains responsible for display-specific operations:

- `render_widget`
- `update_widget`
- `clear_widget`
- `focus_next`
- `activate`
- `reset_session`
- `play_video`
- `subscribe_updates`

This descriptor maps directly to existing mobile action IDs and DAT bridge methods.

### 2. Mobile ORB Edge Descriptor

`spec/meta_glasses_mobile_orb_bridge_interface.json` describes the phone as the edge bridge between glasses and services:

- `register_edge_capabilities`
- `publish_glasses_event`
- `bind_service`
- `invoke_service`
- `subscribe_service_updates`
- `dispatch_glasses_response`
- `revoke_binding`

This descriptor should not render UI directly. It binds services, invokes them, and then delegates rendering to the display widget descriptor or audio/mobile fallback paths.

## Runtime Flow

### Startup

1. Mobile DAT bridge reads device and capability state.
2. Phone computes or fetches local interface CIDs:
   - mobile edge bridge descriptor
   - display widget bridge descriptor
   - diagnostics descriptor
   - selected service descriptors
3. Phone calls `register_edge_capabilities`.
4. Backend returns an `edge_session_id`, accepted interface CIDs, and policy CID.

### Glasses Input

1. DAT/Web App/captouch/Neural Band event occurs.
2. Phone normalizes it as `publish_glasses_event`.
3. ORB policy chooses whether to:
   - handle locally,
   - invoke backend,
   - invoke a bound MCP++ service,
   - update display focus/action state,
   - deny and show fallback.

### Service Invocation

1. Phone calls `bind_service` for the needed service interface CID.
2. Phone invokes `invoke_service` with:
   - operation name,
   - arguments,
   - glasses context,
   - display context,
   - parent receipt CIDs,
   - correlation ID.
3. Backend routes through MCP++ or provider adapters.
4. Service returns output refs, provenance refs, receipt CID, and optional follow-up actions.

### Response Dispatch

1. Phone calls `dispatch_glasses_response`.
2. Dispatch picks render targets:
   - DAT native display widget if available.
   - MRBD Web App preview if display Web Apps are the chosen path.
   - audio summary for voice-first fallback.
   - mobile card/notification for degraded mode.
3. Display operations use `mobile_render_display_widget`, `mobile_update_display_widget`, etc.

## Mobile Implementation Shape

Add a JS service layer above `wearablesBridge.js`:

```text
mobile/src/orb/
  metaGlassesMobileOrbBridge.js
  metaGlassesOrbDescriptors.js
  metaGlassesOrbEdgeSession.js
  metaGlassesOrbDispatch.js
```

Responsibilities:

- Load descriptor JSON artifacts.
- Compute or accept interface CIDs.
- Register phone capabilities.
- Cache `edge_session_id` and policy CID.
- Convert DAT/Web App events to `publish_glasses_event`.
- Bind remote service descriptors.
- Invoke services through backend MCP++ route.
- Convert responses to mobile local actions.
- Preserve correlation and receipt metadata.

The mobile layer should still call existing local display functions:

- `renderDisplayWidget`
- `updateDisplayWidget`
- `clearDisplayWidget`
- `focusDisplayWidget`
- `activateDisplayWidgetAction`
- `resetDisplayWidgetSession`
- `playDisplayWidgetVideo`
- `subscribeDisplayWidgetUpdates`

## Backend Implementation Shape

Add backend endpoints or internal provider functions that can process the mobile edge descriptor methods:

- `register_edge_capabilities`
- `publish_glasses_event`
- `bind_service`
- `invoke_service`
- `subscribe_service_updates`
- `dispatch_glasses_response`
- `revoke_binding`

Implementation should reuse:

- `src/handsfree/mcp/client.py` for MCP++ tool invocation.
- existing provider/capability registry code for routing.
- existing display widget action models in `src/handsfree/models.py`.
- existing metrics and policy wrappers.

The backend remains the control plane. The phone should not gain unrestricted direct access to arbitrary services.

## SwissKnife Integration Shape

Use SwissKnife in three modes.

### Descriptor Authoring

Use `mcp-idl.ts` semantics to define descriptors and compute deterministic interface CIDs. The descriptor should be the contract, not an implementation comment.

### ORB Routing

Use `mcp-orb-capability-router.ts` for:

- discover
- bind
- authorize
- invoke
- stream
- recover

Transport selection should prefer:

1. `local` for phone-native or simulator bridge operations.
2. `mcp-server` for MCP++ services.
3. `websocket` for streamed updates.
4. `http` for simple request/response fallback.

### Display Adapter

Use `meta-glasses-display-orb-adapter.ts` as the display-specific local adapter. Do not make service routing depend on display internals; service routing returns results, then display dispatch renders those results.

## Policy Rules

Initial policy should be conservative:

- Only registered descriptors can be invoked.
- Every invocation needs `correlation_id`.
- Every service invocation gets a receipt.
- Destructive actions require confirmation.
- Display writes require a trusted descriptor or explicit test mode.
- Media refs must be HTTPS or CID-backed with approved gateway/fallback behavior.
- Remote MCP++ calls must go through backend policy unless a service is explicitly whitelisted for phone-direct invocation.
- Degraded mode is normal: return structured fallback instead of throwing.

## First Vertical Slice

Build one end-to-end flow:

1. Phone registers as edge node with display, audio, and diagnostics capabilities.
2. User says or taps: "show task status".
3. Phone publishes a `captouch` or command event.
4. Backend binds a task-status service descriptor.
5. ORB invokes service operation `get_task_status`.
6. Service returns progress state and receipt.
7. Phone dispatches the result as:
   - display widget render if available,
   - Web App preview if selected,
   - audio summary/mobile card fallback otherwise.
8. Trace includes:
   - edge session ID,
   - service interface CID,
   - display interface CID,
   - ORB receipt CID,
   - policy decision,
   - display bridge result.

## Implementation Phases

### Phase 1 - Descriptor and Mapping

- Add `spec/meta_glasses_mobile_orb_bridge_interface.json`.
- Keep `spec/meta_glasses_display_widget_orb_interface.json` display-specific.
- Add tests that all descriptor operation names map to known backend/mobile actions where applicable.

### Phase 2 - Mobile Edge Session

- Add JS edge session manager.
- Register DAT/Web App capabilities with backend.
- Persist active edge session and policy CID.
- Surface edge session state in diagnostics.

### Phase 3 - Event Ingestion

- Normalize DAT session/device/display events.
- Normalize captouch/Neural Band/Web App key events.
- Convert local actions into `publish_glasses_event`.
- Add event CID and receipt handling.

### Phase 4 - Service Binding and Invocation

- Add backend route/provider for `bind_service`.
- Add backend route/provider for `invoke_service`.
- Route MCP++ calls through existing MCP client/config.
- Return normalized service result envelopes.

### Phase 5 - Response Dispatch

- Convert service results into display widget actions.
- Reuse existing mobile local action executor.
- Preserve `interface_cid`, `descriptor_cid`, `orb_receipt_cid`, `policy_decision`, `correlation_id`, and fallback metadata.

### Phase 6 - Streaming and Recovery

- Add `subscribe_service_updates`.
- Map stream events to display widget `subscribe_updates` and `update_widget`.
- Add stale binding recovery and reconnect behavior.

### Phase 7 - Hardware-Free Harness

- Simulate glasses event.
- Register edge.
- Bind service.
- Invoke MCP++ mock.
- Dispatch response.
- Execute mocked display bridge action.
- Assert receipts and diagnostics update.

## Acceptance Criteria

- The phone bridge can be described by interface descriptors, not hardcoded one-off RPC assumptions.
- Mobile can register as an ORB edge node without paired glasses.
- A glasses event can route through ORB to a mocked service and back to a display/audio/mobile fallback.
- Every hop has a correlation ID and receipt/provenance reference.
- Native DAT unavailable states still produce a structured fallback.
- Remote service invocation is policy checked by the backend.

## Open Questions

- Should the first phone-edge transport to backend be normal HTTPS, WebSocket, or MCP server transport?
- Which remote service should be the first real service: GitHub, task status, IPFS dataset search, or model inference?
- Should phone-direct MCP++ invocation ever be allowed, or should all remote service calls pass through backend policy?
- How much of SwissKnife should be bundled into mobile versus used to generate static descriptors and mappings at build time?
