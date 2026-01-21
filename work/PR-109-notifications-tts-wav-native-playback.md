# PR-109: Notifications TTS WAV + native playback

## Checklist
- [x] iOS dev-client: notification TTS plays through glasses when connected
- [x] Android: notification TTS plays through glasses (native) or falls back to expo-av
- [x] Temp `.wav` files cleaned up after playback

## Implementation Summary
- Updated `fetchTTS()` in `mobile/src/api/client.js` to accept format and accept header options
- `speakNotification()` in `notificationsHandler.js` requests WAV format and saves with `.wav` extension
- Native playback via `expo-glasses-audio` is preferred when available, with `expo-av` fallback
- Comprehensive cleanup of temp files and listeners on both completion and error paths

## Notes
- On Android native playback expects a filesystem path (no `file://`).
