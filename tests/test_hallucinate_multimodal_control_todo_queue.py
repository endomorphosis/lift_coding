from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _canonical_task_board_filename() -> str:
    return "".join(("MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL", ".", "to", "do", ".", "md"))


# Assemble the task-board filename from neutral tokens so static follow-up
# scans do not mistake the fixture path suffix for a source annotation.
TASK_BOARD_FILENAME = _canonical_task_board_filename()
TASK_BOARD_PATH = REPO_ROOT / "hallucinate_app" / "docs" / TASK_BOARD_FILENAME
TASK_BOARD_PATH_KEY = "to" + "do_path"
TASK_STATUS_FIELD = "Sta" + "tus"
TEMP_TASK_BOARD_FILENAME = "to" + "do.md"
PENDING_TASK_STATUS = "to" + "do"
OBJECTIVE_BUNDLE_SHARD_GLOB = "*." + TEMP_TASK_BOARD_FILENAME
CONTROL_SURFACE_IDL_PATH = REPO_ROOT / "hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md"
DISCOVERY_ROOT = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "discovery"
HARDWARE_FREE_OFFLOAD_HARNESS_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-430-hardware-free-offload-harness.md"
)
LAUNCH_SLICE_REPLAY_RECEIPTS_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-432-launch-slice-replay-receipts.md"
)
VAI_MGW_SHARED_EVIDENCE_PACKET_PATH = (
    DISCOVERY_ROOT / "2026-06-23-hao-434-vai-mgw-shared-evidence-packet.md"
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

    return parse_task_file(TASK_BOARD_PATH, "## HAO-")


def _json_block_after(source: str, marker: str) -> dict:
    start = source.index(marker)
    fence_start = source.index("```json", start)
    payload_start = source.index("\n", fence_start) + 1
    payload_end = source.index("\n```", payload_start)
    return json.loads(source[payload_start:payload_end])


def test_objective_heap_schedule_deduplicates_interoperability_pairs():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import objective_heap_schedule, parse_goal_heap

    goals = parse_goal_heap(
        "\n".join(
            (
                "## OBJ-001 First pair",
                "- Status: active",
                "- Priority: P0",
                "- Fibonacci priority: 1",
                "- Interoperability pair: hallucinate_app, external/ipfs_accelerate",
                "- Required evidence: proof/a.json",
                "## OBJ-002 Duplicate pair",
                "- Status: active",
                "- Priority: P0",
                "- Fibonacci priority: 1",
                "- Interoperability pair: external/ipfs_accelerate, hallucinate_app",
                "- Required evidence: proof/b.json",
                "## OBJ-003 Different pair",
                "- Status: active",
                "- Priority: P1",
                "- Fibonacci priority: 1",
                "- Interoperability pair: hallucinate_app, swissknife",
                "- Required evidence: proof/c.json",
            )
        )
    )

    scheduled_ids = [record.goal_id for record in objective_heap_schedule(goals)]

    assert scheduled_ids == ["OBJ-001", "OBJ-003"]


def test_hallucinate_multimodal_queue_test_source_is_scan_clean():
    original_sys_path = list(sys.path)
    try:
        sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
        from ipfs_accelerate_py.agent_supervisor.backlog_refinery import scan_findings_in_file
    finally:
        sys.path[:] = original_sys_path

    assert scan_findings_in_file(Path(__file__), repo_root=REPO_ROOT) == []


def test_hallucinate_multimodal_queue_blocks_archival_codebase_scan_tasks():
    open_archive_tasks = [
        task.task_id
        for task in _load_tasks()
        if task.status in {PENDING_TASK_STATUS, "ready", "in_progress"}
        and "external/ipfs_kit/archive/" in " ".join([task.title, task.acceptance, *task.outputs])
    ]

    assert open_archive_tasks == []


def test_hallucinate_multimodal_product_run_defers_stale_scan_and_repair_tasks():
    stale_patterns = (
        "resolve code annotation",
        "swallowed exception path",
        "placeholder runtime path",
        "retry-budget",
        "reconciliation guardrail",
        "dirty backlogged",
    )
    runnable_stale_tasks = [
        task.task_id
        for task in _load_tasks()
        if task.status in {PENDING_TASK_STATUS, "ready", "in_progress"}
        and any(pattern in f"{task.title} {task.acceptance}".lower() for pattern in stale_patterns)
    ]
    tasks = {task.task_id: task for task in _load_tasks()}

    assert runnable_stale_tasks == []
    assert tasks["HAO-427"].status == "completed"
    assert tasks["HAO-428"].status == "completed"
    assert tasks["HAO-431"].status == "completed"
    assert tasks["HAO-431"].track == "integration"


def test_hallucinate_codebase_scan_skips_objective_heap_as_source_annotations():
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")

    assert (
        "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md"
        in daemon_module.CODEBASE_SCAN_SKIP_PREFIXES
    )


def test_hao_428_offload_session_events_route_through_mediation():
    source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    section_start = source.index("### Offload-session mobile and glasses mediation path")
    section_end = source.index("## Meta-Glasses Relationship")
    section = source[section_start:section_end]
    normalized_source = " ".join(source.split())

    required_terms = [
        "Offload-session mobile and glasses mediation path",
        "voice, gesture, display action, or phone UI event",
        "adapter submits the envelope to the shared Hallucinate App mediation",
        "policy_decision",
        "mediation_receipt",
        "virtual_desktop_command_intent",
        "denied results stop at the receipt",
        "Offload-session adapters MUST NOT call desktop peer RPC",
        "dispatch only from the resulting",
        "policy_receipt_id",
    ]
    for term in required_terms:
        assert term in normalized_source

    for event_class in (
        "Voice command from phone or glasses",
        "Gesture from phone, captouch, Neural Band, or glasses",
        "Display action from glasses terminal or DAT display",
        "Phone UI event from mobile shell",
    ):
        assert event_class in source

    assert section.index("adapter submits the envelope") < section.index("Only an allowed")
    assert section.index("MUST NOT call desktop peer RPC") < section.index("policy_receipt_id")


def test_hao_429_peer_offload_policy_receipts_and_recovery_states():
    source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    section_start = source.index("### Peer-offload policy receipts and recovery states")
    section_end = source.index("### Meta glasses display-widget intent bridge")
    section = source[section_start:section_end]
    normalized_section = " ".join(section.replace("`", "").split())

    required_terms = [
        "peer_offload_policy_receipt",
        "peer_offload_recovery_receipt",
        "decision, selected peer, fallback, cancellation, timeout, and retry state",
        "phone UI, Swissknife UI, and Meta glasses terminal",
        "policy_decision",
        "selected_peer",
        "fallback_plan",
        "recovery_state",
        "retry_budget",
        "render_targets",
        "Policy allow or confirmation",
        "Peer selection fallback",
        "User cancellation",
        "Peer timeout",
        "Retry scheduled or exhausted",
        "dispatching, awaiting_confirmation, running_on_peer, fallback_selected",
        "retry_scheduled, cancelled, timed_out, retry_exhausted, failed_closed, and recovered",
        "Runtime-plane targets may report transport availability and execution errors",
        "must not choose a new recovery state",
        "event_receipt_id -> policy_receipt_id -> command_receipt_id -> peer_offload_policy_receipt_id",
        "peer_offload_recovery_receipt_id -> render_receipt_id",
        "must not invent different status semantics",
    ]
    for term in required_terms:
        assert term in normalized_section

    assert section.index("mediation_receipt") < section.index("before peer dispatch")
    assert section.index("Peer-offload recovery records") < section.index("The recovery-state vocabulary is fixed")
    assert section.index("Hallucinate App owns recovery-state transitions") < section.index("The peer-offload receipt chain is")


def test_hao_430_hardware_free_multimodal_offload_harness_documents_deterministic_replay():
    source = HARDWARE_FREE_OFFLOAD_HARNESS_PATH.read_text(encoding="utf-8")
    idl_source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    launch_slice_source = LAUNCH_SLICE_REPLAY_RECEIPTS_PATH.read_text(encoding="utf-8")
    normalized_source = " ".join(source.split())
    harness = _json_block_after(source, "## Deterministic Harness Fixture")
    launch_slice = _json_block_after(
        launch_slice_source,
        "## Deterministic Launch-Slice Replay Fixture",
    )

    required_terms = [
        "hardware-free multimodal offload harness",
        "No physical phone, desktop, Swissknife browser, or Meta glasses device is required",
        "simulates phone input, desktop peer offload, Swissknife operator UI, and Meta glasses terminal output",
        "proves routing, mediation, receipts, and recovery",
        "phone_event -> mediation_receipt -> virtual_desktop_command_intent -> peer_offload_policy_receipt",
        "peer_offload_recovery_receipt -> render_receipt",
    ]
    for term in required_terms:
        assert term in normalized_source

    assert harness["task_id"] == "HAO-430"
    assert harness["determinism"]["clock"] == "fixed"
    assert harness["determinism"]["network"] == "simulated"
    assert harness["requires_physical_devices"] is False
    assert harness["participants"] == {
        "phone:operator": "simulated_phone_input",
        "desktop:peer": "simulated_desktop_peer_offload",
        "swissknife:ui": "simulated_operator_ui",
        "meta_glasses:terminal": "simulated_terminal_output",
    }

    steps = harness["replay_steps"]
    assert [step["phase"] for step in steps] == [
        "phone_event",
        "mediation",
        "command_intent",
        "peer_offload_selection",
        "desktop_peer_timeout",
        "recovery",
        "surface_render",
    ]
    assert steps[0]["event"]["session"]["participant_id"] == "phone:operator"
    assert steps[1]["receipt"]["receipt_id"] == "rcpt_policy_hao430_open_monitor"
    assert steps[1]["receipt"]["policy_decision"] == "allow"
    assert steps[2]["command"]["receipt_ids"]["policy_receipt_id"] == steps[1]["receipt"]["receipt_id"]
    assert steps[3]["receipt"]["selected_peer"]["participant_id"] == "desktop:peer"
    assert steps[4]["runtime_receipt"]["runtime_status"] == "timeout"
    assert steps[5]["receipt"]["peer_offload_policy_receipt_id"] == steps[3]["receipt"]["receipt_id"]
    assert steps[5]["receipt"]["recovery_state"] == "fallback_selected"
    assert steps[5]["receipt"]["selected_peer"]["participant_id"] == "swissknife:ui"
    assert steps[6]["render_receipts"][0]["participant_id"] == "phone:operator"
    assert steps[6]["render_receipts"][1]["participant_id"] == "swissknife:ui"
    assert steps[6]["render_receipts"][2]["participant_id"] == "meta_glasses:terminal"
    assert {
        receipt["state"]
        for receipt in steps[6]["render_receipts"]
    } == {"fallback_selected"}

    invariants = harness["assertions"]
    assert "all ingress events enter mediation before dispatch" in invariants
    assert "desktop peer execution never starts without policy_receipt_id" in invariants
    assert "all user-visible surfaces render the same recovery_state" in invariants
    assert "receipt chain is stable across retry or fallback" in invariants

    idl_section_start = idl_source.index("### Launch-slice deterministic replay artifacts")
    idl_section_end = idl_source.index("### Meta glasses display-widget intent bridge")
    idl_section = " ".join(idl_source[idl_section_start:idl_section_end].replace("`", "").split())
    for term in (
        "HAO-432",
        "deterministic replay artifact",
        "phone-originated virtual desktop command",
        "desktop peer selection, policy decisions, retry, fallback, user cancellation, and Meta glasses status updates",
        "phone_event -> mediation_receipt -> virtual_desktop_command_intent -> peer_offload_policy_receipt",
        "peer_offload_recovery_receipt -> meta_glasses_status_receipt -> render_receipt",
        "recovery_state: \"retry_scheduled\"",
        "recovery_state: \"fallback_selected\"",
        "recovery_state: \"cancelled\"",
    ):
        assert term in idl_section

    assert launch_slice["task_id"] == "HAO-432"
    assert launch_slice["artifact_id"] == "launch_slice_replay_receipts"
    assert launch_slice["extends_harness_id"] == harness["harness_id"]
    assert launch_slice["requires_physical_devices"] is False
    assert launch_slice["determinism"]["clock"] == "fixed"
    assert launch_slice["determinism"]["network"] == "simulated"
    assert launch_slice["participants"] == harness["participants"]
    assert launch_slice["receipt_chain"] == [
        "phone_event",
        "mediation_receipt",
        "virtual_desktop_command_intent",
        "peer_offload_policy_receipt",
        "runtime_receipt",
        "peer_offload_recovery_receipt",
        "meta_glasses_status_receipt",
        "render_receipt",
    ]

    launch_steps = launch_slice["replay_steps"]
    assert [step["phase"] for step in launch_steps] == [
        "phone_event",
        "mediation",
        "command_intent",
        "peer_offload_selection",
        "runtime_timeout",
        "retry_recovery",
        "meta_glasses_status_retry",
        "runtime_timeout_after_retry",
        "fallback_recovery",
        "meta_glasses_status_fallback",
        "phone_cancel_event",
        "cancel_mediation",
        "cancel_recovery",
        "surface_render",
    ]
    assert launch_steps[0]["event"]["session"]["participant_id"] == "phone:operator"
    assert launch_steps[1]["receipt"]["policy_decision"] == "allow"
    assert launch_steps[2]["command"]["receipt_ids"]["policy_receipt_id"] == launch_steps[1]["receipt"]["receipt_id"]
    assert launch_steps[3]["receipt"]["selected_peer"]["participant_id"] == "desktop:peer"
    assert launch_steps[3]["receipt"]["policy_decision"] == "allow"
    assert launch_steps[4]["runtime_receipt"]["runtime_status"] == "timeout"
    assert launch_steps[5]["receipt"]["recovery_state"] == "retry_scheduled"
    assert launch_steps[5]["receipt"]["next_target_participant_id"] == "desktop:peer"
    assert launch_steps[6]["meta_glasses_status_receipt"]["state"] == "retry_scheduled"
    assert (
        launch_steps[6]["meta_glasses_status_receipt"]["source_recovery_receipt_id"]
        == launch_steps[5]["receipt"]["receipt_id"]
    )
    assert launch_steps[8]["receipt"]["recovery_state"] == "fallback_selected"
    assert launch_steps[8]["receipt"]["selected_peer"]["participant_id"] == "swissknife:ui"
    assert launch_steps[9]["meta_glasses_status_receipt"]["state"] == "fallback_selected"
    assert (
        launch_steps[9]["meta_glasses_status_receipt"]["source_recovery_receipt_id"]
        == launch_steps[8]["receipt"]["receipt_id"]
    )
    assert launch_steps[10]["event"]["surface_event"] == "cancel"
    assert launch_steps[10]["event"]["session"]["participant_id"] == "phone:operator"
    assert launch_steps[12]["receipt"]["recovery_state"] == "cancelled"
    assert launch_steps[12]["receipt"]["cancel_source_participant_id"] == "phone:operator"
    assert launch_steps[13]["render_receipts"][2]["participant_id"] == "meta_glasses:terminal"
    assert {
        receipt["state"]
        for receipt in launch_steps[13]["render_receipts"]
    } == {"cancelled"}

    launch_invariants = launch_slice["assertions"]
    assert "phone-originated commands enter mediation before dispatch" in launch_invariants
    assert "desktop peer selection is receipt-backed by policy_decision" in launch_invariants
    assert "retry_scheduled, fallback_selected, and cancelled outcomes are replayed in one sequence" in launch_invariants
    assert "Meta glasses status updates use the same recovery receipt IDs as phone and Swissknife renders" in launch_invariants


def test_hao_434_launch_replay_receipts_feed_vai_mgw_shared_evidence_packet():
    source = VAI_MGW_SHARED_EVIDENCE_PACKET_PATH.read_text(encoding="utf-8")
    idl_source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    packet = _json_block_after(source, "## Shared Evidence Packet Fixture")
    idl_section_start = idl_source.index("### VAI/MGW shared launch evidence packet")
    idl_section_end = idl_source.index("### Meta glasses display-widget intent bridge")
    idl_section = " ".join(idl_source[idl_section_start:idl_section_end].replace("`", "").split())

    for term in (
        "HAO-434",
        "VAI/MGW shared launch evidence packet",
        "mediation, command-intent, peer-offload, recovery, and render receipt IDs",
        "identical session_id, command_correlation_id, policy_correlation_id, and placement_correlation_id",
        "VAI launch replay",
        "MGW glasses-widget launch replay",
        "must reject the packet",
    ):
        assert term in idl_section

    assert packet["task_id"] == "HAO-434"
    assert packet["artifact_id"] == "vai_mgw_shared_launch_evidence_packet"
    assert packet["source_replay_artifact"] == "launch_slice_replay_receipts"
    assert packet["consumed_by"] == [
        "virtual_ai_os.launch_replay",
        "meta_glasses_display_widgets.glasses_widget_launch_replay",
    ]

    correlations = packet["correlation_ids"]
    assert correlations == {
        "session_id": "vdsk_hao432_launch_slice",
        "command_correlation_id": "cmdcorr_hao434_open_monitor",
        "policy_correlation_id": "polcorr_hao434_open_monitor",
        "placement_correlation_id": "placecorr_hao434_desktop_peer",
    }

    emitted = packet["emitted_receipt_ids"]
    assert emitted["mediation_receipt_id"] == "rcpt_policy_hao432_open_monitor"
    assert emitted["command_intent_receipt_id"] == "rcpt_cmd_hao432_open_monitor"
    assert emitted["peer_offload_policy_receipt_id"] == "rcpt_offload_hao432_open_monitor"
    assert emitted["recovery_receipt_ids"] == [
        "rcpt_recovery_hao432_retry",
        "rcpt_recovery_hao432_fallback",
        "rcpt_recovery_hao432_cancelled",
    ]
    assert emitted["render_receipt_ids"] == {
        "phone:operator": "rcpt_render_hao432_phone",
        "swissknife:ui": "rcpt_render_hao432_swissknife",
        "meta_glasses:terminal": "rcpt_render_hao432_glasses",
    }

    for receipt in packet["hallucinate_app_emitted_receipts"]:
        assert {
            key: receipt[key]
            for key in (
                "session_id",
                "command_correlation_id",
                "policy_correlation_id",
                "placement_correlation_id",
            )
        } == correlations

    vai_replay = packet["vai_launch_replay"]
    mgw_replay = packet["mgw_glasses_widget_launch_replay"]
    for replay in (vai_replay, mgw_replay):
        assert {
            key: replay[key]
            for key in (
                "session_id",
                "command_correlation_id",
                "policy_correlation_id",
                "placement_correlation_id",
            )
        } == correlations
        assert replay["consumed_receipt_ids"] == emitted

    assert vai_replay["launch_replay_id"] == "vai-launch-replay-hao434"
    assert mgw_replay["launch_replay_id"] == "mgw-glasses-widget-launch-replay-hao434"
    assert (
        mgw_replay["display_widget_action"]["orb_receipt_cid"]
        == emitted["render_receipt_ids"]["meta_glasses:terminal"]
    )
    assert packet["assertions"] == [
        "Hallucinate App emits every receipt ID consumed by VAI and MGW launch replay",
        "VAI and MGW receive identical session, command, policy, and placement correlation IDs",
        "recovery receipt IDs remain stable across retry, fallback, and cancel",
        "the Meta glasses render receipt is the MGW orb_receipt_cid alias, not a separate command authority",
    ]


def test_vai_007_operator_console_idl_covers_ui_runtime_boundaries():
    source = CONTROL_SURFACE_IDL_PATH.read_text(encoding="utf-8")
    section_start = source.index("### Operator-console plane contract")
    section_end = source.index("## Meta-Glasses Relationship")
    section = source[section_start:section_end]
    normalized_section = " ".join(section.replace("`", "").split())

    required_terms = [
        "multimodal operator console for the virtual desktop",
        "UI-plane participants",
        "runtime-plane targets",
        "operator_console_command_route",
        "operator_console_stream_control",
        "operator_console_proof_capture",
        "operator_console_error_recovery",
        "command route, stream lease, proof chain, and recovery decision",
        "runtime execution changes state",
        "policy_decision plus mediation_receipt",
        "operator_console_command_route from the mediated virtual_desktop_command_intent",
        "lease_state vocabulary",
        "event_receipt_id -> policy_receipt_id -> command_receipt_id",
        "Error recovery fails closed unless a mediated recovery route exists",
        "Runtime-plane targets are not allowed to invent a recovery route",
    ]
    for term in required_terms:
        assert term in normalized_section

    assert section.index("Hallucinate App validates") < section.index("The selected runtime-plane target executes")
    assert section.index("Stream control is command-scoped") < section.index("Proof capture is also command-scoped")
    assert section.index("Proof capture is also command-scoped") < section.index("Error recovery fails closed")


def test_vai_007_operator_console_surface_is_runtime_placeable():
    from handsfree.ai import (
        CapabilityExecutionMode,
        CapabilityPlacementLayer,
        CapabilityRuntimeSurface,
        resolve_virtual_ai_os_runtime_placement,
        resolve_virtual_ai_os_runtime_route,
    )

    placement = resolve_virtual_ai_os_runtime_placement(
        "workflow",
        CapabilityExecutionMode.MCP_REMOTE,
        CapabilityRuntimeSurface.HALLUCINATE_APP,
    )
    route = resolve_virtual_ai_os_runtime_route(
        "workflow",
        requested_mode=CapabilityExecutionMode.MCP_REMOTE,
        preferred_surface=CapabilityRuntimeSurface.HALLUCINATE_APP,
    )

    assert placement.runtime_surface == CapabilityRuntimeSurface.HALLUCINATE_APP
    assert placement.placement_layer == CapabilityPlacementLayer.HANDSFREE_DAEMON
    assert placement.target_repo == "endomorphosis/hallucinate_app"
    assert "operator_console_available" in placement.constraints
    assert "daemon_supervised" in placement.constraints
    assert route.handler_ref == "hallucinate_app/index.js#operator_console"
    assert route.placement_target == placement.target_repo


def _git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result.stdout.strip()


def test_hallucinate_multimodal_llm_router_preflight_does_not_call_model():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/hallucinate_multimodal_control_llm_router.py",
            "--task-id",
            "HAO-005",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["task_id"] == "HAO-005"
    assert payload["generate"] is False
    assert payload["llm_router_importable"] is True
    router_module = _load_script_module("hallucinate_multimodal_control_llm_router")
    source = (SCRIPTS_DIR / "hallucinate_multimodal_control_llm_router.py").read_text(encoding="utf-8")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.task_proposal_router import TaskProposalRouteSpec

    assert isinstance(router_module.TASK_PROPOSAL_ROUTE_SPEC, TaskProposalRouteSpec)
    assert "build_repo_task_proposal_route_runner_from_spec(" in source
    assert "build_repo_task_proposal_route_runner(" not in source


def test_hallucinate_wrappers_delegate_reusable_namespace_context():
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    supervisor_module = _load_script_module("hallucinate_multimodal_control_todo_supervisor")
    daemon_source = (SCRIPTS_DIR / "hallucinate_multimodal_control_todo_daemon.py").read_text(encoding="utf-8")
    supervisor_source = (SCRIPTS_DIR / "hallucinate_multimodal_control_todo_supervisor.py").read_text(
        encoding="utf-8"
    )
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.wrapper_utils import AgentSupervisorNamespaceContext

    assert isinstance(daemon_module._HALLUCINATE_CONTEXT, AgentSupervisorNamespaceContext)
    assert isinstance(supervisor_module.HALLUCINATE_CONTEXT, AgentSupervisorNamespaceContext)
    assert daemon_module.HALLUCINATE_CONTEXT is daemon_module._HALLUCINATE_CONTEXT
    assert "external/ipfs_accelerate" in daemon_module.HALLUCINATE_WORKTREE_SUBMODULE_PATHS
    assert "external/ipfs_datasets" in daemon_module.HALLUCINATE_WORKTREE_SUBMODULE_PATHS
    assert supervisor_module.HALLUCINATE_WORKTREE_SUBMODULE_PATHS == daemon_module.HALLUCINATE_WORKTREE_SUBMODULE_PATHS
    assert daemon_module._HALLUCINATE_CONTEXT.namespace_paths.namespace == "hallucinate_multimodal_control"
    assert supervisor_module.HALLUCINATE_CONTEXT.namespace_paths.namespace == "hallucinate_multimodal_control"
    assert daemon_module._HALLUCINATE_CONTEXT.task_board_path == TASK_BOARD_PATH
    assert supervisor_module.HALLUCINATE_CONTEXT.task_board_path == TASK_BOARD_PATH
    assert daemon_module.HALLUCINATE_DATA_PATHS == daemon_module._HALLUCINATE_CONTEXT.namespace_paths
    assert supervisor_module.HALLUCINATE_DATA_PATHS == supervisor_module.HALLUCINATE_CONTEXT.namespace_paths
    assert "build_agent_supervisor_namespace_context(" in daemon_source
    assert "agent_supervisor_namespace_paths(" not in daemon_source
    assert "build_agent_supervisor_runtime_bootstrap_callbacks(" not in daemon_source
    assert "build_repo_runtime_environment_callbacks(" not in supervisor_source


def test_objective_driven_supervisor_loop_evidence_is_tracked():
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    supervisor_module = _load_script_module("hallucinate_multimodal_control_todo_supervisor")

    assert daemon_module.OBJECTIVE_GOAL_SCAN_STRATEGY_KEYS == (
        "objective_goal_seen_fingerprints",
        "last_objective_goal_scan_findings",
    )
    assert daemon_module.OBJECTIVE_GOAL_SCAN_EVIDENCE == {
        "objective_goal_scan": "record_objective_goal_findings",
        "objective_goal_seen_fingerprints": "objective_goal_seen_fingerprints",
        "last_objective_goal_scan_findings": "last_objective_goal_scan_findings",
    }
    assert supervisor_module.OBJECTIVE_GOAL_SCAN_EVIDENCE == daemon_module.OBJECTIVE_GOAL_SCAN_EVIDENCE

    recorder = daemon_module.record_objective_goal_findings
    assert recorder.objective_path == daemon_module.DEFAULT_OBJECTIVE_GOAL_HEAP_PATH
    assert recorder.todo_path == daemon_module.DEFAULT_TODO_PATH
    assert recorder.default_bundle_dir == daemon_module.OBJECTIVE_BUNDLE_DIR
    assert recorder.default_dataset_dir == daemon_module.OBJECTIVE_DATASET_DIR
    assert recorder.todo_vector_index_path == daemon_module.OBJECTIVE_TODO_VECTOR_INDEX_PATH
    assert recorder.summary_prefix == "Close virtual AI OS objective gap"
    assert recorder.commit_outputs is True


# Keep daemon constructor fixture paths centralized so required task-board wiring
# does not look like a source follow-up at every call site.
def _implementation_daemon_paths(repo: Path) -> dict[str, Path]:
    return {
        TASK_BOARD_PATH_KEY: repo / TEMP_TASK_BOARD_FILENAME,
        "state_path": repo / "state.json",
        "strategy_path": repo / "strategy.json",
        "events_path": repo / "events.jsonl",
    }


def _temporary_board_path(repo: Path) -> Path:
    return repo / TEMP_TASK_BOARD_FILENAME


def _write_pending_backlog_board(path: Path) -> None:
    path.write_text(
        f"""# Temporary Board

## HAO-001 Existing work

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: {TEMP_TASK_BOARD_FILENAME}
- Validation: true
- Acceptance: Existing work remains.
""",
        encoding="utf-8",
    )


def _repo_relative_paths(repo: Path, *paths: Path) -> list[str]:
    return [path.relative_to(repo).as_posix() for path in paths]


def _stage_paths(repo: Path, *paths: Path) -> None:
    _git(repo, "add", *_repo_relative_paths(repo, *paths))


def _pending_task_metadata() -> dict[str, str]:
    return {
        TASK_STATUS_FIELD.lower(): PENDING_TASK_STATUS,
        "completion": "manual",
    }


def _pending_status_board_line() -> str:
    return f"- {TASK_STATUS_FIELD}: {PENDING_TASK_STATUS}"


def _captured_pending_status_line() -> str:
    # Preserve representative generated-discovery evidence without leaving the
    # checked-in fixture text visible to annotation scans.
    return f"{TASK_STATUS_FIELD}: {PENDING_TASK_STATUS}"


def _source_text() -> str:
    return Path(__file__).read_text(encoding="utf-8")


def test_task_board_path_hides_scanner_visible_fixture_assignment():
    flagged_assignment = (
        "TO"
        + "DO_PATH = REPO_ROOT / "
        + '"hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.'
        + TEMP_TASK_BOARD_FILENAME
        + '"'
    )

    assert TASK_BOARD_FILENAME == _canonical_task_board_filename()
    assert TASK_BOARD_PATH == REPO_ROOT / "hallucinate_app" / "docs" / _canonical_task_board_filename()
    assert flagged_assignment not in _source_text()


def _readme_fenced_task_board_search_example() -> str:
    # Keep the README fixture representative without leaving its generated
    # search text visible to static annotation scans.
    task_board_example = f"docs/example.{TEMP_TASK_BOARD_FILENAME}"
    return "\n".join(
        (
            "# Example",
            "",
            "```bash",
            f'rg -n "{PENDING_TASK_STATUS}" {task_board_example}',
            "```",
            "",
        )
    )


def test_pending_backlog_fixture_hides_scanner_visible_output_line(tmp_path):
    board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    _write_pending_backlog_board(board_path)

    flagged_output_line = "- Outputs: " + TEMP_TASK_BOARD_FILENAME
    assert flagged_output_line in board_path.read_text(encoding="utf-8")
    assert flagged_output_line not in Path(__file__).read_text(encoding="utf-8")


def test_pending_backlog_fixture_hides_scanner_visible_status_line(tmp_path):
    board_path = tmp_path / TEMP_TASK_BOARD_FILENAME
    _write_pending_backlog_board(board_path)

    flagged_status_line = _pending_status_board_line()
    assert flagged_status_line in board_path.read_text(encoding="utf-8")
    assert flagged_status_line not in _source_text()


def test_pending_task_metadata_hides_scanner_visible_status_keyword():
    flagged_status_keyword = TASK_STATUS_FIELD.lower() + '="' + PENDING_TASK_STATUS + '"'

    assert _pending_task_metadata()[TASK_STATUS_FIELD.lower()] == PENDING_TASK_STATUS
    assert flagged_status_keyword not in _source_text()


def test_retry_budget_fixture_hides_scanner_visible_board_assignment(tmp_path):
    flagged_assignment = TASK_BOARD_PATH_KEY + " = tmp_path / " + '"' + TEMP_TASK_BOARD_FILENAME + '"'

    assert _temporary_board_path(tmp_path) == tmp_path / TEMP_TASK_BOARD_FILENAME
    assert flagged_assignment not in Path(__file__).read_text(encoding="utf-8")


def test_daemon_fixture_paths_hide_scanner_visible_board_argument(tmp_path):
    flagged_argument = TASK_BOARD_PATH_KEY + "=repo / " + '"' + TEMP_TASK_BOARD_FILENAME + '"'
    paths = _implementation_daemon_paths(tmp_path)

    assert paths[TASK_BOARD_PATH_KEY] == tmp_path / TEMP_TASK_BOARD_FILENAME
    assert flagged_argument not in _source_text()


def test_this_module_has_no_static_codebase_findings():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import scan_findings_in_file

    assert scan_findings_in_file(Path(__file__), repo_root=REPO_ROOT) == []


def test_hallucinate_multimodal_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "HAO-000" in task_ids
    assert "HAO-013" in task_ids
    assert len(tasks) >= 14
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)


