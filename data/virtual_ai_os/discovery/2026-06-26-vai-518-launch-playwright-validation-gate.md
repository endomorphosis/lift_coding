# VAI-518 Launch Playwright Validation Gate

Date: 2026-06-26
Task: VAI-518
Goal id: VAIOS-G727
Goal packet: goal_packet/launch/external/ec964340486b
Packet goals: VAIOS-G727, VAIOS-G729
Evidence term: launch Playwright validation gate
Artifact path: data/virtual_ai_os/discovery/2026-06-26-vai-518-launch-playwright-validation-gate.md

VAI-518 closes the objective gap recorded in
`data/virtual_ai_os/discovery/2026-06-26-vai-518-objective-gap-2f00e48f3541.md`
by making the Meta glasses control-plane input-routing proof visible from the
virtual AI OS discovery lane. The packet reuses the MGW-534 Playwright fixture
and binds it to the same launch command lineage that the supervisor validates.

## Gate Fixture

```json
{
  "schema": "vai_launch_playwright_validation_gate_v1",
  "task_id": "VAI-518",
  "goal_id": "VAIOS-G727",
  "goal_packet": "goal_packet/launch/external/ec964340486b",
  "packet_goals": [
    "VAIOS-G727",
    "VAIOS-G729"
  ],
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/virtual_ai_os/discovery/2026-06-26-vai-518-objective-gap-2f00e48f3541.md",
  "paired_mgw_receipt": "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-launch-playwright-validation-gate.md",
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
  "supervisor_alignment": {
    "todo_vector_key": "2ac1fa3810e3a6b9",
    "merge_key": "d40a3d3f5fd702f0",
    "merge_family": "goal_packet/launch/external/ec964340486b",
    "packet_anchor_task": "VAI-518",
    "packet_member_task": "VAI-520",
    "objective_heap_goal": "VAIOS-G729"
  },
  "assertions": [
    "The virtual AI OS discovery lane names the same launch Playwright validation gate as the MGW-534 packet proof.",
    "The Swissknife Playwright fixture has one replayable event for camera, microphone, headphones, captouch, and Neural Band input routing.",
    "Every required input preserves Bluetooth route-state, Wi-Fi app-level handoff, IPFS CID metadata, libp2p session metadata, and MCP++ envelope profile.",
    "The Hallucinate App multimodal-control-surface gate keeps remote-meta-glasses mediation in the same launch receipt lineage.",
    "The objective heap records this VAI-518 proof for VAIOS-G727 and the shared VAIOS-G729 supervisor-repair packet."
  ],
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_launch_readiness_gate.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
}
```

## Evidence

- `swissknife/test/e2e/fixtures/mgw-519-meta-glasses-control-plane.json`
  carries replayable Meta glasses camera, microphone, headphones, captouch, and
  Neural Band events through the mobile ORB control-plane route.
- `swissknife/test/e2e/meta-glasses-virtual-os.spec.ts` is the Swissknife
  Playwright launch gate for the Meta glasses virtual OS surface.
- `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts` keeps the
  remote-meta-glasses control-surface route in Hallucinate App mediation.
- `data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-launch-playwright-validation-gate.md`
  remains the paired MGW proof for the same goal packet.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records the
  VAI-518 proof for VAIOS-G727 and the shared packet proof for VAIOS-G729.
