# PR-071: Speak push notifications automatically (mobile)

## Goal
When the mobile app receives a push notification, automatically speak a short summary (via backend TTS) through the selected audio output (glasses when connected).

## Why
Push delivery works, but the hands-free value depends on receiving an event and hearing a short spoken summary without manual navigation.

## Scope
Mobile-only changes under `mobile/`.

## Deliverables
- In the push receive handler:
  - Extract `notification_id` (or fallback `id`).
  - Fetch details from `GET /v1/notifications/{notification_id}`.
  - Call `POST /v1/tts` on a concise summary string.
  - Play audio via the existing player.
- Provide a toggle: **"Speak notifications"** (default ON in dev builds).

## Acceptance criteria
- When a push arrives while the app is in the foreground, the app speaks the notification summary.
- When a push arrives in the background, behavior is documented clearly (platform limitations are acceptable if unavoidable).
- No double-audio (system notification sound should remain silent by default).

## Test plan
- Manual:
  - Trigger push via existing dev tooling and confirm spoken playback.
  - Verify the toggle disables speech.
