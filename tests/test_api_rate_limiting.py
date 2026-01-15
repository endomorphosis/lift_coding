"""Tests for API endpoint rate limiting with Retry-After headers and anomaly detection."""

import uuid

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app, get_db
from handsfree.db.action_logs import get_action_logs, write_action_log
from handsfree.security import check_and_log_anomaly


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    yield
    api_module._db_conn = None
    api_module._command_router = None


class TestRetryAfterHeaders:
    """Test that 429 responses include Retry-After header."""

    def test_request_review_returns_retry_after_header(self, client, reset_db, monkeypatch):
        """Test that /v1/actions/request-review returns Retry-After on 429."""
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")
        user_id = str(uuid.uuid4())

        # Create a temporary DB and fill burst limit
        from handsfree.api import get_db
        from handsfree.rate_limit import SIDE_EFFECT_RATE_LIMITS

        db = get_db()
        burst_max = SIDE_EFFECT_RATE_LIMITS["request_review"]["burst_max"]

        for _i in range(burst_max):
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=True,
            )

        # Next request should be rate limited
        response = client.post(
            "/v1/actions/request-review",
            json={
                "repo": "test/repo",
                "pr_number": 123,
                "reviewers": ["alice"],
                "idempotency_key": str(uuid.uuid4()),
            },
            headers={"X-User-ID": user_id},
        )

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0
        assert retry_after <= 10  # Should be within burst window

        # Check response body includes retry_after
        data = response.json()
        assert data["detail"]["error"] == "rate_limited"
        assert data["detail"]["retry_after"] is not None

    def test_rerun_checks_returns_retry_after_header(self, client, reset_db, monkeypatch):
        """Test that /v1/actions/rerun-checks returns Retry-After on 429."""
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")
        user_id = str(uuid.uuid4())

        from handsfree.api import get_db
        from handsfree.rate_limit import SIDE_EFFECT_RATE_LIMITS

        db = get_db()
        burst_max = SIDE_EFFECT_RATE_LIMITS["rerun"]["burst_max"]

        for _i in range(burst_max):
            write_action_log(
                db,
                user_id=user_id,
                action_type="rerun",
                ok=True,
            )

        response = client.post(
            "/v1/actions/rerun-checks",
            json={
                "repo": "test/repo",
                "pr_number": 123,
                "idempotency_key": str(uuid.uuid4()),
            },
            headers={"X-User-ID": user_id},
        )

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0

    def test_merge_returns_retry_after_header(self, client, reset_db, monkeypatch):
        """Test that /v1/actions/merge returns Retry-After on 429."""
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")
        user_id = str(uuid.uuid4())

        from handsfree.api import get_db
        from handsfree.rate_limit import SIDE_EFFECT_RATE_LIMITS

        db = get_db()
        burst_max = SIDE_EFFECT_RATE_LIMITS["merge"]["burst_max"]

        for _i in range(burst_max):
            write_action_log(
                db,
                user_id=user_id,
                action_type="merge",
                ok=True,
            )

        response = client.post(
            "/v1/actions/merge",
            json={
                "repo": "test/repo",
                "pr_number": 123,
                "merge_method": "merge",
                "idempotency_key": str(uuid.uuid4()),
            },
            headers={"X-User-ID": user_id},
        )

        assert response.status_code == 429
        assert "Retry-After" in response.headers
        retry_after = int(response.headers["Retry-After"])
        assert retry_after > 0


