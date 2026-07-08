# HAO-729 MCP Dashboard Launch Gate

Date: 2026-07-08
Task: HAO-729
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Gate state: gate_closed_by_playwright_validation
Source gap: data/hallucinate_multimodal_control/discovery/2026-06-30-hao-729-objective-gap-7ea369464239.md
Receipt: data/hallucinate_multimodal_control/discovery/2026-07-08-hao-729-mcp-dashboard-launch-gate.md
Fixture: hallucinate_app/test/e2e/fixtures/hao-729-mcp-dashboard-launch-gate.json

HAO-729 proof: HAO-729 closes the current Hallucinate supervisor objective gap for the
VAIOS-G723 Hallucinate MCP dashboard interoperability console. The gate keeps
the Hallucinate App dashboard capability catalog, backend service catalog,
daemon health, MCP++ telemetry, `tools/list`, `tools/call`, control_surface
receipts, and Swissknife applications on one launch Playwright validation gate.

The executable Hallucinate MCP dashboard gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full validation chain is:

```text
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)
npm --prefix swissknife run test:e2e:mcp
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

## Covered Terms

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
- headless-safe launch Playwright validation gate
- gate_closed_by_playwright_validation

## Child Goals

- VAIOS-G723-C1 Catalog normalization
- VAIOS-G723-C2 Dashboard UI wiring
- VAIOS-G723-C3 Mediated tool-call receipts
- VAIOS-G723-C4 Swissknife consumers
- VAIOS-G723-C5 Playwright coverage
- VAIOS-G723-C6 Supervisor-generated follow-up subtasks

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes HAO-729
  in the shared `launch_validation_gates` catalog.
- `hallucinate_app/test/e2e/fixtures/hao-729-mcp-dashboard-launch-gate.json`
  records the matching launch readiness receipt.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json`
  snapshots the same HAO-729 gate for Playwright and Swissknife consumers.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` and
  `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` cover the
  catalog normalization, dashboard UI wiring, daemon health, `tools/list`,
  `tools/call`, mediated tool-call receipts, and Playwright coverage.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` proves Swissknife
  consumers see the same HAO-729 dashboard catalog and receipt fixture.

Any HAO-729 dashboard catalog, UI wiring, mediated `tools/list`, mediated `tools/call`, Swissknife consumer, backend validation, headless Playwright, or supervisor follow-up failure remains supervisor-generated follow-up work for `VAIOS-G723`.
