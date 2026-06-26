"""Meta glasses multimodal I/O control-plane transport contract.

The contract is intentionally hardware-free: tests and Swissknife apps can emit
these events without paired glasses, while native DAT/Web Apps adapters can later
translate real device observations into the same control-plane envelope.
"""

from __future__ import annotations

from typing import Final


META_GLASSES_MULTIMODAL_IO_CONTRACT: Final = (
    "handsfree.meta-glasses/multimodal-io-control-plane@0.1.0"
)
META_GLASSES_MULTIMODAL_IO_MOCK_BOUNDARY: Final = (
    "handsfree.meta-glasses/mock-multimodal-io-boundary@0.1.0"
)
MCP_PLUS_PLUS_ENVELOPE_PROFILE: Final = "swissknife.mcp++/event-envelope@0.1.0"

META_GLASSES_CONTROL_PLANE_DEVICES: Final[tuple[str, ...]] = (
    "camera",
    "microphone",
    "headphones",
    "display",
    "captouch",
    "Neural Band",
)

META_GLASSES_CONTROL_PLANE_EVENT_TYPES: Final[tuple[str, ...]] = (
    "camera.photo_ref",
    "camera.video_frame_ref",
    "microphone.route_state",
    "microphone.transcript_ref",
    "headphones.route_state",
    "headphones.playback_state",
    "display.lifecycle_state",
    "display.action",
    "captouch.intent",
    "Neural Band.intent",
    "permission.state",
    "transport.handoff",
)

META_GLASSES_TRANSPORT_ASSUMPTIONS: Final[dict[str, str]] = {
    "bluetooth": (
        "Bluetooth is treated as the phone-to-glasses route for audio profiles "
        "and local device state, not as raw libp2p transport."
    ),
    "wifi": (
        "Wi-Fi may carry app-level handoff traffic through the mobile edge or "
        "Web App path, but raw radio sockets are outside this contract."
    ),
    "dat_availability": (
        "DAT camera/display capabilities are optional; unavailable, denied, or "
        "unsupported states must produce fallback receipts."
    ),
    "ipfs_libp2p_handoff": (
        "IPFS CIDs and libp2p peer/session identifiers live in envelope metadata "
        "for payload handoff and replay, not in raw hardware packets."
    ),
    "mcp_plus_plus": (
        "Every event envelope is compatible with MCP++ receipts by carrying "
        "contract, operation, correlation, policy, and provenance fields."
    ),
}

META_GLASSES_REQUIRED_ENVELOPE_FIELDS: Final[tuple[str, ...]] = (
    "contract",
    "profile",
    "event_type",
    "device",
    "source",
    "edge_session_id",
    "app_binding_id",
    "correlation_id",
    "payload",
    "transport",
    "handoff",
    "fallback",
    "control_plane",
    "policy",
    "receipts",
)

META_GLASSES_MOCK_BOUNDARY_STATES: Final[tuple[str, ...]] = (
    "mock_ready",
    "dat_ready",
    "dat_unavailable",
    "permission_denied",
    "unsupported_capability",
    "route_degraded",
    "route_lost",
)

META_GLASSES_PLAYWRIGHT_FIXTURE_ID: Final = (
    "mgw-519-meta-glasses-control-plane-playwright-fixture"
)


def build_meta_glasses_control_plane_event(
    *,
    event_type: str,
    device: str,
    edge_session_id: str,
    app_binding_id: str,
    correlation_id: str,
    payload: dict[str, object] | None = None,
    transport: dict[str, object] | None = None,
    handoff: dict[str, object] | None = None,
    fallback: dict[str, object] | None = None,
    policy: dict[str, object] | None = None,
    receipts: tuple[str, ...] = (),
) -> dict[str, object]:
    """Build a deterministic MCP++-compatible Meta glasses I/O event envelope."""

    if event_type not in META_GLASSES_CONTROL_PLANE_EVENT_TYPES:
        raise ValueError(f"Unsupported Meta glasses control-plane event type: {event_type}")
    if device not in META_GLASSES_CONTROL_PLANE_DEVICES:
        raise ValueError(f"Unsupported Meta glasses control-plane device: {device}")

    return {
        "contract": META_GLASSES_MULTIMODAL_IO_CONTRACT,
        "profile": MCP_PLUS_PLUS_ENVELOPE_PROFILE,
        "event_type": event_type,
        "device": device,
        "source": "hardware-free-mock",
        "edge_session_id": edge_session_id,
        "app_binding_id": app_binding_id,
        "correlation_id": correlation_id,
        "payload": payload or {},
        "transport": {
            "bluetooth": "route-state",
            "wifi": "app-level-handoff",
            **(transport or {}),
        },
        "handoff": {
            "ipfs_cids": [],
            "libp2p_peer_id": None,
            "libp2p_session_id": None,
            "mcp_plus_plus_profile": MCP_PLUS_PLUS_ENVELOPE_PROFILE,
            **(handoff or {}),
        },
        "fallback": {
            "dat_available": False,
            "state": "mock_ready",
            **(fallback or {}),
        },
        "control_plane": {
            "route": "swissknife.mobile_orb.publish_glasses_event",
            "operation": "publish_glasses_event",
        },
        "policy": policy or {"outcome": "allow", "source": "mock"},
        "receipts": list(receipts),
    }


