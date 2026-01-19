"""Tests for agent task runner module."""

import os
import uuid
from datetime import UTC, datetime, timedelta
from unittest import mock

import pytest

from handsfree.db import init_db
from handsfree.db.agent_tasks import create_agent_task, get_agent_task_by_id
from handsfree.db.notifications import list_notifications
from handsfree.agents.runner import (
    auto_start_created_tasks,
    get_task_completion_delay,
    is_runner_enabled,
    process_running_tasks,
    run_once,
    should_simulate_failure,
    simulate_progress_update,
)


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def test_user_id():
    """Generate a consistent test user ID."""
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def enable_runner():
    """Enable the agent runner for tests."""
    with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_RUNNER_ENABLED": "true"}):
        yield


@pytest.fixture
def disable_auto_push():
    """Disable auto-push for tests to avoid external dependencies."""
    with mock.patch.dict(os.environ, {"NOTIFICATIONS_AUTO_PUSH_ENABLED": "false"}):
        yield


class TestRunnerConfiguration:
    """Test runner configuration helpers."""

    def test_is_runner_enabled_default(self):
        """Test that runner is disabled by default."""
        with mock.patch.dict(os.environ, {}, clear=True):
            assert not is_runner_enabled()

    def test_is_runner_enabled_true(self):
        """Test that runner can be enabled."""
        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_RUNNER_ENABLED": "true"}):
            assert is_runner_enabled()

    def test_is_runner_enabled_false(self):
        """Test that runner can be explicitly disabled."""
        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_RUNNER_ENABLED": "false"}):
            assert not is_runner_enabled()

    def test_get_task_completion_delay_default(self):
        """Test default completion delay."""
        with mock.patch.dict(os.environ, {}, clear=True):
            assert get_task_completion_delay() == 10

    def test_get_task_completion_delay_custom(self):
        """Test custom completion delay."""
        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_TASK_COMPLETION_DELAY": "5"}):
            assert get_task_completion_delay() == 5

    def test_should_simulate_failure_default(self):
        """Test that failure simulation is disabled by default."""
        with mock.patch.dict(os.environ, {}, clear=True):
            assert not should_simulate_failure()

    def test_should_simulate_failure_true(self):
        """Test that failure simulation can be enabled."""
        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_SIMULATE_FAILURE": "true"}):
            assert should_simulate_failure()


class TestAutoStartCreatedTasks:
    """Test auto-starting created tasks."""

    def test_auto_start_single_task(self, db_conn, test_user_id, enable_runner, disable_auto_push):
        """Test auto-starting a single created task."""
        # Create a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )
        assert task.state == "created"

        # Auto-start tasks
        count = auto_start_created_tasks(db_conn)
        assert count == 1

        # Verify task state changed
        updated_task = get_agent_task_by_id(db_conn, task.id)
        assert updated_task.state == "running"
        assert updated_task.trace is not None
        assert "auto_started_at" in updated_task.trace
        assert "auto_started_by" in updated_task.trace
        assert updated_task.trace["auto_started_by"] == "runner_loop"

        # Verify notification was created
        notifications = list_notifications(db_conn, test_user_id)
        assert len(notifications) == 1
        assert notifications[0].event_type == "agent.task_started"
        # Task ID should be in the metadata
        assert notifications[0].metadata["task_id"] == task.id

    def test_auto_start_multiple_tasks(self, db_conn, test_user_id, enable_runner, disable_auto_push):
        """Test auto-starting multiple created tasks."""
        # Create multiple tasks
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

        # Auto-start tasks
        count = auto_start_created_tasks(db_conn)
        assert count == 2

        # Verify both tasks changed state
        updated_task1 = get_agent_task_by_id(db_conn, task1.id)
        updated_task2 = get_agent_task_by_id(db_conn, task2.id)
        assert updated_task1.state == "running"
        assert updated_task2.state == "running"

    def test_auto_start_no_tasks(self, db_conn, enable_runner):
        """Test auto-start with no created tasks."""
        count = auto_start_created_tasks(db_conn)
        assert count == 0

    def test_auto_start_ignores_running_tasks(self, db_conn, test_user_id, enable_runner, disable_auto_push):
        """Test that auto-start ignores already running tasks."""
        # Create and start a task manually
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        # Manually transition to running
        from handsfree.db.agent_tasks import update_agent_task_state
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={"manual": True},
        )

        # Auto-start should find no tasks
        count = auto_start_created_tasks(db_conn)
        assert count == 0


