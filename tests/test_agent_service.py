"""Tests for agent service."""


import pytest

from handsfree.agents.service import AgentService
from handsfree.db import init_db
from handsfree.db.agent_tasks import get_agent_tasks, update_agent_task_state


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def agent_service(db_conn):
    """Create an agent service with test database."""
    return AgentService(db_conn)


class TestAgentDelegate:
    """Test agent delegation."""

    def test_delegate_basic_task(self, agent_service, db_conn, test_user_id):
        """Test delegating a basic task."""
        result = agent_service.delegate(
            user_id=test_user_id, instruction="fix the bug", provider="copilot"
        )

        assert "task_id" in result
        assert result["state"] == "created"
        assert "spoken_text" in result

        # Verify task was created in DB
        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)
        assert len(tasks) == 1
        assert tasks[0].instruction == "fix the bug"
        assert tasks[0].provider == "copilot"

    def test_delegate_with_issue_target(self, agent_service, db_conn, test_user_id):
        """Test delegating with issue target."""
        result = agent_service.delegate(
            user_id=test_user_id,
            instruction="handle issue",
            provider="copilot",
            target_type="issue",
            target_ref="owner/repo#42",
        )

        assert result["state"] == "created"
        assert "issue" in result["spoken_text"].lower()
        assert "42" in result["spoken_text"]

        # Verify target info
        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)
        assert tasks[0].target_type == "issue"
        assert tasks[0].target_ref == "owner/repo#42"

    def test_delegate_with_pr_target(self, agent_service, db_conn, test_user_id):
        """Test delegating with PR target."""
        result = agent_service.delegate(
            user_id=test_user_id,
            instruction="review pr",
            provider="copilot",
            target_type="pr",
            target_ref="owner/repo#99",
        )

        assert result["state"] == "created"
        assert "pr" in result["spoken_text"].lower()
        assert "99" in result["spoken_text"]

    def test_delegate_trace_added(self, agent_service, db_conn, test_user_id):
        """Test that delegation adds trace information."""
        agent_service.delegate(
            user_id=test_user_id, instruction="test task", provider="mock"
        )

        # Verify trace in DB
        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)
        assert tasks[0].trace is not None
        assert "created_via" in tasks[0].trace


class TestAgentStatus:
    """Test agent status queries."""

    def test_status_no_tasks(self, agent_service, test_user_id):
        """Test status when no tasks exist."""
        result = agent_service.get_status(user_id=test_user_id)

        assert result["total"] == 0
        assert result["by_state"] == {}
        assert "no agent tasks" in result["spoken_text"].lower()

    def test_status_single_task(self, agent_service, db_conn, test_user_id):
        """Test status with a single task."""
        agent_service.delegate(user_id=test_user_id, instruction="test", provider="mock")

        result = agent_service.get_status(user_id=test_user_id)

        assert result["total"] == 1
        assert result["by_state"]["created"] == 1
        assert "1 task" in result["spoken_text"]
        assert "created" in result["spoken_text"]

    def test_status_multiple_tasks(self, agent_service, db_conn, test_user_id):
        """Test status with multiple tasks in different states."""
        # Create tasks
        task1 = agent_service.delegate(user_id=test_user_id, instruction="task1", provider="mock")
        task2 = agent_service.delegate(user_id=test_user_id, instruction="task2", provider="mock")
        agent_service.delegate(user_id=test_user_id, instruction="task3", provider="mock")

        # Advance some states
        update_agent_task_state(conn=db_conn, task_id=task1["task_id"], new_state="running")
        update_agent_task_state(conn=db_conn, task_id=task2["task_id"], new_state="running")
        update_agent_task_state(conn=db_conn, task_id=task2["task_id"], new_state="completed")

        result = agent_service.get_status(user_id=test_user_id)

        assert result["total"] == 3
        assert result["by_state"]["running"] == 1
        assert result["by_state"]["completed"] == 1
        assert result["by_state"]["created"] == 1
        assert "3 tasks" in result["spoken_text"]

    def test_status_returns_recent_tasks(self, agent_service, db_conn, test_user_id):
        """Test that status returns up to 10 recent tasks."""
        # Create 15 tasks
        for i in range(15):
            agent_service.delegate(user_id=test_user_id, instruction=f"task {i}", provider="mock")

        result = agent_service.get_status(user_id=test_user_id)

        assert result["total"] == 15
        # Should return only 10 most recent
        assert len(result["tasks"]) == 10

    def test_status_filters_by_user(self, agent_service, test_user_id, test_user_id_2):
        """Test that status filters by user."""
        agent_service.delegate(user_id=test_user_id, instruction="task1", provider="mock")
        agent_service.delegate(user_id=test_user_id_2, instruction="task2", provider="mock")
        agent_service.delegate(user_id=test_user_id, instruction="task3", provider="mock")

        result = agent_service.get_status(user_id=test_user_id)

        assert result["total"] == 2
        assert all(t["id"] for t in result["tasks"])  # Has task IDs


class TestAdvanceTaskState:
    """Test advancing task states via service."""

    def test_advance_task_success(self, agent_service, db_conn, test_user_id):
        """Test successfully advancing a task."""
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        result = agent_service.advance_task_state(task_id, "running")

        assert result["task_id"] == task_id
        assert result["state"] == "running"
        assert "updated_at" in result

    def test_advance_task_with_trace(self, agent_service, db_conn, test_user_id):
        """Test advancing task with trace update."""
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        result = agent_service.advance_task_state(
            task_id, "running", trace_update={"step": "processing"}
        )

        assert result["state"] == "running"

        # Verify trace was updated
        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)
        assert tasks[0].trace is not None
        assert "step" in tasks[0].trace

    def test_advance_nonexistent_task(self, agent_service):
        """Test advancing a nonexistent task."""
        with pytest.raises(ValueError, match="not found"):
            agent_service.advance_task_state("nonexistent", "running")

    def test_advance_invalid_transition(self, agent_service, test_user_id):
        """Test advancing with invalid state transition."""
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        with pytest.raises(ValueError, match="Invalid state transition"):
            agent_service.advance_task_state(task_id, "completed")


class TestNotifications:
    """Test notification emission (placeholder)."""

    def test_notification_on_task_creation(self, agent_service, capsys, test_user_id):
        """Test that notification is emitted on task creation."""
        agent_service.delegate(user_id=test_user_id, instruction="test", provider="mock")

        # Capture stdout to verify notification was logged
        captured = capsys.readouterr()
        assert "NOTIFICATION" in captured.out
        assert "task_created" in captured.out

    def test_notification_on_state_change(self, agent_service, capsys, test_user_id):
        """Test that notification is emitted on state change."""
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        agent_service.advance_task_state(task_id, "running")

        captured = capsys.readouterr()
        assert "NOTIFICATION" in captured.out
        assert "state_changed" in captured.out
