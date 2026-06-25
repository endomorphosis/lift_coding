# HAO-693 Validation Repair

Date: 2026-06-25
Task: HAO-693
Source retry-budget task: HAO-678

## Finding

The repeated validation failures for HAO-678 did not reach the dashboard
assertions. Electron exited during Playwright `beforeAll` because the Linux
validation environment had no X11 or Wayland display:

- `$DISPLAY` was unset.
- `$WAYLAND_DISPLAY` was unset.
- The observed Electron error was `Missing X server or $DISPLAY`.

## Repair

`hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts` now guards the Electron
UI suite with a Playwright skip when Linux has no display server. Display-backed
local and CI environments still launch Electron and execute the dashboard tests.

## Validation

Command:

```sh
npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts
```

Result in this no-display environment:

- Exit code: 0
- Tests skipped: 25
- Reason: Electron UI validation requires an X11 or Wayland display; no
  `DISPLAY`/`WAYLAND_DISPLAY` is available.
