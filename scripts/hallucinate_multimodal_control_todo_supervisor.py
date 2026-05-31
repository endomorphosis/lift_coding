#!/usr/bin/env python3
"""Run the accelerator task supervisor for Hallucinate multimodal-control work."""

from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from hallucinate_multimodal_control_todo_daemon import (  # noqa: E402
    CODEBASE_SCAN_COOLDOWN_SECONDS,
    CODEBASE_SCAN_MAX_FINDINGS,
    CODEBASE_SCAN_MIN_OPEN_TASKS,
    CODEBASE_SCAN_SKIP_PREFIXES,
    DISCOVERY_DIR,
    HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
    OBJECTIVE_BUNDLE_DIR,
    OBJECTIVE_DATASET_DIR,
    OBJECTIVE_SCAN_COOLDOWN_SECONDS,
    OBJECTIVE_SCAN_MAX_FINDINGS,
    OBJECTIVE_SCAN_MIN_OPEN_TASKS,
    OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL,
    OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO,
    OBJECTIVE_TODO_VECTOR_INDEX_PATH,
    HALLUCINATE_INTEROPERABILITY_FOCUS,
    TASK_BOARD_PATH_KEY,
    TASK_BOARD_PATH_OPTION,
    _ensure_runtime_pythonpath,
    ensure_hallucinate_multimodal_bootstrap_paths,
    record_codebase_scan_findings,
    record_objective_goal_findings,
    record_retry_budget_findings,
)


logger = logging.getLogger("hallucinate_multimodal_control_todo_supervisor")
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "hallucinate_multimodal_control_todo_daemon.py"
OBJECTIVE_GRAPH_PATH = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "objective_graph.json"
SUPERVISOR_RUNNING_STATES = {"running", "starting", "recycling", "restarting"}


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def _with_flag_default(argv: list[str], flag: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, *argv]


def _with_repeated_default(argv: list[str], flag: str, values: tuple[str, ...]) -> list[str]:
    if flag in argv:
        return argv
    defaults: list[str] = []
    for value in values:
        defaults.extend([flag, value])
    return [*defaults, *argv]


def _default_llm_merge_resolver_command() -> str:
    configured = os.environ.get("HANDSFREE_HAO_LLM_MERGE_RESOLVER_COMMAND", "").strip()
    if configured:
        return configured
    configured = os.environ.get("IPFS_ACCELERATE_AGENT_LLM_MERGE_RESOLVER_COMMAND", "").strip()
    if configured:
        return configured
    codex = shutil.which("codex")
    if not codex:
        return ""
    return f"{shlex.quote(codex)} exec --dangerously-bypass-approvals-and-sandbox -C . -"


def _pop_bool_flag(argv: list[str], flag: str) -> bool:
    found = False
    kept: list[str] = []
    for item in argv:
        if item == flag:
            found = True
            continue
        kept.append(item)
    argv[:] = kept
    return found


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _read_pid(path: Path) -> int:
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return 0


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _process_command_line(pid: int) -> str:
    if pid <= 0:
        return ""
    cmdline_path = Path("/proc") / str(pid) / "cmdline"
    try:
        raw = cmdline_path.read_bytes()
    except OSError:
        return ""
    return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()


def _hallucinate_supervisor_runtime_paths(state_dir: Path, state_prefix: str) -> dict[str, Path]:
    return {
        "supervisor_status": state_dir / f"{state_prefix}_supervisor_status.json",
        "managed_daemon_pid": state_dir / f"{state_prefix}_managed_daemon.pid",
        "wrapper_pid": state_dir / f"{state_prefix}_supervisor_wrapper.pid",
        "wrapper_out": state_dir / f"{state_prefix}_supervisor_wrapper.out",
        "implementation_lock": state_dir / "implementation.lock",
    }


def _pid_is_hallucinate_supervisor(pid: int) -> bool:
    cmdline = _process_command_line(pid)
    return (
        "hallucinate_multimodal_control_todo_supervisor.py" in cmdline
        or "hallucinate_multimodal_control_autopilot.py" in cmdline
    )


