# PR-117: Mobile TTS WAV temp-file regression

## Goal
Make TTS playback reliable on real devices by keeping the backend TTS format (WAV) consistent with the local temp-file extension and cleanup behavior.

## Why
Recent call sites were saving backend-provided WAV bytes into `.mp3` temp files and (in one spot) using an invalid `expo-file-system` cleanup option. On iOS especially, extension/decoder mismatches can cause silent failures or intermittent playback.

## Acceptance criteria
- TTS temp files are written with a `.wav` extension anywhere we persist them to disk.
- Temp-file cleanup uses `FileSystem.deleteAsync(..., { idempotent: true })`.
- Call sites explicitly request `format: 'wav'` from `fetchTTS()` to prevent future drift.
