# VAI-543 Hallucinate MCP Dashboard Launch Gate

Date: 2026-06-28
Task: VAI-543
Goal id: VAIOS-G723
Evidence term: launch Playwright validation gate

The Hallucinate supervisor backlog mirrors the VAI-543 dashboard launch gate for
`VAIOS-G723`. It keeps catalog normalization, dashboard UI wiring, mediated
tool-call receipts, Swissknife consumers, Playwright coverage,
supervisor-generated follow-up subtasks, daemon health, MCP++ telemetry,
`tools/list`, `tools/call`, and `control_surface receipts` tied to the shared
Hallucinate App and Swissknife MCP dashboard catalog.

Validation command:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

Any dashboard or backend validation failure stays supervisor-generated follow-up
work under `VAIOS-G723-C6 Supervisor-generated follow-up subtasks`.
