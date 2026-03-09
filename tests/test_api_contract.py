"""Contract tests ensuring API responses match OpenAPI schema."""

import sys
import types

import pytest
from fastapi.testclient import TestClient

if "handsfree.secrets" not in sys.modules:
    secrets_module = types.ModuleType("handsfree.secrets")
    secrets_module.get_default_secret_manager = lambda: None
    secrets_module.get_secret_manager = lambda *args, **kwargs: None
    secrets_module.reset_secret_manager = lambda: None
    sys.modules["handsfree.secrets"] = secrets_module

from handsfree.agent_providers import IPFSAccelerateMCPAgentProvider
from handsfree.api import app
from handsfree.db.agent_tasks import create_agent_task, update_agent_task_state
from test_mcp_ipfs_provider import _FakeMCPClient

client = TestClient(app)


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    import handsfree.api as api_module

    api_module._db_conn = None
    api_module._command_router = None
    yield
    api_module._db_conn = None
    api_module._command_router = None


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
    """Test POST /v1/command with PR summarize (read-only operation)."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "summarize pr 123"},
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

    # pr.summarize is a read operation, should not require confirmation
    assert data["status"] == "ok"
    assert "intent" in data
    assert data["intent"]["name"] == "pr.summarize"
    assert "spoken_text" in data

    # Should have cards with PR details
    if "cards" in data and data["cards"]:
        assert isinstance(data["cards"], list)
        assert len(data["cards"]) > 0


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


def test_post_action_command_executes_card_action(reset_db) -> None:
    """Structured action endpoint should execute card actions directly from task_id context."""
    from handsfree.api import get_db
    from handsfree.db.agent_tasks import create_agent_task, update_agent_task_state

    db = get_db()
    user_id = "00000000-0000-0000-0000-000000000001"
    task = create_agent_task(
        conn=db,
        user_id=user_id,
        provider="ipfs_kit_mcp",
        instruction="add this file to ipfs",
        trace={"mcp_capability": "ipfs_add", "provider_label": "IPFS Kit", "mcp_cid": "bafy123"},
    )
    update_agent_task_state(conn=db, task_id=task.id, new_state="running")
    update_agent_task_state(
        conn=db,
        task_id=task.id,
        new_state="completed",
        trace_update={
            "mcp_result_preview": "Added to IPFS",
            "mcp_result_output": {"message": "Added to IPFS", "cid": "bafy123"},
        },
    )

    response = client.post(
        "/v1/commands/action",
        headers={"X-User-ID": user_id},
        json={
            "action_id": "show_result_details",
            "params": {"task_id": task.id},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["intent"]["name"] == "agent.result_details"


def test_post_action_command_rejects_unknown_action(reset_db) -> None:
    """Structured action endpoint should reject unsupported action IDs."""
    response = client.post(
        "/v1/commands/action",
        headers={"X-User-ID": "action-command-user-0000-0000-0000-000000000002"},
        json={
            "action_id": "unknown_action",
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 400
    detail = response.json()
    assert detail["error"] == "invalid_action_id"


def test_post_action_command_accepts_notification_context(reset_db) -> None:
    """Structured action endpoint should resolve result context from notification_id."""
    from handsfree.api import get_db
    from handsfree.db.agent_tasks import create_agent_task, update_agent_task_state
    from handsfree.db.notifications import create_notification

    db = get_db()
    user_id = "00000000-0000-0000-0000-000000000001"
    task = create_agent_task(
        conn=db,
        user_id=user_id,
        provider="ipfs_datasets_mcp",
        instruction="find legal datasets",
        trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
    )
    update_agent_task_state(conn=db, task_id=task.id, new_state="running")
    update_agent_task_state(
        conn=db,
        task_id=task.id,
        new_state="completed",
        trace_update={
            "mcp_result_preview": "Expanded legal query",
            "mcp_result_output": {
                "message": "Expanded legal query",
                "expanded_queries": ["legal datasets", "legal datasets statutes"],
            },
        },
    )
    notification = create_notification(
        conn=db,
        user_id=user_id,
        event_type="task_completed",
        message="Dataset task completed",
        metadata={
            "task_id": task.id,
            "state": "completed",
            "provider_label": "IPFS Datasets",
            "mcp_capability": "dataset_discovery",
            "instruction": "find legal datasets",
            "result_preview": "Expanded legal query",
            "result_output": {
                "message": "Expanded legal query",
                "expanded_queries": ["legal datasets", "legal datasets statutes"],
            },
        },
        priority=5,
    )
    assert notification is not None

    response = client.post(
        "/v1/commands/action",
        headers={"X-User-ID": user_id},
        json={
            "action_id": "show_result_details",
            "params": {"notification_id": notification.id},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["intent"]["name"] == "agent.result_details"
    assert data["cards"][0]["title"] == "IPFS Datasets details"


def test_post_action_command_accepts_embedded_card_context(reset_db) -> None:
    """Structured action endpoint should execute against an embedded cached card."""
    response = client.post(
        "/v1/commands/action",
        headers={"X-User-ID": "00000000-0000-0000-0000-000000000001"},
        json={
            "action_id": "share_cid",
            "params": {
                "card": {
                    "title": "IPFS Kit ipfs add",
                    "subtitle": "Task abc12345 • completed",
                    "lines": ["message: Added to IPFS"],
                    "deep_link": "ipfs://bafy123",
                    "task_id": "abc12345-0000-0000-0000-000000000000",
                    "provider": "ipfs_kit_mcp",
                    "capability": "ipfs_add",
                }
            },
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["intent"]["name"] == "agent.result_share"
    assert data["intent"]["entities"]["cid"] == "bafy123"


def test_post_action_command_accepts_mode_aware_result_action(reset_db) -> None:
    """Structured action endpoint should preserve explicit execution mode params."""
    response = client.post(
        "/v1/commands/action",
        headers={"X-User-ID": "00000000-0000-0000-0000-000000000001"},
        json={
            "action_id": "pin_result_local",
            "params": {
                "card": {
                    "title": "IPFS Kit ipfs pin",
                    "subtitle": "Task abc12345 • completed",
                    "lines": ["message: Pinned bafy123"],
                    "deep_link": "ipfs://bafy123",
                    "task_id": "abc12345-0000-0000-0000-000000000000",
                    "provider": "ipfs_kit_mcp",
                    "capability": "ipfs_pin",
                },
                "cid": "bafy123",
                "mcp_preferred_execution_mode": "direct_import",
            },
            "profile": "workout",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "needs_confirmation"
    assert data["intent"]["name"] == "agent.result_pin"
    assert data["intent"]["entities"]["mcp_preferred_execution_mode"] == "direct_import"


def test_openapi_includes_action_command_and_card_action_schema() -> None:
    """OpenAPI schema should expose structured action command and card action fields."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert "/v1/commands/action" in schema["paths"]
    assert "/v1/agents/tasks/{task_id}/pause" in schema["paths"]
    assert "/v1/agents/tasks/{task_id}/resume" in schema["paths"]
    assert "/v1/agents/tasks/{task_id}/cancel" in schema["paths"]
    command_examples = (
        schema["paths"]["/v1/command"]["post"]["responses"]["200"]["content"]["application/json"]["examples"]
    )
    assert command_examples["task_spawn"]["value"]["follow_on_task"]["summary"] == (
        "IPFS Accelerate agentic fetch running."
    )
    assert command_examples["needs_confirmation"]["value"]["pending_action"]["token"] == "conf-abc123xyz"
    action_examples = (
        schema["paths"]["/v1/commands/action"]["post"]["responses"]["200"]["content"]["application/json"]["examples"]
    )
    assert action_examples["task_spawn"]["value"]["intent"]["name"] == "agent.result_rerun"
    confirm_examples = (
        schema["paths"]["/v1/commands/confirm"]["post"]["responses"]["200"]["content"]["application/json"]["examples"]
    )
    assert confirm_examples["task_spawn"]["value"]["intent"]["name"] == "agent.delegate.confirmed"
    command_error_examples = (
        schema["paths"]["/v1/command"]["post"]["responses"]["400"]["content"]["application/json"]["examples"]
    )
    assert command_error_examples["invalid_request"]["value"]["error"] == "validation_error"
    action_error_examples = (
        schema["paths"]["/v1/commands/action"]["post"]["responses"]["400"]["content"]["application/json"]["examples"]
    )
    assert action_error_examples["invalid_action_id"]["value"]["error"] == "invalid_action_id"
    confirm_error_examples = (
        schema["paths"]["/v1/commands/confirm"]["post"]["responses"]["404"]["content"]["application/json"]["examples"]
    )
    assert confirm_error_examples["expired_pending_action"]["value"]["error"] == "expired"
    task_control = schema["components"]["schemas"]["AgentTaskControlResponse"]
    assert "task_id" in task_control["properties"]
    assert "state" in task_control["properties"]
    assert "message" in task_control["properties"]
    assert "updated_at" in task_control["properties"]
    action_request = schema["components"]["schemas"]["ActionCommandRequest"]
    assert "action_id" in action_request["properties"]
    command_response = schema["components"]["schemas"]["CommandResponse"]
    assert "follow_on_task" in command_response["properties"]
    assert command_response["example"]["follow_on_task"]["summary"] == (
        "IPFS Accelerate agentic fetch running."
    )
    assert command_response["examples"][1]["status"] == "needs_confirmation"
    assert command_response["examples"][1]["pending_action"]["token"] == "conf-abc123xyz"
    follow_on_task = schema["components"]["schemas"]["FollowOnTask"]
    assert "task_id" in follow_on_task["properties"]
    assert "provider_label" in follow_on_task["properties"]
    assert "capability" in follow_on_task["properties"]
    assert "summary" in follow_on_task["properties"]
    assert follow_on_task["example"]["provider_label"] == "IPFS Accelerate"
    ui_card = schema["components"]["schemas"]["UICard"]
    assert "actions" in ui_card["properties"]
    assert "action_items" in ui_card["properties"]
    action_item = schema["components"]["schemas"]["ActionItem"]
    assert "id" in action_item["properties"]
    assert "execution_mode" in action_item["properties"]
    assert "execution_mode_label" in action_item["properties"]


