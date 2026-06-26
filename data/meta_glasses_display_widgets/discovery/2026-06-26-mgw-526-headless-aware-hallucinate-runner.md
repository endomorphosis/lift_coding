# MGW-526 Headless-Aware Hallucinate Runner

Date: 2026-06-26
Task id: MGW-526
Goal id: VAIOS-G723
Track: validation

## Validation Contract

Meta glasses MCP dashboard validation inherits the headless-aware Hallucinate
Playwright runner through this command:

```bash
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
```

The `hallucinate_app` `test:e2e` script resolves to
`node scripts/run_playwright_test.mjs test`, so the MCP dashboard gate uses the
same `xvfb-run` detection, `DISPLAY` / `WAYLAND_DISPLAY` handling, and
`missing_xvfb_for_electron_playwright` diagnostic as the rest of the
Hallucinate Electron Playwright validation.

## Environment Blocker Rule

When Linux has no `DISPLAY`, no `WAYLAND_DISPLAY`, and no `xvfb-run`, the
runner exits with exit 78 and records
`missing_xvfb_for_electron_playwright` as a repairable launch-environment
blocker. That status is not a Meta glasses MCP dashboard contract failure.

When a display server or `xvfb-run` is present, the dashboard specs execute
normally and can fail only for real dashboard or control-plane contract gaps.
Those gaps include the Meta glasses camera, microphone, headphones, and
neural-band control-plane surfaces that feed the shared Hallucinate MCP
dashboard catalog, mediated receipts, and Swissknife consumers.

## Evidence

- `hallucinate_app/scripts/run_playwright_test.mjs` owns the headless-aware
  runner behavior and the exit 78 repairable blocker diagnostic.
- `hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` covers the
  `remote-meta-glasses` client in the dashboard feature exposure path.
- `hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts` covers the
  VAIOS-G723 MCP dashboard interoperability gate.
- `tests/test_virtual_ai_os_launch_readiness_gate.py` asserts the Meta glasses
  MCP dashboard validation command inherits the runner and cannot be satisfied
  by no-display Electron skips.
