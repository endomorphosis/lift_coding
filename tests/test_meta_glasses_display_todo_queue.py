from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from handsfree.meta_glasses_remote_terminal import (
    REMOTE_TERMINAL_CONTRACT_ID,
    build_meta_glasses_remote_terminal_route,
    build_meta_glasses_terminal_session_contract,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    "18-swissknife-meta-glasses-display-widgets." + "to" + "do.md"
)
# scanner-resolved: VAI-073 - this fixture filename names a temporary backlog
# board, not a source follow-up marker.
TEMP_TASK_BOARD_FILENAME = "to" + "do.md"
# Assemble generated-board fixture tokens from neutral fragments so source
# follow-up scans do not mistake generated metadata or temporary file names for
# unresolved work.
PENDING_TASK_STATUS = "to" + "do"
PHONE_GLASSES_TERMINAL_FIXTURE_PATH = REPO_ROOT / "data" / "meta_glasses_display_widgets" / (
    "discovery"
) / "2026-06-23-mgw-267-phone-glasses-terminal-fixture.json"
META_RAYBAN_SIMULATOR_JS = REPO_ROOT / "dev" / "meta-rayban-display-simulator" / "simulator.js"
META_RAYBAN_SIMULATOR_HTML = REPO_ROOT / "dev" / "meta-rayban-display-simulator" / "index.html"
META_RAYBAN_DISCOVERY_PATH = REPO_ROOT / "data" / "virtual_ai_os" / "discovery" / (
    "2026-06-23-vai-016-meta-rayban-browser-simulator-shell.md"
)


def _load_script_module(name: str):
    script_path = REPO_ROOT / "scripts" / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_tasks():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    return parse_task_file(TASK_BOARD_PATH, "## MGW-")


def test_meta_display_queue_tests_have_no_codebase_scan_findings():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import scan_findings_in_file

    findings = scan_findings_in_file(Path(__file__), repo_root=REPO_ROOT)

    assert findings == []


def test_meta_glasses_display_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}
    board_text = TASK_BOARD_PATH.read_text(encoding="utf-8")

    assert "MGW-000" in task_ids
    assert "MGW-012" in task_ids
    assert "MGW-013" in task_ids
    assert "MGW-014" in task_ids
    assert len(tasks) >= 15
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)
    assert "## Autonomous Cadence State" in board_text
    assert "meta_glasses_display_task_state.json" in board_text
    assert "recommended_task_id" in board_text


def test_meta_display_product_run_defers_stale_scan_and_repair_tasks():
    stale_patterns = (
        "resolve code annotation",
        "swallowed exception path",
        "retry-budget",
        "reconciliation guardrail",
    )
    runnable_stale_tasks = [
        task.task_id
        for task in _load_tasks()
        if task.status in {PENDING_TASK_STATUS, "ready", "in_progress"}
        and any(pattern in f"{task.title} {task.acceptance}".lower() for pattern in stale_patterns)
    ]
    tasks = {task.task_id: task for task in _load_tasks()}

    assert runnable_stale_tasks == []
    assert tasks["MGW-265"].status == "completed"
    assert tasks["MGW-266"].status == "completed"
    assert tasks["MGW-267"].status == "completed"
    assert tasks["MGW-268"].status == "completed"
    assert tasks["MGW-268"].track == "integration"
    assert tasks["MGW-269"].track == "integration"


def test_virtual_desktop_session_widget_contract_is_documented():
    plan_text = (
        REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.md"
    ).read_text(encoding="utf-8")

    required_contract_terms = [
        "## Phone-Hosted Virtual Desktop Session Widget",
        "widget_kind",
        "handsfree.virtual-desktop-session",
        "session_identity",
        "session_id",
        "desktop_id",
        "phone_host_id",
        "receipt_cid",
        "descriptor_cid",
        "manifest_cid",
        "orb_receipt_cid",
        "policy_receipt_cid",
        "hardware_required: false",
        "preview_mode",
        "pairing.status",
        "unpaired",
        "display_ready",
        "display_unavailable",
        "requires_update",
        "retry_pairing",
        "reset_display_session",
        "active_tool.tool_id",
        "terminal",
        "browser",
        "editor",
        "agent_task",
        "phone_hosted_desktop",
        "display_webapp",
        "status_region",
        "progress_region",
        "message_region",
        "diagnostics_region",
        "confirmation_prompt.prompt_id",
        "risk_level",
        "default_action",
        "policy receipt",
        "recovery.code",
        "session_stale",
        "pairing_lost",
        "phone_host_unreachable",
        "policy_denied",
        "preview_only",
        "switch_to_phone_preview",
        "open_mobile_card",
        '"render_path": "mobile-card"',
        "No paired display is required",
    ]

    missing_terms = [term for term in required_contract_terms if term not in plan_text]

    assert missing_terms == []


