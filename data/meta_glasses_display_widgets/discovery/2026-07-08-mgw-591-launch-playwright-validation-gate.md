# MGW-591 Launch Playwright Validation Gate

Date: 2026-07-08
Task: MGW-591
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-591-objective-gap-7ea369464239.md

MGW-591 closes the current Meta glasses objective gap for the VAIOS-G723
Hallucinate MCP dashboard interoperability console by repairing the three
concrete defects that were blocking the launch Playwright validation gate in
this worktree, then binding the supervisor gap receipt to the executable
Hallucinate App dashboard Playwright gate, the shared dashboard capability
catalog, and the Swissknife catalog consumer.

## Repaired Defects

1. `swissknife/src/services/swissknife-mcp-capability-registry.ts` was
   missing from this worktree's `swissknife` checkout (only
   `swissknife/src/services/apps/swissknife-mcp-capability-registry.ts`
   existed), which failed
   `tests/test_hallucinate_multimodal_control_todo_queue.py::test_hao_674_integrates_mcp_launch_contracts_with_swissknife_control_surface`
   and
   `tests/test_virtual_ai_os_todo_queue.py::test_vai_503_mcp_dashboard_interoperability_gate_closes_objective_gap`.
   Restored the root-path compatibility re-export so both HAO-674 and VAI-503
   supervisor receipts resolve `SwissknifeMCPLaunchContract`,
   `mcp_plus_plus_advertisement`, `control_surface_route`,
   `buildSwissknifeMCPMediatedInvocationPlan`, and
   `CONTROL_SURFACE_DAEMON_MEDIATION` for `ipfs_kit_py`, `ipfs_datasets_py`,
   and `ipfs_accelerate_py`.
2. `data/swissknife_virtual_desktop/all_tools_supervisor_queue.json` was
   missing even though `implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md`
   documents it as the SVD-037/SVD-041 supervisor queue output, which failed
   `tests/test_virtual_ai_os_todo_queue.py::test_swissknife_all_tools_supervisor_queue_is_resumable`.
   Rebuilt the queue from the SVD-027 through SVD-050 taskboard entries with
   the documented completed/ready/waiting/blocked task ids, dependency graph,
   and resume contract.
3. `swissknife/web/js/apps/mcp-control.js` and
   `swissknife/web/js/apps/p2p-network.js` imported
   `BROWSER_LIBP2P_DEFAULT_CAPABILITY_ORDER` and
   `getBrowserLibp2pDefaultStatus` directly from
   `../../../src/services/mcp/libp2p-browser-runtime.ts`, which the
   SwissKnife desktop web bundle cannot resolve because it is served as
   static files (`python3 -m http.server`) without a TypeScript build step,
   and neither export even existed on the canonical module. This produced
   `"Failed to fetch dynamically imported module"` load errors for the
   `mcp-control` and `p2p-network` desktop apps and failed
   `npm --prefix swissknife run test:e2e:meta-glasses`. Added the missing
   exports (plus a `getBrowserLibp2pDefaultStatus` helper) to
   `src/services/mcp/libp2p-browser-runtime.ts`, and added a hand-maintained
   plain-JS mirror at `swissknife/web/js/libp2p-browser-runtime.js` (matching
   the existing `MCP_DASHBOARD_BROWSER_POLICY` mirroring convention) so the
   two desktop apps import a browser-loadable module instead.

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

MGW-591 attempt 1 records the full launch readiness validation pass after the
repairs above:

- `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q` (197 passed) proves the supervisor-fed backlog, objective heap, receipt fixture, and readiness references stay aligned.
- `npm --prefix hallucinate_app run test:daemon-manager` (10 passed) confirms the shared dashboard capability catalog for `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`.
- `npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts` (100 passed, 33 skipped for missing display server) is the Hallucinate App backend Playwright launch gate for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, and Playwright coverage.
- `cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)` (`missing_xvfb_for_electron_playwright`, exit 78) preserves the no-display runner contract so missing Electron display infrastructure cannot masquerade as dashboard interoperability.
- `npm --prefix swissknife run test:e2e:mcp` (5 passed) proves Swissknife consumers read the same Hallucinate App dashboard capability catalog and MGW-591 receipt.
- `npm --prefix swissknife run test:e2e:meta-glasses` (35 passed) proves the mcp-control and p2p-network desktop apps render without load-error markers after the libp2p browser-runtime mirror repair.
- `npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts` (5 passed) keeps the mediated `control_surface` receipts in the launch chain.

## Covered Terms

- hallucinate_app menus
- Hallucinate App MCP dashboard
- dashboard capability catalog
- daemon health
- tools/list
- tools/call
- ipfs_accelerate_py MCP server
- ipfs_datasets_py MCP server
- ipfs_kit_py MCP server
- Swissknife applications
- Playwright MCP dashboard interoperability
- launch Playwright validation gate

## Child Goals

- VAIOS-G723-C1 Catalog normalization
- VAIOS-G723-C2 Dashboard UI wiring
- VAIOS-G723-C3 Mediated tool-call receipts
- VAIOS-G723-C4 Swissknife consumers
- VAIOS-G723-C5 Playwright coverage
- VAIOS-G723-C6 Supervisor-generated follow-up subtasks

## Evidence

- `swissknife/src/services/swissknife-mcp-capability-registry.ts` restores the
  root-path compatibility re-export for HAO-674/VAI-503 supervisor receipts.
- `data/swissknife_virtual_desktop/all_tools_supervisor_queue.json` restores
  the SVD-027 through SVD-050 resumable supervisor queue.
- `swissknife/src/services/mcp/libp2p-browser-runtime.ts` and
  `swissknife/web/js/libp2p-browser-runtime.js` fix the browser libp2p
  capability status panel used by `mcp-control` and `p2p-network`.
- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes the
  MGW-591 launch gate in `launch_validation_gates` for `VAIOS-G723`.
- `hallucinate_app/test/e2e/fixtures/mgw-591-mcp-dashboard-launch-gate.json`
  records the `launch_readiness_receipt_v1` payload, required backends, child
  goals, follow-up subtasks, `tools/list`, `tools/call`, daemon health paths,
  and `control_surface receipts`.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts`,
  `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`, and
  `swissknife/scripts/test-mcp-dashboard-consumer.cjs` assert catalog
  normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife
  consumers, and Playwright coverage for `VAIOS-G723`.
- `docs/launch/phone_desktop_glasses_readiness.md` and
  `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` bind the
  MGW-591 receipt into the shared launch readiness narrative.