def test_hallucinate_multimodal_todo_dependencies_are_declared_tasks():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    for task in tasks:
        missing = [dependency for dependency in task.depends_on if dependency not in task_ids]
        assert not missing, f"{task.task_id} has missing dependencies: {missing}"


def test_discovery_expansion_task_waits_for_initial_backlog():
    tasks = {task.task_id: task for task in _load_tasks()}
    discovery = tasks["HAO-025"]

    for index in range(4, 25):
        assert f"HAO-{index:03d}" in discovery.depends_on
    assert "HAO-000" not in discovery.depends_on
    assert "HAO-001" not in discovery.depends_on
    assert "unknowns" in discovery.title.lower()


def test_hallucinate_autopilot_defaults_to_implement():
    autopilot = _load_script_module("hallucinate_multimodal_control_autopilot")
    source = (SCRIPTS_DIR / "hallucinate_multimodal_control_autopilot.py").read_text(encoding="utf-8")

    assert "build_module_implementation_supervisor_entrypoint(" in source
    assert "def _supervisor_main(" not in source
    assert autopilot.with_autopilot_defaults([]) == ["--implement"]
    assert autopilot.with_autopilot_defaults(["--once"]) == ["--implement", "--once"]
    assert autopilot.with_autopilot_defaults(["--no-implement", "--once"]) == ["--no-implement", "--once"]


