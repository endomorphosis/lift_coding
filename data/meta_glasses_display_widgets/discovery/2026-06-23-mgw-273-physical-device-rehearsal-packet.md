# MGW-273 Physical-Device Rehearsal Packet

Scope: rehearse the first physical phone plus Meta glasses session for the phone-hosted virtual desktop. This packet depends on the MGW-271 launch-readiness checklist and the MGW-272 shared VAI receipt binding; it does not create a second widget command contract.

## Start Gate

Do not start hardware validation until these simulator replay artifacts match:

- Fixture: `data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-267-phone-glasses-terminal-fixture.json`
- `schema_version: "1.2.0"`
- `launch_replay_evidence.replay_id: "launch-session-widget-replay-mgw-272"`
- `launch_replay_evidence.extends_replay_id: "launch-session-widget-replay-mgw-270"`
- `launch_replay_evidence.render_contract: "handsfree.virtual-desktop-session"`
- `launch_replay_evidence.terminal_contract: "handsfree.meta-glasses/remote-terminal@0.1.0"`
- `launch_replay_evidence.command_contract: "vai.shared_capability_envelope@0.1.0"`
- `launch_replay_evidence.no_second_widget_command_contract: true`
- `launch_replay_evidence.single_replay: true`

The physical-device rehearsal must preserve the replay event order:

1. `virtual_desktop_status`
2. `confirmation_prompt`
3. `peer_offload_update`

## Pairing Prerequisites

- Phone host is the session authority for `session_identity`, policy decisions, command routing, recovery state, and receipt storage.
- Physical Meta glasses are charged, discoverable, updated, and paired through the phone host before widget validation starts.
- Pairing must reach `pairing.status: paired` and then `pairing.status: display_ready`.
- The physical paired device ID must be written to `render_context.paired_device_id` and included in manual evidence.
- Recovery actions must be visible and bounded before the run: `retry_pairing`, `reset_display_session`, `open_phone_preview`, and `open_mobile_card`.
- Pairing failures must render `pairing_lost`, `display_unavailable`, `requires_update`, or `receipt_missing` recovery states instead of continuing silently.

## DAT/Web App Fallback Choice

Primary rehearsal path:

- Use DAT native display only when the phone reports the DAT display adapter, display capability, and firmware path are available.

Required fallback path:

- Use `display_webapp` when DAT native display is unavailable, unstable, or firmware-blocked.
- Keep `mobile-card` as the operator recovery surface for phone-hosted inspection.
- Keep `simulator` as the deterministic contract baseline.

The fallback run must preserve the same pairing badge, active tool label, confirmation prompt, desktop peer offload state, correlation IDs, and receipt IDs. A fallback mismatch blocks physical Meta glasses validation until it is explained in the manual notes.

## Expected Widget States

The first physical-device rehearsal must capture these states before any hardware-only exploratory checks:

| Replay event | Required physical state | Required receipts |
| --- | --- | --- |
| `virtual_desktop_status` | Phone-hosted desktop is running on `phone_local`; Meta glasses show the status region, active tool, pairing badge, progress/message regions, and fallback actions. | `bafy-mgw272-vai-render-receipt`, `ha-mgw270-render-receipt`, `bafy-mgw267-policy`, `bafy-mgw267-orb-status`, `bafy-mgw267-placement-phone`, `bafy-mgw272-recovery-preview` |
| `confirmation_prompt` | Confirmation prompt preserves continue/cancel/retry focus order and backend-approved `terminal.*` action IDs. | `bafy-mgw272-vai-confirm-receipt`, `ha-mgw270-confirm-receipt`, `bafy-mgw267-policy`, `bafy-mgw267-orb-confirm`, `bafy-mgw267-placement-phone`, `bafy-mgw272-recovery-preview` |
| `peer_offload_update` | Desktop peer transfer shows `desktop_peer` placement, selected peer label, transfer phase/progress, and cancel/retry/fallback actions. | `bafy-mgw272-vai-update-receipt`, `ha-mgw270-offload-receipt`, `bafy-mgw267-policy`, `bafy-mgw267-orb-offload`, `bafy-mgw267-placement-peer`, `bafy-mgw272-recovery-preview` |

The shared VAI cancel receipt `bafy-mgw272-vai-cancel-receipt` must be available for cancel actions even if the manual rehearsal does not activate a destructive cancel path.

## Manual Evidence To Capture

- Date/time, operator, phone model, phone OS, app build, Meta glasses model, Meta glasses firmware, network type, and battery state at start and end.
- Pairing transcript: discovery time, `pairing.status` transitions, `render_context.paired_device_id`, reconnect behavior, and any `requires_update` or `display_unavailable` state.
- DAT/Web App fallback decision: DAT capability result, chosen path, reason, and whether the `display_webapp`, `mobile-card`, and `simulator` views show the same widget state.
- Visual evidence: screenshot or short video for `virtual_desktop_status`, `confirmation_prompt`, `peer_offload_update`, and fallback rendering.
- Input evidence: glasses captouch, voice, Neural Band if available, and phone relay latency for confirm, cancel, retry, offload cancel, offload retry, and fallback-to-phone actions.
- Receipt evidence: correlation ID, policy receipt, VAI capability receipt, ORB receipt, bridge receipt, Hallucinate App mediation receipt, placement receipt, transfer receipt when present, and fallback receipt when present.
- Hardware notes: optical legibility, brightness comfort, notification interruption, phone backgrounding behavior, battery drain, thermal behavior, and any DAT native-display firmware issue.

## Exact Replay Artifacts That Must Match

The physical phone plus Meta glasses rehearsal must match these simulator replay values before hardware validation starts:

- Correlation IDs: `corr-mgw-267-status`, `corr-mgw-267-confirm`, `corr-mgw-267-offload`
- Hallucinate App receipt IDs: `ha-mgw270-render-receipt`, `ha-mgw270-confirm-receipt`, `ha-mgw270-offload-receipt`
- Shared VAI capability receipts: `bafy-mgw272-vai-render-receipt`, `bafy-mgw272-vai-confirm-receipt`, `bafy-mgw272-vai-update-receipt`, `bafy-mgw272-vai-cancel-receipt`
- Policy receipt: `bafy-mgw267-policy`
- ORB receipts: `bafy-mgw267-orb-status`, `bafy-mgw267-orb-confirm`, `bafy-mgw267-orb-offload`
- Placement receipts: `bafy-mgw267-placement-phone`, `bafy-mgw267-placement-peer`
- Recovery receipt: `bafy-mgw272-recovery-preview`
- Render and fallback paths from the replay baseline: `render_path: "mobile-card"` and `fallback_path: "display-webapp"` for simulator proof; physical DAT may replace the primary render path only after these baseline values are captured.

Signoff rule: the first physical-device rehearsal is ready for hardware validation only when pairing, DAT/Web App fallback choice, expected widget states, manual evidence, and receipt matching are complete. Any missing receipt, reordered event, unrecorded fallback decision, or unexplained mismatch is a launch blocker for physical Meta glasses validation.
