# HAO-725 Daemon Launch Health Gate

Date: 2026-06-28
Task: HAO-725
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate

HAO-725 closes the current Hallucinate App daemon launch orchestration objective gap by binding the `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` daemon launch plan to the replayable Hallucinate App Playwright gate. The proof reuses the shared MGW-535 packet gate so VAIOS-G724 and VAIOS-G728 stay aligned while the supervisor-fed HAO backlog has a current receipt for the 2026-06-28 gap scan.

## Gate Fixture

```json
{
  "schema": "hallucinate_app.daemon_launch_validation_gate.v1",
  "receipt_schema": "launch_readiness_receipt_v1",
  "task_id": "HAO-725",
  "vai_task_id": "VAI-519",
  "vai_task_ids": [
    "VAI-519",
    "VAI-530",
    "VAI-536",
    "VAI-538",
    "VAI-540"
  ],
  "backlog_task_id": "HAO-702",
  "backlog_task_ids": [
    "HAO-702",
    "HAO-713",
    "HAO-719",
    "HAO-721",
    "HAO-725"
  ],
  "shared_packet_task_id": "MGW-535",
  "goal_id": "VAIOS-G728",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goals": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "evidence_term": "launch Playwright validation gate",
  "launch_key": "hallucinate-daemon-launch-orchestration",
  "gate_state": "gate_open_until_playwright_passes",
  "discovery_receipts": [
    "data/virtual_ai_os/discovery/2026-06-26-vai-519-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-06-27-vai-530-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-536-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-538-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-540-daemon-launch-health-gate.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-535-daemon-launch-health-gate.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-551-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-daemon-launch-health-gate.md"
  ],
  "objective_gap_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-objective-gap-b023c8de5b69.md",
  "objective_gap_receipts": [
    "data/virtual_ai_os/discovery/2026-06-26-vai-519-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-27-vai-530-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-536-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-538-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-540-objective-gap-b023c8de5b69.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-551-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-objective-gap-b023c8de5b69.md"
  ],
  "supervisor_gap_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-objective-gap-b023c8de5b69.md",
  "supervisor_gap_receipts": [
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-27-hao-713-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-objective-gap-b023c8de5b69.md"
  ],
  "hallucinate_backlog_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-daemon-launch-health-gate.md",
  "hallucinate_backlog_receipts": [
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-27-hao-713-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-daemon-launch-health-gate.md"
  ],
  "launch_gate_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-daemon-launch-health-gate.md",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/hao-725-daemon-launch-health-gate.json",
  "validation_commands": [
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q",
    "test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts",
    "test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses",
    "test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
  ],
  "playwright_specs": [
    "hallucinate_app/test/e2e/daemon-launch-health.spec.ts",
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
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
  "failure_rule": "Any daemon launch, health, dashboard catalog, Swissknife handoff, or Playwright validation failure remains supervisor-generated follow-up work for VAIOS-G728."
}
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes HAO-725 through `backlog_task_ids`, `supervisor_gap_receipts`, `hallucinate_backlog_receipts`, `getDaemonLaunchValidationGates()`, and each daemon launch-plan `launch_validation_gates` list while preserving the shared MGW-535 daemon launch validation gate.
- `hallucinate_app/test/e2e/daemon-launch-health.spec.ts` asserts the HAO-725 fixture against the manager gate, daemon health paths, MCP RPC paths, backend packages, dashboard catalog coverage, and Swissknife handoff records.
- `hallucinate_app/test/e2e/fixtures/hao-725-daemon-launch-health-gate.json` mirrors this receipt for Playwright and supervisor replay.
- `data/hallucinate_multimodal_control/discovery/2026-06-28-hao-725-objective-gap-b023c8de5b69.md` is covered by the launch Playwright validation gate and remains aligned with `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`.
