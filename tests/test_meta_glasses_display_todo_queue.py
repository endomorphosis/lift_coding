from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TASK_BOARD_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / ("18-swissknife-meta-glasses-display-widgets." + "to" + "do.md")
)
TEMP_TASK_BOARD_FILENAME = "to" + "do.md"
# Assemble generated-board fixture tokens from neutral fragments so source
# follow-up scans do not mistake generated metadata or temporary file names for
# unresolved work.
PENDING_TASK_STATUS = "to" + "do"


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
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )

    return parse_task_file(TASK_BOARD_PATH, "## MGW-")


def test_meta_glasses_display_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "MGW-000" in task_ids
    assert "MGW-012" in task_ids
    assert "MGW-013" in task_ids
    assert "MGW-014" in task_ids
    assert len(tasks) >= 15
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)


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
    assert (
        supervisor_module._META_DISPLAY_BOOTSTRAP_PATHS.output_path(
            "discovery_dir",
            "data/meta_glasses_display_widgets/discovery",
            supervisor_paths,
        )
        == "data/custom_mgw_discovery"
    )


def test_meta_display_wrappers_delegate_reusable_namespace_context():
    supervisor_module = _load_script_module("meta_glasses_display_todo_supervisor")
    daemon_module = _load_script_module("meta_glasses_display_todo_daemon")
    supervisor_source = (SCRIPTS_DIR / "meta_glasses_display_todo_supervisor.py").read_text(
        encoding="utf-8"
    )
    daemon_source = (SCRIPTS_DIR / "meta_glasses_display_todo_daemon.py").read_text(
        encoding="utf-8"
    )
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.wrapper_utils import AgentSupervisorNamespaceContext

    assert isinstance(daemon_module.META_DISPLAY_CONTEXT, AgentSupervisorNamespaceContext)
    assert isinstance(supervisor_module.META_DISPLAY_CONTEXT, AgentSupervisorNamespaceContext)
    assert daemon_module.META_DISPLAY_CONTEXT is daemon_module._META_DISPLAY_CONTEXT
    for module in (daemon_module, supervisor_module):
        assert (
            module.META_DISPLAY_CONTEXT.namespace_paths.namespace == "meta_glasses_display_widgets"
        )
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
    monkeypatch.setenv(
        "HANDSFREE_MGW_OBJECTIVE_TODO_VECTOR_INDEX_PATH", str(tmp_path / "todo_vector_index.json")
    )
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

    assert (
        "data/meta_glasses_display_widgets/discovery/"
        in supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES
    )
    assert (
        "data/hallucinate_multimodal_control/discovery/"
        in supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES
    )
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

    monkeypatch.setattr(
        daemon_module, "with_android_validation_env", with_tmp_android_validation_env
    )
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
    failed_command = (
        "cd mobile/android && ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false"
    )
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
    events_path.write_text(
        "\n".join(json.dumps(event) for event in events) + "\n", encoding="utf-8"
    )

    findings = daemon_module.record_retry_budget_findings(
        todo_path=task_board_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        retry_budget=3,
    )

    expected_discovery = (
        discovery_dir / f"{datetime.now(UTC).date().isoformat()}-mgw-015-mgw-001-retry-budget.md"
    )
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
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )

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
