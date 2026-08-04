from __future__ import annotations

import json
import signal
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import swissknife_parallel_implementation_supervisor as supervisor  # noqa: E402


class FakeProcess:
    def __init__(self, pid: int, returncode: int | None = None) -> None:
        self.pid = pid
        self.returncode = returncode

    def poll(self) -> int | None:
        return self.returncode

    def terminate(self) -> None:
        self.returncode = -signal.SIGTERM

    def kill(self) -> None:
        self.returncode = -signal.SIGKILL

    def wait(self, timeout: float | None = None) -> int:
        del timeout
        if self.returncode is None:
            self.returncode = 0
        return self.returncode


def _profile(tmp_path: Path, *, max_restarts: int = 0) -> Path:
    profile = {
        "repositoryRoot": str(tmp_path),
        "runtimeRoot": "runtime",
        "todoPath": "tasks.todo.md",
        "taskPrefix": "SCA",
        "statePrefix": "sca",
        "providers": {
            "laneAssignments": ["grok", "codex"],
            "commonEnvironment": {},
        },
        "parallelRuntime": {
            "enabled": True,
            "laneCount": 2,
            "mergeTargetBranch": "agent/test",
            "strictTaskSharding": True,
        },
        "bounds": {"maxRestarts": max_restarts},
    }
    path = tmp_path / "supervisor.json"
    path.write_text(json.dumps(profile), encoding="utf-8")
    return path


def _prepare_run(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    max_restarts: int = 0,
    process_factory: Callable[[supervisor.Lane], FakeProcess],
) -> tuple[Path, dict[int, Callable[[int, object], None]], list[int]]:
    config_path = _profile(tmp_path, max_restarts=max_restarts)
    handlers: dict[int, Callable[[int, object], None]] = {}
    spawn_counts = [0, 0]

    monkeypatch.setattr(
        supervisor,
        "require_swissknife_checkout_lease",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        supervisor,
        "_taskboard_validation",
        lambda *args, **kwargs: {"task_count": 2},
    )
    monkeypatch.setattr(
        supervisor.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(args[0], 0),
    )
    monkeypatch.setattr(
        supervisor,
        "_lane_command",
        lambda **kwargs: (
            ["fake-lane", str(kwargs["lane_index"])],
            tmp_path
            / "runtime"
            / "parallel"
            / "lanes"
            / f"lane-{kwargs['lane_index']:02d}"
            / "state",
        ),
    )

    def fake_signal(signum: int, handler: Callable[[int, object], None]) -> None:
        handlers[signum] = handler

    def fake_spawn(lane: supervisor.Lane, *, repo_root: Path) -> None:
        del repo_root
        spawn_counts[lane.index] += 1
        lane.process = process_factory(lane)
        lane.spawned_at = supervisor.time.monotonic()

    monkeypatch.setattr(supervisor.signal, "signal", fake_signal)
    monkeypatch.setattr(supervisor, "_spawn_lane", fake_spawn)
    return config_path, handlers, spawn_counts


def _final_status(tmp_path: Path) -> dict[str, Any]:
    path = tmp_path / "runtime/parallel/parallel_supervisor_status.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _lane(
    tmp_path: Path,
    *,
    pid: int = 101,
    returncode: int | None = None,
    spawned_at: float = 1.0,
) -> supervisor.Lane:
    return supervisor.Lane(
        index=0,
        state_dir=tmp_path,
        log_path=tmp_path / "lane.log",
        command=["lane"],
        provider="codex",
        environment={},
        supervisor_status_path=tmp_path / "lane-supervisor-status.json",
        process=FakeProcess(pid, returncode),  # type: ignore[arg-type]
        spawned_at=spawned_at,
    )


def test_restart_budget_exhaustion_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path, _, spawn_counts = _prepare_run(
        monkeypatch,
        tmp_path,
        max_restarts=1,
        process_factory=lambda lane: FakeProcess(1000 + lane.index, 17),
    )
    monkeypatch.setattr(supervisor, "_all_tasks_completed", lambda *args: False)
    monkeypatch.setattr(supervisor.time, "sleep", lambda seconds: None)

    assert supervisor.run(config_path) == supervisor.LANE_FAILURE_EXIT_CODE
    assert spawn_counts[0] == 2
    status = _final_status(tmp_path)
    assert status["exit_code"] == supervisor.LANE_FAILURE_EXIT_CODE
    assert "lane-00 exhausted restart budget" in status["stop_reason"]


def test_unrecoverable_initial_lane_launch_returns_nonzero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path, _, _ = _prepare_run(
        monkeypatch,
        tmp_path,
        process_factory=lambda lane: FakeProcess(1500 + lane.index),
    )

    def reject_launch(lane: supervisor.Lane, *, repo_root: Path) -> None:
        del lane, repo_root
        raise OSError("cannot launch lane")

    monkeypatch.setattr(supervisor, "_spawn_lane", reject_launch)

    assert supervisor.run(config_path) == supervisor.LANE_FAILURE_EXIT_CODE
    status = _final_status(tmp_path)
    assert status["exit_code"] == supervisor.LANE_FAILURE_EXIT_CODE
    assert status["stop_reason"].startswith("lane-00 initial launch failed")


