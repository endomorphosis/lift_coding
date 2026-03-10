# PR-018: Wearables bridge diagnostics and native bridge baseline

## Goal
Add the first production-usable wearables bridge for iOS and Android as a local Expo module, focused on diagnostics, capability discovery, selected-target lifecycle, and safe device-session bring-up.

## Why
- `implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md`
- the wearables bridge should first land as a diagnostics and capability-discovery layer, not as a replacement for the current audio flow
- Meta DAT repos are reference inputs, not a required build dependency for this PR baseline

## Scope

### Native module
- create `mobile/modules/expo-meta-wearables-dat`
- add iOS bridge for availability, connected-device info, capability listing, and session lifecycle
- add Android bridge for the same baseline contract
- keep media capture APIs scaffolded but only enable what is stable in this PR
- persist selected target state and expose reconnect/connect operations
- emit rich state-change events for diagnostics and MCP-trigger handoff

### Expo config
- add config plugin support for:
  - iOS `Info.plist` MWDAT keys
  - Android manifest metadata for application id and analytics opt-out
- make bridge config environment-driven so development builds can compile without hardcoded values

### JS integration
- add a narrow JS wrapper and hooks
- extend diagnostics UI to show:
  - bridge availability
  - connected-device metadata
  - advertised capability matrix
  - analytics opt-out state
  - backend routing mode summary
  - selected target state, RSSI, and candidate discovery
- add local wearables receipt actions:
  - `mobile_open_wearables_diagnostics`
  - `mobile_reconnect_wearables_target`

### Testing
- JS hook tests with native mocks
- Android mock-device compatibility validation where practical
- no regression to the current `expo-glasses-audio` path
- contract coverage for local wearables receipt actions across result cards and notifications

## Out of scope
- making DAT the primary STT/TTS path
- full photo/video artifact upload workflows
- command-surface media actions
- hard dependency on GitHub Packages DAT Android artifacts

## Acceptance criteria
- device builds on iOS and Android can report bridge availability and capability state
- diagnostics screen surfaces bridge information without breaking current glasses diagnostics
- Android package-resolution constraints, reference-only fallback, and analytics opt-out behavior are documented
- the app still functions when DAT is unavailable or disabled
- wearables connectivity receipts expose local diagnostics/reconnect actions across backend and mobile surfaces

## Dependencies
- physical device builds for final validation
- existing local module pattern in `mobile/modules/expo-glasses-audio`

## Current status
- baseline delivered as a first-party bridge rather than an official DAT-SDK-dependent integration
- Android-safe builds validate with DAT artifacts disabled
- local wearables receipt action contract is implemented and documented
