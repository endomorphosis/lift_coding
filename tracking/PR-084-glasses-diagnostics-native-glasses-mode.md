# PR-084: Glasses diagnostics — native glasses mode wiring

## Goal
Make the mobile diagnostics flow actually exercise the native glasses audio module when "Glasses Mode" is enabled, so a developer can validate: record → upload → command → TTS → play back through glasses.

## Context
`mobile/src/screens/GlassesDiagnosticsScreen.js` currently provides a DEV-mode audio loop using `expo-av`, but "Glasses Mode" is effectively a placeholder message.

Now that `expo-glasses-audio` provides recording/playback APIs (PR-083), the screen should switch to native APIs when dev mode is OFF.

## Scope
- Update `GlassesDiagnosticsScreen` so:
  - DEV mode uses `expo-av` (current behavior)
  - Glasses mode uses the native module (`ExpoGlassesAudio`) for:
    - audio route info
    - recording to a file
    - playback of recorded audio and TTS output
- Provide graceful fallback on platforms where the native module is unavailable.
- Clean up any stale/legacy commented code blocks that confuse maintenance.

## Non-goals
- Full production UI polish.
- Push notifications.

## Acceptance criteria
- On a physical device with a dev build:
  - Switching to Glasses mode enables native route info.
  - Recording produces a file and playback uses the native path.
  - Running the pipeline speaks back through the glasses when available.

## Suggested files
- `mobile/src/screens/GlassesDiagnosticsScreen.js`
- `mobile/modules/expo-glasses-audio/*`

## Validation
- Follow `mobile/BUILD.md` and manually test both modes.
