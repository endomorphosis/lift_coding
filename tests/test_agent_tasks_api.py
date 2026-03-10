"""Tests for agent tasks API endpoints."""

import uuid
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

from handsfree import api as api_module
from handsfree.api import app
from handsfree.db.agent_tasks import create_agent_task

client = TestClient(app)


@pytest.fixture
def reset_db():
    """Reset the database connection before each test."""
    api_module._db_conn = None
    yield
    api_module._db_conn = None


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def test_user_id_2():
    """Generate a second test user ID."""
    return str(uuid.UUID("87654321-4321-4321-4321-210987654321"))


class TestListAgentTasks:
    """Test GET /v1/agents/tasks endpoint."""

    def test_list_tasks_empty(self, reset_db):
        """Test listing tasks when none exist."""
        response = client.get("/v1/agents/tasks")
        assert response.status_code == 200

        data = response.json()
        assert "tasks" in data
        assert "pagination" in data
        assert data["tasks"] == []
        assert data["pagination"]["limit"] == 100
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["has_more"] is False

    def test_list_tasks_basic(self, reset_db):
        """Test listing basic tasks."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()

        # Create some tasks
        task1 = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Fix bug #1",
        )
        task2 = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Fix bug #2",
        )

        response = client.get("/v1/agents/tasks")
        assert response.status_code == 200

        data = response.json()
        assert len(data["tasks"]) == 2

        # Tasks should be ordered by created_at DESC (newest first)
        assert data["tasks"][0]["id"] == task2.id
        assert data["tasks"][1]["id"] == task1.id

        # Check task structure
        for task_data in data["tasks"]:
            assert "id" in task_data
            assert "state" in task_data
            assert "description" in task_data
            assert "created_at" in task_data
            assert "updated_at" in task_data

    def test_list_tasks_user_scoping(self, reset_db, test_user_id, test_user_id_2):
        """Test that users can only see their own tasks."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()

        # Create tasks for different users
        task1 = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="User 1 task",
        )
        create_agent_task(
            conn=db,
            user_id=test_user_id_2,
            provider="copilot",
            instruction="User 2 task",
        )

        # Request as FIXTURE_USER_ID (default in dev mode)
        response = client.get("/v1/agents/tasks")
        assert response.status_code == 200

        data = response.json()
        # Should only see user 1's task
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == task1.id

    def test_list_tasks_filter_by_status(self, reset_db):
        """Test filtering tasks by status."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()

        # Create tasks with different states
        task1 = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Task 1",
        )
        task2 = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Task 2",
        )

        # Advance task1 to running
        update_agent_task_state(conn=db, task_id=task1.id, new_state="running")

        # Filter for created tasks only
        response = client.get("/v1/agents/tasks?status=created")
        assert response.status_code == 200

        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == task2.id
        assert data["tasks"][0]["state"] == "created"

        # Filter for running tasks only
        response = client.get("/v1/agents/tasks?status=running")
        assert response.status_code == 200

        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == task1.id
        assert data["tasks"][0]["state"] == "running"

    def test_list_tasks_pagination_limit(self, reset_db):
        """Test pagination with limit parameter."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()

        # Create 5 tasks
        for i in range(5):
            create_agent_task(
                conn=db,
                user_id=FIXTURE_USER_ID,
                provider="copilot",
                instruction=f"Task {i}",
            )

        # Request with limit=2
        response = client.get("/v1/agents/tasks?limit=2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["tasks"]) == 2
        assert data["pagination"]["limit"] == 2
        assert data["pagination"]["offset"] == 0
        assert data["pagination"]["has_more"] is True

    def test_list_tasks_pagination_offset(self, reset_db):
        """Test pagination with offset parameter."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()

        # Create 5 tasks
        task_ids = []
        for i in range(5):
            task = create_agent_task(
                conn=db,
                user_id=FIXTURE_USER_ID,
                provider="copilot",
                instruction=f"Task {i}",
            )
            task_ids.append(task.id)

        # Get first page
        response = client.get("/v1/agents/tasks?limit=2&offset=0")
        assert response.status_code == 200
        page1 = response.json()
        assert len(page1["tasks"]) == 2

        # Get second page
        response = client.get("/v1/agents/tasks?limit=2&offset=2")
        assert response.status_code == 200
        page2 = response.json()
        assert len(page2["tasks"]) == 2

        # Get third page
        response = client.get("/v1/agents/tasks?limit=2&offset=4")
        assert response.status_code == 200
        page3 = response.json()
        assert len(page3["tasks"]) == 1
        assert page3["pagination"]["has_more"] is False

        # Ensure no overlap between pages
        page1_ids = {t["id"] for t in page1["tasks"]}
        page2_ids = {t["id"] for t in page2["tasks"]}
        page3_ids = {t["id"] for t in page3["tasks"]}
        assert len(page1_ids & page2_ids) == 0
        assert len(page1_ids & page3_ids) == 0
        assert len(page2_ids & page3_ids) == 0

    def test_list_tasks_with_pr_url(self, reset_db):
        """Test that pr_url from trace is included in response."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()

        # Create task with pr_url in trace
        _ = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Fix issue",
            trace={"pr_url": "https://github.com/owner/repo/pull/123"},
        )

        response = client.get("/v1/agents/tasks")
        assert response.status_code == 200

        data = response.json()
        assert len(data["tasks"]) == 1
        assert "pr_url" in data["tasks"][0]
        assert data["tasks"][0]["pr_url"] == "https://github.com/owner/repo/pull/123"

    def test_list_tasks_filter_by_provider(self, reset_db):
        """Provider filter should narrow task results."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()
        create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="Dataset task",
        )
        create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Copilot task",
        )

        response = client.get("/v1/agents/tasks?provider=ipfs_datasets_mcp")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["provider"] == "ipfs_datasets_mcp"
        assert data["filters"]["provider"] == "ipfs_datasets_mcp"

    def test_list_tasks_filter_by_capability(self, reset_db):
        """Capability filter should match MCP trace capability."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()
        create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="Find legal datasets",
            trace={"mcp_capability": "dataset_discovery"},
        )
        create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="Fetch a site",
            trace={"mcp_capability": "agentic_fetch"},
        )

        response = client.get("/v1/agents/tasks?capability=dataset_discovery")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["trace"]["mcp_capability"] == "dataset_discovery"
        assert data["filters"]["capability"] == "dataset_discovery"

    def test_list_tasks_result_view_normalized(self, reset_db):
        """Normalized result view should hide raw trace/output fields."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()
        create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="Find legal datasets",
            trace={
                "mcp_capability": "dataset_discovery",
                "mcp_result_preview": "Expanded legal query",
                "mcp_result_output": {
                    "message": "Expanded legal query",
                    "expanded_queries": ["legal datasets", "legal datasets statutes"],
                },
            },
        )

        response = client.get("/v1/agents/tasks?result_view=normalized")

        assert response.status_code == 200
        data = response.json()
        assert "result" in data["tasks"][0]
        assert "trace" not in data["tasks"][0]
        assert "result_output" not in data["tasks"][0]
        assert data["filters"]["result_view"] == "normalized"

    def test_list_tasks_result_view_raw(self, reset_db):
        """Raw result view should omit the normalized projection."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()
        create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="Find legal datasets",
            trace={
                "mcp_capability": "dataset_discovery",
                "mcp_result_preview": "Expanded legal query",
                "mcp_result_output": {
                    "message": "Expanded legal query",
                    "expanded_queries": ["legal datasets", "legal datasets statutes"],
                },
            },
        )

        response = client.get("/v1/agents/tasks?result_view=raw")

        assert response.status_code == 200
        data = response.json()
        assert "trace" in data["tasks"][0]
        assert "result_output" in data["tasks"][0]
        assert "result" not in data["tasks"][0]
        assert data["filters"]["result_view"] == "raw"

    def test_list_tasks_results_only(self, reset_db):
        """Results-only mode should return only completed MCP result tasks."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        task1 = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="Find legal datasets",
            trace={"mcp_capability": "dataset_discovery"},
        )
        task2 = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Normal completed task",
        )
        update_agent_task_state(conn=db, task_id=task1.id, new_state="running")
        update_agent_task_state(
            conn=db,
            task_id=task1.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Expanded legal query"},
        )
        update_agent_task_state(conn=db, task_id=task2.id, new_state="running")
        update_agent_task_state(conn=db, task_id=task2.id, new_state="completed")

        response = client.get("/v1/agents/tasks?results_only=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) == 1
        assert data["tasks"][0]["id"] == task1.id
        assert data["filters"]["results_only"] is True

    def test_list_tasks_sort_updated_at_asc(self, reset_db):
        """Sort controls should be forwarded into task ordering."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        older = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Older updated task",
        )
        newer = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="Newer updated task",
        )
        update_agent_task_state(conn=db, task_id=older.id, new_state="running")
        update_agent_task_state(conn=db, task_id=newer.id, new_state="running")

        response = client.get("/v1/agents/tasks?sort=updated_at&direction=asc")

        assert response.status_code == 200
        data = response.json()
        assert data["tasks"][0]["id"] == older.id
        assert data["tasks"][1]["id"] == newer.id
        assert data["filters"]["sort"] == "updated_at"
        assert data["filters"]["direction"] == "asc"

    def test_list_tasks_invalid_limit(self, reset_db):
        """Test error handling for invalid limit parameter."""
        # Limit too high
        response = client.get("/v1/agents/tasks?limit=101")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_parameter"

        # Limit too low
        response = client.get("/v1/agents/tasks?limit=0")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_parameter"

    def test_list_tasks_invalid_offset(self, reset_db):
        """Test error handling for invalid offset parameter."""
        # Negative offset
        response = client.get("/v1/agents/tasks?offset=-1")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_parameter"

    def test_list_tasks_invalid_result_view(self, reset_db):
        """Unknown result views should be rejected."""
        response = client.get("/v1/agents/tasks?result_view=weird")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_parameter"

    def test_list_tasks_invalid_sort(self, reset_db):
        """Unknown sort fields should be rejected."""
        response = client.get("/v1/agents/tasks?sort=weird")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_parameter"

    def test_list_tasks_invalid_direction(self, reset_db):
        """Unknown sort directions should be rejected."""
        response = client.get("/v1/agents/tasks?direction=sideways")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_parameter"

    def test_list_tasks_combined_filters(self, reset_db):
        """Test combining status filter with pagination."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()

        # Create 5 tasks
        tasks = []
        for i in range(5):
            task = create_agent_task(
                conn=db,
                user_id=FIXTURE_USER_ID,
                provider="copilot",
                instruction=f"Task {i}",
            )
            tasks.append(task)

        # Make 3 of them running
        for i in range(3):
            update_agent_task_state(conn=db, task_id=tasks[i].id, new_state="running")

        # Get running tasks with pagination
        response = client.get("/v1/agents/tasks?status=running&limit=2")
        assert response.status_code == 200

        data = response.json()
        assert len(data["tasks"]) == 2
        assert all(t["state"] == "running" for t in data["tasks"])
        assert data["pagination"]["has_more"] is True


class TestGetAgentTaskDetail:
    """Test GET /v1/agents/tasks/{task_id} endpoint."""

    def test_get_task_detail_success(self, reset_db):
        """Task detail should include MCP result data when present."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery"},
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

        response = client.get(f"/v1/agents/tasks/{task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == task.id
        assert data["provider"] == "ipfs_datasets_mcp"
        assert data["result_preview"] == "Expanded legal query"
        assert data["result_output"]["expanded_queries"][0] == "legal datasets"
        assert data["trace"]["mcp_capability"] == "dataset_discovery"
        assert data["result"]["capability"] == "dataset_discovery"
        assert data["result"]["dataset_queries"] == ["legal datasets", "legal datasets statutes"]
        assert data["result"]["message"] == "Expanded legal query"

    def test_get_task_detail_normalizes_ipfs_result(self, reset_db):
        """Task detail should expose CID-focused normalized result fields."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123 on ipfs",
            trace={
                "mcp_capability": "ipfs_pin",
                "mcp_cid": "bafy123",
                "mcp_pin_action": "pin",
            },
        )
        update_agent_task_state(conn=db, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Pinned bafy123",
                "mcp_result_output": {"message": "Pinned bafy123", "status": "success"},
            },
        )

        response = client.get(f"/v1/agents/tasks/{task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["capability"] == "ipfs_pin"
        assert data["result"]["cid"] == "bafy123"
        assert data["result"]["pin_action"] == "pin"
        assert data["result"]["message"] == "Pinned bafy123"

    def test_get_task_detail_exposes_result_envelope(self, reset_db):
        """Task detail should project envelope-backed result fields."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import create_agent_task

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123 on ipfs",
            trace={
                "mcp_capability": "ipfs_pin",
                "mcp_result_envelope": {
                    "provider": "ipfs_kit_mcp",
                    "server_family": "ipfs_kit",
                    "execution_mode": "direct_import",
                    "status": "completed",
                    "summary": "Pinned bafy123.",
                    "spoken_text": "Pinned bafy123.",
                    "structured_output": {"cid": "bafy123", "message": "Pinned bafy123."},
                    "artifact_refs": {"result_cid": "bafy123"},
                    "follow_up_actions": [{"id": "read_cid", "label": "Read CID"}],
                },
            },
        )

        response = client.get(f"/v1/agents/tasks/{task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["result_preview"] == "Pinned bafy123."
        assert data["result_output"]["cid"] == "bafy123"
        assert data["result_envelope"]["execution_mode"] == "direct_import"
        assert data["follow_up_actions"][0]["id"] == "read_cid"
        assert data["result"]["artifact_refs"]["result_cid"] == "bafy123"

    def test_get_task_detail_exposes_runtime_metadata(self, reset_db):
        """Task detail should surface MCP runtime timing metadata."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import create_agent_task

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="inspect connected wearable",
            trace={
                "mcp_capability": "workflow",
                "mcp_started_at": "2026-03-09T00:00:00+00:00",
                "mcp_timeout_s": 30.0,
                "mcp_poll_interval_s": 2.0,
                "mcp_result_envelope": {
                    "provider": "ipfs_accelerate_mcp",
                    "server_family": "ipfs_accelerate",
                    "execution_mode": "mcp_remote",
                    "status": "running",
                    "summary": "Wearables bridge connectivity workflow running for Ray-Ban Meta.",
                    "spoken_text": "Wearables bridge connectivity workflow running for Ray-Ban Meta.",
                    "structured_output": {"workflow": "wearables_bridge_connectivity"},
                    "follow_up_actions": [{"id": "agent_status", "label": "Check Task"}],
                },
            },
        )

        response = client.get(f"/v1/agents/tasks/{task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["mcp_started_at"] == "2026-03-09T00:00:00+00:00"
        assert data["mcp_timeout_s"] == 30.0
        assert data["mcp_poll_interval_s"] == 2.0
        assert isinstance(data["mcp_elapsed_s"], int)
        assert data["result"]["mcp_timeout_s"] == 30.0

    def test_get_task_detail_normalizes_agentic_fetch_result(self, reset_db):
        """Task detail should expose normalized fetch inputs and outputs."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="discover and fetch climate regulations from https://example.com",
            trace={
                "mcp_capability": "agentic_fetch",
                "mcp_seed_url": "https://example.com",
            },
        )
        update_agent_task_state(conn=db, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Agentic fetch complete",
                "mcp_result_output": {
                    "message": "Agentic fetch complete",
                    "status": "success",
                    "seed_urls": ["https://example.com"],
                    "target_terms": ["climate regulations"],
                },
            },
        )

        response = client.get(f"/v1/agents/tasks/{task.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["result"]["capability"] == "agentic_fetch"
        assert data["result"]["seed_urls"] == ["https://example.com"]
        assert data["result"]["target_terms"] == ["climate regulations"]
        assert data["result"]["message"] == "Agentic fetch complete"

    def test_get_task_detail_not_found_for_other_user(self, reset_db, test_user_id_2):
        """Task detail should be user scoped."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="hidden task",
        )

        response = client.get(
            f"/v1/agents/tasks/{task.id}",
            headers={"X-User-ID": test_user_id_2},
        )

        assert response.status_code == 404


class TestAgentTaskControls:
    """Test typed task lifecycle control endpoints."""

    def test_pause_resume_cancel_task_endpoints(self, reset_db):
        """Pause, resume, and cancel should work for the owning user."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import get_agent_task_by_id, update_agent_task_state

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="mock",
            instruction="long running task",
        )
        update_agent_task_state(conn=db, task_id=task.id, new_state="running")

        pause_response = client.post(f"/v1/agents/tasks/{task.id}/pause")
        assert pause_response.status_code == 200
        assert pause_response.json()["state"] == "needs_input"

        resume_response = client.post(f"/v1/agents/tasks/{task.id}/resume")
        assert resume_response.status_code == 200
        assert resume_response.json()["state"] == "running"

        cancel_response = client.post(f"/v1/agents/tasks/{task.id}/cancel")
        assert cancel_response.status_code == 200
        assert cancel_response.json()["state"] == "failed"

        updated_task = get_agent_task_by_id(conn=db, task_id=task.id)
        assert updated_task is not None
        assert updated_task.state == "failed"
        assert updated_task.trace["cancelled"] is True

    def test_task_control_endpoints_are_user_scoped(self, reset_db, test_user_id_2):
        """Lifecycle control endpoints should reject other users' tasks."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="mock",
            instruction="hidden task",
        )
        update_agent_task_state(conn=db, task_id=task.id, new_state="running")

        response = client.post(
            f"/v1/agents/tasks/{task.id}/pause",
            headers={"X-User-ID": test_user_id_2},
        )

        assert response.status_code == 404


class TestAgentTaskMediaAttach:
    """Test DAT media attachment endpoint for agent tasks."""

    def test_attach_media_updates_task_trace(self, reset_db):
        """Attaching DAT media should append attachment metadata to task trace."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import get_agent_task_by_id

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="inspect wearables bridge",
            trace={"client_context": {"feature": "wearables_bridge"}},
        )

        response = client.post(
            f"/v1/agents/tasks/{task.id}/media",
            json={
                "uri": "file:///tmp/uploaded-image.jpg",
                "media_kind": "image",
                "format": "jpg",
                "mime_type": "image/jpeg",
                "source_asset_uri": "file:///tmp/raw-image.jpg",
                "action": "capture_photo",
                "device_id": "AA:BB",
                "device_name": "Ray-Ban Meta",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["task_id"] == task.id
        assert body["media_count"] == 1
        assert body["media"]["uri"] == "file:///tmp/uploaded-image.jpg"
        assert body["media"]["device_name"] == "Ray-Ban Meta"

        updated_task = get_agent_task_by_id(conn=db, task_id=task.id)
        assert updated_task is not None
        assert updated_task.trace["wearables_dat_media_count"] == 1
        assert updated_task.trace["wearables_dat_latest_media"]["uri"] == "file:///tmp/uploaded-image.jpg"
        assert updated_task.trace["wearables_dat_media"][0]["media_kind"] == "image"

    def test_attach_media_is_user_scoped(self, reset_db, test_user_id_2):
        """Users should not be able to attach media to another user's task."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="inspect wearables bridge",
        )

        response = client.post(
            f"/v1/agents/tasks/{task.id}/media",
            headers={"X-User-ID": test_user_id_2},
            json={
                "uri": "file:///tmp/uploaded-image.jpg",
                "media_kind": "image",
            },
        )

        assert response.status_code == 404

    def test_attach_media_rejects_blank_uri(self, reset_db):
        """Attach endpoint should reject missing or blank uri values."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="inspect wearables bridge",
        )

        response = client.post(
            f"/v1/agents/tasks/{task.id}/media",
            json={
                "uri": "   ",
                "media_kind": "image",
            },
        )

        assert response.status_code == 400
        body = response.json()
        assert body["error"] == "invalid_request"
        assert body["message"] == "uri is required"

    def test_attach_media_normalizes_media_kind_case(self, reset_db):
        """Attach endpoint should normalize media_kind casing before persistence."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import get_agent_task_by_id

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="inspect wearables bridge",
        )

        response = client.post(
            f"/v1/agents/tasks/{task.id}/media",
            json={
                "uri": "file:///tmp/uploaded-audio.m4a",
                "media_kind": "AuDiO",
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["media"]["media_kind"] == "audio"

        updated_task = get_agent_task_by_id(conn=db, task_id=task.id)
        assert updated_task is not None
        assert updated_task.trace["wearables_dat_media"][0]["media_kind"] == "audio"


class TestListAgentResults:
    """Test GET /v1/agents/results endpoint."""

    def test_list_results_returns_only_completed_mcp_results(self, reset_db):
        """Results endpoint should exclude tasks without MCP result data."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        dataset_task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery"},
        )
        plain_task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="copilot",
            instruction="plain completed task",
        )
        update_agent_task_state(conn=db, task_id=dataset_task.id, new_state="running")
        update_agent_task_state(
            conn=db,
            task_id=dataset_task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Expanded legal query",
                "mcp_result_output": {
                    "message": "Expanded legal query",
                    "expanded_queries": ["legal datasets", "legal datasets statutes"],
                },
            },
        )
        update_agent_task_state(conn=db, task_id=plain_task.id, new_state="running")
        update_agent_task_state(conn=db, task_id=plain_task.id, new_state="completed")

        response = client.get("/v1/agents/results")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["task_id"] == dataset_task.id
        assert data["results"][0]["result"]["capability"] == "dataset_discovery"

    def test_list_results_supports_presets(self, reset_db):
        """Preset queries should resolve provider/capability combinations."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="discover and fetch climate regulations",
            trace={
                "mcp_capability": "agentic_fetch",
                "mcp_seed_url": "https://example.com",
            },
        )
        update_agent_task_state(conn=db, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Agentic fetch complete",
                "mcp_result_output": {
                    "message": "Agentic fetch complete",
                    "target_terms": ["climate regulations"],
                },
            },
        )

        response = client.get("/v1/agents/results?preset=agentic_fetches")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["filters"]["preset"] == "agentic_fetches"
        assert data["filters"]["provider"] == "ipfs_accelerate_mcp"
        assert data["filters"]["capability"] == "agentic_fetch"

    def test_list_results_supports_saved_view_alias(self, reset_db):
        """View aliases should resolve to stable result queries."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        task = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery"},
        )
        update_agent_task_state(conn=db, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Expanded legal query"},
        )

        response = client.get("/v1/agents/results?view=datasets")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["filters"]["view"] == "datasets"
        assert data["filters"]["preset"] == "dataset_discoveries"
        assert data["filters"]["latest_only"] is True
        assert data["filters"]["provider"] == "ipfs_datasets_mcp"
        assert data["filters"]["capability"] == "dataset_discovery"

    def test_list_results_latest_only_and_summary(self, reset_db):
        """Latest-only should reduce duplicates while summary reflects all filtered results."""
        from handsfree.api import get_db
        from handsfree.auth import FIXTURE_USER_ID
        from handsfree.db.agent_tasks import update_agent_task_state

        db = get_db()
        first = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="first discovery",
            trace={"mcp_capability": "dataset_discovery"},
        )
        second = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_datasets_mcp",
            instruction="second discovery",
            trace={"mcp_capability": "dataset_discovery"},
        )
        fetch = create_agent_task(
            conn=db,
            user_id=FIXTURE_USER_ID,
            provider="ipfs_accelerate_mcp",
            instruction="fetch result",
            trace={"mcp_capability": "agentic_fetch"},
        )
        for task in (first, second, fetch):
            update_agent_task_state(conn=db, task_id=task.id, new_state="running")
            update_agent_task_state(
                conn=db,
                task_id=task.id,
                new_state="completed",
                trace_update={"mcp_result_preview": f"done-{task.id[:6]}"},
            )

        response = client.get("/v1/agents/results?latest_only=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        assert {item["task_id"] for item in data["results"]} == {second.id, fetch.id}
        assert data["summary"]["total_results"] == 3
        assert data["summary"]["by_provider"]["ipfs_datasets_mcp"] == 2
        assert data["summary"]["by_capability"]["dataset_discovery"] == 2
        assert data["filters"]["latest_only"] is True

    def test_list_results_invalid_preset(self, reset_db):
        """Unknown presets should be rejected."""
        response = client.get("/v1/agents/results?preset=weird")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_parameter"

    def test_list_results_invalid_view(self, reset_db):
        """Unknown views should be rejected."""
        response = client.get("/v1/agents/results?view=weird")
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_parameter"
