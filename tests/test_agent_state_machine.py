"""Tests for agent task state transition endpoints and runner."""

import os
import uuid

import pytest

from handsfree.agents.service import AgentService
from handsfree.db import init_db
from handsfree.db.agent_tasks import (
    create_agent_task,
    get_agent_task_by_id,
    update_agent_task_state,
)
from handsfree.db.notifications import list_notifications


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    # Set env var for testing
    os.environ["DUCKDB_PATH"] = ":memory:"
    os.environ["HANDSFREE_AUTH_MODE"] = "dev"
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def agent_service(db_conn):
    """Create agent service with test database."""
    return AgentService(db_conn)


class TestAgentTaskStateEndpoints:
    """Test dev-only agent task state transition endpoints via AgentService."""

    def test_start_task_success(self, agent_service, db_conn, test_user_id):
        """Test successful task start transition."""
        # Create a task in 'created' state
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        # Start the task via service
        result = agent_service.advance_task_state(
            task_id=task.id,
            new_state="running",
            trace_update={
                "started_at": "2024-01-15T10:00:00Z",
                "started_via": "api_endpoint",
            },
        )

        assert result["task_id"] == task.id
        assert result["state"] == "running"
        assert "updated_at" in result

        # Verify task state in database
        updated_task = get_agent_task_by_id(conn=db_conn, task_id=task.id)
        assert updated_task.state == "running"
        assert updated_task.trace is not None
        assert "started_at" in updated_task.trace
        assert updated_task.trace["started_via"] == "api_endpoint"

    def test_start_task_invalid_transition(self, agent_service, db_conn, test_user_id):
        """Test starting a task that's already completed."""
        # Create and complete a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="completed")

        # Try to start it (should fail)
        with pytest.raises(ValueError, match="Invalid state transition"):
            agent_service.advance_task_state(
                task_id=task.id,
                new_state="running",
            )

    def test_start_task_not_found(self, agent_service):
        """Test starting a non-existent task."""
        fake_id = str(uuid.uuid4())
        with pytest.raises(ValueError, match="not found"):
            agent_service.advance_task_state(
                task_id=fake_id,
                new_state="running",
            )

    def test_complete_task_success(self, agent_service, db_conn, test_user_id):
        """Test successful task completion transition."""
        # Create and start a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        # Complete the task via service
        result = agent_service.advance_task_state(
            task_id=task.id,
            new_state="completed",
            trace_update={
                "completed_at": "2024-01-15T11:00:00Z",
                "completed_via": "api_endpoint",
                "pr_url": None,  # Placeholder for PR link
            },
        )

        assert result["task_id"] == task.id
        assert result["state"] == "completed"
        assert "updated_at" in result

        # Verify task state in database
        updated_task = get_agent_task_by_id(conn=db_conn, task_id=task.id)
        assert updated_task.state == "completed"
        assert updated_task.trace is not None
        assert "completed_at" in updated_task.trace
        assert "pr_url" in updated_task.trace

    def test_complete_task_creates_notification(self, agent_service, db_conn, test_user_id):
        """Test that completing a task creates a notification."""
        # Create and start a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        # Complete the task
        result = agent_service.advance_task_state(
            task_id=task.id,
            new_state="completed",
        )

        assert result["state"] == "completed"

        # Check that notification was created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        completion_notifications = [n for n in notifications if n.event_type == "task_completed"]

        assert len(completion_notifications) > 0
        assert completion_notifications[0].metadata["task_id"] == task.id

    def test_fail_task_success(self, agent_service, db_conn, test_user_id):
        """Test successful task failure transition."""
        # Create and start a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        # Fail the task via service
        result = agent_service.advance_task_state(
            task_id=task.id,
            new_state="failed",
            trace_update={
                "failed_at": "2024-01-15T11:30:00Z",
                "failed_via": "api_endpoint",
                "error": "Task failed via dev endpoint",
            },
        )

        assert result["task_id"] == task.id
        assert result["state"] == "failed"

        # Verify task state in database
        updated_task = get_agent_task_by_id(conn=db_conn, task_id=task.id)
        assert updated_task.state == "failed"
        assert updated_task.trace is not None
        assert "failed_at" in updated_task.trace
        assert "error" in updated_task.trace

    def test_fail_task_creates_notification(self, agent_service, db_conn, test_user_id):
        """Test that failing a task creates a notification."""
        # Create and start a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        # Fail the task
        result = agent_service.advance_task_state(
            task_id=task.id,
            new_state="failed",
        )

        assert result["state"] == "failed"

        # Check that notification was created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        failure_notifications = [n for n in notifications if n.event_type == "task_failed"]

        assert len(failure_notifications) > 0
        assert failure_notifications[0].metadata["task_id"] == task.id


