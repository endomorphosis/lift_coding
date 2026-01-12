"""Tests for agent tasks persistence."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.agent_tasks import (
    create_agent_task,
    get_agent_task,
    get_agent_tasks,
    store_agent_trace,
    update_task_status,
)


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


def test_create_agent_task(db_conn):
    """Test creating an agent task."""
    user_id = str(uuid.uuid4())
    task = create_agent_task(
        db_conn,
        user_id=user_id,
        provider="copilot",
        instruction="Fix issue #123",
        repo_full_name="owner/repo",
        issue_number=123,
    )

    assert task.id is not None
    assert task.user_id == user_id
    assert task.provider == "copilot"
    assert task.instruction == "Fix issue #123"
    assert task.repo_full_name == "owner/repo"
    assert task.issue_number == 123
    assert task.pr_number is None
    assert task.status == "created"
    assert task.last_update == "Task created"


def test_create_agent_task_with_pr(db_conn):
    """Test creating an agent task associated with a PR."""
    user_id = str(uuid.uuid4())
    task = create_agent_task(
        db_conn,
        user_id=user_id,
        provider="custom",
        instruction="Address review comments",
        repo_full_name="owner/repo",
        pr_number=456,
    )

    assert task.pr_number == 456
    assert task.issue_number is None


def test_update_task_status(db_conn):
    """Test updating task status."""
    user_id = str(uuid.uuid4())
    task = create_agent_task(
        db_conn,
        user_id=user_id,
        provider="copilot",
        instruction="Test task",
    )

    # Update to running
    success = update_task_status(
        db_conn,
        task.id,
        status="running",
        last_update="Started processing",
    )
    assert success is True

    # Verify update
    updated_task = get_agent_task(db_conn, task.id)
    assert updated_task is not None
    assert updated_task.status == "running"
    assert updated_task.last_update == "Started processing"


def test_update_task_status_transitions(db_conn):
    """Test state machine transitions."""
    user_id = str(uuid.uuid4())
    task = create_agent_task(
        db_conn,
        user_id=user_id,
        provider="copilot",
        instruction="Test transitions",
    )

    # created -> running
    update_task_status(db_conn, task.id, "running", "Agent started")
    task = get_agent_task(db_conn, task.id)
    assert task.status == "running"

    # running -> needs_input
    update_task_status(db_conn, task.id, "needs_input", "Waiting for clarification")
    task = get_agent_task(db_conn, task.id)
    assert task.status == "needs_input"

    # needs_input -> running
    update_task_status(db_conn, task.id, "running", "Resumed")
    task = get_agent_task(db_conn, task.id)
    assert task.status == "running"

    # running -> completed
    update_task_status(db_conn, task.id, "completed", "PR opened")
    task = get_agent_task(db_conn, task.id)
    assert task.status == "completed"


def test_update_task_failed(db_conn):
    """Test marking task as failed."""
    user_id = str(uuid.uuid4())
    task = create_agent_task(
        db_conn,
        user_id=user_id,
        provider="copilot",
        instruction="Test failure",
    )

    update_task_status(db_conn, task.id, "running")
    update_task_status(db_conn, task.id, "failed", "Build failed")

    task = get_agent_task(db_conn, task.id)
    assert task.status == "failed"
    assert task.last_update == "Build failed"


def test_update_nonexistent_task(db_conn):
    """Test updating a non-existent task."""
    result = update_task_status(db_conn, str(uuid.uuid4()), "running")
    assert result is not True


def test_get_agent_task(db_conn):
    """Test retrieving an agent task."""
    user_id = str(uuid.uuid4())
    created = create_agent_task(
        db_conn,
        user_id=user_id,
        provider="copilot",
        instruction="Test get",
        repo_full_name="owner/repo",
    )

    retrieved = get_agent_task(db_conn, created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.user_id == user_id
    assert retrieved.instruction == "Test get"


def test_get_nonexistent_task(db_conn):
    """Test retrieving a non-existent task."""
    result = get_agent_task(db_conn, str(uuid.uuid4()))
    assert result is None


def test_get_agent_tasks(db_conn):
    """Test querying agent tasks."""
    user_id = str(uuid.uuid4())

    # Create multiple tasks
    create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 1")
    create_agent_task(db_conn, user_id=user_id, provider="custom", instruction="Task 2")
    create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 3")

    # Get all tasks for user
    tasks = get_agent_tasks(db_conn, user_id=user_id)
    assert len(tasks) == 3


def test_get_agent_tasks_by_status(db_conn):
    """Test filtering tasks by status."""
    user_id = str(uuid.uuid4())

    task1 = create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 1")
    task2 = create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 2")

    update_task_status(db_conn, task1.id, "running")
    update_task_status(db_conn, task2.id, "completed")

    running_tasks = get_agent_tasks(db_conn, user_id=user_id, status="running")
    assert len(running_tasks) == 1
    assert running_tasks[0].id == task1.id

    completed_tasks = get_agent_tasks(db_conn, user_id=user_id, status="completed")
    assert len(completed_tasks) == 1
    assert completed_tasks[0].id == task2.id


def test_get_agent_tasks_by_provider(db_conn):
    """Test filtering tasks by provider."""
    user_id = str(uuid.uuid4())

    create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 1")
    create_agent_task(db_conn, user_id=user_id, provider="custom", instruction="Task 2")
    create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 3")

    copilot_tasks = get_agent_tasks(db_conn, user_id=user_id, provider="copilot")
    assert len(copilot_tasks) == 2

    custom_tasks = get_agent_tasks(db_conn, user_id=user_id, provider="custom")
    assert len(custom_tasks) == 1


def test_get_agent_tasks_with_limit(db_conn):
    """Test limiting the number of returned tasks."""
    user_id = str(uuid.uuid4())

    for i in range(10):
        create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction=f"Task {i}")

    tasks = get_agent_tasks(db_conn, user_id=user_id, limit=5)
    assert len(tasks) == 5


def test_get_agent_tasks_ordering(db_conn):
    """Test that tasks are returned in descending order by updated_at."""
    user_id = str(uuid.uuid4())

    task1 = create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 1")
    task2 = create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 2")
    task3 = create_agent_task(db_conn, user_id=user_id, provider="copilot", instruction="Task 3")

    # Update task1 status (should move it to top)
    update_task_status(db_conn, task1.id, "running")

    tasks = get_agent_tasks(db_conn, user_id=user_id)

    # task1 should be first (most recently updated)
    assert tasks[0].id == task1.id
    assert tasks[1].id == task3.id
    assert tasks[2].id == task2.id


def test_store_agent_trace(db_conn):
    """Test storing agent trace data."""
    user_id = str(uuid.uuid4())
    task = create_agent_task(
        db_conn,
        user_id=user_id,
        provider="copilot",
        instruction="Test trace",
    )

    trace_data = {
        "prompt": "Fix the bug in file.py",
        "tools_used": ["edit_file", "run_tests"],
        "links": ["https://github.com/owner/repo/pull/123"],
    }

    success = store_agent_trace(db_conn, task.id, trace_data)
    assert success is True
