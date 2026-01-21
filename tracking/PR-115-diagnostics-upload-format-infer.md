# PR-115: Infer diagnostics upload audio format

## Goal
Make the Diagnostics audio pipeline send the correct `format` to the backend by inferring it from the recorded file URI, instead of hardcoding `'m4a'`.

## Why
The native glasses recorder typically produces `.wav` recordings. Uploading WAV bytes while telling the server the format is `m4a` can break STT parsing/decoding and blocks reliable on-device diagnostics.

## Acceptance criteria
- `GlassesDiagnosticsScreen` infers upload format from `lastRecordingUri` and passes it to `uploadDevAudio`.
- No hardcoded `'m4a'` format remains in the diagnostics upload call.
- If the extension cannot be inferred, fall back safely (current behavior).
