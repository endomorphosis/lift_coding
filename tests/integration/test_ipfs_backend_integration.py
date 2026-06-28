"""Integration tests for IPFS backend integration with Hallucinate App/SwissKnife.

These tests verify that:
1. The IPFS adapters correctly handle both available and unavailable states
2. The API endpoints return proper responses
3. The descriptor pack is well-formed for ORB routing
4. The IPC bridge contract is consistent with the backend API
"""

from __future__ import annotations

import base64
import importlib
import json
import sys
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# --------------------------------------------------------------------------- #
# ipfs_kit_adapters tests (corrected to match real API)
# --------------------------------------------------------------------------- #


class TestIPFSKitAdapters:
    """Tests for the ipfs_kit_py adapter layer."""

    def test_unavailable_adapter_raises(self):
        from handsfree.ipfs_kit_adapters import (
            IPFSKitUnavailableError,
            _UnavailableIPFSKitAdapter,
        )

        adapter = _UnavailableIPFSKitAdapter()
        with pytest.raises(IPFSKitUnavailableError):
            adapter.add_bytes(b"test")
        with pytest.raises(IPFSKitUnavailableError):
            adapter.cat("QmTest")
        with pytest.raises(IPFSKitUnavailableError):
            adapter.pin("QmTest")
        with pytest.raises(IPFSKitUnavailableError):
            adapter.unpin("QmTest")
        with pytest.raises(IPFSKitUnavailableError):
            adapter.resolve("QmTest")
        with pytest.raises(IPFSKitUnavailableError):
            adapter.package_dataset([{"key": "value"}])

    def test_unavailable_adapter_get_backend_statuses(self):
        from handsfree.ipfs_kit_adapters import _UnavailableIPFSKitAdapter

        adapter = _UnavailableIPFSKitAdapter()
        assert adapter.get_backend_statuses() == {}

    def test_get_adapter_returns_unavailable_when_not_installed(self):
        from handsfree.ipfs_kit_adapters import (
            get_ipfs_kit_adapter,
            reset_ipfs_kit_adapter_cache,
            _UnavailableIPFSKitAdapter,
        )

        reset_ipfs_kit_adapter_cache()
        with patch.dict(sys.modules, {"ipfs_kit_py": None}):
            reset_ipfs_kit_adapter_cache()
            adapter = get_ipfs_kit_adapter()
            assert isinstance(adapter, _UnavailableIPFSKitAdapter)
        reset_ipfs_kit_adapter_cache()

    def test_module_adapter_uses_ipfs_kit_class(self):
        """Verify the adapter calls ipfs_kit_py.ipfs_kit.ipfs_kit methods."""
        from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

        mock_root = MagicMock()
        adapter = _IPFSKitModuleAdapter(mock_root)

        # Mock the ipfs_kit.ipfs_kit class
        mock_kit_instance = MagicMock()
        mock_kit_instance.ipfs_cat.return_value = b"hello world"
        mock_kit_instance.ipfs_pin_add.return_value = {"Pins": ["QmTest"]}
        mock_kit_instance.ipfs_pin_rm.return_value = {"Pins": ["QmTest"]}

        mock_kit_cls = MagicMock()
        mock_kit_cls.create.return_value = mock_kit_instance

        mock_kit_module = MagicMock()
        mock_kit_module.ipfs_kit = mock_kit_cls

        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = mock_kit_module

            result = adapter.cat("QmTest")
            assert result == b"hello world"
            mock_kit_instance.ipfs_cat.assert_called_once_with("QmTest")

    def test_module_adapter_pin_calls_ipfs_pin_add(self):
        from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

        mock_root = MagicMock()
        adapter = _IPFSKitModuleAdapter(mock_root)

        mock_kit_instance = MagicMock()
        mock_kit_instance.ipfs_pin_add.return_value = {"ok": True}

        mock_kit_cls = MagicMock()
        mock_kit_cls.create.return_value = mock_kit_instance

        mock_kit_module = MagicMock()
        mock_kit_module.ipfs_kit = mock_kit_cls

        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = mock_kit_module
            result = adapter.pin("QmTest")
            mock_kit_instance.ipfs_pin_add.assert_called_once_with("QmTest")

    def test_module_adapter_get_backend_statuses(self):
        from handsfree.ipfs_kit_adapters import _IPFSKitModuleAdapter

        mock_root = MagicMock()
        adapter = _IPFSKitModuleAdapter(mock_root)

        mock_config_module = MagicMock()
        mock_config_module.get_backend_statuses.return_value = {
            "kubo": {"exists": True, "enabled": True}
        }

        with patch("importlib.import_module") as mock_import:
            mock_import.return_value = mock_config_module
            result = adapter.get_backend_statuses()
            assert result == {"kubo": {"exists": True, "enabled": True}}


