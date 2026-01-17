# Mobile Push Smoke Test (Polling Fallback)

Use this when real APNS/FCM delivery isn’t configured yet.

## Steps
1. Run the backend locally.
2. Register a push subscription (token can be a placeholder in dev).
3. Trigger a notification-producing event (or create one via an existing dev flow).
4. Poll `GET /v1/notifications` until the notification appears.
5. Call `POST /v1/tts` with the notification text and play audio on device.

This verifies the client loop (receive -> speak) independent of push provider configuration.
