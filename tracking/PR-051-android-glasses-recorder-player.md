# PR-051: Android glasses recorder + player (SCO) + JS bridge

## Goal
Record from the glasses microphone and play back audio through glasses speakers on Android.

## Scope
- Implement/finish:
  - `mobile/glasses/android/GlassesRecorder.kt`
  - `mobile/glasses/android/GlassesPlayer.kt`
- Manage Bluetooth SCO routing (start/stop SCO, monitor state)
- Write 16kHz mono WAV output suitable for backend STT and local validation
- React Native bridge APIs for record/play/stop + status

## Acceptance criteria
- On a physical Android device paired to Meta AI Glasses:
  - Recording uses the glasses mic (when available)
  - Playback routes to glasses output
  - Output WAV is valid and audible

## References
- `mobile/glasses/README.md` - shared mobile glasses setup and diagnostics notes.
- `mobile/glasses/android/README.md` - Android recorder/player architecture and validation checklist.
- `mobile/glasses/IMPLEMENTATION_STATUS_PR051.md` - PR-051 recorder/player bridge implementation summary.
- `mobile/glasses/android/GlassesRecorder.kt` - standalone Android SCO recorder reference.
- `mobile/glasses/android/GlassesPlayer.kt` - standalone Android SCO WAV player reference.
- `mobile/glasses/android/GlassesAudioModule.kt` - standalone React Native bridge reference.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesRecorder.kt` - active Expo recorder implementation.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesPlayer.kt` - active Expo WAV player implementation.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/ExpoGlassesAudioModule.kt` - active Expo JS bridge implementation.
- `mobile/modules/expo-glasses-audio/index.ts` - JS/TS wrapper for app integration.

## Resolution notes
This tracking note points directly at the current Android source, Expo bridge,
and PR-051 status docs. The older broad diagnostics checklist is not listed here
because its Android section predates the recorder/player bridge implementation
and is only historical planning context.
