# MGW-546 Launch Playwright Validation Gate

Task: MGW-546
Goal id: VAIOS-G723
Track: launch

The objective gap receipt at
`data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-546-objective-gap-7ea369464239.md`
is bound to the Hallucinate MCP dashboard interoperability console and the
shared `launch Playwright validation gate`.

Required evidence terms covered by this gate:

- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- launch Playwright validation gate
- tools/list
- tools/call

The fixture
`hallucinate_app/test/e2e/fixtures/mgw-546-mcp-dashboard-launch-gate.json`
asserts the same dashboard capability catalog, daemon health, MCP++ telemetry,
`tools/list`, `tools/call`, and Swissknife consumer refs that
`hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` validates.

Validation:

```bash
npm --prefix hallucinate_app run test:daemon-manager
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
npm --prefix swissknife run test:e2e:mcp
```
