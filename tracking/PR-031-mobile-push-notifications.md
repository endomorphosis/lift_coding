# PR-031: Mobile push notifications (APNS/FCM) receive + speak

## Goal
Implement the mobile-side push notification loop so notifications can be received on iOS/Android and spoken via TTS playback (phone now; Meta AI Glasses audio routing in a follow-up).

## Background
Backend already supports:
- Push subscription registration via `/v1/notifications/subscriptions` (platform `apns`/`fcm`)
- Notification polling fallback via `GET /v1/notifications`
- TTS audio via `POST /v1/tts`

The missing piece is the client logic:
- request notification permissions
- obtain device token (APNS / FCM)
- register token with backend
- handle incoming notifications and play a short spoken summary

## Scope
- Add mobile implementation notes + scaffolding under `mobile/`:
  - iOS: permission + APNS token retrieval (or via Expo Notifications)
  - Android: permission + FCM token retrieval
  - backend registration: create/delete subscription
  - receive handler: parse payload, fetch details if needed, call `/v1/tts`, play audio
- Document dev/test loop:
  - local backend
  - simulated pushes (where real push isn’t available)
  - polling fallback (`GET /v1/notifications`) to validate end-to-end

## Non-goals
- Full Bluetooth routing through Meta AI Glasses (separate PR).
- Production-grade background execution constraints (we’ll document platform limitations).

## Acceptance criteria
- Mobile docs clearly describe:
  - how to obtain APNS/FCM token
  - how to register it with `/v1/notifications/subscriptions`
  - how to handle an incoming push and trigger TTS playback
- Include a smoke-test procedure using polling fallback.
- No impact to Python tests.

## Agent checklist
- [ ] Add `mobile/push/README.md` with step-by-step setup
- [ ] Add a minimal token-registration client flow (scaffold)
- [ ] Add receive-handler flow (scaffold) including TTS fetch/play
