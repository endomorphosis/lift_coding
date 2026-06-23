# VAI-023 iPhone Native DAT Handoff

Date: 2026-06-12
Updated: 2026-06-23
Task: VAI-023
Track: mobile
Depends on: VAI-018, VAI-020

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
- VAI-018 native mobile parity gate:
  `data/virtual_ai_os/discovery/2026-06-23-vai-018-dat-mockdevicekit-native-mobile-parity.md`
- VAI-020 mobile ORB diagnostics gate:
  `data/virtual_ai_os/discovery/2026-06-23-vai-020-mobile-orb-edge-diagnostics-policy-receipts.md`
- Simulator/Web App package:
  `dev/meta-rayban-display-simulator/`
- Current iOS DAT bridge:
  `mobile/modules/expo-meta-wearables-dat/ios/ExpoMetaWearablesDatModule.swift`
- Current mobile bridge wrapper:
  `mobile/src/native/wearablesBridge.js`
- Current mobile ORB bridge:
  `mobile/src/orb/metaGlassesMobileOrbBridge.js`

## iPhone Native DAT Runtime Contract

The iPhone native DAT handoff is a runtime contract, not only a device test
checklist. A DAT-backed mobile session is acceptable for physical validation
only when the same session can prove these three behaviors with shared
correlation and receipt metadata:

| Behavior | Required runtime contract | Evidence source |
| --- | --- | --- |
| Control local UI | The mobile app accepts display-widget render, update, focus, activate, clear, reset, video, and subscription actions; each result preserves `widgetId`, `widgetCid`, `descriptorCid` or `interfaceCid`, `correlationId`, `requestId`, `operation`, `renderPath`, and fallback `reason`. | `mobile/src/native/wearablesBridge.js`, iPhone bridge diagnostics, simulator trace parity |
| Offload compute | Command execution can stay local or dispatch to backend/desktop peers while preserving parent receipt CIDs, policy decision metadata, placement/offload status, and fallback actions when the selected peer or native DAT display is unavailable. | VAI-020 diagnostics fields, `/v1/mobile/orb/diagnostics`, virtual AI OS E2E dispatch receipts |
| Expose status to Meta glasses | The session publishes a display-widget action or Web App/mobile-card fallback that reports task state, spoken status, recovery state, and degraded edge reasons without leaking private prompt content. | Mobile ORB dispatch payload, Web App readiness export, native DAT result payloads |

The session join keys are `correlation_id`, `request_id`, `receipt_cid`,
`parent_receipt_cids`, `policy_cid`, `descriptor_cid`, `interface_cid`,
`widget_id`, and `widget_cid`. A physical iPhone run that cannot join local UI
control, offload receipts, and glasses-visible status through these fields is
not valid rollout evidence even if one visual display action succeeds.

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
| Mobile ORB diagnostics | `/v1/mobile/orb/diagnostics` and `handsfree.meta-glasses/mobile-orb-diagnostics@0.1.0` | `backend_counts`, `binding_state`, `policy_receipts`, `receipt_integrity`, `edge_health`, `receipt_cids`, `policy_cids`, `fallback_reasons` |
| Observability | backend `/v1/metrics` and mobile logs | before/after metric snapshot and private-content-redacted status logs |
| Rollback proof | backend flag/channel switch and Web App/mobile fallback | validation that native iPhone DAT can be held or disabled without losing fallback display |

## Execution Order

1. Export the simulator trace for the task-progress fixture and record the
   session join keys listed in the runtime contract.
2. Validate Web App readiness with
   `PYTHONPATH=./src python3 scripts/lint_display_webapp_readiness.py dev/meta-rayban-display-simulator/webapp/readiness.json`.
3. Host the Web App over public HTTPS and register it through Meta AI app
   `App Connections > Web apps`.
4. Reconcile the VAI-018 native mobile simulation gate so command capture,
   display updates, networking, and pairing-state evidence are known before the
   physical run.
5. Record iPhone build state: SDK-unlinked fallback, SDK-linked native, or
   bridge-only.
6. Run one mobile ORB diagnostic baseline and preserve VAI-020 receipt fields
   before activating the native DAT display path.
7. Run the physical checklist in
   `docs/meta-wearables-dat-display-physical-validation-checklist.md`.
8. Complete a copy of
   `docs/meta-wearables-dat-display-rollout-evidence-template.md` for the run.
9. Decide one of: proceed with staged native DAT, hold native DAT and keep Web
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
- VAI-020 receipt integrity shows complete command routing, offload selection,
  permission, recovery, and fallback lineage for the same session keys used by
  the iPhone DAT payloads;
- glasses-visible status can be delivered through native DAT, Web App, or
  mobile-card fallback with the same task state and recovery reason;
- no private prompt/content captured in committed logs, screenshots, or metrics.

## Physical Validation Evidence Shape

The completed physical validation packet should contain:

- iPhone build metadata: app version, build identifier, release channel, iOS
  version, DAT SDK target, DAM state, `MWDATCore` linkage, and `MWDATDisplay`
  linkage.
- Hardware metadata: glasses model, firmware version, Meta AI app version,
  account/test cohort, pairing state, target selection state, and app update
  status.
- Local UI control proof: native or fallback payloads for render, update,
  focus, activate, clear, reset, video, and subscribe operations with matching
  simulator action order.
- Compute placement proof: local execution result or offloaded dispatch result
  with placement target, parent receipts, policy outcome, and recovery payload.
- Glasses status proof: display-widget state, spoken status, fallback reason,
  and recovery status visible through native DAT or the HTTPS Web App fallback.
- Rollback proof: a run with `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS=false`
  that still renders status on Web App or mobile-card fallback and preserves
  receipt integrity.

## Physical Evidence Status

Physical validation evidence has not been collected in this worktree. The next
operator with a DAT-capable iPhone/glasses setup should attach redacted run
artifacts to the release ticket or private artifact store and link the completed
evidence template from the rollout decision.
