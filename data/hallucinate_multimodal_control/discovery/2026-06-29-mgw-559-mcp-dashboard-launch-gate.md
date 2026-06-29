# MGW-559 MCP Dashboard Launch Gate

Date: 2026-06-29
Task: MGW-559
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-06-29-mgw-559-objective-gap-7ea369464239.md
Meta launch gate: data/meta_glasses_display_widgets/discovery/2026-06-29-mgw-559-launch-playwright-validation-gate.md

This Hallucinate supervisor mirror keeps the MGW-559 objective gap aligned with
the VAIOS-G723 Hallucinate MCP dashboard interoperability console. The shared
dashboard capability catalog remains the source consumed by Hallucinate App
dashboards, Swissknife applications, and downstream launch-readiness gates.

The executable launch Playwright validation gate is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full validation chain remains:

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
  MGW-559 launch gate and the shared dashboard capability catalog.
- `hallucinate_app/test/e2e/fixtures/mgw-559-mcp-dashboard-launch-gate.json`
  records the launch readiness receipt for the three Python MCP backends:
  `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`,
  `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts`, and
  `swissknife/scripts/test-mcp-dashboard-consumer.cjs` assert catalog
  normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife
  consumers, Playwright coverage, daemon health, MCP++ telemetry, `tools/list`,
  `tools/call`, and `control_surface receipts`.

Any dashboard catalog, UI wiring, mediated `tools/list`, mediated `tools/call`,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for `VAIOS-G723`.
