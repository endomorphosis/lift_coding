"""Landlock-safe pytest configuration for the task-evidence suite.

Under the inherited Landlock ABI-3 write fence only the worktree and private
validation home are writable.  Pytest defaults ``log_file`` to ``os.devnull``
and opens it for write during configure, which fails with PermissionError.
Point the session log at TMPDIR (or a worktree path) instead.
"""

from __future__ import annotations

import os
from pathlib import Path


def pytest_configure(config) -> None:  # type: ignore[no-untyped-def]
    try:
        current = config.getoption("log_file")
    except (ValueError, AttributeError):
        current = None
    if not current:
        try:
            current = config.getini("log_file")
        except ValueError:
            current = None
    if current:
        return
    base = os.environ.get("TMPDIR") or os.environ.get("XDG_CACHE_HOME") or ".pytest_cache"
    path = Path(base) / "pytest-task-evidence-landlock.log"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    except OSError:
        path = Path(".pytest_cache") / "pytest-task-evidence-landlock.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    if hasattr(config.option, "log_file"):
        config.option.log_file = str(path)
