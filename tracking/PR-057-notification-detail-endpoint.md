# PR-057: Notification detail endpoint (mobile deep-link)

## Goal
Let the mobile app fetch full notification details when a push payload includes `notification_id`.

## Current gap
- Mobile handler calls `GET /v1/notifications/{id}` when push data includes `notification_id`.
- Backend only provides `GET /v1/notifications` (list) and does not implement the detail route.
- OpenAPI does not define a notification detail endpoint.

## Scope
- Backend:
  - Add `GET /v1/notifications/{notification_id}` returning the `Notification` record for the current user.
  - Return `404` if the notification does not exist or does not belong to the user.
- OpenAPI:
  - Add the new path and response schema.
- Tests:
  - Add an API test covering success and 404 cases.

## Acceptance criteria
- Mobile can fetch details for a received notification via the new endpoint.
- Contract validation passes.

## References
- src/handsfree/api.py
- src/handsfree/db/notifications.py
- spec/openapi.yaml
- mobile/src/push/notificationsHandler.js
