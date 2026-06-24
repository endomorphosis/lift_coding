from __future__ import annotations

import pytest

from handsfree.meta_glasses_multimodal_io_transport_contract import (
    MCP_PLUS_PLUS_ENVELOPE_PROFILE,
    META_GLASSES_CONTROL_PLANE_DEVICES,
    META_GLASSES_CONTROL_PLANE_EVENT_TYPES,
    META_GLASSES_MOCK_BOUNDARY_STATES,
    META_GLASSES_MULTIMODAL_IO_CONTRACT,
    META_GLASSES_REQUIRED_ENVELOPE_FIELDS,
    META_GLASSES_TRANSPORT_ASSUMPTIONS,
    build_meta_glasses_control_plane_event,
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
