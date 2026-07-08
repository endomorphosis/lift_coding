# MGW-581 Launch Playwright Validation Gate

Date: 2026-07-08
Task: MGW-581
Goal: VAIOS-G723
Schema: launch_readiness_receipt_v1
Lineage: VAIOS-G723:hallucinate-mcp-dashboard-interoperability-console
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-581-objective-gap-7ea369464239.md
Hallucinate mirror: data/hallucinate_multimodal_control/discovery/2026-07-08-mgw-581-mcp-dashboard-launch-gate.md
Fixture: hallucinate_app/test/e2e/fixtures/mgw-581-mcp-dashboard-launch-gate.json
Catalog fixture: hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json
Catalog source: hallucinate_app.node.mcp_daemon_manager.getDashboardCapabilityCatalog

## Gate

MGW-581 binds the current Meta glasses objective scan for the Hallucinate MCP
dashboard interoperability console to a non-skipped backend launch Playwright
validation gate. The Hallucinate App catalog exposes `MGW-581` in
`launch_validation_gates`, and the Playwright specs assert that the same
dashboard capability catalog is consumed by Swissknife applications.

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

## Backends

- ipfs_kit_py MCP server
- ipfs_datasets_py MCP server
- ipfs_accelerate_py MCP server

## Child Goals

- VAIOS-G723-C1 Catalog normalization
- VAIOS-G723-C2 Dashboard UI wiring
- VAIOS-G723-C3 Mediated tool-call receipts
- VAIOS-G723-C4 Swissknife consumers
- VAIOS-G723-C5 Playwright coverage
- VAIOS-G723-C6 Supervisor-generated follow-up subtasks

## Validation Commands

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)
npm --prefix swissknife run test:e2e:mcp
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

## Receipt Route

Hallucinate App dashboard action -> dashboard capability catalog ->
interaction_envelope -> policy_decision -> mediation_receipt -> supervised MCP
server transport -> Swissknife MCP dashboard capability registry.

Any MGW-581 dashboard catalog, UI wiring, mediated tools/list, mediated
tools/call, Swissknife consumer, backend validation, Playwright coverage, or
supervisor follow-up failure remains supervisor-generated follow-up work for
`VAIOS-G723`.

Any dashboard or backend validation failure remains supervisor-generated follow-up work for `VAIOS-G723`.
