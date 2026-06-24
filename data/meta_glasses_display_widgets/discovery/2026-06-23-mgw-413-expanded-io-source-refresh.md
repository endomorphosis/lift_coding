# MGW-413 Expanded Meta Glasses I/O Source Refresh

Date: 2026-06-23
Last refreshed: 2026-06-24
Task: MGW-413
Depends on: MGW-363

This refresh updates the official-source matrix before MGW changes native
hardware assumptions. It keeps native Device Access Toolkit (DAT) phone-app
capabilities separate from display Web Apps capabilities, and keeps
IPFS/libp2p/MCP++ compatibility at the app-level bridge envelope rather than
raw Bluetooth or Wi-Fi packet layers.

## Sources Checked

- Meta Wearables FAQ: https://developers.meta.com/wearables/faq/
- Meta display developer announcement, 2026-05-14:
  https://developers.meta.com/blog/build-for-display-glasses/
- Meta Wearables DAT Android repository, README, 0.7.0 changelog,
  `samples/DisplayAccess`, and `samples/CameraAccess`:
  https://github.com/facebook/meta-wearables-dat-android
  Local planning checkout: `/home/barberb/lift_coding/external/meta-wearables-dat-android`,
  commit `25f3a6d4479b7a4a72f877977b865a11af990d04`.
- Meta Wearables DAT iOS repository, README, 0.7.0 changelog,
  `samples/DisplayAccess`, and `samples/CameraAccess`:
  https://github.com/facebook/meta-wearables-dat-ios
  Local planning checkout: `/home/barberb/lift_coding/external/meta-wearables-dat-ios`,
  commit `a739e94181221e7f321304273bcda2272821b163`.
- Android and iOS DAT v0.7 display release discussions:
  https://github.com/facebook/meta-wearables-dat-android/discussions/95
  and https://github.com/facebook/meta-wearables-dat-ios/discussions/178.
- Meta Wearables Web App AI Toolkit and starter behavior:
  https://github.com/facebookincubator/meta-wearables-webapp
- Wearables Developer Center pages linked from the public FAQ and repositories
  remain release-channel/authentication dependent from this environment, so
  native implementation tasks must re-check authenticated docs before changing
  package, entitlement, firmware, or country/market assumptions.

## 2026-06-24 Verification Delta

- Public Meta sources still present DAT and Web Apps as separate development
  products. DAT is the native iOS/Android phone-app path for camera/video,
  photo capture, microphone/audio route integration, and display-capable device
  sessions. Web Apps are the display-glasses HTML/CSS/JavaScript path for
  on-display web rendering and documented launch inputs.
- The Android and iOS DAT 0.7 changelogs continue to anchor native display
  assumptions: display is a DAM-gated capability, content submission replaces
  the active display view, and display readiness must be observed through
  typed state/error surfaces. CameraAccess remains the native sample family
  for stream/photo behavior and Mock Device Kit camera/session simulation.
- Web Apps starter behavior remains browser-first: Arrow keys and Enter are
  the development stand-in for Meta Neural Band and captouch D-pad activation,
  Chrome DevTools sensors cover geolocation/orientation testing, and a public
  HTTPS URL is required before on-device loading.
- Mock Device Kit evidence should not be stretched into a full native display
  simulator claim. Keep it scoped to documented DAT-style hardware-free flows,
  including camera/session/permission/media behavior and v0.7 displayless
  captouch simulation; keep MGW-owned mocks for display lifecycle, Web Apps
  inputs, Bluetooth audio route state, unsupported states, and bridge
  envelopes.
- No checked official source added raw Bluetooth or Wi-Fi packet APIs for DAT
  or Web Apps. IPFS/libp2p/MCP++ compatibility therefore remains an MGW
  application envelope contract above the Meta transport/runtime surfaces.

## Official Source Matrix

