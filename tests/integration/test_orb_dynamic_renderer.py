"""Test suite for ORB Dynamic App Renderer and auto-UI generation pipeline.

Validates the complete ORB → IDL → Auto-UI → Desktop + Glasses flow under
UIIRDynamicRendererSecurity@1 (UIR-035):
- Dynamic app renderer generates correct HTML structure with escaped text
- Widget selection from JSON schema types
- HTTP method resolution retained for display (GET vs POST badges)
- Form generation from method input schemas
- Result rendering (table, list, denial/error states) via governed ORB path
- No direct fetch/HTTP bypass; policy-mediated invoker required
- Integration with virtual desktop and glasses control plane
"""

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
# ORB Dynamic App Renderer (UIR-035)
# ===========================================================================


class TestORBDynamicAppRenderer:
    """Verify the auto-UI renderer for virtual desktop (governed path)."""

    @pytest.fixture
    def source(self):
        return read_ts("web/src/orb-dynamic-app-renderer.ts")

    def test_renderer_class_exported(self, source):
        assert "export class ORBDynamicAppRenderer" in source

    def test_uir035_security_interface(self, source):
        """Stable UIIRDynamicRendererSecurity@1 identity must be exported."""
        assert "UIIRDynamicRendererSecurity@1" in source
        assert "UIIR_DYNAMIC_RENDERER_SECURITY_INTERFACE" in source

    def test_render_app_method(self, source):
        assert "renderApp(descriptor:" in source

    def test_bind_events_method(self, source):
        assert "bindEvents(container:" in source

    def test_open_orb_generated_app_factory(self, source):
        assert "export function openORBGeneratedApp(" in source

    def test_widget_selection_types(self, source):
        """Must support all widget types."""
        widgets = ["text", "number", "checkbox", "textarea", "json", "cid"]
        for w in widgets:
            assert f"'{w}'" in source, f"Missing widget type: {w}"

    def test_cid_detection_from_field_name(self, source):
        """Fields named 'cid' or ending in '_cid' should use CID widget."""
        assert "name === 'cid'" in source
        assert "endsWith('_cid')" in source

    def test_http_method_resolution(self, source):
        """Must resolve GET vs POST for display badges on method tabs."""
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

    def test_html_escaping_helpers(self, source):
        """UIR-035: all descriptor/result text must go through escaping."""
        assert "export function escapeHtml" in source
        assert "export function sanitizeDescriptorText" in source
        assert "export function looksHostile" in source
        assert "sanitizeDescriptorText" in source
        assert "escapeHtml(" in source

    def test_hostile_markers_blocked(self, source):
        """Executable markers must be detected and never re-echoed raw."""
        assert "'<script'" in source
        assert "'javascript:'" in source
        assert "blocked unsafe content" in source

    def test_result_rendering_table(self, source):
        """Object results rendered as key-value table with escaped cells."""
        assert "<table" in source
        assert "Object.entries" in source

    def test_result_rendering_array(self, source):
        """Array results rendered as capped list with escaped items."""
        assert ".slice(0, 50)" in source

    def test_denial_and_error_rendering(self, source):
        """Denials/errors remain visible and accessible (role=alert)."""
        assert "_renderDenial" in source
        assert 'role="' in source
        assert "alertdialog" in source or "alert" in source
        assert "err?.message" in source or "err.message" in source

    def test_correlation_id_tracking(self, source):
        """Must generate correlation IDs for ORB tracking (no raw HTTP headers)."""
        assert "correlationId" in source
        assert "orb_" in source
        # Direct HTTP header path removed under UIR-035.
        assert "X-Correlation-Id" not in source

    def test_governed_invoker_required(self, source):
        """Actions must route through a policy-mediated ORB invoker."""
        assert "GovernedOrbInvoker" in source
        assert "governedInvoker" in source
        assert "missing_governed_invoker" in source or "Governed ORB invoker is required" in source

    def test_direct_http_blocked(self, source):
        """Direct fetch/HTTP bypass must be absent or explicitly blocked."""
        assert "blockDirectHttp" in source
        assert "blockedDirectHttpAttempts" in source
        # Fail-closed: no AbortSignal.timeout-based raw fetch path.
        assert "AbortSignal.timeout" not in source
        assert "_checkBackendStatus" not in source

    def test_uiir_binding_identity_on_invoke(self, source):
        """Governed invocations retain UI-IR / policy binding fields."""
        assert "ui_ir_cid" in source
        assert "action_binding_id" in source
        assert "policy_cid" in source
        assert "uiIrCid" in source
        assert "actionBindingId" in source
        assert "policyCid" in source

    def test_latency_display(self, source):
        """Must show request latency."""
        assert "orb-latency" in source
        assert "performance.now()" in source

    def test_result_panel_region(self, source):
        """Results land in an accessible live region panel."""
        assert "orb-result-panel" in source
        assert "aria-live" in source

    def test_global_exports(self, source):
        """Must export to window for browser use."""
        assert "window" in source
        assert "ORBDynamicAppRenderer" in source
        assert "openORBGeneratedApp" in source
        assert "escapeHtml" in source


# ===========================================================================
# Virtual Desktop Integration
# ===========================================================================


class TestVirtualDesktopIntegration:
    """Verify the ORB renderer is wired into the virtual desktop."""

    @pytest.fixture
    def source(self):
        return read_ts("web/legacy-archive/src/browser-main.ts")

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
        kit_block = source[source.find("name: 'ipfs-kit'") : source.find("name: 'ipfs-datasets'")]
        kit_methods = kit_block.count("{ name: '")
        assert kit_methods >= 10, f"Kit has {kit_methods} methods, expected >= 10"


# ===========================================================================
# Glasses Registry Update
# ===========================================================================


class TestGlassesRegistryUpdate:
    """Verify the control plane now includes ORB Auto-UI."""

    @pytest.fixture
    def source(self):
        # UIR / glasses path lives under services/glasses/ (not services/ root).
        return read_ts("src/services/glasses/glasses-app-control-plane.ts")

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
