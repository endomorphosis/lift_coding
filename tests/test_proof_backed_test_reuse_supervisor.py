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


def test_every_lane_uses_grok_primary_codex_fallback_policy(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: "/opt/grok/bin/grok" if name == "grok" else None,
    )

    assert len(supervisor.LANES) == 3
    for lane in supervisor.LANES:
        assert lane["provider"] == "grok-codex"
        assert lane["primary_provider"] == "grok"
        assert lane["fallback_provider"] == "codex"
        environment = supervisor._runtime_environment(str(lane["provider"]))
        assert (
            environment["IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER"]
            == "grok-codex"
        )
        assert (
            environment["IPFS_ACCELERATE_AGENT_GROK_BIN"]
            == "/opt/grok/bin/grok"
        )


def test_provider_preflight_uses_codex_when_grok_is_unavailable(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: "/opt/codex/bin/codex" if name == "codex" else None,
    )

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert command == ["/opt/codex/bin/codex", "login", "status"]
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="Logged in using ChatGPT\n",
            stderr="",
        )

    monkeypatch.setattr(supervisor, "_run", fake_run)

    providers = supervisor._provider_preflight()

    assert providers["grok"] == ""
    assert providers["grok_authenticated"] is False
    assert providers["provider_policy"] == {
        "primary": "grok",
        "fallback": "codex",
        "effective_first_provider": "codex",
        "grok_unavailable_action": "use_codex",
    }


def test_provider_preflight_reports_grok_as_effective_primary(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: f"/opt/{name}/bin/{name}"
        if name in {"codex", "grok"}
        else None,
    )

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command[-2:] == ["login", "status"]:
            stdout = "Logged in using ChatGPT\n"
        else:
            assert command == ["/opt/grok/bin/grok", "--version"]
            stdout = "grok 1.2.3\n"
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout=stdout,
            stderr="",
        )

    monkeypatch.setattr(supervisor, "_run", fake_run)
    if str(supervisor.ACCEL_ROOT) not in supervisor.sys.path:
        supervisor.sys.path.insert(0, str(supervisor.ACCEL_ROOT))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import (
        implementation_daemon,
    )

    monkeypatch.setattr(
        implementation_daemon,
        "_grok_cli_available",
        lambda: True,
    )

    providers = supervisor._provider_preflight()

    assert providers["grok_authenticated"] is True
    assert providers["provider_policy"]["effective_first_provider"] == "grok"


def test_provider_preflight_requires_codex_fallback(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        supervisor.shutil,
        "which",
        lambda name: "/opt/grok/bin/grok" if name == "grok" else None,
    )

    with pytest.raises(RuntimeError, match="fallback provider"):
        supervisor._provider_preflight()
