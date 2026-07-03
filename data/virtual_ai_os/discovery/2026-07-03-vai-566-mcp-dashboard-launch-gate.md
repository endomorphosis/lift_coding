# VAI-566 MCP Dashboard Launch Gate

Date: 2026-07-03
Task: VAI-566
Goal id: VAIOS-G723
Lineage id: VAIOS-G723:hallucinate-mcp-dashboard-interoperability-console
Evidence term: launch Playwright validation gate
Source gap: data/virtual_ai_os/discovery/2026-07-03-vai-566-objective-gap-7ea369464239.md

VAI-566 closes the current Virtual AI OS objective gap for the Hallucinate MCP
dashboard interoperability console by binding the scanner-visible objective
receipt (`data/virtual_ai_os/discovery/2026-07-03-vai-566-objective-gap-7ea369464239.md`)
to the existing Hallucinate App dashboard Playwright gate. The shared
dashboard capability catalog produced by
`MCPDaemonManager.getDashboardCapabilityCatalog()` now carries a dedicated
`VAI-566` entry in `launch_validation_gates`, cloned from the `VAI-563` gate
contract so the catalog normalization, dashboard UI wiring, mediated
tool-call receipt, Swissknife consumer, Playwright coverage, and
supervisor-generated follow-up subtask evidence stay additive across every
attempt in the `VAIOS-G723` lineage.

The launch gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full supervisor packet also keeps the Swissknife and multimodal gates in
the same validation chain:

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
  `VAI-566` launch gate in the shared dashboard capability catalog, cloned
  from the `VAI-563` gate contract and appended to
  `DASHBOARD_LAUNCH_VALIDATION_GATES`.
- `hallucinate_app/test/e2e/fixtures/vai-566-mcp-dashboard-launch-gate.json`
  records the matching launch readiness receipt for `VAIOS-G723`.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json` is
  regenerated from the live `getDashboardCapabilityCatalog()` output so it
  stays in parity with the Hallucinate manager after the `VAI-566` gate is
  appended.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` asserts the `VAI-566`
  gate against the live catalog, the receipt fixture, and the shared
  `VAIOS-G723` child goals and follow-up subtasks.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` and
  `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` assert the gate
  against the live catalog, `tools/list`, `tools/call`, daemon health paths,
  mediated receipts, and the three IPFS MCP package dashboards.
- `tests/test_virtual_ai_os_todo_queue.py::test_vai_566_mcp_dashboard_launch_gate_keeps_vaios_g723_aligned`
  proves the `VAI-566` fixture, discovery receipts, objective heap, launch
  readiness doc, Playwright spec, and Swissknife consumer script all stay
  aligned.

## Gate State

Any dashboard catalog, UI wiring, mediated `tools/list`, mediated `tools/call`,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for `VAIOS-G723`.
