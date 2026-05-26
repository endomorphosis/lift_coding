# Meta Wearables DAT Display Physical Validation Checklist

Use this checklist to validate DAT display behavior on physical display-capable glasses before staged rollout.

## Scope

- Device class: display-capable glasses with DAT 0.7+ support
- App mode: DAT app-model (DAM) enabled
- Build type: iPhone development build with native DAT bridge enabled, plus a bridge-only fallback build or channel
- Operator surface: desktop operator console plus mobile diagnostics for remote display rollback and degraded-mode review
- Fallback surface: hosted Display Web App registered in the Meta AI app and phone/mobile-card rendering

## Preconditions

- [ ] Physical iPhone is on the target iOS version and paired to the test glasses
- [ ] Meta AI app is installed, signed in with the test account, and can open `App Connections > Web apps`
- [ ] Glasses firmware and Meta AI app are updated with no pending device/app update prompts
- [ ] Mobile app uses a build that includes `expo-meta-wearables-dat`
- [ ] iPhone native DAT build state is known: SDK-unlinked fallback build or SDK-linked build with `MWDATCore` and `MWDATDisplay`
- [ ] Backend is reachable from device network
- [ ] `scripts/lint_display_webapp_readiness.py` passes for target web app metadata
- [ ] Hosted Display Web App loads over publicly available HTTPS and is added in the Meta AI app
- [ ] `dev/meta-rayban-display-simulator` trace is exported for the same widget/action fixture used on device
- [ ] Default bridge-only Android build passes with `cd mobile/android && ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false` and no Meta package credentials
- [ ] Test account has required permissions for app onboarding and display access

## A) Simulator Trace Parity Gate

- [ ] Simulator fixture name is recorded
- [ ] Exported simulator trace includes `display_state`, `focus`, and `activate`
- [ ] Simulator `widget_id`, `widget_cid`, `descriptor_cid`, `orb_receipt_cid`, and `correlation_id` are recorded when present
- [ ] Simulator focus order matches the Web App readiness descriptor focus order
- [ ] Simulator fallback states are sampled for `dat_native_display_unavailable`, `firmware_update_required`, `dat_app_update_required`, and `display_lifecycle_error`
- [ ] iPhone physical run uses the same manifest, action IDs, operation order, and correlation ID family

Evidence:
- [ ] `meta-rayban-display-simulator-trace.json`
- [ ] Hosted `readiness.json` URL and linter result
- [ ] Screenshot or note showing fixture and display state used for parity

## B) Connectivity + Capability Baseline

- [ ] Open Glasses Diagnostics and confirm bridge/module availability
- [ ] Confirm diagnostics report `platform: ios` for the iPhone run
- [ ] Confirm diagnostics report DAT SDK target >= `0.7.0`
- [ ] Confirm diagnostics report `displaySdkLinked` for the exact iPhone build under test
- [ ] Confirm diagnostics surface DAM/display readiness flags as expected
- [ ] Confirm Meta AI app shows glasses connected and no firmware/app update prompt
- [ ] Confirm hosted Web App fallback launches on glasses through `App Connections > Web apps`
- [ ] Confirm non-display devices still show safe fallback status (no silent failures)

Evidence:
- [ ] Screenshot: diagnostics capability panel
- [ ] Screenshot: readiness/config warnings panel
- [ ] Screenshot: Meta AI app device/app version or update state
- [ ] Screenshot or note: Web App fallback launch

## C) Display Lifecycle Action Validation

Run each action from the diagnostics/action surface and record result metadata.

- [ ] Android SDK-linked build reports `renderPath: native-dat` for native widget render
- [ ] iOS SDK-unlinked build returns explicit `reason: dat_sdk_unlinked` or `reason: display_sdk_unlinked`, `renderPath: mobile-card`, and `displayConnectionState` matching the blocked SDK state for widget actions
- [ ] iOS SDK-linked build with `MWDATDisplay` available reports `displaySdkLinked: true`, `renderPath: native-dat`, and DisplayAccess lifecycle stages before rollout
- [ ] Native render path records `displayLifecycleStages` for DisplayAccess stages: selected display target, session started, display attached, display started, and content sent
- [ ] iPhone native results preserve simulator trace parity for widget/action IDs, operation order, focus target, and correlation metadata
- [ ] Bridge-only Android build returns `reason: dat_native_display_unavailable` and `renderPath: mobile-card` for widget actions
- [ ] Firmware update required state returns `reason: firmware_update_required` and `requiredAction: open_firmware_update`
- [ ] DAT glasses app update required state returns `reason: dat_app_update_required` and `requiredAction: open_dat_glasses_app_update`
- [ ] `renderDisplayTest` returns a structured success/unsupported response
- [ ] `renderDisplayWidget` renders a simple title/body widget and returns widget ID, manifest CID, render path, and display status
- [ ] `renderDisplayWidget` renders compiled manifest text/status/progress regions in the expected visual order for the 600x600 viewport
- [ ] Action regions render as DAT buttons in manifest `focus_order`, and button activation emits action metadata without crashing the app
- [ ] Image media with HTTPS URLs renders natively; CID/IPFS/unsupported image media records a `displayFallback.mediaFallbacks` entry and shows fallback text
- [ ] Video media inside a manifest region is not nested inside a `flexBox`; native render records a video fallback and keeps the rest of the widget visible
- [ ] `playDisplayWidgetVideo` sends HTTPS MP4 content only as a root DAT video view, or records a video fallback for IPFS/CID/missing player cases
- [ ] `updateDisplayWidget` replaces the displayed content and increments update count
- [ ] `focusDisplayWidget` and `activateDisplayWidgetAction` return structured action metadata without crashing
- [ ] `resetDisplayWidgetSession` detaches/restarts cleanly before the next render
- [ ] `clearDisplay` returns a structured success/unsupported response
- [ ] `playDisplayVideo` returns a structured success/unsupported response
- [ ] `resetDisplaySession` returns a structured success/unsupported response
- [ ] Re-running actions is idempotent and does not crash app/bridge

