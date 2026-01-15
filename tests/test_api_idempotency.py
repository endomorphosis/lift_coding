"""Integration tests for API idempotency with persistent storage."""

import uuid

import pytest
from fastapi.testclient import TestClient

from handsfree.api import app


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    global _db_conn
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    # Clear in-memory stores
    api_module.processed_commands.clear()
    api_module.idempotency_store.clear()
    yield
    api_module._db_conn = None
    api_module._command_router = None


client = TestClient(app)


def test_command_endpoint_idempotency(reset_db):
    """Test /v1/command returns same response with same idempotency key."""
    idempotency_key = f"test-key-{uuid.uuid4()}"

    request_body = {
        "input": {"text": "show my inbox"},
        "profile": "default",
        "client_context": {
            "device": "test",
            "locale": "en-US",
            "timezone": "America/Los_Angeles",
            "app_version": "0.1.0",
        },
        "idempotency_key": idempotency_key,
    }

    # First request
    response1 = client.post("/v1/command", json=request_body)
    assert response1.status_code == 200
    data1 = response1.json()

    # Second request with same idempotency key
    response2 = client.post("/v1/command", json=request_body)
    assert response2.status_code == 200
    data2 = response2.json()

    # Responses should be identical
    assert data1 == data2
    assert data1["status"] == data2["status"]
    assert data1["intent"]["name"] == data2["intent"]["name"]
    assert data1["spoken_text"] == data2["spoken_text"]


def test_command_endpoint_idempotency_persists_across_memory_clear(reset_db):
    """Test that idempotency persists even if in-memory cache is cleared."""
    from handsfree.api import processed_commands

    idempotency_key = f"test-key-{uuid.uuid4()}"

    request_body = {
        "input": {"text": "show my inbox"},
        "profile": "default",
        "client_context": {
            "device": "test",
            "locale": "en-US",
            "timezone": "America/Los_Angeles",
            "app_version": "0.1.0",
        },
        "idempotency_key": idempotency_key,
    }

    # First request
    response1 = client.post("/v1/command", json=request_body)
    assert response1.status_code == 200
    data1 = response1.json()

    # Clear in-memory cache to simulate server restart
    processed_commands.clear()

    # Second request should still return cached response from database
    response2 = client.post("/v1/command", json=request_body)
    assert response2.status_code == 200
    data2 = response2.json()

    # Responses should be identical
    assert data1 == data2


def test_request_review_idempotency(reset_db):
    """Test that /v1/actions/request-review returns same response for repeated requests."""
    idempotency_key = f"review-key-{uuid.uuid4()}"

    request_body = {
        "repo": "test/repo",
        "pr_number": 123,
        "reviewers": ["alice", "bob"],
        "idempotency_key": idempotency_key,
    }

    # First request
    response1 = client.post("/v1/actions/request-review", json=request_body)
    assert response1.status_code == 200
    data1 = response1.json()

    # Second request with same idempotency key
    response2 = client.post("/v1/actions/request-review", json=request_body)
    assert response2.status_code == 200
    data2 = response2.json()

    # Responses should be identical
    assert data1 == data2
    assert data1["ok"] == data2["ok"]
    assert data1["message"] == data2["message"]


def test_request_review_idempotency_persists_across_memory_clear(reset_db):
    """Test that request-review idempotency persists even if in-memory cache is cleared."""
    from handsfree.api import idempotency_store

    idempotency_key = f"review-key-{uuid.uuid4()}"

    request_body = {
        "repo": "test/repo",
        "pr_number": 456,
        "reviewers": ["charlie"],
        "idempotency_key": idempotency_key,
    }

    # First request
    response1 = client.post("/v1/actions/request-review", json=request_body)
    assert response1.status_code == 200
    data1 = response1.json()

    # Clear in-memory cache
    idempotency_store.clear()

    # Second request should still return cached response from database
    response2 = client.post("/v1/actions/request-review", json=request_body)
    assert response2.status_code == 200
    data2 = response2.json()

    # Responses should be identical
    assert data1 == data2


