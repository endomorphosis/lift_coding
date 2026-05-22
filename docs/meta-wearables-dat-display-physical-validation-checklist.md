# Meta Wearables DAT Display Physical Validation Checklist

Use this checklist to validate DAT display behavior on physical display-capable glasses before staged rollout.

## Scope

- Device class: display-capable glasses with DAT 0.7+ support
- App mode: DAT app-model (DAM) enabled
- Build type: development build with native DAT bridge enabled

## Preconditions

- [ ] Glasses firmware and companion app are updated
- [ ] Mobile app uses a build that includes `expo-meta-wearables-dat`
- [ ] Backend is reachable from device network
- [ ] `scripts/lint_display_webapp_readiness.py` passes for target web app metadata
- [ ] Default bridge-only Android build passes with `cd mobile/android && ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false` and no Meta package credentials
- [ ] Test account has required permissions for app onboarding and display access

## A) Connectivity + capability baseline

- [ ] Open Glasses Diagnostics and confirm bridge/module availability
- [ ] Confirm diagnostics report DAT SDK target >= `0.7.0`
- [ ] Confirm diagnostics surface DAM/display readiness flags as expected
- [ ] Confirm non-display devices still show safe fallback status (no silent failures)

Evidence:
- [ ] Screenshot: diagnostics capability panel
- [ ] Screenshot: readiness/config warnings panel

## B) Display lifecycle action validation

Run each action from the diagnostics/action surface and record result metadata.

- [ ] Android SDK-linked build reports `renderPath: native-dat` for native widget render
- [ ] Native render path records `displayLifecycleStages` for DisplayAccess stages: selected display target, session started, display attached, display started
- [ ] Bridge-only Android build returns `reason: dat_native_display_unavailable` and `renderPath: mobile-card` for widget actions
- [ ] Firmware update required state returns `reason: firmware_update_required` and `requiredAction: open_firmware_update`
- [ ] DAT glasses app update required state returns `reason: dat_app_update_required` and `requiredAction: open_dat_glasses_app_update`
- [ ] `renderDisplayTest` returns a structured success/unsupported response
- [ ] `renderDisplayWidget` renders a simple title/body widget and returns widget ID, manifest CID, render path, and display status
- [ ] `updateDisplayWidget` replaces the displayed content and increments update count
- [ ] `focusDisplayWidget` and `activateDisplayWidgetAction` return structured action metadata without crashing
- [ ] `resetDisplayWidgetSession` detaches/restarts cleanly before the next render
- [ ] `clearDisplay` returns a structured success/unsupported response
- [ ] `playDisplayVideo` returns a structured success/unsupported response
- [ ] `resetDisplaySession` returns a structured success/unsupported response
- [ ] Re-running actions is idempotent and does not crash app/bridge

Evidence:
- [ ] Screenshot or log excerpt per action result
- [ ] Android log excerpt showing session start, display attach, display ready, and send result
- [ ] Note any error/status code and message payloads

## C) UX and reliability checks

- [ ] Display content is legible at expected brightness/contrast
- [ ] Navigation controls (D-pad/focus model for linked web app) are usable
- [ ] Session reset recovers from failed/interrupted render attempts
- [ ] At least one reconnect cycle preserves stable diagnostics state
- [ ] No app crash, native exception, or repeated bridge timeout during test window

Evidence:
- [ ] 3-5 minute screen recording or timestamped notes of lifecycle run
- [ ] Captured backend/mobile logs for failed attempts (if any)

## D) Rollout readiness decision

- [ ] Blocking issues: none, or all tracked with mitigations
- [ ] Known limitations documented for operator/tester runbook
- [ ] Staged rollout evidence template completed for this run

Result:
- [ ] PASS for staged rollout gate
- [ ] FAIL (requires fixes/retest)
