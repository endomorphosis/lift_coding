"""API keys persistence module.

Manages API key storage and validation for API key authentication mode.
Keys are always stored as secure hashes, never in plaintext.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import duckdb


@dataclass
class ApiKey:
    """Represents an API key record."""

    id: str
    user_id: str
    key_hash: str
    label: str | None
    created_at: datetime
    revoked_at: datetime | None
    last_used_at: datetime | None


def generate_api_key() -> str:
    """Generate a cryptographically secure API key.

    Returns:
        A URL-safe base64-encoded random string (43 characters).
    """
    # Generate 32 random bytes and encode as URL-safe base64
    # This produces a 43-character string
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key using SHA256.

    Args:
        api_key: The plaintext API key.

    Returns:
        Hexadecimal hash of the API key.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()


def create_api_key(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    label: str | None = None,
) -> tuple[str, ApiKey]:
    """Create a new API key for a user.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        label: Optional user-friendly label for the key.

    Returns:
        Tuple of (plaintext_key, ApiKey record).
        The plaintext key is only returned once and never stored.
    """
    key_id = str(uuid.uuid4())
    plaintext_key = generate_api_key()
    key_hash = hash_api_key(plaintext_key)
    now = datetime.now(UTC)

    conn.execute(
        """
        INSERT INTO api_keys
        (id, user_id, key_hash, label, created_at, revoked_at, last_used_at)
        VALUES (?, ?, ?, ?, ?, NULL, NULL)
        """,
        [key_id, user_id, key_hash, label, now],
    )

    api_key_record = ApiKey(
        id=key_id,
        user_id=user_id,
        key_hash=key_hash,
        label=label,
        created_at=now,
        revoked_at=None,
        last_used_at=None,
    )

    return plaintext_key, api_key_record


def validate_api_key(
    conn: duckdb.DuckDBPyConnection,
    api_key: str,
) -> str | None:
    """Validate an API key and return the associated user_id.

    Args:
        conn: Database connection.
        api_key: The plaintext API key to validate.

    Returns:
        User ID if the key is valid and not revoked, None otherwise.
    """
    key_hash = hash_api_key(api_key)

    result = conn.execute(
        """
        SELECT id, user_id
        FROM api_keys
        WHERE key_hash = ? AND revoked_at IS NULL
        """,
        [key_hash],
    ).fetchone()

    if result is None:
        return None

    key_id, user_id = result

    # Update last_used_at timestamp
    now = datetime.now(UTC)
    conn.execute(
        """
        UPDATE api_keys
        SET last_used_at = ?
        WHERE id = ?
        """,
        [now, key_id],
    )

    return str(user_id)


def get_api_key(
    conn: duckdb.DuckDBPyConnection,
    key_id: str,
) -> ApiKey | None:
    """Get an API key by ID.

    Args:
        conn: Database connection.
        key_id: UUID of the API key.

    Returns:
        ApiKey object or None if not found.
    """
    result = conn.execute(
        """
        SELECT id, user_id, key_hash, label, created_at, revoked_at, last_used_at
        FROM api_keys
        WHERE id = ?
        """,
        [key_id],
    ).fetchone()

    if result is None:
        return None

    return ApiKey(
        id=str(result[0]),
        user_id=str(result[1]),
        key_hash=result[2],
        label=result[3],
        created_at=result[4],
        revoked_at=result[5],
        last_used_at=result[6],
    )


def get_api_keys_by_user(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    include_revoked: bool = False,
) -> list[ApiKey]:
    """Get all API keys for a user.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        include_revoked: Whether to include revoked keys (default: False).

    Returns:
        List of ApiKey objects, ordered by creation date (newest first).
    """
    if include_revoked:
        query = """
            SELECT id, user_id, key_hash, label, created_at, revoked_at, last_used_at
            FROM api_keys
            WHERE user_id = ?
            ORDER BY created_at DESC
        """
    else:
        query = """
            SELECT id, user_id, key_hash, label, created_at, revoked_at, last_used_at
            FROM api_keys
            WHERE user_id = ? AND revoked_at IS NULL
            ORDER BY created_at DESC
        """

    results = conn.execute(query, [user_id]).fetchall()

    return [
        ApiKey(
            id=str(row[0]),
            user_id=str(row[1]),
            key_hash=row[2],
            label=row[3],
            created_at=row[4],
            revoked_at=row[5],
            last_used_at=row[6],
        )
        for row in results
    ]


def revoke_api_key(
    conn: duckdb.DuckDBPyConnection,
    key_id: str,
) -> ApiKey | None:
    """Revoke an API key.

    Args:
        conn: Database connection.
        key_id: UUID of the API key.

    Returns:
        Updated ApiKey object or None if not found.
    """
    now = datetime.now(UTC)

    # Check if key exists and is not already revoked
    existing = get_api_key(conn, key_id)
    if existing is None:
        return None

    conn.execute(
        """
        UPDATE api_keys
        SET revoked_at = ?
        WHERE id = ?
        """,
        [now, key_id],
    )

    return get_api_key(conn, key_id)


def delete_api_key(
    conn: duckdb.DuckDBPyConnection,
    key_id: str,
) -> bool:
    """Permanently delete an API key from the database.

    Note: In production, prefer revoking keys over deleting them
    to maintain audit trail.

    Args:
        conn: Database connection.
        key_id: UUID of the API key.

    Returns:
        True if deleted, False if not found.
    """
    existing = get_api_key(conn, key_id)
    if existing is None:
        return False

    conn.execute(
        """
        DELETE FROM api_keys
        WHERE id = ?
        """,
        [key_id],
    )

    return True
