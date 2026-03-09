"""Tests for MCP-backed IPFS agent providers."""

import json
from types import SimpleNamespace

import pytest

from handsfree.agent_providers import (
    IPFSAccelerateMCPAgentProvider,
    IPFSDatasetsMCPAgentProvider,
    IPFSKitMCPAgentProvider,
    get_provider,
)
from handsfree.agents.service import AgentService
from handsfree.commands.intent_parser import IntentParser
from handsfree.db import init_db
from handsfree.db.agent_tasks import get_agent_task_by_id
from handsfree.mcp import MCPConfigurationError
from handsfree.mcp.client import MCPClient
from handsfree.mcp.models import MCPRunStatus, MCPServerConfig, MCPToolInvocationResult


class _FakeMCPClient:
    def __init__(self) -> None:
        self.cancelled_run_ids: list[str] = []
        self.calls: list[tuple[str, dict[str, object]]] = []

    def validate_configuration(self) -> None:
        return None

    def handshake(self) -> dict[str, str]:
        return {"server": "fake-mcp"}

    def list_tools(self) -> list[dict[str, object]]:
        return [{"name": "tools_dispatch"}]

    def invoke_tool(
        self,
        tool_name: str,
        arguments: dict[str, object],
        correlation_id: str,
    ) -> MCPToolInvocationResult:
        self.calls.append((tool_name, arguments))
        if tool_name == "tools_dispatch":
            category = str(arguments.get("category"))
            nested_tool_name = str(arguments.get("tool_name") or arguments.get("tool"))
            parameters = arguments.get("parameters") or arguments.get("params") or {}
            if nested_tool_name == "manage_background_tasks":
                action = parameters.get("action")
                if action == "create":
                    return MCPToolInvocationResult(
                        request_id="req-123",
                        run_id=None,
                        status="running",
                        tool_name=tool_name,
                        output={
                            "status": "success",
                            "task_id": "remote-task-123",
                            "message": "Background task created successfully",
                            "category": category,
                        },
                        raw_response={"ok": True},
                        content=[{"type": "text", "text": json.dumps({"task_id": "remote-task-123"})}],
                    )
                if action == "cancel":
                    return MCPToolInvocationResult(
                        request_id="req-125",
                        run_id=None,
                        status="completed",
                        tool_name=tool_name,
                        output={"status": "success", "task_id": parameters.get("task_id"), "message": "Cancelled"},
                        raw_response={"ok": True},
                        content=[{"type": "text", "text": "Cancelled"}],
                    )
            if nested_tool_name in {"get_task_status", "check_task_status"}:
                return MCPToolInvocationResult(
                    request_id="req-124",
                    run_id=None,
                    status="running",
                    tool_name=tool_name,
                    output={
                        "status": "success",
                        "task": {
                            "task_id": parameters.get("task_id"),
                            "status": "completed",
                        },
                        "message": "Finished",
                    },
                    raw_response={"ok": True},
                    content=[{"type": "text", "text": "Finished"}],
                )
            if nested_tool_name == "expand_legal_query":
                query = parameters.get("query")
                return MCPToolInvocationResult(
                    request_id="req-126",
                    run_id=None,
                    status="completed",
                    tool_name=tool_name,
                    output={
                        "status": "success",
                        "expanded_queries": [query, f"{query} statutes"],
                        "message": "Expanded legal query",
                    },
                    raw_response={"ok": True},
                    content=[{"type": "text", "text": json.dumps({"status": "success"})}],
                )
            if nested_tool_name == "unified_agentic_discover_and_fetch":
                return MCPToolInvocationResult(
                    request_id="req-127",
                    run_id=None,
                    status="completed",
                    tool_name=tool_name,
                    output={
                        "status": "success",
                        "message": "Agentic fetch started and completed",
                    },
                    raw_response={"ok": True},
                    content=[{"type": "text", "text": "Agentic fetch complete"}],
                )
        return MCPToolInvocationResult(
            request_id="req-123",
            run_id=None,
            status="completed",
            tool_name=tool_name,
            output={
                "instruction": arguments.get("instruction"),
                "correlation_id": correlation_id,
            },
            raw_response={"ok": True},
            content=[{"type": "text", "text": "Finished"}],
        )

    def get_run_status(self, run_id: str, correlation_id: str | None = None) -> MCPRunStatus:
        return MCPRunStatus(
            run_id=run_id,
            status="completed",
            message="Finished",
            output={"correlation_id": correlation_id},
            raw_response={"ok": True},
        )

    def cancel_run(self, run_id: str, correlation_id: str | None = None) -> dict[str, object]:
        self.cancelled_run_ids.append(run_id)
        return {"ok": True, "run_id": run_id, "correlation_id": correlation_id}


