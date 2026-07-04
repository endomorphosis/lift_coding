# VAI-574 Daemon Launch Health Gate

Date: 2026-07-04
Task: VAI-574
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate

## Gate

VAI-574 closes the current VAIOS-G728 objective gap filed in
`data/virtual_ai_os/discovery/2026-07-04-vai-574-objective-gap-b023c8de5b69.md`
by binding Hallucinate App daemon launch orchestration to the replayable daemon
health Playwright validation gate:

```text
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts
```

This is the daemon-launch sibling of VAI-573 in the shared
`goal_packet/launch/hallucinate_app/44dceea6bc53` packet, so the VAIOS-G724
dashboard capability catalog gate and VAIOS-G728 daemon health gate advance
together. `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` now
points the VAI-573 dashboard catalog entry at this receipt through
`packet_sibling_gate_receipt`.

The same launch packet stays aligned with the supervisor-fed backlog,
Swissknife consumer gate, and multimodal control surface gate:

```text
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` includes `VAI-574` in `DAEMON_LAUNCH_GATE_VAI_TASK_IDS`, the shared discovery receipts, the objective-gap receipts, the `VAI_574_DAEMON_LAUNCH_VALIDATION_GATE` record returned by `getDaemonLaunchValidationGates()`, every daemon launch-plan `launch_validation_gates` entry for VAIOS-G728, and the VAI-573 dashboard packet sibling reference.
- `hallucinate_app/test/e2e/daemon-launch-health.spec.ts` asserts the VAI-574 fixture against `getDaemonLaunchValidationGate()` and `getDaemonLaunchValidationGates()`, including the shared MGW-535 `vai_task_ids`, `objective_gap_receipts`, `discovery_receipts`, daemon health/RPC paths, backend packages, dashboard capability catalog, and Swissknife handoff records.
- `hallucinate_app/test/e2e/fixtures/vai-574-daemon-launch-health-gate.json` records the VAI-owned launch receipt, backend package list, Playwright specs, and Swissknife handoff records for VAIOS-G728 with packet sibling VAIOS-G724, generated directly from `MCPDaemonManager` for fixture parity.
- `swissknife/test/e2e/meta-glasses-virtual-os.spec.ts` consumes the VAI-574 Hallucinate fixture and proves Swissknife sees the same `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` handoff records.
- `tests/test_hallucinate_multimodal_control_todo_queue.py` keeps the supervisor-fed backlog aligned with `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` by checking this discovery receipt, fixture, shared MGW-535 packet fixture, and required evidence terms together.
- External surfaces remain part of the launch packet evidence through `external/ipfs_accelerate`, `external/ipfs_datasets`, and `external/ipfs_kit` while the runtime contracts use `ipfs_accelerate_py`, `ipfs_datasets_py`, and `ipfs_kit_py` daemon package names.

## Covered Terms

- Hallucinate App daemon health
- daemon launcher
- MCP server
- MCP dashboard
- ipfs_accelerate_py
- ipfs_datasets_py
- ipfs_kit_py
- external/ipfs_accelerate
- external/ipfs_datasets
- external/ipfs_kit
- dashboard capability catalog
- Swissknife applications
- launch Playwright validation gate
- VAI-573
- VAI-574

## Gate Fixture

```json
{
  "schema": "hallucinate_app.daemon_launch_validation_gate.v1",
  "receipt_schema": "launch_readiness_receipt_v1",
  "task_id": "VAI-574",
  "vai_task_id": "VAI-519",
  "vai_task_ids": [
    "VAI-519",
    "VAI-530",
    "VAI-536",
    "VAI-538",
    "VAI-540",
    "VAI-549",
    "VAI-555",
    "VAI-557",
    "VAI-565",
    "VAI-568",
    "VAI-574",
    "VAI-577",
    "VAI-580",
    "VAI-583",
    "VAI-586",
    "VAI-589"
  ],
  "backlog_task_id": "HAO-702",
  "backlog_task_ids": [
    "HAO-702",
    "HAO-713",
    "HAO-719",
    "HAO-721"
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
    "data/virtual_ai_os/discovery/2026-07-02-vai-549-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-555-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-557-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-03-vai-565-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-568-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-574-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-577-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-580-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-583-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-586-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-589-daemon-launch-health-gate.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-535-daemon-launch-health-gate.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-551-daemon-launch-health-gate.md"
  ],
  "objective_gap_receipt": "data/virtual_ai_os/discovery/2026-07-04-vai-574-objective-gap-b023c8de5b69.md",
  "objective_gap_receipts": [
    "data/virtual_ai_os/discovery/2026-06-26-vai-519-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-27-vai-530-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-536-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-538-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-540-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-549-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-555-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-557-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-03-vai-565-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-568-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-574-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-577-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-580-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-583-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-586-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-04-vai-589-objective-gap-b023c8de5b69.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-551-objective-gap-b023c8de5b69.md"
  ],
  "supervisor_gap_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-objective-gap-b023c8de5b69.md",
  "supervisor_gap_receipts": [
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-27-hao-713-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-objective-gap-b023c8de5b69.md"
  ],
  "hallucinate_backlog_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-daemon-launch-health-gate.md",
  "hallucinate_backlog_receipts": [
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-27-hao-713-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-daemon-launch-health-gate.md"
  ],
  "launch_gate_receipt": "data/virtual_ai_os/discovery/2026-07-04-vai-574-daemon-launch-health-gate.md",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/vai-574-daemon-launch-health-gate.json",
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
      "endpoint": "http://127.0.0.1:8014",
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
