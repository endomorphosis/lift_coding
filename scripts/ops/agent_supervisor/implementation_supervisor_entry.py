#!/usr/bin/env python3
"""Lift-coding entry for PCCE implementation tracks.

Keep the control checkout as cwd/repo root and load supervisor code from the
accelerate gitlink. Do not re-root into external/ipfs_accelerate.

The operator seals Epic A completions in DuckDB. The lane-local coordination
store used by claim_next() does not see those rows unless they are mirrored,
so ready PCCE-020+ tasks would stay unclaimable. Mirror DuckDB completed
tasks into coordination before each claim pass so Epics B-H can drain.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
PCCE_R6_PYTHONPATH = Path(__file__).resolve().parent / "pcce_r6_pythonpath"
if str(PCCE_R6_PYTHONPATH) not in sys.path:
    sys.path.insert(0, str(PCCE_R6_PYTHONPATH))

from pcce_r6_completion_mirror import (  # noqa: E402
    mirror_completed_duckdb_tasks,
)


def _install_completed_dependency_mirror() -> None:
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        DatabaseImplementationDaemon,
    )

    original = DatabaseImplementationDaemon.sync_ready_tasks_into_coordination

    def sync_ready_tasks_into_coordination(self: Any) -> list[str]:
        mirror_completed_duckdb_tasks(self)
        return original(self)

    DatabaseImplementationDaemon.sync_ready_tasks_into_coordination = (
        sync_ready_tasks_into_coordination
    )


from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (  # noqa: E402
    main as _supervisor_main,
)


def main() -> int:
    _install_completed_dependency_mirror()
    return int(_supervisor_main())


if __name__ == "__main__":
    raise SystemExit(main())
