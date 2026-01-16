"""Tests for agent command routing."""

import pytest

from handsfree.commands.intent_parser import IntentParser
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.commands.profiles import Profile
from handsfree.commands.router import CommandRouter
from handsfree.db import init_db


@pytest.fixture
def db_conn():
    """Create an in-memory database connection for testing."""
    conn = init_db(":memory:")
    yield conn
    conn.close()


@pytest.fixture
def pending_manager():
    """Create a pending actions manager."""
    return PendingActionManager()


@pytest.fixture
def router(pending_manager, db_conn):
    """Create a command router with database."""
    return CommandRouter(pending_manager, db_conn=db_conn)


@pytest.fixture
def router_no_db(pending_manager):
    """Create a command router without database."""
    return CommandRouter(pending_manager)


@pytest.fixture
def parser():
    """Create an intent parser."""
    return IntentParser()


class TestAgentDelegate:
    """Test agent.delegate command routing."""

    def test_delegate_requires_confirmation(self, router, parser):
        """Test that agent.delegate requires confirmation in workout profile."""
        intent = parser.parse("ask agent to handle issue 42")

        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "needs_confirmation"
        assert "pending_action" in response
        assert "confirm" in response["spoken_text"].lower()

    def test_delegate_no_confirmation_in_default(self, router, parser, test_user_id):
        """Test that agent.delegate doesn't require confirmation in default profile."""
        intent = parser.parse("ask agent to handle issue 42")

        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "task created" in response["spoken_text"].lower()

    def test_delegate_with_issue_target(self, router, parser, test_user_id):
        """Test delegating with issue target."""
        intent = parser.parse("ask agent to fix the bug on issue 42")

        response = router.route(intent, Profile.COMMUTE, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "42" in response["spoken_text"]

    def test_delegate_with_pr_target(self, router, parser, test_user_id):
        """Test delegating with PR target."""
        intent = parser.parse("tell agent to handle PR 99")

        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        # Should mention task creation
        assert (
            "task created" in response["spoken_text"].lower()
            or "pr" in response["spoken_text"].lower()
        )

    def test_delegate_without_db_fails(self, router_no_db, parser):
        """Test that delegation fails without database."""
        intent = parser.parse("ask agent to handle issue 42")

        response = router_no_db.route(intent, Profile.DEFAULT)

        assert response["status"] == "error"
        assert "not available" in response["spoken_text"].lower()


class TestAgentStatus:
    """Test agent.status command routing."""

    def test_status_no_tasks(self, router, parser, test_user_id):
        """Test status with no tasks."""
        intent = parser.parse("agent status")

        response = router.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "no agent tasks" in response["spoken_text"].lower()

    def test_status_with_tasks(self, router, parser, db_conn, test_user_id):
        """Test status with existing tasks."""
        # First create a task using the agent service directly
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        service.delegate(user_id=test_user_id, instruction="test", provider="mock")

        # Now check status
        status_intent = parser.parse("agent status")
        response = router.route(status_intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "1 task" in response["spoken_text"]

    def test_status_without_db_fails(self, router_no_db, parser):
        """Test that status fails without database."""
        intent = parser.parse("agent status")

        response = router_no_db.route(intent, Profile.DEFAULT)

        assert response["status"] == "ok"
        assert "not available" in response["spoken_text"].lower()

    def test_status_alternate_phrasings(self, router, parser):
        """Test alternate phrasings for status."""
        # Test "what's the agent doing"
        intent1 = parser.parse("what's the agent doing")
        response1 = router.route(intent1, Profile.DEFAULT)
        assert response1["status"] == "ok"

        # Test "summarize agent progress"
        intent2 = parser.parse("summarize agent progress")
        response2 = router.route(intent2, Profile.DEFAULT)
        assert response2["status"] == "ok"


class TestAgentIntentParsing:
    """Test that agent intents are correctly parsed."""

    def test_parse_delegate_with_issue(self, parser):
        """Test parsing delegation with issue."""
        intent = parser.parse("ask agent to fix the bug on issue 42")

        assert intent.name == "agent.delegate"
        assert intent.entities["issue_number"] == 42
        assert "fix the bug" in intent.entities["instruction"]

    def test_parse_delegate_with_pr(self, parser):
        """Test parsing delegation with PR."""
        intent = parser.parse("tell agent to review PR 99")

        assert intent.name == "agent.delegate"
        assert intent.entities["pr_number"] == 99

    def test_parse_delegate_copilot_specific(self, parser):
        """Test parsing delegation with copilot provider."""
        intent = parser.parse("tell copilot to handle issue 42")

        assert intent.name == "agent.delegate"
        assert intent.entities["issue_number"] == 42
        assert intent.entities.get("provider") == "copilot"

    def test_parse_agent_status(self, parser):
        """Test parsing agent status."""
        intent = parser.parse("agent status")

        assert intent.name == "agent.status"

    def test_parse_whats_agent_doing(self, parser):
        """Test parsing 'what's the agent doing'."""
        intent = parser.parse("what's the agent doing")

        assert intent.name == "agent.status"


class TestAgentConfirmationFlow:
    """Test agent delegation confirmation flow."""

    def test_confirmation_summary_for_issue(self, router, parser):
        """Test confirmation summary for issue delegation in workout profile."""
        intent = parser.parse("ask agent to fix bug issue 42")

        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "needs_confirmation"
        summary = response["pending_action"]["summary"]
        assert "42" in summary
        assert "issue" in summary.lower()

    def test_confirmation_summary_for_pr(self, router, parser):
        """Test confirmation summary for PR delegation in workout profile."""
        intent = parser.parse("tell agent to handle PR 99")

        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "needs_confirmation"
        summary = response["pending_action"]["summary"]
        assert "99" in summary
        assert "pr" in summary.lower()

    def test_confirmation_summary_without_target(self, router, parser):
        """Test confirmation summary without specific target."""
        # This might not match any pattern, but if it does:
        intent = parser.parse("tell agent to help")

        # Check if it was parsed as agent.delegate
        if intent.name == "agent.delegate":
            # Use WORKOUT profile which requires confirmation
            response = router.route(intent, Profile.WORKOUT)
            assert response["status"] == "needs_confirmation"
            assert "pending_action" in response


class TestAgentPause:
    """Test agent.pause command routing."""

    def test_pause_without_task_id(self, router, parser, db_conn, test_user_id):
        """Test pausing most recent running task."""
        # Create and start a task
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        result = service.delegate(user_id=test_user_id, instruction="test", provider="mock")
        task_id = result["task_id"]

        # Transition to running state
        from handsfree.db.agent_tasks import update_agent_task_state

        update_agent_task_state(conn=db_conn, task_id=task_id, new_state="running")

        # Pause the task
        intent = parser.parse("pause agent")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "paused" in response["spoken_text"].lower()

        # Verify task state
        from handsfree.db.agent_tasks import get_agent_task_by_id

        task = get_agent_task_by_id(conn=db_conn, task_id=task_id)
        assert task.state == "needs_input"

    def test_pause_with_task_id(self, router, parser, db_conn, test_user_id):
        """Test pausing specific task by ID."""
        # Create and start a task
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        result = service.delegate(user_id=test_user_id, instruction="test", provider="mock")
        task_id = result["task_id"]

        # Transition to running state
        from handsfree.db.agent_tasks import update_agent_task_state

        update_agent_task_state(conn=db_conn, task_id=task_id, new_state="running")

        # Pause the specific task
        intent = parser.parse(f"pause task {task_id}")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "paused" in response["spoken_text"].lower()

    def test_pause_no_running_tasks(self, router, parser, test_user_id):
        """Test error when no running tasks to pause."""
        intent = parser.parse("pause agent")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "error"
        assert "no running" in response["spoken_text"].lower()

    def test_pause_without_db_fails(self, router_no_db, parser):
        """Test that pause fails without database."""
        intent = parser.parse("pause agent")
        response = router_no_db.route(intent, Profile.DEFAULT)

        assert response["status"] == "error"
        assert "not available" in response["spoken_text"].lower()


class TestAgentResume:
    """Test agent.resume command routing."""

    def test_resume_without_task_id(self, router, parser, db_conn, test_user_id):
        """Test resuming most recent paused task."""
        # Create, start, and pause a task
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        result = service.delegate(user_id=test_user_id, instruction="test", provider="mock")
        task_id = result["task_id"]

        # Transition to running then pause
        from handsfree.db.agent_tasks import update_agent_task_state

        update_agent_task_state(conn=db_conn, task_id=task_id, new_state="running")
        update_agent_task_state(conn=db_conn, task_id=task_id, new_state="needs_input")

        # Resume the task
        intent = parser.parse("resume agent")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "resumed" in response["spoken_text"].lower()

        # Verify task state
        from handsfree.db.agent_tasks import get_agent_task_by_id

        task = get_agent_task_by_id(conn=db_conn, task_id=task_id)
        assert task.state == "running"

    def test_resume_with_task_id(self, router, parser, db_conn, test_user_id):
        """Test resuming specific task by ID."""
        # Create, start, and pause a task
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        result = service.delegate(user_id=test_user_id, instruction="test", provider="mock")
        task_id = result["task_id"]

        # Transition to running then pause
        from handsfree.db.agent_tasks import update_agent_task_state

        update_agent_task_state(conn=db_conn, task_id=task_id, new_state="running")
        update_agent_task_state(conn=db_conn, task_id=task_id, new_state="needs_input")

        # Resume the specific task
        intent = parser.parse(f"resume task {task_id}")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "resumed" in response["spoken_text"].lower()

    def test_resume_no_paused_tasks(self, router, parser, test_user_id):
        """Test error when no paused tasks to resume."""
        intent = parser.parse("resume agent")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "error"
        assert "no paused" in response["spoken_text"].lower()

    def test_resume_without_db_fails(self, router_no_db, parser):
        """Test that resume fails without database."""
        intent = parser.parse("resume agent")
        response = router_no_db.route(intent, Profile.DEFAULT)

        assert response["status"] == "error"
        assert "not available" in response["spoken_text"].lower()



