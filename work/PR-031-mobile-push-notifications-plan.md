# PR-031: Mobile push notifications (APNS/FCM) receive + speak — execution plan

This PR is intended for a Copilot agent.

## Goal
Make the `mobile/` Expo app able to:
- obtain a device push token (Expo Notifications first; native APNS/FCM optional)
- register that token with the backend (`POST /v1/notifications/subscriptions`)
- receive a push (or simulate/poll) and speak it by calling `POST /v1/tts` and playing the returned audio

## Constraints / guardrails
- Keep backend Python tests green (avoid touching backend unless necessary).
- Prefer Expo-first approach so iOS + Android share code.
- Keep implementation behind a small feature flag / dev toggle (safe-by-default).

## Suggested deliverables
1) Mobile code scaffolding
- `mobile/src/push/pushClient.js`
  - `registerForPushAsync()`
  - `registerSubscriptionWithBackend({ platform, token })`
  - `unregisterSubscriptionWithBackend(subscriptionId)`
- `mobile/src/push/notificationsHandler.js`
  - parses incoming payload
  - chooses what text to speak
  - calls `mobile/src/api/client.js` -> `POST /v1/tts` to fetch audio
  - plays audio via `expo-av`

2) Minimal UI wiring
- Add a small section to the existing `Status` screen or a new screen:
  - "Enable Push"
  - shows current token
  - registers/unregisters
  - "Simulate speak" button that uses polling fallback (`GET /v1/notifications`) and speaks latest.

3) Docs update
- Ensure `mobile/push/README.md` points at the actual code paths.

## API pointers
- Backend contract: `spec/openapi.yaml`
- Push subscription endpoints: `POST/GET/DELETE /v1/notifications/subscriptions`
- Notifications polling fallback: `GET /v1/notifications`
- TTS: `POST /v1/tts`

## Acceptance criteria
- Running `npm start` in `mobile/` allows:
  - registering a push token with the backend in dev mode
  - fetching the latest notification via polling and speaking it through TTS
- No changes required to backend CI.
