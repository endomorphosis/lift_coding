# MGW-547 Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-547
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-547-objective-gap-7ea369464239.md

## Gate

MGW-547 binds the Hallucinate MCP dashboard interoperability console to the
launch Playwright validation gate and keeps the supervisor-fed backlog aligned
with the VAIOS-G723 objective heap.

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

## Evidence

- `hallucinate_app/test/e2e/fixtures/mgw-547-mcp-dashboard-launch-gate.json`
  records the `VAIOS-G723` launch-readiness receipt for attempt 5.
- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes MGW-547
  in the shared dashboard capability catalog `launch_validation_gates`.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the
  receipt against the dashboard capability catalog, daemon health paths,
  `tools/list`, `tools/call`, mediated control_surface receipts, and
  Swissknife consumers.
- `swissknife/scripts/test-mcp-dashboard-consumer.cjs` verifies Swissknife sees
  the same MGW-547 launch gate through the shared catalog.

## Covered Terms

- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- launch Playwright validation gate
- tools/list
- tools/call
