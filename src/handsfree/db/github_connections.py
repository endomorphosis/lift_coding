"""GitHub connections persistence module.

Manages GitHub connection metadata (installation_id, token_ref, scopes).
Does NOT store actual tokens - only references to secret manager.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb


@dataclass
class GitHubConnection:
    """Represents a GitHub connection/installation."""

    id: str
    user_id: str
    installation_id: int | None
    token_ref: str | None
    scopes: str | None
    created_at: datetime
    updated_at: datetime


def create_github_connection(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    installation_id: int | None = None,
    token_ref: str | None = None,
    scopes: str | None = None,
) -> GitHubConnection:
    """Create a GitHub connection entry.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        installation_id: GitHub App installation ID.
        token_ref: Reference to token in secret manager (NOT the actual token).
        scopes: OAuth scopes as a comma-separated string.

    Returns:
        Created GitHubConnection object.
    """
    connection_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    conn.execute(
        """
        INSERT INTO github_connections
        (id, user_id, installation_id, token_ref, scopes, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [connection_id, user_id, installation_id, token_ref, scopes, now, now],
    )

    return GitHubConnection(
        id=connection_id,
        user_id=user_id,
        installation_id=installation_id,
        token_ref=token_ref,
        scopes=scopes,
        created_at=now,
        updated_at=now,
    )


def get_github_connection(
    conn: duckdb.DuckDBPyConnection,
    connection_id: str,
) -> GitHubConnection | None:
    """Get a GitHub connection by ID.

    Args:
        conn: Database connection.
        connection_id: UUID of the connection.

    Returns:
        GitHubConnection object or None if not found.
    """
    result = conn.execute(
        """
        SELECT id, user_id, installation_id, token_ref, scopes, created_at, updated_at
        FROM github_connections
        WHERE id = ?
        """,
        [connection_id],
    ).fetchone()

    if result is None:
        return None

    return GitHubConnection(
        id=str(result[0]),
        user_id=str(result[1]),
        installation_id=result[2],
        token_ref=result[3],
        scopes=result[4],
        created_at=result[5],
        updated_at=result[6],
    )


def get_github_connections_by_user(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
) -> list[GitHubConnection]:
    """Get all GitHub connections for a user.

    Args:
        conn: Database connection.
        user_id: UUID of the user.

    Returns:
        List of GitHubConnection objects.
    """
    results = conn.execute(
        """
        SELECT id, user_id, installation_id, token_ref, scopes, created_at, updated_at
        FROM github_connections
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        [user_id],
    ).fetchall()

    return [
        GitHubConnection(
            id=str(row[0]),
            user_id=str(row[1]),
            installation_id=row[2],
            token_ref=row[3],
            scopes=row[4],
            created_at=row[5],
            updated_at=row[6],
        )
        for row in results
    ]


def update_github_connection(
    conn: duckdb.DuckDBPyConnection,
    connection_id: str,
    installation_id: int | None = None,
    token_ref: str | None = None,
    scopes: str | None = None,
) -> GitHubConnection | None:
    """Update a GitHub connection.

    Args:
        conn: Database connection.
        connection_id: UUID of the connection.
        installation_id: New installation ID (optional).
        token_ref: New token reference (optional).
        scopes: New scopes (optional).

    Returns:
        Updated GitHubConnection object or None if not found.
    """
    now = datetime.now(UTC)

    # Build update query dynamically based on provided parameters
    updates = []
    params = []

    if installation_id is not None:
        updates.append("installation_id = ?")
        params.append(installation_id)

    if token_ref is not None:
        updates.append("token_ref = ?")
        params.append(token_ref)

    if scopes is not None:
        updates.append("scopes = ?")
        params.append(scopes)

    # Always update updated_at
    updates.append("updated_at = ?")
    params.append(now)

    if not updates:
        # Nothing to update
        return get_github_connection(conn, connection_id)

    params.append(connection_id)

    conn.execute(
        f"""
        UPDATE github_connections
        SET {", ".join(updates)}
        WHERE id = ?
        """,
        params,
    )

    return get_github_connection(conn, connection_id)


def delete_github_connection(
    conn: duckdb.DuckDBPyConnection,
    connection_id: str,
) -> bool:
    """Delete a GitHub connection.

    Args:
        conn: Database connection.
        connection_id: UUID of the connection.

    Returns:
        True if deleted, False if not found.
    """
    # First check if the connection exists
    existing = get_github_connection(conn, connection_id)
    if existing is None:
        return False

    conn.execute(
        """
        DELETE FROM github_connections
        WHERE id = ?
        """,
        [connection_id],
    )

    return True


def get_installation_for_repo(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    repo_full_name: str,
) -> int | None:
    """Get the best installation_id for a given repository and user.

    This function helps with multi-installation support by finding the appropriate
    installation_id to use when making API calls for a specific repository.

    Selection order:
    1. Check repo_subscriptions for explicit repo->installation mapping
    2. Fall back to user's most recent github_connection with installation_id

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        repo_full_name: Full repository name (e.g., "owner/repo").

    Returns:
        Installation ID for the repo, or None if not found.
    """
    # First try to find an explicit mapping in repo_subscriptions
    result = conn.execute(
        """
        SELECT installation_id
        FROM repo_subscriptions
        WHERE user_id = ? AND repo_full_name = ? AND installation_id IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        [user_id, repo_full_name],
    ).fetchone()

    if result and result[0] is not None:
        return result[0]

    # Fall back to user's most recent github_connection with installation_id
    connections = get_github_connections_by_user(conn, user_id)
    for connection in connections:
        if connection.installation_id is not None:
            return connection.installation_id

    return None
