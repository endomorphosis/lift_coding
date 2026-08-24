"""Regression coverage for the PCCE r6 coordination completion mirror."""

from __future__ import annotations

import builtins
import importlib.util
import runpy
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = ROOT / "external" / "ipfs_accelerate"
HOOK_ROOT = ROOT / "scripts" / "ops" / "agent_supervisor" / "pcce_r6_pythonpath"
ENTRY_PATH = ROOT / "scripts" / "ops" / "agent_supervisor" / "implementation_supervisor_entry.py"
SITECUSTOMIZE_PATH = HOOK_ROOT / "sitecustomize.py"

for import_root in (ACCEL_ROOT, HOOK_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

import pcce_r6_completion_mirror as completion_mirror  # noqa: E402
from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (  # noqa: E402
    DatabaseCoordinationConflictError,
    duckdb_available,
    open_database_coordinator,
)


def _source_task(
    task_cid: str,
    *,
    alias: str | None = None,
    status: str = "completed",
    dependencies: tuple[str, ...] = (),
    revision: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        task_cid=task_cid,
        task_alias=alias or task_cid,
        status=status,
        dependencies=dependencies,
        revision=revision,
    )


class _TaskSource:
    def __init__(self, *tasks: SimpleNamespace) -> None:
        self.tasks = list(tasks)
        self.limits: list[int] = []

    def list_tasks(self, *, limit: int) -> SimpleNamespace:
        self.limits.append(limit)
        return SimpleNamespace(tasks=list(self.tasks))


class _NoMarkCoordinator:
    def __init__(self, coordinator: Any) -> None:
        self._coordinator = coordinator
        self.mark_calls = 0

    def register_task(self, **kwargs: Any) -> dict[str, Any]:
        return self._coordinator.register_task(**kwargs)

    def claimability(self, task_cid: str) -> dict[str, Any]:
        return self._coordinator.claimability(task_cid)

    def mark_task_complete(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self.mark_calls += 1
        raise AssertionError("an existing succeeded completion must not be replayed")


@pytest.mark.skipif(not duckdb_available(), reason="DuckDB coordination is required")
def test_rich_completion_body_is_preserved_and_later_mirror_unblocks_dependent(
    tmp_path: Path,
) -> None:
    coordinator = open_database_coordinator(tmp_path / "coordination.duckdb")
    rich_body = {
        "schema": "ipfs_accelerate_py/agent-supervisor/task-completion@1",
        "control_completion": {
            "receipt_cid": "baguqeera-rich-primary-evidence",
            "revision": 17,
        },
        "evidence": {"artifact_sha256": "a" * 64, "review": "approved"},
    }
    try:
        coordinator.register_task(task_cid="task:rich", task_id="PCCE-RICH")
        coordinator.mark_task_complete(
            "task:rich",
            status="succeeded",
            body=rich_body,
        )
        coordinator.register_task(
            task_cid="task:later",
            task_id="PCCE-LATER",
            dependency_task_cids=("task:rich",),
        )
        coordinator.register_task(
            task_cid="task:dependent",
            task_id="PCCE-DEPENDENT",
            dependency_task_cids=("task:later",),
        )
        daemon = SimpleNamespace(
            task_source=_TaskSource(
                _source_task("task:rich", alias="PCCE-RICH", revision=17),
                _source_task(
                    "task:later",
                    alias="PCCE-LATER",
                    status="done",
                    dependencies=("task:rich",),
                    revision=18,
                ),
            ),
            coordinator=coordinator,
        )

        assert completion_mirror.mirror_completed_duckdb_tasks(daemon) == 1

        completions = {
            item["task_cid"]: item
            for item in coordinator.coordination_registry_projection()[
                "logical_completions"
            ]
        }
        assert completions["task:rich"] == {
            "task_cid": "task:rich",
            "status": "succeeded",
            "body": rich_body,
        }
        assert completions["task:later"]["body"] == {
            "schema": "pcce-r6-coordination-bootstrap-completion@1",
            "authority": "duckdb_completed_mirror",
            "source_status": "done",
            "task_alias": "PCCE-LATER",
            "task_revision": 18,
        }
        assert coordinator.claimability("task:dependent")["claimable"] is True
    finally:
        coordinator.close()


@pytest.mark.skipif(not duckdb_available(), reason="DuckDB coordination is required")
def test_fresh_process_idempotency_queries_public_state_without_marking(
    tmp_path: Path,
) -> None:
    coordinator = open_database_coordinator(tmp_path / "coordination.duckdb")
    try:
        coordinator.register_task(task_cid="task:complete", task_id="PCCE-COMPLETE")
        coordinator.mark_task_complete(
            "task:complete",
            status="succeeded",
            body={"receipt": {"cid": "baguqeera-authoritative"}},
        )
        proxy = _NoMarkCoordinator(coordinator)
        source = _TaskSource(
            _source_task("task:complete", alias="PCCE-COMPLETE", revision=9)
        )

        first_process = SimpleNamespace(task_source=source, coordinator=proxy)
        second_process = SimpleNamespace(task_source=source, coordinator=proxy)
        assert completion_mirror.mirror_completed_duckdb_tasks(first_process) == 0
        assert completion_mirror.mirror_completed_duckdb_tasks(second_process) == 0
        assert proxy.mark_calls == 0
    finally:
        coordinator.close()


@pytest.mark.skipif(not duckdb_available(), reason="DuckDB coordination is required")
@pytest.mark.parametrize("completion_status", ["prepared", "failed"])
def test_existing_non_success_completion_fails_closed_without_mark(
    tmp_path: Path,
    completion_status: str,
) -> None:
    coordinator = open_database_coordinator(tmp_path / f"{completion_status}.duckdb")
    try:
        coordinator.register_task(task_cid="task:conflict", task_id="PCCE-CONFLICT")
        coordinator.mark_task_complete(
            "task:conflict",
            status=completion_status,
            body={"authority": "existing", "status": completion_status},
        )
        proxy = _NoMarkCoordinator(coordinator)
        daemon = SimpleNamespace(
            task_source=_TaskSource(
                _source_task("task:conflict", alias="PCCE-CONFLICT")
            ),
            coordinator=proxy,
        )

        with pytest.raises(
            DatabaseCoordinationConflictError,
            match=rf"completion status '{completion_status}'",
        ):
            completion_mirror.mirror_completed_duckdb_tasks(daemon)
        assert proxy.mark_calls == 0
    finally:
        coordinator.close()


class _RacingCoordinator:
    def __init__(
        self,
        statuses: list[str],
        mark_error: BaseException,
    ) -> None:
        self.statuses = list(statuses)
        self.mark_error = mark_error
        self.claimability_calls = 0
        self.mark_calls = 0

    def register_task(self, **_kwargs: Any) -> dict[str, Any]:
        return {}

    def claimability(self, _task_cid: str) -> dict[str, Any]:
        self.claimability_calls += 1
        return {"completion_status": self.statuses.pop(0)}

    def mark_task_complete(self, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
        self.mark_calls += 1
        raise self.mark_error


def test_successful_completion_race_is_suppressed_after_public_reread() -> None:
    conflict = DatabaseCoordinationConflictError("completion raced")
    coordinator = _RacingCoordinator(["", "succeeded"], conflict)
    daemon = SimpleNamespace(
        task_source=_TaskSource(_source_task("task:race", alias="PCCE-RACE")),
        coordinator=coordinator,
    )

    assert completion_mirror.mirror_completed_duckdb_tasks(daemon) == 1
    assert coordinator.claimability_calls == 2
    assert coordinator.mark_calls == 1


@pytest.mark.parametrize("raced_status", ["prepared", "failed", ""])
def test_non_success_completion_race_propagates_original_conflict(
    raced_status: str,
) -> None:
    conflict = DatabaseCoordinationConflictError("completion raced to non-success")
    coordinator = _RacingCoordinator(["", raced_status], conflict)
    daemon = SimpleNamespace(
        task_source=_TaskSource(_source_task("task:race", alias="PCCE-RACE")),
        coordinator=coordinator,
    )

    with pytest.raises(DatabaseCoordinationConflictError) as excinfo:
        completion_mirror.mirror_completed_duckdb_tasks(daemon)
    assert excinfo.value is conflict
    assert coordinator.claimability_calls == 2
    assert coordinator.mark_calls == 1


def test_non_conflict_mark_failure_is_not_caught_or_reread() -> None:
    failure = RuntimeError("transport failed")
    coordinator = _RacingCoordinator([""], failure)
    daemon = SimpleNamespace(
        task_source=_TaskSource(_source_task("task:error", alias="PCCE-ERROR")),
        coordinator=coordinator,
    )

    with pytest.raises(RuntimeError) as excinfo:
        completion_mirror.mirror_completed_duckdb_tasks(daemon)
    assert excinfo.value is failure
    assert coordinator.claimability_calls == 1
    assert coordinator.mark_calls == 1


def _load_entry_module() -> Any:
    spec = importlib.util.spec_from_file_location("pcce_r6_mirror_entry_test", ENTRY_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_supervisor_entry_caller_uses_shared_fail_closed_mirror(monkeypatch) -> None:
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        DatabaseImplementationDaemon,
    )

    entry = _load_entry_module()
    assert entry.mirror_completed_duckdb_tasks is completion_mirror.mirror_completed_duckdb_tasks
    original_calls: list[str] = []

    def original_sync(_self: Any) -> list[str]:
        original_calls.append("original")
        return ["ready"]

    conflict = DatabaseCoordinationConflictError("fail closed")

    def conflicting_mirror(_self: Any) -> int:
        raise conflict

    monkeypatch.setattr(
        DatabaseImplementationDaemon,
        "sync_ready_tasks_into_coordination",
        original_sync,
    )
    monkeypatch.setattr(entry, "mirror_completed_duckdb_tasks", conflicting_mirror)
    entry._install_completed_dependency_mirror()

    daemon = object.__new__(DatabaseImplementationDaemon)
    with pytest.raises(DatabaseCoordinationConflictError) as excinfo:
        daemon.sync_ready_tasks_into_coordination()
    assert excinfo.value is conflict
    assert original_calls == []


def test_sitecustomize_caller_uses_shared_fail_closed_mirror(monkeypatch) -> None:
    from ipfs_accelerate_py.agent_supervisor.task_sources import duckdb_state

    monkeypatch.setattr(duckdb_state, "persist_quack_attach_token_vault", lambda: None)
    monkeypatch.setattr(threading.Thread, "start", lambda _self: None)
    real_import = builtins.__import__
    try:
        namespace = runpy.run_path(
            str(SITECUSTOMIZE_PATH),
            run_name="pcce_r6_sitecustomize_test",
        )
    finally:
        builtins.__import__ = real_import

    assert (
        namespace["mirror_completed_duckdb_tasks"]
        is completion_mirror.mirror_completed_duckdb_tasks
    )
    original_calls: list[str] = []

    class FakeDatabaseDaemon:
        def sync_ready_tasks_into_coordination(self) -> list[str]:
            original_calls.append("original")
            return ["ready"]

        def reconcile_terminal_portal_failures(self) -> list[dict[str, Any]]:
            return []

    conflict = DatabaseCoordinationConflictError("fail closed")

    def conflicting_mirror(_self: Any) -> int:
        raise conflict

    namespace["_patch_daemon"].__globals__["mirror_completed_duckdb_tasks"] = (
        conflicting_mirror
    )
    namespace["_patch_daemon"](
        SimpleNamespace(DatabaseImplementationDaemon=FakeDatabaseDaemon)
    )

    with pytest.raises(DatabaseCoordinationConflictError) as excinfo:
        FakeDatabaseDaemon().sync_ready_tasks_into_coordination()
    assert excinfo.value is conflict
    assert original_calls == []
