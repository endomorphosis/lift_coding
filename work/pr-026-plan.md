# PR-026: Automatic push notification delivery - Implementation Plan

## Status
Ready for implementation by GitHub Copilot agent.

## Tracking Document
See `tracking/PR-026-notification-push-delivery.md` for full details.

## Quick Summary
Bridge the gap between notification creation and delivery providers. When notifications are created for users with push subscriptions, automatically deliver them via WebPush/APNS/FCM providers.

## Implementation Checklist
- [ ] Create notification delivery service (`src/handsfree/notifications/delivery.py`)
- [ ] Update `create_notification()` to trigger delivery
- [ ] Add provider selection logic based on subscription platform
- [ ] Add configuration env var `NOTIFICATIONS_AUTO_PUSH_ENABLED`
- [ ] Add delivery tracking fields/migration
- [ ] Write tests with delivery disabled in test mode
- [ ] Update documentation

## Related Files
- `src/handsfree/db/notifications.py` - notification creation
- `src/handsfree/notifications/provider.py` - delivery providers
- `src/handsfree/db/notification_subscriptions.py` - user subscriptions
