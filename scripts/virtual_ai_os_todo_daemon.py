#!/usr/bin/env python3
"""Run the accelerator backlog implementation daemon for virtual-AI-OS work."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
TASK_BOARD_PATH = REPO_ROOT / "implementation_plan" / "docs" / (
    "19-virtual-ai-os-submodule-integration." + "to" + "do.md"
)
TASK_BOARD_PATH_OPTION = "--" + "to" + "do" + "-path"
TASK_BOARD_PATH_ENV = "HANDSFREE_VAI_OS_" + "TO" + "DO" + "_PATH"
STATE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "state"
STATE_DIR_ENV = "HANDSFREE_VAI_OS_STATE_DIR"
WORKTREE_ROOT = REPO_ROOT / "data" / "virtual_ai_os" / "worktrees"
WORKTREE_ROOT_ENV = "HANDSFREE_VAI_OS_WORKTREE_ROOT"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "objective_bundles"
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
    bootstrap_runtime_environment as _bootstrap_runtime_environment,
    resolve_and_ensure_bootstrap_paths as _resolve_and_ensure_bootstrap_paths,
    resolve_bootstrap_paths as _resolve_bootstrap_paths,
)
from ipfs_accelerate_py.agent_supervisor.implementation_daemon_runner import (  # noqa: E402
    ImplementationDaemonDefaults,
    apply_portal_implementation_daemon_defaults,
)

VIRTUAL_AI_OS_BOOTSTRAP_SPECS = (
    BootstrapPathSpec("task_board_path", TASK_BOARD_PATH, TASK_BOARD_PATH_ENV),
    BootstrapPathSpec("state_dir", STATE_DIR, STATE_DIR_ENV),
    BootstrapPathSpec("worktree_root", WORKTREE_ROOT, WORKTREE_ROOT_ENV),
)


def virtual_ai_os_bootstrap_paths() -> dict[str, Path]:
    """Return the repo-local bootstrap paths for the virtual-AI-OS daemon."""

    return _resolve_bootstrap_paths(REPO_ROOT, VIRTUAL_AI_OS_BOOTSTRAP_SPECS)


def ensure_virtual_ai_os_bootstrap_paths(paths: dict[str, Path] | None = None) -> dict[str, Path]:
    """Create local runtime directories used by the virtual-AI-OS daemon."""

    return _resolve_and_ensure_bootstrap_paths(
        REPO_ROOT,
        VIRTUAL_AI_OS_BOOTSTRAP_SPECS,
        ("state_dir", "worktree_root"),
        paths=paths,
    )


def _ensure_runtime_pythonpath() -> None:
    _bootstrap_runtime_environment(REPO_ROOT, (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT), chdir=False)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_virtual_ai_os_bootstrap_paths()
    _bootstrap_runtime_environment(REPO_ROOT, (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT))

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import main as daemon_main

    args = apply_portal_implementation_daemon_defaults(
        args,
        defaults=ImplementationDaemonDefaults(
            todo_path=paths["task_board_path"],
            state_dir=paths["state_dir"],
            task_prefix="## VAI-",
            state_prefix="virtual_ai_os",
            worktree_root=paths["worktree_root"],
            todo_path_flag=TASK_BOARD_PATH_OPTION,
            objective_path=OBJECTIVE_HEAP_PATH,
            objective_bundle_dir=OBJECTIVE_BUNDLE_DIR,
            worktree_submodule_paths=VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS,
        ),
    )
    daemon_main(args)


if __name__ == "__main__":
    main()
