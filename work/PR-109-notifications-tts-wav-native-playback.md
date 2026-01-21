# PR-109: Notifications TTS WAV + native playback

## Checklist
- [ ] iOS dev-client: notification TTS plays through glasses when connected
- [ ] Android: notification TTS plays through glasses (native) or falls back to expo-av
- [ ] Temp `.wav` files cleaned up after playback

## Notes
- On Android native playback expects a filesystem path (no `file://`).
