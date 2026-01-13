"""Contract tests ensuring API responses match OpenAPI schema."""

from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


def test_post_command_text_inbox() -> None:
    """Test POST /v1/command with inbox query."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "inbox"},
            "profile": "workout",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
                "noise_mode": True,
            },
            "idempotency_key": "test-1",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Validate CommandResponse structure
    assert "status" in data
    assert data["status"] in ["ok", "needs_confirmation", "error"]
    assert "intent" in data
    assert "spoken_text" in data

    # Validate ParsedIntent
    assert "name" in data["intent"]
    assert "confidence" in data["intent"]
    assert 0 <= data["intent"]["confidence"] <= 1

    # Should have cards for inbox items
    if "cards" in data:
        assert isinstance(data["cards"], list)
        for card in data["cards"]:
            assert "title" in card


def test_post_command_summarize_pr() -> None:
    """Test POST /v1/command with PR summarize."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "summarize pr 412"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
            "idempotency_key": "test-2",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should have pending action for confirmation
    assert data["status"] == "needs_confirmation"
    assert "pending_action" in data
    assert data["pending_action"] is not None

    # Validate PendingAction
    pending = data["pending_action"]
    assert "token" in pending
    assert "expires_at" in pending
    assert "summary" in pending


def test_post_command_idempotency() -> None:
    """Test idempotency of POST /v1/command."""
    payload = {
        "input": {"type": "text", "text": "inbox"},
        "profile": "default",
        "client_context": {
            "device": "simulator",
            "locale": "en-US",
            "timezone": "America/Los_Angeles",
            "app_version": "0.1.0",
        },
        "idempotency_key": "idem-test-1",
    }

    response1 = client.post("/v1/command", json=payload)
    response2 = client.post("/v1/command", json=payload)

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()


def test_post_confirm_valid_token() -> None:
    """Test POST /v1/commands/confirm with valid token."""
    # First, create a pending action
    cmd_response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "summarize pr 100"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert cmd_response.status_code == 200
    cmd_data = cmd_response.json()
    assert "pending_action" in cmd_data
    token = cmd_data["pending_action"]["token"]

    # Now confirm it
    confirm_response = client.post(
        "/v1/commands/confirm",
        json={"token": token, "idempotency_key": "confirm-test-1"},
    )

    assert confirm_response.status_code == 200
    data = confirm_response.json()
    assert "status" in data
    assert "intent" in data
    assert "spoken_text" in data


def test_post_confirm_invalid_token() -> None:
    """Test POST /v1/commands/confirm with invalid token."""
    response = client.post(
        "/v1/commands/confirm",
        json={"token": "invalid-token-12345"},
    )

    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert "message" in data


def test_get_inbox_default() -> None:
    """Test GET /v1/inbox without profile."""
    response = client.get("/v1/inbox")

    assert response.status_code == 200
    data = response.json()

    # Validate InboxResponse
    assert "items" in data
    assert isinstance(data["items"], list)

    # Validate InboxItem structure
    for item in data["items"]:
        assert "type" in item
        assert item["type"] in ["pr", "mention", "check", "agent"]
        assert "title" in item
        assert "priority" in item
        assert 1 <= item["priority"] <= 5


def test_get_inbox_with_profile() -> None:
    """Test GET /v1/inbox with workout profile."""
    response = client.get("/v1/inbox?profile=workout")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data

    # In workout mode, should only show high priority items
    for item in data["items"]:
        assert item["priority"] >= 4


def test_post_webhook_github() -> None:
    """Test POST /v1/webhooks/github."""
    response = client.post(
        "/v1/webhooks/github",
        json={
            "action": "opened",
            "pull_request": {
                "id": 123,
                "number": 456,
                "title": "Test PR",
            },
        },
        headers={
            "X-GitHub-Event": "pull_request",
            "X-GitHub-Delivery": "test-delivery-001",
            "X-Hub-Signature-256": "dev",
        },
    )

    assert response.status_code == 202
    data = response.json()
    assert "event_id" in data
    assert "message" in data


def test_post_action_request_review() -> None:
    """Test POST /v1/actions/request-review with policy evaluation."""
    response = client.post(
        "/v1/actions/request-review",
        json={
            "repo": "owner/repo",
            "pr_number": 123,
            "reviewers": ["user1", "user2"],
            "idempotency_key": "review-test-1",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Validate ActionResult
    assert "ok" in data
    assert "message" in data
    assert isinstance(data["ok"], bool)
    # Default policy requires confirmation
    assert data["ok"] is False
    assert "confirmation required" in data["message"].lower()


def test_post_action_rerun_checks() -> None:
    """Test POST /v1/actions/rerun-checks stub."""
    response = client.post(
        "/v1/actions/rerun-checks",
        json={
            "repo": "owner/repo",
            "pr_number": 456,
            "idempotency_key": "rerun-test-1",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Validate ActionResult
    assert "ok" in data
    assert "message" in data
    assert "[STUB]" in data["message"]


def test_post_action_merge() -> None:
    """Test POST /v1/actions/merge stub."""
    response = client.post(
        "/v1/actions/merge",
        json={
            "repo": "owner/repo",
            "pr_number": 789,
            "merge_method": "squash",
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Validate ActionResult
    assert "ok" in data
    assert "message" in data
    # Merge should indicate it's not yet implemented
    assert data["ok"] is False
    assert "policy" in data["message"].lower() or "PR-007" in data["message"]


def test_invalid_command_request() -> None:
    """Test POST /v1/command with invalid payload."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text"},  # Missing required 'text' field
            "profile": "default",
        },
    )

    assert response.status_code == 422  # Validation error
