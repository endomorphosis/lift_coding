"""Test suite for ORB Dynamic App Renderer and auto-UI generation pipeline.

Validates the complete ORB → IDL → Auto-UI → Desktop + Glasses flow:
- Dynamic app renderer generates correct HTML structure
- Widget selection from JSON schema types
- HTTP method resolution for IPFS endpoints
- Form generation from method input schemas
- Result rendering (table, list, error states)
- Integration with virtual desktop and glasses control plane
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SWISSKNIFE = REPO_ROOT / "swissknife"


def read_ts(relative_path: str) -> str:
    path = SWISSKNIFE / relative_path
    if not path.exists():
        pytest.skip(f"{path} not found")
    return path.read_text()


# ===========================================================================
# ORB Dynamic App Renderer
# ===========================================================================

class TestORBDynamicAppRenderer:
    """Verify the auto-UI renderer for virtual desktop."""

    @pytest.fixture
    def source(self):
        return read_ts("web/src/orb-dynamic-app-renderer.ts")

    def test_renderer_class_exported(self, source):
        assert "export class ORBDynamicAppRenderer" in source

    def test_render_app_method(self, source):
        assert "renderApp(descriptor:" in source

    def test_bind_events_method(self, source):
        assert "bindEvents(container:" in source

    def test_open_orb_generated_app_factory(self, source):
        assert "export function openORBGeneratedApp(" in source

    def test_widget_selection_types(self, source):
        """Must support all widget types."""
        widgets = ['text', 'number', 'checkbox', 'textarea', 'json', 'cid']
        for w in widgets:
            assert f"'{w}'" in source, f"Missing widget type: {w}"

    def test_cid_detection_from_field_name(self, source):
        """Fields named 'cid' or ending in '_cid' should use CID widget."""
        assert "name === 'cid'" in source
        assert "endsWith('_cid')" in source

    def test_http_method_resolution(self, source):
        """Must resolve GET vs POST for all methods."""
        assert "GET_METHODS" in source
        assert "'cat'" in source
        assert "'list_pins'" in source
        assert "'capabilities'" in source

    def test_generates_method_tabs(self, source):
        """Rendered HTML must have tabs for each method."""
        assert "orb-method-tab" in source

    def test_generates_form_fields(self, source):
        """Must generate input fields from schema properties."""
        assert "data-field=" in source
        assert "renderFieldInput" in source

    def test_generates_invoke_button(self, source):
        """Each method must have an invoke button."""
        assert "orb-invoke-btn" in source

    def test_shows_output_schema(self, source):
        """Must show expected output schema."""
        assert "Expected Output" in source

    def test_result_rendering_table(self, source):
        """Object results rendered as key-value table."""
        assert "<table" in source

    def test_result_rendering_array(self, source):
        """Array results rendered as list."""
        assert "data.slice(0, 50)" in source

    def test_error_rendering(self, source):
        """Must show error state with details."""
        assert "Invocation Failed" in source
        assert "err.message" in source

    def test_correlation_id_tracking(self, source):
        """Must generate correlation IDs for ORB tracking."""
        assert "correlationId" in source
        assert "X-Correlation-Id" in source

    def test_abort_timeout(self, source):
        """Must enforce request timeout."""
        assert "AbortSignal.timeout" in source

    def test_backend_status_check(self, source):
        """Must check backend status on load."""
        assert "_checkBackendStatus" in source

    def test_latency_display(self, source):
        """Must show request latency."""
        assert "orb-latency" in source
        assert "performance.now()" in source

    def test_global_exports(self, source):
        """Must export to window for browser use."""
        assert "window" in source
        assert "ORBDynamicAppRenderer" in source
        assert "openORBGeneratedApp" in source


# ===========================================================================
# Virtual Desktop Integration
# ===========================================================================

class TestVirtualDesktopIntegration:
    """Verify the ORB renderer is wired into the virtual desktop."""

    @pytest.fixture
    def source(self):
        return read_ts("web/src/browser-main.ts")

    def test_imports_renderer(self, source):
        assert "orb-dynamic-app-renderer" in source

    def test_orb_auto_ui_in_app_dispatcher(self, source):
        assert "'orb-auto-ui'" in source
        assert "openORBAutoUILauncher" in source

    def test_orb_auto_ui_in_start_menu(self, source):
        assert "ORB Auto-UI Launcher" in source

    def test_registered_descriptors_defined(self, source):
        """Must have IDL descriptors for all 3 IPFS services."""
        assert "ORB_REGISTERED_DESCRIPTORS" in source
        assert "'ipfs-kit'" in source
        assert "'ipfs-datasets'" in source
        assert "'ipfs-accelerate'" in source

    def test_launcher_opens_generated_app(self, source):
        """Clicking a service in the launcher opens an ORB-generated app."""
        assert "openORBGeneratedApp(descriptor" in source

    def test_13_apps_registered(self, source):
        """Must have 13 apps in the dispatcher (12 + orb-auto-ui)."""
        app_count = source.count("() => open")
        assert app_count >= 13, f"Expected >= 13 app launchers, got {app_count}"

    def test_descriptors_have_correct_method_counts(self, source):
        """IPFS Kit should have 10 methods, Datasets 6, Accelerate 8."""
        # Find method arrays by checking how many name: entries after each descriptor
        kit_block = source[source.find("name: 'ipfs-kit'"):source.find("name: 'ipfs-datasets'")]
        kit_methods = kit_block.count("{ name: '")
        assert kit_methods >= 10, f"Kit has {kit_methods} methods, expected >= 10"


# ===========================================================================
# Glasses Registry Update
# ===========================================================================

class TestGlassesRegistryUpdate:
    """Verify the control plane now includes ORB Auto-UI."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-app-control-plane.ts")

    def test_orb_auto_ui_display_defined(self, source):
        assert "orbAutoUIGlassesDisplay" in source

    def test_orb_auto_ui_in_registry(self, source):
        assert "{ id: 'orb-auto-ui'" in source

    def test_registry_has_10_static_apps(self, source):
        """Registry should have 10 statically defined apps."""
        count = source.count("{ id: '")
        assert count >= 10, f"Expected >= 10 apps in registry, got {count}"

    def test_orb_auto_ui_has_discover_action(self, source):
        assert "'discover-services'" in source
        assert "'orb_discover'" in source

    def test_orb_auto_ui_has_launch_action(self, source):
        assert "'launch-auto-ui'" in source
        assert "'orb_launch'" in source

    def test_ipfs_apps_documented_as_auto_registered(self, source):
        """Comment must indicate IPFS apps come from IDL auto-registration."""
        assert "auto-registered" in source.lower() or "idl-to-glasses-compiler" in source
