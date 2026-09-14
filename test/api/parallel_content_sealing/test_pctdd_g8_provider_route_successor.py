"""Focused tests for the operator-owned PCTDD g7 -> g8 successor."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
ACCELERATE_SOURCE = ROOT / "external/ipfs_accelerate"
if str(ACCELERATE_SOURCE) not in sys.path:
    sys.path.insert(0, str(ACCELERATE_SOURCE))
MODULE_PATH = ROOT / "scripts/pctdd_g8_provider_route_successor.py"


def _module() -> Any:
    g7_path = ROOT / "scripts/pctdd_g7_source_binding_successor.py"
    g7_spec = importlib.util.spec_from_file_location(
        "pctdd_g7_source_binding_successor", g7_path
    )
    assert g7_spec is not None and g7_spec.loader is not None
    g7_module = importlib.util.module_from_spec(g7_spec)
    g7_spec.loader.exec_module(g7_module)
    sys.modules["pctdd_g7_source_binding_successor"] = g7_module
    spec = importlib.util.spec_from_file_location(
        "pctdd_g8_provider_route_successor", MODULE_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def migration() -> Any:
    return _module()


def _population() -> dict[str, Any]:
    return {
        "source_head": "synthetic-g8-head",
        "repository_tree_id": "synthetic-g8-tree",
        "plan_root_cid": "plan:pctdd-test",
        "source_forest": {"source_forest_root": "synthetic-g8-forest"},
        "source_identities": {"accelerate": "synthetic-g8-head"},
    }


def _control(migration: Any, tmp_path: Path) -> Path:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
        database_retry_validation_spec_cid,
    )

    database = tmp_path / "control.duckdb"
    plan = _population()["plan_root_cid"]
    tasks = [
        ("PCTDD-000", "completed", "operator-only", 1),
        ("PCTDD-001", "todo", "grok-only", 2),
        ("PCTDD-002", "completed", "grok-only", 3),
        ("PCTDD-018", "retrying", "grok-only", 4),
        ("PCTDD-029", "todo", "grok-only", 5),
    ]
    population = {
        "repository_tree_id": "historical-g7-tree",
        "plan_root_cid": plan,
        "goals": [{"goal_cid": "goal:pctdd", "goal_id": "PCTDD-G000"}],
        "plans": [
            {
                "plan_cid": plan,
                "plan_alias": "PCTDD-PLAN-V1",
                "goal_cid": "goal:pctdd",
                "status": "active",
            }
        ],
        "tasks": [
            {
                "task_cid": f"task:{alias.lower()}",
                "task_id": alias,
                "goal_cid": "goal:pctdd",
                "plan_cid": plan,
                "ordinal": ordinal,
                "status": status,
                "provider_role": role,
                "title": alias,
                "validations": [["python", "-m", "pytest", alias]],
            }
            for alias, status, role, ordinal in tasks
        ],
    }
    with DatabaseTaskSource(
        database,
        owner_id="pctdd-g8-test:materialize",
        repository_tree_id="historical-g7-tree",
        plan_root_cid=plan,
    ) as source:
        source.materialize(population)
        for alias, lane in (("PCTDD-001", 0), ("PCTDD-029", 1)):
            task = source.get_task(alias)
            assert task is not None
            source.record_queue_backoff(
                task_cid=task.task_cid,
                delay_ms=86_400_000,
                reason="provider_capacity_backoff",
                selection_penalty=10,
            )
            receipt = {
                "schema": migration.DATABASE_RETRY_BUDGET_SCHEMA,
                "operation": "database_unknown_outcome_blocked",
                "validation_spec_cid": database_retry_validation_spec_cid(
                    task.task_cid, task.validations
                ),
                "attempts_used": 2,
                "max_task_attempts": 2,
                "retry_exhausted": True,
                "unknown_outcome_rearm_count": 2,
                "authority_outcome": "unknown",
                "forced_block": True,
                "reason": "callback_authority_incomplete_blocked",
                "task_cid": task.task_cid,
                "attempt_id": f"attempt:{lane}",
                "claim_id": f"claim:{lane}",
                "lease_id": f"lease:{lane}",
                "owner_session_id": f"owner:{lane}",
                "fencing_token": lane + 1,
                "fence_epoch": lane + 1,
            }
            source.compare_and_set_status(
                task.task_cid, task.revision, "blocked", receipt=receipt
            )
    return database


def _policy(migration: Any, database: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    provider = {
        **migration.EXPECTED_ROUTE,
        "implementation_fallback_authorized": True,
    }
    binding = migration._route_binding(provider)
    with DatabaseTaskSource(
        database,
        owner_id="pctdd-g8-test:policy",
        install_schema=False,
        repository_tree_id="historical-g7-tree",
        plan_root_cid=_population()["plan_root_cid"],
    ) as source:
        tasks = migration._task_projection(source)
    revisions: list[dict[str, Any]] = []
    for alias, task in sorted(tasks.items()):
        if task["status"] in migration.COMPLETED_TASK_STATUSES:
            continue
        target = {**task, "body": migration._role_delta_body(task["body"])}
        revisions.append(
            {
                "task_alias": alias,
                "task_cid": task["task_cid"],
                "prior_status": task["status"],
                "prior_revision": task["revision"],
                "target_revision": task["revision"]
                + (2 if alias in migration.EXPECTED_TASK_ALIASES else 1),
                "prior_definition_cid": migration._definition_cid(task),
                "target_definition_cid": migration._definition_cid(target),
                "prior_provider_role": "grok-only",
                "target_provider_role": "grok-implement",
            }
        )
    settlements: list[dict[str, Any]] = []
    for alias, lane in (("PCTDD-001", 0), ("PCTDD-029", 1)):
        task = tasks[alias]
        prior_receipt = dict(task["body"]["completion_receipt"])
        queue_probe = migration.g7._open_local_database(database, read_only=True)
        try:
            prior_queue_state = migration._queue_state_from_connection(
                queue_probe,
                task_cid=task["task_cid"],
            )
        finally:
            queue_probe.close()
        log_record = {
            "path": f"synthetic/lane-{lane}.log",
            "sha256": "0" * 64,
            "size_bytes": 1,
        }
        evidence = {
            "schema": migration.PRE_EFFECT_SCHEMA,
            "task_alias": alias,
            "task_cid": task["task_cid"],
            "attempt_id": f"attempt:{lane}",
            "claim_id": f"claim:{lane}",
            "provider_id": "grok_cli",
            "model_id": "grok-4.6",
            "failure_class": "hard_quota_exhausted",
            "http_status": 402,
            "supervisor_outcome": "provider_capacity_backoff",
            "provider_effect_committed": False,
            "fallback_dispatched": False,
            "workspace_mutated": False,
            "durable_provider_attempt_state": "reserved",
            "evidence_source": "operator_sealed_grok_quota_log",
            "source_artifact_path": log_record["path"],
            "source_artifact_sha256": log_record["sha256"],
            "source_artifact_size_bytes": log_record["size_bytes"],
        }
        evidence["evidence_cid"] = migration.g7._identity(evidence)
        settlements.append(
            {
                "task_alias": alias,
                "task_cid": task["task_cid"],
                "control_revision": task["revision"],
                "lane": lane,
                "attempt_id": f"attempt:{lane}",
                "claim_id": f"claim:{lane}",
                "lease_id": f"lease:{lane}",
                "owner_session_id": f"owner:{lane}",
                "fencing_token": lane + 1,
                "fence_epoch": lane + 1,
                "prior_task_status": "blocked",
                "target_task_status": "todo",
                "coordination_action": (
                    "expire_exact_active_claim"
                    if lane == 0
                    else "preserve_exact_terminal_claim"
                ),
                "prior_claim_state": "accepted" if lane == 0 else "released",
                "prior_attempt_status": "running" if lane == 0 else "released",
                "target_claim_state": "expired" if lane == 0 else "released",
                "target_attempt_status": "expired" if lane == 0 else "released",
                "coordination_projection_root": f"projection:prior:{lane}",
                "prior_completion_receipt": prior_receipt,
                "prior_completion_receipt_cid": migration.g7._identity(prior_receipt),
                "prior_queue_state": prior_queue_state,
                "prior_queue_state_cid": migration.g7._identity(
                    prior_queue_state
                ),
                "pre_effect_log": log_record,
                "pre_effect_evidence": evidence,
                "retry_budget": {
                    "prior_attempts_used": 2,
                    "target_attempts_used": 0,
                    "max_task_attempts": 2,
                    "prior_unknown_outcome_rearm_count": 2,
                    "target_unknown_outcome_rearm_count": 3,
                },
            }
        )
    policy = {
        "schema": migration.MIGRATION_SCHEMA,
        "migration_revision": "PCTDD-SOURCE-PROVIDER-G8",
        "prior_store_generation": "pctdd-v1-g7",
        "target_store_generation": "pctdd-v1-g8",
        "target_quack_endpoint": "quack:127.0.0.1:27278",
        "receipt_marker": migration.MIGRATION_MARKER,
        "provider_route": provider,
        "provider_route_binding_cid": migration.g7._identity(binding),
        "coordination_stores": [{"lane": lane} for lane in range(4)],
        "settlements": settlements,
        "provider_role_revisions": revisions,
        "accepted_plan_root_cid": _population()["plan_root_cid"],
        "prior_plan_revision": 1,
        "copy_policy": {
            "not_copied": [
                "execution_observation",
                "provider_attempt_store",
                "ducklake",
                "read_replica",
                "logs",
                "owner_runtime",
                "worktrees",
                "merge_state",
            ]
        },
        "target_control_projection": {
            "statuses": {"completed": 2, "retrying": 1, "todo": 2},
            "task_revisions": {
                item["task_alias"]: item["target_revision"] for item in revisions
            },
            "ready_frontier": ["PCTDD-001", "PCTDD-018", "PCTDD-029"],
        },
    }
    return policy, binding


def test_private_coordination_storage_normalization_preserves_authority_and_mutates(
    migration: Any, tmp_path: Path
) -> None:
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (
        DatabaseCoordinator,
    )

    database = tmp_path / "quack-lane-coordination.duckdb"
    with DatabaseCoordinator(database, clock_ms=lambda: 1_000) as coordinator:
        coordinator.register_task(task_cid="task:pctdd", task_id="PCTDD")
        claim = coordinator.claim_task(
            task_cid="task:pctdd",
            owner_session_id="session:pctdd",
            lease_ms=60_000,
        )
    before = migration.g7._coordination_projection(database)

    receipt = migration._normalize_private_coordination_storage(database)

    after = migration.g7._coordination_projection(database)
    assert receipt["schema"] == migration.COORDINATION_STORAGE_NORMALIZATION_SCHEMA
    assert receipt["external_access"] is False
    assert receipt["source_mutated"] is False
    assert receipt["pre_projection_root"] == before["projection_root"]
    assert receipt["post_projection_root"] == before["projection_root"]
    assert after["projection_root"] == before["projection_root"]
    assert receipt["source_sha256"] != receipt["normalized_sha256"]
    assert receipt["row_counts"]["task_claims"] == 1
    assert not database.with_name(
        f".{database.name}.logical-source"
    ).exists()

    with DatabaseCoordinator(
        database, clock_ms=lambda: int(claim.expires_at_ms) + 1
    ) as coordinator:
        expired = coordinator.expire_task_claim(
            claim, now_ms=int(claim.expires_at_ms) + 1
        )
    assert expired.state.value == "expired"
    final = migration.g7._coordination_projection(database)
    final_claim = migration.g7._active_claim_for_history(
        final,
        {
            "claim_id": claim.claim_id,
            "attempt_id": claim.attempt_id,
        },
    )
    assert final_claim["state"] == "expired"


def test_control_suffix_revises_only_incomplete_provider_roles(
    migration: Any, tmp_path: Path
) -> None:
    database = _control(migration, tmp_path)
    policy, binding = _policy(migration, database)
    prior = migration.g7._control_projection(database)
    before = migration.g7._stable_file(database, root=tmp_path, noun="before")
    settled = [
        {**item, "post_projection_root": f"projection:post:{item['lane']}"}
        for item in policy["settlements"]
    ]
    suffix = migration._apply_control_suffix(
        database,
        root=tmp_path,
        population=_population(),
        policy={**policy, "repository_root": str(tmp_path)},
        route_binding=binding,
        coordination_settlements=settled,
        prior_projection=prior,
    )
    migration.g7._checkpoint_database(database)
    post = migration.g7._control_projection(database)
    assert post["event_count"] == prior["event_count"] + 9
    assert len(suffix["status_receipts"]) == 2
    assert suffix["coordination_settlements"] == settled
    assert before != migration.g7._stable_file(database, root=tmp_path, noun="after")
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    with DatabaseTaskSource(database, install_schema=False) as source:
        tasks = migration._task_projection(source)
    assert tasks["PCTDD-000"]["body"]["provider_role"] == "operator-only"
    assert tasks["PCTDD-002"]["body"]["provider_role"] == "grok-only"
    for alias in ("PCTDD-001", "PCTDD-018", "PCTDD-029"):
        assert tasks[alias]["body"]["provider_role"] == "grok-implement"
        expected = next(
            item for item in policy["provider_role_revisions"] if item["task_alias"] == alias
        )
        assert migration._definition_cid(tasks[alias]) == expected["target_definition_cid"]
    for alias in migration.EXPECTED_TASK_ALIASES:
        receipt = tasks[alias]["body"]["completion_receipt"]
        assert receipt["schema"] == migration.DATABASE_RETRY_BUDGET_SCHEMA
        assert receipt["attempts_used"] == 0
        assert receipt["unknown_outcome_rearm_count"] == 3
        assert receipt["provider_route_reset_authorized"] is True
        assert receipt["fallback_dispatched"] is False
    with DatabaseTaskSource(database, install_schema=False) as source:
        for alias in migration.EXPECTED_TASK_ALIASES:
            task = source.get_task(alias)
            assert task is not None
            queue = source.intent.get_queue_entry(task.task_cid)
            assert queue is not None
            assert queue.retry_not_before_ms == 0
            assert queue.selection_penalty == 0


def test_absent_queue_rows_are_sealed_and_preserved_without_retry_events(
    migration: Any, tmp_path: Path
) -> None:
    database = _control(migration, tmp_path)
    connection = migration.g7._open_local_database(database, read_only=False)
    try:
        connection.execute(
            "DELETE FROM leases WHERE task_cid IN "
            "(SELECT task_cid FROM tasks WHERE task_alias IN (?,?))",
            list(migration.EXPECTED_TASK_ALIASES),
        )
        connection.execute("CHECKPOINT")
    finally:
        connection.close()
    policy, binding = _policy(migration, database)
    assert {
        item["prior_queue_state"]["disposition"]
        for item in policy["settlements"]
    } == {"absent"}
    migration._policy({"source_provider_route_successor_materialization": policy})
    prior = migration.g7._control_projection(database)
    settled = [
        {**item, "post_projection_root": f"projection:post:{item['lane']}"}
        for item in policy["settlements"]
    ]
    suffix = migration._apply_control_suffix(
        database,
        root=tmp_path,
        population=_population(),
        policy={**policy, "repository_root": str(tmp_path)},
        route_binding=binding,
        coordination_settlements=settled,
        prior_projection=prior,
    )
    post = migration.g7._control_projection(database)
    assert post["event_count"] == prior["event_count"] + 7
    assert all(
        item["queue_retry_event_id"] is None
        and item["queue_disposition"] == "absent"
        for item in suffix["status_receipts"]
    )
    connection = migration.g7._open_local_database(database, read_only=True)
    try:
        assert connection.execute("SELECT COUNT(*) FROM leases").fetchone()[0] == 0
    finally:
        connection.close()


def test_queue_policy_rejects_a_cleared_or_fabricated_predecessor(
    migration: Any, tmp_path: Path
) -> None:
    database = _control(migration, tmp_path)
    policy, _binding = _policy(migration, database)
    settlement = policy["settlements"][0]
    state = settlement["prior_queue_state"]
    state["entry"]["retry_not_before_ms"] = 0
    settlement["prior_queue_state_cid"] = migration.g7._identity(state)
    with pytest.raises(migration.ProviderRouteSuccessorError):
        migration._policy(
            {"source_provider_route_successor_materialization": policy}
        )


def test_policy_rejects_a_self_authorizing_or_effectful_quota_claim(
    migration: Any, tmp_path: Path
) -> None:
    database = _control(migration, tmp_path)
    policy, _binding = _policy(migration, database)
    config = {"source_provider_route_successor_materialization": policy}
    migration._policy(config)
    policy["settlements"][0]["pre_effect_evidence"][
        "fallback_dispatched"
    ] = True
    evidence = dict(policy["settlements"][0]["pre_effect_evidence"])
    evidence.pop("evidence_cid")
    policy["settlements"][0]["pre_effect_evidence"][
        "evidence_cid"
    ] = migration.g7._identity(evidence)
    with pytest.raises(migration.ProviderRouteSuccessorError):
        migration._policy(config)


def test_policy_rejects_an_arbitrary_blocked_task_receipt(
    migration: Any, tmp_path: Path
) -> None:
    database = _control(migration, tmp_path)
    policy, _binding = _policy(migration, database)
    settlement = policy["settlements"][0]
    settlement["prior_completion_receipt"]["forced_block"] = False
    settlement["prior_completion_receipt_cid"] = migration.g7._identity(
        settlement["prior_completion_receipt"]
    )
    with pytest.raises(migration.ProviderRouteSuccessorError):
        migration._policy(
            {"source_provider_route_successor_materialization": policy}
        )


def test_quota_log_is_exact_content_evidence(migration: Any, tmp_path: Path) -> None:
    database = _control(migration, tmp_path / "control")
    policy, _binding = _policy(migration, database)
    settlement = policy["settlements"][0]
    log = tmp_path / "quota.log"
    log.write_bytes(b"grok command failed: HTTP 402 usage balance exhausted\n")
    log.chmod(0o600)
    digest, size = migration.g7._stable_file(log, root=tmp_path, noun="quota")
    record = {"path": "quota.log", "sha256": digest, "size_bytes": size}
    settlement["pre_effect_log"] = record
    evidence = settlement["pre_effect_evidence"]
    evidence.update(
        {
            "source_artifact_path": record["path"],
            "source_artifact_sha256": record["sha256"],
            "source_artifact_size_bytes": record["size_bytes"],
        }
    )
    unhashed = dict(evidence)
    unhashed.pop("evidence_cid")
    evidence["evidence_cid"] = migration.g7._identity(unhashed)
    assert migration._assert_quota_log(root=tmp_path, settlement=settlement) == record
    log.write_bytes(b"grok command succeeded\n")
    with pytest.raises(migration.ProviderRouteSuccessorError):
        migration._assert_quota_log(root=tmp_path, settlement=settlement)


def _small_receipt(
    migration: Any,
    root: Path,
    stage: Path,
    policy: dict[str, Any],
    binding: dict[str, Any],
) -> dict[str, Any]:
    control = stage / "control.duckdb"
    control.write_bytes(b"control")
    control.chmod(0o600)
    coordination: list[dict[str, Any]] = []
    for lane in range(4):
        path = stage / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
        path.parent.mkdir(parents=True, mode=0o700)
        path.write_bytes(f"lane-{lane}".encode())
        path.chmod(0o600)
        digest, size = migration.g7._stable_file(path, root=root, noun="lane")
        coordination.append({"lane": lane, "sha256": digest, "size_bytes": size})
    digest, size = migration.g7._stable_file(control, root=root, noun="control")
    body = {
        "schema": migration.RECEIPT_SCHEMA,
        "target_store_generation": "pctdd-v1-g8",
        "source_binding": migration.g7._source_binding(root, _population()),
        "provider_route_binding": binding,
        "provider_route_binding_cid": policy["provider_route_binding_cid"],
        "control_store": {"sha256": digest, "size_bytes": size},
        "coordination_stores": coordination,
    }
    return {**body, "receipt_cid": migration.g7._identity(body)}


@pytest.mark.parametrize("crash_point", ["prepared", "renamed", "pending", "linked"])
def test_atomic_marker_last_publication_recovers_every_boundary(
    migration: Any, tmp_path: Path, crash_point: str
) -> None:
    root = tmp_path
    target = root / "g8"
    stage = root / "installing"
    stage.mkdir(mode=0o700)
    (stage / "state").mkdir(mode=0o700)
    database = _control(migration, tmp_path / "policy")
    policy, binding = _policy(migration, database)
    receipt = _small_receipt(migration, root, stage, policy, binding)
    prepared = migration._arm_prepared(
        root=root, target_root=target, stage_root=stage, receipt=receipt
    )
    if crash_point != "prepared":
        os.rename(prepared, target)
        if crash_point in {"pending", "linked"}:
            os.rename(
                target / migration.PREPARED_RECEIPT,
                target / migration.PENDING_MARKER,
            )
        if crash_point == "linked":
            os.link(
                target / migration.PENDING_MARKER,
                target / migration.MIGRATION_MARKER,
            )
    assert migration._finish_target_publication(
        root=root,
        target_root=target,
        population=_population(),
        policy=policy,
        route_binding=binding,
    )
    assert (target / migration.MIGRATION_MARKER).is_file()
    assert not (target / migration.PENDING_MARKER).exists()
    assert not (target / migration.PREPARED_RECEIPT).exists()
    for relative in migration._store_relative_files():
        assert os.stat(target / relative, follow_symlinks=False).st_nlink == 1


def test_cli_exports_are_explicit_and_import_has_no_migration_effect(
    migration: Any, tmp_path: Path
) -> None:
    assert callable(migration.migrate_source_provider_route)
    assert callable(migration.check_source_provider_route)
    assert not tuple(tmp_path.iterdir())
