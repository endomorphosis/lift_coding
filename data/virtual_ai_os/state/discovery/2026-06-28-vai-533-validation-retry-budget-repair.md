# VAI-533 Validation Retry-Budget Repair

Date: 2026-06-28
Task: VAI-533
Source task: VAI-531

## Finding

The retry-budget evidence in
`data/virtual_ai_os/state/discovery/2026-06-27-vai-533-vai-531-retry-budget.md`
showed three consecutive failures of:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

Those attempts failed before the VAI-531 dashboard interoperability assertions
could run because the Hallucinate Playwright wrapper treated the selected
launch-gate specs as requiring a graphical display on Linux hosts without
`DISPLAY`, `WAYLAND_DISPLAY`, or `xvfb-run`.

## Repair

`hallucinate_app/scripts/run_playwright_test.mjs` now preserves the display
preflight for Electron UI coverage while allowing declared no-display runnable
launch-gate specs to execute their backend/static Playwright assertions:

- `mcp-feature-exposure.spec.ts`
- `mcp-dashboard-interoperability.spec.ts`
- `multimodal-control-surface.spec.ts`

The repair uses the `NO_DISPLAY_RUNNABLE_SPEC_FILES` allowlist and
`isNoDisplayRunnableRequest` gate. Electron-only or whole-suite requests still
require a display or `xvfb-run` and keep the
`missing_xvfb_for_electron_playwright` diagnostic.

## Validation Gate

This closes the VAI-531 retry-budget blocker by letting the VAI-533 validation
command run real Playwright coverage on headless supervisor hosts:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The launch Playwright validation gate remains preserved because display-only
Electron tests are still skipped only inside the selected specs, while the
backend catalog, launch-plan, mediated receipt, Swissknife consumer, and
multimodal control-surface assertions continue to fail normally when their
contracts regress.
