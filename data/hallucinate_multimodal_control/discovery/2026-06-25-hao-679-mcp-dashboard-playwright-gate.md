# HAO-679 MCP Dashboard Playwright Gate

VAI-503 closes the VAIOS-G723 missing evidence term `launch Playwright
validation gate` with `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`.

The gate covers the dashboard validation terms that HAO-676 and HAO-677 left for
follow-up: catalog normalization, dashboard UI wiring, mediated tool-call receipts,
Swissknife consumers, Playwright coverage, and supervisor-generated follow-up
subtasks if any dashboard or backend validation fails.

## Gate Fixture

```json
{
  "task_id": "HAO-679",
  "primary_task_id": "VAI-503",
  "goal_id": "VAIOS-G723",
  "artifact_id": "mcp_dashboard_interoperability_playwright_gate",
  "missing_evidence_closed": "launch Playwright validation gate",
  "playwright_spec": "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts",
  "playwright_command": "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
  "catalog_schema": "hallucinate_app.mcp_dashboard_capability_catalog.v1",
  "backend_services": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "safe_probe_receipt_terms": [
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
    "tools/list",
    "tools/call",
    "safe_probe",
    "receipt_cid"
  ],
  "swissknife_consumer_evidence": "swissknife/src/services/swissknife-mcp-capability-registry.ts",
  "follow_up_subtasks": [
    "HAO-678",
    "HAO-679",
    "HAO-680",
    "HAO-681",
    "HAO-682",
    "HAO-683"
  ],
  "failure_rule": "dashboard and backend validation failures remain supervisor-generated follow-up subtasks for VAIOS-G723"
}
```
