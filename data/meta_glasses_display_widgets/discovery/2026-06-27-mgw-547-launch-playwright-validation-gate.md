# MGW-547 Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-547
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-547-objective-gap-7ea369464239.md

## Gate

MGW-547 closes the objective gap for the Hallucinate MCP dashboard
interoperability console by binding `VAIOS-G723` to the same launch Playwright
validation gate used by the shared dashboard catalog:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The full launch validation chain also keeps Swissknife, Meta glasses, and
multimodal control-surface consumers in scope:

```text
npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes `MGW-547` in `launch_validation_gates` without changing the primary MGW-533 catalog gate.
- `hallucinate_app/test/e2e/fixtures/mgw-547-mcp-dashboard-launch-gate.json` records the `launch_readiness_receipt_v1` for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the MGW-547 gap receipt, this launch receipt, the Hallucinate backlog receipt, the objective heap proof, the readiness doc, the dashboard capability catalog, daemon health, `tools/list`, `tools/call`, and the three backend packages.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` verifies Swissknife consumes the same dashboard catalog gate entry.
- Attempt 11 receipts, `data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-547-attempt-11-launch-playwright-validation-gate.md` and `data/hallucinate_multimodal_control/discovery/2026-06-28-mgw-547-attempt-11-launch-playwright-validation-gate.md`, are exposed from that same `MGW-547` catalog gate entry so the supervisor-fed backlog remains aligned with the objective heap.

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

## Failure Rule

Any dashboard catalog, UI wiring, mediated `tools/list`, mediated `tools/call`,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for `VAIOS-G723`.
