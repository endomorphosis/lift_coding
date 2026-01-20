"""Tests for agent tasks API endpoints."""

import uuid

import pytest
from fastapi.testclient import TestClient

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
