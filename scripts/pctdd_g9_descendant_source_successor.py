#!/usr/bin/env python3
"""Crash-safe PCTDD g8 -> g9 descendant-source successor.

The adapter copies the exact stopped g8 DuckDB/Quack task authority and its
four coordination histories into a fresh private g9 stage.  It preserves the
54 canonical task rows, their statuses, revisions, definitions, completions,
and the complete predecessor event prefix.  The only logical suffix is one
operator plan revision and one operator evidence node binding the reviewed
descendant source, current governed gitlinks, the resolved generated-guardrail
archive, and the state-only guardrail policy.

No live database is opened.  Capture and migration require the canonical
offline Quack owner fence, a stopped owner receipt, no active coordination
claim/attempt/lease, no control-plane running attempt, no WAL, and an absent
listener.  The predecessor is never mutated.  Publication is a private staged
directory rename with the generation receipt linked last.
"""

from __future__ import annotations

import argparse
import fcntl
import importlib
import importlib.util
import json
import os
import shutil
import stat
import tempfile
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

try:
    g7 = importlib.import_module("pctdd_g7_source_binding_successor")
except ModuleNotFoundError:
    g7 = importlib.import_module("scripts.pctdd_g7_source_binding_successor")


MIGRATION_SCHEMA: Final[str] = "pctdd/descendant-source-successor-materialization@1"
EVIDENCE_SCHEMA: Final[str] = "pctdd/operator-descendant-source-migration@1"
RECEIPT_SCHEMA: Final[str] = "pctdd/descendant-source-migration-receipt@1"
CHECK_SCHEMA: Final[str] = "pctdd/descendant-source-migration-check@1"
CAPTURE_SCHEMA: Final[str] = "pctdd/stopped-g8-descendant-source-capture@1"
ARCHIVE_SCHEMA: Final[str] = "pctdd/resolved-generated-guardrail-archive@1"
MIGRATION_EVIDENCE_KIND: Final[str] = "operator_descendant_source_migration"
MIGRATION_MARKER: Final[str] = "descendant-source-migration-receipt.json"
PENDING_MARKER: Final[str] = ".descendant-source-migration-receipt.pending.json"
PREPARED_RECEIPT: Final[str] = ".descendant-source-migration-prepared-receipt.json"
PREPARED_STAGE_PREFIX: Final[str] = ".pctdd-g9-prepared."
LOCK_NAME: Final[str] = ".pctdd-g9-descendant-source-migration.lock"
EXPECTED_ALIASES: Final[tuple[str, ...]] = tuple(
    f"PCTDD-{index:03d}" for index in range(54)
)
ACTIVE_COORDINATION_COUNTS: Final[tuple[str, ...]] = (
    "active_task_claims",
    "active_task_attempts",
    "active_fenced_leases",
    "active_resource_claims",
    "active_maintenance_leases",
)
GUARDRAIL_FLAGS: Final[tuple[str, ...]] = (
    "retry_budget_guardrail_enabled",
    "dependency_guardrail_enabled",
    "reconciliation_guardrail_enabled",
)


class DescendantSourceSuccessorError(RuntimeError):
    """The g9 descendant-source successor cannot be proven safe."""


def _fail(message: str, exc: BaseException | None = None) -> None:
    error = DescendantSourceSuccessorError(message)
    if exc is None:
        raise error
    raise error from exc


def _task_aliases(projection: Mapping[str, Any]) -> tuple[str, ...]:
    tasks = projection.get("tasks")
    if not isinstance(tasks, list):
        _fail("g8 control projection lacks tasks")
    return tuple(str(item.get("task_alias") or "") for item in tasks if isinstance(item, Mapping))


def _archive_record(root: Path, record: Mapping[str, Any]) -> dict[str, Any]:
    path = g7._file_anchor(root, record, noun="resolved guardrail archive")
    value = g7._load_json(path, root=root, noun="resolved guardrail archive")
    if (
        value.get("schema") != ARCHIVE_SCHEMA
        or value.get("source_board_task_ids") != ["PCTDD-054", "PCTDD-055", "PCTDD-056"]
        or value.get("canonical_active_task_ids") != list(EXPECTED_ALIASES)
        or value.get("all_resolved") is not True
        or value.get("g8_runtime_evidence_preserved") is not True
    ):
        _fail("resolved generated-guardrail archive claim differs")
    records = value.get("guardrails")
    if not isinstance(records, list) or len(records) != 3:
        _fail("resolved generated-guardrail archive population differs")
    for expected, item in zip(("PCTDD-054", "PCTDD-055", "PCTDD-056"), records, strict=True):
        if (
            not isinstance(item, Mapping)
            or item.get("task_id") != expected
            or item.get("status") != "completed"
            or item.get("schedulable") is not False
            or not str(item.get("markdown_block_sha256") or "")
            or not str(item.get("discovery_sha256") or "")
            or not str(item.get("introduction_commit") or "")
            or not str(item.get("resolution_commit") or "")
        ):
            _fail(f"resolved generated-guardrail archive entry differs: {expected}")
    return value


