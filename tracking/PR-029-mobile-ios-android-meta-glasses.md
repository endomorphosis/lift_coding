# PR-029: iOS + Android companion app plan (Meta AI Glasses)

## Goal
Make Handsfree usable end-to-end from **iOS + Android** with **Meta AI Glasses** as the audio I/O device.

This PR is the bridge between the backend (already in this repo) and the missing **mobile/wearable client pipeline**.

## Scope (this repo)
Docs + reference scaffolding to unblock building the real apps.

- Add a clear **mobile integration contract**:
  - Command submission (`POST /v1/command`) with text first, then audio URI
  - Confirmation flow (`POST /v1/commands/confirm`)
  - Notifications polling (`GET /v1/notifications`) + push registration (`/v1/notifications/subscriptions`)
  - TTS playback (`POST /v1/tts`) + expected client behavior

- Add a **reference client flow**:
  - Minimal "reference client" script(s) in `dev/` that simulate:
    - registering APNS/FCM tokens
    - sending a command
    - handling confirmation
    - polling notifications
    - fetching TTS audio bytes

- Add a **Meta AI Glasses integration guide**:
  - Bluetooth audio routing expectations
  - push-to-talk UX guidance
  - how to play TTS through the glasses
  - constraints/notes where vendor SDK policies apply

## Non-goals
- Shipping a full production mobile app inside this repo.
- Implementing bluetooth/wearable audio in Python.

## Acceptance criteria
- New docs explain the full client workflow for:
  - Text command loop
  - Confirmation loop
  - Notifications (poll + push)
  - TTS playback
- Reference client scripts run against local backend and demonstrate the flows.
- Docs explicitly cover both:
  - iOS (APNS) token registration
  - Android (FCM) token registration
- Docs include a dedicated section: "Meta AI Glasses: audio capture + playback".

## Files / pointers
- Backend contract: `spec/openapi.yaml`
- Notifications API: `src/handsfree/api.py`
- Push providers: `src/handsfree/notifications/provider.py`
- Subscriptions persistence: `src/handsfree/db/notification_subscriptions.py`
- Notifications persistence + auto-push: `src/handsfree/db/notifications.py`

## Recommended deliverables
- `docs/mobile-client-integration.md`
- `docs/meta-ai-glasses.md`
- `dev/reference_mobile_client.py` (or equivalent)

## Notes
- Backend already supports APNS/FCM/WebPush subscriptions via `platform`.
- Real APNS/FCM delivery is enabled via env flags (see docs).