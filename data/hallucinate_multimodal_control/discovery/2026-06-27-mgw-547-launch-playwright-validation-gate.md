# MGW-547 Hallucinate Backlog Launch Gate

Date: 2026-06-27
Source task: MGW-547
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

MGW-547 keeps the Hallucinate supervisor-fed backlog aligned with the
`VAIOS-G723` objective heap by pointing the Hallucinate MCP dashboard
interoperability console at the same launch Playwright validation gate consumed
by Meta glasses and Swissknife validation.

The gate covers catalog normalization, dashboard UI wiring, mediated tool-call receipts,
Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks.
It remains open until `mcp-feature-exposure.spec.ts` and
`mcp-dashboard-interoperability.spec.ts` prove the shared dashboard capability
catalog, backend service catalog, daemon health, MCP++ telemetry, `tools/list`,
`tools/call`, and `control_surface` receipts for `ipfs_kit_py`,
`ipfs_datasets_py`, and `ipfs_accelerate_py`.

Validation command:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```
