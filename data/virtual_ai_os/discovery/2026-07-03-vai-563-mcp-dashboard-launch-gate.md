# VAI-563 MCP Dashboard Launch Gate

Date: 2026-07-03
Task: VAI-563
Goal id: VAIOS-G723
Lineage id: VAIOS-G723:hallucinate-mcp-dashboard-interoperability-console
Evidence term: launch Playwright validation gate
Source gap: data/virtual_ai_os/discovery/2026-07-03-vai-563-objective-gap-7ea369464239.md

VAI-563 closes the current Virtual AI OS objective gap for the Hallucinate MCP
dashboard interoperability console by binding the scanner-visible objective
receipt to the existing Hallucinate App dashboard Playwright gate. The fixture
drift that previously separated `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json`,
`hallucinate_app/test/e2e/fixtures/hao-719-daemon-launch-health-gate.json`, and
`hallucinate_app/test/e2e/fixtures/hao-721-daemon-launch-health-gate.json`
from the live dashboard capability catalog and daemon launch health receipts
is repaired: every fixture is regenerated from the shared
`MCPDaemonManager.getDashboardCapabilityCatalog()` output and the discovery
receipts they mirror.

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
  `VAI-563` launch gate in the shared dashboard capability catalog, cloned
  from the `MGW-566` gate contract.
- `hallucinate_app/test/e2e/fixtures/vai-563-mcp-dashboard-launch-gate.json`
  records the matching launch readiness receipt for `VAIOS-G723`.
- `hallucinate_app/test/e2e/fixtures/vai-512-mcp-dashboard-catalog.json` is
  regenerated from the live catalog so it stays in parity with the Hallucinate
  manager (previously drifted after the `MGW-566` merge inserted its gate at
  the end of `DASHBOARD_LAUNCH_VALIDATION_GATES` instead of before `MGW-555`).
- `hallucinate_app/test/e2e/fixtures/hao-719-daemon-launch-health-gate.json`
  and `hallucinate_app/test/e2e/fixtures/hao-721-daemon-launch-health-gate.json`
  are regenerated from `data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-daemon-launch-health-gate.md`
  and `data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-daemon-launch-health-gate.md`
  so `tests/test_hallucinate_multimodal_control_todo_queue.py::test_hao_719_and_hao_721_daemon_launch_gates_align_with_objective_heap`
  passes after `VAI-557` appended to the shared `discovery_receipts` and
  `objective_gap_receipts` lists.
- `data/hallucinate_multimodal_control/discovery/2026-07-02-mgw-566-attempt-2-validation.md`
  is added so `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`
  can read the MGW-566 attempt-2 Hallucinate validation mirror referenced by
  `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` and
  `docs/launch/phone_desktop_glasses_readiness.md`.
- `data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-566-objective-gap-7ea369464239.md`
  gains a `## Gap Closure Evidence` section covering `catalog normalization`,
  `dashboard UI wiring`, `mediated tool-call receipts`, `Swissknife
  consumers`, `Playwright coverage`, and `supervisor-generated follow-up
  subtasks` so the MGW-566 dashboard launch Playwright gate test can assert
  those terms directly against the objective gap receipt.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`,
  `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts`, and
  `swissknife/scripts/test-mcp-dashboard-consumer.cjs` assert the gate against
  the live catalog, `tools/list`, `tools/call`, daemon health paths, mediated
  receipts, and the three IPFS MCP package dashboards.

## Gate State

Any dashboard catalog, UI wiring, mediated `tools/list`, mediated `tools/call`,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for `VAIOS-G723`.
