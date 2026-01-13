"""Notifications persistence module.

Manages storage and retrieval of user-facing notifications.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


@dataclass
class Notification:
    """Represents a user notification."""

    id: str
    user_id: str
    event_type: str
    message: str
    metadata: dict[str, Any] | None
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "message": self.message,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat(),
        }


def create_notification(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> Notification:
    """Create a new notification.

    Args:
        conn: Database connection.
        user_id: User to notify (string, will be converted to UUID).
        event_type: Type of event (e.g., "task_created", "task_state_changed", "webhook.pr_opened").
        message: Human-readable notification message.
        metadata: Optional additional structured data.

    Returns:
        Created Notification object.
    """
    notification_id = str(uuid.uuid4())
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
        INSERT INTO notifications
        (id, user_id, event_type, message, metadata, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [notification_id, user_uuid, event_type, message, json.dumps(metadata) if metadata else None, now],
    )

    return Notification(
        id=notification_id,
        user_id=user_id,
        event_type=event_type,
        message=message,
        metadata=metadata,
        created_at=now,
    )


def list_notifications(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    since: datetime | None = None,
    limit: int = 50,
) -> list[Notification]:
    """List notifications for a user with optional filtering.

    Args:
        conn: Database connection.
        user_id: User ID to filter by (string, will be converted to UUID).
        since: Optional timestamp to get notifications after this time.
        limit: Maximum number of notifications to return (default: 50, max: 100).

    Returns:
        List of Notification objects, ordered by created_at DESC.
    """
    # Clamp limit to reasonable bounds
    limit = max(1, min(limit, 100))

    # Convert user_id to UUID if it's not already one
    try:
        user_uuid = (
            uuid.UUID(user_id) if "-" in user_id else uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
        )
    except (ValueError, AttributeError):
        # If conversion fails, generate a UUID from the string
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    if since:
        query = """
            SELECT id, user_id, event_type, message, metadata, created_at
            FROM notifications
            WHERE user_id = ? AND created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        params = [user_uuid, since, limit]
    else:
        query = """
            SELECT id, user_id, event_type, message, metadata, created_at
            FROM notifications
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        params = [user_uuid, limit]

    result = conn.execute(query, params).fetchall()

    return [
        Notification(
            id=str(row[0]),  # Convert UUID to string
            user_id=user_id,  # Return the original string user_id
            event_type=row[2],
            message=row[3],
            metadata=json.loads(row[4]) if row[4] else None,  # Parse JSON string
            created_at=row[5],
        )
        for row in result
    ]