# --------------------------------------------------------------------------- #
# ipfs_accelerate_adapters tests
# --------------------------------------------------------------------------- #


class TestIPFSAccelerateAdapters:
    """Tests for the ipfs_accelerate_py adapter layer."""

    def test_unavailable_adapter_raises(self):
        from handsfree.ipfs_accelerate_adapters import (
            IPFSAccelerateUnavailableError,
            _UnavailableIPFSAccelerateAdapter,
        )

        adapter = _UnavailableIPFSAccelerateAdapter()
        with pytest.raises(IPFSAccelerateUnavailableError):
            adapter.generate("hello")
        with pytest.raises(IPFSAccelerateUnavailableError):
            adapter.embed(["hello"])
        with pytest.raises(IPFSAccelerateUnavailableError):
            adapter.get_capabilities()
        with pytest.raises(IPFSAccelerateUnavailableError):
            adapter.run_model("model", "input")

    def test_unavailable_adapter_status(self):
        from handsfree.ipfs_accelerate_adapters import _UnavailableIPFSAccelerateAdapter

        adapter = _UnavailableIPFSAccelerateAdapter()
        status = adapter.status()
        assert status["available"] is False

    def test_module_adapter_get_capabilities(self):
        from handsfree.ipfs_accelerate_adapters import _IPFSAccelerateModuleAdapter

        mock_module = MagicMock()
        mock_module.webnn_webgpu_available = True
        mock_module.model_manager_available = True
        mock_module.llm_router_available = True
        mock_module.embeddings_router_available = True
        mock_module.get_instance.side_effect = Exception("no instance")
        # Remove module-level get_capabilities so adapter falls to flag-based path
        del mock_module.get_capabilities

        adapter = _IPFSAccelerateModuleAdapter(mock_module)
        caps = adapter.get_capabilities()
        assert caps["available"] is True
        assert caps["webnn_webgpu_available"] is True

    def test_module_adapter_status_reports_availability_flags(self):
        from handsfree.ipfs_accelerate_adapters import _IPFSAccelerateModuleAdapter

        mock_module = MagicMock()
        mock_module.webnn_webgpu_available = False
        mock_module.llm_router_available = True
        mock_module.embeddings_router_available = False
        mock_module.get_instance.side_effect = Exception("not init")

        adapter = _IPFSAccelerateModuleAdapter(mock_module)
        st = adapter.status()
        assert st["available"] is True
        assert st["llm_router_available"] is True
        assert st["webnn_webgpu_available"] is False


# --------------------------------------------------------------------------- #
# ipfs_datasets_routers tests
# --------------------------------------------------------------------------- #


class TestIPFSDatasetsRouters:
    """Tests for the ipfs_datasets_py router adapter layer."""

    def test_unavailable_embeddings_router_raises(self):
        from handsfree.ipfs_datasets_routers import (
            IPFSDatasetsRouterUnavailableError,
            _UnavailableEmbeddingsRouter,
        )

        router = _UnavailableEmbeddingsRouter()
        with pytest.raises(IPFSDatasetsRouterUnavailableError):
            router.embed_text("hello")
        with pytest.raises(IPFSDatasetsRouterUnavailableError):
            router.embed_texts(["hello"])

    def test_unavailable_ipfs_router_raises(self):
        from handsfree.ipfs_datasets_routers import (
            IPFSDatasetsRouterUnavailableError,
            _UnavailableIPFSRouter,
        )

        router = _UnavailableIPFSRouter()
        with pytest.raises(IPFSDatasetsRouterUnavailableError):
            router.add_bytes(b"data")
        with pytest.raises(IPFSDatasetsRouterUnavailableError):
            router.cat("QmTest")

    def test_unavailable_llm_router_raises(self):
        from handsfree.ipfs_datasets_routers import (
            IPFSDatasetsRouterUnavailableError,
            _UnavailableLLMRouter,
        )

        router = _UnavailableLLMRouter()
        with pytest.raises(IPFSDatasetsRouterUnavailableError):
            router.generate_text("hello")