def test_agent_delegate_response_includes_follow_on_task() -> None:
    """Agent delegation responses should expose explicit follow-on task metadata."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "tell copilot to handle issue 42"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
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
    assert data["follow_on_task"]["task_id"]
    assert data["follow_on_task"]["state"] in {"created", "running", "completed"}
    assert data["follow_on_task"]["provider_label"]
    assert data["follow_on_task"]["summary"]


def test_action_response_includes_follow_on_task_for_rerun(reset_db, monkeypatch) -> None:
    """Structured result actions that spawn work should expose follow-on task metadata."""
    test_user_id = "00000000-0000-0000-0000-000000000001"
    monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_ACCELERATE_MCP", "true")
    fake_provider = IPFSAccelerateMCPAgentProvider(client=_FakeMCPClient())
    monkeypatch.setattr(
        "handsfree.agents.service.get_provider",
        lambda provider_name: fake_provider if provider_name == "ipfs_accelerate_mcp" else None,
    )

    import handsfree.api as api_module

    db = api_module.get_db()
    source_task = create_agent_task(
        conn=db,
        user_id=test_user_id,
        provider="ipfs_accelerate_mcp",
        instruction="discover and fetch climate regulations from https://example.com",
        trace={
            "mcp_capability": "agentic_fetch",
            "provider_label": "IPFS Accelerate",
            "mcp_input": "climate regulations",
            "mcp_seed_url": "https://example.com",
        },
    )
    update_agent_task_state(conn=db, task_id=source_task.id, new_state="running")
    update_agent_task_state(
        conn=db,
        task_id=source_task.id,
        new_state="completed",
        trace_update={
            "mcp_result_preview": "Agentic fetch started and completed",
            "mcp_result_output": {"message": "Agentic fetch started and completed"},
        },
    )

    response = client.post(
        "/v1/commands/action",
        headers={"X-User-ID": test_user_id},
        json={
            "action_id": "rerun_workflow",
            "params": {"task_id": source_task.id},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["intent"]["name"] == "agent.result_rerun"
    assert data["follow_on_task"]["task_id"]
    assert data["follow_on_task"]["task_id"] != source_task.id
    assert data["follow_on_task"]["provider"] == "ipfs_accelerate_mcp"
    assert data["follow_on_task"]["provider_label"] == "IPFS Accelerate"
    assert data["follow_on_task"]["capability"] == "agentic_fetch"
    assert data["follow_on_task"]["summary"] == (
        f"IPFS Accelerate agentic fetch {data['follow_on_task']['state']}."
    )


def test_post_confirm_valid_token() -> None:
    """Test POST /v1/commands/confirm with valid token."""
    # First, create a pending action using a side-effect intent (pr.request_review)
    # in workout profile which requires confirmation
    cmd_response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "request review from alice on pr 100"},
            "profile": "workout",
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
    assert cmd_data["status"] == "needs_confirmation"
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


def test_post_action_rerun_checks(reset_db) -> None:
    """Test POST /v1/actions/rerun-checks with real implementation."""
    # Create policy that allows rerun with confirmation (default behavior)
    from handsfree.api import get_db
    from handsfree.db.repo_policies import create_or_update_repo_policy

    db = get_db()
    create_or_update_repo_policy(
        db,
        user_id="00000000-0000-0000-0000-000000000001",
        repo_full_name="owner/repo",
        allow_rerun=True,
        require_confirmation=True,
    )

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
    # Real implementation should require confirmation by default
    assert data["ok"] is False
    assert "confirmation required" in data["message"].lower()


def test_post_action_merge() -> None:
    """Test POST /v1/actions/merge - now requires policy and confirmation."""
    response = client.post(
        "/v1/actions/merge",
        json={
            "repo": "owner/repo",
            "pr_number": 789,
            "merge_method": "squash",
        },
    )

    # By default, no policy is set, so merge should be denied
    assert response.status_code == 403
    data = response.json()

    # Validate error response
    assert "error" in data
    assert data["error"] == "policy_denied"
    assert "message" in data


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


def test_command_uses_intent_parser() -> None:
    """Test that /v1/command uses intent parser for parsing."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "what needs my attention"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Intent parser should recognize this as inbox.list
    assert data["intent"]["name"] == "inbox.list"
    assert data["intent"]["confidence"] > 0.5


