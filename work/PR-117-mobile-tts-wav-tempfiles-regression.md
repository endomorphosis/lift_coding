# PR-117: Mobile TTS WAV temp-file regression

## Summary
Fix TTS playback regressions caused by saving WAV bytes as `.mp3` temp files and incorrect temp-file cleanup options.

## Changes
- Write `.wav` temp files in:
  - `CommandScreen`
  - `GlassesDiagnosticsScreen`
  - push notification auto-speak handler
- Use `fetchTTS(..., { format: 'wav', accept: 'audio/wav' })` at those call sites.
- Fix `FileSystem.deleteAsync` options to use `{ idempotent: true }`.

## Test plan
- Manual (recommended on-device):
  - Trigger TTS in Command screen.
  - Trigger TTS from Glasses Diagnostics pipeline response.
  - Trigger a push notification and confirm auto-speak plays.
