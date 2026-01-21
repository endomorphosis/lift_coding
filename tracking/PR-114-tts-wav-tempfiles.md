# PR-114: TTS WAV temp files + correct extensions

## Goal
Make TTS playback reliable on real devices by ensuring the client:
- Requests WAV explicitly from `/v1/tts`.
- Saves the returned audio bytes to a `.wav` temp file (not `.mp3`).
- Plays from a file URI rather than a data URL.

## Why
The backend defaults to returning WAV. Writing WAV bytes to a `.mp3` filename (or attempting playback as a data URL) causes device-specific playback failures and blocks glasses routing work.

## Acceptance criteria
- `TTSScreen`, `CommandScreen`, `GlassesDiagnosticsScreen`, and the notifications handler request `{ format: 'wav', accept: 'audio/wav' }`.
- Temp files created for TTS use `.wav` extension.
- Temp files are cleaned up with `FileSystem.deleteAsync(..., { idempotent: true })`.