def _policy(
    config: Mapping[str, Any], *, allow_pending_capture: bool = False
) -> dict[str, Any]:
    raw = config.get("descendant_source_successor_materialization")
    if not isinstance(raw, Mapping):
        _fail("scheduler lacks a g9 descendant-source successor policy")
    policy = dict(raw)
    if (
        policy.get("schema") != MIGRATION_SCHEMA
        or policy.get("migration_revision") != "PCTDD-DESCENDANT-SOURCE-G9"
        or policy.get("prior_store_generation") != "pctdd-v1-g8"
        or policy.get("target_store_generation") != "pctdd-v1-g9"
        or policy.get("target_quack_endpoint") != "quack:127.0.0.1:27278"
        or policy.get("receipt_marker") != MIGRATION_MARKER
    ):
        _fail("g9 descendant-source policy identity differs")
    guardrails = policy.get("generated_guardrail_policy")
    if (
        not isinstance(guardrails, Mapping)
        or guardrails.get("markdown_is_bootstrap_only") is not True
        or guardrails.get("discovery_and_event_evidence_preserved") is not True
        or guardrails.get("generated_task_projection") != "disabled_for_sealed_board"
        or any(guardrails.get(flag) is not False for flag in GUARDRAIL_FLAGS)
    ):
        _fail("g9 generated-board guardrail policy is not state-only and fail-closed")
    if policy.get("expected_task_aliases") != list(EXPECTED_ALIASES):
        _fail("g9 policy does not bind the canonical 54-task population")
    governed = policy.get("governed_gitlinks")
    if not isinstance(governed, Mapping) or set(governed) != {
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "external/ipfs_kit",
    } or any(len(str(value)) != 40 for value in governed.values()):
        _fail("g9 governed gitlink binding differs")
    paths = policy.get("operator_control_paths")
    if not isinstance(paths, list) or not paths or len(paths) != len(set(map(str, paths))):
        _fail("g9 operator control path allowlist differs")
    copy_policy = policy.get("copy_policy")
    if (
        not isinstance(copy_policy, Mapping)
        or copy_policy.get("g8_remains_read_only_history") is not True
        or copy_policy.get("publication")
        != "private_stage_hash_verify_no_overwrite_marker_last"
        or copy_policy.get("copied")
        != ["authoritative_control_store", "coordination_history"]
    ):
        _fail("g9 copy policy differs")
    status = policy.get("capture_status")
    if status == "pending_stopped_g8_capture" and allow_pending_capture:
        if policy.get("stopped_predecessor_capture") is not None:
            _fail("pending g9 policy contains fabricated predecessor capture")
        return policy
    if status != "sealed_stopped_g8_capture":
        _fail("g9 stopped predecessor capture is not sealed")
    capture = policy.get("stopped_predecessor_capture")
    if not isinstance(capture, Mapping) or capture.get("schema") != CAPTURE_SCHEMA:
        _fail("g9 stopped predecessor capture differs")
    required = {
        "prior_control_store",
        "prior_generation_receipt",
        "prior_stopped_owner_status",
        "prior_owner_identity",
        "prior_control_projection",
        "coordination_stores",
        "guardrail_archive",
        "accepted_plan_root_cid",
        "prior_plan_revision",
    }
    if not required.issubset(capture):
        _fail("g9 stopped predecessor capture is incomplete")
    if _task_aliases(capture["prior_control_projection"]) != EXPECTED_ALIASES:
        _fail("captured g8 task population is not canonical")
    stores = capture.get("coordination_stores")
    if (
        not isinstance(stores, list)
        or [item.get("lane") for item in stores if isinstance(item, Mapping)]
        != [0, 1, 2, 3]
    ):
        _fail("g9 capture must bind four ordered coordination stores")
    for item in stores:
        counts = item.get("counts") if isinstance(item, Mapping) else None
        if not isinstance(counts, Mapping) or any(int(counts.get(name, -1)) != 0 for name in ACTIVE_COORDINATION_COUNTS):
            _fail("g9 capture contains an active coordination authority")
    return policy


def validate_pending_policy(config: Mapping[str, Any]) -> dict[str, Any]:
    """Validate a tracked pre-capture package without admitting migration."""

    policy = _policy(config, allow_pending_capture=True)
    return {
        "schema": CHECK_SCHEMA,
        "valid": True,
        "migration_admitted": policy["capture_status"] == "sealed_stopped_g8_capture",
        "capture_status": policy["capture_status"],
    }


def _record(root: Path, relative: str, *, noun: str) -> dict[str, Any]:
    path = g7._confined(root, relative, noun=noun)
    digest, size = g7._stable_file(path, root=root, noun=noun, required_links=1)
    return {"path": relative, "sha256": digest, "size_bytes": size}


def _assert_no_control_attempts(connection: Any) -> dict[str, int]:
    tables = {
        str(row[0])
        for row in connection.execute("SHOW TABLES").fetchall()
    }
    result: dict[str, int] = {}
    for table, column, active in (
        ("task_attempts", "status", ("running",)),
        ("provider_invocations", "status", ("reserved", "running", "dispatched")),
        ("effect_claims", "status", ("reserved", "accepted", "running")),
        ("merge_attempts", "status", ("running", "reserved")),
    ):
        if table not in tables:
            result[table] = 0
            continue
        columns = {str(row[0]) for row in connection.execute(f"DESCRIBE {table}").fetchall()}
        if column not in columns:
            result[table] = 0
            continue
        placeholders = ",".join("?" for _ in active)
        result[table] = int(
            connection.execute(
                f"SELECT COUNT(*) FROM {table} WHERE lower({column}) IN ({placeholders})",
                list(active),
            ).fetchone()[0]
        )
    if any(result.values()):
        _fail("stopped g8 control retains active attempts or effects")
    return result


