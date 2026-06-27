# MGW-548 Validation Retry-Budget Repair

Date: 2026-06-27
Task: MGW-548
Source task: MGW-546

## Finding

The retry-budget evidence in
`data/meta_glasses_display_widgets/state/discovery/2026-06-27-mgw-548-mgw-546-retry-budget.md`
showed three consecutive failures of:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

Those failures exited before Playwright could run because
`hallucinate_app/scripts/run_playwright_test.mjs` returned
`missing_xvfb_for_electron_playwright` on Linux hosts without `DISPLAY`,
`WAYLAND_DISPLAY`, or `xvfb-run`.

## Repair

The Hallucinate Playwright wrapper now permits no-display execution only when
the selected specs are known to contain backend/static launch-gate coverage:

- `mcp-feature-exposure.spec.ts`
- `mcp-dashboard-interoperability.spec.ts`
- `multimodal-control-surface.spec.ts`

Electron UI suites inside those specs remain skipped without a display, while
the backend catalog, launch-plan, mediated receipt, Swissknife consumer, and
multimodal control-surface assertions run under Playwright and can fail the
validation gate normally. Electron-only or whole-suite requests still require a
display or `xvfb-run` and keep the explicit
`missing_xvfb_for_electron_playwright` diagnostic.

## Validation Gate

This repair preserves the launch Playwright validation gate by converting the
MGW-546 command from an environment preflight exit into executable Playwright
coverage on headless supervisor hosts.
