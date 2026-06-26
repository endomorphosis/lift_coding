# HAO-701 Launch Playwright Validation Gate

Date: 2026-06-26
Task: HAO-701
Goal id: VAIOS-G727
Goal packet: goal_packet/launch/external/ec964340486b
Packet goals: VAIOS-G727, VAIOS-G729
Evidence term: launch Playwright validation gate

HAO-701 closes the Hallucinate-owned VAIOS-G727 objective gap by binding the
Meta glasses control-plane input-routing route to the launch Playwright
validation gate. The fixture is hardware-free, but it preserves replay receipts
for Meta Wearables DAT Android and iOS sessions.

## Gate Fixture

```json
{
  "schema": "hao_launch_playwright_validation_gate_v1",
  "task_id": "HAO-701",
  "goal_id": "VAIOS-G727",
  "goal_packet": "goal_packet/launch/external/ec964340486b",
  "packet_goals": [
    "VAIOS-G727",
    "VAIOS-G729"
  ],
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-701-objective-gap-2f00e48f3541.md",
  "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-701-launch-playwright-validation-gate.md",
  "shared_packet_receipt": "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-launch-playwright-validation-gate.md",
  "objective_heap": "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
  "python_gate": {
    "command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_launch_readiness_gate.py -q",
    "tests": [
      "tests/test_hallucinate_multimodal_control_todo_queue.py",
      "tests/test_virtual_ai_os_launch_readiness_gate.py"
    ]
  },
  "playwright_gates": [
    {
      "surface": "swissknife",
      "command": "npm --prefix swissknife run test:e2e:meta-glasses",
      "spec": "swissknife/test/e2e/meta-glasses-virtual-os.spec.ts",
      "fixture": "swissknife/test/e2e/fixtures/mgw-519-meta-glasses-control-plane.json"
    },
    {
      "surface": "hallucinate_app",
      "command": "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts",
      "spec": "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts",
      "route_terms": [
        "remote-meta-glasses",
        "mobile-orb-publish-glasses-event",
        "mediation_receipt"
      ]
    }
  ],
  "required_inputs": [
    "camera",
    "microphone",
    "headphones",
    "captouch",
    "Neural Band"
  ],
  "required_transports": [
    "Bluetooth transport",
    "Wi-Fi transport",
    "IPFS",
    "libp2p",
    "MCP++"
  ],
  "mobile_edges": [
    "external/meta-wearables-dat-android",
    "external/meta-wearables-dat-ios",
    "mobile"
  ],
  "route": [
    "Meta glasses interface",
    "Meta Wearables DAT",
    "mobile phone",
    "Swissknife applications",
    "Hallucinate App mediation",
    "control plane"
  ],
  "supervisor_alignment": {
    "objective_heap_goal": "VAIOS-G727",
    "packet_sibling_goal": "VAIOS-G729",
    "backlog_task": "HAO-701",
    "shared_packet_task": "MGW-534",
    "keeps_supervisor_fed_backlog_aligned": true
  },
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_launch_readiness_gate.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
}
```

## Evidence

- `swissknife/test/e2e/fixtures/mgw-519-meta-glasses-control-plane.json`
  carries replayable camera, microphone, headphones, captouch, and Neural Band
  events through the mobile ORB control-plane route.
- `swissknife/test/e2e/meta-glasses-virtual-os.spec.ts` is the Swissknife
  launch Playwright gate for the Meta glasses virtual OS surface.
- `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts` keeps
  `remote-meta-glasses` and `mobile-orb-publish-glasses-event` inside
  Hallucinate App mediation receipts.
- `data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-launch-playwright-validation-gate.md`
  is the shared packet proof for `VAIOS-G727` and `VAIOS-G729`.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  this HAO-701 proof so supervisor-fed backlog repair remains aligned with the
  objective heap.