def test_operator_sigterm_returns_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path, handlers, _ = _prepare_run(
        monkeypatch,
        tmp_path,
        process_factory=lambda lane: FakeProcess(2000 + lane.index),
    )
    monkeypatch.setattr(supervisor, "_all_tasks_completed", lambda *args: False)

    def stop_on_sleep(seconds: float) -> None:
        del seconds
        handlers[signal.SIGTERM](signal.SIGTERM, object())

    monkeypatch.setattr(supervisor.time, "sleep", stop_on_sleep)

    assert supervisor.run(config_path) == 0
    status = _final_status(tmp_path)
    assert status["exit_code"] == 0
    assert status["stop_reason"] == "operator_signal:SIGTERM"


def test_operator_sigterm_during_restart_backoff_returns_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path, handlers, spawn_counts = _prepare_run(
        monkeypatch,
        tmp_path,
        max_restarts=1,
        process_factory=lambda lane: FakeProcess(2500 + lane.index, 17),
    )
    monkeypatch.setattr(supervisor, "_all_tasks_completed", lambda *args: False)

    def stop_during_backoff(seconds: float) -> None:
        del seconds
        handlers[signal.SIGTERM](signal.SIGTERM, object())

    monkeypatch.setattr(supervisor.time, "sleep", stop_during_backoff)

    assert supervisor.run(config_path) == 0
    assert spawn_counts[0] == 1
    status = _final_status(tmp_path)
    assert status["exit_code"] == 0
    assert status["stop_reason"] == "operator_signal:SIGTERM"


def test_completed_backlog_returns_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    config_path, _, _ = _prepare_run(
        monkeypatch,
        tmp_path,
        process_factory=lambda lane: FakeProcess(3000 + lane.index),
    )
    monkeypatch.setattr(supervisor, "_all_tasks_completed", lambda *args: True)

    assert supervisor.run(config_path) == 0
    status = _final_status(tmp_path)
    assert status["exit_code"] == 0
    assert status["stop_reason"] == "backlog_completed"


def test_all_blocked_backlog_is_not_complete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    tasks = [
        SimpleNamespace(status="completed"),
        SimpleNamespace(status="blocked"),
    ]
    monkeypatch.setattr(supervisor, "parse_task_file", lambda *args: tasks)

    assert not supervisor._all_tasks_completed(tmp_path / "tasks.md", "SCA")


def test_missing_lane_status_is_ignored_only_during_startup_grace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lane = _lane(tmp_path, spawned_at=100.0)
    monkeypatch.setattr(supervisor, "LANE_STATUS_STARTUP_GRACE_SECONDS", 300.0)

    assert supervisor._lane_status_failure(lane, now_monotonic=399.0) is None
    failure = supervisor._lane_status_failure(lane, now_monotonic=401.0)
    assert failure is not None
    assert "status unavailable after startup grace" in failure


def test_lane_status_must_match_live_supervisor_pid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lane = _lane(tmp_path, pid=401, spawned_at=1.0)
    lane.supervisor_status_path.write_text(
        json.dumps(
            {
                "supervisor_pid": 999,
                "updated_at": "2026-07-29T20:00:00+00:00",
                "supervisor_heartbeat_seconds": 30,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(supervisor, "LANE_STATUS_STARTUP_GRACE_SECONDS", 0.0)

    failure = supervisor._lane_status_failure(
        lane,
        now_monotonic=2.0,
        now_epoch=1785355260.0,
    )
    assert failure == "lane-00 status belongs to pid 999, expected 401"


def test_stale_lane_status_forces_nonzero_shutdown(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def running_lane(lane: supervisor.Lane) -> FakeProcess:
        process = FakeProcess(5000 + lane.index)
        lane.supervisor_status_path.parent.mkdir(parents=True, exist_ok=True)
        lane.supervisor_status_path.write_text(
            json.dumps(
                {
                    "supervisor_pid": process.pid,
                    "updated_at": 1.0,
                    "supervisor_heartbeat_seconds": 30,
                }
            ),
            encoding="utf-8",
        )
        return process

    config_path, _, _ = _prepare_run(
        monkeypatch,
        tmp_path,
        process_factory=running_lane,
    )
    monkeypatch.setattr(supervisor, "_all_tasks_completed", lambda *args: False)
    monkeypatch.setattr(supervisor, "LANE_STATUS_STARTUP_GRACE_SECONDS", 0.0)

    assert supervisor.run(config_path) == supervisor.LANE_FAILURE_EXIT_CODE
    status = _final_status(tmp_path)
    assert status["exit_code"] == supervisor.LANE_FAILURE_EXIT_CODE
    assert "status heartbeat is stale" in status["stop_reason"]


def test_fresh_lane_status_is_healthy(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    lane = _lane(tmp_path, pid=601, spawned_at=1.0)
    lane.supervisor_status_path.write_text(
        json.dumps(
            {
                "supervisor_pid": 601,
                "updated_at": "2026-07-29T20:00:00+00:00",
                "supervisor_heartbeat_seconds": 30,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(supervisor, "LANE_STATUS_STARTUP_GRACE_SECONDS", 0.0)

    assert (
        supervisor._lane_status_failure(
            lane,
            now_monotonic=2.0,
            now_epoch=1785355260.0,
        )
        is None
    )
