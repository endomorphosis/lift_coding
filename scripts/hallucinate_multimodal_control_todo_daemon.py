#!/usr/bin/env python3
"""Run the generalized accelerator backlog daemon for Hallucinate multimodal-control work."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DEFAULT_TODO_PATH = REPO_ROOT / "hallucinate_app" / "docs" / ("MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL." + "to" + "do.md")
TASK_BOARD_PATH_OPTION = "--" + "to" + "do" + "-path"
TASK_BOARD_PATH_KEY = "to" + "do_path"
DEFAULT_OBJECTIVE_GOAL_HEAP_PATH = Path(
    os.environ.get(
        "HANDSFREE_HAO_OBJECTIVE_GOAL_HEAP_PATH",
        str(REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"),
    )
)
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "discovery"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "objective_bundles"
OBJECTIVE_DATASET_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "objective_datasets"
OBJECTIVE_TODO_VECTOR_INDEX_PATH = OBJECTIVE_BUNDLE_DIR / "todo_vector_index.json"
VALIDATION_RETRY_BUDGET = 3
MERGE_RETRY_BUDGET = 3
OBJECTIVE_SCAN_MIN_OPEN_TASKS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_MIN_OPEN_TASKS", "20"))
OBJECTIVE_SCAN_MAX_FINDINGS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_MAX_FINDINGS", "12"))
OBJECTIVE_SCAN_COOLDOWN_SECONDS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_COOLDOWN_SECONDS", "900"))
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL", "6"))
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO", "4"))
CODEBASE_SCAN_MIN_OPEN_TASKS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_MIN_OPEN_TASKS", "5"))
CODEBASE_SCAN_MAX_FINDINGS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_MAX_FINDINGS", "5"))
CODEBASE_SCAN_COOLDOWN_SECONDS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_COOLDOWN_SECONDS", "21600"))
CODEBASE_SCAN_SKIP_PREFIXES = (
    "data/hallucinate_multimodal_control/discovery/",
    "data/hallucinate_multimodal_control/objective_bundles/",
    "data/hallucinate_multimodal_control/objective_datasets/",
    "data/hallucinate_multimodal_control/state/",
    "data/hallucinate_multimodal_control/worktrees/",
    "data/meta_glasses_display_widgets/discovery/",
    "data/meta_glasses_display_widgets/state/",
    "data/meta_glasses_display_widgets/worktrees/",
    "data/virtual_ai_os/discovery/",
    "data/virtual_ai_os/objective_bundles/",
    "data/virtual_ai_os/objective_datasets/",
    "data/virtual_ai_os/state/",
    "data/virtual_ai_os/worktrees/",
)
HALLUCINATE_WORKTREE_SUBMODULE_PATHS = ("hallucinate_app", "ipfs_datasets_py", "swissknife")

logger = logging.getLogger("hallucinate_multimodal_control_todo_daemon")


def hallucinate_multimodal_bootstrap_paths() -> dict[str, Path]:
    todo_path = Path(os.environ.get("HANDSFREE_HAO_TODO_PATH", str(DEFAULT_TODO_PATH)))
    state_dir = Path(os.environ.get("HANDSFREE_HAO_STATE_DIR", str(DEFAULT_STATE_DIR)))
    worktree_root = Path(os.environ.get("HANDSFREE_HAO_WORKTREE_ROOT", str(DEFAULT_WORKTREE_ROOT)))
    objective_goal_heap_path = Path(
        os.environ.get("HANDSFREE_HAO_OBJECTIVE_GOAL_HEAP_PATH", str(DEFAULT_OBJECTIVE_GOAL_HEAP_PATH))
    )
    return {
        "repo_root": REPO_ROOT,
        "todo_path": todo_path,
        "objective_goal_heap_path": objective_goal_heap_path,
        "state_dir": state_dir,
        "worktree_root": worktree_root,
    }


def ensure_hallucinate_multimodal_bootstrap_paths(
    paths: dict[str, Path] | None = None,
) -> dict[str, Path]:
    resolved = paths or hallucinate_multimodal_bootstrap_paths()
    resolved["state_dir"].mkdir(parents=True, exist_ok=True)
    resolved["worktree_root"].mkdir(parents=True, exist_ok=True)
    return resolved


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def _ensure_ipfs_accelerate_path() -> None:
    if str(IPFS_ACCELERATE_ROOT) not in sys.path:
        sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))


def _ensure_runtime_pythonpath() -> None:
    _ensure_ipfs_accelerate_path()
    for path in (IPFS_DATASETS_ROOT,):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    existing = os.environ.get("PYTHONPATH", "")
    paths = [str(IPFS_ACCELERATE_ROOT), str(IPFS_DATASETS_ROOT)]
    os.environ["PYTHONPATH"] = os.pathsep.join([*paths, existing] if existing else paths)


def _task_prefix_from_header(task_header_prefix: str) -> str:
    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import task_id_prefix

    return task_id_prefix(task_header_prefix or "## HAO-")


def _task_ids_from_todo(todo_text: str, *, task_prefix: str) -> list[str]:
    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import task_ids_from_todo_text

    return task_ids_from_todo_text(todo_text, task_prefix=task_prefix)


def _discovery_output_path(repo_root: Path, discovery_dir: Path) -> str:
    try:
        return discovery_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "data/hallucinate_multimodal_control/discovery"


def _objective_bundle_dir(repo_root: Path, bundle_dir: Path | None) -> Path:
    if bundle_dir is not None:
        return bundle_dir
    return repo_root / "data" / "hallucinate_multimodal_control" / "objective_bundles"


def _objective_dataset_dir(repo_root: Path, dataset_dir: Path | None) -> Path:
    if dataset_dir is not None:
        return dataset_dir
    return repo_root / "data" / "hallucinate_multimodal_control" / "objective_datasets"


def record_objective_goal_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    state_path: Path | None = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_task_state.json",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    objective_path: Path = DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
    bundle_dir: Path | None = None,
    dataset_dir: Path | None = None,
    todo_vector_index_path: Path | None = None,
    task_header_prefix: str = "## HAO-",
    repo_root: Path = REPO_ROOT,
    min_open_tasks: int = OBJECTIVE_SCAN_MIN_OPEN_TASKS,
    max_findings: int = OBJECTIVE_SCAN_MAX_FINDINGS,
    cooldown_seconds: int = OBJECTIVE_SCAN_COOLDOWN_SECONDS,
    surplus_findings_per_goal: int = OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL,
    surplus_min_terms_per_todo: int = OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO,
    force: bool = False,
) -> list[dict[str, object]]:
    """Feed the HAO board from missing evidence in the objective heap."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import record_objective_backlog_findings

    task_prefix = _task_prefix_from_header(task_header_prefix)
    todo_text = todo_path.read_text(encoding="utf-8") if todo_path.exists() else ""
    depends_on = ["HAO-013"] if "HAO-013" in _task_ids_from_todo(todo_text, task_prefix=task_prefix) else []
    return record_objective_backlog_findings(
        repo_root=repo_root,
        objective_path=objective_path,
        todo_path=todo_path,
        discovery_dir=discovery_dir,
        bundle_dir=_objective_bundle_dir(repo_root, bundle_dir),
        dataset_dir=_objective_dataset_dir(repo_root, dataset_dir),
        strategy_path=strategy_path,
        state_path=state_path,
        task_prefix=task_prefix,
        depends_on=depends_on,
        min_open_tasks=min_open_tasks,
        max_findings=max_findings,
        cooldown_seconds=cooldown_seconds,
        force=force,
        write_todo_vector_index=True,
        todo_vector_index_path=todo_vector_index_path or _objective_bundle_dir(repo_root, bundle_dir) / "todo_vector_index.json",
        surplus_findings_per_goal=surplus_findings_per_goal,
        surplus_min_terms_per_todo=surplus_min_terms_per_todo,
        summary_prefix="Close virtual AI OS objective gap",
        discovery_output_path=_discovery_output_path(repo_root, discovery_dir),
        commit_outputs=True,
        commit_subject="HAO: record objective goal backlog findings",
    )


