# VAI-339 Launch Replay Gate

Task: VAI-339
Track: launch
Depends on: VAI-010, VAI-011, VAI-023, VAI-338

This packet extends the deterministic hardware-free launch replay with one
shared evidence packet for the phone-hosted virtual desktop launch slice. It
does not replace the physical-device rehearsal gate; it proves the CI-safe
receipt shape that a physical phone, desktop peer, Swissknife operator surface,
Hallucinate App, and Meta glasses terminal must preserve.

## Deterministic Launch Replay Gate

```json
{
  "task_id": "VAI-339",
  "replay_id": "vai-339-launch-replay-gate",
  "requires_physical_devices": false,
  "command_contract": "vai.shared_capability_envelope@0.1.0",
  "single_evidence_packet": true,
  "join_keys": {
    "task_id": "VAI-339",
    "command_id": "cmd-vai339-open-monitor",
    "session_id": "vdsk-vai339-launch-session",
    "desktop_id": "desktop-vai339",
    "correlation_id": "corr-vai339-launch-replay",
    "request_id": "req-vai339-phone-origin",
    "widget_id": "virtual-ai-os-launch-replay",
    "widget_cid": "sha256:vai339-widget",
    "descriptor_cid": "sha256:vai339-descriptor",
    "manifest_cid": "sha256:vai339-manifest",
    "policy_cid": "sha256:vai339-policy",
    "capability_receipt_cid": "sha256:vai339-capability-receipt"
  },
  "covers": [
    "phone_originated_command",
    "hallucinate_app_mediation",
    "swissknife_presentation",
    "desktop_peer_or_phone_local_placement",
    "meta_glasses_terminal_contract",
    "shared_policy_placement_recovery_capability_receipts"
  ],
  "receipt_lineage": [
    "phone_event_receipt",
    "hallucinate_app_mediation_receipt",
    "policy_receipt_cid",
    "placement_receipt_cid",
    "desktop_peer_execution_receipt",
    "meta_glasses_render_receipt",
    "recovery_receipt_cid",
    "capability_receipt_cid"
  ],
  "participants": {
    "phone:operator": "originates the command with the shared envelope",
    "hallucinate_app:operator_console": "mediates policy and command intent before dispatch",
    "swissknife:ui": "shows the virtual desktop session and ORB descriptor",
    "desktop:peer": "receives the selected desktop-peer placement when policy allows it",
    "meta_glasses:terminal": "renders through the remote terminal display-widget contract"
  },
  "widget_capabilities": [
    "vai.glasses_widget.render",
    "vai.glasses_widget.update",
    "vai.glasses_widget.confirm",
    "vai.glasses_widget.cancel"
  ],
  "terminal_contract_id": "handsfree.meta-glasses/remote-terminal@0.1.0",
  "terminal_endpoints": [
    "meta_glasses_audio_input",
    "meta_glasses_audio_output",
    "meta_glasses_display_widget"
  ],
  "placement_policy": {
    "selected_runtime": "desktop_peer",
    "fallback_runtime": "phone_local",
    "placement_receipt_cid": "sha256:vai339-placement-peer",
    "recovery_receipt_cid": "sha256:vai339-recovery-phone-local"
  },
  "acceptance_assertions": [
    "the phone-originated command enters Hallucinate App mediation before desktop-peer dispatch",
    "Swissknife and Meta glasses consume the same descriptor_cid and manifest_cid",
    "desktop-peer placement and phone-local recovery are reconciled through parent receipt lineage",
    "render, update, confirm, and cancel actions reuse the VAI shared capability envelope and capability receipts"
  ]
}
```

## Validation

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_end_to_end_harness.py tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_meta_glasses_display_todo_queue.py -q
```