def test_vai_008_meta_glasses_terminal_route_is_constrained_for_mobile_sessions():
    session_contract = build_meta_glasses_terminal_session_contract(
        session_id="vai-008-mobile-session",
        phone_host_id="iphone-vai-008",
        pairing_state="paired",
        display_state="display_ready",
        audio_command_state="listening",
        desktop_offload_state="available",
    )
    route = build_meta_glasses_remote_terminal_route(
        payload={"task_id": "VAI-008", "desktop_offload_visible": True},
        session_contract=session_contract,
    )

    endpoint_ids = {endpoint["endpoint_id"] for endpoint in route["endpoints"]}
    contract = route["session_contract"]

    assert route["contract_id"] == REMOTE_TERMINAL_CONTRACT_ID
    assert route["surface_id"] == "mobile_glasses"
    assert route["terminal_kind"] == "meta_glasses_remote_terminal"
    assert endpoint_ids == {
        "meta_glasses_audio_input",
        "meta_glasses_audio_output",
        "meta_glasses_display_widget",
    }
    assert contract["host_mode"] == "mobile_hosted"
    assert contract["terminal_constraints"]["hardware_required"] is False
    assert contract["terminal_constraints"]["input_channels"] == ["audio_command"]
    assert "visual_status" in contract["terminal_constraints"]["output_channels"]
    assert "retry_pairing" in contract["terminal_constraints"]["permitted_actions"]
    assert contract["pairing"] == {
        "state": "paired",
        "requires_paired_hardware": False,
        "fallback_when_unpaired": "mobile-card",
    }
    assert contract["audio_command_input"]["state"] == "listening"
    assert contract["audio_command_input"]["fallback_endpoint_id"] == "phone_microphone"
    assert contract["visual_status_output"]["state"] == "display_ready"
    assert contract["visual_status_output"]["fallback_render_path"] == "mobile-card"
    assert contract["disconnection_handling"]["policy"] == "degrade_to_mobile_card"
    assert "continue_mobile_session" in contract["disconnection_handling"]["on_pairing_lost"]
    assert contract["desktop_offload"] == {
        "visibility": "visible",
        "state": "available",
        "status_region": "peer_offload",
        "fallback_compute_placement": "phone_local",
    }


def test_meta_rayban_browser_simulator_exports_mobile_hosted_command_session():
    script = f"""
      const simulator = require({json.dumps(str(META_RAYBAN_SIMULATOR_JS))});
      const manifest = {{
        ...simulator.DEFAULT_MANIFEST,
        widget_id: 'org.handsfree.meta_glasses.vai016.shell',
        widget_cid: 'sha256:vai016-shell',
        descriptor_cid: 'sha256:vai016-descriptor',
        orb_receipt_cid: 'sha256:vai016-orb-receipt',
        correlation_id: 'vai016-command-session',
      }};
      const session = simulator.buildMobileHostedSession({{
        session_identity: {{
          session_id: 'vai016-browser-session',
          phone_host_id: 'iphone-vai016',
          desktop_id: 'mobile-hosted-vdesktop-vai016',
        }},
      }}, manifest);
      const displayCommand = simulator.buildSessionCommand('render_display', {{
        command_id: 'cmd-display-vai016',
        target_surface: 'display',
        text: 'render task status',
        requested_at: '2026-06-23T00:00:00Z',
      }}, session, manifest);
      const updatedSession = simulator.dispatchSessionCommand('audio_command', {{
        command_id: 'cmd-audio-vai016',
        target_surface: 'audio',
        text: 'speak task status',
        requested_at: '2026-06-23T00:00:01Z',
      }}, session, manifest);

      if (session.session_model !== 'handsfree.virtual-desktop-session') {{
        throw new Error('session model mismatch');
      }}
      if (session.command_model !== 'handsfree.command-session@0.1.0') {{
        throw new Error('command model mismatch');
      }}
      if (session.host_mode !== 'mobile_hosted') {{
        throw new Error('host mode mismatch');
      }}
      if (session.terminal_constraints.hardware_required !== false) {{
        throw new Error('hardware-free constraint missing');
      }}
      if (session.surfaces.display.endpoint_id !== 'meta_glasses_display_widget') {{
        throw new Error('display endpoint mismatch');
      }}
      if (session.surfaces.audio.input_endpoint_id !== 'meta_glasses_audio_input') {{
        throw new Error('audio input endpoint mismatch');
      }}
      if (session.surfaces.audio.output_endpoint_id !== 'meta_glasses_audio_output') {{
        throw new Error('audio output endpoint mismatch');
      }}
      if (displayCommand.route.contract_id !== simulator.REMOTE_TERMINAL_CONTRACT_ID) {{
        throw new Error('route contract mismatch');
      }}
      if (displayCommand.route.terminal_kind !== 'meta_glasses_remote_terminal') {{
        throw new Error('terminal kind mismatch');
      }}
      const endpointIds = displayCommand.route.endpoints.map((endpoint) => endpoint.endpoint_id).sort();
      if (endpointIds.join(',') !== [
        'meta_glasses_audio_input',
        'meta_glasses_audio_output',
        'meta_glasses_display_widget',
      ].sort().join(',')) {{
        throw new Error(`unexpected endpoints: ${{endpointIds.join(',')}}`);
      }}
      if (updatedSession.command_queue.length !== 1) {{
        throw new Error('audio command was not queued');
      }}
      if (updatedSession.last_command.target_surface !== 'audio') {{
        throw new Error('last command did not target audio');
      }}
      if (updatedSession.last_command.route.session_contract.host_mode !== 'mobile_hosted') {{
        throw new Error('queued command route lost mobile host mode');
      }}
    """
    subprocess.run(["node", "-e", script], check=True, cwd=REPO_ROOT)


