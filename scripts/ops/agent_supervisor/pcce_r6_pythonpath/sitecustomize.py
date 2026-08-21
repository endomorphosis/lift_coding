"""Imported for every PCCE r6 supervisor/daemon process via PYTHONPATH.

The daemon is launched as ``python -m ...implementation_daemon``, so the
supervisor entry wrap does not run in the claim process. Patch
DatabaseImplementationDaemon when that module loads.
"""

from __future__ import annotations

import builtins
import logging
from typing import Any

_LOG = logging.getLogger("pcce.r6.coordination_mirror")
_TARGET = "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon"
_COMPLETED = frozenset({"completed", "complete", "done", "skipped"})
_real_import = builtins.__import__


def _mirror_completed_duckdb_tasks(daemon: Any) -> int:
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        TASK_SOURCE_QUERY_LIMIT,
    )

    mirrored = 0
    page = daemon.task_source.list_tasks(limit=TASK_SOURCE_QUERY_LIMIT)
    for task in page.tasks:
        status = str(task.status or "").strip().lower()
        if status not in _COMPLETED:
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


def _patch(module: Any) -> None:
    cls = getattr(module, "DatabaseImplementationDaemon", None)
    if cls is None or getattr(cls, "_pcce_r6_mirror_installed", False):
        return
    original = cls.sync_ready_tasks_into_coordination

    def sync_ready_tasks_into_coordination(self: Any) -> list[str]:
        try:
            mirrored = _mirror_completed_duckdb_tasks(self)
            _LOG.info(
                "mirrored %s completed DuckDB tasks into coordination",
                mirrored,
            )
        except Exception:
            _LOG.exception("failed to mirror completed DuckDB tasks")
        return original(self)

    cls.sync_ready_tasks_into_coordination = sync_ready_tasks_into_coordination
    cls._pcce_r6_mirror_installed = True


def _import(name, globals=None, locals=None, fromlist=(), level=0):  # type: ignore[no-untyped-def]
    module = _real_import(name, globals, locals, fromlist, level)
    if name == _TARGET or (
        fromlist and name == "ipfs_accelerate_py.agent_supervisor.todo_daemon"
    ):
        loaded = builtins.__import__("sys").modules.get(_TARGET)
        if loaded is not None:
            _patch(loaded)
    return module


builtins.__import__ = _import
