# MGW-363 Meta Glasses I/O Capability Research

Date: 2026-06-23
Last refreshed: 2026-06-24
Task: MGW-363

This note records the current official Meta glasses capability surface before
MGW expands Swissknife hardware assumptions. It distinguishes native Device
Access Toolkit (DAT) phone-app capabilities from display Web Apps capabilities,
and treats Bluetooth, Wi-Fi, IPFS, libp2p, and MCP++ as app-level bridge
concerns unless Meta documents lower-level transport hooks.

## Official Sources Checked

- Meta display developer announcement, 2026-05-14:
  https://developers.meta.com/blog/build-for-display-glasses/
- Meta Wearables developer FAQ:
  https://developers.meta.com/wearables/faq/
- Meta Wearables DAT Android repository and samples,
  `meta-wearables-dat-android` 0.7.0 README and `samples/CameraAccess`,
  `samples/DisplayAccess`:
  https://github.com/facebook/meta-wearables-dat-android
  Local planning checkout: `/home/barberb/lift_coding/external/meta-wearables-dat-android`,
  commit `25f3a6d4479b7a4a72f877977b865a11af990d04`.
- Meta Wearables DAT iOS repository and samples,
  `meta-wearables-dat-ios` 0.7.0 README and `samples/CameraAccess`,
  `samples/DisplayAccess`:
  https://github.com/facebook/meta-wearables-dat-ios
  Local planning checkout: `/home/barberb/lift_coding/external/meta-wearables-dat-ios`,
  commit `a739e94181221e7f321304273bcda2272821b163`.
- Meta Wearables Web Apps AI toolkit and references:
  https://github.com/facebookincubator/meta-wearables-webapp
  Checked 2026-06-24 at commit `de9ebda5012abc58b98176ebf12e15a04a02c8dc`.
- Android and iOS DAT v0.7 display release announcements:
  https://github.com/facebook/meta-wearables-dat-android/discussions/95
  and https://github.com/facebook/meta-wearables-dat-ios/discussions/178.
- Wearables Developer Center pages checked but effectively login-gated from
  this environment: DAT build overview, iOS integration, Android integration,
  display overview, Mock Device Kit, Web Apps, known issues, and
  `llms.txt?full=true`.

## Capability Matrix