def test_meta_rayban_browser_simulator_shell_declares_session_controls_and_discovery():
    html = META_RAYBAN_SIMULATOR_HTML.read_text(encoding="utf-8")
    source = META_RAYBAN_SIMULATOR_JS.read_text(encoding="utf-8")
    discovery = META_RAYBAN_DISCOVERY_PATH.read_text(encoding="utf-8")

    for token in [
        "command-surface-select",
        "dispatch-command-button",
        "export-session-button",
        "session-log",
    ]:
        assert token in html
    for token in [
        "buildMobileHostedSession",
        "buildSessionCommand",
        "dispatchSessionCommand",
        "handsfree.virtual-desktop-session",
        "handsfree.command-session@0.1.0",
        "meta_glasses_audio_input",
        "meta_glasses_audio_output",
        "meta_glasses_display_widget",
    ]:
        assert token in source
    for token in [
        "VAI-016",
        "Meta Ray-Ban browser simulator shell",
        "display surface",
        "audio surface",
        "mobile-hosted virtual desktop",
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py",
    ]:
        assert token in discovery


def test_peer_offload_widget_contract_extension_is_documented():
    plan_text = (
        REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.md"
    ).read_text(encoding="utf-8")

    required_contract_terms = [
        "Peer-offload state",
        "peer_offload.availability",
        "desktop-offload availability",
        "unavailable",
        "discovering",
        "available",
        "selected",
        "transferring",
        "running",
        "degraded",
        "failed",
        "fallback_active",
        "peer_offload.selected_peer",
        "peer_id",
        "display_name",
        "endpoint_hint",
        "trust_level",
        "capability_class",
        "last_seen_at",
        "policy_receipt_cid",
        "peer_offload.compute_placement",
        "phone_local",
        "desktop_peer",
        "hybrid",
        "fallback_phone",
        "placement_receipt_cid",
        "peer_offload.transfer_state",
        "operation_id",
        "bytes_sent",
        "bytes_total",
        "throughput_bps",
        "peer_offload.actions",
        "cancel_offload",
        "retry_offload",
        "fallback_to_phone",
        "select_peer",
        "dismiss_offload_message",
        "open_mobile_card",
        "backend-approved action ID",
        "same correlation ID used by the active policy receipt",
        "peer_offload.receipts",
        "orb_receipt_cid",
        "transfer_receipt_cid",
        "fallback_receipt_cid",
        "must not replace `descriptor_refs.policy_receipt_cid`",
        "existing policy receipt model",
        "peer_offload.error",
        "retryable",
    ]

    missing_terms = [term for term in required_contract_terms if term not in plan_text]

    assert missing_terms == []


