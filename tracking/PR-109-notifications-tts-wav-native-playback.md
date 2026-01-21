# PR-109: Notifications TTS WAV + native playback

## Goal
Make the notification → TTS playback path device-ready by:
- Requesting explicit WAV from `/v1/tts`.
- Saving temp audio as `.wav` (format/extension match).
- Preferring native playback via `expo-glasses-audio` when available (routes to glasses), with `expo-av` fallback.

## Why
Today notifications use `fetchTTS()` default (mp3) but save the file as `.mp3`, and playback is via `expo-av` only. That's brittle and often won't route to glasses.

## Acceptance criteria
- `speakNotification()` requests `{ format: 'wav' }` and writes a `.wav` temp file.
- When `expo-glasses-audio` is available, playback uses `playAudio()`.
- Temp files + listeners are cleaned up on completion/error.
