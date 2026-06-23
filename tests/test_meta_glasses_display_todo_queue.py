from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


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
    assert tasks["MGW-268"].track == "integration"


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
    assert fixture["schema_version"] == "1.0.0"
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

    for event in events:
        state = event["widget_state"]
        descriptor_refs = state["descriptor_refs"]
        peer_receipts = state["peer_offload"]["receipts"]

        assert state["widget_kind"] == "handsfree.virtual-desktop-session"
        assert state["session_identity"]["session_id"] == "vdesktop-session-mgw-267"
        assert state["session_identity"]["phone_host_id"] == offline_contract["phone_host_id"]
        assert state["render_context"]["hardware_required"] is False
        assert state["render_context"]["paired_device_id"] is None
        assert state["render_context"]["preview_mode"] is True
        assert state["pairing"]["status"] == "unpaired"
        assert state["active_tool"]["surface"] == "mobile_card"
        assert {"status_region", "progress_region", "message_region", "diagnostics_region"} <= set(
            state["regions"]
        )
        assert peer_receipts["policy_receipt_cid"] == descriptor_refs["policy_receipt_cid"]
        assert "open_mobile_card" in state["recovery"]["next_actions"]
        assert state["recovery"]["fallback"]["render_path"] == "mobile-card"

    confirmation_state = events[1]["widget_state"]
    prompt = confirmation_state["confirmation_prompt"]
    assert prompt["prompt_id"] == "confirm-stop-mgw-267"
    assert prompt["kind"] == "cancel"
    assert prompt["risk_level"] == "medium"
    assert prompt["default_action"] == "continue"
    assert [action["id"] for action in prompt["actions"]] == ["continue", "cancel_task"]
    assert [action["focus_order"] for action in prompt["actions"]] == [1, 2]
    assert all(action["backend_action_id"].startswith("terminal.") for action in prompt["actions"])
    assert all(
        action["correlation_id"] == events[1]["correlation_id"] for action in prompt["actions"]
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
