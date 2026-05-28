# HAO-186 Resolution

Date: 2026-05-28
Source: hallucinate_app/hallucinate_app/node/menu_generator.js:439

## Finding

The `openServerConfig` case in `handleAction` had a stub implementation — only a
`console.log` and a `// TODO: Implement server config window` comment with no
functional behaviour.

## Fix

Replaced the stub with a `navigateToView` call that opens `views/settings.html`.
When a `serverId` is present on the action item, the server ID is appended as a
query parameter (`?server=<id>`) so the settings page can highlight or filter to
the relevant server entry. If no `serverId` is present, the plain settings view is
opened (matching the existing `openSettings` action behaviour).

```js
case 'openServerConfig':
  if (item.serverId) {
    this.navigateToView(resolveViewPath(`views/settings.html?server=${encodeURIComponent(item.serverId)}`));
  } else {
    this.navigateToView(resolveViewPath('views/settings.html'));
  }
  break;
```

## Why Not a False Positive

The menu item was wired up in `menu_config.js` and reachable at runtime, but
clicking it did nothing visible to the user. The fix makes it functional using
the established `navigateToView` + `resolveViewPath` pattern already used for
`openSettings`.
