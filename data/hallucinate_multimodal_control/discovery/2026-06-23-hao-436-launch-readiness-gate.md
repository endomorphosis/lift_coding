# HAO-436 Launch Readiness Gate

Task: HAO-436
Goal id: VAIOS-G697
Track: launch
Missing evidence closed: launch Playwright validation gate

This Hallucinate App packet mirrors the VAI-340 production gate so the
supervisor-fed backlog and objective heap point at the same explicit readiness
evidence. The gate is intentionally not satisfied by generic Playwright or AST
matches: it requires the Python guard plus the Swissknife and Hallucinate App
Playwright commands to prove the phone-hosted Swissknife virtual desktop,
desktop-peer offload, Hallucinate App mediation, and Meta glasses terminal path.

## LaunchReadinessGate

```json
{
  "schema": "launch_readiness_receipt_v1",
  "task_id": "HAO-436",
  "goal_id": "VAIOS-G697",
  "receipt_id": "launch-readiness-hao-436-phone-desktop-glasses",
  "vaios_receipt": "data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md",
  "readiness_doc": "docs/launch/phone_desktop_glasses_readiness.md",
  "requires_physical_devices": false,
  "physical_device_follow_up_required": false,
  "physical_readiness_requirements": [
    {
      "task_id": "HAO-437",
      "artifact_id": "real_phone_ingress_rehearsal_receipt",
      "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-437-phone-ingress-rehearsal.md",
      "required_for_launch_ready": true
    },
    {
      "task_id": "HAO-438",
      "artifact_id": "desktop_peer_offload_smoke_receipt",
      "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-438-desktop-peer-offload-smoke.md",
      "required_for_launch_ready": true
    },
    {
      "task_id": "HAO-439",
      "artifact_id": "meta_glasses_terminal_receipt",
      "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-23-hao-439-meta-glasses-terminal-receipt.md",
      "required_for_launch_ready": true
    }
  ],
  "python_gate": {
    "path": "tests/test_virtual_ai_os_launch_readiness_gate.py",
    "command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q"
  },
  "playwright_gates": [
    {
      "surface": "swissknife",
      "command": "npm --prefix swissknife run test:e2e:meta-glasses",
      "spec": "swissknife/test/e2e/meta-glasses-virtual-os.spec.ts",
      "covers": [
        "phone-hosted Swissknife virtual desktop",
        "desktop-peer offload",
        "Meta glasses terminal"
      ]
    },
    {
      "surface": "hallucinate_app",
      "command": "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts",
      "spec": "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts",
      "covers": [
        "Hallucinate App mediation",
        "remote-meta-glasses",
        "policy_decision",
        "mediation_receipt"
      ]
    }
  ],
  "product_critical_hops": [
    "phone-hosted Swissknife virtual desktop",
    "desktop-peer offload",
    "Hallucinate App mediation",
    "Meta glasses terminal"
  ],
  "playwright_lineage": {
    "lineage_id": "VAIOS-G697:launch-readiness:phone-desktop-glasses",
    "same_receipt_lineage": true,
    "required_gates": [
      "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q",
      "npm --prefix swissknife run test:e2e:meta-glasses",
      "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
    ]
  },
  "hardware_free_fallback": {
    "explicit": true,
    "physical_capture_unavailable_state": "gate_open_physical_capture_pending",
    "fallback_is_launch_ready": false
  },
  "blocking_rule": "VAIOS-G697 remains active until the launch Playwright validation gate passes for the same receipt lineage.",
  "split_policy": "No child goal is required unless physical phone, desktop peer, or Meta glasses capture needs separate evidence after this deterministic gate passes."
}
```

## Backlog Alignment

- Objective heap: `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`
- Readiness doc: `docs/launch/phone_desktop_glasses_readiness.md`
- VAI receipt: `data/virtual_ai_os/discovery/2026-06-23-vai-340-launch-readiness-gate.md`
- HAO gap source: `data/hallucinate_multimodal_control/discovery/2026-06-23-hao-436-objective-gap-3c1f2a790f3e.md`

## Validation

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q
npm --prefix swissknife run test:e2e:meta-glasses
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
