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
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
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
ORPHAN_RECOVERY_POLICY_SCHEMA: Final[str] = (
    "pctdd/orphan-terminal-migration-recovery-policy@1"
)
ORPHAN_RECOVERY_PLAN_SCHEMA: Final[str] = (
    "pctdd/orphan-terminal-migration-recovery-plan@1"
)
ORPHAN_RECOVERY_RECEIPT_SCHEMA: Final[str] = (
    "pctdd/orphan-terminal-migration-recovery-receipt@1"
)
ORPHAN_RECOVERY_MARKER: Final[str] = (
    "descendant-source-orphan-terminal-recovery-receipt.json"
)
ORPHAN_RECOVERY_PREPARED: Final[str] = (
    ".descendant-source-orphan-terminal-recovery-prepared.json"
)
ORPHAN_RECOVERY_PENDING: Final[str] = (
    ".descendant-source-orphan-terminal-recovery-receipt.pending.json"
)
ORPHAN_RECOVERY_ALIASES: Final[tuple[str, ...]] = (
    "PCTDD-001",
    "PCTDD-031",
    "PCTDD-034",
)
ORPHAN_RECOVERY_EVIDENCE_KIND: Final[str] = (
    "operator_orphan_terminal_migration_revalidation"
)
MAX_VALIDATION_OUTPUT_BYTES: Final[int] = 262_144
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


class _TransientRecoveryLockCleanup:
    """Retire only empty local task/coordination locks on every exit path."""

    def __init__(self, target: Path) -> None:
        self._target = target

    def __enter__(self) -> None:
        return None

    def __exit__(self, *_details: object) -> bool:
        g7._retire_private_stage_coordination_locks(self._target)
        return False


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
    recovery = policy.get("orphan_terminal_recovery")
    expected_profiles = {
        alias: f"pctdd-validation/PCTDD-PLAN-V1.1/{alias}@1"
        for alias in ORPHAN_RECOVERY_ALIASES
    }
    if (
        not isinstance(recovery, Mapping)
        or recovery.get("schema") != ORPHAN_RECOVERY_POLICY_SCHEMA
        or recovery.get("candidate_task_aliases") != list(ORPHAN_RECOVERY_ALIASES)
        or recovery.get("receipt_marker") != ORPHAN_RECOVERY_MARKER
        or recovery.get("prepared_receipt") != ORPHAN_RECOVERY_PREPARED
        or recovery.get("validation_dispatcher")
        != "scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py"
        or recovery.get("validation_profile_path")
        != "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json"
        or recovery.get("validation_profiles") != expected_profiles
        or recovery.get("prior_store_generation") != policy["prior_store_generation"]
        or recovery.get("target_store_generation") != policy["target_store_generation"]
        or recovery.get("one_shot") is not True
        or recovery.get("requires_exact_source_binding") is not True
        or recovery.get("requires_exact_stopped_capture") is not True
        or recovery.get("requires_offline_owner_fence") is not True
        or recovery.get("green_transition") != "blocked_to_completed"
        or recovery.get("non_green_transition") != "blocked_to_retrying"
        or recovery.get("coordination_completion_required") is not True
        or type(recovery.get("timeout_seconds")) is not int
        or not 1 <= int(recovery["timeout_seconds"]) <= 21_600
    ):
        _fail("g9 orphan-terminal recovery policy differs")
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


def _event_prefix(database: Path | str, count: int) -> str:
    connection = g7._open_control_target(database)
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


def _owner_lock_relative() -> Path:
    return Path(".control.duckdb.state-owner.lock")


def _validate_owner_lock(target: Path) -> None:
    path = target / _owner_lock_relative()
    metadata = os.stat(path, follow_symlinks=False)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_nlink != 1
        or metadata.st_size != 0
    ):
        _fail("g9 offline owner lock is unsafe")


def _load_marker_snapshot(
    *, root: Path, path: Path, noun: str, required_links: int = 1
) -> tuple[dict[str, Any], tuple[int, ...]]:
    """Read an operator marker once and retain its inode/content identity."""

    payload, _digest, _size, identity = g7._read_stable_file_snapshot(
        path,
        root=root,
        noun=noun,
        required_links=required_links,
        maximum_bytes=g7.MAX_JSON_BYTES,
    )
    if identity[-2:] != (int(os.geteuid()), 0o600):
        _fail(f"{noun} is not private")
    return g7._decode_json(payload, noun=noun), identity


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


def _capture_binding(policy: Mapping[str, Any]) -> str:
    return g7._identity(dict(policy["stopped_predecessor_capture"]))


def _load_initial_migration_receipt(
    *, root: Path, target: Path, population: Mapping[str, Any], policy: Mapping[str, Any]
) -> dict[str, Any]:
    marker = target / MIGRATION_MARKER
    if not marker.is_file() or marker.is_symlink():
        _fail("g9 migration marker is absent before orphan recovery")
    receipt, marker_identity = _load_marker_snapshot(
        root=root, path=marker, noun="g9 migration marker"
    )
    _validate_receipt(receipt, root=root, population=population, policy=policy)
    return receipt


def _task_validation_argv(
    task: Any, *, alias: str, recovery_policy: Mapping[str, Any]
) -> list[str]:
    expected_text = (
        f"python {recovery_policy['validation_dispatcher']} --task {alias}"
    )
    validations = list(task.validations)
    if len(validations) != 1:
        _fail(f"{alias} does not have exactly one sealed validation")
    validation = dict(validations[0])
    if (
        validation.get("argv") != [expected_text]
        or dict(validation.get("policy") or {}).get("representation") != "shell_text"
        or task.body.get("validation_profile_id")
        != recovery_policy["validation_profiles"][alias]
    ):
        _fail(f"{alias} validation dispatcher/profile binding differs")
    return [
        os.fspath(Path(sys.executable).resolve()),
        str(recovery_policy["validation_dispatcher"]),
        "--task",
        alias,
    ]


def _current_output_manifest(root: Path, task: Any, *, alias: str) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    missing: list[str] = []
    paths = [str(dict(item).get("path") or "") for item in task.outputs]
    if not paths or len(paths) != len(set(paths)):
        _fail(f"{alias} declared output population differs")
    for relative in paths:
        path = g7._confined(root, relative, noun=f"{alias} output")
        if not path.is_file() or path.is_symlink():
            missing.append(relative)
            continue
        repository = root
        repository_relative = relative
        repository_authority = "."
        gitlink_oid: str | None = None
        for gitlink in (
            "external/ipfs_accelerate",
            "external/ipfs_datasets",
            "external/ipfs_kit",
        ):
            prefix = gitlink + "/"
            if relative.startswith(prefix):
                repository = root / gitlink
                repository_relative = relative[len(prefix):]
                repository_authority = gitlink
                outer_entry = g7._git(root, "ls-tree", "HEAD", "--", gitlink).split()
                if len(outer_entry) < 4 or outer_entry[1] != "commit":
                    _fail(f"{alias} owning gitlink differs: {gitlink}")
                gitlink_oid = outer_entry[2]
                break
        mode = g7._git(
            repository, "ls-tree", "HEAD", "--", repository_relative
        ).split()
        if len(mode) < 4 or mode[1] != "blob":
            missing.append(relative)
            continue
        worktree_blob = g7._git(
            repository, "hash-object", "--", repository_relative
        )
        repository_head = g7._git(repository, "rev-parse", "HEAD")
        repository_tree = g7._git(repository, "rev-parse", "HEAD^{tree}")
        if gitlink_oid is not None and repository_head != gitlink_oid:
            _fail(f"{alias} nested authority differs from its gitlink: {relative}")
        if worktree_blob != mode[2]:
            _fail(f"{alias} output differs from the bound source tree: {relative}")
        digest, size = g7._stable_file(
            path, root=root, noun=f"{alias} output", required_links=None
        )
        final_mode = g7._git(
            repository, "ls-tree", "HEAD", "--", repository_relative
        ).split()
        final_head = g7._git(repository, "rev-parse", "HEAD")
        final_tree = g7._git(repository, "rev-parse", "HEAD^{tree}")
        if (
            final_mode != mode
            or final_head != repository_head
            or final_tree != repository_tree
        ):
            _fail(f"{alias} output authority changed while hashing: {relative}")
        if gitlink_oid is not None:
            final_outer = g7._git(root, "ls-tree", "HEAD", "--", repository_authority).split()
            if (
                len(final_outer) < 4
                or final_outer[1] != "commit"
                or final_outer[2] != gitlink_oid
                or final_head != gitlink_oid
            ):
                _fail(f"{alias} gitlink changed while hashing: {relative}")
        records.append(
            {
                "path": relative,
                "repository_authority": repository_authority,
                "repository_head": repository_head,
                "repository_tree": repository_tree,
                "gitlink_oid": gitlink_oid,
                "git_mode": mode[0],
                "git_blob_oid": worktree_blob,
                "sha256": digest,
                "size_bytes": size,
            }
        )
    return {"outputs": records, "missing_outputs": sorted(missing)}