def _runtime_lock_owner_is_alive(path: Path) -> bool:
    metadata = _read_json(path)
    try:
        pid = int(metadata.get("pid") or 0)
    except (TypeError, ValueError):
        return False
    if not _pid_alive(pid):
        return False
    owner_script = str(metadata.get("owner_script") or "")
    if owner_script and owner_script not in _process_command_line(pid):
        return False
    return True


def repair_hallucinate_supervisor_runtime(state_dir: Path, state_prefix: str) -> dict[str, Any]:
    """Clear stale Hallucinate supervisor/daemon markers before health checks."""

    paths = _hallucinate_supervisor_runtime_paths(state_dir, state_prefix)
    repairs: dict[str, Any] = {"removed": [], "updated_status": False}
    for key in ("managed_daemon_pid", "wrapper_pid"):
        path = paths[key]
        pid = _read_pid(path)
        if not path.exists():
            continue
        if pid and _pid_alive(pid):
            continue
        path.unlink(missing_ok=True)
        repairs["removed"].append(str(path))

    lock_path = paths["implementation_lock"]
    if lock_path.exists() and not _runtime_lock_owner_is_alive(lock_path):
        lock_path.unlink(missing_ok=True)
        repairs["removed"].append(str(lock_path))

    status_path = paths["supervisor_status"]
    status = _read_json(status_path)
    supervisor_pid = int(status.get("supervisor_pid") or 0)
    daemon_pid = int(status.get("daemon_pid") or 0)
    status_value = str(status.get("status") or "")
    supervisor_alive = _pid_alive(supervisor_pid)
    daemon_alive = _pid_alive(daemon_pid)
    if status and status_value in SUPERVISOR_RUNNING_STATES and not supervisor_alive:
        status.update(
            {
                "status": "stale",
                "repaired_at": _utc_now(),
                "repair_reason": "supervisor_pid_not_running",
                "supervisor_pid_alive": False,
                "daemon_pid_alive": daemon_alive,
            }
        )
        _write_json(status_path, status)
        repairs["updated_status"] = True
    return repairs


def hallucinate_supervisor_is_running(state_dir: Path, state_prefix: str) -> bool:
    paths = _hallucinate_supervisor_runtime_paths(state_dir, state_prefix)
    candidates = [
        _read_pid(paths["wrapper_pid"]),
        int(_read_json(paths["supervisor_status"]).get("supervisor_pid") or 0),
    ]
    return any(_pid_alive(pid) and _pid_is_hallucinate_supervisor(pid) for pid in candidates)


def _background_supervisor_args(argv: list[str]) -> list[str]:
    args = [item for item in argv if item != "--once"]
    if "--implement" not in args and "--no-implement" not in args:
        args = ["--implement", *args]
    return args


