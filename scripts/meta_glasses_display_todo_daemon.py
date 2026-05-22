#!/usr/bin/env python3
"""Run the ipfs_datasets_py todo implementation daemon for display-widget work."""

from __future__ import annotations

import os
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
LOCAL_JDK = REPO_ROOT / ".tools" / "jdk17" / "jdk-17.0.18+8"
LOCAL_ANDROID_SDK = REPO_ROOT / ".tools" / "android-sdk"


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


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    os.chdir(REPO_ROOT)
    _bootstrap_android_validation_env()
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(IPFS_DATASETS_ROOT), existing] if existing else [str(IPFS_DATASETS_ROOT)]
    )

    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import main as daemon_main

    args = _with_default(args, "--todo-path", str(TODO_PATH))
    args = _with_default(args, "--state-dir", str(STATE_DIR))
    args = _with_default(args, "--task-prefix", "## MGW-")
    args = _with_default(args, "--state-prefix", "meta_glasses_display")
    daemon_main(args)


if __name__ == "__main__":
    main()
