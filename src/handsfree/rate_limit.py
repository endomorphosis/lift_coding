"""Rate limiting for side-effect actions.

Implements basic rate limiting to prevent abuse of side-effect endpoints.
Includes burst limiting and stricter defaults for side-effect actions.
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
    is_burst_limited: bool = False


# Stricter defaults for side-effect actions
SIDE_EFFECT_RATE_LIMITS = {
    "request_review": {
        "window_seconds": 60,
        "max_requests": 10,
        "burst_seconds": 10,
        "burst_max": 3,
    },
    "rerun": {"window_seconds": 60, "max_requests": 5, "burst_seconds": 10, "burst_max": 2},
    "merge": {"window_seconds": 60, "max_requests": 5, "burst_seconds": 10, "burst_max": 2},
    "comment": {"window_seconds": 60, "max_requests": 10, "burst_seconds": 10, "burst_max": 3},
}


def check_rate_limit(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_type: str,
    window_seconds: int = 60,
    max_requests: int = 10,
    burst_seconds: int | None = None,
    burst_max: int | None = None,
) -> RateLimitResult:
    """Check if a user has exceeded rate limits for an action type.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        action_type: Type of action being rate limited.
        window_seconds: Time window for rate limiting (default: 60 seconds).
        max_requests: Maximum requests allowed in the window (default: 10).
        burst_seconds: Optional burst window in seconds (e.g., 10s).
        burst_max: Optional max requests allowed in burst window.

    Returns:
        RateLimitResult indicating if the request is allowed.
    """
    # Calculate the start of the time window
    now = datetime.now(UTC)
    window_start = now - timedelta(seconds=window_seconds)

    # Check burst limit first if configured
    if burst_seconds is not None and burst_max is not None:
        burst_start = now - timedelta(seconds=burst_seconds)
        burst_result = conn.execute(
            """
            SELECT COUNT(*) 
            FROM action_logs
            WHERE user_id = ? 
              AND action_type = ?
              AND created_at >= ?
            """,
            [user_id, action_type, burst_start],
        ).fetchone()

        burst_count = burst_result[0] if burst_result else 0

        if burst_count >= burst_max:
            # Find the oldest action in burst window to calculate retry_after
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
                [user_id, action_type, burst_start],
            ).fetchone()

            if oldest_result:
                oldest_time = oldest_result[0]
                retry_after = int(
                    (oldest_time + timedelta(seconds=burst_seconds) - now).total_seconds()
                )
                retry_after = max(1, retry_after)  # At least 1 second
            else:
                retry_after = burst_seconds

            return RateLimitResult(
                allowed=False,
                reason=(
                    f"Burst limit exceeded: {burst_count}/{burst_max} requests "
                    f"in the last {burst_seconds}s"
                ),
                retry_after_seconds=retry_after,
                is_burst_limited=True,
            )

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


def check_side_effect_rate_limit(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_type: str,
) -> RateLimitResult:
    """Check rate limits for side-effect actions with stricter defaults.

    This is a convenience wrapper that applies consistent rate limiting
    for side-effect actions (request_review, rerun, merge, comment).

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        action_type: Type of side-effect action.

    Returns:
        RateLimitResult indicating if the request is allowed.
    """
    # Get default limits for this action type
    limits = SIDE_EFFECT_RATE_LIMITS.get(
        action_type,
        {"window_seconds": 60, "max_requests": 10, "burst_seconds": 10, "burst_max": 3},
    )

    return check_rate_limit(
        conn,
        user_id,
        action_type,
        window_seconds=limits["window_seconds"],
        max_requests=limits["max_requests"],
        burst_seconds=limits["burst_seconds"],
        burst_max=limits["burst_max"],
    )
