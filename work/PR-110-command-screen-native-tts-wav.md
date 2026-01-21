# PR-110: CommandScreen TTS WAV + native playback

## Checklist
- [ ] iOS dev-client: command response spoken text plays through glasses when connected
- [ ] Android: spoken text plays (native or expo-av fallback)
- [ ] Stop button stops playback and cleans temp file

## Notes
- Android native playback expects a filesystem path (no `file://`).