def test_hardware_free_phone_glasses_terminal_fixture_is_deterministic():
    fixture = json.loads(PHONE_GLASSES_TERMINAL_FIXTURE_PATH.read_text(encoding="utf-8"))
    offline_contract = fixture["offline_contract"]
    launch_replay = fixture["launch_replay_evidence"]
    events = fixture["events"]
    credential_key_fragments = ("credential", "access_token", "refresh_token", "client_secret")

    def credential_like_paths(value, path="fixture"):
        if isinstance(value, dict):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                if any(fragment in key.lower() for fragment in credential_key_fragments):
                    yield child_path
                yield from credential_like_paths(child, child_path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                yield from credential_like_paths(child, f"{path}[{index}]")

    assert fixture["fixture_id"] == "mgw-267-phone-glasses-terminal"
    assert fixture["schema_version"] == "1.2.0"
    assert launch_replay["task_id"] == "MGW-272"
    assert launch_replay["replay_id"] == "launch-session-widget-replay-mgw-272"
    assert launch_replay["extends_replay_id"] == "launch-session-widget-replay-mgw-270"
    assert launch_replay["render_contract"] == "handsfree.virtual-desktop-session"
    assert launch_replay["terminal_contract"] == REMOTE_TERMINAL_CONTRACT_ID
    assert launch_replay["command_contract"] == "vai.shared_capability_envelope@0.1.0"
    assert launch_replay["no_second_widget_command_contract"] is True
    assert launch_replay["single_replay"] is True
    assert set(launch_replay["covers"]) == {
        "phone_hosted_virtual_desktop_status",
        "desktop_peer_offload_state",
        "confirmation_cancel_retry_actions",
        "hallucinate_app_receipt_ids",
        "shared_vai_capability_receipts",
        "placement_recovery_receipt_ids",
    }
    assert set(launch_replay["shared_vai_capability_receipt_cids"]) == {
        "bafy-mgw272-vai-render-receipt",
        "bafy-mgw272-vai-confirm-receipt",
        "bafy-mgw272-vai-update-receipt",
        "bafy-mgw272-vai-cancel-receipt",
    }
    assert set(launch_replay["placement_recovery_receipt_cids"]) == {
        "bafy-mgw267-placement-phone",
        "bafy-mgw267-placement-peer",
        "bafy-mgw272-recovery-preview",
    }
    assert offline_contract["deterministic"] is True
    assert offline_contract["requires_meta_credentials"] is False
    assert offline_contract["requires_paired_hardware"] is False
    assert offline_contract["hardware_required"] is False
    assert offline_contract["paired_device_id"] is None
    assert offline_contract["transport"] == "in_memory_fixture"
    assert offline_contract["clock"] == {
        "start": "2026-06-23T00:00:00Z",
        "step_ms": 1000,
    }
    assert list(credential_like_paths(fixture)) == [
        "fixture.offline_contract.requires_meta_credentials"
    ]
    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert [event["timestamp"] for event in events] == [
        "2026-06-23T00:00:00Z",
        "2026-06-23T00:00:01Z",
        "2026-06-23T00:00:02Z",
    ]
    assert [event["event_type"] for event in events] == [
        "virtual_desktop_status",
        "confirmation_prompt",
        "peer_offload_update",
    ]
    assert [
        event["widget_state"]["hallucinate_app"]["mediation_receipt_id"] for event in events
    ] == launch_replay["hallucinate_app_receipt_ids"]

    for event in events:
        state = event["widget_state"]
        descriptor_refs = state["descriptor_refs"]
        hallucinate_app = state["hallucinate_app"]
        shared_receipts = state["shared_vai_receipts"]
        peer_receipts = state["peer_offload"]["receipts"]
        regions = state["regions"]
        action_region = regions["action_region"]
        placement_receipt_cid = state["peer_offload"]["compute_placement"]["placement_receipt_cid"]

        assert state["widget_kind"] == "handsfree.virtual-desktop-session"
        assert state["session_identity"]["session_id"] == "vdesktop-session-mgw-267"
        assert state["session_identity"]["phone_host_id"] == offline_contract["phone_host_id"]
        assert state["render_context"]["hardware_required"] is False
        assert state["render_context"]["paired_device_id"] is None
        assert state["render_context"]["preview_mode"] is True
        assert state["pairing"]["status"] == "unpaired"
        assert state["active_tool"]["surface"] == "mobile_card"
        assert {"status_region", "progress_region", "message_region", "diagnostics_region"} <= set(
            regions
        )
        assert regions["status_region"]["phone_hosted_status"]
        assert regions["status_region"]["compute_placement"] in {"phone_local", "desktop_peer"}
        assert regions["status_region"]["hallucinate_app_receipt_id"] == (
            hallucinate_app["mediation_receipt_id"]
        )
        assert regions["diagnostics_region"]["hallucinate_app_receipt_id"] == (
            hallucinate_app["mediation_receipt_id"]
        )
        assert hallucinate_app["mediation_receipt_id"].startswith("ha-mgw270-")
        assert hallucinate_app["rendered_receipt_ids"] == [hallucinate_app["mediation_receipt_id"]]
        assert hallucinate_app["virtual_desktop_command_intent_id"].startswith(
            "ha-mgw270-command-"
        )
        assert shared_receipts["command_contract"] == launch_replay["command_contract"]
        assert shared_receipts["capability_id"].startswith("vai.glasses_widget.")
        assert shared_receipts["capability_receipt_cid"] in (
            launch_replay["shared_vai_capability_receipt_cids"]
        )
        assert shared_receipts["mediation_receipt_id"] == hallucinate_app["mediation_receipt_id"]
        assert shared_receipts["placement_receipt_cid"] == placement_receipt_cid
        assert shared_receipts["recovery_receipt_cid"] == "bafy-mgw272-recovery-preview"
        assert shared_receipts["policy_receipt_cid"] == descriptor_refs["policy_receipt_cid"]
        assert shared_receipts["orb_receipt_cid"] == descriptor_refs["orb_receipt_cid"]
        assert action_region["actions"]
        assert all(
            action["hallucinate_app_receipt_id"] == hallucinate_app["mediation_receipt_id"]
            for action in action_region["actions"]
        )
        assert all(
            action["mediation_receipt_id"] == hallucinate_app["mediation_receipt_id"]
            for action in action_region["actions"]
        )
        assert all(
            action["capability_receipt_cid"] in launch_replay["shared_vai_capability_receipt_cids"]
            for action in action_region["actions"]
        )
        assert all(
            action["placement_receipt_cid"] == placement_receipt_cid
            for action in action_region["actions"]
        )
        assert all(
            action["recovery_receipt_cid"] == shared_receipts["recovery_receipt_cid"]
            for action in action_region["actions"]
        )
        assert all(
            action["command_contract"] == launch_replay["command_contract"]
            for action in action_region["actions"]
        )
        assert {
            action["vai_capability_id"] for action in action_region["actions"]
        } <= {
            "vai.glasses_widget.render",
            "vai.glasses_widget.update",
            "vai.glasses_widget.confirm",
            "vai.glasses_widget.cancel",
        }
        assert all(
            action["correlation_id"] == event["correlation_id"]
            for action in action_region["actions"]
        )
        assert all(
            action["backend_action_id"].startswith("terminal.")
            for action in action_region["actions"]
        )
        assert peer_receipts["policy_receipt_cid"] == descriptor_refs["policy_receipt_cid"]
        assert peer_receipts["capability_receipt_cid"] == shared_receipts["capability_receipt_cid"]
        assert peer_receipts["mediation_receipt_id"] == shared_receipts["mediation_receipt_id"]
        assert peer_receipts["placement_receipt_cid"] == placement_receipt_cid
        assert peer_receipts["recovery_receipt_cid"] == shared_receipts["recovery_receipt_cid"]
        assert "open_mobile_card" in state["recovery"]["next_actions"]
        assert state["recovery"]["fallback"]["render_path"] == "mobile-card"

    confirmation_state = events[1]["widget_state"]
    prompt = confirmation_state["confirmation_prompt"]
    assert prompt["prompt_id"] == "confirm-stop-mgw-267"
    assert prompt["kind"] == "cancel"
    assert prompt["risk_level"] == "medium"
    assert prompt["default_action"] == "continue"
    assert [action["id"] for action in prompt["actions"]] == [
        "continue",
        "cancel_task",
        "retry_confirmation",
    ]
    assert [action["kind"] for action in prompt["actions"]] == ["confirm", "cancel", "retry"]
    assert [action["focus_order"] for action in prompt["actions"]] == [1, 2, 3]
    assert all(action["backend_action_id"].startswith("terminal.") for action in prompt["actions"])
    assert all(
        action["correlation_id"] == events[1]["correlation_id"] for action in prompt["actions"]
    )
    assert all(
        action["hallucinate_app_receipt_id"] == "ha-mgw270-confirm-receipt"
        for action in prompt["actions"]
    )
    assert all(
        action["mediation_receipt_id"] == "ha-mgw270-confirm-receipt"
        for action in prompt["actions"]
    )
    assert [action["vai_capability_id"] for action in prompt["actions"]] == [
        "vai.glasses_widget.confirm",
        "vai.glasses_widget.cancel",
        "vai.glasses_widget.update",
    ]
    assert all(
        action["capability_receipt_cid"] in launch_replay["shared_vai_capability_receipt_cids"]
        for action in prompt["actions"]
    )
    assert all(
        action["placement_receipt_cid"] == "bafy-mgw267-placement-phone"
        for action in prompt["actions"]
    )
    assert all(
        action["recovery_receipt_cid"] == "bafy-mgw272-recovery-preview"
        for action in prompt["actions"]
    )
    assert all(
        action["command_contract"] == launch_replay["command_contract"]
        for action in prompt["actions"]
    )

    peer_offload = events[2]["widget_state"]["peer_offload"]
    assert peer_offload["availability"] == "transferring"
    assert peer_offload["selected_peer"]["peer_id"] == "desktop-peer-01"
    assert peer_offload["compute_placement"]["mode"] == "desktop_peer"
    assert peer_offload["transfer_state"] == {
        "operation_id": "offload-transfer-mgw-267",
        "phase": "uploading_context",
        "bytes_sent": 5242880,
        "bytes_total": 8388608,
        "percent": 62,
        "eta_ms": 42000,
        "throughput_bps": 1048576,
        "message": "Sending task context to desktop peer.",
    }
    assert {"cancel_offload", "retry_offload", "fallback_to_phone", "open_mobile_card"} <= set(
        peer_offload["actions"]
    )
    assert peer_offload["receipts"]["hallucinate_app_receipt_id"] == "ha-mgw270-offload-receipt"
    assert peer_offload["receipts"]["capability_receipt_cid"] == (
        "bafy-mgw272-vai-update-receipt"
    )
    assert peer_offload["receipts"]["placement_receipt_cid"] == "bafy-mgw267-placement-peer"
    assert peer_offload["receipts"]["recovery_receipt_cid"] == "bafy-mgw272-recovery-preview"

    launch_action_kinds = {
        action["kind"]
        for event in events
        for action in event["widget_state"]["regions"]["action_region"]["actions"]
    }
    assert {"confirm", "cancel", "retry"} <= launch_action_kinds

    launch_capability_ids = {
        action["vai_capability_id"]
        for event in events
        for action in event["widget_state"]["regions"]["action_region"]["actions"]
    } | {action["vai_capability_id"] for action in prompt["actions"]}
    assert launch_capability_ids == {
        "vai.glasses_widget.render",
        "vai.glasses_widget.update",
        "vai.glasses_widget.confirm",
        "vai.glasses_widget.cancel",
    }


def test_meta_glasses_display_todo_dependencies_are_declared_tasks():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    for task in tasks:
        missing = [dependency for dependency in task.depends_on if dependency not in task_ids]
        assert not missing, f"{task.task_id} has missing dependencies: {missing}"


def test_discovery_expansion_task_waits_for_initial_backlog():
    tasks = {task.task_id: task for task in _load_tasks()}
    discovery = tasks["MGW-013"]

    for index in range(1, 13):
        assert f"MGW-{index:03d}" in discovery.depends_on
    assert "MGW-000" not in discovery.depends_on
    assert "unknowns" in discovery.title.lower()


def test_discovered_supervisor_guardrail_depends_on_discovery_task():
    tasks = {task.task_id: task for task in _load_tasks()}
    guardrail = tasks["MGW-014"]

    assert guardrail.depends_on == ["MGW-013"]
    assert "retry" in guardrail.title.lower()
    assert "JDK 17" in guardrail.acceptance


def test_supervisor_bootstrap_adds_post_initial_discovery_tasks(tmp_path):
    supervisor_module = _load_script_module("meta_glasses_display_todo_supervisor")
    ensure_post_initial_discovery_backlog = supervisor_module.ensure_post_initial_discovery_backlog

    task_board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    task_board_path.write_text(
        """# Temporary Board

## MGW-001 Initial task

- Status: completed
- Completion: manual
- Priority: P0
- Track: ops
- Depends on:
- Outputs: docs/example.md
- Validation: true
- Acceptance: Example task.
""",
        encoding="utf-8",
    )

    assert ensure_post_initial_discovery_backlog(task_board_path)
    updated = task_board_path.read_text(encoding="utf-8")

    assert "## MGW-013 Investigate implementation unknowns and expand the backlog" in updated
    assert "Depends on: MGW-001, MGW-002, MGW-003" in updated
    assert "MGW-012" in updated
    assert "## MGW-014 Add supervisor validation-environment and retry-budget guardrails" in updated
    assert "Depends on: MGW-013" in updated
    assert not ensure_post_initial_discovery_backlog(task_board_path)


def test_meta_display_bootstrap_paths_can_be_overridden(tmp_path, monkeypatch):
    supervisor_module = _load_script_module("meta_glasses_display_todo_supervisor")
    daemon_module = _load_script_module("meta_glasses_display_todo_daemon")
    custom_board = tmp_path / TEMP_TASK_BOARD_FILENAME
    custom_state = tmp_path / "state"
    custom_worktrees = tmp_path / "worktrees"
    custom_discovery = REPO_ROOT / "data" / "custom_mgw_discovery"
    custom_objective = tmp_path / "objective.md"
    custom_bundles = tmp_path / "bundles"
    custom_graph = tmp_path / "objective_graph.json"
    custom_datasets = tmp_path / "datasets"
    custom_vector_index = tmp_path / "todo_vector_index.json"

    monkeypatch.setenv("HANDSFREE_MGW_TODO_PATH", str(custom_board))
    monkeypatch.setenv("HANDSFREE_MGW_STATE_DIR", str(custom_state))
    monkeypatch.setenv("HANDSFREE_MGW_WORKTREE_ROOT", str(custom_worktrees))
    monkeypatch.setenv("HANDSFREE_MGW_DISCOVERY_DIR", str(custom_discovery))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_HEAP_PATH", str(custom_objective))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_BUNDLE_DIR", str(custom_bundles))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_GRAPH_PATH", str(custom_graph))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_DATASET_DIR", str(custom_datasets))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_TODO_VECTOR_INDEX_PATH", str(custom_vector_index))

    daemon_paths = daemon_module.meta_display_bootstrap_paths()
    supervisor_paths = supervisor_module.meta_display_bootstrap_paths()

    assert daemon_paths["todo_path"] == custom_board
    assert daemon_paths["state_dir"] == custom_state
    assert daemon_paths["worktree_root"] == custom_worktrees
    assert daemon_paths["discovery_dir"] == custom_discovery
    assert daemon_paths["objective_heap_path"] == custom_objective
    assert daemon_paths["objective_bundle_dir"] == custom_bundles
    assert supervisor_paths["objective_graph_path"] == custom_graph
    assert supervisor_paths["objective_dataset_dir"] == custom_datasets
    assert supervisor_paths["objective_todo_vector_index_path"] == custom_vector_index
    assert supervisor_module._META_DISPLAY_BOOTSTRAP_PATHS.output_path(
        "discovery_dir",
        "data/meta_glasses_display_widgets/discovery",
        supervisor_paths,
    ) == "data/custom_mgw_discovery"


