# Mobile Push Notifications (Placeholder)

Tracked in `tracking/PR-031-mobile-push-notifications.md`.

## Backend endpoints
- Register token: `POST /v1/notifications/subscriptions`
- List subscriptions: `GET /v1/notifications/subscriptions`
- Delete subscription: `DELETE /v1/notifications/subscriptions/{id}`
- Poll fallback: `GET /v1/notifications`
- Speak: `POST /v1/tts`

## TODO
- Decide implementation stack (Expo Notifications vs native APNS/FCM)
- Implement token retrieval
- Register token with backend
- Handle inbound push payload
- Fetch/speak summary