def _default_validation_runner(
    argv: Sequence[str], *, root: Path, timeout_seconds: int
) -> dict[str, Any]:
    def capture(stream: Any) -> tuple[bytes, str, int, bool]:
        stream.flush()
        size = int(stream.seek(0, os.SEEK_END))
        stream.seek(0)
        digest = hashlib.sha256()
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        stream.seek(max(0, size - MAX_VALIDATION_OUTPUT_BYTES))
        tail = bytes(stream.read(MAX_VALIDATION_OUTPUT_BYTES))
        return tail, digest.hexdigest(), size, size > MAX_VALIDATION_OUTPUT_BYTES

    with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
        process = subprocess.Popen(
            list(argv),
            cwd=root,
            stdin=subprocess.DEVNULL,
            stdout=stdout_file,
            stderr=stderr_file,
            start_new_session=True,
            close_fds=True,
        )
        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (
                terminate_process_with_grace,
            )

            termination = terminate_process_with_grace(
                process, grace_seconds=5.0, kill_wait_seconds=5.0
            )
            if termination.timed_out:
                _fail("validation process tree did not terminate after timeout")
        stdout, stdout_digest, stdout_size, stdout_truncated = capture(stdout_file)
        stderr, stderr_digest, stderr_size, stderr_truncated = capture(stderr_file)
        if timed_out:
            return {
                "attempted": True,
                "returncode": 124,
                "stdout_sha256": stdout_digest,
                "stderr_sha256": stderr_digest,
                "stdout_size_bytes": stdout_size,
                "stderr_size_bytes": stderr_size,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
                "timeout": True,
            }
        records: list[dict[str, Any]] = []
        parse_error = stdout_truncated
        duplicate_key = False

        def reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
            nonlocal duplicate_key
            value: dict[str, Any] = {}
            for key, item in pairs:
                if key in value:
                    duplicate_key = True
                    raise ValueError(f"duplicate validation key: {key}")
                value[key] = item
            return value

        records: list[dict[str, Any]] = []
        for line in stdout.decode("utf-8", errors="strict").splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line, object_pairs_hook=reject_duplicate_pairs)
            except (json.JSONDecodeError, ValueError):
                parse_error = True
                continue
            if not isinstance(value, dict):
                parse_error = True
                continue
            records.append(value)
        return {
            "attempted": True,
            "returncode": int(process.returncode or 0),
            "stdout_sha256": stdout_digest,
            "stderr_sha256": stderr_digest,
            "stdout_size_bytes": stdout_size,
            "stderr_size_bytes": stderr_size,
            "stdout_truncated": stdout_truncated,
            "stderr_truncated": stderr_truncated,
            "records": records,
            "record_parse_error": parse_error,
            "duplicate_json_key": duplicate_key,
        }


def _validation_is_admitted(
    validation: Mapping[str, Any], *, expected_profile: str, expected_task: str
) -> bool:
    records = validation.get("records")
    if (
        validation.get("attempted") is not True
        or validation.get("returncode") != 0
        or validation.get("timeout") is True
        or validation.get("stdout_truncated") is not False
        or validation.get("stderr_truncated") is not False
        or validation.get("record_parse_error") is True
        or validation.get("duplicate_json_key") is True
        or not isinstance(records, list)
        or len(records) != 2
        or any(
            not isinstance(item, Mapping)
            or item.get("task_id") != expected_task
            or item.get("profile_id") != expected_profile
            or item.get("status") != "passed"
            or item.get("returncode") != 0
            for item in records
        )
    ):
        return False
    if [item.get("step") for item in records] != [0, 1]:
        return False
    if [item.get("evidence_policy") for item in records] != [
        "required_acceptance",
        "protected_baseline_regression",
    ]:
        return False
    required = [
        item for item in records
        if isinstance(item, Mapping)
        and item.get("evidence_policy") == "required_acceptance"
    ]
    if len(required) != 1 or required[0].get("step") != 0:
        return False
    phase = required[0].get("pytest_phase_evidence")
    counts = phase.get("counts") if isinstance(phase, Mapping) else None
    if not isinstance(counts, Mapping) or set(counts) != {
        "passed", "failed", "skipped", "xfail", "xpass", "error", "rerun"
    }:
        return False
    numbers = [
        phase.get("test_count"),
        phase.get("phase_count"),
        phase.get("fully_passed_test_count"),
        *(counts.get(name) for name in counts),
    ]
    if not all(type(value) is int and value >= 0 for value in numbers):
        return False
    test_count = int(phase["test_count"])
    phase_count = int(phase["phase_count"])
    if (
        phase.get("schema") != "pctdd/pytest-phase-outcome@1"
        or test_count <= 0
        or phase_count != test_count * 3
        or int(phase["fully_passed_test_count"]) != test_count
        or int(counts["passed"]) != phase_count
        or sum(int(value) for value in counts.values()) != phase_count
        or any(
            int(counts[name]) != 0
            for name in ("failed", "skipped", "xfail", "xpass", "error", "rerun")
        )
    ):
        return False
    launchers = [item.get("validation_python_launcher") for item in records]
    if not all(
        isinstance(item, Mapping)
        and set(item) == {
            "mode", "content_sha256", "interpreter_sha256", "policy_sha256", "sealed"
        }
        and item.get("sealed") is True
        and all(
            isinstance(item.get(field), str) and bool(item.get(field))
            for field in (
                "mode", "content_sha256", "interpreter_sha256", "policy_sha256"
            )
        )
        for item in launchers
    ):
        return False
    return launchers[0] == launchers[1]
