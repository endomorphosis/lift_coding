"""Hardware-free virtual AI OS integration harness.

The harness intentionally stays in-process: phone, desktop peer, SwissKnife UI,
Hallucinate App command plane, and Meta glasses terminal are represented by
deterministic control-plane records that flow through the public routing kernel
and mobile ORB API.
"""

from __future__ import annotations

import sys
import types
from dataclasses import dataclass, field
from typing import Any

import pytest
from fastapi.testclient import TestClient

from handsfree.ai import CapabilityExecutionMode, CapabilityRuntimeSurface
from handsfree.capability_registry import CapabilityDispatchRequest, CapabilityRoutingKernel
from handsfree.meta_glasses_remote_terminal import (
    REMOTE_TERMINAL_CONTRACT_ID,
    build_meta_glasses_remote_terminal_route,
    build_meta_glasses_terminal_session_contract,
)


@dataclass
class SimulatedDesktopPeer:
    """Minimal desktop peer used by the harness runtime binding."""

    peer_id: str = "desktop-peer-vai-010"
    display_name: str = "Desk GPU"
    offloaded_commands: list[dict[str, Any]] = field(default_factory=list)
    fail_next_status: bool = False

    def run(self, request_arguments: dict[str, Any]) -> dict[str, Any]:
        command = request_arguments["command"]
        self.offloaded_commands.append(
            {
                "command": command,
                "task_id": request_arguments["task_id"],
                "placement": "desktop_peer",
            }
        )
        return {
            "status": "completed",
            "peer_id": self.peer_id,
            "compute_placement": "desktop_peer",
            "stream_events": [
                {
                    "sequence": 1,
                    "stream": "task-progress",
                    "phase": "dispatch",
                    "text": "Command accepted by Hallucinate App.",
                },
                {
                    "sequence": 2,
                    "stream": "task-progress",
                    "phase": "offload",
                    "text": "SwissKnife ORB transferred context to desktop peer.",
                },
                {
                    "sequence": 3,
                    "stream": "task-progress",
                    "phase": "response",
                    "text": "Desktop peer streamed the answer back to the phone.",
                },
            ],
            "response_text": "VAI-010 harness completed on desktop peer.",
            "artifact_refs": request_arguments["artifact_refs"],
        }

    def status_or_recover(self) -> dict[str, Any]:
        if self.fail_next_status:
            self.fail_next_status = False
            return {
                "status": "error",
                "reason": "desktop_peer_disconnected",
                "recoverable": True,
                "recovery": {
                    "action": "fallback_to_phone",
                    "compute_placement": "phone_local",
                    "render_path": "mobile-card",
                },
            }
        return {
            "status": "completed",
            "peer_id": self.peer_id,
            "compute_placement": "desktop_peer",
        }


