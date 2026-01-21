# PR-112: Android expo-glasses-audio reliability fixes

## Goal
Make the Android native module (`mobile/modules/expo-glasses-audio`) actually usable on-device for glasses testing:
- Recording produces a real WAV file and returns a usable `file://` URI.
- Playback accepts `file://` URIs.
- `getAudioRoute()` returns sensible structured info.

## Why
Android device testing depends on the native module being correct and stable. The existing implementation had multiple hard failures (wrong enum references, null output file, path/URI mismatches) that would block real-device debugging.

## Acceptance criteria
- `startRecording()` creates a WAV file and returns `uri` as `file://...`.
- `stopRecording()` returns the recorded file URI/size/duration when available.
- `playAudio()` works with both `file://...` URIs and raw file paths.
- `getAudioRoute()` no longer relies on parsing a human-formatted summary string.
