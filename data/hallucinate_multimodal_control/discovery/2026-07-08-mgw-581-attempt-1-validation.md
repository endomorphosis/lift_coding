# MGW-581 Attempt 1 Hallucinate Validation Mirror

Date: 2026-07-08
Task: MGW-581
Goal: VAIOS-G723
Evidence term: launch Playwright validation gate
Fixture: hallucinate_app/test/e2e/fixtures/mgw-581-mcp-dashboard-launch-gate.json

This Hallucinate mirror records the attempt-1 validation packet for the
MGW-581 dashboard launch gate. It keeps the backlog/objective queue command,
Hallucinate daemon-manager catalog check, Hallucinate MCP dashboard backend
Playwright gate, no-display Playwright runner contract, Swissknife MCP
dashboard consumer gate, Swissknife Meta glasses gate, and Hallucinate
multimodal control_surface gate aligned for VAIOS-G723.

The gate requires Hallucinate App menus, Hallucinate App MCP dashboard,
dashboard capability catalog, backend service catalog, daemon health, MCP++
telemetry, tools/list, tools/call, control_surface receipts, Swissknife
applications, catalog normalization, dashboard UI wiring, mediated tool-call
receipts, Swissknife consumers, Playwright coverage, supervisor-generated
follow-up subtasks, and launch Playwright validation gate evidence for
ipfs_kit_py MCP server, ipfs_datasets_py MCP server, and ipfs_accelerate_py MCP
server.

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

Failures in dashboard catalog normalization, dashboard UI wiring, mediated
tools/list, mediated tools/call, Swissknife consumers, backend validation,
Playwright coverage, or the control_surface gate remain supervisor-generated
follow-up work for `VAIOS-G723`.
