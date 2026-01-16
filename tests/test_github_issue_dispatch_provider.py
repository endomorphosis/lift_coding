"""Tests for GitHubIssueDispatchProvider."""

import json
import os
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from handsfree.agent_providers import GitHubIssueDispatchProvider
from handsfree.db.agent_tasks import AgentTask


def make_task(**kwargs) -> AgentTask:
    """Helper to create AgentTask with default timestamps."""
    defaults = {
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(kwargs)
    return AgentTask(**defaults)


class TestGitHubIssueDispatchProvider:
    """Tests for GitHub issue dispatch provider."""

    def test_provider_not_configured_no_repo(self):
        """Test that provider fails gracefully when dispatch repo not configured."""
        with patch.dict(os.environ, {"HANDSFREE_AGENT_DISPATCH_REPO": ""}, clear=False):
            provider = GitHubIssueDispatchProvider()

            task = make_task(
                id="task-123",
                user_id="user-456",
                provider="github_issue_dispatch",
                state="created",
                instruction="Test instruction",
                target_type=None,
                target_ref=None,
                trace={},
            )

            result = provider.start_task(task)

            assert result["ok"] is False
            assert result["status"] == "failed"
            assert "not configured" in result["message"]
            assert "HANDSFREE_AGENT_DISPATCH_REPO not set" in result["message"]

    def test_provider_not_configured_no_token(self):
        """Test that provider fails gracefully when token not available."""
        with patch.dict(
            os.environ,
            {
                "HANDSFREE_AGENT_DISPATCH_REPO": "owner/repo",
                "GITHUB_TOKEN": "",
            },
            clear=True,
        ):
            provider = GitHubIssueDispatchProvider()

            task = make_task(
                id="task-123",
                user_id="user-456",
                provider="github_issue_dispatch",
                state="created",
                instruction="Test instruction",
                target_type=None,
                target_ref=None,
                trace={},
            )

            result = provider.start_task(task)

            assert result["ok"] is False
            assert result["status"] == "failed"
            assert "not configured" in result["message"]
            assert "No GitHub token available" in result["message"]

    @patch("handsfree.github.client.create_issue")
    def test_start_task_success(self, mock_create_issue):
        """Test successful task dispatch."""
        mock_create_issue.return_value = {
            "ok": True,
            "issue_url": "https://github.com/owner/repo/issues/123",
            "issue_number": 123,
        }

        with patch.dict(
            os.environ,
            {
                "HANDSFREE_AGENT_DISPATCH_REPO": "owner/repo",
                "GITHUB_TOKEN": "ghp_token123",
            },
        ):
            provider = GitHubIssueDispatchProvider()

            task = make_task(
                id="task-456",
                user_id="user-789",
                provider="github_issue_dispatch",
                state="created",
                instruction="Please fix the bug in the authentication module",
                target_type="pr",
                target_ref="owner/repo#42",
                trace={},
            )

            result = provider.start_task(task)

            # Verify result
            assert result["ok"] is True
            assert result["status"] == "running"
            assert "Dispatch issue created" in result["message"]
            assert result["trace"]["issue_url"] == "https://github.com/owner/repo/issues/123"
            assert result["trace"]["issue_number"] == 123
            assert result["trace"]["provider"] == "github_issue_dispatch"
            assert result["trace"]["dispatch_repo"] == "owner/repo"

            # Verify create_issue was called correctly
            mock_create_issue.assert_called_once()
            call_kwargs = mock_create_issue.call_args[1]
            assert call_kwargs["repo"] == "owner/repo"
            assert call_kwargs["token"] == "ghp_token123"
            assert call_kwargs["labels"] == ["copilot-agent"]

            # Verify issue title and body
            assert "Please fix the bug in the authentication module" in call_kwargs["title"]
            body = call_kwargs["body"]
            assert "task-456" in body
            assert "user-789" in body
            assert "Please fix the bug in the authentication module" in body
            assert "pr `owner/repo#42`" in body
            assert "agent_task_metadata" in body

            # Verify metadata in body
            assert "task-456" in body
            metadata_match = json.loads(body.split("<!-- agent_task_metadata")[1].split("-->")[0])
            assert metadata_match["task_id"] == "task-456"
            assert metadata_match["user_id"] == "user-789"
            assert metadata_match["provider"] == "github_issue_dispatch"

    @patch("handsfree.github.client.create_issue")
    def test_start_task_long_instruction_truncated(self, mock_create_issue):
        """Test that long instructions are truncated in the title."""
        mock_create_issue.return_value = {
            "ok": True,
            "issue_url": "https://github.com/owner/repo/issues/124",
            "issue_number": 124,
        }

        long_instruction = "A" * 200

        with patch.dict(
            os.environ,
            {
                "HANDSFREE_AGENT_DISPATCH_REPO": "owner/repo",
                "GITHUB_TOKEN": "ghp_token123",
            },
        ):
            provider = GitHubIssueDispatchProvider()

            task = make_task(
                id="task-456",
                user_id="user-789",
                provider="github_issue_dispatch",
                state="created",
                instruction=long_instruction,
                target_type=None,
                target_ref=None,
                trace={},
            )

            result = provider.start_task(task)

            assert result["ok"] is True

            # Verify title is truncated
            call_kwargs = mock_create_issue.call_args[1]
            title = call_kwargs["title"]
            assert len(title) <= 103  # 100 chars + "..."
            assert title.endswith("...")

            # But full instruction is in body
            body = call_kwargs["body"]
            assert long_instruction in body

    @patch("handsfree.github.client.create_issue")
    def test_start_task_no_instruction(self, mock_create_issue):
        """Test task dispatch with no instruction."""
        mock_create_issue.return_value = {
            "ok": True,
            "issue_url": "https://github.com/owner/repo/issues/125",
            "issue_number": 125,
        }

        with patch.dict(
            os.environ,
            {
                "HANDSFREE_AGENT_DISPATCH_REPO": "owner/repo",
                "GITHUB_TOKEN": "ghp_token123",
            },
        ):
            provider = GitHubIssueDispatchProvider()

            task = make_task(
                id="task-789",
                user_id="user-101",
                provider="github_issue_dispatch",
                state="created",
                instruction=None,
                target_type=None,
                target_ref=None,
                trace={},
            )

            result = provider.start_task(task)

            assert result["ok"] is True

            # Verify default title is used
            call_kwargs = mock_create_issue.call_args[1]
            assert call_kwargs["title"] == "Agent Task"

    @patch("handsfree.github.client.create_issue")
    def test_start_task_github_api_failure(self, mock_create_issue):
        """Test handling of GitHub API failure."""
        mock_create_issue.return_value = {
            "ok": False,
            "message": "API rate limit exceeded",
            "status_code": 403,
        }

        with patch.dict(
            os.environ,
            {
                "HANDSFREE_AGENT_DISPATCH_REPO": "owner/repo",
                "GITHUB_TOKEN": "ghp_token123",
            },
        ):
            provider = GitHubIssueDispatchProvider()

            task = make_task(
                id="task-999",
                user_id="user-888",
                provider="github_issue_dispatch",
                state="created",
                instruction="Test instruction",
                target_type=None,
                target_ref=None,
                trace={},
            )

            result = provider.start_task(task)

            assert result["ok"] is False
            assert result["status"] == "failed"
            assert "API rate limit exceeded" in result["message"]
            assert result["trace"]["error"] == "issue_creation_failed"

    @patch("handsfree.github.client.create_issue")
    def test_start_task_exception(self, mock_create_issue):
        """Test handling of exceptions during dispatch."""
        mock_create_issue.side_effect = Exception("Network error")

        with patch.dict(
            os.environ,
            {
                "HANDSFREE_AGENT_DISPATCH_REPO": "owner/repo",
                "GITHUB_TOKEN": "ghp_token123",
            },
        ):
            provider = GitHubIssueDispatchProvider()

            task = make_task(
                id="task-error",
                user_id="user-error",
                provider="github_issue_dispatch",
                state="created",
                instruction="Test instruction",
                target_type=None,
                target_ref=None,
                trace={},
            )

            result = provider.start_task(task)

            assert result["ok"] is False
            assert result["status"] == "failed"
            assert "Exception during dispatch" in result["message"]
            assert "Network error" in result["message"]
            assert result["trace"]["error"] == "exception"

    def test_check_status_with_pr_url(self):
        """Test status check when PR URL is in trace."""
        provider = GitHubIssueDispatchProvider()

        task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="completed",
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={
                "issue_url": "https://github.com/owner/repo/issues/123",
                "pr_url": "https://github.com/owner/repo/pull/456",
            },
        )

        result = provider.check_status(task)

        assert result["ok"] is True
        assert result["status"] == "completed"
        assert "PR opened" in result["message"]
        assert "pull/456" in result["message"]

    def test_check_status_with_issue_url_only(self):
        """Test status check when only issue URL is in trace."""
        provider = GitHubIssueDispatchProvider()

        task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="running",
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={
                "issue_url": "https://github.com/owner/repo/issues/123",
            },
        )

        result = provider.check_status(task)

        assert result["ok"] is True
        assert result["status"] == "running"
        assert "Dispatch issue created" in result["message"]

    def test_check_status_no_trace(self):
        """Test status check when no trace information available."""
        provider = GitHubIssueDispatchProvider()

        task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="created",
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={},
        )

        result = provider.check_status(task)

        assert result["ok"] is True
        assert result["status"] == "created"
        assert "tracked via webhooks" in result["message"]

    def test_cancel_task(self):
        """Test task cancellation."""
        provider = GitHubIssueDispatchProvider()

        task = make_task(
            id="task-123",
            user_id="user-456",
            provider="github_issue_dispatch",
            state="running",
            instruction="Test",
            target_type=None,
            target_ref=None,
            trace={"issue_url": "https://github.com/owner/repo/issues/123"},
        )

        result = provider.cancel_task(task)

        assert result["ok"] is True
        assert result["status"] == "failed"
        assert "cancelled" in result["message"].lower()

    def test_provider_with_custom_token_provider(self):
        """Test provider with custom token provider."""
        mock_token_provider = MagicMock()
        mock_token_provider.get_token.return_value = "custom_token"

        with patch.dict(
            os.environ,
            {"HANDSFREE_AGENT_DISPATCH_REPO": "owner/repo"},
        ):
            provider = GitHubIssueDispatchProvider(token_provider=mock_token_provider)

            assert provider._get_token() == "custom_token"
            mock_token_provider.get_token.assert_called_once()
