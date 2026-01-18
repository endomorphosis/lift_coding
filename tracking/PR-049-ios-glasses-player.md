# PR-049: iOS glasses Bluetooth player (WAV/TTS) + JS bridge

## Goal
Enable reliable audio playback through Meta AI glasses speakers on iOS.

## Scope
- Implement/finish `mobile/glasses/ios/GlassesPlayer.swift`
- Configure `AVAudioSession` for Bluetooth output routing
- Add a React Native bridge so the diagnostics screen can:
  - play a local WAV file
  - play backend TTS audio saved to disk
  - stop playback

## Acceptance criteria
- On a physical iPhone paired to Meta AI Glasses, playback routes to the glasses.
- Playback can be started/stopped from the diagnostics UI.
- Works in an Expo development build (not Expo Go).

## References
- mobile/glasses/TODO.md
- mobile/glasses/ios/
- mobile/src/screens/GlassesDiagnosticsScreen.js
