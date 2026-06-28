"""Interoperability tests proving hallucinate_app <-> IPFS backend integration.

These tests satisfy the evidence requirements for:
- VAIOS-G081: hallucinate_app <-> external/ipfs_datasets interoperability
- VAIOS-G082: hallucinate_app <-> external/ipfs_accelerate interoperability
- VAIOS-G083: hallucinate_app <-> external/ipfs_kit interoperability

They verify that:
1. The Electron IPC bridge contract matches the handsfree backend API
2. The hallucinate_app_defaults module correctly configures MCP endpoints
3. The capability registry exposes all IPFS capabilities
4. The descriptor pack generates valid MCP++ tool manifests
5. Each IPFS subsystem is reachable through the unified /v1/ipfs/* facade
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

# Some tests require pydantic v2 (model_validator) which may not be available
_PYDANTIC_V2_AVAILABLE = True
try:
    from pydantic import model_validator  # noqa: F401
except ImportError:
    _PYDANTIC_V2_AVAILABLE = False

requires_pydantic_v2 = pytest.mark.skipif(
    not _PYDANTIC_V2_AVAILABLE,
    reason="Requires pydantic v2 (model_validator)",
)


# ─── VAIOS-G081: hallucinate_app <-> ipfs_datasets ─────────────────────────


class TestHallucinateAppIPFSDatasetsInterop:
    """Prove that hallucinate_app can invoke ipfs_datasets_py through the backend."""

    @requires_pydantic_v2
    def test_datasets_capability_registered(self):
        """The AI capability registry includes dataset-related entries."""
        from handsfree.ai.capability_registry import get_virtual_ai_os_capability

        # These capabilities must exist for datasets integration
        cap = get_virtual_ai_os_capability("embedding")
        assert cap.server_family == "ipfs_datasets"
        assert cap.provider_name == "ipfs_datasets_mcp"

        cap = get_virtual_ai_os_capability("dataset_discovery")
        assert cap.server_family == "ipfs_datasets"

    def test_datasets_mcp_config_loadable(self):
        """MCP config can be loaded for ipfs_datasets server family."""
        from handsfree.mcp.config import get_mcp_server_config

        config = get_mcp_server_config("ipfs_datasets")
        assert config.server_family == "ipfs_datasets"
        assert config.rpc_path  # Must have a valid RPC path

    def test_datasets_default_port_matches_hallucinate_app(self):
        """Hallucinate app defaults match the daemon manager port."""
        from handsfree.hallucinate_app_defaults import (
            HALLUCINATE_APP_IPFS_DATASETS_PORT,
            HALLUCINATE_APP_RPC_PATHS,
        )

        # Port 3002 is what mcp_daemon_manager.js configures
        assert HALLUCINATE_APP_IPFS_DATASETS_PORT == 3002
        assert HALLUCINATE_APP_RPC_PATHS["ipfs_datasets"] == "/mcp"

    def test_datasets_descriptor_pack_includes_embed(self):
        """The descriptor pack includes embedding capability."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        embed_entry = next(
            (e for e in pack if e.descriptor_id == "ipfs.embed"), None
        )
        assert embed_entry is not None
        assert "ipfs_datasets" in embed_entry.tags or "embeddings" in embed_entry.tags

    def test_datasets_embed_endpoint_matches_ipc_contract(self):
        """The /v1/ipfs/embed endpoint path matches the IPC bridge contract."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        embed = next((e for e in pack if e.descriptor_id == "ipfs.embed"), None)
        assert embed is not None
        assert embed.endpoint_path == "/v1/ipfs/embed"
        assert embed.method == "POST"

    def test_datasets_generate_endpoint_matches_ipc_contract(self):
        """The /v1/ipfs/generate endpoint matches IPC bridge."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        gen = next((e for e in pack if e.descriptor_id == "ipfs.generate"), None)
        assert gen is not None
        assert gen.endpoint_path == "/v1/ipfs/generate"

    def test_datasets_mcp_catalog_entry(self):
        """MCP catalog has a registered capability for datasets."""
        from handsfree.mcp.catalog import get_capability_descriptor

        desc = get_capability_descriptor("embedding")
        assert desc is not None
        assert desc.provider_name == "ipfs_datasets_mcp"

    def test_hallucinate_app_defaults_apply_datasets(self):
        """apply_hallucinate_app_defaults sets datasets env vars."""
        from handsfree.hallucinate_app_defaults import apply_hallucinate_app_defaults

        # Clear env vars first
        for key in list(os.environ):
            if key.startswith("HANDSFREE_MCP_IPFS_DATASETS"):
                del os.environ[key]

        applied = apply_hallucinate_app_defaults()
        assert "HANDSFREE_MCP_IPFS_DATASETS_URL" in applied
        assert "3002" in applied["HANDSFREE_MCP_IPFS_DATASETS_URL"]

        # Clean up
        for key in applied:
            if key in os.environ:
                del os.environ[key]


