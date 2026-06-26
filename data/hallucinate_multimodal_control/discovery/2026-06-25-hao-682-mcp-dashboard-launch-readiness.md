# HAO-682 MCP Dashboard Launch Readiness

HAO-682 aggregates the Hallucinate MCP dashboard interoperability evidence for
VAIOS-G723 and VAI-503. It closes the scanner-visible `launch Playwright
validation gate` gap by tying the shared dashboard capability catalog, mediated
tool-call receipts, Swissknife consumers, and Playwright gate to one launch
readiness receipt.

## Receipt

```json
{
  "schema": "launch_readiness_receipt_v1",
  "task_id": "HAO-682",
  "vai_task_id": "VAI-503",
  "goal_id": "VAIOS-G723",
  "lineage_id": "VAIOS-G723:mcp-dashboard-interoperability",
  "evidence_term": "launch Playwright validation gate",
  "gate_state": "gate_open_until_playwright_passes",
  "playwright_specs": [
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
  ],
  "validation_commands": [
    "npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts",
    "npm --prefix swissknife run test:e2e:mcp"
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
    "supervisor-generated follow-up subtasks"
  ],
  "catalog_schema": "hallucinate_app.mcp_dashboard_capability_catalog.v1",
  "receipt_route": [
    "Hallucinate App dashboard action",
    "dashboard capability catalog",
    "interaction_envelope",
    "policy_decision",
    "mediation_receipt",
    "supervised MCP server transport"
  ],
  "follow_up_subtasks": [
    "HAO-678",
    "HAO-679",
    "HAO-680",
    "HAO-681",
    "HAO-682",
    "HAO-683"
  ],
  "failure_rule": "Any dashboard, backend, receipt, Swissknife consumer, or Playwright validation failure remains supervisor-generated follow-up work for VAIOS-G723."
}
```

## Gate Contract

The Hallucinate App Playwright command must prove the dashboard feature exposure
spec and the dashboard interoperability spec together. In a display-capable
environment, the Electron UI tests open the three dashboard menu entries,
observe daemon/catalog-backed dashboard controls, and verify visible preload
bridge receipts. In a headless environment, the backend gate still executes the
catalog normalization, safe tools/call mediation, Swissknife consumer, and
supervisor follow-up assertions so the launch gate cannot pass on a missing
catalog or receipt path.

The Swissknife consumer command proves the same `ipfs_kit_py`,
`ipfs_datasets_py`, and `ipfs_accelerate_py` catalog entries and receipt aliases
are visible to Swissknife applications. Failures in either command stay attached
to HAO-678 through HAO-683 for catalog normalization, dashboard UI wiring,
mediated tool-call receipts, Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks.