| Surface | Native DAT phone apps | Display Web Apps | MGW assumption |
| --- | --- | --- | --- |
| camera photo capture | Supported through DAT camera APIs in Android and iOS `CameraAccess`. Samples request camera permission, start a device session/stream, and capture a photo while streaming. Mock Device Kit can provide a captured image fixture. | Not documented as a Web Apps capability in the FAQ or Web Apps toolkit. | Model as native DAT capture with permission state, visible capture/recording state, active-stream lifecycle, content-addressed output reference, and unsupported Web Apps fallback. |
| camera video capture/streaming | Supported through DAT camera streaming on Android and iOS. The public README describes video streaming and photo capture; samples render live frames from `Stream.videoStream`/equivalent stream flows. | Not documented as direct Web Apps camera access. A public feature request asks for Web Apps live camera capture, which reinforces that it is not an established Web Apps surface. | Model as native DAT video stream or recorded payload reference, not raw WebRTC/browser camera by default. |
| microphone input | Meta FAQ says DAT includes microphone/audio, but supported devices initially access microphone and speakers through iOS or Android Bluetooth profiles. No checked public DAT sample exposes raw microphone frames. | Not listed for Web Apps at launch, and the Web Apps toolkit does not define microphone capture APIs. | Model as phone OS Bluetooth profile route state plus policy-approved capture/transcription envelopes; do not assume raw DAT microphone packets unless future authenticated docs expose them. |
| speaker/headphone output | Meta FAQ says speaker access is through iOS or Android Bluetooth profiles. Existing HandsFree audio docs already route playback through platform audio. | Browser media playback may exist as standard web behavior, but official Web Apps capability lists do not define speaker/headphone route controls. | Model as Bluetooth audio route diagnostics, playback intents, fallback, and receipts; do not assume raw speaker transport or forced route control. |
| display output | DAT 0.7 adds display capability for Meta Ray-Ban Display. Android uses `mwdat-display`; iOS uses `MWDATDisplay`. `DisplayAccess` sends text, images, buttons, lists, and video players. | Web Apps render standalone HTML/CSS/JavaScript directly on Meta Ray-Ban Display from a public HTTPS URL added through the Meta AI app in Developer Mode. | Support both paths separately: native DAT display bridge and Web Apps renderer/preview, each with lifecycle receipts and fallback. |
| display lifecycle | Native samples require registration, display-capable connected device selection, `DeviceSession.start()`, `addDisplay()`, display start/state observation, send, stop/remove display, and session stop. Android treats `DisplayState.STARTED` as readiness; iOS observes `.started`. Each send replaces the active root display content. | Web Apps are browser-testable, hosted at public HTTPS URLs, then added through Meta AI app Developer Mode. Browser testing simulates D-pad and sensors; on-device testing requires Meta Ray-Ban Display paired with Meta AI app. | Mocks must expose registration, device selection, session starting/started/stopped, display attaching/started/stopped, send success/failure, update-required, unavailable, and stale-session states. |
| Meta Neural Band | Not exposed in DAT samples as raw Meta Neural Band, raw EMG, or mid-level gesture telemetry. The display announcement describes gesture control via Meta Neural Band for display glasses. | FAQ says Web Apps can access input from Meta Neural Band. The Web Apps toolkit models EMG wrist-band input as D-pad/Arrow key navigation and Enter/tap activation. | Treat as normalized focus, direction, activation, and app intent events. Do not assume raw EMG, tap duration, swipe length, or continuous gesture streams. |
| captouch | Mock Device Kit sample UI contains captouch tap/tap-and-hold simulation for displayless glasses, but public DAT display samples do not establish a native production captouch event API. | FAQ says Web Apps can access captouch. The Web Apps toolkit groups captouch with D-pad and Enter input. | Treat captouch as normalized input events when surfaced by Web Apps or mocks; keep native DAT production captouch support unknown. |
| motion/orientation | Not established as a native DAT app surface in checked public samples. | FAQ and Web Apps toolkit document motion/orientation through standard web `devicemotion` and `deviceorientation`/sensor-style APIs. | Model as Web Apps sensor events with start/stop, timestamp, source path, and deterministic mocks; native DAT support remains unsupported/unknown. |
| phone GPS | Not established as a glasses-specific native DAT surface beyond normal phone-app capabilities. | FAQ and Web Apps toolkit document phone GPS via `navigator.geolocation`; toolkit notes the location comes from the paired companion phone and the glasses have no GPS hardware. | Model GPS as companion-phone context with accuracy, permission/source, timestamp, stale-state, and privacy metadata. |
| local storage | Native phone apps have platform storage, but no glasses-specific DAT local-storage surface was identified. | Web Apps toolkit documents standard Web Storage (`localStorage` and `sessionStorage`) with no SDK. | Model Web Apps local state separately from backend/IPFS state; do not treat `localStorage` as durable control-plane storage. |
| Bluetooth | Android and iOS samples require Bluetooth permissions/background modes for DAT connection; FAQ says audio uses platform Bluetooth profiles. | Web Apps do not expose raw Bluetooth hooks in checked sources. | Treat Bluetooth as phone/glasses connection and audio-route metadata, not as an IPFS/libp2p transport by itself. |
| Wi-Fi | iOS sample plist strings say the phone can find/connect to glasses over Wi-Fi; Web Apps need network connectivity and a public HTTPS URL. | Web Apps require public HTTPS hosting and may depend on phone/glasses connectivity. | Treat Wi-Fi as connectivity/availability metadata, not as direct packet access. |
| Mock Device Kit | FAQ says Mock Device Kit can test without hardware, pair simulated devices, change device state, simulate permissions, and simulate media streaming. The same FAQ says it currently does not support display glasses. Android/iOS `CameraAccess` samples use mock camera feed/photo fixtures, and sample UI includes captouch simulation for displayless mock glasses. | Web Apps are browser-testable; no Mock Device Kit display-glasses support found. | Keep repo-owned mocks for native display lifecycle, Web Apps inputs, audio routes, motion/GPS, unsupported states, and bridge envelopes. Reuse Mock Device Kit only for DAT camera/session-like flows. |

## Release Channel And Package Constraints

- All checked DAT and display surfaces are developer preview. Public
  distribution is not open; the FAQ says developer preview is for building,
  prototyping, and testing, while DAT projects and release channels live in
  Wearables Developer Center.
- Meta's display announcement and the Android/iOS v0.7 discussions say display
  availability began rolling out on 2026-05-14 over the following weeks. Future
  work must re-check SDK version, firmware, Meta AI app, country/market,
  organization, and release-channel state before native implementation.
