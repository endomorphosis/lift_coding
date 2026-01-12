"""Persistence API for webhook events."""

import json
from typing import Any
from uuid import UUID, uuid4

import duckdb


def create_webhook_event(
    conn: duckdb.DuckDBPyConnection,
    source: str,
    signature_ok: bool,
    payload: dict[str, Any],
    event_type: str | None = None,
    delivery_id: str | None = None,
) -> UUID:
    """
    Store a webhook event.

    Args:
        conn: Database connection.
        source: Source of the webhook (e.g., "github").
        signature_ok: Whether the webhook signature was verified.
        payload: The webhook payload (will be stored as JSONB).
        event_type: Optional event type (e.g., "pull_request", "push").
        delivery_id: Optional delivery ID from webhook headers.

    Returns:
        The event ID.
    """
    event_id = uuid4()

    conn.execute(
        """
        INSERT INTO webhook_events (id, source, event_type, delivery_id, signature_ok, payload)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            str(event_id),
            source,
            event_type,
            delivery_id,
            signature_ok,
            json.dumps(payload),
        ],
    )

    return event_id


def get_webhook_events(
    conn: duckdb.DuckDBPyConnection,
    source: str | None = None,
    event_type: str | None = None,
    signature_ok: bool | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Query webhook events with optional filters.

    Args:
        conn: Database connection.
        source: Optional filter by source.
        event_type: Optional filter by event type.
        signature_ok: Optional filter by signature verification status.
        limit: Maximum number of results (default: 100).

    Returns:
        List of webhook events (most recent first).
    """
    query = """
        SELECT id, source, event_type, delivery_id, signature_ok, payload, received_at
        FROM webhook_events
        WHERE 1=1
    """
    params = []

    if source:
        query += " AND source = ?"
        params.append(source)

    if event_type:
        query += " AND event_type = ?"
        params.append(event_type)

    if signature_ok is not None:
        query += " AND signature_ok = ?"
        params.append(signature_ok)

    query += " ORDER BY received_at DESC LIMIT ?"
    params.append(limit)

    results = conn.execute(query, params).fetchall()

    return [
        {
            "id": row[0],
            "source": row[1],
            "event_type": row[2],
            "delivery_id": row[3],
            "signature_ok": row[4],
            "payload": json.loads(row[5]),
            "received_at": row[6],
        }
        for row in results
    ]
