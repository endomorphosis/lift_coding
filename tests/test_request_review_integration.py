"""Integration tests for request-review action with policy and audit logging."""

import re
import uuid

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app
from handsfree.db.action_logs import get_action_logs
from handsfree.db.pending_actions import create_pending_action
from handsfree.db.repo_policies import create_or_update_repo_policy


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    global _db_conn
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None  # Also reset the router so it gets new db_conn
    yield
    api_module._db_conn = None
    api_module._command_router = None


client = TestClient(app)


def test_request_review_with_default_policy(reset_db):
    """Test that request-review requires confirmation with default policy."""
    from handsfree.api import get_db

    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "reviewers": ["alice", "bob"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Default policy requires confirmation
    assert data["ok"] is False
    assert "confirmation required" in data["message"].lower()
    assert "token" in data["message"]

    # Check that audit log was created
    db = get_db()
    logs = get_action_logs(db, action_type="request_review", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is True  # Request was valid, just needs confirmation
    assert logs[0].result.get("status") == "needs_confirmation"


def test_request_review_with_allow_policy(reset_db):
    """Test that request-review succeeds when policy allows without confirmation."""
    from handsfree.api import get_db

    db = get_db()

    # Create policy that allows without confirmation
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/allowed-repo",
        allow_request_review=True,
        require_confirmation=False,
    )

    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/allowed-repo",
            "pr_number": 42,
            "reviewers": ["alice"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should succeed immediately
    assert data["ok"] is True
    assert "review requested" in data["message"].lower()
    assert data["url"] is not None

    # Check audit log
    logs = get_action_logs(db, action_type="request_review", limit=10)
    last_log = logs[0]
    assert last_log.ok is True
    assert last_log.result.get("status") == "success"


def test_request_review_with_deny_policy(reset_db):
    """Test that request-review is denied when policy denies it."""
    from handsfree.api import get_db

    db = get_db()

    # Create policy that denies request_review
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/denied-repo",
        allow_request_review=False,
    )

    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/denied-repo",
            "pr_number": 42,
            "reviewers": ["alice"],
        },
    )

    assert response.status_code == 403
    data = response.json()

    assert data["error"] == "policy_denied"
    assert "not allowed" in data["message"].lower()

    # Check audit log shows denial
    logs = get_action_logs(db, action_type="request_review", limit=10)
    last_log = logs[0]
    assert last_log.ok is False
    assert last_log.result.get("error") == "policy_denied"


def test_request_review_idempotency(reset_db):
    """Test that request-review is idempotent with idempotency_key."""
    from handsfree.api import get_db

    db = get_db()
    idempotency_key = f"test-idem-{uuid.uuid4()}"

    # First request
    response1 = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "reviewers": ["alice"],
            "idempotency_key": idempotency_key,
        },
    )

    assert response1.status_code == 200
    data1 = response1.json()

    # Second request with same idempotency key
    response2 = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "reviewers": ["alice"],
            "idempotency_key": idempotency_key,
        },
    )

    assert response2.status_code == 200
    data2 = response2.json()

    # Should return the same result
    assert data1 == data2

    # Check that only one audit log was created
    logs = get_action_logs(db, action_type="request_review", limit=100)
    logs_with_key = [log for log in logs if log.idempotency_key == idempotency_key]
    assert len(logs_with_key) == 1


def test_request_review_rate_limiting(reset_db):
    """Test that request-review enforces rate limits."""
    from handsfree.api import get_db

    db = get_db()
    user_id = "00000000-0000-0000-0000-000000000001"

    # Create policy that allows without confirmation to test rate limiting directly
    create_or_update_repo_policy(
        db,
        user_id=user_id,
        repo_full_name="test/rate-test",
        allow_request_review=True,
        require_confirmation=False,
    )

    # Make 10 requests (should all succeed)
    for i in range(1, 11):  # Start at 1 since pr_number must be >= 1
        response = client.post(
            "/v1/actions/request-review",
            json={
                "repo": "test/rate-test",
                "pr_number": i,
                "reviewers": ["alice"],
            },
        )
        assert response.status_code == 200

    # 11th request should be rate limited
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/rate-test",
            "pr_number": 999,
            "reviewers": ["alice"],
        },
    )

    assert response.status_code == 429
    data = response.json()
    assert data["error"] == "rate_limited"
    assert "retry_after" in data

    # Check audit log shows rate limiting
    logs = get_action_logs(db, action_type="request_review", limit=20)
    rate_limited_logs = [log for log in logs if log.result.get("error") == "rate_limited"]
    assert len(rate_limited_logs) > 0


def test_request_review_validation(reset_db):
    """Test that request-review validates input correctly."""
    # Missing required fields
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/repo",
            # Missing pr_number and reviewers
        },
    )

    assert response.status_code == 422  # Validation error


def test_request_review_audit_log_target_format(reset_db):
    """Test that audit logs use correct target format."""
    from handsfree.api import get_db

    db = get_db()

    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "owner/repo",
            "pr_number": 123,
            "reviewers": ["user1"],
        },
    )

    assert response.status_code == 200

    # Check audit log target format
    logs = get_action_logs(db, action_type="request_review", limit=10)
    last_log = logs[0]
    assert last_log.target == "owner/repo#123"


def test_confirm_request_review_executes_once(reset_db):
    """Test that confirming a request_review action executes exactly once."""
    from handsfree.api import get_db

    db = get_db()

    # Create a request that requires confirmation
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/confirm-repo",
            "pr_number": 99,
            "reviewers": ["alice"],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "token" in data["message"]

    # Extract token from message
    match = re.search(r"token '([^']+)'", data["message"])
    assert match is not None
    token = match.group(1)

    # Confirm the action
    confirm_response = client.post(
        "/v1/commands/confirm",
        json={"token": token},
    )

    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["status"] == "ok"
    assert "review requested" in confirm_data["spoken_text"].lower()

    # Check that audit log was created for the confirmation
    logs = get_action_logs(db, action_type="request_review", limit=10)
    confirmation_logs = [log for log in logs if log.result.get("via_confirmation")]
    assert len(confirmation_logs) == 1
    assert confirmation_logs[0].ok is True
    assert confirmation_logs[0].target == "test/confirm-repo#99"


def test_confirm_request_review_retry_does_not_duplicate(reset_db):
    """Test that retrying confirmation does not duplicate audit logs or side effects."""
    from handsfree.api import get_db

    db = get_db()

    # Create a request that requires confirmation
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/retry-repo",
            "pr_number": 100,
            "reviewers": ["bob"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Extract token
    match = re.search(r"token '([^']+)'", data["message"])
    assert match is not None
    token = match.group(1)

    # Confirm the action once
    confirm_response1 = client.post(
        "/v1/commands/confirm",
        json={"token": token},
    )

    assert confirm_response1.status_code == 200

    # Count audit logs for confirmation
    logs_after_first = get_action_logs(db, action_type="request_review", limit=10)
    confirmation_logs_after_first = [
        log for log in logs_after_first if log.result.get("via_confirmation")
    ]
    assert len(confirmation_logs_after_first) == 1

    # Try to confirm again with the same token (should fail)
    confirm_response2 = client.post(
        "/v1/commands/confirm",
        json={"token": token},
    )

    # Should return 404 because the action was already consumed
    assert confirm_response2.status_code == 404
    error_data = confirm_response2.json()
    assert error_data["error"] == "not_found"
    assert "already consumed" in error_data["message"] or "not found" in error_data["message"]

    # Confirm that no duplicate audit logs were created
    logs_after_retry = get_action_logs(db, action_type="request_review", limit=10)
    confirmation_logs_after_retry = [
        log for log in logs_after_retry if log.result.get("via_confirmation")
    ]
    assert len(confirmation_logs_after_retry) == 1  # Still only one confirmation log


def test_confirm_missing_token_returns_404(reset_db):
    """Test that confirming with a missing/invalid token returns 404."""
    confirm_response = client.post(
        "/v1/commands/confirm",
        json={"token": "nonexistent-token-12345"},
    )

    assert confirm_response.status_code == 404
    error_data = confirm_response.json()
    assert error_data["error"] == "not_found"
    assert "not found" in error_data["message"].lower()


def test_confirm_expired_token_returns_404(reset_db):
    """Test that confirming with an expired token returns 404."""
    from handsfree.api import get_db

    db = get_db()

    # Create an already-expired pending action
    expired_action = create_pending_action(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        summary="Expired test action",
        action_type="request_review",
        action_payload={"repo": "test/repo", "pr_number": 1, "reviewers": ["alice"]},
        expires_in_seconds=-10,  # Already expired
    )

    # Try to confirm the expired action
    confirm_response = client.post(
        "/v1/commands/confirm",
        json={"token": expired_action.token},
    )

    assert confirm_response.status_code == 404
    error_data = confirm_response.json()
    assert error_data["error"] == "not_found"
    # Should contain either "not found" or "expired" in the error message
    message_lower = error_data["message"].lower()
    assert "not found" in message_lower or "expired" in message_lower
