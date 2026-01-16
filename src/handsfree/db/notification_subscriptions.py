"""Notification subscriptions persistence module.

Manages storage and retrieval of user notification subscriptions for push delivery.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


@dataclass
class NotificationSubscription:
    """Represents a notification subscription for push delivery."""

    id: str
    user_id: str
    endpoint: str
    subscription_keys: dict[str, str] | None
    created_at: datetime
    updated_at: datetime
    platform: str = "webpush"  # webpush, apns, fcm

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "endpoint": self.endpoint,
            "subscription_keys": self.subscription_keys or {},
            "platform": self.platform,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


def create_subscription(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    endpoint: str,
    subscription_keys: dict[str, str] | None = None,
    platform: str = "webpush",
) -> NotificationSubscription:
    """Create a new notification subscription.

    Args:
        conn: Database connection.
        user_id: User ID (string, will be converted to UUID).
        endpoint: Subscription endpoint URL or identifier.
        subscription_keys: Optional provider-specific keys (e.g., auth, p256dh for WebPush).
        platform: Platform type: 'webpush', 'apns', or 'fcm'.

    Returns:
        Created NotificationSubscription object.
    """
    subscription_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # Convert user_id to UUID if it's not already one
    try:
        user_uuid = (
            uuid.UUID(user_id) if "-" in user_id else uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
        )
    except (ValueError, AttributeError):
        # If conversion fails, generate a UUID from the string
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    conn.execute(
        """
        INSERT INTO notification_subscriptions
        (id, user_id, endpoint, subscription_keys, platform, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            subscription_id,
            user_uuid,
            endpoint,
            json.dumps(subscription_keys) if subscription_keys else None,
            platform,
            now,
            now,
        ],
    )

    return NotificationSubscription(
        id=subscription_id,
        user_id=user_id,
        endpoint=endpoint,
        subscription_keys=subscription_keys,
        platform=platform,
        created_at=now,
        updated_at=now,
    )


def list_subscriptions(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
) -> list[NotificationSubscription]:
    """List all notification subscriptions for a user.

    Args:
        conn: Database connection.
        user_id: User ID to filter by (string, will be converted to UUID).

    Returns:
        List of NotificationSubscription objects.
    """
    # Convert user_id to UUID if it's not already one
    try:
        user_uuid = (
            uuid.UUID(user_id) if "-" in user_id else uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
        )
    except (ValueError, AttributeError):
        # If conversion fails, generate a UUID from the string
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    query = """
        SELECT id, user_id, endpoint, subscription_keys, platform, created_at, updated_at
        FROM notification_subscriptions
        WHERE user_id = ?
        ORDER BY created_at DESC
    """
    result = conn.execute(query, [user_uuid]).fetchall()

    return [
        NotificationSubscription(
            id=str(row[0]),  # Convert UUID to string
            user_id=user_id,  # Return the original string user_id
            endpoint=row[2],
            subscription_keys=json.loads(row[3]) if row[3] else None,
            platform=row[4] if len(row) > 4 else "webpush",
            created_at=row[5] if len(row) > 5 else row[4],
            updated_at=row[6] if len(row) > 6 else row[5],
        )
        for row in result
    ]


def get_subscription(
    conn: duckdb.DuckDBPyConnection,
    subscription_id: str,
) -> NotificationSubscription | None:
    """Get a specific notification subscription by ID.

    Args:
        conn: Database connection.
        subscription_id: Subscription UUID.

    Returns:
        NotificationSubscription object or None if not found.
    """
    query = """
        SELECT id, user_id, endpoint, subscription_keys, platform, created_at, updated_at
        FROM notification_subscriptions
        WHERE id = ?
    """
    result = conn.execute(query, [subscription_id]).fetchone()

    if result is None:
        return None

    return NotificationSubscription(
        id=str(result[0]),
        user_id=str(result[1]),
        endpoint=result[2],
        subscription_keys=json.loads(result[3]) if result[3] else None,
        platform=result[4] if len(result) > 4 else "webpush",
        created_at=result[5] if len(result) > 5 else result[4],
        updated_at=result[6] if len(result) > 6 else result[5],
    )


def delete_subscription(
    conn: duckdb.DuckDBPyConnection,
    subscription_id: str,
) -> bool:
    """Delete a notification subscription.

    Args:
        conn: Database connection.
        subscription_id: Subscription UUID.

    Returns:
        True if deleted, False if not found.
    """
    result = conn.execute(
        """
        DELETE FROM notification_subscriptions
        WHERE id = ?
        RETURNING id
        """,
        [subscription_id],
    ).fetchone()

    return result is not None
