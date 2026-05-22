#!/usr/bin/env python3
"""Run the ipfs_datasets_py todo supervisor for display-widget work."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
WORKTREE_ROOT = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "worktrees"
LOCAL_JDK = REPO_ROOT / ".tools" / "jdk17" / "jdk-17.0.18+8"
LOCAL_ANDROID_SDK = REPO_ROOT / ".tools" / "android-sdk"
INITIAL_BACKLOG_TASK_IDS = tuple(f"MGW-{index:03d}" for index in range(1, 13))
INITIAL_BACKLOG_DEPENDENCIES = ", ".join(INITIAL_BACKLOG_TASK_IDS)

DISCOVERY_EXPANSION_TASK = f"""## MGW-013 Investigate implementation unknowns and expand the backlog

- Status: todo
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: {INITIAL_BACKLOG_DEPENDENCIES}
- Outputs: implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; rg -n "MGW-013|unknown unknowns|Discovery Expansion|discovered" implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Acceptance: After the initial backlog completes, investigate the Swissknife, HandsFree backend, mobile DAT bridge, external Meta DAT references, and hardware-free test harness code paths for missed work. Append new daemon-parseable MGW tasks for discovered gaps, or write a dated no-new-unknowns discovery report with evidence and commands run.
"""

SUPERVISOR_GUARDRAIL_TASK = """## MGW-014 Add supervisor validation-environment and retry-budget guardrails

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-013
- Outputs: scripts/meta_glasses_display_todo_supervisor.py, scripts/meta_glasses_display_todo_daemon.py, tests/test_meta_glasses_display_todo_queue.py, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; PYTHONPATH=external/ipfs_datasets python3 scripts/meta_glasses_display_todo_supervisor.py --once
- Acceptance: Discovered during MGW-010: Android validation needs the repo-local JDK 17/Android SDK environment, and repeated validation failures should become evidence-backed discovery follow-up items instead of indefinite retry loops. The supervisor documents/enforces the validation environment and records retry-budget findings as daemon-parseable backlog work.
"""


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def _bootstrap_android_validation_env() -> None:
    if (LOCAL_JDK / "bin" / "java").exists():
        os.environ["JAVA_HOME"] = str(LOCAL_JDK)
        os.environ["PATH"] = os.pathsep.join([str(LOCAL_JDK / "bin"), os.environ.get("PATH", "")])
    if (LOCAL_ANDROID_SDK / "platform-tools").exists():
        os.environ["ANDROID_HOME"] = str(LOCAL_ANDROID_SDK)
        os.environ["ANDROID_SDK_ROOT"] = str(LOCAL_ANDROID_SDK)
        os.environ["PATH"] = os.pathsep.join(
            [str(LOCAL_ANDROID_SDK / "platform-tools"), os.environ.get("PATH", "")]
        )


def _task_is_present(todo_text: str, task_id: str) -> bool:
    return f"## {task_id} " in todo_text


def ensure_post_initial_discovery_backlog(todo_path: Path = TODO_PATH) -> bool:
    """Keep the post-initial discovery expansion tasks in the supervised board."""
    if not todo_path.exists():
        return False

    todo_text = todo_path.read_text(encoding="utf-8")
    additions: list[str] = []

    if not _task_is_present(todo_text, "MGW-013"):
        additions.append(DISCOVERY_EXPANSION_TASK.strip())
    if not _task_is_present(todo_text, "MGW-014"):
        additions.append(SUPERVISOR_GUARDRAIL_TASK.strip())

    if not additions:
        return False

    updated = todo_text.rstrip() + "\n\n" + "\n\n".join(additions) + "\n"
    todo_path.write_text(updated, encoding="utf-8")
    return True


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    os.chdir(REPO_ROOT)
    _bootstrap_android_validation_env()
    ensure_post_initial_discovery_backlog(TODO_PATH)
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(IPFS_DATASETS_ROOT), existing] if existing else [str(IPFS_DATASETS_ROOT)]
    )

    from ipfs_datasets_py.optimizers.todo_daemon.implementation_supervisor import main as supervisor_main

    args = _with_default(args, "--todo-path", str(TODO_PATH))
    args = _with_default(args, "--state-dir", str(STATE_DIR))
    args = _with_default(args, "--task-prefix", "## MGW-")
    args = _with_default(args, "--state-prefix", "meta_glasses_display")
    args = _with_default(args, "--worktree-root", str(WORKTREE_ROOT))
    supervisor_main(args)


if __name__ == "__main__":
    main()