def capture_stopped_descendant_authority(
    *,
    root: Path,
    control_path: str,
    generation_receipt_path: str,
    status_path: str,
    coordination_paths: Sequence[str],
    guardrail_archive_path: str,
) -> dict[str, Any]:
    """Capture exact stopped g8 anchors under the canonical offline fence."""

    if len(coordination_paths) != 4:
        _fail("g9 capture requires exactly four coordination stores")
    root = root.resolve()
    control = g7._confined(root, control_path, noun="g8 control store")
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        offline_state_server_fence,
    )

    try:
        with offline_state_server_fence(
            database_path=control,
            connection_factory=lambda path: g7._open_local_database(path, read_only=True),
        ) as connection:
            latest = g7._latest_state_server_from_connection(connection)
            status_record = _record(root, status_path, noun="stopped g8 owner status")
            status = g7._load_json(
                g7._confined(root, status_path, noun="stopped g8 owner status"),
                root=root,
                noun="stopped g8 owner status",
            )
            identity = status.get("identity")
            if (
                status.get("interface") != "QuackStateServer@1"
                or status.get("lifecycle") != "stopped"
                or not isinstance(identity, Mapping)
                or identity.get("status") != "stopped"
                or latest.get("status") != "stopped"
                or not str(latest.get("stopped_at") or "")
            ):
                _fail("captured g8 owner is not exactly stopped")
            for field in (
                "server_id", "store_id", "database_uuid", "process_birth_id",
                "listen_uri", "extension_fingerprint", "schema_revision",
                "generation", "started_at", "status",
            ):
                expected = identity.get(field)
                if field in {"schema_revision", "generation"}:
                    expected = int(expected)
                if latest.get(field) != expected:
                    _fail(f"captured g8 owner identity differs: {field}")
            g7._assert_listener_stopped({"target_quack_endpoint": latest["listen_uri"]})
            owner_dir = g7._confined(root, status_path, noun="g8 owner status").parent
            forbidden = (
                control.with_name(f".{control.name}.state-owner.json"),
                owner_dir / "quack-state-server.pid",
                owner_dir / "quack-state-server.owner.json",
                owner_dir / "quack-state-server.stop",
            )
            if any(os.path.lexists(path) for path in forbidden) or tuple(owner_dir.glob("*.quack-token")):
                _fail("captured g8 owner retains live authority artifacts")
            if os.path.lexists(control.with_name(control.name + ".wal")):
                _fail("stopped g8 control has an uncheckpointed WAL")
            projection = g7._control_projection(control)
            if _task_aliases(projection) != EXPECTED_ALIASES or projection["counts"]["tasks"] != 54:
                _fail("captured g8 control is not the canonical 54-task authority")
            active_control = _assert_no_control_attempts(connection)
            generation_record = _record(root, generation_receipt_path, noun="g8 generation receipt")
            generation = g7._load_json(
                g7._confined(root, generation_receipt_path, noun="g8 generation receipt"),
                root=root,
                noun="g8 generation receipt",
            )
            if generation.get("target_store_generation") != "pctdd-v1-g8":
                _fail("captured generation receipt is not g8")
            coordination: list[dict[str, Any]] = []
            for lane, relative in enumerate(coordination_paths):
                database = g7._confined(root, relative, noun=f"g8 lane {lane} coordination")
                if os.path.lexists(database.with_name(database.name + ".wal")):
                    _fail(f"g8 lane {lane} retains an uncheckpointed WAL")
                record = _record(root, relative, noun=f"g8 lane {lane} coordination")
                lane_projection = g7._coordination_projection(database)
                counts = dict(lane_projection.get("counts") or {})
                if any(int(counts.get(name, -1)) != 0 for name in ACTIVE_COORDINATION_COUNTS):
                    _fail(f"g8 lane {lane} retains active coordination authority")
                coordination.append(
                    {
                        "lane": lane,
                        **record,
                        "projection_root": lane_projection["projection_root"],
                        "counts": {name: int(counts[name]) for name in ACTIVE_COORDINATION_COUNTS},
                    }
                )
            archive_record = _record(root, guardrail_archive_path, noun="resolved guardrail archive")
            _archive_record(root, archive_record)
            plan_rows = projection.get("plan") or []
            if len(plan_rows) != 1:
                _fail("g8 accepted plan population differs")
            plan = plan_rows[0]
            capture = {
                "schema": CAPTURE_SCHEMA,
                "prior_control_store": _record(root, control_path, noun="stopped g8 control store"),
                "prior_generation_receipt": generation_record,
                "prior_stopped_owner_status": status_record,
                "prior_owner_identity": {**latest, "fence_epoch": int(identity["fence_epoch"])},
                "prior_control_projection": projection,
                "control_quiescence": active_control,
                "coordination_stores": coordination,
                "guardrail_archive": archive_record,
                "accepted_plan_root_cid": str(plan[0]),
                "prior_plan_revision": int(plan[3]),
            }
            return capture
    except DescendantSourceSuccessorError:
        raise
    except Exception as exc:
        _fail("stopped g8 descendant-source capture failed closed", exc)


