# Push Notification Delivery

This document describes the optional push notification delivery feature added to the HandsFree Dev Companion.

## Overview

The notification system supports two delivery methods:

1. **Poll-based (default)**: Clients poll `GET /v1/notifications` to retrieve notifications
2. **Push-based (optional)**: Notifications are actively delivered to subscribed endpoints

Both methods can be used simultaneously - polling continues to work even when push delivery is enabled.

## Architecture

### NotificationDeliveryProvider

The `NotificationDeliveryProvider` is an abstract interface for push notification providers:

```python
from handsfree.notifications import NotificationDeliveryProvider

class NotificationDeliveryProvider(ABC):
    @abstractmethod
    def send(
        self,
        subscription_endpoint: str,
        notification_data: dict[str, Any],
        subscription_keys: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a notification to a subscription endpoint."""
        pass
```

### Providers

#### DevLoggerProvider

A development provider that logs notifications instead of sending them. Useful for testing and development.

```python
from handsfree.notifications import DevLoggerProvider

provider = DevLoggerProvider()
result = provider.send(
    subscription_endpoint="https://push.example.com/endpoint",
    notification_data={
        "id": "notif-123",
        "event_type": "test_event",
        "message": "Test notification",
    }
)
```

## Configuration

Push notification delivery is controlled by the `HANDSFREE_NOTIFICATION_PROVIDER` environment variable:

- `"logger"` or `"dev"`: Enable DevLoggerProvider (logs notifications)
- Empty or not set: Push delivery disabled (polling only)

Example:
```bash
export HANDSFREE_NOTIFICATION_PROVIDER=logger
```

## API Endpoints

### Create Subscription

Create a new notification subscription for the authenticated user.

```
POST /v1/notifications/subscriptions
```

**Request Body:**
```json
{
  "endpoint": "https://push.example.com/subscription-id",
  "subscription_keys": {
    "auth": "secret-auth-key",
    "p256dh": "public-key"
  }
}
```

**Response:** (201 Created)
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "endpoint": "https://push.example.com/subscription-id",
  "subscription_keys": {
    "auth": "secret-auth-key",
    "p256dh": "public-key"
  },
  "created_at": "2024-01-14T12:00:00Z",
  "updated_at": "2024-01-14T12:00:00Z"
}
```

### List Subscriptions

Get all notification subscriptions for the authenticated user.

```
GET /v1/notifications/subscriptions
```

**Response:** (200 OK)
```json
{
  "subscriptions": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "endpoint": "https://push.example.com/subscription-id",
      "subscription_keys": {},
      "created_at": "2024-01-14T12:00:00Z",
      "updated_at": "2024-01-14T12:00:00Z"
    }
  ]
}
```

### Delete Subscription

Delete a notification subscription.

```
DELETE /v1/notifications/subscriptions/{subscription_id}
```

**Response:** (204 No Content)

## Database Schema

A new `notification_subscriptions` table stores user subscriptions:

```sql
CREATE TABLE notification_subscriptions (
  id                  UUID PRIMARY KEY,
  user_id             UUID NOT NULL,
  endpoint            TEXT NOT NULL,
  subscription_keys   JSON,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

## Delivery Behavior

When a notification is created via `create_notification()`:

1. The notification is **always** persisted to the database (for polling)
2. If a push provider is configured (`HANDSFREE_NOTIFICATION_PROVIDER` set):
   - Fetch all subscriptions for the user
   - Send the notification to each subscription endpoint
   - Log delivery success/failure
   - **Delivery failures do not prevent notification creation**

3. Clients can still poll `GET /v1/notifications` regardless of push delivery

## Testing

### Unit Tests

```bash
# Test subscription CRUD operations
pytest tests/test_notification_subscriptions.py

# Test delivery provider and integration
pytest tests/test_notification_delivery.py
```

### Manual Testing

1. **Enable push provider:**
   ```bash
   export HANDSFREE_NOTIFICATION_PROVIDER=logger
   ```

2. **Create a subscription:**
   ```bash
   curl -X POST http://localhost:8000/v1/notifications/subscriptions \
     -H "Content-Type: application/json" \
     -H "X-User-Id: 00000000-0000-0000-0000-000000000001" \
     -d '{"endpoint": "https://push.example.com/test"}'
   ```

3. **Trigger a notification** (e.g., via webhook or agent task)

4. **Check logs** for delivery messages:
   ```
   INFO:handsfree.db.notifications:Delivered notification <id> to subscription <sub_id>: dev-<hash>
   ```

5. **Verify polling still works:**
   ```bash
   curl http://localhost:8000/v1/notifications \
     -H "X-User-ID: 00000000-0000-0000-0000-000000000001"
   ```

## Future Enhancements

- **WebPush Provider**: Implement a real WebPush provider using standard libraries (e.g., `pywebpush`)
- **VAPID Keys**: Store VAPID keys via environment variables for WebPush authentication
- **Retry Logic**: Add exponential backoff for failed deliveries
- **Delivery Status**: Track delivery status per subscription
- **Subscription Verification**: Add endpoint verification during subscription creation