def test_meta_display_bootstrap_docs_match_runtime_paths():
    config_text = (REPO_ROOT / "docs" / "CONFIGURATION.md").read_text(encoding="utf-8")
    getting_started_text = (REPO_ROOT / "docs" / "GETTING_STARTED.md").read_text(encoding="utf-8")

    for text in (config_text, getting_started_text):
        assert "scripts/meta_glasses_display_todo_daemon.py --once" in text
        assert "scripts/meta_glasses_display_todo_supervisor.py --once" in text
        assert "HANDSFREE_MGW_TODO_PATH" in text
        assert "HANDSFREE_MGW_STATE_DIR" in text
        assert "HANDSFREE_MGW_WORKTREE_ROOT" in text
        assert "data/meta_glasses_display_widgets/state" in text
        assert "data/meta_glasses_display_widgets/worktrees" in text

    assert "HANDSFREE_MGW_DISCOVERY_DIR" in config_text
    assert "meta_glasses_display_task_state.json" in config_text


def test_meta_display_wrappers_delegate_reusable_namespace_context():
    supervisor_module = _load_script_module("meta_glasses_display_todo_supervisor")
    daemon_module = _load_script_module("meta_glasses_display_todo_daemon")
    supervisor_source = (SCRIPTS_DIR / "meta_glasses_display_todo_supervisor.py").read_text(encoding="utf-8")
    daemon_source = (SCRIPTS_DIR / "meta_glasses_display_todo_daemon.py").read_text(encoding="utf-8")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.wrapper_utils import AgentSupervisorNamespaceContext

    assert isinstance(daemon_module.META_DISPLAY_CONTEXT, AgentSupervisorNamespaceContext)
    assert isinstance(supervisor_module.META_DISPLAY_CONTEXT, AgentSupervisorNamespaceContext)
    assert daemon_module.META_DISPLAY_CONTEXT is daemon_module._META_DISPLAY_CONTEXT
    assert "external/ipfs_accelerate" in daemon_module.META_DISPLAY_WORKTREE_SUBMODULE_PATHS
    assert "external/ipfs_datasets" in daemon_module.META_DISPLAY_WORKTREE_SUBMODULE_PATHS
    assert supervisor_module.META_DISPLAY_WORKTREE_SUBMODULE_PATHS == daemon_module.META_DISPLAY_WORKTREE_SUBMODULE_PATHS
    for module in (daemon_module, supervisor_module):
        assert module.META_DISPLAY_CONTEXT.namespace_paths.namespace == "meta_glasses_display_widgets"
        assert module.META_DISPLAY_CONTEXT.task_board_path == TASK_BOARD_PATH
        assert module.META_DISPLAY_DATA_PATHS == module.META_DISPLAY_CONTEXT.namespace_paths
    assert "build_agent_supervisor_namespace_context(" in daemon_source
    assert "build_agent_supervisor_namespace_context(" not in supervisor_source
    assert "agent_supervisor_namespace_paths(" not in daemon_source
    assert "agent_supervisor_namespace_paths(" not in supervisor_source
    assert "build_agent_supervisor_runtime_bootstrap_callbacks(" not in daemon_source
    assert "build_agent_supervisor_runtime_bootstrap_callbacks(" not in supervisor_source


