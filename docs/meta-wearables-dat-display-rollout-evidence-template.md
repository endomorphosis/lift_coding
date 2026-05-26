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
- iPhone model:
- iOS version:
- Glasses model:
- Glasses firmware version:
- Meta AI app version:
- Meta AI app Web App URL registered: (yes/no/link)
- DAT SDK target observed:
- iPhone DAT build state: (SDK-unlinked fallback / SDK-linked native / bridge-only)
- `MWDATCore` linked: (yes/no)
- `MWDATDisplay` linked: (yes/no)

## Environment And Flags

- Backend URL:
- Auth mode:
- DAM enabled: (yes/no)
- Display mode config summary:
- Display Web App URL:
- Web App readiness descriptor URL:
- Simulator trace artifact:

| Flag | Value | Evidence source |
|---|---|---|
| `HANDSFREE_DISPLAY_WIDGETS_ENABLED` |  |  |
| `HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR` |  |  |
| `HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK` |  |  |
| `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID` |  |  |
| `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS` |  |  |

Rollback command or config change:

- Backend:
- iPhone native DAT:
- Mobile release channel/build:
- Meta AI app Web App fallback:
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
  - `displaySdkLinked`:
  - `displayReady`:
  - `displayConnectionState`:
  - `displayLifecycleStages`:
  - `configWarnings`:
- Physical iPhone/Meta AI app readiness:
  - Glasses paired and connected:
  - Firmware update prompt absent:
  - Meta AI app Web App launch succeeds:
  - iPhone Bluetooth audio route verified:

## Simulator Trace Parity

Capture the desktop simulator export before the real iPhone run, then compare the iPhone DAT result payloads against it.

| Field / event | Simulator expected | iPhone observed | Pass/fail | Notes |
|---|---|---|---|---|
| Fixture name |  |  |  |  |
| `widget_id` |  |  |  |  |
| `widget_cid` |  |  |  |  |
| `descriptor_cid` |  |  |  |  |
| `orb_receipt_cid` |  |  |  |  |
| `correlation_id` |  |  |  |  |
| Focus order | `pause -> dismiss` or fixture-specific order |  |  |  |
| Activate action ID |  |  |  |  |
| Operation sequence | display state -> focus -> activate -> update/clear/reset |  |  |  |
| Fallback reason sample | `dat_native_display_unavailable` / `firmware_update_required` / `dat_app_update_required` / `display_lifecycle_error` |  |  |  |

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

## iPhone Native DAT Result Payloads

| Payload field | `renderDisplayWidget` | `updateDisplayWidget` | focus/activate | clear/reset |
|---|---|---|---|---|
| `supported` |  |  |  |  |
| `renderPath` |  |  |  |  |
| `reason` |  |  |  |  |
| `requiredAction` |  |  |  |  |
| `displayConnectionState` |  |  |  |  |
| `displayRenderPath` |  |  |  |  |
| `displayLastError` |  |  |  |  |
| `displayLifecycleStages` |  |  |  |  |
| DisplayAccess target selected |  |  |  |  |
| DisplayAccess session started |  |  |  |  |
| DisplayAccess display attached |  |  |  |  |
| DisplayAccess display started |  |  |  |  |
| DisplayAccess content sent |  |  |  |  |

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
| DAT SDK unlinked on iPhone |  | `reason: dat_sdk_unlinked`, `renderPath: mobile-card`, native iPhone DAT flag remains off. |  |  |
| `MWDATDisplay` unlinked on iPhone |  | `reason: display_sdk_unlinked`, `displaySdkLinked: false`, Web App fallback remains usable. |  |  |
| DAM disabled |  | `reason: dam_disabled`; native iPhone DAT rollout holds until metadata is fixed. |  |  |
| SDK target below `0.7.0` |  | `reason: sdk_version_unsupported`; rollout holds. |  |  |
| Firmware update required |  | `reason: firmware_update_required`; operator updates glasses firmware in Meta AI app before retest. |  |  |
| Meta AI app or glasses DAT app update required |  | `reason: dat_app_update_required`; app update path is visible before retest. |  |  |
| DisplayAccess lifecycle timeout/error |  | Reset session once; repeated failure triggers rollback to Web App/mobile-card. |  |  |
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
- iPhone simulator trace parity:
- iPhone DisplayAccess lifecycle completeness:
- Firmware / Meta AI app update behavior:
- Native DAT Android behavior:
- Native DAT iOS behavior:

## Rollback Validation

| Rollback path | Switch/change | Validation evidence | Result |
|---|---|---|---|
| Hold iPhone native DAT | `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS=false` |  |  |
| Stop display widget emission | `HANDSFREE_DISPLAY_WIDGETS_ENABLED=false` |  |  |
| Preserve Web App fallback | `HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK=true` |  |  |
| Mobile build/channel rollback | Last bridge-only iPhone build/channel |  |  |
| Physical display fallback | Meta AI app Web App or mobile-card path |  |  |

## Attached Artifacts

- [ ] Diagnostics screenshots with private content redacted
- [ ] Simulator trace export and parity notes
- [ ] Hosted Web App `readiness.json` and linter output
- [ ] iPhone build metadata, DAT SDK target, and `MWDATDisplay` linkage note
- [ ] Glasses firmware and Meta AI app version screenshot/note
- [ ] DisplayAccess lifecycle log excerpt
- [ ] Action result payload logs
- [ ] `/v1/metrics` snapshots
- [ ] Backend config snapshot
- [ ] Mobile/backend logs for failures, status codes only where possible
- [ ] Screen recording or operator notes
- [ ] Rollback validation screenshots/logs
- [ ] Issue links if defects were found

## Rollout Decision

- Decision: (proceed / hold / rollback)
- Blocking issues:
- Mitigations:
- Rollback completed: (yes/no/not needed)
- Next checkpoint date:
