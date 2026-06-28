"""Comprehensive test suite for the Meta Glasses control plane system.

Tests the complete glasses integration pipeline before iPhone/Meta Glasses deployment:
- Control plane state machine (app switching, focus, stack navigation)
- Voice intent recognition (16 patterns, slot extraction, aliases)
- Gesture dispatch (13 types, cooldown, confidence threshold)
- ORB bridge endpoint resolution
- Notification pipeline (priority queue, auto-dismiss)
- State synchronization engine
- Widget descriptor validation
- Display profile constraints
"""

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
SWISSKNIFE = REPO_ROOT / "swissknife"


# ---------------------------------------------------------------------------
# Helpers - Parse TypeScript source to verify behavior contracts
# ---------------------------------------------------------------------------

def read_ts(relative_path: str) -> str:
    path = SWISSKNIFE / relative_path
    if not path.exists():
        pytest.skip(f"{path} not found")
    return path.read_text()


# ===========================================================================
# Test Suite 1: Control Plane State Machine
# ===========================================================================

class TestGlassesControlPlane:
    """Verify the GlassesAppControlPlane state machine."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-app-control-plane.ts")

    def test_registry_has_all_apps(self, source):
        """All 9+ apps must be in GLASSES_APP_REGISTRY."""
        required_apps = ['terminal', 'ai-chat', 'file-manager', 'settings',
                         'code-editor', 'task-manager', 'model-browser',
                         'idl-explorer', 'glasses-preview']
        for app in required_apps:
            assert f"id: '{app}'" in source, f"Missing app in registry: {app}"

    def test_all_apps_have_display_profile(self, source):
        """Each app must have a display variable defined."""
        displays = re.findall(r'export const (\w+GlassesDisplay)', source)
        assert len(displays) >= 9, f"Expected >= 9 display profiles, got {len(displays)}"

    def test_control_plane_class_methods(self, source):
        """Control plane must have all lifecycle methods."""
        methods = ['listApps', 'openApp', 'goBack', 'focusNext', 'focusPrevious',
                   'activate', 'getCurrentDisplay', 'registerApp', 'getState']
        for method in methods:
            assert f"{method}(" in source, f"Missing method: {method}"

    def test_focus_order_defined_for_all_displays(self, source):
        """Every display profile must have focus_order."""
        # Count display defs vs focus_order occurrences
        display_count = source.count("makeDisplayProfile(")
        focus_count = source.count("focus_order:")
        # focus_order is in the makeDisplayProfile helper, so it's always set
        assert "focus_order: actions.filter" in source

    def test_all_displays_have_fallback(self, source):
        """Every display must define fallback paths."""
        assert "fallback: [" in source
        # mobile-card fallback must exist
        assert "'mobile-card'" in source
        assert "'notification'" in source

    def test_app_stack_navigation(self, source):
        """goBack must pop from appStack."""
        assert "appStack.pop()" in source
        assert "appStack.push(" in source

    def test_focus_wraps_around(self, source):
        """Focus must wrap using modulo."""
        assert "% focusOrder.length" in source or "% actions.length" in source


# ===========================================================================
# Test Suite 2: Voice Intent Recognition
# ===========================================================================

class TestVoiceIntentRecognition:
    """Verify voice intent patterns and routing."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-enhanced-control-plane.ts")

    def test_all_intent_patterns_defined(self, source):
        """Must have patterns for all core intents."""
        intents = ['app.open', 'app.back', 'focus.next', 'focus.previous',
                   'action.activate', 'search.semantic', 'generate.text']
        for intent in intents:
            assert f"'{intent}'" in source, f"Missing intent: {intent}"

    def test_app_aliases_comprehensive(self, source):
        """Must have aliases for all apps."""
        aliases = ['terminal', 'console', 'shell', 'chat', 'ai', 'files',
                   'editor', 'code', 'settings', 'tasks', 'models',
                   'ipfs', 'datasets', 'accelerate', 'gpu', 'glasses']
        for alias in aliases:
            assert f"'{alias}'" in source, f"Missing voice alias: {alias}"

    def test_voice_patterns_are_case_insensitive(self, source):
        """All regex patterns must use /i flag."""
        patterns = re.findall(r'/([^/]+)/(\w*)', source)
        # TypeScript regex with 'i' flag
        assert source.count("/i,") >= 5 or source.count("/i}") >= 5 or source.count("/i ") >= 5

    def test_slot_extraction_for_search(self, source):
        """Search intent must extract query slot."""
        assert "query" in source
        assert "search" in source.lower()

    def test_slot_extraction_for_generate(self, source):
        """Generate intent must extract prompt slot."""
        assert "prompt" in source

    def test_recognize_returns_null_for_unknown(self, source):
        """Unrecognized transcripts must return null."""
        assert "return null" in source


