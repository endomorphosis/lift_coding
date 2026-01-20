# PR-089: Mobile push subscription settings + user controls

## Goal
Provide a small settings/diagnostics UI for push notifications so users can:
- register/unregister their push token with the backend
- see current subscription status
- control whether notifications auto-speak

## Context
We have push token registration helpers in [mobile/src/push/pushClient.js](mobile/src/push/pushClient.js), but there is no user-facing control surface. For demos, this makes push setup brittle.

## Scope
- Add a settings section or a simple screen that:
  - requests permission
  - shows the current Expo push token (masked) and subscription id(s)
  - allows register/unregister with backend
  - toggle: auto-speak notifications
- Persist toggle state via `AsyncStorage`.

## Non-goals
- Full notification center UI.

## Acceptance criteria
- A user can complete push setup from inside the app without using logs.
- Toggle state persists across restarts.

## Suggested files
- `mobile/src/push/pushClient.js`
- `mobile/src/screens/SettingsScreen.js` (or create a new settings screen if needed)
- `mobile/src/api/client.js`

## Validation
- Manual on device: register, trigger test notification, verify behavior.
