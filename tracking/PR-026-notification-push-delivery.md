# PR-026: Automatic push notification delivery

## Goal
Automatically deliver notifications to users via their registered push subscriptions (WebPush/APNS/FCM) when notifications are created, instead of relying solely on polling.

## Background
The system currently:
- Creates notifications in the database when events occur (agent tasks, webhooks, etc.)
- Provides a polling endpoint (`GET /v1/notifications`) for clients to retrieve notifications
- Has notification delivery providers (WebPush, APNS, FCM) but they are not automatically invoked

What's missing is the bridge between notification creation and delivery provider invocation.

## Scope
- Add a notification delivery service that:
  - Is invoked when notifications are created
  - Queries user's active push subscriptions
  - Selects appropriate provider based on subscription platform
  - Sends push notifications via the provider
  - Logs delivery results and handles errors gracefully
- Update `create_notification()` to optionally trigger push delivery
- Add configuration for enabling/disabling auto-push (default: enabled in production, disabled in tests)
- Add delivery tracking (last_delivery_attempt, delivery_status) to notifications table
- Handle provider failures gracefully (log but don't block notification creation)

## Non-goals
- Building new notification providers (use existing WebPush/APNS/FCM providers)
- Advanced delivery features (batching, retry queues) - keep it simple for MVP
- Push notification content customization beyond basic payload

## Acceptance criteria
- When a notification is created for a user with active push subscriptions, it is automatically delivered via the appropriate provider
- Delivery attempts are logged and tracked in the notification record
- Provider errors don't prevent notification creation or break the API
- Tests remain green (with delivery disabled in test config)
- Dev mode can optionally disable auto-push for local development

## Implementation notes
- Add delivery service in `src/handsfree/notifications/delivery.py`
- Modify `create_notification()` in `src/handsfree/db/notifications.py` to call delivery service
- Query subscriptions from `notification_subscriptions` table
- Select provider based on subscription platform field (webpush/apns/fcm)
- Add env var `NOTIFICATIONS_AUTO_PUSH_ENABLED` (default: true)
- Add migration for delivery tracking fields if needed

## Related PRs
- PR-015: WebPush provider
- PR-024: APNS/FCM scaffolding
- PR-016: Agent delegation (emits task notifications)
