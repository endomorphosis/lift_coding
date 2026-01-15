"""Repository subscriptions persistence module.

Manages mappings between repositories and users for webhook notification routing.
"""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb


@dataclass
class RepoSubscription:
    """Represents a user's subscription to a repository for notifications."""

    id: str
    user_id: str
    repo_full_name: str
    installation_id: int | None
    created_at: datetime


def create_repo_subscription(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    repo_full_name: str,
    installation_id: int | None = None,
) -> RepoSubscription:
    """Create a repo subscription entry.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        repo_full_name: Full repository name (e.g., "owner/repo").
        installation_id: GitHub App installation ID (optional).

    Returns:
        Created RepoSubscription object.
    """
    subscription_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    conn.execute(
        """
        INSERT INTO repo_subscriptions
        (id, user_id, repo_full_name, installation_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        [subscription_id, user_id, repo_full_name, installation_id, now],
    )

    return RepoSubscription(
        id=subscription_id,
        user_id=user_id,
        repo_full_name=repo_full_name,
        installation_id=installation_id,
        created_at=now,
    )


def list_repo_subscriptions(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
) -> list[RepoSubscription]:
    """List all repo subscriptions for a user.

    Args:
        conn: Database connection.
        user_id: UUID of the user.

    Returns:
        List of RepoSubscription objects, ordered by created_at DESC.
    """
    results = conn.execute(
        """
        SELECT id, user_id, repo_full_name, installation_id, created_at
        FROM repo_subscriptions
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        [user_id],
    ).fetchall()

    return [
        RepoSubscription(
            id=str(row[0]),
            user_id=str(row[1]),
            repo_full_name=str(row[2]),
            installation_id=row[3],
            created_at=row[4],
        )
        for row in results
    ]


def get_users_for_repo(
    conn: duckdb.DuckDBPyConnection,
    repo_full_name: str,
) -> list[str]:
    """Get all user IDs subscribed to a repository.

    Args:
        conn: Database connection.
        repo_full_name: Full repository name (e.g., "owner/repo").

    Returns:
        List of user IDs (as strings).
    """
    results = conn.execute(
        """
        SELECT DISTINCT user_id
        FROM repo_subscriptions
        WHERE repo_full_name = ?
        """,
        [repo_full_name],
    ).fetchall()

    return [str(row[0]) for row in results]


def get_users_for_installation(
    conn: duckdb.DuckDBPyConnection,
    installation_id: int,
) -> list[str]:
    """Get all user IDs associated with a GitHub installation.

    This checks both repo_subscriptions and github_connections tables.

    Args:
        conn: Database connection.
        installation_id: GitHub App installation ID.

    Returns:
        List of user IDs (as strings).
    """
    # First, try to get users directly from repo_subscriptions
    results = conn.execute(
        """
        SELECT DISTINCT user_id
        FROM repo_subscriptions
        WHERE installation_id = ?
        """,
        [installation_id],
    ).fetchall()

    if results:
        return [str(row[0]) for row in results]

    # Fallback: check github_connections table
    results = conn.execute(
        """
        SELECT DISTINCT user_id
        FROM github_connections
        WHERE installation_id = ?
        """,
        [installation_id],
    ).fetchall()

    return [str(row[0]) for row in results]


def delete_repo_subscription(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    repo_full_name: str,
) -> bool:
    """Delete a repo subscription.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        repo_full_name: Full repository name.

    Returns:
        True if deleted, False if not found.
    """
    result = conn.execute(
        """
        DELETE FROM repo_subscriptions
        WHERE user_id = ? AND repo_full_name = ?
        RETURNING id
        """,
        [user_id, repo_full_name],
    ).fetchone()

    return result is not None