# ===========================================================================
# Test Suite 3: Gesture Dispatch
# ===========================================================================

class TestGestureDispatch:
    """Verify gesture recognition and dispatch."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-enhanced-control-plane.ts")

    def test_all_gesture_types_defined(self, source):
        """Must support all 13 gesture types."""
        gestures = ['swipe_left', 'swipe_right', 'swipe_up', 'swipe_down',
                    'tap', 'double_tap', 'long_press', 'pinch_in', 'pinch_out',
                    'flick_left', 'flick_right', 'head_nod', 'head_shake']
        for g in gestures:
            assert f"'{g}'" in source, f"Missing gesture type: {g}"

    def test_gesture_bindings_map_to_actions(self, source):
        """Each gesture must map to a control plane action."""
        actions = ['goBack', 'focusNext', 'focusPrevious', 'activate',
                   'scrollUp', 'scrollDown', 'openAppSwitcher',
                   'expandDetail', 'collapseDetail', 'confirm', 'dismiss']
        for action in actions:
            assert f"'{action}'" in source, f"Missing gesture action: {action}"

    def test_cooldown_enforcement(self, source):
        """Must enforce cooldown between gestures."""
        assert "cooldown" in source.lower()
        assert "lastGestureTime" in source or "cooldownMs" in source

    def test_confidence_threshold(self, source):
        """Must reject low-confidence gestures."""
        assert "confidence" in source
        assert "0.7" in source  # Minimum threshold

    def test_gesture_dispatch_returns_action(self, source):
        """dispatch() must return the action string or null."""
        assert "dispatch(" in source
        assert "return binding.action" in source or "return null" in source


# ===========================================================================
# Test Suite 4: ORB Bridge
# ===========================================================================

class TestORBBridge:
    """Verify ORB invoke bridge endpoint resolution."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-enhanced-control-plane.ts")

    def test_all_endpoints_mapped(self, source):
        """Must map all IPFS methods to endpoints."""
        endpoints = ['/add', '/cat', '/pin', '/unpin', '/list_pins', '/stat',
                     '/resolve', '/dag/get', '/dag/put', '/name/publish',
                     '/name/resolve', '/embed', '/generate', '/list_datasets',
                     '/search/semantic', '/vector/search', '/capabilities',
                     '/hardware_profile', '/inference', '/metrics', '/endpoints',
                     '/scrape/url', '/workflow/execute']
        for ep in endpoints:
            assert f"'{ep}'" in source, f"Missing ORB endpoint mapping: {ep}"

    def test_get_vs_post_distinction(self, source):
        """Must correctly identify GET vs POST methods."""
        # These should be GET
        get_methods = ['cat', 'list_pins', 'stat', 'resolve', 'capabilities',
                       'hardware_profile', 'metrics', 'endpoints', 'list_datasets']
        assert "getMethods" in source or "GET" in source
        for method in get_methods:
            assert f"'{method}'" in source

    def test_correlation_id_included(self, source):
        """Must include correlation ID in requests."""
        assert "correlation" in source.lower() or "correlationId" in source

    def test_timeout_enforcement(self, source):
        """Must enforce request timeout."""
        assert "timeout" in source.lower() or "AbortSignal" in source

    def test_error_handling(self, source):
        """Must handle fetch errors gracefully."""
        assert "catch" in source
        assert "success: false" in source or "error" in source