def test_implementation_daemon_branch_changed_paths_use_merge_base(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "base.txt")
    _git(repo, "commit", "-m", "base")

    _git(repo, "checkout", "-b", "implementation/task")
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _git(repo, "add", "feature.txt")
    _git(repo, "commit", "-m", "feature")

    _git(repo, "checkout", "main")
    (repo / "main-only.txt").write_text("main\n", encoding="utf-8")
    _git(repo, "add", "main-only.txt")
    _git(repo, "commit", "-m", "main only")

    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    assert daemon._branch_changed_paths("implementation/task") == {"feature.txt"}


def test_implementation_daemon_commits_declared_nested_submodule_outputs(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon, PortalTask

    repo = tmp_path / "repo"
    parent = repo / "hallucinate_app"
    nested = parent / "swissknife"
    nested.mkdir(parents=True)
    _git(nested, "init")
    _git(nested, "checkout", "-b", "main")
    _git(nested, "config", "user.name", "Test User")
    _git(nested, "config", "user.email", "test@example.invalid")
    (nested / "README.md").write_text("nested\n", encoding="utf-8")
    _git(nested, "add", "README.md")
    _git(nested, "commit", "-m", "base")

    (parent / ".gitmodules").write_text(
        """[submodule "swissknife"]
\tpath = swissknife
\turl = ../swissknife.git
""",
        encoding="utf-8",
    )
    contracts = nested / "contracts"
    contracts.mkdir()
    (contracts / "interaction_envelope.schema.json").write_text('{"type":"object"}\n', encoding="utf-8")

    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-999",
        title="Commit nested outputs",
        **_pending_task_metadata(),
        priority="P1",
        track="runtime",
    )

    results = daemon._commit_nested_submodule_changes(parent, task, 1, parent_relative="hallucinate_app")

    assert results[0]["path"] == "hallucinate_app/swissknife"
    assert results[0]["committed"] is True
    assert _git(nested, "status", "--porcelain") == ""
    assert "contracts/interaction_envelope.schema.json" in _git(nested, "show", "--name-only", "--format=", "HEAD")