Evidence:
- [ ] Screenshot or log excerpt per action result
- [ ] iPhone log excerpt showing DisplayAccess target selection, session start, display attach/start, and send result
- [ ] Android log excerpt showing session start, display attach, display ready, and send result
- [ ] Note any error/status code and message payloads

## D) Native DAT Fallback Criteria

Native iPhone DAT display is not rollout-ready if any blocked state silently succeeds, returns an unstructured error, or fails to preserve a working Web App/mobile-card fallback.

| Gate | Expected fallback evidence | Rollout decision |
|---|---|---|
| DAT SDK unlinked | `reason: dat_sdk_unlinked`, `renderPath: mobile-card`, `supported: false` | Keep `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS=false`. |
| `MWDATDisplay` unlinked | `reason: display_sdk_unlinked`, `displaySdkLinked: false` | Keep native iPhone DAT off and use browser Web App fallback. |
| DAM disabled | `reason: dam_disabled`, `displayReady: false` | Rebuild app metadata before retest. |
| DAT SDK target below `0.7.0` | `reason: sdk_version_unsupported` | Block native rollout until SDK target is updated. |
| No selected display target | `reason: target_required` or `display_capability_missing` | Reconnect/select glasses before retest; use mobile-card if unresolved. |
| Firmware update required | `reason: firmware_update_required` and operator-visible firmware update action | Update glasses firmware in Meta AI app before retest. |
| Meta AI app or glasses DAT app update required | `reason: dat_app_update_required` and operator-visible app update action | Update Meta AI app/glasses app path before retest. |
| DisplayAccess lifecycle error or timeout | `reason: display_lifecycle_error` or lifecycle timeout status | Reset session once; rollback if repeated in the same run. |
| Unsupported image/video/CID media | `displayFallback.mediaFallbacks` or equivalent fallback metadata | Accept only if text/action regions stay visible and evidence records degraded media. |

## E) Rollback Validation

- [ ] Set or confirm `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS=false` and verify iPhone no longer reports `renderPath: native-dat`
- [ ] Keep `HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK=true` and verify the hosted Web App still opens from the Meta AI app
- [ ] If display actions must stop entirely, set `HANDSFREE_DISPLAY_WIDGETS_ENABLED=false` and verify no new mobile display widget action is emitted
- [ ] Move the iPhone test cohort back to the last bridge-only/mobile-card build or release channel if native SDK linkage is unstable
- [ ] Repeat one command after rollback and capture diagnostics showing `mobile-card` or `display-webapp`
- [ ] Record rollback flag values, build/channel, and validation output in the evidence template

## F) UX And Reliability Checks

- [ ] Display content is legible at expected brightness/contrast
- [ ] Navigation controls (D-pad/focus model for linked web app) are usable
- [ ] Session reset recovers from failed/interrupted render attempts
- [ ] At least one reconnect cycle preserves stable diagnostics state
- [ ] No app crash, native exception, or repeated bridge timeout during test window
- [ ] Desktop operator workflow can explain the current display state, fallback reason, and recommended rollback step without requiring device logs
- [ ] Degraded-mode handling is explicit: unsupported/blocked/native-unavailable states surface `renderPath`, `reason`, and `requiredAction` values that testers can record
- [ ] iPhone physical run and simulator trace remain explainably equivalent when native DAT succeeds or falls back

Evidence:
- [ ] 3-5 minute screen recording or timestamped notes of lifecycle run
- [ ] Captured backend/mobile logs for failed attempts (if any)
- [ ] Operator-console screenshot or notes showing desktop visibility into the same display/session state

## G) Rollout Readiness Decision

- [ ] Blocking issues: none, or all tracked with mitigations
- [ ] Known limitations documented for operator/tester runbook
- [ ] Staged rollout evidence template completed for this run
- [ ] Rollback decision for native DAT display enablement is documented (ship native DAT, stay bridge-only, or keep mobile-card fallback)
- [ ] Evidence includes simulator trace parity, iPhone diagnostics, firmware/Meta AI app versions, DisplayAccess lifecycle, fallback criteria, and rollback validation

Result:
- [ ] PASS for staged rollout gate
- [ ] FAIL (requires fixes/retest)
