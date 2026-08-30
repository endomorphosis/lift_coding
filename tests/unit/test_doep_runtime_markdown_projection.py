from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

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


def test_bootstrap_accepts_initial_and_canonical_reload_supervisor_entries() -> None:
    module = _module()
    entry = str(
        (
            ROOT
            / "scripts/ops/agent_supervisor/implementation_supervisor_entry.py"
        ).resolve()
    )
    canonical_module = (
        "ipfs_accelerate_py.agent_supervisor.todo_daemon."
        "implementation_supervisor"
    )

    assert module._canonical_supervisor_entry(("/usr/bin/python3", entry))
    assert module._canonical_supervisor_entry(
        ("/usr/bin/python3", "-m", canonical_module)
    )


@pytest.mark.parametrize(
    "argv",
    [
        ("/usr/bin/python3", "-m", "implementation_supervisor"),
        (
            "/usr/bin/python3",
            "-m",
            "untrusted.supervisor",
            "--note",
            "ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor",
        ),
        (
            "/usr/bin/python3",
            "/tmp/implementation_supervisor_entry.py",
        ),
    ],
)
def test_bootstrap_rejects_noncanonical_supervisor_entries(
    argv: tuple[str, ...],
) -> None:
    module = _module()

    assert module._canonical_supervisor_entry(argv) is False


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


