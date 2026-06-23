# MGW-029 Meta Glasses I/O Research Seed

Date: 2026-06-23

This note seeds the expanded MGW task lane. It is intentionally conservative: implementation tasks must keep verifying official Meta documentation and local DAT samples before assuming native package availability, hardware support, release-channel access, or transport behavior.

## Sources Checked

- Meta display developer announcement, 2026-05-14: https://developers.meta.com/blog/build-for-display-glasses/
- Meta Wearables developer FAQ: https://developers.meta.com/wearables/faq/
- Meta Wearables DAT Android repository: https://github.com/facebook/meta-wearables-dat-android
- Meta Wearables DAT iOS repository: https://github.com/facebook/meta-wearables-dat-ios

## Current Findings

- Meta describes two developer-preview paths for display glasses: extending native iOS/Android apps and building display Web Apps.
- DAT documentation describes native mobile access to glasses capabilities including camera/photo/video workflows, microphone/audio, and display where supported.
- The public Android DAT repository exposes `mwdat-core`, `mwdat-camera`, and `mwdat-mockdevice` modules. Camera and mock-device work should anchor on those modules before adding native assumptions.
- The public iOS DAT repository also describes connecting to Meta AI glasses and using video streaming/photo capture capabilities.
- Meta documentation describes microphone and speaker behavior through standard iOS/Android Bluetooth audio profiles. MGW should model this as a platform route/capability abstraction, not as raw audio packets.
- Web Apps for display glasses are documented as supporting motion/orientation, phone GPS, Meta Neural Band input, captouch input, and local storage. These are the cleanest public input surfaces for neural/captouch style controls.
- The Mock Device Kit is useful for hardware-free testing, but public FAQ language currently says it does not support display glasses. MGW therefore needs independent display and expanded I/O mocks.

## Implementation Constraints

- Keep Meta package credentials and paired glasses optional for default tests and builds.
- Keep native DAT display and expanded I/O behind capability checks and structured unsupported/degraded fallbacks.
- Treat Bluetooth and Wi-Fi as lower-level routes. IPFS/libp2p/MCP++ compatibility belongs in the app-level bridge envelope unless official Meta docs expose lower-level hooks.
- Preserve privacy boundaries: camera, microphone, GPS, neural/captouch, and motion inputs need explicit permission state, policy decisions, redaction metadata, and receipts.
- Swissknife applications should consume normalized contracts, not platform-specific DAT objects.

## Follow-Up Questions

- What exact display Web Apps input event shapes does Meta expose for Neural Band and captouch in the current developer-preview SDK?
- Which DAT version and release channel expose display capability packages for Android and iOS in the target build environment?
- Can Mock Device Kit simulate any camera/session behavior that is reusable for expanded I/O, even though display glasses are not covered?
- Where should long-lived content-addressed camera/audio artifacts be stored: local IPFS node, remote pinning service, app sandbox cache, or policy-dependent backend storage?
