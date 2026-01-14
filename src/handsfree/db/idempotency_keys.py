"""Idempotency keys persistence module.

Manages idempotency keys for exactly-once semantics with database backing.
"""

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import duckdb


@dataclass
class IdempotencyKey:
    """Represents a stored idempotency key with its response."""

    key: str
    user_id: str
    endpoint: str
    response_data: dict[str, Any]
    audit_log_id: str | None
    expires_at: datetime
    created_at: datetime


def store_idempotency_key(
    conn: duckdb.DuckDBPyConnection,
    key: str,
    user_id: str,
    endpoint: str,
    response_data: dict[str, Any],
    audit_log_id: str | None = None,
    expires_in_seconds: int = 86400,  # 24 hours default
) -> IdempotencyKey:
    """Store an idempotency key with its response.

    Implements read-before-write behavior: if key exists, returns existing entry.
    This ensures exactly-once semantics even under concurrent requests.

    Args:
        conn: Database connection.
        key: Idempotency key string.
        user_id: UUID of the user.
        endpoint: API endpoint (e.g., "/v1/command", "/v1/actions/request-review").
        response_data: JSON-serializable response data.
        audit_log_id: Optional UUID of related audit log entry.
        expires_in_seconds: Time until key expires (default: 24 hours).

    Returns:
        IdempotencyKey object (either newly created or existing).
    """
    # Read-before-write: check if key already exists
    existing = get_idempotency_key(conn, key)
    if existing:
        return existing

    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=expires_in_seconds)

    # Insert new key (may fail if concurrent request inserted same key)
    try:
        conn.execute(
            """
            INSERT INTO idempotency_keys
            (key, user_id, endpoint, response_data, audit_log_id, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [key, user_id, endpoint, response_data, audit_log_id, expires_at, now],
        )

        return IdempotencyKey(
            key=key,
            user_id=user_id,
            endpoint=endpoint,
            response_data=response_data,
            audit_log_id=audit_log_id,
            expires_at=expires_at,
            created_at=now,
        )
    except duckdb.ConstraintException:
        # Concurrent insert - read the existing key
        existing = get_idempotency_key(conn, key)
        if existing:
            return existing
        # Should not happen, but re-raise if it does
        raise


def get_idempotency_key(
    conn: duckdb.DuckDBPyConnection,
    key: str,
) -> IdempotencyKey | None:
    """Get an idempotency key and its response.

    Returns None if key doesn't exist or is expired.

    Args:
        conn: Database connection.
        key: Idempotency key string.

    Returns:
        IdempotencyKey if found and not expired, None otherwise.
    """
    result = conn.execute(
        """
        SELECT key, user_id, endpoint, response_data, audit_log_id, expires_at, created_at
        FROM idempotency_keys
        WHERE key = ?
        """,
        [key],
    ).fetchone()

    if not result:
        return None

    # Parse response_data if it's a string
    response_data = result[3]
    if isinstance(response_data, str):
        response_data = json.loads(response_data)

    idempotency_key = IdempotencyKey(
        key=result[0],
        user_id=str(result[1]),
        endpoint=result[2],
        response_data=response_data,
        audit_log_id=str(result[4]) if result[4] else None,
        expires_at=result[5],
        created_at=result[6],
    )

    # Check if expired
    if idempotency_key.expires_at < datetime.now(UTC):
        return None

    return idempotency_key


def get_idempotency_response(
    conn: duckdb.DuckDBPyConnection,
    key: str,
) -> dict[str, Any] | None:
    """Get the cached response for an idempotency key.

    Convenience method that returns just the response data.

    Args:
        conn: Database connection.
        key: Idempotency key string.

    Returns:
        Response data dict if key found and not expired, None otherwise.
    """
    idempotency_key = get_idempotency_key(conn, key)
    if idempotency_key:
        return idempotency_key.response_data
    return None


def cleanup_expired_keys(conn: duckdb.DuckDBPyConnection) -> int:
    """Remove all expired idempotency keys.

    Args:
        conn: Database connection.

    Returns:
        Number of keys deleted.
    """
    now = datetime.now(UTC)
    result = conn.execute(
        "DELETE FROM idempotency_keys WHERE expires_at < ? RETURNING key",
        [now],
    )
    rows = result.fetchall()
    return len(rows)
