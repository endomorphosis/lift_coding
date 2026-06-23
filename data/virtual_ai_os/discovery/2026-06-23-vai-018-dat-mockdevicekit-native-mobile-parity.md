# VAI-018 DAT MockDeviceKit Native Mobile Parity

Date: 2026-06-23
Task: VAI-018
Track: mobile

## Scope

VAI-018 compares the repo's native mobile simulation behavior with the DAT
MockDeviceKit assumptions recorded in the Meta Ray-Ban simulator plan. The goal
is to identify pre-hardware gaps that would affect command capture, display
updates, networking, or device-pairing state before a physical iPhone DAT run.

## Reviewed inputs

- Simulator plan:
  `implementation_plan/docs/20-meta-rayban-display-interface-simulator.md`
- VAI-017 readiness handoff:
  `data/virtual_ai_os/discovery/2026-06-23-vai-017-simulator-artifacts-mobile-orb-webapp-readiness.md`
- iPhone DAT handoff packet:
  `data/virtual_ai_os/discovery/2026-06-12-vai-023-iphone-native-dat-handoff.md`
- Browser/Web App simulator:
  `dev/meta-rayban-display-simulator/`
- Web App readiness metadata:
  `dev/meta-rayban-display-simulator/webapp/readiness.json`
- Mobile DAT bridge wrapper:
  `mobile/src/native/wearablesBridge.js`
- iOS DAT native module:
  `mobile/modules/expo-meta-wearables-dat/ios/ExpoMetaWearablesDatModule.swift`
- Android DAT native module:
  `mobile/modules/expo-meta-wearables-dat/android/src/main/java/expo/modules/metawearablesdat/ExpoMetaWearablesDatModule.kt`

## Parity comparison

| Area | Native mobile simulation behavior | DAT MockDeviceKit assumption | Parity decision |
| --- | --- | --- | --- |
| Command capture | The browser session exports `handsfree.virtual-desktop-session`, audio command endpoints, queued command envelopes, keyboard focus, and action activation. The Web App can publish ORB receipts for register, event, bind, invoke, and dispatch. | MockDeviceKit can simulate device registration, permissions, paired mock devices, camera/video/photo paths, device state, and some captouch gestures, but it is not the command queue or ORB receipt source. | Partial parity. Use the browser/Web App/mobile ORB proof bundle as the command-capture source, then compare DAT runs by `correlation_id`, `request_id`, action ID, and receipt CID. MockDeviceKit alone is insufficient for command capture acceptance. |
| Display updates | The simulator and Web App render the canonical 600x600 manifest, D-pad focus order, fallback render path, and structured bridge fields. The iOS and Android bridges expose `render_display_widget`, `update_display_widget`, `clear_display_widget`, `focus_display_widget`, `activate_display_widget_action`, `reset_display_widget_session`, `play_display_widget_video`, and `subscribe_display_widget_updates`. | DAT Display sends complete views to one display capability per device session. Public evidence reviewed for the plan did not confirm that MockDeviceKit renders native DAT Display UI output. | Gap. Treat MockDeviceKit as device/session/media simulation, not visual display proof. Native mobile simulation must keep using the browser/Web App renderer for visual parity and only use MockDeviceKit to exercise session/device blockers before physical display validation. |
| Networking | Web App readiness requires a public HTTPS deployment URL, unauthenticated static files, and ORB calls to the mobile backend. Native DAT display video requires HTTPS MP4 media and the bridge records fallback paths when native display is unavailable. | MockDeviceKit can help simulate phone-mediated DAT configuration and media flows, but it does not prove public HTTPS Web App loading or backend ORB reachability from the phone/glasses path. | Partial parity. Keep Web App HTTPS loading and mobile ORB receipt checks as separate gates. DAT-native tests must also preserve backend URL/auth mode, HTTPS media URLs, and fallback render targets in the handoff evidence. |
| Device-pairing state | The browser simulator intentionally starts unpaired with `requires_paired_hardware: false` and fallback to `mobile-card`. The iOS bridge records selected target state, session state, adapter state, target timestamps, and `displayConnectionState`, but reference-only scans return no known devices until a target is selected. | MockDeviceKit is expected to simulate paired mock devices and device power/don/unfold state, so it can cover more pairing lifecycle states than the browser simulator. | Gap that affects rollout. Before native DAT promotion, MockDeviceKit or physical evidence must cover selected target, target connected, target ready, disconnected, update required, and no-target cases; browser-only evidence cannot close pairing parity. |

## Required native mobile simulation gate

A native mobile simulation run can advance to physical DAT validation only when
the evidence bundle records:

- `widget_id`, `widget_cid`, `descriptor_cid` or `interface_cid`,
  `correlation_id`, `request_id`, focus order, action ID, and parent receipt
  CIDs from the VAI-017 simulator/Web App/mobile ORB bundle.
- DAT bridge diagnostics for `sdkLinked`, `displaySdkLinked`,
  `displayDamEnabled`, `sdkVersionTarget`, `displayReady`,
  `targetConnectionState`, `displayConnectionState`,
  `displayLifecycleStages`, and selected target metadata.
- Display action results for render, update, focus, activate, clear, reset,
  video playback, and update subscription, including fallback `reason`,
  `requiredAction`, and `renderPath`.
- Networking proof for the hosted Web App HTTPS URL, backend ORB endpoint
  reachability, and HTTPS-only native display media.
- Device-pairing proof from MockDeviceKit or physical hardware for no target,
  selected target, connected target, ready target, update-required target, and
  disconnected/reconnect states.

## Gaps to carry forward

- Command capture remains browser/Web App/mobile ORB driven. MockDeviceKit does
  not replace the command-session export or ORB receipt lineage.
- Native DAT visual display parity is not closed by MockDeviceKit. Whole-view
  native DAT Display output still needs SDK-linked simulator/device evidence or
  physical glasses evidence.
- Networking is split between Web App HTTPS loading, backend ORB reachability,
  and native DAT HTTPS media validation. A single MockDeviceKit run cannot prove
  all three.
- Pairing state is the main MockDeviceKit value for native mobile simulation,
  but the repo's iOS reference-only bridge currently records selected targets
  without discovering real or mock nearby devices.

## Acceptance mapping

VAI-018 acceptance is satisfied for planning/discovery because the native mobile
simulator behavior and DAT MockDeviceKit assumptions have been compared across
command capture, display updates, networking, and device-pairing state. The
recorded decision is to keep VAI-017 simulator/Web App/mobile ORB artifacts as
the command and display parity source, use DAT MockDeviceKit for device/session
state simulation, and hold native DAT rollout until SDK-linked or physical
evidence closes the remaining display and pairing gaps.

## Validation

Backlog validation command:

```bash
rg -n "VAI-018|MockDeviceKit|native mobile simulation|DAT" implementation_plan/docs/19-virtual-ai-os-submodule-integration.md data/virtual_ai_os/discovery
```
