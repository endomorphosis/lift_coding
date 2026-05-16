# Meta Wearables DAT 0.7 + Display Integration Baseline

## Scope

This document captures the current in-repo baseline and immediate upgrade scaffolding for integrating Meta Wearables DAT 0.7 display features in HandsFree mobile and related contracts.

## Baseline snapshot

### Current bridge and diagnostics surfaces

- Expo module: `/home/runner/work/lift_coding/lift_coding/mobile/modules/expo-meta-wearables-dat`
- Native bridge wrappers:
  - `/home/runner/work/lift_coding/lift_coding/mobile/src/native/wearablesBridge.js`
  - `/home/runner/work/lift_coding/lift_coding/mobile/src/native/metaWearablesDat.js`
- Diagnostics UI:
  - `/home/runner/work/lift_coding/lift_coding/mobile/src/screens/GlassesDiagnosticsScreen.js`
- Capability summarization:
  - `/home/runner/work/lift_coding/lift_coding/mobile/src/utils/metaWearablesDatCapabilities.js`

### Local action contract touchpoints

- Mobile local action handling:
  - `/home/runner/work/lift_coding/lift_coding/mobile/src/utils/agentActions.js`
- API schema descriptions:
  - `/home/runner/work/lift_coding/lift_coding/src/handsfree/models.py`

## Delta against upstream DAT 0.7

Upstream 0.7 introduces app-model + display capability flows (DAM + display rendering/video support) and additional session/typed error semantics.

Implemented in this repository as scaffolding:

- Android DAT default target upgraded to `0.7.0` in module gradle defaults.
- Optional dependency coordinates added for:
  - `mwdat-core`
  - `mwdat-camera`
  - `mwdat-display`
  - `mwdat-mockdevice`
- Expo plugin now supports:
  - DAT SDK target metadata
  - DAM app-model metadata on iOS and Android
  - display-mode validation checks for required app identifiers
- Bridge contracts expanded for display lifecycle test actions:
  - `renderDisplayTest`
  - `clearDisplay`
  - `playDisplayVideo`
  - `resetDisplaySession`
- Diagnostics contract expanded with compatibility/readiness metadata:
  - `sdkVersionTarget`
  - `sdkMeetsMinimum`
  - `datAppModelEnabled`
  - `displayDamEnabled`
  - `displayReady`
  - `configWarnings`

## Target device matrix (current)

### Display-capable glasses

- Requirement: DAT app-model (DAM) enabled and DAT SDK meeting minimum target (`0.7.0+`)
- Current in-repo state: diagnostics + contract scaffolding is present; native display rendering path is intentionally stubbed with actionable status messages.

### Non-display-capable glasses / fallback

- Existing audio-first and diagnostics-first flow remains the primary reliable path.
- Display actions are surfaced as unsupported/bridge-reference in diagnostics instead of failing silently.

## Minimum SDK targets

- Android DAT: `0.7.0` default target
- iOS DAT: `0.7.0` target metadata surfaced in config/diagnostics contract

## Immediate next implementation gates

1. Replace display test stubs with real DAT session/display attach APIs where SDK linkage is available.
2. Add backend-driven display action orchestration with follow-up action contracts.
3. Add CI split lanes for DAT-disabled and DAT-enabled mobile builds.
4. Add physical-device validation checklist for display-capable models.
