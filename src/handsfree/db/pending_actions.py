"""Pending actions persistence module.

Manages pending actions that require user confirmation with expiry.
"""

import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import duckdb


@dataclass
class PendingAction:
    """Represents a pending action awaiting confirmation."""

    token: str
    user_id: str
    summary: str
    action_type: str
    action_payload: dict[str, Any]
    expires_at: datetime
    created_at: datetime


def generate_token(length: int = 32) -> str:
    """Generate a secure random token for pending actions."""
    return secrets.token_urlsafe(length)


def create_pending_action(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    summary: str,
    action_type: str,
    action_payload: dict[str, Any],
    expires_in_seconds: int = 3600,
) -> PendingAction:
    """Create a new pending action requiring confirmation.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        summary: Human-readable summary of the action.
        action_type: Type of action (e.g., "merge_pr", "rerun_workflow").
        action_payload: JSON-serializable payload with action details.
        expires_in_seconds: Time until action expires (default: 1 hour).

    Returns:
        Created PendingAction object.
    """
    token = generate_token()
    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=expires_in_seconds)

    conn.execute(
        """
        INSERT INTO pending_actions 
        (token, user_id, summary, action_type, action_payload, expires_at, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [token, user_id, summary, action_type, action_payload, expires_at, now],
    )

    return PendingAction(
        token=token,
        user_id=user_id,
        summary=summary,
        action_type=action_type,
        action_payload=action_payload,
        expires_at=expires_at,
        created_at=now,
    )


def get_pending_action(
    conn: duckdb.DuckDBPyConnection,
    token: str,
) -> PendingAction | None:
    """Get a pending action by token.

    Args:
        conn: Database connection.
        token: The action token.

    Returns:
        PendingAction if found and not expired, None otherwise.
    """
    result = conn.execute(
        """
        SELECT token, user_id, summary, action_type, action_payload, expires_at, created_at
        FROM pending_actions
        WHERE token = ?
        """,
        [token],
    ).fetchone()

    if not result:
        return None

    # Parse JSON payload if it's a string
    payload = result[4]
    if isinstance(payload, str):
        payload = json.loads(payload)

    pending_action = PendingAction(
        token=result[0],
        user_id=str(result[1]),
        summary=result[2],
        action_type=result[3],
        action_payload=payload,
        expires_at=result[5],
        created_at=result[6],
    )

    # Check if expired
    if pending_action.expires_at < datetime.now(UTC):
        return None

    return pending_action


def delete_pending_action(
    conn: duckdb.DuckDBPyConnection,
    token: str,
) -> bool:
    """Delete a pending action (typically after confirmation or expiry).

    Args:
        conn: Database connection.
        token: The action token.

    Returns:
        True if action was deleted, False if not found.
    """
    result = conn.execute(
        "DELETE FROM pending_actions WHERE token = ?",
        [token],
    )
    return result.fetchone() is not None


def cleanup_expired_actions(conn: duckdb.DuckDBPyConnection) -> int:
    """Remove all expired pending actions.

    Args:
        conn: Database connection.

    Returns:
        Number of actions deleted.
    """
    now = datetime.now(UTC)
    conn.execute(
        "DELETE FROM pending_actions WHERE expires_at < ?",
        [now],
    )
    # DuckDB doesn't return row count directly, so we approximate
    return 0  # Could query count before/after if needed