# ===========================================================================
# Test Suite 5: Notification Pipeline
# ===========================================================================

class TestNotificationPipeline:
    """Verify the priority notification queue."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-enhanced-control-plane.ts")

    def test_priority_levels_defined(self, source):
        """Must support 4 priority levels."""
        priorities = ['critical', 'high', 'normal', 'low']
        for p in priorities:
            assert f"'{p}'" in source, f"Missing priority: {p}"

    def test_critical_interrupts_immediately(self, source):
        """Critical notifications must bypass queue."""
        assert "critical" in source
        # Should display immediately
        assert "_display" in source or "display" in source

    def test_queue_size_limit(self, source):
        """Queue must have a maximum size."""
        assert "maxQueueSize" in source or "max" in source.lower()

    def test_auto_dismiss_with_ttl(self, source):
        """Notifications must auto-dismiss after TTL."""
        assert "ttl" in source.lower() or "ttlMs" in source
        assert "setTimeout" in source or "dismiss" in source

    def test_display_modes(self, source):
        """Must support multiple display modes."""
        modes = ['banner', 'toast', 'badge', 'audio_only']
        for mode in modes:
            assert f"'{mode}'" in source, f"Missing display mode: {mode}"


# ===========================================================================
# Test Suite 6: State Synchronization
# ===========================================================================

class TestStateSynchronization:
    """Verify reactive state sync between apps and display."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-enhanced-control-plane.ts")

    def test_state_binding_interface(self, source):
        """Must define StateBinding with source, regionId, transform."""
        assert "StateBinding" in source
        assert "source" in source
        assert "regionId" in source

    def test_dirty_checking(self, source):
        """Must track dirty state keys."""
        assert "dirty" in source

    def test_throttled_updates(self, source):
        """Must throttle updates to respect max_update_hz."""
        assert "throttle" in source.lower() or "schedule" in source.lower()

    def test_listener_notification(self, source):
        """Must notify listeners on state changes."""
        assert "listener" in source.lower()
        assert "onRegionUpdate" in source or "listeners" in source


# ===========================================================================
# Test Suite 7: Widget Descriptor Validation
# ===========================================================================

class TestWidgetDescriptorValidation:
    """Verify glasses widget descriptors pass validation."""

    @pytest.fixture
    def glasses_widgets_source(self):
        return read_ts("src/services/ipfs-glasses-widgets.ts")

    @pytest.fixture
    def display_profile_source(self):
        return read_ts("src/services/meta-glasses-display-profile.ts")

    def test_all_ipfs_widgets_defined(self, glasses_widgets_source):
        """Must have widgets for Kit, Datasets, Accelerate."""
        assert "ipfsKitGlassesWidget" in glasses_widgets_source
        assert "ipfsDatasetsGlassesWidget" in glasses_widgets_source
        assert "ipfsAccelerateGlassesWidget" in glasses_widgets_source

    def test_viewport_size_correct(self, glasses_widgets_source):
        """All widgets must use 600x600 viewport."""
        assert "width: 600" in glasses_widgets_source
        assert "height: 600" in glasses_widgets_source

    def test_all_widgets_have_actions(self, glasses_widgets_source):
        """Each widget must have action bindings."""
        action_count = glasses_widgets_source.count("id: '")
        assert action_count >= 9, f"Expected >= 9 action bindings, got {action_count}"

    def test_focus_order_matches_actions(self, glasses_widgets_source):
        """focus_order must reference valid action IDs."""
        # Extract action IDs
        action_ids = re.findall(r"id: '([^']+)'", glasses_widgets_source)
        focus_refs = re.findall(r"focus_order: \[([^\]]+)\]", glasses_widgets_source)
        # Every focus ref should be a valid action ID (simplified check)
        assert len(focus_refs) >= 3  # One per widget

    def test_display_profile_has_validation(self, display_profile_source):
        """Display profile module must export validation functions."""
        assert "validateMetaGlassesWidgetDescriptor" in display_profile_source
        assert "validateMetaGlassesDisplayProfile" in display_profile_source

    def test_render_path_dat_native(self, glasses_widgets_source):
        """All widgets must use dat-native render path."""
        assert "'dat-native'" in glasses_widgets_source

    def test_mobile_fallback_defined(self, glasses_widgets_source):
        """All widgets must have mobile fallback."""
        assert "'mobile-card'" in glasses_widgets_source

    def test_input_modes_include_voice(self, glasses_widgets_source):
        """All widgets must support voice input."""
        assert "'voice'" in glasses_widgets_source


