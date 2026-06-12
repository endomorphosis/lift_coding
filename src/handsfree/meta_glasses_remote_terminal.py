"""Meta glasses remote terminal endpoint contract.

The mobile bridge remains the transport owner, but routing callers need stable
audio and display endpoint ids so they can treat the glasses as a terminal
surface instead of a generic notification target.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Final

REMOTE_TERMINAL_CONTRACT_ID: Final = "handsfree.meta-glasses/remote-terminal@0.1.0"


@dataclass(frozen=True)
class MetaGlassesRemoteTerminalEndpoint:
    """A routable terminal endpoint exposed through the mobile/glasses bridge."""

    endpoint_id: str
    channel: str
    direction: str
    role: str
    handler_ref: str
    fallback_target: str
    contract_id: str = REMOTE_TERMINAL_CONTRACT_ID

    def as_dict(self) -> dict[str, str]:
        """Return the endpoint as JSON-serializable contract metadata."""
        return {
            "endpoint_id": self.endpoint_id,
            "channel": self.channel,
            "direction": self.direction,
            "role": self.role,
            "handler_ref": self.handler_ref,
            "fallback_target": self.fallback_target,
            "contract_id": self.contract_id,
        }


_REMOTE_TERMINAL_ENDPOINTS: tuple[MetaGlassesRemoteTerminalEndpoint, ...] = (
    MetaGlassesRemoteTerminalEndpoint(
        endpoint_id="meta_glasses_audio_input",
        channel="audio",
        direction="input",
        role="command_capture",
        handler_ref="mobile.modules.expo_glasses_audio:record_audio",
        fallback_target="phone_microphone",
    ),
    MetaGlassesRemoteTerminalEndpoint(
        endpoint_id="meta_glasses_audio_output",
        channel="audio",
        direction="output",
        role="tts_playback",
        handler_ref="mobile.modules.expo_glasses_audio:play_audio",
        fallback_target="phone_speaker",
    ),
    MetaGlassesRemoteTerminalEndpoint(
        endpoint_id="meta_glasses_display_widget",
        channel="display",
        direction="output",
        role="display_widget_rendering",
        handler_ref=(
            "handsfree.meta_glasses_mobile_orb_runtime:"
            "invoke_mobile_orb_runtime_binding"
        ),
        fallback_target="display_webapp_or_mobile_card",
    ),
)

_ENDPOINTS_BY_ID = {
    endpoint.endpoint_id: endpoint for endpoint in _REMOTE_TERMINAL_ENDPOINTS
}


def list_meta_glasses_remote_terminal_endpoints() -> tuple[
    MetaGlassesRemoteTerminalEndpoint, ...
]:
    """Return stable Meta glasses remote terminal endpoints."""
    return _REMOTE_TERMINAL_ENDPOINTS


def get_meta_glasses_remote_terminal_endpoint(
    endpoint_id: str,
) -> MetaGlassesRemoteTerminalEndpoint:
    """Resolve one Meta glasses remote terminal endpoint by id."""
    normalized = endpoint_id.strip().lower()
    try:
        return _ENDPOINTS_BY_ID[normalized]
    except KeyError as exc:
        raise KeyError(f"Unknown Meta glasses remote terminal endpoint: {endpoint_id}") from exc


def build_meta_glasses_remote_terminal_route(
    *,
    payload: Mapping[str, Any] | None = None,
    render_targets: tuple[str, ...] = ("audio", "display"),
) -> dict[str, Any]:
    """Build a compact route manifest for audio/display terminal dispatch."""
    requested_targets = set(render_targets)
    endpoints = [
        endpoint.as_dict()
        for endpoint in _REMOTE_TERMINAL_ENDPOINTS
        if endpoint.channel in requested_targets
        or endpoint.endpoint_id in requested_targets
        or endpoint.role in requested_targets
    ]
    return {
        "contract_id": REMOTE_TERMINAL_CONTRACT_ID,
        "surface_id": "mobile_glasses",
        "terminal_kind": "meta_glasses_remote_terminal",
        "render_targets": list(render_targets),
        "endpoints": endpoints,
        "payload": dict(payload or {}),
    }


def route_audio_endpoint(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build the Meta glasses audio input/output terminal route."""
    return build_meta_glasses_remote_terminal_route(
        payload=payload,
        render_targets=("audio",),
    )


def route_display_endpoint(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build the Meta glasses display-widget terminal route."""
    return build_meta_glasses_remote_terminal_route(
        payload=payload,
        render_targets=("display", "display_widget_rendering"),
    )


__all__ = [
    "REMOTE_TERMINAL_CONTRACT_ID",
    "MetaGlassesRemoteTerminalEndpoint",
    "build_meta_glasses_remote_terminal_route",
    "get_meta_glasses_remote_terminal_endpoint",
    "list_meta_glasses_remote_terminal_endpoints",
    "route_audio_endpoint",
    "route_display_endpoint",
]