def _authority_context() -> dict[str, object]:
    return {
        "store_id": "doep-v1-r5",
        "database_uuid": "11111111-1111-4111-8111-111111111111",
        "store_generation": 5,
        "fence_epoch": 5,
        "store_revision": 45,
        "plan_root_cid": "sha256:plan",
        "repository_tree_id": "sha256:tree",
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


def _authority_board(**overrides: object) -> SimpleNamespace:
    program = {
        "task_source_kind": "duckdb",
        "authority_mode": "quack",
        "failover_policy": "fail_closed",
        "explicit_legacy": False,
        "quack_endpoint": "quack:127.0.0.1:27942",
        "endpoint_secret_handle": "env://IPFS_ACCELERATE_AGENT_QUACK_TOKEN",
    }
    program.update(overrides)
    return SimpleNamespace(
        resolved_database_program=lambda: SimpleNamespace(**program),
        payload={
            "operational_control_plane": {
                "markdown_is_bootstrap_only": True,
                "automatic_file_fallback_permitted": False,
                "direct_multi_process_duckdb_file_open_permitted": False,
                "outage_policy": "fail_closed",
            },
            "ducklake_projection_program": {
                "authority": False,
                "may_grant_authority": False,
                "scheduling_prerequisite": False,
                "acceptance_prerequisite": False,
                "completion_prerequisite": False,
            },
        },
    )


def test_handoff_requires_duckdb_quack_and_projection_only_markdown() -> None:
    module = _module()
    module._require_doep_duckdb_authority(_authority_board())

    for drift in (
        {"task_source_kind": "markdown"},
        {"authority_mode": "legacy_markdown"},
        {"failover_policy": "fallback"},
        {"explicit_legacy": True},
    ):
        with pytest.raises(module.HandoffError, match="DuckDB tasks"):
            module._require_doep_duckdb_authority(_authority_board(**drift))

    ducklake_authority = _authority_board()
    ducklake_authority.payload["ducklake_projection_program"]["authority"] = True
    with pytest.raises(module.HandoffError, match="DuckDB tasks"):
        module._require_doep_duckdb_authority(ducklake_authority)

    markdown_authority = _authority_board()
    markdown_authority.payload["operational_control_plane"][
        "markdown_is_bootstrap_only"
    ] = False
    with pytest.raises(module.HandoffError, match="DuckDB tasks"):
        module._require_doep_duckdb_authority(markdown_authority)


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


def test_status_integrity_binds_markdown_bytes_to_live_duckdb_revision(
    tmp_path: Path,
) -> None:
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
    live = {
        "launch_id": "sha256:launch",
        "owner_server_id": "server:test",
        "store_revision": 7,
        "event_cursor": 11,
        "projection_cid": "baguqeera-database-projection",
        "plan_root_cid": "sha256:plan",
        "repository_tree_id": "sha256:tree",
        "task_count": 1,
        "runtime_markdown_projection": {
            "authority": False,
            "ready": True,
            "error": "",
            "receipt_cid": receipt["receipt_cid"],
            "store_revision": 7,
            "event_cursor": 11,
            "database_projection_cid": "baguqeera-database-projection",
            "taskboard_path": str(paths["task_projection"]),
            "objectives_path": str(paths["objective_projection"]),
            "receipt_path": str(paths["projection_receipt"]),
        },
    }

    integrity = module._runtime_projection_integrity(paths=paths, live=live)
    assert integrity["ready"] is True
    assert integrity["authority"] is False
    assert integrity["issues"] == []

    paths["objective_projection"].write_text("tampered\n", encoding="utf-8")
    drifted = module._runtime_projection_integrity(paths=paths, live=live)
    assert drifted["ready"] is False
    assert "projection_objectives_digest_mismatch" in drifted["issues"]


def test_busy_duckdb_projection_does_not_terminate_task_execution() -> None:
    module = _module()
    monitor = object.__new__(module._LiveMonitor)
    generation_counter = iter(range(1, 9))
    snapshot_counter = iter(range(1, 9))

    class BusyClient:
        @staticmethod
        def load_generation():
            revision = next(generation_counter)
            return SimpleNamespace(content_id=f"generation-{revision}")

    class BusySource:
        @staticmethod
        def snapshot():
            revision = next(snapshot_counter)
            return SimpleNamespace(
                projection_cid=f"projection-{revision}", revision=revision
            )

        @staticmethod
        def list_tasks(*, limit: int):
            assert limit == 500
            return SimpleNamespace(next_cursor="", revision=0)

    monitor.client = BusyClient()
    monitor.source = BusySource()
    monitor.projection_failure = ""

    monitor._write()

    assert "typed database state changed" in monitor.projection_failure


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
        authority_context=_authority_context(),
    )
    loaded_sidecar, loaded_authorization = module._load_blocked_retry_authorization(
        paths=paths,
        task_cid=module.BLOCKED_RETRY_TASK_CID,
        authority_context=_authority_context(),
    )

    assert loaded_sidecar == sidecar
    assert loaded_authorization == authorization
    assert sidecar["historical_candidate_fingerprint"] == "unavailable"
    assert sidecar["retained_candidate_admitted"] is False
    assert authorization["require_fresh_portal_revalidation"] is True

    changed_database = {**_authority_context(), "database_uuid": "different"}
    with pytest.raises(module.HandoffError, match="authorization has drifted"):
        module._load_blocked_retry_authorization(
            paths=paths,
            task_cid=module.BLOCKED_RETRY_TASK_CID,
            authority_context=changed_database,
        )


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
            authority_context=_authority_context(),
        )


def _doep031_body(module, *, terminal: dict[str, object] | None = None) -> dict[str, object]:
    child_paths = list(module.DOEP031_CHILD_PATHS)
    return {
        "stable_task_id": module.DOEP031_TASK_ALIAS,
        "board_namespace": module.PROGRAM_ID,
        "plan_revision": "DOEP-PLAN-V5",
        "owning_repository": "external/ipfs_kit",
        "exact_outputs": child_paths,
        "owned_files": child_paths,
        "write_scope": child_paths,
        "superproject_outputs": list(module.DOEP031_OUTPUT_SCOPE),
        "completion_receipt": dict(terminal or module.DOEP031_TERMINAL_RECEIPT),
    }


