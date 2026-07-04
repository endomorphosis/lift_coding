# VAI-610 MCP Dashboard Launch Gate

Date: 2026-07-04
Task: VAI-610
Goal id: VAIOS-G723
Lineage id: VAIOS-G723:hallucinate-mcp-dashboard-interoperability-console
Evidence term: launch Playwright validation gate
Source gap: data/virtual_ai_os/discovery/2026-07-04-vai-610-objective-gap-7ea369464239.md

VAI-610 closes the current Virtual AI OS objective gap for the Hallucinate MCP
dashboard interoperability console by binding the objective-scan receipt to the
shared dashboard capability catalog, the Hallucinate App launch Playwright
validation gate, mediated tool-call receipt coverage, and the Swissknife MCP
dashboard consumer gate.

The focused dashboard gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full supervisor validation chain is:

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

## Child Goals

- VAIOS-G723-C1 Catalog normalization
- VAIOS-G723-C2 Dashboard UI wiring
- VAIOS-G723-C3 Mediated tool-call receipts
- VAIOS-G723-C4 Swissknife consumers
- VAIOS-G723-C5 Playwright coverage
- VAIOS-G723-C6 Supervisor-generated follow-up subtasks

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes the
  `VAI-610` launch gate in `getDashboardCapabilityCatalog`.
- `hallucinate_app/test/e2e/fixtures/vai-610-mcp-dashboard-launch-gate.json`
  records the matching `launch_readiness_receipt_v1` receipt for `VAIOS-G723`.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json` is
  regenerated from the live catalog so Hallucinate App and Swissknife consume
  one shared dashboard capability catalog.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts
  the VAI-610 catalog entry, receipt fixture, objective-gap receipt, launch
  gate receipt, Hallucinate supervisor mirror, attempt-1 validation receipts,
  objective heap, readiness doc, and all dashboard server handoff records.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` asserts that Swissknife
  consumers see the same VAI-610 catalog entry, child goals, follow-up
  subtasks, required evidence terms, and attempt receipts.

## Gate State

Any VAI-610 dashboard catalog, dashboard UI wiring, mediated `tools/list`,
mediated `tools/call`, Swissknife consumer, backend validation, Playwright
coverage, or supervisor follow-up failure remains supervisor-generated
follow-up work for `VAIOS-G723`.
