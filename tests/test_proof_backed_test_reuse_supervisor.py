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


def test_configured_submodule_initialization_is_scoped_and_non_updating(
    supervisor: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        calls.append((command, dict(kwargs)))
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(supervisor.subprocess, "run", fake_run)

    initialized = supervisor._initialize_configured_submodules()

    assert initialized == (
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "external/ipfs_kit",
    )
    assert calls[0][0] == [
        "git",
        "submodule",
        "init",
        "--",
        *initialized,
    ]
    assert "update" not in calls[0][0]
    assert calls[0][1]["cwd"] == supervisor.REPO_ROOT


def test_report_only_board_validation_does_not_persist_projection(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    projection_dir = tmp_path / "projection"
    projection_dir.mkdir()
    monkeypatch.setattr(supervisor, "PROJECTION_DIR", projection_dir)
    monkeypatch.setattr(
        supervisor,
        "_run",
        lambda *_args, **_kwargs: subprocess.CompletedProcess(
            args=[],
            returncode=0,
            stdout=json.dumps({"valid": True, "task_count": 41}),
            stderr="",
        ),
    )

    result = supervisor._validate_board(persist_projection=False)

    assert result["valid"] is True
    assert not (projection_dir / "native_board_preflight.json").exists()


def test_closeout_artifact_presence_projects_missing_inputs_without_authority(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    gate_path = tmp_path / "goal_completion_gate.json"
    evidence_path = tmp_path / "goal_completion_evidence.json"
    paths = {
        "gatePathSuffix": gate_path,
        "evidencePathSuffix": evidence_path,
    }
    monkeypatch.setattr(
        supervisor,
        "_completion_state_path",
        lambda field: paths[field],
    )
    gate_path.write_text("{}\n", encoding="utf-8")

    projection = supervisor._required_closeout_artifact_presence()

    assert projection["artifact_presence_ready"] is False
    assert projection["missing_required_artifacts"] == ["evidence"]
    assert projection["required_artifacts"]["gate"]["present"] is True
    assert (
        projection["artifact_presence_is_completion_authority"]
        is False
    )


def _configure_closeout_test(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    diagnosis_passed: bool,
) -> list[Path]:
    monkeypatch.setattr(
        supervisor,
        "_require_isolated_clean_checkout",
        lambda: {
            "branch": "agent/proof-backed-test-reuse",
            "commit": "commit-1",
            "tree": "tree-1",
            "submodules": {},
        },
    )
    monkeypatch.setattr(
        supervisor,
        "_validate_board",
        lambda **_kwargs: {"valid": True, "task_count": 41},
    )
    monkeypatch.setattr(
        supervisor,
        "_reviewed_completion_projection",
        lambda: {
            "implementation": {
                "task_count": 41,
                "completed_task_count": 41,
                "open_task_ids": [],
            }
        },
    )
    monkeypatch.setattr(
        supervisor,
        "_status_payload",
        lambda: {
            "healthy": True,
            "work_complete": True,
            "lanes": [],
        },
    )
    monkeypatch.setattr(
        supervisor,
        "_completion_state_path",
        lambda field: tmp_path / field,
    )
    observed_health_paths: list[Path] = []

    def fake_run(
        command: list[str], **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        assert command[-1] == "--report-only"
        health_path = Path(
            command[command.index("--supervisor-health-input-path") + 1]
        )
        observed_health_paths.append(health_path)
        health = json.loads(health_path.read_text(encoding="utf-8"))
        assert health["status"]["healthy"] is True
        assert health["status"]["work_complete"] is True
        payload = {
            "mode": "report_only",
            "passed": diagnosis_passed,
            "reason_codes": [] if diagnosis_passed else ["missing_artifact"],
        }
        return subprocess.CompletedProcess(
            command,
            0 if diagnosis_passed else 1,
            json.dumps(payload),
            "",
        )

    monkeypatch.setattr(supervisor, "_run", fake_run)
    monkeypatch.setattr(
        supervisor,
        "_stop_lane",
        lambda _lane: (_ for _ in ()).throw(
            AssertionError("diagnosis must not stop lanes")
        ),
    )
    return observed_health_paths


def test_closeout_report_only_uses_ephemeral_health_and_keeps_lanes_running(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    observed_health_paths = _configure_closeout_test(
        supervisor,
        monkeypatch,
        tmp_path,
        diagnosis_passed=True,
    )

    result = supervisor._closeout(report_only=True)

    assert result["diagnosis_passed"] is True
    assert result["lanes_stopped"] is False
    assert result["operator_commit_required"] is False
    assert len(observed_health_paths) == 1
    assert not observed_health_paths[0].exists()
    assert not any(tmp_path.iterdir())


def test_closeout_refuses_failed_diagnosis_before_stopping_lanes(
    supervisor: Any,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _configure_closeout_test(
        supervisor,
        monkeypatch,
        tmp_path,
        diagnosis_passed=False,
    )

    result = supervisor._closeout()

    assert result["closeout_passed"] is False
    assert result["precloseout_diagnosis_passed"] is False
    assert result["lanes_stopped"] == []
    assert result["result"]["reason_codes"] == ["missing_artifact"]
