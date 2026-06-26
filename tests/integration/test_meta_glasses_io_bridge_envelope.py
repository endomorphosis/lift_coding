"""Integration proof for Meta glasses IPFS/libp2p/MCP++ bridge envelopes."""

from __future__ import annotations

import copy
import hashlib
from typing import Any

import pytest


CAPABILITIES = [
    "camera.photo_capture",
    "microphone.input",
    "neural_band.input",
    "captouch.input",
    "motion.orientation",
    "phone_gps.context",
    "display.output",
]
CID_PREFIX = "sha256:"
RAW_TRANSPORTS = {"bluetooth", "wifi"}
CONTROL_ROUTES = {
    "swissknife.mobile_orb.publish_glasses_event",
    "swissknife.mobile_orb.request_capture",
    "swissknife.webapp_bridge.publish_display_event",
}


def cid(seed: str) -> str:
    return f"{CID_PREFIX}{hashlib.sha256(seed.encode('utf-8')).hexdigest()}"


def make_envelope(
    capability: str,
    *,
    raw_transport: str = "wifi",
    bridge_provider: str = "display-webapp",
    readiness: str = "ready",
    backpressure: str = "none",
    permission_state: str = "granted",
    sequence: int = 1,
) -> dict[str, Any]:
    correlation_id = f"corr-mgw-420-{capability.replace('.', '-')}-{sequence}"
    bridge_route = (
        "phone-app.bluetooth-audio"
        if raw_transport == "bluetooth"
        else "display-webapp.browser-bridge"
    )
    control_route = (
        "swissknife.mobile_orb.publish_glasses_event"
        if raw_transport == "bluetooth" or capability == "phone_gps.context"
        else "swissknife.webapp_bridge.publish_display_event"
    )
    if capability.startswith("camera."):
        control_route = "swissknife.mobile_orb.request_capture"

    content_cid = cid(f"payload:{capability}:{correlation_id}")
    envelope_cid = cid(f"envelope:{capability}:{correlation_id}:{content_cid}")
    libp2p_provided = raw_transport == "wifi"
    outcome = "deny" if permission_state == "denied" else "allow"
    return {
        "profile": "handsfree.meta-glasses/io-bridge-transport",
        "profile_version": "0.1.0",
        "io_profile": "handsfree.meta-glasses/expanded-io",
        "io_profile_version": "0.1.0",
        "envelope_id": envelope_cid,
        "identity": {
            "device_id": "meta-glasses-device-mgw-420",
            "device_session_id": "device-session-mgw-420",
            "app_binding_id": f"{capability}.binding",
            "app_id": "swissknife.meta-glasses",
            "correlation_id": correlation_id,
        },
        "route": {
            "raw_transport": raw_transport,
            "bridge_provider": bridge_provider,
            "bridge_route": bridge_route,
            "raw_transport_is_ipfs_libp2p_or_mcp": False,
            "route_decision_id": f"route-mgw-420-{capability}",
            "control_plane_route": control_route,
            "readiness": readiness,
            "capability": capability,
        },
        "permission": {
            "state": permission_state,
            "required_scopes": [f"meta_glasses.{capability}", "meta_glasses.control.route"],
            "granted_scopes": [] if permission_state == "denied" else ["meta_glasses.control.route"],
            "denied_scopes": [f"meta_glasses.{capability}"] if permission_state == "denied" else [],
        },
        "flow_control": {
            "latency_ms": 22 if raw_transport == "wifi" else 42,
            "jitter_ms": 5,
            "backpressure": backpressure,
            "queued_bytes": 2048 if backpressure == "soft_limit" else 0,
            "dropped_messages": 0,
        },
        "payload_limits": {
            "max_payload_bytes": 1_048_576 if raw_transport == "wifi" else 65_536,
            "max_content_cid_count": 8,
            "chunking_required_above_bytes": 262_144 if raw_transport == "wifi" else 16_384,
            "inline_payload_allowed": False,
        },
        "content": [
            {
                "cid": content_cid,
                "purpose": "input" if capability != "display.output" else "output",
                "size_bytes": 4096,
                "media_type": "application/octet-stream",
            }
        ],
        "app_layers": {
            "ipfs": "provided_by_bridge",
            "libp2p": "provided_by_bridge" if libp2p_provided else "not_provided",
            "mcp_plus_plus": "provided_by_bridge",
            **(
                {
                    "libp2p_peer_id": f"12D3KooW{capability.replace('.', '')}Peer",
                    "libp2p_remote_peer_id": "12D3KooWMetaGlassesRemotePeer",
                    "libp2p_session_id": f"libp2p-session-{capability.replace('.', '-')}",
                }
                if libp2p_provided
                else {}
            ),
        },
        "receipts": {
            "mcp_tool_receipt_id": f"mcp-tool-receipt-{correlation_id}",
            "mcp_event_receipt_id": f"mcp-event-receipt-{correlation_id}",
            "envelope_cid": envelope_cid,
            "policy_receipt_id": f"policy-receipt-{correlation_id}",
        },
        "policy": {
            "decision_id": f"policy-{capability}-{sequence}",
            "outcome": outcome,
            "reasons": ["bridge envelope authorized by Hallucinate App policy"],
            "required_scopes": [f"meta_glasses.{capability}", "meta_glasses.control.route"],
            "granted_scopes": [] if outcome == "deny" else ["meta_glasses.control.route"],
            "decision_cid": cid(f"policy:{capability}:{correlation_id}:{outcome}"),
        },
        "privacy": {
            "strategy": "content_reference_only",
            "redacted_fields": ["payload.inline_bytes", "raw_transport.local_address"],
            "metadata_cid": cid(f"privacy:{capability}:{correlation_id}"),
            "reason": "raw payload remains behind the bridge",
        },
    }


