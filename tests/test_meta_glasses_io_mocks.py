import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SWISSKNIFE_FIXTURE = (
    ROOT / "swissknife" / "test" / "fixtures" / "meta-glasses-io" / "hardware-free-expanded-io.json"
)
MOBILE_FIXTURE = ROOT / "mobile" / "src" / "native" / "__fixtures__" / "metaWearablesIoStates.js"

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


def load_swissknife_fixture():
    return json.loads(SWISSKNIFE_FIXTURE.read_text())


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
