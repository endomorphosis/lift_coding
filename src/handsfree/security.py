"""Security monitoring and anomaly detection.

Tracks suspicious activity patterns and logs security events.
"""

import logging
from datetime import UTC, datetime, timedelta

import duckdb

from handsfree.db.action_logs import write_action_log
from handsfree.logging_utils import log_warning, redact_secrets

logger = logging.getLogger(__name__)


# Thresholds for anomaly detection
ANOMALY_DETECTION_WINDOW_SECONDS = 300  # 5 minutes
ANOMALY_THRESHOLD_DENIALS = 5  # Repeated denials within window


def check_and_log_anomaly(
    conn: duckdb.DuckDBPyConnection,
    user_id: str,
    action_type: str,
    denial_type: str,
    target: str | None = None,
    request_data: dict | None = None,
) -> bool:
    """Check for anomalous activity patterns and log if detected.

    Tracks repeated rate limit violations or policy denials within a time window.
    If anomalous behavior is detected, logs a security.anomaly audit entry.

    Args:
        conn: Database connection.
        user_id: UUID of the user.
        action_type: Type of action that was denied (e.g., "request_review").
        denial_type: Type of denial ("rate_limited" or "policy_denied").
        target: Optional target of the action (e.g., "owner/repo#123").
        request_data: Optional request data for context.

    Returns:
        True if anomalous behavior was detected and logged, False otherwise.
    """
    # Look for recent denials in the anomaly detection window
    now = datetime.now(UTC)
    window_start = now - timedelta(seconds=ANOMALY_DETECTION_WINDOW_SECONDS)

    # Count recent denials (both rate_limited and policy_denied)
    result = conn.execute(
        """
        SELECT COUNT(*) 
        FROM action_logs
        WHERE user_id = ? 
          AND action_type = ?
          AND ok = FALSE
          AND created_at >= ?
          AND (
              json_extract_string(result, '$.error') = 'rate_limited'
              OR json_extract_string(result, '$.error') = 'policy_denied'
          )
        """,
        [user_id, action_type, window_start],
    ).fetchone()

    denial_count = result[0] if result else 0

    # Check if threshold is exceeded
    if denial_count >= ANOMALY_THRESHOLD_DENIALS:
        # Log security anomaly
        log_warning(
            logger,
            f"Suspicious activity detected: {denial_count} repeated {denial_type} denials",
            user_id=user_id,
            action_type=action_type,
            denial_type=denial_type,
            denial_count=denial_count,
            window_seconds=ANOMALY_DETECTION_WINDOW_SECONDS,
            target=redact_secrets(str(target)) if target else None,
        )

        # Write audit log with security.anomaly action type
        try:
            write_action_log(
                conn,
                user_id=user_id,
                action_type="security.anomaly",
                ok=False,
                target=target,
                request=request_data,
                result={
                    "anomaly_type": "repeated_denials",
                    "original_action": action_type,
                    "denial_type": denial_type,
                    "denial_count": denial_count,
                    "window_seconds": ANOMALY_DETECTION_WINDOW_SECONDS,
                },
            )
        except Exception as e:
            # Don't fail the request if anomaly logging fails
            log_warning(
                logger,
                f"Failed to write security.anomaly audit log: {e}",
                user_id=user_id,
                error=str(e),
            )

        return True

    return False
