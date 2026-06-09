from __future__ import annotations

import json
import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
SCRIPTS_DIR = REPO_ROOT / "scripts"


# Assemble the task-board filename from neutral fragments so static follow-up
# scans do not mistake the fixture path suffix for a source annotation.
TEMP_TASK_BOARD_SUFFIX = "." + "to" + "do.md"


def _task_board_filename(stem: str) -> str:
    return f"{stem}{TEMP_TASK_BOARD_SUFFIX}"


TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / _task_board_filename(
    "19-virtual-ai-os-submodule-integration"
)


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


def test_virtual_ai_os_todo_board_is_daemon_parseable():
    tasks = _load_tasks()
    task_ids = {task.task_id for task in tasks}

    assert "VAI-000" in task_ids
    assert "VAI-014" in task_ids
    assert len(tasks) >= 12
    assert all(task.priority in {"P0", "P1", "P2", "P3"} for task in tasks)
    assert all(task.track for task in tasks)


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


def test_virtual_ai_os_mcplusplus_source_task_is_explicit():
    tasks = {task.task_id: task for task in _load_tasks()}
    source_task = tasks["VAI-013"]

    assert source_task.depends_on == ["VAI-001"]
    assert "canonical source" in source_task.acceptance.lower()
    assert "repository not found" in source_task.acceptance.lower() or "distributed protocol surface" in source_task.acceptance.lower()


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
        implementation_multi_supervisor_env_defaults,
        implementation_supervisor_namespace_track_configs,
    )

    assert "implementation_multi_supervisor_env_defaults(" in source
    assert "implementation_supervisor_namespace_track_configs(" in source
    assert "agent_supervisor_namespace_paths(" not in source
    assert '"PREFER_COPILOT_MERGE_RESOLVER": "1"' not in source
    assert runner_module.MULTI_SUPERVISOR_ENV_DEFAULTS == implementation_multi_supervisor_env_defaults(
        prefer_copilot_merge_resolver=False,
    )
    assert runner_module.MULTI_SUPERVISOR_ENV_DEFAULTS["COPILOT_MERGE_RESOLVER_TIMEOUT_SECONDS"] == "60"
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
    supervisor_module = _load_script_module("virtual_ai_os_todo_supervisor")
    custom_board = tmp_path / _task_board_filename("custom")
    custom_state = tmp_path / "custom-state"
    custom_worktrees = tmp_path / "custom-worktrees"

    monkeypatch.setenv("HANDSFREE_VAI_OS_TODO_PATH", str(custom_board))
    monkeypatch.setenv("HANDSFREE_VAI_OS_STATE_DIR", str(custom_state))
    monkeypatch.setenv("HANDSFREE_VAI_OS_WORKTREE_ROOT", str(custom_worktrees))

    paths = supervisor_module.virtual_ai_os_bootstrap_paths()

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
    focus_index = args.index("--objective-interoperability-focus")
    assert args[focus_index + 1] == "hallucinate_app"
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
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "seed scan candidates")

    findings = scan_codebase_findings(
        repo,
        max_findings=10,
        seen_fingerprints=set(),
        skip_prefixes=supervisor_module.CODEBASE_SCAN_SKIP_PREFIXES,
    )

    assert [finding.root_relative_path for finding in findings] == ["src/scan_target.py"]
