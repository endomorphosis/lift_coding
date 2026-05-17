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

- [ ] `renderDisplayTest` returns a structured success/unsupported response
- [ ] `clearDisplay` returns a structured success/unsupported response
- [ ] `playDisplayVideo` returns a structured success/unsupported response
- [ ] `resetDisplaySession` returns a structured success/unsupported response
- [ ] Re-running actions is idempotent and does not crash app/bridge

Evidence:
- [ ] Screenshot or log excerpt per action result
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

