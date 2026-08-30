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


def _blocked_retry_events(
    module,
    *,
    workspace: str = "/campaign/worktrees/workspace_6b4c063bd5e3_bdd9b20cc1e1",
) -> list[dict[str, object]]:
    deferred = {
        "cleaned": False,
        "reason": "verification_deferred_checkout_lease_active",
        "retained": True,
    }
    uncommitted = {
        "committed": False,
        "reason": "verification_deferred_checkout_lease_active",
    }
    return [
        {
            "sequence": 12,
            "event_id": module.BLOCKED_RETRY_EVENT_IDS[12],
            "type": "implementation_protected_path_verification_lock_timeout",
            "task_id": module.BLOCKED_RETRY_TASK_ALIAS,
            "canonical_task_cid": module.BLOCKED_RETRY_TASK_CID,
            "attempt": 1,
            "reason": module.BLOCKED_RETRY_REASON,
            "lock": {"acquired": False, "reason": "lock_exists"},
            "workspace_path": workspace,
        },
        {
            "sequence": 13,
            "event_id": module.BLOCKED_RETRY_EVENT_IDS[13],
            "type": "protected_path_verification_deferred_worktree_retained",
            "task_id": module.BLOCKED_RETRY_TASK_ALIAS,
            "canonical_task_cid": module.BLOCKED_RETRY_TASK_CID,
            "attempt": 1,
            "reason": "verification_deferred_checkout_lease_active",
            "cleanup_result": deferred,
            "commit_result": uncommitted,
            "implementation_commit": "",
            "worktree_path": workspace,
            "branch": module.BLOCKED_RETRY_BRANCH,
        },
        {
            "sequence": 14,
            "event_id": module.BLOCKED_RETRY_EVENT_IDS[14],
            "type": "implementation_finished",
            "task_id": module.BLOCKED_RETRY_TASK_ALIAS,
            "task_cid": module.BLOCKED_RETRY_TASK_CID,
            "canonical_task_cid": module.BLOCKED_RETRY_TASK_CID,
            "attempt": 1,
            "reason": module.BLOCKED_RETRY_REASON,
            "provider_dispatched": True,
            "returncode": 1,
            "deferred": True,
            "attempt_consumed": False,
            "cleanup_result": deferred,
            "commit_result": uncommitted,
            "merge_result": {"merged": False, "reason": "not_attempted"},
            "failed_preservation_result": {"retained": True, "preserved": False},
            "implementation_commit": "",
            "worktree_path": workspace,
            "branch": module.BLOCKED_RETRY_BRANCH,
            "baseline_ref": module.BLOCKED_RETRY_BASELINE,
        },
    ]


def _event_payload(events: list[dict[str, object]]) -> bytes:
    return b"".join(
        json.dumps(event, sort_keys=True).encode("utf-8") + b"\n" for event in events
    )


