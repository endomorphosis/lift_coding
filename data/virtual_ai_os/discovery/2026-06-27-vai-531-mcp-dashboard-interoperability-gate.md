# VAI-531 MCP Dashboard Interoperability Gate

Task: VAI-531
Backlog peer: HAO-714
Goal id: VAIOS-G723
Track: launch
Missing evidence closed: launch Playwright validation gate

VAI-531 closes the current VAIOS-G723 objective gap by making the Hallucinate
App MCP dashboard interoperability console scanner-visible in the runtime
dashboard capability catalog. The catalog field
`dashboard_interoperability_validation_gate` points to this receipt, the
HAO-714 peer receipt, and the fixture asserted by Playwright.

The gate proves catalog normalization, dashboard UI wiring, mediated
tool-call receipts, Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks for the `ipfs_kit_py`,
`ipfs_datasets_py`, and `ipfs_accelerate_py` dashboard backends. It also keeps
daemon health, MCP++ telemetry, `tools/list`, `tools/call`, and
`control_surface` receipts in the same launch Playwright validation gate.

## DashboardInteroperabilityValidationGate

```json
{
  "schema": "mcp_dashboard_interoperability_gate_v1",
  "task_id": "VAI-531",
  "backlog_task_id": "HAO-714",
  "goal_id": "VAIOS-G723",
  "lineage_id": "VAIOS-G723:mcp-dashboard-interoperability",
  "evidence_term": "launch Playwright validation gate",
  "catalog_field": "dashboard_interoperability_validation_gate",
  "catalog_source": "hallucinate_app.node.mcp_daemon_manager.getDashboardCapabilityCatalog",
  "catalog_schema": "hallucinate_app.mcp_dashboard_capability_catalog.v1",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/vai-531-mcp-dashboard-interoperability-gate.json",
  "playwright_specs": [
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
  ],
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
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
  "child_goals": [
    "VAIOS-G723-C1 Catalog normalization",
    "VAIOS-G723-C2 Dashboard UI wiring",
    "VAIOS-G723-C3 Mediated tool-call receipts",
    "VAIOS-G723-C4 Swissknife consumers",
    "VAIOS-G723-C5 Playwright coverage",
    "VAIOS-G723-C6 Supervisor-generated follow-up subtasks"
  ],
  "follow_up_subtasks": [
    "HAO-678",
    "HAO-679",
    "HAO-680",
    "HAO-681",
    "HAO-682",
    "HAO-683"
  ],
  "validation_commands": [
    "npm --prefix hallucinate_app run test:daemon-manager",
    "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
    "npm --prefix swissknife run test:e2e:mcp",
    "test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses",
    "test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
  ],
  "failure_rule": "Any dashboard catalog, UI wiring, mediated tools/list, mediated tools/call, Swissknife consumer, backend validation, or Playwright failure remains supervisor-generated follow-up work for VAIOS-G723."
}
```