def _doep031_row(
    module,
    *,
    status: str = "blocked",
    revision: int = 4,
    terminal: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "task_alias": module.DOEP031_TASK_ALIAS,
        "task_cid": module.DOEP031_TASK_CID,
        "ordinal": 22,
        "objective_id": module.PROGRAM_ID,
        "plan_cid": "sha256:6c197a4b92682b3b813656123e09956846dc4f5abadf417f37fb7cc0133ddba4",
        "status": status,
        "revision": revision,
        "identity_json": json.dumps(
            {
                "task_alias": module.DOEP031_TASK_ALIAS,
                "task_cid": module.DOEP031_TASK_CID,
            }
        ),
        "body_json": json.dumps(_doep031_body(module, terminal=terminal)),
    }


def _doep031_events(module, workspace: str) -> list[dict[str, object]]:
    common = {
        "task_id": module.DOEP031_TASK_ALIAS,
        "canonical_task_cid": module.DOEP031_TASK_CID,
        "canonical_task_key": module.DOEP031_TASK_CID,
        "attempt": 1,
    }
    events: list[dict[str, object]] = []
    types = {
        11: "implementation_protected_path_snapshot_recorded",
        12: "implementation_started",
        13: "pre_implementation_kernel_evaluated",
        14: "implementation_protected_path_mutated",
        15: "cleanup_finished",
        16: "protected_path_interrupted_worktree_preserved",
        17: "implementation_finished",
    }
    for sequence in range(11, 18):
        event = {
            "sequence": sequence,
            "event_id": module.DOEP031_EVENT_IDS[sequence],
            "type": types[sequence],
            "stream_id": module.DOEP031_STREAM_ID,
            "snapshot_id": module.DOEP031_SNAPSHOT_ID,
            **({"previous_event_id": module.DOEP031_EVENT_IDS[sequence - 1]} if sequence > 11 else {}),
            **(common if sequence != 15 else {}),
            **(
                {
                    "workspace_path" if sequence in (11, 14) else "worktree_path": workspace
                }
                if sequence != 13
                else {}
            ),
        }
        events.append(event)
    by_sequence = {int(event["sequence"]): event for event in events}
    by_sequence[12].update(
        {
            "baseline_ref": module.DOEP031_BASELINE,
            "branch": module.DOEP031_BRANCH,
            "outputs": list(module.DOEP031_OUTPUT_SCOPE),
        }
    )
    mutation = {
        "path": module.DOEP031_PROTECTED_PATH,
        "scope": "shared_checkout",
        "change": "content_changed",
        "before": {"sha256": module.DOEP031_PROTECTED_BEFORE_SHA256},
        "after": {"sha256": module.DOEP031_PROTECTED_AFTER_SHA256},
    }
    by_sequence[14].update(
        {
            "reason": module.DOEP031_PORTAL_REASON,
            "shared_checkout_restored": False,
            "mutations": [mutation],
        }
    )
    by_sequence[15].update(
        {"branch": module.DOEP031_BRANCH, "cleaned": True, "deleted_branch": True}
    )
    commit_result = {
        "committed": True,
        "commit": module.DOEP031_CANDIDATE_COMMIT,
        "submodule_results": [
            {
                "path": "external/ipfs_kit",
                "committed": True,
                "commit": module.DOEP031_CANDIDATE_CHILD,
            }
        ],
    }
    by_sequence[16].update(
        {
            "branch": module.DOEP031_BRANCH,
            "preserved": True,
            "preserved_commit": module.DOEP031_CANDIDATE_COMMIT,
            "implementation_commit": module.DOEP031_CANDIDATE_COMMIT,
            "rescue_branch": module.DOEP031_RESCUE_REF.removeprefix("refs/heads/"),
            "commit_result": commit_result,
        }
    )
    by_sequence[17].update(
        {
            "branch": module.DOEP031_BRANCH,
            "baseline_ref": module.DOEP031_BASELINE,
            "implementation_commit": module.DOEP031_CANDIDATE_COMMIT,
            "provider_dispatched": True,
            "attempt_consumed": False,
            "deferred": True,
            "reason": module.DOEP031_PORTAL_REASON,
            "returncode": 1,
            "merge_result": {"merged": False, "reason": "not_attempted"},
        }
    )
    return events