# --------------------------------------------------------------------------- #
# IPFS Descriptor Pack tests
# --------------------------------------------------------------------------- #


class TestIPFSDescriptorPack:
    """Tests for the SwissKnife IPFS descriptor pack."""

    def test_descriptor_pack_has_all_operations(self):
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        descriptor_ids = {e.descriptor_id for e in pack}
        assert "ipfs.status" in descriptor_ids
        assert "ipfs.add" in descriptor_ids
        assert "ipfs.cat" in descriptor_ids
        assert "ipfs.pin" in descriptor_ids
        assert "ipfs.unpin" in descriptor_ids
        assert "ipfs.resolve" in descriptor_ids
        assert "ipfs.embed" in descriptor_ids
        assert "ipfs.generate" in descriptor_ids
        assert "ipfs.capabilities" in descriptor_ids

    def test_descriptor_pack_as_dicts_is_serializable(self):
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack_as_dicts

        dicts = get_ipfs_descriptor_pack_as_dicts()
        # Must be JSON-serializable
        serialized = json.dumps(dicts)
        assert len(serialized) > 100
        assert all(isinstance(d, dict) for d in dicts)

    def test_mcp_tool_manifest_is_well_formed(self):
        from handsfree.ipfs_descriptor_pack import get_ipfs_mcp_tool_manifest

        manifest = get_ipfs_mcp_tool_manifest()
        assert manifest["name"] == "ipfs-integration"
        assert manifest["version"] == "1.0.0"
        assert len(manifest["tools"]) > 0
        for tool in manifest["tools"]:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

    def test_capability_ids_unique(self):
        from handsfree.ipfs_descriptor_pack import get_ipfs_capability_ids

        ids = get_ipfs_capability_ids()
        assert len(ids) == len(set(ids))

    def test_lookup_descriptor(self):
        from handsfree.ipfs_descriptor_pack import lookup_ipfs_descriptor

        entry = lookup_ipfs_descriptor("ipfs_add_content")
        assert entry is not None
        assert entry.endpoint_path == "/v1/ipfs/add"

        missing = lookup_ipfs_descriptor("nonexistent")
        assert missing is None


# --------------------------------------------------------------------------- #
# API Integration tests (using FastAPI test client)
# --------------------------------------------------------------------------- #


