"""OAuth state persistence module.

Manages OAuth state tokens for CSRF protection during OAuth flows.
States are short-lived (10 min TTL) and consumed on first use.
"""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import duckdb


@dataclass
class OAuthState:
    """Represents an OAuth state token."""

    state: str
    user_id: str
    scopes: str | None
    created_at: datetime
    expires_at: datetime
    consumed_at: datetime | None


def generate_oauth_state(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    scopes: str | None = None,
    ttl_minutes: int = 10,
) -> str:
    """Generate and store a new OAuth state token.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        scopes: OAuth scopes as a comma-separated string.
        ttl_minutes: Time-to-live for the state token in minutes (default: 10).

    Returns:
        Generated state token (random secure string).
    """
    # Generate a cryptographically secure random token
    state = secrets.token_urlsafe(32)
    
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=ttl_minutes)

    conn.execute(
        """
        INSERT INTO oauth_states (state, user_id, scopes, created_at, expires_at, consumed_at)
        VALUES (?, ?, ?, ?, ?, NULL)
        """,
        [state, user_id, scopes, now, expires_at],
    )

    return state


def validate_and_consume_oauth_state(
    conn: duckdb.DuckDBPyConnection,
    state: str,
    user_id: str,
) -> OAuthState | None:
    """Validate and consume an OAuth state token.

    This function:
    1. Checks if the state exists
    2. Verifies it belongs to the correct user
    3. Checks it hasn't expired
    4. Checks it hasn't been consumed already
    5. Marks it as consumed (one-time use)

    Args:
        conn: Database connection.
        state: State token to validate.
        user_id: Expected user ID for the state.

    Returns:
        OAuthState object if valid, None if invalid/expired/consumed.
    """
    now = datetime.now(UTC)

    # Fetch the state record
    result = conn.execute(
        """
        SELECT state, user_id, scopes, created_at, expires_at, consumed_at
        FROM oauth_states
        WHERE state = ?
        """,
        [state],
    ).fetchone()

    if not result:
        return None

    oauth_state = OAuthState(
        state=result[0],
        user_id=str(result[1]),  # Convert UUID to string for consistency
        scopes=result[2],
        created_at=result[3],
        expires_at=result[4],
        consumed_at=result[5],
    )

    # Validate the state
    if oauth_state.user_id != user_id:
        return None

    if oauth_state.expires_at < now:
        return None

    if oauth_state.consumed_at is not None:
        return None

    # Mark as consumed (one-time use)
    conn.execute(
        """
        UPDATE oauth_states
        SET consumed_at = ?
        WHERE state = ?
        """,
        [now, state],
    )

    return oauth_state


def cleanup_expired_oauth_states(
    conn: duckdb.DuckDBPyConnection,
    older_than_hours: int = 24,
) -> int:
    """Clean up expired or old OAuth states.

    Args:
        conn: Database connection.
        older_than_hours: Delete states older than this many hours (default: 24).

    Returns:
        Number of states deleted.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=older_than_hours)

    result = conn.execute(
        """
        DELETE FROM oauth_states
        WHERE created_at < ? OR expires_at < ?
        """,
        [cutoff, datetime.now(UTC)],
    )

    return result.fetchone()[0] if result else 0