@dataclass
class SimulatedDesktopOperatorSession:
    """Deterministic desktop operator path across SwissKnife and Hallucinate App."""

    session_id: str = "vai-024-desktop-operator-session"
    presented_sessions: list[dict[str, Any]] = field(default_factory=list)
    mediated_controls: list[dict[str, Any]] = field(default_factory=list)
    placement_receipts: list[dict[str, Any]] = field(default_factory=list)

    def present_swissknife_session(self, dispatch_plan) -> dict[str, Any]:
        swissknife_entrypoint = dispatch_plan.entrypoints[0]
        hallucinate_entrypoint = next(
            entry for entry in dispatch_plan.entrypoints if entry.surface_id == "hallucinate_app"
        )
        session = {
            "session_id": self.session_id,
            "task_id": dispatch_plan.payload["task_id"],
            "presented_by": swissknife_entrypoint.surface_id,
            "operator_console": hallucinate_entrypoint.surface_id,
            "hosted_surface": hallucinate_entrypoint.metadata["hosted_surface"],
            "virtual_ui_plane": swissknife_entrypoint.metadata["virtual_ui_plane"],
            "orb_plane": swissknife_entrypoint.metadata["orb_plane"],
            "controls": ("voice", "pointer", "image", "keyboard"),
            "descriptor_ref": "sha256:vai024-swissknife-session-descriptor",
        }
        self.presented_sessions.append(session)
        return session

    def route_hallucinate_control(
        self,
        *,
        session: dict[str, Any],
        dispatch_plan,
        modality: str,
        control: str,
        placement_preference: str,
    ) -> dict[str, Any]:
        hallucinate_entrypoint = next(
            entry for entry in dispatch_plan.entrypoints if entry.surface_id == "hallucinate_app"
        )
        envelope = {
            "interaction_envelope": {
                "session_id": session["session_id"],
                "surface": "hallucinate_app",
                "source_modality": modality,
                "raw_payload": {"control": control},
            },
            "normalized_intent": {
                "capability_id": dispatch_plan.capability_id,
                "command": control,
                "placement_preference": placement_preference,
            },
            "policy_decision": {
                "outcome": "allow",
                "reason": "desktop_operator_test_harness",
            },
            "mediation_receipt": f"sha256:vai024-{modality}-{placement_preference}-receipt",
            "virtual_desktop_command_intent": {
                "target_surface": session["hosted_surface"],
                "operator_console": hallucinate_entrypoint.surface_id,
                "dispatch_handler": dispatch_plan.route.handler_ref,
            },
        }
        self.mediated_controls.append(envelope)
        return envelope

    def execute_locally(self, *, dispatch_plan, envelope: dict[str, Any]) -> dict[str, Any]:
        receipt = {
            "receipt_cid": "sha256:vai024-local-placement-receipt",
            "session_id": envelope["interaction_envelope"]["session_id"],
            "capability_id": dispatch_plan.capability_id,
            "command": envelope["normalized_intent"]["command"],
            "compute_placement": "local",
            "runtime_surface": dispatch_plan.route.runtime_surface.value,
            "placement_layer": dispatch_plan.route.placement_layer.value,
            "placement_target": dispatch_plan.route.placement_target,
            "status": "completed",
        }
        self.placement_receipts.append(receipt)
        return receipt

    def handoff_to_peer(
        self,
        *,
        dispatch_plan,
        envelope: dict[str, Any],
        desktop_peer: SimulatedDesktopPeer,
    ) -> dict[str, Any]:
        output = desktop_peer.run(
            {
                "task_id": dispatch_plan.payload["task_id"],
                "command": envelope["normalized_intent"]["command"],
                "artifact_refs": dispatch_plan.payload["artifact_refs"],
            }
        )
        receipt = {
            "receipt_cid": "sha256:vai024-peer-placement-receipt",
            "session_id": envelope["interaction_envelope"]["session_id"],
            "capability_id": dispatch_plan.capability_id,
            "command": envelope["normalized_intent"]["command"],
            "compute_placement": output["compute_placement"],
            "runtime_surface": dispatch_plan.route.runtime_surface.value,
            "placement_layer": dispatch_plan.route.placement_layer.value,
            "placement_target": dispatch_plan.route.placement_target,
            "peer_id": output["peer_id"],
            "stream_events": output["stream_events"],
            "status": output["status"],
        }
        self.placement_receipts.append(receipt)
        return receipt


def _install_secret_stub() -> None:
    if "handsfree.secrets" in sys.modules:
        return

    secrets_module = types.ModuleType("handsfree.secrets")
    secrets_module.get_default_secret_manager = lambda: None
    secrets_module.get_secret_manager = lambda *args, **kwargs: None
    secrets_module.reset_secret_manager = lambda: None
    sys.modules["handsfree.secrets"] = secrets_module


def _clear_mobile_orb_state(api_module: Any) -> None:
    api_module.mobile_orb_edge_sessions.clear()
    api_module.mobile_orb_service_bindings.clear()
    api_module.mobile_orb_service_subscriptions.clear()
    api_module.mobile_orb_events.clear()
    api_module.mobile_orb_invocations.clear()
    api_module.mobile_orb_dispatches.clear()
    api_module.mobile_orb_revocations.clear()


