# HAO-721 Daemon Launch Health Gate

Date: 2026-06-28
Task: HAO-721
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate

HAO-721 closes the current Hallucinate App daemon launch orchestration
objective gap by binding the `ipfs_kit_py`, `ipfs_datasets_py`, and
`ipfs_accelerate_py` daemon launch plan to the replayable Hallucinate App
Playwright gate. The proof reuses the shared MGW-535 packet gate so VAIOS-G724
and VAIOS-G728 stay aligned while the supervisor-fed HAO backlog has a current
receipt for the 2026-06-28 gap scan.

## Gate Fixture

```json
{
  "schema": "hao_daemon_launch_health_gate_v1",
  "task_id": "HAO-721",
  "shared_packet_task_id": "MGW-535",
  "goal_id": "VAIOS-G728",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goals": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-objective-gap-b023c8de5b69.md",
  "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-daemon-launch-health-gate.md",
  "shared_packet_receipt": "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-535-daemon-launch-health-gate.md",
  "objective_heap": "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
  "manager_gate_fixture": "hallucinate_app/test/e2e/fixtures/mgw-535-daemon-launch-health-gate.json",
  "playwright_gate": {
    "surface": "hallucinate_app",
    "command": "npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts",
    "spec": "hallucinate_app/test/e2e/daemon-launch-health.spec.ts",
    "asserts": [
      "Hallucinate App daemon health",
      "daemon launcher",
      "MCP server",
      "MCP dashboard",
      "dashboard capability catalog",
      "Swissknife applications",
      "launch Playwright validation gate"
    ]
  },
  "playwright_specs": [
    "hallucinate_app/test/e2e/daemon-launch-health.spec.ts",
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
  ],
  "validation_commands": [
    "npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts",
    "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
    "npm --prefix swissknife run test:e2e:meta-glasses",
    "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
  ],
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "required_evidence": [
    "Hallucinate App daemon health",
    "daemon launcher",
    "MCP server",
    "MCP dashboard",
    "ipfs_accelerate_py",
    "ipfs_datasets_py",
    "ipfs_kit_py",
    "dashboard capability catalog",
    "Swissknife applications",
    "launch Playwright validation gate"
  ],
  "supervisor_alignment": {
    "objective_heap_goal": "VAIOS-G728",
    "packet_sibling_goal": "VAIOS-G724",
    "backlog_task": "HAO-721",
    "shared_packet_task": "MGW-535",
    "keeps_supervisor_fed_backlog_aligned": true
  },
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
}
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes HAO-721
  through `backlog_task_ids`, `supervisor_gap_receipts`, and
  `hallucinate_backlog_receipts` while preserving the shared MGW-535 daemon
  launch validation gate.
- `hallucinate_app/test/e2e/daemon-launch-health.spec.ts` asserts the HAO-721
  fixture against the manager gate, daemon health paths, MCP RPC paths, backend
  packages, dashboard catalog coverage, and Swissknife handoff records.
- `hallucinate_app/test/e2e/fixtures/hao-721-daemon-launch-health-gate.json`
  mirrors this receipt for Playwright and supervisor replay.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  this HAO-721 proof under VAIOS-G728 and references packet sibling VAIOS-G724.
