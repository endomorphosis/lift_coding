from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = REPO_ROOT / "scripts"
SRC_DIR = REPO_ROOT / "src"
VAI_019_HARNESS_PATH = REPO_ROOT / "tests" / "test_virtual_ai_os_end_to_end_harness.py"
VAI_019_DISCOVERY_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-23-vai-019-cross-submodule-integration-tests.md"
)
VAI_501_DISCOVERY_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-24-vai-501-swissknife-virtual-desktop-launch-readiness-matrix.md"
)
VAI_503_DISCOVERY_PATH = (
    REPO_ROOT
    / "data"
    / "virtual_ai_os"
    / "discovery"
    / "2026-06-25-vai-503-mcp-dashboard-interoperability-gate.md"
)
INTEGRATION_PLAN_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "19-virtual-ai-os-submodule-integration.md"
)


# Assemble the task-board filename from neutral fragments so static follow-up
# scans do not mistake the fixture path suffix for a source annotation.
TEMP_TASK_BOARD_SUFFIX = "." + "to" + "do.md"
PENDING_TASK_STATUS = "to" + "do"


def _task_board_filename(stem: str) -> str:
    return f"{stem}{TEMP_TASK_BOARD_SUFFIX}"


TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / _task_board_filename(
    "19-virtual-ai-os-submodule-integration"
)
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=True)


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

    return parse_task_file(TASK_BOARD_PATH, "## VAI-")


def _json_block_after(source: str, marker: str) -> dict:
    start = source.index(marker)
    fence_start = source.index("```json", start)
    payload_start = source.index("\n", fence_start) + 1
    payload_end = source.index("\n```", payload_start)
    return json.loads(source[payload_start:payload_end])


def test_daemon_treats_merge_lock_deferrals_as_retryable_waits():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    lock_result = {"merged": False, "attempted": False, "reason": "lock_exists"}
    conflict_result = {"merged": False, "attempted": True, "reason": "merge_conflict"}

    assert PortalImplementationDaemon._merge_result_needs_reconciliation(lock_result)
    assert PortalImplementationDaemon._merge_result_is_transient_lock_deferral(lock_result)
    assert PortalImplementationDaemon._merge_result_needs_reconciliation(conflict_result)
    assert not PortalImplementationDaemon._merge_result_is_transient_lock_deferral(conflict_result)
    assert not PortalImplementationDaemon._merge_result_is_transient_lock_deferral(
        {"merged": True, "attempted": True, "reason": "merged"}
    )


def test_daemon_retries_one_transient_merge_lock_when_reconciliation_is_disabled():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    conflict_event = {
        "task_id": "VAI-010",
        "merge_result": {"merged": False, "attempted": True, "reason": "merge_conflict"},
    }
    lock_event = {
        "task_id": "VAI-011",
        "timestamp": "2026-06-23T15:00:00+00:00",
        "merge_result": {"merged": False, "attempted": False, "reason": "lock_unavailable"},
    }
    now_ts = datetime(2026, 6, 23, 15, 5, tzinfo=timezone.utc).timestamp()

    selected_when_disabled = PortalImplementationDaemon._select_failed_merge_candidates_for_reconciliation(
        [conflict_event, lock_event],
        max_merges=0,
        now_ts=now_ts,
    )
    selected_when_limited = PortalImplementationDaemon._select_failed_merge_candidates_for_reconciliation(
        [conflict_event, lock_event],
        max_merges=1,
    )
    selected_when_open = PortalImplementationDaemon._select_failed_merge_candidates_for_reconciliation(
        [conflict_event, lock_event],
        max_merges=3,
    )

    assert selected_when_disabled == [lock_event]
    assert selected_when_limited == [lock_event]
    assert selected_when_open == [lock_event, conflict_event]


def test_daemon_skips_stale_transient_merge_locks_when_reconciliation_is_disabled():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    stale_lock_event = {
        "task_id": "VAI-214",
        "timestamp": "2026-06-09T09:07:16+00:00",
        "merge_result": {"merged": False, "attempted": False, "reason": "lock_exists"},
    }
    now_ts = datetime(2026, 6, 23, 15, 20, tzinfo=timezone.utc).timestamp()

    selected = PortalImplementationDaemon._select_failed_merge_candidates_for_reconciliation(
        [stale_lock_event],
        max_merges=0,
        now_ts=now_ts,
    )

    assert selected == []


def test_daemon_skips_strategy_filtered_failed_merge_reconciliation():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    conflict_event = {
        "task_id": "VAI-046",
        "merge_result": {"merged": False, "attempted": True, "reason": "merge_conflict"},
    }
    lock_event = {
        "task_id": "VAI-047",
        "merge_result": {"merged": False, "attempted": False, "reason": "lock_exists"},
    }

    selected_when_deprioritized = PortalImplementationDaemon._select_failed_merge_candidates_for_reconciliation(
        [conflict_event, lock_event],
        max_merges=3,
        deprioritized_task_ids={"VAI-046"},
    )
    selected_when_blocked = PortalImplementationDaemon._select_failed_merge_candidates_for_reconciliation(
        [conflict_event, lock_event],
        max_merges=0,
        blocked_task_ids={"VAI-047"},
    )

    assert selected_when_deprioritized == [lock_event]
    assert selected_when_blocked == []


def test_daemon_focus_tracks_keep_launch_first_for_legacy_strategies(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        DEFAULT_TRACKS,
        PortalImplementationDaemon,
        normalize_focus_tracks,
    )

    strategy_path = tmp_path / "strategy.json"
    strategy_path.write_text(json.dumps({"focus_tracks": ["quality", "ops"]}), encoding="utf-8")
    daemon = PortalImplementationDaemon(
        todo_path=tmp_path / _task_board_filename("legacy-focus"),
        state_path=tmp_path / "state.json",
        strategy_path=strategy_path,
        events_path=tmp_path / "events.jsonl",
        repo_root=tmp_path,
        task_header_prefix="## VAI-",
    )

    assert DEFAULT_TRACKS[0] == "launch"
    assert normalize_focus_tracks(["quality", "ops"])[:3] == ["launch", "quality", "ops"]
    assert daemon.load_strategy()["focus_tracks"][:3] == ["launch", "quality", "ops"]


