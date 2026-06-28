# MGW-546 Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-546
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate
Source gap: data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-546-objective-gap-7ea369464239.md

## Gate

MGW-546 binds the Hallucinate MCP dashboard interoperability console to the
launch Playwright validation gate and its child goal evidence.

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

## Evidence

- `hallucinate_app/test/e2e/fixtures/mgw-546-mcp-dashboard-launch-gate.json`
  records the `VAIOS-G723` launch-readiness receipt.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the
  receipt against the shared dashboard capability catalog, daemon health paths,
  `tools/list`, `tools/call`, control_surface receipts, and Swissknife
  consumers.
- The child goals remain attached to catalog normalization, dashboard UI
  wiring, mediated tool-call receipts, Swissknife consumers, Playwright
  coverage, and supervisor-generated follow-up subtasks.

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

