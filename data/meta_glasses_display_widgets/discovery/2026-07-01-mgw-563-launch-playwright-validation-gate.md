# MGW-563 Launch Playwright Validation Gate

Date: 2026-07-01
Task: MGW-563
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-07-01-mgw-563-objective-gap-7ea369464239.md

MGW-563 closes the current Meta glasses objective gap for the VAIOS-G723
Hallucinate MCP dashboard interoperability console by binding the supervisor
gap receipt to the executable Hallucinate App dashboard Playwright gate, the
shared dashboard capability catalog, and the Swissknife catalog consumer.

The focused launch Playwright validation gate is:

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

## Attempt 1 Validation Contract

MGW-563 attempt 1 makes the non-skipped backend launch gate explicit:

- `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q` proves the supervisor-fed backlog, objective heap, receipt fixture, and readiness references stay aligned.
- `npm --prefix hallucinate_app run test:daemon-manager` confirms the shared dashboard capability catalog for `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`.
- `npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts` is the Hallucinate App backend Playwright launch gate for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, and Playwright coverage.
- `cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)` preserves the no-display runner contract so missing Electron display infrastructure cannot masquerade as dashboard interoperability.
- `npm --prefix swissknife run test:e2e:mcp` proves Swissknife consumers read the same Hallucinate App dashboard capability catalog and MGW-563 receipt.
- `test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses` and `test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts` keep the Meta glasses and mediated `control_surface` receipts in the launch chain.

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
  MGW-563 launch gate in `launch_validation_gates` for `VAIOS-G723`.
- `hallucinate_app/test/e2e/fixtures/mgw-563-mcp-dashboard-launch-gate.json`
  records the `launch_readiness_receipt_v1` payload, required backends, child
  goals, follow-up subtasks, `tools/list`, `tools/call`, daemon health paths,
  and `control_surface receipts`.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` and
  `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` assert the
  MGW-563 catalog gate, fixture, receipt route, and discovery evidence.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` requires the same
  MGW-563 launch gate before Swissknife consumes the Hallucinate App dashboard
  capability catalog.
- `docs/launch/phone_desktop_glasses_readiness.md` and
  `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` preserve
  the supervisor-fed backlog alignment for `VAIOS-G723`.

Any dashboard catalog, UI wiring, mediated `tools/list`, mediated `tools/call`,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for `VAIOS-G723`.
