"""Notifications persistence module.

Manages storage and retrieval of user-facing notifications.
"""

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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
    priority: int = 3
    profile: str = "default"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "message": self.message,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat(),
            "priority": self.priority,
            "profile": self.profile,
        }


def _generate_dedupe_key(event_type: str, metadata: dict[str, Any] | None) -> str:
    """Generate a deduplication key based on event type and metadata.

    Args:
        event_type: Type of event.
        metadata: Event metadata containing repo, target ref, etc.

    Returns:
        Dedupe key string (hash of key components).
    """
    if not metadata:
        # No metadata, just use event type
        return hashlib.sha256(event_type.encode()).hexdigest()[:16]

    # Extract key fields for deduplication
    repo = metadata.get("repo", "")
    pr_number = metadata.get("pr_number", "")
    issue_number = metadata.get("issue_number", "")
    head_branch = metadata.get("head_branch", "")
    commit_sha = metadata.get("commit_sha", "")

    # Build dedupe components
    components = [event_type, repo]
    if pr_number:
        components.append(f"pr:{pr_number}")
    if issue_number:
        components.append(f"issue:{issue_number}")
    if head_branch:
        components.append(f"branch:{head_branch}")
    if commit_sha:
        components.append(f"commit:{commit_sha}")

    # Hash the components
    dedupe_string = "|".join(str(c) for c in components)
    return hashlib.sha256(dedupe_string.encode()).hexdigest()[:16]


def _get_event_priority(event_type: str) -> int:
    """Get priority level for an event type.

    Priority scale: 1 (low) to 5 (high)
    - 5: Critical events (PR merged, deployment failures, security alerts)
    - 4: Important events (PR opened/closed, review requested)
    - 3: Medium events (PR synchronized, check suite status)
    - 2: Low events (PR labeled, comments)
    - 1: Very low events (minor updates)

    Args:
        event_type: Type of event.

    Returns:
        Priority level (1-5).
    """
    # High priority events
    if event_type in [
        "webhook.pr_merged",
        "webhook.deployment_failure",
        "webhook.security_alert",
        "webhook.check_suite_failure",
    ]:
        return 5

    # Important events
    if event_type in [
        "webhook.pr_opened",
        "webhook.pr_closed",
        "webhook.review_requested",
        "webhook.pr_review_submitted",
    ]:
        return 4

    # Medium priority events
    if event_type in [
        "webhook.pr_synchronize",
        "webhook.pr_reopened",
        "webhook.check_suite_completed",
        "webhook.check_suite_success",
    ]:
        return 3

    # Low priority events
    if event_type in [
        "webhook.pr_labeled",
        "webhook.pr_unlabeled",
        "webhook.issue_comment",
    ]:
        return 2

    # Default to medium priority for unknown events
    return 3


def _should_throttle_notification(priority: int, profile: str) -> bool:
    """Determine if a notification should be throttled based on priority and profile.

    Args:
        priority: Notification priority (1-5).
        profile: User profile (workout, commute, kitchen, default).

    Returns:
        True if notification should be throttled (not created), False otherwise.
    """
    # Profile-specific thresholds
    thresholds = {
        "workout": 4,  # Only high priority (4+)
        "commute": 3,  # Medium and above (3+)
        "kitchen": 2,  # Low and above (2+)
        "default": 1,  # Very low and above (1+)
    }

    threshold = thresholds.get(profile, 1)  # Default to permissive
    return priority < threshold


