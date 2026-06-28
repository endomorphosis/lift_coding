# HAO-714 MCP Dashboard Interoperability Gate

Task: HAO-714
Backlog peer: VAI-531
Goal id: VAIOS-G723
Track: launch
Missing evidence closed: launch Playwright validation gate

HAO-714 is the supervisor-fed Hallucinate backlog peer for the VAI-531
dashboard interoperability gate. It keeps the launch Playwright validation
gate aligned with the VAIOS-G723 objective heap and the Hallucinate App
runtime catalog field `dashboard_interoperability_validation_gate`.

The peer gate covers catalog normalization, dashboard UI wiring, mediated
tool-call receipts, Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks. It also names daemon health, MCP++
telemetry, `tools/list`, `tools/call`, `control_surface` receipts, and the
three required MCP backends: `ipfs_kit_py`, `ipfs_datasets_py`, and
`ipfs_accelerate_py`.

## DashboardInteroperabilityValidationGate

```json
{
  "schema": "mcp_dashboard_interoperability_gate_v1",
  "task_id": "HAO-714",
  "vai_task_id": "VAI-531",
  "goal_id": "VAIOS-G723",
  "lineage_id": "VAIOS-G723:mcp-dashboard-interoperability",
  "evidence_term": "launch Playwright validation gate",
  "catalog_field": "dashboard_interoperability_validation_gate",
  "catalog_source": "hallucinate_app.node.mcp_daemon_manager.getDashboardCapabilityCatalog",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/vai-531-mcp-dashboard-interoperability-gate.json",
  "required_evidence": [
    "catalog normalization",
    "dashboard UI wiring",
    "mediated tool-call receipts",
    "Swissknife consumers",
    "Playwright coverage",
    "supervisor-generated follow-up subtasks",
    "daemon health",
    "MCP++ telemetry",
    "tools/list",
    "tools/call",
    "control_surface receipts",
    "launch Playwright validation gate"
  ],
  "validation_commands": [
    "npm --prefix hallucinate_app run test:daemon-manager",
    "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
    "npm --prefix swissknife run test:e2e:mcp",
    "test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
  ],
  "failure_rule": "Any dashboard or backend validation failure remains supervisor-generated follow-up work for VAIOS-G723."
}
```
