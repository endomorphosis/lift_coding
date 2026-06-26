# Meta Glasses Expanded I/O Physical Validation Checklist

Use this checklist for physical Android and iOS validation before enabling
expanded Meta glasses I/O outside hardware-free mocks. Native DAT camera,
display, and Bluetooth audio route features are optional by default and remain
disabled unless every gate in this document passes with recorded evidence.

## Scope

- DAT version target: `0.7.0` or newer
- Platforms: Android DAT v0.7 physical build and iOS DAT v0.7 parity build
- Device class: display-capable Meta glasses paired to the test phone
- Native routes: DAT camera photo/video, DAT display lifecycle, and phone OS
  Bluetooth microphone, speaker, and headphone route diagnostics
- Web routes: hosted Display Web App over publicly reachable HTTPS
- Input routes: Meta Neural Band, captouch, motion/orientation, and phone GPS
- Fallback routes: mobile-card, display-webapp, bridge-only mocks, and no-audio
  fallback where policy requires it

## A) Native DAT Feature Gates

Native DAT camera, display, and Bluetooth audio route features are not required
for default CI, local development, or hardware-free Playwright runs. Keep native
feature flags off unless all gates below pass for the exact app build, account,
phone, glasses, release channel, and environment under test.

| Gate | Required evidence | Keep optional or disabled when missing |
| --- | --- | --- |
| Package credentials | Meta Wearables DAT package access, dependency resolution, and SDK linkage are available for the build host. | Keep Android `-PmetaWearablesDatAndroidEnabled=false`; keep iOS DAT SDK-unlinked fallback. |
| Developer Mode or release channel | Developer Mode is enabled for development runs, or the app is installed from an approved DAT release channel. | Report `package_or_release_channel_unavailable` or `dat_sdk_unlinked`; use bridge-only/mobile fallback. |
| App registration | App ID, bundle ID/package name, DAM/app-model metadata, and Web App registration match the test account. | Report `dam_disabled` or registration mismatch; do not start native capture or display. |
| Firmware and app update state | Glasses firmware, Meta AI app, and glasses DAT app show no pending update prompts. | Return `firmware_update_required` or `dat_app_update_required` with an operator-visible action. |
| Paired hardware | The phone is paired to the intended display-capable glasses and the target is selected. | Return `target_required`, `display_capability_missing`, or `route_unavailable`. |
| Capability checks | Runtime diagnostics report camera, display, and Bluetooth route capabilities before use. | Return `unsupported`, `dat_native_display_unavailable`, or route-specific fallback metadata. |

Feature gate decision:
- [ ] Native DAT camera stays off unless package credentials, Developer Mode or
      release channel, app registration, firmware/app update state, paired
      hardware, and camera capability checks all pass.
- [ ] Native DAT display stays off unless package credentials, Developer Mode or
      release channel, app registration, firmware/app update state, paired
      display-capable hardware, DAM metadata, DAT v0.7+, and display capability
      checks all pass.
- [ ] Bluetooth microphone, speaker, and headphone routes stay diagnostic and
      optional unless phone OS route permissions, paired hardware, Bluetooth
      profile state, and route capability checks all pass.
- [ ] Missing or denied gates produce structured fallback evidence before any
      camera frame, microphone packet, playback, display render, Neural Band,
      captouch, motion, or GPS data leaves the adapter.

Evidence:
- [ ] Build flags, release channel, package credential state, and SDK target
- [ ] Developer Mode or approved release-channel screenshot
- [ ] App registration and DAM/Web App metadata
- [ ] Firmware, Meta AI app, and glasses DAT app versions
- [ ] Paired hardware target and display-capable device selection
- [ ] Diagnostics capability snapshot and fallback reason for every disabled gate

## B) Android DAT v0.7 Physical Run

- [ ] Install the Android build compiled with DAT v0.7 metadata.
- [ ] Verify the default bridge-only build remains valid when package
      credentials are absent.
- [ ] Enable the native DAT Android feature flag only for the credentialed
      physical test build.
- [ ] Confirm the diagnostics panel reports platform `android`, SDK target
      `0.7.0` or newer, camera capability, display capability, Bluetooth adapter
      state, paired glasses, and selected display target.
- [ ] Confirm non-display devices show explicit fallback status and do not
      silently select a native display path.

Evidence:
- [ ] Android build variant and DAT SDK target
- [ ] Diagnostics screenshot before first native action
- [ ] Screenshot or log showing display-capable device selection
- [ ] Fallback screenshot for a non-display or unselected target

## C) iOS DAT v0.7 Physical Run

- [ ] Install the iOS build with DAT v0.7 metadata for the test account.
- [ ] Confirm SDK-unlinked fallback behavior before testing any SDK-linked build.
- [ ] Enable native iOS DAT only for the credentialed physical test build.
- [ ] Confirm diagnostics report platform `ios`, `MWDATCore` linkage,
      `MWDATDisplay` linkage when display is tested, SDK target `0.7.0` or
      newer, DAM metadata, paired glasses, and selected display target.
- [ ] Confirm iOS returns `dat_sdk_unlinked`, `display_sdk_unlinked`,
      `dam_disabled`, `sdk_version_unsupported`, or `target_required` rather
      than silently succeeding when a gate is missing.

Evidence:
- [ ] iOS build channel and DAT SDK target
- [ ] SDK-linked or SDK-unlinked diagnostic payload
- [ ] DisplayAccess lifecycle logs when display succeeds
- [ ] Fallback payload when native DAT remains unavailable

