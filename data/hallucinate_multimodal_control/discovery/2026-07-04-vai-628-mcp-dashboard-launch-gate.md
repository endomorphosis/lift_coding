# VAI-628 Hallucinate MCP Dashboard Launch Gate

Date: 2026-07-04
Task: VAI-628
Goal id: VAIOS-G723
Lineage id: VAIOS-G723:hallucinate-mcp-dashboard-interoperability-console
Evidence term: launch Playwright validation gate
Virtual AI OS source: data/virtual_ai_os/discovery/2026-07-04-vai-628-mcp-dashboard-launch-gate.md

The Hallucinate supervisor mirror keeps the VAI-628 launch Playwright
validation gate aligned with the Hallucinate App MCP dashboard interoperability
console and the `VAIOS-G723` objective heap.

## Covered Terms

- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
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
- launch Playwright validation gate

## Child Goals

- VAIOS-G723-C1 Catalog normalization
- VAIOS-G723-C2 Dashboard UI wiring
- VAIOS-G723-C3 Mediated tool-call receipts
- VAIOS-G723-C4 Swissknife consumers
- VAIOS-G723-C5 Playwright coverage
- VAIOS-G723-C6 Supervisor-generated follow-up subtasks

## Validation Chain

```text
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)
npm --prefix swissknife run test:e2e:mcp
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

The shared fixture
`hallucinate_app/test/e2e/fixtures/vai-628-mcp-dashboard-launch-gate.json`
preserves child goals for catalog normalization, dashboard UI wiring, mediated
tool-call receipts, Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks. Any dashboard or backend validation
failure remains supervisor-generated follow-up work for `VAIOS-G723`.