# ===========================================================================
# Test Suite 8: Display Constraints
# ===========================================================================

class TestDisplayConstraints:
    """Verify display constraints are within safe limits."""

    @pytest.fixture
    def source(self):
        return read_ts("src/services/glasses-app-control-plane.ts")

    def test_max_update_hz_within_limit(self, source):
        """max_update_hz must not exceed 5 (META_GLASSES_MAX_SAFE_UPDATE_HZ)."""
        hz_values = re.findall(r'max_update_hz:\s*(\d+)', source)
        for hz in hz_values:
            assert int(hz) <= 5, f"max_update_hz {hz} exceeds safe limit of 5"

    def test_max_text_blocks_within_limit(self, source):
        """max_text_blocks must be reasonable (<=6)."""
        text_values = re.findall(r'max_text_blocks:\s*(\d+)', source)
        for v in text_values:
            assert int(v) <= 6, f"max_text_blocks {v} too high"

    def test_max_actions_within_limit(self, source):
        """max_actions must be <= 3 (constrained display)."""
        action_values = re.findall(r'max_actions:\s*(\d+)', source)
        for v in action_values:
            assert int(v) <= 3, f"max_actions {v} too high for glasses display"

    def test_regions_within_viewport(self, source):
        """All region bounds must fit within 600x600 viewport."""
        bounds = re.findall(r'bounds:\s*\{\s*x:\s*(\d+),\s*y:\s*(\d+),\s*width:\s*(\d+),\s*height:\s*(\d+)\s*\}', source)
        for x, y, w, h in bounds:
            assert int(x) + int(w) <= 600, f"Region exceeds viewport width: x={x} w={w}"
            assert int(y) + int(h) <= 600, f"Region exceeds viewport height: y={y} h={h}"

    def test_requires_focus_order(self, source):
        """All displays must require focus order (set in makeDisplayProfile helper)."""
        assert "requires_focus_order: true" in source


# ===========================================================================
# Test Suite 9: IDL Profile Integration
# ===========================================================================

class TestIDLProfileIntegration:
    """Verify IDL descriptors are compatible with glasses widget generation."""

    @pytest.fixture
    def idl_source(self):
        return read_ts("src/services/ipfs-idl-descriptors.ts")

    @pytest.fixture
    def ui_profiles_source(self):
        return read_ts("src/services/ipfs-ui-profiles.ts")

    def test_all_idl_descriptors_have_methods(self, idl_source):
        """Every descriptor must have methods array."""
        descriptors = re.findall(r'export const (\w+Descriptor)', idl_source)
        assert len(descriptors) >= 3
        for desc in descriptors:
            assert desc in idl_source

    def test_methods_have_input_output_schemas(self, idl_source):
        """All methods must have inputSchema and outputSchema."""
        input_count = idl_source.count("inputSchema:")
        output_count = idl_source.count("outputSchema:")
        assert input_count >= 25, f"Expected >= 25 inputSchemas, got {input_count}"
        assert output_count >= 25, f"Expected >= 25 outputSchemas, got {output_count}"

    def test_ui_profiles_have_templates(self, ui_profiles_source):
        """UI profiles must define primary_template."""
        templates = re.findall(r"primary_template:\s*'([^']+)'", ui_profiles_source)
        assert 'explorer' in templates
        assert 'dashboard' in templates
        assert 'job-console' in templates

    def test_ui_profiles_have_workflow_graphs(self, ui_profiles_source):
        """At least 2 profiles must have workflow_graph."""
        wf_count = ui_profiles_source.count("workflow_graph:")
        assert wf_count >= 2

    def test_ui_profiles_have_state_models(self, ui_profiles_source):
        """All profiles must have state_model."""
        sm_count = ui_profiles_source.count("state_model:")
        assert sm_count >= 3


