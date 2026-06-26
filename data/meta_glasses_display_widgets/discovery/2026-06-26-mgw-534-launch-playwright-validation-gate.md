# MGW-534 Launch Playwright Validation Gate

Date: 2026-06-26
Task: MGW-534
Goal id: VAIOS-G727
Goal packet: goal_packet/launch/external/ec964340486b
Packet goals: VAIOS-G727, VAIOS-G729
Evidence term: launch Playwright validation gate

MGW-534 closes the VAIOS-G727 objective gap by binding the Meta glasses
control-plane input-routing fixture to the launch Playwright validation gate.
The proof is hardware-free but preserves replay receipts for physical Meta
Wearables DAT sessions on Android and iOS.

## Gate Fixture

```json
{
  "schema": "mgw_launch_playwright_validation_gate_v1",
  "task_id": "MGW-534",
  "goal_id": "VAIOS-G727",
  "goal_packet": "goal_packet/launch/external/ec964340486b",
  "packet_goals": [
    "VAIOS-G727",
    "VAIOS-G729"
  ],
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-objective-gap-2f00e48f3541.md",
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
      "fixture": "hallucinate_app/test/e2e/fixtures/hao-675-launch-replay.json"
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
  "route": [
    "Meta glasses interface",
    "Meta Wearables DAT Android or iOS session",
    "mobile phone",
    "Swissknife applications",
    "Hallucinate App mediation",
    "control plane"
  ],
  "mobile_edges": [
    "external/meta-wearables-dat-android",
    "external/meta-wearables-dat-ios",
    "mobile"
  ],
  "assertions": [
    "The Swissknife Playwright fixture has one replayable event for each required VAIOS-G727 input.",
    "Every event uses the same mobile ORB control-plane route, Bluetooth route-state, Wi-Fi app-level handoff, IPFS CID metadata, libp2p session metadata, and MCP++ envelope profile.",
    "The Hallucinate App multimodal-control-surface Playwright gate keeps remote-meta-glasses mediation in the same launch receipt lineage.",
    "The objective heap records this MGW-534 proof for VAIOS-G727 and the shared VAIOS-G729 packet so supervisor-fed backlog repair remains aligned."
  ],
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_launch_readiness_gate.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
}
```

## Evidence

- `swissknife/test/e2e/fixtures/mgw-519-meta-glasses-control-plane.json`
  carries replayable camera, microphone, headphones, captouch, and Neural Band
  events on the Swissknife mobile ORB control-plane route.
- `swissknife/src/services/meta-glasses-multimodal-io-transport-contract.ts`
  and `src/handsfree/meta_glasses_multimodal_io_transport_contract.py` generate
  the same hardware-free fixture shape for Playwright and Python validation.
- `swissknife/test/e2e/meta-glasses-virtual-os.spec.ts` is the Swissknife launch
  Playwright validation gate for the Meta glasses virtual OS surface.
- `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts` keeps the
  remote-meta-glasses control-surface route in Hallucinate App mediation.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records the
  MGW-534 proof for VAIOS-G727 and the shared packet proof for VAIOS-G729.