| Source | DAT native phone-app evidence | Web Apps evidence | MGW-413 assumption |
| --- | --- | --- | --- |
| Meta Wearables FAQ | Defines DAT as the iOS/Android route for AI glasses sensors and hands-free mobile app experiences. It lists video streaming, photo capture, microphone/audio, and Meta Ray-Ban Display on-device display, while saying microphone and speaker access initially use iOS or Android Bluetooth profiles. It also says Mock Device Kit can test without hardware but currently does not support display glasses. | Defines Web Apps as display-glasses-only standalone HTML/CSS/JavaScript apps. At launch they can access motion/orientation, connected-phone GPS, Meta Neural Band input, captouch, and local storage, and can be tested in a standard browser before deployment by public URL through the Meta AI app. | Treat DAT and Web Apps as separate product surfaces. Model audio as Bluetooth audio route state, not raw DAT audio frames. Keep repo-owned mocks for display lifecycle and Web Apps inputs because Mock Device Kit display-glasses coverage is not documented. |
| Display developer announcement | Says display capability was added to native DAT for iOS/Android. Native display UI supports text, images, lists, buttons, and video playback, in addition to DAT camera/audio/display integration. | Introduces Web Apps for standalone display experiences using standard web tools, motion/orientation, phone GPS, Meta Neural Band input, local storage, browser preview, and URL deployment. It also says Web Apps can be shared by password-protected URLs and DAT builds by release channels with up to 100 testers during Developer Preview. | MGW should expose both `dat-native` and `display-webapp` render paths. Release-channel state is part of readiness, not a build-time guarantee. |
| Android DAT 0.7 changelog and samples | `mwdat-display` adds `Display`, `DisplayConfiguration`, `DisplayState`, `DisplayError`, `DeviceSession.addDisplay(config)`, `removeDisplay()`, `Display.sendContent { ... }`, FlexBox/Text/Icon/Image/Button primitives, and MP4 `VideoPlayer`. Each send replaces the entire display, one view is presented at a time, and vertical scrolling is the documented content direction. DAM is required for display through `com.meta.wearable.mwdat.DAM_ENABLED=true`. `DisplayAccess` requires credentials, Bluetooth/Internet permissions, a display-capable device, session start, display attach/readiness, firmware update handling, and DAT glasses app update handling. `CameraAccess` shows native stream/photo flows and Mock Device Kit camera fixtures. | Not applicable; Android DAT repo is native. | Android display and camera must remain optional behind package, credential, DAM, release-channel, firmware/app, and runtime capability gates. MGW mocks need device/session/display states, update-required states, stream/photo outputs, and `Bluetooth audio route` diagnostics separately. |
| iOS DAT 0.7 changelog and samples | `MWDATDisplay` adds `Display`, `DeviceSession.addDisplay(...)`, `display.send(_:)`, FlexBox/Text/Button/Image/Icon/VideoPlayer primitives, typed display/video state and errors, and Objective-C display bridge types. Each send submits a single root `FlexBox` or `VideoPlayer` and replaces previous content. DAM is required through Info.plist configuration. `DisplayAccess` requires Developer Mode, registration, connection, display content send, firmware update, and DAT app-on-glasses update flows. `CameraAccess` uses `MWDATMockDevice`, mock test client, registration/permission simulation, and camera stream/photo behavior. | Not applicable; iOS DAT repo is native. | iOS display and camera readiness must be represented as native DAT lifecycle states. The app-facing registry should not require Swift package linkage in default tests. |
| Web Apps starter kit | Not applicable; the starter kit is not a native DAT package. | Documents Web Apps as standard HTML/CSS/JavaScript on Meta Ray-Ban Display. Browser testing uses Arrow keys to simulate D-pad input. Sensor testing uses Chrome DevTools geolocation and orientation overrides. Deployment requires a publicly available HTTPS URL. Design constraints include 600x600 viewport, D-pad navigation only, EMG wristband gestures translated to Arrow keys, high contrast, `.focusable` elements, and dark backgrounds. Skills include sensor support for accelerometer, gyroscope, and compass. | Model Meta Neural Band and captouch as normalized Arrow/Enter/focus/activation intents unless authenticated docs expose richer event payloads. Model motion/orientation and phone GPS as Web Apps input events with browser-testable mocks. Do not treat Web Apps as the camera, microphone, speaker/headphone, raw Bluetooth, or raw Wi-Fi path. |
| Mock Device Kit limits | FAQ and DAT samples support hardware-free simulated device setup, device state, permissions, camera streaming/media, captured image fixtures, and v0.7 displayless captouch simulation. | Web Apps are browser-testable, but no Mock Device Kit display-glasses lifecycle support was confirmed. | Reuse Mock Device Kit for DAT camera/session/permission-like flows only where available. Keep MGW-owned mocks for native display lifecycle, Meta Neural Band, captouch, motion/orientation, phone GPS, Bluetooth audio route, unsupported capability, route loss/degradation, release-channel/package failure, and bridge envelopes. |
| Release-channel/package constraints | Android DAT 0.7 uses GitHub Packages and requires a token with `read:packages`; public README lists core/camera/mockdevice while DisplayAccess adds `mwdat-display`, with a note that distribution depends on the display artifact being available in the target Maven/release channel. iOS uses Swift Package Manager, `MWDATDisplay`, app credentials, DAM metadata, app registration, Developer Mode, and compatible firmware/glasses app state. DAT builds are developer-preview release-channel artifacts. | Web Apps deploy by public HTTPS URL and are added through the Meta AI app in Developer Mode; browser tests do not prove production on-device availability. | Default CI must not require Meta package credentials, physical glasses, or release-channel access. Readiness receipts must include package unavailable, release channel unavailable, Developer Mode missing, firmware update required, DAT app update required, and unsupported hardware. |
| Unsupported or unknown surfaces | No checked official source exposes raw DAT microphone frames, raw DAT speaker packets, raw Neural Band EMG, native production captouch event streams, native DAT motion/orientation APIs, native DAT glasses-specific GPS APIs, or raw Bluetooth/Wi-Fi sockets for custom protocols. | No checked official source exposes Web Apps camera capture, microphone capture, explicit speaker/headphone route control, notifications, offline mode, text input, back navigation, mouse/touch input, continuous cursor input, or raw Bluetooth/Wi-Fi sockets. | Unsupported surfaces must return structured unavailable/unsupported results. Future implementation must not infer native hardware APIs from consumer product behavior or from browser-standard capabilities that Meta's Web Apps docs do not list. |

