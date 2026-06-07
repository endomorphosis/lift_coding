#!/usr/bin/env python3
"""Run the ipfs_datasets_py todo supervisor for Hallucinate multimodal-control work."""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from hallucinate_multimodal_control_todo_daemon import (  # noqa: E402
    IPFS_DATASETS_ROOT,
    DISCOVERY_DIR,
    ensure_hallucinate_multimodal_bootstrap_paths,
    record_retry_budget_findings,
)


logger = logging.getLogger("hallucinate_multimodal_control_todo_supervisor")
DAEMON_SCRIPT_PATH = REPO_ROOT / "scripts" / "hallucinate_multimodal_control_todo_daemon.py"


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_hallucinate_multimodal_bootstrap_paths()
    os.chdir(REPO_ROOT)
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(IPFS_DATASETS_ROOT), existing] if existing else [str(IPFS_DATASETS_ROOT)]
    )

    args = _with_default(args, "--todo-path", str(paths["todo_path"]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## HAO-")
    args = _with_default(args, "--state-prefix", "hallucinate_multimodal_control")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))

    from ipfs_datasets_py.optimizers.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor,
        PortalSupervisorConfig,
        parse_args,
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
    record_retry_budget_findings(
        todo_path=parsed.todo_path,
        events_path=daemon_events_path,
        strategy_path=strategy_path,
        discovery_dir=DISCOVERY_DIR,
        task_header_prefix=parsed.task_prefix,
    )
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
            implementation_timeout=parsed.implementation_timeout,
            use_ephemeral_worktree=parsed.implement and not parsed.no_ephemeral_worktree,
            worktree_root=parsed.worktree_root,
            repo_root=REPO_ROOT,
            daemon_script_path=DAEMON_SCRIPT_PATH,
        )
    )
    if parsed.once:
        result = supervisor.run_once()
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