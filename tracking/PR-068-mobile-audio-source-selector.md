# PR-068: Mobile audio source selector (Ray-Ban Meta mic reliability)

## Goal
Make MVP1 demos reliable by allowing the mobile app to explicitly choose the **audio capture source**:
- **Phone mic** (recommended default for iOS demos)
- **Glasses/Bluetooth mic** (when available)

…and clearly surface the current audio route/state so the user understands when Bluetooth mic routing is unstable.

## Why
The primary MVP1 demo blocker called out in the plan is iOS Bluetooth microphone reliability (A2DP  HFP/HSP switching). We already have route monitoring and fallback logic, but there is no user-visible control to force a stable capture path.

## Scope
Mobile-only changes under `mobile/`.

## Deliverables
- A simple **Audio Source** setting (UI) with at least:
  - `Phone Mic` (forces phone mic recording)
  - `Glasses/Bluetooth Mic` (attempts Bluetooth mic capture; if unavailable, show error and fall back)
  - `Auto` (optional: use current behavior)
- Persist selection in AsyncStorage.
- Plumb selection into the recording path so it actually affects capture.
- Display current audio route / capture source in the Status/Diagnostics UI.

## Acceptance criteria
- On iOS with Ray-Ban Meta connected, user can set **Phone Mic** and consistently record commands while still playing TTS through glasses.
- If user selects **Glasses/Bluetooth Mic** and the route is not available, the UI shows an actionable warning and recording still works via fallback.
- Selection persists across app restarts.

## Implementation notes
- Likely touch points:
  - `mobile/src/screens/StatusScreen.js` (settings surface)
  - Recording hook/service in `mobile/src/` and native module bridge in `mobile/modules/expo-glasses-audio`.
  - iOS route monitoring: `mobile/glasses/ios/AudioRouteMonitor.swift`.
- Prefer minimal UI; demo reliability > polish.

## Test plan
- Manual:
  - iOS simulator / device: switch between sources, confirm it persists.
  - Real iPhone + Ray-Ban Meta: verify phone-mic capture + glasses playback is stable.
