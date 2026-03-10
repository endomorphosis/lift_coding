"""Notifications persistence module.

Manages storage and retrieval of user-facing notifications.
"""

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


def _execution_mode_label(mode: str | None) -> str | None:
    """Return a short label for a resolved execution mode."""
    normalized = str(mode or "").strip().lower()
    return {
        "direct_import": "Local",
        "mcp_remote": "Remote",
    }.get(normalized)


def _resolve_execution_modes(metadata: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """Extract preferred and resolved execution modes from notification metadata."""
    metadata = metadata or {}
    envelope = metadata.get("result_envelope")
    preferred_mode = metadata.get("mcp_preferred_execution_mode")
    resolved_mode = metadata.get("mcp_execution_mode")

    if not isinstance(preferred_mode, str) and isinstance(envelope, dict):
        preferred_mode = envelope.get("preferred_execution_mode")
    if not isinstance(resolved_mode, str) and isinstance(envelope, dict):
        resolved_mode = envelope.get("execution_mode")

    preferred = (
        preferred_mode.strip().lower()
        if isinstance(preferred_mode, str) and preferred_mode.strip()
        else None
    )
    resolved = (
        resolved_mode.strip().lower()
        if isinstance(resolved_mode, str) and resolved_mode.strip()
        else None
    )
    return preferred, resolved


def _execution_mode_detail_line(metadata: dict[str, Any] | None) -> str | None:
    """Return an execution detail line for notification cards."""
    preferred_mode, resolved_mode = _resolve_execution_modes(metadata)
    label = _execution_mode_label(resolved_mode)
    if not label:
        return None
    if preferred_mode == "direct_import" and resolved_mode == "mcp_remote":
        return f"Execution: {label} (local unavailable)"
    return f"Execution: {label}"


def _render_result_lines(metadata: dict[str, Any] | None) -> list[str]:
    """Render compact result lines from notification metadata."""
    if not metadata:
        return []

    lines: list[str] = []
    result_envelope = metadata.get("result_envelope")
    result_output = (
        result_envelope.get("structured_output")
        if isinstance(result_envelope, dict)
        else metadata.get("result_output")
    )
    if isinstance(result_output, dict):
        for key in ("message", "status", "expanded_queries", "target_terms", "seed_urls"):
            value = result_output.get(key)
            if value is None:
                continue
            if isinstance(value, list):
                rendered = ", ".join(str(item) for item in value[:3])
            else:
                rendered = str(value)
            if rendered:
                lines.append(f"{key}: {rendered}")

        task_info = result_output.get("task")
        if isinstance(task_info, dict):
            task_status = task_info.get("status")
            task_id = task_info.get("task_id")
            if task_status:
                lines.append(f"task.status: {task_status}")
            if task_id:
                lines.append(f"task.id: {task_id}")

    preview = (
        result_envelope.get("summary")
        if isinstance(result_envelope, dict)
        else metadata.get("result_preview")
    )
    if not lines and isinstance(preview, str) and preview.strip():
        lines.append(f"Result: {preview.strip()}")
    execution_line = _execution_mode_detail_line(metadata)
    if execution_line and execution_line not in lines:
        if len(lines) >= 3:
            lines = lines[:2]
        lines.append(execution_line)
    return lines[:3]


def _notification_workflow(metadata: dict[str, Any] | None) -> str | None:
    """Extract workflow name from notification metadata."""
    metadata = metadata or {}
    result_envelope = metadata.get("result_envelope")
    structured_output = (
        result_envelope.get("structured_output")
        if isinstance(result_envelope, dict)
        else metadata.get("result_output")
    )
    if isinstance(structured_output, dict):
        workflow = structured_output.get("workflow")
        if isinstance(workflow, str) and workflow.strip():
            return workflow.strip()
    return None


def _append_local_wearables_actions(
    items: list[dict[str, Any]],
    workflow: str | None,
) -> list[dict[str, Any]]:
    """Prepend app-local wearables actions for connectivity receipts."""
    if workflow != "wearables_bridge_connectivity":
        return list(items)

    next_items = list(items)
    if not any(item.get("id") == "mobile_reconnect_wearables_target" for item in next_items):
        next_items.insert(
            0,
            {
                "id": "mobile_reconnect_wearables_target",
                "label": "Reconnect Target",
                "phrase": "reconnect the selected wearables target",
            },
        )
    if not any(item.get("id") == "mobile_open_wearables_diagnostics" for item in next_items):
        next_items.insert(
            0,
            {
                "id": "mobile_open_wearables_diagnostics",
                "label": "Open Diagnostics",
                "phrase": "open wearables bridge diagnostics",
            },
        )
    return next_items


def _append_local_wearables_action_phrases(
    actions: list[str],
    workflow: str | None,
) -> list[str]:
    """Prepend user-facing wearables local action phrases."""
    if workflow != "wearables_bridge_connectivity":
        return list(actions)

    next_actions = list(actions)
    if "reconnect the selected wearables target" not in next_actions:
        next_actions.insert(0, "reconnect the selected wearables target")
    if "open wearables bridge diagnostics" not in next_actions:
        next_actions.insert(0, "open wearables bridge diagnostics")
    return next_actions


def _notification_result_actions(
    capability: str | None,
    deep_link: str | None,
) -> list[str]:
    """Return user-facing result actions for notification cards."""
    actions = [
        "open that result",
        "show task details for that result",
        "show another result like this",
        "save that result to ipfs",
        "save that result to ipfs locally",
        "save that result to ipfs remotely",
    ]
    if isinstance(deep_link, str) and deep_link.startswith("ipfs://"):
        actions.extend(
            [
                "read the cid",
                "share that cid",
                "pin that",
                "pin that locally",
                "pin that remotely",
                "unpin that",
                "unpin that locally",
                "unpin that remotely",
            ]
        )
    normalized_capability = (capability or "").strip().lower()
    if normalized_capability in {"workflow", "agentic_fetch"}:
        actions.append("rerun that workflow remotely")
    if normalized_capability == "agentic_fetch":
        actions.append("rerun that fetch with https://example.com remotely")
    if normalized_capability == "dataset_discovery":
        actions.append("rerun that dataset search with labor law datasets remotely")
    return actions


def _notification_result_action_items(
    capability: str | None,
    deep_link: str | None,
) -> list[dict[str, Any]]:
    """Return structured actions for notification cards."""
    save_mode_items: list[dict[str, Any]] = [
        {
            "id": "save_result_to_ipfs_local",
            "label": "Save To IPFS Locally",
            "phrase": "save that result to ipfs locally",
            "execution_mode": "direct_import",
            "execution_mode_label": "Local",
            "params": {"mcp_preferred_execution_mode": "direct_import"},
        },
        {
            "id": "save_result_to_ipfs_remote",
            "label": "Save To IPFS Remotely",
            "phrase": "save that result to ipfs remotely",
            "execution_mode": "mcp_remote",
            "execution_mode_label": "Remote",
            "params": {"mcp_preferred_execution_mode": "mcp_remote"},
        },
    ]

    items: list[dict[str, Any]] = [
        {"id": "open_result", "label": "Open Result", "phrase": "open that result"},
        {
            "id": "show_result_details",
            "label": "Task Details",
            "phrase": "show task details for that result",
        },
        {
            "id": "show_related_results",
            "label": "Related Results",
            "phrase": "show another result like this",
        },
        {
            "id": "save_result_to_ipfs",
            "label": "Save To IPFS",
            "phrase": "save that result to ipfs",
        },
    ]
    cid: str | None = None
    if isinstance(deep_link, str) and deep_link.startswith("ipfs://"):
        cid = deep_link.removeprefix("ipfs://").strip() or None
    if cid:
        items.extend(
            [
                {"id": "read_cid", "label": "Read CID", "phrase": "read the cid", "params": {"cid": cid}},
                {"id": "share_cid", "label": "Share CID", "phrase": "share that cid", "params": {"cid": cid}},
                {"id": "pin_result", "label": "Pin", "phrase": "pin that", "params": {"cid": cid}},
                {
                    "id": "pin_result_local",
                    "label": "Pin Locally",
                    "phrase": "pin that locally",
                    "execution_mode": "direct_import",
                    "execution_mode_label": "Local",
                    "params": {"cid": cid, "mcp_preferred_execution_mode": "direct_import"},
                },
                {
                    "id": "pin_result_remote",
                    "label": "Pin Remotely",
                    "phrase": "pin that remotely",
                    "execution_mode": "mcp_remote",
                    "execution_mode_label": "Remote",
                    "params": {"cid": cid, "mcp_preferred_execution_mode": "mcp_remote"},
                },
                {
                    "id": "unpin_result_local",
                    "label": "Unpin Locally",
                    "phrase": "unpin that locally",
                    "execution_mode": "direct_import",
                    "execution_mode_label": "Local",
                    "params": {"cid": cid, "mcp_preferred_execution_mode": "direct_import"},
                },
                {
                    "id": "unpin_result_remote",
                    "label": "Unpin Remotely",
                    "phrase": "unpin that remotely",
                    "execution_mode": "mcp_remote",
                    "execution_mode_label": "Remote",
                    "params": {"cid": cid, "mcp_preferred_execution_mode": "mcp_remote"},
                },
            ]
        )
        items.extend(save_mode_items)
        items.append({"id": "unpin_result", "label": "Unpin", "phrase": "unpin that", "params": {"cid": cid}})
    else:
        items.extend(save_mode_items)
    normalized_capability = (capability or "").strip().lower()
    if normalized_capability in {"workflow", "agentic_fetch"}:
        items.append(
            {
                "id": "rerun_workflow",
                "label": "Rerun Workflow",
                "phrase": "rerun that workflow remotely",
                "execution_mode": "mcp_remote",
                "execution_mode_label": "Remote",
                "params": {"mcp_preferred_execution_mode": "mcp_remote"},
            }
        )
    if normalized_capability == "agentic_fetch":
        items.append(
            {
                "id": "rerun_fetch_with_url",
                "label": "Rerun Fetch",
                "phrase": "rerun that fetch with https://example.com remotely",
                "execution_mode": "mcp_remote",
                "execution_mode_label": "Remote",
                "params": {
                    "mcp_seed_url": "https://example.com",
                    "mcp_preferred_execution_mode": "mcp_remote",
                },
            }
        )
    if normalized_capability == "dataset_discovery":
        items.append(
            {
                "id": "rerun_dataset_search",
                "label": "Rerun Dataset Search",
                "phrase": "rerun that dataset search with labor law datasets remotely",
                "execution_mode": "mcp_remote",
                "execution_mode_label": "Remote",
                "params": {
                    "mcp_input": "labor law datasets",
                    "mcp_preferred_execution_mode": "mcp_remote",
                },
            }
        )
    return items


def build_notification_card(
    notification_id: str,
    event_type: str,
    message: str,
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Build a compact UI card payload for notification consumers."""
    if not event_type.startswith("task_"):
        return None

    metadata = metadata or {}
    workflow = _notification_workflow(metadata)
    state = metadata.get("state", event_type.removeprefix("task_"))
    provider_label = metadata.get("provider_label") or metadata.get("provider") or "Agent task"
    task_id = str(metadata.get("task_id", ""))[:8]
    title = f"{provider_label} {state}".strip().title()

    instruction = metadata.get("instruction")
    lines: list[str] = []
    if isinstance(instruction, str) and instruction.strip():
        lines.append(f"Instruction: {instruction[:60]}")

    lines.extend(_render_result_lines(metadata))
    if not lines:
        lines.append(message)

    deep_link: str | None = None
    result_envelope = metadata.get("result_envelope")
    if isinstance(metadata.get("pr_url"), str) and metadata["pr_url"].strip():
        deep_link = metadata["pr_url"].strip()
    else:
        cid = metadata.get("mcp_cid")
        if not cid and isinstance(result_envelope, dict):
            artifact_refs = result_envelope.get("artifact_refs")
            if isinstance(artifact_refs, dict):
                cid = artifact_refs.get("result_cid")
        if not cid and isinstance(metadata.get("result_output"), dict):
            cid = metadata["result_output"].get("cid")
        if isinstance(cid, str) and cid.strip():
            deep_link = f"ipfs://{cid.strip()}"
        elif (
            metadata.get("mcp_capability") == "agentic_fetch"
            and isinstance(metadata.get("mcp_seed_url"), str)
            and metadata["mcp_seed_url"].strip()
        ):
            deep_link = metadata["mcp_seed_url"].strip()
        elif isinstance(metadata.get("task_id"), str) and metadata["task_id"].strip():
            deep_link = f"/v1/agents/tasks/{metadata['task_id'].strip()}"
        else:
            deep_link = f"/v1/notifications/{notification_id}"

    action_items = (
        metadata.get("follow_up_actions")
        if isinstance(metadata.get("follow_up_actions"), list) and metadata.get("follow_up_actions")
        else _notification_result_action_items(
            metadata.get("mcp_capability") if isinstance(metadata.get("mcp_capability"), str) else None,
            deep_link,
        )
    )

    return {
        "title": title,
        "subtitle": f"Task {task_id} • {state}" if task_id else state,
        "lines": lines[:4],
        "deep_link": deep_link,
        "action_items": _append_local_wearables_actions(action_items, workflow),
        "actions": _append_local_wearables_action_phrases(
            _notification_result_actions(
                metadata.get("mcp_capability") if isinstance(metadata.get("mcp_capability"), str) else None,
                deep_link,
            ),
            workflow,
        ),
    }


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
    last_delivery_attempt: datetime | None = None
    delivery_status: str = "pending"  # pending, success, failed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        result = {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "message": self.message,
            "metadata": self.metadata or {},
            "created_at": self.created_at.isoformat(),
            "priority": self.priority,
            "profile": self.profile,
        }
        # Only include delivery fields if they're set
        if self.last_delivery_attempt:
            result["last_delivery_attempt"] = self.last_delivery_attempt.isoformat()
        if self.delivery_status != "pending":
            result["delivery_status"] = self.delivery_status
        card = build_notification_card(self.id, self.event_type, self.message, self.metadata)
        if card is not None:
            result["card"] = card
        return result


def generate_dedupe_key(event_type: str, metadata: dict[str, Any] | None) -> str:
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


def get_event_priority(event_type: str) -> int:
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


def should_throttle_notification(priority: int, profile: str) -> bool:
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
        priority = get_event_priority(event_type)

    # Check throttling
    if should_throttle_notification(priority, profile):
        logger.debug(
            "Notification throttled: event_type=%s, priority=%d, profile=%s",
            event_type,
            priority,
            profile,
        )
        return None

    # Generate dedupe key
    dedupe_key = generate_dedupe_key(event_type, metadata)

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
        logger.debug(
            "Notification deduplicated: event_type=%s, dedupe_key=%s, existing_id=%s",
            event_type,
            dedupe_key,
            existing[0],
        )
        # Notification deduplicated - return None to indicate no new notification created
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
    import os

    from handsfree.notifications.provider import get_provider_for_platform

    logger = logging.getLogger(__name__)

    # Check if auto-push is enabled
    auto_push_enabled = os.getenv("NOTIFICATIONS_AUTO_PUSH_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
    )
    if not auto_push_enabled:
        logger.debug(
            "Auto-push disabled via NOTIFICATIONS_AUTO_PUSH_ENABLED, "
            "skipping delivery for notification %s",
            notification.id,
        )
        return

    # Get subscriptions for this user
    from handsfree.db.notification_subscriptions import list_subscriptions

    subscriptions = list_subscriptions(conn, notification.user_id)

    if not subscriptions:
        logger.debug("No push subscriptions for user %s, skipping delivery", notification.user_id)
        # Don't update delivery status - leave it as 'pending' to indicate no delivery was attempted
        return

    # Prepare notification payload
    notification_data = {
        # Mobile clients expect this key when deciding whether to fetch full details.
        # Keep `id` as well for backward compatibility.
        "notification_id": notification.id,
        "id": notification.id,
        "event_type": notification.event_type,
        "message": notification.message,
        "metadata": notification.metadata or {},
        "created_at": notification.created_at.isoformat(),
    }
    card = build_notification_card(
        notification.id,
        notification.event_type,
        notification.message,
        notification.metadata,
    )
    if card is not None:
        notification_data["card"] = card

    # Track delivery results
    delivery_success = False

    # Send to all subscriptions using platform-specific providers
    for subscription in subscriptions:
        try:
            # Get the appropriate provider for this subscription's platform
            provider = get_provider_for_platform(subscription.platform)

            if provider is None:
                logger.warning(
                    "No provider available for platform %s, skipping subscription %s",
                    subscription.platform,
                    subscription.id,
                )
                continue

            result = provider.send(
                subscription_endpoint=subscription.endpoint,
                notification_data=notification_data,
                subscription_keys=subscription.subscription_keys,
            )
            if result["ok"]:
                logger.info(
                    "Delivered notification %s to subscription %s (platform=%s): %s",
                    notification.id,
                    subscription.id,
                    subscription.platform,
                    result.get("delivery_id"),
                )
                delivery_success = True
            else:
                logger.warning(
                    "Failed to deliver notification %s to subscription %s (platform=%s): %s",
                    notification.id,
                    subscription.id,
                    subscription.platform,
                    result.get("message"),
                )
        except Exception as e:
            logger.error(
                "Error delivering notification %s to subscription %s (platform=%s): %s",
                notification.id,
                subscription.id,
                subscription.platform,
                e,
                exc_info=True,
            )

    # Update delivery tracking in database
    now = datetime.now(UTC)
    if delivery_success:
        # At least one delivery succeeded
        delivery_status = "success"
    else:
        # All deliveries failed (or no provider available)
        delivery_status = "failed"

    conn.execute(
        """
        UPDATE notifications
        SET last_delivery_attempt = ?, delivery_status = ?
        WHERE id = ?
        """,
        [now, delivery_status, notification.id],
    )


def get_notification(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    notification_id: str,
) -> Notification | None:
    """Get a single notification by ID for a specific user.

    Args:
        conn: Database connection.
        user_id: User ID to filter by (string, will be converted to UUID).
        notification_id: Notification ID to fetch.

    Returns:
        Notification object if found and belongs to user, None otherwise.
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
        SELECT id, user_id, event_type, message, metadata, created_at, priority, profile,
               last_delivery_attempt, delivery_status
        FROM notifications
        WHERE id = ? AND user_id = ?
    """
    params = [notification_id, user_uuid]

    result = conn.execute(query, params).fetchone()

    if not result:
        return None

    return Notification(
        id=str(result[0]),  # Convert UUID to string
        user_id=user_id,  # Return the original string user_id
        event_type=result[2],
        message=result[3],
        metadata=json.loads(result[4]) if result[4] else None,  # Parse JSON string
        created_at=result[5],
        priority=result[6] if len(result) > 6 else 3,  # Default priority for backward compatibility
        profile=result[7]
        if len(result) > 7
        else "default",  # Default profile for backward compatibility
        last_delivery_attempt=result[8] if len(result) > 8 else None,
        delivery_status=result[9] if len(result) > 9 else "pending",
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
            SELECT id, user_id, event_type, message, metadata, created_at, priority, profile,
                   last_delivery_attempt, delivery_status
            FROM notifications
            WHERE user_id = ? AND created_at > ?
            ORDER BY created_at DESC
            LIMIT ?
        """
        params = [user_uuid, since, limit]
    else:
        query = """
            SELECT id, user_id, event_type, message, metadata, created_at, priority, profile,
                   last_delivery_attempt, delivery_status
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
            last_delivery_attempt=row[8] if len(row) > 8 else None,
            delivery_status=row[9] if len(row) > 9 else "pending",
        )
        for row in result
    ]