def validate_envelope(envelope: dict[str, Any] | None) -> list[str]:
    if envelope is None:
        return ["ENVELOPE_MISSING"]

    errors: list[str] = []
    route = envelope.get("route") or {}
    permission = envelope.get("permission") or {}
    flow = envelope.get("flow_control") or {}
    limits = envelope.get("payload_limits") or {}
    app_layers = envelope.get("app_layers") or {}
    receipts = envelope.get("receipts") or {}
    policy = envelope.get("policy")
    content = envelope.get("content")

    if (
        envelope.get("profile") != "handsfree.meta-glasses/io-bridge-transport"
        or envelope.get("profile_version") != "0.1.0"
        or envelope.get("io_profile") != "handsfree.meta-glasses/expanded-io"
    ):
        errors.append("PROFILE")
    if not envelope.get("identity", {}).get("app_binding_id"):
        errors.append("IDENTITY")
    if route.get("raw_transport") not in RAW_TRANSPORTS:
        errors.append("BRIDGE_ROUTE")
    if route.get("raw_transport_is_ipfs_libp2p_or_mcp") is not False:
        errors.append("APP_LAYER_BOUNDARY")
    if route.get("control_plane_route") not in CONTROL_ROUTES or not route.get("route_decision_id"):
        errors.append("ROUTE_DECISION")
    if not permission or "state" not in permission:
        errors.append("PERMISSION_STATE")
    if flow.get("latency_ms", -1) < 0 or flow.get("backpressure") not in {"none", "soft_limit", "hard_limit", "blocked"}:
        errors.append("FLOW_CONTROL")
    if limits.get("max_payload_bytes", 0) <= 0 or limits.get("max_content_cid_count", 0) < len(content or []):
        errors.append("PAYLOAD_LIMITS")
    if not content or any(not str(ref.get("cid", "")).startswith(CID_PREFIX) for ref in content):
        errors.append("CONTENT_CIDS")
    if app_layers.get("libp2p") == "provided_by_bridge" and not all(
        app_layers.get(key)
        for key in ("libp2p_peer_id", "libp2p_remote_peer_id", "libp2p_session_id")
    ):
        errors.append("UNAUTHORIZED_RELAY")
    if app_layers.get("libp2p") == "not_provided" and any(
        app_layers.get(key)
        for key in ("libp2p_peer_id", "libp2p_remote_peer_id", "libp2p_session_id")
    ):
        errors.append("APP_LAYER_BOUNDARY")
    if not receipts.get("mcp_tool_receipt_id") or not receipts.get("mcp_event_receipt_id") or not str(receipts.get("envelope_cid", "")).startswith(CID_PREFIX):
        errors.append("RECEIPTS")
    if not policy or not policy.get("decision_id") or policy.get("outcome") not in {"allow", "deny", "fallback", "degrade", "require_confirmation"}:
        errors.append("POLICY_DECISION")
    if policy and policy.get("outcome") == "deny" and permission.get("state") != "denied":
        errors.append("UNAUTHORIZED_RELAY")
    if not envelope.get("privacy", {}).get("redacted_fields"):
        errors.append("PRIVACY_REDACTION")
    return errors


