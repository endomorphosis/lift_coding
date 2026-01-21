# PR-104: Notifications TTS — correct format and route playback through glasses when available

## Why
For on-device iOS/Meta Glasses debugging, notifications must reliably speak through the glasses.
Today `notificationsHandler`:
- calls `fetchTTS()` (backend defaults to WAV) but saves the file as `.mp3`
- always plays via `expo-av`, which may not route through Bluetooth HFP/SCO

## Scope
- Update `mobile/src/push/notificationsHandler.js` to:
  - Request an explicit TTS format and write the temp file with the matching extension
  - Prefer native glasses playback via `expo-glasses-audio` when available
  - Wait for native `onPlaybackStatus` completion before deleting temp files (with timeout fallback)
  - Keep current `expo-av` fallback for DEV / non-native builds
- Update `mobile/src/screens/TTSScreen.js` to use the same `fetchTTS(text, { format })` behavior.

## Acceptance Criteria
- Push notifications speak successfully in Glasses Mode without relying on `expo-av` routing.
- Temp file extensions match actual audio format.
- Temp files are deleted after playback completion (or timeout), not before.
- Existing DEV-mode behavior remains functional.
