# PR-050: Android audio route monitor (AudioManager) + JS bridge

## Goal
Expose real-time Android audio routing state (inputs/outputs, SCO) for Meta AI glasses diagnostics.

## Scope
- Implement/finish `mobile/glasses/android/AudioRouteMonitor.kt`
- Detect Bluetooth headset/SCO availability + connection state
- Expose route snapshots + change callbacks to React Native

## Acceptance criteria
- On a physical Android device paired to Meta AI Glasses, the diagnostics UI shows:
  - current input/output devices
  - SCO status and audio mode
  - updates on connect/disconnect

## References
- `mobile/glasses/README.md` - shared mobile glasses setup and diagnostics notes.
- `mobile/glasses/android/README.md` - Android audio route monitor architecture and validation notes.
- `mobile/glasses/android/IMPLEMENTATION_NOTE.md` - standalone versus Expo module implementation guidance.
- `mobile/glasses/android/AudioRouteMonitor.kt` - standalone Android route monitor reference.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/AudioRouteMonitor.kt` - active Expo Android route monitor implementation.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesAudioModule.kt` - legacy Android React Native bridge reference.
- `mobile/modules/expo-glasses-audio/index.ts` - JS/TS wrapper exposing route snapshots and route-change events.

## Resolution notes
The codebase scan evidence for MGW-101 matched broad planning checklist context
from `mobile/glasses/TODO.md`. That checklist predates the current Android route
monitor implementation, so this tracker now points directly at the current
Android documentation, source, and JS bridge surfaces needed to validate PR-050.