- Android DAT 0.7.0 uses GitHub Packages and requires a GitHub token with
  `read:packages` for Maven dependency resolution. README examples list
  `mwdat-core`, `mwdat-camera`, and `mwdat-mockdevice`; `DisplayAccess` also
  depends on `mwdat-display`. Default CI must keep Meta packages optional.
- iOS DAT 0.7.0 installs through Swift Package Manager from the public repo.
  `DisplayAccess` requires `MWDAT` plist metadata, app link URL scheme,
  `MetaAppID`, `ClientToken`, `TeamID`, and `DAMEnabled=true`.
- Android `DisplayAccess` requires manifest metadata for
  `com.meta.wearable.mwdat.APPLICATION_ID`,
  `com.meta.wearable.mwdat.CLIENT_TOKEN`, and
  `com.meta.wearable.mwdat.DAM_ENABLED=true`, plus Bluetooth and Internet
  permissions.
- Native display and camera sessions can fail because glasses firmware or the
  DAT app on the glasses needs an update. MGW receipts need explicit
  `dat_app_update_required`, `firmware_update_required`, and
  `package_or_release_channel_unavailable` states.
- Web Apps require a publicly available HTTPS URL for on-device loading. Local
  browser tests are valid for layout, D-pad/Arrow/Enter input, geolocation, and
  sensor simulation, but not proof of production device availability.

## Unsupported Or Unknown Surfaces

- No official source checked here exposes raw Meta Neural Band EMG data, tap
  duration, swipe length, arbitrary low-level gesture telemetry, or camera zoom
  gestures as a native DAT API.
- No official source checked here exposes raw Bluetooth or Wi-Fi sockets to DAT
  or Web Apps for custom protocol traffic.
- No official source checked here exposes direct Web Apps camera capture,
  microphone capture, notifications, offline mode, text input, back navigation,
  mouse/touch input, continuous cursor input, or explicit speaker/headphone route
  control.
- No official source checked here shows Mock Device Kit support for Meta
  Ray-Ban Display native display lifecycle.
- Native DAT production captouch, motion/orientation, and phone GPS APIs remain
  unknown from the public samples checked here; Web Apps are the documented path
  for those inputs.
- Wearables Developer Center pages remain partially inaccessible without
  authenticated access from this environment, so implementation tasks must
  re-check authenticated docs before changing native package assumptions.

## Bridge Envelope Implications

- Camera photo/video payloads should cross the Swissknife/MCP++ control plane as
  content-addressed references with capture metadata, permission state,
  user-visible capture/recording state, device/session IDs, firmware/app
  compatibility state, and retention policy. Do not inline large media in
  control events.
- Microphone input and speaker/headphone output should cross as route decisions,
  transcript/audio artifact references, playback intents, Bluetooth profile
  diagnostics, fallback reasons, and receipts. Bluetooth profile routing stays an
  OS/platform route, not a raw transport contract.
- Display output must include path identity (`dat-native`, `display-webapp`,
  `simulator`, `mobile-card`, `audio-summary`), lifecycle state, capability
  readiness, display package/linkage state, release-channel state, and fallback
  reason.
- Meta Neural Band, captouch, motion/orientation, and phone GPS should become
  normalized event envelopes with app binding IDs, timestamps, sequence numbers,
  source path, policy decision, replay protection, and optional privacy
  redaction.
- Bluetooth and Wi-Fi metadata can inform route quality, latency, and fallback
  decisions, but IPFS/libp2p/MCP++ compatibility is provided by the application
  bridge envelope: CIDs, peer IDs, session IDs, policy receipts, route receipts,
  backpressure, acknowledgements, and retry/degradation state.
- Hardware-free tests must cover ready, denied, unavailable, degraded,
  disconnect, update-required, stale route, unsupported capability, and release
  channel/package unavailable outcomes for every surface before native DAT
  assumptions land.

## Follow-Up Questions

- After authenticated Developer Center access, what exact Web Apps event shapes
  are exposed for Meta Neural Band and captouch beyond Arrow/Enter keyboard
  mapping?
- Which SDK, firmware, Meta AI app version, country, organization, and
  release-channel state are required for native DAT display in the target test
  environment?
- Can the current Mock Device Kit simulate any reusable device/session failure
  states beyond camera streaming, photo capture, permission, and displayless
  captouch flows?
- What retention policy should control long-lived content-addressed
  camera/audio artifacts: local IPFS node, remote pinning service, app sandbox
  cache, backend object store, or policy-dependent deletion?
