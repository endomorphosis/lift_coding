# HAO-440 Launch Readiness Physical Aggregate

Task: HAO-440
Goal id: VAIOS-G697
Track: launch
Missing evidence closed: aggregate physical readiness receipt and Playwright lineage

This aggregate packet binds the HAO-437, HAO-438, and HAO-439 physical-readiness
receipts to the canonical `launch_readiness_receipt_v1` evidence. It prevents
VAIOS-G697 from becoming `launch_ready` unless the three dependency receipts are
present, every launch Playwright gate is listed in the same lineage, and the
hardware-free fallback remains explicit when physical capture is unavailable.

## Physical Readiness Aggregate Fixture

```json
{
  "schema": "launch_readiness_physical_evidence_aggregate_v1",
  "task_id": "HAO-440",
  "goal_id": "VAIOS-G697",
  "artifact_id": "launch_readiness_physical_evidence_aggregate",
  "launch_readiness_receipt": "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md",
  "required_physical_receipts": [
    {
      "task_id": "HAO-437",
      "artifact_id": "real_phone_ingress_rehearsal_receipt",
      "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-437-phone-ingress-rehearsal.md",
      "required_for_launch_ready": true,
      "proves": "physical phone ingress enters Hallucinate App as an interaction_envelope and fails closed when the phone adapter is absent"
    },
    {
      "task_id": "HAO-438",
      "artifact_id": "desktop_peer_offload_smoke_receipt",
      "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-438-desktop-peer-offload-smoke.md",
      "required_for_launch_ready": true,
      "proves": "desktop:peer selection records capability and runtime health, emits peer_offload_policy_receipt, and recovers to phone_local"
    },
    {
      "task_id": "HAO-439",
      "artifact_id": "meta_glasses_terminal_receipt",
      "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-439-meta-glasses-terminal-receipt.md",
      "required_for_launch_ready": true,
      "proves": "meta_glasses:terminal display_action and confirmation route through the HAO-431 bridge and fail closed on stale pairing or display evidence"
    }
  ],
  "playwright_lineage": {
    "lineage_id": "VAIOS-G697:launch-readiness:phone-desktop-glasses",
    "same_receipt_lineage": true,
    "required_gates": [
      {
        "surface": "python_static_receipt_gate",
        "command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q",
        "receipt_path": "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md"
      },
      {
        "surface": "swissknife_meta_glasses_playwright",
        "command": "npm --prefix swissknife run test:e2e:meta-glasses",
        "receipt_path": "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md"
      },
      {
        "surface": "hallucinate_app_multimodal_playwright",
        "command": "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts",
        "receipt_path": "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md"
      }
    ]
  },
  "hardware_free_fallback": {
    "explicit": true,
    "physical_capture_unavailable_state": "gate_open_physical_capture_pending",
    "fallback_is_launch_ready": false,
    "fallback_receipts": [
      "data/virtual_ai_os/discovery/2026-06-23-vai-010-hardware-free-e2e-harness.md",
      "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-430-hardware-free-offload-harness.md",
      "data/virtual_ai_os/discovery/2026-06-23-vai-339-launch-replay-gate.md"
    ]
  },
  "launch_ready_requires": [
    "HAO-437 real_phone_ingress_rehearsal_receipt present",
    "HAO-438 desktop_peer_offload_smoke_receipt present",
    "HAO-439 meta_glasses_terminal_receipt present",
    "all Playwright launch gates pass in VAIOS-G697:launch-readiness:phone-desktop-glasses",
    "hardware-free fallback remains explicit and non-launch-ready when physical capture is unavailable"
  ],
  "gate_state_before_requirements_pass": "open",
  "gate_state_after_requirements_pass": "launch_ready"
}
```

## Gate Effect

The aggregate is intentionally stricter than the hardware-free replay. The
fallback receipts remain useful for deterministic development and CI, but they
do not satisfy launch readiness on their own. If any HAO-437, HAO-438, or HAO-439
receipt is absent, VAIOS-G697 stays open with
`gate_open_physical_capture_pending`.
