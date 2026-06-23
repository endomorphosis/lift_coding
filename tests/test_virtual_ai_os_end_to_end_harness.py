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
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from handsfree.ai import (
    CapabilityExecutionMode,
    CapabilityRuntimeSurface,
    list_virtual_ai_os_capabilities,
)
from handsfree.capability_registry import CapabilityDispatchRequest, CapabilityRoutingKernel
from handsfree.meta_glasses_remote_terminal import (
    REMOTE_TERMINAL_CONTRACT_ID,
    build_meta_glasses_remote_terminal_route,
    build_meta_glasses_terminal_session_contract,
)
from handsfree.virtual_ai_os_observability import (
    build_virtual_ai_os_observability_bundle,
    build_virtual_ai_os_placement_change_artifact,
    build_virtual_ai_os_remote_execution_receipt_artifact,
    build_virtual_ai_os_rollback_event_artifact,
)
from handsfree.virtual_ai_os_components import get_virtual_ai_os_component_repo_contracts


REPO_ROOT = Path(__file__).resolve().parents[1]
VAI_339_DISCOVERY_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-23-vai-339-launch-replay-gate.md"
)
VAI_019_DISCOVERY_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-23-vai-019-cross-submodule-integration-tests.md"
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
    for state_name in (
        "mobile_orb_edge_sessions",
        "mobile_orb_service_bindings",
        "mobile_orb_service_subscriptions",
        "mobile_orb_events",
        "mobile_orb_receipts",
        "mobile_orb_invocations",
        "mobile_orb_dispatches",
        "mobile_orb_revocations",
    ):
        state = getattr(api_module, state_name, None)
        if state is not None:
            state.clear()


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


def _json_block_after(source: str, marker: str) -> dict[str, Any]:
    import json

    start = source.index(marker)
    fence_start = source.index("```json", start)
    payload_start = source.index("\n", fence_start) + 1
    payload_end = source.index("\n```", payload_start)
    return json.loads(source[payload_start:payload_end])


def _component_contracts_by_id() -> dict[str, dict[str, Any]]:
    return {
        str(contract["component_id"]): contract
        for contract in get_virtual_ai_os_component_repo_contracts({}, repo_root=REPO_ROOT)
    }


