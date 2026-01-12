"""Webhook events persistence layer using DuckDB."""

import json
import logging
import uuid
from typing import Any

from handsfree.db import get_connection

logger = logging.getLogger(__name__)


class DBWebhookStore:
    """Database-backed webhook event store with replay protection."""

    def is_duplicate_delivery(self, delivery_id: str) -> bool:
        """Check if delivery ID has been processed before.

        Args:
            delivery_id: GitHub delivery ID

        Returns:
            True if delivery ID exists in database, False otherwise
        """
        with get_connection() as conn:
            result = conn.execute(
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
        """Store webhook event in the database.

        Args:
            delivery_id: GitHub delivery ID
            event_type: GitHub event type
            payload: Raw webhook payload
            signature_ok: Whether signature verification passed

        Returns:
            Event ID (UUID)
        """
        event_id = str(uuid.uuid4())

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO webhook_events 
                (id, source, event_type, delivery_id, signature_ok, payload, received_at)
                VALUES (?, ?, ?, ?, ?, ?, now())
                """,
                [
                    event_id,
                    "github",
                    event_type,
                    delivery_id,
                    signature_ok,
                    json.dumps(payload),
                ],
            )

        logger.info(
            "Stored webhook event: id=%s, type=%s, delivery_id=%s",
            event_id,
            event_type,
            delivery_id,
        )
        return event_id

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        """Retrieve stored event by ID.

        Args:
            event_id: Event UUID

        Returns:
            Event dict or None if not found
        """
        with get_connection() as conn:
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

            return {
                "id": result[0],
                "source": result[1],
                "event_type": result[2],
                "delivery_id": result[3],
                "signature_ok": result[4],
                "payload": json.loads(result[5]) if result[5] else None,
                "received_at": result[6],
            }

    def list_events(self, limit: int = 100) -> list[dict[str, Any]]:
        """List recent events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of event dicts
        """
        with get_connection() as conn:
            results = conn.execute(
                """
                SELECT id, source, event_type, delivery_id, signature_ok, payload, received_at
                FROM webhook_events
                ORDER BY received_at DESC
                LIMIT ?
                """,
                [limit],
            ).fetchall()

            return [
                {
                    "id": row[0],
                    "source": row[1],
                    "event_type": row[2],
                    "delivery_id": row[3],
                    "signature_ok": row[4],
                    "payload": json.loads(row[5]) if row[5] else None,
                    "received_at": row[6],
                }
                for row in results
            ]


# Global store instance
_db_webhook_store = DBWebhookStore()


def get_db_webhook_store() -> DBWebhookStore:
    """Get the global DB webhook store instance."""
    return _db_webhook_store
