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


@dataclass(frozen=True)
class MetaGlassesTerminalSessionContract:
    """Constrained mobile-hosted terminal session state for glasses routing."""

    session_id: str
    phone_host_id: str
    pairing_state: str
    display_state: str
    audio_command_state: str
    desktop_offload_state: str
    disconnection_policy: str
    fallback_render_path: str
    hardware_required: bool = False

    def as_dict(self) -> dict[str, Any]:
        """Return the session contract as JSON-serializable metadata."""
        return {
            "session_id": self.session_id,
            "phone_host_id": self.phone_host_id,
            "host_mode": "mobile_hosted",
            "terminal_constraints": {
                "hardware_required": self.hardware_required,
                "input_channels": ["audio_command"],
                "output_channels": ["visual_status", "tts"],
                "permitted_actions": [
                    "confirm",
                    "cancel",
                    "retry_pairing",
                    "switch_to_phone_preview",
                    "open_desktop_offload_status",
                ],
            },
            "pairing": {
                "state": self.pairing_state,
                "requires_paired_hardware": False,
                "fallback_when_unpaired": self.fallback_render_path,
            },
            "audio_command_input": {
                "state": self.audio_command_state,
                "endpoint_id": "meta_glasses_audio_input",
                "fallback_endpoint_id": "phone_microphone",
            },
            "visual_status_output": {
                "state": self.display_state,
                "endpoint_id": "meta_glasses_display_widget",
                "fallback_render_path": self.fallback_render_path,
            },
            "disconnection_handling": {
                "policy": self.disconnection_policy,
                "on_pairing_lost": [
                    "mark_display_unavailable",
                    "continue_mobile_session",
                    "surface_reconnect_action",
                ],
                "fallback_render_path": self.fallback_render_path,
            },
            "desktop_offload": {
                "visibility": "visible",
                "state": self.desktop_offload_state,
                "status_region": "peer_offload",
                "fallback_compute_placement": "phone_local",
            },
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
    session_contract: (
        MetaGlassesTerminalSessionContract | Mapping[str, Any] | None
    ) = None,
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
        "session_contract": _session_contract_as_dict(session_contract),
        "payload": dict(payload or {}),
    }


def _session_contract_as_dict(
    session_contract: MetaGlassesTerminalSessionContract | Mapping[str, Any] | None,
) -> dict[str, Any]:
    if session_contract is None:
        return build_meta_glasses_terminal_session_contract().as_dict()
    if isinstance(session_contract, MetaGlassesTerminalSessionContract):
        return session_contract.as_dict()
    return dict(session_contract)


def build_meta_glasses_terminal_session_contract(
    *,
    session_id: str = "mobile-hosted-session",
    phone_host_id: str = "phone-host",
    pairing_state: str = "unpaired",
    display_state: str = "display_unavailable",
    audio_command_state: str = "ready",
    desktop_offload_state: str = "discovering",
    disconnection_policy: str = "degrade_to_mobile_card",
    fallback_render_path: str = "mobile-card",
) -> MetaGlassesTerminalSessionContract:
    """Build the constrained terminal contract for mobile-hosted glasses sessions."""
    return MetaGlassesTerminalSessionContract(
        session_id=session_id,
        phone_host_id=phone_host_id,
        pairing_state=pairing_state,
        display_state=display_state,
        audio_command_state=audio_command_state,
        desktop_offload_state=desktop_offload_state,
        disconnection_policy=disconnection_policy,
        fallback_render_path=fallback_render_path,
    )


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
    "MetaGlassesTerminalSessionContract",
    "build_meta_glasses_remote_terminal_route",
    "build_meta_glasses_terminal_session_contract",
    "get_meta_glasses_remote_terminal_endpoint",
    "list_meta_glasses_remote_terminal_endpoints",
    "route_audio_endpoint",
    "route_display_endpoint",
]
