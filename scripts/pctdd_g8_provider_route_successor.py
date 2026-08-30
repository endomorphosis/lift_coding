#!/usr/bin/env python3
"""Crash-safe PCTDD g7 -> g8 source/provider-route successor.

This is an operator-only adapter over the existing PCTDD DuckDB/Quack task
authority, coordination databases, canonical ordered provider router, and the
g7 migration primitives.  It never decides that a provider fallback may run.
It only binds the reviewed ``grok-4.6 -> Codex gpt-5.6-terra`` quota/medium
route into the accepted plan and re-arms two *exact*, independently evidenced
pre-effect attempts in a fresh runtime generation.

The adapter may run only after the exact g7 Quack owner is stopped.  It copies
the stopped control database and four coordination histories into a private
stage, appends one plan revision and one operator evidence node, expires the
two exact coordination claims, and publishes the five stores atomically.  A
receipt marker is linked last.  Execution observations, provider-attempt
stores, DuckLake/read replicas, logs, owner state, worktrees, and merge state
are verified as inputs where configured but are never copied.

The typed Grok 402 observation is candidate evidence that the predecessor
attempt ended before provider/effect authority.  It is deliberately not an
authorization to dispatch Codex.  Runtime fallback continues to require the
existing router-owned nonce-bound preflight, independent quota evidence, and
``DurableProviderAttemptCAS`` transition.
"""

from __future__ import annotations

import argparse
import fcntl
import importlib
import json
import os
import shutil
import stat
import tempfile
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

try:
    g7 = importlib.import_module("pctdd_g7_source_binding_successor")
except ModuleNotFoundError:
    g7 = importlib.import_module("scripts.pctdd_g7_source_binding_successor")


MIGRATION_SCHEMA: Final[str] = (
    "pctdd/source-provider-route-successor-materialization@1"
)
EVIDENCE_SCHEMA: Final[str] = (
    "pctdd/operator-control-plane-source-provider-route-migration@1"
)
RECEIPT_SCHEMA: Final[str] = (
    "pctdd/source-provider-route-migration-receipt@1"
)
CHECK_SCHEMA: Final[str] = (
    "pctdd/source-provider-route-migration-check@1"
)
PRE_EFFECT_SCHEMA: Final[str] = (
    "pctdd/pre-effect-provider-capacity-evidence@1"
)
MIGRATION_EVIDENCE_KIND: Final[str] = (
    "operator_control_plane_source_provider_route_migration"
)
MIGRATION_MARKER: Final[str] = "source-provider-route-migration-receipt.json"
PENDING_MARKER: Final[str] = (
    ".source-provider-route-migration-receipt.pending.json"
)
PREPARED_RECEIPT: Final[str] = (
    ".source-provider-route-migration-prepared-receipt.json"
)
PREPARED_STAGE_PREFIX: Final[str] = ".pctdd-g8-prepared."
LOCK_NAME: Final[str] = ".pctdd-g8-provider-route-migration.lock"
DATABASE_RETRY_BUDGET_SCHEMA: Final[str] = (
    "ipfs_accelerate_py/agent-supervisor/database-retry-budget@1"
)
MAX_UNKNOWN_OUTCOME_REARMS: Final[int] = 3
EXPECTED_TASK_ALIASES: Final[tuple[str, str]] = ("PCTDD-001", "PCTDD-029")
EXPECTED_ROUTE: Final[dict[str, str]] = {
    "primary_provider_id": "grok_cli",
    "primary_model_id": "grok-4.6",
    "fallback_provider_id": "codex",
    "fallback_model_id": "gpt-5.6-terra",
    "fallback_trigger": "primary_quota_exhausted",
    "fallback_reasoning_effort": "medium",
}
COMPLETED_TASK_STATUSES: Final[frozenset[str]] = frozenset(
    {"completed", "skipped", "complete", "done"}
)


class ProviderRouteSuccessorError(RuntimeError):
    """The g8 successor cannot be proven safe from sealed current evidence."""


def _fail(message: str, exc: BaseException | None = None) -> None:
    error = ProviderRouteSuccessorError(message)
    if exc is None:
        raise error
    raise error from exc


def _route_binding(provider: Mapping[str, Any]) -> dict[str, Any]:
    """Resolve the exact tuple through the existing router authority."""

    from ipfs_accelerate_py.llm_router import (
        resolve_agent_implementation_route,
    )

    if provider.get("implementation_fallback_authorized") is not True:
        _fail("g8 provider fallback is not explicitly operator-authorized")
    values = {field: str(provider.get(field) or "") for field in EXPECTED_ROUTE}
    if values != EXPECTED_ROUTE:
        _fail("g8 provider route is not the reviewed quota/medium tuple")
    if "provider_id" in provider or "model_id" in provider:
        _fail("g8 ordered provider route is mixed with legacy provider fields")
    try:
        route = resolve_agent_implementation_route(**values)
    except ValueError as exc:
        _fail("canonical router rejected the g8 provider route", exc)
    if route.authorization is not None or route.as_dict() != EXPECTED_ROUTE:
        _fail("canonical router returned a different g8 route")
    binding = route.as_binding_dict()
    if (
        binding.get("authorization") is not None
        or binding.get("invocation_binding") is not None
        or binding.get("fallback_implementer_identity") != "codex"
        or not str(binding.get("route_id") or "")
    ):
        _fail("g8 route binding exceeds the reviewed legacy quota authority")
    return binding


def _validate_pre_effect_evidence(
    settlement: Mapping[str, Any],
) -> dict[str, Any]:
    raw = settlement.get("pre_effect_evidence")
    if not isinstance(raw, Mapping):
        _fail("g8 settlement lacks pre-effect evidence")
    evidence = dict(raw)
    evidence_cid = str(evidence.pop("evidence_cid", ""))
    if evidence_cid != g7._identity(evidence):
        _fail("g8 pre-effect evidence identity differs")
    expected = {
        "schema",
        "task_alias",
        "task_cid",
        "attempt_id",
        "claim_id",
        "provider_id",
        "model_id",
        "failure_class",
        "http_status",
        "supervisor_outcome",
        "provider_effect_committed",
        "fallback_dispatched",
        "workspace_mutated",
        "durable_provider_attempt_state",
        "evidence_source",
        "source_artifact_path",
        "source_artifact_sha256",
        "source_artifact_size_bytes",
    }
    if set(evidence) != expected:
        _fail("g8 pre-effect evidence fields differ")
    if (
        evidence["schema"] != PRE_EFFECT_SCHEMA
        or evidence["task_alias"] != settlement.get("task_alias")
        or evidence["task_cid"] != settlement.get("task_cid")
        or evidence["attempt_id"] != settlement.get("attempt_id")
        or evidence["claim_id"] != settlement.get("claim_id")
        or evidence["provider_id"] != "grok_cli"
        or evidence["model_id"] != "grok-4.6"
        or evidence["failure_class"] != "hard_quota_exhausted"
        or evidence["http_status"] != 402
        or evidence["supervisor_outcome"] != "provider_capacity_backoff"
        or evidence["provider_effect_committed"] is not False
        or evidence["fallback_dispatched"] is not False
        or evidence["workspace_mutated"] is not False
        or evidence["durable_provider_attempt_state"] not in {"absent", "reserved"}
        or evidence["evidence_source"]
        not in {
            "operator_sealed_grok_quota_receipt",
            "operator_sealed_provider_capacity_receipt",
            "operator_sealed_grok_quota_log",
        }
        or evidence["source_artifact_path"]
        != settlement.get("pre_effect_log", {}).get("path")
        or evidence["source_artifact_sha256"]
        != settlement.get("pre_effect_log", {}).get("sha256")
        or evidence["source_artifact_size_bytes"]
        != settlement.get("pre_effect_log", {}).get("size_bytes")
    ):
        _fail("g8 pre-effect evidence exceeds the exact Grok 402 claim")
    return {**evidence, "evidence_cid": evidence_cid}


def _validate_retry_budget(settlement: Mapping[str, Any]) -> dict[str, int]:
    raw = settlement.get("retry_budget")
    if not isinstance(raw, Mapping) or set(raw) != {
        "prior_attempts_used",
        "target_attempts_used",
        "max_task_attempts",
        "prior_unknown_outcome_rearm_count",
        "target_unknown_outcome_rearm_count",
    }:
        _fail("g8 settlement retry budget is incomplete")
    values: dict[str, int] = {}
    for field, value in raw.items():
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _fail(f"g8 retry budget {field} is malformed")
        values[str(field)] = value
    if (
        values["prior_attempts_used"] < 1
        or values["target_attempts_used"] != 0
        or values["max_task_attempts"] != 2
        or values["target_unknown_outcome_rearm_count"]
        != values["prior_unknown_outcome_rearm_count"] + 1
        or values["target_unknown_outcome_rearm_count"]
        > MAX_UNKNOWN_OUTCOME_REARMS
    ):
        _fail("g8 retry budget does not encode one bounded pre-effect rearm")
    return values


