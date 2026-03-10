"""Tests for agent command routing."""

import pytest

from handsfree.agent_providers import (
    IPFSAccelerateMCPAgentProvider,
    IPFSDatasetsMCPAgentProvider,
    IPFSKitMCPAgentProvider,
)
from handsfree.commands.intent_parser import IntentParser, ParsedIntent
from handsfree.commands.pending_actions import PendingActionManager
from handsfree.commands.profiles import Profile
from handsfree.commands.router import CommandRouter
from handsfree.db import init_db
from handsfree.db.agent_tasks import (
    create_agent_task,
    get_agent_task_by_id,
    update_agent_task_state,
)
from test_mcp_ipfs_provider import _FakeMCPClient


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

    def test_direct_dataset_phrase_routes_to_mcp_provider(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Test direct dataset phrase is routed through the datasets MCP provider."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")
        fake_provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_datasets_mcp" else None,
        )
        intent = parser.parse("find legal datasets")

        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Expanded legal query"
        assert response["intent"]["entities"]["task_id"] is not None
        assert response["intent"]["entities"]["state"] == "completed"
        assert response["cards"][0]["title"] == "IPFS Datasets dataset discovery"

    def test_direct_ipfs_pin_local_phrase_routes_with_direct_import_mode(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Local IPFS pin phrases should request direct-import execution."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")

        class _FakeKitAdapter:
            def pin(self, cid: str, **kwargs):
                return {"ok": True, "cid": cid, "options": kwargs}

            def unpin(self, cid: str, **kwargs):
                return {"ok": True, "cid": cid, "options": kwargs}

        fake_provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_kit_mcp" else None,
        )
        monkeypatch.setattr("handsfree.agent_providers.get_ipfs_kit_adapter", lambda: _FakeKitAdapter())
        intent = parser.parse("pin bafytestcid on ipfs locally")

        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["mcp_execution_mode"] == "direct_import"
        task = get_agent_task_by_id(db_conn, response["intent"]["entities"]["task_id"])
        assert task is not None
        assert task.trace["mcp_execution_mode"] == "direct_import"
        assert task.trace["mcp_cid"] == "bafytestcid"

    def test_direct_ipfs_pin_local_phrase_falls_back_to_remote_when_direct_disabled(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Local IPFS pin phrases should resolve to remote mode when direct execution is disabled."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_ALLOW_DIRECT_EXECUTION", "false")

        fake_provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_kit_mcp" else None,
        )
        intent = parser.parse("pin bafytestcid on ipfs locally")

        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["mcp_execution_mode"] == "mcp_remote"
        assert "local execution isn't available" in response["spoken_text"].lower()
        assert "Execution: Remote (local unavailable)" in response["cards"][0]["lines"]
        task = get_agent_task_by_id(db_conn, response["intent"]["entities"]["task_id"])
        assert task is not None
        assert task.trace["mcp_execution_mode"] == "mcp_remote"
        assert task.trace["mcp_cid"] == "bafytestcid"

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

        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

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

    def test_status_alternate_phrasings(self, router, parser, test_user_id):
        """Test alternate phrasings for status."""
        # Test "what's the agent doing"
        intent1 = parser.parse("what's the agent doing")
        response1 = router.route(intent1, Profile.DEFAULT, user_id=test_user_id)
        assert response1["status"] == "ok"

        # Test "summarize agent progress"
        intent2 = parser.parse("summarize agent progress")
        response2 = router.route(intent2, Profile.DEFAULT, user_id=test_user_id)
        assert response2["status"] == "ok"

    def test_status_includes_structured_mcp_results(self, router, parser, db_conn, test_user_id):
        """Completed MCP tasks should render structured result lines and debug output."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Expanded legal query",
                "mcp_result_output": {
                    "message": "Expanded legal query",
                    "status": "success",
                    "expanded_queries": ["legal datasets", "legal datasets statutes"],
                },
            },
        )

        intent = parser.parse("agent status")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert response["cards"][0]["lines"][1] == "message: Expanded legal query"
        assert "expanded_queries: legal datasets, legal datasets statutes" in response["cards"][0]["lines"]

    def test_results_saved_view_returns_cards(self, router, parser, db_conn, test_user_id):
        """Saved result views should surface completed MCP results."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Expanded legal query",
                "mcp_result_output": {
                    "message": "Expanded legal query",
                    "expanded_queries": ["legal datasets", "legal datasets statutes"],
                },
            },
        )

        intent = parser.parse("show latest dataset discoveries")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "1 datasets result" in response["spoken_text"].lower()
        assert response["intent"]["entities"]["view"] == "datasets"
        assert response["cards"][0]["title"] == "IPFS Datasets dataset discovery"
        assert "expanded_queries: legal datasets, legal datasets statutes" in response["cards"][0]["lines"]
        assert response["cards"][0]["deep_link"] == f"/v1/agents/tasks/{task.id}"
        assert "show task details for that result" in response["cards"][0]["actions"]
        assert "rerun that dataset search with labor law datasets remotely" in response["cards"][0]["actions"]
        assert response["cards"][0]["action_items"][0]["id"] == "open_result"
        assert response["cards"][0]["action_items"][-1]["id"] == "rerun_dataset_search"

    def test_results_saved_view_supports_result_envelope(self, router, parser, db_conn, test_user_id):
        """Saved result views should render envelope-backed results."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123 on ipfs",
            trace={
                "mcp_capability": "ipfs_pin",
                "provider_label": "IPFS Kit",
                "mcp_result_envelope": {
                    "summary": "Pinned bafy123.",
                    "structured_output": {"message": "Pinned bafy123.", "cid": "bafy123"},
                    "artifact_refs": {"result_cid": "bafy123"},
                    "follow_up_actions": [{"id": "read_cid", "label": "Read CID", "phrase": "read the cid"}],
                },
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="completed")

        intent = ParsedIntent(name="agent.results", confidence=1.0, entities={"view": None})
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert response["cards"][0]["deep_link"] == "ipfs://bafy123"
        assert response["cards"][0]["lines"][0] == "message: Pinned bafy123."
        assert response["cards"][0]["action_items"][0]["id"] == "read_cid"

    def test_results_saved_view_renders_wearables_connectivity_receipt(
        self, router, parser, db_conn, test_user_id
    ):
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_accelerate_mcp",
            instruction="inspect connected wearable",
            trace={
                "mcp_capability": "workflow",
                "provider_label": "IPFS Accelerate",
                "mcp_result_envelope": {
                    "summary": "Wearables bridge connectivity receipt captured for Ray-Ban Meta.",
                    "structured_output": {
                        "workflow": "wearables_bridge_connectivity",
                        "device_id": "AA:BB",
                        "device_name": "Ray-Ban Meta",
                        "target_connection_state": "connected",
                        "target_rssi": -42,
                        "cid": "bafyreceipt",
                    },
                    "artifact_refs": {"result_cid": "bafyreceipt"},
                },
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="completed")

        intent = ParsedIntent(name="agent.results", confidence=1.0, entities={"view": None})
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert response["cards"][0]["title"] == "Wearables Connectivity Receipt"
        assert "device: Ray-Ban Meta" in response["cards"][0]["lines"]
        assert response["cards"][0]["deep_link"] == "ipfs://bafyreceipt"
        assert response["cards"][0]["action_items"][0]["id"] == "mobile_open_wearables_diagnostics"
        assert response["cards"][0]["action_items"][1]["id"] == "mobile_reconnect_wearables_target"
        assert response["cards"][0]["action_items"][6]["label"] == "Read Receipt"

    def test_results_saved_view_supports_next_navigation(
        self, router, parser, db_conn, test_user_id
    ):
        """Saved result views should participate in session navigation."""
        dataset_task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="first legal dataset query",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        fetch_task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_accelerate_mcp",
            instruction="fetch climate regulations",
            trace={"mcp_capability": "agentic_fetch", "provider_label": "IPFS Accelerate"},
        )
        for task, preview in (
            (dataset_task, "First legal result"),
            (fetch_task, "Second fetch result"),
        ):
            update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
            update_agent_task_state(
                conn=db_conn,
                task_id=task.id,
                new_state="completed",
                trace_update={
                    "mcp_result_preview": preview,
                    "mcp_result_output": {"message": preview},
                },
            )

        initial = router.route(
            parser.parse("agent results"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="results-session",
        )
        next_response = router.route(
            parser.parse("next result"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="results-session",
        )

        assert initial["status"] == "ok"
        assert len(initial["cards"]) == 2
        assert next_response["status"] == "ok"
        assert len(next_response["cards"]) == 1
        assert next_response["cards"][0]["lines"][0] == "message: First legal result"

    def test_open_current_result_uses_selected_card(
        self, router, parser, db_conn, test_user_id
    ):
        """Open-result follow-up should return the current result card."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Expanded legal query"},
        )

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="open-result-session",
        )
        response = router.route(
            parser.parse("open that result"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="open-result-session",
        )

        assert response["status"] == "ok"
        assert response["cards"][0]["deep_link"] == f"/v1/agents/tasks/{task.id}"
        assert response["debug"]["tool_calls"][0]["deep_link"] == f"/v1/agents/tasks/{task.id}"

    def test_show_task_details_for_current_result(
        self, router, parser, db_conn, test_user_id
    ):
        """Result-detail follow-up should load the selected task from the DB."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Expanded legal query",
                "mcp_result_output": {
                    "message": "Expanded legal query",
                    "expanded_queries": ["legal datasets", "legal datasets statutes"],
                },
            },
        )

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="details-result-session",
        )
        response = router.route(
            parser.parse("show task details for that result"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="details-result-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["task_id"] == task.id
        assert response["cards"][0]["title"] == "IPFS Datasets details"
        assert response["cards"][0]["lines"][0] == "State: completed"
        assert "Capability: dataset discovery" in response["cards"][0]["lines"]
        assert "message: Expanded legal query" in response["cards"][0]["lines"]

    def test_show_available_actions_for_current_result(
        self, router, parser, db_conn, test_user_id
    ):
        """Result-action help should reflect the current result's available follow-ups."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="add this file to ipfs",
            trace={"mcp_capability": "ipfs_add", "provider_label": "IPFS Kit", "mcp_cid": "bafy123"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Added to IPFS",
                "mcp_result_output": {"message": "Added to IPFS", "cid": "bafy123"},
            },
        )

        router.route(
            parser.parse("show recent ipfs results"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="result-actions-session",
        )
        response = router.route(
            parser.parse("what can i do with that result"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="result-actions-session",
        )

        assert response["status"] == "ok"
        assert response["cards"][0]["title"] == "Available result actions"
        assert "read the cid" in response["cards"][0]["lines"]
        assert "share that cid" in response["debug"]["tool_calls"][0]["actions"]
        assert "pin that" in response["debug"]["tool_calls"][0]["actions"]
        assert response["cards"][0]["action_items"][0]["id"] == "open_result"
        assert response["debug"]["tool_calls"][0]["action_items"][4]["id"] == "read_cid"

    def test_show_another_result_like_this_returns_related_results(
        self, router, parser, db_conn, test_user_id
    ):
        """Related-result follow-up should reuse the selected result's provider/capability."""
        first_task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets about privacy",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        second_task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets about labor law",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        for task, preview in (
            (first_task, "Privacy datasets"),
            (second_task, "Labor datasets"),
        ):
            update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
            update_agent_task_state(
                conn=db_conn,
                task_id=task.id,
                new_state="completed",
                trace_update={
                    "mcp_result_preview": preview,
                    "mcp_result_output": {"message": preview},
                },
            )

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="related-result-session",
        )
        response = router.route(
            parser.parse("show another result like this"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="related-result-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["provider"] == "ipfs_datasets_mcp"
        assert response["intent"]["entities"]["capability"] == "dataset_discovery"
        assert response["intent"]["entities"]["source_task_id"] == second_task.id
        assert response["cards"][0]["task_id"] == first_task.id
        assert response["cards"][0]["lines"][0] == "message: Privacy datasets"

    def test_rerun_current_workflow_requires_confirmation_in_workout(
        self, router, parser, db_conn, test_user_id
    ):
        """Workflow reruns should require confirmation in workout profile."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_accelerate_mcp",
            instruction="discover and fetch climate regulations from https://example.com",
            trace={"mcp_capability": "agentic_fetch", "provider_label": "IPFS Accelerate"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Agentic fetch started and completed"},
        )

        router.route(
            parser.parse("summarize latest fetches"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="rerun-confirm-session",
        )
        response = router.route(
            parser.parse("rerun that workflow"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="rerun-confirm-session",
        )

        assert response["status"] == "needs_confirmation"
        assert "rerun the current workflow result" in response["pending_action"]["summary"].lower()

    def test_rerun_current_workflow_creates_new_accelerate_task(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Workflow reruns should clone the selected accelerate task context."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_ACCELERATE_MCP", "true")
        fake_provider = IPFSAccelerateMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_accelerate_mcp" else None,
        )

        source_task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_accelerate_mcp",
            instruction="discover and fetch climate regulations from https://example.com",
            trace={
                "mcp_capability": "agentic_fetch",
                "provider_label": "IPFS Accelerate",
                "mcp_input": "climate regulations",
                "mcp_seed_url": "https://example.com",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=source_task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=source_task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Agentic fetch started and completed",
                "mcp_result_output": {
                    "message": "Agentic fetch started and completed",
                    "status": "success",
                },
            },
        )

        initial = router.route(
            parser.parse("summarize latest fetches"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="rerun-session",
        )
        response = router.route(
            parser.parse("rerun that workflow"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="rerun-session",
        )

        assert initial["status"] == "ok"
        assert initial["cards"][0]["task_id"] == source_task.id
        assert response["status"] == "ok"
        assert "completed" in response["spoken_text"].lower()
        assert response["intent"]["entities"]["source_task_id"] == source_task.id
        rerun_task_id = response["intent"]["entities"]["task_id"]
        assert rerun_task_id != source_task.id
        assert response["debug"]["tool_calls"][0]["provider"] == "ipfs_accelerate_mcp"

        rerun_task = get_agent_task_by_id(db_conn, rerun_task_id)
        assert rerun_task is not None
        assert rerun_task.provider == "ipfs_accelerate_mcp"
        assert rerun_task.state == "completed"
        assert rerun_task.instruction == source_task.instruction
        assert rerun_task.trace is not None
        assert rerun_task.trace["source_task_id"] == source_task.id
        assert rerun_task.trace["rerun_of_task_id"] == source_task.id
        assert rerun_task.trace["mcp_capability"] == "agentic_fetch"
        assert rerun_task.trace["mcp_seed_url"] == "https://example.com"

    def test_rerun_current_fetch_with_new_url_requires_confirmation_in_workout(
        self, router, parser, db_conn, test_user_id
    ):
        """Parameterized fetch reruns should require confirmation in workout profile."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_accelerate_mcp",
            instruction="discover and fetch climate regulations from https://example.com",
            trace={
                "mcp_capability": "agentic_fetch",
                "provider_label": "IPFS Accelerate",
                "mcp_input": "climate regulations",
                "mcp_seed_url": "https://example.com",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Agentic fetch started and completed"},
        )

        router.route(
            parser.parse("summarize latest fetches"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="rerun-fetch-confirm-session",
        )
        response = router.route(
            parser.parse("rerun that fetch with https://example.org"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="rerun-fetch-confirm-session",
        )

        assert response["status"] == "needs_confirmation"
        assert "https://example.org" in response["pending_action"]["summary"]

    def test_rerun_current_fetch_with_new_url_creates_new_accelerate_task(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Fetch reruns should clone target terms and replace only the seed URL."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_ACCELERATE_MCP", "true")
        fake_provider = IPFSAccelerateMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_accelerate_mcp" else None,
        )

        source_task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_accelerate_mcp",
            instruction="discover and fetch climate regulations from https://example.com",
            trace={
                "mcp_capability": "agentic_fetch",
                "provider_label": "IPFS Accelerate",
                "mcp_input": "climate regulations",
                "mcp_seed_url": "https://example.com",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=source_task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=source_task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Agentic fetch started and completed",
                "mcp_result_output": {
                    "message": "Agentic fetch started and completed",
                    "status": "success",
                },
            },
        )

        router.route(
            parser.parse("summarize latest fetches"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="rerun-fetch-session",
        )
        response = router.route(
            parser.parse("rerun that fetch with https://example.org"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="rerun-fetch-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["source_task_id"] == source_task.id
        assert response["intent"]["entities"]["mcp_seed_url"] == "https://example.org"
        rerun_task_id = response["intent"]["entities"]["task_id"]
        rerun_task = get_agent_task_by_id(db_conn, rerun_task_id)
        assert rerun_task is not None
        assert rerun_task.provider == "ipfs_accelerate_mcp"
        assert rerun_task.instruction == "discover and fetch climate regulations from https://example.org"
        assert rerun_task.trace is not None
        assert rerun_task.trace["mcp_capability"] == "agentic_fetch"
        assert rerun_task.trace["mcp_input"] == "climate regulations"
        assert rerun_task.trace["mcp_seed_url"] == "https://example.org"
        assert rerun_task.trace["source_task_id"] == source_task.id

    def test_share_current_result_returns_shareable_cid(
        self, router, parser, db_conn, test_user_id
    ):
        """CID-sharing follow-up should expose a stable share payload."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="add this file to ipfs",
            trace={"mcp_capability": "ipfs_add", "provider_label": "IPFS Kit", "mcp_cid": "bafy123"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Added to IPFS",
                "mcp_result_output": {"message": "Added to IPFS", "cid": "bafy123"},
            },
        )

        router.route(
            parser.parse("show recent ipfs results"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="share-result-session",
        )
        response = router.route(
            parser.parse("share that cid"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="share-result-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["cid"] == "bafy123"
        assert response["cards"][0]["deep_link"] == "ipfs://bafy123"
        assert response["debug"]["tool_calls"][0]["share_payload"]["uri"] == "ipfs://bafy123"
        assert "bafy123" in response["spoken_text"]

    def test_save_current_result_to_ipfs_requires_confirmation_in_workout(
        self, router, parser, db_conn, test_user_id
    ):
        """Saving a selected result to IPFS should require confirmation in workout profile."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Expanded legal query"},
        )

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="save-result-confirm-session",
        )
        response = router.route(
            parser.parse("save that result to ipfs"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="save-result-confirm-session",
        )

        assert response["status"] == "needs_confirmation"
        assert "save the current result to ipfs" in response["pending_action"]["summary"].lower()

    def test_save_current_result_to_ipfs_creates_ipfs_add_task(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Saving a selected result should delegate an IPFS add with serialized result content."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        fake_provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_kit_mcp" else None,
        )

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Expanded legal query",
                "mcp_result_output": {
                    "message": "Expanded legal query",
                    "expanded_queries": ["legal datasets", "legal datasets statutes"],
                },
            },
        )

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="save-result-session",
        )
        response = router.route(
            parser.parse("save that result to ipfs"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="save-result-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["source_task_id"] == task.id
        save_task_id = response["intent"]["entities"]["task_id"]
        save_task = get_agent_task_by_id(db_conn, save_task_id)
        assert save_task is not None
        assert save_task.provider == "ipfs_kit_mcp"
        assert save_task.trace is not None
        assert save_task.trace["mcp_capability"] == "ipfs_add"
        assert save_task.trace["source_task_id"] == task.id
        assert save_task.trace["saved_result_provider"] == "ipfs_datasets_mcp"
        assert '"result_preview": "Expanded legal query"' in save_task.trace["mcp_input"]

    def test_save_current_result_to_ipfs_locally_uses_direct_import(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Local save-result phrases should create a direct-import IPFS add task."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")

        class _FakeKitAdapter:
            def add_bytes(self, data: bytes, **kwargs):
                return {"cid": "bafylocal999", "size": len(data)}

        fake_provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_kit_mcp" else None,
        )
        monkeypatch.setattr("handsfree.agent_providers.get_ipfs_kit_adapter", lambda: _FakeKitAdapter())

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={"mcp_capability": "dataset_discovery", "provider_label": "IPFS Datasets"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Expanded legal query"},
        )

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="save-result-local-session",
        )
        response = router.route(
            parser.parse("save that result to ipfs locally"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="save-result-local-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["mcp_execution_mode"] == "direct_import"
        save_task = get_agent_task_by_id(db_conn, response["intent"]["entities"]["task_id"])
        assert save_task is not None
        assert save_task.trace["mcp_execution_mode"] == "direct_import"
        assert save_task.trace["mcp_capability"] == "ipfs_add"
        assert save_task.trace["mcp_cid"] == "bafylocal999"

    def test_save_current_result_to_ipfs_serializes_result_envelope(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Saving a selected result should include the envelope in serialized payloads."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        fake_provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_kit_mcp" else None,
        )

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={
                "mcp_capability": "dataset_discovery",
                "provider_label": "IPFS Datasets",
                "mcp_result_envelope": {
                    "summary": "Expanded legal query",
                    "structured_output": {"message": "Expanded legal query"},
                    "follow_up_actions": [{"id": "open_result", "label": "Open Result", "phrase": "open that result"}],
                },
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="completed")

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="save-result-envelope-session",
        )
        response = router.route(
            parser.parse("save that result to ipfs"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="save-result-envelope-session",
        )

        assert response["status"] == "ok"
        save_task = get_agent_task_by_id(db_conn, response["intent"]["entities"]["task_id"])
        assert save_task is not None
        assert '"result_envelope"' in save_task.trace["mcp_input"]

    def test_rerun_current_dataset_search_requires_confirmation_in_workout(
        self, router, parser, db_conn, test_user_id
    ):
        """Parameterized dataset reruns should require confirmation in workout profile."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={
                "mcp_capability": "dataset_discovery",
                "provider_label": "IPFS Datasets",
                "mcp_input": "legal datasets",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Expanded legal query"},
        )

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="rerun-dataset-confirm-session",
        )
        response = router.route(
            parser.parse("rerun that dataset search with labor law datasets"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="rerun-dataset-confirm-session",
        )

        assert response["status"] == "needs_confirmation"
        assert "labor law datasets" in response["pending_action"]["summary"]

    def test_rerun_current_dataset_search_creates_new_dataset_task(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Dataset reruns should replace only the dataset query."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")
        fake_provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_datasets_mcp" else None,
        )

        source_task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_datasets_mcp",
            instruction="find legal datasets",
            trace={
                "mcp_capability": "dataset_discovery",
                "provider_label": "IPFS Datasets",
                "mcp_input": "legal datasets",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=source_task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=source_task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Expanded legal query",
                "mcp_result_output": {
                    "message": "Expanded legal query",
                    "expanded_queries": ["legal datasets", "legal datasets statutes"],
                },
            },
        )

        router.route(
            parser.parse("show latest dataset discoveries"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="rerun-dataset-session",
        )
        response = router.route(
            parser.parse("rerun that dataset search with labor law datasets"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="rerun-dataset-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["source_task_id"] == source_task.id
        assert response["intent"]["entities"]["mcp_input"] == "labor law datasets"
        rerun_task_id = response["intent"]["entities"]["task_id"]
        rerun_task = get_agent_task_by_id(db_conn, rerun_task_id)
        assert rerun_task is not None
        assert rerun_task.provider == "ipfs_datasets_mcp"
        assert rerun_task.instruction == "find labor law datasets"
        assert rerun_task.trace is not None
        assert rerun_task.trace["mcp_capability"] == "dataset_discovery"
        assert rerun_task.trace["mcp_input"] == "labor law datasets"
        assert rerun_task.trace["source_task_id"] == source_task.id

    def test_unpin_current_result_requires_confirmation_in_workout(
        self, router, parser, db_conn, test_user_id
    ):
        """Unpin follow-up should require confirmation in workout profile."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="add this file to ipfs",
            trace={"mcp_capability": "ipfs_add", "provider_label": "IPFS Kit", "mcp_cid": "bafy123"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Added to IPFS"},
        )

        router.route(
            parser.parse("show recent ipfs results"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="unpin-confirm-session",
        )
        response = router.route(
            parser.parse("unpin that"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="unpin-confirm-session",
        )

        assert response["status"] == "needs_confirmation"
        assert "unpin the current ipfs result" in response["pending_action"]["summary"].lower()

    def test_unpin_current_result_creates_ipfs_kit_task(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Unpin follow-up should delegate through the IPFS Kit MCP provider."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        fake_provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_kit_mcp" else None,
        )

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="add this file to ipfs",
            trace={"mcp_capability": "ipfs_add", "provider_label": "IPFS Kit", "mcp_cid": "bafy123"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={
                "mcp_result_preview": "Added to IPFS",
                "mcp_result_output": {"message": "Added to IPFS", "cid": "bafy123"},
            },
        )

        router.route(
            parser.parse("show recent ipfs results"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="unpin-session",
        )
        response = router.route(
            parser.parse("unpin that"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="unpin-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["cid"] == "bafy123"
        assert response["debug"]["tool_calls"][0]["pin_action"] == "unpin"

        task_id = response["intent"]["entities"]["task_id"]
        unpin_task = get_agent_task_by_id(db_conn, task_id)
        assert unpin_task is not None
        assert unpin_task.provider == "ipfs_kit_mcp"
        assert unpin_task.trace is not None
        assert unpin_task.trace["mcp_cid"] == "bafy123"
        assert unpin_task.trace["mcp_pin_action"] == "unpin"

    def test_unpin_current_result_locally_uses_direct_import_mode(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Unpin follow-up should propagate direct-import execution hints."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")

        class _FakeKitAdapter:
            def pin(self, cid: str, **kwargs):
                return {"ok": True, "cid": cid, "options": kwargs}

            def unpin(self, cid: str, **kwargs):
                return {"ok": True, "cid": cid, "options": kwargs}

        fake_provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_kit_mcp" else None,
        )
        monkeypatch.setattr("handsfree.agent_providers.get_ipfs_kit_adapter", lambda: _FakeKitAdapter())

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="add this file to ipfs",
            trace={"mcp_capability": "ipfs_add", "provider_label": "IPFS Kit", "mcp_cid": "bafy123"},
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Added to IPFS"},
        )

        router.route(
            parser.parse("show recent ipfs results"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="unpin-local-session",
        )
        response = router.route(
            parser.parse("unpin that locally"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="unpin-local-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["mcp_execution_mode"] == "direct_import"
        task_id = response["intent"]["entities"]["task_id"]
        unpin_task = get_agent_task_by_id(db_conn, task_id)
        assert unpin_task is not None
        assert unpin_task.trace["mcp_execution_mode"] == "direct_import"

    def test_rerun_fetch_remote_uses_mcp_remote_mode(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Fetch reruns should preserve remote execution hints in trace and response."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_ACCELERATE_MCP", "true")
        fake_provider = IPFSAccelerateMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_accelerate_mcp" else None,
        )

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_accelerate_mcp",
            instruction="discover and fetch climate regulations from https://example.org",
            trace={
                "mcp_capability": "agentic_fetch",
                "provider_label": "IPFS Accelerate",
                "mcp_input": "climate regulations",
                "mcp_seed_url": "https://example.org",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Agentic fetch started and completed"},
        )

        router.route(
            parser.parse("show recent fetches"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="rerun-fetch-remote-session",
        )
        response = router.route(
            parser.parse("rerun that fetch with https://example.com via mcp"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="rerun-fetch-remote-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["mcp_execution_mode"] == "mcp_remote"
        rerun_task = get_agent_task_by_id(db_conn, response["intent"]["entities"]["task_id"])
        assert rerun_task is not None
        assert rerun_task.trace["mcp_execution_mode"] == "mcp_remote"
        assert rerun_task.trace["mcp_seed_url"] == "https://example.com"

    def test_read_current_cid_routes_to_ai_read(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Read-CID follow-up should reuse ai.read_cid for IPFS result cards."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123 on ipfs",
            trace={
                "mcp_capability": "ipfs_pin",
                "provider_label": "IPFS Kit",
                "mcp_cid": "bafy123",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Pinned bafy123"},
        )

        class StubExecution:
            capability_id = "ipfs.content.read_ai_output"

            class execution_mode:
                value = "direct_import"

            output = {
                "spoken_text": "Recovered summary text.",
                "headline": "Stored summary",
                "summary": "Recovered summary text.",
                "cid": "bafy123",
                "trace": {"provider": "ipfs_content_router", "operation": "cat", "cid": "bafy123"},
            }

        def stub_execute_ai_request(request, **kwargs):
            assert request.capability_id == "ipfs.content.read_ai_output"
            assert request.options["cid"] == "bafy123"
            return StubExecution()

        monkeypatch.setattr("handsfree.commands.router.execute_ai_request", stub_execute_ai_request)

        router.route(
            parser.parse("show recent ipfs results"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="read-result-session",
        )
        response = router.route(
            parser.parse("read the cid"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="read-result-session",
        )

        assert response["status"] == "ok"
        assert response["spoken_text"] == "Recovered summary text."
        assert response["debug"]["resolved_context"]["cid"] == "bafy123"

    def test_pin_current_result_requires_confirmation_in_workout(
        self, router, parser, db_conn, test_user_id
    ):
        """Pin-result follow-up should require confirmation in workout profile."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123 on ipfs",
            trace={
                "mcp_capability": "ipfs_pin",
                "provider_label": "IPFS Kit",
                "mcp_cid": "bafy123",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Pinned bafy123"},
        )

        router.route(
            parser.parse("show recent ipfs results"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="pin-confirm-session",
        )
        response = router.route(
            parser.parse("pin that"),
            Profile.WORKOUT,
            user_id=test_user_id,
            session_id="pin-confirm-session",
        )

        assert response["status"] == "needs_confirmation"
        assert "pin the current ipfs result" in response["spoken_text"].lower()

    def test_pin_current_result_delegates_to_ipfs_kit(
        self, router, parser, db_conn, test_user_id, monkeypatch
    ):
        """Pin-result follow-up should delegate to ipfs_kit_mcp with the selected CID."""
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        fake_provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_kit_mcp" else None,
        )

        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123 on ipfs",
            trace={
                "mcp_capability": "ipfs_pin",
                "provider_label": "IPFS Kit",
                "mcp_cid": "bafy123",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Pinned bafy123"},
        )

        router.route(
            parser.parse("show recent ipfs results"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="pin-result-session",
        )
        response = router.route(
            parser.parse("pin that"),
            Profile.DEFAULT,
            user_id=test_user_id,
            session_id="pin-result-session",
        )

        assert response["status"] == "ok"
        assert response["intent"]["entities"]["cid"] == "bafy123"
        assert response["cards"][0]["lines"][0] == "CID: bafy123"
        assert fake_provider._client.calls[-1] == ("ipfs_pin_add", {"cid": "bafy123"})  # type: ignore[union-attr]


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

    def test_parse_delegate_ipfs_accelerate_specific(self, parser):
        """Test parsing delegation with MCP-backed IPFS provider alias."""
        intent = parser.parse("tell the ipfs accelerate agent to run a workflow on issue 42")

        assert intent.name == "agent.delegate"
        assert intent.entities["issue_number"] == 42
        assert intent.entities.get("provider") == "ipfs_accelerate_mcp"

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

    def test_confirmation_summary_includes_mcp_provider_label(self, router, parser):
        """Test confirmation summary uses MCP provider display name."""
        intent = parser.parse("ask the ipfs datasets agent to find legal datasets")

        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "needs_confirmation"
        summary = response["pending_action"]["summary"]
        assert "IPFS Datasets" in summary

    def test_confirmation_summary_includes_execution_mode_hint(self, router, parser):
        """Test confirmation summary reflects resolved execution mode."""
        intent = parser.parse("pin bafytestcid on ipfs locally")

        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "needs_confirmation"
        summary = response["pending_action"]["summary"].lower()
        assert "locally" in summary

    def test_confirmation_summary_for_result_pin_includes_execution_mode(self, router, parser):
        """Result pin confirmations should mention local execution when requested."""
        intent = parser.parse("pin that locally")

        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "needs_confirmation"
        assert "locally" in response["pending_action"]["summary"].lower()

    def test_confirmation_summary_notes_local_fallback_when_direct_disabled(
        self, router, parser, monkeypatch
    ):
        """Confirmation summaries should explain when local execution falls back to remote."""
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_ALLOW_DIRECT_EXECUTION", "false")

        intent = parser.parse("pin bafytestcid on ipfs locally")

        response = router.route(intent, Profile.WORKOUT)

        assert response["status"] == "needs_confirmation"
        summary = response["pending_action"]["summary"].lower()
        assert "remotely" in summary
        assert "local execution isn't available" in summary

    def test_result_cards_advertise_local_and_remote_ipfs_actions(
        self, router, parser, db_conn, test_user_id
    ):
        """IPFS result cards should expose explicit local and remote action phrases."""
        task = create_agent_task(
            conn=db_conn,
            user_id=test_user_id,
            provider="ipfs_kit_mcp",
            instruction="pin bafy123 on ipfs",
            trace={
                "mcp_capability": "ipfs_pin",
                "provider_label": "IPFS Kit",
                "mcp_cid": "bafy123",
            },
        )
        update_agent_task_state(conn=db_conn, task_id=task.id, new_state="running")
        update_agent_task_state(
            conn=db_conn,
            task_id=task.id,
            new_state="completed",
            trace_update={"mcp_result_preview": "Pinned bafy123"},
        )

        response = router.route(
            parser.parse("show recent ipfs results"),
            Profile.DEFAULT,
            user_id=test_user_id,
        )

        assert response["status"] == "ok"
        actions = response["cards"][0]["actions"]
        assert "save that result to ipfs locally" in actions
        assert "save that result to ipfs remotely" in actions
        assert "pin that locally" in actions
        assert "pin that remotely" in actions
        assert "unpin that locally" in actions
        assert "unpin that remotely" in actions

        action_items = response["cards"][0]["action_items"]
        local_save = next(item for item in action_items if item["id"] == "save_result_to_ipfs_local")
        assert local_save["execution_mode"] == "direct_import"
        assert local_save["execution_mode_label"] == "Local"
        assert local_save["params"]["mcp_preferred_execution_mode"] == "direct_import"
        local_pin = next(item for item in action_items if item["id"] == "pin_result_local")
        assert local_pin["execution_mode"] == "direct_import"
        assert local_pin["execution_mode_label"] == "Local"
        assert local_pin["params"]["mcp_preferred_execution_mode"] == "direct_import"
        remote_pin = next(item for item in action_items if item["id"] == "pin_result_remote")
        assert remote_pin["execution_mode"] == "mcp_remote"
        assert remote_pin["execution_mode_label"] == "Remote"
        assert remote_pin["params"]["mcp_preferred_execution_mode"] == "mcp_remote"

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
        # Create a task - it will auto-start to "running"
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        result = service.delegate(user_id=test_user_id, instruction="test", provider="mock")
        task_id = result["task_id"]

        # Task is already in "running" state after delegation
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
        # Create a task - it will auto-start to "running"
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        result = service.delegate(user_id=test_user_id, instruction="test", provider="mock")
        task_id = result["task_id"]

        # Task is already in "running" state after delegation
        # Pause the specific task
        intent = parser.parse(f"pause task {task_id}")
        response = router.route(intent, Profile.DEFAULT, user_id=test_user_id)

        assert response["status"] == "ok"
        assert "paused" in response["spoken_text"].lower()

    def test_pause_no_running_tasks(self, router, parser, test_user_id):
        """Test pausing when no tasks are running."""
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
        # Create a task - it will auto-start to "running", then pause it
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        result = service.delegate(user_id=test_user_id, instruction="test", provider="mock")
        task_id = result["task_id"]

        # Task is already in "running" state, pause it
        from handsfree.db.agent_tasks import update_agent_task_state

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
        # Create a task - it will auto-start to "running", then pause it
        from handsfree.agents.service import AgentService

        service = AgentService(db_conn)
        result = service.delegate(user_id=test_user_id, instruction="test", provider="mock")
        task_id = result["task_id"]

        # Task is already in "running" state, pause it
        from handsfree.db.agent_tasks import update_agent_task_state

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