def record_codebase_scan_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    state_path: Path | None = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_task_state.json",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## HAO-",
    repo_root: Path = REPO_ROOT,
    min_open_tasks: int = CODEBASE_SCAN_MIN_OPEN_TASKS,
    max_findings: int = CODEBASE_SCAN_MAX_FINDINGS,
    cooldown_seconds: int = CODEBASE_SCAN_COOLDOWN_SECONDS,
    force: bool = False,
) -> list[dict[str, object]]:
    """Feed the HAO board with accelerator static-scan findings when backlog runs low."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import record_codebase_scan_findings as record_scan

    task_prefix = _task_prefix_from_header(task_header_prefix)
    todo_text = todo_path.read_text(encoding="utf-8") if todo_path.exists() else ""
    depends_on = ["HAO-013"] if "HAO-013" in _task_ids_from_todo(todo_text, task_prefix=task_prefix) else []
    return record_scan(
        todo_path=todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo_root,
        task_prefix=task_prefix,
        depends_on=depends_on,
        min_open_tasks=min_open_tasks,
        max_findings=max_findings,
        cooldown_seconds=cooldown_seconds,
        force=force,
        discovery_output_path=_discovery_output_path(repo_root, discovery_dir),
        skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
        commit_outputs=True,
        commit_subject="HAO: record codebase scan backlog findings",
    )


def record_retry_budget_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    events_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_events.jsonl",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## HAO-",
    retry_budget: int = VALIDATION_RETRY_BUDGET,
    merge_retry_budget: int = MERGE_RETRY_BUDGET,
) -> list[dict[str, object]]:
    """Turn repeated validation or merge failures into accelerator backlog items."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (
        git_toplevel_for_path,
        record_retry_budget_findings as record_retries,
    )

    task_prefix = _task_prefix_from_header(task_header_prefix)
    todo_text = todo_path.read_text(encoding="utf-8") if todo_path.exists() else ""
    validation_depends_on = ["HAO-013"] if "HAO-013" in _task_ids_from_todo(todo_text, task_prefix=task_prefix) else []
    inferred_repo_root = git_toplevel_for_path(todo_path.parent) or REPO_ROOT
    findings = record_retries(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        task_header_prefix_value=task_header_prefix,
        task_prefix=task_prefix,
        validation_retry_budget=retry_budget,
        merge_retry_budget=merge_retry_budget,
        validation_depends_on=validation_depends_on,
        discovery_output_path=_discovery_output_path(inferred_repo_root, discovery_dir),
        commit_outputs=True,
        repo_root=inferred_repo_root,
        commit_subject="HAO: record retry-budget guardrail outputs",
    )
    for finding in findings:
        if finding.get("failure_kind") == "validation":
            finding.pop("failure_kind", None)
    return findings


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_hallucinate_multimodal_bootstrap_paths()
    os.chdir(REPO_ROOT)
    _ensure_runtime_pythonpath()

    args = _with_default(args, TASK_BOARD_PATH_OPTION, str(paths[TASK_BOARD_PATH_KEY]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## HAO-")
    args = _with_default(args, "--state-prefix", "hallucinate_multimodal_control")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
        LLM_MERGE_RESOLVER_COMMAND_ENV,
        LLM_MERGE_RESOLVER_TIMEOUT_ENV,
        PortalImplementationDaemon,
        parse_args,
    )

    parsed = parse_args(args)
    logging.basicConfig(
        level=getattr(logging, parsed.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if parsed.llm_merge_resolver_command:
        os.environ[LLM_MERGE_RESOLVER_COMMAND_ENV] = parsed.llm_merge_resolver_command
    if parsed.llm_merge_resolver_timeout_seconds is not None:
        os.environ[LLM_MERGE_RESOLVER_TIMEOUT_ENV] = str(parsed.llm_merge_resolver_timeout_seconds)
    state_path = parsed.state_dir / f"{parsed.state_prefix}_task_state.json"
    strategy_path = parsed.state_dir / f"{parsed.state_prefix}_strategy.json"
    events_path = parsed.state_dir / f"{parsed.state_prefix}_events.jsonl"
    daemon = PortalImplementationDaemon(
        todo_path=parsed.todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        events_path=events_path,
        repo_root=REPO_ROOT,
        task_header_prefix=parsed.task_prefix,
        implement=parsed.implement,
        implementation_command=parsed.implementation_command or None,
        implementation_timeout=parsed.implementation_timeout or DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
        use_ephemeral_worktree=parsed.implement and not parsed.no_ephemeral_worktree,
        worktree_root=parsed.worktree_root,
        worktree_submodule_paths=parsed.worktree_submodule_path or HALLUCINATE_WORKTREE_SUBMODULE_PATHS,
        llm_merge_resolver_command=parsed.llm_merge_resolver_command or None,
        llm_merge_resolver_timeout_seconds=parsed.llm_merge_resolver_timeout_seconds,
    )

    while True:
        objective_findings = record_objective_goal_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            objective_path=paths["objective_goal_heap_path"],
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
        )
        if objective_findings:
            logger.warning("Recorded Hallucinate objective-goal findings before daemon pass: %s", objective_findings)
        scan_findings = record_codebase_scan_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
        )
        if scan_findings:
            logger.warning("Recorded Hallucinate codebase-scan findings before daemon pass: %s", scan_findings)
        findings = record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        if findings:
            logger.warning("Recorded Hallucinate retry-budget findings before daemon pass: %s", findings)
        result = daemon.run_once()
        findings = record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        if findings:
            logger.warning("Recorded Hallucinate retry-budget findings after daemon pass: %s", findings)
        objective_findings = record_objective_goal_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            objective_path=paths["objective_goal_heap_path"],
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
        )
        if objective_findings:
            logger.warning("Recorded Hallucinate objective-goal findings after daemon pass: %s", objective_findings)
        scan_findings = record_codebase_scan_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
        )
        if scan_findings:
            logger.warning("Recorded Hallucinate codebase-scan findings after daemon pass: %s", scan_findings)
        logger.info("Hallucinate multimodal-control daemon pass complete: %s", result)
        if parsed.once:
            break
        time.sleep(parsed.interval)


if __name__ == "__main__":
    main()
