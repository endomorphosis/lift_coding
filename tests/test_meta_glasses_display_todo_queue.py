from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = REPO_ROOT / "scripts"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"
PLAN_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.md"


def _load_script_module(name: str):
    script_path = SCRIPTS_DIR / f"{name}.py"
    if str(SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_DIR))
    if str(IPFS_ACCELERATE_ROOT) not in sys.path:
        sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_tasks():
    if str(IPFS_ACCELERATE_ROOT) not in sys.path:
        sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        parse_task_file,
    )

    return parse_task_file(TODO_PATH, "## MGW-")


def test_meta_glasses_display_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "MGW-000" in task_ids
    assert "MGW-012" in task_ids
    assert "MGW-013" in task_ids
    assert "MGW-373" in task_ids
    assert len(tasks) >= 14
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


def test_expanded_meta_glasses_io_tasks_cover_contracts_mocks_transport_and_tests():
    tasks = {task.task_id: task for task in _load_tasks()}

    expected_dependencies = {
        "MGW-363": ["MGW-001"],
        "MGW-364": ["MGW-363"],
        "MGW-365": ["MGW-363", "MGW-364"],
        "MGW-366": ["MGW-364"],
        "MGW-367": ["MGW-364", "MGW-365", "MGW-366"],
        "MGW-368": ["MGW-364", "MGW-365", "MGW-366"],
        "MGW-369": ["MGW-364", "MGW-365", "MGW-366"],
        "MGW-370": ["MGW-367", "MGW-368", "MGW-369"],
        "MGW-371": ["MGW-365", "MGW-366", "MGW-367", "MGW-368", "MGW-369", "MGW-370"],
        "MGW-372": ["MGW-367", "MGW-368", "MGW-369", "MGW-370", "MGW-371"],
        "MGW-373": ["MGW-371", "MGW-372"],
    }
    expected_acceptance_terms = {
        "MGW-363": ["Meta Neural Band", "captouch", "Bluetooth-profile", "IPFS/libp2p/MCP++"],
        "MGW-364": ["camera", "microphone", "speaker/headphone", "control-plane route decisions"],
        "MGW-365": ["Hardware-free", "DAT camera", "control-plane event envelopes", "phone GPS"],
        "MGW-366": ["Bluetooth", "Wi-Fi", "control-plane route decision", "libp2p peer IDs"],
        "MGW-367": ["camera photo", "video stream", "pass normalized capture events", "control plane"],
        "MGW-368": ["microphone", "speaker/headphone", "raw-audio leakage", "control plane"],
        "MGW-369": ["Meta Neural Band", "captouch", "motion/orientation", "control-plane route decisions"],
        "MGW-370": ["Swissknife applications", "interaction bindings", "control plane", "MCP++ receipts"],
        "MGW-371": ["Bluetooth/Wi-Fi", "control-plane route decisions", "unauthorized control-plane handoffs"],
        "MGW-372": ["Playwright", "app interaction bindings", "control-plane handoff evidence"],
        "MGW-373": ["Launch readiness", "control-plane routing evidence", "Playwright results"],
    }

    for task_id, dependencies in expected_dependencies.items():
        task = tasks[task_id]

        assert task.status == "todo"
        assert task.priority in {"P0", "P1"}
        assert task.depends_on == dependencies
        for term in expected_acceptance_terms[task_id]:
            assert term in task.acceptance


