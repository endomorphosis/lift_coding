"""Regressions for the PCTDD g9 orphan-terminal recovery boundary."""

from __future__ import annotations

import importlib.util
import json
import sys
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
ACCELERATE_SOURCE = ROOT / "external/ipfs_accelerate"
if str(ACCELERATE_SOURCE) not in sys.path:
    sys.path.insert(0, str(ACCELERATE_SOURCE))


def _module() -> Any:
    g7_path = ROOT / "scripts/pctdd_g7_source_binding_successor.py"
    g7_spec = importlib.util.spec_from_file_location(
        "pctdd_g7_source_binding_successor", g7_path
    )
    assert g7_spec is not None and g7_spec.loader is not None
    g7 = importlib.util.module_from_spec(g7_spec)
    g7_spec.loader.exec_module(g7)
    sys.modules["pctdd_g7_source_binding_successor"] = g7

    path = ROOT / "scripts/pctdd_g9_descendant_source_successor.py"
    spec = importlib.util.spec_from_file_location(
        "pctdd_g9_orphan_recovery_regressions", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def migration() -> Any:
    return _module()


def _admitted_validation(*, task: str, profile: str) -> dict[str, Any]:
    launcher = {
        "mode": "sealed-interpreter",
        "content_sha256": "1" * 64,
        "interpreter_sha256": "2" * 64,
        "policy_sha256": "3" * 64,
        "sealed": True,
    }
    return {
        "attempted": True,
        "returncode": 0,
        "timeout": False,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "record_parse_error": False,
        "duplicate_json_key": False,
        "records": [
            {
                "task_id": task,
                "profile_id": profile,
                "step": 0,
                "status": "passed",
                "returncode": 0,
                "evidence_policy": "required_acceptance",
                "validation_python_launcher": dict(launcher),
                "pytest_phase_evidence": {
                    "schema": "pctdd/pytest-phase-outcome@1",
                    "sha256": "sha256:" + "4" * 64,
                    "test_count": 2,
                    "phase_count": 6,
                    "fully_passed_test_count": 2,
                    "counts": {
                        "passed": 6,
                        "failed": 0,
                        "skipped": 0,
                        "xfail": 0,
                        "xpass": 0,
                        "error": 0,
                        "rerun": 0,
                    },
                },
            },
            {
                "task_id": task,
                "profile_id": profile,
                "step": 1,
                "status": "passed",
                "returncode": 0,
                "evidence_policy": "protected_baseline_regression",
                "validation_python_launcher": dict(launcher),
            },
        ],
    }


def test_validation_admission_requires_exact_complete_two_record_evidence(
    migration: Any,
) -> None:
    task = "PCTDD-001"
    profile = "pctdd-validation/PCTDD-PLAN-V1.1/PCTDD-001@1"
    evidence = _admitted_validation(task=task, profile=profile)

    assert migration._validation_is_admitted(
        evidence, expected_profile=profile, expected_task=task
    )

    truncated = deepcopy(evidence)
    truncated["stdout_truncated"] = True
    assert not migration._validation_is_admitted(
        truncated, expected_profile=profile, expected_task=task
    )

    missing_fully_passed = deepcopy(evidence)
    del missing_fully_passed["records"][0]["pytest_phase_evidence"][
        "fully_passed_test_count"
    ]
    assert not migration._validation_is_admitted(
        missing_fully_passed, expected_profile=profile, expected_task=task
    )


def test_live_progressed_check_uses_only_authenticated_quack_transport(
    migration: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "g9"
    target.mkdir()
    migration_marker = target / migration.MIGRATION_MARKER
    recovery_marker = target / migration.ORPHAN_RECOVERY_MARKER
    migration_marker.write_text("{}\n", encoding="utf-8")
    recovery_marker.write_text("{}\n", encoding="utf-8")

    endpoint = "quack:127.0.0.1:27278"
    task_definition_digest = "task-definitions:g9"
    policy = {
        "target_runtime_root": "g9",
        "target_quack_endpoint": endpoint,
        "stopped_predecessor_capture": {
            "prior_control_projection": {
                "task_definition_digest": task_definition_digest
            }
        },
    }
    migration_receipt = {
        "migration_event_watermark": 41,
        "migration_event_prefix_digest": "event-prefix:migration",
    }
    recovery_receipt = {
        "recovery_event_watermark": 52,
        "recovery_event_prefix_digest": "event-prefix:recovery",
    }
    marker_records = {
        migration_marker: (migration_receipt, (1, 2, 3)),
        recovery_marker: (recovery_receipt, (4, 5, 6)),
    }
    identity = {
        "server_id": "server:g9",
        "store_id": "g9/control.duckdb",
        "database_uuid": "database:g9",
        "process_birth_id": "process:g9",
        "listen_uri": endpoint,
        "extension_fingerprint": "quack:extensions",
        "schema_revision": 9,
        "generation": 31,
        "started_at": "2026-09-01T00:00:00Z",
        "status": "ready",
    }
    transport_calls: list[tuple[str, Any]] = []

    monkeypatch.setattr(migration, "_policy", lambda _config: dict(policy))
    monkeypatch.setattr(
        migration.g7, "_assert_source_delta", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        migration.g7,
        "_confined",
        lambda *_args, **_kwargs: target,
    )
    monkeypatch.setattr(
        migration,
        "_load_marker_snapshot",
        lambda *, path, **_kwargs: marker_records[path],
    )
    monkeypatch.setattr(migration, "_validate_receipt", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        migration, "_validate_recovery_receipt", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        migration,
        "_live_g9_owner",
        lambda **_kwargs: {"identity": dict(identity)},
    )

    def projection(control_target: Any) -> dict[str, Any]:
        transport_calls.append(("projection", control_target))
        assert control_target == endpoint
        return {
            "tasks": [
                {"task_alias": f"PCTDD-{index:03d}"} for index in range(54)
            ],
            "task_definition_digest": task_definition_digest,
        }

    def event_prefix(control_target: Any, watermark: int) -> str:
        transport_calls.append(("event-prefix", control_target))
        assert control_target == endpoint
        return {
            41: migration_receipt["migration_event_prefix_digest"],
            52: recovery_receipt["recovery_event_prefix_digest"],
        }[watermark]

    def latest(control_target: Any) -> dict[str, Any]:
        transport_calls.append(("latest-state-server", control_target))
        assert control_target == endpoint
        return {**identity, "stopped_at": None}

    monkeypatch.setattr(migration.g7, "_control_projection", projection)
    monkeypatch.setattr(migration, "_event_prefix", event_prefix)
    monkeypatch.setattr(migration.g7, "_latest_state_server", latest)
    monkeypatch.setattr(
        migration.g7,
        "_open_local_database",
        lambda *_args, **_kwargs: pytest.fail(
            "live allow_progressed inspection opened the local DuckDB path"
        ),
    )

    result = migration.check_descendant_source(
        root=tmp_path,
        config={"descendant_source_successor_materialization": policy},
        population={"repository_tree_id": "tree:g9"},
        allow_progressed=True,
    )

    assert result["valid"] is True
    assert result["verification_transport"] == "quack"
    assert transport_calls
    assert {target for _operation, target in transport_calls} == {endpoint}


def test_live_quack_rows_match_offline_tuple_projections(
    migration: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
        DuckDBRow,
    )

    task_columns = (
        "task_alias",
        "task_cid",
        "goal_cid",
        "plan_cid",
        "objective_id",
        "ordinal",
        "status",
        "revision",
        "priority",
        "identity_json",
        "body_json",
    )
    task_row = (
        "PCTDD-000",
        "task:000",
        "goal:000",
        "plan:000",
        "PCTDD-G000",
        1,
        "completed",
        3,
        "critical",
        json.dumps({"task_alias": "PCTDD-000"}),
        json.dumps({"completion_receipt": {"accepted": True}}),
    )
    event_columns = (
        "event_id",
        "stream_id",
        "sequence",
        "global_sequence",
        "event_type",
        "task_cid",
        "attempt_id",
        "session_id",
        "recorded_at",
        "body_json",
    )
    event_row = (
        "event:1",
        "task:000",
        1,
        1,
        "task.completed",
        "task:000",
        None,
        "session:operator",
        "2026-09-01T00:00:00Z",
        "{}",
    )
    projection_tables = {
        "goals",
        "goal_edges",
        "task_dependencies",
        "task_outputs",
        "task_acceptance",
        "task_validations",
        "completion_receipts",
        "validation_results",
        "evidence_nodes",
        "plan_revisions",
    }

    class Cursor:
        def __init__(
            self,
            columns: tuple[str, ...],
            rows: list[tuple[Any, ...]],
            *,
            mapped: bool,
        ) -> None:
            self.columns = columns
            self.rows = rows
            self.mapped = mapped

        def _row(self, values: tuple[Any, ...]) -> Any:
            return DuckDBRow(self.columns, values) if self.mapped else values

        def fetchall(self) -> list[Any]:
            return [self._row(row) for row in self.rows]

        def fetchone(self) -> Any | None:
            return self._row(self.rows[0]) if self.rows else None

    class Connection:
        def __init__(self, *, mapped: bool) -> None:
            self.mapped = mapped

        def execute(self, sql: str, _parameters: Any = None) -> Cursor:
            query = " ".join(sql.split())
            if query.startswith("SELECT status, COUNT(*) FROM tasks"):
                return Cursor(
                    ("status", "count_star()"),
                    [("completed", 1)],
                    mapped=self.mapped,
                )
            if query.startswith("SELECT plan_cid, plan_alias"):
                return Cursor(
                    ("plan_cid", "plan_alias", "status", "revision", "body_json"),
                    [("plan:000", "pctdd", "active", 2, "{}")],
                    mapped=self.mapped,
                )
            if query.startswith("SELECT task_alias,task_cid"):
                return Cursor(task_columns, [task_row], mapped=self.mapped)
            if query.startswith("SELECT COALESCE(MAX(global_sequence),0)"):
                return Cursor(("max", "count_star()"), [(1, 1)], mapped=self.mapped)
            if query.startswith("SELECT COUNT(*) FROM"):
                table = query.split("FROM", 1)[1].strip().split()[0]
                return Cursor(
                    ("count_star()",),
                    [(1 if table in {"goals", "tasks"} else 0,)],
                    mapped=self.mapped,
                )
            if query.startswith("DESCRIBE SELECT * FROM"):
                table = query.rsplit(" ", 1)[1]
                assert table in projection_tables
                return Cursor(
                    ("column_name", "column_type"),
                    [("task_cid", "VARCHAR")],
                    mapped=self.mapped,
                )
            if query.startswith("SELECT * FROM"):
                table = query.rsplit(" ", 1)[1]
                assert table in projection_tables
                return Cursor(("task_cid",), [], mapped=self.mapped)
            if query.startswith("SELECT event_id,stream_id"):
                return Cursor(event_columns, [event_row], mapped=self.mapped)
            if query.startswith("SELECT server_id,store_id"):
                columns = (
                    "server_id",
                    "store_id",
                    "database_uuid",
                    "process_birth_id",
                    "listen_uri",
                    "extension_fingerprint",
                    "schema_revision",
                    "generation",
                    "started_at",
                    "stopped_at",
                    "status",
                    "revision",
                )
                values = (
                    "server:1",
                    "control.duckdb",
                    "database:1",
                    "birth:1",
                    "quack:127.0.0.1:27278",
                    "sha256:extension",
                    1,
                    31,
                    "2026-09-01T00:00:00Z",
                    None,
                    "ready",
                    1,
                )
                return Cursor(columns, [values], mapped=self.mapped)
            raise AssertionError(f"unexpected projection query: {query}")

        def close(self) -> None:
            pass

    monkeypatch.setattr(
        migration.g7, "_open_control_target", lambda _target: Connection(mapped=False)
    )
    offline_projection = migration.g7._control_projection(Path("offline.duckdb"))
    offline_prefix = migration._event_prefix(Path("offline.duckdb"), 1)
    offline_owner = migration.g7._latest_state_server(Path("offline.duckdb"))

    monkeypatch.setattr(
        migration.g7, "_open_control_target", lambda _target: Connection(mapped=True)
    )
    live_projection = migration.g7._control_projection("quack:127.0.0.1:27278")
    live_prefix = migration._event_prefix("quack:127.0.0.1:27278", 1)
    live_owner = migration.g7._latest_state_server("quack:127.0.0.1:27278")

    assert live_projection == offline_projection
    assert live_prefix == offline_prefix
    assert live_owner == offline_owner


def test_migration_replay_with_final_recovery_marker_skips_recovery_mutation(
    migration: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    target = tmp_path / "g9"
    target.mkdir()
    (target / migration.MIGRATION_MARKER).write_text("{}\n", encoding="utf-8")
    (target / migration.ORPHAN_RECOVERY_MARKER).write_text(
        "{}\n", encoding="utf-8"
    )
    policy = {"target_runtime_root": "g9"}
    checked: list[bool] = []

    monkeypatch.setattr(migration, "_policy", lambda _config: dict(policy))
    monkeypatch.setattr(
        migration.g7, "_assert_source_delta", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        migration.g7, "_confined", lambda *_args, **_kwargs: target
    )
    monkeypatch.setattr(
        migration,
        "recover_orphan_terminals",
        lambda **_kwargs: pytest.fail(
            "published orphan recovery was mutated during migration replay"
        ),
    )

    expected = {"schema": migration.CHECK_SCHEMA, "valid": True}

    def check(**kwargs: Any) -> dict[str, Any]:
        checked.append(bool(kwargs["allow_progressed"]))
        return expected

    monkeypatch.setattr(migration, "check_descendant_source", check)

    result = migration.migrate_descendant_source(
        root=tmp_path,
        config={"descendant_source_successor_materialization": policy},
        population={"repository_tree_id": "tree:g9"},
    )

    assert result == expected
    assert checked == [True]


def test_parsed_inner_timeout_is_blocking_not_retrying_or_admitted(
    migration: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ipfs_accelerate_py.agent_supervisor.task_sources import (
        database_task_source as task_source_module,
    )

    tasks = {
        alias: SimpleNamespace(
            task_alias=alias,
            task_cid=f"task:{alias}",
            status="blocked",
            revision=7,
            body={"completion_receipt": {"claim_id": f"claim:{alias}"}},
        )
        for alias in migration.ORPHAN_RECOVERY_ALIASES
    }

    class FakeTaskSource:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def __enter__(self) -> "FakeTaskSource":
            return self

        def __exit__(self, *_details: object) -> bool:
            return False

        def get_task(self, alias: str) -> Any:
            return tasks[alias]

    profiles = {
        alias: f"pctdd-validation/PCTDD-PLAN-V1.1/{alias}@1"
        for alias in migration.ORPHAN_RECOVERY_ALIASES
    }
    policy = {
        "prior_store_generation": "g8",
        "target_store_generation": "g9",
        "orphan_terminal_recovery": {
            "timeout_seconds": 10,
            "validation_profiles": profiles,
        },
    }

    def parsed_inner_timeout(
        argv: list[str], *, root: Path, timeout_seconds: int
    ) -> dict[str, Any]:
        del root, timeout_seconds
        alias = argv[-1]
        launcher = {
            "mode": "sealed-interpreter",
            "content_sha256": "1" * 64,
            "interpreter_sha256": "2" * 64,
            "policy_sha256": "3" * 64,
            "sealed": True,
        }
        return {
            "attempted": True,
            "returncode": 124,
            "timeout": False,
            "stdout_truncated": False,
            "stderr_truncated": False,
            "record_parse_error": False,
            "duplicate_json_key": False,
            "records": [
                {
                    "task_id": alias,
                    "profile_id": profiles[alias],
                    "step": 0,
                    "status": "timeout",
                    "returncode": 124,
                    "evidence_policy": "required_acceptance",
                    "validation_python_launcher": launcher,
                }
            ],
        }

    monkeypatch.setattr(task_source_module, "DatabaseTaskSource", FakeTaskSource)
    monkeypatch.setattr(
        migration,
        "_terminal_claim_binding",
        lambda **kwargs: {
            "lane": 0,
            "claim": {"claim_id": kwargs["blocked_receipt"]["claim_id"]},
        },
    )
    monkeypatch.setattr(
        migration,
        "_current_output_manifest",
        lambda *_args, **_kwargs: {"outputs": [], "missing_outputs": []},
    )
    monkeypatch.setattr(
        migration,
        "_task_validation_argv",
        lambda _task, *, alias, recovery_policy: ["validation-dispatcher", alias],
    )
    monkeypatch.setattr(migration.g7, "_source_binding", lambda *_args: "source:g9")
    monkeypatch.setattr(migration, "_capture_binding", lambda _policy: "capture:g8")
    monkeypatch.setattr(
        migration.g7,
        "_control_projection",
        lambda _path: {"event_watermark": 7, "event_prefix_digest": "events:g8"},
    )
    monkeypatch.setattr(
        migration.g7,
        "_coordination_projection",
        lambda _path: {"claims": [], "completions": []},
    )

    plan = migration._prepare_orphan_recovery_plan(
        root=tmp_path,
        target=tmp_path / "g9",
        population={"repository_tree_id": "tree:g9", "plan_root_cid": "plan:g9"},
        policy=policy,
        migration_receipt={"receipt_cid": "migration:g9", "control_store": {}},
        validation_runner=parsed_inner_timeout,
    )

    assert not migration._validation_is_admitted(
        parsed_inner_timeout(
            ["validation-dispatcher", "PCTDD-001"],
            root=tmp_path,
            timeout_seconds=10,
        ),
        expected_profile=profiles["PCTDD-001"],
        expected_task="PCTDD-001",
    )
    assert [decision["target_status"] for decision in plan["decisions"]] == [
        "blocked",
        "blocked",
        "blocked",
    ]


def test_validation_authority_binds_launcher_but_not_log_observations(
    migration: Any,
) -> None:
    task = "PCTDD-001"
    profile = "pctdd-validation/PCTDD-PLAN-V1.1/PCTDD-001@1"
    evidence = _admitted_validation(task=task, profile=profile)

    authority = migration._validation_authority_projection(
        evidence, expected_profile=profile, expected_task=task
    )

    observational = deepcopy(evidence)
    observational.update(
        {
            "stdout_sha256": "a" * 64,
            "stderr_sha256": "b" * 64,
            "stdout_size_bytes": 1234,
            "stderr_size_bytes": 5678,
        }
    )
    observational["records"][0]["elapsed_seconds"] = 3.5
    observational["records"][1]["elapsed_seconds"] = 13.75
    assert migration._validation_authority_projection(
        observational, expected_profile=profile, expected_task=task
    ) == authority

    launcher_drift = deepcopy(evidence)
    for record in launcher_drift["records"]:
        record["validation_python_launcher"]["interpreter_sha256"] = "f" * 64
    assert migration._validation_is_admitted(
        launcher_drift, expected_profile=profile, expected_task=task
    )
    assert migration._validation_authority_projection(
        launcher_drift, expected_profile=profile, expected_task=task
    ) != authority


def test_blocked_recovery_plan_is_rejected_before_persistent_publication(
    migration: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ipfs_accelerate_py.agent_supervisor.runtime import (
        quack_state_server as state_server,
    )

    target = tmp_path / "g9"
    target.mkdir()
    policy = {"target_runtime_root": "g9"}
    blocked_plan = {
        "recovery_plan_id": "recovery:blocked",
        "decisions": [
            {"task_alias": "PCTDD-001", "target_status": "blocked"}
        ],
    }
    published_paths: list[Path] = []

    @contextmanager
    def offline_fence(**_kwargs: Any) -> Any:
        yield SimpleNamespace(close=lambda: None)

    monkeypatch.setattr(state_server, "offline_state_server_fence", offline_fence)
    monkeypatch.setattr(migration, "_policy", lambda _config: dict(policy))
    monkeypatch.setattr(
        migration.g7, "_assert_source_delta", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        migration.g7, "_confined", lambda *_args, **_kwargs: target
    )
    monkeypatch.setattr(
        migration,
        "_load_initial_migration_receipt",
        lambda **_kwargs: {"receipt_cid": "migration:g9"},
    )
    monkeypatch.setattr(migration, "_store_relative_files", lambda: ())
    monkeypatch.setattr(
        migration,
        "_prepare_orphan_recovery_plan",
        lambda **_kwargs: deepcopy(blocked_plan),
    )
    monkeypatch.setattr(
        migration, "_validate_recovery_plan", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        migration,
        "_verify_prepared_recovery_progress",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        migration.g7, "_close_offline_fence_probe", lambda _probe: None
    )
    monkeypatch.setattr(
        migration.g7,
        "_retire_private_stage_coordination_locks",
        lambda _target: None,
    )
    monkeypatch.setattr(
        migration.g7,
        "_write_new_json",
        lambda path, _payload: published_paths.append(Path(path)),
    )
    monkeypatch.setattr(
        migration.g7, "_fsync_private_file", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(migration.g7, "_fsync_directory", lambda _path: None)

    with pytest.raises(
        migration.DescendantSourceSuccessorError,
        match="validation infrastructure is unavailable",
    ):
        migration.recover_orphan_terminals(
            root=tmp_path,
            config={"descendant_source_successor_materialization": policy},
            population={"repository_tree_id": "tree:g9"},
        )

    assert published_paths == []
    assert not (target / migration.ORPHAN_RECOVERY_PREPARED).exists()


def test_replay_revalidates_before_non_expiring_recovery_evidence_apply(
    migration: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from ipfs_accelerate_py.agent_supervisor.runtime import (
        quack_state_server as state_server,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources import (
        database_task_source as task_source_module,
    )

    target = tmp_path / "g9"
    target.mkdir()
    prepared = target / migration.ORPHAN_RECOVERY_PREPARED
    prepared.write_text("{}\n", encoding="utf-8")
    policy = {"target_runtime_root": "g9"}
    plan = {"recovery_plan_id": "recovery:fresh", "decisions": []}
    calls: list[str] = []
    constructor_kwargs: list[dict[str, Any]] = []

    @contextmanager
    def offline_fence(**_kwargs: Any) -> Any:
        yield SimpleNamespace(close=lambda: None)

    class FakeTaskSource:
        def __init__(self, *_args: Any, **kwargs: Any) -> None:
            calls.append("apply")
            constructor_kwargs.append(dict(kwargs))

        def __enter__(self) -> "FakeTaskSource":
            return self

        def __exit__(self, *_details: object) -> bool:
            return False

    monkeypatch.setattr(state_server, "offline_state_server_fence", offline_fence)
    monkeypatch.setattr(task_source_module, "DatabaseTaskSource", FakeTaskSource)
    monkeypatch.setattr(migration, "_policy", lambda _config: dict(policy))
    monkeypatch.setattr(
        migration.g7, "_assert_source_delta", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        migration.g7, "_confined", lambda *_args, **_kwargs: target
    )
    monkeypatch.setattr(
        migration,
        "_load_initial_migration_receipt",
        lambda **_kwargs: {"receipt_cid": "migration:g9"},
    )
    monkeypatch.setattr(migration.g7, "_load_json", lambda *_args, **_kwargs: plan)
    monkeypatch.setattr(
        migration, "_validate_recovery_plan", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        migration,
        "_verify_prepared_recovery_progress",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        migration,
        "_revalidate_prepared_recovery_plan",
        lambda **_kwargs: calls.append("revalidate"),
    )
    monkeypatch.setattr(
        migration,
        "_recovery_receipt",
        lambda **_kwargs: {"recovery_receipt_cid": "receipt:fresh"},
    )
    monkeypatch.setattr(
        migration, "_publish_recovery_receipt", lambda **_kwargs: None
    )
    monkeypatch.setattr(
        migration.g7, "_close_offline_fence_probe", lambda _probe: None
    )
    monkeypatch.setattr(
        migration.g7,
        "_retire_private_stage_coordination_locks",
        lambda _target: None,
    )

    migration.recover_orphan_terminals(
        root=tmp_path,
        config={"descendant_source_successor_materialization": policy},
        population={"repository_tree_id": "tree:g9", "plan_root_cid": "plan:g9"},
    )

    assert calls == ["revalidate", "apply"]
    assert constructor_kwargs == [
        {
            "owner_id": "pctdd-descendant-source-g9:orphan-recovery-apply",
            "install_schema": False,
            "repository_tree_id": "tree:g9",
            "plan_root_cid": "plan:g9",
            "evidence_freshness_seconds": 0,
        }
    ]