def _component_validation_artifacts(
    component_ids: tuple[str, ...],
    contracts: dict[str, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    artifacts: dict[str, dict[str, str]] = {}
    for component_id in component_ids:
        contract = contracts[component_id]
        root = Path(str(contract["resolved_root"]))
        candidate_files = (
            root / "package.json",
            root / "pyproject.toml",
            root / "README.md",
        )
        evidence_file = next(path for path in candidate_files if path.exists())
        assert root.exists(), f"{component_id} root is not checked out: {root}"
        assert (root / ".git").exists(), f"{component_id} is missing a submodule git marker"
        artifacts[component_id] = {
            "root": str(root.relative_to(REPO_ROOT)),
            "git_marker": str((root / ".git").relative_to(REPO_ROOT)),
            "evidence_file": str(evidence_file.relative_to(REPO_ROOT)),
            "role": str(contract["role"]),
        }
    return artifacts


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
    assert diagnostics_payload["source"] == "backend"
    assert diagnostics_payload["edge_sessions_count"] == 1
    assert diagnostics_payload["events_count"] == 1
    assert diagnostics_payload["bindings_count"] == 1
    assert diagnostics_payload["subscriptions_count"] == 0
    assert diagnostics_payload["receipts_count"] == 7
    assert diagnostics_payload["binding_state"]["active_count"] == 1
    assert diagnostics_payload["binding_state"]["revoked_count"] == 0
    assert diagnostics_payload["binding_state"]["bindings"][0]["operation"] == (
        "run_desktop_command"
    )
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


def test_vai_019_cross_submodule_routes_select_placement_and_collect_artifacts():
    contracts = _component_contracts_by_id()
    kernel = CapabilityRoutingKernel()
    operator_session = SimulatedDesktopOperatorSession(session_id="vai-019-cross-submodule-session")
    desktop_peer = SimulatedDesktopPeer(peer_id="desktop-peer-vai-019")
    task_id = "VAI-019"
    artifact_refs = {
        "result_cid": "sha256:vai019-result",
        "receipt_ref": "sha256:vai019-receipt",
        "event_dag_ref": "sha256:vai019-events",
        "delegation_ref": "sha256:vai019-delegation",
    }

    session_plan = kernel.dispatch_task(
        CapabilityDispatchRequest(
            capability_id="ui_render_session",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            source_surface="hallucinate_app",
            payload={
                "task_id": task_id,
                "artifact_refs": artifact_refs,
                "desktop_surface": "swissknife.virtual_desktop",
            },
        )
    )
    session = operator_session.present_swissknife_session(session_plan)

    scenarios = [
        {
            "scenario_id": "desktop-dataset-discovery",
            "component_ids": ("swissknife", "hallucinate_app", "ipfs_datasets_py"),
            "capability_id": "dataset_discovery",
            "requested_mode": None,
            "preferred_surface": CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            "command": "route dataset discovery through the virtual desktop peer",
            "modality": "voice",
            "placement_preference": "desktop_peer",
            "expected_runtime_surface": "swissknife_orb",
            "expected_placement_target": "endomorphosis/swissknife",
        },
        {
            "scenario_id": "local-ipfs-pin-receipt",
            "component_ids": ("hallucinate_app", "ipfs_kit_py"),
            "capability_id": "ipfs_pin",
            "requested_mode": CapabilityExecutionMode.DIRECT_IMPORT,
            "preferred_surface": None,
            "command": "pin the cross-submodule validation manifest locally",
            "modality": "keyboard",
            "placement_preference": "local",
            "expected_runtime_surface": "direct_adapter",
            "expected_placement_target": "endomorphosis/ipfs_kit_py",
        },
    ]
    evidence_packet: dict[str, Any] = {
        "task_id": task_id,
        "evidence_id": "vai-019-cross-submodule-integration",
        "requires_physical_devices": False,
        "scenarios": [],
    }

    for scenario in scenarios:
        component_ids = scenario["component_ids"]
        validation_artifacts = _component_validation_artifacts(component_ids, contracts)
        assert len(validation_artifacts) >= 2

        dispatch_plan = kernel.dispatch_task(
            CapabilityDispatchRequest(
                capability_id=scenario["capability_id"],
                requested_mode=scenario["requested_mode"],
                preferred_surface=scenario["preferred_surface"],
                source_surface="hallucinate_app",
                payload={
                    "task_id": task_id,
                    "scenario_id": scenario["scenario_id"],
                    "artifact_refs": artifact_refs,
                    "command": scenario["command"],
                },
            )
        )
        control = operator_session.route_hallucinate_control(
            session=session,
            dispatch_plan=dispatch_plan,
            modality=scenario["modality"],
            control=scenario["command"],
            placement_preference=scenario["placement_preference"],
        )

        if scenario["placement_preference"] == "desktop_peer":
            receipt = operator_session.handoff_to_peer(
                dispatch_plan=dispatch_plan,
                envelope=control,
                desktop_peer=desktop_peer,
            )
        else:
            receipt = operator_session.execute_locally(
                dispatch_plan=dispatch_plan,
                envelope=control,
            )

        scenario_evidence = {
            "scenario_id": scenario["scenario_id"],
            "component_ids": list(component_ids),
            "command": scenario["command"],
            "capability_id": dispatch_plan.capability_id,
            "routed_from": control["virtual_desktop_command_intent"]["operator_console"],
            "presented_by": session["presented_by"],
            "runtime_surface": dispatch_plan.route.runtime_surface.value,
            "placement_target": dispatch_plan.route.placement_target,
            "compute_placement": receipt["compute_placement"],
            "receipt_cid": receipt["receipt_cid"],
            "validation_artifacts": validation_artifacts,
        }
        evidence_packet["scenarios"].append(scenario_evidence)

        assert control["policy_decision"]["outcome"] == "allow"
        assert control["virtual_desktop_command_intent"]["target_surface"] == (
            "swissknife.virtual_desktop"
        )
        assert dispatch_plan.route.runtime_surface.value == scenario["expected_runtime_surface"]
        assert dispatch_plan.route.placement_target == scenario["expected_placement_target"]
        assert receipt["status"] == "completed"
        assert receipt["capability_id"] == scenario["capability_id"]
        assert receipt["command"] == scenario["command"]

    assert [scenario["compute_placement"] for scenario in evidence_packet["scenarios"]] == [
        "desktop_peer",
        "local",
    ]
    assert desktop_peer.offloaded_commands == [
        {
            "command": "route dataset discovery through the virtual desktop peer",
            "task_id": task_id,
            "placement": "desktop_peer",
        }
    ]

    documented_packet = _json_block_after(
        VAI_019_DISCOVERY_PATH.read_text(encoding="utf-8"),
        "## Cross-Submodule Harness Evidence",
    )
    assert documented_packet["task_id"] == evidence_packet["task_id"]
    assert documented_packet["evidence_id"] == evidence_packet["evidence_id"]
    assert documented_packet["scenarios"] == [
        {
            "scenario_id": scenario["scenario_id"],
            "component_ids": list(scenario["component_ids"]),
            "capability_id": scenario["capability_id"],
            "runtime_surface": scenario["runtime_surface"],
            "placement_target": scenario["placement_target"],
            "compute_placement": scenario["compute_placement"],
        }
        for scenario in evidence_packet["scenarios"]
    ]


def test_vai_339_launch_replay_gate_builds_one_shared_evidence_packet():
    kernel = CapabilityRoutingKernel()
    task_id = "VAI-339"
    session_id = "vdsk-vai339-launch-session"
    command_id = "cmd-vai339-open-monitor"
    correlation_id = "corr-vai339-launch-replay"
    request_id = "req-vai339-phone-origin"
    command = "open the launch monitor on the virtual desktop"
    phone_host_id = "phone-vai339"
    desktop_id = "desktop-vai339"
    widget_id = "virtual-ai-os-launch-replay"
    widget_cid = "sha256:vai339-widget"
    descriptor_cid = "sha256:vai339-descriptor"
    manifest_cid = "sha256:vai339-manifest"
    policy_cid = "sha256:vai339-policy"
    policy_receipt_cid = "sha256:vai339-policy-receipt"
    placement_receipt_cid = "sha256:vai339-placement-peer"
    capability_receipt_cid = "sha256:vai339-capability-receipt"
    recovery_receipt_cid = "sha256:vai339-recovery-phone-local"
    artifact_refs = {
        "result_cid": "sha256:vai339-result",
        "receipt_ref": capability_receipt_cid,
        "event_dag_ref": "sha256:vai339-events",
        "delegation_ref": "sha256:vai339-delegation",
    }

    terminal_route = build_meta_glasses_remote_terminal_route(
        payload={"task_id": task_id, "command_id": command_id, "correlation_id": correlation_id},
        session_contract=build_meta_glasses_terminal_session_contract(
            session_id=session_id,
            phone_host_id=phone_host_id,
            pairing_state="unpaired",
            display_state="display_unavailable",
            audio_command_state="listening",
            desktop_offload_state="available",
        ),
    )
    session_plan = kernel.dispatch_task(
        CapabilityDispatchRequest(
            capability_id="ui_render_session",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            source_surface="hallucinate_app",
            payload={
                "task_id": task_id,
                "session_id": session_id,
                "command_id": command_id,
                "correlation_id": correlation_id,
                "artifact_refs": artifact_refs,
            },
        )
    )
    peer_plan = kernel.dispatch_task(
        CapabilityDispatchRequest(
            capability_id="dataset_discovery",
            preferred_surface=CapabilityRuntimeSurface.SWISSKNIFE_ORB,
            source_surface="hallucinate_app",
            payload={
                "task_id": task_id,
                "session_id": session_id,
                "command_id": command_id,
                "correlation_id": correlation_id,
                "artifact_refs": artifact_refs,
            },
        )
    )

    operator_session = SimulatedDesktopOperatorSession(session_id=session_id)
    desktop_peer = SimulatedDesktopPeer(peer_id="desktop-peer-vai-339")
    swissknife_session = operator_session.present_swissknife_session(session_plan)
    mediation = operator_session.route_hallucinate_control(
        session=swissknife_session,
        dispatch_plan=peer_plan,
        modality="phone_audio",
        control=command,
        placement_preference="desktop_peer",
    )
    peer_receipt = operator_session.handoff_to_peer(
        dispatch_plan=peer_plan,
        envelope=mediation,
        desktop_peer=desktop_peer,
    )

    capability_actions = [
        "vai.glasses_widget.render",
        "vai.glasses_widget.update",
        "vai.glasses_widget.confirm",
        "vai.glasses_widget.cancel",
    ]
    capabilities = {entry.capability_id: entry for entry in list_virtual_ai_os_capabilities()}
    widget_capability_receipts = {
        capability_id: {
            "capability_id": capability_id,
            "capability_receipt_cid": f"{capability_receipt_cid}-{capability_id.rsplit('.', 1)[1]}",
            "manifest_cid": manifest_cid,
            "descriptor_cid": descriptor_cid,
            "policy_receipt_cid": policy_receipt_cid,
            "placement_receipt_cid": placement_receipt_cid,
            "recovery_receipt_cid": recovery_receipt_cid,
        }
        for capability_id in capability_actions
    }

    placement_change = build_virtual_ai_os_placement_change_artifact(
        task_id=task_id,
        correlation_id=correlation_id,
        from_placement="phone_local",
        to_placement="desktop_peer",
        reason="policy_allowed_desktop_peer",
        placement_ref=placement_receipt_cid,
    )
    remote_execution = build_virtual_ai_os_remote_execution_receipt_artifact(
        task_id=task_id,
        correlation_id=correlation_id,
        remote_surface="desktop-peer-vai-339",
        operation="run_desktop_command",
        status="completed",
        receipt_ref=peer_receipt["receipt_cid"],
        parent_artifact_ids=(placement_change["artifact_id"],),
    )
    rollback = build_virtual_ai_os_rollback_event_artifact(
        task_id=task_id,
        correlation_id=correlation_id,
        rollback_action="fallback_to_phone",
        reason="desktop_peer_disconnected_after_render",
        restored_placement="phone_local",
        restored_ref=recovery_receipt_cid,
        parent_artifact_ids=(remote_execution["artifact_id"],),
    )
    observability_bundle = build_virtual_ai_os_observability_bundle(
        task_id=task_id,
        correlation_id=correlation_id,
        artifacts=(placement_change, remote_execution, rollback),
    )

    evidence_packet = {
        "task_id": task_id,
        "replay_id": "vai-339-launch-replay-gate",
        "requires_physical_devices": False,
        "command_contract": "vai.shared_capability_envelope@0.1.0",
        "single_evidence_packet": True,
        "join_keys": {
            "task_id": task_id,
            "command_id": command_id,
            "session_id": session_id,
            "desktop_id": desktop_id,
            "correlation_id": correlation_id,
            "request_id": request_id,
            "widget_id": widget_id,
            "widget_cid": widget_cid,
            "descriptor_cid": descriptor_cid,
            "manifest_cid": manifest_cid,
            "policy_cid": policy_cid,
            "capability_receipt_cid": capability_receipt_cid,
        },
        "phone_originated_command": {
            "participant_id": "phone:operator",
            "phone_host_id": phone_host_id,
            "command": command,
            "terminal_contract_id": terminal_route["contract_id"],
        },
        "hallucinate_app_mediation": {
            "participant_id": "hallucinate_app:operator_console",
            "interaction_envelope": mediation["interaction_envelope"],
            "normalized_intent": mediation["normalized_intent"],
            "policy_decision": mediation["policy_decision"],
            "mediation_receipt": mediation["mediation_receipt"],
            "virtual_desktop_command_intent": mediation["virtual_desktop_command_intent"],
            "policy_cid": policy_cid,
            "policy_receipt_cid": policy_receipt_cid,
        },
        "swissknife_presentation": {
            "participant_id": "swissknife:ui",
            "presented_by": swissknife_session["presented_by"],
            "orb_plane": swissknife_session["orb_plane"],
            "descriptor_cid": descriptor_cid,
            "manifest_cid": manifest_cid,
            "visible_session_id": swissknife_session["session_id"],
        },
        "placement": {
            "selected_runtime": "desktop_peer",
            "placement_receipt_cid": placement_receipt_cid,
            "peer_receipt": peer_receipt,
            "recovery": {
                "recovery_receipt_cid": recovery_receipt_cid,
                "action": "fallback_to_phone",
                "compute_placement": "phone_local",
                "render_path": "mobile-card",
            },
        },
        "meta_glasses_terminal": {
            "participant_id": "meta_glasses:terminal",
            "terminal_contract_id": terminal_route["contract_id"],
            "endpoint_ids": [endpoint["endpoint_id"] for endpoint in terminal_route["endpoints"]],
            "fallback_render_path": terminal_route["session_contract"]["visual_status_output"][
                "fallback_render_path"
            ],
            "widget_capability_receipts": widget_capability_receipts,
        },
        "observability_bundle": observability_bundle,
        "assertions": [
            "phone command enters Hallucinate App mediation before desktop peer dispatch",
            "Swissknife and Meta glasses share descriptor and manifest CIDs",
            "desktop-peer placement and phone-local recovery share one receipt lineage",
            "render/update/confirm/cancel actions use the VAI shared capability envelope",
        ],
    }

    assert evidence_packet["phone_originated_command"]["participant_id"] == "phone:operator"
    assert evidence_packet["hallucinate_app_mediation"]["policy_decision"]["outcome"] == "allow"
    assert evidence_packet["swissknife_presentation"]["orb_plane"] == "swissknife.orb"
    assert evidence_packet["placement"]["peer_receipt"]["compute_placement"] == "desktop_peer"
    assert evidence_packet["placement"]["recovery"]["compute_placement"] == "phone_local"
    assert evidence_packet["meta_glasses_terminal"]["terminal_contract_id"] == (
        REMOTE_TERMINAL_CONTRACT_ID
    )
    assert set(evidence_packet["meta_glasses_terminal"]["endpoint_ids"]) == {
        "meta_glasses_audio_input",
        "meta_glasses_audio_output",
        "meta_glasses_display_widget",
    }
    assert set(widget_capability_receipts) == set(capability_actions)
    assert all(
        capabilities[capability_id].command_envelope_fields
        and "capability_receipt_cid" in capabilities[capability_id].receipt_fields
        for capability_id in capability_actions
    )
    assert all(
        receipt["descriptor_cid"] == descriptor_cid
        and receipt["manifest_cid"] == manifest_cid
        and receipt["policy_receipt_cid"] == policy_receipt_cid
        and receipt["placement_receipt_cid"] == placement_receipt_cid
        and receipt["recovery_receipt_cid"] == recovery_receipt_cid
        for receipt in widget_capability_receipts.values()
    )
    assert evidence_packet["observability_bundle"]["artifact_ids"] == [
        placement_change["artifact_id"],
        remote_execution["artifact_id"],
        rollback["artifact_id"],
    ]

    documented_packet = _json_block_after(
        VAI_339_DISCOVERY_PATH.read_text(encoding="utf-8"),
        "## Deterministic Launch Replay Gate",
    )
    assert documented_packet["task_id"] == evidence_packet["task_id"]
    assert documented_packet["replay_id"] == evidence_packet["replay_id"]
    assert documented_packet["join_keys"] == evidence_packet["join_keys"]
    assert documented_packet["covers"] == [
        "phone_originated_command",
        "hallucinate_app_mediation",
        "swissknife_presentation",
        "desktop_peer_or_phone_local_placement",
        "meta_glasses_terminal_contract",
        "shared_policy_placement_recovery_capability_receipts",
    ]
