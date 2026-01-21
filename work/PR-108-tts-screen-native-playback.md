# PR-108: TTSScreen native playback + format correctness

## Checklist
- [ ] iOS dev-client: TTSScreen plays through glasses when connected
- [ ] Android: TTSScreen plays (native or expo-av fallback)
- [ ] Stop button stops playback and cleans temp file

## Notes
- Native Android playback expects a filesystem path; this screen strips the `file://` prefix on Android only.