def test_confirm_endpoint_idempotency(reset_db):
    """Test that /v1/commands/confirm returns same response for repeated confirmations."""
    from handsfree.api import get_db
    from handsfree.db.pending_actions import create_pending_action

    db = get_db()
    user_id = "00000000-0000-0000-0000-000000000001"

    # Create a pending action
    pending_action = create_pending_action(
        db,
        user_id=user_id,
        summary="Test action",
        action_type="request_review",
        action_payload={
            "repo": "test/repo",
            "pr_number": 789,
            "reviewers": ["dave"],
        },
        expires_in_seconds=300,
    )

    idempotency_key = f"confirm-key-{uuid.uuid4()}"

    # First confirmation request
    response1 = client.post(
        "/v1/commands/confirm",
        json={
            "token": pending_action.token,
            "idempotency_key": idempotency_key,
        },
    )
    assert response1.status_code == 200
    data1 = response1.json()

    # Second confirmation with same idempotency key should return cached response
    # (even though the pending action is already consumed)
    response2 = client.post(
        "/v1/commands/confirm",
        json={
            "token": pending_action.token,
            "idempotency_key": idempotency_key,
        },
    )
    assert response2.status_code == 200
    data2 = response2.json()

    # Responses should be identical
    assert data1 == data2
    assert data1["status"] == data2["status"]


def test_confirm_without_idempotency_key_prevents_double_execution(reset_db):
    """Test that confirming without idempotency key still prevents double execution."""
    from handsfree.api import get_db
    from handsfree.db.pending_actions import create_pending_action

    db = get_db()
    user_id = "00000000-0000-0000-0000-000000000001"

    # Create a pending action
    pending_action = create_pending_action(
        db,
        user_id=user_id,
        summary="Test action",
        action_type="request_review",
        action_payload={
            "repo": "test/repo",
            "pr_number": 999,
            "reviewers": ["eve"],
        },
        expires_in_seconds=300,
    )

    # First confirmation (no idempotency key)
    response1 = client.post(
        "/v1/commands/confirm",
        json={"token": pending_action.token},
    )
    assert response1.status_code == 200

    # Second confirmation with same token should fail (action already consumed)
    response2 = client.post(
        "/v1/commands/confirm",
        json={"token": pending_action.token},
    )
    assert response2.status_code == 404
    data2 = response2.json()
    assert data2["error"] == "not_found"


def test_idempotency_keys_linked_to_audit_logs(reset_db):
    """Test that idempotency keys are properly linked to audit log entries."""
    from handsfree.api import get_db
    from handsfree.db.idempotency_keys import get_idempotency_key

    idempotency_key = f"audit-link-{uuid.uuid4()}"

    request_body = {
        "repo": "test/repo",
        "pr_number": 111,
        "reviewers": ["frank"],
        "idempotency_key": idempotency_key,
    }

    # Make request
    response = client.post("/v1/actions/request-review", json=request_body)
    assert response.status_code == 200

    # Check that idempotency key is linked to audit log
    db = get_db()
    idem_key = get_idempotency_key(db, idempotency_key)
    assert idem_key is not None
    # Should have audit_log_id if action was executed
    # (may be None if action requires confirmation)
    if idem_key.response_data.get("ok"):
        assert idem_key.audit_log_id is not None


def test_rerun_checks_idempotency(reset_db):
    """Test that /v1/actions/rerun-checks supports idempotency."""
    idempotency_key = f"rerun-key-{uuid.uuid4()}"

    request_body = {
        "repo": "test/repo",
        "pr_number": 222,
        "idempotency_key": idempotency_key,
    }

    # First request
    response1 = client.post("/v1/actions/rerun-checks", json=request_body)
    assert response1.status_code == 200
    data1 = response1.json()

    # Second request with same idempotency key
    response2 = client.post("/v1/actions/rerun-checks", json=request_body)
    assert response2.status_code == 200
    data2 = response2.json()

    # Responses should be identical
    assert data1 == data2


def test_merge_idempotency(reset_db):
    """Test that /v1/actions/merge supports idempotency."""
    idempotency_key = f"merge-key-{uuid.uuid4()}"

    request_body = {
        "repo": "test/repo",
        "pr_number": 333,
        "idempotency_key": idempotency_key,
    }

    # First request
    response1 = client.post("/v1/actions/merge", json=request_body)
    assert response1.status_code == 200
    data1 = response1.json()

    # Second request with same idempotency key
    response2 = client.post("/v1/actions/merge", json=request_body)
    assert response2.status_code == 200
    data2 = response2.json()

    # Responses should be identical
    assert data1 == data2
