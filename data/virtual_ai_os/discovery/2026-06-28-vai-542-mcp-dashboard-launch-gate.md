# VAI-542 MCP Dashboard Launch Gate

Date: 2026-06-28
Task: VAI-542
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/virtual_ai_os/discovery/2026-06-28-vai-542-objective-gap-7ea369464239.md
Hallucinate follow-up: HAO-724

## Gate

VAI-542 keeps the Hallucinate App MCP dashboard interoperability console aligned
with the objective heap and the supervisor-fed backlog. The focused launch gate
is:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full validation set remains:

```text
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)
npm --prefix swissknife run test:e2e:mcp
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

## Child Goals

- VAIOS-G723-C1 Catalog normalization
- VAIOS-G723-C2 Dashboard UI wiring
- VAIOS-G723-C3 Mediated tool-call receipts
- VAIOS-G723-C4 Swissknife consumers
- VAIOS-G723-C5 Playwright coverage
- VAIOS-G723-C6 Supervisor-generated follow-up subtasks

## Covered Evidence

- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- daemon health
- MCP++ telemetry
- tools/list
- tools/call
- control_surface receipts
- launch Playwright validation gate

## Proof

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes the
  `VAI-542` dashboard validation gate in the shared catalog.
- `hallucinate_app/test/e2e/fixtures/vai-542-mcp-dashboard-launch-gate.json`
  records the matching receipt schema and child goals.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` and
  `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` assert the
  gate against the generated catalog, mediated receipts, and objective heap.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` requires Swissknife to
  consume the same VAI-542 catalog entry.

## Gate State

Any dashboard catalog, UI wiring, mediated tools/list, mediated tools/call,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for VAIOS-G723.
