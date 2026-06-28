# MGW-551 Daemon Launch Health Gate

Date: 2026-06-28
Task: MGW-551
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate

MGW-551 closes the Hallucinate App daemon launch orchestration objective gap
filed in
`data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-551-objective-gap-b023c8de5b69.md`.
The proof is additive to the shared MGW-535 daemon launch packet so VAIOS-G728
keeps one Hallucinate App launch gate while the MGW supervisor backlog has an
explicit receipt for this objective-gap task.

## Gate Fixture

```json
{
  "schema": "meta_glasses_display_widgets.daemon_launch_health_gate_v1",
  "task_id": "MGW-551",
  "shared_packet_task_id": "MGW-535",
  "goal_id": "VAIOS-G728",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goals": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-551-objective-gap-b023c8de5b69.md",
  "receipt_path": "data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-551-daemon-launch-health-gate.md",
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
  "swissknife_handoff": [
    {
      "daemon_id": "ipfs-kit",
      "server_package": "ipfs_kit_py",
      "swissknife_consumer": "Swissknife IPFS storage, pin dashboard, and backend health surfaces",
      "mediation_contract_ref": "control_surface_contract:mcp-daemon:ipfs-kit"
    },
    {
      "daemon_id": "ipfs-datasets",
      "server_package": "ipfs_datasets_py",
      "swissknife_consumer": "Swissknife dataset, content, index, provenance, and background task surfaces",
      "mediation_contract_ref": "control_surface_contract:mcp-daemon:ipfs-datasets"
    },
    {
      "daemon_id": "ipfs-accelerate",
      "server_package": "ipfs_accelerate_py",
      "swissknife_consumer": "Swissknife hardware profile, inference job, job status, and telemetry surfaces",
      "mediation_contract_ref": "control_surface_contract:mcp-daemon:ipfs-accelerate"
    }
  ],
  "supervisor_alignment": {
    "objective_heap_goal": "VAIOS-G728",
    "packet_sibling_goal": "VAIOS-G724",
    "backlog_task": "MGW-551",
    "shared_packet_task": "MGW-535",
    "keeps_supervisor_fed_backlog_aligned": true
  },
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)"
}
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` includes this
  MGW-551 discovery receipt and objective-gap receipt in
  `getDaemonLaunchValidationGate`.
- `hallucinate_app/test/e2e/daemon-launch-health.spec.ts` asserts
  `hallucinate_app/test/e2e/fixtures/mgw-551-daemon-launch-health-gate.json`
  against the manager gate, backend package list, daemon health paths,
  Playwright launch command, and Swissknife handoff records.
- The gate covers Hallucinate App daemon health, daemon launcher, MCP server,
  MCP dashboard, `ipfs_accelerate_py`, `ipfs_datasets_py`, `ipfs_kit_py`,
  dashboard capability catalog, Swissknife applications, and launch Playwright
  validation gate evidence for VAIOS-G728.