def test_doep031_task_authority_binds_exact_blocked_revision_and_terminal_receipt() -> None:
    module = _module()
    body, terminal = module._validated_doep031_task_row(_doep031_row(module))

    assert body["superproject_outputs"] == list(module.DOEP031_OUTPUT_SCOPE)
    assert terminal == module.DOEP031_TERMINAL_RECEIPT

    row = _doep031_row(module)
    row["status"] = "completed"
    with pytest.raises(module.HandoffError, match="revision, status, or output scope"):
        module._validated_doep031_task_row(row)

    terminal_drift = json.loads(json.dumps(module.DOEP031_TERMINAL_RECEIPT))
    terminal_drift["attempt_id"] = "attempt:wrong"
    with pytest.raises(module.HandoffError, match="exact sealed failure"):
        module._validated_doep031_task_row(
            _doep031_row(module, terminal=terminal_drift)
        )


@pytest.mark.parametrize(
    ("sequence", "field", "replacement"),
    [
        (11, "event_id", "sha256:wrong"),
        (14, "shared_checkout_restored", True),
        (15, "deleted_branch", False),
        (16, "preserved_commit", "0" * 40),
        (17, "attempt_consumed", True),
    ],
)
def test_doep031_event_chain_fails_closed_on_identity_or_candidate_drift(
    sequence: int,
    field: str,
    replacement: object,
) -> None:
    module = _module()
    workspace = "/campaign/worktrees/" + module.DOEP031_WORKSPACE_NAME
    events = _doep031_events(module, workspace)
    module._validated_doep031_events(
        _event_payload(events),
        workspace_path=workspace,
    )
    next(event for event in events if event["sequence"] == sequence)[field] = replacement

    with pytest.raises(module.HandoffError):
        module._validated_doep031_events(
            _event_payload(events),
            workspace_path=workspace,
        )


def test_doep031_artifacts_bind_snapshot_incident_binding_and_event_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    root = tmp_path / "runtime"
    state = root / "state"
    attempt = state / module.DOEP031_ATTEMPT_RELATIVE
    attempt.mkdir(parents=True)
    workspace = str(root / "worktrees" / module.DOEP031_WORKSPACE_NAME)
    artifacts: dict[str, bytes] = {
        "portal-events.jsonl": _event_payload(_doep031_events(module, workspace)),
        "portal-events.jsonl.manifest.json": json.dumps(
            {
                "stream_id": module.DOEP031_STREAM_ID,
                "snapshot_id": module.DOEP031_SNAPSHOT_ID,
                "latest_sequence": 18,
            }
        ).encode(),
        "database-attempt-binding.json": json.dumps(
            {
                "binding_id": "sha256:025031355642bae02ba1e0358444cdc76b5c13ccf6ccfdb71b32703d51cdd2bd",
                "task_alias": module.DOEP031_TASK_ALIAS,
                "task_cid": module.DOEP031_TASK_CID,
                "canonical_task_key": module.DOEP031_TASK_CID,
                "task_revision": 3,
                "attempt_number": 1,
                "attempt_id": module.DOEP031_TERMINAL_RECEIPT["attempt_id"],
                "claim_id": module.DOEP031_TERMINAL_RECEIPT["claim_id"],
                "lease_id": module.DOEP031_TERMINAL_RECEIPT["lease_id"],
            }
        ).encode(),
        "implementation-protected-path-active.json": json.dumps(
            {
                "schema": "implementation-protected-path-active-v1",
                "task_id": module.DOEP031_TASK_ALIAS,
                "canonical_task_cid": module.DOEP031_TASK_CID,
                "canonical_task_key": module.DOEP031_TASK_CID,
                "attempt": 1,
                "workspace_path": workspace,
                "snapshot": {
                    "shared_checkout": {
                        "git_head": module.DOEP031_BASELINE,
                        "paths": {
                            module.DOEP031_PROTECTED_PATH: {
                                "sha256": module.DOEP031_PROTECTED_BEFORE_SHA256
                            }
                        },
                    }
                },
            }
        ).encode(),
        "implementation-protected-path-incident.json": json.dumps(
            {
                "schema": "implementation-protected-path-incident-v1",
                "task_id": module.DOEP031_TASK_ALIAS,
                "canonical_task_cid": module.DOEP031_TASK_CID,
                "canonical_task_key": module.DOEP031_TASK_CID,
                "attempt": 1,
                "workspace_path": workspace,
                "reason": module.DOEP031_PORTAL_REASON,
                "requires_operator_clearance": True,
                "shared_checkout_restored": False,
                "mutations": [
                    {
                        "path": module.DOEP031_PROTECTED_PATH,
                        "scope": "shared_checkout",
                        "before": {"sha256": module.DOEP031_PROTECTED_BEFORE_SHA256},
                        "after": {"sha256": module.DOEP031_PROTECTED_AFTER_SHA256},
                    }
                ],
            }
        ).encode(),
    }
    for name, payload in artifacts.items():
        (attempt / name).write_bytes(payload)
    monkeypatch.setattr(
        module,
        "DOEP031_ARTIFACT_SHA256",
        {name: "sha256:" + hashlib.sha256(payload).hexdigest() for name, payload in artifacts.items()},
    )

    evidence = module._doep031_artifact_evidence(
        {"root": root, "state": state},
        task_cid=module.DOEP031_TASK_CID,
    )
    assert evidence["candidate_commit"] == module.DOEP031_CANDIDATE_COMMIT
    assert evidence["incident_path"] == module.DOEP031_PROTECTED_PATH

    (attempt / "implementation-protected-path-incident.json").write_bytes(b"{}")
    with pytest.raises(module.HandoffError, match="artifact .* drifted"):
        module._doep031_artifact_evidence(
            {"root": root, "state": state},
            task_cid=module.DOEP031_TASK_CID,
        )


