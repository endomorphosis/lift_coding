# PR-103: Glasses diagnostics — use native events, fix URIs/formats, and remove timeout-based UI state

## Why
Before testing on iOS / Meta AI Glasses, the diagnostics screen needs to be reliable:
- Don’t guess playback completion with timeouts.
- Handle native module URI differences (`file://` vs absolute paths).
- Upload audio using the correct format/extension (WAV vs M4A).
- Request TTS in a known format and save with the correct extension.

## Scope
- Update `mobile/src/screens/GlassesDiagnosticsScreen.js` to:
  - Import the native module via the `expo-glasses-audio` package.
  - Subscribe to `onRecordingProgress` and `onPlaybackStatus` events to drive UI state.
  - Normalize file URIs for `expo-file-system` reads.
  - Infer upload format from the recorded file URI/extension.
  - Avoid deleting temp TTS audio before playback completes.
- Update `mobile/src/api/client.js` `fetchTTS()` to allow specifying `format`.

## Acceptance Criteria
- In Glasses Mode, playback state (`isPlaying`) is updated via native events, not timeouts.
- Upload uses `format=wav` when the recorded file is WAV; uses `m4a` for Expo AV recordings.
- TTS request explicitly sets a format (default `mp3`) and the temp file extension matches.
- No runtime errors on screen mount/unmount (cleanup is correct).