def _blocked_task_row(module) -> dict[str, object]:
    terminal = {
        "operation": "database_portal_terminal_failure",
        "reason": module.BLOCKED_RETRY_REASON,
        "retryable": False,
        "attempt_number": 1,
        "control_expected_status": "in_progress",
        "control_expected_revision": 3,
    }
    return {
        "status": "blocked",
        "revision": 4,
        "body_json": json.dumps({"completion_receipt": terminal}, sort_keys=True),
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


def test_historical_blocked_retry_accepts_only_exact_nonadmitted_evidence() -> None:
    module = _module()
    events = _blocked_retry_events(module)

    timeout, retained, finished = module._validated_blocked_retry_events(
        _event_payload(events),
        task_cid=module.BLOCKED_RETRY_TASK_CID,
    )

    assert timeout["sequence"] == 12
    assert retained["cleanup_result"]["retained"] is True
    assert finished["provider_dispatched"] is True
    assert finished["implementation_commit"] == ""


@pytest.mark.parametrize(
    ("event_index", "field", "replacement"),
    [
        (0, "event_id", "sha256:wrong"),
        (1, "worktree_path", "/outside/worktree"),
        (2, "provider_dispatched", False),
        (2, "branch", "implementation/unrelated"),
        (2, "baseline_ref", "0" * 40),
        (2, "merge_result", {"merged": True, "reason": "merged"}),
    ],
)
def test_historical_blocked_retry_rejects_evidence_drift(
    event_index: int,
    field: str,
    replacement: object,
) -> None:
    module = _module()
    events = _blocked_retry_events(module)
    events[event_index][field] = replacement

    with pytest.raises(module.HandoffError, match="exact retained lock-timeout failure"):
        module._validated_blocked_retry_events(
            _event_payload(events),
            task_cid=module.BLOCKED_RETRY_TASK_CID,
        )


def test_historical_blocked_retry_task_identity_is_sealed() -> None:
    module = _module()
    population = {
        "tasks": [
            {
                "task_alias": module.BLOCKED_RETRY_TASK_ALIAS,
                "task_cid": module.BLOCKED_RETRY_TASK_CID,
            }
        ]
    }

    assert module._blocked_retry_task_cid(population) == module.BLOCKED_RETRY_TASK_CID
    population["tasks"][0]["task_cid"] = "sha256:wrong"
    with pytest.raises(module.HandoffError, match="unique DOEP-030 identity"):
        module._blocked_retry_task_cid(population)


def test_historical_blocked_retry_authorization_binds_workspace_and_digests(
    tmp_path: Path,
) -> None:
    module = _module()
    root = tmp_path / "runtime"
    state = root / "state"
    workspace = root / "worktrees" / module.BLOCKED_RETRY_WORKSPACE_NAME
    workspace.mkdir(parents=True)
    event_path = state / module.BLOCKED_RETRY_ATTEMPT_RELATIVE / "portal-events.jsonl"
    event_path.parent.mkdir(parents=True)
    event_path.write_bytes(
        _event_payload(_blocked_retry_events(module, workspace=str(workspace)))
    )
    paths = {
        "root": root,
        "state": state,
        "blocked_retry_sidecar": root / "evidence.json",
        "blocked_retry_authorization": root / "authorization.json",
    }

    sidecar, authorization = module._prepare_blocked_retry_authorization(
        paths=paths,
        task_cid=module.BLOCKED_RETRY_TASK_CID,
        task_row=_blocked_task_row(module),
    )
    loaded_sidecar, loaded_authorization = module._load_blocked_retry_authorization(
        paths=paths,
        task_cid=module.BLOCKED_RETRY_TASK_CID,
    )

    assert loaded_sidecar == sidecar
    assert loaded_authorization == authorization
    assert sidecar["historical_candidate_fingerprint"] == "unavailable"
    assert sidecar["retained_candidate_admitted"] is False
    assert authorization["require_fresh_portal_revalidation"] is True


def test_historical_blocked_retry_authorization_rejects_workspace_escape(
    tmp_path: Path,
) -> None:
    module = _module()
    root = tmp_path / "runtime"
    state = root / "state"
    outside = tmp_path / "outside"
    outside.mkdir()
    event_path = state / module.BLOCKED_RETRY_ATTEMPT_RELATIVE / "portal-events.jsonl"
    event_path.parent.mkdir(parents=True)
    event_path.write_bytes(
        _event_payload(_blocked_retry_events(module, workspace=str(outside)))
    )
    paths = {
        "root": root,
        "state": state,
        "blocked_retry_sidecar": root / "evidence.json",
        "blocked_retry_authorization": root / "authorization.json",
    }

    with pytest.raises(module.HandoffError, match="retained workspace is unavailable"):
        module._prepare_blocked_retry_authorization(
            paths=paths,
            task_cid=module.BLOCKED_RETRY_TASK_CID,
            task_row=_blocked_task_row(module),
        )
