# PR-111: CommandScreen recording format inference

## Summary
Fix on-device audio upload brittleness in `CommandScreen`.

## Changes
- Switch recording options from `Audio.RecordingOptionsPresets.HIGH_QUALITY` to explicit `.m4a`-targeting options.
- Infer upload `format` from the recorded URI extension (fallback behavior for iOS `.caf`).
- Apply inference to both primary command audio uploads and the voice confirmation clip.

## Test plan
- Run `npm test` / existing test suite (if applicable).
- Manual on-device:
  - Record a command on iOS and Android.
  - Confirm the uploaded `format` matches the file produced.
  - Confirm backend processes without decode errors.
