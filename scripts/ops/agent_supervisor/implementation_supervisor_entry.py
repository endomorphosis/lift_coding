#!/usr/bin/env python3
"""Generic lift-coding entry for the canonical nested supervisor runtime.

Keep the composed control checkout as cwd/repository root while importing the
supervisor implementation from the exact accelerator gitlink. Current runtime
code owns DuckDB readiness synchronization; campaign-specific monkey patches
must not be installed here.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (  # noqa: E402
    main as _supervisor_main,
)


def main() -> int:
    return int(_supervisor_main())


if __name__ == "__main__":
    raise SystemExit(main())
