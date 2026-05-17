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

## Source alignment (validated in this environment)

Accessible upstream sources used for this integration baseline:

- `https://github.com/facebook/meta-wearables-dat-ios` (README + CHANGELOG)
- `https://github.com/facebook/meta-wearables-dat-android` (README + setup requirements)
- `https://github.com/facebookincubator/meta-wearables-webapp` (web-app constraints/tooling)

Blocked fetch targets (must be validated manually in release checklist):

- `https://developers.meta.com/blog/build-for-display-glasses/`
- `https://wearables.developer.meta.com/docs/develop/webapps`
- `https://developers.facebook.com/docs/ray-ban/...`

## DAT 0.7 requirements matrix (current state)

| Area | DAT 0.7 expectation | Current repo state | Gap |
|---|---|---|---|
| Android SDK target | 0.7.0+ | `0.7.0` default target configured | Environment-specific enablement still mostly off |
| iOS SDK target metadata | 0.7.0+ | `0.7.0` target exposed in diagnostics/config | Native link path still bridge-first |
| DAM app model | required for display | plugin + metadata scaffolding present | production DAM rollout matrix needed |
| Display lifecycle actions | render/clear/video/reset | bridge methods exposed across JS/native | previously stub-only responses; now bridge lifecycle state added |
| Display diagnostics | session/readiness/error visibility | readiness + config warnings + capability matrix | needs hardware-backed validation paths |
| Backend follow-up actions | include display-safe actions by capability | diagnostics/reconnect/render/clear existed | expanded actions added for play video + reset |
| Web-app display constraints | 600x600, D-pad focus, high contrast, HTTPS deployment | dedicated evaluator + linter + example readiness descriptor in-repo | execute physical-device checklist runs and capture staged rollout evidence artifacts |

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

## Web-app display support module (Phase F)

This repository now includes a dedicated compatibility evaluator for display-glasses web-app readiness:

- Evaluator module: `src/handsfree/display_webapp_compat.py`
- Linter script: `scripts/lint_display_webapp_readiness.py`
- Example checklist payload: `config/display_webapp_readiness.example.json`

Current enforced checks:

- HTTPS + publicly reachable deployment URL
- 600x600 viewport requirement
- D-pad/focus navigation contract (`dpad_focus` + focusable targets + validated order)
- dark-theme support
- contrast ratio floor (`>= 4.5`)
- documented app-connection onboarding path

Run the linter:

```bash
cd <repo-root>
PYTHONPATH=./src python3 scripts/lint_display_webapp_readiness.py config/display_webapp_readiness.example.json
```

Exit codes:

- `0` = readiness checks pass
- `1` = one or more blocking checks failed

## Web-app deployment + onboarding path (Phase F)

Recommended deployment flow for display web-apps:

1. Publish the web-app to a publicly reachable HTTPS origin.
2. Validate readiness using the internal linter before onboarding.
3. Record onboarding guidance for operators/users:
   - app endpoint URL
   - prerequisites and account/permission needs
   - app-connection steps in wearables companion flow
4. Store readiness artifacts and onboarding notes with release evidence for staged rollout.

## Physical validation + staged rollout artifacts (Phase G)

This repository now includes templates to run and record hardware-backed validation:

- Physical validation checklist:
  - `docs/meta-wearables-dat-display-physical-validation-checklist.md`
- Staged rollout evidence template:
  - `docs/meta-wearables-dat-display-rollout-evidence-template.md`

Recommended gate sequence:

1. Run the webapp readiness linter for the target deployment metadata.
2. Execute the physical-device checklist on display-capable hardware.
3. Record outcomes, artifacts, and rollout decision in the evidence template.

## Minimum SDK targets

- Android DAT: `0.7.0` default target
- iOS DAT: `0.7.0` target metadata surfaced in config/diagnostics contract

## Immediate next implementation gates

1. Replace display test stubs with real DAT session/display attach APIs where SDK linkage is available.
2. Add backend-driven display action orchestration with follow-up action contracts.
