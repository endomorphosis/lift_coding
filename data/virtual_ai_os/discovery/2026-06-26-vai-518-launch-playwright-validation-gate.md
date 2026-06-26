# VAI-518 Launch Playwright Validation Gate

Date: 2026-06-26
Task: VAI-518
Goal id: VAIOS-G727
Goal packet: goal_packet/launch/external/ec964340486b
Packet goals: VAIOS-G727, VAIOS-G729
Evidence term: launch Playwright validation gate

VAI-518 closes the virtual AI OS objective gap for Meta glasses
control-plane input routing by binding the VAI backlog task to the shared
MGW-534, HAO-701, and VAI-520 packet evidence. The gate remains hardware-free
for launch CI, but it preserves replayable Meta Wearables DAT Android and iOS
edges for physical follow-up.

## Gate Fixture

```json
{
  "schema": "vai_meta_glasses_input_routing_launch_playwright_gate_v1",
  "task_id": "VAI-518",
  "goal_id": "VAIOS-G727",
  "goal_packet": "goal_packet/launch/external/ec964340486b",
  "packet_goals": [
    "VAIOS-G727",
    "VAIOS-G729"
  ],
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/virtual_ai_os/discovery/2026-06-26-vai-518-objective-gap-2f00e48f3541.md",
  "receipt_path": "data/virtual_ai_os/discovery/2026-06-26-vai-518-launch-playwright-validation-gate.md",
  "objective_heap": "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
  "shared_packet_receipts": [
    "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-launch-playwright-validation-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-701-launch-playwright-validation-gate.md",
    "data/virtual_ai_os/discovery/2026-06-26-vai-520-launch-playwright-validation-gate.md"
  ],
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
    "backlog_task": "VAI-518",
    "shared_packet_tasks": [
      "MGW-534",
      "HAO-701",
      "VAI-520"
    ],
    "keeps_supervisor_fed_backlog_aligned": true
  },
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_launch_readiness_gate.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
}
```

## Evidence

- `data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-launch-playwright-validation-gate.md`
  proves the Meta glasses interface, camera, microphone, headphones, captouch,
  Neural Band, Bluetooth transport, Wi-Fi transport, IPFS, libp2p, MCP++,
  mobile phone, Swissknife applications, and control plane fixture against the
  Swissknife launch Playwright gate.
- `data/hallucinate_multimodal_control/discovery/2026-06-26-hao-701-launch-playwright-validation-gate.md`
  proves the Hallucinate App mediation side of the same route using the
  `remote-meta-glasses` and `mobile-orb-publish-glasses-event` route terms.
- `data/virtual_ai_os/discovery/2026-06-26-vai-520-launch-playwright-validation-gate.md`
  keeps packet sibling `VAIOS-G729` aligned with the supervisor active steering
  and validation repair path.
- `swissknife/test/e2e/fixtures/mgw-519-meta-glasses-control-plane.json`
  is the replayable control-plane input fixture used by both the Python launch
  readiness gate and `npm --prefix swissknife run test:e2e:meta-glasses`.
- `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts` keeps the
  remote Meta glasses input routed through Hallucinate App mediation receipts.

## Validation

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_launch_readiness_gate.py -q
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

- 2026-06-26: Python launch receipt gate passed with 86 tests.
- 2026-06-26: Swissknife Meta glasses Playwright gate passed with 3 tests.
- 2026-06-26: Hallucinate App multimodal control surface Playwright gate passed with 5 tests.
