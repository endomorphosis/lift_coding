"""Commands persistence module.

Manages command history with privacy toggle for transcript storage.
"""

import json
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import duckdb


@dataclass
class Command:
    """Represents a stored command with parsed intent."""

    id: str
    user_id: str
    profile: str
    input_type: str
    transcript: str | None
    intent_name: str | None
    intent_confidence: float | None
    entities: dict[str, Any] | None
    status: str
    created_at: datetime


def store_command(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    input_type: str,
    status: str,
    profile: str = "default",
    transcript: str | None = None,
    intent_name: str | None = None,
    intent_confidence: float | None = None,
    entities: dict[str, Any] | None = None,
    store_transcript: bool = False,
) -> Command:
    """Store a command in the database.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        input_type: Type of input ("text" or "audio").
        status: Command status ("ok", "needs_confirmation", "error").
        profile: User profile name (default: "default").
        transcript: Command transcript (only stored if store_transcript=True).
        intent_name: Parsed intent name.
        intent_confidence: Confidence score for the intent (0.0-1.0).
        entities: Extracted entities as JSON.
        store_transcript: Whether to store the transcript (privacy toggle).

    Returns:
        Created Command object.
    """
    command_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    # Only store transcript if explicitly allowed
    stored_transcript = transcript if store_transcript else None

    conn.execute(
        """
        INSERT INTO commands
        (id, user_id, profile, input_type, transcript, intent_name, 
         intent_confidence, entities, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            command_id,
            user_id,
            profile,
            input_type,
            stored_transcript,
            intent_name,
            intent_confidence,
            entities,
            status,
            now,
        ],
    )

    return Command(
        id=command_id,
        user_id=user_id,
        profile=profile,
        input_type=input_type,
        transcript=stored_transcript,
        intent_name=intent_name,
        intent_confidence=intent_confidence,
        entities=entities,
        status=status,
        created_at=now,
    )


def get_commands(
    conn: duckdb.DuckDBPyConnection,
    user_id: str | None = None,
    profile: str | None = None,
    status: str | None = None,
    limit: int = 100,
) -> list[Command]:
    """Query commands with optional filters.

    Args:
        conn: Database connection.
        user_id: Filter by user ID.
        profile: Filter by profile name.
        status: Filter by status.
        limit: Maximum number of commands to return.

    Returns:
        List of Command objects, ordered by created_at DESC.
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
        params.append(user_id)

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
        Command(
            id=str(row[0]),
            user_id=str(row[1]),
            profile=row[2],
            input_type=row[3],
            transcript=row[4],
            intent_name=row[5],
            intent_confidence=row[6],
            entities=json.loads(row[7]) if isinstance(row[7], str) and row[7] else row[7],
            status=row[8],
            created_at=row[9],
        )
        for row in results
    ]


def get_command_by_id(
    conn: duckdb.DuckDBPyConnection,
    command_id: str,
) -> Command | None:
    """Get a specific command by ID.

    Args:
        conn: Database connection.
        command_id: The command ID.

    Returns:
        Command if found, None otherwise.
    """
    result = conn.execute(
        """
        SELECT id, user_id, profile, input_type, transcript, intent_name,
               intent_confidence, entities, status, created_at
        FROM commands
        WHERE id = ?
        """,
        [command_id],
    ).fetchone()

    if not result:
        return None

    return Command(
        id=str(result[0]),
        user_id=str(result[1]),
        profile=result[2],
        input_type=result[3],
        transcript=result[4],
        intent_name=result[5],
        intent_confidence=result[6],
        entities=json.loads(result[7]) if isinstance(result[7], str) and result[7] else result[7],
        status=result[8],
        created_at=result[9],
    )
