# HAO-187 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/node/menu_generator.js:444

## Finding

The codebase scan filed `// TODO: Implement config reset` at line 444 of
`menu_generator.js`. A prior attempt replaced the stub with a working
`resetConfig` handler that shows a confirmation dialog and then navigates to
`views/settings.html?reset=true`. However, `settings.html` did not handle the
`?reset=true` query parameter — the reset action was wired up in the menu but
the page performed no actual reset when reached via that URL.

## Fix

Added a `resetSettings()` function in `settings.html` that:
1. Clears `localStorage['appSettings']` (removes all persisted user preferences).
2. Restores each form control to its default value (matching the application defaults already referenced in `saveSettings()`).
3. Shows a styled inline banner confirming the reset.

On page load, the script now checks for `?reset=true` and calls `resetSettings()`
instead of `loadSettings()`, so the reset is applied immediately when the menu
action navigates to the page.

```js
const _params = new URLSearchParams(window.location.search);
if (_params.get('reset') === 'true') {
  resetSettings();
} else {
  loadSettings();
}
```

## Files Changed

- `hallucinate_app/hallucinate_app/node/views/settings.html` — added `resetSettings()` and URL-parameter detection.