def test_expanded_meta_glasses_io_second_wave_targets_swissknife_app_integration():
    tasks = {task.task_id: task for task in _load_tasks()}

    expected_dependencies = {
        "MGW-413": ["MGW-363"],
        "MGW-414": ["MGW-364", "MGW-413"],
        "MGW-415": ["MGW-365", "MGW-413"],
        "MGW-416": ["MGW-364", "MGW-413"],
        "MGW-417": ["MGW-365", "MGW-366", "MGW-367", "MGW-368"],
        "MGW-418": ["MGW-369", "MGW-413", "MGW-415"],
        "MGW-419": ["MGW-370", "MGW-416"],
        "MGW-420": ["MGW-371", "MGW-417", "MGW-419"],
        "MGW-421": ["MGW-414", "MGW-417", "MGW-418", "MGW-419"],
        "MGW-422": ["MGW-372", "MGW-420", "MGW-421"],
        "MGW-423": ["MGW-413", "MGW-417", "MGW-418"],
        "MGW-424": [
            "MGW-413",
            "MGW-414",
            "MGW-415",
            "MGW-416",
            "MGW-417",
            "MGW-418",
            "MGW-419",
            "MGW-420",
            "MGW-421",
            "MGW-422",
            "MGW-423",
        ],
    }
    expected_acceptance_terms = {
        "MGW-413": ["native DAT", "Web Apps", "IPFS/libp2p/MCP++", "Bluetooth or Wi-Fi"],
        "MGW-414": ["Swissknife applications", "app binding IDs", "control-plane route decisions"],
        "MGW-415": ["DisplayAccess", "CameraAccess", "Arrow/Enter", "without Meta credentials"],
        "MGW-416": ["camera capture", "GPS", "redaction", "replay protection"],
        "MGW-417": ["camera", "microphone route", "speaker/headphone route", "MCP++ receipts"],
        "MGW-418": ["Neural Band", "captouch", "motion/orientation", "phone GPS"],
        "MGW-419": ["Hallucinate App policy", "IPFS persistence", "libp2p relay"],
        "MGW-420": ["IPFS CIDs", "libp2p peer/session IDs", "raw Bluetooth/Wi-Fi transport claims"],
        "MGW-421": ["Demo Swissknife app", "control-plane handoff receipts", "fallback UI"],
        "MGW-422": ["Playwright", "visible app state", "no unauthorized control-plane handoff"],
        "MGW-423": ["Native DAT", "feature gates", "physical validation checklist"],
        "MGW-424": ["deprioritize generic code-annotation cleanup", "P0/P1 expanded-I/O tasks"],
    }

    for task_id, dependencies in expected_dependencies.items():
        task = tasks[task_id]

        assert task.status == "todo"
        assert task.priority in {"P0", "P1"}
        assert task.depends_on == dependencies
        for term in expected_acceptance_terms[task_id]:
            assert term in task.acceptance


def test_expanded_meta_glasses_io_scope_is_documented_in_plan():
    source = PLAN_PATH.read_text(encoding="utf-8")

    for term in [
        "2026-06-23 scope expansion",
        "camera photo/video capture",
        "microphone input",
        "speaker/headphone output",
        "Meta Neural Band",
        "captouch",
        "control plane",
        "interaction bindings",
        "Bluetooth",
        "Wi-Fi",
        "IPFS",
        "libp2p",
        "MCP++",
        "Phase 10: Expanded Meta Glasses I/O for Swissknife Apps",
        "Second-wave MGW task split",
        "MGW-424",
        "Playwright tests",
    ]:
        assert term in source


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


def test_meta_glasses_supervisor_wrapper_uses_active_accelerate_runner(monkeypatch):
    supervisor_module = _load_script_module("meta_glasses_display_todo_supervisor")
    daemon_module = _load_script_module("meta_glasses_display_todo_daemon")
    source = (SCRIPTS_DIR / "meta_glasses_display_todo_supervisor.py").read_text(
        encoding="utf-8"
    )
    captured: dict[str, list[str] | None] = {}

    class FakeRunner:
        def run(self, argv):
            captured["argv"] = None if argv is None else list(argv)

    monkeypatch.setattr(supervisor_module, "_meta_glasses_display_supervisor_runner", FakeRunner())
    args = [
        "--worktree-reconciliation-max-merges",
        "3",
        "--merge-reconciliation-max-merges",
        "3",
        "--daemon-merged-worktree-cleanup-max",
        "50",
        "--objective-mission-term",
        "Meta glasses interface",
    ]

    supervisor_module.main(args)

    assert captured["argv"] == args
    assert "ipfs_datasets_py.optimizers.todo_daemon.implementation_supervisor" not in source
    assert "build_script_supervisor_bootstrap_runner(" in source
    assert supervisor_module.META_GLASSES_DISPLAY_ENV_PREFIX == "HANDSFREE_MGW"
    assert supervisor_module.CODEBASE_SCAN_SETTINGS.min_open_tasks == 0
    assert supervisor_module.CODEBASE_SCAN_SETTINGS.max_findings == 0
    assert supervisor_module.DAEMON_SCRIPT_PATH.name == "meta_glasses_display_todo_daemon.py"
    assert "swissknife" in supervisor_module.META_GLASSES_DISPLAY_WORKTREE_SUBMODULE_PATHS
    assert (
        daemon_module.META_GLASSES_DISPLAY_WORKTREE_SUBMODULE_PATHS
        == supervisor_module.META_GLASSES_DISPLAY_WORKTREE_SUBMODULE_PATHS
    )
