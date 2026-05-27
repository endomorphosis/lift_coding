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
- `mobile/src/screens/GlassesDiagnosticsScreen.js` - diagnostics UI integration for route status, recording, playback, and TTS playback.
- `mobile/modules/expo-glasses-audio/README.md` - active Expo module API and development-build usage notes.
- `mobile/glasses/BRIDGE_README.md` - standalone bridge architecture reference for Android recorder/player behavior.
- `docs/implementation/IMPLEMENTATION_SUMMARY_PR052.md` - PR-052 implementation summary and validation notes.
- `docs/meta-ai-glasses-audio-routing.md` - Bluetooth audio routing background for Meta AI Glasses.

## Resolution notes
This tracking note now points at the current PR-052 implementation artifacts:
the diagnostics screen, active Expo module docs, bridge architecture notes,
implementation summary, and audio-routing guide. The older broad glasses
diagnostics checklist is historical planning context and is intentionally not
used as the PR-052 reference.
