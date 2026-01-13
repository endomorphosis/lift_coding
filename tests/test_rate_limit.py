"""Tests for rate limiting."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.action_logs import write_action_log
from handsfree.rate_limit import check_rate_limit


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_check_rate_limit_allows_first_request(db_conn):
    """Test that first request is always allowed."""
    user_id = str(uuid.uuid4())

    result = check_rate_limit(
        db_conn,
        user_id=user_id,
        action_type="test_action",
        window_seconds=60,
        max_requests=10,
    )

    assert result.allowed is True
    assert "0/10" in result.reason


def test_check_rate_limit_allows_under_limit(db_conn):
    """Test that requests under the limit are allowed."""
    user_id = str(uuid.uuid4())

    # Create 5 action logs
    for _i in range(5):
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="test_action",
            ok=True,
        )

    result = check_rate_limit(
        db_conn,
        user_id=user_id,
        action_type="test_action",
        window_seconds=60,
        max_requests=10,
    )

    assert result.allowed is True
    assert "5/10" in result.reason


def test_check_rate_limit_denies_over_limit(db_conn):
    """Test that requests over the limit are denied."""
    user_id = str(uuid.uuid4())

    # Create 10 action logs (at the limit)
    for _i in range(10):
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="test_action",
            ok=True,
        )

    result = check_rate_limit(
        db_conn,
        user_id=user_id,
        action_type="test_action",
        window_seconds=60,
        max_requests=10,
    )

    assert result.allowed is False
    assert "10/10" in result.reason
    assert result.retry_after_seconds is not None
    assert result.retry_after_seconds > 0


def test_check_rate_limit_different_users(db_conn):
    """Test that rate limits are per-user."""
    user1 = str(uuid.uuid4())
    user2 = str(uuid.uuid4())

    # Fill up user1's rate limit
    for _i in range(10):
        write_action_log(
            db_conn,
            user_id=user1,
            action_type="test_action",
            ok=True,
        )

    # User1 should be rate limited
    result1 = check_rate_limit(
        db_conn,
        user_id=user1,
        action_type="test_action",
        window_seconds=60,
        max_requests=10,
    )
    assert result1.allowed is False

    # User2 should still be allowed
    result2 = check_rate_limit(
        db_conn,
        user_id=user2,
        action_type="test_action",
        window_seconds=60,
        max_requests=10,
    )
    assert result2.allowed is True


def test_check_rate_limit_different_action_types(db_conn):
    """Test that rate limits are per-action-type."""
    user_id = str(uuid.uuid4())

    # Fill up rate limit for action_type_a
    for _i in range(10):
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="action_type_a",
            ok=True,
        )

    # action_type_a should be rate limited
    result_a = check_rate_limit(
        db_conn,
        user_id=user_id,
        action_type="action_type_a",
        window_seconds=60,
        max_requests=10,
    )
    assert result_a.allowed is False

    # action_type_b should still be allowed
    result_b = check_rate_limit(
        db_conn,
        user_id=user_id,
        action_type="action_type_b",
        window_seconds=60,
        max_requests=10,
    )
    assert result_b.allowed is True


def test_check_rate_limit_custom_window(db_conn):
    """Test rate limiting with a custom time window."""
    user_id = str(uuid.uuid4())

    # Create 3 action logs
    for _i in range(3):
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="test_action",
            ok=True,
        )

    # Should be denied with a small limit
    result = check_rate_limit(
        db_conn,
        user_id=user_id,
        action_type="test_action",
        window_seconds=60,
        max_requests=2,
    )
    assert result.allowed is False


def test_check_rate_limit_includes_failed_actions(db_conn):
    """Test that both successful and failed actions count toward the rate limit."""
    user_id = str(uuid.uuid4())

    # Create mix of successful and failed action logs
    for _i in range(5):
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="test_action",
            ok=True,
        )
    for _i in range(5):
        write_action_log(
            db_conn,
            user_id=user_id,
            action_type="test_action",
            ok=False,
        )

    result = check_rate_limit(
        db_conn,
        user_id=user_id,
        action_type="test_action",
        window_seconds=60,
        max_requests=10,
    )

    # All 10 actions (both ok and not ok) should count
    assert result.allowed is False
    assert "10/10" in result.reason