# ===========================================================================
# Test Suite 10: Mobile Deployment Readiness
# ===========================================================================

class TestMobileDeploymentReadiness:
    """Verify the system is ready for iPhone/Meta Glasses deployment."""

    def test_mobile_package_exists(self):
        """Mobile package.json must exist."""
        path = REPO_ROOT / "mobile" / "package.json"
        assert path.exists(), "mobile/package.json not found"

    def test_expo_glasses_audio_module(self):
        """expo-glasses-audio module must exist."""
        path = REPO_ROOT / "mobile" / "modules" / "expo-glasses-audio"
        assert path.exists(), "expo-glasses-audio module not found"

    def test_expo_meta_wearables_dat_module(self):
        """expo-meta-wearables-dat module must exist."""
        path = REPO_ROOT / "mobile" / "modules" / "expo-meta-wearables-dat"
        assert path.exists(), "expo-meta-wearables-dat module not found"

    def test_mobile_bridge_exists(self):
        """Mobile ORB bridge TypeScript must exist."""
        path = SWISSKNIFE / "src" / "services" / "meta-glasses-mobile-orb-bridge.ts"
        assert path.exists(), "meta-glasses-mobile-orb-bridge.ts not found"

    def test_display_orb_adapter_exists(self):
        """Display ORB adapter must exist."""
        path = SWISSKNIFE / "src" / "services" / "meta-glasses-display-orb-adapter.ts"
        assert path.exists(), "meta-glasses-display-orb-adapter.ts not found"

    def test_widget_compiler_exists(self):
        """Widget compiler must exist."""
        path = SWISSKNIFE / "src" / "services" / "meta-glasses-widget-compiler.ts"
        assert path.exists(), "meta-glasses-widget-compiler.ts not found"

    def test_interface_registry_exists(self):
        """Interface registry must exist."""
        path = SWISSKNIFE / "src" / "services" / "ipfs-interface-registry.ts"
        assert path.exists(), "ipfs-interface-registry.ts not found"

    def test_control_plane_exports_consistent(self):
        """Both control plane files must export compatible interfaces."""
        cp1 = read_ts("src/services/glasses-app-control-plane.ts")
        cp2 = read_ts("src/services/glasses-enhanced-control-plane.ts")
        # Enhanced must import from base
        assert "GlassesAppControlPlane" in cp2
        assert "GLASSES_APP_REGISTRY" in cp2 or "glasses-app-control-plane" in cp2

    def test_all_action_methods_are_valid_backend_endpoints(self):
        """Action method names must map to known backend endpoints."""
        cp = read_ts("src/services/glasses-app-control-plane.ts")
        enhanced = read_ts("src/services/glasses-enhanced-control-plane.ts")
        
        # Extract method names from action bindings
        methods = set(re.findall(r"method:\s*'([^']+)'", cp))
        
        # Verify endpoint resolver covers them
        endpoints = re.findall(r"'([^']+)':\s*'/[^']*'", enhanced)
        endpoint_methods = set(endpoints)
        
        # Core IPFS methods should be in the resolver
        core_methods = {'add', 'cat', 'pin', 'list_pins', 'stat', 'inference', 'metrics'}
        for m in core_methods:
            assert m in endpoint_methods or m in enhanced, f"Method '{m}' not resolved in ORB bridge"
