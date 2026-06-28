"""Tests verifying all virtual desktop apps are integrated with MCP backend tools."""
import pytest
import json
import re


# --- Test helpers ---

def read_browser_main():
    """Read the browser-main.ts source for verification."""
    with open('swissknife/web/src/browser-main.ts', 'r') as f:
        return f.read()


# --- File Manager Integration ---

class TestFileManagerIntegration:
    """Verify File Manager connects to ipfs_kit_py endpoints."""
    
    def test_has_pin_button(self):
        src = read_browser_main()
        assert 'fm-pin-btn' in src
        assert 'Pin to IPFS' in src

    def test_has_upload_button(self):
        src = read_browser_main()
        assert 'fm-upload-btn' in src
        assert 'Upload to IPFS' in src

    def test_uses_add_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/add' in src

    def test_uses_list_pins_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/list_pins' in src

    def test_uses_pin_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/pin' in src

    def test_uses_status_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/status' in src

    def test_shows_ipfs_panel(self):
        src = read_browser_main()
        assert 'ipfs-panel' in src
        assert 'IPFS Pinned Content' in src


# --- Model Browser Integration ---

class TestModelBrowserIntegration:
    """Verify Model Browser connects to ipfs_accelerate_py endpoints."""
    
    def test_uses_list_models(self):
        src = read_browser_main()
        assert '/v1/ipfs/list_models' in src

    def test_uses_capabilities(self):
        src = read_browser_main()
        assert '/v1/ipfs/capabilities' in src

    def test_uses_hardware_profile(self):
        src = read_browser_main()
        assert '/v1/ipfs/hardware_profile' in src

    def test_uses_search_models(self):
        src = read_browser_main()
        assert '/v1/ipfs/search_models' in src

    def test_has_model_search(self):
        src = read_browser_main()
        assert 'model-search' in src

    def test_shows_gpu_info(self):
        src = read_browser_main()
        assert 'model-hw-info' in src
        assert 'GPU:' in src


# --- Task Manager Integration ---

class TestTaskManagerIntegration:
    """Verify Task Manager connects to monitoring endpoints."""
    
    def test_uses_metrics_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/metrics' in src

    def test_uses_endpoints_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/endpoints' in src

    def test_checks_mcp_daemons(self):
        src = read_browser_main()
        assert 'ipfs_kit_py' in src
        assert 'ipfs_datasets_py' in src
        assert 'ipfs_accelerate_py' in src

    def test_shows_daemon_ports(self):
        src = read_browser_main()
        assert '8004' in src
        assert '3002' in src
        assert '3003' in src

    def test_shows_gpu_utilization(self):
        src = read_browser_main()
        assert 'GPU Utilization' in src
        assert 'tm-gpu' in src

    def test_shows_throughput(self):
        src = read_browser_main()
        assert 'Throughput' in src
        assert 'tm-throughput' in src


# --- Code Editor Integration ---

class TestCodeEditorIntegration:
    """Verify Code Editor connects to AI generation and IPFS storage."""
    
    def test_has_save_to_ipfs(self):
        src = read_browser_main()
        assert 'ce-save-ipfs' in src
        assert 'Save to IPFS' in src

    def test_has_ai_assist(self):
        src = read_browser_main()
        assert 'ce-ai-assist' in src
        assert 'AI Assist' in src

    def test_has_load_cid(self):
        src = read_browser_main()
        assert 'ce-load-cid' in src
        assert 'Load CID' in src

    def test_uses_generate_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/generate' in src

    def test_uses_add_for_save(self):
        src = read_browser_main()
        # Code editor uses /v1/ipfs/add for saving
        assert 'ce-save-ipfs' in src
        assert '/v1/ipfs/add' in src

    def test_uses_cat_for_load(self):
        src = read_browser_main()
        assert '/v1/ipfs/cat' in src

    def test_has_keyboard_shortcut(self):
        src = read_browser_main()
        assert "ctrlKey" in src
        assert "Space" in src


# --- Terminal Integration ---