def _terminal_claim_binding(
    *, target: Path, task: Any, blocked_receipt: Mapping[str, Any]
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (
        DatabaseCoordinator,
    )

    claim_id = str(blocked_receipt.get("claim_id") or "")
    if not claim_id:
        _fail(f"{task.task_alias} blocked receipt lacks a claim")
    matches: list[dict[str, Any]] = []
    for lane in range(4):
        database = target / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
        with DatabaseCoordinator(database) as coordinator:
            claim = coordinator.get_task_claim(claim_id)
            if claim is None:
                continue
            claim_record = claim.to_dict()
            expected = {
                "task_cid": task.task_cid,
                "claim_id": claim_id,
                "attempt_id": str(blocked_receipt.get("attempt_id") or ""),
                "attempt_number": int(blocked_receipt.get("attempt_number") or 0),
                "owner_session_id": str(blocked_receipt.get("owner_session_id") or ""),
                "lease_id": str(blocked_receipt.get("lease_id") or ""),
                "fencing_token": int(blocked_receipt.get("fencing_token") or 0),
                "fence_epoch": int(blocked_receipt.get("fence_epoch") or 0),
            }
            if (
                claim_record.get("state") not in {"released", "expired"}
                or any(claim_record.get(name) != value for name, value in expected.items())
                or coordinator.get_prepared_task_completion(task.task_cid) is not None
            ):
                _fail(f"{task.task_alias} historical terminal claim differs")
            matches.append({"lane": lane, "claim": claim_record})
    if len(matches) != 1:
        _fail(f"{task.task_alias} terminal claim is absent or ambiguous")
    return matches[0]


def _prepare_orphan_recovery_plan(
    *,
    root: Path,
    target: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    migration_receipt: Mapping[str, Any],
    validation_runner: Any | None,
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    recovery_policy = dict(policy["orphan_terminal_recovery"])
    runner = validation_runner or _default_validation_runner
    decisions: list[dict[str, Any]] = []
    with DatabaseTaskSource(
        target / "control.duckdb",
        owner_id="pctdd-descendant-source-g9:orphan-recovery-plan",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        for alias in ORPHAN_RECOVERY_ALIASES:
            task = source.get_task(alias)
            if task is None or task.status != "blocked":
                _fail(f"{alias} is not the exact blocked migration candidate")
            blocked_receipt = task.body.get("completion_receipt")
            if not isinstance(blocked_receipt, Mapping) or not blocked_receipt:
                _fail(f"{alias} blocked receipt is absent")
            claim_binding = _terminal_claim_binding(
                target=target, task=task, blocked_receipt=blocked_receipt
            )
            output_manifest = _current_output_manifest(root, task, alias=alias)
            argv = _task_validation_argv(
                task, alias=alias, recovery_policy=recovery_policy
            )
            if output_manifest["missing_outputs"]:
                validation = {
                    "attempted": False,
                    "returncode": 1,
                    "reason": "declared_outputs_missing",
                }
                target_status = "retrying"
            else:
                try:
                    observed = runner(
                        argv,
                        root=root,
                        timeout_seconds=int(recovery_policy["timeout_seconds"]),
                    )
                    validation = dict(observed)
                except Exception as exc:
                    validation = {
                        "attempted": False,
                        "returncode": 125,
                        "reason": "validation_infrastructure_error",
                        "error_type": type(exc).__name__,
                    }
                if type(validation.get("returncode")) is not int:
                    validation = {
                        "attempted": False,
                        "returncode": 125,
                        "reason": "validation_result_malformed",
                    }
                admitted = _validation_is_admitted(
                    validation,
                    expected_profile=str(recovery_policy["validation_profiles"][alias]),
                    expected_task=alias,
                )
                if admitted:
                    target_status = "completed"
                elif (
                    validation.get("attempted") is True
                    and validation.get("timeout") is not True
                    and validation.get("stdout_truncated") is False
                    and validation.get("stderr_truncated") is False
                    and validation.get("record_parse_error") is not True
                    and validation.get("duplicate_json_key") is not True
                    and isinstance(validation.get("records"), list)
                    and validation.get("records")
                ):
                    target_status = "retrying"
                else:
                    target_status = "blocked"
            evidence_body = {
                "schema": "pctdd/orphan-terminal-current-tree-validation@1",
                "source_binding": g7._source_binding(root, population),
                "capture_binding": _capture_binding(policy),
                "migration_receipt_cid": migration_receipt["receipt_cid"],
                "task_alias": alias,
                "task_cid": task.task_cid,
                "blocked_revision": int(task.revision),
                "blocked_receipt": dict(blocked_receipt),
                "output_manifest": output_manifest,
                "validation_argv": argv,
                "validation": validation,
                "target_status": target_status,
                "claim_binding": claim_binding,
            }
            decisions.append(
                {
                    **evidence_body,
                    "evidence_digest": g7._identity(evidence_body),
                }
            )
    initial_control_projection = g7._control_projection(target / "control.duckdb")
    initial_coordination_projections = [
        {
            "lane": lane,
            "projection": g7._coordination_projection(
                target / "state" / f"lane-{lane}"
                / "quack-lane-coordination.duckdb"
            ),
        }
        for lane in range(4)
    ]
    body = {
        "schema": ORPHAN_RECOVERY_PLAN_SCHEMA,
        "prior_store_generation": policy["prior_store_generation"],
        "target_store_generation": policy["target_store_generation"],
        "source_binding": g7._source_binding(root, population),
        "capture_binding": _capture_binding(policy),
        "migration_receipt_cid": migration_receipt["receipt_cid"],
        "candidate_task_aliases": list(ORPHAN_RECOVERY_ALIASES),
        "initial_control_store": dict(migration_receipt["control_store"]),
        "initial_control_projection": initial_control_projection,
        "initial_coordination_projections": initial_coordination_projections,
        "decisions": decisions,
    }
    return {**body, "recovery_plan_id": g7._identity(body)}


def _validate_recovery_plan(
    plan: Mapping[str, Any], *, root: Path, population: Mapping[str, Any],
    policy: Mapping[str, Any], migration_receipt: Mapping[str, Any]
) -> None:
    body = dict(plan)
    plan_id = str(body.pop("recovery_plan_id", ""))
    decisions = plan.get("decisions")
    initial_control = plan.get("initial_control_projection")
    initial_coordination = plan.get("initial_coordination_projections")
    if (
        plan.get("schema") != ORPHAN_RECOVERY_PLAN_SCHEMA
        or plan_id != g7._identity(body)
        or plan.get("source_binding") != g7._source_binding(root, population)
        or plan.get("capture_binding") != _capture_binding(policy)
        or plan.get("migration_receipt_cid") != migration_receipt["receipt_cid"]
        or plan.get("candidate_task_aliases") != list(ORPHAN_RECOVERY_ALIASES)
        or not isinstance(initial_control, Mapping)
        or initial_control.get("event_prefix_digest")
        != migration_receipt["migration_event_prefix_digest"]
        or initial_control.get("task_definition_digest")
        != policy["stopped_predecessor_capture"]["prior_control_projection"][
            "task_definition_digest"
        ]
        or not isinstance(initial_coordination, list)
        or [
            item.get("lane") for item in initial_coordination
            if isinstance(item, Mapping)
        ] != list(range(4))
        or not isinstance(decisions, list)
        or [item.get("task_alias") for item in decisions if isinstance(item, Mapping)]
        != list(ORPHAN_RECOVERY_ALIASES)
    ):
        _fail("g9 orphan recovery prepared plan differs")
    for item in decisions:
        evidence = dict(item)
        digest = str(evidence.pop("evidence_digest", ""))
        if (
            digest != g7._identity(evidence)
            or item.get("target_status") not in {"completed", "retrying", "blocked"}
            or item.get("source_binding") != plan["source_binding"]
            or item.get("capture_binding") != plan["capture_binding"]
        ):
            _fail("g9 orphan recovery decision differs")


def _revalidate_prepared_recovery_plan(
    *,
    root: Path,
    target: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    plan: Mapping[str, Any],
    validation_runner: Any | None,
) -> None:
    """Re-run prepared validation before any crash-replayed control mutation."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    recovery_policy = dict(policy["orphan_terminal_recovery"])
    runner = validation_runner or _default_validation_runner
    with DatabaseTaskSource(
        target / "control.duckdb",
        owner_id="pctdd-descendant-source-g9:orphan-recovery-revalidate",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        for value in plan["decisions"]:
            decision = dict(value)
            alias = str(decision["task_alias"])
            task = source.get_task(alias)
            if task is None or task.task_cid != decision["task_cid"]:
                _fail(f"{alias} prepared recovery task identity differs")
            expected_revision = int(decision["blocked_revision"])
            if task.status == "blocked":
                if int(task.revision) != expected_revision:
                    _fail(f"{alias} prepared recovery blocked revision differs")
            elif (
                task.status != decision["target_status"]
                or int(task.revision) != expected_revision + 1
                or dict(task.body.get("completion_receipt") or {}).get(
                    "recovery_plan_id"
                ) != plan["recovery_plan_id"]
            ):
                _fail(f"{alias} prepared recovery partial transition differs")
            current_manifest = _current_output_manifest(root, task, alias=alias)
            if current_manifest != decision["output_manifest"]:
                _fail(f"{alias} prepared recovery output manifest is stale")
            argv = _task_validation_argv(
                task, alias=alias, recovery_policy=recovery_policy
            )
            if argv != decision["validation_argv"]:
                _fail(f"{alias} prepared recovery validation command is stale")
            if current_manifest["missing_outputs"]:
                fresh_status = "retrying"
            else:
                try:
                    validation = dict(
                        runner(
                            argv,
                            root=root,
                            timeout_seconds=int(recovery_policy["timeout_seconds"]),
                        )
                    )
                except Exception as exc:
                    _fail(
                        f"{alias} prepared recovery revalidation infrastructure failed",
                        exc,
                    )
                if _validation_is_admitted(
                    validation,
                    expected_profile=str(recovery_policy["validation_profiles"][alias]),
                    expected_task=alias,
                ):
                    fresh_status = "completed"
                elif (
                    validation.get("attempted") is True
                    and validation.get("timeout") is not True
                    and validation.get("stdout_truncated") is False
                    and validation.get("stderr_truncated") is False
                    and validation.get("record_parse_error") is not True
                    and isinstance(validation.get("records"), list)
                    and validation.get("records")
                ):
                    fresh_status = "retrying"
                else:
                    _fail(f"{alias} prepared recovery revalidation is unavailable")
            if fresh_status != decision["target_status"]:
                _fail(f"{alias} prepared recovery validation outcome changed")


def _verify_prepared_recovery_progress(
    *, target: Path, policy: Mapping[str, Any], plan: Mapping[str, Any]
) -> None:
    """Admit only the exact crash-prefix of this operator recovery plan."""

    initial = dict(plan["initial_control_projection"])
    current = g7._control_projection(target / "control.duckdb")
    if (
        current.get("task_definition_digest")
        != initial.get("task_definition_digest")
        or _event_prefix(
            target / "control.duckdb", int(initial["event_watermark"])
        ) != initial["event_prefix_digest"]
    ):
        _fail("prepared recovery control prefix or definitions differ")
    baseline_tasks = {
        str(item["task_alias"]): dict(item) for item in initial["tasks"]
    }
    current_tasks = {
        str(item["task_alias"]): dict(item) for item in current["tasks"]
    }
    if set(current_tasks) != set(baseline_tasks):
        _fail("prepared recovery task population differs")
    decisions = {
        str(item["task_alias"]): dict(item) for item in plan["decisions"]
    }
    transitioned: list[str] = []
    for alias, baseline in baseline_tasks.items():
        observed = current_tasks[alias]
        if alias not in decisions:
            if observed != baseline:
                _fail(f"prepared recovery changed unrelated task {alias}")
            continue
        decision = decisions[alias]
        target_row = {
            **baseline,
            "status": decision["target_status"],
            "revision": int(decision["blocked_revision"]) + 1,
        }
        if observed == target_row:
            transitioned.append(alias)
        elif observed != baseline:
            _fail(f"prepared recovery task suffix differs: {alias}")
    expected_transition_prefix = [
        alias
        for alias in ORPHAN_RECOVERY_ALIASES
        if decisions[alias]["target_status"] != "blocked"
    ][: len(transitioned)]
    if transitioned != expected_transition_prefix:
        _fail("prepared recovery task transitions are not an ordered prefix")

    expected_events: list[tuple[str, dict[str, Any]]] = []
    for alias in ORPHAN_RECOVERY_ALIASES:
        decision = decisions[alias]
        if decision["target_status"] == "blocked":
            continue
        expected_events.append(("intent.validation_recorded", decision))
        if decision["target_status"] == "completed":
            expected_events.append(("intent.completion_recorded", decision))
        else:
            expected_events.extend(
                (
                    ("intent.evidence_recorded", decision),
                    ("intent.task_status_changed", decision),
                )
            )
    connection = g7._open_control_target(target / "control.duckdb")
    try:
        suffix = connection.execute(
            "SELECT event_type,task_cid,body_json FROM domain_events "
            "WHERE global_sequence > ? ORDER BY global_sequence",
            [int(initial["event_watermark"])],
        ).fetchall()
    finally:
        connection.close()
    if len(suffix) > len(expected_events):
        _fail("prepared recovery control event suffix is too long")
    minimum_events = sum(
        2 if decisions[alias]["target_status"] == "completed" else 3
        for alias in transitioned
    )
    if len(suffix) < minimum_events:
        _fail("prepared recovery task transition lacks its exact event suffix")
    for row, (expected_type, decision) in zip(
        suffix, expected_events, strict=False
    ):
        event_type, task_cid, raw_body = str(row[0]), str(row[1]), str(row[2])
        envelope = json.loads(raw_body)
        body = envelope.get("body") if isinstance(envelope, Mapping) else None
        if (
            event_type != expected_type
            or task_cid != decision["task_cid"]
            or not isinstance(body, Mapping)
            or envelope.get("event_type") != expected_type
        ):
            _fail("prepared recovery control event sequence differs")
        if expected_type == "intent.validation_recorded":
            nested = body.get("body")
            if (
                body.get("evidence_digest") != decision["evidence_digest"]
                or not isinstance(nested, Mapping)
                or nested.get("recovery_plan_id") != plan["recovery_plan_id"]
                or nested.get("decision")
                != {**decision, "recovery_plan_id": plan["recovery_plan_id"]}
            ):
                _fail("prepared recovery validation event differs")
        elif expected_type == "intent.evidence_recorded":
            if (
                body.get("evidence_kind") != ORPHAN_RECOVERY_EVIDENCE_KIND
                or body.get("digest") != decision["evidence_digest"]
                or body.get("body") != decision
            ):
                _fail("prepared recovery evidence event differs")
        else:
            receipt = body.get("receipt")
            if (
                body.get("status") != decision["target_status"]
                or not isinstance(receipt, Mapping)
                or receipt.get("recovery_plan_id") != plan["recovery_plan_id"]
                or receipt.get("evidence_digest") != decision["evidence_digest"]
            ):
                _fail("prepared recovery status event differs")

    initial_lanes = {
        int(item["lane"]): dict(item["projection"])
        for item in plan["initial_coordination_projections"]
    }
    for lane in range(4):
        baseline = initial_lanes[lane]
        observed = g7._coordination_projection(
            target / "state" / f"lane-{lane}"
            / "quack-lane-coordination.duckdb"
        )
        for field in (
            "schema", "authority_schema", "dependency_edges", "task_claims",
            "task_attempts", "fenced_leases", "resource_claims",
            "maintenance_leases", "task_claim_state_counts",
            "resource_claim_state_counts", "task_attempt_status_counts",
            "fenced_lease_kind_state_counts", "maintenance_lease_state_counts",
        ):
            if observed.get(field) != baseline.get(field):
                _fail(f"prepared recovery changed lane {lane} field {field}")
        base_tasks = {item["task_cid"]: dict(item) for item in baseline["tasks"]}
        seen_tasks = {item["task_cid"]: dict(item) for item in observed["tasks"]}
        if set(base_tasks) != set(seen_tasks):
            _fail(f"prepared recovery changed lane {lane} task population")
        base_completions = {
            item["task_cid"]: dict(item)
            for item in baseline["logical_completions"]
        }
        seen_completions = {
            item["task_cid"]: dict(item)
            for item in observed["logical_completions"]
        }
        allowed_completions = dict(base_completions)
        for decision in decisions.values():
            task_cid = str(decision["task_cid"])
            task_row = seen_tasks[task_cid]
            base_task = base_tasks[task_cid]
            if decision["target_status"] == "completed":
                completion_body = _coordination_completion_body(
                    decision, str(plan["recovery_plan_id"])
                )
                expected_completion = {
                    "task_cid": task_cid,
                    "status": "succeeded",
                    "body": completion_body,
                }
                baseline_completion = base_completions.get(task_cid)
                current_completion = seen_completions.get(task_cid)
                if (
                    current_completion == baseline_completion
                    and task_row == base_task
                ):
                    continue
                if current_completion == expected_completion:
                    allowed_completions[task_cid] = expected_completion
                    if task_row != {**base_task, "ready": False}:
                        _fail(
                            f"prepared recovery lane {lane} readiness differs"
                        )
                else:
                    _fail(f"prepared recovery lane {lane} partial completion differs")
            elif task_row != base_task:
                _fail(f"prepared recovery changed retry task in lane {lane}")
        if seen_completions != allowed_completions:
            _fail(f"prepared recovery lane {lane} completion population differs")


def _coordination_completion_body(decision: Mapping[str, Any], plan_id: str) -> dict[str, Any]:
    claim = dict(decision["claim_binding"])["claim"]
    return {
        "schema": "pctdd/orphan-terminal-coordination-completion@1",
        "recovery_plan_id": plan_id,
        "task_cid": decision["task_cid"],
        "evidence_digest": decision["evidence_digest"],
        **{
            name: claim[name]
            for name in (
                "attempt_id", "attempt_number", "claim_id", "lease_id",
                "owner_session_id", "fencing_token", "fence_epoch",
            )
        },
    }


def _ensure_validation_result(
    source: Any, decision: Mapping[str, Any], *, create: bool
) -> None:
    """Persist one canonical operator validation result, idempotently."""

    task_cid = str(decision["task_cid"])
    digest = str(decision["evidence_digest"])
    outcome = "passed" if decision["target_status"] == "completed" else "failed"
    body = {
        "schema": "pctdd/orphan-terminal-validation-result@1",
        "operator_revalidation": True,
        "provider_dispatched": False,
        "recovery_plan_id": str(decision.get("recovery_plan_id") or ""),
        "decision": dict(decision),
    }

    def rows() -> list[tuple[Any, ...]]:
        with source._intent._connection(write=False) as connection:
            return connection.execute(
                "SELECT outcome,evidence_digest,body_json FROM validation_results "
                "WHERE task_cid=? AND evidence_digest=? ORDER BY result_id",
                [task_cid, digest],
            ).fetchall()

    observed = rows()
    if not observed and create:
        source.record_validation_result(
            task_cid=task_cid,
            outcome=outcome,
            evidence_digest=digest,
            argv=list(decision["validation_argv"]),
            attempt_id="",
            body=body,
        )
        observed = rows()
    if (
        len(observed) != 1
        or str(observed[0][0]) != outcome
        or str(observed[0][1]) != digest
        or json.loads(str(observed[0][2])) != body
    ):
        _fail(f"{decision['task_alias']} canonical validation result differs")


def _apply_orphan_recovery_plan(
    *, root: Path, target: Path, population: Mapping[str, Any], plan: Mapping[str, Any]
) -> list[dict[str, Any]]:
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (
        DatabaseCoordinator,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    outcomes: list[dict[str, Any]] = []
    with DatabaseTaskSource(
        target / "control.duckdb",
        owner_id="pctdd-descendant-source-g9:orphan-recovery-apply",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        for decision_value in plan["decisions"]:
            decision = dict(decision_value)
            alias = str(decision["task_alias"])
            target_status = str(decision["target_status"])
            task = source.get_task(alias)
            if task is None:
                _fail(f"{alias} disappeared during orphan recovery")
            control_receipt = {
                "schema": "pctdd/orphan-terminal-control-transition@1",
                "recovery_plan_id": plan["recovery_plan_id"],
                "task_alias": alias,
                "task_cid": decision["task_cid"],
                "blocked_revision": decision["blocked_revision"],
                "blocked_receipt": decision["blocked_receipt"],
                "evidence_digest": decision["evidence_digest"],
                "target_status": target_status,
                "operator_owned": True,
                "provider_dispatched": False,
            }
            lane = int(dict(decision["claim_binding"])["lane"])
            claim_record = dict(dict(decision["claim_binding"])["claim"])
            lane_path = target / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
            completion_body: dict[str, Any] | None = (
                _coordination_completion_body(decision, str(plan["recovery_plan_id"]))
                if target_status == "completed"
                else None
            )
            with DatabaseCoordinator(lane_path) as coordinator:
                claim = coordinator.get_task_claim(str(claim_record["claim_id"]))
                if claim is None or claim.to_dict() != claim_record:
                    _fail(f"{alias} terminal claim changed before recovery CAS")
                is_unapplied = (
                    task.status == "blocked"
                    and int(task.revision) == int(decision["blocked_revision"])
                )
                _ensure_validation_result(
                    source,
                    {**decision, "recovery_plan_id": plan["recovery_plan_id"]},
                    create=is_unapplied,
                )
                if is_unapplied:
                    current = source._intent.current_evidence_for_task(task.task_cid)
                    if not any(
                        item.get("evidence_kind")
                        in {"validation", ORPHAN_RECOVERY_EVIDENCE_KIND}
                        and item.get("digest") == decision["evidence_digest"]
                        for item in current
                    ):
                        source.record_evidence(
                            task_cid=task.task_cid,
                            evidence_kind=(
                                "validation" if target_status == "completed"
                                else ORPHAN_RECOVERY_EVIDENCE_KIND
                            ),
                            digest=str(decision["evidence_digest"]),
                            body=decision,
                        )

                    def control_cas() -> Any:
                        return source.compare_and_set_status(
                            task.task_cid,
                            expected_revision=int(task.revision),
                            status=target_status,
                            receipt=control_receipt,
                            evidence_digests=(
                                [str(decision["evidence_digest"])]
                                if target_status == "completed"
                                else None
                            ),
                        )

                    if target_status != "blocked":
                        coordinator.execute_with_terminal_task_claim_barrier(
                            claim, control_cas
                        )
                        task = source.get_task(alias)
                expected_revision = int(decision["blocked_revision"]) + (
                    0 if target_status == "blocked" else 1
                )
                expected_receipt = (
                    dict(decision["blocked_receipt"])
                    if target_status == "blocked"
                    else control_receipt
                )
                if (
                    task is None
                    or task.status != target_status
                    or int(task.revision) != expected_revision
                    or dict(task.body.get("completion_receipt") or {}) != expected_receipt
                ):
                    _fail(f"{alias} orphan recovery CAS did not commit exactly")
            for candidate_lane in range(4):
                candidate_path = (
                    target / "state" / f"lane-{candidate_lane}"
                    / "quack-lane-coordination.duckdb"
                )
                with DatabaseCoordinator(candidate_path) as coordinator:
                    row = coordinator._require().execute(
                        "SELECT ready FROM coordination_tasks WHERE task_cid = ?",
                        [task.task_cid],
                    ).fetchone()
                    if row is None:
                        _fail(f"{alias} is absent from coordination lane {candidate_lane}")
                    completion = coordinator._require().execute(
                        "SELECT status,body_json FROM task_completions "
                        "WHERE task_cid=?",
                        [task.task_cid],
                    ).fetchone()
                    if target_status == "completed":
                        assert completion_body is not None
                        if completion is None:
                            coordinator.mark_task_complete(
                                task.task_cid,
                                status="succeeded",
                                body=completion_body,
                            )
                            completion = coordinator._require().execute(
                                "SELECT status,body_json FROM task_completions "
                                "WHERE task_cid=?",
                                [task.task_cid],
                            ).fetchone()
                        if (
                            completion is None
                            or str(completion[0]) != "succeeded"
                            or json.loads(str(completion[1])) != completion_body
                            or coordinator.claimability(task.task_cid).get(
                                "completion_status"
                            ) != "succeeded"
                        ):
                            _fail(
                                f"{alias} completion differs in lane {candidate_lane}"
                            )
                    elif target_status == "retrying":
                        readiness = coordinator.claimability(task.task_cid)
                        if (
                            completion is not None
                            or coordinator.get_prepared_task_completion(task.task_cid)
                            is not None
                            or not bool(row[0])
                            or (
                                candidate_lane == lane
                                and not bool(readiness.get("claimable"))
                            )
                        ):
                            _fail(
                                f"{alias} retry is not freshly claimable in lane "
                                f"{candidate_lane}"
                            )
            outcomes.append(
                {
                    "task_alias": alias,
                    "task_cid": task.task_cid,
                    "status": target_status,
                    "revision": int(task.revision),
                    "lane": lane,
                    "coordination_lanes": list(range(4)),
                    "evidence_digest": decision["evidence_digest"],
                    "decision": decision,
                    "control_receipt": expected_receipt,
                    "coordination_completion": completion_body,
                }
            )
    return outcomes


def _recovery_receipt(
    *, root: Path, target: Path, population: Mapping[str, Any], policy: Mapping[str, Any],
    migration_receipt: Mapping[str, Any], plan: Mapping[str, Any], outcomes: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    g7._checkpoint_database(target / "control.duckdb")
    post = g7._control_projection(target / "control.duckdb")
    stores = []
    for relative in _store_relative_files():
        digest, size = g7._stable_file(target / relative, root=root, noun="recovered g9 store", required_links=None)
        stores.append({"path": relative.as_posix(), "sha256": digest, "size_bytes": size})
    body = {
        "schema": ORPHAN_RECOVERY_RECEIPT_SCHEMA,
        "source_binding": g7._source_binding(root, population),
        "capture_binding": _capture_binding(policy),
        "prior_store_generation": policy["prior_store_generation"],
        "target_store_generation": policy["target_store_generation"],
        "migration_receipt_cid": migration_receipt["receipt_cid"],
        "recovery_plan_id": plan["recovery_plan_id"],
        "candidate_task_aliases": list(ORPHAN_RECOVERY_ALIASES),
        "outcomes": [dict(item) for item in outcomes],
        "stores": stores,
        "recovery_event_watermark": post["event_watermark"],
        "recovery_event_prefix_digest": post["event_prefix_digest"],
        "one_shot": True,
    }
    return {**body, "recovery_receipt_cid": g7._identity(body)}


def _validate_recovery_receipt(
    receipt: Mapping[str, Any], *, root: Path, population: Mapping[str, Any],
    policy: Mapping[str, Any], migration_receipt: Mapping[str, Any]
) -> None:
    body = dict(receipt)
    cid = str(body.pop("recovery_receipt_cid", ""))
    if (
        receipt.get("schema") != ORPHAN_RECOVERY_RECEIPT_SCHEMA
        or cid != g7._identity(body)
        or receipt.get("source_binding") != g7._source_binding(root, population)
        or receipt.get("capture_binding") != _capture_binding(policy)
        or receipt.get("prior_store_generation") != policy["prior_store_generation"]
        or receipt.get("target_store_generation") != policy["target_store_generation"]
        or receipt.get("migration_receipt_cid") != migration_receipt["receipt_cid"]
        or receipt.get("candidate_task_aliases") != list(ORPHAN_RECOVERY_ALIASES)
        or receipt.get("one_shot") is not True
        or not isinstance(receipt.get("recovery_plan_id"), str)
        or not str(receipt.get("recovery_plan_id") or "")
        or type(receipt.get("recovery_event_watermark")) is not int
        or int(receipt.get("recovery_event_watermark") or 0)
        < int(migration_receipt["migration_event_watermark"])
        or not isinstance(receipt.get("recovery_event_prefix_digest"), str)
        or not isinstance(receipt.get("stores"), list)
    ):
        _fail("g9 orphan-terminal recovery receipt differs")


def _verify_recovery_outcomes(target: Path, receipt: Mapping[str, Any]) -> None:
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (
        DatabaseCoordinator,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    outcomes = receipt.get("outcomes")
    if not isinstance(outcomes, list) or [
        item.get("task_alias") for item in outcomes if isinstance(item, Mapping)
    ] != list(ORPHAN_RECOVERY_ALIASES):
        _fail("g9 orphan recovery outcome population differs")
    with DatabaseTaskSource(
        target / "control.duckdb",
        owner_id="pctdd-descendant-source-g9:orphan-recovery-verify",
        install_schema=False,
    ) as source:
        for raw in outcomes:
            outcome = dict(raw)
            task = source.get_task(str(outcome["task_alias"]))
            if (
                task is None
                or task.task_cid != outcome["task_cid"]
                or task.status != outcome["status"]
                or int(task.revision) != int(outcome["revision"])
                or dict(task.body.get("completion_receipt") or {})
                != dict(outcome.get("control_receipt") or {})
            ):
                _fail(f"{outcome['task_alias']} recovery outcome is not current")
            decision = outcome.get("decision")
            if not isinstance(decision, Mapping):
                _fail(f"{task.task_alias} recovery decision is absent")
            _ensure_validation_result(
                source,
                {
                    **dict(decision),
                    "recovery_plan_id": receipt["recovery_plan_id"],
                },
                create=False,
            )
            lanes = outcome.get("coordination_lanes")
            if lanes != list(range(4)):
                _fail(f"{task.task_alias} coordination lane population differs")
            for lane in lanes:
                with DatabaseCoordinator(
                    target / "state" / f"lane-{int(lane)}"
                    / "quack-lane-coordination.duckdb"
                ) as coordinator:
                    readiness = coordinator.claimability(task.task_cid)
                    if task.status == "completed":
                        if readiness.get("completion_status") != "succeeded":
                            _fail(f"{task.task_alias} coordination completion is absent")
                        row = coordinator._require().execute(
                            "SELECT status,body_json FROM task_completions "
                            "WHERE task_cid = ?",
                            [task.task_cid],
                        ).fetchone()
                        if (
                            row is None
                            or str(row[0]) != "succeeded"
                            or json.loads(str(row[1]))
                            != dict(outcome.get("coordination_completion") or {})
                        ):
                            _fail(
                                f"{task.task_alias} coordination completion body differs"
                            )
                    elif task.status == "retrying":
                        row = coordinator._require().execute(
                            "SELECT ready FROM coordination_tasks WHERE task_cid = ?",
                            [task.task_cid],
                        ).fetchone()
                        if (
                            readiness.get("completion_status")
                            or (
                                int(lane) == int(outcome["lane"])
                                and not readiness.get("claimable")
                            )
                            or row is None
                            or not bool(row[0])
                        ):
                            _fail(f"{task.task_alias} retry coordination is not clean")
                        if outcome.get("coordination_completion") is not None:
                            _fail(f"{task.task_alias} retry carries a completion body")
                    else:
                        _fail(f"{task.task_alias} recovery outcome status differs")


def _verify_recovery_authority(
    *, root: Path, target: Path, migration_receipt: Mapping[str, Any],
    recovery_receipt: Mapping[str, Any]
) -> None:
    records = {
        str(item.get("path") or ""): dict(item)
        for item in recovery_receipt.get("stores", ())
        if isinstance(item, Mapping)
    }
    expected_paths = {item.as_posix() for item in _store_relative_files()}
    if set(records) != expected_paths:
        _fail("g9 orphan recovery store receipt population differs")
    for relative in _store_relative_files():
        observed = g7._stable_file(
            target / relative,
            root=root,
            noun=f"recovered g9 {relative.as_posix()}",
            required_links=None,
        )
        record = records[relative.as_posix()]
        if observed != (str(record.get("sha256") or ""), int(record.get("size_bytes") or -1)):
            _fail(f"g9 orphan recovery store differs: {relative.as_posix()}")
    control = target / "control.duckdb"
    if _event_prefix(
        control, int(migration_receipt["migration_event_watermark"])
    ) != migration_receipt["migration_event_prefix_digest"]:
        _fail("g9 immutable migration event prefix differs after recovery")
    if _event_prefix(
        control, int(recovery_receipt["recovery_event_watermark"])
    ) != recovery_receipt["recovery_event_prefix_digest"]:
        _fail("g9 orphan recovery event prefix differs")
    try:
        _verify_recovery_outcomes(target, recovery_receipt)
    finally:
        g7._retire_private_stage_coordination_locks(target)


def _publish_recovery_receipt(*, root: Path, target: Path, receipt: Mapping[str, Any]) -> None:
    pending = target / ORPHAN_RECOVERY_PENDING
    marker = target / ORPHAN_RECOVERY_MARKER
    if not os.path.lexists(pending):
        g7._write_new_json(pending, receipt)
        g7._fsync_private_file(pending, noun="g9 orphan recovery receipt")
        g7._fsync_directory(target)
    if not os.path.lexists(marker):
        os.link(pending, marker, follow_symlinks=False)
        g7._fsync_directory(target)
    if os.path.lexists(pending):
        pending.unlink()
    prepared = target / ORPHAN_RECOVERY_PREPARED
    if os.path.lexists(prepared):
        prepared.unlink()
    g7._fsync_directory(target)


def recover_orphan_terminals(
    *, root: Path, config: Mapping[str, Any], population: Mapping[str, Any],
    validation_runner: Any | None = None
) -> dict[str, Any]:
    """Recover the closed g8 orphan-terminal set under the offline g9 fence."""

    root = root.resolve()
    policy = _policy(config)
    policy["repository_root"] = str(root)
    g7._assert_source_delta(root, population, policy)
    target = g7._confined(root, policy["target_runtime_root"], noun="g9 runtime root")
    migration_receipt = _load_initial_migration_receipt(
        root=root, target=target, population=population, policy=policy
    )
    marker = target / ORPHAN_RECOVERY_MARKER
    if os.path.lexists(marker):
        pending_path = target / ORPHAN_RECOVERY_PENDING
        pending_exists = os.path.lexists(pending_path)
        if pending_exists:
            marker_stat = os.stat(marker, follow_symlinks=False)
            pending_stat = os.stat(pending_path, follow_symlinks=False)
            if (
                (marker_stat.st_dev, marker_stat.st_ino)
                != (pending_stat.st_dev, pending_stat.st_ino)
                or marker_stat.st_nlink != 2
                or pending_stat.st_nlink != 2
            ):
                _fail("g9 orphan recovery marker/pending hardlink differs")
        receipt, _marker_identity = _load_marker_snapshot(
            root=root,
            path=marker,
            noun="g9 orphan recovery marker",
            required_links=2 if pending_exists else 1,
        )
        _validate_recovery_receipt(
            receipt, root=root, population=population, policy=policy,
            migration_receipt=migration_receipt,
        )
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
            offline_state_server_fence,
        )
        with offline_state_server_fence(
            database_path=target / "control.duckdb",
            connection_factory=lambda path: g7._open_local_database(path, read_only=True),
        ) as probe, _TransientRecoveryLockCleanup(target):
            g7._close_offline_fence_probe(probe)
            _verify_recovery_authority(
                root=root,
                target=target,
                migration_receipt=migration_receipt,
                recovery_receipt=receipt,
            )
            if pending_exists:
                pending_path.unlink()
            if os.path.lexists(target / ORPHAN_RECOVERY_PREPARED):
                (target / ORPHAN_RECOVERY_PREPARED).unlink()
            g7._fsync_directory(target)
        return {"schema": CHECK_SCHEMA, "valid": True, "mode": "recover-orphan-terminals", "replayed": True, "receipt": receipt}
    prepared_path = target / ORPHAN_RECOVERY_PREPARED
    if os.path.lexists(target / ORPHAN_RECOVERY_PENDING):
        receipt = g7._load_json(
            target / ORPHAN_RECOVERY_PENDING, root=root,
            noun="pending g9 orphan recovery receipt",
        )
        _validate_recovery_receipt(
            receipt, root=root, population=population, policy=policy,
            migration_receipt=migration_receipt,
        )
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
            offline_state_server_fence,
        )
        with offline_state_server_fence(
            database_path=target / "control.duckdb",
            connection_factory=lambda path: g7._open_local_database(path, read_only=True),
        ) as probe, _TransientRecoveryLockCleanup(target):
            g7._close_offline_fence_probe(probe)
            _verify_recovery_authority(
                root=root,
                target=target,
                migration_receipt=migration_receipt,
                recovery_receipt=receipt,
            )
            _publish_recovery_receipt(root=root, target=target, receipt=receipt)
        return {"schema": CHECK_SCHEMA, "valid": True, "mode": "recover-orphan-terminals", "replayed": True, "receipt": receipt}
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        offline_state_server_fence,
    )
    with offline_state_server_fence(
        database_path=target / "control.duckdb",
        connection_factory=lambda path: g7._open_local_database(path, read_only=True),
    ) as probe, _TransientRecoveryLockCleanup(target):
        g7._close_offline_fence_probe(probe)
        replaying_plan = os.path.lexists(prepared_path)
        if replaying_plan:
            plan = g7._load_json(prepared_path, root=root, noun="prepared g9 orphan recovery")
        else:
            for relative in _store_relative_files():
                _validate_store(root, target, relative, migration_receipt)
            plan = _prepare_orphan_recovery_plan(
                root=root, target=target, population=population, policy=policy,
                migration_receipt=migration_receipt, validation_runner=validation_runner,
            )
            g7._write_new_json(prepared_path, plan)
            g7._fsync_private_file(prepared_path, noun="prepared g9 orphan recovery")
            g7._fsync_directory(target)
        _validate_recovery_plan(
            plan, root=root, population=population, policy=policy,
            migration_receipt=migration_receipt,
        )
        _verify_prepared_recovery_progress(
            target=target, policy=policy, plan=plan
        )
        if replaying_plan:
            _revalidate_prepared_recovery_plan(
                root=root,
                target=target,
                population=population,
                policy=policy,
                plan=plan,
                validation_runner=validation_runner,
            )
        blocked = [
            str(item["task_alias"])
            for item in plan["decisions"]
            if item.get("target_status") == "blocked"
        ]
        if blocked:
            prepared_path.unlink(missing_ok=True)
            g7._fsync_directory(target)
            _fail(
                "g9 orphan recovery validation infrastructure is unavailable: "
                + ",".join(blocked)
            )
        g7._assert_source_delta(root, population, policy)
        outcomes = _apply_orphan_recovery_plan(
            root=root, target=target, population=population, plan=plan
        )
        _verify_prepared_recovery_progress(
            target=target, policy=policy, plan=plan
        )
        g7._retire_private_stage_coordination_locks(target)
        g7._assert_source_delta(root, population, policy)
        receipt = _recovery_receipt(
            root=root, target=target, population=population, policy=policy,
            migration_receipt=migration_receipt, plan=plan, outcomes=outcomes,
        )
        _publish_recovery_receipt(root=root, target=target, receipt=receipt)
    return {"schema": CHECK_SCHEMA, "valid": True, "mode": "recover-orphan-terminals", "replayed": False, "receipt": receipt}


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
        if (
            not os.path.lexists(target / ORPHAN_RECOVERY_MARKER)
            or os.path.lexists(target / ORPHAN_RECOVERY_PENDING)
            or os.path.lexists(target / ORPHAN_RECOVERY_PREPARED)
        ):
            recover_orphan_terminals(
                root=root, config=config, population=population
            )
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
            check_descendant_source(
                root=root, config=config, population=population, allow_progressed=False
            )
            recover_orphan_terminals(
                root=root, config=config, population=population
            )
            return check_descendant_source(
                root=root, config=config, population=population,
                allow_progressed=False,
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
        check_descendant_source(
            root=root, config=config, population=population,
            allow_progressed=False,
        )
        recovery = recover_orphan_terminals(
            root=root, config=config, population=population
        )
        return {
            "schema": CHECK_SCHEMA,
            "valid": True,
            "mode": "migrate-descendant-source",
            "migration_required": False,
            "receipt": receipt,
            "orphan_terminal_recovery": recovery,
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


def _live_g9_owner(
    *, root: Path, target: Path, policy: Mapping[str, Any],
    migration_receipt: Mapping[str, Any]
) -> dict[str, Any] | None:
    status_path = target / "quack-owner" / "quack-state-server.status.json"
    if not os.path.lexists(status_path):
        return None
    status = g7._load_json(status_path, root=root, noun="g9 Quack owner status")
    lifecycle = str(status.get("lifecycle") or "")
    if lifecycle == "stopped":
        return None
    if lifecycle != "ready" or not isinstance(status.get("identity"), Mapping):
        _fail("g9 Quack owner lifecycle is not safely inspectable")
    identity = dict(status["identity"])
    prior = dict(policy["stopped_predecessor_capture"]["prior_owner_identity"])
    endpoint = str(policy["target_quack_endpoint"])
    try:
        database_path = Path(str(status["database_path"])).resolve()
    except (KeyError, OSError, ValueError) as exc:
        _fail("g9 Quack owner database path is malformed", exc)
    if (
        status.get("interface") != "QuackStateServer@1"
        or identity.get("interface") != "StateServerIdentity@1"
        or identity.get("status") != "ready"
        or identity.get("listen_uri") != endpoint
        or status.get("store_id")
        != str((target / "control.duckdb").relative_to(root))
        or identity.get("store_id") != status.get("store_id")
        or identity.get("database_uuid") != prior["database_uuid"]
        or identity.get("extension_fingerprint")
        != prior.get("extension_fingerprint")
        or status.get("extension_fingerprint")
        != prior.get("extension_fingerprint")
        or database_path != (target / "control.duckdb").resolve()
        or int(status.get("port") or 0) != int(endpoint.rsplit(":", 1)[1])
        or int(identity.get("generation") or 0) <= int(prior["generation"])
        or int(identity.get("fence_epoch") or 0)
        != int(identity.get("generation") or 0)
        or migration_receipt.get("target_store_generation")
        != policy["target_store_generation"]
    ):
        _fail("live g9 Quack owner is not the exact successor")
    return status


def _verify_descendant_target(
    *, root: Path, target: Path, control_target: Path | str,
    population: Mapping[str, Any], policy: Mapping[str, Any],
    receipt: Mapping[str, Any], recovery_receipt: Mapping[str, Any] | None,
    live_owner: Mapping[str, Any] | None, allow_progressed: bool
) -> dict[str, Any]:
    post = g7._control_projection(control_target)
    if _task_aliases(post) != EXPECTED_ALIASES:
        _fail("g9 target does not retain canonical tasks")
    captured = dict(policy["stopped_predecessor_capture"]["prior_control_projection"])
    if post.get("task_definition_digest") != captured.get("task_definition_digest"):
        _fail("g9 current task definitions differ from the stopped authority")
    if _event_prefix(
        control_target, int(receipt["migration_event_watermark"])
    ) != receipt["migration_event_prefix_digest"]:
        _fail("g9 immutable migration event prefix differs")
    if recovery_receipt is None:
        if allow_progressed:
            _fail("g9 progressed verification lacks the required recovery suffix")
        if post["event_prefix_digest"] != receipt["migration_event_prefix_digest"]:
            _fail("g9 target progressed before initial verification")
    elif _event_prefix(
        control_target, int(recovery_receipt["recovery_event_watermark"])
    ) != recovery_receipt["recovery_event_prefix_digest"]:
        _fail("g9 orphan recovery event prefix differs")
    if not allow_progressed:
        if live_owner is not None or not isinstance(control_target, Path):
            _fail("strict g9 verification requires the offline owner fence")
        if recovery_receipt is None:
            for relative in _store_relative_files():
                _validate_store(root, target, relative, receipt)
        else:
            _verify_recovery_authority(
                root=root,
                target=target,
                migration_receipt=receipt,
                recovery_receipt=recovery_receipt,
            )
        _validate_owner_lock(target)
        expected = set(_store_relative_files()) | {
            Path(MIGRATION_MARKER), _owner_lock_relative()
        }
        if recovery_receipt is not None:
            expected.add(Path(ORPHAN_RECOVERY_MARKER))
        if _stage_files(target) != expected:
            _fail("g9 strict descendant-source population differs")
    if live_owner is not None:
        latest = g7._latest_state_server(control_target)
        identity = dict(live_owner["identity"])
        for field in (
            "server_id", "store_id", "database_uuid", "process_birth_id",
            "listen_uri", "extension_fingerprint", "schema_revision",
            "generation", "started_at", "status",
        ):
            expected_value = identity[field]
            if field in {"schema_revision", "generation"}:
                expected_value = int(expected_value)
            if latest[field] != expected_value:
                _fail(f"live g9 transport identity differs: {field}")
        if latest["stopped_at"] is not None or latest["status"] != "ready":
            _fail("live g9 transport is not ready")
    return {
        "schema": CHECK_SCHEMA,
        "valid": True,
        "mode": "check-descendant-source-migration",
        "allow_progressed": bool(allow_progressed),
        "verification_transport": "quack" if live_owner is not None else "offline",
        "receipt": dict(receipt),
        "orphan_terminal_recovery_receipt": (
            None if recovery_receipt is None else dict(recovery_receipt)
        ),
        "task_count": 54,
        "generated_guardrail_task_rows": 0,
    }


def check_descendant_source(
    *, root: Path, config: Mapping[str, Any], population: Mapping[str, Any],
    allow_progressed: bool
) -> dict[str, Any]:
    """Verify immutable g9 prefixes without opening a live Quack database."""

    root = root.resolve()
    policy = _policy(config)
    policy["repository_root"] = str(root)
    g7._assert_source_delta(root, population, policy)
    target = g7._confined(root, policy["target_runtime_root"], noun="g9 runtime root")
    marker = target / MIGRATION_MARKER
    if not marker.is_file() or marker.is_symlink():
        _fail("g9 migration marker is absent")
    receipt, marker_identity = _load_marker_snapshot(
        root=root, path=marker, noun="g9 migration marker"
    )
    _validate_receipt(receipt, root=root, population=population, policy=policy)
    recovery_marker = target / ORPHAN_RECOVERY_MARKER
    recovery_receipt: dict[str, Any] | None = None
    recovery_identity: tuple[int, ...] | None = None
    if recovery_marker.is_file() and not recovery_marker.is_symlink():
        recovery_receipt, recovery_identity = _load_marker_snapshot(
            root=root,
            path=recovery_marker,
            noun="g9 orphan recovery marker",
        )
        _validate_recovery_receipt(
            recovery_receipt,
            root=root,
            population=population,
            policy=policy,
            migration_receipt=receipt,
        )
    if os.path.lexists(target / PENDING_MARKER) or os.path.lexists(
        target / PREPARED_RECEIPT
    ):
        _fail("g9 publication remains incomplete")
    if os.path.lexists(target / ORPHAN_RECOVERY_PENDING) or os.path.lexists(
        target / ORPHAN_RECOVERY_PREPARED
    ):
        _fail("g9 orphan-terminal recovery remains incomplete")
    live_owner = _live_g9_owner(
        root=root, target=target, policy=policy, migration_receipt=receipt
    )
    if live_owner is not None and not allow_progressed:
        _fail("strict g9 verification cannot inspect a live owner")
    if live_owner is None:
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
            offline_state_server_fence,
        )

        try:
            with offline_state_server_fence(
                database_path=target / "control.duckdb",
                connection_factory=lambda path: g7._open_local_database(
                    path, read_only=True
                ),
            ) as probe:
                g7._close_offline_fence_probe(probe)
                fenced_receipt, fenced_marker_identity = _load_marker_snapshot(
                    root=root,
                    path=marker,
                    noun="fenced g9 migration marker",
                )
                if (
                    fenced_receipt != receipt
                    or fenced_marker_identity != marker_identity
                ):
                    _fail("g9 migration marker changed before fenced inspection")
                if recovery_receipt is not None:
                    fenced_recovery, fenced_recovery_identity = _load_marker_snapshot(
                        root=root,
                        path=recovery_marker,
                        noun="fenced g9 orphan recovery marker",
                    )
                    if (
                        fenced_recovery != recovery_receipt
                        or fenced_recovery_identity != recovery_identity
                    ):
                        _fail(
                            "g9 orphan recovery marker changed before fenced inspection"
                        )
                result = _verify_descendant_target(
                    root=root,
                    target=target,
                    control_target=target / "control.duckdb",
                    population=population,
                    policy=policy,
                    receipt=receipt,
                    recovery_receipt=recovery_receipt,
                    live_owner=None,
                    allow_progressed=allow_progressed,
                )
        except DescendantSourceSuccessorError:
            raise
        except Exception as exc:
            _fail("g9 offline authority could not be fenced", exc)
    else:
        result = _verify_descendant_target(
            root=root,
            target=target,
            control_target=str(policy["target_quack_endpoint"]),
            population=population,
            policy=policy,
            receipt=receipt,
            recovery_receipt=recovery_receipt,
            live_owner=live_owner,
            allow_progressed=allow_progressed,
        )
    final_receipt, final_marker_identity = _load_marker_snapshot(
        root=root, path=marker, noun="final g9 migration marker"
    )
    final_recovery: dict[str, Any] | None = None
    final_recovery_identity: tuple[int, ...] | None = None
    if recovery_receipt is not None:
        final_recovery, final_recovery_identity = _load_marker_snapshot(
            root=root,
            path=recovery_marker,
            noun="final g9 orphan recovery marker",
        )
    if (
        final_receipt != receipt
        or final_marker_identity != marker_identity
        or final_recovery != recovery_receipt
        or final_recovery_identity != recovery_identity
    ):
        _fail("g9 immutable migration markers changed during verification")
    g7._assert_source_delta(root, population, policy)
    return result


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
    parser.add_argument(
        "command",
        choices=("migrate", "check", "check-policy", "recover-orphan-terminals"),
    )
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
    elif arguments.command == "recover-orphan-terminals":
        result = recover_orphan_terminals(
            root=root, config=config, population=population
        )
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
    "ORPHAN_RECOVERY_MARKER",
    "ORPHAN_RECOVERY_POLICY_SCHEMA",
    "ORPHAN_RECOVERY_RECEIPT_SCHEMA",
    "RECEIPT_SCHEMA",
    "capture_stopped_descendant_authority",
    "check_descendant_source",
    "migrate_descendant_source",
    "recover_orphan_terminals",
    "validate_pending_policy",
)


if __name__ == "__main__":
    raise SystemExit(main())
