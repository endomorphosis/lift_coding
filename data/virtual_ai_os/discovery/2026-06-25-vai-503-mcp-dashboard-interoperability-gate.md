# VAI-503 MCP Dashboard Interoperability Gate

Task: VAI-503
Goal id: VAIOS-G723
Track: launch
Missing evidence closed: launch Playwright validation gate

This packet binds the Hallucinate App MCP dashboard console to a launch
Playwright validation gate. The gate is dashboard-specific: it must prove that
the operator console exposes catalog normalization, dashboard UI wiring,
mediated tool-call receipts, Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks for `ipfs_kit_py`,
`ipfs_datasets_py`, and `ipfs_accelerate_py`.

## DashboardInteroperabilityGate

```json
{
  "schema": "mcp_dashboard_interoperability_gate_v1",
  "task_id": "VAI-503",
  "goal_id": "VAIOS-G723",
  "evidence_term": "launch Playwright validation gate",
  "playwright_command": "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
  "playwright_spec": "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts",
  "catalog_source": "hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js",
  "catalog_schema": "hallucinate_app.mcp_dashboard_capability_catalog.v1",
  "catalog_normalization": [
    "ipfs_kit_py endpoint http://127.0.0.1:8014",
    "ipfs_datasets_py native dashboard catalog http://127.0.0.1:8899/api/hallucinate/dashboard-catalog",
    "ipfs_accelerate_py MCP++ profile mcp++/profile-e-mcp-p2p"
  ],
  "dashboard_ui_wiring": [
    "IPFS Kit Dashboard",
    "IPFS Datasets Dashboard",
    "IPFS Accelerate Dashboard",
    "MCP Daemon Manager"
  ],
  "mediated_tool_call_receipts": {
    "before_invoke_hook": "hallucinate_app.node.control_surface_invocation.ControlSurfaceInvocationGate.beforeInvoke",
    "required_terms": [
      "interaction_envelope",
      "policy_decision",
      "mediation_receipt",
      "tools/list",
      "tools/call",
      "safe_probe",
      "receipt_cid"
    ]
  },
  "swissknife_consumers": {
    "source": "swissknife/src/services/swissknife-mcp-capability-registry.ts",
    "ipfs_kit_py_port": 8014,
    "shared_receipt_schema": "mcp_server_invocation_receipt_v1",
    "consumer_test": "swissknife/test/mcp-plus-plus/ipfs-ui-descriptors.test.ts"
  },
  "supervisor_follow_up_subtasks": [
    "HAO-678",
    "HAO-679",
    "HAO-680",
    "HAO-681",
    "HAO-682",
    "HAO-683"
  ],
  "failure_rule": "If any dashboard or backend validation fails, the supervisor-generated follow-up subtasks remain attached to VAIOS-G723 instead of being replaced by broad scans."
}
```

## Validation

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
npm --prefix swissknife run test:e2e:mcp
```