## D) Camera Stream And Photo Capture

- [ ] Request foreground camera consent on Android and iOS before capture.
- [ ] Capture one still photo through the native DAT camera path when the camera
      feature gate passes.
- [ ] Start and stop one short video stream or video capture path when supported
      by the physical build.
- [ ] Record content-addressed photo/video references only after privacy policy
      allows persistence.
- [ ] Deny camera permission once and verify no raw frame or content CID is
      emitted.
- [ ] Remove camera capability or use an unsupported device once and verify
      structured fallback evidence.

Evidence:
- [ ] Permission prompt or granted/denied state
- [ ] Redacted content CID or receipt for allowed photo capture
- [ ] Start/stop stream result or explicit unsupported response
- [ ] Denied-permission and unsupported-device fallback payloads

## E) Bluetooth Route Diagnostics

- [ ] Pair glasses and confirm Bluetooth state at the phone OS level.
- [ ] Validate microphone input route readiness through the expected Bluetooth
      profile, such as HFP where applicable.
- [ ] Validate speaker output route readiness through the expected Bluetooth
      profile, such as A2DP where applicable.
- [ ] Validate headphone output route readiness where the device exposes a
      separate route.
- [ ] Interrupt or disconnect Bluetooth once and confirm `route_lost`,
      `route_unavailable`, or `degraded` fallback evidence.
- [ ] Confirm audio route diagnostics do not claim raw Bluetooth packets are
      IPFS, libp2p, or MCP++ transports.

Evidence:
- [ ] Android and iOS Bluetooth route screenshots or logs
- [ ] Microphone, speaker, and headphone route payloads
- [ ] Disconnect/interruption fallback payload
- [ ] Privacy redaction and no-raw-audio note

## F) Display And Web Apps HTTPS Deployment

- [ ] Select display-capable glasses before native DAT display actions.
- [ ] Render a native DAT display test card when the display feature gate passes.
- [ ] Render a compiled widget manifest with text, status, progress, image
      fallback, video fallback, focus, and action activation evidence.
- [ ] Confirm DisplayAccess lifecycle stages or equivalent diagnostics:
      selected target, session started, display attached, display started, and
      content sent.
- [ ] Deploy the Display Web App over publicly reachable HTTPS.
- [ ] Register the Web App in the Meta AI app and launch it from
      `App Connections > Web apps`.
- [ ] Confirm the HTTPS Web App fallback remains usable when native DAT display
      is disabled, unlinked, or blocked by firmware/app update state.

Evidence:
- [ ] Native DAT display result payload
- [ ] Display Web App HTTPS URL and readiness-linter result
- [ ] Meta AI app registration screenshot
- [ ] Native-disabled Web App fallback screenshot

## G) Neural Band, Captouch, Motion, And GPS

- [ ] Validate Meta Neural Band input in the Display Web App or approved input
      path, including at least one select/activate gesture.
- [ ] Validate captouch Arrow and Enter-style navigation where supported.
- [ ] Validate motion/orientation events with a visible app state change or
      diagnostic payload.
- [ ] Validate phone GPS context with explicit permission state and redacted
      location evidence.
- [ ] Deny input, motion, or location permission once and verify policy-denied
      fallback evidence.

Evidence:
- [ ] Neural Band input event payload or screen recording
- [ ] Captouch navigation payload or screen recording
- [ ] Motion/orientation diagnostic payload
- [ ] Phone GPS permission and redacted location payload
- [ ] Denied-permission fallback receipt

## H) Fallback Evidence And Privacy Review

- [ ] Exercise missing package credentials or release channel and verify native
      DAT stays optional.
- [ ] Exercise Developer Mode disabled or unapproved release-channel state.
- [ ] Exercise app registration mismatch or DAM disabled state.
- [ ] Exercise firmware update required and app update required states.
- [ ] Exercise unpaired hardware, wrong hardware, non-display hardware, and
      missing capability states.
- [ ] Confirm every fallback includes route, reason, required action when
      available, policy decision, privacy redaction metadata, and receipt or
      correlation ID.
- [ ] Confirm raw camera frames, raw microphone audio, precise GPS, face
      embeddings, and biometric input are absent from logs unless explicitly
      approved by the privacy review.
- [ ] Complete privacy review for persistence, redaction, retention, operator
      visibility, and rollback artifacts.

Evidence:
- [ ] Fallback matrix with one row per blocked gate
- [ ] Privacy-review signoff or tracked exception
- [ ] Redacted logs attached to the release ticket

## I) Rollback

- [ ] Disable native DAT Android with `metaWearablesDatAndroidEnabled=false` and
      verify camera/display native paths no longer activate.
- [ ] Disable native DAT iOS by using the SDK-unlinked fallback build or turning
      the native DAT feature flag off.
- [ ] Keep Web App fallback enabled and verify the HTTPS Display Web App still
      opens.
- [ ] Move the test cohort back to the last bridge-only, mobile-card, or
      display-webapp release channel.
- [ ] Repeat one camera, one display, one Bluetooth route, one Neural Band or
      captouch input, one motion/GPS, and one fallback check after rollback.
- [ ] Record rollback flags, app versions, release channel, and operator-visible
      evidence.

Result:
- [ ] PASS for staged physical validation
- [ ] FAIL and keep native DAT expanded I/O optional or disabled