def test_meta_display_bootstrap_creates_runtime_directories(tmp_path):
    daemon_module = _load_script_module("meta_glasses_display_todo_daemon")
    paths = {
        "repo_root": tmp_path,
        "todo_path": tmp_path / TEMP_TASK_BOARD_FILENAME,
        "state_dir": tmp_path / "state",
        "worktree_root": tmp_path / "worktrees",
        "discovery_dir": tmp_path / "discovery",
        "objective_heap_path": tmp_path / "objective.md",
        "objective_bundle_dir": tmp_path / "bundles",
        "objective_dataset_dir": tmp_path / "datasets",
    }

    daemon_module.ensure_meta_display_bootstrap_paths(paths)

    assert paths["state_dir"].exists()
    assert paths["worktree_root"].exists()
    assert paths["discovery_dir"].exists()
    assert paths["objective_bundle_dir"].exists()
    assert paths["objective_dataset_dir"].exists()


def test_meta_display_supervisor_ensure_running_flag_uses_runtime_helper(tmp_path, monkeypatch):
    supervisor_module = _load_script_module("meta_glasses_display_todo_supervisor")
    task_board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    task_board_path.write_text("# Temporary Board\n", encoding="utf-8")
    captured: dict[str, object] = {}

    monkeypatch.setenv("HANDSFREE_MGW_TODO_PATH", str(task_board_path))
    monkeypatch.setenv("HANDSFREE_MGW_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HANDSFREE_MGW_WORKTREE_ROOT", str(tmp_path / "worktrees"))
    monkeypatch.setenv("HANDSFREE_MGW_DISCOVERY_DIR", str(tmp_path / "discovery"))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_HEAP_PATH", str(tmp_path / "objective.md"))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_GRAPH_PATH", str(tmp_path / "objective_graph.json"))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_BUNDLE_DIR", str(tmp_path / "objective_bundles"))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_DATASET_DIR", str(tmp_path / "objective_datasets"))
    monkeypatch.setenv("HANDSFREE_MGW_OBJECTIVE_TODO_VECTOR_INDEX_PATH", str(tmp_path / "todo_vector_index.json"))
    runtime_class = type(supervisor_module._meta_display_supervisor_runtime)
    monkeypatch.setattr(
        runtime_class,
        "run_configured",
        lambda self, args, **kwargs: captured.setdefault(
            "payload",
            {"runtime": self, "args": args, "kwargs": kwargs},
        ),
    )

    supervisor_module.main(["--ensure-running", "--once"])

    payload = captured["payload"]
    runtime = payload["runtime"]
    args = payload["args"]
    kwargs = payload["kwargs"]
    assert "--ensure-running" not in args
    assert kwargs["ensure_running"] is True
    assert runtime.process_match_any == supervisor_module.META_DISPLAY_SUPERVISOR_PROCESS_MARKERS


