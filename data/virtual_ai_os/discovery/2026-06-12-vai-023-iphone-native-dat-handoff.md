# VAI-023 iPhone Native DAT Handoff

Date: 2026-06-12
Task: VAI-023
Track: ops

## Purpose

This packet prepares the iPhone native DAT handoff for physical validation. It
does not claim a successful physical-device run; it defines the evidence bundle
that must be carried from the hardware-free virtual AI OS path into the iPhone
DAT run before any native display rollout decision.

## Reviewed Inputs

- Virtual AI OS plan:
  `implementation_plan/docs/19-virtual-ai-os-submodule-integration.md`
- Meta Ray-Ban simulator plan:
  `implementation_plan/docs/20-meta-rayban-display-interface-simulator.md`
- Physical validation checklist:
  `docs/meta-wearables-dat-display-physical-validation-checklist.md`
- Rollout evidence template:
  `docs/meta-wearables-dat-display-rollout-evidence-template.md`
- Display integration baseline:
  `docs/meta-wearables-dat-display-integration.md`
- Simulator/Web App package:
  `dev/meta-rayban-display-simulator/`
- Current iOS DAT bridge:
  `mobile/modules/expo-meta-wearables-dat/ios/ExpoMetaWearablesDatModule.swift`

## Handoff Bundle

Carry these artifacts into the physical iPhone run:

| Item | Source | Required evidence |
| --- | --- | --- |
| Simulator fixture | `dev/meta-rayban-display-simulator/fixtures/task-progress.json` | fixture name, manifest/action IDs, operation order |
| Simulator trace | exported from `dev/meta-rayban-display-simulator/` | `display_state`, `focus`, `activate`, fallback samples, correlation metadata |
| Web App readiness metadata | `dev/meta-rayban-display-simulator/webapp/readiness.json` | linter command and pass/fail result |
| Hosted Web App | deployed copy of `dev/meta-rayban-display-simulator/webapp/` | public HTTPS URL registered in Meta AI app |
| iPhone app build | development build with `expo-meta-wearables-dat` | build identifier, release channel, DAT SDK target, `MWDATCore` and `MWDATDisplay` linkage |
| Device state | physical iPhone, glasses, Meta AI app | iOS version, glasses firmware, Meta AI app version, pairing/connectivity screenshot or note |
| Runtime flags | backend/mobile environment | display-widget flags, rollback flag values, backend URL/auth mode |
| Result payloads | iPhone diagnostics/action surface | `supported`, `renderPath`, `reason`, `requiredAction`, `displayConnectionState`, `displayLifecycleStages` |
| Observability | backend `/v1/metrics` and mobile logs | before/after metric snapshot and private-content-redacted status logs |
| Rollback proof | backend flag/channel switch and Web App/mobile fallback | validation that native iPhone DAT can be held or disabled without losing fallback display |

## Execution Order

1. Export the simulator trace for the task-progress fixture.
2. Validate Web App readiness with
   `PYTHONPATH=./src python3 scripts/lint_display_webapp_readiness.py dev/meta-rayban-display-simulator/webapp/readiness.json`.
3. Host the Web App over public HTTPS and register it through Meta AI app
   `App Connections > Web apps`.
4. Record iPhone build state: SDK-unlinked fallback, SDK-linked native, or
   bridge-only.
5. Run the physical checklist in
   `docs/meta-wearables-dat-display-physical-validation-checklist.md`.
6. Complete a copy of
   `docs/meta-wearables-dat-display-rollout-evidence-template.md` for the run.
7. Decide one of: proceed with staged native DAT, hold native DAT and keep Web
   App/mobile-card fallback, or rollback display widgets entirely.

## Decision Gates

Native iPhone DAT remains held unless the completed evidence shows:

- simulator and iPhone payload parity for manifest IDs, action IDs, focus order,
  operation order, and correlation metadata;
- `displaySdkLinked: true` and DAT SDK target `>= 0.7.0` for a native-display
  build;
- DisplayAccess lifecycle progress through target selection, session start,
  display attach/start, and content send;
- structured fallback payloads for SDK-unlinked, display-SDK-unlinked, DAM
  disabled, firmware/app update, lifecycle error, and unsupported media states;
- Web App or mobile-card fallback still works after setting
  `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS=false`;
- no private prompt/content captured in committed logs, screenshots, or metrics.

## Physical Evidence Status

Physical validation evidence has not been collected in this worktree. The next
operator with a DAT-capable iPhone/glasses setup should attach redacted run
artifacts to the release ticket or private artifact store and link the completed
evidence template from the rollout decision.