def _validate_prior_blocked_receipt(
    settlement: Mapping[str, Any], actual: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    raw = settlement.get("prior_completion_receipt")
    if not isinstance(raw, Mapping):
        _fail("g8 settlement lacks the exact stopped completion receipt")
    receipt = dict(raw)
    if settlement.get("prior_completion_receipt_cid") != g7._identity(receipt):
        _fail("g8 stopped completion receipt identity differs")
    if actual is not None and dict(actual) != receipt:
        _fail("g8 task does not retain the sealed stopped completion receipt")
    operation = str(receipt.get("operation") or receipt.get("reason") or "")
    budget = _validate_retry_budget(settlement)
    if (
        operation != "database_unknown_outcome_blocked"
        or receipt.get("forced_block") is not True
        or receipt.get("retry_exhausted") is not True
        or int(receipt.get("attempts_used") or -1)
        != budget["prior_attempts_used"]
        or int(receipt.get("max_task_attempts") or -1)
        != budget["max_task_attempts"]
        or int(receipt.get("unknown_outcome_rearm_count") or -1)
        != budget["prior_unknown_outcome_rearm_count"]
    ):
        _fail("g8 predecessor receipt is not the exact forced unknown-outcome block")
    for field in (
        "task_cid",
        "attempt_id",
        "claim_id",
        "lease_id",
        "owner_session_id",
        "fencing_token",
        "fence_epoch",
    ):
        if receipt.get(field) != settlement.get(field):
            _fail(f"g8 stopped completion receipt differs: {field}")
    return receipt


def _policy(config: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    raw = config.get("source_provider_route_successor_materialization")
    if not isinstance(raw, Mapping):
        _fail("scheduler lacks a g8 source/provider-route successor policy")
    policy = dict(raw)
    if (
        policy.get("schema") != MIGRATION_SCHEMA
        or policy.get("migration_revision") != "PCTDD-SOURCE-PROVIDER-G8"
        or policy.get("prior_store_generation") != "pctdd-v1-g7"
        or policy.get("target_store_generation") != "pctdd-v1-g8"
        or policy.get("target_quack_endpoint") != "quack:127.0.0.1:27278"
        or policy.get("receipt_marker") != MIGRATION_MARKER
    ):
        _fail("g8 source/provider-route policy identity differs")
    provider = policy.get("provider_route")
    if not isinstance(provider, Mapping):
        _fail("g8 provider route policy is absent")
    route_binding = _route_binding(provider)
    expected_route_cid = str(policy.get("provider_route_binding_cid") or "")
    if expected_route_cid != g7._identity(route_binding):
        _fail("g8 provider route binding CID differs")
    coordination = policy.get("coordination_stores")
    if (
        not isinstance(coordination, list)
        or [item.get("lane") for item in coordination if isinstance(item, Mapping)]
        != [0, 1, 2, 3]
    ):
        _fail("g8 policy must name four ordered coordination stores")
    settlements = policy.get("settlements")
    if (
        not isinstance(settlements, list)
        or tuple(
            str(item.get("task_alias") or "")
            for item in settlements
            if isinstance(item, Mapping)
        )
        != EXPECTED_TASK_ALIASES
        or len(settlements) != 2
    ):
        _fail("g8 policy must settle exactly PCTDD-001 and PCTDD-029")
    lanes: list[int] = []
    for item in settlements:
        if not isinstance(item, Mapping):
            _fail("g8 settlement is malformed")
        required = (
            "task_alias",
            "task_cid",
            "control_revision",
            "lane",
            "claim_id",
            "attempt_id",
            "lease_id",
            "owner_session_id",
            "fencing_token",
            "fence_epoch",
            "prior_task_status",
            "target_task_status",
            "coordination_action",
            "prior_claim_state",
            "prior_attempt_status",
            "target_claim_state",
            "target_attempt_status",
            "coordination_projection_root",
            "prior_completion_receipt_cid",
            "pre_effect_log",
        )
        if any(not str(item.get(field) or "") for field in required if field != "lane"):
            _fail(f"{item.get('task_alias')} settlement identity is incomplete")
        lane = item.get("lane")
        if isinstance(lane, bool) or not isinstance(lane, int) or lane not in range(4):
            _fail("g8 settlement lane is malformed")
        lanes.append(lane)
        prior_completion = item.get("prior_completion_receipt")
        pre_effect_log = item.get("pre_effect_log")
        if (
            item.get("prior_task_status") != "blocked"
            or item.get("target_task_status") != "todo"
            or item.get("coordination_action")
            not in {"expire_exact_active_claim", "preserve_exact_terminal_claim"}
            or item.get("prior_claim_state") not in {"accepted", "released"}
            or item.get("prior_attempt_status") not in {"running", "released"}
            or item.get("target_claim_state") not in {"expired", "released"}
            or item.get("target_attempt_status") not in {"expired", "released"}
            or (
                item.get("coordination_action") == "expire_exact_active_claim"
                and (
                    item.get("prior_claim_state") != "accepted"
                    or item.get("prior_attempt_status") != "running"
                    or item.get("target_claim_state") != "expired"
                    or item.get("target_attempt_status") != "expired"
                )
            )
            or (
                item.get("coordination_action") == "preserve_exact_terminal_claim"
                and (
                    item.get("prior_claim_state") != "released"
                    or item.get("prior_attempt_status") != "released"
                    or item.get("target_claim_state") != "released"
                    or item.get("target_attempt_status") != "released"
                )
            )
            or not isinstance(prior_completion, Mapping)
            or not isinstance(pre_effect_log, Mapping)
            or set(pre_effect_log) != {"path", "sha256", "size_bytes"}
            or item.get("prior_completion_receipt_cid")
            != g7._identity(prior_completion)
        ):
            _fail("g8 settlement is not the exact stopped blocked predecessor")
        _validate_pre_effect_evidence(item)
        _validate_retry_budget(item)
        _validate_prior_blocked_receipt(item)
    if len(set(lanes)) != 2:
        _fail("g8 stranded attempts do not have distinct lane owners")
    revisions = policy.get("provider_role_revisions")
    if not isinstance(revisions, list) or not revisions:
        _fail("g8 policy lacks sealed incomplete-task provider revisions")
    aliases: list[str] = []
    for revision in revisions:
        if not isinstance(revision, Mapping):
            _fail("g8 provider-role revision is malformed")
        required = {
            "task_alias",
            "task_cid",
            "prior_status",
            "prior_revision",
            "target_revision",
            "prior_definition_cid",
            "target_definition_cid",
            "prior_provider_role",
            "target_provider_role",
        }
        if set(revision) != required:
            _fail("g8 provider-role revision fields differ")
        alias = str(revision.get("task_alias") or "")
        if (
            not alias.startswith("PCTDD-")
            or revision.get("prior_provider_role") != "grok-only"
            or revision.get("target_provider_role") != "grok-implement"
            or revision.get("prior_status") in COMPLETED_TASK_STATUSES
            or int(revision.get("prior_revision") or 0) < 1
            or int(revision.get("target_revision") or 0)
            != int(revision.get("prior_revision") or 0)
            + (2 if alias in EXPECTED_TASK_ALIASES else 1)
        ):
            _fail("g8 provider-role revision is outside the reviewed delta")
        aliases.append(alias)
    if aliases != sorted(set(aliases)) or "PCTDD-000" in aliases:
        _fail("g8 provider-role revisions are not a unique ordered task set")
    target = policy.get("target_control_projection")
    if not isinstance(target, Mapping):
        _fail("g8 target control projection is absent")
    if dict(target.get("task_revisions") or {}) != {
        str(item["task_alias"]): int(item["target_revision"])
        for item in revisions
    }:
        _fail("g8 target task revisions differ from the sealed role delta")
    copy_policy = policy.get("copy_policy")
    required_not_copied = {
        "execution_observation",
        "provider_attempt_store",
        "ducklake",
        "read_replica",
        "logs",
        "owner_runtime",
        "worktrees",
        "merge_state",
    }
    if (
        not isinstance(copy_policy, Mapping)
        or set(copy_policy.get("not_copied") or ()) != required_not_copied
    ):
        _fail("g8 copy policy does not exclude every execution/runtime sidecar")
    return policy, route_binding


def _definition_projection(task: Mapping[str, Any]) -> dict[str, Any]:
    """Return the full immutable task definition, excluding runtime receipt."""

    body = dict(task.get("body") or {})
    body.pop("completion_receipt", None)
    return {
        "task_cid": str(task["task_cid"]),
        "task_alias": str(task["task_alias"]),
        "goal_cid": str(task["goal_cid"]),
        "plan_cid": str(task.get("plan_cid") or ""),
        "objective_id": str(task.get("objective_id") or ""),
        "ordinal": int(task["ordinal"]),
        "priority": str(task.get("priority") or ""),
        "identity": dict(task.get("identity") or {}),
        "body": body,
        "dependencies": list(task.get("dependencies") or ()),
        "outputs": [dict(item) for item in task.get("outputs") or ()],
        "acceptance": [dict(item) for item in task.get("acceptance") or ()],
        "validations": [dict(item) for item in task.get("validations") or ()],
    }


def _definition_cid(task: Mapping[str, Any]) -> str:
    return g7._identity(_definition_projection(task))


def _role_delta_body(body: Mapping[str, Any]) -> dict[str, Any]:
    updated = dict(body)
    if updated.get("provider_role") != "grok-only":
        _fail("incomplete task does not have the sealed grok-only provider role")
    updated["provider_role"] = "grok-implement"
    return updated


def _task_projection(source: Any) -> dict[str, dict[str, Any]]:
    rows = source.intent.list_tasks(limit=256)
    return {str(row["task_alias"]): dict(row) for row in rows}


def _control_tasks_from_connection(connection: Any) -> dict[str, dict[str, Any]]:
    rows = connection.execute(
        "SELECT task_cid,task_alias,goal_cid,plan_cid,objective_id,ordinal,"
        "status,revision,priority,identity_json,body_json FROM tasks "
        "ORDER BY task_alias"
    ).fetchall()
    tasks: dict[str, dict[str, Any]] = {}
    for row in rows:
        task_cid = str(row[0])
        tasks[str(row[1])] = {
            "task_cid": task_cid,
            "task_alias": str(row[1]),
            "goal_cid": str(row[2]),
            "plan_cid": str(row[3] or ""),
            "objective_id": str(row[4] or ""),
            "ordinal": int(row[5]),
            "status": str(row[6]),
            "revision": int(row[7]),
            "priority": str(row[8] or ""),
            "identity": json.loads(str(row[9])),
            "body": json.loads(str(row[10])),
            "dependencies": [
                str(item[0])
                for item in connection.execute(
                    "SELECT dependency_task_cid FROM task_dependencies "
                    "WHERE task_cid=? ORDER BY dependency_task_cid",
                    [task_cid],
                ).fetchall()
            ],
            "outputs": [
                {
                    "ordinal": int(item[0]),
                    "path": str(item[1]),
                    "effect": json.loads(str(item[2])),
                }
                for item in connection.execute(
                    "SELECT ordinal,path,effect_json FROM task_outputs "
                    "WHERE task_cid=? ORDER BY ordinal",
                    [task_cid],
                ).fetchall()
            ],
            "acceptance": [
                {
                    "ordinal": int(item[0]),
                    "criterion": str(item[1]),
                    "evidence_policy": json.loads(str(item[2])),
                }
                for item in connection.execute(
                    "SELECT ordinal,criterion,evidence_policy_json "
                    "FROM task_acceptance WHERE task_cid=? ORDER BY ordinal",
                    [task_cid],
                ).fetchall()
            ],
            "validations": [
                {
                    "ordinal": int(item[0]),
                    "argv": json.loads(str(item[1])),
                    "policy": json.loads(str(item[2])),
                }
                for item in connection.execute(
                    "SELECT ordinal,argv_json,policy_json FROM task_validations "
                    "WHERE task_cid=? ORDER BY ordinal",
                    [task_cid],
                ).fetchall()
            ],
        }
    return tasks


def _ready_aliases(tasks: Mapping[str, Mapping[str, Any]]) -> list[str]:
    completed_cids = {
        str(task["task_cid"])
        for task in tasks.values()
        if str(task["status"]) in COMPLETED_TASK_STATUSES
    }
    return [
        alias
        for alias, task in sorted(
            tasks.items(), key=lambda item: (int(item[1]["ordinal"]), item[0])
        )
        if str(task["status"])
        in {
            "proposed",
            "admitted",
            "pending",
            "ready",
            "todo",
            "queued",
            "retrying",
        }
        and set(task.get("dependencies") or ()).issubset(completed_cids)
    ]


def _validate_role_revision_population(
    source: Any,
    policy: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    tasks = _task_projection(source)
    incomplete = sorted(
        alias
        for alias, task in tasks.items()
        if str(task["status"]) not in COMPLETED_TASK_STATUSES
    )
    revisions = [dict(item) for item in policy["provider_role_revisions"]]
    if [item["task_alias"] for item in revisions] != incomplete:
        _fail("g8 provider revisions do not cover every and only incomplete task")
    for record in revisions:
        task = tasks[str(record["task_alias"])]
        body = dict(task["body"])
        target_task = {**task, "body": _role_delta_body(body)}
        if (
            task["task_cid"] != record["task_cid"]
            or task["status"] != record["prior_status"]
            or int(task["revision"]) != int(record["prior_revision"])
            or _definition_cid(task) != record["prior_definition_cid"]
            or _definition_cid(target_task) != record["target_definition_cid"]
        ):
            _fail(f"{record['task_alias']} sealed provider revision differs")
    return tasks, revisions


def _assert_private_stopped_owner(
    *,
    root: Path,
    policy: Mapping[str, Any],
    control: Path,
    status_path: Path,
    connection: Any,
) -> dict[str, Any]:
    status = g7._load_json(status_path, root=root, noun="stopped g7 Quack status")
    identity = status.get("identity")
    expected = dict(policy["prior_owner_identity"])
    latest = g7._latest_state_server_from_connection(connection)
    row_fields = (
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
    identity_fields = (
        "server_id",
        "store_id",
        "database_uuid",
        "process_birth_id",
        "listen_uri",
        "extension_fingerprint",
        "schema_revision",
        "generation",
        "started_at",
        "status",
    )
    if (
        status.get("interface") != "QuackStateServer@1"
        or status.get("lifecycle") != "stopped"
        or not isinstance(identity, Mapping)
        or any(field not in expected for field in (*row_fields, "fence_epoch"))
        or latest != {field: expected[field] for field in row_fields}
        or any(identity.get(field) != expected[field] for field in identity_fields)
        or int(identity.get("fence_epoch") or 0) != int(expected["fence_epoch"])
        or latest["status"] != "stopped"
        or not str(latest["stopped_at"] or "")
        or Path(str(status.get("database_path") or "")).resolve()
        != control.resolve()
    ):
        _fail("stopped g7 Quack identity differs")
    owner_dir = status_path.parent
    forbidden = (
        control.with_name(f".{control.name}.state-owner.json"),
        owner_dir / "quack-state-server.pid",
        owner_dir / "quack-state-server.owner.json",
        owner_dir / "quack-state-server.stop",
    )
    if any(os.path.lexists(path) for path in forbidden) or tuple(
        owner_dir.glob("*.quack-token")
    ):
        _fail("stopped g7 owner retains live authority artifacts")
    g7._assert_listener_stopped(policy)
    return latest


def _table_names(connection: Any) -> set[str]:
    return {str(row[0]) for row in connection.execute("SHOW TABLES").fetchall()}


def _attempt_rows(
    connection: Any,
    table: str,
    settlement: Mapping[str, Any],
) -> list[tuple[Any, ...]]:
    columns = [
        str(row[0])
        for row in connection.execute(f"DESCRIBE SELECT * FROM {table}").fetchall()
    ]
    if "attempt_id" in columns:
        return connection.execute(
            f"SELECT * FROM {table} WHERE attempt_id=?",
            [settlement["attempt_id"]],
        ).fetchall()
    if "task_cid" in columns:
        return connection.execute(
            f"SELECT * FROM {table} WHERE task_cid=?",
            [settlement["task_cid"]],
        ).fetchall()
    return []


def _assert_pre_effect_attempts(
    databases: Sequence[tuple[str, Path]],
    settlements: Sequence[Mapping[str, Any]],
) -> None:
    """Prove the old claims stopped before any provider/effect authority."""

    forbidden_tables = (
        "provider_invocations",
        "provider_calls",
        "effect_claims",
        "merge_attempts",
        "mutations",
        "proof_attempts",
        "worktrees",
        "completion_receipts",
        "validation_results",
    )
    for noun, database in databases:
        connection = g7._open_local_database(database, read_only=True)
        try:
            tables = _table_names(connection)
            for settlement in settlements:
                _validate_pre_effect_evidence(settlement)
                for table in forbidden_tables:
                    if table in tables and _attempt_rows(connection, table, settlement):
                        _fail(
                            f"{settlement['task_alias']} has effect evidence in "
                            f"{noun}:{table}"
                        )
                if "attempt_dispatch_journal" in tables:
                    rows = connection.execute(
                        "SELECT dispatch_kind,outcome FROM attempt_dispatch_journal "
                        "WHERE attempt_id=?",
                        [settlement["attempt_id"]],
                    ).fetchall()
                    if any(
                        str(kind) in {"provider", "effect"}
                        and str(outcome) not in {"deferred", "preentry_failed"}
                        for kind, outcome in rows
                    ):
                        _fail(
                            f"{settlement['task_alias']} has ambiguous callback dispatch"
                        )
                if "database_task_attempts" not in tables:
                    continue
                rows = connection.execute(
                    "SELECT task_cid,committed_phase,status,body_json FROM "
                    "database_task_attempts WHERE attempt_id=?",
                    [settlement["attempt_id"]],
                ).fetchall()
                if not rows:
                    continue
                if len(rows) != 1:
                    _fail(f"{settlement['task_alias']} execution attempt is ambiguous")
                task_cid, phase, status, body_json = rows[0]
                body = json.loads(str(body_json))
                if (
                    str(task_cid) != settlement["task_cid"]
                    or str(phase) != "context"
                    or str(status) != "running"
                    or str(body.get("worktree_id") or "")
                ):
                    _fail(f"{settlement['task_alias']} exceeded the pre-effect phase")
                phases = connection.execute(
                    "SELECT phase FROM attempt_phases WHERE attempt_id=? "
                    "ORDER BY revision",
                    [settlement["attempt_id"]],
                ).fetchall()
                if [str(row[0]) for row in phases] != ["claimed", "context"]:
                    _fail(f"{settlement['task_alias']} phase history is not pre-effect")
        finally:
            connection.close()


def _coordination_attempt(
    projection: Mapping[str, Any], settlement: Mapping[str, Any]
) -> dict[str, Any]:
    claim = g7._active_claim_for_history(projection, settlement)
    attempts = [
        dict(item)
        for item in projection.get("task_attempts", ())
        if isinstance(item, Mapping)
        and item.get("attempt_id") == settlement["attempt_id"]
    ]
    if len(attempts) != 1:
        _fail("g8 terminal coordination attempt is absent or ambiguous")
    attempt = attempts[0]
    for field in (
        "task_cid",
        "attempt_id",
        "lease_id",
        "owner_session_id",
        "fencing_token",
        "fence_epoch",
    ):
        if claim.get(field) != settlement.get(field):
            _fail(f"g8 terminal coordination claim differs: {field}")
    if (
        claim.get("state") != settlement["prior_claim_state"]
        or attempt.get("status") != settlement["prior_attempt_status"]
        or projection.get("projection_root")
        != settlement["coordination_projection_root"]
    ):
        _fail("g8 coordination history is not the sealed predecessor state")
    return {
        "task_alias": settlement["task_alias"],
        "task_cid": settlement["task_cid"],
        "claim_id": settlement["claim_id"],
        "attempt_id": settlement["attempt_id"],
        "lease_id": settlement["lease_id"],
        "fencing_token": int(settlement["fencing_token"]),
        "fence_epoch": int(settlement["fence_epoch"]),
        "prior_claim_state": claim["state"],
        "prior_attempt_status": attempt["status"],
        "projection_root": projection["projection_root"],
    }


def _settle_coordination_attempt(
    database: Path, settlement: Mapping[str, Any]
) -> dict[str, Any]:
    before = g7._coordination_projection(database)
    prior = _coordination_attempt(before, settlement)
    if settlement["coordination_action"] == "expire_exact_active_claim":
        result = g7._expire_stranded_claim(database, settlement)
        g7._checkpoint_database(database)
        after = g7._coordination_projection(database)
    else:
        result = {
            "task_alias": settlement["task_alias"],
            "task_cid": settlement["task_cid"],
            "claim_id": settlement["claim_id"],
            "attempt_id": settlement["attempt_id"],
            "lease_id": settlement["lease_id"],
            "fencing_token": int(settlement["fencing_token"]),
            "fence_epoch": int(settlement["fence_epoch"]),
            "pre_projection_root": before["projection_root"],
            "post_projection_root": before["projection_root"],
        }
        after = before
    claim = g7._active_claim_for_history(after, settlement)
    attempts = [
        dict(item)
        for item in after.get("task_attempts", ())
        if isinstance(item, Mapping)
        and item.get("attempt_id") == settlement["attempt_id"]
    ]
    if (
        len(attempts) != 1
        or claim.get("state") != settlement["target_claim_state"]
        or attempts[0].get("status") != settlement["target_attempt_status"]
    ):
        _fail("g8 coordination settlement did not reach its sealed target state")
    return {
        **prior,
        **result,
        "coordination_action": settlement["coordination_action"],
        "target_claim_state": claim["state"],
        "target_attempt_status": attempts[0]["status"],
    }


def _assert_quota_log(
    *, root: Path, settlement: Mapping[str, Any]
) -> dict[str, Any]:
    record = dict(settlement["pre_effect_log"])
    path = g7._confined(
        root,
        record["path"],
        noun=f"{settlement['task_alias']} sealed Grok quota log",
    )
    payload, digest, size, identity = g7._read_stable_file_snapshot(
        path,
        root=root,
        noun=f"{settlement['task_alias']} sealed Grok quota log",
        required_links=1,
        maximum_bytes=64 * 1024,
    )
    if (
        digest != record["sha256"]
        or size != int(record["size_bytes"])
        or identity[-2:] != (int(os.geteuid()), 0o600)
    ):
        _fail(f"{settlement['task_alias']} Grok quota log anchor differs")
    lowered = payload.lower()
    if not all(fragment in lowered for fragment in (b"grok", b"402", b"usage", b"balance")):
        _fail(f"{settlement['task_alias']} log lacks the exact quota signature")
    _validate_pre_effect_evidence(settlement)
    return record


def _assert_prior_anchor(
    root: Path,
    policy: Mapping[str, Any],
    *,
    fenced_connection: Any | None = None,
) -> dict[str, Any]:
    """Verify the exact stopped g7 authority under its canonical owner fence."""

    root = root.resolve()
    control_record = dict(policy["prior_control_store"])
    control = g7._confined(root, control_record["path"], noun="stopped g7 control")
    if fenced_connection is None:
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
            offline_state_server_fence,
        )

        try:
            with offline_state_server_fence(
                database_path=control,
                connection_factory=lambda path: g7._open_local_database(
                    path, read_only=True
                ),
            ) as connection:
                return _assert_prior_anchor(
                    root,
                    policy,
                    fenced_connection=connection,
                )
        except ProviderRouteSuccessorError:
            raise
        except Exception as exc:
            _fail("stopped g7 authority could not be fenced", exc)

    control = g7._file_anchor(
        root,
        control_record,
        noun="stopped g7 control store",
    )
    if os.path.lexists(control.with_name(control.name + ".wal")):
        _fail("stopped g7 control store retains an unsealed WAL")
    status_path = g7._file_anchor(
        root,
        dict(policy["prior_stopped_status"]),
        noun="stopped g7 Quack status",
    )
    generation_receipt = g7._file_anchor(
        root,
        dict(policy["prior_generation_receipt"]),
        noun="accepted g7 generation receipt",
    )
    generation_body = g7._load_json(
        generation_receipt,
        root=root,
        noun="accepted g7 generation receipt",
    )
    if (
        generation_body.get("schema") != g7.RECEIPT_SCHEMA
        or generation_body.get("target_store_generation") != "pctdd-v1-g7"
    ):
        _fail("g7 generation receipt identity differs")
    _assert_private_stopped_owner(
        root=root,
        policy=policy,
        control=control,
        status_path=status_path,
        connection=fenced_connection,
    )

    coordination: list[dict[str, Any]] = []
    for raw in policy["coordination_stores"]:
        record = dict(raw)
        lane = int(record["lane"])
        database = g7._file_anchor(
            root,
            record,
            noun=f"stopped g7 lane {lane} coordination store",
        )
        wal_record = record.get("wal")
        wal: Path | None = None
        if isinstance(wal_record, Mapping):
            wal = g7._file_anchor(
                root,
                wal_record,
                noun=f"stopped g7 lane {lane} coordination WAL",
            )
        elif os.path.lexists(database.with_name(database.name + ".wal")):
            _fail(f"stopped g7 lane {lane} has an unsealed coordination WAL")
        observation_record = record.get("execution_observation")
        if not isinstance(observation_record, Mapping):
            _fail(f"stopped g7 lane {lane} lacks execution observation")
        observation = g7._file_anchor(
            root,
            observation_record,
            noun=f"stopped g7 lane {lane} execution observation",
        )
        observation_wal_record = observation_record.get("wal")
        observation_wal: Path | None = None
        if isinstance(observation_wal_record, Mapping):
            observation_wal = g7._file_anchor(
                root,
                observation_wal_record,
                noun=f"stopped g7 lane {lane} execution observation WAL",
            )
        elif os.path.lexists(observation.with_name(observation.name + ".wal")):
            _fail(f"stopped g7 lane {lane} has an unsealed observation WAL")
        coordination.append(
            {
                "policy": record,
                "database": database,
                "wal": wal,
                "execution_record": dict(observation_record),
                "execution_database": observation,
                "execution_wal": observation_wal,
            }
        )

    projection = g7._control_projection(control)
    expected_projection = dict(policy["prior_control_projection"])
    for field in (
        "statuses",
        "event_watermark",
        "event_count",
        "event_prefix_digest",
        "task_definition_digest",
        "accepted_tables_digest",
        "historical_row_hashes",
        "counts",
    ):
        if projection[field] != expected_projection[field]:
            _fail(f"stopped g7 control projection differs: {field}")
    plan = projection["plan"]
    if (
        len(plan) != 1
        or plan[0][0] != policy["accepted_plan_root_cid"]
        or int(plan[0][3]) != int(policy["prior_plan_revision"])
    ):
        _fail("stopped g7 accepted plan differs")
    for settlement in policy["settlements"]:
        lane = int(settlement["lane"])
        _coordination_attempt(
            g7._coordination_projection(coordination[lane]["database"]),
            settlement,
        )
        _assert_quota_log(root=root, settlement=settlement)
    return {
        "control": control,
        "status": status_path,
        "generation_receipt": generation_receipt,
        "control_projection": projection,
        "coordination": coordination,
    }


def _capture_file_record(root: Path, relative: str, *, noun: str) -> dict[str, Any]:
    path = g7._confined(root, relative, noun=noun)
    digest, size = g7._stable_file(path, root=root, noun=noun, required_links=1)
    return {"path": relative, "sha256": digest, "size_bytes": size}


def capture_stopped_source_provider_route_authority(
    *,
    root: Path,
    control_path: str,
    generation_receipt_path: str,
    status_path: str,
    coordination_paths: Sequence[str],
    execution_observation_paths: Sequence[str],
    pre_effect_log_paths: Mapping[str, str],
) -> dict[str, Any]:
    """Capture the exact stopped g7 authority under one canonical owner fence."""

    if (
        len(coordination_paths) != 4
        or len(execution_observation_paths) != 4
        or set(pre_effect_log_paths) != set(EXPECTED_TASK_ALIASES)
    ):
        _fail("g8 capture requires four lanes and two exact quota logs")
    root = root.resolve()
    control = g7._confined(root, control_path, noun="g7 capture control")
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        offline_state_server_fence,
    )

    try:
        with offline_state_server_fence(
            database_path=control,
            connection_factory=lambda path: g7._open_local_database(
                path, read_only=True
            ),
        ) as probe:
            latest = g7._latest_state_server_from_connection(probe)
            g7._close_offline_fence_probe(probe)
            control_record = _capture_file_record(
                root, control_path, noun="stopped g7 control store"
            )
            if os.path.lexists(control.with_name(control.name + ".wal")):
                _fail("stopped g7 control has an unsealed WAL")
            generation_record = _capture_file_record(
                root,
                generation_receipt_path,
                noun="accepted g7 generation receipt",
            )
            generation = g7._load_json(
                g7._confined(root, generation_receipt_path, noun="g7 receipt"),
                root=root,
                noun="accepted g7 generation receipt",
            )
            if (
                generation.get("schema") != g7.RECEIPT_SCHEMA
                or generation.get("target_store_generation") != "pctdd-v1-g7"
            ):
                _fail("captured generation receipt is not the g7 authority")
            status_record = _capture_file_record(
                root, status_path, noun="stopped g7 owner status"
            )
            status = g7._load_json(
                g7._confined(root, status_path, noun="g7 owner status"),
                root=root,
                noun="stopped g7 owner status",
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
                _fail("captured g7 owner is not exactly stopped")
            for field, value in latest.items():
                if identity.get(field) != value and field not in {"stopped_at", "revision"}:
                    _fail(f"captured g7 owner identity differs: {field}")
            owner = {**latest, "fence_epoch": int(identity["fence_epoch"])}
            owner_dir = g7._confined(root, status_path, noun="g7 owner status").parent
            forbidden_owner_artifacts = (
                control.with_name(f".{control.name}.state-owner.json"),
                owner_dir / "quack-state-server.pid",
                owner_dir / "quack-state-server.owner.json",
                owner_dir / "quack-state-server.stop",
            )
            if any(os.path.lexists(path) for path in forbidden_owner_artifacts) or tuple(
                owner_dir.glob("*.quack-token")
            ):
                _fail("captured g7 owner retains live authority artifacts")
            g7._assert_listener_stopped(
                {"target_quack_endpoint": str(identity["listen_uri"])}
            )

            coordination_records: list[dict[str, Any]] = []
            coordination_projections: list[dict[str, Any]] = []
            observation_paths: list[Path] = []
            for lane, (coord_relative, observation_relative) in enumerate(
                zip(
                    coordination_paths,
                    execution_observation_paths,
                    strict=True,
                )
            ):
                coord_record = _capture_file_record(
                    root,
                    coord_relative,
                    noun=f"stopped g7 lane {lane} coordination",
                )
                coord = g7._confined(
                    root, coord_relative, noun=f"g7 lane {lane} coordination"
                )
                wal = coord.with_name(coord.name + ".wal")
                if os.path.lexists(wal):
                    coord_record["wal"] = _capture_file_record(
                        root,
                        wal.relative_to(root).as_posix(),
                        noun=f"stopped g7 lane {lane} coordination WAL",
                    )
                observation_record = _capture_file_record(
                    root,
                    observation_relative,
                    noun=f"stopped g7 lane {lane} execution observation",
                )
                observation = g7._confined(
                    root,
                    observation_relative,
                    noun=f"g7 lane {lane} execution observation",
                )
                observation_wal = observation.with_name(observation.name + ".wal")
                if os.path.lexists(observation_wal):
                    observation_record["wal"] = _capture_file_record(
                        root,
                        observation_wal.relative_to(root).as_posix(),
                        noun=f"stopped g7 lane {lane} execution WAL",
                    )
                projection = g7._coordination_projection(coord)
                coord_record.update(
                    {
                        "lane": lane,
                        "projection_root": projection["projection_root"],
                        "execution_observation": observation_record,
                    }
                )
                coordination_records.append(coord_record)
                coordination_projections.append(projection)
                observation_paths.append(observation)

            connection = g7._open_local_database(control, read_only=True)
            try:
                tasks = _control_tasks_from_connection(connection)
            finally:
                connection.close()
            prior_projection = g7._control_projection(control)
            plan = prior_projection["plan"]
            if len(plan) != 1:
                _fail("captured g7 plan population is ambiguous")

            settlements: list[dict[str, Any]] = []
            for alias in EXPECTED_TASK_ALIASES:
                task = tasks.get(alias)
                if task is None or task["status"] != "blocked":
                    _fail(f"{alias} is not the exact stopped blocked task")
                receipt = task["body"].get("completion_receipt")
                if not isinstance(receipt, Mapping):
                    _fail(f"{alias} stopped receipt is absent")
                claim_id = str(receipt.get("claim_id") or "")
                matches: list[tuple[int, dict[str, Any], dict[str, Any]]] = []
                for lane, projection in enumerate(coordination_projections):
                    claims = [
                        dict(item)
                        for item in projection.get("task_claims", ())
                        if isinstance(item, Mapping)
                        and item.get("claim_id") == claim_id
                    ]
                    attempts = [
                        dict(item)
                        for item in projection.get("task_attempts", ())
                        if isinstance(item, Mapping)
                        and item.get("attempt_id") == receipt.get("attempt_id")
                    ]
                    if len(claims) == len(attempts) == 1:
                        matches.append((lane, claims[0], attempts[0]))
                if len(matches) != 1:
                    _fail(f"{alias} stopped coordination identity is ambiguous")
                lane, claim, attempt = matches[0]
                if claim["state"] == "accepted" and attempt["status"] == "running":
                    action = "expire_exact_active_claim"
                    target_claim, target_attempt = "expired", "expired"
                elif claim["state"] == "released" and attempt["status"] == "released":
                    action = "preserve_exact_terminal_claim"
                    target_claim, target_attempt = "released", "released"
                else:
                    _fail(f"{alias} coordination state is not an admitted predecessor")
                log_record = _capture_file_record(
                    root,
                    str(pre_effect_log_paths[alias]),
                    noun=f"{alias} Grok quota log",
                )
                base = {
                    "task_alias": alias,
                    "task_cid": task["task_cid"],
                    "control_revision": task["revision"],
                    "lane": lane,
                    "attempt_id": receipt["attempt_id"],
                    "claim_id": receipt["claim_id"],
                    "lease_id": receipt["lease_id"],
                    "owner_session_id": receipt["owner_session_id"],
                    "fencing_token": int(receipt["fencing_token"]),
                    "fence_epoch": int(receipt["fence_epoch"]),
                    "prior_task_status": "blocked",
                    "target_task_status": "todo",
                    "coordination_action": action,
                    "prior_claim_state": claim["state"],
                    "prior_attempt_status": attempt["status"],
                    "target_claim_state": target_claim,
                    "target_attempt_status": target_attempt,
                    "coordination_projection_root": coordination_projections[lane][
                        "projection_root"
                    ],
                    "prior_completion_receipt": dict(receipt),
                    "prior_completion_receipt_cid": g7._identity(receipt),
                    "pre_effect_log": log_record,
                    "retry_budget": {
                        "prior_attempts_used": int(receipt["attempts_used"]),
                        "target_attempts_used": 0,
                        "max_task_attempts": int(receipt["max_task_attempts"]),
                        "prior_unknown_outcome_rearm_count": int(
                            receipt["unknown_outcome_rearm_count"]
                        ),
                        "target_unknown_outcome_rearm_count": int(
                            receipt["unknown_outcome_rearm_count"]
                        )
                        + 1,
                    },
                }
                evidence = {
                    "schema": PRE_EFFECT_SCHEMA,
                    "task_alias": alias,
                    "task_cid": task["task_cid"],
                    "attempt_id": receipt["attempt_id"],
                    "claim_id": receipt["claim_id"],
                    "provider_id": "grok_cli",
                    "model_id": "grok-4.6",
                    "failure_class": "hard_quota_exhausted",
                    "http_status": 402,
                    "supervisor_outcome": "provider_capacity_backoff",
                    "provider_effect_committed": False,
                    "fallback_dispatched": False,
                    "workspace_mutated": False,
                    "durable_provider_attempt_state": "absent",
                    "evidence_source": "operator_sealed_grok_quota_log",
                    "source_artifact_path": log_record["path"],
                    "source_artifact_sha256": log_record["sha256"],
                    "source_artifact_size_bytes": log_record["size_bytes"],
                }
                evidence["evidence_cid"] = g7._identity(evidence)
                base["pre_effect_evidence"] = evidence
                _validate_prior_blocked_receipt(base, receipt)
                _assert_quota_log(root=root, settlement=base)
                settlements.append(base)

            _assert_pre_effect_attempts(
                [
                    ("main-control", control),
                    *(
                        (
                            f"lane-{lane}-coordination",
                            g7._confined(root, path, noun="coordination capture"),
                        )
                        for lane, path in enumerate(coordination_paths)
                    ),
                    *(
                        (f"lane-{lane}-execution", path)
                        for lane, path in enumerate(observation_paths)
                    ),
                ],
                settlements,
            )
            revisions: list[dict[str, Any]] = []
            for alias, task in sorted(tasks.items()):
                if task["status"] in COMPLETED_TASK_STATUSES:
                    continue
                target_task = {**task, "body": _role_delta_body(task["body"])}
                revisions.append(
                    {
                        "task_alias": alias,
                        "task_cid": task["task_cid"],
                        "prior_status": task["status"],
                        "prior_revision": task["revision"],
                        "target_revision": task["revision"]
                        + (2 if alias in EXPECTED_TASK_ALIASES else 1),
                        "prior_definition_cid": _definition_cid(task),
                        "target_definition_cid": _definition_cid(target_task),
                        "prior_provider_role": "grok-only",
                        "target_provider_role": "grok-implement",
                    }
                )
            target_statuses = dict(prior_projection["statuses"])
            target_statuses["blocked"] = int(target_statuses.get("blocked", 0)) - 2
            if target_statuses["blocked"] == 0:
                target_statuses.pop("blocked")
            target_statuses["todo"] = int(target_statuses.get("todo", 0)) + 2
            target_status_by_alias = {
                alias: (
                    "todo" if alias in EXPECTED_TASK_ALIASES else task["status"]
                )
                for alias, task in tasks.items()
            }
            target_tasks = {
                alias: {**task, "status": target_status_by_alias[alias]}
                for alias, task in tasks.items()
            }
            ready = _ready_aliases(target_tasks)
            return {
                "prior_control_store": control_record,
                "prior_generation_receipt": generation_record,
                "prior_stopped_status": status_record,
                "prior_owner_identity": owner,
                "coordination_stores": coordination_records,
                "prior_control_projection": prior_projection,
                "accepted_plan_root_cid": str(plan[0][0]),
                "prior_plan_revision": int(plan[0][3]),
                "settlements": settlements,
                "provider_role_revisions": revisions,
                "target_control_projection": {
                    "statuses": target_statuses,
                    "task_revisions": {
                        item["task_alias"]: item["target_revision"]
                        for item in revisions
                    },
                    "ready_frontier": ready,
                },
            }
    except ProviderRouteSuccessorError:
        raise
    except Exception as exc:
        _fail("stopped g7 provider-route authority capture failed closed", exc)


def _migration_body(
    *,
    root: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    route_binding: Mapping[str, Any],
    prior_projection: Mapping[str, Any],
    coordination_settlements: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": EVIDENCE_SCHEMA,
        "migration_revision": policy["migration_revision"],
        "migration_kind": "exact_source_and_provider_route_successor",
        "prior_store_generation": policy["prior_store_generation"],
        "target_store_generation": policy["target_store_generation"],
        "accepted_plan_root_cid": policy["accepted_plan_root_cid"],
        "source_binding": g7._source_binding(root, population),
        "provider_route_binding": dict(route_binding),
        "provider_route_binding_cid": policy["provider_route_binding_cid"],
        "prior_event_watermark": prior_projection["event_watermark"],
        "prior_event_prefix_digest": prior_projection["event_prefix_digest"],
        "prior_task_definition_digest": prior_projection[
            "task_definition_digest"
        ],
        "prior_accepted_tables_digest": prior_projection[
            "accepted_tables_digest"
        ],
        "provider_role_revisions": [
            dict(item) for item in policy["provider_role_revisions"]
        ],
        "coordination_settlements": [
            dict(item) for item in coordination_settlements
        ],
        "pre_effect_evidence_cids": [
            str(_validate_pre_effect_evidence(item)["evidence_cid"])
            for item in policy["settlements"]
        ],
        "copy_policy": dict(policy["copy_policy"]),
        "claim_boundaries": {
            "accepted_completion_changes": 0,
            "completed_task_definition_changes": 0,
            "goal_changes": 0,
            "provider_invocation_changes": 0,
            "effect_claim_changes": 0,
            "merge_attempt_changes": 0,
            "fallback_authority_created": False,
            "worker_self_approval": False,
        },
    }


def _apply_control_suffix(
    database: Path,
    *,
    root: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    route_binding: Mapping[str, Any],
    coordination_settlements: Sequence[Mapping[str, Any]],
    prior_projection: Mapping[str, Any],
) -> dict[str, Any]:
    """Append the one reviewed g8 suffix through canonical repositories."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
        database_retry_validation_spec_cid,
    )

    counter = g7._open_local_database(database, read_only=True)
    try:
        prior_task_revision_count = int(
            counter.execute("SELECT COUNT(*) FROM task_revisions").fetchone()[0]
        )
    finally:
        counter.close()
    accepted_plan = str(policy["accepted_plan_root_cid"])
    with DatabaseTaskSource(
        database,
        owner_id="pctdd-provider-route-g8:private-stage",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=accepted_plan,
    ) as source:
        operator = source.get_task("PCTDD-000")
        if operator is None or operator.status != "completed":
            _fail("PCTDD-000 historical completion differs")
        plan = source.get_plan(accepted_plan)
        if plan is None or int(plan["revision"]) != int(
            policy["prior_plan_revision"]
        ):
            _fail("accepted g7 plan is not at its sealed revision")
        prior_tasks, role_revisions = _validate_role_revision_population(
            source, policy
        )
        completed_definitions = {
            alias: _definition_cid(task)
            for alias, task in prior_tasks.items()
            if str(task["status"]) in COMPLETED_TASK_STATUSES
        }

        source_binding = g7._source_binding(root, population)
        plan_receipt = source.plans.append_revision(
            plan_cid=accepted_plan,
            expected_revision=int(policy["prior_plan_revision"]),
            body={
                "current_source_binding": source_binding,
                "source_provider_route_migration_revision": policy[
                    "migration_revision"
                ],
                "provider_route_binding": dict(route_binding),
                "provider_route_binding_cid": policy[
                    "provider_route_binding_cid"
                ],
                "accepted_plan_root_preserved": True,
                "provider_role_revision_count": len(role_revisions),
                "completed_task_definition_changes": 0,
                "accepted_completion_changes": 0,
            },
            delta={
                "kind": "exact_source_and_provider_route_successor",
                "current_source_head": source_binding["source_head"],
                "current_repository_tree_id": source_binding[
                    "repository_tree_id"
                ],
                "provider_route_binding_cid": policy[
                    "provider_route_binding_cid"
                ],
            },
        )
        migration_body = _migration_body(
            root=root,
            population=population,
            policy=policy,
            route_binding=route_binding,
            prior_projection=prior_projection,
            coordination_settlements=coordination_settlements,
        )
        migration_digest = g7._control_plane_content_identity(migration_body)
        evidence = source.record_evidence(
            task_cid=operator.task_cid,
            evidence_kind=MIGRATION_EVIDENCE_KIND,
            digest=migration_digest,
            body=migration_body,
        )

        status_receipts: list[dict[str, Any]] = []
        settlements_by_alias = {
            str(item["task_alias"]): dict(item)
            for item in coordination_settlements
        }
        policy_settlements = {
            str(item["task_alias"]): dict(item)
            for item in policy["settlements"]
        }
        for alias in EXPECTED_TASK_ALIASES:
            settlement = settlements_by_alias.get(alias)
            expected = policy_settlements.get(alias)
            if settlement is None or expected is None:
                _fail(f"{alias} exact coordination settlement is absent")
            task = source.get_task(alias)
            if (
                task is None
                or task.status != "blocked"
                or task.revision != int(expected["control_revision"])
                or task.task_cid != expected["task_cid"]
            ):
                _fail(f"{alias} control row is not the sealed stopped block")
            prior_receipt = task.body.get("completion_receipt")
            if not isinstance(prior_receipt, Mapping):
                _fail(f"{alias} prior blocked receipt is absent")
            _validate_prior_blocked_receipt(expected, prior_receipt)
            budget = _validate_retry_budget(expected)
            validation_spec_cid = database_retry_validation_spec_cid(
                task.task_cid, task.validations
            )
            if prior_receipt.get("validation_spec_cid") != validation_spec_cid:
                _fail(f"{alias} prior validation-spec binding differs")
            pre_effect = _validate_pre_effect_evidence(expected)
            reset_receipt = {
                "schema": DATABASE_RETRY_BUDGET_SCHEMA,
                "operation": "operator_provider_route_migration_reset",
                "migration_digest": migration_digest,
                "provider_route_binding_cid": policy[
                    "provider_route_binding_cid"
                ],
                "pre_effect_evidence_cid": pre_effect["evidence_cid"],
                "task_cid": task.task_cid,
                "task_alias": task.task_alias,
                "previous_control_revision": task.revision,
                "attempt_id": expected["attempt_id"],
                "claim_id": expected["claim_id"],
                "lease_id": expected["lease_id"],
                "owner_session_id": expected["owner_session_id"],
                "fencing_token": int(expected["fencing_token"]),
                "fence_epoch": int(expected["fence_epoch"]),
                "coordination_post_projection_root": settlement[
                    "post_projection_root"
                ],
                "provider_effect_committed": False,
                "fallback_dispatched": False,
                "automatic_retry_admitted": False,
                "old_result_reusable": False,
                "validation_spec_cid": validation_spec_cid,
                "attempts_used": budget["target_attempts_used"],
                "max_task_attempts": budget["max_task_attempts"],
                "retry_exhausted": False,
                "unknown_outcome_rearm_count": budget[
                    "target_unknown_outcome_rearm_count"
                ],
                "provider_route_reset_authorized": True,
                "process_instance_id": "operator:pctdd-provider-route-g8",
                "prior_blocked_receipt_cid": expected[
                    "prior_completion_receipt_cid"
                ],
            }
            reset = source.compare_and_set_status(
                task.task_cid,
                task.revision,
                "todo",
                receipt=reset_receipt,
            )
            status_receipts.append(
                {
                    "task_alias": alias,
                    "reset_event_id": reset.receipt_cid,
                    "resulting_revision": reset.task.revision,
                    "pre_effect_evidence_cid": pre_effect["evidence_cid"],
                }
            )

        role_receipts: list[dict[str, Any]] = []
        for record in role_revisions:
            alias = str(record["task_alias"])
            current = source.intent.get_task(alias)
            if current is None:
                _fail(f"{alias} disappeared before provider-role revision")
            expected_revision = int(record["prior_revision"]) + (
                1 if alias in EXPECTED_TASK_ALIASES else 0
            )
            if (
                int(current["revision"]) != expected_revision
                or str(current["status"])
                != ("todo" if alias in EXPECTED_TASK_ALIASES else record["prior_status"])
            ):
                _fail(f"{alias} current revision changed before role revision")
            prior_body = dict(current["body"])
            target_body = _role_delta_body(prior_body)
            before_without_receipt = {**current, "body": prior_body}
            after_without_receipt = {**current, "body": target_body}
            if (
                _definition_cid(before_without_receipt)
                != record["prior_definition_cid"]
                or _definition_cid(after_without_receipt)
                != record["target_definition_cid"]
            ):
                _fail(f"{alias} provider-role delta changed another definition field")
            receipt = source.intent.upsert_task(
                task_cid=str(current["task_cid"]),
                task_alias=str(current["task_alias"]),
                goal_cid=str(current["goal_cid"]),
                plan_cid=str(current.get("plan_cid") or ""),
                objective_id=str(current.get("objective_id") or ""),
                ordinal=int(current["ordinal"]),
                status=str(current["status"]),
                priority=str(current.get("priority") or ""),
                body=target_body,
                identity=dict(current.get("identity") or {}),
                expected_revision=expected_revision,
            )
            updated = source.intent.get_task(alias)
            if (
                updated is None
                or int(updated["revision"]) != int(record["target_revision"])
                or _definition_cid(updated) != record["target_definition_cid"]
            ):
                _fail(f"{alias} provider-role revision did not commit exactly")
            role_receipts.append(
                {
                    "task_alias": alias,
                    "event_id": receipt.event_id,
                    "prior_definition_cid": record["prior_definition_cid"],
                    "target_definition_cid": record["target_definition_cid"],
                    "resulting_revision": int(updated["revision"]),
                }
            )

    return {
        "plan_event_id": plan_receipt.event_id,
        "migration_evidence_event_id": evidence.event_id,
        "migration_digest": migration_digest,
        "status_receipts": status_receipts,
        "provider_role_receipts": role_receipts,
        "completed_definition_cids": completed_definitions,
        "prior_task_revision_count": prior_task_revision_count,
    }


def _verify_staged_successor(
    *,
    stage_root: Path,
    database: Path,
    coordination_paths: Sequence[Path],
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    prior_projection: Mapping[str, Any],
    suffix: Mapping[str, Any],
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    post = g7._control_projection(database)
    target = dict(policy["target_control_projection"])
    if post["statuses"] != dict(target["statuses"]):
        _fail("g8 task status population differs")
    if post["accepted_tables_digest"] != prior_projection["accepted_tables_digest"]:
        _fail("g8 changed accepted goals, relations, completion, or validation rows")
    for table, prior_hashes in prior_projection["historical_row_hashes"].items():
        post_hashes = post["historical_row_hashes"].get(table, ())
        if Counter(prior_hashes) - Counter(post_hashes):
            _fail(f"g8 altered or lost historical rows in {table}")
    for key in (
        "completion_receipts",
        "validation_results",
        "goals",
        "tasks",
        "task_dependencies",
        "provider_invocations",
        "effect_claims",
        "merge_attempts",
    ):
        if post["counts"][key] != prior_projection["counts"][key]:
            _fail(f"g8 changed preserved count: {key}")
    if post["counts"]["evidence_nodes"] != prior_projection["counts"]["evidence_nodes"] + 1:
        _fail("g8 must append exactly one operator evidence node")
    if post["counts"]["plan_revisions"] != prior_projection["counts"]["plan_revisions"] + 1:
        _fail("g8 must append exactly one plan revision")
    role_count = len(policy["provider_role_revisions"])
    expected_event_delta = role_count + 4
    if (
        post["event_count"] != prior_projection["event_count"] + expected_event_delta
        or post["event_watermark"]
        != prior_projection["event_watermark"] + expected_event_delta
    ):
        _fail("g8 control event suffix is not exactly N role revisions plus four")

    connection = g7._open_local_database(database, read_only=True)
    try:
        task_revision_count = int(
            connection.execute("SELECT COUNT(*) FROM task_revisions").fetchone()[0]
        )
        evidence_rows = connection.execute(
            "SELECT digest,body_json FROM evidence_nodes WHERE evidence_kind=?",
            [MIGRATION_EVIDENCE_KIND],
        ).fetchall()
    finally:
        connection.close()
    if task_revision_count != int(suffix["prior_task_revision_count"]) + role_count + 2:
        _fail("g8 task revision suffix is not exactly N role revisions plus two")
    if len(evidence_rows) != 1:
        _fail("g8 operator provider-route evidence is absent or ambiguous")
    evidence_body = json.loads(str(evidence_rows[0][1]))
    if (
        str(evidence_rows[0][0]) != suffix["migration_digest"]
        or g7._control_plane_content_identity(evidence_body)
        != suffix["migration_digest"]
    ):
        _fail("g8 operator provider-route evidence bytes differ")

    with DatabaseTaskSource(
        database,
        owner_id="pctdd-provider-route-g8:stage-verify",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(policy["accepted_plan_root_cid"]),
    ) as source:
        tasks = _task_projection(source)
        expected_revisions = {
            str(item["task_alias"]): dict(item)
            for item in policy["provider_role_revisions"]
        }
        for alias, record in expected_revisions.items():
            task = tasks[alias]
            if (
                int(task["revision"]) != int(record["target_revision"])
                or task["body"].get("provider_role") != "grok-implement"
                or _definition_cid(task) != record["target_definition_cid"]
            ):
                _fail(f"g8 provider-role successor differs: {alias}")
        for alias, expected_cid in dict(
            suffix["completed_definition_cids"]
        ).items():
            if _definition_cid(tasks[alias]) != expected_cid:
                _fail(f"g8 changed completed task definition: {alias}")
        ready = [item.task_alias for item in source.ready_tasks(limit=100).tasks]
    if ready != list(target["ready_frontier"]):
        _fail("g8 initial ready frontier differs")
    plan = post["plan"]
    if (
        len(plan) != 1
        or int(plan[0][3]) != int(policy["prior_plan_revision"]) + 1
        or json.loads(str(plan[0][4])).get("provider_route_binding_cid")
        != policy["provider_route_binding_cid"]
    ):
        _fail("g8 active plan provider-route revision differs")

    coordination = [g7._coordination_projection(path) for path in coordination_paths]
    return {
        "control_projection": post,
        "task_revision_count": task_revision_count,
        "ready_frontier": ready,
        "control_store": {
            "sha256": g7._stable_file(
                database, root=stage_root, noun="staged g8 control"
            )[0],
            "size_bytes": database.stat().st_size,
        },
        "coordination_stores": [
            {
                "lane": lane,
                "sha256": g7._stable_file(
                    path, root=stage_root, noun=f"staged g8 lane {lane}"
                )[0],
                "size_bytes": path.stat().st_size,
                "projection_root": coordination[lane]["projection_root"],
            }
            for lane, path in enumerate(coordination_paths)
        ],
        "suffix": dict(suffix),
    }


def _receipt(
    *,
    root: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    route_binding: Mapping[str, Any],
    prior_projection: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "migration_revision": policy["migration_revision"],
        "prior_store_generation": policy["prior_store_generation"],
        "target_store_generation": policy["target_store_generation"],
        "accepted_plan_root_cid": policy["accepted_plan_root_cid"],
        "source_binding": g7._source_binding(root, population),
        "provider_route_binding": dict(route_binding),
        "provider_route_binding_cid": policy["provider_route_binding_cid"],
        "prior_control_store": dict(policy["prior_control_store"]),
        "prior_generation_receipt": dict(policy["prior_generation_receipt"]),
        "prior_owner_identity": dict(policy["prior_owner_identity"]),
        "prior_stopped_status": dict(policy["prior_stopped_status"]),
        "prior_event_watermark": prior_projection["event_watermark"],
        "prior_event_prefix_digest": prior_projection["event_prefix_digest"],
        "prior_task_definition_digest": prior_projection[
            "task_definition_digest"
        ],
        "historical_row_hashes": {
            table: list(hashes)
            for table, hashes in prior_projection["historical_row_hashes"].items()
        },
        "migration_event_watermark": verified["control_projection"][
            "event_watermark"
        ],
        "migration_event_prefix_digest": verified["control_projection"][
            "event_prefix_digest"
        ],
        "target_task_definition_digest": verified["control_projection"][
            "task_definition_digest"
        ],
        "control_store": dict(verified["control_store"]),
        "coordination_stores": [
            dict(item) for item in verified["coordination_stores"]
        ],
        "plan_revision_changes": 1,
        "evidence_node_changes": 1,
        "provider_role_revision_changes": len(policy["provider_role_revisions"]),
        "task_status_changes": 2,
        "completed_task_definition_changes": 0,
        "accepted_completion_changes": 0,
        "provider_invocation_changes": 0,
        "effect_claim_changes": 0,
        "merge_attempt_changes": 0,
        "fallback_authority_created": False,
        "worker_self_approval": False,
        "rearmed_task_aliases": list(EXPECTED_TASK_ALIASES),
        "ready_frontier": list(verified["ready_frontier"]),
        "copied_artifact_classes": [
            "authoritative_control_store",
            "coordination_history",
        ],
        "not_copied_artifact_classes": list(policy["copy_policy"]["not_copied"]),
        "suffix": dict(verified["suffix"]),
    }
    return {**receipt, "receipt_cid": g7._identity(receipt)}


def _store_relative_files() -> tuple[Path, ...]:
    return (
        Path("control.duckdb"),
        *(
            Path("state")
            / f"lane-{lane}"
            / "quack-lane-coordination.duckdb"
            for lane in range(4)
        ),
    )


def _store_record(relative: Path, receipt: Mapping[str, Any]) -> dict[str, Any]:
    if relative == Path("control.duckdb"):
        return dict(receipt["control_store"])
    lane = int(relative.parts[1].split("-", 1)[1])
    records = {
        int(item["lane"]): dict(item)
        for item in receipt["coordination_stores"]
    }
    return records[lane]


def _validate_receipt_identity(
    receipt: Mapping[str, Any],
    *,
    root: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    route_binding: Mapping[str, Any],
) -> None:
    unhashed = dict(receipt)
    receipt_cid = str(unhashed.pop("receipt_cid", ""))
    if (
        receipt.get("schema") != RECEIPT_SCHEMA
        or receipt_cid != g7._identity(unhashed)
        or receipt.get("source_binding") != g7._source_binding(root, population)
        or receipt.get("provider_route_binding") != dict(route_binding)
        or receipt.get("provider_route_binding_cid")
        != policy["provider_route_binding_cid"]
        or receipt.get("target_store_generation")
        != policy["target_store_generation"]
    ):
        _fail("g8 migration receipt identity differs")


def _validate_store(
    *,
    root: Path,
    target_root: Path,
    relative: Path,
    receipt: Mapping[str, Any],
) -> None:
    path = target_root / relative
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        _fail(f"published g8 store is absent: {relative.as_posix()}", exc)
    if (
        not stat.S_ISREG(metadata.st_mode)
        or int(metadata.st_uid) != int(os.geteuid())
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or int(metadata.st_nlink) != 1
    ):
        _fail(f"published g8 store is not private: {relative.as_posix()}")
    record = _store_record(relative, receipt)
    observed = g7._stable_file(
        path,
        root=root,
        noun=f"published g8 {relative.as_posix()}",
        required_links=1,
    )
    if observed != (str(record["sha256"]), int(record["size_bytes"])):
        _fail(f"published g8 store differs: {relative.as_posix()}")


def _validate_stores(
    *, root: Path, target_root: Path, receipt: Mapping[str, Any]
) -> None:
    for relative in _store_relative_files():
        _validate_store(
            root=root,
            target_root=target_root,
            relative=relative,
            receipt=receipt,
        )


def _prepared_path(target_root: Path, receipt: Mapping[str, Any]) -> Path:
    cid = str(receipt.get("receipt_cid") or "")
    digest = cid.removeprefix("sha256:")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        _fail("g8 prepared-stage receipt CID is malformed")
    return target_root.parent / f"{PREPARED_STAGE_PREFIX}{digest}"


def _expected_stage_files() -> set[Path]:
    return set(_store_relative_files()) | {Path(PREPARED_RECEIPT)}


def _validate_prepared(
    *,
    root: Path,
    target_root: Path,
    stage_root: Path,
    receipt: Mapping[str, Any],
) -> None:
    if stage_root != _prepared_path(target_root, receipt):
        _fail("g8 prepared-stage path does not bind its receipt")
    g7._assert_private_directory(stage_root)
    observed: set[Path] = set()
    for path in stage_root.rglob("*"):
        if path.is_dir() and not path.is_symlink():
            g7._assert_private_directory(path)
            continue
        relative = path.relative_to(stage_root)
        if relative not in _expected_stage_files():
            _fail(f"g8 prepared stage has unexpected artifact: {relative}")
        observed.add(relative)
    if observed != _expected_stage_files():
        _fail("g8 prepared stage is incomplete")
    prepared = g7._load_json(
        stage_root / PREPARED_RECEIPT,
        root=root,
        noun="prepared g8 migration receipt",
    )
    if prepared != dict(receipt):
        _fail("g8 prepared receipt bytes differ")
    _validate_stores(root=root, target_root=stage_root, receipt=receipt)


def _arm_prepared(
    *,
    root: Path,
    target_root: Path,
    stage_root: Path,
    receipt: Mapping[str, Any],
) -> Path:
    observation_root = stage_root / ".execution-observation-verification"
    if os.path.lexists(observation_root):
        shutil.rmtree(observation_root)
    g7._write_new_json(stage_root / PREPARED_RECEIPT, receipt)
    for relative in _store_relative_files():
        g7._fsync_private_file(
            stage_root / relative, noun=f"staged g8 {relative.as_posix()}"
        )
    g7._fsync_private_file(
        stage_root / PREPARED_RECEIPT, noun="staged g8 migration receipt"
    )
    for path in stage_root.rglob("*"):
        if path.is_dir() and not path.is_symlink():
            g7._assert_private_directory(path)
            g7._fsync_directory(path)
    g7._fsync_directory(stage_root)
    prepared = _prepared_path(target_root, receipt)
    if os.path.lexists(prepared):
        _fail("g8 prepared stage already exists")
    os.rename(stage_root, prepared)
    g7._fsync_directory(prepared.parent)
    _validate_prepared(
        root=root,
        target_root=target_root,
        stage_root=prepared,
        receipt=receipt,
    )
    return prepared


def _load_marker_snapshot(
    *, root: Path, target_root: Path, noun: str
) -> tuple[dict[str, Any], tuple[int, ...]]:
    marker = target_root / MIGRATION_MARKER
    pending = target_root / PENDING_MARKER
    pending_exists = os.path.lexists(pending)
    payload, _digest, _size, identity = g7._read_stable_file_snapshot(
        marker,
        root=root,
        noun=noun,
        required_links=2 if pending_exists else 1,
        maximum_bytes=g7.MAX_JSON_BYTES,
    )
    receipt = g7._decode_json(payload, noun=noun)
    if identity[-2:] != (int(os.geteuid()), 0o600):
        _fail("g8 migration marker is not private")
    if pending_exists:
        marker_stat = os.stat(marker, follow_symlinks=False)
        pending_stat = os.stat(pending, follow_symlinks=False)
        if (marker_stat.st_dev, marker_stat.st_ino) != (
            pending_stat.st_dev,
            pending_stat.st_ino,
        ):
            _fail("g8 pending receipt is not the marker hardlink")
    return receipt, identity


def _target_population(target_root: Path) -> tuple[set[Path], set[Path]]:
    stores = set(_store_relative_files())
    allowed = stores | {
        Path(PREPARED_RECEIPT),
        Path(PENDING_MARKER),
        Path(MIGRATION_MARKER),
    }
    present: set[Path] = set()
    unexpected: set[Path] = set()
    for path in target_root.rglob("*"):
        if path.is_dir() and not path.is_symlink():
            continue
        relative = path.relative_to(target_root)
        if relative in allowed:
            present.add(relative)
        else:
            unexpected.add(relative)
    return present, unexpected


def _finish_target_publication(
    *,
    root: Path,
    target_root: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    route_binding: Mapping[str, Any],
) -> bool:
    marker = target_root / MIGRATION_MARKER
    pending = target_root / PENDING_MARKER
    prepared_receipt = target_root / PREPARED_RECEIPT
    if not os.path.lexists(target_root):
        candidates = sorted(target_root.parent.glob(f"{PREPARED_STAGE_PREFIX}*"))
        if not candidates:
            return False
        if len(candidates) != 1:
            _fail("g8 prepared-stage population is ambiguous")
        stage = candidates[0]
        receipt = g7._load_json(
            stage / PREPARED_RECEIPT,
            root=root,
            noun="orphan prepared g8 migration receipt",
        )
        _validate_receipt_identity(
            receipt,
            root=root,
            population=population,
            policy=policy,
            route_binding=route_binding,
        )
        g7._retire_private_stage_coordination_locks(stage)
        _validate_prepared(
            root=root,
            target_root=target_root,
            stage_root=stage,
            receipt=receipt,
        )
        _publish_stage(
            root=root,
            stage_root=stage,
            target_root=target_root,
            receipt=receipt,
        )
        return True

    g7._assert_private_directory(target_root)
    present, unexpected = _target_population(target_root)
    if unexpected:
        _fail("g8 target contains unrecognized artifacts")
    if os.path.lexists(marker):
        receipt, _identity = _load_marker_snapshot(
            root=root, target_root=target_root, noun="g8 migration marker"
        )
        _validate_receipt_identity(
            receipt,
            root=root,
            population=population,
            policy=policy,
            route_binding=route_binding,
        )
        expected = set(_store_relative_files()) | {Path(MIGRATION_MARKER)}
        if os.path.lexists(pending):
            expected.add(Path(PENDING_MARKER))
        if present != expected:
            _fail("g8 marker lacks the exact store/receipt population")
        _validate_stores(root=root, target_root=target_root, receipt=receipt)
        if os.path.lexists(pending):
            pending.unlink()
            g7._fsync_directory(target_root)
        return True
    if os.path.lexists(prepared_receipt):
        if os.path.lexists(pending):
            _fail("g8 target has ambiguous prepared receipts")
        receipt = g7._load_json(
            prepared_receipt,
            root=root,
            noun="renamed prepared g8 migration receipt",
        )
        _validate_receipt_identity(
            receipt,
            root=root,
            population=population,
            policy=policy,
            route_binding=route_binding,
        )
        if present != set(_store_relative_files()) | {Path(PREPARED_RECEIPT)}:
            _fail("g8 renamed prepared target is incomplete")
        _validate_stores(root=root, target_root=target_root, receipt=receipt)
        os.rename(prepared_receipt, pending)
        g7._fsync_directory(target_root)
    elif os.path.lexists(pending):
        receipt = g7._load_json(
            pending, root=root, noun="pending g8 migration receipt"
        )
        _validate_receipt_identity(
            receipt,
            root=root,
            population=population,
            policy=policy,
            route_binding=route_binding,
        )
        if present != set(_store_relative_files()) | {Path(PENDING_MARKER)}:
            _fail("g8 pending target is incomplete")
        _validate_stores(root=root, target_root=target_root, receipt=receipt)
    else:
        _fail("g8 runtime exists without a prepared, pending, or final receipt")
    os.link(pending, marker, follow_symlinks=False)
    g7._fsync_directory(target_root)
    pending.unlink()
    g7._fsync_directory(target_root)
    return True


def _publish_stage(
    *, root: Path, stage_root: Path, target_root: Path, receipt: Mapping[str, Any]
) -> None:
    if os.path.lexists(target_root):
        _fail("g8 target already exists before atomic publication")
    _validate_prepared(
        root=root,
        target_root=target_root,
        stage_root=stage_root,
        receipt=receipt,
    )
    os.rename(stage_root, target_root)
    g7._fsync_directory(target_root.parent)
    prepared = target_root / PREPARED_RECEIPT
    pending = target_root / PENDING_MARKER
    marker = target_root / MIGRATION_MARKER
    _validate_stores(root=root, target_root=target_root, receipt=receipt)
    os.rename(prepared, pending)
    g7._fsync_directory(target_root)
    _validate_stores(root=root, target_root=target_root, receipt=receipt)
    os.link(pending, marker, follow_symlinks=False)
    g7._fsync_directory(target_root)
    pending.unlink()
    g7._fsync_directory(target_root)


def _migration_rows(database: Path | str, receipt: Mapping[str, Any]) -> dict[str, Any]:
    connection = g7._open_control_target(database)
    try:
        events = connection.execute(
            "SELECT event_id,stream_id,sequence,global_sequence,event_type,task_cid,"
            "attempt_id,session_id,recorded_at,body_json FROM domain_events "
            "WHERE global_sequence <= ? ORDER BY global_sequence",
            [int(receipt["migration_event_watermark"])],
        ).fetchall()
        evidence = connection.execute(
            "SELECT evidence_id,evidence_kind,digest,body_json FROM evidence_nodes "
            "WHERE evidence_kind=?",
            [MIGRATION_EVIDENCE_KIND],
        ).fetchall()
        plan = connection.execute(
            "SELECT plan_cid,revision,body_json FROM plans WHERE plan_cid=?",
            [receipt["accepted_plan_root_cid"]],
        ).fetchone()
        manifests = {
            table: g7._normalized_rows(connection, table)["row_hashes"]
            for table in receipt["historical_row_hashes"]
        }
    finally:
        connection.close()
    return {
        "migration_event_prefix_digest": g7._identity(
            [g7._canonical_row(row) for row in events]
        ),
        "evidence": [list(row) for row in evidence],
        "plan": list(plan) if plan is not None else None,
        "historical_row_hashes": manifests,
    }


def _live_owner(
    *,
    root: Path,
    target_root: Path,
    policy: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any] | None:
    status_path = target_root / "quack-owner" / "quack-state-server.status.json"
    if not os.path.lexists(status_path):
        return None
    status = g7._load_json(status_path, root=root, noun="g8 Quack owner status")
    lifecycle = str(status.get("lifecycle") or "")
    if lifecycle == "stopped":
        return None
    if lifecycle != "ready":
        _fail("g8 Quack owner lifecycle is not safely inspectable")
    identity = status.get("identity")
    if not isinstance(identity, Mapping):
        _fail("g8 Quack owner identity is absent")
    expected_endpoint = str(policy["target_quack_endpoint"])
    expected_store = str((target_root / "control.duckdb").relative_to(root))
    prior_owner = dict(receipt["prior_owner_identity"])
    expected_extension = str(prior_owner.get("extension_fingerprint") or "")
    try:
        database_path = Path(str(status["database_path"])).resolve()
    except (KeyError, OSError, ValueError) as exc:
        _fail("g8 Quack owner database path is malformed", exc)
    if (
        status.get("interface") != "QuackStateServer@1"
        or identity.get("interface") != "StateServerIdentity@1"
        or identity.get("status") != "ready"
        or identity.get("listen_uri") != expected_endpoint
        or identity.get("extension_fingerprint") != expected_extension
        or status.get("extension_fingerprint") != expected_extension
        or identity.get("store_id") != expected_store
        or status.get("store_id") != expected_store
        or identity.get("database_uuid") != prior_owner["database_uuid"]
        or database_path != (target_root / "control.duckdb").resolve()
        or int(status.get("port") or 0)
        != int(expected_endpoint.rsplit(":", 1)[1])
        or int(identity.get("generation") or 0)
        <= int(prior_owner["generation"])
        or int(identity.get("fence_epoch") or 0)
        != int(identity.get("generation") or 0)
    ):
        _fail("live g8 Quack owner is not the exact successor")
    return dict(status)


def _verify_target(
    *,
    root: Path,
    target_root: Path,
    control_target: Path | str,
    coordination: Sequence[Path],
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    receipt: Mapping[str, Any],
    live_owner: Mapping[str, Any] | None,
    allow_progressed: bool,
) -> dict[str, Any]:
    rows = _migration_rows(control_target, receipt)
    if rows["migration_event_prefix_digest"] != receipt[
        "migration_event_prefix_digest"
    ]:
        _fail("g8 migration event prefix differs")
    if len(rows["evidence"]) != 1:
        _fail("g8 operator provider-route evidence is absent or ambiguous")
    evidence_body = json.loads(str(rows["evidence"][0][3]))
    if (
        rows["evidence"][0][1] != MIGRATION_EVIDENCE_KIND
        or rows["evidence"][0][2] != receipt["suffix"]["migration_digest"]
        or g7._control_plane_content_identity(evidence_body)
        != receipt["suffix"]["migration_digest"]
    ):
        _fail("g8 operator provider-route evidence differs")
    for table, prior_hashes in receipt["historical_row_hashes"].items():
        observed = rows["historical_row_hashes"].get(table, ())
        if Counter(prior_hashes) - Counter(observed):
            _fail(f"g8 lost historical rows in {table}")
    projection = g7._control_projection(control_target)
    if projection["task_definition_digest"] != receipt[
        "target_task_definition_digest"
    ]:
        _fail("g8 current task definitions differ")
    plan = rows["plan"]
    if plan is None or int(plan[1]) < int(policy["prior_plan_revision"]) + 1:
        _fail("g8 provider-route plan revision is absent")
    plan_body = json.loads(str(plan[2]))
    if (
        plan_body.get("current_source_binding") != g7._source_binding(root, population)
        or plan_body.get("provider_route_binding_cid")
        != policy["provider_route_binding_cid"]
    ):
        _fail("g8 active plan source/provider binding differs")
    if live_owner is None:
        settled_by_alias = {
            str(item["task_alias"]): dict(item)
            for item in receipt["suffix"]["coordination_settlements"]
        }
        for settlement in policy["settlements"]:
            lane = int(settlement["lane"])
            projection = g7._coordination_projection(coordination[lane])
            claim = g7._active_claim_for_history(projection, settlement)
            attempts = [
                dict(item)
                for item in projection.get("task_attempts", ())
                if isinstance(item, Mapping)
                and item.get("attempt_id") == settlement["attempt_id"]
            ]
            recorded = settled_by_alias.get(str(settlement["task_alias"]), {})
            if (
                len(attempts) != 1
                or claim.get("state") != settlement["target_claim_state"]
                or attempts[0].get("status")
                != settlement["target_attempt_status"]
                or projection.get("projection_root")
                != recorded.get("post_projection_root")
            ):
                _fail("g8 settled coordination history was not retained")
    if not allow_progressed:
        control = target_root / "control.duckdb"
        if g7._stable_file(control, root=root, noun="g8 control store")[0] != receipt[
            "control_store"
        ]["sha256"]:
            _fail("g8 control store changed before launch")
        for lane, path in enumerate(coordination):
            if g7._stable_file(
                path, root=root, noun=f"g8 lane {lane} coordination"
            )[0] != receipt["coordination_stores"][lane]["sha256"]:
                _fail("g8 coordination store changed before launch")
    if live_owner is not None:
        latest = g7._latest_state_server(control_target)
        live_identity = dict(live_owner["identity"])
        for field in (
            "server_id",
            "store_id",
            "database_uuid",
            "process_birth_id",
            "listen_uri",
            "extension_fingerprint",
            "schema_revision",
            "generation",
            "started_at",
            "status",
        ):
            expected = live_identity[field]
            if field in {"schema_revision", "generation"}:
                expected = int(expected)
            if latest[field] != expected:
                _fail(f"live g8 transport identity differs: {field}")
        if latest["stopped_at"] is not None or latest["status"] != "ready":
            _fail("live g8 transport is not ready")
    connection = g7._open_control_target(control_target)
    try:
        tasks = _control_tasks_from_connection(connection)
        for record_value in policy["provider_role_revisions"]:
            record = dict(record_value)
            task = tasks[str(record["task_alias"])]
            if (
                task["body"].get("provider_role") != "grok-implement"
                or _definition_cid(task) != record["target_definition_cid"]
            ):
                _fail(f"g8 provider role is stale: {record['task_alias']}")
        ready = _ready_aliases(tasks)
    finally:
        connection.close()
    if not allow_progressed and ready != list(receipt["ready_frontier"]):
        _fail("g8 initial ready frontier differs")
    return {
        "schema": CHECK_SCHEMA,
        "valid": True,
        "mode": "check-source-provider-route-migration",
        "allow_progressed": bool(allow_progressed),
        "verification_transport": "quack" if live_owner is not None else "offline",
        "receipt": dict(receipt),
        "ready_task_ids": ready,
    }


def check_source_provider_route(
    *,
    root: Path,
    config: Mapping[str, Any],
    population: Mapping[str, Any],
    allow_progressed: bool,
) -> dict[str, Any]:
    """Verify the g8 immutable prefix without racing its live Quack owner."""

    root = root.resolve()
    policy, route_binding = _policy(config)
    policy["repository_root"] = str(root)
    g7._assert_source_delta(root, population, policy)
    target_root = g7._confined(
        root, policy["target_runtime_root"], noun="g8 runtime root"
    )
    if not os.path.lexists(target_root):
        _fail("g8 runtime root is absent")
    g7._assert_private_directory(target_root)
    receipt, marker_identity = _load_marker_snapshot(
        root=root, target_root=target_root, noun="g8 migration marker"
    )
    _validate_receipt_identity(
        receipt,
        root=root,
        population=population,
        policy=policy,
        route_binding=route_binding,
    )
    control = target_root / "control.duckdb"
    coordination = [
        target_root
        / "state"
        / f"lane-{lane}"
        / "quack-lane-coordination.duckdb"
        for lane in range(4)
    ]
    live_owner = _live_owner(
        root=root,
        target_root=target_root,
        policy=policy,
        receipt=receipt,
    )
    if live_owner is not None and not allow_progressed:
        _fail("initial g8 verification cannot inspect a live owner")
    if live_owner is None:
        if not all(path.is_file() and not path.is_symlink() for path in (control, *coordination)):
            _fail("g8 authoritative store set is incomplete")
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
            offline_state_server_fence,
        )

        try:
            with offline_state_server_fence(
                database_path=control,
                connection_factory=lambda path: g7._open_local_database(
                    path, read_only=True
                ),
            ) as probe:
                g7._close_offline_fence_probe(probe)
                fenced_receipt, fenced_identity = _load_marker_snapshot(
                    root=root,
                    target_root=target_root,
                    noun="fenced g8 migration marker",
                )
                if fenced_receipt != receipt or fenced_identity != marker_identity:
                    _fail("g8 migration marker changed before fenced inspection")
                result = _verify_target(
                    root=root,
                    target_root=target_root,
                    control_target=control,
                    coordination=coordination,
                    population=population,
                    policy=policy,
                    receipt=receipt,
                    live_owner=None,
                    allow_progressed=allow_progressed,
                )
        except ProviderRouteSuccessorError:
            raise
        except Exception as exc:
            _fail("g8 offline authority could not be fenced", exc)
    else:
        result = _verify_target(
            root=root,
            target_root=target_root,
            control_target=str(policy["target_quack_endpoint"]),
            coordination=coordination,
            population=population,
            policy=policy,
            receipt=receipt,
            live_owner=live_owner,
            allow_progressed=allow_progressed,
        )
    final_receipt, final_identity = _load_marker_snapshot(
        root=root, target_root=target_root, noun="final g8 migration marker"
    )
    if final_receipt != receipt or final_identity != marker_identity:
        _fail("g8 migration marker changed during verification")
    _validate_receipt_identity(
        final_receipt,
        root=root,
        population=population,
        policy=policy,
        route_binding=route_binding,
    )
    g7._assert_source_delta(root, population, policy)
    return dict(result)


def _new_private_stage(parent: Path) -> Path:
    stage = Path(tempfile.mkdtemp(prefix=".pctdd-g8-installing.", dir=parent))
    g7._assert_private_directory(stage)
    g7._ensure_private_directory(stage / "state")
    return stage


def migrate_source_provider_route(
    *,
    root: Path,
    config: Mapping[str, Any],
    population: Mapping[str, Any],
) -> dict[str, Any]:
    """Create the fresh g8 authority; never mutate the stopped g7 source."""

    root = root.resolve()
    policy, route_binding = _policy(config)
    policy["repository_root"] = str(root)
    g7._assert_source_delta(root, population, policy)
    target_root = g7._confined(
        root, policy["target_runtime_root"], noun="g8 runtime root"
    )
    marker = target_root / MIGRATION_MARKER
    if os.path.lexists(marker):
        return check_source_provider_route(
            root=root,
            config=config,
            population=population,
            allow_progressed=True,
        )

    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        offline_state_server_fence,
    )

    prior_control = g7._confined(
        root,
        policy["prior_control_store"]["path"],
        noun="stopped g7 control store",
    )
    predecessor_fence = offline_state_server_fence(
        database_path=prior_control,
        connection_factory=lambda path: g7._open_local_database(
            path, read_only=True
        ),
    )
    predecessor_connection: Any | None = None
    lock_directory = target_root.parent / ".pctdd-g8-migration-locks"
    g7._ensure_private_directory(lock_directory)
    lock_path = lock_directory / LOCK_NAME
    descriptor: int | None = None
    lock_identity: tuple[int, int] | None = None
    stage_root: Path | None = None
    try:
        predecessor_connection = predecessor_fence.__enter__()
        prior = _assert_prior_anchor(
            root,
            policy,
            fenced_connection=predecessor_connection,
        )
        descriptor, lock_identity = g7._open_migration_lock(lock_path)
        deadline = time.monotonic() + 10.0
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    _fail("timed out acquiring g8 migration lock", exc)
                time.sleep(0.02)
        g7._assert_migration_lock_identity(lock_path, descriptor, lock_identity)
        if _finish_target_publication(
            root=root,
            target_root=target_root,
            population=population,
            policy=policy,
            route_binding=route_binding,
        ):
            result = check_source_provider_route(
                root=root,
                config=config,
                population=population,
                allow_progressed=False,
            )
            g7._assert_migration_lock_identity(
                lock_path, descriptor, lock_identity
            )
            g7._assert_source_delta(root, population, policy)
            return result

        stage_root = _new_private_stage(target_root.parent)
        stage_control = stage_root / "control.duckdb"
        g7._copy_anchored_file(
            prior["control"],
            stage_control,
            root=root,
            record=policy["prior_control_store"],
            noun="stopped g7 control store",
        )
        coordination_paths: list[Path] = []
        for item in prior["coordination"]:
            lane = int(item["policy"]["lane"])
            target = (
                stage_root
                / "state"
                / f"lane-{lane}"
                / "quack-lane-coordination.duckdb"
            )
            g7._copy_with_optional_wal(
                item["database"],
                item["wal"],
                target,
                root=root,
                record=item["policy"],
                noun=f"g7 lane {lane} coordination store",
            )
            coordination_paths.append(target)

        observations: list[tuple[str, Path]] = [
            ("main-control", stage_control),
            *(
                (f"lane-{lane}-coordination", path)
                for lane, path in enumerate(coordination_paths)
            ),
        ]
        observation_root = stage_root / ".execution-observation-verification"
        for item in prior["coordination"]:
            lane = int(item["policy"]["lane"])
            target = observation_root / f"lane-{lane}.duckdb"
            g7._copy_with_optional_wal(
                item["execution_database"],
                item["execution_wal"],
                target,
                root=root,
                record=item["execution_record"],
                noun=f"g7 lane {lane} execution observation",
            )
            observations.append((f"lane-{lane}-execution", target))
        _assert_pre_effect_attempts(observations, policy["settlements"])

        settlements: list[dict[str, Any]] = []
        by_lane = {
            int(item["lane"]): dict(item) for item in policy["settlements"]
        }
        for lane, database in enumerate(coordination_paths):
            expected = by_lane.get(lane)
            if expected is None:
                continue
            settled = _settle_coordination_attempt(database, expected)
            settlements.append({**settled, **expected})
        settlements.sort(key=lambda item: EXPECTED_TASK_ALIASES.index(item["task_alias"]))
        if [item["task_alias"] for item in settlements] != list(
            EXPECTED_TASK_ALIASES
        ):
            _fail("g8 did not settle the exact stranded task pair")
        suffix = _apply_control_suffix(
            stage_control,
            root=root,
            population=population,
            policy=policy,
            route_binding=route_binding,
            coordination_settlements=settlements,
            prior_projection=prior["control_projection"],
        )
        g7._checkpoint_database(stage_control)
        verified = _verify_staged_successor(
            stage_root=stage_root,
            database=stage_control,
            coordination_paths=coordination_paths,
            population=population,
            policy=policy,
            prior_projection=prior["control_projection"],
            suffix=suffix,
        )
        g7._retire_private_stage_coordination_locks(stage_root)
        receipt = _receipt(
            root=root,
            population=population,
            policy=policy,
            route_binding=route_binding,
            prior_projection=prior["control_projection"],
            verified=verified,
        )
        stage_root = _arm_prepared(
            root=root,
            target_root=target_root,
            stage_root=stage_root,
            receipt=receipt,
        )
        g7._assert_source_delta(root, population, policy)
        _assert_prior_anchor(
            root,
            policy,
            fenced_connection=predecessor_connection,
        )
        g7._assert_migration_lock_identity(lock_path, descriptor, lock_identity)
        _publish_stage(
            root=root,
            stage_root=stage_root,
            target_root=target_root,
            receipt=receipt,
        )
        observed, _identity = _load_marker_snapshot(
            root=root, target_root=target_root, noun="published g8 migration marker"
        )
        if observed != receipt:
            _fail("published g8 migration receipt changed")
        g7._assert_migration_lock_identity(lock_path, descriptor, lock_identity)
        g7._assert_source_delta(root, population, policy)
        return {
            "schema": CHECK_SCHEMA,
            "valid": True,
            "mode": "migrate-source-provider-route",
            "migration_required": False,
            "receipt": receipt,
            "target_runtime_root": str(target_root.relative_to(root)),
            "ready_task_ids": list(receipt["ready_frontier"]),
        }
    finally:
        if descriptor is not None:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
            except OSError:
                pass
            os.close(descriptor)
        if stage_root is not None and stage_root.exists():
            if not stage_root.name.startswith(PREPARED_STAGE_PREFIX):
                shutil.rmtree(stage_root)
        if predecessor_connection is not None:
            predecessor_fence.__exit__(None, None, None)


def _load_cli_inputs(config_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    materializer_path = root / "scripts/materialize_parallel_content_sealing_proof_carrying_tdd_program.py"
    spec = importlib.util.spec_from_file_location("pctdd_g8_materializer", materializer_path)
    if spec is None or spec.loader is None:
        _fail("PCTDD materializer cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    board, config, _raw = module._load_board(config_path)
    population = module._population(board, config)
    return root, dict(config), dict(population)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("migrate", "check"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--allow-progressed", action="store_true")
    args = parser.parse_args(argv)
    root, config, population = _load_cli_inputs(args.config.resolve())
    if args.command == "migrate":
        result = migrate_source_provider_route(
            root=root, config=config, population=population
        )
    else:
        result = check_source_provider_route(
            root=root,
            config=config,
            population=population,
            allow_progressed=bool(args.allow_progressed),
        )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


__all__ = (
    "CHECK_SCHEMA",
    "EVIDENCE_SCHEMA",
    "MIGRATION_SCHEMA",
    "PRE_EFFECT_SCHEMA",
    "RECEIPT_SCHEMA",
    "ProviderRouteSuccessorError",
    "capture_stopped_source_provider_route_authority",
    "check_source_provider_route",
    "migrate_source_provider_route",
)


if __name__ == "__main__":
    raise SystemExit(main())
