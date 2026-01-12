"""Persistence API for action logs (audit trail)."""

import json
from typing import Any
from uuid import UUID, uuid4

import duckdb


def create_action_log(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    action_type: str,
    ok: bool,
    target: str | None = None,
    request: dict[str, Any] | None = None,
    result: dict[str, Any] | None = None,
    idempotency_key: str | None = None,
) -> UUID:
    """
    Create an action log entry.

    Args:
        conn: Database connection.
        user_id: User ID who performed the action.
        action_type: Type of action (e.g., "merge_pr", "rerun_workflow").
        ok: Whether the action succeeded.
        target: Optional target of the action (e.g., "owner/repo#123").
        request: Optional request payload.
        result: Optional result payload.
        idempotency_key: Optional idempotency key (for deduplication).

    Returns:
        The log entry ID.
    """
    # Check for existing entry with same idempotency_key
    if idempotency_key:
        existing = conn.execute(
            "SELECT id FROM action_logs WHERE idempotency_key = ?",
            [idempotency_key],
        ).fetchone()
        if existing:
            return UUID(str(existing[0]))

    log_id = uuid4()

    conn.execute(
        """
        INSERT INTO action_logs
            (id, user_id, action_type, target, request, result, ok, idempotency_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            str(log_id),
            str(user_id),
            action_type,
            target,
            json.dumps(request) if request else None,
            json.dumps(result) if result else None,
            ok,
            idempotency_key,
        ],
    )

    return log_id


def get_action_logs(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID | None = None,
    action_type: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Query action logs with optional filters.

    Args:
        conn: Database connection.
        user_id: Optional filter by user ID.
        action_type: Optional filter by action type.
        limit: Maximum number of results (default: 100).

    Returns:
        List of log entries (most recent first).
    """
    query = """
        SELECT id, user_id, action_type, target, request, result, ok, idempotency_key, created_at
        FROM action_logs
        WHERE 1=1
    """
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(str(user_id))

    if action_type:
        query += " AND action_type = ?"
        params.append(action_type)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    results = conn.execute(query, params).fetchall()

    return [
        {
            "id": row[0],
            "user_id": str(row[1]),
            "action_type": row[2],
            "target": row[3],
            "request": json.loads(row[4]) if row[4] else None,
            "result": json.loads(row[5]) if row[5] else None,
            "ok": row[6],
            "idempotency_key": row[7],
            "created_at": row[8],
        }
        for row in results
    ]