def create_notification(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None = None,
    profile: str = "default",
    priority: int | None = None,
    dedupe_window_seconds: int = 300,
) -> Notification | None:
    """Create a new notification with deduplication and throttling.

    Args:
        conn: Database connection.
        user_id: User to notify (string, will be converted to UUID).
        event_type: Type of event (e.g., "task_created", "task_state_changed", "webhook.pr_opened").
        message: Human-readable notification message.
        metadata: Optional additional structured data.
        profile: User profile for throttling decisions (workout, commute, kitchen, default).
        priority: Optional priority override (1-5). If None, determined from event_type.
        dedupe_window_seconds: Time window in seconds for deduplication (default: 300 = 5 minutes).

    Returns:
        Created Notification object, or None if throttled/deduplicated.
    """
    # Determine priority
    if priority is None:
        priority = _get_event_priority(event_type)

    # Check throttling
    if _should_throttle_notification(priority, profile):
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            "Notification throttled: event_type=%s, priority=%d, profile=%s",
            event_type,
            priority,
            profile,
        )
        return None

    # Generate dedupe key
    dedupe_key = _generate_dedupe_key(event_type, metadata)

    # Convert user_id to UUID if it's not already one
    try:
        user_uuid = (
            uuid.UUID(user_id) if "-" in user_id else uuid.uuid5(uuid.NAMESPACE_DNS, user_id)
        )
    except (ValueError, AttributeError):
        # If conversion fails, generate a UUID from the string
        user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, user_id)

    # Check for duplicate within dedupe window
    now = datetime.now(UTC)
    dedupe_cutoff = now - timedelta(seconds=dedupe_window_seconds)

    existing = conn.execute(
        """
        SELECT id, created_at
        FROM notifications
        WHERE user_id = ? AND dedupe_key = ? AND created_at > ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        [user_uuid, dedupe_key, dedupe_cutoff],
    ).fetchone()

    if existing:
        import logging

        logger = logging.getLogger(__name__)
        logger.debug(
            "Notification deduplicated: event_type=%s, dedupe_key=%s, existing_id=%s",
            event_type,
            dedupe_key,
            existing[0],
        )
        # Return the existing notification (converted to Notification object)
        # We'll just return None to indicate it was deduplicated
        return None

    # Create new notification
    notification_id = str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO notifications
        (id, user_id, event_type, message, metadata, created_at, priority, profile, dedupe_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            notification_id,
            user_uuid,
            event_type,
            message,
            json.dumps(metadata) if metadata else None,
            now,
            priority,
            profile,
            dedupe_key,
        ],
    )

    notification = Notification(
        id=notification_id,
        user_id=user_id,
        event_type=event_type,
        message=message,
        metadata=metadata,
        created_at=now,
        priority=priority,
        profile=profile,
    )

    # Optionally deliver notification via push provider
    _deliver_notification(conn, notification)

    return notification


def _deliver_notification(
    conn: duckdb.DuckDBPyConnection,
    notification: Notification,
) -> None:
    """Deliver notification via push provider if enabled.

    Args:
        conn: Database connection.
        notification: Notification to deliver.
    """
    import logging

    from handsfree.notifications import get_notification_provider

    logger = logging.getLogger(__name__)
    provider = get_notification_provider()

    if provider is None:
        # Push notifications disabled
        return

    # Get subscriptions for this user
    from handsfree.db.notification_subscriptions import list_subscriptions

    subscriptions = list_subscriptions(conn, notification.user_id)

    if not subscriptions:
        logger.debug("No push subscriptions for user %s, skipping delivery", notification.user_id)
        return

    # Prepare notification payload
    notification_data = {
        "id": notification.id,
        "event_type": notification.event_type,
        "message": notification.message,
        "metadata": notification.metadata or {},
        "created_at": notification.created_at.isoformat(),
    }

    # Send to all subscriptions
    for subscription in subscriptions:
        try:
            result = provider.send(
                subscription_endpoint=subscription.endpoint,
                notification_data=notification_data,
                subscription_keys=subscription.subscription_keys,
            )
            if result["ok"]:
                logger.info(
                    "Delivered notification %s to subscription %s: %s",
                    notification.id,
                    subscription.id,
                    result.get("delivery_id"),
                )
            else:
                logger.warning(
                    "Failed to deliver notification %s to subscription %s: %s",
                    notification.id,
                    subscription.id,
                    result.get("message"),
                )
        except Exception as e:
            logger.error(
                "Error delivering notification %s to subscription %s: %s",
                notification.id,
                subscription.id,
                e,
                exc_info=True,
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
            SELECT id, user_id, event_type, message, metadata, created_at, priority, profile
            FROM notifications
            WHERE user_id = ? AND created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        params = [user_uuid, since, limit]
    else:
        query = """
            SELECT id, user_id, event_type, message, metadata, created_at, priority, profile
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
            priority=row[6] if len(row) > 6 else 3,  # Default priority for backward compatibility
            profile=row[7]
            if len(row) > 7
            else "default",  # Default profile for backward compatibility
        )
        for row in result
    ]