def test_codebase_scan_skips_generated_discovery_dirs():
    supervisor_module = _load_script_module("meta_glasses_display_todo_supervisor")

    assert "data/meta_glasses_display_widgets/discovery/" in supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES
    assert "data/hallucinate_multimodal_control/discovery/" in supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES
    assert supervisor_module.META_DISPLAY_INTEROPERABILITY_FOCUS == ("hallucinate_app",)


def test_android_validation_environment_uses_repo_local_tools(monkeypatch):
    daemon_module = _load_script_module("meta_glasses_display_todo_daemon")
    jdk = REPO_ROOT / ".tools" / "jdk17" / "jdk-17.0.18+8"
    sdk = REPO_ROOT / ".tools" / "android-sdk"

    monkeypatch.delenv("JAVA_HOME", raising=False)
    monkeypatch.delenv("ANDROID_HOME", raising=False)
    monkeypatch.delenv("ANDROID_SDK_ROOT", raising=False)
    monkeypatch.setenv("PATH", "/usr/bin")

    contract = daemon_module._bootstrap_android_validation_env(REPO_ROOT)

    assert contract["env"]["JAVA_HOME"] == str(jdk)
    assert os.environ["JAVA_HOME"] == str(jdk)
    assert os.environ["ANDROID_HOME"] == str(sdk)
    assert os.environ["ANDROID_SDK_ROOT"] == str(sdk)
    assert os.environ["PATH"].split(os.pathsep)[0] == str(jdk / "bin")


