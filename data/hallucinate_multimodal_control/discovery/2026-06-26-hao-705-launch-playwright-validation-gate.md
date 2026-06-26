# HAO-705 Launch Playwright Validation Gate

Date: 2026-06-26
Task: HAO-705
Goal id: VAIOS-G726
Evidence term: launch Playwright validation gate

HAO-705 closes the Hallucinate-owned VAIOS-G726 objective gap by binding the
cross-device virtual desktop offload replay to the shared Swissknife and
Hallucinate App Playwright launch gates. The fixture is hardware-free, but it
keeps phone-hosted, desktop-peer, IPFS/libp2p/MCP++, mediation, cross-device e2e
validation, launch readiness receipt, and Playwright launch replay terms in one
replay lineage.

## Gate Fixture

```json
{
  "schema": "hao_cross_device_launch_playwright_gate_v1",
  "task_id": "HAO-705",
  "goal_id": "VAIOS-G726",
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-705-objective-gap-4ca32c914d33.md",
  "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-705-launch-playwright-validation-gate.md",
  "objective_heap": "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
  "lineage_id": "VAIOS-G726:cross-device-virtual-desktop-offload-launch-replay",
  "source_replay_fixture": "swissknife/test/e2e/fixtures/vai-502-cross-device-playwright-replay.json",
  "playwright_fixture": "hallucinate_app/test/e2e/fixtures/hao-705-cross-device-launch-gate.json",
  "mirrored_swissknife_fixture": "swissknife/test/e2e/fixtures/hao-705-cross-device-launch-gate.json",
  "python_gate": {
    "command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q",
    "tests": [
      "tests/test_virtual_ai_os_launch_readiness_gate.py"
    ]
  },
  "playwright_gates": [
    {
      "surface": "swissknife",
      "command": "npm --prefix swissknife run test:e2e:meta-glasses",
      "spec": "swissknife/test/e2e/meta-glasses-virtual-os.spec.ts",
      "asserts_fixture": "swissknife/test/e2e/fixtures/hao-705-cross-device-launch-gate.json"
    },
    {
      "surface": "hallucinate_app",
      "command": "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts",
      "spec": "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts",
      "asserts_fixture": "hallucinate_app/test/e2e/fixtures/hao-705-cross-device-launch-gate.json"
    }
  ],
  "route": [
    "phone-hosted Swissknife virtual desktop",
    "mobile phone",
    "desktop peer discovery",
    "desktop peer offload",
    "IPFS",
    "libp2p",
    "MCP++",
    "Hallucinate App mediation",
    "Meta glasses terminal",
    "launch readiness receipt"
  ],
  "mission_terms": [
    "phone-hosted Swissknife virtual desktop",
    "desktop peer offload",
    "mobile phone",
    "Hallucinate App mediation",
    "IPFS",
    "libp2p",
    "MCP++",
    "launch readiness receipt",
    "cross-device e2e validation",
    "Playwright launch replay",
    "launch Playwright validation gate"
  ],
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "cross_device_replay": {
    "phone_hosted_mode": "phone-hosted",
    "control_plane_command": "desktop.request_handoff",
    "selected_runtime": "desktop_peer",
    "fallback_runtime": "phone_local",
    "desktop_peer_receipt": "sha256:vai502-desktop-peer-timeout",
    "phone_fallback_receipt": "sha256:vai502-phone-fallback-receipt",
    "meta_glasses_render_receipt": "sha256:vai502-meta-glasses-render-receipt",
    "launch_readiness_lineage": "VAIOS-G697:launch-readiness:phone-desktop-glasses"
  },
  "validation_command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)",
  "supervisor_alignment": {
    "objective_heap_goal": "VAIOS-G726",
    "backlog_task": "HAO-705",
    "bundle": "objective/launch/cross-device-virtual-desktop-offload-replay",
    "keeps_supervisor_fed_backlog_aligned": true
  }
}
```

## Evidence

- `swissknife/test/e2e/fixtures/vai-502-cross-device-playwright-replay.json`
  supplies the phone-hosted command receipt, desktop-peer timeout, phone-local
  fallback, and Meta glasses terminal render receipt.
- `hallucinate_app/test/e2e/fixtures/hao-705-cross-device-launch-gate.json` and
  `swissknife/test/e2e/fixtures/hao-705-cross-device-launch-gate.json` mirror
  the same launch gate so both Playwright surfaces assert the VAIOS-G726 replay.
- `tests/test_virtual_ai_os_launch_readiness_gate.py` verifies the receipt,
  mirrored fixtures, existing VAI-502 replay fixture, and objective heap proof
  stay aligned with the launch Playwright validation gate.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  this HAO-705 proof so supervisor-fed backlog repair remains aligned with the
  objective heap.
