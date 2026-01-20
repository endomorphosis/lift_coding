# PR-083 work log

## Checklist
- [ ] Implement WAV writing in Android `startRecording`.
- [ ] Implement WAV parsing + playback in Android `playAudio`.
- [ ] Emit `onPlaybackStatus` events.
- [ ] Align JS exports/types with the native module name(s).
- [ ] Update module README.

## Notes
- Keep the Android implementation aligned with iOS module API.
- Prefer small, deterministic formats: PCM16 mono.
