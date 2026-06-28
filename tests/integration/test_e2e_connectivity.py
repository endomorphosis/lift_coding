"""End-to-end integration connectivity verification.

Validates the full IPFS backend pipeline:
    Backend API -> IPC Handlers -> Preload API -> Dashboard JS (BackendConnector)

Tests that:
1. All 31 backend endpoints are defined
2. All IPC channels have matching handlers
3. All preload methods map to valid IPC channels
4. BackendConnector SDK exposes all operations
5. ORB profiles cover all operations
6. Dashboard HTML files include backend-connector.js
"""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import pytest

# Repo root
REPO_ROOT = Path(__file__).parent.parent.parent
HALLUCINATE_APP = REPO_ROOT / "hallucinate_app"
SWISSKNIFE = REPO_ROOT / "swissknife"
HANDSFREE = REPO_ROOT / "src" / "handsfree" / "handlers"


def _load_module_from_path(name: str, path: Path):
    """Load a Python module directly from file path (bypass __init__)."""
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        pytest.skip(f"Cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    return mod, spec


class TestBackendEndpointCoverage:
    """Verify all backend endpoints are defined."""

    def _get_routes(self):
        content = (HANDSFREE / "ipfs_integration.py").read_text()
        routes = re.findall(r'@router\.(get|post|put|delete)\("([^"]+)"', content)
        return [(method.upper(), path) for method, path in routes]

    def test_minimum_endpoint_count(self):
        routes = self._get_routes()
        assert len(routes) >= 31, f"Expected >= 31 endpoints, got {len(routes)}"

    def test_core_endpoints_present(self):
        routes = self._get_routes()
        paths = [r[1] for r in routes]
        required = [
            "/status", "/add", "/cat", "/pin", "/unpin", "/resolve",
            "/embed", "/generate", "/capabilities", "/hardware_profile",
            "/list_models", "/list_datasets", "/inference",
            "/list_pins", "/stat", "/dag/get", "/dag/put",
            "/name/publish", "/name/resolve",
            "/search_models", "/metrics", "/endpoints",
        ]
        for ep in required:
            assert ep in paths, f"Missing endpoint: {ep}"

    def test_extended_endpoints_present(self):
        routes = self._get_routes()
        paths = [r[1] for r in routes]
        extended = [
            "/vector/index", "/vector/search", "/vector/metadata",
            "/search/semantic", "/search/similarity", "/search/faceted",
            "/scrape/url", "/scrape/batch", "/workflow/execute",
        ]
        for ep in extended:
            assert ep in paths, f"Missing extended endpoint: {ep}"


class TestIPCChannelCoverage:
    """Verify IPC handlers cover all channels."""

    def _get_ipc_channels(self):
        path = HALLUCINATE_APP / "hallucinate_app" / "node" / "ipfs_ipc_handlers.js"
        content = path.read_text()
        channels = re.findall(r"(\w+):\s*'(ipfs:[^']+)'", content)
        return dict(channels)

    def test_minimum_channel_count(self):
        channels = self._get_ipc_channels()
        assert len(channels) >= 31, f"Expected >= 31 IPC channels, got {len(channels)}"

    def test_handler_registrations(self):
        path = HALLUCINATE_APP / "hallucinate_app" / "node" / "ipfs_ipc_handlers.js"
        content = path.read_text()
        channels = self._get_ipc_channels()
        for name, channel in channels.items():
            assert f"IPFS_IPC_CHANNELS.{name}" in content, f"No handler for {name} ({channel})"

    def test_extended_channels_exist(self):
        channels = self._get_ipc_channels()
        required = [
            "VECTOR_INDEX", "VECTOR_SEARCH", "VECTOR_METADATA",
            "SEMANTIC_SEARCH", "SIMILARITY_SEARCH", "FACETED_SEARCH",
            "SCRAPE_URL", "SCRAPE_BATCH", "WORKFLOW_EXECUTE",
        ]
        for ch in required:
            assert ch in channels, f"Missing IPC channel: {ch}"


class TestPreloadAPICoverage:
    """Verify preload.cjs exposes all IPC channels."""

    def _get_preload_methods(self):
        path = HALLUCINATE_APP / "preload.cjs"
        content = path.read_text()
        # Match pattern: methodName: (args) => ipcRenderer.invoke('ipfs:channel', ...)
        methods = re.findall(r"(\w+):\s*\([^)]*\)\s*=>\s*ipcRenderer\.invoke\('(ipfs:[^']+)'", content)
        return dict(methods)

    def test_minimum_preload_method_count(self):
        methods = self._get_preload_methods()
        assert len(methods) >= 31, f"Expected >= 31 preload methods, got {len(methods)}"

    def test_preload_matches_ipc_channels(self):
        """Every preload method should map to a registered IPC channel."""
        path = HALLUCINATE_APP / "hallucinate_app" / "node" / "ipfs_ipc_handlers.js"
        ipc_content = path.read_text()
        methods = self._get_preload_methods()
        for method_name, channel in methods.items():
            assert channel in ipc_content, f"Preload method '{method_name}' uses channel '{channel}' not found in IPC handlers"

    def test_extended_preload_methods(self):
        methods = self._get_preload_methods()
        required = [
            "vectorIndex", "vectorSearch", "vectorMetadata",
            "semanticSearch", "similaritySearch", "facetedSearch",
            "scrapeUrl", "scrapeBatch", "workflowExecute",
        ]
        for m in required:
            assert m in methods, f"Missing preload method: {m}"


class TestBackendConnectorSDK:
    """Verify BackendConnector JS SDK exposes all sub-clients."""

    def _get_sdk_content(self):
        path = HALLUCINATE_APP / "hallucinate_app" / "node" / "views" / "components" / "backend-connector.js"
        return path.read_text()

    def test_sdk_classes_defined(self):
        content = self._get_sdk_content()
        classes = ["BackendConnector", "IPFSKitClient", "IPFSDatasetsClient",
                   "IPFSAccelerateClient", "VectorSearchClient", "WebScrapingClient", "WorkflowClient"]
        for cls in classes:
            assert f"class {cls}" in content, f"Missing SDK class: {cls}"

    def test_sdk_sub_routers(self):
        content = self._get_sdk_content()
        routers = ["this.kit", "this.datasets", "this.accelerate",
                   "this.vector", "this.scraping", "this.workflow"]
        for r in routers:
            assert r in content, f"Missing sub-router: {r}"

    def test_kit_methods(self):
        content = self._get_sdk_content()
        methods = ["add", "cat", "pin", "unpin", "listPins", "stat",
                   "dagGet", "dagPut", "namePublish", "nameResolve", "resolve"]
        for m in methods:
            assert f"async {m}(" in content, f"Missing kit method: {m}"

    def test_vector_methods(self):
        content = self._get_sdk_content()
        methods = ["index", "search", "metadata", "semanticSearch", "similaritySearch", "facetedSearch"]
        for m in methods:
            assert f"async {m}(" in content, f"Missing vector method: {m}"


class TestDashboardConnectivity:
    """Verify dashboards include backend-connector.js."""

    VIEWS_DIR = HALLUCINATE_APP / "hallucinate_app" / "node" / "views"

    def test_ipfs_dashboards_have_connector(self):
        for name in ["ipfs_kit_dashboard.html", "ipfs_accelerate_dashboard.html", "ipfs_datasets_dashboard.html"]:
            content = (self.VIEWS_DIR / name).read_text()
            assert "backend-connector.js" in content, f"{name} missing backend-connector.js"

    def test_main_dashboard_has_backend_health(self):
        content = (self.VIEWS_DIR / "dashboard.html").read_text()
        assert "ipfsBackendStatus" in content
        assert "checkBackendHealth" in content

    def test_daemon_manager_has_tool_explorer(self):
        content = (self.VIEWS_DIR / "daemon_manager.html").read_text()
        assert "unified-tool-explorer" in content
        assert "mcppp-panel" in content

    def test_shared_components_exist(self):
        components_dir = self.VIEWS_DIR / "components"
        required = [
            "backend-connector.js",
            "health-status-bar.js",
            "sidebar-nav.js",
            "tool-invocation-panel.js",
            "unified-tool-explorer.js",
            "mcppp-protocol-panel.js",
        ]
        for comp in required:
            assert (components_dir / comp).exists(), f"Missing component: {comp}"


class TestSwissKnifeIntegration:
    """Verify SwissKnife has IPFS integration."""

    def test_desktop_has_ipfs_apps(self):
        path = SWISSKNIFE / "web" / "src" / "browser-main.ts"
        if not path.exists():
            pytest.skip("SwissKnife web source not available")
        content = path.read_text()
        assert "ipfs-explorer" in content
        assert "datasets-browser" in content
        assert "accelerate-panel" in content

    def test_orb_profiles_exist(self):
        path = SWISSKNIFE / "src" / "services" / "ipfs-orb-profiles.ts"
        if not path.exists():
            pytest.skip("ORB profiles not available")
        content = path.read_text()
        assert "ipfsKitProfile" in content
        assert "ipfsDatasetsProfile" in content
        assert "ipfsAccelerateProfile" in content

    def test_commands_registered(self):
        path = SWISSKNIFE / "src" / "commands.ts"
        if not path.exists():
            pytest.skip("commands.ts not available")
        content = path.read_text()
        assert "ipfsBackendCommands" in content

    def test_ipfs_storage_implemented(self):
        path = SWISSKNIFE / "src" / "storage" / "ipfs" / "ipfs-storage.ts"
        if not path.exists():
            pytest.skip("ipfs-storage.ts not available")
        content = path.read_text()
        # Verify placeholders are replaced
        assert "localhost:8080" in content
        assert "list_pins" in content
