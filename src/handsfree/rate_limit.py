"""Rate limiting for side-effect actions.

Implements basic rate limiting to prevent abuse of side-effect endpoints.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import duckdb


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    reason: str
    retry_after_seconds: int | None = None


def check_rate_limit(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_type: str,
    window_seconds: int = 60,
    max_requests: int = 10,
) -> RateLimitResult:
    """Check if a user has exceeded rate limits for an action type.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        action_type: Type of action being rate limited.
        window_seconds: Time window for rate limiting (default: 60 seconds).
        max_requests: Maximum requests allowed in the window (default: 10).

    Returns:
        RateLimitResult indicating if the request is allowed.
    """
    # Calculate the start of the time window
    now = datetime.now(UTC)
    window_start = now - timedelta(seconds=window_seconds)

    # Count actions in the current window
    result = conn.execute(
        """
        SELECT COUNT(*) 
        FROM action_logs
        WHERE user_id = ? 
          AND action_type = ?
          AND created_at >= ?
        """,
        [user_id, action_type, window_start],
    ).fetchone()

    count = result[0] if result else 0

    if count >= max_requests:
        # Find the oldest action in the window to calculate retry_after
        oldest_result = conn.execute(
            """
            SELECT created_at
            FROM action_logs
            WHERE user_id = ?
              AND action_type = ?
              AND created_at >= ?
            ORDER BY created_at ASC
            LIMIT 1
            """,
            [user_id, action_type, window_start],
        ).fetchone()

        if oldest_result:
            oldest_time = oldest_result[0]
            retry_after = int(
                (oldest_time + timedelta(seconds=window_seconds) - now).total_seconds()
            )
            retry_after = max(1, retry_after)  # At least 1 second
        else:
            retry_after = window_seconds

        return RateLimitResult(
            allowed=False,
            reason=(
                f"Rate limit exceeded: {count}/{max_requests} requests "
                f"in the last {window_seconds}s"
            ),
            retry_after_seconds=retry_after,
        )

    return RateLimitResult(
        allowed=True,
        reason=f"Rate limit ok: {count}/{max_requests} requests in the last {window_seconds}s",
    )