def _inspect_predecessor(
    root: Path, policy: Mapping[str, Any], *, connection: Any
) -> dict[str, Any]:
    capture = dict(policy["stopped_predecessor_capture"])
    control_record = dict(capture["prior_control_store"])
    control = g7._file_anchor(root, control_record, noun="stopped g8 control store")
    if os.path.lexists(control.with_name(control.name + ".wal")):
        _fail("stopped g8 control developed a WAL")
    projection = g7._control_projection(control)
    if projection != capture["prior_control_projection"]:
        _fail("stopped g8 control projection differs from capture")
    _assert_no_control_attempts(connection)
    g7._file_anchor(root, capture["prior_generation_receipt"], noun="g8 generation receipt")
    g7._file_anchor(root, capture["prior_stopped_owner_status"], noun="g8 stopped status")
    _archive_record(root, capture["guardrail_archive"])
    coordination: list[dict[str, Any]] = []
    for item_value in capture["coordination_stores"]:
        item = dict(item_value)
        lane = int(item["lane"])
        path = g7._file_anchor(root, item, noun=f"g8 lane {lane} coordination")
        if os.path.lexists(path.with_name(path.name + ".wal")):
            _fail(f"g8 lane {lane} developed a WAL")
        lane_projection = g7._coordination_projection(path)
        if lane_projection["projection_root"] != item["projection_root"]:
            _fail(f"g8 lane {lane} projection differs")
        counts = lane_projection.get("counts") or {}
        if any(int(counts.get(name, -1)) != 0 for name in ACTIVE_COORDINATION_COUNTS):
            _fail(f"g8 lane {lane} is no longer quiescent")
        coordination.append({"policy": item, "database": path})
    g7._assert_listener_stopped(policy)
    return {"control": control, "projection": projection, "coordination": coordination}


def _event_prefix(database: Path, count: int) -> str:
    connection = g7._open_local_database(database, read_only=True)
    try:
        rows = connection.execute(
            "SELECT event_id,stream_id,sequence,global_sequence,event_type,task_cid,"
            "attempt_id,session_id,recorded_at,body_json FROM domain_events "
            "ORDER BY global_sequence LIMIT ?", [int(count)]
        ).fetchall()
    finally:
        connection.close()
    return g7._identity([g7._canonical_row(row) for row in rows])


def _migration_body(
    *, root: Path, population: Mapping[str, Any], policy: Mapping[str, Any], prior: Mapping[str, Any]
) -> dict[str, Any]:
    capture = policy["stopped_predecessor_capture"]
    return {
        "schema": EVIDENCE_SCHEMA,
        "migration_revision": policy["migration_revision"],
        "migration_kind": "exact_descendant_source_successor",
        "prior_store_generation": policy["prior_store_generation"],
        "target_store_generation": policy["target_store_generation"],
        "source_binding": g7._source_binding(root, population),
        "governed_gitlinks": dict(policy["governed_gitlinks"]),
        "prior_event_watermark": prior["event_watermark"],
        "prior_event_prefix_digest": prior["event_prefix_digest"],
        "prior_task_definition_digest": prior["task_definition_digest"],
        "prior_accepted_tables_digest": prior["accepted_tables_digest"],
        "guardrail_archive": dict(capture["guardrail_archive"]),
        "generated_guardrail_policy": dict(policy["generated_guardrail_policy"]),
        "copy_policy": dict(policy["copy_policy"]),
        "claim_boundaries": {
            "task_status_changes": 0,
            "task_revision_changes": 0,
            "task_definition_changes": 0,
            "accepted_completion_changes": 0,
            "goal_changes": 0,
            "provider_invocation_changes": 0,
            "effect_claim_changes": 0,
            "merge_attempt_changes": 0,
            "generated_guardrail_task_rows": 0,
            "worker_self_approval": False,
        },
    }