class TestMCPIPFSProviders:
    def test_factory_returns_ipfs_datasets_mcp_provider(self):
        provider = get_provider("ipfs_datasets_mcp")
        assert isinstance(provider, IPFSDatasetsMCPAgentProvider)

    def test_start_task_uses_client_and_returns_trace(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")
        provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())
        task = SimpleNamespace(
            id="task-123",
            instruction="find legal datasets",
            target_type=None,
            target_ref=None,
            trace=None,
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["status"] == "running"
        assert result["trace"]["provider"] == "ipfs_datasets_mcp"
        assert result["trace"]["mcp_request_id"] == "req-123"
        assert result["trace"]["mcp_run_id"] is None
        assert result["trace"]["mcp_execution_mode"] == "mcp_remote"
        assert result["trace"]["mcp_sync_completed"] is False
        assert result["trace"]["mcp_remote_task_id"] == "remote-task-123"
        assert result["trace"]["tool_name"] == "tools_dispatch"

    def test_start_task_fails_when_endpoint_missing(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")

        class _MissingConfigClient(_FakeMCPClient):
            def validate_configuration(self) -> None:
                raise MCPConfigurationError("missing endpoint")

        provider = IPFSDatasetsMCPAgentProvider(client=_MissingConfigClient())
        task = SimpleNamespace(
            id="task-123",
            instruction="find datasets",
            target_type=None,
            target_ref=None,
            trace=None,
        )

        result = provider.start_task(task)

        assert result["ok"] is False
        assert result["status"] == "failed"
        assert result["trace"]["error"] == "configuration_error"

    def test_check_status_maps_completed_state(self):
        provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())
        task = SimpleNamespace(
            id="task-123",
            instruction="find legal datasets",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_status_strategy": "tool_polling",
                "mcp_remote_task_id": "remote-task-123",
                "correlation_id": "corr-1",
            },
        )

        result = provider.check_status(task)

        assert result["ok"] is True
        assert result["status"] == "completed"
        assert result["trace"]["last_protocol_state"] == "success"

    def test_cancel_task_uses_run_id(self):
        client = _FakeMCPClient()
        provider = IPFSDatasetsMCPAgentProvider(client=client)
        task = SimpleNamespace(
            id="task-123",
            instruction="find legal datasets",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_status_strategy": "tool_polling",
                "mcp_remote_task_id": "remote-task-123",
                "correlation_id": "corr-1",
            },
        )

        result = provider.cancel_task(task)

        assert result["ok"] is True
        assert result["status"] == "failed"
        assert client.cancelled_run_ids == []
        assert client.calls[-1][0] == "tools_dispatch"

    def test_ipfs_kit_direct_add_uses_real_tool_binding(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        task = SimpleNamespace(
            id="task-124",
            instruction="add this file to ipfs",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "ipfs_add",
                "mcp_input": "this file",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["tool_name"] == "ipfs_add"
        assert result["trace"]["mcp_sync_completed"] is True
        assert provider._client.calls[-1] == ("ipfs_add", {"content": "this file"})  # type: ignore[union-attr]

    def test_ipfs_kit_direct_pin_uses_real_tool_binding(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        task = SimpleNamespace(
            id="task-125",
            instruction="pin bafy123 on ipfs",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "ipfs_pin",
                "mcp_cid": "bafy123",
                "mcp_pin_action": "pin",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["tool_name"] == "ipfs_pin_add"
        assert provider._client.calls[-1] == ("ipfs_pin_add", {"cid": "bafy123"})  # type: ignore[union-attr]

    def test_ipfs_datasets_direct_discovery_uses_legal_query_tool(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")
        provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())
        task = SimpleNamespace(
            id="task-126",
            instruction="find legal datasets",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "dataset_discovery",
                "mcp_input": "legal datasets",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["tool_name"] == "tools_dispatch"
        assert result["trace"]["mcp_sync_completed"] is True
        assert provider._client.calls[-1] == (  # type: ignore[union-attr]
            "tools_dispatch",
            {
                "category": "legal_dataset_tools",
                "tool": "expand_legal_query",
                "params": {"query": "legal datasets"},
            },
        )

    def test_ipfs_accelerate_direct_agentic_fetch_uses_web_archive_tool(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_ACCELERATE_MCP", "true")
        provider = IPFSAccelerateMCPAgentProvider(client=_FakeMCPClient())
        task = SimpleNamespace(
            id="task-127",
            instruction="discover and fetch climate regulations from https://example.com",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "agentic_fetch",
                "mcp_input": "climate regulations",
                "mcp_seed_url": "https://example.com",
            },
        )

    def test_ipfs_kit_direct_import_pin_uses_local_adapter(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")

        class _FakeKitAdapter:
            def pin(self, cid: str, **kwargs):
                return {"ok": True, "cid": cid, "mode": "pin", "options": kwargs}

            def unpin(self, cid: str, **kwargs):
                return {"ok": True, "cid": cid, "mode": "unpin", "options": kwargs}

        monkeypatch.setattr("handsfree.agent_providers.get_ipfs_kit_adapter", lambda: _FakeKitAdapter())
        client = _FakeMCPClient()
        provider = IPFSKitMCPAgentProvider(client=client)
        task = SimpleNamespace(
            id="task-128",
            instruction="pin bafy123",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "ipfs_pin",
                "mcp_cid": "bafy123",
                "mcp_pin_action": "pin",
                "mcp_preferred_execution_mode": "direct_import",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["mcp_execution_mode"] == "direct_import"
        assert result["trace"]["mcp_sync_completed"] is True
        assert result["trace"]["tool_name"] == "ipfs_kit.pin"
        assert result["trace"]["mcp_result_output"] == {
            "ok": True,
            "cid": "bafy123",
            "mode": "pin",
            "options": {},
        }
        assert client.calls == []

    def test_ipfs_kit_direct_import_add_uses_local_adapter(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")

        class _FakeKitAdapter:
            def add_bytes(self, data: bytes, **kwargs):
                return {"cid": "bafyadd123", "size": len(data), "options": kwargs}

        monkeypatch.setattr("handsfree.agent_providers.get_ipfs_kit_adapter", lambda: _FakeKitAdapter())
        client = _FakeMCPClient()
        provider = IPFSKitMCPAgentProvider(client=client)
        task = SimpleNamespace(
            id="task-128c",
            instruction="save content to ipfs",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "ipfs_add",
                "mcp_input": "hello ipfs",
                "mcp_preferred_execution_mode": "direct_import",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["mcp_execution_mode"] == "direct_import"
        assert result["trace"]["mcp_cid"] == "bafyadd123"
        assert result["trace"]["tool_name"] == "ipfs_kit.add_bytes"
        assert result["trace"]["mcp_result_output"]["cid"] == "bafyadd123"
        assert client.calls == []

    def test_ipfs_kit_direct_import_cat_uses_local_adapter(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")

        class _FakeKitAdapter:
            def cat(self, cid: str, **kwargs):
                return b"hello from ipfs"

        monkeypatch.setattr("handsfree.agent_providers.get_ipfs_kit_adapter", lambda: _FakeKitAdapter())
        client = _FakeMCPClient()
        provider = IPFSKitMCPAgentProvider(client=client)
        task = SimpleNamespace(
            id="task-128d",
            instruction="read bafycat123",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "ipfs_cat",
                "mcp_cid": "bafycat123",
                "mcp_preferred_execution_mode": "direct_import",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["mcp_execution_mode"] == "direct_import"
        assert result["trace"]["tool_name"] == "ipfs_kit.cat"
        assert result["trace"]["mcp_result_output"] == {
            "cid": "bafycat123",
            "content": "hello from ipfs",
        }
        assert client.calls == []

    def test_ipfs_kit_remote_only_policy_disables_direct_import(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_ALLOW_DIRECT_EXECUTION", "false")

        client = _FakeMCPClient()
        provider = IPFSKitMCPAgentProvider(client=client)
        task = SimpleNamespace(
            id="task-128e",
            instruction="pin bafy123",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "ipfs_pin",
                "mcp_cid": "bafy123",
                "mcp_pin_action": "pin",
                "mcp_preferred_execution_mode": "direct_import",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["mcp_execution_mode"] == "mcp_remote"
        assert client.calls[-1] == ("ipfs_pin_add", {"cid": "bafy123"})

    def test_ipfs_kit_env_preferred_mode_uses_local_adapter(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_PREFERRED_EXECUTION_MODE", "direct_import")

        class _FakeKitAdapter:
            def pin(self, cid: str, **kwargs):
                return {"ok": True, "cid": cid, "mode": "pin", "options": kwargs}

            def unpin(self, cid: str, **kwargs):
                return {"ok": True, "cid": cid, "mode": "unpin", "options": kwargs}

        monkeypatch.setattr("handsfree.agent_providers.get_ipfs_kit_adapter", lambda: _FakeKitAdapter())
        client = _FakeMCPClient()
        provider = IPFSKitMCPAgentProvider(client=client)
        task = SimpleNamespace(
            id="task-128b",
            instruction="pin bafy999",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "ipfs_pin",
                "mcp_cid": "bafy999",
                "mcp_pin_action": "pin",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["mcp_execution_mode"] == "direct_import"
        assert result["trace"]["mcp_result_output"]["cid"] == "bafy999"
        assert client.calls == []

    def test_ipfs_datasets_direct_import_embedding_uses_local_router(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")

        class _FakeEmbeddingsRouter:
            def embed_text(self, text: str, **kwargs):
                return [float(len(text))]

            def embed_texts(self, texts: list[str], **kwargs):
                return [[float(len(text))] for text in texts]

        monkeypatch.setattr(
            "handsfree.agent_providers.get_embeddings_router",
            lambda: _FakeEmbeddingsRouter(),
        )
        client = _FakeMCPClient()
        provider = IPFSDatasetsMCPAgentProvider(client=client)
        task = SimpleNamespace(
            id="task-129",
            instruction="embed this text",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "embedding",
                "mcp_input": "labor law",
                "mcp_preferred_execution_mode": "direct_import",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is True
        assert result["trace"]["mcp_execution_mode"] == "direct_import"
        assert result["trace"]["mcp_sync_completed"] is True
        assert result["trace"]["tool_name"] == "ipfs_datasets.embed_text"
        assert result["trace"]["mcp_result_output"] == [9.0]
        assert client.calls == []

    def test_ipfs_kit_rejects_capability_from_other_provider(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_KIT_MCP", "true")
        provider = IPFSKitMCPAgentProvider(client=_FakeMCPClient())
        task = SimpleNamespace(
            id="task-128",
            instruction="find legal datasets",
            target_type=None,
            target_ref=None,
            trace={
                "mcp_capability": "dataset_discovery",
            },
        )

        result = provider.start_task(task)

        assert result["ok"] is False
        assert result["status"] == "failed"
        assert "not supported" in result["message"]


class TestMCPAgentParserAndService:
    @pytest.fixture
    def db_conn(self):
        conn = init_db(":memory:")
        yield conn
        conn.close()

    @pytest.fixture
    def parser(self):
        return IntentParser()

    def test_parser_extracts_ipfs_datasets_provider(self, parser):
        result = parser.parse("ask the ipfs datasets agent to find legal datasets")

        assert result.name == "agent.delegate"
        assert result.entities["provider"] == "ipfs_datasets_mcp"
        assert result.entities["instruction"] == "find legal datasets"

    def test_delegate_uses_explicit_mcp_provider(self, db_conn, parser, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")
        intent = parser.parse("ask the ipfs datasets agent to find legal datasets")
        fake_provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())

        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_datasets_mcp" else None,
        )

        service = AgentService(db_conn)
        result = service.delegate(
            user_id="test-user",
            instruction=intent.entities["instruction"],
            provider=intent.entities["provider"],
        )

        task = get_agent_task_by_id(db_conn, result["task_id"])
        assert task is not None
        assert task.provider == "ipfs_datasets_mcp"
        assert task.state == "completed"
        assert task.trace is not None
        assert task.trace["mcp_capability"] == "dataset_discovery"
        assert task.trace["provider_label"] == "IPFS Datasets"
        assert task.trace["mcp_sync_completed"] is True
        assert task.trace.get("mcp_remote_task_id") is None
        assert result["spoken_text"] == "Expanded legal query"

    def test_get_status_polls_mcp_provider(self, db_conn, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")
        fake_provider = IPFSDatasetsMCPAgentProvider(client=_FakeMCPClient())
        monkeypatch.setattr(
            "handsfree.agents.service.get_provider",
            lambda provider_name: fake_provider if provider_name == "ipfs_datasets_mcp" else None,
        )

        service = AgentService(db_conn)
        result = service.delegate(
            user_id="test-user",
            instruction="find legal datasets",
            provider="ipfs_datasets_mcp",
        )

        status = service.get_status("test-user")
        task = get_agent_task_by_id(db_conn, result["task_id"])

        assert status["by_state"]["completed"] == 1
        assert status["tasks"][0]["result_preview"] == "Expanded legal query"
        assert status["tasks"][0]["result_output"]["expanded_queries"] == [
            "find legal datasets",
            "find legal datasets statutes",
        ]
        assert task is not None
        assert task.state == "completed"
        assert task.trace is not None
        assert task.trace["mcp_result_preview"] == "Expanded legal query"
        assert task.trace["mcp_result_output"]["expanded_queries"] == [
            "find legal datasets",
            "find legal datasets statutes",
        ]


class TestMCPClientJSONRPC:
    def test_invoke_tool_uses_jsonrpc_methods(self, monkeypatch):
        config = MCPServerConfig(
            server_family="ipfs_datasets",
            endpoint="http://localhost:8000",
            tool_name="tools_dispatch",
        )
        client = MCPClient(config)
        recorded: list[tuple[str, dict[str, object]]] = []

        def fake_post(path: str, payload: dict[str, object]) -> dict[str, object]:
            recorded.append((path, payload))
            method = payload["method"]
            if method == "initialize":
                return {"jsonrpc": "2.0", "id": payload["id"], "result": {"capabilities": {"tools": {}}}}
            if method == "tools/call":
                return {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "content": [{"type": "text", "text": "ok"}],
                    },
                }
            raise AssertionError(f"Unexpected method: {method}")

        monkeypatch.setattr(client, "_post_json", fake_post)

        result = client.invoke_tool("tools_dispatch", {"category": "dataset_tools"}, "corr-1")

        assert [payload["method"] for _, payload in recorded] == ["initialize", "tools/call"]
        assert recorded[0][0] == "/mcp"
        assert recorded[1][0] == "/mcp"
        assert result.status == "completed"
        assert result.content[0]["text"] == "ok"

    def test_list_tools_uses_jsonrpc_method(self, monkeypatch):
        config = MCPServerConfig(
            server_family="ipfs_datasets",
            endpoint="http://localhost:8000",
            tool_name="tools_dispatch",
        )
        client = MCPClient(config)
        recorded: list[tuple[str, dict[str, object]]] = []

        def fake_post(path: str, payload: dict[str, object]) -> dict[str, object]:
            recorded.append((path, payload))
            method = payload["method"]
            if method == "initialize":
                return {"jsonrpc": "2.0", "id": payload["id"], "result": {"capabilities": {"tools": {}}}}
            if method == "tools/list":
                return {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "result": {
                        "tools": [{"name": "tools_dispatch"}],
                    },
                }
            raise AssertionError(f"Unexpected method: {method}")

        monkeypatch.setattr(client, "_post_json", fake_post)

        tools = client.list_tools()

        assert [payload["method"] for _, payload in recorded] == ["initialize", "tools/list"]
        assert tools == [{"name": "tools_dispatch"}]

    def test_stdio_transport_uses_content_length_framing(self):
        class _FakeStdin:
            def __init__(self) -> None:
                self.writes: list[str] = []

            def write(self, data: str) -> int:
                self.writes.append(data)
                return len(data)

            def flush(self) -> None:
                return None

        class _FakeStdout:
            def __init__(self, message: dict[str, object]) -> None:
                body = json.dumps(message)
                self._parts = [
                    f"Content-Length: {len(body.encode('utf-8'))}\r\n",
                    "\r\n",
                ]
                self._body = body

            def readline(self) -> str:
                if self._parts:
                    return self._parts.pop(0)
                return ""

            def read(self, length: int) -> str:
                return self._body[:length]

        class _FakeProcess:
            def __init__(self, message: dict[str, object]) -> None:
                self.stdin = _FakeStdin()
                self.stdout = _FakeStdout(message)
                self.stderr = None

            def poll(self):
                return None

        config = MCPServerConfig(
            server_family="ipfs_datasets",
            endpoint="",
            transport="stdio",
            command="python",
            args=["-m", "ipfs_datasets_py.mcp_server"],
            tool_name="tools_dispatch",
        )
        client = MCPClient(config)
        fake_process = _FakeProcess({"jsonrpc": "2.0", "id": 1, "result": {"capabilities": {}}})
        client._process = fake_process  # type: ignore[assignment]

        response = client._rpc_request("initialize", {"protocolVersion": "2024-11-05", "capabilities": {}})

        assert response["result"]["capabilities"] == {}
        written = fake_process.stdin.writes[0]
        assert "Content-Length:" in written
        assert '"method": "initialize"' in written
