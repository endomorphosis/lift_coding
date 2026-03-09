"""Peer chat persistence helpers."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb


@dataclass
class StoredPeerChatMessage:
    """Represents a persisted peer chat message."""

    id: str
    conversation_id: str
    peer_id: str
    sender_peer_id: str
    text: str
    priority: str
    timestamp_ms: int
    created_at: datetime


@dataclass
class StoredPeerChatConversation:
    """Represents a summarized peer chat conversation."""

    conversation_id: str
    peer_id: str
    sender_peer_id: str
    last_text: str
    priority: str
    last_timestamp_ms: int
    message_count: int


def store_peer_chat_message(
    conn: duckdb.DuckDBPyConnection,
    conversation_id: str,
    peer_id: str,
    sender_peer_id: str,
    text: str,
    priority: str,
    timestamp_ms: int,
) -> StoredPeerChatMessage:
    """Persist a peer chat message."""
    message_id = str(uuid.uuid4())
    created_at = datetime.now(UTC)
    conn.execute(
        """
        INSERT INTO peer_chat_messages
        (id, conversation_id, peer_id, sender_peer_id, text, priority, timestamp_ms, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [message_id, conversation_id, peer_id, sender_peer_id, text, priority, timestamp_ms, created_at],
    )
    return StoredPeerChatMessage(
        id=message_id,
        conversation_id=conversation_id,
        peer_id=peer_id,
        sender_peer_id=sender_peer_id,
        text=text,
        priority=priority,
        timestamp_ms=timestamp_ms,
        created_at=created_at,
    )


def list_peer_chat_messages(
    conn: duckdb.DuckDBPyConnection,
    conversation_id: str,
) -> list[StoredPeerChatMessage]:
    """List peer chat messages for a conversation ordered by timestamp."""
    rows = conn.execute(
        """
        SELECT id, conversation_id, peer_id, sender_peer_id, text, priority, timestamp_ms, created_at
        FROM peer_chat_messages
        WHERE conversation_id = ?
        ORDER BY timestamp_ms ASC, created_at ASC
        """,
        [conversation_id],
    ).fetchall()
    return [
        StoredPeerChatMessage(
            id=str(row[0]),
            conversation_id=row[1],
            peer_id=row[2],
            sender_peer_id=row[3],
            text=row[4],
            priority=row[5],
            timestamp_ms=int(row[6]),
            created_at=row[7],
        )
        for row in rows
    ]


def list_recent_peer_chat_conversations(
    conn: duckdb.DuckDBPyConnection,
    limit: int = 20,
) -> list[StoredPeerChatConversation]:
    """List recent peer chat conversations ordered by last message timestamp."""
    rows = conn.execute(
        """
        WITH ranked AS (
          SELECT
            conversation_id,
            peer_id,
            sender_peer_id,
            text,
            priority,
            timestamp_ms,
            ROW_NUMBER() OVER (
              PARTITION BY conversation_id
              ORDER BY timestamp_ms DESC, created_at DESC
            ) AS row_num,
            COUNT(*) OVER (PARTITION BY conversation_id) AS message_count
          FROM peer_chat_messages
        )
        SELECT
          conversation_id,
          peer_id,
          sender_peer_id,
          text,
          priority,
          timestamp_ms,
          message_count
        FROM ranked
        WHERE row_num = 1
        ORDER BY timestamp_ms DESC
        LIMIT ?
        """,
        [limit],
    ).fetchall()
    return [
        StoredPeerChatConversation(
            conversation_id=row[0],
            peer_id=row[1],
            sender_peer_id=row[2],
            last_text=row[3],
            priority=row[4],
            last_timestamp_ms=int(row[5]),
            message_count=int(row[6]),
        )
        for row in rows
    ]
