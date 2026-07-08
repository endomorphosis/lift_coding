# MGW-581 Attempt 1 Launch Playwright Validation Gate

Date: 2026-07-08
Task: MGW-581
Goal: VAIOS-G723
Evidence term: launch Playwright validation gate
Fixture: hallucinate_app/test/e2e/fixtures/mgw-581-mcp-dashboard-launch-gate.json

Attempt 1 records the deterministic validation gate for the MGW-581
Hallucinate MCP dashboard interoperability console. The gate covers Hallucinate
App menus, Hallucinate App MCP dashboard, dashboard capability catalog, backend
service catalog, daemon health, MCP++ telemetry, tools/list, tools/call,
control_surface receipts, Swissknife applications, catalog normalization,
dashboard UI wiring, mediated tool-call receipts, Swissknife consumers,
Playwright coverage, supervisor-generated follow-up subtasks, and launch
Playwright validation gate evidence for ipfs_kit_py MCP server,
ipfs_datasets_py MCP server, and ipfs_accelerate_py MCP server.

Required evidence closure:

- Hallucinate App menus
- Hallucinate App MCP dashboard
- dashboard capability catalog
- backend service catalog
- daemon health
- MCP++ telemetry
- tools/list
- tools/call
- control_surface receipts
- ipfs_kit_py MCP server
- ipfs_datasets_py MCP server
- ipfs_accelerate_py MCP server
- Swissknife applications
- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- launch Playwright validation gate

Validation packet:

```bash
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)
npm --prefix swissknife run test:e2e:mcp
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

On supervisor hosts without a display server, Electron UI dashboard cases may
emit the expected missing_xvfb_for_electron_playwright diagnostic while the
backend/static mcp-feature-exposure.spec.ts and mcp-dashboard-interoperability.spec.ts
launch gate remains executable. Any dashboard or backend validation failure
continues as supervisor-generated follow-up work for `VAIOS-G723` under
VAIOS-G723-C6 Supervisor-generated follow-up subtasks.
