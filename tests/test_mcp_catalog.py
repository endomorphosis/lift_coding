"""Tests for MCP provider and capability registry helpers."""

from handsfree.mcp import (
    get_capability_descriptor,
    get_provider_capabilities,
    resolve_capability_execution_mode,
    resolve_provider_capability,
)


class TestMCPCatalog:
    def test_provider_capabilities_include_execution_modes(self):
        capabilities = {
            descriptor.capability_id: descriptor
            for descriptor in get_provider_capabilities("ipfs_kit_mcp")
        }

        assert "ipfs_pin" in capabilities
        assert "ipfs_add" in capabilities
        assert "ipfs_cat" in capabilities
        assert capabilities["ipfs_pin"].title == "Pin Content"
        assert capabilities["ipfs_pin"].execution_modes == ("direct_import", "mcp_remote")
        assert capabilities["ipfs_add"].execution_modes == ("direct_import", "mcp_remote")
        assert capabilities["ipfs_cat"].execution_modes == ("direct_import", "mcp_remote")

    def test_resolve_provider_capability_uses_explicit_or_inferred_value(self):
        assert resolve_provider_capability("ipfs_datasets_mcp", "dataset_discovery") == "dataset_discovery"
        assert resolve_provider_capability(
            "ipfs_datasets_mcp",
            instruction="find legal datasets about labor law",
        ) == "dataset_discovery"
        assert resolve_provider_capability("ipfs_datasets_mcp", "ipfs_pin") is None

    def test_resolve_capability_execution_mode_prefers_supported_mode(self):
        assert resolve_capability_execution_mode("ipfs_kit_mcp", "ipfs_pin", "direct_import") == "direct_import"
        assert resolve_capability_execution_mode("ipfs_kit_mcp", "ipfs_pin", "api_live") == "mcp_remote"

    def test_resolve_capability_execution_mode_respects_remote_only_policy(self, monkeypatch):
        monkeypatch.setenv("HANDSFREE_MCP_IPFS_KIT_ALLOW_DIRECT_EXECUTION", "false")

        assert resolve_capability_execution_mode("ipfs_kit_mcp", "ipfs_pin", "direct_import") == "mcp_remote"
        assert resolve_capability_execution_mode("ipfs_kit_mcp", "ipfs_add", "direct_import") == "mcp_remote"

    def test_get_capability_descriptor_returns_canonical_metadata(self):
        descriptor = get_capability_descriptor("agentic_fetch")

        assert descriptor is not None
        assert descriptor.provider_name == "ipfs_accelerate_mcp"
        assert descriptor.server_family == "ipfs_accelerate"
        assert descriptor.default_execution_mode == "mcp_remote"
        assert descriptor.confirmation_policy == "safe_write"
        assert descriptor.input_schema_ref == "handsfree.capability.agentic_fetch.input"
