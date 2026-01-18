"""Integration tests for agent delegation with environment variable configuration."""

import json

import pytest
import respx
from httpx import Response

from handsfree.commands.intent_parser import IntentParser
from handsfree.db import init_db
from handsfree.db.agent_tasks import get_agent_task_by_id
from handsfree.db.notifications import list_notifications


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def parser():
    """Create an intent parser."""
    return IntentParser()


class TestAgentDelegationWithEnvVar:
    """Test agent delegation using environment variable configuration."""

    def test_github_issue_dispatch_via_env_var(self, db_conn, monkeypatch):
        """Test that github_issue_dispatch provider is used when set via env var."""
        from handsfree.agents.service import AgentService

        # Set up environment variables
        monkeypatch.setenv("HANDSFREE_AGENT_DEFAULT_PROVIDER", "github_issue_dispatch")
        monkeypatch.setenv("HANDSFREE_AGENT_DISPATCH_REPO", "test-owner/test-repo")
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token-for-test")

        # Mock GitHub API
        with respx.mock:
            # Mock create issue endpoint
            create_issue_route = respx.post(
                "https://api.github.com/repos/test-owner/test-repo/issues"
            ).mock(
                return_value=Response(
                    200,
                    json={
                        "number": 42,
                        "html_url": "https://github.com/test-owner/test-repo/issues/42",
                    },
                )
            )

            # Create task via AgentService without specifying provider
            service = AgentService(db_conn)
            result = service.delegate(
                user_id="test-user",
                instruction="Fix the authentication bug",
                provider=None,  # Should use env var default
            )

            # Verify task was created with github_issue_dispatch provider
            task_id = result["task_id"]
            task = get_agent_task_by_id(db_conn, task_id)

            assert task is not None
            assert task.provider == "github_issue_dispatch"
            assert task.state == "running"
            assert result["provider"] == "github_issue_dispatch"

            # Verify GitHub API was called
            assert create_issue_route.called
            request = create_issue_route.calls[0].request
            request_body = json.loads(request.content)
            
            # Verify issue metadata
            assert "Fix the authentication bug" in request_body["title"]
            assert task_id in request_body["body"]
            assert "agent_task_metadata" in request_body["body"]
            assert "copilot-agent" in request_body["labels"]

            # Verify task trace has dispatch info
            assert task.trace is not None
            assert task.trace.get("provider") == "github_issue_dispatch"
            assert task.trace.get("issue_number") == 42
            assert task.trace.get("issue_url") == "https://github.com/test-owner/test-repo/issues/42"

    def test_explicit_provider_overrides_env_var(self, db_conn, monkeypatch):
        """Test that explicit provider argument overrides env var."""
        from handsfree.agents.service import AgentService

        # Set up environment variable for github_issue_dispatch
        monkeypatch.setenv("HANDSFREE_AGENT_DEFAULT_PROVIDER", "github_issue_dispatch")
        monkeypatch.setenv("HANDSFREE_AGENT_DISPATCH_REPO", "test-owner/test-repo")

        # Create task with explicit mock provider (should override env var)
        service = AgentService(db_conn)
        result = service.delegate(
            user_id="test-user",
            instruction="Test task",
            provider="mock",  # Explicit provider overrides env var
        )

        # Verify task was created with mock provider (not github_issue_dispatch)
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.provider == "mock"
        assert result["provider"] == "mock"

    def test_task_lifecycle_with_github_issue_dispatch(self, db_conn, monkeypatch):
        """Test complete lifecycle: delegate -> dispatch issue -> PR opened -> task completed."""
        from handsfree.agents.service import AgentService
        from handsfree.api import _correlate_pr_with_agent_tasks
        from handsfree import api

        # Mock get_db to return our test db_conn
        monkeypatch.setattr(api, "get_db", lambda: db_conn)

        # Set up environment variables
        monkeypatch.setenv("HANDSFREE_AGENT_DEFAULT_PROVIDER", "github_issue_dispatch")
        monkeypatch.setenv("HANDSFREE_AGENT_DISPATCH_REPO", "test-owner/test-repo")
        monkeypatch.setenv("GITHUB_TOKEN", "fake-token-for-test")

        # Mock GitHub API
        with respx.mock:
            # Mock create issue endpoint
            respx.post("https://api.github.com/repos/test-owner/test-repo/issues").mock(
                return_value=Response(
                    200,
                    json={
                        "number": 99,
                        "html_url": "https://github.com/test-owner/test-repo/issues/99",
                    },
                )
            )

            # Step 1: Delegate task (should create GitHub issue)
            service = AgentService(db_conn)
            result = service.delegate(
                user_id="test-user",
                instruction="Implement new feature",
                provider=None,  # Use env var default
            )

            task_id = result["task_id"]
            task = get_agent_task_by_id(db_conn, task_id)

            assert task is not None
            assert task.provider == "github_issue_dispatch"
            assert task.state == "running"
            assert task.trace.get("issue_number") == 99

            # Step 2: Simulate PR opened event with issue reference
            normalized = {
                "event_type": "pull_request",
                "action": "opened",
                "pr_number": 123,
                "pr_url": "https://github.com/test-owner/test-repo/pull/123",
                "repo": "test-owner/test-repo",
            }

            raw_payload = {
                "pull_request": {
                    "number": 123,
                    "body": "Fixes #99\n\nImplements the new feature as requested.",
                }
            }

            # Correlate PR with task
            _correlate_pr_with_agent_tasks(normalized, raw_payload)

            # Step 3: Verify task was marked as completed
            updated_task = get_agent_task_by_id(db_conn, task_id)
            assert updated_task.state == "completed"
            assert updated_task.trace.get("pr_url") == "https://github.com/test-owner/test-repo/pull/123"
            assert updated_task.trace.get("pr_number") == 123
            assert updated_task.trace.get("correlated_via") == "issue_reference"

            # Step 4: Verify completion notification was created
            notifications = list_notifications(conn=db_conn, user_id="test-user", limit=10)
            completion_notifications = [
                n for n in notifications if n.event_type == "task_completed"
            ]
            assert len(completion_notifications) > 0
            assert task_id in completion_notifications[0].message
            assert "PR:" in completion_notifications[0].message


