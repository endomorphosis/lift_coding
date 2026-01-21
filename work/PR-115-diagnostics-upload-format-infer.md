# PR-115: Infer diagnostics upload audio format

## Summary
Fix the Diagnostics audio command pipeline to stop hardcoding `'m4a'` when uploading recorded audio. The upload format is now inferred from the recorded file URI (e.g. `.wav`).

## Changes
- `GlassesDiagnosticsScreen`: add a small URI-based format inference helper and use it when calling `uploadDevAudio`.

## Test plan
- Manual on-device: record from Diagnostics and run “process through pipeline”.
- Confirm the backend accepts/decodes the uploaded audio and returns a valid response.