class TestSimulateProgressUpdate:
    """Test progress update simulation."""

    def test_progress_update_for_running_task(self, db_conn, test_user_id, disable_auto_push):
        """Test adding progress update to a running task."""
        # Create and start a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        from handsfree.db.agent_tasks import update_agent_task_state
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={"started": True},
        )

        # Add progress update
        result = simulate_progress_update(db_conn, task.id, "Making progress...")
        assert result is True

        # Verify trace was updated
        updated_task = get_agent_task_by_id(db_conn, task.id)
        assert updated_task.trace["progress"] == "Making progress..."
        assert "last_progress_at" in updated_task.trace

    def test_progress_update_for_non_running_task(self, db_conn, test_user_id):
        """Test that progress update fails for non-running tasks."""
        # Create a task in created state
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        # Try to add progress update
        result = simulate_progress_update(db_conn, task.id, "Should not work")
        assert result is False

    def test_progress_update_for_nonexistent_task(self, db_conn):
        """Test that progress update fails for nonexistent task."""
        fake_id = str(uuid.uuid4())
        result = simulate_progress_update(db_conn, fake_id, "Should not work")
        assert result is False


class TestProcessRunningTasks:
    """Test processing running tasks."""

    def test_complete_running_task_after_delay(self, db_conn, test_user_id, disable_auto_push):
        """Test that running tasks complete after the configured delay."""
        # Create and start a task with a timestamp in the past
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        from handsfree.db.agent_tasks import update_agent_task_state

        # Start the task with a timestamp 15 seconds ago (beyond default 10s delay)
        past_time = datetime.now(UTC) - timedelta(seconds=15)
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={
                "auto_started_at": past_time.isoformat(),
                "auto_started_by": "test",
            },
        )

        # Process running tasks with default delay (10s)
        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_TASK_COMPLETION_DELAY": "10"}):
            stats = process_running_tasks(db_conn)

        assert stats["completed"] == 1
        assert stats["failed"] == 0

        # Verify task state changed to completed
        updated_task = get_agent_task_by_id(db_conn, task.id)
        assert updated_task.state == "completed"
        assert "completed_at" in updated_task.trace
        assert updated_task.trace["result"] == "success"

        # Verify notification was created
        notifications = list_notifications(db_conn, test_user_id)
        assert len(notifications) == 1
        assert notifications[0].event_type == "agent.task_completed"

    def test_fail_running_task_when_configured(self, db_conn, test_user_id, disable_auto_push):
        """Test that running tasks fail when failure simulation is enabled."""
        # Create and start a task with a timestamp in the past
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        from handsfree.db.agent_tasks import update_agent_task_state

        past_time = datetime.now(UTC) - timedelta(seconds=15)
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={
                "auto_started_at": past_time.isoformat(),
                "auto_started_by": "test",
            },
        )

        # Process running tasks with failure simulation enabled
        with mock.patch.dict(
            os.environ,
            {
                "HANDSFREE_AGENT_TASK_COMPLETION_DELAY": "10",
                "HANDSFREE_AGENT_SIMULATE_FAILURE": "true",
            },
        ):
            stats = process_running_tasks(db_conn)

        assert stats["completed"] == 0
        assert stats["failed"] == 1

        # Verify task state changed to failed
        updated_task = get_agent_task_by_id(db_conn, task.id)
        assert updated_task.state == "failed"
        assert "completed_at" in updated_task.trace
        assert updated_task.trace["result"] == "simulated_failure"

        # Verify notification was created
        notifications = list_notifications(db_conn, test_user_id)
        assert len(notifications) == 1
        assert notifications[0].event_type == "agent.task_failed"

    def test_progress_update_before_completion(self, db_conn, test_user_id, disable_auto_push):
        """Test that progress updates are added before completion."""
        # Create and start a task with a timestamp at exactly half the delay
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        from handsfree.db.agent_tasks import update_agent_task_state

        # Start the task 6 seconds ago (half of 10s delay, not enough to complete)
        past_time = datetime.now(UTC) - timedelta(seconds=6)
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={
                "auto_started_at": past_time.isoformat(),
                "auto_started_by": "test",
            },
        )

        # Process running tasks
        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_TASK_COMPLETION_DELAY": "10"}):
            stats = process_running_tasks(db_conn)

        # Should have added progress but not completed
        assert stats["progressed"] == 1
        assert stats["completed"] == 0
        assert stats["failed"] == 0

        # Verify task is still running with progress update
        updated_task = get_agent_task_by_id(db_conn, task.id)
        assert updated_task.state == "running"
        assert "last_progress_at" in updated_task.trace
        assert "progress" in updated_task.trace

    def test_skip_task_without_start_time(self, db_conn, test_user_id, disable_auto_push):
        """Test that tasks without auto_started_at are skipped."""
        # Create a task and manually set it to running without auto_started_at
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        from handsfree.db.agent_tasks import update_agent_task_state

        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={"manual": True},  # No auto_started_at
        )

        # Process running tasks
        stats = process_running_tasks(db_conn)

        # Task should be skipped
        assert stats["completed"] == 0
        assert stats["failed"] == 0
        assert stats["progressed"] == 0

        # Task should still be running
        updated_task = get_agent_task_by_id(db_conn, task.id)
        assert updated_task.state == "running"

    def test_process_multiple_running_tasks(self, db_conn, test_user_id, disable_auto_push):
        """Test processing multiple running tasks."""
        from handsfree.db.agent_tasks import update_agent_task_state

        # Create two tasks that should complete
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

        past_time = datetime.now(UTC) - timedelta(seconds=15)

        for task in [task1, task2]:
            update_agent_task_state(
                conn=db_conn,
                task_id=task.id,
                new_state="running",
                trace_update={
                    "auto_started_at": past_time.isoformat(),
                    "auto_started_by": "test",
                },
            )

        # Process running tasks
        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_TASK_COMPLETION_DELAY": "10"}):
            stats = process_running_tasks(db_conn)

        assert stats["completed"] == 2

        # Verify both tasks completed
        updated_task1 = get_agent_task_by_id(db_conn, task1.id)
        updated_task2 = get_agent_task_by_id(db_conn, task2.id)
        assert updated_task1.state == "completed"
        assert updated_task2.state == "completed"


