"""Tests for agent service."""

import pytest

from handsfree.agents.service import AgentService
from handsfree.agent_providers import IPFSDatasetsMCPAgentProvider
from handsfree.db import init_db
from handsfree.db.agent_tasks import get_agent_tasks, update_agent_task_state
from test_mcp_ipfs_provider import _FakeMCPClient


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
        # Task should transition to "running" after successful provider start
        assert result["state"] == "running"
        assert "spoken_text" in result

        # Verify task was created in DB and transitioned to running
        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)
        assert len(tasks) == 1
        assert tasks[0].instruction == "fix the bug"
        assert tasks[0].provider == "copilot"
        assert tasks[0].state == "running"

    def test_delegate_with_issue_target(self, agent_service, db_conn, test_user_id):
        """Test delegating with issue target."""
        result = agent_service.delegate(
            user_id=test_user_id,
            instruction="handle issue",
            provider="copilot",
            target_type="issue",
            target_ref="owner/repo#42",
        )

        # Task should transition to "running" after successful provider start
        assert result["state"] == "running"
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

        # Task should transition to "running" after successful provider start
        assert result["state"] == "running"
        assert "pr" in result["spoken_text"].lower()
        assert "99" in result["spoken_text"]

    def test_delegate_trace_added(self, agent_service, db_conn, test_user_id):
        """Test that delegation adds trace information."""
        agent_service.delegate(user_id=test_user_id, instruction="test task", provider="mock")

        # Verify trace in DB
        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)
        assert tasks[0].trace is not None
        assert "created_via" in tasks[0].trace

    def test_delegate_adds_mcp_provider_metadata(
        self, agent_service, db_conn, test_user_id, monkeypatch
    ):
        """Test that MCP providers get normalized capability metadata."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")
        fake_provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_datasets_mcp" else None,
        )
        result = agent_service.delegate(
            user_id=test_user_id,
            instruction="find legal datasets",
            provider="ipfs_datasets_mcp",
        )

        tasks = get_agent_tasks(conn=db_conn, user_id=test_user_id)
        assert result["spoken_text"] == "Expanded legal query"
        assert result["state"] == "completed"
        assert tasks[0].trace is not None
        assert tasks[0].state == "completed"
        assert tasks[0].trace["provider_label"] == "IPFS Datasets"
        assert tasks[0].trace["mcp_capability"] == "dataset_discovery"


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
        # Mock provider auto-advances to "running" on first status check
        assert result["by_state"]["running"] == 1
        assert "1 task" in result["spoken_text"]
        assert "running" in result["spoken_text"]

    def test_status_multiple_tasks(self, agent_service, db_conn, test_user_id):
        """Test status with multiple tasks in different states."""
        # Create tasks - they will auto-start to "running"
        agent_service.delegate(user_id=test_user_id, instruction="task1", provider="mock")
        task2 = agent_service.delegate(user_id=test_user_id, instruction="task2", provider="mock")
        agent_service.delegate(user_id=test_user_id, instruction="task3", provider="mock")

        # Tasks are already "running" after delegate, advance task2 to completed
        update_agent_task_state(conn=db_conn, task_id=task2["task_id"], new_state="completed")

        result = agent_service.get_status(user_id=test_user_id)

        assert result["total"] == 3
        # task1 and task3 are running, task2 is completed
        assert result["by_state"]["running"] == 2
        assert result["by_state"]["completed"] == 1
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

    def test_status_prefers_result_envelope_fields(self, agent_service, db_conn, test_user_id):
        """Status payload should use normalized envelope fields when available."""
        from handsfree.db.agent_tasks import create_agent_task

        create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123",
            trace={
                "mcp_capability": "ipfs_pin",
                "mcp_result_envelope": {
                    "summary": "Pinned bafy123.",
                    "structured_output": {"cid": "bafy123", "message": "Pinned bafy123."},
                    "follow_up_actions": [{"id": "read_cid", "label": "Read CID"}],
                },
            },
        )

        result = agent_service.get_status(user_id=test_user_id)

        assert result["tasks"][0]["result_preview"] == "Pinned bafy123."
        assert result["tasks"][0]["result_output"]["cid"] == "bafy123"
        assert result["tasks"][0]["follow_up_actions"][0]["id"] == "read_cid"

    def test_status_includes_execution_mode_metadata(self, agent_service, db_conn, test_user_id):
        """Status payload should surface preferred and resolved execution mode metadata."""
        from handsfree.db.agent_tasks import create_agent_task

        create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123",
            trace={
                "mcp_capability": "ipfs_pin",
                "mcp_preferred_execution_mode": "direct_import",
                "mcp_execution_mode": "mcp_remote",
                "mcp_result_preview": "Pinned bafy123.",
            },
        )

        result = agent_service.get_status(user_id=test_user_id)

        assert result["tasks"][0]["mcp_preferred_execution_mode"] == "direct_import"
        assert result["tasks"][0]["mcp_execution_mode"] == "mcp_remote"


class TestAdvanceTaskState:
    """Test advancing task states via service."""

    def test_advance_task_success(self, agent_service, db_conn, test_user_id):
        """Test successfully advancing a task."""
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        # Task is already "running" after delegation, advance to "completed"
        result = agent_service.advance_task_state(task_id, "completed")

        assert result["task_id"] == task_id
        assert result["state"] == "completed"
        assert "updated_at" in result

    def test_advance_task_with_trace(self, agent_service, db_conn, test_user_id):
        """Test advancing task with trace update."""
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        # Task is already "running" after delegation, advance to "completed" with trace
        result = agent_service.advance_task_state(
            task_id, "completed", trace_update={"step": "processing"}
        )

        assert result["state"] == "completed"

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

        # Task is in "running" state, try invalid transition to "created"
        with pytest.raises(ValueError, match="Invalid state transition"):
            agent_service.advance_task_state(task_id, "created")


class TestNotifications:
    """Test notification emission."""

    def test_completion_notification_message_mentions_remote_fallback(
        self, agent_service, db_conn, test_user_id
    ):
        """Completion notifications should mention when local execution fell back to remote."""
        from handsfree.db.agent_tasks import create_agent_task, get_agent_tasks
        from handsfree.db.notifications import list_notifications

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123 on ipfs",
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")

        agent_service.advance_task_state(
            task.id,
            "completed",
            trace_update={
                "provider_label": "IPFS Kit",
                "mcp_capability": "ipfs_pin",
                "mcp_cid": "bafy123",
                "mcp_result_preview": "Pinned bafy123",
                "mcp_preferred_execution_mode": "direct_import",
                "mcp_execution_mode": "mcp_remote",
            },
        )

        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert notifications
        assert "Execution: remote (local unavailable)" in notifications[0].message

    def test_notification_on_task_creation(self, agent_service, db_conn, test_user_id):
        """Test that notification is persisted on task creation."""
        from handsfree.db.notifications import list_notifications

        agent_service.delegate(user_id=test_user_id, instruction="test", provider="mock")

        # Verify notification was created in database
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        assert len(notifications) >= 1
        task_created_notifs = [n for n in notifications if n.event_type == "task_created"]
        assert len(task_created_notifs) >= 1

    def test_notification_on_state_change(self, agent_service, db_conn, test_user_id):
        """Test that notification is persisted on state change."""
        from handsfree.db.notifications import list_notifications

        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        # Task is already "running" after delegation, advance to "completed"
        agent_service.advance_task_state(task_id, "completed")

        # Verify notification was created in database
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        # Should have task_created, task_running, and task_completed notifications
        assert len(notifications) >= 3

    def test_notification_on_task_completion(self, agent_service, db_conn, test_user_id):
        """Test that completing a task writes a notification."""
        from handsfree.db.notifications import list_notifications

        # Create task - it will auto-start to "running"
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test task", provider="mock"
        )
        task_id = task_result["task_id"]

        # Complete the task (already in "running" state)
        agent_service.advance_task_state(task_id, "completed")

        # Verify completion notification was created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        completion_notifs = [n for n in notifications if n.event_type == "task_completed"]
        assert len(completion_notifs) == 1

        # Verify the notification includes task_id and state
        notif = completion_notifs[0]
        assert notif.metadata is not None
        assert notif.metadata["task_id"] == task_id
        assert notif.metadata["state"] == "completed"
        assert task_id in notif.message

    def test_notification_on_task_failure(self, agent_service, db_conn, test_user_id):
        """Test that failing a task writes a notification."""
        from handsfree.db.notifications import list_notifications

        # Create and fail task
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test task", provider="mock"
        )
        task_id = task_result["task_id"]

        # Fail the task
        agent_service.advance_task_state(task_id, "failed")

        # Verify failure notification was created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        failure_notifs = [n for n in notifications if n.event_type == "task_failed"]
        assert len(failure_notifs) == 1

        # Verify the notification includes task_id and state
        notif = failure_notifs[0]
        assert notif.metadata is not None
        assert notif.metadata["task_id"] == task_id
        assert notif.metadata["state"] == "failed"
        assert task_id in notif.message

    def test_completion_notification_includes_pr_url(self, agent_service, db_conn, test_user_id):
        """Test that completion notification includes PR URL when provided in trace."""
        from handsfree.db.notifications import list_notifications

        # Create task - it will auto-start to "running"
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="fix bug", provider="mock"
        )
        task_id = task_result["task_id"]

        # Complete with PR URL in trace (task is already "running")
        agent_service.advance_task_state(
            task_id,
            "completed",
            trace_update={
                "pr_url": "https://github.com/owner/repo/pull/123",
                "pr_number": 123,
                "repo_full_name": "owner/repo",
            },
        )

        # Verify notification includes PR info
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        completion_notifs = [n for n in notifications if n.event_type == "task_completed"]
        assert len(completion_notifs) == 1

        notif = completion_notifs[0]
        assert notif.metadata is not None
        assert notif.metadata["pr_url"] == "https://github.com/owner/repo/pull/123"
        assert notif.metadata["pr_number"] == 123
        assert notif.metadata["repo_full_name"] == "owner/repo"
        assert "https://github.com/owner/repo/pull/123" in notif.message

    def test_completion_notification_with_pr_number_only(
        self, agent_service, db_conn, test_user_id
    ):
        """Test completion notification with PR number but no URL."""
        from handsfree.db.notifications import list_notifications

        # Create task - it will auto-start to "running"
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        # Complete with PR number (task is already "running")
        agent_service.advance_task_state(
            task_id,
            "completed",
            trace_update={"pr_number": 456, "repo_full_name": "owner/repo"},
        )

        # Verify notification includes PR reference
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        completion_notifs = [n for n in notifications if n.event_type == "task_completed"]
        assert len(completion_notifs) == 1

        notif = completion_notifs[0]
        assert notif.metadata is not None
        assert notif.metadata["pr_number"] == 456
        assert notif.metadata["repo_full_name"] == "owner/repo"
        assert "owner/repo#456" in notif.message

    def test_completion_notification_without_pr_info(self, agent_service, db_conn, test_user_id):
        """Test completion notification works without PR info."""
        from handsfree.db.notifications import list_notifications

        # Create task - it will auto-start to "running"
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test", provider="mock"
        )
        task_id = task_result["task_id"]

        # Complete without PR info (task is already "running")
        agent_service.advance_task_state(task_id, "completed")

        # Verify notification was still created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        completion_notifs = [n for n in notifications if n.event_type == "task_completed"]
        assert len(completion_notifs) == 1

        notif = completion_notifs[0]
        assert notif.metadata is not None
        assert notif.metadata["task_id"] == task_id
        assert notif.metadata["state"] == "completed"
        # Should not have PR fields
        assert "pr_url" not in notif.metadata
        assert "pr_number" not in notif.metadata

    def test_mock_provider_auto_advances_on_status_checks(
        self, agent_service, db_conn, test_user_id
    ):
        """Test that mock provider auto-advances task through multiple status checks."""
        from handsfree.db.notifications import list_notifications

        # Create a task with mock provider - it will auto-start to "running"
        task_result = agent_service.delegate(
            user_id=test_user_id, instruction="test auto-advance", provider="mock"
        )
        task_id = task_result["task_id"]

        # Initial state should be "running" after auto-start
        assert task_result["state"] == "running"

        # Verify "created" and "running" notifications exist
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        created_notifs = [n for n in notifications if n.event_type == "task_created"]
        assert len(created_notifs) >= 1
        running_notifs = [n for n in notifications if n.event_type == "task_running"]
        assert len(running_notifs) >= 1

        # Status check should show task as running
        result1 = agent_service.get_status(user_id=test_user_id)
        assert result1["total"] == 1
        assert result1["by_state"]["running"] == 1

        # Second status check should keep it "running" (step 0 -> step 1)
        result2 = agent_service.get_status(user_id=test_user_id)
        assert result2["by_state"]["running"] == 1

        # Third status check should advance to "completed" (step 2)
        result3 = agent_service.get_status(user_id=test_user_id)
        assert result3["by_state"]["completed"] == 1

        # Verify "completed" notification was created
        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        completed_notifs = [n for n in notifications if n.event_type == "task_completed"]
        assert len(completed_notifs) == 1

        # Verify completion notification includes task_id and state
        notif = completed_notifs[0]
        assert notif.metadata is not None
        assert notif.metadata["task_id"] == task_id
        assert notif.metadata["state"] == "completed"
        assert task_id in notif.message

        # Verify completion notification includes PR info from trace
        assert notif.metadata.get("pr_url") == "https://github.com/mock/repo/pull/123"

    def test_async_mcp_completion_notification_includes_result(
        self, db_conn, test_user_id, monkeypatch
    ):
        """Completed MCP tasks should notify with stored result preview/output."""
        from handsfree.agent_providers import IPFSDatasetsMCPAgentProvider
        from handsfree.agents.service import AgentService
        from handsfree.db.notifications import list_notifications
        from test_mcp_ipfs_provider import _FakeMCPClient

        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")
        fake_provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_datasets_mcp" else None,
        )

        service = AgentService(db_conn)
        task_result = service.delegate(
            user_id=test_user_id,
            instruction="find legal datasets",
            provider="ipfs_datasets_mcp",
        )

        status = service.get_status(user_id=test_user_id)

        assert status["by_state"]["completed"] == 1

        notifications = list_notifications(conn=db_conn, user_id=test_user_id)
        completion_notifs = [n for n in notifications if n.event_type == "task_completed"]
        assert len(completion_notifs) == 1

        notif = completion_notifs[0]
        assert notif.metadata is not None
        assert notif.metadata["task_id"] == task_result["task_id"]
        assert notif.metadata["provider"] == "ipfs_datasets_mcp"
        assert notif.metadata["provider_label"] == "IPFS Datasets"
        assert notif.metadata["mcp_capability"] == "dataset_discovery"
        assert notif.metadata["result_preview"] == "Expanded legal query"
        assert notif.metadata["result_output"]["expanded_queries"] == [
            "find legal datasets",
            "find legal datasets statutes",
        ]
        assert "Result: Expanded legal query" in notif.message