def ensure_hallucinate_supervisor_running(argv: list[str], *, state_dir: Path, state_prefix: str) -> dict[str, Any]:
    repairs = repair_hallucinate_supervisor_runtime(state_dir, state_prefix)
    if hallucinate_supervisor_is_running(state_dir, state_prefix):
        return {"started": False, "reason": "already_running", "repairs": repairs}

    paths = _hallucinate_supervisor_runtime_paths(state_dir, state_prefix)
    launch_args = _background_supervisor_args(argv)
    command = [sys.executable, str(Path(__file__).resolve()), *launch_args]
    _ensure_runtime_pythonpath()
    env = dict(os.environ)
    paths["wrapper_out"].parent.mkdir(parents=True, exist_ok=True)
    out_handle = paths["wrapper_out"].open("ab")
    try:
        process = subprocess.Popen(
            command,
            cwd=REPO_ROOT,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    finally:
        out_handle.close()
    paths["wrapper_pid"].write_text(f"{process.pid}\n", encoding="utf-8")
    time.sleep(1.0)
    return {
        "started": _pid_alive(process.pid),
        "pid": process.pid,
        "command": command,
        "wrapper_out": str(paths["wrapper_out"]),
        "repairs": repairs,
    }


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    ensure_running = _pop_bool_flag(args, "--ensure-running")
    paths = ensure_hallucinate_multimodal_bootstrap_paths()
    os.chdir(REPO_ROOT)
    _ensure_runtime_pythonpath()

    args = _with_default(args, TASK_BOARD_PATH_OPTION, str(paths[TASK_BOARD_PATH_KEY]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## HAO-")
    args = _with_default(args, "--state-prefix", "hallucinate_multimodal_control")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))
    args = _with_default(args, "--daemon-script-path", str(DAEMON_SCRIPT_PATH))
    args = _with_default(args, "--supervisor-script-path", str(Path(__file__).resolve()))
    args = _with_default(args, "--max-restarts", "0")
    resolver_command = _default_llm_merge_resolver_command()
    if resolver_command:
        args = _with_default(args, "--llm-merge-resolver-command", resolver_command)
    args = _with_flag_default(args, "--objective-refill-scan")
    args = _with_flag_default(args, "--objective-seed-interoperability-goals")
    args = _with_repeated_default(args, "--objective-interoperability-focus", HALLUCINATE_INTEROPERABILITY_FOCUS)
    args = _with_default(args, "--objective-path", str(paths["objective_goal_heap_path"]))
    args = _with_default(args, "--objective-graph-path", str(OBJECTIVE_GRAPH_PATH))
    args = _with_default(args, "--objective-bundle-dir", str(OBJECTIVE_BUNDLE_DIR))
    args = _with_default(args, "--objective-dataset-dir", str(OBJECTIVE_DATASET_DIR))
    args = _with_default(args, "--objective-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--objective-discovery-output-path", DISCOVERY_DIR.relative_to(REPO_ROOT).as_posix())
    args = _with_default(args, "--objective-scan-min-open-tasks", str(OBJECTIVE_SCAN_MIN_OPEN_TASKS))
    args = _with_default(args, "--objective-scan-max-findings", str(OBJECTIVE_SCAN_MAX_FINDINGS))
    args = _with_default(args, "--objective-scan-cooldown-seconds", str(OBJECTIVE_SCAN_COOLDOWN_SECONDS))
    # scanner-resolved: MGW-189, MGW-190, HAO-247, VAI-165, HAO-253, VAI-169, HAO-257, HAO-262, VAI-174 — "todo" below is part of the CLI flag name --objective-todo-vector-index-path (work-item queue path), not a deferred-work annotation.
    args = _with_default(args, "--objective-todo-vector-index-path", str(OBJECTIVE_TODO_VECTOR_INDEX_PATH))
    args = _with_default(args, "--objective-surplus-findings-per-goal", str(OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL))
    # scanner-resolved: MGW-191, MGW-192, HAO-244, HAO-248, HAO-249, VAI-166, HAO-254, VAI-170, HAO-258, HAO-263 — "todo" in --objective-surplus-min-terms-per-todo refers to backlog task entries (CLI flag name, not a deferred-work annotation).
    args = _with_default(args, "--objective-surplus-min-terms-per-todo", str(OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO))
    args = _with_flag_default(args, "--codebase-refill-scan")
    args = _with_default(args, "--codebase-scan-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--codebase-scan-discovery-output-path", DISCOVERY_DIR.relative_to(REPO_ROOT).as_posix())
    args = _with_default(args, "--codebase-scan-min-open-tasks", str(CODEBASE_SCAN_MIN_OPEN_TASKS))
    args = _with_default(args, "--codebase-scan-max-findings", str(CODEBASE_SCAN_MAX_FINDINGS))
    args = _with_default(args, "--codebase-scan-cooldown-seconds", str(CODEBASE_SCAN_COOLDOWN_SECONDS))
    args = _with_repeated_default(args, "--codebase-scan-skip-prefix", CODEBASE_SCAN_SKIP_PREFIXES)

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,
        PortalSupervisorConfig,
        parse_args,
        split_csv_values,
    )

    parsed = parse_args(args)
    logging.basicConfig(
        level=getattr(logging, parsed.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    state_path = parsed.state_dir / f"{parsed.state_prefix}_task_state.json"
    strategy_path = parsed.state_dir / f"{parsed.state_prefix}_strategy.json"
    events_path = parsed.state_dir / f"{parsed.state_prefix}_supervisor_events.jsonl"
    daemon_events_path = parsed.state_dir / f"{parsed.state_prefix}_events.jsonl"
    record_objective_goal_findings(
        todo_path=parsed.todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=DISCOVERY_DIR,
        objective_path=parsed.objective_path or paths["objective_goal_heap_path"],
        bundle_dir=parsed.objective_bundle_dir,
        dataset_dir=parsed.objective_dataset_dir,
        todo_vector_index_path=parsed.objective_todo_vector_index_path,
        task_header_prefix=parsed.task_prefix,
        repo_root=REPO_ROOT,
        min_open_tasks=parsed.objective_scan_min_open_tasks,
        max_findings=parsed.objective_scan_max_findings,
        cooldown_seconds=parsed.objective_scan_cooldown_seconds,
        surplus_findings_per_goal=parsed.objective_surplus_findings_per_goal,
        surplus_min_terms_per_todo=parsed.objective_surplus_min_terms_per_todo,
    )
    record_codebase_scan_findings(
        todo_path=parsed.todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=DISCOVERY_DIR,
        task_header_prefix=parsed.task_prefix,
        repo_root=REPO_ROOT,
        min_open_tasks=parsed.codebase_scan_min_open_tasks,
        max_findings=parsed.codebase_scan_max_findings,
        cooldown_seconds=parsed.codebase_scan_cooldown_seconds,
    )
    record_retry_budget_findings(
        todo_path=parsed.todo_path,
        events_path=daemon_events_path,
        strategy_path=strategy_path,
        discovery_dir=DISCOVERY_DIR,
        task_header_prefix=parsed.task_prefix,
    )
    if ensure_running:
        result = ensure_hallucinate_supervisor_running(
            args,
            state_dir=parsed.state_dir,
            state_prefix=parsed.state_prefix,
        )
        logger.info("Hallucinate multimodal-control supervisor ensure complete: %s", result)
        return

    repairs = repair_hallucinate_supervisor_runtime(parsed.state_dir, parsed.state_prefix)
    if repairs.get("removed") or repairs.get("updated_status"):
        logger.info("Repaired stale Hallucinate supervisor runtime markers: %s", repairs)

    supervisor = PortalImplementationSupervisor(
        PortalSupervisorConfig(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            events_path=events_path,
            state_dir=parsed.state_dir,
            stale_seconds=parsed.stale_seconds,
            check_interval=parsed.check_interval,
            max_restarts=parsed.max_restarts,
            daemon_interval=parsed.daemon_interval,
            task_prefix=parsed.task_prefix,
            state_prefix=parsed.state_prefix,
            implement=parsed.implement,
            implementation_command=parsed.implementation_command,
            llm_merge_resolver_command=parsed.llm_merge_resolver_command,
            llm_merge_resolver_timeout_seconds=parsed.llm_merge_resolver_timeout_seconds,
            implementation_timeout=parsed.implementation_timeout,
            implementation_log_stall_seconds=parsed.implementation_log_stall_seconds,
            use_ephemeral_worktree=parsed.implement and not parsed.no_ephemeral_worktree,
            worktree_root=parsed.worktree_root,
            worktree_submodule_paths=tuple(parsed.worktree_submodule_path or HALLUCINATE_WORKTREE_SUBMODULE_PATHS),
            codebase_refill_enabled=parsed.codebase_refill_scan,
            codebase_scan_discovery_dir=parsed.codebase_scan_discovery_dir,
            codebase_scan_discovery_output_path=parsed.codebase_scan_discovery_output_path,
            codebase_scan_min_open_tasks=parsed.codebase_scan_min_open_tasks,
            codebase_scan_max_findings=parsed.codebase_scan_max_findings,
            codebase_scan_cooldown_seconds=parsed.codebase_scan_cooldown_seconds,
            codebase_scan_depends_on=split_csv_values(parsed.codebase_scan_depends_on),
            codebase_scan_skip_prefixes=tuple(parsed.codebase_scan_skip_prefix),
            codebase_scan_commit_outputs=parsed.codebase_scan_commit_outputs,
            codebase_scan_commit_subject=parsed.codebase_scan_commit_subject,
            objective_refill_enabled=parsed.objective_refill_scan,
            objective_path=parsed.objective_path,
            objective_graph_path=parsed.objective_graph_path,
            objective_bundle_dir=parsed.objective_bundle_dir,
            objective_dataset_dir=parsed.objective_dataset_dir,
            objective_discovery_dir=parsed.objective_discovery_dir,
            objective_discovery_output_path=parsed.objective_discovery_output_path,
            objective_summary_prefix=parsed.objective_summary_prefix,
            objective_refine_goals=parsed.objective_refine_goals,
            objective_reconcile_goal_completion=parsed.objective_reconcile_goal_completion,
            objective_seed_interoperability_goals=parsed.objective_seed_interoperability_goals,
            objective_interoperability_focus=split_csv_values(parsed.objective_interoperability_focus),
            objective_max_interoperability_goals=parsed.objective_max_interoperability_goals,
            objective_ensure_tracking_document=parsed.objective_ensure_tracking_document,
            objective_ultimate_goal=parsed.objective_ultimate_goal,
            objective_root_evidence=split_csv_values(parsed.objective_root_evidence),
            objective_goal_prefix=parsed.objective_goal_prefix,
            objective_root_goal_id=parsed.objective_root_goal_id,
            objective_root_goal_title=parsed.objective_root_goal_title,
            objective_tracking_document_title=parsed.objective_tracking_document_title,
            objective_scan_min_open_tasks=parsed.objective_scan_min_open_tasks,
            objective_scan_max_findings=parsed.objective_scan_max_findings,
            objective_scan_cooldown_seconds=parsed.objective_scan_cooldown_seconds,
            objective_scan_depends_on=split_csv_values(parsed.objective_scan_depends_on),
            objective_max_refinement_children=parsed.objective_max_refinement_children,
            objective_max_refinement_depth=parsed.objective_max_refinement_depth,
            objective_persist_ast_dataset=parsed.objective_persist_ast_dataset,
            objective_write_todo_vector_index=parsed.objective_write_todo_vector_index,
            objective_todo_vector_index_path=parsed.objective_todo_vector_index_path,
            objective_surplus_findings_per_goal=parsed.objective_surplus_findings_per_goal,
            objective_surplus_min_terms_per_todo=parsed.objective_surplus_min_terms_per_todo,
            repo_root=REPO_ROOT,
            daemon_script_path=parsed.daemon_script_path or DAEMON_SCRIPT_PATH,
            supervisor_script_path=parsed.supervisor_script_path,
        )
    )
    if parsed.once:
        result = supervisor.run_once()
        record_objective_goal_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            objective_path=parsed.objective_path or paths["objective_goal_heap_path"],
            bundle_dir=parsed.objective_bundle_dir,
            dataset_dir=parsed.objective_dataset_dir,
            todo_vector_index_path=parsed.objective_todo_vector_index_path,
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
            min_open_tasks=parsed.objective_scan_min_open_tasks,
            max_findings=parsed.objective_scan_max_findings,
            cooldown_seconds=parsed.objective_scan_cooldown_seconds,
            surplus_findings_per_goal=parsed.objective_surplus_findings_per_goal,
            surplus_min_terms_per_todo=parsed.objective_surplus_min_terms_per_todo,
        )
        record_codebase_scan_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
            min_open_tasks=parsed.codebase_scan_min_open_tasks,
            max_findings=parsed.codebase_scan_max_findings,
            cooldown_seconds=parsed.codebase_scan_cooldown_seconds,
        )
        record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=daemon_events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        logger.info("Hallucinate multimodal-control supervisor check complete: %s", result)
        return
    supervisor.run_forever()


if __name__ == "__main__":
    main()