class TestRunOnce:
    """Test the main run_once function."""

    def test_run_once_disabled(self, db_conn):
        """Test run_once when runner is disabled."""
        with mock.patch.dict(os.environ, {}, clear=True):
            result = run_once(db_conn)

        assert result["enabled"] is False
        assert result["tasks_started"] == 0

    def test_run_once_with_created_tasks(self, db_conn, test_user_id, enable_runner, disable_auto_push):
        """Test run_once starts created tasks."""
        # Create a task
        create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        result = run_once(db_conn)

        assert result["enabled"] is True
        assert result["tasks_started"] == 1
        assert result["tasks_completed"] == 0

    def test_run_once_with_running_tasks(self, db_conn, test_user_id, enable_runner, disable_auto_push):
        """Test run_once completes running tasks."""
        from handsfree.db.agent_tasks import update_agent_task_state

        # Create and start a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        past_time = datetime.now(UTC) - timedelta(seconds=15)
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={
                "auto_started_at": past_time.isoformat(),
                "auto_started_by": "test",
            },
        )

        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_TASK_COMPLETION_DELAY": "10"}):
            result = run_once(db_conn)

        assert result["enabled"] is True
        assert result["tasks_started"] == 0
        assert result["tasks_completed"] == 1
        assert result["tasks_failed"] == 0

    def test_run_once_full_lifecycle(self, db_conn, test_user_id, enable_runner, disable_auto_push):
        """Test full lifecycle: create -> running -> completed."""
        # Create a task
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test task",
        )

        # First run: start the task
        result1 = run_once(db_conn)
        assert result1["tasks_started"] == 1
        assert result1["tasks_completed"] == 0

        # Verify task is running
        running_task = get_agent_task_by_id(db_conn, task.id)
        assert running_task.state == "running"

        # Manipulate the start time to simulate elapsed time
        # We need to directly update the trace, not use update_agent_task_state
        # because we can't transition running->running
        import json
        import uuid as uuid_module

        past_time = datetime.now(UTC) - timedelta(seconds=15)
        task_uuid = uuid_module.UUID(task.id)

        # Update the trace directly
        updated_trace = running_task.trace or {}
        updated_trace["auto_started_at"] = past_time.isoformat()

        db_conn.execute(
            """
            UPDATE agent_tasks
            SET last_update = ?, updated_at = ?
            WHERE id = ?
            """,
            [json.dumps(updated_trace), datetime.now(UTC), task_uuid],
        )

        # Second run: complete the task
        with mock.patch.dict(os.environ, {"HANDSFREE_AGENT_TASK_COMPLETION_DELAY": "10"}):
            result2 = run_once(db_conn)

        assert result2["tasks_started"] == 0
        assert result2["tasks_completed"] == 1

        # Verify task is completed
        completed_task = get_agent_task_by_id(db_conn, task.id)
        assert completed_task.state == "completed"

        # Verify notifications were created (started + completed)
        notifications = list_notifications(db_conn, test_user_id)
        assert len(notifications) == 2
        event_types = {n.event_type for n in notifications}
        assert "agent.task_started" in event_types
        assert "agent.task_completed" in event_types
