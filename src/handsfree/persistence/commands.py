"""Persistence API for commands (with privacy toggle for transcript)."""

import json
from typing import Any
from uuid import UUID, uuid4

import duckdb


def create_command(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID,
    input_type: str,
    status: str,
    profile: str = "default",
    transcript: str | None = None,
    store_transcript: bool = False,
    intent_name: str | None = None,
    intent_confidence: float | None = None,
    entities: dict[str, Any] | None = None,
) -> UUID:
    """
    Store a command (user input + parsed intent).

    Args:
        conn: Database connection.
        user_id: User ID who issued the command.
        input_type: Type of input (e.g., "text", "audio").
        status: Command status (e.g., "ok", "needs_confirmation", "error").
        profile: User profile/mode (default: "default").
        transcript: The transcript of the command.
        store_transcript: Whether to store the transcript (privacy toggle). Default: False.
        intent_name: Recognized intent name.
        intent_confidence: Intent confidence score (0-1).
        entities: Extracted entities (stored as JSONB).

    Returns:
        The command ID.
    """
    command_id = uuid4()

    # Respect privacy toggle: only store transcript if explicitly allowed
    transcript_to_store = transcript if store_transcript else None

    conn.execute(
        """
        INSERT INTO commands
            (id, user_id, profile, input_type, transcript, intent_name,
             intent_confidence, entities, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            str(command_id),
            str(user_id),
            profile,
            input_type,
            transcript_to_store,
            intent_name,
            intent_confidence,
            json.dumps(entities) if entities else None,
            status,
        ],
    )

    return command_id


def get_commands(
    conn: duckdb.DuckDBPyConnection,
    user_id: UUID | None = None,
    profile: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """
    Query commands with optional filters.

    Args:
        conn: Database connection.
        user_id: Optional filter by user ID.
        profile: Optional filter by profile.
        status: Optional filter by status.
        limit: Maximum number of results (default: 100).

    Returns:
        List of commands (most recent first).
    """
    query = """
        SELECT id, user_id, profile, input_type, transcript, intent_name,
               intent_confidence, entities, status, created_at
        FROM commands
        WHERE 1=1
    """
    params = []

    if user_id:
        query += " AND user_id = ?"
        params.append(str(user_id))

    if profile:
        query += " AND profile = ?"
        params.append(profile)

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    results = conn.execute(query, params).fetchall()

    return [
        {
            "id": row[0],
            "user_id": row[1],
            "profile": row[2],
            "input_type": row[3],
            "transcript": row[4],  # May be None if privacy toggle was off
            "intent_name": row[5],
            "intent_confidence": row[6],
            "entities": json.loads(row[7]) if row[7] else None,
            "status": row[8],
            "created_at": row[9],
        }
        for row in results
    ]
