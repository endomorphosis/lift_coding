"""Tests for enhanced rate limiting with burst limits and anomaly detection."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.action_logs import get_action_logs, write_action_log
from handsfree.rate_limit import (
    SIDE_EFFECT_RATE_LIMITS,
    check_rate_limit,
    check_side_effect_rate_limit,
)
from handsfree.security import check_and_log_anomaly


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


class TestBurstLimiting:
    """Test burst rate limiting functionality."""

    def test_burst_limit_triggers_before_window_limit(self, db_conn):
        """Test that burst limit triggers before the window limit."""
        user_id = str(uuid.uuid4())

        # Create 3 action logs quickly (burst_max is 3)
        for _i in range(3):
            write_action_log(
                db_conn,
                user_id=user_id,
                action_type="test_action",
                ok=True,
            )

        # Should be denied by burst limit (3/3 in last 10s)
        result = check_rate_limit(
            db_conn,
            user_id=user_id,
            action_type="test_action",
            window_seconds=60,
            max_requests=10,
            burst_seconds=10,
            burst_max=3,
        )

        assert result.allowed is False
        assert result.is_burst_limited is True
        assert "Burst limit exceeded" in result.reason
        assert "3/3" in result.reason
        assert result.retry_after_seconds is not None
        assert result.retry_after_seconds > 0

    def test_burst_limit_allows_under_burst_max(self, db_conn):
        """Test that requests under burst max are allowed."""
        user_id = str(uuid.uuid4())

        # Create 2 action logs (under burst_max of 3)
        for _i in range(2):
            write_action_log(
                db_conn,
                user_id=user_id,
                action_type="test_action",
                ok=True,
            )

        # Should be allowed
        result = check_rate_limit(
            db_conn,
            user_id=user_id,
            action_type="test_action",
            window_seconds=60,
            max_requests=10,
            burst_seconds=10,
            burst_max=3,
        )

        assert result.allowed is True
        assert result.is_burst_limited is False

    def test_burst_limit_per_user(self, db_conn):
        """Test that burst limits are per-user."""
        user1 = str(uuid.uuid4())
        user2 = str(uuid.uuid4())

        # Fill up user1's burst limit
        for _i in range(3):
            write_action_log(
                db_conn,
                user_id=user1,
                action_type="test_action",
                ok=True,
            )

        # User1 should be burst limited
        result1 = check_rate_limit(
            db_conn,
            user_id=user1,
            action_type="test_action",
            window_seconds=60,
            max_requests=10,
            burst_seconds=10,
            burst_max=3,
        )
        assert result1.allowed is False
        assert result1.is_burst_limited is True

        # User2 should still be allowed
        result2 = check_rate_limit(
            db_conn,
            user_id=user2,
            action_type="test_action",
            window_seconds=60,
            max_requests=10,
            burst_seconds=10,
            burst_max=3,
        )
        assert result2.allowed is True
        assert result2.is_burst_limited is False


class TestSideEffectRateLimits:
    """Test side-effect rate limit helper function."""

    def test_side_effect_rate_limits_configured(self):
        """Test that side-effect actions have configured limits."""
        # Check that all expected side-effect actions have limits
        expected_actions = ["request_review", "rerun", "merge", "comment"]
        for action in expected_actions:
            assert action in SIDE_EFFECT_RATE_LIMITS
            limits = SIDE_EFFECT_RATE_LIMITS[action]
            assert "window_seconds" in limits
            assert "max_requests" in limits
            assert "burst_seconds" in limits
            assert "burst_max" in limits

    def test_check_side_effect_rate_limit_uses_burst(self, db_conn):
        """Test that check_side_effect_rate_limit applies burst limits."""
        user_id = str(uuid.uuid4())

        # Get the burst limit for request_review
        burst_max = SIDE_EFFECT_RATE_LIMITS["request_review"]["burst_max"]

        # Create actions up to burst limit
        for _i in range(burst_max):
            write_action_log(
                db_conn,
                user_id=user_id,
                action_type="request_review",
                ok=True,
            )

        # Should be denied by burst limit
        result = check_side_effect_rate_limit(
            db_conn,
            user_id,
            "request_review",
        )

        assert result.allowed is False
        assert result.is_burst_limited is True

    def test_side_effect_rate_limits_stricter_for_dangerous_actions(self):
        """Test that merge and rerun have stricter limits than request_review."""
        request_review_limits = SIDE_EFFECT_RATE_LIMITS["request_review"]
        merge_limits = SIDE_EFFECT_RATE_LIMITS["merge"]
        rerun_limits = SIDE_EFFECT_RATE_LIMITS["rerun"]

        # Merge and rerun should have lower limits
        assert merge_limits["max_requests"] <= request_review_limits["max_requests"]
        assert rerun_limits["max_requests"] <= request_review_limits["max_requests"]
        assert merge_limits["burst_max"] <= request_review_limits["burst_max"]
        assert rerun_limits["burst_max"] <= request_review_limits["burst_max"]


class TestAnomalyDetection:
    """Test anomaly detection and security logging."""

    def test_anomaly_detected_after_repeated_rate_limits(self, db_conn):
        """Test that anomaly is detected after repeated rate limit denials."""
        user_id = str(uuid.uuid4())

        # Create 5 rate limit denials (threshold is 5 denials in 5 minutes)
        for _i in range(5):
            write_action_log(
                db_conn,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target="test/repo#123",
                request={"reviewers": ["alice"]},
                result={"error": "rate_limited", "message": "Rate limit exceeded"},
            )

        # Check for anomaly
        anomaly_detected = check_and_log_anomaly(
            db_conn,
            user_id,
            "request_review",
            "rate_limited",
            target="test/repo#123",
            request_data={"reviewers": ["alice"]},
        )

        assert anomaly_detected is True

        # Verify security.anomaly audit log was created
        logs = get_action_logs(db_conn, user_id=user_id, action_type="security.anomaly")
        assert len(logs) >= 1

        # Check the anomaly log details
        anomaly_log = logs[0]
        assert anomaly_log.ok is False
        assert anomaly_log.result["anomaly_type"] == "repeated_denials"
        assert anomaly_log.result["original_action"] == "request_review"
        assert anomaly_log.result["denial_type"] == "rate_limited"
        assert anomaly_log.result["denial_count"] >= 5

    def test_anomaly_not_detected_below_threshold(self, db_conn):
        """Test that no anomaly is detected below threshold."""
        user_id = str(uuid.uuid4())

        # Create only 3 denials (below threshold of 5)
        for _i in range(3):
            write_action_log(
                db_conn,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target="test/repo#123",
                request={"reviewers": ["alice"]},
                result={"error": "rate_limited", "message": "Rate limit exceeded"},
            )

        # Check for anomaly
        anomaly_detected = check_and_log_anomaly(
            db_conn,
            user_id,
            "request_review",
            "rate_limited",
            target="test/repo#123",
            request_data={"reviewers": ["alice"]},
        )

        assert anomaly_detected is False

        # Verify no security.anomaly audit log was created
        logs = get_action_logs(db_conn, user_id=user_id, action_type="security.anomaly")
        assert len(logs) == 0

    def test_anomaly_detected_for_policy_denials(self, db_conn):
        """Test that anomaly detection works for policy denials too."""
        user_id = str(uuid.uuid4())

        # Create 5 policy denials
        for _i in range(5):
            write_action_log(
                db_conn,
                user_id=user_id,
                action_type="merge",
                ok=False,
                target="test/repo#123",
                request={"merge_method": "merge"},
                result={"error": "policy_denied", "message": "Merge not allowed"},
            )

        # Check for anomaly
        anomaly_detected = check_and_log_anomaly(
            db_conn,
            user_id,
            "merge",
            "policy_denied",
            target="test/repo#123",
            request_data={"merge_method": "merge"},
        )

        assert anomaly_detected is True

        # Verify security.anomaly audit log was created
        logs = get_action_logs(db_conn, user_id=user_id, action_type="security.anomaly")
        assert len(logs) >= 1
        assert logs[0].result["denial_type"] == "policy_denied"

    def test_anomaly_per_action_type(self, db_conn):
        """Test that anomaly detection is per action type."""
        user_id = str(uuid.uuid4())

        # Create 3 denials for request_review
        for _i in range(3):
            write_action_log(
                db_conn,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                result={"error": "rate_limited", "message": "Rate limit exceeded"},
            )

        # Create 3 denials for merge
        for _i in range(3):
            write_action_log(
                db_conn,
                user_id=user_id,
                action_type="merge",
                ok=False,
                result={"error": "rate_limited", "message": "Rate limit exceeded"},
            )

        # Neither should trigger anomaly (3 < 5 threshold)
        anomaly_rr = check_and_log_anomaly(
            db_conn,
            user_id,
            "request_review",
            "rate_limited",
        )
        anomaly_merge = check_and_log_anomaly(
            db_conn,
            user_id,
            "merge",
            "rate_limited",
        )

        assert anomaly_rr is False
        assert anomaly_merge is False
