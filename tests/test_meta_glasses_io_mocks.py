import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWISSKNIFE_FIXTURE = (
    ROOT / "swissknife" / "test" / "fixtures" / "meta-glasses-io" / "hardware-free-expanded-io.json"
)
SOURCE_MATRIX_FIXTURE = (
    ROOT / "swissknife" / "test" / "fixtures" / "meta-glasses-io" / "source-matrix" / "index.json"
)
PYTHON_SOURCE_MATRIX_FIXTURE = ROOT / "tests" / "fixtures" / "meta_glasses_io_source_matrix.json"
MOBILE_FIXTURE = ROOT / "mobile" / "src" / "native" / "__fixtures__" / "metaWearablesIoStates.js"
MOBILE_SOURCE_MATRIX_FIXTURE = (
    ROOT / "mobile" / "src" / "native" / "__fixtures__" / "metaWearablesDatSourceMatrix.js"
)

REQUIRED_CAPABILITIES = {
    "camera.photo_capture",
    "camera.video_capture",
    "microphone.input",
    "speaker.output",
    "headphone.output",
    "display.output",
    "neural_band.input",
    "captouch.input",
    "motion.orientation",
    "phone_gps.context",
}

REQUIRED_FAILURES = {
    "permission_denial",
    "disconnect",
    "unsupported_capability",
    "degraded_capability",
    "stale_session",
    "route_loss",
    "recovery",
}

REQUIRED_SOURCE_FAILURES = {
    "permission_denial",
    "unsupported_display",
    "release_channel_missing",
    "firmware_update_required",
    "dat_app_update_required",
    "route_loss",
    "backpressure",
    "local_storage_limit",
    "recovery",
}

REQUIRED_SOURCE_FAMILIES = {
    "android-dat-displayaccess-v0.7",
    "ios-dat-displayaccess-v0.7",
    "dat-cameraaccess-v0.7",
    "meta-display-webapps-inputs",
    "bluetooth-audio-route-readiness",
}


def load_swissknife_fixture():
    return json.loads(SWISSKNIFE_FIXTURE.read_text())


def load_source_matrix_fixture():
    return json.loads(SOURCE_MATRIX_FIXTURE.read_text())


def test_swissknife_meta_glasses_io_fixture_is_hardware_free():
    fixture = load_swissknife_fixture()

    assert fixture["hardware_free"] is True
    assert fixture["credentials_required"] is False
    assert fixture["dat_package_access_required"] is False
    assert fixture["paired_glasses_required"] is False
    assert fixture["physical_hardware_required"] is False


def test_swissknife_meta_glasses_io_fixture_covers_expanded_io_and_failure_modes():
    fixture = load_swissknife_fixture()
    capabilities = {entry["kind"]: entry for entry in fixture["capabilities"]}
    failures = {entry["id"]: entry for entry in fixture["failure_modes"]}

    assert set(capabilities) == REQUIRED_CAPABILITIES
    assert set(failures) >= REQUIRED_FAILURES
    assert capabilities["camera.photo_capture"]["mock_operation"] == "capturePhoto"
    assert capabilities["camera.video_capture"]["mock_operation"] == "startVideoStream"
    assert capabilities["microphone.input"]["route"] == "bluetooth-hfp-input"
    assert capabilities["speaker.output"]["route"] == "bluetooth-a2dp-output"
    assert capabilities["headphone.output"]["route"] == "bluetooth-a2dp-output"
    assert "widget_rendered" in capabilities["display.output"]["lifecycle"]
    assert "pinch" in capabilities["neural_band.input"]["gestures"]
    assert "swipe_forward" in capabilities["captouch.input"]["touch_events"]
    assert "quaternion" in capabilities["motion.orientation"]["sample"]
    assert capabilities["phone_gps.context"]["sample"]["source"] == "phone-os-mock"


def test_swissknife_meta_glasses_io_fixture_has_bindings_and_control_plane_envelopes():
    fixture = load_swissknife_fixture()
    binding_ids = {entry["binding_id"] for entry in fixture["swissknife_app_bindings"]}
    envelope_types = {entry["event_type"] for entry in fixture["control_plane_envelopes"]}
    envelope_capabilities = {entry["capability"] for entry in fixture["control_plane_envelopes"]}

    for capability in REQUIRED_CAPABILITIES:
        assert f"{capability}.binding" in binding_ids

    assert {"capability.ready", "display.lifecycle", "route.recovered"} <= envelope_types
    assert {"camera.photo_capture", "camera.video_capture", "display.output", "microphone.input"} <= envelope_capabilities
    for envelope in fixture["control_plane_envelopes"]:
        assert envelope["correlation_id"]
        assert envelope["receipt"]["receipt_kind"].startswith("mcp++/")
        assert envelope["receipt"]["receipt_cid"].startswith("sha256:")


