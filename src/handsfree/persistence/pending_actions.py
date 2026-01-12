"""Persistence API for pending actions."""

import json
import secrets
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import duckdb


def create_pending_action(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    summary: str,
    action_type: str,
    action_payload: dict[str, Any],
    expires_in_seconds: int = 3600,
    token: str | None = None,
) -> str:
    """
    Create a new pending action.

    Args:
        conn: Database connection.
        user_id: User ID who initiated the action.
        summary: Human-readable summary of the action.
        action_type: Type of action (e.g., "merge_pr", "rerun_workflow").
        action_payload: JSON payload with action details.
        expires_in_seconds: Expiry time in seconds (default: 1 hour).
        token: Optional token (auto-generated if not provided).

    Returns:
        The action token (for confirmation).
    """
    if token is None:
        token = secrets.token_urlsafe(32)

    expires_at = datetime.now() + timedelta(seconds=expires_in_seconds)

    conn.execute(
        """
        INSERT INTO pending_actions
            (token, user_id, summary, action_type, action_payload, expires_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [token, str(user_id), summary, action_type, json.dumps(action_payload), expires_at],
    )

    return token


def get_pending_action(conn: duckdb.DuckDBPyConnection, token: str) -> dict[str, Any] | None:
    """
    Get a pending action by token, if it exists and hasn't expired.

    Args:
        conn: Database connection.
        token: Action token.

    Returns:
        Dictionary with action details, or None if not found or expired.
    """
    result = conn.execute(
        """
        SELECT token, user_id, summary, action_type, action_payload, expires_at, created_at
        FROM pending_actions
        WHERE token = ? AND expires_at > now()
        """,
        [token],
    ).fetchone()

    if result is None:
        return None

    return {
        "token": result[0],
        "user_id": result[1],
        "summary": result[2],
        "action_type": result[3],
        "action_payload": json.loads(result[4]),
        "expires_at": result[5],
        "created_at": result[6],
    }


def delete_pending_action(conn: duckdb.DuckDBPyConnection, token: str) -> bool:
    """
    Delete a pending action (e.g., after confirmation or cancellation).

    Args:
        conn: Database connection.
        token: Action token.

    Returns:
        True if action was deleted, False if not found.
    """
    result = conn.execute(
        "DELETE FROM pending_actions WHERE token = ?",
        [token],
    )
    return result.fetchone()[0] > 0 if result else False


def cleanup_expired_actions(conn: duckdb.DuckDBPyConnection) -> int:
    """
    Delete all expired pending actions.

    Args:
        conn: Database connection.

    Returns:
        Number of actions deleted.
    """
    result = conn.execute("DELETE FROM pending_actions WHERE expires_at <= now()")
    return result.fetchone()[0] if result else 0