class TestCorrelationWithMetadata:
    """Test PR correlation using metadata markers."""

    def test_pr_correlation_via_metadata_marker(self, db_conn, monkeypatch):
        """Test that PR is correlated via agent_task_metadata comment."""
        from handsfree.agents.service import AgentService
        from handsfree.api import _correlate_pr_with_agent_tasks
        from handsfree import api

        # Mock get_db to return our test db_conn
        monkeypatch.setattr(api, "get_db", lambda: db_conn)

        # Create a task with copilot provider
        service = AgentService(db_conn)
        result = service.delegate(
            user_id="test-user",
            instruction="Fix bug",
            provider="copilot",
        )

        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)
        assert task.state == "running"

        # Simulate PR opened event with metadata marker
        pr_body = f"""
# Fix for authentication bug

This PR fixes the authentication issue.

<!-- agent_task_metadata
{{"task_id": "{task_id}", "user_id": "test-user", "provider": "copilot"}}
-->
"""

        normalized = {
            "event_type": "pull_request",
            "action": "opened",
            "pr_number": 456,
            "pr_url": "https://github.com/test-owner/test-repo/pull/456",
            "repo": "test-owner/test-repo",
        }

        raw_payload = {
            "pull_request": {
                "number": 456,
                "body": pr_body,
            }
        }

        # Correlate PR with task
        _correlate_pr_with_agent_tasks(normalized, raw_payload)

        # Verify task was marked as completed
        updated_task = get_agent_task_by_id(db_conn, task_id)
        assert updated_task.state == "completed"
        assert updated_task.trace.get("pr_url") == "https://github.com/test-owner/test-repo/pull/456"
        assert updated_task.trace.get("pr_number") == 456
        assert updated_task.trace.get("correlated_via") == "pr_metadata"
