# MGW-549 Hallucinate Validation Retry-Budget Repair

Date: 2026-06-28
Task: MGW-549
Source task: MGW-547

This Hallucinate-side receipt mirrors
`data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-549-validation-retry-budget-repair.md`.

The repair keeps the Hallucinate MCP dashboard launch Playwright validation
gate focused on executable backend/static coverage and restores missing
scanner-visible evidence for HAO-682, MGW-546, and HAO-712.

Validated gate:

```text
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```
