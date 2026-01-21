# PR-112: Android expo-glasses-audio reliability fixes

## Summary
Fix Android native glasses-audio module issues that block on-device testing.

## Changes
- Fix audio source enum wiring (`AudioSource`) in `ExpoGlassesAudioModule`.
- Ensure recordings create and write to an actual WAV output file.
- Return consistent `file://` URIs from recording APIs.
- Accept `file://` URIs for playback.
- Build `getAudioRoute()` response from structured route data rather than parsing summary strings.

## Test plan
- Build dev client for Android and open the Glasses diagnostics screen.
- Record a short clip and confirm:
  - a WAV file is created,
  - `stopRecording()` returns a non-empty URI,
  - playback succeeds.
