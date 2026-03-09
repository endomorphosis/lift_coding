"""Persistence helpers for transport session cursors."""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime

import duckdb

from handsfree.transport.libp2p_bluetooth import PersistedTransportSessionCursor


def load_transport_session_cursors(
    conn: duckdb.DuckDBPyConnection,
) -> dict[str, PersistedTransportSessionCursor]:
    """Load all persisted transport session cursors keyed by peer_id."""
    rows = conn.execute(
        """
        SELECT peer_id, peer_ref, session_id, resume_token, capabilities_json, updated_at
        FROM transport_session_cursors
        """
    ).fetchall()
    cursors: dict[str, PersistedTransportSessionCursor] = {}
    for row in rows:
        capabilities = ()
        try:
            decoded = json.loads(row[4]) if row[4] else []
            if isinstance(decoded, list) and all(isinstance(item, str) for item in decoded):
                capabilities = tuple(decoded)
        except json.JSONDecodeError:
            capabilities = ()
        cursors[row[0]] = PersistedTransportSessionCursor(
            peer_id=row[0],
            peer_ref=row[1],
            session_id=row[2],
            resume_token=row[3],
            capabilities=capabilities,
            updated_at_ms=int(row[5].timestamp() * 1000) if row[5] is not None else None,
        )
    return cursors


def store_transport_session_cursor(
    conn: duckdb.DuckDBPyConnection,
    cursor: PersistedTransportSessionCursor,
) -> None:
    """Insert or update a transport session cursor."""
    conn.execute(
        """
        INSERT INTO transport_session_cursors
        (peer_id, peer_ref, session_id, resume_token, capabilities_json, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(peer_id) DO UPDATE SET
          peer_ref = excluded.peer_ref,
          session_id = excluded.session_id,
          resume_token = excluded.resume_token,
          capabilities_json = excluded.capabilities_json,
          updated_at = excluded.updated_at
        """,
        [
            cursor.peer_id,
            cursor.peer_ref,
            cursor.session_id,
            cursor.resume_token,
            json.dumps(list(cursor.capabilities), separators=(",", ":"), sort_keys=True),
            datetime.fromtimestamp(
                (cursor.updated_at_ms if cursor.updated_at_ms is not None else int(datetime.now(UTC).timestamp() * 1000))
                / 1000,
                tz=UTC,
            ),
        ],
    )


def delete_transport_session_cursor(conn: duckdb.DuckDBPyConnection, peer_id: str) -> None:
    """Delete a persisted transport session cursor."""
    conn.execute("DELETE FROM transport_session_cursors WHERE peer_id = ?", [peer_id])


class DuckDBTransportSessionStore:
    """Transport session store backed by the main HandsFree DuckDB database."""

    def __init__(self, conn_factory: Callable[[], duckdb.DuckDBPyConnection]) -> None:
        self._conn_factory = conn_factory

    def load_all(self) -> dict[str, PersistedTransportSessionCursor]:
        conn = self._conn_factory()
        return load_transport_session_cursors(conn)

    def save(self, cursor: PersistedTransportSessionCursor) -> None:
        conn = self._conn_factory()
        store_transport_session_cursor(conn, cursor)

    def delete(self, peer_id: str) -> None:
        conn = self._conn_factory()
        delete_transport_session_cursor(conn, peer_id)
