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
- mobile/glasses/TODO.md
- mobile/glasses/android/
