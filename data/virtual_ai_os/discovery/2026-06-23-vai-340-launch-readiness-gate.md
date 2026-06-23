# VAI-340 Launch Readiness Gate

Task: VAI-340
Goal id: VAIOS-G697
Track: launch
Missing evidence closed: launch Playwright validation gate

This packet turns the VAIOS-G697 production launch readiness objective into a
single explicit receipt contract. Scanner hits against generic Playwright or
receipt terms are not enough: the launch gate is open only when the fast Python
guard, the Swissknife Meta glasses Playwright gate, and the Hallucinate App
multimodal control-surface Playwright gate are all wired to the same product
slice.

Mission coverage: phone-hosted Swissknife virtual desktop, desktop-peer offload,
Hallucinate App mediation, and Meta glasses terminal.

## LaunchReadinessGate

```json
{
  "schema": "launch_readiness_receipt_v1",
  "task_id": "VAI-340",
  "goal_id": "VAIOS-G697",
  "receipt_id": "launch-readiness-vai-340-phone-desktop-glasses",
  "requires_physical_devices": false,
  "physical_device_follow_up_required": false,
  "physical_readiness_requirements": [
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
  "command_contract": "vai.shared_capability_envelope@0.1.0",
  "readiness_doc": "docs/launch/phone_desktop_glasses_readiness.md",
  "python_gate": {
    "path": "tests/test_virtual_ai_os_launch_readiness_gate.py",
    "command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q"
  },
  "playwright_gates": [
    {
      "surface": "swissknife",
      "command": "npm --prefix swissknife run test:e2e:meta-glasses",
      "package_script": "test:e2e:meta-glasses",
      "config": "swissknife/build-tools/configs/playwright.meta-glasses.config.ts",
      "spec": "swissknife/test/e2e/meta-glasses-virtual-os.spec.ts",
      "required_assertions": [
        "opens every SwissKnife desktop app",
        "renders a reusable Meta glasses ORB template",
        "meta-glasses-chromium",
        "results.json",
        "apps-meta-display-report.json"
      ]
    },
    {
      "surface": "hallucinate_app",
      "command": "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts",
      "package_script": "test:e2e",
      "runner": "hallucinate_app/scripts/run_playwright_test.mjs",
      "spec": "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts",
      "required_assertions": [
        "voice",
        "gesture",
        "mouse",
        "agent",
        "remote-meta-glasses",
        "policy_decision",
        "mediation_receipt"
      ]
    }
  ],
  "product_critical_hops": [
    {
      "hop": "phone_originated_command",
      "evidence": "VAI-339 launch replay request_id and shared capability envelope"
    },
    {
      "hop": "hallucinate_app_mediation",
      "evidence": "multimodal-control-surface.spec.ts policy decision and mediation receipt"
    },
    {
      "hop": "swissknife_virtual_desktop",
      "evidence": "meta-glasses-virtual-os.spec.ts opens every Swissknife desktop app"
    },
    {
      "hop": "desktop_peer_offload",
      "evidence": "VAI-339 placement receipt keeps desktop_peer with phone_local recovery"
    },
    {
      "hop": "meta_glasses_terminal",
      "evidence": "Swissknife ORB template renders Meta glasses display-widget receipts"
    }
  ],
  "blocking_rule": "The production launch objective remains active until the Python readiness gate and both Playwright commands pass for the same receipt lineage.",
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
  "pass_together_rule": {
    "required_commands": [
      "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q",
      "npm --prefix swissknife run test:e2e:meta-glasses",
      "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
    ],
    "same_receipt_lineage": true,
    "gate_state_before_all_pass": "open",
    "gate_state_after_all_pass": "launch_ready"
  },
  "split_policy": "No child split is required unless physical phone, desktop peer, or Meta glasses capture fails independently of this deterministic Playwright gate."
}
```

## Validation

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q
npm --prefix swissknife run test:e2e:meta-glasses
npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```
