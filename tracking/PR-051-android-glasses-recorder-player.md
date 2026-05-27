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
- mobile/glasses/IMPLEMENTATION_STATUS_PR051.md
- mobile/glasses/android/README.md
- mobile/glasses/android/GlassesRecorder.kt
- mobile/glasses/android/GlassesPlayer.kt
- mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/ExpoGlassesAudioModule.kt
- mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesRecorder.kt
- mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesPlayer.kt
