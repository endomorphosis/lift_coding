# MGW-017 Android Native Manifest Rendering

Date: 2026-05-22
Task: MGW-017 Render compiled widget manifest regions on Android native DAT display

## Outcome

Android native DAT display rendering now parses compiled widget manifests and maps safe 600x600 manifest content into the DisplayAccess DSL instead of rendering only a title/detail/footer summary.

The renderer now:

- Renders text, status, and progress regions in manifest visual order.
- Renders focusable action regions as DAT buttons ordered by `focus_order`.
- Sends HTTPS image media through the DAT image builder when available.
- Keeps video content out of `flexBox`; `play_video` uses a root DAT video view only for HTTPS MP4 sources with linked player classes.
- Records unsupported viewport, region, image, and video cases in `displayFallback.renderFallbacks`, with `regionFallbacks` and `mediaFallbacks` breakdowns, while continuing to send fallback text content when possible.

## Validation

Planned validation commands for this task:

```bash
cd mobile && npm test -- --runInBand modules/expo-meta-wearables-dat/__tests__/index.test.js
cd mobile/android && env JAVA_HOME=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8 PATH=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8/bin:$PATH ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false
```

Physical validation follow-up is tracked in `docs/meta-wearables-dat-display-physical-validation-checklist.md`.
