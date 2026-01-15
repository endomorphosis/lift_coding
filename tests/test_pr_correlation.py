"""Tests for agent task correlation with PR webhooks."""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from handsfree.api import _correlate_pr_with_agent_tasks
from handsfree.db.agent_tasks import AgentTask


def make_task(**kwargs) -> AgentTask:
    """Helper to create AgentTask with default timestamps."""
    defaults = {
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return AgentTask(**defaults)


class TestPRCorrelation:
    """Tests for PR webhook correlation with agent tasks."""

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    @patch("handsfree.db.agent_tasks.update_agent_task_state")
    def test_correlate_via_metadata(self, mock_update, mock_get_tasks, mock_get_db):
        """Test correlation via agent_task_metadata in PR body."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Create a running task
        task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="running",
            instruction="Fix the bug",
            target_type=None,
            target_ref=None,
            trace={"issue_url": "https://github.com/owner/repo/issues/42"},
        )
        mock_get_tasks.return_value = [task]

        # Create updated task
        updated_task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="completed",
            instruction="Fix the bug",
            target_type=None,
            target_ref=None,
            trace={
                "issue_url": "https://github.com/owner/repo/issues/42",
                "pr_url": "https://github.com/owner/repo/pull/100",
                "pr_number": 100,
            },
        )
        mock_update.return_value = updated_task

        # Create webhook payload with metadata
        normalized = {
            "event_type": "pull_request",
            "action": "opened",
            "pr_number": 100,
            "pr_url": "https://github.com/owner/repo/pull/100",
            "repo": "owner/repo",
        }

        raw_payload = {
            "pull_request": {
                "number": 100,
                "body": """# Fix the authentication bug

This PR fixes the issue.

<!-- agent_task_metadata
{"task_id": "task-123", "user_id": "user-456", "provider": "github_issue_dispatch"}
-->""",
            }
        }

        # Call correlation function
        with patch("handsfree.api.logger") as mock_logger:
            _correlate_pr_with_agent_tasks(normalized, raw_payload)

            # Verify task was updated
            mock_update.assert_called_once_with(
                conn=mock_db,
                task_id="task-123",
                new_state="completed",
                trace_update={
                    "pr_url": "https://github.com/owner/repo/pull/100",
                    "pr_number": 100,
                    "repo_full_name": "owner/repo",
                    "correlated_via": "pr_metadata",
                },
            )

            # Verify log message
            mock_logger.info.assert_called()

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    @patch("handsfree.db.agent_tasks.update_agent_task_state")
    def test_correlate_via_issue_reference(self, mock_update, mock_get_tasks, mock_get_db):
        """Test correlation via 'Fixes #N' reference in PR body."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Create a running task with issue number in trace
        task = make_task(
            id="task-456",
            user_id="user-789",
            provider="github_issue_dispatch",
            state="running",
            instruction="Implement feature",
            target_type=None,
            target_ref=None,
            trace={
                "issue_url": "https://github.com/owner/repo/issues/42",
                "issue_number": 42,
                "dispatch_repo": "owner/repo",
            },
        )
        mock_get_tasks.return_value = [task]

        # Create updated task
        updated_task = make_task(
            id="task-456",
            user_id="user-789",
            provider="github_issue_dispatch",
            state="completed",
            instruction="Implement feature",
            target_type=None,
            target_ref=None,
            trace={
                "issue_url": "https://github.com/owner/repo/issues/42",
                "issue_number": 42,
                "dispatch_repo": "owner/repo",
                "pr_url": "https://github.com/owner/repo/pull/200",
                "pr_number": 200,
            },
        )
        mock_update.return_value = updated_task

        # Create webhook payload with issue reference
        normalized = {
            "event_type": "pull_request",
            "action": "opened",
            "pr_number": 200,
            "pr_url": "https://github.com/owner/repo/pull/200",
            "repo": "owner/repo",
        }

        raw_payload = {
            "pull_request": {
                "number": 200,
                "body": "Fixes #42\n\nThis PR implements the requested feature.",
            }
        }

        # Call correlation function
        with patch("handsfree.api.logger") as mock_logger:
            _correlate_pr_with_agent_tasks(normalized, raw_payload)

            # Verify task was updated
            mock_update.assert_called_once_with(
                conn=mock_db,
                task_id="task-456",
                new_state="completed",
                trace_update={
                    "pr_url": "https://github.com/owner/repo/pull/200",
                    "pr_number": 200,
                    "repo_full_name": "owner/repo",
                    "correlated_via": "issue_reference",
                },
            )

            # Verify log message
            mock_logger.info.assert_called()

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    @patch("handsfree.db.agent_tasks.update_agent_task_state")
    def test_correlate_closes_keyword(self, mock_update, mock_get_tasks, mock_get_db):
        """Test correlation with 'Closes #N' keyword."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        task = make_task(
            id="task-999",
            user_id="user-888",
            provider="github_issue_dispatch",
            state="running",
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={
                "issue_number": 99,
                "dispatch_repo": "test/repo",
            },
        )
        mock_get_tasks.return_value = [task]

        updated_task = make_task(
            id="task-999",
            user_id="user-888",
            provider="github_issue_dispatch",
            state="completed",
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={
                "issue_number": 99,
                "dispatch_repo": "test/repo",
                "pr_url": "https://github.com/test/repo/pull/300",
            },
        )
        mock_update.return_value = updated_task

        normalized = {
            "event_type": "pull_request",
            "action": "opened",
            "pr_number": 300,
            "pr_url": "https://github.com/test/repo/pull/300",
            "repo": "test/repo",
        }

        raw_payload = {
            "pull_request": {
                "number": 300,
                "body": "Closes #99",
            }
        }

        _correlate_pr_with_agent_tasks(normalized, raw_payload)

        mock_update.assert_called_once()

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    def test_no_correlation_different_repo(self, mock_get_tasks, mock_get_db):
        """Test that correlation doesn't happen for different repos."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="running",
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={
                "issue_number": 42,
                "dispatch_repo": "different/repo",  # Different repo
            },
        )
        mock_get_tasks.return_value = [task]

        normalized = {
            "event_type": "pull_request",
            "action": "opened",
            "pr_number": 100,
            "pr_url": "https://github.com/owner/repo/pull/100",
            "repo": "owner/repo",
        }

        raw_payload = {
            "pull_request": {
                "number": 100,
                "body": "Fixes #42",  # Same issue number but different repo
            }
        }

        with patch("handsfree.db.agent_tasks.update_agent_task_state") as mock_update:
            _correlate_pr_with_agent_tasks(normalized, raw_payload)

            # Should not update any task
            mock_update.assert_not_called()

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    def test_no_correlation_for_closed_tasks(self, mock_get_tasks, mock_get_db):
        """Test that already completed/failed tasks are not updated."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Task already completed
        task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="completed",  # Already completed
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={
                "issue_number": 42,
                "dispatch_repo": "owner/repo",
            },
        )
        mock_get_tasks.return_value = [task]

        normalized = {
            "event_type": "pull_request",
            "action": "opened",
            "pr_number": 100,
            "pr_url": "https://github.com/owner/repo/pull/100",
            "repo": "owner/repo",
        }

        raw_payload = {
            "pull_request": {
                "number": 100,
                "body": "Fixes #42",
            }
        }

        with patch("handsfree.db.agent_tasks.update_agent_task_state") as mock_update:
            _correlate_pr_with_agent_tasks(normalized, raw_payload)

            # Should not update already completed task
            mock_update.assert_not_called()

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    def test_no_correlation_for_pr_synchronize(self, mock_get_tasks, mock_get_db):
        """Test that correlation only happens on PR opened, not other actions."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        normalized = {
            "event_type": "pull_request",
            "action": "synchronize",  # Not 'opened'
            "pr_number": 100,
            "pr_url": "https://github.com/owner/repo/pull/100",
            "repo": "owner/repo",
        }

        raw_payload = {
            "pull_request": {
                "number": 100,
                "body": "Fixes #42",
            }
        }

        # Should not even query tasks
        _correlate_pr_with_agent_tasks(normalized, raw_payload)

        mock_get_tasks.assert_not_called()

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    def test_no_correlation_for_non_pr_events(self, mock_get_tasks, mock_get_db):
        """Test that correlation only happens for PR events."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        normalized = {
            "event_type": "issue_comment",  # Not PR event
            "action": "created",
            "repo": "owner/repo",
        }

        raw_payload = {"issue": {}}

        # Should not even query tasks
        _correlate_pr_with_agent_tasks(normalized, raw_payload)

        mock_get_tasks.assert_not_called()

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    @patch("handsfree.db.agent_tasks.update_agent_task_state")
    def test_correlation_with_multiple_issue_refs(self, mock_update, mock_get_tasks, mock_get_db):
        """Test correlation when PR references multiple issues."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        # Two tasks with different issue numbers
        task1 = make_task(
            id="task-1",
            user_id="user-1",
            provider="github_issue_dispatch",
            state="running",
            instruction="Task 1",
            target_type=None,
            target_ref=None,
            trace={
                "issue_number": 10,
                "dispatch_repo": "owner/repo",
            },
        )

        task2 = make_task(
            id="task-2",
            user_id="user-2",
            provider="github_issue_dispatch",
            state="running",
            instruction="Task 2",
            target_type=None,
            target_ref=None,
            trace={
                "issue_number": 20,
                "dispatch_repo": "owner/repo",
            },
        )

        mock_get_tasks.return_value = [task1, task2]

        updated_task = make_task(
            id="task-1",
            user_id="user-1",
            provider="github_issue_dispatch",
            state="completed",
            instruction="Task 1",
            target_type=None,
            target_ref=None,
            trace={
                "issue_number": 10,
                "dispatch_repo": "owner/repo",
                "pr_url": "https://github.com/owner/repo/pull/100",
            },
        )
        mock_update.return_value = updated_task

        normalized = {
            "event_type": "pull_request",
            "action": "opened",
            "pr_number": 100,
            "pr_url": "https://github.com/owner/repo/pull/100",
            "repo": "owner/repo",
        }

        raw_payload = {
            "pull_request": {
                "number": 100,
                "body": "Fixes #10 and resolves #20",  # References both issues
            }
        }

        _correlate_pr_with_agent_tasks(normalized, raw_payload)

        # Should only update first matching task (breaks after first match)
        assert mock_update.call_count == 1

    @patch("handsfree.api.get_db")
    @patch("handsfree.db.agent_tasks.get_agent_tasks")
    def test_correlation_handles_malformed_metadata(self, mock_get_tasks, mock_get_db):
        """Test that malformed metadata doesn't crash the correlation."""
        mock_db = MagicMock()
        mock_get_db.return_value = mock_db

        task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="running",
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={},
        )
        mock_get_tasks.return_value = [task]

        normalized = {
            "event_type": "pull_request",
            "action": "opened",
            "pr_number": 100,
            "pr_url": "https://github.com/owner/repo/pull/100",
            "repo": "owner/repo",
        }

        # Malformed JSON in metadata
        raw_payload = {
            "pull_request": {
                "number": 100,
                "body": "<!-- agent_task_metadata\n{invalid json\n-->",
            }
        }

        with patch("handsfree.db.agent_tasks.update_agent_task_state") as mock_update:
            # Should not crash
            _correlate_pr_with_agent_tasks(normalized, raw_payload)

            # Should not update anything due to malformed metadata
            mock_update.assert_not_called()
