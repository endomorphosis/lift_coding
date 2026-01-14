"""Webhook events persistence module.

Manages storage of incoming webhook events for replay and debugging.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


@dataclass
class WebhookEvent:
    """Represents a stored webhook event."""

    id: str
    source: str
    event_type: str | None
    delivery_id: str | None
    signature_ok: bool
    payload: dict[str, Any] | None
    received_at: datetime


def store_webhook_event(
    conn: duckdb.DuckDBPyConnection,
    source: str,
    signature_ok: bool,
    event_type: str | None = None,
    delivery_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> WebhookEvent:
    """Store a webhook event.

    Args:
        conn: Database connection.
        source: Source of the webhook (e.g., "github").
        signature_ok: Whether the webhook signature was valid.
        event_type: Type of event (e.g., "push", "pull_request").
        delivery_id: Unique delivery ID from the webhook provider.
        payload: Full webhook payload (JSON-serializable).

    Returns:
        Created WebhookEvent object.
    """
    event_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    conn.execute(
        """
        INSERT INTO webhook_events
        (id, source, event_type, delivery_id, signature_ok, payload, received_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [event_id, source, event_type, delivery_id, signature_ok, payload, now],
    )

    return WebhookEvent(
        id=event_id,
        source=source,
        event_type=event_type,
        delivery_id=delivery_id,
        signature_ok=signature_ok,
        payload=payload,
        received_at=now,
    )


def get_webhook_events(
    conn: duckdb.DuckDBPyConnection,
    source: str | None = None,
    event_type: str | None = None,
    signature_ok: bool | None = None,
    limit: int = 100,
) -> list[WebhookEvent]:
    """Query webhook events with optional filters.

    Args:
        conn: Database connection.
        source: Filter by source (e.g., "github").
        event_type: Filter by event type.
        signature_ok: Filter by signature validity.
        limit: Maximum number of events to return.

    Returns:
        List of WebhookEvent objects, ordered by received_at DESC.
    """
    query = (
        "SELECT id, source, event_type, delivery_id, signature_ok, payload, "
        "received_at FROM webhook_events WHERE 1=1"
    )
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
        WebhookEvent(
            id=str(row[0]),
            source=row[1],
            event_type=row[2],
            delivery_id=row[3],
            signature_ok=row[4],
            payload=json.loads(row[5]) if isinstance(row[5], str) and row[5] else row[5],
            received_at=row[6],
        )
        for row in results
    ]


def get_webhook_event_by_id(
    conn: duckdb.DuckDBPyConnection,
    event_id: str,
) -> WebhookEvent | None:
    """Get a specific webhook event by ID.

    Args:
        conn: Database connection.
        event_id: The event ID.

    Returns:
        WebhookEvent if found, None otherwise.
    """
    result = conn.execute(
        """
        SELECT id, source, event_type, delivery_id, signature_ok, payload, received_at
        FROM webhook_events
        WHERE id = ?
        """,
        [event_id],
    ).fetchone()

    if not result:
        return None

    return WebhookEvent(
        id=str(result[0]),
        source=result[1],
        event_type=result[2],
        delivery_id=result[3],
        signature_ok=result[4],
        payload=json.loads(result[5]) if isinstance(result[5], str) and result[5] else result[5],
        received_at=result[6],
    )


class DBWebhookStore:
    """Database-backed webhook store with replay protection.

    This store uses DuckDB for persistence and provides replay protection
    by checking for duplicate delivery IDs in the database.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection):
        """Initialize the DB webhook store.

        Args:
            conn: Database connection.
        """
        self.conn = conn

    def is_duplicate_delivery(self, delivery_id: str) -> bool:
        """Check if delivery ID has been processed before.

        Args:
            delivery_id: GitHub delivery ID to check.

        Returns:
            True if the delivery ID exists in the database, False otherwise.
        """
        result = self.conn.execute(
            "SELECT COUNT(*) FROM webhook_events WHERE delivery_id = ?",
            [delivery_id],
        ).fetchone()
        return result[0] > 0 if result else False

    def store_event(
        self,
        delivery_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature_ok: bool,
    ) -> str:
        """Store webhook event and return event ID.

        Args:
            delivery_id: GitHub delivery ID.
            event_type: GitHub event type.
            payload: Full webhook payload.
            signature_ok: Whether signature verification passed.

        Returns:
            Event ID (UUID string).
        """
        event = store_webhook_event(
            self.conn,
            source="github",
            signature_ok=signature_ok,
            event_type=event_type,
            delivery_id=delivery_id,
            payload=payload,
        )
        return event.id

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Retrieve stored event by ID.

        Args:
            event_id: The event ID.

        Returns:
            Event dict or None if not found.
        """
        event = get_webhook_event_by_id(self.conn, event_id)
        if not event:
            return None

        return {
            "id": event.id,
            "source": event.source,
            "event_type": event.event_type,
            "delivery_id": event.delivery_id,
            "signature_ok": event.signature_ok,
            "payload": event.payload,
            "received_at": event.received_at,
        }

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """List recent events.

        Args:
            limit: Maximum number of events to return.

        Returns:
            List of event dicts, ordered by received_at DESC.
        """
        events = get_webhook_events(self.conn, limit=limit)
        return [
            {
                "id": event.id,
                "source": event.source,
                "event_type": event.event_type,
                "delivery_id": event.delivery_id,
                "signature_ok": event.signature_ok,
                "payload": event.payload,
                "received_at": event.received_at,
            }
            for event in events
        ]


def get_db_webhook_store() -> DBWebhookStore:
    """Get a DB-backed webhook store instance.

    This function provides a singleton-like access to the webhook store
    that uses the database for persistence.

    Returns:
        DBWebhookStore instance connected to the database.
    """
    from handsfree.db import init_db

    conn = init_db()
    return DBWebhookStore(conn)
