# MGW-363 Meta Glasses I/O Capability Research

Date: 2026-06-23
Task: MGW-363

This note records the current official Meta glasses capability surface before MGW expands Swissknife hardware assumptions. It distinguishes native Device Access Toolkit (DAT) phone-app capabilities from display Web Apps capabilities, and treats Bluetooth, Wi-Fi, IPFS, libp2p, and MCP++ as app-level bridge concerns unless Meta documents lower-level transport hooks.

## Official Sources Checked

- Meta display developer announcement, 2026-05-14: https://developers.meta.com/blog/build-for-display-glasses/
- Meta Wearables developer FAQ: https://developers.meta.com/wearables/faq/
- Meta Wearables DAT Android repository and samples, `meta-wearables-dat-android` 0.7.0 README and `samples/CameraAccess`, `samples/DisplayAccess`: https://github.com/facebook/meta-wearables-dat-android
- Meta Wearables DAT iOS repository and samples, `meta-wearables-dat-ios` 0.7.0 README and `samples/CameraAccess`, `samples/DisplayAccess`: https://github.com/facebook/meta-wearables-dat-ios
- Meta Wearables Web Apps AI toolkit and references: https://github.com/facebookincubator/meta-wearables-webapp
- Meta Wearables Developer Center pages discovered but login-gated from this environment: DAT build overview, iOS integration, Android integration, display overview, Mock Device Kit, Web Apps, known issues, and `llms.txt?full=true`.

## Capability Matrix

| Surface | Native DAT phone apps | Display Web Apps | MGW assumption |
| --- | --- | --- | --- |
| camera photo capture | Supported through DAT camera stream/photo APIs in iOS and Android samples. Photo capture succeeds while the camera stream is active. | Not documented as a Web Apps capability in public FAQ/blog/Web App toolkit sources. | Model as native DAT capture with permission, active-stream lifecycle, content-addressed output reference, and unsupported Web Apps fallback. |
| camera video capture/streaming | Supported through DAT camera streaming on iOS and Android; samples show live frames and photo capture. Public release notes mention high-resolution video streaming support. | Not documented as direct Web Apps camera access. | Model as native DAT video stream or recorded payload reference, not raw WebRTC/browser camera by default. |
| microphone input | Meta FAQ says microphone/audio are available, but microphone and speakers are accessed through iOS or Android Bluetooth profiles. | Not listed for Web Apps at launch. | Model as phone OS audio route state plus policy-approved capture/transcription envelope, not raw DAT mic frames unless future docs expose them. |
| speaker/headphone output | Meta FAQ says speaker access is through iOS or Android Bluetooth profiles. | Browser audio playback may exist as standard web media behavior, but official Web Apps capability lists do not define speaker routing controls. | Model as Bluetooth audio route diagnostics and output intent receipts; do not assume raw speaker transport or forced route control. |
| display output | DAT 0.7 adds display for Meta Ray-Ban Display. iOS and Android DisplayAccess samples start a device session, attach display, wait for `DisplayState.STARTED`, then send text/images/buttons/video. | Web Apps render standalone HTML/CSS/JavaScript directly on Meta Ray-Ban Display from a public HTTPS URL. | Support both paths separately: native DAT display bridge and Web Apps renderer/preview, each with lifecycle receipts and fallback. |
| display lifecycle | Native samples require registration, a selected display-capable connected device, session start, display add/attach, display state observation, send, detach/remove display, and session stop. DAM is required for display. | Web Apps are added through Meta AI app Developer Mode and loaded by URL; browser testing can simulate D-pad and sensors. | MGW mocks must expose session, attach, started, stopped, update-required, unavailable, and stale-session states. |
| Meta Neural Band | Not exposed in DAT samples as raw Neural Band data. Meta announcement describes gesture controls via Meta Neural Band for display glasses. | FAQ and Web Apps toolkit describe Web Apps input from Meta Neural Band; toolkit maps D-pad/Enter/back style controls to keyboard events. | Treat as normalized gesture/focus/activation events. Do not assume raw EMG or mid-level sensor data. |
| captouch | MockDevice sample code contains captouch tap controls, but public DAT display samples do not establish a native app event API for production captouch. | FAQ and Web Apps toolkit describe captouch/D-pad input for Web Apps. | Treat captouch as normalized input events when surfaced by Web Apps or mocks; keep native DAT production support unknown. |
| motion/orientation | Not established as native DAT surface in checked public samples. | FAQ and Web Apps toolkit document motion/orientation through standard web DeviceMotionEvent/DeviceOrientationEvent-style APIs. | Model as Web Apps sensor events plus deterministic mocks; native DAT support remains unsupported/unknown. |
| phone GPS | Not established as native DAT surface in checked public samples beyond normal phone app capabilities. | FAQ and Web Apps toolkit document phone GPS via `navigator.geolocation`, sourced from the paired companion phone. | Model GPS as companion-phone context with accuracy, permission/source, timestamp, and stale-state metadata. |
| local storage | Native phone apps have platform storage but no glasses-specific DAT local-storage surface was identified. | Web Apps toolkit documents local storage. | Model Web Apps local state separately from backend/IPFS state; do not treat localStorage as durable control-plane storage. |
| Bluetooth | Required by Android/iOS DAT setup and used by platform audio profiles. iOS DisplayAccess also declares Bluetooth background modes. | Web Apps do not expose raw Bluetooth hooks in checked sources. | Treat Bluetooth as phone/glasses route metadata, not as an IPFS/libp2p transport by itself. |
| Wi-Fi | iOS DisplayAccess sample includes local network usage text saying the phone can find/connect to glasses over Wi-Fi; Web App toolkit notes intermittent Wi-Fi connectivity. | Web Apps require public HTTPS hosting and network connectivity. | Treat Wi-Fi as connectivity/availability metadata, not as direct packet access. |
| Mock Device Kit | DAT FAQ says Mock Device Kit can test without hardware and simulate permissions/media streaming; FAQ also says it currently does not support display glasses. Android/iOS samples include camera/mock flows. | Web Apps are browser-testable; no Mock Device Kit display-glasses support found. | Keep repo-owned mocks for display, Web Apps inputs, audio routes, motion/GPS, and bridge envelopes. Reuse Mock Device Kit only for DAT camera/session-like flows. |