def test_doep031_git_proof_requires_clean_strict_forward_disjoint_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    current_head = "c" * 40
    current_tree = "d" * 40
    dirty = {"value": ""}
    before = b"incident-before"
    after = b"control-after"
    monkeypatch.setattr(
        module,
        "DOEP031_PROTECTED_BEFORE_SHA256",
        hashlib.sha256(before).hexdigest(),
    )
    monkeypatch.setattr(
        module,
        "DOEP031_PROTECTED_AFTER_SHA256",
        hashlib.sha256(after).hexdigest(),
    )

    def fake_git_read(repository: Path, *arguments: str, binary: bool = False):
        if arguments[:3] == ("show", "-s", "--format=%H%n%P%n%T%n%s"):
            commit = arguments[3]
            if commit == module.DOEP031_CONTROL_COMMIT:
                return "\n".join(
                    [
                        commit,
                        module.DOEP031_CONTROL_PARENT,
                        module.DOEP031_CONTROL_TREE,
                        "Allow sealed supervisor control-plane reloads",
                    ]
                )
            if commit == module.DOEP031_CANDIDATE_COMMIT:
                return "\n".join(
                    [
                        commit,
                        module.DOEP031_BASELINE,
                        module.DOEP031_CANDIDATE_TREE,
                        "DOEP-031: Extend the current canonical implementation to add transactional event publication without creating a competing subsystem.",
                    ]
                )
            return "\n".join(
                [
                    module.DOEP031_CANDIDATE_CHILD,
                    module.DOEP031_BASE_CHILD,
                    module.DOEP031_CANDIDATE_CHILD_TREE,
                    "DOEP-031: Extend the current canonical implementation to add transactional event publication without creating a competing subsystem.",
                ]
            )
        if arguments[:2] == ("rev-parse", "HEAD^{commit}"):
            return current_head
        if arguments[:2] == ("rev-parse", "HEAD^{tree}"):
            return current_tree
        if arguments[0] == "rev-parse":
            return module.DOEP031_CANDIDATE_COMMIT
        if arguments[0] == "diff-tree":
            commit = arguments[-1]
            if commit == module.DOEP031_CONTROL_COMMIT:
                return "\n".join(module.DOEP031_CONTROL_PATHS)
            if commit == module.DOEP031_CANDIDATE_COMMIT:
                return "M\texternal/ipfs_kit"
            return "\n".join(f"M\t{path}" for path in module.DOEP031_CHILD_PATHS)
        if arguments[0] == "ls-tree":
            child = (
                module.DOEP031_BASE_CHILD
                if arguments[1] == module.DOEP031_BASELINE
                else module.DOEP031_CANDIDATE_CHILD
            )
            return f"160000 commit {child}\texternal/ipfs_kit"
        if arguments[0] == "cat-file":
            return before if arguments[-1].startswith(module.DOEP031_BASELINE) else after
        if arguments[0] == "status":
            return dirty["value"]
        raise AssertionError(arguments)

    def fake_is_ancestor(repository: Path, older: str, newer: str) -> bool:
        return not (
            older == module.DOEP031_CANDIDATE_COMMIT and newer == current_head
        )

    monkeypatch.setattr(module, "_git_read", fake_git_read)
    monkeypatch.setattr(module, "_git_is_ancestor", fake_is_ancestor)
    proof = module._doep031_git_evidence(tmp_path)
    assert proof["control_candidate_scope_disjoint"] is True
    assert proof["candidate_merged"] is False

    dirty["value"] = " M " + module.DOEP031_PROTECTED_PATH
    with pytest.raises(module.HandoffError, match="clean strict-forward"):
        module._doep031_git_evidence(tmp_path)