def test_mobile_fixture_exports_hardware_free_states_for_all_acceptance_paths():
    source = MOBILE_FIXTURE.read_text()

    required_terms = [
        "META_WEARABLES_IO_STATES",
        "createMetaWearablesIoMockNativeModule",
        "credentialsRequired: false",
        "datPackageAccessRequired: false",
        "pairedGlassesRequired: false",
        "physicalHardwareRequired: false",
        "photoCapture: true",
        "videoStream: true",
        "microphoneRoute: true",
        "speakerRoute: true",
        "headphoneRoute: true",
        "neuralBand: true",
        "captouch: true",
        "motionOrientation: true",
        "phoneGps: true",
        "permissionDenied",
        "disconnected",
        "unsupportedCapability",
        "degradedCapability",
        "staleSession",
        "routeLoss",
        "recovery",
    ]
    for term in required_terms:
        assert term in source


def test_source_matrix_fixture_mirrors_public_dat_and_webapps_shapes_without_hardware():
    matrix = load_source_matrix_fixture()
    source_families = {entry["id"] for entry in matrix["source_families"]}
    failure_modes = {entry["id"]: entry for entry in matrix["failure_modes"]}
    web_app_tokens = json.dumps(matrix["web_app_inputs"])

    assert matrix["hardware_free"] is True
    assert matrix["credentials_required"] is False
    assert matrix["dat_package_access_required"] is False
    assert matrix["paired_glasses_required"] is False
    assert matrix["physical_hardware_required"] is False
    assert source_families == REQUIRED_SOURCE_FAMILIES
    assert set(failure_modes) >= REQUIRED_SOURCE_FAILURES
    assert "display_target_selected" in matrix["display_access_lifecycle_v0_7"]
    assert "device_session_started" in matrix["display_access_lifecycle_v0_7"]
    assert "display_attached" in matrix["display_access_lifecycle_v0_7"]
    assert "display_content_sent" in matrix["display_access_lifecycle_v0_7"]
    assert "camera_stream_started" in matrix["camera_access_lifecycle_v0_7"]
    assert "camera_photo_captured" in matrix["camera_access_lifecycle_v0_7"]
    assert "ArrowLeft" in web_app_tokens
    assert "ArrowRight" in web_app_tokens
    assert "Enter" in web_app_tokens
    assert "pinch" in web_app_tokens
    assert "swipe_forward" in web_app_tokens
    assert any(entry["id"] == "webapp-local-storage-quota" for entry in matrix["storage_limits"])
    assert failure_modes["release_channel_missing"]["readiness"] == "package_or_release_channel_unavailable"
    assert failure_modes["firmware_update_required"]["readiness"] == "firmware_update_required"
    assert failure_modes["dat_app_update_required"]["readiness"] == "dat_app_update_required"
    assert failure_modes["route_loss"]["recovery"] == "reroute_bluetooth_profile"
    assert failure_modes["backpressure"]["recovery"] == "drop_ephemeral_frames_and_resume"


def test_source_matrix_python_and_mobile_exports_cover_required_terms():
    python_matrix = json.loads(PYTHON_SOURCE_MATRIX_FIXTURE.read_text())
    mobile_source = MOBILE_SOURCE_MATRIX_FIXTURE.read_text()

    assert set(python_matrix["required_source_families"]) == REQUIRED_SOURCE_FAMILIES
    assert set(python_matrix["required_failure_modes"]) >= REQUIRED_SOURCE_FAILURES
    for term in [
        "META_WEARABLES_DAT_SOURCE_MATRIX",
        "createMetaWearablesDatSourceMatrixMock",
        "hardwareFree: true",
        "credentialsRequired: false",
        "datPackageAccessRequired: false",
        "pairedGlassesRequired: false",
        "physicalHardwareRequired: false",
        "display_target_selected",
        "device_session_started",
        "display_content_sent",
        "camera_stream_started",
        "camera_photo_captured",
        "bluetooth-hfp-input",
        "bluetooth-a2dp-output",
        "ArrowLeft",
        "ArrowRight",
        "Enter",
        "pinch",
        "swipe_forward",
        "motion.orientation",
        "phone_gps.context",
        "local_storage_limit",
        "permission_denial",
        "unsupported_display",
        "release_channel_missing",
        "firmware_update_required",
        "dat_app_update_required",
        "route_loss",
        "backpressure",
        "recovery",
    ]:
        assert term in mobile_source
