"""Action logs persistence module.

Manages audit logs for side-effect actions with idempotency support.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


@dataclass
class ActionLog:
    """Represents an audit log entry for a side-effect action."""

    id: str
    user_id: str
    action_type: str
    target: str | None
    request: dict[str, Any] | None
    result: dict[str, Any] | None
    ok: bool
    idempotency_key: str | None
    created_at: datetime


def write_action_log(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_type: str,
    ok: bool,
    target: str | None = None,
    request: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> ActionLog:
    """Write an action log entry.

    Args:
        conn: Database connection.
        user_id: UUID of the user performing the action.
        action_type: Type of action (e.g., "merge_pr", "create_issue").
        ok: Whether the action succeeded.
        target: Target of the action (e.g., "owner/repo#123").
        request: Request payload (JSON-serializable).
        result: Result payload (JSON-serializable).
        idempotency_key: Optional key to prevent duplicate logs.

    Returns:
        Created ActionLog object.

    Raises:
        ValueError: If idempotency_key is provided and already exists.
    """
    # Check for existing idempotency key
    if idempotency_key:
        existing = conn.execute(
            "SELECT id FROM action_logs WHERE idempotency_key = ?",
            [idempotency_key],
        ).fetchone()
        if existing:
            raise ValueError(f"Action log with idempotency_key '{idempotency_key}' already exists")

    log_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    conn.execute(
        """
        INSERT INTO action_logs
        (id, user_id, action_type, target, request, result, ok, idempotency_key, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [log_id, user_id, action_type, target, request, result, ok, idempotency_key, now],
    )

    return ActionLog(
        id=log_id,
        user_id=user_id,
        action_type=action_type,
        target=target,
        request=request,
        result=result,
        ok=ok,
        idempotency_key=idempotency_key,
        created_at=now,
    )


def get_action_logs(
    conn: duckdb.DuckDBPyConnection,
    user_id: str | None = None,
    action_type: str | None = None,
    limit: int = 100,
) -> list[ActionLog]:
    """Query action logs with optional filters.

    Args:
        conn: Database connection.
        user_id: Filter by user ID.
        action_type: Filter by action type.
        limit: Maximum number of logs to return.

    Returns:
        List of ActionLog objects, ordered by created_at DESC.
    """
    query = (
        "SELECT id, user_id, action_type, target, request, result, ok, "
        "idempotency_key, created_at FROM action_logs WHERE 1=1"
    )
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(user_id)

    if action_type:
        query += " AND action_type = ?"
        params.append(action_type)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    results = conn.execute(query, params).fetchall()

    return [
        ActionLog(
            id=str(row[0]),
            user_id=str(row[1]),
            action_type=row[2],
            target=row[3],
            request=json.loads(row[4]) if isinstance(row[4], str) and row[4] else row[4],
            result=json.loads(row[5]) if isinstance(row[5], str) and row[5] else row[5],
            ok=row[6],
            idempotency_key=row[7],
            created_at=row[8],
        )
        for row in results
    ]


def get_action_log_by_id(
    conn: duckdb.DuckDBPyConnection,
    log_id: str,
) -> ActionLog | None:
    """Get a specific action log by ID.

    Args:
        conn: Database connection.
        log_id: The log entry ID.

    Returns:
        ActionLog if found, None otherwise.
    """
    result = conn.execute(
        """
        SELECT id, user_id, action_type, target, request, result, ok, idempotency_key, created_at
        FROM action_logs
        WHERE id = ?
        """,
        [log_id],
    ).fetchone()

    if not result:
        return None

    return ActionLog(
        id=str(result[0]),
        user_id=str(result[1]),
        action_type=result[2],
        target=result[3],
        request=json.loads(result[4]) if isinstance(result[4], str) and result[4] else result[4],
        result=json.loads(result[5]) if isinstance(result[5], str) and result[5] else result[5],
        ok=result[6],
        idempotency_key=result[7],
        created_at=result[8],
    )