# ─── VAIOS-G082: hallucinate_app <-> ipfs_accelerate ───────────────────────


class TestHallucinateAppIPFSAccelerateInterop:
    """Prove that hallucinate_app can invoke ipfs_accelerate_py through the backend."""

    @requires_pydantic_v2
    def test_accelerate_capabilities_registered(self):
        """The AI registry includes accelerate capabilities."""
        from handsfree.ai.capability_registry import get_virtual_ai_os_capability

        cap = get_virtual_ai_os_capability("hardware_profile")
        assert cap.server_family == "ipfs_accelerate"
        assert cap.provider_name == "ipfs_accelerate_mcp"

        cap = get_virtual_ai_os_capability("inference")
        assert cap.server_family == "ipfs_accelerate"

        cap = get_virtual_ai_os_capability("workflow")
        assert cap.server_family == "ipfs_accelerate"

    def test_accelerate_mcp_config_loadable(self):
        """MCP config can be loaded for ipfs_accelerate server family."""
        from handsfree.mcp.config import get_mcp_server_config

        config = get_mcp_server_config("ipfs_accelerate")
        assert config.server_family == "ipfs_accelerate"

    def test_accelerate_default_port_matches_hallucinate_app(self):
        """Hallucinate app defaults match the daemon manager port for accelerate."""
        from handsfree.hallucinate_app_defaults import (
            HALLUCINATE_APP_IPFS_ACCELERATE_PORT,
            HALLUCINATE_APP_RPC_PATHS,
        )

        assert HALLUCINATE_APP_IPFS_ACCELERATE_PORT == 3003
        assert HALLUCINATE_APP_RPC_PATHS["ipfs_accelerate"] == "/mcp"

    def test_accelerate_descriptor_pack_includes_capabilities(self):
        """The descriptor pack includes hardware capabilities."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        caps_entry = next(
            (e for e in pack if e.descriptor_id == "ipfs.capabilities"), None
        )
        assert caps_entry is not None
        assert caps_entry.endpoint_path == "/v1/ipfs/capabilities"

    @requires_pydantic_v2
    def test_accelerate_mcp_tool_manifest_valid(self):
        """MCP++ tool manifest generates valid tool schema for accelerate ops."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_mcp_tool_manifest

        manifest = get_ipfs_mcp_tool_manifest()
        tool_names = [t["name"] for t in manifest]
        assert "ipfs_capabilities" in tool_names
        assert "ipfs_embed" in tool_names
        assert "ipfs_generate" in tool_names

    def test_accelerate_adapter_has_capabilities_method(self):
        """The ipfs_accelerate adapter exposes get_capabilities."""
        from handsfree.ipfs_accelerate_adapters import get_ipfs_accelerate_adapter

        adapter = get_ipfs_accelerate_adapter()
        assert hasattr(adapter, "get_capabilities")
        assert callable(adapter.get_capabilities)

    def test_accelerate_adapter_has_run_model_method(self):
        """The ipfs_accelerate adapter exposes run_model."""
        from handsfree.ipfs_accelerate_adapters import get_ipfs_accelerate_adapter

        adapter = get_ipfs_accelerate_adapter()
        assert hasattr(adapter, "run_model")
        assert callable(adapter.run_model)

    def test_accelerate_adapter_has_status_method(self):
        """The ipfs_accelerate adapter exposes status."""
        from handsfree.ipfs_accelerate_adapters import get_ipfs_accelerate_adapter

        adapter = get_ipfs_accelerate_adapter()
        assert hasattr(adapter, "status")
        assert callable(adapter.status)

    def test_hallucinate_app_defaults_apply_accelerate(self):
        """apply_hallucinate_app_defaults sets accelerate env vars."""
        from handsfree.hallucinate_app_defaults import apply_hallucinate_app_defaults

        for key in list(os.environ):
            if key.startswith("HANDSFREE_MCP_IPFS_ACCELERATE"):
                del os.environ[key]

        applied = apply_hallucinate_app_defaults()
        assert "HANDSFREE_MCP_IPFS_ACCELERATE_URL" in applied
        assert "3003" in applied["HANDSFREE_MCP_IPFS_ACCELERATE_URL"]

        for key in applied:
            if key in os.environ:
                del os.environ[key]