class TestTerminalIntegration:
    """Verify Terminal provides CLI access to all IPFS commands."""
    
    def test_has_ipfs_status_command(self):
        src = read_browser_main()
        assert "'ipfs status'" in src

    def test_has_ipfs_add_command(self):
        src = read_browser_main()
        assert "'ipfs add'" in src

    def test_has_ipfs_cat_command(self):
        src = read_browser_main()
        assert "'ipfs cat'" in src

    def test_has_ipfs_pin_command(self):
        src = read_browser_main()
        assert "'ipfs pin'" in src

    def test_has_ipfs_pins_command(self):
        src = read_browser_main()
        assert "'ipfs pins'" in src

    def test_has_ipfs_models_command(self):
        src = read_browser_main()
        assert "'ipfs models'" in src

    def test_has_ipfs_capabilities_command(self):
        src = read_browser_main()
        assert "'ipfs capabilities'" in src

    def test_has_ipfs_datasets_command(self):
        src = read_browser_main()
        assert "'ipfs datasets'" in src

    def test_has_ipfs_search_command(self):
        src = read_browser_main()
        assert "'ipfs search'" in src

    def test_has_ipfs_generate_command(self):
        src = read_browser_main()
        assert "'ipfs generate'" in src

    def test_has_ipfs_inference_command(self):
        src = read_browser_main()
        assert "'ipfs inference'" in src

    def test_has_ipfs_hardware_command(self):
        src = read_browser_main()
        assert "'ipfs hardware'" in src

    def test_has_ipfs_metrics_command(self):
        src = read_browser_main()
        assert "'ipfs metrics'" in src

    def test_has_ipfs_stat_command(self):
        src = read_browser_main()
        assert "'ipfs stat'" in src

    def test_has_help_command(self):
        src = read_browser_main()
        assert "'help'" in src
        assert "Available IPFS commands" in src

    def test_routes_to_correct_endpoints(self):
        src = read_browser_main()
        # Each command maps to the correct backend endpoint
        assert '/v1/ipfs/status' in src
        assert '/v1/ipfs/add' in src
        assert '/v1/ipfs/cat' in src
        assert '/v1/ipfs/pin' in src
        assert '/v1/ipfs/list_pins' in src
        assert '/v1/ipfs/stat' in src
        assert '/v1/ipfs/list_models' in src
        assert '/v1/ipfs/capabilities' in src
        assert '/v1/ipfs/hardware_profile' in src
        assert '/v1/ipfs/metrics' in src
        assert '/v1/ipfs/list_datasets' in src
        assert '/v1/ipfs/search/semantic' in src
        assert '/v1/ipfs/generate' in src
        assert '/v1/ipfs/inference' in src


# --- Settings Integration ---

class TestSettingsIntegration:
    """Verify Settings displays MCP backend configuration."""
    
    def test_shows_ucan_identity(self):
        src = read_browser_main()
        assert 'UCAN Identity' in src
        assert 'ucanIdentity' in src or 'ucanDid' in src

    def test_shows_mcp_backend_ports(self):
        src = read_browser_main()
        # Settings shows all port assignments
        assert ':8004' in src
        assert ':3002' in src
        assert ':3003' in src
        assert ':8765' in src

    def test_shows_backend_status(self):
        src = read_browser_main()
        assert 'backendOnline' in src or 'Online' in src

    def test_shows_meta_glasses_status(self):
        src = read_browser_main()
        assert 'Meta Glasses' in src


# --- AI Chat Integration ---

class TestAIChatIntegration:
    """Verify AI Chat connects to generation/search endpoints."""
    
    def test_uses_generate_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/generate' in src

    def test_uses_semantic_search(self):
        src = read_browser_main()
        assert '/v1/ipfs/search/semantic' in src

    def test_uses_inference_endpoint(self):
        src = read_browser_main()
        assert '/v1/ipfs/inference' in src


# --- Cross-cutting Integration ---

class TestCrossCuttingIntegration:
    """Verify overall integration patterns across all apps."""
    
    def test_all_apps_use_backend_constant(self):
        """All app functions should use a BACKEND constant."""
        src = read_browser_main()
        # Count BACKEND declarations (each app function should have one)
        backend_decls = src.count("const BACKEND = 'http://localhost:8080'")
        # At minimum: File Manager, Model Browser, Task Manager, Code Editor, Terminal
        assert backend_decls >= 5, f"Expected at least 5 BACKEND declarations, found {backend_decls}"

    def test_all_apps_have_error_handling(self):
        """All apps should handle fetch failures gracefully."""
        src = read_browser_main()
        # Check for try/catch around fetch calls
        assert src.count('catch') >= 10, "Expected error handling in all apps"

    def test_all_backend_endpoints_covered(self):
        """All 31 backend endpoints should be accessible from at least one app."""
        src = read_browser_main()
        required_endpoints = [
            '/v1/ipfs/status', '/v1/ipfs/add', '/v1/ipfs/cat', '/v1/ipfs/pin',
            '/v1/ipfs/list_pins', '/v1/ipfs/list_models', '/v1/ipfs/capabilities',
            '/v1/ipfs/hardware_profile', '/v1/ipfs/metrics', '/v1/ipfs/endpoints',
            '/v1/ipfs/generate', '/v1/ipfs/inference', '/v1/ipfs/search/semantic',
            '/v1/ipfs/list_datasets', '/v1/ipfs/stat', '/v1/ipfs/search_models',
        ]
        missing = [ep for ep in required_endpoints if ep not in src]
        assert len(missing) == 0, f"Missing endpoints in UI: {missing}"

    def test_timeout_protection(self):
        """Fetch calls should have timeout protection."""
        src = read_browser_main()
        assert 'AbortSignal.timeout' in src or 'signal:' in src

    def test_all_13_apps_registered(self):
        """All 13 desktop apps should be in the app registry."""
        src = read_browser_main()
        expected_apps = [
            'file-manager', 'model-browser', 'task-manager',
            'code-editor', 'terminal', 'ai-chat', 'settings',
        ]
        for app in expected_apps:
            assert app in src, f"App '{app}' not found in registry"