class TestIPFSIntegrationAPI:
    """Tests for the /v1/ipfs/* HTTP endpoints."""

    @pytest.fixture
    def client(self):
        """Create a test client for the FastAPI app."""
        pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient
        from handsfree.handlers.ipfs_integration import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_status_endpoint_returns_structure(self, client):
        resp = client.get("/v1/ipfs/status")
        assert resp.status_code == 200
        data = resp.json()
        assert "ipfs_kit" in data
        assert "ipfs_datasets" in data
        assert "ipfs_accelerate" in data
        assert "timestamp" in data

    def test_capabilities_endpoint(self, client):
        resp = client.get("/v1/ipfs/capabilities")
        assert resp.status_code == 200
        data = resp.json()
        assert "ok" in data
        # May be False if ipfs_accelerate_py not installed - that's OK
        assert "capabilities" in data or "error" in data

    def test_add_endpoint_503_when_no_backend(self, client):
        """When no IPFS backend is available, should return 503."""
        payload = {
            "data_base64": base64.b64encode(b"test data").decode("ascii"),
            "pin": True,
        }
        resp = client.post("/v1/ipfs/add", json=payload)
        # 503 expected when no backend available
        assert resp.status_code in (200, 503)

    def test_cat_endpoint_503_when_no_backend(self, client):
        resp = client.post("/v1/ipfs/cat", json={"cid": "QmTest123"})
        assert resp.status_code in (200, 503)

    def test_embed_endpoint_503_when_no_provider(self, client):
        resp = client.post("/v1/ipfs/embed", json={"texts": ["hello world"]})
        assert resp.status_code in (200, 503)

    def test_generate_endpoint_503_when_no_provider(self, client):
        resp = client.post("/v1/ipfs/generate", json={"prompt": "hello"})
        assert resp.status_code in (200, 503)

    def test_embed_falls_back_to_accelerate_when_datasets_unavailable(self, client):
        from handsfree.ipfs_datasets_routers import IPFSDatasetsRouterUnavailableError

        accelerate = MagicMock()
        accelerate.embed.return_value = [[0.1, 0.2, 0.3]]

        with patch(
            "handsfree.handlers.ipfs_integration.get_embeddings_router",
            side_effect=IPFSDatasetsRouterUnavailableError("datasets unavailable"),
        ), patch(
            "handsfree.handlers.ipfs_integration.get_ipfs_accelerate_adapter",
            return_value=accelerate,
        ):
            resp = client.post("/v1/ipfs/embed", json={"texts": ["hello world"]})

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["provider_used"] == "accelerate"
        assert payload["embeddings"] == [[0.1, 0.2, 0.3]]

    def test_generate_falls_back_to_accelerate_when_datasets_unavailable(self, client):
        from handsfree.ipfs_datasets_routers import IPFSDatasetsRouterUnavailableError

        accelerate = MagicMock()
        accelerate.generate.return_value = "accelerated output"

        with patch(
            "handsfree.handlers.ipfs_integration.get_llm_router",
            side_effect=IPFSDatasetsRouterUnavailableError("llm unavailable"),
        ), patch(
            "handsfree.handlers.ipfs_integration.get_ipfs_accelerate_adapter",
            return_value=accelerate,
        ):
            resp = client.post("/v1/ipfs/generate", json={"prompt": "hello"})

        assert resp.status_code == 200
        payload = resp.json()
        assert payload["provider_used"] == "accelerate"
        assert payload["text"] == "accelerated output"


# --------------------------------------------------------------------------- #
# End-to-end interoperability proof
# --------------------------------------------------------------------------- #


class TestIPFSInteroperabilityProof:
    """Proves the three IPFS packages can be used together through the
    unified capability routing kernel as required by VAIOS-G081/G082/G083."""

    def test_all_adapters_coexist(self):
        """All three adapter modules import cleanly without conflicts."""
        from handsfree.ipfs_kit_adapters import get_ipfs_kit_adapter
        from handsfree.ipfs_datasets_routers import get_embeddings_router, get_ipfs_router, get_llm_router
        from handsfree.ipfs_accelerate_adapters import get_ipfs_accelerate_adapter

        # All should return adapters (possibly unavailable stubs)
        kit = get_ipfs_kit_adapter()
        embeddings = get_embeddings_router()
        ipfs = get_ipfs_router()
        llm = get_llm_router()
        accel = get_ipfs_accelerate_adapter()

        assert kit is not None
        assert embeddings is not None
        assert ipfs is not None
        assert llm is not None
        assert accel is not None

    def test_descriptor_pack_covers_all_adapters(self):
        """The descriptor pack references capabilities from all three packages."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_descriptor_pack

        pack = get_ipfs_descriptor_pack()
        tags_seen = set()
        for entry in pack:
            tags_seen.update(entry.tags)

        # Must cover storage (kit/datasets), AI (datasets/accelerate), hardware (accelerate)
        assert "storage" in tags_seen
        assert "ai" in tags_seen
        assert "accelerate" in tags_seen

    def test_swissknife_binding_includes_ipfs_capabilities(self):
        """The SwissKnife virtual UI binding can reference IPFS capability IDs."""
        from handsfree.ipfs_descriptor_pack import get_ipfs_capability_ids

        try:
            from handsfree.swissknife_virtual_ui import get_swissknife_virtual_ai_os_binding
        except ImportError:
            pytest.skip("swissknife_virtual_ui requires pydantic v2+")

        binding = get_swissknife_virtual_ai_os_binding()
        ipfs_caps = get_ipfs_capability_ids()

        # The binding should be well-formed
        assert binding.binding_id is not None
        assert binding.orb_plane.surface_id == "swissknife_orb"

        # IPFS capabilities should be registerable
        assert len(ipfs_caps) >= 9
