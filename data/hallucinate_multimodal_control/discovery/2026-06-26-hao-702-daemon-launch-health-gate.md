# HAO-702 Daemon Launch Health Gate

Date: 2026-06-26
Task: HAO-702
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate

HAO-702 closes the Hallucinate-owned VAIOS-G728 objective gap by binding the
Hallucinate App daemon launcher and health monitor to a replayable Playwright
validation gate. The shared packet proof remains MGW-535, while this receipt
keeps the supervisor-fed HAO backlog aligned with the objective heap.

## Gate Fixture

```json
{
  "schema": "hao_daemon_launch_health_gate_v1",
  "task_id": "HAO-702",
  "shared_packet_task_id": "MGW-535",
  "goal_id": "VAIOS-G728",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goals": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-objective-gap-b023c8de5b69.md",
  "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-daemon-launch-health-gate.md",
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
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)",
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "daemon_health_paths": [
    {
      "daemon_id": "ipfs-kit",
      "server_package": "ipfs_kit_py",
      "endpoint": "http://127.0.0.1:8004",
      "health_path": "/api/mcp/status",
      "rpc_path": "/mcp/tools/call",
      "startup_order": 10
    },
    {
      "daemon_id": "ipfs-datasets",
      "server_package": "ipfs_datasets_py",
      "endpoint": "http://127.0.0.1:3002",
      "health_path": "/health/ready",
      "rpc_path": "/datasets/load",
      "startup_order": 20
    },
    {
      "daemon_id": "ipfs-accelerate",
      "server_package": "ipfs_accelerate_py",
      "endpoint": "http://127.0.0.1:3003",
      "health_path": "/api/mcp/status",
      "rpc_path": "/mcp",
      "startup_order": 30
    }
  ],
  "swissknife_handoff": [
    "Swissknife IPFS storage, pin dashboard, and backend health surfaces",
    "Swissknife dataset, content, index, provenance, and background task surfaces",
    "Swissknife hardware profile, inference job, job status, and telemetry surfaces"
  ],
  "supervisor_alignment": {
    "objective_heap_goal": "VAIOS-G728",
    "packet_sibling_goal": "VAIOS-G724",
    "backlog_task": "HAO-702",
    "shared_packet_task": "MGW-535",
    "keeps_supervisor_fed_backlog_aligned": true
  }
}
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes
  `getDaemonLaunchValidationGate`, `backlog_task_id`, `launch_objective_ids`,
  and `launch_validation_gate` for `HAO-702`, `MGW-535`, `VAIOS-G728`, and
  packet sibling `VAIOS-G724`.
- `hallucinate_app/test/e2e/daemon-launch-health.spec.ts` asserts the headless
  Playwright gate, daemon health paths, MCP server RPC paths, dashboard handoff,
  backend package ordering, and Swissknife consumer records.
- `hallucinate_app/test/e2e/fixtures/mgw-535-daemon-launch-health-gate.json`
  is the stable launch readiness fixture consumed by the Playwright gate.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  this HAO-702 proof so objective-heap scheduling and supervisor-fed backlog
  repair preserve the same packet evidence.