def build_meta_glasses_playwright_fixture(
    *,
    fixture_id: str = META_GLASSES_PLAYWRIGHT_FIXTURE_ID,
    edge_session_id: str = "edge-session-mgw-519-playwright",
    app_binding_id: str = "swissknife-app-binding-mgw-519",
) -> dict[str, object]:
    """Build a deterministic hardware-free fixture for Playwright replay.

    The fixture keeps camera, microphone, headphones, display, captouch, and
    Neural Band events on the same control-plane route that physical DAT
    adapters will use later, with receipt CIDs preserved for replay against real
    devices.
    """

    base_handoff = {
        "ipfs_cids": ["bafy-mgw519-fixture-root"],
        "libp2p_peer_id": "12D3KooWMgw519FixturePeer",
        "libp2p_session_id": "libp2p-mgw-519-playwright",
    }
    scenarios = (
        (
            "camera.photo_ref",
            "camera",
            "corr-mgw519-camera",
            {
                "mode": "photo",
                "cid": "bafy-mgw519-camera-photo",
                "mime_type": "image/jpeg",
                "redaction": "content-addressed-reference-only",
            },
            "bafy-mgw519-receipt-camera",
        ),
        (
            "microphone.transcript_ref",
            "microphone",
            "corr-mgw519-microphone",
            {
                "route": "bluetooth-hfp",
                "transcript_cid": "bafy-mgw519-microphone-transcript",
                "raw_audio": "not_in_fixture",
            },
            "bafy-mgw519-receipt-microphone",
        ),
        (
            "headphones.playback_state",
            "headphones",
            "corr-mgw519-headphones",
            {
                "route": "bluetooth-a2dp",
                "state": "playing",
                "spoken_summary": "Task status rendered on Meta glasses.",
            },
            "bafy-mgw519-receipt-headphones",
        ),
        (
            "display.action",
            "display",
            "corr-mgw519-display",
            {
                "widget_id": "swissknife-playwright-status-widget",
                "action": "render_widget",
                "render_path": "display-webapp",
            },
            "bafy-mgw519-receipt-display",
        ),
        (
            "captouch.intent",
            "captouch",
            "corr-mgw519-captouch",
            {
                "intent": "select",
                "gesture": "single_tap",
                "surface": "right_temple",
                "confidence": 0.97,
            },
            "bafy-mgw519-receipt-captouch",
        ),
        (
            "Neural Band.intent",
            "Neural Band",
            "corr-mgw519-neural-band",
            {
                "intent": "activate",
                "key": "Enter",
                "confidence": 0.94,
            },
            "bafy-mgw519-receipt-neural-band",
        ),
    )

    events = [
        build_meta_glasses_control_plane_event(
            event_type=event_type,
            device=device,
            edge_session_id=edge_session_id,
            app_binding_id=app_binding_id,
            correlation_id=correlation_id,
            payload=payload,
            handoff={
                **base_handoff,
                "ipfs_cids": [
                    *base_handoff["ipfs_cids"],
                    *(
                        value
                        for key, value in payload.items()
                        if key == "cid" or key.endswith("_cid")
                    ),
                ],
            },
            fallback={
                "dat_available": False,
                "state": "dat_unavailable",
                "reason": "MGW-519 Playwright control-plane fixture runs without paired Meta glasses hardware.",
            },
            policy={
                "outcome": "allow",
                "source": "mgw-519-playwright-fixture",
                "capabilities": [f"{device}/mock", "control-plane/replay"],
            },
            receipts=(receipt_cid,),
        )
        for event_type, device, correlation_id, payload, receipt_cid in scenarios
    ]

    return {
        "task_id": "MGW-519",
        "fixture_id": fixture_id,
        "description": (
            "Meta glasses hardware-free control-plane mocks for Playwright and "
            "Swissknife app validation."
        ),
        "contract": META_GLASSES_MULTIMODAL_IO_CONTRACT,
        "mock_boundary": META_GLASSES_MULTIMODAL_IO_MOCK_BOUNDARY,
        "profile": MCP_PLUS_PLUS_ENVELOPE_PROFILE,
        "playwright_ready": True,
        "edge_session": {
            "edge_session_id": edge_session_id,
            "app_binding_id": app_binding_id,
            "hardware_required": False,
            "paired_meta_glasses_required": False,
        },
        "events": events,
        "replay_receipts": [
            {
                "receipt_cid": receipt,
                "correlation_id": correlation_id,
                "physical_dat_replay_target": "Meta Wearables DAT device session",
                "preserve_for_dat_replay": True,
            }
            for _, _, correlation_id, _, receipt in scenarios
        ],
    }
