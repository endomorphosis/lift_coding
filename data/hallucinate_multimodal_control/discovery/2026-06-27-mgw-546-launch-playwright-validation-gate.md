# MGW-546 Hallucinate Backlog Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-546
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

This Hallucinate backlog mirror keeps the MGW-546 dashboard interoperability
gate visible to the HAO supervisor. It uses the same Hallucinate MCP dashboard
interoperability console evidence as the MGW receipt and preserves the
VAIOS-G723 child goals for any failed dashboard or backend validation.

## Evidence

- Hallucinate MCP dashboard interoperability console
- dashboard capability catalog
- daemon health
- MCP++ telemetry
- tools/list
- tools/call
- control_surface receipts
- catalog normalization
- dashboard UI wiring
- mediated tool-call receipts
- Swissknife consumers
- Playwright coverage
- supervisor-generated follow-up subtasks
- launch Playwright validation gate
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts`
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`
- `npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts`
- `npm --prefix swissknife run test:e2e:mcp`

Any dashboard catalog, UI wiring, mediated tools/list, mediated tools/call,
Swissknife consumer, backend validation, or Playwright failure remains
supervisor-generated follow-up work for VAIOS-G723.
