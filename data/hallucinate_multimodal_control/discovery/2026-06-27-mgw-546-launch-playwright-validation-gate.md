# MGW-546 Hallucinate Launch Playwright Validation Gate

Task: MGW-546
Goal id: VAIOS-G723
Track: launch

The Hallucinate backlog mirrors the MGW-546 dashboard interoperability gate so
failed launch validation remains supervisor-generated follow-up work for the
Hallucinate MCP dashboard interoperability console.

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

The gate uses
`hallucinate_app/test/e2e/fixtures/mgw-546-mcp-dashboard-launch-gate.json` and
`hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` to bind the
dashboard capability catalog, daemon health, MCP++ telemetry, mediated
`tools/list`, mediated `tools/call`, and Swissknife consumer refs back to the
shared launch readiness packet.

Validation:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```
