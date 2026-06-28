# MGW-547 Attempt 7 Hallucinate Backlog Launch Gate

Date: 2026-06-28
Source task: MGW-547
Attempt: 7
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

MGW-547 attempt 7 keeps the Hallucinate supervisor-fed backlog aligned with
the `VAIOS-G723` objective heap. The Hallucinate MCP dashboard interoperability
console uses the shared dashboard capability catalog consumed by Swissknife and
the Meta glasses launch readiness gate.

The attempt-7 gate covers catalog normalization, dashboard UI wiring, mediated
tool-call receipts, Swissknife consumers, Playwright coverage, and
supervisor-generated follow-up subtasks.

Exact scanner terms: catalog normalization; dashboard UI wiring; mediated tool-call receipts; Swissknife consumers; Playwright coverage; supervisor-generated follow-up subtasks; launch Playwright validation gate; tools/list; tools/call.

It remains open until
`mcp-feature-exposure.spec.ts` and `mcp-dashboard-interoperability.spec.ts`
prove daemon health, MCP++ telemetry, `tools/list`, `tools/call`, and
`control_surface` receipts for `ipfs_kit_py`, `ipfs_datasets_py`, and
`ipfs_accelerate_py`.

Validation command:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

Any dashboard or backend validation failure stays supervisor-generated follow-up
work under `VAIOS-G723-C6 Supervisor-generated follow-up subtasks`.
