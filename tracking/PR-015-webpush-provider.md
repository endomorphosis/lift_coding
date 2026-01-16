# PR-015: Add WebPush notification delivery provider

## Goal
Implement a real push delivery provider (WebPush) behind the existing `NotificationDeliveryProvider` abstraction.

## Background
The implementation plan calls for notification delivery to mobile/wearable. The codebase has a provider abstraction and a dev logger provider, but no real push implementation.

## Scope
- Add a `WebPushProvider` implementation.
- Add configuration for VAPID keys.
- Ensure delivery errors are handled safely and recorded.
- Add targeted unit tests.

## Non-goals
- APNS/FCM integration.
- Mobile client subscription UX.

## Acceptance criteria
- Setting `HANDSFREE_NOTIFICATION_PROVIDER=webpush` enables actual WebPush sends.
- Delivery uses VAPID auth (public/private key) and supports subscription keys (`p256dh`, `auth`).
- Unit tests cover success and failure paths without network calls.
- CI remains green.

## Implementation notes
- Likely add dependency: `pywebpush` (optional, with graceful fallback if not installed).
- Extend `get_notification_provider()` to recognize `webpush`.
- Use env vars:
  - `HANDSFREE_WEBPUSH_VAPID_PUBLIC_KEY`
  - `HANDSFREE_WEBPUSH_VAPID_PRIVATE_KEY`
  - `HANDSFREE_WEBPUSH_VAPID_SUBJECT` (e.g., `mailto:ops@example.com`)
- Tests should mock the underlying send function.

