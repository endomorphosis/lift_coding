# PR-056: Notification subscriptions accept Expo platform

## Goal
Unblock real mobile push delivery by aligning the API contract with the mobile client and backend delivery support.

## Current gap
- Mobile registers push subscriptions with `platform: "expo"`.
- Backend validates `platform` as `webpush|apns|fcm` (rejects `expo`).
- OpenAPI schema also excludes `expo`.

## Scope
- Backend:
  - Update request/response models to allow `platform: expo`.
  - Ensure create/list subscription endpoints accept and return `expo`.
- OpenAPI:
  - Add `expo` to `CreateNotificationSubscriptionRequest.platform` enum.
  - Add `expo` to `NotificationSubscriptionResponse.platform` enum.
- Tests:
  - Add/extend an API test that `POST /v1/notifications/subscriptions` accepts `platform=expo`.
  - Add/extend a test that the created subscription is returned by `GET /v1/notifications/subscriptions`.

## Acceptance criteria
- A request with `platform: expo` is accepted (201) and persisted.
- `scripts/validate_openapi.py` passes and contract tests remain green.

## References
- src/handsfree/models.py
- src/handsfree/api.py
- spec/openapi.yaml
- mobile/src/push/pushClient.js
