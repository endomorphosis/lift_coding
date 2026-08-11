"""Bootstrap tests for the worker planner–doctor (WPD) control plane."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = REPO_ROOT / "scripts" / "validate_supervisor_worker_planner_doctor_board.py"
CONTROL = [
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "47-supervisor-worker-planner-doctor-integration-plan-2026-08-06.md",
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "47-supervisor-worker-planner-doctor-integration.objectives.md",
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "47-supervisor-worker-planner-doctor-integration.todo.md",
    REPO_ROOT / "config" / "supervisor_worker_planner_doctor_integration_scheduler.json",
    REPO_ROOT / "config" / "supervisor_worker_planner_doctor_supervisor.json",
    REPO_ROOT / "scripts" / "validate_supervisor_worker_planner_doctor_board.py",
    REPO_ROOT / "scripts" / "supervisor_worker_planner_doctor_supervisor.sh",
]


def test_control_artifacts_exist() -> None:
    missing = [str(path.relative_to(REPO_ROOT)) for path in CONTROL if not path.is_file()]
    assert not missing, f"missing control artifacts: {missing}"


def test_board_validator_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--check-all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is True
    assert payload["task_count"] == 22
    assert payload["goal_count"] == 8
    assert payload["terminal_task_id"] == "WPD-070"
    assert payload["board_namespace"] == "agent-supervisor-worker-planner-doctor-v1"


def test_ready_wave_after_bootstrap_semantics() -> None:
    result = subprocess.run(
        [sys.executable, str(VALIDATOR), "--check-all"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    payload = json.loads(result.stdout)
    if payload.get("bootstrap_completed"):
        assert set(payload["ready_after_bootstrap"]).issubset(
            set(payload["ready_task_ids"]) | set(payload["completed_task_ids"])
        )
    else:
        assert payload["ready_task_ids"] == ["WPD-000"]
