from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/ops/agent_supervisor/direct_objective_event_driven_planning_handoff.py"


def _module():
    spec = importlib.util.spec_from_file_location("doep_handoff_projection_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _snapshot(*, revision: int = 7, event_cursor: int = 11) -> dict[str, object]:
    return {
        "revision": revision,
        "event_cursor": event_cursor,
        "projection_cid": "baguqeera-database-projection",
        "plan_root_cid": "sha256:plan",
        "repository_tree_id": "sha256:tree",
    }


def _generation(*, revision: int = 7) -> dict[str, object]:
    return {
        "store_id": "doep-v1-r5",
        "database_uuid": "11111111-1111-4111-8111-111111111111",
        "generation": 5,
        "fence_epoch": 5,
        "revision": revision,
    }


def _tasks(*, status: str = "in_progress", revision: int = 3) -> list[dict[str, object]]:
    return [
        {
            "task_cid": "sha256:task",
            "task_alias": "DOEP-030",
            "objective_id": "agent-supervisor-direct-objective-and-event-driven-planning-v1",
            "goal_cid": "sha256:goal",
            "plan_cid": "sha256:plan",
            "ordinal": 30,
            "status": status,
            "revision": revision,
            "dependencies": ["sha256:dependency"],
            "outputs": [{"kind": "primary", "path": "contracts/events.py"}],
            "validations": [{"argv": ["python3", "-m", "pytest", "test_events.py", "-q"]}],
            "body": {
                "title": "Define canonical event schema",
                "subgoal_id": "DOEP-G040.S1",
                "parent_goal_id": "DOEP-G040",
                "owning_repository": "external/ipfs_accelerate",
            },
        }
    ]


def _paths(root: Path) -> dict[str, Path]:
    return {
        "task_projection": root / "current-taskboard.md",
        "objective_projection": root / "current-objectives.md",
        "projection_receipt": root / "receipt.json",
    }


def test_runtime_markdown_is_deterministic_non_authoritative_duckdb_projection() -> None:
    module = _module()
    first = module._render_runtime_taskboard(
        snapshot=_snapshot(), generation=_generation(), tasks=_tasks()
    )
    second = module._render_runtime_taskboard(
        snapshot=_snapshot(), generation=_generation(), tasks=_tasks()
    )
    objectives = module._render_runtime_objectives(
        snapshot=_snapshot(), generation=_generation(), tasks=_tasks()
    )

    assert first == second
    assert b"NON-AUTHORITATIVE RUNTIME PROJECTION" in first
    assert b"DuckDB -> exclusive QuackStateServer -> TypedDatabaseTaskSource" in first
    assert b"DOEP-030" in first and b"in_progress" in first
    assert b"task-derived operational view" in objectives
    assert b"DOEP-G040.S1" in objectives


def test_publish_receipt_binds_exact_projection_and_repairs_tampering(tmp_path: Path) -> None:
    module = _module()
    paths = _paths(tmp_path)
    receipt = module._publish_runtime_projections(
        paths=paths,
        snapshot=_snapshot(),
        generation=_generation(),
        tasks=_tasks(),
        owner_server_id="server:test",
        launch_id="sha256:launch",
    )

    task_bytes = paths["task_projection"].read_bytes()
    objective_bytes = paths["objective_projection"].read_bytes()
    stored = json.loads(paths["projection_receipt"].read_text(encoding="utf-8"))
    assert receipt == stored
    assert stored["authority"] is False
    assert stored["store_revision"] == 7
    assert (
        stored["artifacts"]["taskboard"]["sha256"]
        == "sha256:" + hashlib.sha256(task_bytes).hexdigest()
    )
    assert (
        stored["artifacts"]["objectives"]["sha256"]
        == "sha256:" + hashlib.sha256(objective_bytes).hexdigest()
    )

    paths["task_projection"].write_text("tampered\n", encoding="utf-8")
    module._publish_runtime_projections(
        paths=paths,
        snapshot=_snapshot(),
        generation=_generation(),
        tasks=_tasks(),
        owner_server_id="server:test",
        launch_id="sha256:launch",
    )
    assert paths["task_projection"].read_bytes() == task_bytes


def test_stale_runtime_markdown_publisher_cannot_overwrite_newer_snapshot(tmp_path: Path) -> None:
    module = _module()
    paths = _paths(tmp_path)
    module._publish_runtime_projections(
        paths=paths,
        snapshot=_snapshot(revision=8, event_cursor=12),
        generation=_generation(revision=8),
        tasks=_tasks(status="completed", revision=4),
        owner_server_id="server:new",
        launch_id="sha256:new",
    )
    current = paths["task_projection"].read_bytes()

    with pytest.raises(module.HandoffError, match="stale runtime Markdown publisher"):
        module._publish_runtime_projections(
            paths=paths,
            snapshot=_snapshot(revision=7, event_cursor=11),
            generation=_generation(revision=7),
            tasks=_tasks(),
            owner_server_id="server:stale",
            launch_id="sha256:stale",
        )
    assert paths["task_projection"].read_bytes() == current
