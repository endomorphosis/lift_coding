# Meta Wearables DAT Display Rollout Evidence Template

Complete this template for each staged rollout checkpoint. Store the completed copy with the release artifacts or link it from the release ticket; do not commit device screenshots or logs that contain private user content.

## Run Metadata

- Date:
- Owner:
- Rollout stage: (internal / test organization / production canary / production)
- Branch/commit:
- Backend deploy identifier:
- App build identifier:
- Release channel:
- Device model:
- OS / firmware version:
- DAT SDK target observed:

## Environment And Flags

- Backend URL:
- Auth mode:
- DAM enabled: (yes/no)
- Display mode config summary:
- Web app URL (if used):

| Flag | Value | Evidence source |
|---|---|---|
| `HANDSFREE_DISPLAY_WIDGETS_ENABLED` |  |  |
| `HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR` |  |  |
| `HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK` |  |  |
| `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID` |  |  |
| `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS` |  |  |

Rollback command or config change:

- Backend:
- Mobile release channel:
- Expected rollback validation:

## Readiness Checks

- Webapp readiness linter result:
  - Command: `PYTHONPATH=./src python3 scripts/lint_display_webapp_readiness.py config/display_webapp_readiness.example.json`
  - Status: (pass/fail)
  - Notes:
- Backend config validation:
  - Command: `PYTHONPATH=./src pytest tests/test_meta_glasses_display_config.py`
  - Status: (pass/fail)
  - Notes:
- Diagnostics readiness flags:
  - `sdkMeetsMinimum`:
  - `datAppModelEnabled`:
  - `displayDamEnabled`:
  - `displayReady`:
  - `configWarnings`:

## Display Lifecycle Results

| Action | Result | Error/status code | Latency ms | Notes |
|---|---|---|---:|---|
| `renderDisplayTest` |  |  |  |  |
| `render_widget` |  |  |  |  |
| `update_widget` |  |  |  |  |
| `focus_next` |  |  |  |  |
| `activate` |  |  |  |  |
| `clear_widget` |  |  |  |  |
| `reset_session` |  |  |  |  |
| `clearDisplay` |  |  |  |  |
| `playDisplayVideo` |  |  |  |  |
| `resetDisplaySession` |  |  |  |  |

## Observability Snapshot

Capture the `/v1/metrics` display widget section before and after the checkpoint.

| Metric | Before | After | Threshold / decision rule | Notes |
|---|---:|---:|---|---|
| `handsfree_display_widget_render_success_total` |  |  | Render succeeds on every required physical test. |  |
| `handsfree_display_widget_policy_denial_total` |  |  | Expected denials only; unexpected increase blocks rollout. |  |
| `handsfree_display_widget_bridge_error_total` |  |  | Any repeated bridge error blocks production rollout. |  |
| `handsfree_display_widget_render_latency_ms.p50` |  |  | Record observed p50. |  |
| `handsfree_display_widget_render_latency_ms.p95` |  |  | p95 must be acceptable for glanceable UI. |  |

## Failure-Mode Review

| Failure mode | Evidence captured | Expected behavior | Pass/fail | Issue link |
|---|---|---|---|---|
| Unsupported glasses |  | Structured unavailable response and phone/webapp fallback when allowed. |  |  |
| Stale display session |  | Session reset is offered and no stale widget remains visible. |  |  |
| Missing release-channel access |  | Operator sees actionable diagnostics; backend rollback remains available. |  |  |
| Missing DAT packages |  | Bridge-only build continues; native path stays disabled. |  |  |
| Descriptor validation failure |  | Widget action is denied before render and denial is observable. |  |  |
| Policy denial |  | No render action is emitted when trusted descriptors are required. |  |  |
| Bridge error |  | Error is counted and payload/logs contain a non-private status code. |  |  |
| Latency budget exceeded |  | Rollout holds or falls back to phone/webapp path. |  |  |

## Privacy Review Notes

- Descriptor provenance reviewed:
- User prompt or task content shown on display:
- Display content retention policy:
- Analytics opt-out behavior:
- Screenshot or video redaction completed:
- Logs checked for descriptor CID, widget CID, ORB receipt CID, and policy decision only; no raw private prompt/content retained beyond policy:

## Reliability Observations

- Reconnect behavior:
- Session recovery behavior:
- Crash/timeout incidents:
- Fallback behavior on non-display path:
- Native DAT Android behavior:
- Native DAT iOS behavior:

## Attached Artifacts

- [ ] Diagnostics screenshots with private content redacted
- [ ] Action result payload logs
- [ ] `/v1/metrics` snapshots
- [ ] Backend config snapshot
- [ ] Mobile/backend logs for failures, status codes only where possible
- [ ] Screen recording or operator notes
- [ ] Issue links if defects were found

## Rollout Decision

- Decision: (proceed / hold / rollback)
- Blocking issues:
- Mitigations:
- Rollback completed: (yes/no/not needed)
- Next checkpoint date:
