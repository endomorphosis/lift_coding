"""Integration tests for rerun_checks with live mode GitHub API calls."""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        """Return JSON data."""
        if not self._json_data:
            # Simulate JSONDecodeError for empty response
            import json

            raise json.JSONDecodeError("Expecting value", "", 0)
        return self._json_data


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    yield
    api_module._db_conn = None
    api_module._command_router = None


client = TestClient(app)


def test_rerun_checks_live_mode_success(reset_db, monkeypatch):
    """Test rerun_checks with live mode enabled and successful GitHub API call."""
    # Enable live mode
    monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")

    # Mock the GitHub API calls
    call_count = {"get": 0, "post": 0}

    def mock_get(*args, **kwargs):
        call_count["get"] += 1
        url = args[0] if args else kwargs.get("url", "")

        # Mock PR endpoint
        if "/pulls/" in url:
            return MockResponse(
                status_code=200,
                json_data={
                    "number": 42,
                    "head": {"sha": "abc123def456"},
                },
            )
        # Mock workflow runs endpoint
        elif "/actions/runs" in url:
            return MockResponse(
                status_code=200,
                json_data={
                    "total_count": 1,
                    "workflow_runs": [
                        {
                            "id": 12345,
                            "name": "CI",
                            "status": "completed",
                            "conclusion": "failure",
                        }
                    ],
                },
            )
        return MockResponse(status_code=404)

    def mock_post(*args, **kwargs):
        call_count["post"] += 1
        # Mock rerun endpoint
        return MockResponse(status_code=201)

    import handsfree.github.client as client_module

    client_module._import_httpx()
    monkeypatch.setattr(client_module._httpx, "get", mock_get)
    monkeypatch.setattr(client_module._httpx, "post", mock_post)

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_rerun=True,
        require_confirmation=False,
    )

    # Make the request
    response = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "test/repo",
            "pr_number": 42,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should succeed via live mode
    assert data["ok"] is True
    assert "re-run" in data["message"].lower() or "rerun" in data["message"].lower()

    # Check audit log shows live mode execution
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="rerun", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is True
    assert logs[0].result.get("message") == "Checks re-run (live mode)"
    assert logs[0].result.get("run_id") == 12345


def test_rerun_checks_fixture_mode(reset_db, monkeypatch):
    """Test rerun_checks falls back to fixture mode when live mode disabled."""
    # Disable live mode
    monkeypatch.setenv("GITHUB_LIVE_MODE", "false")

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_rerun=True,
        require_confirmation=False,
    )

    # Make the request
    response = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "test/repo",
            "pr_number": 42,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should succeed in fixture mode
    assert data["ok"] is True
    assert "re-run" in data["message"].lower()

    # Check audit log shows fixture mode execution
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="rerun", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is True
    assert logs[0].result.get("message") == "Checks re-run (fixture)"


def test_rerun_checks_requires_confirmation(reset_db, monkeypatch):
    """Test rerun_checks requires confirmation when policy dictates."""
    # Disable live mode for simplicity
    monkeypatch.setenv("GITHUB_LIVE_MODE", "false")

    # Create policy that requires confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_rerun=True,
        require_confirmation=True,
    )

    # Make the request
    response = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "test/repo",
            "pr_number": 42,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should require confirmation
    assert data["ok"] is False
    assert "confirmation required" in data["message"].lower()
    assert "token" in data["message"].lower()

    # Extract token from message
    import re

    token_match = re.search(r"token '([^']+)'", data["message"])
    assert token_match is not None
    token = token_match.group(1)

    # Check audit log shows confirmation required
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="rerun", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is True
    assert logs[0].result.get("status") == "needs_confirmation"

    # Now confirm the action
    confirm_response = client.post(
        "/v1/commands/confirm",
        json={"token": token},
    )

    assert confirm_response.status_code == 200
    confirm_data = confirm_response.json()
    assert confirm_data["status"] == "ok"
    assert "re-run" in confirm_data["spoken_text"].lower()

    # Check audit log shows successful execution after confirmation
    logs = get_action_logs(db, action_type="rerun", limit=10)
    confirmed_log = next((log for log in logs if log.result.get("via_confirmation")), None)
    assert confirmed_log is not None
    assert confirmed_log.ok is True