@pytest.fixture
def mobile_orb_api():
    _install_secret_stub()
    from handsfree import api as api_module

    _clear_mobile_orb_state(api_module)
    yield TestClient(api_module.app), api_module
    _clear_mobile_orb_state(api_module)


def _display_widget_action(
    *,
    descriptor_cid: str,
    interface_cid: str,
    receipt_cid: str,
    task_id: str,
    title: str,
    summary: str,
    stream_events: list[dict[str, Any]],
    recovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fallback = {
        "reason": "dat_native_display_unavailable",
        "render_path": "mobile-card",
        "message": "Showing the virtual AI OS terminal in the phone preview.",
        "recovery": recovery or {},
    }
    return {
        "type": "mobile_render_display_widget",
        "operation": "render_widget",
        "correlation_id": "corr-vai-010",
        "request_id": f"render-{task_id.lower()}",
        "descriptor_cid": descriptor_cid,
        "interface_cid": interface_cid,
        "widget_id": "virtual-ai-os-e2e-harness",
        "widget_cid": "sha256:vai010-widget",
        "orb_receipt_cid": receipt_cid,
        "manifest": {
            "schema": "handsfree.meta-glasses/widget-manifest",
            "schema_version": "0.1.0",
            "widget_id": "virtual-ai-os-e2e-harness",
            "widget_cid": "sha256:vai010-widget",
            "interface_cid": interface_cid,
            "operation": "render_widget",
            "state": {
                "values": {
                    "title": title,
                    "summary": summary,
                    "status": "streaming" if recovery is None else "recovered",
                    "stream_events": stream_events,
                }
            },
            "fallback": fallback,
        },
        "state": {
            "title": title,
            "summary": summary,
            "status": "streaming" if recovery is None else "recovered",
            "stream_events": stream_events,
        },
        "fallback": fallback,
        "issued_at": "2026-06-23T00:00:00Z",
    }


def test_hardware_free_virtual_ai_os_harness_dispatches_offloads_streams_and_recovers(
    mobile_orb_api, monkeypatch
):
    client, api_module = mobile_orb_api
    desktop_peer = SimulatedDesktopPeer()
    task_id = "VAI-010"
    command = "summarize daemon status and stream it to glasses"
    artifact_refs = {
        "result_cid": "sha256:vai010-result",
        "receipt_ref": "sha256:vai010-receipt",
        "event_dag_ref": "sha256:vai010-events",
        "delegation_ref": "sha256:vai010-delegation",
    }

    dispatch_plan = CapabilityRoutingKernel().dispatch_task(
        CapabilityDispatchRequest(
            capability_id="dataset_discovery",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            source_surface="hallucinate_app",
            payload={
                "task_id": task_id,
                "command": command,
                "operator_plane": "hallucinate_app",
                "artifact_refs": artifact_refs,
            },
        )
    )
    route = dispatch_plan.route
    entrypoint_ids = [entry.surface_id for entry in dispatch_plan.entrypoints]
    swissknife_entrypoint = dispatch_plan.entrypoints[0]
    hallucinate_entrypoint = next(
        entry for entry in dispatch_plan.entrypoints if entry.surface_id == "hallucinate_app"
    )

    terminal_route = build_meta_glasses_remote_terminal_route(
        payload=dispatch_plan.payload,
        render_targets=("audio", "display"),
        session_contract=build_meta_glasses_terminal_session_contract(
            session_id="vai-010-mobile-session",
            phone_host_id="phone-vai-010",
            pairing_state="unpaired",
            display_state="display_unavailable",
            audio_command_state="listening",
            desktop_offload_state="available",
        ),
    )

    assert route.runtime_surface == CapabilityRuntimeSurface.SWISSKNIFE_ORB
    assert swissknife_entrypoint.metadata["orb_plane"] == "swissknife.orb"
    assert hallucinate_entrypoint.metadata["virtual_ui_plane"] == (
        "hallucinate_app.operator_console"
    )
    assert entrypoint_ids == [
        "swissknife_orb",
        "hallucinate_app",
        "mobile_glasses",
        "meta_glasses_audio",
        "meta_glasses_display",
    ]
    assert terminal_route["contract_id"] == REMOTE_TERMINAL_CONTRACT_ID
    assert terminal_route["session_contract"]["terminal_constraints"]["hardware_required"] is False
    assert terminal_route["session_contract"]["desktop_offload"]["state"] == "available"

    runtime_calls: list[dict[str, Any]] = []

    def fake_runtime_binding(*, binding, request):
        runtime_calls.append(
            {
                "operation": request.operation,
                "tool_name": binding["runtime_binding"]["tool_name"],
                "arguments": dict(request.arguments),
            }
        )
        if request.operation == "run_desktop_command":
            output = desktop_peer.run(dict(request.arguments))
            return {
                "binding_type": "handsfree.mcp-server",
                "transport": "mcp-server",
                "status": "completed",
                "server_family": binding["runtime_binding"]["server_family"],
                "tool_name": binding["runtime_binding"]["tool_name"],
                "output": output,
                "content": [
                    {"type": "text", "text": event["text"]}
                    for event in output["stream_events"]
                ],
            }

        status = desktop_peer.status_or_recover()
        return {
            "binding_type": "handsfree.mcp-server",
            "transport": "mcp-server",
            "status": status["status"],
            "server_family": binding["runtime_binding"]["server_family"],
            "tool_name": binding["runtime_binding"]["tool_name"],
            "output": status,
            "error": status.get("reason"),
        }

    monkeypatch.setattr(api_module, "invoke_mobile_orb_runtime_binding", fake_runtime_binding)

    registered = client.post(
        "/v1/mobile/orb/register_edge_capabilities",
        json={
            "edge_id": "vai-010-phone-edge",
            "platform": "simulator",
            "device_id": "phone-vai-010",
            "device_model": "Hardware-free phone simulator",
            "dat_capabilities": {
                "session": True,
                "audio": False,
                "display": False,
                "displayVideo": False,
                "webAppDisplay": True,
            },
            "local_interface_cids": [
                "sha256:vai010-mobile-edge",
                "sha256:vai010-display-widget",
            ],
            "transport_preferences": ["local", "mcp-server"],
            "interaction_envelope": {
                "source": "meta_glasses_terminal",
                "audio_command": command,
            },
        },
    )
    assert registered.status_code == 200
    edge = registered.json()
    assert edge["policy_decision"]["outcome"] == "allow"

    event = client.post(
        "/v1/mobile/orb/publish_glasses_event",
        json={
            "edge_session_id": edge["edge_session_id"],
            "event_type": "audio_state",
            "payload": {
                "transcript": command,
                "terminal_route": terminal_route,
                "source_endpoint_id": "meta_glasses_audio_input",
            },
            "correlation_id": "corr-vai-010",
        },
    )
    assert event.status_code == 200
    event_payload = event.json()
    assert event_payload["accepted"] is True

    binding = client.post(
        "/v1/mobile/orb/bind_service",
        json={
            "edge_session_id": edge["edge_session_id"],
            "service_interface_cid": "sha256:vai010-swissknife-orb",
            "service_descriptor": {
                "name": "virtual_ai_os_end_to_end_harness",
                "namespace": "swissknife.orb.virtual_ai_os",
                "methods": [
                    {"name": "run_desktop_command"},
                    {"name": "check_desktop_peer"},
                ],
                "requires": [
                    "hallucinate_app.command_plane",
                    "swissknife.virtual_desktop",
                    "desktop_peer.compute",
                ],
                "metadata": {
                    "server_family": route.server_family,
                    "tool_name": "tools_dispatch",
                    "provider_name": route.provider_name,
                },
            },
            "operation": "run_desktop_command",
            "transport_preference": "mcp-server",
            "user_intent": command,
            "policy_context": {
                "runtime_surface": route.runtime_surface.value,
                "source_surface": "hallucinate_app",
                "terminal_contract_id": terminal_route["contract_id"],
            },
        },
    )
    assert binding.status_code == 200
    binding_payload = binding.json()
    orb_binding = binding_payload["orb_binding"]
    assert binding_payload["policy_decision"]["outcome"] == "allow"
    assert orb_binding["transport_binding"]["metadata"]["interface_descriptor"]["namespace"] == (
        "swissknife.orb.virtual_ai_os"
    )

    invoked = client.post(
        "/v1/mobile/orb/invoke_service",
        json={
            "binding_handle": binding_payload["binding_handle"],
            "operation": "run_desktop_command",
            "arguments": {
                "task_id": task_id,
                "command": command,
                "operator_plane": "hallucinate_app",
                "ui_plane": "swissknife.virtual_desktop",
                "capability_dispatch": {
                    "route": {
                        "capability_id": route.capability_id,
                        "runtime_surface": route.runtime_surface.value,
                        "handler_ref": route.handler_ref,
                    },
                    "entrypoints": entrypoint_ids,
                },
                "artifact_refs": artifact_refs,
                "terminal_route": terminal_route,
            },
            "glasses_context": {
                "terminal_kind": "meta_glasses_remote_terminal",
                "source_endpoint_id": "meta_glasses_audio_input",
            },
            "correlation_id": "corr-vai-010",
            "parent_receipt_cids": [event_payload["receipt_cid"]],
        },
    )
    assert invoked.status_code == 200
    invoked_payload = invoked.json()
    transport_result = invoked_payload["service_result"]["transport_result"]
    stream_events = transport_result["output"]["stream_events"]
    spoken_text = transport_result["output"]["response_text"]

    assert invoked_payload["ok"] is True
    assert runtime_calls[0]["operation"] == "run_desktop_command"
    assert runtime_calls[0]["arguments"]["operator_plane"] == "hallucinate_app"
    assert desktop_peer.offloaded_commands == [
        {
            "command": command,
            "task_id": task_id,
            "placement": "desktop_peer",
        }
    ]
    assert transport_result["output"]["compute_placement"] == "desktop_peer"
    assert [event["phase"] for event in stream_events] == [
        "dispatch",
        "offload",
        "response",
    ]

    render_action = _display_widget_action(
        descriptor_cid=orb_binding["descriptor_cid"],
        interface_cid=orb_binding["interface_cid"],
        receipt_cid=invoked_payload["receipt_cid"],
        task_id=task_id,
        title="Virtual AI OS E2E harness",
        summary=spoken_text,
        stream_events=stream_events,
    )
    dispatched = client.post(
        "/v1/mobile/orb/dispatch_glasses_response",
        json={
            "edge_session_id": edge["edge_session_id"],
            "result": {
                **invoked_payload,
                "display_widget_action": render_action,
                "spoken_text": spoken_text,
            },
            "render_targets": ["display_widget", "display_webapp", "audio", "mobile_card"],
            "fallback": render_action["fallback"],
            "correlation_id": "corr-vai-010",
            "parent_receipt_cids": [
                event_payload["receipt_cid"],
                invoked_payload["receipt_cid"],
            ],
        },
    )
    assert dispatched.status_code == 200
    dispatched_payload = dispatched.json()
    assert dispatched_payload["display_widget_action"]["state"]["stream_events"] == stream_events
    assert dispatched_payload["spoken_text"] == spoken_text
    assert "mobile_render_display_widget" in [
        action["id"] for action in dispatched_payload["dispatched_actions"]
    ]

    desktop_peer.fail_next_status = True
    recovery_invoked = client.post(
        "/v1/mobile/orb/invoke_service",
        json={
            "binding_handle": binding_payload["binding_handle"],
            "operation": "check_desktop_peer",
            "arguments": {
                "task_id": task_id,
                "command": "check desktop peer",
                "artifact_refs": artifact_refs,
            },
            "correlation_id": "corr-vai-010-recovery",
            "parent_receipt_cids": [dispatched_payload["receipt_cid"]],
        },
    )
    assert recovery_invoked.status_code == 200
    recovery_payload = recovery_invoked.json()
    recovery_result = recovery_payload["service_result"]["transport_result"]
    recovery = recovery_result["output"]["recovery"]

    assert recovery_payload["ok"] is False
    assert recovery_result["status"] == "error"
    assert recovery_result["error"] == "desktop_peer_disconnected"
    assert recovery == {
        "action": "fallback_to_phone",
        "compute_placement": "phone_local",
        "render_path": "mobile-card",
    }

    recovery_action = _display_widget_action(
        descriptor_cid=orb_binding["descriptor_cid"],
        interface_cid=orb_binding["interface_cid"],
        receipt_cid=recovery_payload["receipt_cid"],
        task_id=task_id,
        title="Virtual AI OS E2E harness",
        summary="Desktop peer disconnected. Continuing on the phone preview.",
        stream_events=[
            {
                "sequence": 4,
                "stream": "task-progress",
                "phase": "recovery",
                "text": "Desktop peer disconnected; phone fallback is active.",
            }
        ],
        recovery=recovery,
    )
    recovery_dispatched = client.post(
        "/v1/mobile/orb/dispatch_glasses_response",
        json={
            "edge_session_id": edge["edge_session_id"],
            "result": {
                **recovery_payload,
                "display_widget_action": recovery_action,
                "spoken_text": recovery_action["state"]["summary"],
            },
            "render_targets": ["display_widget", "display_webapp", "audio", "mobile_card"],
            "fallback": recovery_action["fallback"],
            "correlation_id": "corr-vai-010-recovery",
            "parent_receipt_cids": [
                dispatched_payload["receipt_cid"],
                recovery_payload["receipt_cid"],
            ],
        },
    )
    assert recovery_dispatched.status_code == 200
    recovery_dispatch_payload = recovery_dispatched.json()
    assert recovery_dispatch_payload["display_widget_action"]["state"]["status"] == "recovered"
    assert recovery_dispatch_payload["display_widget_action"]["fallback"]["recovery"] == recovery
    assert recovery_dispatch_payload["spoken_text"] == (
        "Desktop peer disconnected. Continuing on the phone preview."
    )

    diagnostics = client.get(
        "/v1/mobile/orb/diagnostics",
        params={"edge_session_id": edge["edge_session_id"]},
    )
    assert diagnostics.status_code == 200
    diagnostics_payload = diagnostics.json()
    assert diagnostics_payload["backend_counts"] == {
        "edge_sessions": 1,
        "events": 1,
        "bindings": 1,
        "subscriptions": 0,
        "invocations": 2,
        "dispatches": 2,
        "revocations": 0,
    }
    assert diagnostics_payload["binding_state"]["status"] == "bound"
    assert "dat_native_display_unavailable" in diagnostics_payload["fallback_reasons"]
    assert invoked_payload["receipt_cid"] in diagnostics_payload["receipt_cids"]
    assert recovery_payload["receipt_cid"] in diagnostics_payload["receipt_cids"]


def test_desktop_operator_harness_presents_routes_and_places_local_or_peer_work():
    kernel = CapabilityRoutingKernel()
    operator_session = SimulatedDesktopOperatorSession()
    desktop_peer = SimulatedDesktopPeer(peer_id="desktop-peer-vai-024")
    task_id = "VAI-024"
    artifact_refs = {
        "result_cid": "sha256:vai024-result",
        "receipt_ref": "sha256:vai024-receipt",
        "event_dag_ref": "sha256:vai024-events",
        "delegation_ref": "sha256:vai024-delegation",
    }

    session_plan = kernel.dispatch_task(
        CapabilityDispatchRequest(
            capability_id="ui_render_session",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            source_surface="hallucinate_app",
            payload={
                "task_id": task_id,
                "operator_plane": "hallucinate_app",
                "desktop_surface": "swissknife.virtual_desktop",
                "artifact_refs": artifact_refs,
            },
        )
    )
    session = operator_session.present_swissknife_session(session_plan)

    local_plan = kernel.dispatch_task(
        CapabilityDispatchRequest(
            capability_id="ipfs_pin",
            requested_mode=CapabilityExecutionMode.DIRECT_IMPORT,
            source_surface="hallucinate_app",
            payload={
                "task_id": task_id,
                "artifact_refs": artifact_refs,
                "cid": "bafy-vai024-local-session-snapshot",
            },
        )
    )
    local_control = operator_session.route_hallucinate_control(
        session=session,
        dispatch_plan=local_plan,
        modality="voice",
        control="pin the session snapshot locally",
        placement_preference="local",
    )
    local_receipt = operator_session.execute_locally(
        dispatch_plan=local_plan,
        envelope=local_control,
    )

    peer_plan = kernel.dispatch_task(
        CapabilityDispatchRequest(
            capability_id="dataset_discovery",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            source_surface="hallucinate_app",
            payload={
                "task_id": task_id,
                "artifact_refs": artifact_refs,
                "query": "multimodal desktop operator evidence",
            },
        )
    )
    peer_control = operator_session.route_hallucinate_control(
        session=session,
        dispatch_plan=peer_plan,
        modality="image",
        control="inspect the screenshot and hand dataset search to the peer",
        placement_preference="desktop_peer",
    )
    peer_receipt = operator_session.handoff_to_peer(
        dispatch_plan=peer_plan,
        envelope=peer_control,
        desktop_peer=desktop_peer,
    )

    assert session == {
        "session_id": "vai-024-desktop-operator-session",
        "task_id": task_id,
        "presented_by": "swissknife_orb",
        "operator_console": "hallucinate_app",
        "hosted_surface": "swissknife.virtual_desktop",
        "virtual_ui_plane": "swissknife.virtual_desktop",
        "orb_plane": "swissknife.orb",
        "controls": ("voice", "pointer", "image", "keyboard"),
        "descriptor_ref": "sha256:vai024-swissknife-session-descriptor",
    }
    assert session_plan.route.runtime_surface == CapabilityRuntimeSurface.SWISSKNIFE_ORB
    assert session_plan.route.handler_ref == "swissknife.orb::ui_render_session"
    assert session_plan.entrypoints[0].metadata["virtual_ui_app_id"] == "mcp-control"

    routed_modalities = [
        control["interaction_envelope"]["source_modality"]
        for control in operator_session.mediated_controls
    ]
    assert routed_modalities == [
        "voice",
        "image",
    ]
    assert all(
        control["policy_decision"]["outcome"] == "allow"
        and control["virtual_desktop_command_intent"]["operator_console"] == "hallucinate_app"
        for control in operator_session.mediated_controls
    )

    assert local_receipt == {
        "receipt_cid": "sha256:vai024-local-placement-receipt",
        "session_id": session["session_id"],
        "capability_id": "ipfs_pin",
        "command": "pin the session snapshot locally",
        "compute_placement": "local",
        "runtime_surface": "direct_adapter",
        "placement_layer": "content_provenance",
        "placement_target": "endomorphosis/ipfs_kit_py",
        "status": "completed",
    }
    assert peer_receipt["compute_placement"] == "desktop_peer"
    assert peer_receipt["runtime_surface"] == "swissknife_orb"
    assert peer_receipt["placement_layer"] == "swissknife_orb"
    assert peer_receipt["placement_target"] == "endomorphosis/swissknife"
    assert peer_receipt["peer_id"] == "desktop-peer-vai-024"
    assert [event["phase"] for event in peer_receipt["stream_events"]] == [
        "dispatch",
        "offload",
        "response",
    ]
    assert desktop_peer.offloaded_commands == [
        {
            "command": "inspect the screenshot and hand dataset search to the peer",
            "task_id": task_id,
            "placement": "desktop_peer",
        }
    ]
