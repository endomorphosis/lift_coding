# MGW-134 Resolution

Date: 2026-05-28
Task: MGW-134
Source finding: hallucinate_app/hallucinate_app/node/menu_generator.js:421
Fingerprint: dc01283308eaf9726fe91a9b9944e947dd5b1345

## Finding

The `openSettings` action in `MenuGenerator.handleAction` contained only a
`console.log` call and a `// TODO: Implement settings window` comment with no
functional implementation.

## Fix

Replaced the stub with a proper `openSettings()` method on `MenuGenerator` that:

1. Delegates to a caller-supplied `createSettingsWindow` factory when one is
   provided via constructor options (consistent with how `createSwissKnifeWindow`
   and `createMCPDashboardWindow` are already wired in).
2. Falls back to creating an Electron `BrowserWindow` directly, loading
   `views/settings.html` via `resolveViewPath`.
3. Reuses the window if it is already open (focus instead of re-open), and
   cleans up the reference on close.

`BrowserWindow` was added to the existing `electron` import. The constructor
now accepts `createSettingsWindow` as an option and stores `_settingsWindow`
for lifecycle tracking.

## Files changed

- `hallucinate_app/hallucinate_app/node/menu_generator.js`
