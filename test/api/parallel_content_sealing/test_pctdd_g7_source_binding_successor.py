"""Focused safety tests for the PCTDD g6 -> g7 source-only successor."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import textwrap
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
G6 = ROOT / "data/agent_supervisor/parallel_content_sealing_proof_carrying_tdd_v1_g6"
MODULE_PATH = ROOT / "scripts/pctdd_g7_source_binding_successor.py"
ACCELERATE_SOURCE = ROOT / "external/ipfs_accelerate"
if ACCELERATE_SOURCE.is_dir() and str(ACCELERATE_SOURCE) not in sys.path:
    sys.path.insert(0, str(ACCELERATE_SOURCE))


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("pctdd_g7_source_binding_successor", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def migration() -> Any:
    return _module()


def _require_g6() -> None:
    if not (G6 / "control.duckdb").is_file():
        pytest.skip("the sealed local PCTDD g6 rehearsal authority is unavailable")


def _record(module: Any, path: Path) -> dict[str, Any]:
    digest, size = module._stable_file(path, root=ROOT, noun=path.as_posix())
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "sha256": digest,
        "size_bytes": size,
    }


def _population() -> dict[str, Any]:
    return {
        "source_head": "synthetic-current-head",
        "repository_tree_id": "synthetic-current-tree",
        "plan_root_cid": "synthetic-current-plan-root",
        "source_forest": {"source_forest_root": "synthetic-source-forest"},
        "source_identities": {"accelerate": "synthetic-current-head"},
    }


def _settlements() -> list[dict[str, Any]]:
    return [
        {
            "task_alias": "PCTDD-001",
            "task_cid": "baguqeera3ce62yl3w5ar5ygfoh76tmjzzojm5qfhvirjjjuqeserigpa2cra",
            "control_revision": 15,
            "claim_id": "claim:e468be9408284fa0a03724ee067a11d9",
            "attempt_id": "attempt:6743f55697cf4fc281712cf77a8f6fec",
            "lease_id": "lease:5516aa2e9ef649f099419ce77eafc7c3",
            "owner_session_id": "embedded-store:aa8373fcda60e36bd6300fc27e6b2a6c",
            "fencing_token": 6,
            "fence_epoch": 6,
        },
        {
            "task_alias": "PCTDD-029",
            "task_cid": "baguqeera2s4tz4myfd7egggeqdj3swxcxfrgws236z7rb7idmmn5jegnbgva",
            "control_revision": 5,
            "claim_id": "claim:b4288022fe5c45b68988018384405bce",
            "attempt_id": "attempt:a365561afbac46f680b27f7e0cf5527e",
            "lease_id": "lease:d827fd4a0c9a4d019483a5e680e14d51",
            "owner_session_id": "embedded-store:44dc846d44d5a59744347de494f628bd",
            "fencing_token": 2,
            "fence_epoch": 2,
        },
    ]


def _policy(module: Any) -> dict[str, Any]:
    _require_g6()
    capture = module.capture_stopped_source_authority(
        root=ROOT,
        control_path=(G6 / "control.duckdb").relative_to(ROOT).as_posix(),
        bootstrap_path=(
            G6 / "evidence/bootstrap/pctdd-bootstrap.json"
        ).relative_to(ROOT).as_posix(),
        status_path=(
            G6 / "quack-owner/quack-state-server.status.json"
        ).relative_to(ROOT).as_posix(),
        coordination_paths=[
            (
                G6 / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
            ).relative_to(ROOT).as_posix()
            for lane in range(4)
        ],
        execution_observation_paths=[
            (
                G6
                / "state"
                / f"lane-{lane}"
                / "quack-lane-control.execution.duckdb"
            ).relative_to(ROOT).as_posix()
            for lane in range(4)
        ],
    )
    settlements = _settlements()
    coordination = [dict(item) for item in capture["coordination_stores"]]
    for lane, record in enumerate(coordination):
        if lane < 2:
            record["settlement"] = settlements[lane]
    return {
        "target_quack_endpoint": "quack:127.0.0.1:27278",
        "prior_control_store": capture["prior_control_store"],
        "prior_bootstrap_receipt": capture["prior_bootstrap_receipt"],
        "prior_stopped_status": capture["prior_stopped_status"],
        "prior_owner_identity": capture["prior_owner_identity"],
        "coordination_stores": coordination,
        "prior_control_projection": capture["prior_control_projection"],
        "accepted_plan_root_cid": (
            "baguqeeraaiqrxovjj4y3ecx6jtvzqfrrrqwuag7hl2c35i2z3eapax2nzaya"
        ),
        "prior_plan_revision": 1,
        "target_control_projection": {
            "statuses": {"completed": 14, "retrying": 3, "todo": 37},
            "task_revisions": {"PCTDD-001": 17, "PCTDD-029": 7},
            "ready_frontier": [
                "PCTDD-001",
                "PCTDD-018",
                "PCTDD-029",
                "PCTDD-031",
                "PCTDD-033",
            ],
        },
        "migration_revision": "PCTDD-SOURCE-G7",
        "prior_store_generation": "pctdd-v1-g6",
        "target_store_generation": "pctdd-v1-g7",
        "copy_policy": {"not_copied": ["execution_observation"]},
        "repository_root": str(ROOT),
    }


def _stage_successor(module: Any, tmp_path: Path) -> tuple[Path, list[Path], dict[str, Any], dict[str, Any]]:
    policy = _policy(module)
    prior = module._assert_prior_anchor(ROOT, policy)
    stage = tmp_path / "stage"
    stage.mkdir()
    control = stage / "control.duckdb"
    module._copy_anchored_file(
        prior["control"],
        control,
        root=ROOT,
        record=policy["prior_control_store"],
        noun="test g6 control",
    )
    coordination_paths: list[Path] = []
    for item in prior["coordination"]:
        lane = int(item["policy"]["lane"])
        target = stage / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
        module._copy_with_optional_wal(
            item["database"],
            item["wal"],
            target,
            root=ROOT,
            record=item["policy"],
            noun=f"test lane {lane} coordination",
        )
        coordination_paths.append(target)
    module._verify_all_execution_observations(
        root=ROOT,
        prior=prior,
        settlements=_settlements(),
        stage_root=stage,
    )
    settled: list[dict[str, Any]] = []
    for item, database in zip(prior["coordination"], coordination_paths, strict=True):
        expected = item["policy"].get("settlement")
        if expected:
            settled.append({**module._expire_stranded_claim(database, expected), **expected})
            module._checkpoint_database(database)
    suffix = module._apply_control_suffix(
        control,
        _population(),
        policy,
        settled,
        prior["control_projection"],
    )
    module._checkpoint_database(control)
    verified = module._verify_staged_successor(
        stage,
        control,
        coordination_paths,
        policy,
        prior["control_projection"],
        suffix,
    )
    return control, coordination_paths, policy, verified


def _source_anchor_records(policy: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        policy["prior_control_store"],
        policy["prior_bootstrap_receipt"],
        policy["prior_stopped_status"],
    ]
    for lane in policy["coordination_stores"]:
        records.append(lane)
        if "wal" in lane:
            records.append(lane["wal"])
        observation = lane["execution_observation"]
        records.append(observation)
        if "wal" in observation:
            records.append(observation["wal"])
    return records


def test_copied_g6_migration_is_six_events_and_preserves_retry_budget(
    migration: Any, tmp_path: Path
) -> None:
    initial_policy = _policy(migration)
    before = {
        record["path"]: (record["sha256"], int(record["size_bytes"]))
        for record in _source_anchor_records(initial_policy)
    }
    control, coordination, policy, verified = _stage_successor(migration, tmp_path)
    projection = verified["control_projection"]
    prior = policy["prior_control_projection"]
    assert projection["event_count"] == prior["event_count"] + 6
    assert projection["event_watermark"] == prior["event_watermark"] + 6
    assert projection["statuses"] == {"completed": 14, "retrying": 3, "todo": 37}
    assert projection["task_definition_digest"] == prior["task_definition_digest"]
    assert set(prior["historical_row_hashes"]["completion_receipts"]) <= set(
        projection["historical_row_hashes"]["completion_receipts"]
    )
    connection = migration._open_local_database(control, read_only=True)
    try:
        for alias, revision in (("PCTDD-001", 17), ("PCTDD-029", 7)):
            row = connection.execute(
                "SELECT revision,body_json FROM tasks WHERE task_alias=?", [alias]
            ).fetchone()
            assert row is not None and int(row[0]) == revision
            receipt = json.loads(str(row[1]))["completion_receipt"]
            assert receipt["schema"] == (
                "ipfs_accelerate_py/agent-supervisor/database-retry-budget@1"
            )
            assert receipt["attempts_used"] == 1
            assert receipt["max_task_attempts"] == 2
            assert receipt["retry_exhausted"] is False
            assert receipt["unknown_outcome_rearm_count"] == 2
            assert receipt["automatic_retry_admitted"] is False
            assert receipt["old_result_reusable"] is False
    finally:
        connection.close()
    ready = migration._ready_task_aliases(
        control, population=_population(), policy=policy
    )
    assert ready == policy["target_control_projection"]["ready_frontier"]
    assert len(coordination) == 4
    after = {
        record["path"]: migration._stable_file(
            ROOT / record["path"],
            root=ROOT,
            noun=f"post-test source {record['path']}",
        )
        for record in _source_anchor_records(policy)
    }
    assert after == before
    receipt = migration._receipt(
        _population(), policy, policy["prior_control_projection"], verified
    )
    connection = migration._open_local_database(control, read_only=False)
    try:
        row = connection.execute(
            "SELECT receipt_cid,body_json FROM completion_receipts ORDER BY receipt_cid LIMIT 1"
        ).fetchone()
        assert row is not None
        connection.execute(
            "UPDATE completion_receipts SET body_json=? WHERE receipt_cid=?",
            [str(row[1]) + " ", str(row[0])],
        )
        connection.execute("CHECKPOINT")
    finally:
        connection.close()
    rows = migration._migration_rows(control, receipt)
    with pytest.raises(migration.SourceBindingMigrationError, match="completion_receipts"):
        migration._assert_historical_manifests(rows, receipt)


def test_lane_local_provider_evidence_blocks_settlement(
    migration: Any, tmp_path: Path
) -> None:
    policy = _policy(migration)
    lane = policy["coordination_stores"][0]
    execution_record = lane["execution_observation"]
    source = ROOT / execution_record["path"]
    target = tmp_path / "lane-0.execution.duckdb"
    wal_record = execution_record.get("wal")
    wal = ROOT / wal_record["path"] if wal_record else None
    migration._copy_with_optional_wal(
        source,
        wal,
        target,
        root=ROOT,
        record=execution_record,
        noun="test lane-local execution observation",
    )
    expected = _settlements()[0]
    connection = migration._open_local_database(target, read_only=False)
    try:
        connection.execute(
            "INSERT INTO provider_invocations VALUES (?,?,?,?,?,?,?)",
            [
                "invocation:test-forged",
                expected["attempt_id"],
                "task:forged-mismatch-must-not-hide-exact-attempt",
                "provider:test-forged",
                "owner:test",
                1,
                "{}",
            ],
        )
        connection.execute("CHECKPOINT")
    finally:
        connection.close()
    with pytest.raises(migration.SourceBindingMigrationError, match="provider_invocations"):
        migration._assert_no_effectful_attempt_evidence(
            [("lane-0-execution", target)], [expected]
        )


def test_prior_owner_extension_fingerprint_is_exact(
    migration: Any,
) -> None:
    policy = _policy(migration)
    policy["prior_owner_identity"] = {
        **policy["prior_owner_identity"],
        "extension_fingerprint": "sha256:" + "0" * 64,
    }
    with pytest.raises(
        migration.SourceBindingMigrationError,
        match="(?:identity|state-server row) differs",
    ):
        migration.inspect_stopped_source_authority(root=ROOT, policy=policy)


def test_predecessor_projection_runs_under_continuous_owner_fence(
    migration: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = _policy(migration)
    real_projection = migration._control_projection
    lock_path = G6 / ".control.duckdb.state-owner.lock"

    def projection_while_fenced(database: Path) -> dict[str, Any]:
        import fcntl

        descriptor = os.open(lock_path, os.O_RDWR | getattr(os, "O_NOFOLLOW", 0))
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(descriptor)
        return real_projection(database)

    monkeypatch.setattr(migration, "_control_projection", projection_while_fenced)
    snapshot = migration.inspect_stopped_source_authority(root=ROOT, policy=policy)
    assert snapshot["control_projection"]["event_count"] == 182


def test_historical_row_encoding_distinguishes_null_and_empty(
    migration: Any,
    tmp_path: Path,
) -> None:
    database = tmp_path / "typed-rows.duckdb"
    connection = migration._open_local_database(database, read_only=False)
    try:
        connection.execute("CREATE TABLE exact_rows(value VARCHAR)")
        connection.execute("INSERT INTO exact_rows VALUES (NULL), ('')")
        manifest = migration._normalized_rows(connection, "exact_rows")
        assert manifest["rows"][0] != manifest["rows"][1]
        assert len(set(manifest["row_hashes"])) == 2
        connection.execute("UPDATE exact_rows SET value='' WHERE value IS NULL")
        changed = migration._normalized_rows(connection, "exact_rows")
    finally:
        connection.close()
    with pytest.raises(
        migration.SourceBindingMigrationError,
        match="exact_rows",
    ):
        migration._assert_historical_manifests(
            {"historical_row_hashes": {"exact_rows": changed["row_hashes"]}},
            {"historical_row_hashes": {"exact_rows": manifest["row_hashes"]}},
        )


def _small_receipt(
    module: Any, root: Path, stage: Path, *, variant: str = ""
) -> dict[str, Any]:
    records = []
    for lane in range(4):
        path = stage / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
        path.parent.mkdir(parents=True, exist_ok=True)
        (stage / "state").chmod(0o700)
        path.parent.chmod(0o700)
        path.write_bytes(f"lane-{lane}-{variant}".encode())
        path.chmod(0o600)
        digest, size = module._stable_file(path, root=root, noun=f"lane {lane}")
        records.append({"lane": lane, "sha256": digest, "size_bytes": size})
    control = stage / "control.duckdb"
    control.write_bytes(f"control-{variant}".encode())
    control.chmod(0o600)
    digest, size = module._stable_file(control, root=root, noun="control")
    body = {
        "schema": module.RECEIPT_SCHEMA,
        "source_binding": _population_source_binding(),
        "control_store": {"sha256": digest, "size_bytes": size},
        "coordination_stores": records,
    }
    return {**body, "receipt_cid": module._identity(body)}


def _arm_small_stage(
    module: Any,
    root: Path,
    stage: Path,
    target: Path,
    *,
    variant: str = "",
) -> tuple[Path, dict[str, Any]]:
    receipt = _small_receipt(module, root, stage, variant=variant)
    prepared = module._arm_prepared_stage(
        root=root,
        target_root=target,
        stage_root=stage,
        receipt=receipt,
    )
    return prepared, receipt


def _population_source_binding() -> dict[str, Any]:
    population = _population()
    return {
        "source_head": population["source_head"],
        "repository_tree_id": population["repository_tree_id"],
        "current_plan_root_cid": population["plan_root_cid"],
        "source_forest_root": population["source_forest"]["source_forest_root"],
        "source_identities": population["source_identities"],
    }


def test_receipt_last_publication_recovers_only_complete_exact_set(
    migration: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    target = tmp_path / "target"
    stage, receipt = _arm_small_stage(migration, tmp_path, stage, target)
    real_link = os.link

    def interrupted(source: Any, destination: Any, **kwargs: Any) -> None:
        if Path(destination).name == migration.MIGRATION_MARKER:
            raise OSError("injected marker-link crash")
        real_link(source, destination, **kwargs)

    monkeypatch.setattr(migration.os, "link", interrupted)
    with pytest.raises(OSError, match="injected"):
        migration._publish_stage(
            tmp_path,
            stage,
            target,
            migration._store_relative_files(),
            receipt,
        )
    assert not (target / migration.MIGRATION_MARKER).exists()
    assert (target / migration.PENDING_MARKER).exists()
    monkeypatch.setattr(migration.os, "link", real_link)
    assert migration._finish_pending_publication(
        root=tmp_path,
        target_root=target,
        population=_population(),
    )
    assert (target / migration.MIGRATION_MARKER).is_file()
    assert not (target / migration.PENDING_MARKER).exists()
    for relative in migration._store_relative_files():
        assert os.stat(target / relative, follow_symlinks=False).st_nlink == 1


def test_atomic_directory_rename_recovers_before_pending_receipt(
    migration: Any, tmp_path: Path
) -> None:
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    target = tmp_path / "target"
    stage, receipt = _arm_small_stage(migration, tmp_path, stage, target)
    os.rename(stage, target)
    assert migration._finish_pending_publication(
        root=tmp_path,
        target_root=target,
        population=_population(),
    )
    assert (target / migration.MIGRATION_MARKER).is_file()
    migration._validate_published_stores(
        root=tmp_path,
        target_root=target,
        receipt=receipt,
    )
    for relative in migration._store_relative_files():
        assert os.stat(target / relative, follow_symlinks=False).st_nlink == 1


def test_atomic_renamed_target_mismatch_remains_fail_closed(
    migration: Any, tmp_path: Path
) -> None:
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    target = tmp_path / "target"
    stage, receipt = _arm_small_stage(migration, tmp_path, stage, target)
    os.rename(stage, target)
    corrupt = target / "control.duckdb"
    corrupt.write_bytes(b"corrupt")
    corrupt.chmod(0o600)
    with pytest.raises(migration.SourceBindingMigrationError, match="store differs"):
        migration._finish_pending_publication(
            root=tmp_path,
            target_root=target,
            population=_population(),
        )


@pytest.mark.parametrize(
    "crash_boundary",
    ("prepared", "directory_renamed", "receipt_renamed", "marker_linked"),
)
def test_atomic_publication_recovers_across_separate_process_restart(
    migration: Any,
    tmp_path: Path,
    crash_boundary: str,
) -> None:
    stage = tmp_path / "stage"
    stage.mkdir(mode=0o700)
    target = tmp_path / "target"
    stage, receipt = _arm_small_stage(
        migration,
        tmp_path,
        stage,
        target,
        variant=crash_boundary,
    )
    child = textwrap.dedent(
        """
        import importlib.util
        import json
        import os
        import sys
        from pathlib import Path

        module_path = Path(sys.argv[1])
        root = Path(sys.argv[2])
        stage = Path(sys.argv[3])
        target = Path(sys.argv[4])
        boundary = sys.argv[5]
        spec = importlib.util.spec_from_file_location("pctdd_child", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if boundary == "prepared":
            os._exit(71)
        receipt = json.loads((stage / module.PREPARED_RECEIPT).read_text())
        real_rename = os.rename
        real_link = os.link

        def sync_directory(path):
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)

        def crashing_rename(source, destination, *args, **kwargs):
            real_rename(source, destination, *args, **kwargs)
            destination = Path(destination)
            if boundary == "directory_renamed" and destination == target:
                sync_directory(target.parent)
                os._exit(72)
            if boundary == "receipt_renamed" and destination.name == module.PENDING_MARKER:
                sync_directory(target)
                os._exit(73)

        def crashing_link(source, destination, *args, **kwargs):
            real_link(source, destination, *args, **kwargs)
            if boundary == "marker_linked" and Path(destination).name == module.MIGRATION_MARKER:
                sync_directory(target)
                os._exit(74)

        module.os.rename = crashing_rename
        module.os.link = crashing_link
        module._publish_stage(
            root,
            stage,
            target,
            module._store_relative_files(),
            receipt,
        )
        raise SystemExit(0)
        """
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ACCELERATE_SOURCE)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            child,
            str(MODULE_PATH),
            str(tmp_path),
            str(stage),
            str(target),
            crash_boundary,
        ],
        cwd=ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode in {71, 72, 73, 74}, result.stderr
    visible_stores = sum(
        int(os.path.lexists(target / relative))
        for relative in migration._store_relative_files()
    )
    assert visible_stores in {0, 5}
    assert migration._finish_pending_publication(
        root=tmp_path,
        target_root=target,
        population=_population(),
    )
    marker = migration._load_json(
        target / migration.MIGRATION_MARKER,
        root=tmp_path,
        noun="restarted atomic publication marker",
    )
    assert marker == receipt
    assert not os.path.lexists(target / migration.PENDING_MARKER)
    assert not os.path.lexists(target / migration.PREPARED_RECEIPT)
    assert not os.path.lexists(migration._prepared_stage_path(target, receipt))
    for relative in migration._store_relative_files():
        assert os.stat(target / relative, follow_symlinks=False).st_nlink == 1


def test_concurrent_publication_has_one_no_overwrite_winner(
    migration: Any, tmp_path: Path
) -> None:
    stage_a = tmp_path / "stage-a"
    stage_b = tmp_path / "stage-b"
    stage_a.mkdir(mode=0o700)
    stage_b.mkdir(mode=0o700)
    target = tmp_path / "target"
    stage_a, receipt_a = _arm_small_stage(
        migration, tmp_path, stage_a, target, variant="a"
    )
    stage_b, receipt_b = _arm_small_stage(
        migration, tmp_path, stage_b, target, variant="b"
    )
    assert receipt_a != receipt_b
    barrier = threading.Barrier(2)

    def publish(item: tuple[Path, dict[str, Any]]) -> str:
        stage, receipt = item
        barrier.wait()
        try:
            migration._publish_stage(
                tmp_path,
                stage,
                target,
                migration._store_relative_files(),
                receipt,
            )
        except (OSError, migration.SourceBindingMigrationError):
            return "refused"
        return "published"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(publish, ((stage_a, receipt_a), (stage_b, receipt_b))))
    assert sorted(outcomes) == ["published", "refused"]
    marker = migration._load_json(
        target / migration.MIGRATION_MARKER,
        root=tmp_path,
        noun="concurrent publication marker",
    )
    assert marker == receipt_a or marker == receipt_b
    marker_receipt = receipt_a if marker == receipt_a else receipt_b
    migration._validate_published_stores(
        root=tmp_path, target_root=target, receipt=marker_receipt
    )


def test_receipt_writer_retries_short_writes(
    migration: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "receipt.json"
    value = {"schema": "test", "payload": "x" * 128}
    real_write = os.write
    calls = 0

    def short_write(descriptor: int, payload: Any) -> int:
        nonlocal calls
        calls += 1
        view = memoryview(payload)
        return real_write(descriptor, view[: max(1, len(view) // 3)])

    monkeypatch.setattr(migration.os, "write", short_write)
    migration._write_new_json(target, value)
    assert calls > 1
    assert json.loads(target.read_text(encoding="utf-8")) == value


def test_migration_lock_pins_private_single_link_inode(
    migration: Any, tmp_path: Path
) -> None:
    lock = tmp_path / "migration.lock"
    descriptor, identity = migration._open_migration_lock(lock)
    try:
        migration._assert_migration_lock_identity(lock, descriptor, identity)
        replacement = tmp_path / "replacement.lock"
        replacement.write_bytes(b"")
        replacement.chmod(0o600)
        os.replace(replacement, lock)
        with pytest.raises(
            migration.SourceBindingMigrationError, match="lock identity changed"
        ):
            migration._assert_migration_lock_identity(lock, descriptor, identity)
    finally:
        os.close(descriptor)

    unsafe_mode = tmp_path / "unsafe-mode.lock"
    unsafe_mode.write_bytes(b"")
    unsafe_mode.chmod(0o640)
    with pytest.raises(
        migration.SourceBindingMigrationError, match="private, regular, and singly linked"
    ):
        migration._open_migration_lock(unsafe_mode)

    linked = tmp_path / "linked.lock"
    linked.write_bytes(b"")
    linked.chmod(0o600)
    os.link(linked, tmp_path / "linked-alias.lock")
    with pytest.raises(
        migration.SourceBindingMigrationError, match="private, regular, and singly linked"
    ):
        migration._open_migration_lock(linked)


def test_source_delta_rechecks_worktree_after_head_and_tree_pin(
    migration: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status_checks = 0

    def changing_git(_root: Path, *arguments: str) -> str:
        nonlocal status_checks
        if arguments == ("rev-parse", "HEAD"):
            return "head"
        if arguments == ("rev-parse", "anchor^{tree}"):
            return "anchor-tree"
        if arguments == ("rev-parse", "head^{tree}"):
            return "tree"
        if arguments[:2] == ("merge-base", "--is-ancestor"):
            return ""
        if arguments[:2] == ("status", "--porcelain=v1"):
            status_checks += 1
            return "" if status_checks == 1 else " M control.json"
        if arguments[:3] == ("diff", "--name-status", "--no-renames"):
            return "M\tcontrol.json"
        raise AssertionError(f"unexpected git arguments: {arguments!r}")

    monkeypatch.setattr(migration, "_git", changing_git)
    with pytest.raises(
        migration.SourceBindingMigrationError,
        match="source worktree changed during validation",
    ):
        migration._assert_source_delta(
            tmp_path,
            {
                "source_head": "head",
                "repository_tree_id": "tree",
            },
            {
                "control_source_anchor_head": "anchor",
                "control_source_anchor_tree": "anchor-tree",
                "operator_control_paths": ["control.json"],
                "governed_gitlinks": {},
            },
        )
    assert status_checks == 2


def test_live_progress_check_never_opens_local_control_or_lanes(
    migration: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "g7").mkdir(mode=0o700)
    receipt_body = {
        "schema": migration.RECEIPT_SCHEMA,
        "source_binding": _population_source_binding(),
        "prior_owner_identity": {
            "database_uuid": "db",
            "generation": 20,
            "fence_epoch": 20,
            "extension_fingerprint": "sha256:extension",
        },
        "historical_row_hashes": {"completion_receipts": ["sha256:old"]},
        "prior_task_definition_digest": "sha256:definitions",
        "migration_event_prefix_digest": "sha256:events",
        "migration_event_watermark": 6,
        "accepted_plan_root_cid": "accepted-plan",
        "suffix": {"migration_digest": "sha256:migration"},
    }
    receipt = {**receipt_body, "receipt_cid": migration._identity(receipt_body)}
    evidence_body = {"source": "migration"}
    migration_digest = migration._identity(evidence_body)
    receipt["suffix"]["migration_digest"] = migration_digest
    receipt_body = {key: value for key, value in receipt.items() if key != "receipt_cid"}
    receipt["receipt_cid"] = migration._identity(receipt_body)
    marker_path = tmp_path / "g7" / migration.MIGRATION_MARKER
    migration._write_new_json(marker_path, receipt)
    live_identity = {
        "server_id": "server:g7",
        "store_id": "g7/control.duckdb",
        "database_uuid": "db",
        "process_birth_id": "birth:g7",
        "listen_uri": "quack:127.0.0.1:27278",
        "extension_fingerprint": "sha256:extension",
        "schema_revision": 1,
        "generation": 21,
        "fence_epoch": 21,
        "started_at": "now",
        "status": "ready",
    }
    policy = {
        "target_runtime_root": "g7",
        "target_quack_endpoint": "quack:127.0.0.1:27278",
        "prior_plan_revision": 1,
        "accepted_plan_root_cid": "accepted-plan",
        "target_control_projection": {"ready_frontier": []},
        "coordination_stores": [{"lane": lane} for lane in range(4)],
    }
    monkeypatch.setattr(migration, "_policy", lambda _config: dict(policy))
    monkeypatch.setattr(migration, "_assert_source_delta", lambda *args: None)
    monkeypatch.setattr(
        migration,
        "_live_g7_owner",
        lambda **kwargs: {"identity": live_identity},
    )
    monkeypatch.setattr(
        migration,
        "_migration_rows",
        lambda target_value, receipt_value: {
            "migration_event_prefix_digest": "sha256:events",
            "evidence": [["e", migration.MIGRATION_EVIDENCE_KIND, migration_digest, json.dumps(evidence_body)]],
            "plan": ["accepted-plan", 2, json.dumps({"current_source_binding": _population_source_binding()})],
            "historical_row_hashes": {"completion_receipts": ["sha256:old"]},
        },
    )
    monkeypatch.setattr(
        migration,
        "_control_projection",
        lambda target_value: {"task_definition_digest": "sha256:definitions"},
    )
    monkeypatch.setattr(
        migration,
        "_latest_state_server",
        lambda target_value: {**live_identity, "stopped_at": None, "revision": 1},
    )
    monkeypatch.setattr(migration, "_ready_task_aliases", lambda *args, **kwargs: [])

    def local_access_forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("live check attempted direct local database access")

    monkeypatch.setattr(migration, "_open_local_database", local_access_forbidden)
    monkeypatch.setattr(migration, "_coordination_projection", local_access_forbidden)
    monkeypatch.setattr(migration, "_stable_file", local_access_forbidden)
    result = migration.check_source_binding(
        root=tmp_path,
        config={},
        population=_population(),
        allow_progressed=True,
    )
    assert result["valid"] is True
    assert result["verification_transport"] == "quack"
    monkeypatch.setattr(
        migration,
        "_latest_state_server",
        lambda target_value: {
            **live_identity,
            "stopped_at": None,
            "revision": 1,
            "extension_fingerprint": "sha256:different-extension",
        },
    )
    with pytest.raises(
        migration.SourceBindingMigrationError,
        match="extension_fingerprint",
    ):
        migration.check_source_binding(
            root=tmp_path,
            config={},
            population=_population(),
            allow_progressed=True,
        )

    monkeypatch.setattr(
        migration,
        "_latest_state_server",
        lambda target_value: {**live_identity, "stopped_at": None, "revision": 1},
    )

    def replace_marker_during_quack_check(*args: Any, **kwargs: Any) -> list[str]:
        replacement = marker_path.with_name("replacement-marker.json")
        migration._write_new_json(replacement, receipt)
        os.replace(replacement, marker_path)
        return []

    monkeypatch.setattr(
        migration, "_ready_task_aliases", replace_marker_during_quack_check
    )
    with pytest.raises(
        migration.SourceBindingMigrationError,
        match="marker changed during verification",
    ):
        migration.check_source_binding(
            root=tmp_path,
            config={},
            population=_population(),
            allow_progressed=True,
        )

    monkeypatch.setattr(migration, "_ready_task_aliases", lambda *args, **kwargs: [])
    source_checks = 0

    def source_changes_during_quack_check(*args: Any, **kwargs: Any) -> None:
        nonlocal source_checks
        source_checks += 1
        if source_checks == 2:
            raise migration.SourceBindingMigrationError(
                "source head or tree changed during validation"
            )

    monkeypatch.setattr(migration, "_assert_source_delta", source_changes_during_quack_check)
    with pytest.raises(
        migration.SourceBindingMigrationError,
        match="source head or tree changed during validation",
    ):
        migration.check_source_binding(
            root=tmp_path,
            config={},
            population=_population(),
            allow_progressed=True,
        )
    assert source_checks == 2


def test_same_descriptor_json_decoder_rejects_symlink(
    migration: Any, tmp_path: Path
) -> None:
    source = tmp_path / "source.json"
    source.write_text('{"value":1}\n', encoding="utf-8")
    link = tmp_path / "link.json"
    link.symlink_to(source.name)
    with pytest.raises(migration.SourceBindingMigrationError, match="absent or unsafe"):
        migration._load_json(link, root=tmp_path, noun="symlink JSON")