def test_doep031_authorization_is_immutable_and_revalidates_current_tree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    paths = {
        "doep031_recovery_sidecar": tmp_path / "sidecar.json",
        "doep031_recovery_authorization": tmp_path / "authorization.json",
    }
    artifacts = {"incident": "exact"}
    git_evidence = {"current_head": "a" * 40, "current_tree": "b" * 40}
    monkeypatch.setattr(
        module,
        "_doep031_artifact_evidence",
        lambda paths, task_cid: dict(artifacts),
    )
    monkeypatch.setattr(module, "_doep031_git_evidence", lambda: dict(git_evidence))
    authority = {
        **_authority_context(),
        "plan_root_cid": "sha256:6c197a4b92682b3b813656123e09956846dc4f5abadf417f37fb7cc0133ddba4",
        "repository_tree_id": "sha256:2de6ca649a36e4ae245d83ae39af8e66d529619ee302b69b34b796f9ae231efe",
    }
    sidecar, authorization = module._prepare_doep031_recovery_authorization(
        paths=paths,
        task_cid=module.DOEP031_TASK_CID,
        task_row=_doep031_row(module),
        authority_context=authority,
    )
    loaded = module._load_doep031_recovery_authorization(
        paths=paths,
        task_cid=module.DOEP031_TASK_CID,
        authority_context=authority,
    )
    assert loaded == (sidecar, authorization)
    assert authorization["transition_target"] == "retrying"
    assert authorization["direct_completion_authorized"] is False

    git_evidence["current_tree"] = "c" * 40
    with pytest.raises(module.HandoffError, match="authorization has drifted"):
        module._load_doep031_recovery_authorization(
            paths=paths,
            task_cid=module.DOEP031_TASK_CID,
            authority_context=authority,
        )


