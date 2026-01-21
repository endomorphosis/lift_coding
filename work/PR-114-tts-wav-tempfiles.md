# PR-114: TTS WAV temp files + correct extensions

## Summary
Fix multiple mobile call sites that requested WAV TTS but saved/played it as “.mp3”, which breaks on-device playback.

## Changes
- `TTSScreen`: request WAV, write `.wav` temp file, play from file.
- `CommandScreen`: request WAV, write `.wav` temp file, fix deleteAsync option (`idempotent`).
- `GlassesDiagnosticsScreen`: request WAV, write `.wav` temp file.
- `notificationsHandler`: request WAV and save `.wav` temp file.

## Test plan
- Manual on-device: trigger TTS from `TTSScreen`, from a notification, and from `CommandScreen` response.
- Verify audio plays and temp files are deleted afterward.
