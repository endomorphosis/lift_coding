from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "proof_backed_test_reuse_supervisor.py"


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "proof_backed_test_reuse_supervisor", SCRIPT
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def supervisor() -> Any:
    return _load_module()


def _run_board_readiness(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    payload: dict[str, object],
) -> dict[str, object]:
    state_root = tmp_path / "state"
    log_dir = tmp_path / "logs"
    task_state_path = (
        state_root / "preflight" / "board" / "ptr_preflight_task_state.json"
    )
    task_state_path.parent.mkdir(parents=True)
    log_dir.mkdir()
    task_state_path.write_text(json.dumps(payload), encoding="utf-8")

    monkeypatch.setattr(supervisor, "STATE_DIR", state_root)
    monkeypatch.setattr(supervisor, "LOG_DIR", log_dir)
    monkeypatch.setattr(
        supervisor,
        "_run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[], returncode=0, stdout="", stderr=""
        ),
    )
    return supervisor._no_agent_readiness()


def test_completed_board_is_valid_quiescent_readiness(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "task_count": 32,
        "completed_count": 32,
        "ready_count": 0,
        "selectable_ready_count": 0,
        "waiting_count": 0,
        "blocked_count": 0,
        "blocked_task_ids": [],
        "selection_idle_reason": "no_shard_selectable_ready_tasks",
    }

    readiness = _run_board_readiness(
        supervisor, monkeypatch, tmp_path, payload
    )

    assert readiness["work_complete"] is True
    assert readiness["selectable_ready_count"] == 0


def test_incomplete_board_without_selectable_work_is_rejected(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "task_count": 32,
        "completed_count": 31,
        "selectable_ready_count": 0,
        "blocked_count": 0,
        "blocked_task_ids": [],
        "selection_idle_reason": "no_shard_selectable_ready_tasks",
    }

    with pytest.raises(RuntimeError, match="no selectable task"):
        _run_board_readiness(supervisor, monkeypatch, tmp_path, payload)


def test_completed_board_with_blocked_tasks_is_rejected(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    payload = {
        "task_count": 32,
        "completed_count": 32,
        "selectable_ready_count": 0,
        "blocked_count": 1,
        "blocked_task_ids": ["PTR-999"],
        "selection_idle_reason": "no_shard_selectable_ready_tasks",
    }

    with pytest.raises(RuntimeError, match="blocked tasks"):
        _run_board_readiness(supervisor, monkeypatch, tmp_path, payload)
