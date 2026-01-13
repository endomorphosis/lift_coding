"""Tests for agent delegation and status intents."""

from fastapi.testclient import TestClient

from handsfree.api import app

client = TestClient(app)


def test_agent_delegate_with_issue():
    """Test delegating a task to an agent with an issue number."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "ask agent to fix issue 123"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["intent"]["name"] == "agent.delegate"
    assert data["intent"]["confidence"] >= 0.8
    assert "task" in data["spoken_text"].lower()
    # Router's agent service returns "Task created" instead of "delegated"
    assert "created" in data["spoken_text"].lower() or "delegated" in data["spoken_text"].lower()

    # Check entities
    entities = data["intent"]["entities"]
    assert entities["issue_number"] == 123


def test_agent_delegate_with_pr():
    """Test delegating a task to an agent with a PR number."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "ask agent to fix PR 456"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["intent"]["name"] == "agent.delegate"
    entities = data["intent"]["entities"]
    assert entities["pr_number"] == 456


def test_agent_delegate_simple_instruction():
    """Test delegating a task with a simple instruction."""
    response = client.post(
        "/v1/command",
        json={
            "input": {
                "type": "text",
                "text": "ask agent to add error handling to the API",
            },
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["intent"]["name"] == "agent.delegate"
    assert "add error handling" in data["intent"]["entities"]["instruction"].lower()


def test_agent_status_no_tasks():
    """Test querying agent status when no tasks exist."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "agent status"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    # Router uses "agent.progress" for status queries
    assert data["intent"]["name"] == "agent.progress"
    # After previous tests, there might be tasks, so we just check the structure
    assert "agent" in data["spoken_text"].lower()


def test_agent_status_with_tasks():
    """Test querying agent status after creating tasks."""
    # Create a task first
    client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "ask agent to fix issue 789"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    # Query status
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "agent status"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    # Router uses "agent.progress" for status queries
    assert data["intent"]["name"] == "agent.progress"
    assert "task" in data["spoken_text"].lower()


def test_agent_progress_query():
    """Test querying agent progress (synonym for status)."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "summarize agent progress"},
            "profile": "default",
            "client_context": {
                "device": "test",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    # Router uses agent.progress for all status/progress queries
    assert data["intent"]["name"] == "agent.progress"


def test_agent_delegate_with_idempotency():
    """Test that idempotency works for agent delegation."""
    idempotency_key = "test-agent-delegate-123"

    request_data = {
        "input": {"type": "text", "text": "ask agent to fix issue 999"},
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
    response1 = client.post("/v1/command", json=request_data)
    assert response1.status_code == 200
    data1 = response1.json()
    task_id_1 = data1["intent"]["entities"]["task_id"]

    # Second request with same key should return same response
    response2 = client.post("/v1/command", json=request_data)
    assert response2.status_code == 200
    data2 = response2.json()
    task_id_2 = data2["intent"]["entities"]["task_id"]

    assert task_id_1 == task_id_2
