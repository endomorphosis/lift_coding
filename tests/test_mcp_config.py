"""Tests for MCP configuration helpers."""

from handsfree.mcp.config import get_mcp_server_config, is_mcp_provider_enabled


class TestMCPConfig:
    def test_ipfs_datasets_config_reads_endpoint_and_defaults(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_DATASETS_URL", "http://localhost:8010")
        monkeypatch.delenv("HANDSFREE_MCP_IPFS_DATASETS_TOOL_NAME", raising=False)

        config = get_mcp_server_config("ipfs_datasets")

        assert config.server_family == "ipfs_datasets"
        assert config.endpoint == "http://localhost:8010"
        assert config.tool_name == "tools_dispatch"
        assert config.timeout_s == 30.0
        assert config.poll_interval_s == 2.0
        assert config.rpc_path == "/mcp"
        assert config.protocol_version == "2024-11-05"
        assert config.task_category is None
        assert config.task_create_tool is None

    def test_config_respects_tool_name_override(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_URL", "http://localhost:8011")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_TOOL_NAME", "ipfs_kit.custom_tool")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_RPC_PATH", "/rpc")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_TRANSPORT", "stdio")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_COMMAND", "python")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_ARGS", "-m ipfs_kit_py.mcp.server")

        config = get_mcp_server_config("ipfs_kit")

        assert config.tool_name == "ipfs_kit.custom_tool"
        assert config.rpc_path == "/rpc"
        assert config.transport == "stdio"
        assert config.command == "python"
        assert config.args == ["-m", "ipfs_kit_py.mcp.server"]

    def test_config_reads_task_tool_overrides(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_ACCELERATE_URL", "http://localhost:8012")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_ACCELERATE_TASK_CATEGORY", "workflow")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_ACCELERATE_TASK_CREATE_TOOL", "create_workflow")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_ACCELERATE_TASK_STATUS_TOOL", "get_task_status")
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_ACCELERATE_TASK_CANCEL_TOOL", "manage_background_tasks")

        config = get_mcp_server_config("ipfs_accelerate")

        assert config.tool_name == "tools_dispatch"
        assert config.task_category == "workflow"
        assert config.task_create_tool == "create_workflow"
        assert config.task_status_tool == "get_task_status"
        assert config.task_cancel_tool == "manage_background_tasks"

    def test_provider_enablement_defaults_true(self, monkeypatch):
        monkeypatch.delenv("HANDSFREE_MCP_ENABLED", raising=False)
        monkeypatch.delenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", raising=False)

        assert is_mcp_provider_enabled("ipfs_datasets_mcp") is True

    def test_provider_enablement_respects_provider_flag(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "false")

        assert is_mcp_provider_enabled("ipfs_datasets_mcp") is False

    def test_provider_enablement_respects_global_flag(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_MCP_ENABLED", "false")
        monkeypatch.setenv("HANDSFREE_AGENT_ENABLE_IPFS_DATASETS_MCP", "true")

        assert is_mcp_provider_enabled("ipfs_datasets_mcp") is False
