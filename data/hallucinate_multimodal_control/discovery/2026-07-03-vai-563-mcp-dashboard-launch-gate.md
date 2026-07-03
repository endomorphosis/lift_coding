# VAI-563 Hallucinate MCP Dashboard Launch Gate

Date: 2026-07-03
Task: VAI-563
Goal id: VAIOS-G723
Lineage id: VAIOS-G723:hallucinate-mcp-dashboard-interoperability-console
Evidence term: launch Playwright validation gate
Virtual AI OS source: data/virtual_ai_os/discovery/2026-07-03-vai-563-mcp-dashboard-launch-gate.md

The Hallucinate supervisor mirror keeps the VAI-563 launch Playwright
validation gate aligned with the Hallucinate App MCP dashboard
interoperability console and the `VAIOS-G723` objective heap. VAI-563 repairs
the fixture drift that separated `vai-512-mcp-dashboard-catalog.json`,
`hao-719-daemon-launch-health-gate.json`, and
`hao-721-daemon-launch-health-gate.json` from the live dashboard capability
catalog and daemon launch health receipts after the `MGW-566` merge and the
`VAI-557` discovery-receipt append, and adds the missing
`2026-07-02-mgw-566-attempt-2-validation.md` Hallucinate mirror so the
`MGW-566` launch Playwright gate test can read it.

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

## Validation Results

- `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q` -> 127 passed, 1 warning.
- `npm --prefix hallucinate_app run test:daemon-manager` -> 10 passed.
- `npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts` -> 33 skipped, 37 passed. The skipped tests are display-dependent Electron UI tests; the backend launch Playwright validation gate was non-skipped and passed.
- `cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)` -> `missing_xvfb_for_electron_playwright` contract path accepted.
- `npm --prefix swissknife run test:e2e:mcp` -> 5 passed.
- `npm --prefix swissknife run test:e2e:meta-glasses` -> 6 passed.
- `npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts` -> 5 passed.

The shared fixture
`hallucinate_app/test/e2e/fixtures/vai-563-mcp-dashboard-launch-gate.json`
preserves child goals for catalog normalization, dashboard UI wiring, mediated
tool-call receipts, Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks. Any dashboard or backend validation
failure remains supervisor-generated follow-up work for `VAIOS-G723`.
