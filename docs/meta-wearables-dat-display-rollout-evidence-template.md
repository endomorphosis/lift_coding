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
- VAI-023 handoff packet:
- DAT SDK target observed:
- iPhone DAT build state: (SDK-unlinked fallback / SDK-linked native / bridge-only)
- `MWDATCore` linked: (yes/no)
- `MWDATDisplay` linked: (yes/no)
- Expanded Meta glasses I/O run ID:
- Meta glasses I/O profile version:
- Meta glasses I/O launch readiness aggregate:
  `docs/meta-glasses-io-launch-readiness.md`
- Camera route tested: (native DAT / mock only / unavailable)
- Microphone route tested: (Bluetooth HFP / mock only / unavailable)
- Speaker/headphone route tested: (Bluetooth A2DP / mock only / unavailable)
- Meta Neural Band route tested: (display Web App / mock only / unavailable)
- Captouch route tested: (display Web App / mock only / unavailable)
- Motion/GPS route tested: (display Web App + phone OS / mock only / unavailable)

## Environment And Flags

- Backend URL:
- Auth mode:
- DAM enabled: (yes/no)
- Display mode config summary:
- Display Web App URL:
- Web App readiness descriptor URL:
- Simulator trace artifact:
- Handoff bundle reviewed: (yes/no/link)

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
- Expanded Meta glasses I/O readiness:
  - Camera permission prompt and capture path verified:
  - Microphone permission and Bluetooth route verified:
  - Speaker/headphone Bluetooth route verified:
  - Meta Neural Band input verified:
  - Captouch input verified:
  - Motion/orientation input verified:
  - Phone GPS permission/context verified:
  - Control plane receipt lineage verified:
  - IPFS content CIDs recorded for allowed payload refs:
  - libp2p peer/session IDs recorded when bridge provided them:
  - MCP++ receipts recorded for allow, fallback, denial, and error paths:

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

## Expanded Meta Glasses I/O Results

Record one row per capability. Do not paste raw camera frames, raw microphone
audio, private display content, precise GPS, or raw Meta Neural Band/captouch
telemetry into this template; use redacted content references and status codes.

| Capability | Route observed | Permission state | Control plane route | IPFS CID / payload ref | libp2p session | MCP++ receipt | Fallback/result | Notes |
|---|---|---|---|---|---|---|---|---|
| Camera photo capture |  |  |  |  |  |  |  |  |
| Camera video capture/stream |  |  |  |  |  |  |  |  |
| Microphone input |  |  |  |  |  |  |  |  |
| Speaker output |  |  |  |  |  |  |  |  |
| Headphone output |  |  |  |  |  |  |  |  |
| Display output |  |  |  |  |  |  |  |  |
| Meta Neural Band input |  |  |  |  |  |  |  |  |
| Captouch input |  |  |  |  |  |  |  |  |
| Motion/orientation |  |  |  |  |  |  |  |  |
| Phone GPS context |  |  |  |  |  |  |  |  |

## Control Plane And Conformance Snapshot

- Meta glasses I/O conformance command:
  - Command: `PYTHONPATH=./src pytest tests/test_meta_glasses_io_mcpplusplus_contract.py`
  - Status: (pass/fail/not run)
  - Notes:
- Swissknife MCP++ conformance command:
  - Command: `cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-conformance.test.ts --config=config/jest/jest.config.cjs --runInBand`
  - Status: (pass/fail/not run)
  - Notes:
- Swissknife Playwright command:
  - Command: `cd swissknife && npx playwright test test/e2e/meta-glasses-io-apps.spec.ts --config=playwright.config.ts`
  - Status: (pass/fail/not run)
  - Notes:
- Control-plane route decisions reviewed:
- IPFS/libp2p/MCP++ envelope boundary reviewed:
- `raw_transport_is_ipfs_libp2p_or_mcp=false` confirmed where applicable:
- Hardware-free fixture parity reviewed:

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
| Missing DAT credentials |  | Native DAT camera/display routes stay disabled; mock or bridge-only path continues with package or release-channel unavailable evidence. |  |  |
| Unsupported camera route |  | Structured unsupported response; no raw camera payload emitted; mobile-card or text fallback selected when allowed. |  |  |
| Camera permission denied |  | MCP++ policy-denial receipt; capture is not started and no IPFS camera CID is created. |  |  |
| Microphone permission denied |  | MCP++ policy-denial receipt; no raw microphone audio or transcript leaves the adapter. |  |  |
| Unavailable microphone route |  | `route_lost`, `route_unavailable`, or degraded route evidence; fallback avoids raw-audio leakage. |  |  |
| Unavailable speaker/headphone route |  | Playback route reports unavailable/degraded and falls back to phone, display text, mobile-card, or no-audio mode by policy. |  |  |
| Meta Neural Band unavailable |  | Display Web App or mock route reports unsupported/unavailable; app uses D-pad, mobile, or no-input fallback. |  |  |
| Captouch unavailable |  | Display Web App or mock route reports unsupported/unavailable; app uses D-pad, mobile, or no-input fallback. |  |  |
| Motion/orientation unavailable |  | Sensor route reports unsupported/unavailable or stale; app lowers sample rate or disables motion behavior. |  |  |
| Phone GPS permission denied |  | Location context is withheld; coarse/no-location fallback is used and denial receipt is recorded. |  |  |
| Unauthorized control-plane handoff |  | MCP++ policy-denial receipt; ORB/tool dispatch is blocked and replay key is preserved. |  |  |
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
- Camera route behavior:
- Microphone route behavior:
- Speaker/headphone route behavior:
- Meta Neural Band behavior:
- Captouch behavior:
- Motion/orientation and phone GPS behavior:
- Control plane / IPFS / libp2p / MCP++ behavior:

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
- [ ] Expanded Meta glasses I/O capability result table
- [ ] Meta glasses I/O control-plane route and MCP++ receipt snapshot
- [ ] IPFS/libp2p bridge envelope evidence, redacted
- [ ] Playwright and conformance command output
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
