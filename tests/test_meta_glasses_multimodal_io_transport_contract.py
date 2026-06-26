from __future__ import annotations

import json
from pathlib import Path

import pytest

from handsfree.meta_glasses_multimodal_io_transport_contract import (
    MCP_PLUS_PLUS_ENVELOPE_PROFILE,
    META_GLASSES_CONTROL_PLANE_DEVICES,
    META_GLASSES_CONTROL_PLANE_EVENT_TYPES,
    META_GLASSES_MOCK_BOUNDARY_STATES,
    META_GLASSES_MULTIMODAL_IO_CONTRACT,
    META_GLASSES_PLAYWRIGHT_FIXTURE_ID,
    META_GLASSES_REQUIRED_ENVELOPE_FIELDS,
    META_GLASSES_TRANSPORT_ASSUMPTIONS,
    build_meta_glasses_control_plane_event,
    build_meta_glasses_playwright_fixture,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SWISSKNIFE_PLAYWRIGHT_FIXTURE = (
    REPO_ROOT
    / "swissknife"
    / "test"
    / "e2e"
    / "fixtures"
    / "mgw-519-meta-glasses-control-plane.json"
)


def test_meta_glasses_multimodal_io_contract_covers_required_devices_and_transport_terms():
    assert {
        "camera",
        "microphone",
        "headphones",
        "display",
        "captouch",
        "Neural Band",
    }.issubset(META_GLASSES_CONTROL_PLANE_DEVICES)
    assert {
        "camera.photo_ref",
        "microphone.route_state",
        "headphones.route_state",
        "display.lifecycle_state",
        "captouch.intent",
        "Neural Band.intent",
        "transport.handoff",
    }.issubset(META_GLASSES_CONTROL_PLANE_EVENT_TYPES)
    assert "dat_unavailable" in META_GLASSES_MOCK_BOUNDARY_STATES
    assert "unsupported_capability" in META_GLASSES_MOCK_BOUNDARY_STATES
    assert "Bluetooth" in META_GLASSES_TRANSPORT_ASSUMPTIONS["bluetooth"]
    assert "Wi-Fi" in META_GLASSES_TRANSPORT_ASSUMPTIONS["wifi"]
    assert "IPFS CIDs" in META_GLASSES_TRANSPORT_ASSUMPTIONS["ipfs_libp2p_handoff"]
    assert "MCP++" in META_GLASSES_TRANSPORT_ASSUMPTIONS["mcp_plus_plus"]


def test_meta_glasses_control_plane_event_is_mcp_plus_plus_compatible():
    envelope = build_meta_glasses_control_plane_event(
        event_type="camera.photo_ref",
        device="camera",
        edge_session_id="edge-session-1",
        app_binding_id="app-binding-camera",
        correlation_id="corr-1",
        payload={"cid": "bafyphoto"},
        handoff={
            "ipfs_cids": ["bafyphoto"],
            "libp2p_peer_id": "peer-1",
            "libp2p_session_id": "session-1",
        },
        fallback={"dat_available": False, "state": "dat_unavailable"},
        receipts=("receipt-1",),
    )

    assert set(META_GLASSES_REQUIRED_ENVELOPE_FIELDS).issubset(envelope)
    assert envelope["contract"] == META_GLASSES_MULTIMODAL_IO_CONTRACT
    assert envelope["profile"] == MCP_PLUS_PLUS_ENVELOPE_PROFILE
    assert envelope["control_plane"] == {
        "route": "swissknife.mobile_orb.publish_glasses_event",
        "operation": "publish_glasses_event",
    }
    assert envelope["transport"]["bluetooth"] == "route-state"
    assert envelope["transport"]["wifi"] == "app-level-handoff"
    assert envelope["handoff"]["ipfs_cids"] == ["bafyphoto"]
    assert envelope["handoff"]["libp2p_peer_id"] == "peer-1"
    assert envelope["fallback"]["state"] == "dat_unavailable"
    assert envelope["receipts"] == ["receipt-1"]


def test_meta_glasses_control_plane_event_rejects_unknown_boundary_terms():
    with pytest.raises(ValueError, match="event type"):
        build_meta_glasses_control_plane_event(
            event_type="raw.bluetooth.packet",
            device="camera",
            edge_session_id="edge-session-1",
            app_binding_id="app-binding-camera",
            correlation_id="corr-1",
        )

    with pytest.raises(ValueError, match="device"):
        build_meta_glasses_control_plane_event(
            event_type="camera.photo_ref",
            device="raw-radio",
            edge_session_id="edge-session-1",
            app_binding_id="app-binding-camera",
            correlation_id="corr-1",
        )


def test_mgw_519_playwright_fixture_covers_modalities_and_replay_receipts():
    fixture = build_meta_glasses_playwright_fixture()

    assert fixture["task_id"] == "MGW-519"
    assert fixture["fixture_id"] == META_GLASSES_PLAYWRIGHT_FIXTURE_ID
    assert fixture["playwright_ready"] is True
    assert fixture["edge_session"]["paired_meta_glasses_required"] is False

    events = fixture["events"]
    devices = {event["device"] for event in events}
    event_types = {event["event_type"] for event in events}

    assert {
        "camera",
        "microphone",
        "headphones",
        "display",
        "captouch",
        "Neural Band",
    }.issubset(devices)
    assert {
        "camera.photo_ref",
        "microphone.transcript_ref",
        "headphones.playback_state",
        "display.action",
        "captouch.intent",
        "Neural Band.intent",
    }.issubset(event_types)

    for event in events:
        assert event["contract"] == META_GLASSES_MULTIMODAL_IO_CONTRACT
        assert event["control_plane"]["route"] == (
            "swissknife.mobile_orb.publish_glasses_event"
        )
        assert event["fallback"]["state"] == "dat_unavailable"
        assert event["receipts"], event

    replay_receipts = fixture["replay_receipts"]
    assert len(replay_receipts) == len(events)
    assert {receipt["receipt_cid"] for receipt in replay_receipts} == {
        event["receipts"][0] for event in events
    }
    assert all(
        receipt["preserve_for_dat_replay"] is True for receipt in replay_receipts
    )


def test_mgw_519_checked_in_playwright_fixture_is_replayable():
    fixture = json.loads(SWISSKNIFE_PLAYWRIGHT_FIXTURE.read_text(encoding="utf-8"))

    assert fixture["task_id"] == "MGW-519"
    assert fixture["playwright_ready"] is True
    assert fixture["edge_session"]["hardware_required"] is False
    assert {event["device"] for event in fixture["events"]} >= {
        "camera",
        "microphone",
        "headphones",
        "display",
        "captouch",
        "Neural Band",
    }
    assert all(
        event["control_plane"]["operation"] == "publish_glasses_event"
        for event in fixture["events"]
    )
    assert all(event["receipts"] for event in fixture["events"])
    assert all(
        receipt["physical_dat_replay_target"] == "Meta Wearables DAT device session"
        for receipt in fixture["replay_receipts"]
    )
