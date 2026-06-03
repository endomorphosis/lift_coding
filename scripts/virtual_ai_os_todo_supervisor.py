#!/usr/bin/env python3
"""Run the accelerator backlog supervisor for virtual-AI-OS work."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    env_int as _env_int,
    repo_relative_or_default as _repo_relative_or_default,
    task_board_filename as _task_board_filename,
    task_board_path_option as _task_board_path_option,
)

DEFAULT_TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    _task_board_filename("19-virtual-ai-os-submodule-integration")
)
TASK_BOARD_PATH_OPTION = _task_board_path_option()
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "virtual_ai_os" / "worktrees"
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "virtual_ai_os_todo_daemon.py"
DISCOVERY_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "discovery"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_GRAPH_PATH = REPO_ROOT / "data" / "virtual_ai_os" / "objective_graph.json"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "objective_bundles"
OBJECTIVE_DATASET_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "objective_datasets"
OBJECTIVE_TODO_VECTOR_INDEX_PATH = OBJECTIVE_BUNDLE_DIR / "todo_vector_index.json"
DISCOVERY_OUTPUT_PATH = _repo_relative_or_default(
    DISCOVERY_DIR,
    REPO_ROOT,
    "data/virtual_ai_os/discovery",
)
OBJECTIVE_SCAN_MIN_OPEN_TASKS = _env_int("HANDSFREE_VAI_OS_OBJECTIVE_SCAN_MIN_OPEN_TASKS", 20)
OBJECTIVE_SCAN_MAX_FINDINGS = _env_int("HANDSFREE_VAI_OS_OBJECTIVE_SCAN_MAX_FINDINGS", 12)
OBJECTIVE_SCAN_COOLDOWN_SECONDS = _env_int("HANDSFREE_VAI_OS_OBJECTIVE_SCAN_COOLDOWN_SECONDS", 900)
OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL = _env_int("HANDSFREE_VAI_OS_OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL", 6)
OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO = _env_int("HANDSFREE_VAI_OS_OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO", 4)
# scanner-resolved: VAI-168 — "scripts/" in CODEBASE_SCAN_SKIP_PREFIXES is an intentional exclusion so the scanner ignores supervisor/daemon scripts that reference backlog task-board file paths by design, not deferred-work annotations.
CODEBASE_SCAN_SKIP_PREFIXES = (
    "scripts/",  # supervisor/daemon scripts reference backlog task-board file paths by design, not as code annotations
    "data/virtual_ai_os/discovery/",
    "data/virtual_ai_os/objective_bundles/",
    "data/virtual_ai_os/objective_datasets/",
    "data/virtual_ai_os/state/",
    "data/virtual_ai_os/worktrees/",
    "data/hallucinate_multimodal_control/discovery/",
    "data/hallucinate_multimodal_control/state/",
    "data/hallucinate_multimodal_control/worktrees/",
    "data/meta_glasses_display_widgets/discovery/",
    "data/meta_glasses_display_widgets/state/",
    "data/meta_glasses_display_widgets/worktrees/",
)
VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS = (
    "external/ipfs_datasets",
    "external/ipfs_accelerate",
    "external/ipfs_kit",
    "Mcp-Plus-Plus",
    "swissknife",
    "hallucinate_app",
)

if str(IPFS_ACCELERATE_ROOT) not in sys.path:
    sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))

from ipfs_accelerate_py.agent_supervisor.wrapper_utils import (  # noqa: E402
    BootstrapPathSpec,
    build_bootstrap_path_ensurer as _build_bootstrap_path_ensurer,
    build_bootstrap_path_resolver as _build_bootstrap_path_resolver,
    build_default_llm_merge_resolver_command_callback as _build_default_llm_merge_resolver_command_callback,
    build_runtime_environment_callback as _build_runtime_environment_callback,
    env_csv_tuple as _env_csv_tuple,
)
from ipfs_accelerate_py.agent_supervisor.implementation_supervisor_runner import (  # noqa: E402
    CodebaseRefillDefaults,
    ImplementationSupervisorDefaults,
    ObjectiveRefillDefaults,
    apply_portal_implementation_supervisor_defaults,
)

VIRTUAL_AI_OS_INTEROPERABILITY_FOCUS = _env_csv_tuple(
    "HANDSFREE_VAI_OS_INTEROPERABILITY_FOCUS",
    "hallucinate_app",
)
VIRTUAL_AI_OS_BOOTSTRAP_SPECS = (
    BootstrapPathSpec("todo_path", DEFAULT_TODO_PATH, "HANDSFREE_VAI_OS_TODO_PATH"),
    BootstrapPathSpec("state_dir", DEFAULT_STATE_DIR, "HANDSFREE_VAI_OS_STATE_DIR"),
    BootstrapPathSpec("worktree_root", DEFAULT_WORKTREE_ROOT, "HANDSFREE_VAI_OS_WORKTREE_ROOT"),
)
_enter_runtime_environment = _build_runtime_environment_callback(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
)
_ensure_runtime_pythonpath = _build_runtime_environment_callback(
    REPO_ROOT,
    (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT),
    chdir=False,
)
virtual_ai_os_bootstrap_paths = _build_bootstrap_path_resolver(REPO_ROOT, VIRTUAL_AI_OS_BOOTSTRAP_SPECS)
ensure_virtual_ai_os_bootstrap_paths = _build_bootstrap_path_ensurer(
    REPO_ROOT,
    VIRTUAL_AI_OS_BOOTSTRAP_SPECS,
    ("state_dir", "worktree_root"),
)
_default_llm_merge_resolver_command = _build_default_llm_merge_resolver_command_callback(
    primary_env_var="HANDSFREE_VAI_OS_LLM_MERGE_RESOLVER_COMMAND"
)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_virtual_ai_os_bootstrap_paths()
    _enter_runtime_environment()

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import main as supervisor_main

    args = apply_portal_implementation_supervisor_defaults(
        args,
        defaults=ImplementationSupervisorDefaults(
            todo_path=paths["todo_path"],
            state_dir=paths["state_dir"],
            task_prefix="## VAI-",
            state_prefix="virtual_ai_os",
            worktree_root=paths["worktree_root"],
            daemon_script_path=DAEMON_SCRIPT_PATH,
            supervisor_script_path=Path(__file__).resolve(),
            llm_merge_resolver_command=_default_llm_merge_resolver_command(),
            worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
        ),
        objective=ObjectiveRefillDefaults(
            objective_path=OBJECTIVE_HEAP_PATH,
            objective_graph_path=OBJECTIVE_GRAPH_PATH,
            objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
            objective_dataset_dir=OBJECTIVE_DATASET_DIR,
            objective_discovery_dir=DISCOVERY_DIR,
            objective_discovery_output_path=DISCOVERY_OUTPUT_PATH,
            objective_scan_min_open_tasks=OBJECTIVE_SCAN_MIN_OPEN_TASKS,
            objective_scan_max_findings=OBJECTIVE_SCAN_MAX_FINDINGS,
            objective_scan_cooldown_seconds=OBJECTIVE_SCAN_COOLDOWN_SECONDS,
            objective_todo_vector_index_path=OBJECTIVE_TODO_VECTOR_INDEX_PATH,
            objective_surplus_findings_per_goal=OBJECTIVE_SURPLUS_FINDINGS_PER_GOAL,
            objective_surplus_min_terms_per_todo=OBJECTIVE_SURPLUS_MIN_TERMS_PER_TODO,
            objective_interoperability_focus=VIRTUAL_AI_OS_INTEROPERABILITY_FOCUS,
            seed_interoperability_goals=True,
        ),
        codebase=CodebaseRefillDefaults(
            codebase_scan_discovery_dir=DISCOVERY_DIR,
            codebase_scan_discovery_output_path=DISCOVERY_OUTPUT_PATH,
            codebase_scan_min_open_tasks=0,
            codebase_scan_skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
        ),
    )
    supervisor_main(args)


if __name__ == "__main__":
    main()