def test_rerun_checks_policy_denied(reset_db, monkeypatch):
    """Test rerun_checks respects policy denial."""
    # Disable live mode for simplicity
    monkeypatch.setenv("GITHUB_LIVE_MODE", "false")

    # Create policy that denies rerun
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_rerun=False,  # Deny rerun
    )

    # Make the request
    response = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "test/repo",
            "pr_number": 42,
        },
    )

    # Should be denied with 403
    assert response.status_code == 403
    data = response.json()
    assert "policy" in data["message"].lower() or "not allowed" in data["message"].lower()

    # Check audit log shows policy denial
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="rerun", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is False
    assert logs[0].result.get("error") == "policy_denied"


def test_rerun_checks_rate_limited(reset_db, monkeypatch):
    """Test rerun_checks respects rate limiting."""
    # Disable live mode for simplicity
    monkeypatch.setenv("GITHUB_LIVE_MODE", "false")

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_rerun=True,
        require_confirmation=False,
    )

    # Make 5 successful requests (should hit rate limit at max_requests=5)
    for i in range(5):
        response = client.post(
            "/v1/actions/rerun-checks",
            json={
                "repo": "test/repo",
                "pr_number": 42 + i,
            },
        )
        assert response.status_code == 200

    # 6th request should be rate limited
    response = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "test/repo",
            "pr_number": 50,
        },
    )

    assert response.status_code == 429
    data = response.json()
    assert "rate limit" in data["message"].lower()
    assert "retry_after" in data

    # Check audit log shows rate limit
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="rerun", limit=10)
    rate_limited_log = next(
        (log for log in logs if not log.ok and log.result.get("error") == "rate_limited"),
        None,
    )
    assert rate_limited_log is not None


def test_rerun_checks_github_api_error(reset_db, monkeypatch):
    """Test rerun_checks handles GitHub API errors gracefully."""
    # Enable live mode
    monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")

    # Mock the GitHub API calls to return an error
    def mock_get(*args, **kwargs):
        url = args[0] if args else kwargs.get("url", "")
        # Mock PR endpoint
        if "/pulls/" in url:
            return MockResponse(
                status_code=404,
                json_data={"message": "Not Found"},
            )
        return MockResponse(status_code=404)

    import handsfree.github.client as client_module

    client_module._import_httpx()
    monkeypatch.setattr(client_module._httpx, "get", mock_get)

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_rerun=True,
        require_confirmation=False,
    )

    # Make the request
    response = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "test/repo",
            "pr_number": 42,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should return error
    assert data["ok"] is False
    assert "error" in data["message"].lower() or "404" in data["message"]

    # Check audit log shows error
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="rerun", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is False
    assert logs[0].result.get("status") == "error"


def test_rerun_checks_idempotency(reset_db, monkeypatch):
    """Test rerun_checks respects idempotency keys."""
    # Disable live mode for simplicity
    monkeypatch.setenv("GITHUB_LIVE_MODE", "false")

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_rerun=True,
        require_confirmation=False,
    )

    # Make the first request with idempotency key
    response1 = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "idempotency_key": "test-key-123",
        },
    )

    assert response1.status_code == 200
    data1 = response1.json()
    assert data1["ok"] is True

    # Make the same request again with the same idempotency key
    response2 = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "idempotency_key": "test-key-123",
        },
    )

    assert response2.status_code == 200
    data2 = response2.json()

    # Should return the same result
    assert data2 == data1

    # Check audit log - should only have one entry for this action
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="rerun", limit=10)
    logs_with_key = [log for log in logs if log.idempotency_key == "test-key-123"]
    assert len(logs_with_key) == 1