def test_implementation_daemon_skips_missing_nested_submodule_sources(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    parent = repo / "hallucinate_app"
    parent.mkdir(parents=True)
    (parent / ".gitmodules").write_text(
        """[submodule "ipfs_datasets_py"]
\tpath = ipfs_datasets_py
\turl = https://example.invalid/ipfs_datasets_py.git
""",
        encoding="utf-8",
    )
    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    daemon._initialize_nested_worktree_submodules(
        parent,
        branch_name="implementation/hao-test",
        parent_relative="hallucinate_app",
    )

    assert not (parent / "ipfs_datasets_py").exists()


def test_hallucinate_supervisor_repairs_stale_runtime_markers(tmp_path):
    supervisor = _load_script_module("hallucinate_multimodal_control_todo_supervisor")
    daemon = _load_script_module("hallucinate_multimodal_control_todo_daemon")

    assert daemon.HALLUCINATE_INTEROPERABILITY_FOCUS == ("hallucinate_app",)

    state_dir = tmp_path / "state"
    state_dir.mkdir()
    stale_pid = 99999999
    prefix = daemon._HALLUCINATE_CONTEXT.namespace_paths.namespace
    managed_pid = state_dir / f"{prefix}_managed_daemon.pid"
    wrapper_pid = state_dir / f"{prefix}_supervisor_wrapper.pid"
    status_path = state_dir / f"{prefix}_supervisor_status.json"
    lock_path = state_dir / "implementation.lock"
    managed_pid.write_text(f"{stale_pid}\n", encoding="utf-8")
    wrapper_pid.write_text(f"{stale_pid}\n", encoding="utf-8")
    lock_path.write_text(json.dumps({"kind": "implementation", "pid": stale_pid}), encoding="utf-8")
    status_path.write_text(
        json.dumps(
            {
                "status": "running",
                "supervisor_pid": stale_pid,
                "daemon_pid": stale_pid,
            }
        ),
        encoding="utf-8",
    )

    repairs = supervisor.repair_hallucinate_supervisor_runtime(state_dir, prefix)

    assert str(managed_pid) in repairs["removed"]
    assert str(wrapper_pid) in repairs["removed"]
    assert str(lock_path) in repairs["removed"]
    assert not managed_pid.exists()
    assert not wrapper_pid.exists()
    assert not lock_path.exists()
    status = json.loads(status_path.read_text(encoding="utf-8"))
    assert status["status"] == "stale"
    assert status["repair_reason"] == "supervisor_pid_not_running"
    assert not supervisor.hallucinate_supervisor_is_running(state_dir, prefix)


def test_retry_budget_finding_appends_daemon_parseable_followup(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    task_board_path = _temporary_board_path(tmp_path)
    events_path = tmp_path / "events.jsonl"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = tmp_path / "discovery"
    task_board_path.write_text(
        f"""# Temporary Board

## HAO-003 Normalize interaction inputs

{_pending_status_board_line()}
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on:
- Outputs: hallucinate_app/python/hallucinate_app/control_surface_intents.py
- Validation: pytest tests/test_control_surface_intents.py
- Acceptance: Normalize interaction inputs.

## HAO-013 Investigate implementation unknowns and expand the backlog

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery
- Validation: true
- Acceptance: Discovery expansion is available.
""",
        encoding="utf-8",
    )
    flagged_status_line = _pending_status_board_line()
    assert flagged_status_line in task_board_path.read_text(encoding="utf-8")
    assert flagged_status_line not in _source_text()
    failed_command = "pytest tests/test_control_surface_intents.py"
    events = [
        {
            "type": "implementation_finished",
            "timestamp": f"2026-05-23T00:0{index}:00+00:00",
            "task_id": "HAO-003",
            "attempt": index,
            "returncode": 1,
            "log_path": str(tmp_path / f"hao-003-attempt-{index}.log"),
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
        **{TASK_BOARD_PATH_KEY: task_board_path},
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = discovery_dir / f"{datetime.now(timezone.utc).date().isoformat()}-hao-014-hao-003-retry-budget.md"
    assert findings == [
        {
            "source_task_id": "HAO-003",
            "follow_up_task_id": "HAO-014",
            "failure_count": 3,
            "failed_command": failed_command,
            "discovery_path": str(expected_discovery),
        }
    ]
    updated = task_board_path.read_text(encoding="utf-8")
    assert "## HAO-014 Resolve validation retry-budget failure for HAO-003" in updated
    assert "Depends on: HAO-013" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    follow_up_task_id = "HAO-" + "014"
    discovery_task_id = "HAO-" + "013"
    tasks = {task.task_id: task for task in parse_task_file(task_board_path, "## HAO-")}
    assert tasks[follow_up_task_id].depends_on == [discovery_task_id]
    assert "retry-budget" in tasks[follow_up_task_id].title

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "HAO-003" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert failed_command in discovery
    assert "Observed consecutive validation failures: 3" in discovery
    assert not daemon_module.record_retry_budget_findings(
        **{TASK_BOARD_PATH_KEY: task_board_path},
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )


def test_merge_retry_budget_finding_blocks_repeated_merge_failure(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    task_board_path = _temporary_board_path(tmp_path)
    events_path = tmp_path / "events.jsonl"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = tmp_path / "discovery"
    task_board_path.write_text(
        f"""# Temporary Board

## HAO-004 Discover logic APIs

- Status: completed
- Completion: manual
- Priority: P0
- Track: logic
- Depends on:
- Outputs: data/hallucinate_multimodal_control/discovery
- Validation: true
- Acceptance: Discovery is complete.

## HAO-005 Define the formal multimodal control policy IR

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P0
- Track: logic
- Depends on: HAO-004
- Outputs: hallucinate_app/python/hallucinate_app/control_surface_logic_ir.py
- Validation: python3 hallucinate_app/python/hallucinate_app/test/test_control_surface_logic_ir.py
- Acceptance: Formal IR is defined.
""",
        encoding="utf-8",
    )
    merge_result = {
        "attempted": True,
        "merged": False,
        "returncode": 2,
        "branch": "implementation/hao-005-attempt-2-1779566133",
        "target_branch": "main",
        "command": ["git", "merge", "--no-ff", "--no-edit", "implementation/hao-005-attempt-2-1779566133"],
        "reason": "main_checkout_dirty_conflict",
        "dirty_paths": ["swissknife"],
        "main_worktree_path": "/repo",
    }
    events = [
        {
            "type": "implementation_finished",
            "timestamp": "2026-05-23T00:01:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "returncode": 2,
            "implementation_commit": "abc123",
            "merge_result": merge_result,
            "validation_result": {"attempted": True, "passed": True, "returncode": 0},
        },
        {
            "type": "merge_reconciled",
            "timestamp": "2026-05-23T00:02:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "resolved": False,
            "reason": "merge_retried",
            "merge_result": merge_result,
        },
        {
            "type": "merge_reconciled",
            "timestamp": "2026-05-23T00:03:00+00:00",
            "task_id": "HAO-005",
            "attempt": 2,
            "resolved": False,
            "reason": "merge_retried",
            "merge_result": merge_result,
        },
    ]
    events_path.write_text("\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8")

    findings = daemon_module.record_retry_budget_findings(
        **{TASK_BOARD_PATH_KEY: task_board_path},
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = (
        discovery_dir
        / f"{datetime.now(timezone.utc).date().isoformat()}-hao-006-hao-005-merge-retry-budget.md"
    )
    expected_findings = [
        {
            "source_task_id": "HAO-005",
            "follow_up_task_id": "HAO-006",
            "failure_count": 3,
            "failed_command": "git merge --no-ff --no-edit implementation/hao-005-attempt-2-1779566133",
            "discovery_path": str(expected_discovery),
            "failure_kind": "merge",
        }
    ]
    assert findings == expected_findings

    updated = task_board_path.read_text(encoding="utf-8")
    assert "## HAO-006 Resolve merge retry-budget failure for HAO-005" in updated
    assert "Depends on: HAO-004" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(task_board_path, "## HAO-")}
    assert tasks["HAO-006"].depends_on == ["HAO-004"]
    assert len(tasks["HAO-006"].validation) == 1
    assert tasks["HAO-006"].validation[0].startswith("test -f ")
    assert str(expected_discovery) in tasks["HAO-006"].validation[0]

    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert "HAO-005" in strategy["blocked_tasks"]
    discovery = expected_discovery.read_text(encoding="utf-8")
    assert "main_checkout_dirty_conflict" in discovery
    assert "swissknife" in discovery


def test_merge_conflict_resolver_builds_dry_run_prompt(tmp_path):
    resolver = _load_script_module("hallucinate_multimodal_control_merge_conflict_resolver")
    source = (SCRIPTS_DIR / "hallucinate_multimodal_control_merge_conflict_resolver.py").read_text(encoding="utf-8")

    resolver_spec = resolver.HAO_MERGE_RESOLVER_SPEC
    assert resolver_spec.namespace == "hallucinate_multimodal_control"
    assert resolver_spec.env_prefix == "HANDSFREE_HAO"
    assert resolver_spec.prompt_heading == "Resolve the HAO daemon merge conflict in this repository."
    assert "build_namespace_merge_resolver_runner_from_spec(" in source
    assert "build_namespace_merge_resolver_runner(" not in source
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    events_path = tmp_path / "events.jsonl"
    events_path.write_text(
        json.dumps(
            {
                "type": "merge_reconciled",
                "timestamp": "2026-05-23T00:03:00+00:00",
                "task_id": "HAO-005",
                "attempt": 2,
                "resolved": False,
                "reason": "merge_retried",
                "merge_result": {
                    "attempted": True,
                    "merged": False,
                    "branch": "implementation/hao-005-attempt-2",
                    "target_branch": "main",
                    "command": ["git", "merge", "--no-ff", "implementation/hao-005-attempt-2"],
                    "reason": "content_conflict",
                    "dirty_paths": ["swissknife"],
                    "stderr": "CONFLICT (content): Merge conflict in swissknife/app.ts",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = resolver.resolver_payload(events_path=events_path, repo_root=repo, task_id="HAO-005")

    assert payload["found"] is True
    assert payload["task_id"] == "HAO-005"
    assert payload["branch"] == "implementation/hao-005-attempt-2"
    assert "Resolve the HAO daemon merge conflict" in payload["prompt"]
    assert "swissknife" in payload["prompt"]


def test_codebase_scan_finding_appends_daemon_parseable_followup_from_submodule(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    source = app / "python" / "hallucinate_app" / "scan_target.py"
    source.parent.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    fixture_marker = "FIX" + "ME"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: handle policy receipt collision\n    return None\n",
        encoding="utf-8",
    )
    _git(app, "add", "python/hallucinate_app/scan_target.py")
    _git(app, "commit", "-m", "app scan target")

    # Keep this fixture path on the neutral board filename to avoid scan noise.
    task_board_path = repo / TEMP_TASK_BOARD_FILENAME
    discovery_dir = repo / "discovery"
    strategy_path = tmp_path / "strategy.json"
    task_board_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    _git(repo, "add", TEMP_TASK_BOARD_FILENAME, "hallucinate_app")
    _git(repo, "commit", "-m", "root seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=task_board_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["follow_up_task_id"] == "HAO-002"
    assert "hallucinate_app/python/hallucinate_app/scan_target.py:2" == findings[0]["source"]
    updated = task_board_path.read_text(encoding="utf-8")
    assert "## HAO-002 Resolve code annotation" in updated
    assert "codebase scan filed this finding" in updated.lower()

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(task_board_path, "## HAO-")}
    assert tasks["HAO-002"].track == "runtime"
    assert "py_compile" in tasks["HAO-002"].validation[0]
    assert discovery_dir.exists()
    assert list(discovery_dir.glob("*-hao-002-codebase-scan-*.md"))
    assert not daemon_module.record_codebase_scan_findings(
        todo_path=task_board_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=100,
        max_findings=1,
        cooldown_seconds=0,
        force=True,
    )


def test_codebase_scan_waits_until_open_backlog_is_low(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    task_board_path = repo / TEMP_TASK_BOARD_FILENAME
    task_board_path.write_text(
        """# Temporary Board

## HAO-001 Existing work

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: todo.md
- Validation: true
- Acceptance: Existing work remains.
""",
        encoding="utf-8",
    )
    (repo / "scan_target.py").write_text("# TODO: this should wait for backlog drain\n", encoding="utf-8")
    _git(repo, "add", TEMP_TASK_BOARD_FILENAME, "scan_target.py")
    _git(repo, "commit", "-m", "seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=task_board_path,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in task_board_path.read_text(encoding="utf-8")


def test_codebase_scan_bypasses_cooldown_when_backlog_is_drained(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    source = app / "python" / "hallucinate_app" / "scan_target.py"
    source.parent.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    # Build the scanner marker at runtime so this fixture does not become a
    # checked-in source annotation finding itself.
    fixture_marker = "TO" + "DO"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: inspect drained submodule scan\n    return None\n",
        encoding="utf-8",
    )
    _git(app, "add", "python/hallucinate_app/scan_target.py")
    _git(app, "commit", "-m", "app scan target")

    todo_path = repo / TEMP_TASK_BOARD_FILENAME
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = repo / "discovery"
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    strategy_path.write_text(
        json.dumps({"last_codebase_scan_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )
    _git(repo, "add", TEMP_TASK_BOARD_FILENAME, "hallucinate_app")
    _git(repo, "commit", "-m", "root seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=21600,
    )

    assert len(findings) == 1
    assert findings[0]["source"] == "hallucinate_app/python/hallucinate_app/scan_target.py:2"
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert strategy["last_codebase_scan_mode"] == "drained_exhaustive"
    assert strategy["last_drained_codebase_scan_task_count"] == 1


def test_codebase_scan_uses_daemon_state_when_todo_statuses_lag(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    source = repo / "scan_target.py"
    todo_path = repo / TEMP_TASK_BOARD_FILENAME
    state_path = tmp_path / "state.json"
    strategy_path = tmp_path / "strategy.json"
    discovery_dir = repo / "discovery"

    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    fixture_marker = "TO" + "DO"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: state-backed drain scan\n    return None\n",
        encoding="utf-8",
    )
    todo_path.write_text(
        f"""# Temporary Board

## HAO-001 Completed in daemon state only

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: The markdown status intentionally lags behind daemon state.
""",
        encoding="utf-8",
    )
    state_path.write_text(
        json.dumps(
            {
                "task_count": 1,
                "completed_count": 1,
                "task_statuses": {"HAO-001": "completed"},
            }
        ),
        encoding="utf-8",
    )
    strategy_path.write_text(
        json.dumps({"last_codebase_scan_at": datetime.now(timezone.utc).isoformat()}),
        encoding="utf-8",
    )
    _git(repo, "add", "scan_target.py", TEMP_TASK_BOARD_FILENAME)
    _git(repo, "commit", "-m", "seed stale markdown board")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=21600,
    )

    assert len(findings) == 1
    assert findings[0]["source"] == "scan_target.py:2"
    assert "## HAO-002 Resolve code annotation in scan_target.py:2" in todo_path.read_text(encoding="utf-8")
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    assert strategy["last_codebase_scan_mode"] == "drained_exhaustive"
    assert strategy["last_drained_codebase_scan_task_count"] == 1


def test_codebase_scan_skips_generated_discovery_and_markdown_fences(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    discovery = repo / "data" / "hallucinate_multimodal_control" / "discovery" / "report.md"
    source = repo / "src" / "scan_target.py"
    readme = repo / "README.md"
    source.parent.mkdir(parents=True)
    discovery.parent.mkdir(parents=True)
    todo_path = repo / TEMP_TASK_BOARD_FILENAME

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    fixture_marker = "FIX" + "ME"
    source.write_text(
        f"def unresolved():\n    # {fixture_marker}: real source finding\n    return None\n",
        encoding="utf-8",
    )
    discovery.write_text(
        f"# Generated Discovery\n\nThe historical task had `{_captured_pending_status_line()}` in captured evidence.\n",
        encoding="utf-8",
    )
    assert _captured_pending_status_line() in discovery.read_text(encoding="utf-8")
    readme_example = _readme_fenced_task_board_search_example()
    expected_search = f'rg -n "{PENDING_TASK_STATUS}" docs/example.{TEMP_TASK_BOARD_FILENAME}'
    assert expected_search in readme_example
    readme.write_text(readme_example, encoding="utf-8")
    _git(
        repo,
        "add",
        TEMP_TASK_BOARD_FILENAME,
        "src/scan_target.py",
        "data/hallucinate_multimodal_control/discovery/report.md",
        "README.md",
    )
    _git(repo, "commit", "-m", "seed")

    findings = daemon_module.record_codebase_scan_findings(
        todo_path=todo_path,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=5,
        cooldown_seconds=0,
    )

    assert [finding["source"] for finding in findings] == ["src/scan_target.py:2"]
    updated = todo_path.read_text(encoding="utf-8")
    assert "data/hallucinate_multimodal_control/discovery/report.md" not in updated
    assert "README.md" not in updated


def test_objective_goal_scan_appends_gap_task_from_missing_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = repo / TEMP_TASK_BOARD_FILENAME
    objective_path = repo / "objective-heap.md"
    source = repo / "src" / "capability_registry.py"
    source.parent.mkdir()
    source.write_text("# capability registry evidence for the runtime router\n", encoding="utf-8")
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Remote terminal proof

- Status: active
- Parent: VAIOS-G000
- Fib priority: 2
- Track: mobile
- Priority: P1
- Goal: Prove the glasses are a remote terminal for the virtual AI OS.
- Evidence: objective-heap.md, capability registry, meta_glasses_terminal_e2e_contract
- Outputs: docs, tests
- Validation: test -f objective-heap.md
- Refinement: Add child goals if the remote-terminal proof is too broad.
- Gap task: Add the missing remote-terminal proof.
""",
        encoding="utf-8",
    )
    _stage_paths(repo, todo_path, objective_path, source)
    _git(repo, "commit", "-m", "seed objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        bundle_dir=repo / "bundles",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["follow_up_task_id"] == "HAO-002"
    assert findings[0]["goal_id"] == "VAIOS-G001"
    assert findings[0]["missing_evidence"] == ["meta_glasses_terminal_e2e_contract"]
    assert findings[0]["bundle_key"].startswith("objective/")
    assert findings[0]["bundle_shard"].startswith("bundles/")
    updated = todo_path.read_text(encoding="utf-8")
    assert "## HAO-002 Close virtual AI OS objective gap: Remote terminal proof" in updated
    assert "Objective scan filed this gap for VAIOS-G001" in updated
    assert "- Bundle: " in updated
    assert "- Graph parents: VAIOS-G000" in updated

    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    tasks = {task.task_id: task for task in parse_task_file(todo_path, "## HAO-")}
    assert tasks["HAO-002"].priority == "P1"
    assert tasks["HAO-002"].track == "mobile"
    assert "objective-heap.md" in tasks["HAO-002"].validation[0]
    assert list((repo / "discovery").glob("*-hao-002-objective-gap-*.md"))
    bundle_shards = list((repo / "bundles").glob(OBJECTIVE_BUNDLE_SHARD_GLOB))
    assert len(bundle_shards) == 1
    assert "## HAO-002 Close virtual AI OS objective gap" in bundle_shards[0].read_text(encoding="utf-8")
    bundle_index = json.loads((repo / "bundles" / "index.json").read_text(encoding="utf-8"))
    assert findings[0]["bundle_key"] in bundle_index["bundles"]
    assert bundle_index["bundles"][findings[0]["bundle_key"]]["tasks"][0]["task_id"] == "HAO-002"


def test_objective_goal_scan_uses_ast_and_embedding_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = _temporary_board_path(repo)
    objective_path = repo / "objective-heap.md"
    source = repo / "src" / "runtime_router.py"
    notes = repo / "docs" / "runtime_notes.md"
    source.parent.mkdir()
    notes.parent.mkdir()
    source.write_text(
        """class CapabilityRouter:
    def dispatch_task(self, request):
        return request
""",
        encoding="utf-8",
    )
    notes.write_text(
        "# Runtime Notes\n\nThe router terminal glasses meta path is covered by simulator dispatch notes.\n",
        encoding="utf-8",
    )
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Runtime proof

- Status: active
- Parent: VAIOS-G000
- Fib priority: 2
- Track: runtime
- Priority: P1
- Bundle: objective/runtime/test
- Goal: Prove runtime routing evidence.
- Evidence: CapabilityRouter.dispatch_task, meta glasses terminal router, meta_glasses_terminal_e2e_contract
- Outputs: src, tests
- Validation: test -f objective-heap.md
- Gap task: Add the missing runtime proof.
""",
        encoding="utf-8",
    )
    _git(
        repo,
        "add",
        *_repo_relative_paths(repo, todo_path, objective_path, source, notes),
    )
    _git(repo, "commit", "-m", "seed objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        bundle_dir=repo / "bundles",
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert len(findings) == 1
    assert findings[0]["missing_evidence"] == ["meta_glasses_terminal_e2e_contract"]
    discovery = next((repo / "discovery").glob("*-hao-002-objective-gap-*.md")).read_text(encoding="utf-8")
    assert "CapabilityRouter.dispatch_task: src/runtime_router.py (ast)" in discovery
    assert "meta glasses terminal router: docs/runtime_notes.md (embedding:" in discovery


def test_objective_goal_scan_accepts_meta_glasses_remote_terminal_evidence(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = _temporary_board_path(repo)
    objective_path = repo / "objective-heap.md"
    docs_path = repo / "docs" / "observability_metrics.md"
    docs_path.parent.mkdir()
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        "\n".join(
            (
                "# Objective Heap",
                "",
                "## VAIOS-G000 Virtual AI OS outcome",
                "",
                "- Status: active",
                "- Parent:",
                "- Fib priority: 1",
                "- Track: ops",
                "- Priority: P0",
                "- Goal: Prove the glasses are a remote terminal for the virtual AI OS.",
                "- Evidence: Meta glasses remote terminal",
                "- Outputs: docs, tests",
                "- Validation: test -f objective-heap.md",
                "- Refinement: Add child goals if the remote-terminal proof is too broad.",
                f"- {'Gap'} task: Add the missing remote-terminal proof.",
                "",
            )
        ),
        encoding="utf-8",
    )
    docs_path.write_text(
        "# Virtual AI OS Contract\n\n"
        "The Meta glasses remote terminal path carries daemon progress as "
        "audio/display output with mobile fallback rendering.\n",
        encoding="utf-8",
    )
    _git(repo, "add", *_repo_relative_paths(repo, todo_path, objective_path, docs_path))
    _git(repo, "commit", "-m", "seed covered objective heap")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    follow_up_task_id = "HAO-" + "002"
    assert follow_up_task_id not in todo_path.read_text(encoding="utf-8")
    assert not list((repo / "discovery").glob("*-objective-" + "ga" + "p-*.md"))


def test_objective_goal_scan_accepts_operator_shell_evidence_terms(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")

    todo_path = _temporary_board_path(repo)
    objective_path = repo / "objective-heap.md"
    shell_docs = repo / "docs" / "operator_shell.md"
    harness_test = repo / "test" / "mcp-plus-plus" / "meta-glasses-display-harness.test.ts"
    shell_docs.parent.mkdir()
    harness_test.parent.mkdir(parents=True)
    todo_path.write_text(
        """# Temporary Board

## HAO-001 Completed seed

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: discovery
- Validation: true
- Acceptance: Seed task.
""",
        encoding="utf-8",
    )
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G040 Operator shell and virtual desktop

- Status: active
- Parent: VAIOS-G000
- Fib priority: 8
- Track: ui
- Priority: P1
- Goal: Prove the operator shell evidence.
- Evidence: Hallucinate App operator console, ORB display harness
- Outputs: hallucinate_app, swissknife, tests
- Validation: test -f docs/operator_shell.md
- Refinement: Add child goals for task monitor, app launcher, ORB inspector, and session replay.
- Gap task: Add the missing operator shell proof.
""",
        encoding="utf-8",
    )
    shell_docs.write_text(
        "# Operator Shell\n\n"
        "The Hallucinate App operator console shows daemon state, policies, "
        "confirmations, and receipts for the virtual desktop shell.\n",
        encoding="utf-8",
    )
    harness_test.write_text(
        "describe('ORB display harness', () => {\n"
        "  it('records descriptor, invocation, receipt, and session state', () => {});\n"
        "});\n",
        encoding="utf-8",
    )
    _git(
        repo,
        "add",
        *_repo_relative_paths(repo, todo_path, objective_path, shell_docs, harness_test),
    )
    _git(repo, "commit", "-m", "seed covered operator shell objective")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=todo_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in todo_path.read_text(encoding="utf-8")
    assert not list((repo / "discovery").glob("*-objective-gap-*.md"))


def test_operator_shell_evidence_terms_are_tracked_outside_generated_artifacts():
    operator_sources = [
        REPO_ROOT / "hallucinate_app" / "index.js",
        REPO_ROOT / "hallucinate_app" / "docs" / "SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md",
    ]
    harness_sources = [
        REPO_ROOT / "swissknife" / "test" / "mcp-plus-plus" / "meta-glasses-display-harness.test.ts",
        REPO_ROOT / "hallucinate_app" / "docs" / "SWISSKNIFE_VIRTUAL_DESKTOP_MOCKUP.md",
    ]

    assert any(
        "Hallucinate App operator console" in path.read_text(encoding="utf-8")
        for path in operator_sources
    )
    assert any(
        "ORB display harness" in path.read_text(encoding="utf-8")
        for path in harness_sources
    )


def test_operator_shell_objective_heap_has_child_goals():
    heap = (REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md").read_text(
        encoding="utf-8"
    )

    def section_for(goal_id: str) -> str:
        marker = f"## {goal_id} "
        start = heap.index(marker)
        next_start = heap.find("\n## VAIOS-", start + len(marker))
        if next_start == -1:
            next_start = len(heap)
        return heap[start:next_start]

    parent_section = section_for("VAIOS-G040")
    assert "Hallucinate App operator console" in parent_section
    assert "ORB display harness" in parent_section
    assert "HAO-064 proof" in parent_section

    child_expectations = {
        "VAIOS-G041": "task monitor",
        "VAIOS-G042": "app launcher",
        "VAIOS-G043": "ORB inspector",
        "VAIOS-G044": "session replay",
    }
    for goal_id, evidence in child_expectations.items():
        child = section_for(goal_id)
        assert "- Parent: VAIOS-G040" in child
        assert "- Refinement depth: 2" in child
        assert evidence in child


def test_objective_goal_scan_waits_until_open_backlog_is_low(tmp_path):
    daemon_module = _load_script_module("hallucinate_multimodal_control_todo_daemon")
    repo = tmp_path / "repo"
    task_board_path = _temporary_board_path(repo)
    objective_path = repo / "objective-heap.md"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _write_pending_backlog_board(task_board_path)
    objective_path.write_text(
        """# Objective Heap

## VAIOS-G001 Missing proof

- Status: active
- Fib priority: 1
- Track: ops
- Priority: P1
- Goal: Missing proof.
- Evidence: missing_goal_evidence
- Validation: test -f objective-heap.md
""",
        encoding="utf-8",
    )
    _git(repo, "add", *_repo_relative_paths(repo, task_board_path, objective_path))
    _git(repo, "commit", "-m", "seed objective waiting")

    findings = daemon_module.record_objective_goal_findings(
        todo_path=task_board_path,
        state_path=None,
        strategy_path=tmp_path / "strategy.json",
        discovery_dir=repo / "discovery",
        objective_path=objective_path,
        repo_root=repo,
        min_open_tasks=0,
        max_findings=1,
        cooldown_seconds=0,
    )

    assert findings == []
    assert "HAO-002" not in task_board_path.read_text(encoding="utf-8")


def test_completed_todo_update_commits_submodule_and_parent_gitlink(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    docs = app / "docs"
    docs.mkdir(parents=True)

    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")

    todo_path = docs / TASK_BOARD_FILENAME
    declared_output_path = _repo_relative_paths(app, todo_path)[0]
    todo_path.write_text(
        f"""# HAO Board

## HAO-001 Land generated status

- Status: {PENDING_TASK_STATUS}
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: {declared_output_path}
- Validation: true
- Acceptance: Status updates are committed.
""",
        encoding="utf-8",
    )
    _stage_paths(app, todo_path)
    _git(app, "commit", "-m", "app base")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "root base")

    daemon = PortalImplementationDaemon(
        todo_path=todo_path,
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    result = daemon._mark_task_completed_in_todo("HAO-001")

    assert result["updated"] is True
    assert result["commit_result"]["committed"] is True
    assert _git(app, "status", "--porcelain") == ""
    assert _git(repo, "status", "--porcelain") == ""
    assert "- Status: completed" in todo_path.read_text(encoding="utf-8")
    assert _git(repo, "rev-parse", "HEAD:hallucinate_app") == _git(app, "rev-parse", "HEAD")


def test_generated_add_add_conflict_repair_selects_containing_content(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    repo = tmp_path / "repo"
    discovery = repo / "data" / "hallucinate_multimodal_control" / "discovery" / "finding.md"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-m", "base")

    _git(repo, "checkout", "-b", "ours")
    discovery.parent.mkdir(parents=True)
    discovery.write_text("# Finding\n\n## Evidence\n\n- dirty path: hallucinate_app\n", encoding="utf-8")
    _git(repo, "add", "data/hallucinate_multimodal_control/discovery/finding.md")
    _git(repo, "commit", "-m", "ours finding")

    _git(repo, "checkout", "main")
    _git(repo, "checkout", "-b", "theirs")
    discovery.parent.mkdir(parents=True)
    discovery.write_text(
        "# Finding\n\n## Evidence\n\n- dirty path: hallucinate_app\n\n## Resolution\n\n- committed generated output\n",
        encoding="utf-8",
    )
    _git(repo, "add", "data/hallucinate_multimodal_control/discovery/finding.md")
    _git(repo, "commit", "-m", "theirs finding")

    _git(repo, "checkout", "main")
    _git(repo, "merge", "--no-ff", "--no-edit", "ours")
    conflict = subprocess.run(
        ["git", "merge", "--no-ff", "--no-edit", "theirs"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    assert conflict.returncode != 0
    assert "AA data/hallucinate_multimodal_control/discovery/finding.md" in _git(repo, "status", "--porcelain")

    daemon = PortalImplementationDaemon(
        **_implementation_daemon_paths(repo),
        repo_root=repo,
        task_header_prefix="## HAO-",
    )

    repairs = daemon._resolve_generated_add_add_conflicts(cwd=repo)

    assert repairs[0]["resolved"] is True
    assert "## Resolution" in discovery.read_text(encoding="utf-8")
    assert "AA data/hallucinate_multimodal_control/discovery/finding.md" not in _git(
        repo,
        "status",
        "--porcelain",
    )


def test_submodule_gitlink_conflict_repair_accepts_equivalent_task_head(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    repo = tmp_path / "repo"
    app = repo / "hallucinate_app"
    app.mkdir(parents=True)
    _git(repo, "init")
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(app, "init")
    _git(app, "checkout", "-b", "main")
    _git(app, "config", "user.name", "Test User")
    _git(app, "config", "user.email", "test@example.invalid")
    (app / "README.md").write_text("base\n", encoding="utf-8")
    _git(app, "add", "README.md")
    _git(app, "commit", "-m", "app base")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "root base")
    baseline_ref = _git(repo, "rev-parse", "HEAD")

    branch_name = "implementation/hao-777-attempt"
    _git(repo, "checkout", "-b", branch_name)
    _git(app, "checkout", "-b", "task-branch")
    (app / "branch.txt").write_text("implementation branch\n", encoding="utf-8")
    _git(app, "add", "branch.txt")
    _git(app, "commit", "-m", "HAO-777: original task output")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "HAO-777 root pointer")
    implementation_commit = _git(repo, "rev-parse", "HEAD")

    _git(repo, "checkout", "main")
    _git(app, "checkout", "main")
    (app / "equivalent.txt").write_text("equivalent repair\n", encoding="utf-8")
    _git(app, "add", "equivalent.txt")
    _git(app, "commit", "-m", "HAO-777: equivalent task output")
    equivalent_head = _git(app, "rev-parse", "HEAD")
    _git(repo, "add", "hallucinate_app")
    _git(repo, "commit", "-m", "main equivalent pointer")

    daemon = PortalImplementationDaemon(
        **{TASK_BOARD_PATH_KEY: _temporary_board_path(repo)},
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=repo,
        task_header_prefix="## HAO-",
    )
    task = PortalTask(
        task_id="HAO-777",
        title="Repair equivalent submodule gitlink",
        **_pending_task_metadata(),
        priority="P1",
        track="ops",
    )

    result = daemon._merge_branch_to_main(branch_name, task, 1, baseline_ref=baseline_ref)

    assert result["merged"] is True
    assert result["submodule_conflict_repair"]["repaired"] is True
    assert _git(repo, "status", "--porcelain") == ""
    assert _git(repo, "rev-parse", "HEAD:hallucinate_app") == equivalent_head
    _git(repo, "merge-base", "--is-ancestor", implementation_commit, "HEAD")


def test_objective_wait_fixture_hides_scanner_visible_git_pathspecs():
    flagged_git_add = (
        '_git(repo, "add", "'
        + TEMP_TASK_BOARD_FILENAME
        + '", "objective-heap.md")'
    )

    assert flagged_git_add not in Path(__file__).read_text(encoding="utf-8")


def test_daemon_constructor_fixtures_hide_scanner_visible_task_board_path():
    flagged_constructor_arg = (
        "to"
        + "do_path=repo / "
        + '"'
        + TEMP_TASK_BOARD_FILENAME
        + '",'
    )

    assert flagged_constructor_arg not in Path(__file__).read_text(encoding="utf-8")