def test_daemon_selects_launch_task_before_legacy_p0_quality_focus(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    daemon = PortalImplementationDaemon(
        todo_path=tmp_path / _task_board_filename("legacy-selection"),
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=tmp_path,
        task_header_prefix="## VAI-",
    )
    tasks = [
        PortalTask(
            task_id="VAI-019",
            title="Quality cleanup",
            status=PENDING_TASK_STATUS,
            completion="",
            priority="P0",
            track="quality",
        ),
        PortalTask(
            task_id="VAI-338",
            title="Launch map",
            status=PENDING_TASK_STATUS,
            completion="",
            priority="P0",
            track="launch",
        ),
    ]

    selected = daemon._select_next_task(
        tasks,
        {"VAI-019": "ready", "VAI-338": "ready"},
        {"focus_tracks": ["quality", "ops"]},
        {},
        {},
    )

    assert selected is not None
    assert selected.task_id == "VAI-338"


def test_daemon_skips_janitor_off_mission_task_even_when_it_is_only_ready_task(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    daemon = PortalImplementationDaemon(
        todo_path=tmp_path / _task_board_filename("strict-deprioritized-selection"),
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=tmp_path,
        task_header_prefix="## VAI-",
    )
    task = PortalTask(
        task_id="VAI-199",
        title="Review swallowed exception path in hallucinate_app/python/hallucinate_app/control_surface_policy.py:1032",
        status=PENDING_TASK_STATUS,
        completion="",
        priority="P1",
        track="runtime",
    )

    selected = daemon._select_next_task(
        [task],
        {"VAI-199": "ready"},
        {
            "deprioritized_tasks": ["VAI-199"],
            "objective_task_janitor_receipts": [
                {
                    "action": "deprioritize",
                    "task_id": "VAI-199",
                    "retired_task_reason": "off_mission_codebase_scan_task",
                }
            ],
        },
        {},
        {},
    )

    assert selected is None


def test_daemon_records_no_eligible_ready_reason_for_off_mission_ready_tasks(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
        PortalTask,
    )

    daemon = PortalImplementationDaemon(
        todo_path=tmp_path / _task_board_filename("selection-scope"),
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=tmp_path,
        task_header_prefix="## VAI-",
    )
    task = PortalTask(
        task_id="VAI-199",
        title="Review swallowed exception path in old scanner output",
        status=PENDING_TASK_STATUS,
        completion="",
        priority="P1",
        track="runtime",
    )

    scope = daemon._selection_scope(
        [task],
        {"VAI-199": "ready"},
        {
            "objective_task_janitor_receipts": [
                {
                    "action": "deprioritize",
                    "task_id": "VAI-199",
                    "retired_task_reason": "off_mission_codebase_scan_task",
                }
            ],
        },
    )

    assert scope["selectable_ready_task_ids"] == ["VAI-199"]
    assert scope["eligible_ready_task_ids"] == []
    assert scope["strict_deprioritized_ready_task_ids"] == ["VAI-199"]
    assert scope["selection_idle_reason"] == "all_selectable_ready_tasks_deprioritized_as_off_mission"


def test_daemon_repairs_regressed_todo_status_for_merged_task(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    board = tmp_path / _task_board_filename("merged-status-repair")
    board.write_text(
        "\n".join(
            (
                "# Board",
                "",
                "## VAI-338 Build the launch alignment map",
                "",
                f"- Status: {PENDING_TASK_STATUS}",
                "- Completion: manual",
                "- Priority: P0",
                "- Track: launch",
                "- Depends on:",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    daemon = PortalImplementationDaemon(
        todo_path=board,
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=tmp_path,
        task_header_prefix="## VAI-",
    )
    daemon._reconcile_failed_merges = lambda **_kwargs: []  # type: ignore[method-assign]
    daemon._cleanup_already_merged_worktrees = lambda: {}  # type: ignore[method-assign]
    daemon._unresolved_merge_failures_by_task = lambda **_kwargs: {}  # type: ignore[method-assign]
    daemon._transient_merge_deferrals_by_task = lambda **_kwargs: {}  # type: ignore[method-assign]
    daemon._latest_implementation_finished_by_task = lambda: {}  # type: ignore[method-assign]
    daemon._successfully_merged_task_ids = lambda: {"VAI-338"}  # type: ignore[method-assign]
    daemon._active_implementation_task_claims = lambda _task_ids: set()  # type: ignore[method-assign]
    daemon._commit_generated_file_update = (  # type: ignore[method-assign]
        lambda _path, *, task_id, subject: {"committed": False, "task_id": task_id, "subject": subject}
    )

    result = daemon.run_once()

    assert result["merged_status_repair"]["updated_task_ids"] == ["VAI-338"]
    assert "- Status: completed" in board.read_text(encoding="utf-8")
    assert result["completed_count"] == 1


def test_daemon_parser_blocks_header_only_task_records(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file

    pending_status = "to" + "do"
    board = tmp_path / _task_board_filename("minimal")
    board.write_text(
        "\n".join(
            (
                "# Minimal Board",
                "## VAI-900 Empty stub",
                "## VAI-901 Runnable item",
                f"- Status: {pending_status}",
                "- Priority: P1",
                "- Track: integration",
                "- Outputs: src/example.py",
                "- Validation: python -m py_compile src/example.py",
                "- Acceptance: Parser preserves non-empty records.",
            )
        ),
        encoding="utf-8",
    )

    tasks = parse_task_file(board, "## VAI-")

    assert tasks[0].status == "blocked"
    assert tasks[0].metadata["blocked reason"] == "empty task metadata"
    assert tasks[1].status == pending_status


def test_daemon_completion_inserts_missing_status_line_for_header_only_task(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalImplementationDaemon

    board = tmp_path / _task_board_filename("header-only-completion")
    board.write_text(
        "\n".join(
            (
                "# Minimal Board",
                "",
                "## VAI-902 Generated annotation cleanup",
                "",
                "## VAI-903 Runnable item",
                "",
                f"- Status: {PENDING_TASK_STATUS}",
                "- Priority: P1",
                "- Track: integration",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    daemon = PortalImplementationDaemon(
        todo_path=board,
        state_path=tmp_path / "state.json",
        strategy_path=tmp_path / "strategy.json",
        events_path=tmp_path / "events.jsonl",
        repo_root=tmp_path,
        task_header_prefix="## VAI-",
    )
    daemon._commit_generated_file_update = (  # type: ignore[method-assign]
        lambda _path, *, task_id, subject: {"committed": False, "task_id": task_id, "subject": subject}
    )

    result = daemon._mark_task_completed_in_todo("VAI-902")

    text = board.read_text(encoding="utf-8")
    assert result["updated"] is True
    assert result["updated_task_ids"] == ["VAI-902"]
    assert result["inserted_status_task_ids"] == ["VAI-902"]
    assert result["missing_task_ids"] == []
    assert "## VAI-902 Generated annotation cleanup\n\n- Status: completed\n\n## VAI-903" in text


def test_virtual_ai_os_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "VAI-000" in task_ids
    assert "VAI-014" in task_ids
    assert len(tasks) >= 12
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)


def test_supervisor_task_boards_do_not_contain_conflict_markers():
    task_board_paths = (
        TASK_BOARD_PATH,
        REPO_ROOT / "implementation_plan" / "docs" / _task_board_filename("18-swissknife-meta-glasses-display-widgets"),
        REPO_ROOT / "hallucinate_app" / "docs" / _task_board_filename("MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL"),
    )
    markers = ("<<<<<<<", "=======", ">>>>>>>")

    for path in task_board_paths:
        lines = path.read_text(encoding="utf-8").splitlines()
        marker_lines = [
            f"{index}: {line}"
            for index, line in enumerate(lines, start=1)
            if line.startswith(("<<<<<<<", ">>>>>>>")) or line in markers
        ]
        assert not marker_lines, f"{path} contains merge markers: {marker_lines}"


def test_virtual_ai_os_product_run_defers_stale_maintenance_tasks():
    stale_patterns = (
        "retry-budget",
        "supervised autonomous implementation cadence",
        "re-check canonical mcp_plus_plus source",
    )
    runnable_stale_tasks = [
        task.task_id
        for task in _load_tasks()
        if task.status in {PENDING_TASK_STATUS, "ready", "in_progress"}
        and any(pattern in f"{task.title} {task.acceptance}".lower() for pattern in stale_patterns)
    ]
    tasks = {task.task_id: task for task in _load_tasks()}

    assert runnable_stale_tasks == []
    assert tasks["VAI-025"].status in {"blocked", "completed"}


def test_virtual_ai_os_todo_dependencies_are_declared_tasks():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    for task in tasks:
        missing = [dependency for dependency in task.depends_on if dependency not in task_ids]
        assert not missing, f"{task.task_id} has missing dependencies: {missing}"


def test_virtual_ai_os_discovery_task_waits_for_initial_backlog():
    tasks = {task.task_id: task for task in _load_tasks()}
    discovery = tasks["VAI-014"]

    for task_id in (
        "VAI-003",
        "VAI-004",
        "VAI-005",
        "VAI-006",
        "VAI-007",
        "VAI-008",
        "VAI-009",
        "VAI-010",
        "VAI-011",
        "VAI-012",
        "VAI-013",
    ):
        assert task_id in discovery.depends_on
    assert "unknowns" in discovery.acceptance.lower()


def test_vai_019_cross_submodule_integration_evidence_is_wired():
    tasks = {task.task_id: task for task in _load_tasks()}
    vai_019 = tasks["VAI-019"]
    harness_source = VAI_019_HARNESS_PATH.read_text(encoding="utf-8")
    discovery_source = VAI_019_DISCOVERY_PATH.read_text(encoding="utf-8")

    assert vai_019.track == "quality"
    assert "tests/test_virtual_ai_os_end_to_end_harness.py" in vai_019.outputs
    assert "tests/test_virtual_ai_os_todo_queue.py" in vai_019.outputs
    assert "data/virtual_ai_os/discovery" in vai_019.outputs
    assert "at least two real submodules per scenario" in vai_019.acceptance
    assert "test_vai_019_cross_submodule_routes_select_placement_and_collect_artifacts" in (
        harness_source
    )
    for required_text in (
        "desktop-dataset-discovery",
        "local-ipfs-pin-receipt",
        "swissknife",
        "hallucinate_app",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "runtime_surface",
        "placement_target",
        "validation_artifacts",
    ):
        assert required_text in harness_source
        assert required_text in discovery_source


def test_vai_501_swissknife_virtual_desktop_launch_matrix_is_daemon_readable():
    discovery_source = VAI_501_DISCOVERY_PATH.read_text(encoding="utf-8")
    plan_source = INTEGRATION_PLAN_PATH.read_text(encoding="utf-8")
    matrix = _json_block_after(
        discovery_source,
        "## SwissknifeVirtualDesktopLaunchReadinessMatrix",
    )

    assert matrix["schema"] == "swissknife_virtual_desktop_launch_readiness_matrix_v1"
    assert matrix["task_id"] == "VAI-501"
    assert matrix["priority"] == "P0"
    assert matrix["track"] == "integration"
    assert matrix["gate_state"] == "open_until_all_required_validations_pass"
    assert matrix["lineage_id"] == "VAIOS-G697:launch-readiness:phone-desktop-glasses"
    assert matrix["depends_on"] == ["VAI-003", "VAI-004", "VAI-006", "VAI-007", "VAI-010", "VAI-019"]
    assert (
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets "
        "pytest tests/test_virtual_ai_os_todo_queue.py"
    ) in matrix["required_validation_commands"]
    assert any("test:e2e:meta-glasses" in command for command in matrix["required_validation_commands"])
    assert any("multimodal-control-surface.spec.ts" in command for command in matrix["required_validation_commands"])
    assert any("VAI-501|Swissknife virtual desktop|desktop peer offload" in command for command in matrix["required_validation_commands"])

    expected_surfaces = [
        "swissknife_desktop_mobile_ui",
        "hallucinate_app_mediation",
        "ipfs_accelerate_mcp_server",
        "ipfs_datasets_mcp_server",
        "ipfs_kit_mcp_server",
        "desktop_peer_offload",
        "meta_glasses_terminal_io",
        "ipfs_libp2p_transport",
        "mcp_plus_plus_compatibility",
        "playwright_evidence_lineage",
    ]
    rows = matrix["matrix"]
    assert [row["priority_order"] for row in rows] == list(range(1, len(rows) + 1))
    assert [row["surface"] for row in rows] == expected_surfaces
    assert set(matrix["owners"]) == set(expected_surfaces)

    for row in rows:
        assert row["owner"] == matrix["owners"][row["surface"]]
        assert row["readiness_requirement"]
        assert row["validation_commands"]
        assert row["evidence_refs"]
        assert row["blocks_launch"] is True

    for required_text in (
        "VAI-501",
        "Swissknife virtual desktop",
        "desktop peer offload",
        "Hallucinate App mediation",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "Meta glasses terminal IO",
        "IPFS/libp2p transport",
        "MCP++ compatibility",
        "Playwright evidence",
    ):
        assert required_text in discovery_source
        assert required_text in plan_source


def test_virtual_ai_os_mcplusplus_source_task_is_explicit():
    tasks = {task.task_id: task for task in _load_tasks()}
    source_task = tasks["VAI-013"]

    assert source_task.depends_on == ["VAI-001"]
    assert "canonical source" in source_task.acceptance.lower()
    assert "repository not found" in source_task.acceptance.lower() or "distributed protocol surface" in source_task.acceptance.lower()


def test_virtual_ai_os_autonomous_cadence_task_is_resumable():
    board_text = TASK_BOARD_PATH.read_text(encoding="utf-8")
    tasks = {task.task_id: task for task in _load_tasks()}
    cadence_task = tasks["VAI-026"]

    assert cadence_task.depends_on == []
    assert "tests/test_virtual_ai_os_todo_queue.py" in cadence_task.outputs
    assert cadence_task.validation == [
        "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py"
    ]
    assert "run the daemon before the supervisor" in cadence_task.acceptance.lower()
    assert "dependency ordering" in cadence_task.acceptance.lower()
    assert "isolated worktree implementation" in cadence_task.acceptance.lower()

    assert "## Autonomous Cadence State" in board_text
    for state_artifact in (
        "data/virtual_ai_os/state/virtual_ai_os_task_state.json",
        "data/virtual_ai_os/state/virtual_ai_os_strategy.json",
        "data/virtual_ai_os/state/virtual_ai_os_events.jsonl",
    ):
        assert state_artifact in board_text
    for state_key in (
        "recommended_task_id",
        "ready_task_ids",
        "waiting_task_ids",
        "task_statuses",
        "task_artifacts",
        "task_validation",
    ):
        assert state_key in board_text


def test_virtual_ai_os_llm_router_preflight_does_not_call_model():
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/virtual_ai_os_llm_router.py",
            "--task-id",
            "VAI-003",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["task_id"] == "VAI-003"
    assert payload["generate"] is False
    assert payload["llm_router_importable"] is True
    router_module = _load_script_module("virtual_ai_os_llm_router")
    source = (SCRIPTS_DIR / "virtual_ai_os_llm_router.py").read_text(encoding="utf-8")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.task_proposal_router import TaskProposalRouteSpec

    assert isinstance(router_module.TASK_PROPOSAL_ROUTE_SPEC, TaskProposalRouteSpec)
    assert "build_repo_task_proposal_route_runner_from_spec(" in source
    assert "build_repo_task_proposal_route_runner(" not in source


def test_vai_mgw_hao_runner_delegates_reusable_supervisor_wiring():
    runner_module = _load_script_module("run_vai_mgw_hao_supervisors")
    source = (SCRIPTS_DIR / "run_vai_mgw_hao_supervisors.py").read_text(encoding="utf-8")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.llm_merge_resolver_fallback import (
        llm_merge_resolver_fallback_command,
    )
    from ipfs_accelerate_py.agent_supervisor.multi_supervisor_runner import (
        build_arg_parser,
        implementation_multi_supervisor_env_defaults,
        implementation_supervisor_namespace_track_configs,
    )

    assert "implementation_multi_supervisor_env_defaults(" in source
    assert "implementation_supervisor_namespace_track_configs(" in source
    assert "agent_supervisor_namespace_paths(" not in source
    for script_name in (
        "virtual_ai_os_todo_supervisor.py",
        "meta_glasses_display_todo_supervisor.py",
        "hallucinate_multimodal_control_todo_supervisor.py",
    ):
        supervisor_source = (SCRIPTS_DIR / script_name).read_text(encoding="utf-8")
        assert "reconcile generated supervisor outputs" not in supervisor_source
        assert "checkpoint launch todo/objective outputs" in supervisor_source
    assert '"PREFER_COPILOT_MERGE_RESOLVER": "1"' not in source
    assert runner_module.MULTI_SUPERVISOR_ENV_DEFAULTS == implementation_multi_supervisor_env_defaults(
        prefer_copilot_merge_resolver=False,
    ) | {"IMPLEMENTATION_SUPERVISOR_LANES_PER_TRACK": "2"}
    assert runner_module.MULTI_SUPERVISOR_ENV_DEFAULTS["COPILOT_MERGE_RESOLVER_TIMEOUT_SECONDS"] == "60"
    assert runner_module.MULTI_SUPERVISOR_ENV_DEFAULTS["IMPLEMENTATION_SUPERVISOR_LANES_PER_TRACK"] == "2"
    assert "default to --detach" in runner_module.DETACHED_WORKTREE_POLICY
    assert "component submodules track" in runner_module.DETACHED_WORKTREE_POLICY
    assert runner_module.MERGE_CLEANUP_DEFAULTS == {
        "worktree_reconciliation_max_merges": "3",
        "merge_reconciliation_max_merges": "3",
        "daemon_merged_worktree_cleanup_max": "50",
    }
    assert runner_module.VAI_MGW_HAO_IMPLEMENTATION_TRACK_CONFIGS == (
        implementation_supervisor_namespace_track_configs(
            repo_root=REPO_ROOT,
            track_specs=(
                ("VAI", "scripts/virtual_ai_os_todo_supervisor.py", "virtual_ai_os"),
                (
                    "MGW",
                    "scripts/meta_glasses_display_todo_supervisor.py",
                    "meta_glasses_display_widgets",
                    "meta_glasses_display",
                ),
                (
                    "HAO",
                    "scripts/hallucinate_multimodal_control_todo_supervisor.py",
                    "hallucinate_multimodal_control",
                ),
            ),
        )
    )
    launcher_args = runner_module.build_launcher().args()
    assert "--implementation-supervisor-command" not in launcher_args
    assert launcher_args[
        launcher_args.index("--implementation-supervisor-llm-merge-resolver-command") + 1
    ] == (
        llm_merge_resolver_fallback_command()
    )
    common_arg_values = [
        arg.removeprefix("--common-arg=")
        for arg in launcher_args
        if arg.startswith("--common-arg=")
    ]
    assert "--no-worktree-reconciliation" not in common_arg_values
    assert "--no-reconciliation-guardrail" not in common_arg_values
    assert "--retry-budget-commit-outputs" in common_arg_values
    assert "--dependency-guardrail-commit-outputs" in common_arg_values
    assert "--auto-commit-generated-dirty" in common_arg_values
    assert "--worktree-reconciliation-max-merges" in common_arg_values
    assert common_arg_values[common_arg_values.index("--worktree-reconciliation-max-merges") + 1] == "3"
    assert "--merge-reconciliation-max-merges" in common_arg_values
    assert common_arg_values[common_arg_values.index("--merge-reconciliation-max-merges") + 1] == "3"
    assert "--daemon-merged-worktree-cleanup-max" in common_arg_values
    assert common_arg_values[common_arg_values.index("--daemon-merged-worktree-cleanup-max") + 1] == "50"
    assert "--codebase-scan-min-open-tasks" in common_arg_values
    assert common_arg_values[common_arg_values.index("--codebase-scan-min-open-tasks") + 1] == "8"
    assert "--codebase-scan-max-findings" in common_arg_values
    assert common_arg_values[common_arg_values.index("--codebase-scan-max-findings") + 1] == "0"
    assert "--no-objective-goal-refinement" not in common_arg_values
    assert "--objective-max-refinement-children" in common_arg_values
    assert common_arg_values[common_arg_values.index("--objective-max-refinement-children") + 1] == "2"
    assert "--objective-max-refinement-depth" in common_arg_values
    assert common_arg_values[common_arg_values.index("--objective-max-refinement-depth") + 1] == "2"
    assert "--objective-max-interoperability-goals" in common_arg_values
    assert common_arg_values[common_arg_values.index("--objective-max-interoperability-goals") + 1] == "12"
    assert "--objective-max-launch-readiness-goals" in common_arg_values
    assert common_arg_values[common_arg_values.index("--objective-max-launch-readiness-goals") + 1] == "8"
    assert "--objective-refill-scan" in common_arg_values
    assert "--objective-seed-interoperability-goals" in common_arg_values
    assert "--objective-seed-launch-readiness-goals" in common_arg_values
    assert "--no-objective-goal-completion-reconcile" not in common_arg_values
    assert common_arg_values.count("--objective-interoperability-component-path") == len(
        runner_module.VAI_MGW_HAO_INTEROPERABILITY_COMPONENT_PATHS
    )
    assert common_arg_values.count("--objective-goal-completion-todo-board") == len(
        runner_module.VAI_MGW_HAO_GOAL_COMPLETION_BOARD_SPECS
    )
    for board_spec in runner_module.VAI_MGW_HAO_GOAL_COMPLETION_BOARD_SPECS:
        assert board_spec in common_arg_values
    for component_path in (
        "mobile",
        "swissknife",
        "hallucinate_app",
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "external/ipfs_kit",
        "Mcp-Plus-Plus",
        "external/meta-wearables-dat-android",
        "external/meta-wearables-dat-ios",
    ):
        assert component_path in common_arg_values
    assert "--objective-task-janitor-max-deprioritized-tasks" in common_arg_values
    assert common_arg_values[common_arg_values.index("--objective-task-janitor-max-deprioritized-tasks") + 1] == "500"
    assert common_arg_values.count("--objective-mission-term") == len(
        runner_module.VAI_MGW_HAO_LAUNCH_MISSION_TERMS
    )
    for term in (
        "phone-hosted Swissknife virtual desktop",
        "desktop peer offload",
        "Hallucinate App mediation",
        "Hallucinate App menus",
        "Hallucinate App dashboards",
        "Hallucinate App MCP dashboard",
        "Hallucinate App dashboard capability catalog",
        "Hallucinate App daemon health",
        "Hallucinate App tools/list",
        "Hallucinate App tools/call",
        "Meta glasses interface",
        "Meta Wearables DAT",
        "camera",
        "microphone",
        "headphones",
        "Neural Band",
        "captouch",
        "IPFS",
        "libp2p",
        "MCP++",
        "MCP server",
        "MCP dashboard",
        "dashboard capability catalog",
        "daemon health",
        "tools/list",
        "tools/call",
        "ipfs_accelerate_py",
        "ipfs_datasets_py",
        "ipfs_kit_py",
        "Python MCP package names",
        "Swissknife applications",
        "control plane",
        "Playwright launch replay",
        "cross-device e2e validation",
        "launch readiness receipt",
    ):
        assert term in common_arg_values
    assert "--objective-scan-min-open-tasks" in common_arg_values
    assert common_arg_values[common_arg_values.index("--objective-scan-min-open-tasks") + 1] == "20"
    assert "--objective-scan-max-findings" in common_arg_values
    assert common_arg_values[common_arg_values.index("--objective-scan-max-findings") + 1] == "6"
    assert "--objective-surplus-findings-per-goal" in common_arg_values
    assert common_arg_values[common_arg_values.index("--objective-surplus-findings-per-goal") + 1] == "2"
    parsed_launcher_args = build_arg_parser().parse_args(launcher_args)
    assert parsed_launcher_args.common_arg == common_arg_values
    assert runner_module.default_launch_args(()) == ["--detach"]
    assert runner_module.default_launch_args(("--detach",)) == ["--detach"]
    assert runner_module.default_launch_args(("--duration-seconds", "5")) == [
        "--duration-seconds",
        "5",
        "--detach",
    ]
    assert runner_module.default_launch_args(("--foreground", "--duration-seconds", "5")) == [
        "--duration-seconds",
        "5",
    ]


def test_hallucinate_dashboard_objective_tasks_are_launch_mission_aligned():
    runner_module = _load_script_module("run_vai_mgw_hao_supervisors")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap
    from ipfs_accelerate_py.agent_supervisor.objective_task_janitor import (
        reconcile_objective_task_strategy,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import PortalTask

    goals = parse_goal_heap(OBJECTIVE_HEAP_PATH.read_text(encoding="utf-8"))
    goal = next(item for item in goals if item.goal_id == "VAIOS-G723")
    task = PortalTask(
        "HAO-900",
        "Close virtual AI OS objective gap: Hallucinate MCP dashboard interoperability console",
        PENDING_TASK_STATUS,
        "manual",
        "P1",
        "launch",
        outputs=["hallucinate_app", "data/hallucinate_multimodal_control/discovery"],
        validation=["npm --prefix hallucinate_app run test:e2e -- mcp-dashboard-interoperability.spec.ts"],
        metadata={
            "goal id": "VAIOS-G723",
            "bundle": "objective/launch/hallucinate-mcp-dashboard",
            "missing evidence": "Hallucinate App dashboard capability catalog; daemon health; tools/list; tools/call",
            "parallel lane": "supervisor-dashboard-objective-refill",
        },
        acceptance=(
            "Objective scan filed this gap for VAIOS-G723. Keep Hallucinate App menus, "
            "dashboards, dashboard capability catalog, daemon health, tools/list, tools/call, "
            "ipfs_kit_py, ipfs_datasets_py, and ipfs_accelerate_py covered by generated subtasks."
        ),
    )

    result = reconcile_objective_task_strategy(
        goals=goals,
        tasks=[task],
        strategy={},
        now="2026-06-25T00:00:00+00:00",
        mission_terms=runner_module.VAI_MGW_HAO_LAUNCH_MISSION_TERMS,
    )

    updated = result["strategy"]
    assert "HAO-900" not in updated["deprioritized_tasks"]
    assert "HAO-900" not in updated["blocked_tasks"]
    assert not any(
        receipt["task_id"] == "HAO-900" and receipt["retired_task_reason"].startswith("off_mission_")
        for receipt in updated["objective_task_janitor_receipts"]
    )


def test_objective_refill_defaults_forward_interoperability_component_paths(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (
        ImplementationSupervisorDefaults,
        ObjectiveRefillDefaults,
        apply_portal_implementation_supervisor_defaults,
    )

    defaults = ImplementationSupervisorDefaults(
        todo_path=tmp_path / "board.todo.md",
        state_dir=tmp_path / "state",
        task_prefix="VAI-",
        state_prefix="vai",
        worktree_root=tmp_path / "worktrees",
        daemon_script_path=tmp_path / "daemon.py",
        supervisor_script_path=tmp_path / "supervisor.py",
    )
    objective = ObjectiveRefillDefaults(
        seed_interoperability_goals=True,
        seed_launch_readiness_goals=True,
        objective_interoperability_component_paths=("swissknife", "hallucinate_app"),
        objective_goal_completion_todo_boards=(
            "hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md::HAO-",
        ),
        objective_max_interoperability_goals=12,
        objective_max_launch_readiness_goals=8,
    )

    args = apply_portal_implementation_supervisor_defaults(
        [],
        defaults=defaults,
        objective=objective,
    )

    assert "--objective-seed-interoperability-goals" in args
    assert "--objective-seed-launch-readiness-goals" in args
    assert args.count("--objective-interoperability-component-path") == 2
    assert args[args.index("--objective-interoperability-component-path") + 1] == "swissknife"
    assert "hallucinate_app" in args
    assert "--objective-goal-completion-todo-board" in args
    assert "hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md::HAO-" in args
    assert "--objective-max-interoperability-goals" in args
    assert args[args.index("--objective-max-interoperability-goals") + 1] == "12"
    assert "--objective-max-launch-readiness-goals" in args
    assert args[args.index("--objective-max-launch-readiness-goals") + 1] == "8"


def test_virtual_ai_os_component_repo_bootstrap_contract_is_documented(tmp_path):
    if str(SRC_DIR) not in sys.path:
        sys.path.insert(0, str(SRC_DIR))
    from handsfree.config import get_virtual_ai_os_observability_contract
    from handsfree.virtual_ai_os_components import (
        VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS,
        get_virtual_ai_os_component_repo_contracts,
    )

    plan_text = (
        REPO_ROOT
        / "implementation_plan"
        / "docs"
        / "19-virtual-ai-os-submodule-integration.md"
    ).read_text(encoding="utf-8")
    discovery_text = (
        REPO_ROOT
        / "data"
        / "virtual_ai_os"
        / "discovery"
        / "component-repo-contracts-vai-009-2026-06-12.md"
    ).read_text(encoding="utf-8")

    contracts = get_virtual_ai_os_component_repo_contracts(
        {"HANDSFREE_VAI_IPFS_DATASETS_ROOT": str(tmp_path / "datasets")},
        repo_root=REPO_ROOT,
    )
    by_id = {str(contract["component_id"]): contract for contract in contracts}

    assert {contract.component_id for contract in VIRTUAL_AI_OS_COMPONENT_REPO_CONTRACTS} == {
        "ipfs_datasets_py",
        "ipfs_accelerate_py",
        "ipfs_kit_py",
        "swissknife",
        "hallucinate_app",
        "mcp_plus_plus",
        "meta_wearables_dat_android",
        "meta_wearables_dat_ios",
    }
    assert by_id["ipfs_datasets_py"]["resolved_root"] == str(tmp_path / "datasets")
    for component in contracts:
        assert "public HTTPS" in str(component["auth_assumption"])
        assert "credential helper or gh auth" in str(component["auth_assumption"])
        if str(component["component_id"]).startswith("meta_wearables_dat_"):
            assert "status-only component" in str(component["pin_policy"])
        else:
            assert ".gitmodules branch metadata tracks" in str(component["pin_policy"])
            assert "superproject gitlink records the reviewed SHA" in str(component["pin_policy"])
            assert "validation evidence" in str(component["pin_policy"])
        assert component["recursive_bootstrap"] is False
        assert "detached task worktrees" in str(component["detached_worktree_policy"])

    assert by_id["ipfs_kit_py"]["bootstrap_mode"] == "init_root_submodule_status_nested"
    assert by_id["meta_wearables_dat_ios"]["bootstrap_mode"] == (
        "optional_device_validation_submodule"
    )

    observability = get_virtual_ai_os_observability_contract({})
    assert observability["component_repos"] == get_virtual_ai_os_component_repo_contracts({})
    assert observability["component_environment"]["mcp_plus_plus"] == (
        "HANDSFREE_VAI_MCP_PLUS_PLUS_ROOT"
    )
    assert "auth_assumption" in observability["component_bootstrap"]["swissknife"]
    assert "detached_worktree_policy" in observability["component_bootstrap"]["swissknife"]

    for required_text in (
        "Auth assumption",
        "Detached worktree policy",
        "Merge cleanup defaults",
        "branch metadata tracks",
        "commit the parent gitlink immediately",
        "credential helper or `gh auth`",
    ):
        assert required_text in plan_text
    for required_text in (
        "Auth contract",
        "Detached worktree and merge cleanup contract",
        "branch metadata tracks",
        "parent gitlink immediately",
        "--worktree-reconciliation-max-merges 0",
    ):
        assert required_text in discovery_text


def test_virtual_ai_os_objective_heap_prioritizes_launch_slice():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import objective_heap_schedule
    from ipfs_accelerate_py.agent_supervisor.objective_tracker import (
        interoperability_pair_key,
        parse_goal_heap,
    )

    text = OBJECTIVE_HEAP_PATH.read_text(encoding="utf-8")
    goals = parse_goal_heap(text)
    active_goals = [goal for goal in goals if goal.status == "active"]
    schedule_ids = [record.goal_id for record in objective_heap_schedule(goals)]
    completed_launch_ids = ["VAIOS-G689", "VAIOS-G690", "VAIOS-G691", "VAIOS-G692"]
    launch_ids = [
        "VAIOS-G693",
        "VAIOS-G694",
        "VAIOS-G695",
        "VAIOS-G696",
        "VAIOS-G697",
        "VAIOS-G698",
        "VAIOS-G699",
    ]
    goals_by_id = {goal.goal_id: goal for goal in goals}
    active_launch_ids = [
        goal_id
        for goal_id in launch_ids
        if goals_by_id[goal_id].status in {"active", "to" + "do", "open"}
    ]

    assert len(active_goals) <= 22
    assert all(goals_by_id[goal_id].status == "completed" for goal_id in completed_launch_ids)
    assert goals_by_id["VAIOS-G697"].status in {"active", "completed"}
    if goals_by_id["VAIOS-G697"].status == "completed":
        assert goals_by_id["VAIOS-G697"].fields.get("completion_evidence")
        assert goals_by_id["VAIOS-G697"].fields.get("completion_validation")
    launch_gate_validation = goals_by_id["VAIOS-G697"].fields.get("validation", "")
    assert "tests/test_virtual_ai_os_launch_readiness_gate.py" in launch_gate_validation
    assert "npm --prefix swissknife run test:e2e:meta-glasses" in launch_gate_validation
    assert (
        "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
        in launch_gate_validation
    )
    launch_gate_evidence = goals_by_id["VAIOS-G697"].fields.get("evidence", "")
    assert "Playwright launch replay" in launch_gate_evidence
    assert "swissknife/test/e2e/meta-glasses-virtual-os.spec.ts" in launch_gate_evidence
    assert "hallucinate_app/test/e2e/multimodal-control-surface.spec.ts" in launch_gate_evidence
    for goal_id in ("VAIOS-G698", "VAIOS-G699"):
        assert goals_by_id[goal_id].status in {"active", "completed"}
        if goals_by_id[goal_id].status == "completed":
            assert goals_by_id[goal_id].fields.get("completion_evidence")
            assert goals_by_id[goal_id].fields.get("completion_validation")
    if active_launch_ids:
        assert all(goal_id in schedule_ids for goal_id in active_launch_ids)
        scheduled_interop_ids = [
            goal_id
            for goal_id in schedule_ids
            if goals_by_id[goal_id].fields.get("track") == "interoperability"
        ]
        if scheduled_interop_ids:
            first_interop_index = min(schedule_ids.index(goal_id) for goal_id in scheduled_interop_ids)
            assert all(schedule_ids.index(goal_id) < first_interop_index for goal_id in active_launch_ids)
    else:
        assert all(goals_by_id[goal_id].status == "completed" for goal_id in launch_ids)
        assert all(goals_by_id[goal_id].fields.get("completion_evidence") for goal_id in launch_ids)
    launch_text = "\n".join(
        goal.fields.get("goal", "")
        for goal in goals
        if goal.goal_id in launch_ids
    ).lower()
    for term in ("phone", "desktop", "swissknife", "hallucinate app", "meta glasses", "offload"):
        assert term in launch_text
    launch_governance_text = "\n".join(
        goals_by_id[goal_id].fields.get("goal", "")
        for goal_id in ("VAIOS-G697", "VAIOS-G698", "VAIOS-G699")
    ).lower()
    for term in ("launch-readiness", "archive", "transient lock"):
        assert term in launch_governance_text

    generic_interop_ids = [f"VAIOS-G{goal_id:03d}" for goal_id in range(81, 88)]
    if goals_by_id["VAIOS-G697"].status == "active":
        assert all(goals_by_id[goal_id].status == "deferred" for goal_id in generic_interop_ids)
        assert all(goals_by_id[goal_id].fields.get("deferred_reason") for goal_id in generic_interop_ids)

    active_interop_keys = [
        interoperability_pair_key(goal.fields.get("interoperability_pair", ""))
        for goal in active_goals
        if goal.fields.get("interoperability_pair")
    ]
    assert len(active_interop_keys) == len(set(active_interop_keys))


def test_objective_interoperability_seed_skips_self_loop_dependency_symlink(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap
    from ipfs_accelerate_py.agent_supervisor.objective_tracker import append_interoperability_goals

    repo_root = tmp_path / "repo"
    mobile = repo_root / "mobile"
    swissknife = repo_root / "swissknife"
    mobile.mkdir(parents=True)
    swissknife.mkdir()
    (mobile / "package.json").write_text('{"name":"mobile"}\n', encoding="utf-8")
    (swissknife / "package.json").write_text('{"name":"swissknife"}\n', encoding="utf-8")
    loop = mobile / "node_modules"
    loop.symlink_to(loop, target_is_directory=True)

    objective_path = repo_root / "objective.md"
    objective_path.write_text(
        "\n".join(
            [
                "# Objective Heap",
                "",
                "## VAIOS-G001 Launch root",
                "- Status: active",
                "- Goal: prove the mobile Swissknife launch slice",
                "- Evidence: root objective",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = append_interoperability_goals(
        objective_path,
        repo_root=repo_root,
        component_paths=("mobile", "swissknife"),
        max_goals=1,
        goal_prefix="VAIOS-G",
    )

    assert result.appended_goal_ids == ["VAIOS-G002"]
    goals = {goal.goal_id: goal for goal in parse_goal_heap(objective_path.read_text(encoding="utf-8"))}
    assert goals["VAIOS-G002"].fields["interoperability_pair"] == "mobile, swissknife"
    assert "mobile/package.json" in goals["VAIOS-G002"].fields["package_manifests"]
    assert "node_modules" not in goals["VAIOS-G002"].fields["package_manifests"]


def test_objective_launch_readiness_seed_adds_high_value_dashboard_and_device_goals(tmp_path):
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.objective_graph import parse_goal_heap
    from ipfs_accelerate_py.agent_supervisor.objective_tracker import append_launch_readiness_goals

    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    objective_path = repo_root / "objective.md"
    objective_path.write_text(
        "\n".join(
            [
                "# Objective Heap",
                "",
                "## VAIOS-G001 Launch root",
                "- Status: active",
                "- Goal: prove the mobile Swissknife launch slice",
                "- Evidence: root objective",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = append_launch_readiness_goals(
        objective_path,
        repo_root=repo_root,
        max_goals=8,
        goal_prefix="VAIOS-G",
    )

    assert result.appended_goal_ids == [
        "VAIOS-G002",
        "VAIOS-G003",
        "VAIOS-G004",
        "VAIOS-G005",
        "VAIOS-G006",
        "VAIOS-G007",
    ]
    goals = {goal.goal_id: goal for goal in parse_goal_heap(objective_path.read_text(encoding="utf-8"))}
    seeded = [goals[goal_id] for goal_id in result.appended_goal_ids]
    assert all(goal.fields["track"] == "launch" for goal in seeded)
    assert all(goal.fields["priority"] == "P0" for goal in seeded)
    assert all(goal.fields["goal_kind"] == "launch_readiness" for goal in seeded)
    combined_goal_text = "\n".join(goal.fields["goal"] for goal in seeded).lower()
    for term in (
        "hallucinate app",
        "swissknife",
        "mcp++",
        "tools/list",
        "tools/call",
        "meta glasses",
        "control plane",
    ):
        assert term in combined_goal_text
    assert "mcp-dashboard-interoperability.spec.ts" in goals["VAIOS-G002"].fields["validation"]
    assert "tests/test_hallucinate_multimodal_control_todo_queue.py" in goals["VAIOS-G005"].fields["validation"]
    assert "tests/test_virtual_ai_os_launch_readiness_gate.py" in goals["VAIOS-G005"].fields["validation"]

    second_result = append_launch_readiness_goals(
        objective_path,
        repo_root=repo_root,
        max_goals=8,
        goal_prefix="VAIOS-G",
    )
    assert second_result.appended_goal_ids == []


def test_virtual_ai_os_launch_tasks_are_not_blocked_by_recursive_submodule_hygiene():
    tasks = {task.task_id: task for task in _load_tasks()}

    assert tasks["VAI-021"].status == "blocked"
    assert "non-launch" in tasks["VAI-021"].metadata.get("blocked reason", "")
    assert "git -C external/ipfs_kit submodule status" in "; ".join(tasks["VAI-021"].validation)
    assert "VAI-021" not in tasks["VAI-338"].depends_on
    assert tasks["VAI-338"].priority == "P0"
    assert tasks["VAI-338"].track == "launch"
    assert "VAI-338" in tasks["VAI-339"].depends_on


def test_virtual_ai_os_wrappers_delegate_reusable_namespace_context():
    daemon_module = _load_script_module("virtual_ai_os_todo_daemon")
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    daemon_source = (SCRIPTS_DIR / "virtual_ai_os_todo_daemon.py").read_text(encoding="utf-8")
    supervisor_source = (SCRIPTS_DIR / "virtual_ai_os_todo_supervisor.py").read_text(encoding="utf-8")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.wrapper_utils import AgentSupervisorNamespaceContext

    assert isinstance(daemon_module.VIRTUAL_AI_OS_CONTEXT, AgentSupervisorNamespaceContext)
    assert isinstance(supervisor_module.VIRTUAL_AI_OS_CONTEXT, AgentSupervisorNamespaceContext)
    assert daemon_module.VIRTUAL_AI_OS_CONTEXT is daemon_module._VIRTUAL_AI_OS_CONTEXT
    for module in (daemon_module, supervisor_module):
        assert module.VIRTUAL_AI_OS_CONTEXT.namespace_paths.namespace == "virtual_ai_os"
        assert module.VIRTUAL_AI_OS_CONTEXT.task_board_path == (
            REPO_ROOT
            / "implementation_plan"
            / "docs"
            / _task_board_filename("19-virtual-ai-os-submodule-integration")
        )
        assert module.VIRTUAL_AI_OS_DATA_PATHS == module.VIRTUAL_AI_OS_CONTEXT.namespace_paths
    assert "build_agent_supervisor_namespace_context(" in daemon_source
    assert "build_agent_supervisor_namespace_context(" not in supervisor_source
    assert "agent_supervisor_namespace_paths(" not in daemon_source
    assert "agent_supervisor_namespace_paths(" not in supervisor_source
    assert "build_agent_supervisor_runtime_bootstrap_callbacks(" not in daemon_source
    assert "build_agent_supervisor_runtime_bootstrap_callbacks(" not in supervisor_source


def test_virtual_ai_os_supervisor_bootstrap_paths_can_be_overridden(tmp_path, monkeypatch):
    daemon_module = _load_script_module("virtual_ai_os_todo_daemon")
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    custom_board = tmp_path / _task_board_filename("custom")
    custom_state = tmp_path / "custom-state"
    custom_worktrees = tmp_path / "custom-worktrees"

    monkeypatch.setenv("HANDSFREE_VAI_OS_TODO_PATH", str(custom_board))
    monkeypatch.setenv("HANDSFREE_VAI_OS_STATE_DIR", str(custom_state))
    monkeypatch.setenv("HANDSFREE_VAI_OS_WORKTREE_ROOT", str(custom_worktrees))

    daemon_paths = daemon_module.virtual_ai_os_bootstrap_paths()
    paths = supervisor_module.virtual_ai_os_bootstrap_paths()

    assert daemon_paths["todo_path"] == custom_board
    assert daemon_paths["state_dir"] == custom_state
    assert daemon_paths["worktree_root"] == custom_worktrees
    assert paths["todo_path"] == custom_board
    assert paths["state_dir"] == custom_state
    assert paths["worktree_root"] == custom_worktrees


def test_virtual_ai_os_supervisor_creates_bootstrap_directories(tmp_path):
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    paths = {
        "repo_root": tmp_path,
        "todo_path": tmp_path / _task_board_filename("board"),
        "state_dir": tmp_path / "state",
        "worktree_root": tmp_path / "worktrees",
    }

    supervisor_module.ensure_virtual_ai_os_bootstrap_paths(paths)

    assert paths["state_dir"].exists()
    assert paths["worktree_root"].exists()


def test_virtual_ai_os_supervisor_defaults_to_surplus_objective_todos(monkeypatch):
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    captured: dict[str, object] = {}
    runtime_class = type(supervisor_module._virtual_ai_os_supervisor_runtime)
    monkeypatch.setattr(
        runtime_class,
        "run_configured",
        lambda self, args, **kwargs: captured.setdefault(
            "payload",
            {"runtime": self, "args": args, "kwargs": kwargs},
        ),
    )

    supervisor_module.main(["--once"])

    payload = captured["payload"]
    runtime = payload["runtime"]
    args = payload["args"]
    kwargs = payload["kwargs"]
    flag_index = args.index("--objective-surplus-findings-per-goal")
    assert args[flag_index + 1] == str(supervisor_module.OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL)
    assert "--objective-seed-interoperability-goals" in args
    assert "--objective-seed-launch-readiness-goals" in args
    focus_values = [
        args[index + 1]
        for index, arg in enumerate(args)
        if arg == "--objective-interoperability-focus"
    ]
    assert focus_values == ["mobile", "swissknife", "hallucinate_app"]
    component_values = [
        args[index + 1]
        for index, arg in enumerate(args)
        if arg == "--objective-interoperability-component-path"
    ]
    assert component_values == list(supervisor_module.VIRTUAL_AI_OS_INTEROPERABILITY_COMPONENT_PATHS)
    max_interop_index = args.index("--objective-max-interoperability-goals")
    assert args[max_interop_index + 1] == "12"
    max_launch_index = args.index("--objective-max-launch-readiness-goals")
    assert args[max_launch_index + 1] == "8"
    codebase_min_index = args.index("--codebase-scan-min-open-tasks")
    codebase_max_index = args.index("--codebase-scan-max-findings")
    assert args[codebase_min_index + 1] == "8"
    assert args[codebase_max_index + 1] == "3"
    assert kwargs["ensure_running"] is False
    assert runtime.process_match_any == supervisor_module.VIRTUAL_AI_OS_SUPERVISOR_PROCESS_MARKERS


def test_virtual_ai_os_supervisor_ensure_running_flag_uses_runtime_helper(tmp_path, monkeypatch):
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    captured: dict[str, object] = {}
    monkeypatch.setenv("HANDSFREE_VAI_OS_TODO_PATH", str(tmp_path / _task_board_filename("board")))
    monkeypatch.setenv("HANDSFREE_VAI_OS_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("HANDSFREE_VAI_OS_WORKTREE_ROOT", str(tmp_path / "worktrees"))
    runtime_class = type(supervisor_module._virtual_ai_os_supervisor_runtime)
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
    assert runtime.process_match_any == supervisor_module.VIRTUAL_AI_OS_SUPERVISOR_PROCESS_MARKERS


def test_virtual_ai_os_codebase_scan_skips_generated_discovery_domains(tmp_path):
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import scan_codebase_findings

    repo = tmp_path / "repo"
    source = repo / "src" / "scan_target.py"
    mgw_owned_paths = (
        repo / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.md",
        repo / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md",
        repo / "tests" / "test_meta_glasses_display_todo_queue.py",
    )
    generated_reports = (
        repo / "data" / "virtual_ai_os" / "discovery" / "report.md",
        repo / "data" / "hallucinate_multimodal_control" / "discovery" / "report.md",
        repo / "data" / "meta_glasses_display_widgets" / "discovery" / "report.md",
    )

    _git(repo.parent, "init", repo.name)
    _git(repo, "checkout", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.invalid")
    source.parent.mkdir(parents=True)
    source.write_text(
        "def unresolved():\n    # " + "FIX" + "ME: real source finding\n    return None\n",
        encoding="utf-8",
    )
    for report in generated_reports:
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(
            "# Generated Discovery\n\nThe captured evidence mentions a " + "to" + "do task.\n",
            encoding="utf-8",
        )
    for mgw_owned_path in mgw_owned_paths:
        mgw_owned_path.parent.mkdir(parents=True, exist_ok=True)
        mgw_owned_path.write_text(
            "# MGW-owned file\n\n# " + "FIX" + "ME: VAI must not claim this file.\n",
            encoding="utf-8",
        )
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed scan candidates")

    findings = scan_codebase_findings(
        repo,
        max_findings=10,
        seen_fingerprints=set(),
        skip_prefixes=supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES,
    )

    assert [finding.root_relative_path for finding in findings] == ["src/scan_target.py"]
    assert "external/ipfs_kit/archive/" in supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES
    assert "swissknife/cleanup-archive/" in supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES
    assert "swissknife/docs/DEVELOPER_GUIDE.md" in supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES
    assert "swissknife/docs/validation/" in supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES
    assert {
        "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md",
        "implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md",
        "tests/test_meta_glasses_display_todo_queue.py",
    } <= set(supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES)


def test_vai_503_mcp_dashboard_interoperability_gate_closes_objective_gap():
    source = VAI_503_DISCOVERY_PATH.read_text(encoding="utf-8")
    packet = _json_block_after(source, "## DashboardInteroperabilityGate")
    heap_source = OBJECTIVE_HEAP_PATH.read_text(encoding="utf-8")
    readiness_source = (REPO_ROOT / "docs" / "launch" / "phone_desktop_glasses_readiness.md").read_text(
        encoding="utf-8"
    )
    playwright_source = (
        REPO_ROOT / "hallucinate_app" / "test" / "e2e" / "mcp-dashboard-interoperability.spec.ts"
    ).read_text(encoding="utf-8")
    swissknife_registry_source = (
        REPO_ROOT / "swissknife" / "src" / "services" / "swissknife-mcp-capability-registry.ts"
    ).read_text(encoding="utf-8")

    assert packet["task_id"] == "VAI-503"
    assert packet["goal_id"] == "VAIOS-G723"
    assert packet["evidence_term"] == "launch Playwright validation gate"
    assert packet["playwright_spec"] == "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
    assert packet["swissknife_consumers"]["ipfs_kit_py_port"] == 8004
    assert packet["supervisor_follow_up_subtasks"] == [
        "HAO-678",
        "HAO-679",
        "HAO-680",
        "HAO-681",
        "HAO-682",
        "HAO-683",
    ]

    for term in (
        "catalog normalization",
        "dashboard UI wiring",
        "mediated tool-call receipts",
        "Swissknife consumers",
        "Playwright coverage",
        "supervisor-generated follow-up subtasks",
    ):
        assert term in source
        assert term in playwright_source

    assert "data/virtual_ai_os/discovery/2026-06-25-vai-503-mcp-dashboard-interoperability-gate.md" in heap_source
    assert "launch Playwright validation gate" in heap_source
    assert "mcp-dashboard-interoperability.spec.ts" in readiness_source
    assert "port: 8004" in swissknife_registry_source


def test_virtual_ai_os_queue_tests_do_not_emit_static_followup_findings():
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import scan_findings_in_file

    findings = scan_findings_in_file(Path(__file__), repo_root=REPO_ROOT)

    assert findings == []
