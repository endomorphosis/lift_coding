# PR-052: Glasses JS integration + end-to-end TTS playback

## Goal
Wire the native iOS/Android glasses audio modules into the React Native app so the diagnostics screen can:
- Detect route changes
- Record audio via glasses mic
- Play back audio (including TTS output) via glasses speakers

## Scope
- Add JS/TS wrapper module(s) for the native bridges (iOS + Android)
- Integrate into the Glasses diagnostics flow:
  - Route monitor status UI
  - Start/stop recording, show file path/uri
  - Playback recorded WAV
  - Playback TTS (provider output) on glasses
- Ensure Expo dev-client expectations are documented (Expo Go not supported)

## Acceptance criteria
- On iOS and Android physical devices paired to Meta AI Glasses:
  - Route status updates correctly
  - Record → play back via glasses works
  - "Test TTS" plays through glasses

## References
- mobile/src/screens/GlassesDiagnosticsScreen.js
- mobile/glasses/TODO.md
- PR-046..PR-051 native work