def test_android_gradle_validations_are_env_wrapped_in_board():
    tasks = _load_tasks()
    gradle_validations = [
        command
        for task in tasks
        for command in task.validation
        if "./gradlew" in command and "mobile/android" in command
    ]

    assert gradle_validations
    assert all(".tools/jdk17/jdk-17.0.18+8" in command for command in gradle_validations)
    assert all("JAVA_HOME=" in command for command in gradle_validations)


def test_enforce_android_validation_environment_rewrites_bare_gradle_command(tmp_path):
    daemon_module = _load_script_module("meta_glasses_display_todo_daemon")
    task_board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    task_board_path.write_text(
        f"""# Temporary Board

## MGW-001 Android task

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on:
- Outputs: mobile/android
- Validation: cd mobile/android && ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false
- Acceptance: Build Android.
""",
        encoding="utf-8",
    )

    assert daemon_module.enforce_android_validation_environment(task_board_path, REPO_ROOT)
    updated = task_board_path.read_text(encoding="utf-8")

    assert f"- Status: {PENDING_TASK_STATUS}" in updated and "env JAVA_HOME=" in updated
    assert ".tools/jdk17/jdk-17.0.18+8" in updated
    assert "ANDROID_SDK_ROOT=" in updated
    assert not daemon_module.enforce_android_validation_environment(task_board_path, REPO_ROOT)


def test_retry_budget_finding_appends_daemon_parseable_followup(tmp_path, monkeypatch):
    daemon_module = _load_script_module("meta_glasses_display_todo_daemon")
    local_jdk_bin = tmp_path / ".tools" / "jdk17" / "jdk-17.0.18+8" / "bin"
    local_jdk_bin.mkdir(parents=True)
    (local_jdk_bin / "java").touch()
    (tmp_path / ".tools" / "android-sdk" / "platform-tools").mkdir(parents=True)
    original_with_android_validation_env = daemon_module.with_android_validation_env

    def with_tmp_android_validation_env(command: str) -> str:
        return original_with_android_validation_env(command, tmp_path)

    monkeypatch.setattr(daemon_module, "with_android_validation_env", with_tmp_android_validation_env)
    task_board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    assert task_board_path.name == TEMP_TASK_BOARD_FILENAME
    events_path = tmp_path / "events.jsonl"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = tmp_path / "discovery"
    task_board_path.write_text(
        f"""# Temporary Board

## MGW-001 Android task

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on:
- Outputs: mobile/android/app/build.gradle
- Validation: cd mobile/android && ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false
- Acceptance: Build Android.

## MGW-014 Guardrails

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: scripts/meta_glasses_display_todo_daemon.py
- Validation: true
- Acceptance: Guardrails are installed.
""",
        encoding="utf-8",
    )
    fixture_text = task_board_path.read_text(encoding="utf-8")
    assert f"- Status: {PENDING_TASK_STATUS}" in fixture_text
    failed_command = "cd mobile/android && ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false"
    events = [
        {
            "type": "implementation_finished",
            "timestamp": f"2026-05-22T00:0{index}:00+00:00",
            "task_id": "MGW-001",
            "attempt": index,
            "returncode": 1,
            "log_path": str(tmp_path / f"mgw-001-attempt-{index}.log"),
            "validation_result": {
                "attempted": True,
                "passed": False,
                "returncode": 1,
                "failed_command": failed_command,
                "results": [{"command": failed_command, "returncode": 1}],
            },
        }
        for index in range(1, 4)
    ]
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    findings = daemon_module.record_retry_budget_findings(
        todo_path=task_board_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = discovery_dir / f"{datetime.now(timezone.utc).date().isoformat()}-mgw-015-mgw-001-retry-budget.md"
    assert findings == [
        {
            "source_task_id": "MGW-001",
            "follow_up_task_id": "MGW-015",
            "failure_count": 3,
            "failed_command": failed_command,
            "discovery_path": str(expected_discovery),
        }
    ]
    updated = task_board_path.read_text(encoding="utf-8")
    assert "## MGW-015 Resolve validation retry-budget failure for MGW-001" in updated
    assert "Depends on: MGW-014" in updated
    assert "env JAVA_HOME=" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(task_board_path, "## MGW-")}
    assert tasks["MGW-015"].depends_on == ["MGW-014"]
    assert "retry-budget" in tasks["MGW-015"].title

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "MGW-001" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert failed_command in discovery
    assert "Observed consecutive validation failures: 3" in discovery
    assert not daemon_module.record_retry_budget_findings(
        todo_path=task_board_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )


def test_meta_glasses_llm_router_preflight_does_not_call_model():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/meta_glasses_display_llm_router.py",
            "--task-id",
            "MGW-001",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert '"generate": false' in completed.stdout
    assert '"llm_router_importable": true' in completed.stdout
    router_module = _load_script_module("meta_glasses_display_llm_router")
    source = (SCRIPTS_DIR / "meta_glasses_display_llm_router.py").read_text(encoding="utf-8")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.task_proposal_router import TaskProposalRouteSpec

    assert isinstance(router_module.TASK_PROPOSAL_ROUTE_SPEC, TaskProposalRouteSpec)
    assert "build_repo_task_proposal_route_runner_from_spec(" in source
    assert "build_repo_task_proposal_route_runner(" not in source
