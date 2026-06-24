# MGW-413 Expanded Meta Glasses I/O Source Refresh

Date: 2026-06-23

This refresh expands the MGW lane from display widgets into the broader
Meta glasses interaction surface needed by Swissknife applications: camera,
microphone route, speaker/headphone route, display output, Meta Neural Band,
captouch, motion/orientation, phone GPS, and app-level control-plane handoff.

## Sources Checked

- Meta Wearables FAQ: https://developers.meta.com/wearables/faq/
- Meta display developer announcement: https://developers.meta.com/blog/build-for-display-glasses/
- Meta Wearables DAT Android repository and 0.7.0 changelog: https://github.com/facebook/meta-wearables-dat-android
- Meta Wearables DAT iOS repository: https://github.com/facebook/meta-wearables-dat-ios
- Meta Wearables Web App AI Toolkit: https://github.com/facebookincubator/meta-wearables-webapp
- Local DAT Android DisplayAccess and CameraAccess samples at `external/meta-wearables-dat-android`, commit `25f3a6d`.
- Local DAT iOS DisplayAccess and CameraAccess samples at `external/meta-wearables-dat-ios`, commit `a739e94`.

## Confirmed Constraints

- Meta exposes two public developer-preview paths: native DAT phone apps and display Web Apps. MGW must model them as distinct capability routes.
- DAT is the native route for glasses camera photo/video, mobile app integration, and display sessions on display-capable glasses.
- Microphone and speaker/headphone behavior should be modeled through iOS/Android Bluetooth audio route state, permission state, fallback state, and privacy receipts rather than assuming raw DAT audio packet access.
- DAT v0.7.0 adds native display support, the Device Access Toolkit App Model requirement for display, `DeviceSession.addDisplay`, one-root content replacement semantics, MP4 video playback, device/session error streams, `Device.isDisplayCapable`, and Mock Device Kit captouch simulation.
- Web Apps are the public display-glasses route for standalone HTML/CSS/JavaScript apps, browser-first layout testing, public HTTPS deployment, D-pad style Arrow/Enter input, motion/orientation, phone GPS, Meta Neural Band/captouch input, and local storage.
- Web Apps are not the public route for camera, microphone, speaker/headphone audio, or raw Bluetooth/Wi-Fi access.
- The public FAQ says Mock Device Kit enables hardware-free testing but does not currently support display glasses. MGW must keep independent mocks for display lifecycle and expanded I/O until official mock coverage changes.
- No checked official source exposes raw Neural Band EMG, raw Bluetooth/Wi-Fi packets, or direct Web Apps camera/microphone/audio routes.

## MGW Implementation Direction

- Swissknife applications should bind to normalized app-facing descriptors, not platform-specific DAT objects.
- Camera and display payloads may become content-addressed artifacts when policy allows storage; the bridge envelope should carry IPFS CIDs, app binding IDs, peer/session IDs, policy decisions, route decisions, replay protection, backpressure, and MCP++ receipts.
- Bluetooth and Wi-Fi remain route metadata unless an app-level phone/web bridge explicitly provides IPFS/libp2p/MCP++ behavior.
- Playwright coverage should validate Web Apps display layouts, Arrow/Enter Neural Band/captouch mappings, mocked motion/orientation, mocked GPS, visible app state, and control-plane receipt evidence without physical glasses.
- Native DAT validation should stay optional and gated by package access, Developer Mode or release-channel access, compatible firmware/app state, and physical device evidence.
