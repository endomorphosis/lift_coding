"""Test suite for IDL-to-Glasses compiler and dashboard state bridge.

Validates:
- Auto-compilation of IDL descriptors into glasses display profiles
- State bridge WebSocket protocol contract
- Deployment readiness validator logic
"""

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SWISSKNIFE = REPO_ROOT / "swissknife"
HALLUCINATE = REPO_ROOT / "hallucinate_app"


def read_ts(relative_path: str) -> str:
    path = SWISSKNIFE / relative_path
    if not path.exists():
        pytest.skip(f"{path} not found")
    return path.read_text()


def read_js(relative_path: str) -> str:
    path = HALLUCINATE / relative_path
    if not path.exists():
        pytest.skip(f"{path} not found")
    return path.read_text()


# ===========================================================================
# IDL-to-Glasses Compiler Tests
# ===========================================================================

class TestIDLToGlassesCompiler:
    """Verify the auto-compilation pipeline."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/idl-to-glasses-compiler.ts")

    def test_exports_main_functions(self, source):
        assert "export function compileIDLToGlassesDisplay(" in source
        assert "export function compileIDLToAppEntry(" in source
        assert "export function autoRegisterIDLServices(" in source

    def test_has_ipfs_descriptors(self, source):
        assert "IPFS_IDL_DESCRIPTORS" in source
        assert "'ipfs-explorer'" in source
        assert "'datasets-browser'" in source
        assert "'accelerate-panel'" in source

    def test_has_compile_options(self, source):
        assert "IPFS_AUTO_COMPILE_OPTIONS" in source
        assert "priorityMethods" in source

    def test_template_selection_heuristic(self, source):
        """Must have heuristic for template selection."""
        assert "selectTemplate" in source
        assert "'list'" in source
        assert "'status'" in source
        assert "'task-progress'" in source
        assert "'single-card'" in source

    def test_method_prioritization(self, source):
        """Must prioritize methods by usability on glasses."""
        assert "prioritizeMethods" in source
        assert "required" in source  # Fewer required params = higher priority

    def test_viewport_is_600x600(self, source):
        assert "width: 600" in source
        assert "height: 600" in source

    def test_actions_are_focusable(self, source):
        assert "focusable: true" in source

    def test_fallback_paths_generated(self, source):
        assert "'mobile-card'" in source
        assert "'notification'" in source

    def test_render_path_dat_native(self, source):
        assert "'dat-native'" in source

    def test_each_descriptor_has_methods(self, source):
        """Each IPFS descriptor must have realistic method list."""
        # Count method definitions per descriptor
        kit_methods = source.count("{ name: '") 
        assert kit_methods >= 20  # 3 services × ~7 methods each

    def test_format_label_function(self, source):
        """Must format method names into readable labels."""
        assert "formatLabel" in source
        assert ".slice(0, 12)" in source  # Constrained to glasses display width

    def test_region_generation_by_template(self, source):
        """Must generate different regions based on template."""
        assert "case 'list'" in source
        assert "case 'status'" in source
        assert "case 'task-progress'" in source

    def test_auto_register_returns_report(self, source):
        """autoRegisterIDLServices must return registered + errors."""
        assert "registered: string[]" in source
        assert "errors: Array<" in source


# ===========================================================================
# State Bridge Tests
# ===========================================================================

class TestGlassesStateBridge:
    """Verify the dashboard-to-glasses WebSocket bridge."""

    @pytest.fixture
    def source(self):
        return read_js("hallucinate_app/node/views/components/glasses-state-bridge.js")

    def test_base_class_exists(self, source):
        assert "class GlassesStateBridge" in source

    def test_ipfs_kit_bridge(self, source):
        assert "class IPFSKitGlassesBridge extends GlassesStateBridge" in source

    def test_ipfs_datasets_bridge(self, source):
        assert "class IPFSDatasetsGlassesBridge extends GlassesStateBridge" in source

    def test_ipfs_accelerate_bridge(self, source):
        assert "class IPFSAccelerateGlassesBridge extends GlassesStateBridge" in source

    def test_websocket_url_configurable(self, source):
        assert "ws://localhost:8765/glasses/state" in source
        assert "wsUrl" in source

    def test_batched_state_updates(self, source):
        """Must batch state updates to reduce network traffic."""
        assert "batchIntervalMs" in source
        assert "_scheduleBatch" in source
        assert "_flushBatch" in source

    def test_reconnect_on_disconnect(self, source):
        assert "reconnectMs" in source
        assert "_connect" in source
        assert "onclose" in source

    def test_command_listener_api(self, source):
        """Must support subscribing to incoming commands."""
        assert "onCommand(listener)" in source
        assert "this.listeners.push" in source

    def test_protocol_messages(self, source):
        """Must send correct message types."""
        assert "'register'" in source
        assert "'state_update'" in source
        assert "'event'" in source
        assert "'pong'" in source

    def test_convenience_methods(self, source):
        """IPFS bridges must have convenience methods."""
        assert "updatePins(" in source
        assert "updateDatasets(" in source
        assert "updateMetrics(" in source
        assert "notifyAdded(" in source
        assert "notifyInference(" in source

    def test_exports_for_browser_and_node(self, source):
        assert "window.GlassesStateBridge" in source
        assert "module.exports" in source

    def test_glasses_events_dispatched(self, source):
        """Must dispatch CustomEvents for glasses interactions."""
        assert "glasses-focus" in source
        assert "glasses-activate" in source


# ===========================================================================
# Dashboard Integration Tests
# ===========================================================================

class TestDashboardGlassesIntegration:
    """Verify dashboards include the glasses bridge."""

    def test_kit_dashboard_includes_bridge(self):
        path = HALLUCINATE / "hallucinate_app/node/views/ipfs_kit_dashboard.html"
        if not path.exists():
            pytest.skip("ipfs_kit_dashboard.html not found")
        content = path.read_text()
        assert "glasses-state-bridge.js" in content
        assert "IPFSKitGlassesBridge" in content

    def test_datasets_dashboard_includes_bridge(self):
        path = HALLUCINATE / "hallucinate_app/node/views/ipfs_datasets_dashboard.html"
        if not path.exists():
            pytest.skip("ipfs_datasets_dashboard.html not found")
        content = path.read_text()
        assert "glasses-state-bridge.js" in content
        assert "IPFSDatasetsGlassesBridge" in content

    def test_accelerate_dashboard_includes_bridge(self):
        path = HALLUCINATE / "hallucinate_app/node/views/ipfs_accelerate_dashboard.html"
        if not path.exists():
            pytest.skip("ipfs_accelerate_dashboard.html not found")
        content = path.read_text()
        assert "glasses-state-bridge.js" in content
        assert "IPFSAccelerateGlassesBridge" in content


# ===========================================================================
# Deployment Readiness Validator Tests
# ===========================================================================

class TestDeploymentValidator:
    """Verify the deployment readiness validator structure."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/deployment-readiness-validator.ts")

    def test_validator_class_exists(self, source):
        assert "class DeploymentReadinessValidator" in source

    def test_validate_method(self, source):
        assert "validate(): DeploymentReport" in source

    def test_all_categories_checked(self, source):
        categories = [
            '_validateControlPlane',
            '_validateIDLCompilation',
            '_validateORBEndpoints',
            '_validateVoicePatterns',
            '_validateGestureBindings',
            '_validateDisplayConstraints',
            '_validateAppRegistry',
            '_validateStateSyncBindings',
            '_validateNotificationPipeline',
            '_validateMobileBridgeContract',
        ]
        for cat in categories:
            assert cat in source, f"Missing validation category: {cat}"

    def test_report_structure(self, source):
        assert "DeploymentReport" in source
        assert "totalChecks" in source
        assert "passed" in source
        assert "failed" in source
        assert "warnings" in source
        assert "deployReady" in source

    def test_format_report_function(self, source):
        assert "formatDeploymentReport" in source

    def test_voice_test_cases(self, source):
        """Must test voice recognition patterns."""
        assert "'open terminal'" in source
        assert "'go back'" in source
        assert "'search for" in source

    def test_gesture_test_all_types(self, source):
        """Must test all 13 gesture types."""
        gestures = ['swipe_left', 'swipe_right', 'swipe_up', 'swipe_down',
                    'tap', 'double_tap', 'long_press',
                    'flick_left', 'flick_right',
                    'pinch_in', 'pinch_out',
                    'head_nod', 'head_shake']
        for g in gestures:
            assert f"'{g}'" in source, f"Missing gesture test: {g}"

    def test_ipfs_auto_registration_verified(self, source):
        """Must verify IPFS apps are auto-registered."""
        assert "ipfs-explorer" in source
        assert "datasets-browser" in source
        assert "accelerate-panel" in source


# ===========================================================================
# Enhanced Control Plane - New Features
# ===========================================================================

class TestEnhancedControlPlaneUpdates:
    """Verify the enhanced control plane improvements."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-enhanced-control-plane.ts")

    def test_imports_idl_compiler(self, source):
        assert "idl-to-glasses-compiler" in source

    def test_auto_register_on_construction(self, source):
        assert "_autoRegisterIDLApps" in source
        assert "autoRegisterIDLServices" in source

    def test_emit_method_on_state_sync(self, source):
        """StateSync must have emit() for gesture events."""
        assert "emit(appId: string, event: string, payload:" in source

    def test_scroll_gesture_handling(self, source):
        """Gesture handler must process scroll actions."""
        assert "case 'scrollUp'" in source
        assert "case 'scrollDown'" in source
        assert "'scroll'" in source

    def test_expand_collapse_handling(self, source):
        assert "case 'expandDetail'" in source
        assert "case 'collapseDetail'" in source
        assert "'zoom'" in source

    def test_app_switcher_gesture(self, source):
        assert "case 'openAppSwitcher'" in source
        assert "listApps()" in source

    def test_context_menu_gesture(self, source):
        assert "case 'showContextMenu'" in source
        assert "'context_menu'" in source
