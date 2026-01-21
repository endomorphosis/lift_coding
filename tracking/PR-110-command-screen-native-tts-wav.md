# PR-110: CommandScreen TTS WAV + native playback

## Goal
Make `CommandScreen` TTS device-ready by:
- Requesting explicit WAV from `/v1/tts`.
- Writing a temp `.wav` file (format/extension match).
- Preferring native playback via `expo-glasses-audio` when available (routes to glasses), with `expo-av` fallback.

## Why
The current implementation relies on a data URL → `.mp3` temp file flow even though the backend defaults to WAV. This is brittle and can mis-route audio off-glasses.

## Acceptance criteria
- `playTTS()` requests `{ format: 'wav' }` and writes `.wav`.
- When available, playback uses `ExpoGlassesAudio.playAudio()`.
- Temp files + listeners cleaned up on completion/stop/unmount.
