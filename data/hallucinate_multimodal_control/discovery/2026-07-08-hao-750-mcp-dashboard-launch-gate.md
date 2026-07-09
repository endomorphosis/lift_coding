# HAO-750 MCP Dashboard Launch Gate

Date: 2026-07-08
Task: HAO-750
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Gate state: gate_open_until_playwright_passes
Source gap: data/hallucinate_multimodal_control/discovery/2026-07-08-hao-750-objective-gap-7ea369464239.md
Todo source: hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md:9569

HAO-750 closes the Hallucinate MCP dashboard interoperability console gap by
binding the shared Hallucinate App dashboard capability catalog, backend service
catalog, daemon health, MCP++ telemetry, mediated `tools/list`, mediated
`tools/call`, `control_surface receipts`, and Swissknife consumers to the launch
Playwright validation gate for `ipfs_kit_py`, `ipfs_datasets_py`, and
`ipfs_accelerate_py`.

## Required Evidence

- Hallucinate App menus
- Hallucinate App MCP dashboard
- dashboard capability catalog
- backend service catalog
- daemon health
- MCP++ telemetry
- tools/list
- tools/call
- control_surface receipts
- Swissknife applications
- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- launch Playwright validation gate

## Child Goals

- VAIOS-G723-C1 Catalog normalization
- VAIOS-G723-C2 Dashboard UI wiring
- VAIOS-G723-C3 Mediated tool-call receipts
- VAIOS-G723-C4 Swissknife consumers
- VAIOS-G723-C5 Playwright coverage
- VAIOS-G723-C6 Supervisor-generated follow-up subtasks

## Validation Gate

```sh
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)
npm --prefix swissknife run test:e2e:mcp
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

## Catalog Contract

```json
{
  "schema": "launch_readiness_receipt_v1",
  "task_id": "HAO-750",
  "goal_id": "VAIOS-G723",
  "lineage_id": "VAIOS-G723:hallucinate-mcp-dashboard-interoperability-console",
  "source_gap_receipt": "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-750-objective-gap-7ea369464239.md",
  "launch_gate_receipt": "data/hallucinate_multimodal_control/discovery/2026-07-08-hao-750-mcp-dashboard-launch-gate.md",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/hao-750-mcp-dashboard-launch-gate.json",
  "catalog_fixture": "hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json",
  "catalog_schema": "hallucinate_app.mcp_dashboard_capability_catalog.v1",
  "catalog_generated_by": "hallucinate_app.node.mcp_daemon_manager.getDashboardCapabilityCatalog",
  "evidence_term": "launch Playwright validation gate",
  "gate_state": "gate_open_until_playwright_passes",
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ]
}
```

## Evidence Files

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` emits the HAO-750 `launch_validation_gates` entry from `getDashboardCapabilityCatalog`.
- `hallucinate_app/test/e2e/fixtures/hao-750-mcp-dashboard-launch-gate.json` snapshots the HAO-750 gate from the production catalog.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json` snapshots the shared dashboard capability catalog consumed by Hallucinate App and Swissknife.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` asserts the Electron and headless dashboard capability catalog expose HAO-750.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` validates this receipt, the objective gap receipt, the JSON fixture, the objective heap proof, and the launch readiness document.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` asserts Swissknife consumes the same HAO-750 catalog entry and headless Playwright validation command.

## Failure Rule

Any HAO-750 catalog normalization, dashboard UI wiring, mediated `tools/list`,
mediated `tools/call`, Swissknife consumer, backend validation, Playwright
coverage, or supervisor-generated follow-up subtasks failure remains
supervisor-fed launch work for VAIOS-G723.
