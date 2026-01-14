"""Integration tests for request_review with live mode GitHub API calls."""

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app


class MockResponse:
    """Mock HTTP response for testing."""

    def __init__(self, status_code: int, json_data: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        """Return JSON data."""
        return self._json_data


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    global _db_conn
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    yield
    api_module._db_conn = None
    api_module._command_router = None


client = TestClient(app)


def test_request_review_live_mode_success(reset_db, monkeypatch):
    """Test request_review with live mode enabled and successful GitHub API call."""
    # Enable live mode
    monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")

    # Mock the GitHub API call
    def mock_post(*args, **kwargs):
        return MockResponse(
            status_code=201,
            json_data={
                "id": 1,
                "node_id": "PR_1",
                "number": 42,
            },
        )

    import handsfree.github.client as client_module

    client_module._import_httpx()
    monkeypatch.setattr(client_module._httpx, "post", mock_post)

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_request_review=True,
        require_confirmation=False,
    )

    # Make the request
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

    # Should succeed via live mode
    assert data["ok"] is True
    assert "alice" in data["message"] or "bob" in data["message"]

    # Check audit log shows live mode execution
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="request_review", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is True
    assert logs[0].result.get("message") == "Review requested (live mode)"


def test_request_review_live_mode_github_error(reset_db, monkeypatch):
    """Test request_review with live mode when GitHub API returns an error."""
    # Enable live mode
    monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")

    # Mock the GitHub API call to return an error
    def mock_post(*args, **kwargs):
        return MockResponse(
            status_code=422,
            json_data={"message": "Validation Failed"},
        )

    import handsfree.github.client as client_module

    client_module._import_httpx()
    monkeypatch.setattr(client_module._httpx, "post", mock_post)

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_request_review=True,
        require_confirmation=False,
    )

    # Make the request
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "reviewers": ["invalid-user"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should return error from GitHub API
    assert data["ok"] is False
    assert "GitHub API error" in data["message"]

    # Check audit log shows error
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="request_review", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is False
    assert logs[0].result.get("status") == "error"


def test_request_review_fallback_to_fixture_no_token(reset_db, monkeypatch):
    """Test that request_review falls back to fixtures when live mode is enabled but no token."""
    # Enable live mode but no token
    monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_request_review=True,
        require_confirmation=False,
    )

    # Make the request
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "reviewers": ["alice"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should succeed via fixture mode
    assert data["ok"] is True

    # Check audit log shows fixture mode
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="request_review", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is True
    assert logs[0].result.get("message") == "Review requested (fixture)"


def test_request_review_fallback_to_fixture_live_mode_disabled(reset_db, monkeypatch):
    """Test that request_review uses fixtures when live mode is disabled."""
    # Disable live mode
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_request_review=True,
        require_confirmation=False,
    )

    # Make the request
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "reviewers": ["alice"],
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should succeed via fixture mode
    assert data["ok"] is True

    # Check audit log shows fixture mode
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="request_review", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is True
    assert logs[0].result.get("message") == "Review requested (fixture)"


def test_confirm_request_review_live_mode(reset_db, monkeypatch):
    """Test confirming request_review with live mode enabled."""
    # Enable live mode
    monkeypatch.setenv("GITHUB_LIVE_MODE", "true")
    monkeypatch.setenv("GITHUB_TOKEN", "test_token_123")

    # Mock the GitHub API call
    def mock_post(*args, **kwargs):
        return MockResponse(
            status_code=201,
            json_data={
                "id": 1,
                "node_id": "PR_1",
                "number": 42,
            },
        )

    import handsfree.github.client as client_module

    client_module._import_httpx()
    monkeypatch.setattr(client_module._httpx, "post", mock_post)

    # Create a pending action
    from handsfree.api import get_db
    from handsfree.db.pending_actions import create_pending_action

    db = get_db()
    pending = create_pending_action(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        summary="Request review from alice on test/repo#42",
        action_type="request_review",
        action_payload={
            "repo": "test/repo",
            "pr_number": 42,
            "reviewers": ["alice"],
        },
        expires_in_seconds=300,
    )

    # Confirm the action
    response = client.post(
        "/v1/commands/confirm",
        json={
            "token": pending.token,
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should succeed
    assert data["status"] == "ok"
    assert "alice" in data["spoken_text"]

    # Check audit log shows live mode execution
    from handsfree.db.action_logs import get_action_logs

    logs = get_action_logs(db, action_type="request_review", limit=10)
    assert len(logs) > 0
    assert logs[0].ok is True
    assert logs[0].result.get("message") == "Review requested (live mode)"
    assert logs[0].result.get("via_confirmation") is True


def test_no_network_calls_without_live_mode(reset_db, monkeypatch):
    """Test that no network calls are made when live mode is disabled."""
    # Disable live mode
    monkeypatch.delenv("GITHUB_LIVE_MODE", raising=False)

    # Track if httpx.post was called
    post_called = {"called": False}

    def mock_post(*args, **kwargs):
        post_called["called"] = True
        return MockResponse(status_code=201, json_data={})

    import handsfree.github.client as client_module

    # Only patch if httpx is imported
    if client_module._httpx:
        monkeypatch.setattr(client_module._httpx, "post", mock_post)

    # Create policy that allows without confirmation
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="test/repo",
        allow_request_review=True,
        require_confirmation=False,
    )

    # Make the request
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "test/repo",
            "pr_number": 42,
            "reviewers": ["alice"],
        },
    )

    assert response.status_code == 200

    # Verify no network call was made
    assert post_called["called"] is False
