# PR-111: CommandScreen recording format inference

## Goal
Make `CommandScreen` audio upload reliable on real devices by:
- Recording into a consistent backend-supported container (`.m4a`).
- Inferring the upload `format` from the recorded file URI instead of hardcoding `'m4a'`.

## Why
The previous flow hardcoded `'m4a'` even though iOS may produce `.caf` with default presets, causing backend format mismatches.

## Acceptance criteria
- `startRecording()` uses explicit recording options targeting `.m4a`.
- `sendAudioAsCommand()` uses an inferred `format` when calling `uploadDevAudio()`.
- Voice confirmation clip uses the same approach.