class TestAgentRunner:
    """Test agent runner loop functionality."""

    def test_runner_enabled_check(self):
        """Test runner enabled environment variable check."""
        from handsfree.agents.runner import is_runner_enabled

        # Test disabled (default)
        os.environ.pop("HANDSFREE_AGENT_RUNNER_ENABLED", None)
        assert not is_runner_enabled()

        # Test enabled
        os.environ["HANDSFREE_AGENT_RUNNER_ENABLED"] = "true"
        assert is_runner_enabled()

        # Test case insensitivity
        os.environ["HANDSFREE_AGENT_RUNNER_ENABLED"] = "TRUE"
        assert is_runner_enabled()

        # Test invalid value
        os.environ["HANDSFREE_AGENT_RUNNER_ENABLED"] = "yes"
        assert not is_runner_enabled()

        # Clean up
        os.environ.pop("HANDSFREE_AGENT_RUNNER_ENABLED", None)

    def test_auto_start_created_tasks(self, db_conn, test_user_id):
        """Test auto-starting created tasks."""
        from handsfree.agents.runner import auto_start_created_tasks

        # Create multiple tasks in 'created' state
        task1 = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="task 1",
        )
        task2 = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="task 2",
        )

        # Create one task already running (should not be affected)
        task3 = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="task 3",
        )
        update_agent_task_state(conn=db_conn, task_id=task3.id, new_state="running")

        # Run auto-start
        count = auto_start_created_tasks(db_conn)

        # Should have started 2 tasks
        assert count == 2

        # Verify tasks are now running
        from handsfree.db.agent_tasks import get_agent_task_by_id

        updated_task1 = get_agent_task_by_id(conn=db_conn, task_id=task1.id)
        assert updated_task1.state == "running"
        assert "auto_started_at" in updated_task1.trace

        updated_task2 = get_agent_task_by_id(conn=db_conn, task_id=task2.id)
        assert updated_task2.state == "running"
        assert "auto_started_by" in updated_task2.trace
        assert updated_task2.trace["auto_started_by"] == "runner_loop"

    def test_simulate_progress_update(self, db_conn, test_user_id):
        """Test simulating progress updates for running tasks."""
        from handsfree.agents.runner import simulate_progress_update

        # Create and start a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        # Simulate progress update
        success = simulate_progress_update(
            conn=db_conn,
            task_id=task.id,
            progress_message="Processing step 1 of 5",
        )

        assert success

        # Verify trace was updated
        from handsfree.db.agent_tasks import get_agent_task_by_id

        updated_task = get_agent_task_by_id(conn=db_conn, task_id=task.id)
        assert updated_task.state == "running"  # Still running
        assert updated_task.trace["progress"] == "Processing step 1 of 5"
        assert "last_progress_at" in updated_task.trace

    def test_simulate_progress_update_non_running_task(self, db_conn, test_user_id):
        """Test that progress updates only work for running tasks."""
        from handsfree.agents.runner import simulate_progress_update

        # Create a task in 'created' state
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        # Try to update progress (should fail)
        success = simulate_progress_update(
            conn=db_conn,
            task_id=task.id,
            progress_message="This should not work",
        )

        assert not success

    def test_run_once_when_disabled(self, db_conn):
        """Test run_once when runner is disabled."""
        from handsfree.agents.runner import run_once

        os.environ.pop("HANDSFREE_AGENT_RUNNER_ENABLED", None)

        result = run_once(db_conn)

        assert not result["enabled"]
        assert result["tasks_started"] == 0
        assert "disabled" in result["message"].lower()

    def test_run_once_when_enabled(self, db_conn, test_user_id):
        """Test run_once when runner is enabled."""
        from handsfree.agents.runner import run_once

        os.environ["HANDSFREE_AGENT_RUNNER_ENABLED"] = "true"

        # Create some tasks
        create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="task 1",
        )
        create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="task 2",
        )

        result = run_once(db_conn)

        assert result["enabled"]
        assert result["tasks_started"] == 2
        assert "timestamp" in result

        # Clean up
        os.environ.pop("HANDSFREE_AGENT_RUNNER_ENABLED", None)


class TestTraceRequirements:
    """Test that trace stores required information."""

    def test_trace_stores_transcript(self, db_conn, test_user_id):
        """Test that trace can store original transcript."""
        from datetime import UTC, datetime

        trace = {
            "transcript": "fix the bug in issue 123",
            "created_at": datetime.now(UTC).isoformat(),
        }

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="fix the bug",
            trace=trace,
        )

        from handsfree.db.agent_tasks import get_agent_task_by_id

        retrieved_task = get_agent_task_by_id(conn=db_conn, task_id=task.id)
        assert retrieved_task.trace["transcript"] == "fix the bug in issue 123"

    def test_trace_stores_intent_and_entities(self, db_conn, test_user_id):
        """Test that trace can store parsed intent and entities."""
        trace = {
            "intent_name": "agent.delegate",
            "entities": {
                "instruction": "fix bug",
                "issue_number": 123,
            },
        }

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="fix bug",
            trace=trace,
        )

        from handsfree.db.agent_tasks import get_agent_task_by_id

        retrieved_task = get_agent_task_by_id(conn=db_conn, task_id=task.id)
        assert retrieved_task.trace["intent_name"] == "agent.delegate"
        assert retrieved_task.trace["entities"]["issue_number"] == 123

    def test_trace_stores_timestamps(self, db_conn, test_user_id):
        """Test that trace stores timestamps."""
        from datetime import UTC, datetime

        now = datetime.now(UTC).isoformat()
        trace = {
            "created_at": now,
        }

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test",
            trace=trace,
        )

        # Add more timestamps via state updates
        task = update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={
                "started_at": datetime.now(UTC).isoformat(),
            },
        )

        from handsfree.db.agent_tasks import get_agent_task_by_id

        retrieved_task = get_agent_task_by_id(conn=db_conn, task_id=task.id)
        assert "created_at" in retrieved_task.trace
        assert "started_at" in retrieved_task.trace

    def test_trace_stores_pr_url_placeholder(self, db_conn, test_user_id):
        """Test that trace can store PR URL placeholder."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test",
        )

        # Transition to running then completed with PR URL
        task = update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
        )

        task = update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "pr_url": "https://github.com/owner/repo/pull/123",
                "pr_number": 123,
                "repo_full_name": "owner/repo",
            },
        )

        from handsfree.db.agent_tasks import get_agent_task_by_id

        retrieved_task = get_agent_task_by_id(conn=db_conn, task_id=task.id)
        assert retrieved_task.trace["pr_url"] == "https://github.com/owner/repo/pull/123"
        assert retrieved_task.trace["pr_number"] == 123
