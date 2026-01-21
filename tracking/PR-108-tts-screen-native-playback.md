# PR-108: TTSScreen native playback + format correctness

## Goal
Make the manual Text-to-Speech screen behave like the on-device pipeline:
- Request explicit WAV from `/v1/tts`.
- Write audio to a temp file with the correct extension.
- Prefer `expo-glasses-audio` native playback when available (routes to glasses), with `expo-av` fallback.

## Why
The existing TTSScreen uses a data-URL playback path that is brittle on real devices and doesn’t reliably route audio to glasses.

## Acceptance criteria
- TTSScreen plays TTS from a temp `.wav` file.
- When `expo-glasses-audio` is available, playback uses `playAudio()`.
- Temp files and listeners are cleaned up on stop/completion.
