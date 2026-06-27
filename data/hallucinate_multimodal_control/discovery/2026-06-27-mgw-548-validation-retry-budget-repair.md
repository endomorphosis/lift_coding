# MGW-548 Hallucinate Validation Retry-Budget Repair

Date: 2026-06-27
Task: MGW-548
Source task: MGW-546

This Hallucinate-side receipt mirrors the Meta glasses repair evidence in
`data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-548-validation-retry-budget-repair.md`.

The repair keeps the Hallucinate MCP dashboard launch Playwright validation
gate executable on no-display supervisor hosts by allowing selected
backend/static specs to run through Playwright instead of exiting at the
`missing_xvfb_for_electron_playwright` preflight. Electron UI coverage still
requires `DISPLAY`, `WAYLAND_DISPLAY`, or `xvfb-run`.

Validated specs:

- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts`
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts`
- `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts`
