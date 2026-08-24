"""Idempotent PCCE r6 DuckDB-to-coordination completion mirroring."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

COMPLETED_STATUSES = frozenset({"completed", "complete", "done", "skipped"})
_SUCCEEDED_COMPLETION_STATUS = "succeeded"


def _mirrored_task_cids(daemon: Any) -> set[str]:
    """Return the process-local cache used only to avoid redundant reads."""

    seen = getattr(daemon, "_pcce_r6_mirrored_task_cids", None)
    if seen is None:
        seen = set()
        daemon._pcce_r6_mirrored_task_cids = seen
    return seen


def _completion_status(readiness: Mapping[str, Any]) -> str:
    """Read the public coordination completion status without normalizing it."""

    return str(readiness.get("completion_status") or "")


def mirror_completed_duckdb_tasks(daemon: Any) -> int:
    """Copy DuckDB completions into coordination without replaying their body.

    The coordination completion body is durable evidence owned by the first
    successful writer. A later process must therefore treat an existing
    ``succeeded`` row as the idempotent result instead of replaying the PCCE
    bootstrap body over it. Any other completion status is an authority
    conflict and fails closed.
    """

    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (
        DatabaseCoordinationConflictError,
    )
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        TASK_SOURCE_QUERY_LIMIT,
    )

    seen = _mirrored_task_cids(daemon)
    mirrored = 0
    page = daemon.task_source.list_tasks(limit=TASK_SOURCE_QUERY_LIMIT)
    for task in page.tasks:
        source_status = str(task.status or "").strip().lower()
        if source_status not in COMPLETED_STATUSES:
            continue
        task_cid = str(task.task_cid)
        if task_cid in seen:
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
        readiness = daemon.coordinator.claimability(task_cid)
        completion_status = _completion_status(readiness)
        if completion_status == _SUCCEEDED_COMPLETION_STATUS:
            seen.add(task_cid)
            continue
        if completion_status:
            raise DatabaseCoordinationConflictError(
                "completed DuckDB task conflicts with existing coordination "
                f"completion status {completion_status!r} for {task_cid}"
            )

        try:
            daemon.coordinator.mark_task_complete(
                task.task_cid,
                status=_SUCCEEDED_COMPLETION_STATUS,
                body={
                    "schema": "pcce-r6-coordination-bootstrap-completion@1",
                    "authority": "duckdb_completed_mirror",
                    "source_status": source_status,
                    "task_alias": task.task_alias,
                    "task_revision": int(task.revision),
                },
            )
        except DatabaseCoordinationConflictError:
            raced_readiness = daemon.coordinator.claimability(task_cid)
            if _completion_status(raced_readiness) != _SUCCEEDED_COMPLETION_STATUS:
                raise

        seen.add(task_cid)
        mirrored += 1
    return mirrored
