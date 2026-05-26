#!/usr/bin/env python3
"""Run the accelerator todo supervisor for virtual-AI-OS work."""

from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DEFAULT_TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "19-virtual-ai-os-submodule-integration.todo.md"
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "virtual_ai_os" / "worktrees"
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "virtual_ai_os_todo_daemon.py"
DISCOVERY_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "discovery"
OBJECTIVE_HEAP_PATH = REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"
OBJECTIVE_GRAPH_PATH = REPO_ROOT / "data" / "virtual_ai_os" / "objective_graph.json"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "objective_bundles"
OBJECTIVE_DATASET_DIR = REPO_ROOT / "data" / "virtual_ai_os" / "objective_datasets"
CODEBASE_SCAN_SKIP_PREFIXES = (
    "data/virtual_ai_os/discovery/",
    "data/virtual_ai_os/objective_bundles/",
    "data/virtual_ai_os/objective_datasets/",
    "data/virtual_ai_os/state/",
    "data/virtual_ai_os/worktrees/",
)
VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS = (
    "external/ipfs_datasets",
    "external/ipfs_accelerate",
    "external/ipfs_kit",
    "Mcp-Plus-Plus",
    "swissknife",
    "hallucinate_app",
)


def virtual_ai_os_bootstrap_paths() -> dict[str, Path]:
    """Return the repo-local bootstrap contract for virtual-AI-OS supervision."""

    todo_path = Path(os.environ.get("HANDSFREE_VAI_OS_TODO_PATH", str(DEFAULT_TODO_PATH)))
    state_dir = Path(os.environ.get("HANDSFREE_VAI_OS_STATE_DIR", str(DEFAULT_STATE_DIR)))
    worktree_root = Path(
        os.environ.get("HANDSFREE_VAI_OS_WORKTREE_ROOT", str(DEFAULT_WORKTREE_ROOT))
    )
    return {
        "repo_root": REPO_ROOT,
        "todo_path": todo_path,
        "state_dir": state_dir,
        "worktree_root": worktree_root,
    }


def ensure_virtual_ai_os_bootstrap_paths(paths: dict[str, Path] | None = None) -> dict[str, Path]:
    """Create the local state and worktree directories used by the supervisor."""

    resolved = paths or virtual_ai_os_bootstrap_paths()
    resolved["state_dir"].mkdir(parents=True, exist_ok=True)
    resolved["worktree_root"].mkdir(parents=True, exist_ok=True)
    return resolved


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
    configured = os.environ.get("HANDSFREE_VAI_OS_LLM_MERGE_RESOLVER_COMMAND", "").strip()
    if configured:
        return configured
    configured = os.environ.get("IPFS_ACCELERATE_AGENT_LLM_MERGE_RESOLVER_COMMAND", "").strip()
    if configured:
        return configured
    codex = shutil.which("codex")
    if not codex:
        return ""
    return f"{shlex.quote(codex)} exec --dangerously-bypass-approvals-and-sandbox -C . -"


def _ensure_runtime_pythonpath() -> None:
    for path in (IPFS_ACCELERATE_ROOT, IPFS_DATASETS_ROOT):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    existing = os.environ.get("PYTHONPATH", "")
    paths = [str(IPFS_ACCELERATE_ROOT), str(IPFS_DATASETS_ROOT)]
    os.environ["PYTHONPATH"] = os.pathsep.join([*paths, existing] if existing else paths)


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_virtual_ai_os_bootstrap_paths()
    os.chdir(REPO_ROOT)
    _ensure_runtime_pythonpath()

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import main as supervisor_main

    args = _with_default(args, "--todo-path", str(paths["todo_path"]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## VAI-")
    args = _with_default(args, "--state-prefix", "virtual_ai_os")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))
    args = _with_default(args, "--daemon-script-path", str(DAEMON_SCRIPT_PATH))
    args = _with_default(args, "--supervisor-script-path", str(Path(__file__).resolve()))
    args = _with_default(args, "--max-restarts", "0")
    resolver_command = _default_llm_merge_resolver_command()
    if resolver_command:
        args = _with_default(args, "--llm-merge-resolver-command", resolver_command)
    args = _with_repeated_default(args, "--worktree-submodule-path", VIRTUAL_AI_OS_WORKTREE_SUBMODULE_PATHS)
    args = _with_flag_default(args, "--objective-refill-scan")
    args = _with_default(args, "--objective-path", str(OBJECTIVE_HEAP_PATH))
    args = _with_default(args, "--objective-graph-path", str(OBJECTIVE_GRAPH_PATH))
    args = _with_default(args, "--objective-bundle-dir", str(OBJECTIVE_BUNDLE_DIR))
    args = _with_default(args, "--objective-dataset-dir", str(OBJECTIVE_DATASET_DIR))
    args = _with_default(args, "--objective-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--objective-discovery-output-path", "data/virtual_ai_os/discovery")
    args = _with_default(args, "--objective-scan-min-open-tasks", "0")
    args = _with_flag_default(args, "--codebase-refill-scan")
    args = _with_default(args, "--codebase-scan-discovery-dir", str(DISCOVERY_DIR))
    args = _with_default(args, "--codebase-scan-discovery-output-path", "data/virtual_ai_os/discovery")
    args = _with_default(args, "--codebase-scan-min-open-tasks", "0")
    args = _with_repeated_default(args, "--codebase-scan-skip-prefix", CODEBASE_SCAN_SKIP_PREFIXES)
    supervisor_main(args)


if __name__ == "__main__":
    main()