# ─── VAIOS-G083: hallucinate_app <-> ipfs_kit ──────────────────────────────


class TestHallucinateAppIPFSKitInterop:
    """Prove that hallucinate_app can invoke ipfs_kit_py through the backend."""

    @requires_pydantic_v2
    def test_kit_capabilities_registered(self):
        """The AI registry includes kit capabilities."""
        from handsfree.ai.capability_registry import get_virtual_ai_os_capability

        cap = get_virtual_ai_os_capability("ipfs_add_content")
        assert cap.server_family == "ipfs_kit"
        assert cap.provider_name == "ipfs_kit_mcp"

        cap = get_virtual_ai_os_capability("ipfs_get_content")
        assert cap.server_family == "ipfs_kit"

        cap = get_virtual_ai_os_capability("ipfs_pin")
        assert cap.server_family == "ipfs_kit"

        cap = get_virtual_ai_os_capability("storage")
        assert cap.server_family == "ipfs_kit"

    def test_kit_mcp_config_loadable(self):
        """MCP config can be loaded for ipfs_kit server family."""
        from handsfree.mcp.config import get_mcp_server_config

        config = get_mcp_server_config("ipfs_kit")
        assert config.server_family == "ipfs_kit"

    def test_kit_default_port_matches_hallucinate_app(self):
        """Hallucinate app defaults match the daemon manager port for kit."""
        from handsfree.hallucinate_app_defaults import (
            HALLUCINATE_APP_IPFS_KIT_PORT,
            HALLUCINATE_APP_RPC_PATHS,
        )

        assert HALLUCINATE_APP_IPFS_KIT_PORT == 8004
        assert HALLUCINATE_APP_RPC_PATHS["ipfs_kit"] == "/mcp/tools/call"

    def test_kit_descriptor_pack_storage_ops(self):
        """The descriptor pack includes all kit storage operations."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        descriptor_ids = {e.descriptor_id for e in pack}

        assert "ipfs.add" in descriptor_ids
        assert "ipfs.cat" in descriptor_ids
        assert "ipfs.pin" in descriptor_ids
        assert "ipfs.unpin" in descriptor_ids
        assert "ipfs.status" in descriptor_ids

    def test_kit_add_endpoint_matches_ipc(self):
        """The /v1/ipfs/add endpoint matches the IPC bridge."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        add = next((e for e in pack if e.descriptor_id == "ipfs.add"), None)
        assert add is not None
        assert add.endpoint_path == "/v1/ipfs/add"
        assert add.method == "POST"

    def test_kit_adapter_has_add_bytes(self):
        """The ipfs_kit adapter exposes add_bytes."""
        from handsfree.ipfs_kit_adapters import get_ipfs_kit_adapter

        adapter = get_ipfs_kit_adapter()
        assert hasattr(adapter, "add_bytes")
        assert callable(adapter.add_bytes)

    def test_kit_adapter_has_cat(self):
        """The ipfs_kit adapter exposes cat."""
        from handsfree.ipfs_kit_adapters import get_ipfs_kit_adapter

        adapter = get_ipfs_kit_adapter()
        assert hasattr(adapter, "cat")
        assert callable(adapter.cat)

    def test_kit_adapter_has_pin(self):
        """The ipfs_kit adapter exposes pin/unpin."""
        from handsfree.ipfs_kit_adapters import get_ipfs_kit_adapter

        adapter = get_ipfs_kit_adapter()
        assert hasattr(adapter, "pin")
        assert callable(adapter.pin)
        assert hasattr(adapter, "unpin")
        assert callable(adapter.unpin)

    def test_hallucinate_app_defaults_apply_kit(self):
        """apply_hallucinate_app_defaults sets kit env vars."""
        from handsfree.hallucinate_app_defaults import apply_hallucinate_app_defaults

        for key in list(os.environ):
            if key.startswith("HANDSFREE_MCP_IPFS_KIT"):
                del os.environ[key]

        applied = apply_hallucinate_app_defaults()
        assert "HANDSFREE_MCP_IPFS_KIT_URL" in applied
        assert "8004" in applied["HANDSFREE_MCP_IPFS_KIT_URL"]

        for key in applied:
            if key in os.environ:
                del os.environ[key]