## Release Channel And Package Constraints

- All checked DAT and display surfaces are developer preview. Public distribution is not open; the FAQ says Web Apps can be shared by URL and DAT builds through release channels during preview.
- Meta's display announcement says access rolled out from 2026-05-14 over the following weeks; future work must re-check version, firmware, Meta AI app, and organization availability before native implementation.
- Android DAT 0.7.0 uses GitHub Packages and requires a GitHub token with `read:packages` for Maven dependency resolution. README examples list `mwdat-core`, `mwdat-camera`, and `mwdat-mockdevice`; display work also uses `mwdat-display` in the public DisplayAccess sample/agent docs, so default CI must keep Meta packages optional.
- iOS DAT 0.7.0 installs through Swift Package Manager from the public repo. DisplayAccess requires `MWDAT` plist metadata, app link URL scheme, `MetaAppID`, `ClientToken`, `TeamID`, and `DAMEnabled=true`.
- Android DisplayAccess requires manifest metadata for `com.meta.wearable.mwdat.APPLICATION_ID`, `CLIENT_TOKEN`, and `DAM_ENABLED=true`, plus Bluetooth and Internet permissions.
- Native display sessions can fail because the DAT app on the glasses or glasses firmware needs an update. MGW receipts need explicit `dat_app_update_required`, `firmware_update_required`, and `package_or_release_channel_unavailable` states.

## Unsupported Or Unknown Surfaces

- No official source checked here exposes raw Neural Band EMG data, tap duration, swipe length, or arbitrary low-level gesture telemetry.
- No official source checked here exposes raw Bluetooth or Wi-Fi sockets to DAT or Web Apps for custom protocol traffic.
- No official source checked here exposes direct Web Apps camera capture, microphone capture, or explicit speaker/headphone route control.
- No official source checked here shows Mock Device Kit support for Meta Ray-Ban Display display lifecycle.
- Native DAT production captouch, motion/orientation, and phone GPS APIs remain unknown from the public samples checked here; Web Apps are the documented path for those inputs.
- Wearables Developer Center pages were login-gated from this environment, so future implementation tasks must re-check authenticated docs before changing native package assumptions.

## Bridge Envelope Implications

- Camera photo/video payloads should cross the Swissknife/MCP++ control plane as content-addressed references with capture metadata, permission state, user-visible recording state, device/session IDs, and retention policy. Do not inline large media in control events.
- Microphone input and speaker/headphone output should cross as route decisions, transcript/audio artifact references, playback intents, and receipts. Bluetooth profile routing stays an OS/platform route, not a raw transport contract.
- Display output must include path identity (`dat-native`, `display-webapp`, `simulator`, `mobile-card`, `audio-summary`), lifecycle state, capability readiness, and fallback reason.
- Meta Neural Band, captouch, motion/orientation, and phone GPS should become normalized event envelopes with app binding IDs, timestamps, sequence numbers, source path, policy decision, replay protection, and optional privacy redaction.
- Bluetooth and Wi-Fi metadata can inform route quality, latency, and fallback decisions, but IPFS/libp2p/MCP++ compatibility is provided by the application bridge envelope: CIDs, peer IDs, session IDs, policy receipts, route receipts, backpressure, and acknowledgements.
- Hardware-free tests must cover ready, denied, unavailable, degraded, disconnect, update-required, stale route, and unsupported capability outcomes for every surface before native DAT assumptions land.

## Follow-Up Questions

- After authenticated Developer Center access, what exact Web Apps event shapes are exposed for Meta Neural Band and captouch beyond D-pad/Enter/back keyboard mapping?
- Which SDK, firmware, Meta AI app version, country, organization, and release-channel state are required for native DAT display in the target test environment?
- Can the current Mock Device Kit simulate any reusable device/session failure states beyond camera streaming and photo capture?
- What retention policy should control long-lived content-addressed camera/audio artifacts: local IPFS node, remote pinning service, app sandbox cache, backend object store, or policy-dependent deletion?
