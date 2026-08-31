"""Focused tests for the operator-owned PCTDD g8 -> g9 successor."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
ACCELERATE = ROOT / "external/ipfs_accelerate"
if str(ACCELERATE) not in sys.path:
    sys.path.insert(0, str(ACCELERATE))


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
        "pctdd_g9_descendant_source_successor", path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _generator() -> Any:
    path = ROOT / "scripts/generate_parallel_content_sealing_proof_carrying_tdd_controls.py"
    spec = importlib.util.spec_from_file_location("pctdd_g9_control_generator", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def migration() -> Any:
    return _module()


def test_final_capture_gate_requires_a_clean_committed_descendant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator = _generator()

    def dirty_git(*arguments: str, **_kwargs: Any) -> str:
        if arguments[:2] == ("rev-parse", "HEAD"):
            return "f" * 40
        if arguments[0] == "status":
            return " M protected-control"
        raise AssertionError(arguments)

    monkeypatch.setattr(generator, "git", dirty_git)
    with pytest.raises(RuntimeError, match="clean outer worktree"):
        generator._assert_clean_descendant_capture_source()

    def clean_git(*arguments: str, **_kwargs: Any) -> str:
        if arguments[:2] == ("rev-parse", "HEAD"):
            return "f" * 40
        if arguments[0] == "status":
            return ""
        if arguments[0] == "merge-base":
            return ""
        if arguments[0] == "diff":
            return "M\tscripts/pctdd_g9_descendant_source_successor.py"
        raise AssertionError(arguments)

    monkeypatch.setattr(generator, "git", clean_git)
    generator._assert_clean_descendant_capture_source()


def test_active_board_and_guardrail_archive_are_exact() -> None:
    board_path = Path(
        "docs/architecture/parallel_content_sealing_proof_carrying_tdd.todo.md"
    )
    current = (ROOT / board_path).read_bytes()
    aliases = re.findall(rb"(?m)^## (PCTDD-\d{3})\b", current)
    assert aliases == [f"PCTDD-{index:03d}".encode() for index in range(54)]

    historical = subprocess.check_output(
        ["git", "show", f"9eec0a6d3dd5c0915b85080623c958563d422e3a:{board_path}"],
        cwd=ROOT,
    )
    headings = list(re.finditer(rb"(?m)^## (PCTDD-\d{3})\b.*(?:\n|$)", historical))
    blocks: dict[str, bytes] = {}
    for index, match in enumerate(headings):
        alias = match.group(1).decode()
        if alias in {"PCTDD-054", "PCTDD-055", "PCTDD-056"}:
            end = headings[index + 1].start() if index + 1 < len(headings) else len(historical)
            blocks[alias] = historical[match.start():end]
    archive = json.loads(
        (
            ROOT
            / "docs/architecture/parallel_content_sealing_proof_carrying_tdd_inventory/g8_resolved_guardrail_archive.json"
        ).read_text(encoding="utf-8")
    )
    assert set(blocks) == {"PCTDD-054", "PCTDD-055", "PCTDD-056"}
    for record in archive["guardrails"]:
        block = blocks[record["task_id"]]
        assert len(block) == record["markdown_block_size_bytes"]
        assert hashlib.sha256(block).hexdigest() == record["markdown_block_sha256"]


def _population() -> dict[str, Any]:
    return {
        "source_head": "synthetic-g9-head",
        "repository_tree_id": "synthetic-g9-tree",
        "plan_root_cid": "plan:pctdd",
        "source_forest": {"source_forest_root": "forest:g9"},
        "source_identities": {"accelerate": "synthetic-g9-head"},
    }


def _control(migration: Any, directory: Path) -> Path:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    directory.mkdir(parents=True, exist_ok=True)
    database = directory / "control.duckdb"
    plan = _population()["plan_root_cid"]
    tasks = []
    for index in range(54):
        alias = f"PCTDD-{index:03d}"
        status = "completed" if index in {0, 2, 3, 4, 21, 22} else "todo"
        tasks.append(
            {
                "task_cid": f"task:{index:03d}",
                "task_id": alias,
                "goal_cid": "goal:pctdd",
                "plan_cid": plan,
                "ordinal": index,
                "status": status,
                "provider_role": "operator-only" if index == 0 else "grok-implement",
                "title": alias,
                "validations": [["python", "-m", "pytest", alias]],
            }
        )
    material = {
        "repository_tree_id": "historical-g8-tree",
        "plan_root_cid": plan,
        "goals": [{"goal_cid": "goal:pctdd", "goal_id": "PCTDD-G000"}],
        "plans": [
            {
                "plan_cid": plan,
                "plan_alias": "PCTDD-PLAN-V1.1",
                "goal_cid": "goal:pctdd",
                "status": "active",
            }
        ],
        "tasks": tasks,
    }
    with DatabaseTaskSource(
        database,
        owner_id="pctdd-g9-test:materialize",
        repository_tree_id="historical-g8-tree",
        plan_root_cid=plan,
    ) as source:
        source.materialize(material)
        operator = source.get_task("PCTDD-000")
        assert operator is not None
        source.record_evidence(
            task_cid=operator.task_cid,
            evidence_kind="synthetic-g8-history",
            digest="sha256:" + "1" * 64,
            body={"schema": "synthetic/history@1"},
        )
    return database


def _capture(migration: Any, database: Path) -> dict[str, Any]:
    prior = migration.g7._control_projection(database)
    return {
        "schema": migration.CAPTURE_SCHEMA,
        "prior_control_store": {"path": "g8/control.duckdb", "sha256": "0" * 64, "size_bytes": 1},
        "prior_generation_receipt": {"path": "g8/receipt.json", "sha256": "1" * 64, "size_bytes": 1},
        "prior_stopped_owner_status": {"path": "g8/status.json", "sha256": "2" * 64, "size_bytes": 1},
        "prior_owner_identity": {"status": "stopped"},
        "prior_control_projection": prior,
        "coordination_stores": [
            {
                "lane": lane,
                "path": f"g8/lane-{lane}.duckdb",
                "sha256": str(lane) * 64,
                "size_bytes": 1,
                "projection_root": f"projection:{lane}",
                "counts": {name: 0 for name in migration.ACTIVE_COORDINATION_COUNTS},
            }
            for lane in range(4)
        ],
        "guardrail_archive": {"path": "archive.json", "sha256": "a" * 64, "size_bytes": 1},
        "accepted_plan_root_cid": _population()["plan_root_cid"],
        "prior_plan_revision": 1,
    }


def _policy(migration: Any, database: Path, *, pending: bool = False) -> dict[str, Any]:
    return {
        "schema": migration.MIGRATION_SCHEMA,
        "migration_revision": "PCTDD-DESCENDANT-SOURCE-G9",
        "prior_store_generation": "pctdd-v1-g8",
        "target_store_generation": "pctdd-v1-g9",
        "prior_runtime_root": "g8",
        "target_runtime_root": "g9",
        "target_quack_endpoint": "quack:127.0.0.1:27278",
        "receipt_marker": migration.MIGRATION_MARKER,
        "capture_status": (
            "pending_stopped_g8_capture" if pending else "sealed_stopped_g8_capture"
        ),
        "stopped_predecessor_capture": None if pending else _capture(migration, database),
        "control_source_anchor_head": "0" * 40,
        "control_source_anchor_tree": "1" * 40,
        "operator_control_paths": ["scripts/pctdd_g9_descendant_source_successor.py"],
        "governed_gitlinks": {
            "external/ipfs_accelerate": "2" * 40,
            "external/ipfs_datasets": "3" * 40,
            "external/ipfs_kit": "4" * 40,
        },
        "expected_task_aliases": list(migration.EXPECTED_ALIASES),
        "generated_guardrail_policy": {
            "markdown_is_bootstrap_only": True,
            "discovery_and_event_evidence_preserved": True,
            "generated_task_projection": "disabled_for_sealed_board",
            **{flag: False for flag in migration.GUARDRAIL_FLAGS},
        },
        "copy_policy": {
            "copied": ["authoritative_control_store", "coordination_history"],
            "not_copied": ["owner_runtime", "worktrees", "merge_state"],
            "publication": "private_stage_hash_verify_no_overwrite_marker_last",
            "g8_remains_read_only_history": True,
        },
    }


def test_pending_policy_is_typed_and_cannot_admit_migration(
    migration: Any, tmp_path: Path
) -> None:
    database = _control(migration, tmp_path)
    config = {"descendant_source_successor_materialization": _policy(migration, database, pending=True)}
    result = migration.validate_pending_policy(config)
    assert result == {
        "schema": migration.CHECK_SCHEMA,
        "valid": True,
        "migration_admitted": False,
        "capture_status": "pending_stopped_g8_capture",
    }
    with pytest.raises(migration.DescendantSourceSuccessorError, match="not sealed"):
        migration._policy(config)


def test_check_policy_cli_is_static_before_canonical_branch_integration(
    migration: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    result = migration.main(
        [
            "check-policy",
            "--config",
            str(
                ROOT
                / "config/agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"
            ),
        ]
    )
    assert result == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "capture_status": "pending_stopped_g8_capture",
        "migration_admitted": False,
        "schema": migration.CHECK_SCHEMA,
        "valid": True,
    }


@pytest.mark.parametrize("flag", ("retry_budget_guardrail_enabled", "dependency_guardrail_enabled", "reconciliation_guardrail_enabled"))
def test_policy_rejects_every_markdown_generating_guardrail(
    migration: Any, tmp_path: Path, flag: str
) -> None:
    database = _control(migration, tmp_path / flag)
    policy = _policy(migration, database)
    policy["generated_guardrail_policy"][flag] = True
    with pytest.raises(migration.DescendantSourceSuccessorError, match="guardrail"):
        migration._policy({"descendant_source_successor_materialization": policy})


@pytest.mark.parametrize("count_name", ("active_task_claims", "active_task_attempts", "active_fenced_leases", "active_resource_claims", "active_maintenance_leases"))
def test_policy_rejects_active_coordination_authority(
    migration: Any, tmp_path: Path, count_name: str
) -> None:
    database = _control(migration, tmp_path / count_name)
    policy = _policy(migration, database)
    policy["stopped_predecessor_capture"]["coordination_stores"][0]["counts"][count_name] = 1
    with pytest.raises(migration.DescendantSourceSuccessorError, match="active"):
        migration._policy({"descendant_source_successor_materialization": policy})


def test_control_suffix_preserves_all_54_tasks_receipts_and_event_prefix(
    migration: Any, tmp_path: Path
) -> None:
    database = _control(migration, tmp_path)
    prior = migration.g7._control_projection(database)
    policy = _policy(migration, database)
    suffix = migration._apply_control_suffix(
        database,
        root=tmp_path,
        population=_population(),
        policy=policy,
        prior_projection=prior,
    )
    migration.g7._checkpoint_database(database)
    post = migration._verify_staged_successor(
        database, prior=prior, policy=policy, suffix=suffix
    )
    assert [item["task_alias"] for item in post["tasks"]] == list(migration.EXPECTED_ALIASES)
    assert post["tasks"] == prior["tasks"]
    assert post["statuses"] == prior["statuses"]
    assert post["task_definition_digest"] == prior["task_definition_digest"]
    assert post["historical_row_hashes"]["completion_receipts"] == prior["historical_row_hashes"]["completion_receipts"]
    assert post["event_count"] == prior["event_count"] + 2
    assert migration._event_prefix(database, prior["event_count"]) == prior["event_prefix_digest"]
    assert not any(item["task_alias"] in {"PCTDD-054", "PCTDD-055", "PCTDD-056"} for item in post["tasks"])


def _small_receipt(migration: Any, root: Path, stage: Path) -> dict[str, Any]:
    (stage / "state").mkdir(mode=0o700)
    control = stage / "control.duckdb"
    control.write_bytes(b"control")
    control.chmod(0o600)
    stores = []
    for lane in range(4):
        path = stage / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
        path.parent.mkdir(mode=0o700)
        path.write_bytes(f"lane-{lane}".encode())
        path.chmod(0o600)
        digest, size = migration.g7._stable_file(path, root=root, noun="lane")
        stores.append({"lane": lane, "sha256": digest, "size_bytes": size})
    digest, size = migration.g7._stable_file(control, root=root, noun="control")
    body = {
        "schema": migration.RECEIPT_SCHEMA,
        "target_store_generation": "pctdd-v1-g9",
        "control_store": {"sha256": digest, "size_bytes": size},
        "coordination_stores": stores,
    }
    return {**body, "receipt_cid": migration.g7._identity(body)}


@pytest.mark.parametrize("crash_point", ("prepared", "renamed", "pending", "linked"))
def test_marker_last_publication_recovers_each_pre_marker_boundary(
    migration: Any, tmp_path: Path, crash_point: str
) -> None:
    target = tmp_path / "g9"
    stage = tmp_path / "installing"
    stage.mkdir(mode=0o700)
    receipt = _small_receipt(migration, tmp_path, stage)
    prepared = migration._arm_prepared(root=tmp_path, target=target, stage=stage, receipt=receipt)
    if crash_point != "prepared":
        os.rename(prepared, target)
        if crash_point in {"pending", "linked"}:
            os.rename(target / migration.PREPARED_RECEIPT, target / migration.PENDING_MARKER)
        if crash_point == "linked":
            os.link(target / migration.PENDING_MARKER, target / migration.MIGRATION_MARKER)
    assert migration._finish_publication(
        root=tmp_path,
        target=target,
        receipt_validator=lambda observed: observed == receipt or pytest.fail("receipt changed"),
    )
    assert (target / migration.MIGRATION_MARKER).is_file()
    assert not (target / migration.PENDING_MARKER).exists()
    assert not (target / migration.PREPARED_RECEIPT).exists()
    for relative in migration._store_relative_files():
        assert os.stat(target / relative, follow_symlinks=False).st_nlink == 1


def test_dirty_pending_g9_publication_fails_closed(
    migration: Any, tmp_path: Path
) -> None:
    target = tmp_path / "g9"
    stage = tmp_path / "installing"
    stage.mkdir(mode=0o700)
    receipt = _small_receipt(migration, tmp_path, stage)
    prepared = migration._arm_prepared(
        root=tmp_path, target=target, stage=stage, receipt=receipt
    )
    os.rename(prepared, target)
    os.rename(target / migration.PREPARED_RECEIPT, target / migration.PENDING_MARKER)
    junk = target / "unreviewed-sidecar"
    junk.write_bytes(b"not admitted")
    junk.chmod(0o600)
    with pytest.raises(
        migration.DescendantSourceSuccessorError,
        match="unexpected artifacts",
    ):
        migration._finish_publication(
            root=tmp_path,
            target=target,
            receipt_validator=lambda observed: observed == receipt
            or pytest.fail("receipt changed"),
        )
    assert not (target / migration.MIGRATION_MARKER).exists()


def _capture_files(tmp_path: Path) -> tuple[Path, list[str]]:
    for relative in ("control.duckdb", "status.json", "receipt.json", "archive.json"):
        path = tmp_path / relative
        path.write_text("{}", encoding="utf-8")
        path.chmod(0o600)
    coordination = []
    for lane in range(4):
        path = tmp_path / f"lane-{lane}.duckdb"
        path.write_bytes(b"lane")
        path.chmod(0o600)
        coordination.append(path.name)
    return tmp_path / "control.duckdb", coordination


def _mock_capture_environment(
    migration: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[Path, list[str]]:
    control, coordination = _capture_files(tmp_path)
    identity = {
        "server_id": "server:g8", "store_id": "store:g8", "database_uuid": "db:g8",
        "process_birth_id": "birth:g8", "listen_uri": "quack:127.0.0.1:27278",
        "extension_fingerprint": "sha256:" + "f" * 64, "schema_revision": 1,
        "generation": 8, "started_at": "then", "stopped_at": "now", "status": "stopped",
        "revision": 2,
    }
    @contextmanager
    def fence(**_kwargs: Any):
        yield object()
    import ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server as server
    monkeypatch.setattr(server, "offline_state_server_fence", fence)
    monkeypatch.setattr(migration.g7, "_latest_state_server_from_connection", lambda _c: identity)
    monkeypatch.setattr(migration, "_assert_no_control_attempts", lambda _c: {"task_attempts": 0})
    monkeypatch.setattr(
        migration.g7,
        "_control_projection",
        lambda _p: {
            "tasks": [{"task_alias": alias} for alias in migration.EXPECTED_ALIASES],
            "counts": {"tasks": 54},
            "plan": [["plan:pctdd", "PCTDD-PLAN-V1.1", "active", 1, "{}"]],
        },
    )
    monkeypatch.setattr(
        migration.g7,
        "_coordination_projection",
        lambda _p: {
            "projection_root": "projection:empty",
            "counts": {name: 0 for name in migration.ACTIVE_COORDINATION_COUNTS},
        },
    )
    archive = {
        "schema": migration.ARCHIVE_SCHEMA,
        "source_board_task_ids": ["PCTDD-054", "PCTDD-055", "PCTDD-056"],
        "canonical_active_task_ids": list(migration.EXPECTED_ALIASES),
        "all_resolved": True,
        "g8_runtime_evidence_preserved": True,
        "guardrails": [
            {
                "task_id": alias, "status": "completed", "schedulable": False,
                "markdown_block_sha256": "a", "discovery_sha256": "b",
                "introduction_commit": "c", "resolution_commit": "d",
            }
            for alias in ("PCTDD-054", "PCTDD-055", "PCTDD-056")
        ],
    }
    def load(_path: Path, *, noun: str, **_kwargs: Any) -> dict[str, Any]:
        if "status" in noun:
            return {
                "interface": "QuackStateServer@1", "lifecycle": "stopped",
                "identity": {**identity, "fence_epoch": 8},
            }
        if "generation" in noun:
            return {"target_store_generation": "pctdd-v1-g8"}
        return archive
    monkeypatch.setattr(migration.g7, "_load_json", load)
    return control, coordination


def test_capture_refuses_wal_and_listener(
    migration: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    control, coordination = _mock_capture_environment(migration, monkeypatch, tmp_path)
    wal = control.with_name(control.name + ".wal")
    wal.write_bytes(b"uncheckpointed")
    with pytest.raises(
        migration.DescendantSourceSuccessorError,
        match="(?:WAL|failed closed)",
    ):
        migration.capture_stopped_descendant_authority(
            root=tmp_path, control_path=control.name, generation_receipt_path="receipt.json",
            status_path="status.json", coordination_paths=coordination,
            guardrail_archive_path="archive.json",
        )
    wal.unlink()
    monkeypatch.setattr(
        migration.g7,
        "_assert_listener_stopped",
        lambda _policy: (_ for _ in ()).throw(RuntimeError("listener active")),
    )
    with pytest.raises(migration.DescendantSourceSuccessorError, match="failed closed"):
        migration.capture_stopped_descendant_authority(
            root=tmp_path, control_path=control.name, generation_receipt_path="receipt.json",
            status_path="status.json", coordination_paths=coordination,
            guardrail_archive_path="archive.json",
        )


def test_partial_target_and_import_fail_closed_without_side_effects(
    migration: Any, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    database = _control(migration, tmp_path / "policy")
    policy = _policy(migration, database)
    policy["target_runtime_root"] = "partial-g9"
    (tmp_path / "partial-g9").mkdir(mode=0o700)
    monkeypatch.setattr(migration.g7, "_assert_source_delta", lambda *_args, **_kwargs: None)
    with pytest.raises(migration.DescendantSourceSuccessorError, match="marker"):
        migration.check_descendant_source(
            root=tmp_path,
            config={"descendant_source_successor_materialization": policy},
            population=_population(),
            allow_progressed=False,
        )
    assert callable(migration.migrate_descendant_source)
    assert not (tmp_path / "partial-g9" / migration.MIGRATION_MARKER).exists()