def test_doep031_command_uses_typed_retry_cas_and_stops_at_retrying(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    paths = {
        "operator_pid": tmp_path / "operator.pid",
        "doep031_recovery_sidecar": tmp_path / "sidecar.json",
        "doep031_recovery_authorization": tmp_path / "authorization.json",
        "doep031_recovery_receipt": tmp_path / "receipt.json",
    }
    population = {
        "plan_root_cid": "sha256:6c197a4b92682b3b813656123e09956846dc4f5abadf417f37fb7cc0133ddba4",
        "repository_tree_id": "sha256:2de6ca649a36e4ae245d83ae39af8e66d529619ee302b69b34b796f9ae231efe",
        "tasks": [
            {
                "task_alias": module.DOEP031_TASK_ALIAS,
                "task_cid": module.DOEP031_TASK_CID,
            }
        ],
    }
    authorization = {
        "expected_task_revision": 4,
        "task_body": _doep031_body(module),
        "terminal_receipt": dict(module.DOEP031_TERMINAL_RECEIPT),
        "max_task_attempts_before": 1,
        "max_task_attempts_after": 2,
        "operator_handoff_receipt_id": "sha256:authorization",
        "sidecar_evidence_id": "sha256:evidence",
        "now_ms": 1234,
        "authorized_at": "2026-08-30T00:00:00+00:00",
    }
    sidecar = {"evidence_id": "sha256:evidence"}
    calls: dict[str, object] = {}

    class Generation:
        @staticmethod
        def to_record():
            return {
                "store_id": "doep-v1-r5",
                "database_uuid": "uuid",
                "generation": 1,
                "fence_epoch": 1,
                "revision": 10,
            }

    class Result:
        accepted = True
        outcome = SimpleNamespace(value="accepted")
        result = {
            "task_cid": module.DOEP031_TASK_CID,
            "task_revision": 5,
            "attempt_number": 1,
            "fresh_attempt_number": 2,
            "max_task_attempts_before": 1,
            "max_task_attempts_after": 2,
            "attempt_refunded": False,
            "operator_handoff_receipt_id": "sha256:authorization",
            "sidecar_evidence_id": "sha256:evidence",
            "fresh_portal_revalidation_requirement_id": "sha256:revalidate",
        }

        @staticmethod
        def to_dict():
            return {"outcome": "accepted", "result": dict(Result.result)}

    class Client:
        selects = 0

        @staticmethod
        def load_generation():
            return Generation()

        def execute(self, operation: str, parameters: dict[str, object]):
            assert operation == "select_task_by_cid"
            assert parameters == {"task_cid": module.DOEP031_TASK_CID}
            self.selects += 1
            if self.selects == 1:
                return [_doep031_row(module)]
            return [_doep031_row(module, status="retrying", revision=5)]

        @staticmethod
        def recover_blocked_task_retry(**kwargs):
            calls["cas"] = kwargs
            return Result()

        @staticmethod
        def close():
            calls["client_closed"] = True

    client = Client()

    class Server:
        @staticmethod
        def start():
            return SimpleNamespace(server_id="server:test")

        @staticmethod
        def ready():
            return True

        @staticmethod
        def revoke_typed_client_grant(grant_id: str):
            calls["revoked"] = grant_id

        @staticmethod
        def stop():
            calls["stopped"] = True

    monkeypatch.setattr(module, "_load", lambda: (object(), population, paths))
    monkeypatch.setattr(module, "_build_server", lambda board, paths: Server())
    monkeypatch.setattr(
        module,
        "_make_blocked_retry_recovery_client",
        lambda server, board, task_cid, task_alias: (
            client,
            SimpleNamespace(grant_id="grant:test"),
        ),
    )
    monkeypatch.setattr(
        module,
        "_prepare_doep031_recovery_authorization",
        lambda **kwargs: (sidecar, authorization),
    )
    monkeypatch.setattr(
        module,
        "_revalidate_doep031_recovery",
        lambda **kwargs: calls.setdefault("revalidated", True),
    )
    monkeypatch.setattr(
        module,
        "_immutable_json",
        lambda path, payload: calls.setdefault("receipt", dict(payload)),
    )

    assert module.recover_doep031_protected_control_plane_update() == 0
    assert calls["cas"]["require_fresh_portal_revalidation"] is True
    assert calls["receipt"]["transition_status"] == "retrying"
    assert calls["receipt"]["direct_completion_authorized"] is False
    assert calls["revalidated"] is True
    assert calls["stopped"] is True
