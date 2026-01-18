"""Tests for agent provider selection and trace scaffolding."""

import json

import pytest

from handsfree.commands.intent_parser import IntentParser
from handsfree.db import init_db
from handsfree.db.agent_tasks import get_agent_task_by_id


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


class TestProviderSelection:
    """Test provider selection from intent entities."""

    def test_copilot_provider_from_intent(self, db_conn, parser):
        """Test that 'tell copilot to...' creates task with provider=copilot."""
        from handsfree.agents.service import AgentService

        # Parse intent
        intent = parser.parse("tell copilot to handle issue 123")

        assert intent.name == "agent.delegate"
        assert intent.entities.get("provider") == "copilot"
        assert intent.entities.get("issue_number") == 123

        # Create task via AgentService
        service = AgentService(db_conn)
        result = service.delegate(
            user_id="test-user",
            instruction=intent.entities.get("instruction", "handle"),
            provider=intent.entities.get("provider", "copilot"),
            target_type="issue",
            target_ref="#123",
        )

        # Verify task was created with correct provider
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.provider == "copilot"
        # Task should auto-start to "running" state
        assert task.state == "running"
        assert task.target_type == "issue"
        assert task.target_ref == "#123"

    def test_default_provider_when_not_specified(self, db_conn, parser):
        """Test that provider defaults to copilot when not specified."""
        from handsfree.agents.service import AgentService

        # Parse intent without explicit provider
        intent = parser.parse("ask agent to fix issue 456")

        assert intent.name == "agent.delegate"
        assert intent.entities.get("provider") is None  # Not in entities
        assert intent.entities.get("issue_number") == 456

        # Create task with None provider (should use default)
        service = AgentService(db_conn)
        result = service.delegate(
            user_id="test-user",
            instruction=intent.entities.get("instruction", "fix"),
            provider=intent.entities.get("provider"),  # None - use default
            target_type="issue",
            target_ref="#456",
        )

        # Verify task was created with copilot provider (default)
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.provider == "copilot"

    def test_env_var_overrides_default_provider(self, db_conn, monkeypatch):
        """Test that HANDSFREE_AGENT_DEFAULT_PROVIDER env var overrides default."""
        from handsfree.agents.service import AgentService

        # Set environment variable to use mock provider
        monkeypatch.setenv("HANDSFREE_AGENT_DEFAULT_PROVIDER", "mock")

        # Create task without specifying provider
        service = AgentService(db_conn)
        result = service.delegate(
            user_id="test-user",
            instruction="test task",
            provider=None,  # Use env var default
        )

        # Verify task was created with mock provider from env var
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.provider == "mock"
        assert task.state == "running"

    def test_explicit_provider_overrides_env_var(self, db_conn, monkeypatch):
        """Test that explicit provider argument overrides env var."""
        from handsfree.agents.service import AgentService

        # Set environment variable to use mock provider
        monkeypatch.setenv("HANDSFREE_AGENT_DEFAULT_PROVIDER", "mock")

        # Create task with explicit copilot provider (should override env var)
        service = AgentService(db_conn)
        result = service.delegate(
            user_id="test-user",
            instruction="test task",
            provider="copilot",  # Explicit provider overrides env var
        )

        # Verify task was created with copilot provider (explicit arg)
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.provider == "copilot"
        assert task.state == "running"


class TestTraceScaffolding:
    """Test trace field storage."""

    def test_trace_stores_intent_and_entities(self, db_conn):
        """Test that trace stores parsed intent and entities."""
        from datetime import UTC, datetime

        from handsfree.agents.service import AgentService

        # Create task with trace
        service = AgentService(db_conn)

        trace = {
            "transcript": "tell copilot to handle issue 123",
            "intent_name": "agent.delegate",
            "entities": {
                "instruction": "handle",
                "issue_number": 123,
                "provider": "copilot",
            },
            "created_at": datetime.now(UTC).isoformat(),
        }

        result = service.delegate(
            user_id="test-user",
            instruction="handle",
            provider="copilot",
            target_type="issue",
            target_ref="#123",
            trace=trace,
        )

        # Verify trace was stored
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.trace is not None
        assert task.trace["transcript"] == "tell copilot to handle issue 123"
        assert task.trace["intent_name"] == "agent.delegate"
        assert "created_at" in task.trace
        assert "entities" in task.trace
        assert task.trace["entities"]["provider"] == "copilot"
        assert task.trace["entities"]["issue_number"] == 123

    def test_trace_is_json_serializable(self, db_conn):
        """Test that trace can be serialized to JSON."""
        from datetime import UTC, datetime

        from handsfree.agents.service import AgentService

        # Create task with trace
        service = AgentService(db_conn)

        trace = {
            "transcript": "test command",
            "intent_name": "agent.delegate",
            "entities": {"instruction": "test", "provider": "copilot"},
            "created_at": datetime.now(UTC).isoformat(),
        }

        result = service.delegate(
            user_id="test-user",
            instruction="test",
            provider="copilot",
            trace=trace,
        )

        # Verify trace can be serialized
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.trace is not None

        # Ensure it can be serialized to JSON
        json_str = json.dumps(task.trace)
        assert json_str is not None

        # Ensure it can be deserialized
        deserialized = json.loads(json_str)
        assert deserialized["transcript"] == "test command"
        assert deserialized["entities"]["provider"] == "copilot"


class TestTargetReferenceNormalization:
    """Test target reference format."""

    def test_target_ref_stores_canonical_format(self, db_conn):
        """Test that target_ref is stored in canonical format."""
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)

        # Create task with target_ref
        result = service.delegate(
            user_id="test-user",
            instruction="handle",
            provider="copilot",
            target_type="issue",
            target_ref="#123",  # For now, just #123 (repo would come from context)
        )

        # Verify target_ref format
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.target_ref == "#123"
        assert task.target_type == "issue"


class TestStateCreation:
    """Test that tasks are created with correct initial state."""

    def test_task_created_with_initial_state(self, db_conn):
        """Test that new tasks auto-start to 'running' state."""
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)

        result = service.delegate(
            user_id="test-user",
            instruction="test",
            provider="copilot",
        )

        # Verify state - tasks now auto-start to "running"
        task_id = result["task_id"]
        task = get_agent_task_by_id(db_conn, task_id)

        assert task is not None
        assert task.state == "running"
        assert result["state"] == "running"
