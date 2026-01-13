"""Tests for agent tasks persistence."""

import uuid

import pytest

from handsfree.db import init_db
from handsfree.db.agent_tasks import (
    create_agent_task,
    get_agent_task_by_id,
    get_agent_tasks,
    update_agent_task_state,
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
    # Use a fixed UUID for consistent testing
    return str(uuid.UUID("12345678-1234-1234-1234-123456789012"))


@pytest.fixture
def test_user_id_2():
    """Generate a second test user ID."""
    return str(uuid.UUID("87654321-4321-4321-4321-210987654321"))


class TestAgentTaskCreation:
    """Test agent task creation."""

    def test_create_basic_task(self, db_conn, test_user_id):
        """Test creating a basic agent task."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="fix the bug",
        )

        assert task.id is not None
        assert task.user_id == test_user_id
        assert task.provider == "copilot"
        assert task.instruction == "fix the bug"
        assert task.state == "created"
        assert task.target_type is None
        assert task.target_ref is None

    def test_create_task_with_issue_target(self, db_conn, test_user_id):
        """Test creating a task with issue target."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="handle issue",
            target_type="issue",
            target_ref="owner/repo#42",
        )

        assert task.target_type == "issue"
        assert task.target_ref == "owner/repo#42"

    def test_create_task_with_pr_target(self, db_conn, test_user_id):
        """Test creating a task with PR target."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="review pr",
            target_type="pr",
            target_ref="owner/repo#99",
        )

        assert task.target_type == "pr"
        assert task.target_ref == "owner/repo#99"

    def test_create_task_with_trace(self, db_conn, test_user_id):
        """Test creating a task with trace data."""
        trace = {"source": "test", "metadata": {"key": "value"}}
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="mock",
            instruction="test task",
            trace=trace,
        )

        assert task.trace == trace


class TestAgentTaskRetrieval:
    """Test agent task retrieval."""

    def test_get_task_by_id(self, db_conn, test_user_id):
        """Test retrieving a task by ID."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test",
        )

        retrieved = get_agent_task_by_id(conn=db_conn, task_id=task.id)

        assert retrieved is not None
        assert retrieved.id == task.id
        assert retrieved.user_id == test_user_id
        assert retrieved.provider == task.provider
        assert retrieved.instruction == task.instruction

    def test_get_nonexistent_task(self, db_conn):
        """Test retrieving a nonexistent task."""
        retrieved = get_agent_task_by_id(conn=db_conn, task_id=str(uuid.uuid4()))

        assert retrieved is None

    def test_get_tasks_by_user(self, db_conn, test_user_id, test_user_id_2):
        """Test querying tasks by user."""
        create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="task 1"
        )
        create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="task 2"
        )
        create_agent_task(
            conn=db_conn, user_id=test_user_id_2, provider="copilot", instruction="task 3"
        )

        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)

        assert len(tasks) == 2
        assert all(t.user_id == test_user_id for t in tasks)

    def test_get_tasks_by_provider(self, db_conn, test_user_id):
        """Test querying tasks by provider."""
        create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="task 1"
        )
        create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="custom", instruction="task 2"
        )
        create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="task 3"
        )

        tasks = get_agent_tasks(conn=db_conn, provider="copilot")

        assert len(tasks) == 2
        assert all(t.provider == "copilot" for t in tasks)

    def test_get_tasks_by_state(self, db_conn, test_user_id):
        """Test querying tasks by state."""
        task1 = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="task 1"
        )
        task2 = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="task 2"
        )

        # Advance one task
        update_agent_task_state(conn=db_conn, task_id=task1.id, new_state="running")

        tasks = get_agent_tasks(conn=db_conn, state="created")

        assert len(tasks) == 1
        assert tasks[0].id == task2.id


class TestAgentTaskStateTransitions:
    """Test agent task state transitions."""

    def test_valid_transition_created_to_running(self, db_conn, test_user_id):
        """Test valid transition from created to running."""
        task = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="test"
        )

        updated = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        assert updated is not None
        assert updated.state == "running"
        assert updated.updated_at > task.updated_at

    def test_valid_transition_running_to_completed(self, db_conn, test_user_id):
        """Test valid transition from running to completed."""
        task = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="test"
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        updated = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="completed")

        assert updated is not None
        assert updated.state == "completed"

    def test_valid_transition_running_to_needs_input(self, db_conn, test_user_id):
        """Test valid transition from running to needs_input."""
        task = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="test"
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        updated = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="needs_input")

        assert updated is not None
        assert updated.state == "needs_input"

    def test_invalid_transition_created_to_completed(self, db_conn, test_user_id):
        """Test invalid transition from created to completed."""
        task = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="test"
        )

        with pytest.raises(ValueError, match="Invalid state transition"):
            update_agent_task_state(conn=db_conn, task_id=task.id, new_state="completed")

    def test_invalid_transition_completed_to_running(self, db_conn, test_user_id):
        """Test invalid transition from completed to any state."""
        task = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="test"
        )
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        task = update_agent_task_state(conn=db_conn, task_id=task.id, new_state="completed")

        with pytest.raises(ValueError, match="Invalid state transition"):
            update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

    def test_transition_with_trace_update(self, db_conn, test_user_id):
        """Test state transition with trace update."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="copilot",
            instruction="test",
            trace={"initial": "data"},
        )

        updated = update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="running",
            trace_update={"step": "started"},
        )

        assert updated.trace is not None
        assert updated.trace["initial"] == "data"
        assert updated.trace["step"] == "started"

    def test_update_nonexistent_task(self, db_conn):
        """Test updating a nonexistent task."""
        result = update_agent_task_state(
            conn=db_conn, task_id=str(uuid.uuid4()), new_state="running"
        )

        assert result is None


class TestAgentTaskQueries:
    """Test agent task queries."""

    def test_tasks_ordered_by_created_at_desc(self, db_conn, test_user_id):
        """Test that tasks are returned in descending order by creation time."""
        task1 = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="first"
        )
        task2 = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="second"
        )
        task3 = create_agent_task(
            conn=db_conn, user_id=test_user_id, provider="copilot", instruction="third"
        )

        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)

        assert len(tasks) == 3
        # Most recent first
        assert tasks[0].id == task3.id
        assert tasks[1].id == task2.id
        assert tasks[2].id == task1.id

    def test_limit_tasks(self, db_conn, test_user_id):
        """Test limiting number of returned tasks."""
        for i in range(10):
            create_agent_task(
                conn=db_conn, user_id=test_user_id, provider="copilot", instruction=f"task {i}"
            )

        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id, limit=5)

        assert len(tasks) == 5