## Capability Routing Decision

Native DAT camera/display/audio-route capabilities:

- Camera photo/video capture is a native DAT phone-app capability. Android and
  iOS `CameraAccess` samples establish stream/session/photo flows and Mock
  Device Kit camera fixtures. MGW should emit capture references, not inline
  large media in control-plane events.
- Display output is a native DAT phone-app capability only when display packages,
  DAM metadata, registration, device session, display attach, firmware/glasses
  app compatibility, and release-channel access all line up. Each native send
  replaces the active display content.
- Microphone and speaker/headphone behavior is a Bluetooth audio route
  capability through iOS/Android platform profiles. MGW should model permission,
  route readiness, degraded/lost route state, fallback, transcripts/artifact
  references, playback intents, diagnostics, and receipts rather than raw audio
  packet ownership.

Display Web Apps input capabilities:

- Meta Neural Band and captouch are documented Web Apps inputs. Current starter
  behavior maps them to D-pad style Arrow key navigation and Enter/tap
  activation, so MGW should expose normalized intent events, not raw EMG or
  low-level touch streams.
- Motion/orientation and phone GPS are documented Web Apps inputs. They should
  be modeled as timestamped Web Apps sensor/location events with permission,
  source path, stale-state, and privacy metadata.
- Web Apps local storage is browser-local state. It is not a durable
  Swissknife/IPFS control-plane store.

## Bridge Envelope Implications

- IPFS/libp2p/MCP++ compatibility lives in MGW app-level bridge envelopes:
  IPFS CIDs, libp2p peer IDs, session IDs, app binding IDs, policy decisions,
  control-plane route decisions, replay protection, backpressure, latency,
  retry/degradation state, acknowledgements, and MCP++ receipts.
- Bluetooth and Wi-Fi can appear as connection, reachability, quality, and
  audio-route metadata. They are not raw IPFS/libp2p transports unless a
  separately implemented app-level phone/Web App bridge provides content
  addressing, peer/session identity, policy checks, and receipts.
- DAT and Web Apps adapters must publish the same normalized event/envelope
  families so tests can run without paired hardware or Meta package access:
  camera refs, microphone route/transcript refs, headphones route/playback
  state, display lifecycle/action, Meta Neural Band intent, captouch intent,
  motion/orientation, phone GPS, permission state, unsupported capability, and
  transport handoff.

## Implementation Guardrails

- Keep DAT package linkage optional in default builds. Native adapters should
  fail closed to structured `dat_unavailable`, `package_unavailable`,
  `release_channel_unavailable`, `unsupported_capability`, or update-required
  receipts.
- Keep Web Apps adapters browser-testable. Playwright coverage can validate
  600x600 layout, Arrow/Enter input, mocked motion/orientation, mocked GPS,
  focus state, and control-plane receipts, but it cannot certify physical
  device availability.
- Do not merge Neural Band and captouch into native DAT assumptions. Current
  official evidence routes those inputs through Web Apps or Mock Device Kit
  simulation, not production native DAT gesture APIs.
- Re-check authenticated Wearables Developer Center docs before any task changes
  native firmware, market, SDK, entitlement, app-model, package, or release
  channel requirements.

## Downstream Gate

MGW-414 through MGW-424 should consume this matrix as a source-of-truth split:
native DAT capabilities may be requested for camera, native display, and
Bluetooth audio route readiness, while Web Apps capabilities may be requested
for Meta Neural Band, captouch, motion/orientation, phone GPS, browser-tested
D-pad input, and local storage. Anything outside those official surfaces must
be represented as `unsupported_capability`, `route_unavailable`, or an
app-level bridge envelope until a newer official source changes the boundary.
