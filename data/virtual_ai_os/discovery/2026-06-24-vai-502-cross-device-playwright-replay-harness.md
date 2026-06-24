# VAI-502 Cross-Device Virtual Desktop Playwright Replay Harness

Task: VAI-502
Priority: P0
Track: validation
Depends on: VAI-501

This specifies a hardware-free Playwright replay path for the supervisor launch
receipt. The replay launches the Swissknife virtual desktop, sends a mediated
control plane command through Hallucinate App, simulates phone-hosted execution,
tries desktop peer offload, falls back to phone-local execution, and records
Meta glasses status output with stable proof artifacts.

## Replay Harness Receipt

```json
{
  "schema": "cross_device_virtual_desktop_playwright_replay_receipt_v1",
  "task_id": "VAI-502",
  "lineage_id": "VAIOS-G697:launch-readiness:phone-desktop-glasses",
  "requires_hardware": false,
  "validation_commands": [
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_playwright_replay_harness.py",
    "npm --prefix swissknife run test:e2e:meta-glasses -- --grep @vai-502",
    "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts --grep @vai-502"
  ],
  "launch_path": {
    "surface": "Swissknife virtual desktop",
    "playwright_fixture": "swissknife/test/e2e/fixtures/vai-502-cross-device-playwright-replay.json",
    "ready_selector": ".desktop",
    "proof_artifact": "test-results/vai-502/swissknife-virtual-desktop.png"
  },
  "control_plane": {
    "mediator": "Hallucinate App mediation",
    "command": "desktop.request_handoff",
    "mediation_fixture": "hallucinate_app/test/e2e/fixtures/vai-502-control-plane-mediation.json",
    "policy_receipt_id": "sha256:vai502-policy-receipt",
    "mediation_receipt_id": "sha256:vai502-mediation-receipt"
  },
  "phone_execution": {
    "mode": "phone-hosted",
    "participant_id": "phone:operator-simulator",
    "command_receipt_id": "sha256:vai502-phone-command-receipt"
  },
  "desktop_peer_offload": {
    "selected_peer": "desktop peer:simulated-workstation",
    "first_attempt": {
      "placement": "desktop_peer",
      "status": "timeout",
      "receipt_id": "sha256:vai502-desktop-peer-timeout"
    },
    "fallback": {
      "placement": "phone_local",
      "status": "completed",
      "receipt_id": "sha256:vai502-phone-fallback-receipt"
    }
  },
  "meta_glasses_status_output": {
    "participant_id": "meta_glasses:terminal",
    "status_text": "Meta glasses status: control plane mediated; desktop peer timeout; phone-hosted fallback active.",
    "render_receipt_id": "sha256:vai502-meta-glasses-render-receipt",
    "proof_artifact": "test-results/vai-502/meta-glasses-status.json"
  },
  "proof_artifacts": [
    "swissknife/test/e2e/fixtures/vai-502-cross-device-playwright-replay.json",
    "hallucinate_app/test/e2e/fixtures/vai-502-control-plane-mediation.json",
    "test-results/vai-502/swissknife-virtual-desktop.png",
    "test-results/vai-502/control-plane-ledger.json",
    "test-results/vai-502/meta-glasses-status.json"
  ],
  "supervisor_launch_receipt_terms": [
    "VAI-502",
    "Playwright",
    "phone-hosted",
    "desktop peer",
    "Meta glasses",
    "control plane"
  ]
}
```

## Notes

The Playwright replay remains hardware-free by using deterministic participants:
`phone:operator-simulator`, `desktop peer:simulated-workstation`, and
`meta_glasses:terminal`. Physical phone, desktop peer, and Meta glasses runs can
reuse the same receipt IDs as parent evidence but are not required for this
validation harness.