def route_status(envelope: dict[str, Any], *, seen: set[str], in_flight: int = 0) -> str:
    errors = validate_envelope(envelope)
    if errors:
        return f"failed:{errors[0]}"
    replay_key = ":".join(
        [
            envelope["identity"]["app_id"],
            envelope["identity"]["app_binding_id"],
            envelope["identity"]["correlation_id"],
        ]
    )
    if replay_key in seen:
        return "replayed"
    seen.add(replay_key)
    if envelope["flow_control"]["backpressure"] in {"hard_limit", "blocked"} or in_flight >= 4:
        return "backpressure"
    if envelope["policy"]["outcome"] == "deny":
        return "denied"
    if envelope["route"]["readiness"] in {"unsupported", "stale_session"}:
        return "fallback"
    return "accepted"


@pytest.mark.parametrize("capability", CAPABILITIES)
def test_bridge_envelopes_carry_required_ipfs_libp2p_mcp_metadata(capability: str) -> None:
    raw_transport = "bluetooth" if capability in {"microphone.input", "phone_gps.context"} else "wifi"
    provider = "phone-app" if raw_transport == "bluetooth" else "display-webapp"
    envelope = make_envelope(capability, raw_transport=raw_transport, bridge_provider=provider)

    assert validate_envelope(envelope) == []
    assert envelope["content"][0]["cid"].startswith(CID_PREFIX)
    assert envelope["receipts"]["mcp_tool_receipt_id"].startswith("mcp-tool-receipt-")
    assert envelope["receipts"]["mcp_event_receipt_id"].startswith("mcp-event-receipt-")
    assert envelope["receipts"]["policy_receipt_id"].startswith("policy-receipt-")
    assert envelope["policy"]["decision_cid"].startswith(CID_PREFIX)
    assert envelope["route"]["route_decision_id"]
    assert envelope["identity"]["app_binding_id"].endswith(".binding")
    assert envelope["route"]["raw_transport_is_ipfs_libp2p_or_mcp"] is False
    assert envelope["payload_limits"]["inline_payload_allowed"] is False
    assert envelope["flow_control"]["latency_ms"] >= 0
    if raw_transport == "wifi":
        assert envelope["app_layers"]["libp2p_peer_id"].startswith("12D3KooW")
        assert envelope["app_layers"]["libp2p_session_id"].startswith("libp2p-session-")
    else:
        assert envelope["app_layers"]["libp2p"] == "not_provided"


def test_replay_backpressure_payload_limits_and_fallback_states_are_deterministic() -> None:
    seen: set[str] = set()
    envelope = make_envelope("display.output")
    assert route_status(envelope, seen=seen) == "accepted"
    assert route_status(envelope, seen=seen) == "replayed"

    backpressure = make_envelope("display.output", backpressure="hard_limit", sequence=2)
    assert route_status(backpressure, seen=seen) == "backpressure"

    fallback = make_envelope("display.output", readiness="unsupported", sequence=3)
    assert route_status(fallback, seen=seen) == "fallback"

    too_many_cids = make_envelope("camera.photo_capture", sequence=4)
    too_many_cids["payload_limits"]["max_content_cid_count"] = 0
    assert validate_envelope(too_many_cids) == ["PAYLOAD_LIMITS"]


@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (lambda env: env.update({"profile": "wrong"}), ["PROFILE"]),
        (lambda env: env["route"].update({"raw_transport_is_ipfs_libp2p_or_mcp": True}), ["APP_LAYER_BOUNDARY"]),
        (lambda env: env.pop("policy"), ["POLICY_DECISION"]),
        (lambda env: env["policy"].update({"outcome": "deny"}), ["UNAUTHORIZED_RELAY"]),
        (lambda env: env["app_layers"].pop("libp2p_session_id"), ["UNAUTHORIZED_RELAY"]),
        (lambda env: env["route"].update({"raw_transport": "ipfs"}), ["BRIDGE_ROUTE"]),
        (lambda env: env["receipts"].update({"mcp_event_receipt_id": ""}), ["RECEIPTS"]),
        (lambda env: env["content"][0].update({"cid": "not-a-cid"}), ["CONTENT_CIDS"]),
    ],
)
def test_malformed_missing_policy_unauthorized_raw_transport_and_missing_receipts_fail(
    mutation: Any,
    expected: list[str],
) -> None:
    envelope = make_envelope("display.output")
    mutated = copy.deepcopy(envelope)
    mutation(mutated)
    errors = validate_envelope(mutated)

    assert errors == expected
