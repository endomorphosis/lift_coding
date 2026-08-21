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

COMPLETED_STATUSES = frozenset({"completed", "complete", "done", "skipped"})


def _mirror_completed_duckdb_tasks(daemon: Any) -> int:
    """Copy DuckDB completed tasks into the lane coordination store."""

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        TASK_SOURCE_QUERY_LIMIT,
    )

    mirrored = 0
    page = daemon.task_source.list_tasks(limit=TASK_SOURCE_QUERY_LIMIT)
    for task in page.tasks:
        status = str(task.status or "").strip().lower()
        if status not in COMPLETED_STATUSES:
            continue
        daemon.coordinator.register_task(
            task_cid=task.task_cid,
            task_id=task.task_alias or task.task_cid,
            dependency_task_cids=tuple(str(dep) for dep in task.dependencies),
            body={
                "task_alias": task.task_alias,
                "status": task.status,
                "producer": "pcce-r6-completed-dependency-mirror",
            },
        )
        daemon.coordinator.mark_task_complete(
            task.task_cid,
            status="succeeded",
            body={
                "schema": "pcce-r6-coordination-bootstrap-completion@1",
                "authority": "duckdb_completed_mirror",
                "source_status": status,
                "task_alias": task.task_alias,
                "task_revision": int(task.revision),
            },
        )
        mirrored += 1
    return mirrored


def _install_completed_dependency_mirror() -> None:
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        PortalImplementationDaemon,
    )

    original = PortalImplementationDaemon.sync_ready_tasks_into_coordination

    def sync_ready_tasks_into_coordination(self: Any) -> list[str]:
        _mirror_completed_duckdb_tasks(self)
        return original(self)

    PortalImplementationDaemon.sync_ready_tasks_into_coordination = (
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