class TestVoiceCommandRateLimiting:
    """Test voice command responses for rate limiting."""

    def test_voice_command_rate_limit_includes_retry_guidance(self, client, reset_db, monkeypatch):
        """Test that voice commands include user-friendly retry guidance."""
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")
        user_id = str(uuid.uuid4())

        from handsfree.api import get_db
        from handsfree.rate_limit import SIDE_EFFECT_RATE_LIMITS

        db = get_db()
        burst_max = SIDE_EFFECT_RATE_LIMITS["request_review"]["burst_max"]

        # Fill burst limit
        for _i in range(burst_max):
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=True,
            )

        # Make a voice command request
        response = client.post(
            "/v1/command",
            json={
                "input": {"type": "text", "text": "request review from alice on PR 123"},
                "profile": "default",
                "client_context": {
                    "device": "test",
                    "locale": "en-US",
                    "timezone": "UTC",
                    "app_version": "0.1.0",
                },
            },
            headers={"X-User-ID": user_id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "error"

        # Check spoken text includes retry guidance
        spoken_text = data["spoken_text"]
        assert "Rate limit exceeded" in spoken_text
        assert "try again" in spoken_text or "seconds" in spoken_text


class TestAnomalyAuditLogs:
    """Test that anomalies are logged in audit logs."""

    def test_anomaly_logged_after_repeated_rate_limits(self, client, reset_db, monkeypatch):
        """Test that security.anomaly is logged after repeated rate limits."""
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")
        user_id = str(uuid.uuid4())

        from handsfree.api import get_db

        db = get_db()

        # Create 5 rate limit denials to trigger anomaly detection
        for _i in range(5):
            response = client.post(
                "/v1/actions/request-review",
                json={
                    "repo": "test/repo",
                    "pr_number": 123,
                    "reviewers": ["alice"],
                    "idempotency_key": str(uuid.uuid4()),
                },
                headers={"X-User-ID": user_id},
            )
            # First few will succeed or be rate limited
            # We need to create denials manually for this test
            write_action_log(
                db,
                user_id=user_id,
                action_type="request_review",
                ok=False,
                target="test/repo#123",
                request={"reviewers": ["alice"]},
                result={"error": "rate_limited", "message": "Rate limit exceeded"},
            )

        # Make one more request which should trigger anomaly detection
        response = client.post(
            "/v1/actions/request-review",
            json={
                "repo": "test/repo",
                "pr_number": 123,
                "reviewers": ["alice"],
                "idempotency_key": str(uuid.uuid4()),
            },
            headers={"X-User-ID": user_id},
        )

        # Should be rate limited
        assert response.status_code == 429

        # Check for security.anomaly audit log
        logs = get_action_logs(db, user_id=user_id, action_type="security.anomaly")
        assert len(logs) >= 1

        # Verify anomaly log structure
        anomaly_log = logs[0]
        assert anomaly_log.action_type == "security.anomaly"
        assert anomaly_log.ok is False
        assert "anomaly_type" in anomaly_log.result
        assert anomaly_log.result["anomaly_type"] == "repeated_denials"
        assert anomaly_log.result["original_action"] == "request_review"

    def test_anomaly_logged_for_policy_denials(self, client, reset_db, monkeypatch):
        """Test that security.anomaly is logged for repeated policy denials."""
        monkeypatch.setenv("HANDSFREE_AUTH_MODE", "dev")
        user_id = str(uuid.uuid4())

        db = get_db()

        # Create 5 policy denials manually
        # (not counting towards rate limit by using different timestamps)
        for _i in range(5):
            write_action_log(
                db,
                user_id=user_id,
                action_type="merge",
                ok=False,
                target="test/repo#123",
                request={"merge_method": "merge"},
                result={"error": "policy_denied", "message": "Merge not allowed"},
            )

        # Manually trigger anomaly detection to simulate what would happen on the next policy denial
        anomaly_detected = check_and_log_anomaly(
            db,
            user_id,
            "merge",
            "policy_denied",
            target="test/repo#123",
            request_data={"merge_method": "merge"},
        )

        # Verify anomaly was detected
        assert anomaly_detected is True

        # Check for security.anomaly audit log
        logs = get_action_logs(db, user_id=user_id, action_type="security.anomaly")
        assert len(logs) >= 1
        assert logs[0].result["denial_type"] == "policy_denied"
        assert logs[0].result["original_action"] == "merge"
