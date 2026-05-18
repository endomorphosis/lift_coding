# Meta Wearables DAT Display Rollout Evidence Template

Complete this template for each staged rollout checkpoint.

## Run metadata

- Date:
- Owner:
- Branch/commit:
- App build identifier:
- Device model:
- OS / firmware version:
- DAT SDK target observed:

## Environment

- Backend URL:
- Auth mode:
- DAM enabled: (yes/no)
- Display mode config summary:
- Web app URL (if used):

## Readiness checks

- Webapp readiness linter result:
  - Command: `PYTHONPATH=./src python3 scripts/lint_display_webapp_readiness.py config/display_webapp_readiness.example.json`
  - Status: (pass/fail)
  - Notes:
- Diagnostics readiness flags:
  - `sdkMeetsMinimum`:
  - `datAppModelEnabled`:
  - `displayDamEnabled`:
  - `displayReady`:
  - `configWarnings`:

## Display lifecycle results

| Action | Result | Error/status code | Notes |
|---|---|---|---|
| `renderDisplayTest` |  |  |  |
| `clearDisplay` |  |  |  |
| `playDisplayVideo` |  |  |  |
| `resetDisplaySession` |  |  |  |

## Reliability observations

- Reconnect behavior:
- Session recovery behavior:
- Crash/timeout incidents:
- Fallback behavior on non-display path:

## Attached artifacts

- [ ] Diagnostics screenshots
- [ ] Action result payload logs
- [ ] Mobile/backend logs for failures (if any)
- [ ] Screen recording or operator notes
- [ ] Issue links (if defects found)

## Rollout decision

- Decision: (proceed / hold)
- Blocking issues:
- Mitigations:
- Next checkpoint date:

