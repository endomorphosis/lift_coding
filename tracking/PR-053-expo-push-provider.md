# PR-053: Push delivery alignment (Expo tokens)

## Goal
Make "notify on events" actually reach the mobile app by supporting the current mobile subscription style (Expo push token).

## Current gap
- Mobile registers push subscriptions with `platform: "expo"` and `endpoint: <expoPushToken>`.
- Backend delivery currently only supports `webpush`, `apns`, and `fcm` providers.
- Result: notifications are persisted but never delivered to devices using Expo tokens.

## Scope
- Add an `ExpoPushProvider` backend delivery provider.
- Extend provider selection to recognize `platform == "expo"`.
- Add configuration for Expo access token (optional) and basic rate/error handling.
- Add tests covering:
  - Provider selection for `expo`
  - Delivery call shape and failure handling

## Acceptance criteria
- Registering push from the mobile app results in backend delivery attempts.
- On webhook event creation (or manual notification creation), delivery returns success in dev mode (can stub in tests).

## References
- mobile/src/push/pushClient.js
- src/handsfree/db/notifications.py
- src/handsfree/notifications/provider.py
