# VAI-110 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/node/menu_generator.js:433

## Finding

The `openSwissKnifeApp` action handler had a TODO comment:
`// TODO: Launch specific app within SwissKnife`

Menu items in `menu_config.js` supply an `app` property (terminal, editor, files, chat, music, video) that was never passed to `createSwissKnifeWindow`.

## Fix

1. **menu_generator.js** — Pass `item.app` to `createSwissKnifeWindow(item.app)` instead of calling it with no arguments. Removed the TODO comment.

2. **index.js** — Updated `createSwissKnifeWindow(appName)` to accept an optional `appName` parameter and pass it as a URL hash via `win.loadFile(..., { hash: appName })`. The dashboard page can read `location.hash` to navigate to the named app section on load.

## Verdict

Bug fix (incomplete feature): the app name from menu config was silently discarded. Now it is forwarded to the window so the frontend can route to the correct section.