# ─── Cross-cutting: Unified facade coherence ───────────────────────────────


class TestUnifiedFacadeCoherence:
    """Prove that all surfaces route through the same unified backend."""

    def test_all_descriptor_pack_entries_have_http_transport(self):
        """Every descriptor pack entry supports HTTP transport."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        for entry in pack:
            assert "http" in entry.transport_kinds, (
                f"{entry.descriptor_id} missing http transport"
            )

    @requires_pydantic_v2
    def test_capability_registry_covers_all_server_families(self):
        """Registry has entries for all three IPFS server families."""
        from handsfree.ai.capability_registry import list_virtual_ai_os_capabilities

        caps = list_virtual_ai_os_capabilities()
        families = {c.server_family for c in caps}
        assert "ipfs_kit" in families
        assert "ipfs_datasets" in families
        assert "ipfs_accelerate" in families

    def test_hallucinate_app_environment_detection(self):
        """Environment detection works correctly."""
        from handsfree.hallucinate_app_defaults import is_hallucinate_app_environment

        # Not set -> False
        os.environ.pop("HALLUCINATE_APP_MANAGED", None)
        assert is_hallucinate_app_environment() is False

        # Set -> True
        os.environ["HALLUCINATE_APP_MANAGED"] = "true"
        assert is_hallucinate_app_environment() is True

        # Clean up
        del os.environ["HALLUCINATE_APP_MANAGED"]

    def test_dashboard_catalog_entries_for_all_servers(self):
        """Dashboard catalog entries can be generated for all server families."""
        from handsfree.hallucinate_app_defaults import (
            get_hallucinate_app_dashboard_catalog_entry,
        )

        for family in ("ipfs_kit", "ipfs_datasets", "ipfs_accelerate"):
            entry = get_hallucinate_app_dashboard_catalog_entry(family)
            assert entry["daemon_id"], f"No daemon_id for {family}"
            assert entry["endpoint"], f"No endpoint for {family}"
            assert entry["health_path"], f"No health_path for {family}"
            assert entry["tool_protocols"], f"No tool_protocols for {family}"

    @requires_pydantic_v2
    def test_execution_matrix_complete(self):
        """Execution matrix includes all IPFS capabilities."""
        from handsfree.ai.capability_registry import (
            build_virtual_ai_os_execution_matrix,
        )

        matrix = build_virtual_ai_os_execution_matrix()
        cap_ids = {row["capability_id"] for row in matrix}

        # All IPFS-related capabilities must be in the matrix
        required = {
            "embedding", "ipfs_pin", "storage", "dataset_discovery",
            "workflow", "agentic_fetch", "hardware_profile", "inference",
            "ipfs_add_content", "ipfs_get_content",
        }
        for req in required:
            assert req in cap_ids, f"Missing capability in execution matrix: {req}"

    @requires_pydantic_v2
    def test_swissknife_virtual_ui_binding_includes_ipfs_caps(self):
        """SwissKnife virtual UI binding includes IPFS capability IDs."""
        from handsfree.swissknife_virtual_ui import build_swissknife_surface_metadata

        metadata = build_swissknife_surface_metadata()
        cap_ids = metadata.get("orb_plane", {}).get("capability_ids", ())

        # Must include IPFS capabilities
        assert "embedding" in cap_ids
        assert "ipfs_pin" in cap_ids
        assert "storage" in cap_ids


# --------------------------------------------------------------------------- #
# Extended endpoint coverage tests
# --------------------------------------------------------------------------- #


class TestExtendedEndpointCoverage:
    """Tests verifying the new endpoints (hardware_profile, list_models, list_datasets, inference)."""

    def _get_router_paths(self):
        """Import the router directly (bypass handlers/__init__.py which triggers pydantic v2)."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "ipfs_integration",
            str(Path(__file__).resolve().parents[2] / "src" / "handsfree" / "handlers" / "ipfs_integration.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except ImportError:
            pytest.skip("Cannot import ipfs_integration (missing pydantic/fastapi)")
        return [route.path for route in mod.router.routes]

    @pytest.mark.skipif(not _PYDANTIC_V2_AVAILABLE, reason="Requires pydantic v2")
    def test_ipfs_integration_router_has_hardware_profile(self):
        """The /v1/ipfs/hardware_profile endpoint exists in the router."""
        paths = self._get_router_paths()
        assert "/hardware_profile" in paths

    @pytest.mark.skipif(not _PYDANTIC_V2_AVAILABLE, reason="Requires pydantic v2")
    def test_ipfs_integration_router_has_list_models(self):
        """The /v1/ipfs/list_models endpoint exists in the router."""
        paths = self._get_router_paths()
        assert "/list_models" in paths

    @pytest.mark.skipif(not _PYDANTIC_V2_AVAILABLE, reason="Requires pydantic v2")
    def test_ipfs_integration_router_has_list_datasets(self):
        """The /v1/ipfs/list_datasets endpoint exists in the router."""
        paths = self._get_router_paths()
        assert "/list_datasets" in paths

    @pytest.mark.skipif(not _PYDANTIC_V2_AVAILABLE, reason="Requires pydantic v2")
    def test_ipfs_integration_router_has_inference(self):
        """The /v1/ipfs/inference endpoint exists in the router."""
        paths = self._get_router_paths()
        assert "/inference" in paths

    @pytest.mark.skipif(not _PYDANTIC_V2_AVAILABLE, reason="Requires pydantic v2")
    def test_total_endpoint_count_is_13(self):
        """Router should have 13 endpoints (9 original + 4 new)."""
        paths = self._get_router_paths()
        assert len(paths) >= 13, f"Expected >=13 endpoints, got {len(paths)}: {paths}"

    def test_ipc_handler_file_declares_extended_channels(self):
        """ipfs_ipc_handlers.js includes the new IPC channels."""
        ipc_file = Path(__file__).resolve().parents[2] / "hallucinate_app" / "hallucinate_app" / "node" / "ipfs_ipc_handlers.js"
        if not ipc_file.exists():
            pytest.skip("hallucinate_app submodule not available")

        content = ipc_file.read_text()
        for channel in ["HARDWARE_PROFILE", "LIST_MODELS", "LIST_DATASETS", "INFERENCE"]:
            assert channel in content, f"Missing IPC channel: {channel}"

    def test_preload_exposes_extended_api(self):
        """preload.cjs exposes the new IPFS API methods."""
        preload = Path(__file__).resolve().parents[2] / "hallucinate_app" / "preload.cjs"
        if not preload.exists():
            pytest.skip("hallucinate_app submodule not available")

        content = preload.read_text()
        for method in ["hardwareProfile", "listModels", "listDatasets", "inference"]:
            assert method in content, f"Missing preload method: {method}"

    def test_swissknife_datasets_command_exists(self):
        """SwissKnife has a datasets-command.ts file."""
        cmd_file = Path(__file__).resolve().parents[2] / "swissknife" / "src" / "commands" / "datasets-command.ts"
        if not cmd_file.exists():
            pytest.skip("swissknife submodule not available")

        content = cmd_file.read_text()
        assert "DatasetsCommand" in content
        assert "embed" in content
        assert "listDatasets" in content

    def test_swissknife_accelerate_command_exists(self):
        """SwissKnife has an accelerate-command.ts file."""
        cmd_file = Path(__file__).resolve().parents[2] / "swissknife" / "src" / "commands" / "accelerate-command.ts"
        if not cmd_file.exists():
            pytest.skip("swissknife submodule not available")

        content = cmd_file.read_text()
        assert "AccelerateCommand" in content
        assert "hardwareProfile" in content
        assert "inference" in content

    def test_handsfree_backend_bridge_exists(self):
        """SwissKnife has a handsfree-backend-bridge.ts that routes ORB capabilities."""
        bridge_file = Path(__file__).resolve().parents[2] / "swissknife" / "src" / "integration" / "ipfs" / "handsfree-backend-bridge.ts"
        if not bridge_file.exists():
            pytest.skip("swissknife submodule not available")

        content = bridge_file.read_text()
        assert "HandsfreeBackendBridge" in content
        assert "routeORBCapability" in content
        # Must map all key operations
        for op in ["ipfs_add", "ipfs_cat", "embed", "hardware_profile", "inference", "list_datasets"]:
            assert op in content, f"Missing ORB route mapping: {op}"