def _apply_control_suffix(
    database: Path,
    *,
    root: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    prior_projection: Mapping[str, Any],
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    accepted = str(policy["stopped_predecessor_capture"]["accepted_plan_root_cid"])
    prior_revision = int(policy["stopped_predecessor_capture"]["prior_plan_revision"])
    with DatabaseTaskSource(
        database,
        owner_id="pctdd-descendant-source-g9:private-stage",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=accepted,
    ) as source:
        operator = source.get_task("PCTDD-000")
        if operator is None or operator.status != "completed":
            _fail("PCTDD-000 historical completion differs")
        plan = source.get_plan(accepted)
        if plan is None or int(plan["revision"]) != prior_revision:
            _fail("accepted g8 plan revision differs")
        source_binding = g7._source_binding(root, population)
        plan_receipt = source.plans.append_revision(
            plan_cid=accepted,
            expected_revision=prior_revision,
            body={
                "current_source_binding": source_binding,
                "descendant_source_migration_revision": policy["migration_revision"],
                "resolved_guardrail_archive": dict(policy["stopped_predecessor_capture"]["guardrail_archive"]),
                "generated_guardrail_policy": dict(policy["generated_guardrail_policy"]),
                "accepted_plan_root_preserved": True,
                "task_definition_changes": 0,
                "task_status_changes": 0,
                "accepted_completion_changes": 0,
            },
            delta={
                "kind": "exact_descendant_source_successor",
                "current_source_head": source_binding["source_head"],
                "current_repository_tree_id": source_binding["repository_tree_id"],
                "guardrail_task_projection": "disabled_for_sealed_board",
            },
        )
        body = _migration_body(
            root=root,
            population=population,
            policy=policy,
            prior=prior_projection,
        )
        digest = g7._control_plane_content_identity(body)
        evidence = source.record_evidence(
            task_cid=operator.task_cid,
            evidence_kind=MIGRATION_EVIDENCE_KIND,
            digest=digest,
            body=body,
        )
    return {
        "plan_event_id": plan_receipt.event_id,
        "migration_evidence_event_id": evidence.event_id,
        "migration_digest": digest,
    }


def _verify_staged_successor(
    database: Path,
    *,
    prior: Mapping[str, Any],
    policy: Mapping[str, Any],
    suffix: Mapping[str, Any],
) -> dict[str, Any]:
    post = g7._control_projection(database)
    if post["tasks"] != prior["tasks"] or post["statuses"] != prior["statuses"]:
        _fail("g9 changed task status, revision, CID, or population")
    if post["task_definition_digest"] != prior["task_definition_digest"]:
        _fail("g9 changed a task definition")
    for table in ("goals", "goal_edges", "completion_receipts", "validation_results"):
        if post["historical_row_hashes"][table] != prior["historical_row_hashes"][table]:
            _fail(f"g9 changed historical {table}")
    for count in (
        "goals", "tasks", "task_dependencies", "completion_receipts",
        "validation_results", "provider_invocations", "effect_claims", "merge_attempts",
    ):
        if post["counts"][count] != prior["counts"][count]:
            _fail(f"g9 changed historical {count} count")
    if (
        post["counts"]["plan_revisions"] != prior["counts"]["plan_revisions"] + 1
        or post["counts"]["evidence_nodes"] != prior["counts"]["evidence_nodes"] + 1
        or post["event_count"] != prior["event_count"] + 2
        or _event_prefix(database, int(prior["event_count"])) != prior["event_prefix_digest"]
        or _task_aliases(post) != EXPECTED_ALIASES
    ):
        _fail("g9 logical suffix or event prefix differs")
    connection = g7._open_local_database(database, read_only=True)
    try:
        evidence = connection.execute(
            "SELECT digest,body_json FROM evidence_nodes WHERE evidence_kind=?",
            [MIGRATION_EVIDENCE_KIND],
        ).fetchall()
        plan = connection.execute(
            "SELECT revision,body_json FROM plans WHERE plan_cid=?",
            [policy["stopped_predecessor_capture"]["accepted_plan_root_cid"]],
        ).fetchone()
    finally:
        connection.close()
    if (
        len(evidence) != 1
        or str(evidence[0][0]) != suffix["migration_digest"]
        or g7._control_plane_content_identity(json.loads(str(evidence[0][1])))
        != suffix["migration_digest"]
        or int(plan[0]) != int(policy["stopped_predecessor_capture"]["prior_plan_revision"]) + 1
    ):
        _fail("g9 operator suffix rows differ")
    return post


def _store_relative_files() -> tuple[Path, ...]:
    return (
        Path("control.duckdb"),
        *(Path("state") / f"lane-{lane}" / "quack-lane-coordination.duckdb" for lane in range(4)),
    )


def _store_record(relative: Path, receipt: Mapping[str, Any]) -> dict[str, Any]:
    if relative == Path("control.duckdb"):
        return dict(receipt["control_store"])
    lane = int(relative.parts[1].split("-", 1)[1])
    return {int(item["lane"]): dict(item) for item in receipt["coordination_stores"]}[lane]


def _validate_receipt(
    receipt: Mapping[str, Any], *, root: Path, population: Mapping[str, Any], policy: Mapping[str, Any]
) -> None:
    body = dict(receipt)
    cid = str(body.pop("receipt_cid", ""))
    if receipt.get("schema") != RECEIPT_SCHEMA or cid != g7._identity(body):
        _fail("g9 migration receipt identity differs")
    if (
        receipt.get("source_binding") != g7._source_binding(root, population)
        or receipt.get("migration_revision") != policy["migration_revision"]
        or receipt.get("prior_store_generation") != policy["prior_store_generation"]
        or receipt.get("target_store_generation") != policy["target_store_generation"]
        or receipt.get("governed_gitlinks") != policy["governed_gitlinks"]
        or receipt.get("generated_guardrail_policy") != policy["generated_guardrail_policy"]
        or receipt.get("guardrail_archive")
        != policy["stopped_predecessor_capture"]["guardrail_archive"]
        or receipt.get("task_count") != 54
        or any(
            receipt.get(field) != 0
            for field in (
                "task_status_changes",
                "task_revision_changes",
                "task_definition_changes",
                "accepted_completion_changes",
            )
        )
        or receipt.get("plan_revision_changes") != 1
        or receipt.get("evidence_node_changes") != 1
        or receipt.get("g8_source_mutated") is not False
    ):
        _fail("g9 migration receipt belongs to another source or policy")


def _validate_store(root: Path, target: Path, relative: Path, receipt: Mapping[str, Any]) -> None:
    path = target / relative
    metadata = os.stat(path, follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        _fail(f"g9 published store is unsafe: {relative.as_posix()}")
    expected = _store_record(relative, receipt)
    observed = g7._stable_file(path, root=root, noun=f"g9 {relative.as_posix()}", required_links=None)
    if observed != (str(expected["sha256"]), int(expected["size_bytes"])):
        _fail(f"g9 published store differs: {relative.as_posix()}")


def _prepared_path(target: Path, receipt: Mapping[str, Any]) -> Path:
    cid = str(receipt.get("receipt_cid") or "")
    digest = cid.removeprefix("sha256:")
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        _fail("g9 prepared receipt CID is malformed")
    return target.parent / f"{PREPARED_STAGE_PREFIX}{digest}"


def _stage_files(stage: Path) -> set[Path]:
    return {
        path.relative_to(stage)
        for path in stage.rglob("*")
        if not (path.is_dir() and not path.is_symlink())
    }


def _validate_prepared(
    *, root: Path, target: Path, stage: Path, receipt: Mapping[str, Any], require_all: bool
) -> None:
    g7._assert_private_directory(stage)
    expected = set(_store_relative_files()) | {Path(PREPARED_RECEIPT)}
    observed = _stage_files(stage)
    if not observed.issubset(expected) or Path(PREPARED_RECEIPT) not in observed or (require_all and observed != expected):
        _fail("g9 prepared stage population differs")
    stored = g7._load_json(stage / PREPARED_RECEIPT, root=root, noun="prepared g9 receipt")
    if stored != dict(receipt):
        _fail("g9 prepared receipt bytes differ")
    for relative in set(_store_relative_files()) & observed:
        _validate_store(root, stage, relative, receipt)


def _arm_prepared(*, root: Path, target: Path, stage: Path, receipt: Mapping[str, Any]) -> Path:
    g7._write_new_json(stage / PREPARED_RECEIPT, receipt)
    prepared = _prepared_path(target, receipt)
    if os.path.lexists(prepared):
        _fail("g9 prepared stage already exists")
    for relative in _store_relative_files():
        g7._fsync_private_file(stage / relative, noun=f"staged g9 {relative.as_posix()}")
    g7._fsync_private_file(stage / PREPARED_RECEIPT, noun="staged g9 receipt")
    for path in stage.rglob("*"):
        if path.is_dir() and not path.is_symlink():
            g7._assert_private_directory(path)
            g7._fsync_directory(path)
    g7._fsync_directory(stage)
    os.rename(stage, prepared)
    g7._fsync_directory(prepared.parent)
    _validate_prepared(root=root, target=target, stage=prepared, receipt=receipt, require_all=True)
    return prepared


def _publish_stage(*, root: Path, stage: Path, target: Path, receipt: Mapping[str, Any]) -> None:
    if os.path.lexists(target):
        _fail("g9 target already exists")
    _validate_prepared(root=root, target=target, stage=stage, receipt=receipt, require_all=True)
    os.rename(stage, target)
    g7._fsync_directory(target.parent)
    prepared = target / PREPARED_RECEIPT
    pending = target / PENDING_MARKER
    marker = target / MIGRATION_MARKER
    os.rename(prepared, pending)
    g7._fsync_directory(target)
    for relative in _store_relative_files():
        _validate_store(root, target, relative, receipt)
        if os.stat(target / relative, follow_symlinks=False).st_nlink != 1:
            _fail("g9 published store retains a hardlink")
    os.link(pending, marker, follow_symlinks=False)
    g7._fsync_directory(target)
    pending.unlink()
    g7._fsync_directory(target)


def _finish_publication(
    *, root: Path, target: Path, receipt_validator: Any
) -> bool:
    candidates = sorted(target.parent.glob(f"{PREPARED_STAGE_PREFIX}*"))
    if not os.path.lexists(target):
        if not candidates:
            return False
        if len(candidates) != 1:
            _fail("g9 prepared stage population is ambiguous")
        stage = candidates[0]
        receipt = g7._load_json(stage / PREPARED_RECEIPT, root=root, noun="orphan g9 receipt")
        receipt_validator(receipt)
        _publish_stage(root=root, stage=stage, target=target, receipt=receipt)
        return True
    if candidates:
        _fail("g9 target and prepared stage coexist ambiguously")
    g7._assert_private_directory(target)
    marker, pending, prepared = (
        target / MIGRATION_MARKER,
        target / PENDING_MARKER,
        target / PREPARED_RECEIPT,
    )
    if os.path.lexists(marker):
        expected = set(_store_relative_files()) | {Path(MIGRATION_MARKER)}
        if os.path.lexists(pending):
            expected.add(Path(PENDING_MARKER))
        if _stage_files(target) != expected:
            _fail("g9 linked publication contains unexpected artifacts")
        payload, _digest, _size, _identity = g7._read_stable_file_snapshot(
            marker,
            root=root,
            noun="g9 marker",
            required_links=2 if os.path.lexists(pending) else 1,
            maximum_bytes=g7.MAX_JSON_BYTES,
        )
        receipt = g7._decode_json(payload, noun="g9 marker")
        receipt_validator(receipt)
        if os.path.lexists(pending):
            pending.unlink()
            g7._fsync_directory(target)
        return True
    if os.path.lexists(prepared):
        receipt = g7._load_json(prepared, root=root, noun="renamed g9 receipt")
        receipt_validator(receipt)
        _validate_prepared(
            root=root,
            target=target,
            stage=target,
            receipt=receipt,
            require_all=True,
        )
        os.rename(prepared, pending)
        g7._fsync_directory(target)
    elif os.path.lexists(pending):
        receipt = g7._load_json(pending, root=root, noun="pending g9 receipt")
        receipt_validator(receipt)
        expected = set(_store_relative_files()) | {Path(PENDING_MARKER)}
        if _stage_files(target) != expected:
            _fail("g9 pending publication contains unexpected artifacts")
    else:
        _fail("g9 runtime exists without a publication receipt")
    for relative in _store_relative_files():
        _validate_store(root, target, relative, receipt)
    os.link(pending, marker, follow_symlinks=False)
    g7._fsync_directory(target)
    pending.unlink()
    g7._fsync_directory(target)
    return True


def _receipt(
    *, root: Path, stage: Path, population: Mapping[str, Any], policy: Mapping[str, Any], prior: Mapping[str, Any], post: Mapping[str, Any], suffix: Mapping[str, Any]
) -> dict[str, Any]:
    control = stage / "control.duckdb"
    digest, size = g7._stable_file(control, root=root, noun="staged g9 control")
    stores: list[dict[str, Any]] = []
    for lane in range(4):
        path = stage / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
        lane_digest, lane_size = g7._stable_file(path, root=root, noun=f"staged g9 lane {lane}")
        stores.append({"lane": lane, "sha256": lane_digest, "size_bytes": lane_size})
    body = {
        "schema": RECEIPT_SCHEMA,
        "migration_revision": policy["migration_revision"],
        "prior_store_generation": policy["prior_store_generation"],
        "target_store_generation": policy["target_store_generation"],
        "source_binding": g7._source_binding(root, population),
        "governed_gitlinks": dict(policy["governed_gitlinks"]),
        "generated_guardrail_policy": dict(policy["generated_guardrail_policy"]),
        "guardrail_archive": dict(policy["stopped_predecessor_capture"]["guardrail_archive"]),
        "control_store": {"sha256": digest, "size_bytes": size},
        "coordination_stores": stores,
        "prior_event_watermark": prior["event_watermark"],
        "prior_event_prefix_digest": prior["event_prefix_digest"],
        "migration_event_watermark": post["event_watermark"],
        "migration_event_prefix_digest": post["event_prefix_digest"],
        "task_count": 54,
        "task_status_changes": 0,
        "task_revision_changes": 0,
        "task_definition_changes": 0,
        "accepted_completion_changes": 0,
        "plan_revision_changes": 1,
        "evidence_node_changes": 1,
        "g8_source_mutated": False,
        "suffix": dict(suffix),
    }
    return {**body, "receipt_cid": g7._identity(body)}


def _new_stage(parent: Path) -> Path:
    stage = Path(tempfile.mkdtemp(prefix=".pctdd-g9-installing.", dir=parent))
    g7._assert_private_directory(stage)
    g7._ensure_private_directory(stage / "state")
    return stage


def migrate_descendant_source(
    *, root: Path, config: Mapping[str, Any], population: Mapping[str, Any]
) -> dict[str, Any]:
    """Create the fresh g9 authority; never mutate the stopped g8 source."""

    root = root.resolve()
    policy = _policy(config)
    policy["repository_root"] = str(root)
    g7._assert_source_delta(root, population, policy)
    target = g7._confined(root, policy["target_runtime_root"], noun="g9 runtime root")
    def validator(receipt: Mapping[str, Any]) -> None:
        _validate_receipt(
            receipt,
            root=root,
            population=population,
            policy=policy,
        )
    if os.path.lexists(target / MIGRATION_MARKER) and not os.path.lexists(
        target / PENDING_MARKER
    ):
        return check_descendant_source(
            root=root, config=config, population=population, allow_progressed=True
        )
    prior_control = g7._file_anchor(
        root, policy["stopped_predecessor_capture"]["prior_control_store"], noun="stopped g8 control store"
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        offline_state_server_fence,
    )

    fence = offline_state_server_fence(
        database_path=prior_control,
        connection_factory=lambda path: g7._open_local_database(path, read_only=True),
    )
    predecessor_connection: Any | None = None
    descriptor: int | None = None
    stage: Path | None = None
    lock_dir = target.parent / ".pctdd-g9-migration-locks"
    g7._ensure_private_directory(lock_dir)
    try:
        predecessor_connection = fence.__enter__()
        prior = _inspect_predecessor(root, policy, connection=predecessor_connection)
        descriptor, lock_identity = g7._open_migration_lock(lock_dir / LOCK_NAME)
        deadline = time.monotonic() + 10.0
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    _fail("timed out acquiring g9 migration lock", exc)
                time.sleep(0.02)
        g7._assert_migration_lock_identity(lock_dir / LOCK_NAME, descriptor, lock_identity)
        if _finish_publication(root=root, target=target, receipt_validator=validator):
            return check_descendant_source(
                root=root, config=config, population=population, allow_progressed=False
            )
        stage = _new_stage(target.parent)
        stage_control = stage / "control.duckdb"
        g7._copy_anchored_file(
            prior["control"], stage_control, root=root,
            record=policy["stopped_predecessor_capture"]["prior_control_store"],
            noun="stopped g8 control store",
        )
        coordination_paths: list[Path] = []
        for item in prior["coordination"]:
            lane = int(item["policy"]["lane"])
            path = stage / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
            g7._copy_anchored_file(
                item["database"], path, root=root, record=item["policy"],
                noun=f"g8 lane {lane} coordination",
            )
            coordination_paths.append(path)
        suffix = _apply_control_suffix(
            stage_control,
            root=root,
            population=population,
            policy=policy,
            prior_projection=prior["projection"],
        )
        g7._checkpoint_database(stage_control)
        post = _verify_staged_successor(
            stage_control,
            prior=prior["projection"],
            policy=policy,
            suffix=suffix,
        )
        for lane, path in enumerate(coordination_paths):
            projection = g7._coordination_projection(path)
            if projection["projection_root"] != prior["coordination"][lane]["policy"]["projection_root"]:
                _fail(f"g9 changed lane {lane} coordination history")
        g7._retire_private_stage_coordination_locks(stage)
        receipt = _receipt(
            root=root,
            stage=stage,
            population=population,
            policy=policy,
            prior=prior["projection"],
            post=post,
            suffix=suffix,
        )
        stage = _arm_prepared(root=root, target=target, stage=stage, receipt=receipt)
        g7._assert_source_delta(root, population, policy)
        _inspect_predecessor(root, policy, connection=predecessor_connection)
        _publish_stage(root=root, stage=stage, target=target, receipt=receipt)
        stage = None
        return {
            "schema": CHECK_SCHEMA,
            "valid": True,
            "mode": "migrate-descendant-source",
            "migration_required": False,
            "receipt": receipt,
            "target_runtime_root": str(target.relative_to(root)),
        }
    finally:
        if descriptor is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(descriptor)
        if stage is not None and stage.exists() and not stage.name.startswith(PREPARED_STAGE_PREFIX):
            shutil.rmtree(stage)
        if predecessor_connection is not None:
            fence.__exit__(None, None, None)


def check_descendant_source(
    *, root: Path, config: Mapping[str, Any], population: Mapping[str, Any], allow_progressed: bool
) -> dict[str, Any]:
    root = root.resolve()
    policy = _policy(config)
    policy["repository_root"] = str(root)
    g7._assert_source_delta(root, population, policy)
    target = g7._confined(root, policy["target_runtime_root"], noun="g9 runtime root")
    marker = target / MIGRATION_MARKER
    if not marker.is_file() or marker.is_symlink():
        _fail("g9 migration marker is absent")
    receipt = g7._load_json(marker, root=root, noun="g9 migration marker")
    _validate_receipt(receipt, root=root, population=population, policy=policy)
    for relative in _store_relative_files():
        _validate_store(root, target, relative, receipt)
    if not allow_progressed:
        expected = set(_store_relative_files()) | {Path(MIGRATION_MARKER)}
        if _stage_files(target) != expected:
            _fail("g9 initial publication contains unexpected artifacts")
    elif os.path.lexists(target / PENDING_MARKER) or os.path.lexists(
        target / PREPARED_RECEIPT
    ):
        _fail("g9 publication remains incomplete")
    post = g7._control_projection(target / "control.duckdb")
    if _task_aliases(post) != EXPECTED_ALIASES:
        _fail("g9 target does not retain canonical tasks")
    if not allow_progressed:
        if post["event_prefix_digest"] != receipt["migration_event_prefix_digest"]:
            _fail("g9 target progressed before initial verification")
        if g7._stable_file(target / "control.duckdb", root=root, noun="g9 control")[0] != receipt["control_store"]["sha256"]:
            _fail("g9 control bytes changed before initial verification")
    return {
        "schema": CHECK_SCHEMA,
        "valid": True,
        "mode": "check-descendant-source-migration",
        "allow_progressed": bool(allow_progressed),
        "receipt": receipt,
        "task_count": 54,
        "generated_guardrail_task_rows": 0,
    }


def _load_cli_controls(config_path: Path) -> tuple[Path, Any, Any, dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    path = root / "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py"
    spec = importlib.util.spec_from_file_location("pctdd_g9_materializer", path)
    if spec is None or spec.loader is None:
        _fail("PCTDD materializer cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    board, config, _raw = module._load_board(config_path)
    return root, module, board, dict(config)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "check", "check-policy"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--allow-progressed", action="store_true")
    arguments = parser.parse_args(argv)
    root, materializer, board, config = _load_cli_controls(arguments.config.resolve())
    if arguments.command == "check-policy":
        # Static policy validation must remain useful before the reviewed
        # descendant commit is integrated onto the configured canonical
        # branch.  It intentionally does not inspect source or runtime state.
        result = validate_pending_policy(config)
    else:
        population = dict(materializer._population(board, config))
    if arguments.command == "migrate":
        result = migrate_descendant_source(root=root, config=config, population=population)
    elif arguments.command == "check":
        result = check_descendant_source(
            root=root, config=config, population=population,
            allow_progressed=bool(arguments.allow_progressed),
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


__all__ = (
    "ARCHIVE_SCHEMA",
    "CAPTURE_SCHEMA",
    "CHECK_SCHEMA",
    "DescendantSourceSuccessorError",
    "EVIDENCE_SCHEMA",
    "MIGRATION_SCHEMA",
    "RECEIPT_SCHEMA",
    "capture_stopped_descendant_authority",
    "check_descendant_source",
    "migrate_descendant_source",
    "validate_pending_policy",
)


if __name__ == "__main__":
    raise SystemExit(main())
