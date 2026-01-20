# PR-086: Mobile push handling (background-safe) + auto-speak

## Goal
Make the mobile app reliably handle incoming push notifications and automatically speak a short summary via TTS, including when the app is backgrounded and then resumed.

## Context
- The mobile code can register Expo push tokens ([mobile/src/push/pushClient.js](mobile/src/push/pushClient.js)).
- The backend supports push subscriptions and notification persistence/delivery.
- What’s missing is a robust receive/handling loop and a demo-ready “auto-speak” behavior that doesn’t break audio routing.

## Scope
- Implement push receive handlers using `expo-notifications`:
  - foreground notification handler
  - tapped notification response handler
- When a notification arrives:
  - fetch notification details from backend if payload is minimal
  - generate spoken text (prefer server-provided text if available)
  - call `POST /v1/tts` and play audio
- Background-safe behavior:
  - if app is backgrounded, defer speaking until app is foregrounded (document platform constraints)
  - ensure audio mode is configured safely before playback
- Provide a small debug UI section (or logs) showing:
  - last notification received
  - last spoken text
  - last playback error

## Non-goals
- Full always-on background speaking.
- Glasses-native audio routing (covered by PR-083/084).

## Acceptance criteria
- On a physical device with Expo dev build:
  - Register Expo token and backend subscription successfully.
  - Receive a test notification.
  - App speaks a short summary (foreground) and does not crash.
  - When backgrounded, speaking is deferred until foregrounded/resumed.
- Minimal documentation added for how to test.

## Suggested files
- `mobile/src/push/pushClient.js`
- Push initialization location (app entry / navigation root)
- A screen that can display debug state (Settings / diagnostics)

## Validation
- Manual on-device test.