def test_agent_status_via_router() -> None:
    """Test that agent status command goes through router."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "agent status"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Intent parser should recognize this as agent.status
    assert data["intent"]["name"] == "agent.status"
    assert data["status"] == "ok"


def test_agent_delegate_requires_confirmation_in_workout() -> None:
    """Test that agent.delegate requires confirmation in workout profile."""
    response = client.post(
        "/v1/command",
        json={
            "input": {"type": "text", "text": "ask agent to handle issue 42"},
            "profile": "workout",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    # Should require confirmation in workout profile
    assert data["status"] == "needs_confirmation"
    assert data["intent"]["name"] == "agent.delegate"
    assert "pending_action" in data
    assert "token" in data["pending_action"]


def test_session_support_via_header() -> None:
    """Test session support via X-Session-Id header."""
    session_id = "test-session-123"

    # First command with session
    response1 = client.post(
        "/v1/command",
        headers={"X-Session-Id": session_id},
        json={
            "input": {"type": "text", "text": "inbox"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response1.status_code == 200
    data1 = response1.json()
    original_text = data1["spoken_text"]

    # Repeat command with same session
    response2 = client.post(
        "/v1/command",
        headers={"X-Session-Id": session_id},
        json={
            "input": {"type": "text", "text": "repeat"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response2.status_code == 200
    data2 = response2.json()

    # Should return same spoken text
    assert data2["spoken_text"] == original_text


def test_session_isolation() -> None:
    """Test that different sessions have isolated histories."""
    # Session 1
    response1 = client.post(
        "/v1/command",
        headers={"X-Session-Id": "session-1"},
        json={
            "input": {"type": "text", "text": "inbox"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response1.status_code == 200

    # Session 2 - repeat should not see session 1's history
    response2 = client.post(
        "/v1/command",
        headers={"X-Session-Id": "session-2"},
        json={
            "input": {"type": "text", "text": "repeat"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response2.status_code == 200
    data2 = response2.json()

    # Should indicate nothing to repeat
    assert "nothing to repeat" in data2["spoken_text"].lower()


def test_repeat_preserves_follow_on_task(reset_db) -> None:
    """Session replay should preserve explicit follow_on_task metadata."""
    session_id = "repeat-follow-on-task-session"

    first = client.post(
        "/v1/command",
        headers={"X-Session-Id": session_id},
        json={
            "input": {"type": "text", "text": "tell copilot to handle issue 42"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert first.status_code == 200
    first_data = first.json()
    assert first_data["follow_on_task"]["task_id"]

    repeated = client.post(
        "/v1/command",
        headers={"X-Session-Id": session_id},
        json={
            "input": {"type": "text", "text": "repeat"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert repeated.status_code == 200
    repeated_data = repeated.json()
    assert repeated_data["follow_on_task"] == first_data["follow_on_task"]


def test_system_next_navigation() -> None:
    """Test system.next navigation through inbox items."""
    session_id = "test-nav-session"

    # Get inbox (should have multiple items)
    response1 = client.post(
        "/v1/command",
        headers={"X-Session-Id": session_id},
        json={
            "input": {"type": "text", "text": "inbox"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response1.status_code == 200
    data1 = response1.json()

    # Should have cards
    if "cards" in data1 and len(data1.get("cards", [])) > 1:
        # Next command should work
        response2 = client.post(
            "/v1/command",
            headers={"X-Session-Id": session_id},
            json={
                "input": {"type": "text", "text": "next"},
                "profile": "default",
                "client_context": {
                    "device": "simulator",
                    "locale": "en-US",
                    "timezone": "America/Los_Angeles",
                    "app_version": "0.1.0",
                },
            },
        )

        assert response2.status_code == 200
        data2 = response2.json()

        # Should have status ok
        assert data2["status"] == "ok"
        # Should have a single card (the next item)
        assert "cards" in data2
        assert len(data2["cards"]) == 1


def test_next_without_list() -> None:
    """Test next command without any list context."""
    response = client.post(
        "/v1/command",
        headers={"X-Session-Id": "new-session"},
        json={
            "input": {"type": "text", "text": "next"},
            "profile": "default",
            "client_context": {
                "device": "simulator",
                "locale": "en-US",
                "timezone": "America/Los_Angeles",
                "app_version": "0.1.0",
            },
        },
    )

    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert "no list" in data["spoken_text"].lower()


def test_list_agent_tasks_contract(reset_db) -> None:
    """Test GET /v1/agents/tasks matches OpenAPI contract."""
    response = client.get("/v1/agents/tasks")

    assert response.status_code == 200
    data = response.json()

    # Validate response structure per OpenAPI spec
    assert "tasks" in data
    assert "pagination" in data
    assert isinstance(data["tasks"], list)
    assert isinstance(data["pagination"], dict)

    # Validate pagination structure
    pagination = data["pagination"]
    assert "limit" in pagination
    assert "offset" in pagination
    assert "has_more" in pagination
    assert isinstance(pagination["limit"], int)
    assert isinstance(pagination["offset"], int)
    assert isinstance(pagination["has_more"], bool)

    # If there are tasks, validate task structure
    if data["tasks"]:
        for task in data["tasks"]:
            assert "id" in task
            assert "state" in task
            assert "description" in task
            assert "created_at" in task
            assert "updated_at" in task
            assert isinstance(task["id"], str)
            assert task["state"] in ["created", "running", "needs_input", "completed", "failed"]
            assert isinstance(task["description"], str)
            # pr_url is optional
            if "pr_url" in task:
                assert isinstance(task["pr_url"], str)


def test_list_agent_tasks_with_filters_contract(reset_db) -> None:
    """Test GET /v1/agents/tasks with filters matches OpenAPI contract."""
    # Test with status filter
    response = client.get("/v1/agents/tasks?status=created")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "pagination" in data

    # Test with pagination
    response = client.get("/v1/agents/tasks?limit=10&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert data["pagination"]["limit"] == 10
    assert data["pagination"]["offset"] == 0

    # Test with all filters combined
    response = client.get("/v1/agents/tasks?status=running&limit=5&offset=2")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert data["pagination"]["limit"] == 5
    assert data["pagination"]["offset"] == 2
    assert "filters" in data

    # Test MCP-specific filters
    response = client.get(
        "/v1/agents/tasks?provider=ipfs_datasets_mcp&capability=dataset_discovery&result_view=normalized"
    )
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data
    assert "filters" in data
    assert data["filters"]["provider"] == "ipfs_datasets_mcp"
    assert data["filters"]["capability"] == "dataset_discovery"
    assert data["filters"]["result_view"] == "normalized"
    assert "results_only" in data["filters"]
    assert "sort" in data["filters"]
    assert "direction" in data["filters"]


def test_list_agent_results_contract(reset_db) -> None:
    """Test GET /v1/agents/results basic contract."""
    response = client.get("/v1/agents/results?view=datasets")

    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "pagination" in data
    assert "summary" in data
    assert "filters" in data
    assert isinstance(data["results"], list)
    assert isinstance(data["pagination"], dict)
    assert isinstance(data["summary"], dict)
    assert isinstance(data["filters"], dict)
    assert data["filters"]["view"] == "datasets"
    assert data["filters"]["preset"] == "dataset_discoveries"
    assert data["filters"]["latest_only"] is True
