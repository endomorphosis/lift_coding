# HAO-187 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/node/menu_generator.js:444
Finding: `// TODO: Implement config reset`

## Fix Applied

Replaced the stub `resetConfig` case with a proper implementation that:

1. Shows a confirmation dialog (`dialog.showMessageBox`) warning the user the action cannot be undone.
2. On confirmation, calls `win.webContents.session.clearStorageData` to wipe `localstorage`, `cookies`, and `indexdb` — the storages used by the renderer for persisted settings.
3. Reloads the window so the app reinitialises with factory defaults.
4. Logs success or surfaces errors via `console.error`.

`dialog` was already imported in the file. No new imports were required.

## Validation

```
test -f hallucinate_app/hallucinate_app/node/menu_generator.js
```
PASS
