# MGW-546 Launch Playwright Validation Gate

Date: 2026-06-27
Task: MGW-546
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

## Gate

MGW-546 binds the `VAIOS-G723` Hallucinate MCP dashboard interoperability
console to the executable launch Playwright validation gate:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` exposes an MGW-546 `launch_validation_gates` entry for `VAIOS-G723`.
- `hallucinate_app/test/e2e/fixtures/mgw-546-mcp-dashboard-launch-gate.json` records the catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` asserts the dashboard capability catalog, daemon health, `tools/list`, `tools/call`, `ipfs_kit_py`, `ipfs_datasets_py`, `ipfs_accelerate_py`, and the shared receipt route.

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
