#!/usr/bin/env python3
"""Start the sealed DOEP board through the existing Quack supervisor runtime.

This is deliberately a bootstrap adapter, not a scheduler or state authority.
It owns one existing ``QuackStateServer``, seals the existing typed execution
route, and conveys PID-bound grants to the existing configured-board
supervisors over an inherited private socket.  Task mutation remains owned by
the canonical Quack/DuckDB transition service.  DuckLake remains a
non-authoritative, rebuildable projection.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import socket
import struct
import sys
import threading
import time
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

ROOT: Final = Path(__file__).resolve().parents[3]
ACCELERATE_ROOT: Final = ROOT / "external" / "ipfs_accelerate"
for _path in (str(ACCELERATE_ROOT), str(ROOT)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

PROGRAM_ID: Final = "agent-supervisor-direct-objective-and-event-driven-planning-v1"
CONFIG: Final = (
    ROOT / "config/agent_supervisor_direct_objective_event_driven_planning_scheduler.json"
)
BOARD: Final = ROOT / "config/agent_supervisor_direct_objective_event_driven_planning_board.json"
OWNER_SESSION: Final = "doep-v1-executor"
GRANT_TTL_SECONDS: Final = 86_400.0
OPERATOR_SCHEMA: Final = "ipfs_accelerate_py/agent-supervisor/doep-bootstrap-handoff@1"
BROKER_SCHEMA: Final = "ipfs_accelerate_py/agent-supervisor/doep-bootstrap-broker@1"
LIVE_STATUS_SCHEMA: Final = "ipfs_accelerate_py/agent-supervisor/doep-live-status@1"
RUNTIME_PROJECTION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/doep-runtime-markdown-projection@1"
)
RUNTIME_PROJECTION_RECEIPT_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/doep-runtime-markdown-projection-receipt@1"
)
RUNTIME_PROJECTION_RENDERER: Final = "doep-runtime-markdown-renderer-v1"
BLOCKED_RETRY_RECOVERY_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/doep-blocked-retry-bootstrap@1"
)
BLOCKED_RETRY_EVIDENCE_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/doep-blocked-retry-evidence@1"
)
BLOCKED_RETRY_TASK_ALIAS: Final = "DOEP-030"
BLOCKED_RETRY_TASK_CID: Final = (
    "sha256:b8cf8ce01eaa5a1ac744d169ba756d37146bfaaef5a52087f005d268b92410b7"
)
BLOCKED_RETRY_REASON: Final = "implementation_protected_path_verification_lock_timeout"
BLOCKED_RETRY_ATTEMPT_RELATIVE: Final = Path(
    "lane-2/doep_lane_2_database_portal_attempts/4cd6f925e2180fedcf9c9a47"
)
BLOCKED_RETRY_WORKSPACE_NAME: Final = "workspace_6b4c063bd5e3_bdd9b20cc1e1"
BLOCKED_RETRY_BRANCH: Final = (
    "implementation/doep-030-b8d4ee0e8de3-attempt-1-1788101472"
)
BLOCKED_RETRY_BASELINE: Final = "fadf091facbf259fec0ff55af3d2104ed16f66df"
BLOCKED_RETRY_EVENT_IDS: Final = {
    12: "sha256:11912cfadf8ba2770ea9fde9d2091b09234eb2b34edf7614e4c8274e60af7829",
    13: "sha256:9c5ed5bdba7c9b2c7e132842dc45c6ec5453f63c1d8cdf55d0470d39745cd82c",
    14: "sha256:1b8663745aa9c30d13acded849bcbf4458bd2c4e9a64331b9d07369802de7eea",
}
QUACK_RE: Final = re.compile(
    r"^quack:(?://)?(127(?:\.\d{1,3}){3}|localhost):(\d{1,5})$",
    re.IGNORECASE,
)
ACTIVE_STATUSES: Final = frozenset(
    {
        "claimed",
        "dispatched",
        "provider_starting",
        "provider_running",
        "provider_completed",
        "in_progress",
        "running",
        "validating",
        "validation_succeeded",
        "merge_pending",
        "merging",
        "reconciliation_pending",
    }
)
FAILED_STATUSES: Final = frozenset(
    {"blocked", "failed", "terminal_failed", "quarantined", "rejected"}
)
TERMINAL_STATUSES: Final = frozenset(
    {
        "completed",
        "complete",
        "done",
        "skipped",
        "cancelled",
        "terminal_succeeded",
        "terminal_failed",
        "quarantined",
        "rejected",
    }
)


class HandoffError(RuntimeError):
    """Fail-closed error at the narrow DOEP handoff boundary."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _atomic_bytes(path: Path, payload: bytes) -> None:
    """Replace one disposable projection without exposing partial bytes."""

    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}.{threading.get_ident()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        dict(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def _sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _markdown_text(value: Any) -> str:
    return (
        str(value or "")
        .replace("\\", "\\\\")
        .replace("|", "\\|")
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )


def _projection_header(
    *,
    title: str,
    snapshot: Mapping[str, Any],
    generation: Mapping[str, Any],
) -> list[str]:
    return [
        f"# {title}",
        "",
        "> **NON-AUTHORITATIVE RUNTIME PROJECTION.** The sole operational task source is "
        "> DuckDB through the exclusive Quack state owner. This file is never ingested, "
        "> claimed from, or used to terminalize work; deleting it only causes regeneration.",
        "",
        f"- Projection schema: `{RUNTIME_PROJECTION_SCHEMA}`",
        f"- Renderer: `{RUNTIME_PROJECTION_RENDERER}`",
        "- Source authority: `DuckDB -> exclusive QuackStateServer -> TypedDatabaseTaskSource`",
        f"- Store ID: `{_markdown_text(generation.get('store_id'))}`",
        f"- Database UUID: `{_markdown_text(generation.get('database_uuid'))}`",
        f"- Store generation: `{int(generation.get('generation') or 0)}`",
        f"- Fence epoch: `{int(generation.get('fence_epoch') or 0)}`",
        f"- Store revision: `{int(snapshot.get('revision') or 0)}`",
        f"- Event watermark: `{int(snapshot.get('event_cursor') or 0)}`",
        f"- Database projection CID: `{_markdown_text(snapshot.get('projection_cid'))}`",
        f"- Plan root CID: `{_markdown_text(snapshot.get('plan_root_cid'))}`",
        f"- Repository tree identity: `{_markdown_text(snapshot.get('repository_tree_id'))}`",
        "",
    ]


def _render_runtime_taskboard(
    *,
    snapshot: Mapping[str, Any],
    generation: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
) -> bytes:
    ordered = sorted(
        (dict(task) for task in tasks),
        key=lambda task: (int(task.get("ordinal") or 0), str(task.get("task_alias") or "")),
    )
    statuses = Counter(str(task.get("status") or "unknown") for task in ordered)
    lines = _projection_header(
        title="DOEP current task board (DuckDB projection)",
        snapshot=snapshot,
        generation=generation,
    )
    lines += ["## Status summary", "", "| Status | Tasks |", "| --- | ---: |"]
    lines.extend(
        f"| `{_markdown_text(status)}` | {count} |" for status, count in sorted(statuses.items())
    )
    lines += ["", "## Tasks", ""]
    for task in ordered:
        body = task.get("body")
        body = dict(body) if isinstance(body, Mapping) else {}
        dependencies = task.get("dependencies")
        dependencies = list(dependencies) if isinstance(dependencies, (list, tuple)) else []
        outputs = task.get("outputs")
        outputs = list(outputs) if isinstance(outputs, (list, tuple)) else []
        validations = task.get("validations")
        validations = list(validations) if isinstance(validations, (list, tuple)) else []
        output_paths = [
            str(item.get("path") or "")
            for item in outputs
            if isinstance(item, Mapping) and str(item.get("path") or "")
        ]
        validation_argv = [
            " ".join(str(token) for token in item.get("argv", ()))
            for item in validations
            if isinstance(item, Mapping) and isinstance(item.get("argv"), (list, tuple))
        ]
        alias = _markdown_text(task.get("task_alias") or task.get("task_cid"))
        lines += [
            f"### {alias} {_markdown_text(body.get('title'))}",
            "",
            f"- Status: `{_markdown_text(task.get('status'))}`",
            f"- Revision: `{int(task.get('revision') or 0)}`",
            f"- Task CID: `{_markdown_text(task.get('task_cid'))}`",
            f"- Objective: `{_markdown_text(task.get('objective_id'))}`",
            f"- Goal CID: `{_markdown_text(task.get('goal_cid'))}`",
            f"- Goal ID: `{_markdown_text(body.get('subgoal_id') or body.get('goal_id'))}`",
            f"- Parent goal: `{_markdown_text(body.get('parent_goal_id'))}`",
            f"- Owning repository: `{_markdown_text(body.get('owning_repository'))}`",
            f"- Dependencies: {', '.join(f'`{_markdown_text(item)}`' for item in dependencies) or 'none'}",
            f"- Exact outputs: {', '.join(f'`{_markdown_text(item)}`' for item in output_paths) or 'none'}",
            f"- Exact validation: {'; '.join(f'`{_markdown_text(item)}`' for item in validation_argv) or 'none'}",
            "",
        ]
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _render_runtime_objectives(
    *,
    snapshot: Mapping[str, Any],
    generation: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
) -> bytes:
    grouped: dict[str, dict[str, list[Mapping[str, Any]]]] = {}
    for raw in tasks:
        task = dict(raw)
        objective_id = str(task.get("objective_id") or "unbound-objective")
        goal_cid = str(task.get("goal_cid") or "unbound-goal")
        grouped.setdefault(objective_id, {}).setdefault(goal_cid, []).append(task)
    lines = _projection_header(
        title="DOEP current objective/task satisfaction view (DuckDB projection)",
        snapshot=snapshot,
        generation=generation,
    )
    lines += [
        "This is a task-derived operational view. It does not invent objective or goal semantic status; "
        "those remain canonical database records and are only satisfied by admitted evidence.",
        "",
    ]
    success_statuses = {"completed", "complete", "done", "terminal_succeeded", "skipped"}
    for objective_id, goals in sorted(grouped.items()):
        objective_tasks = [task for goal_tasks in goals.values() for task in goal_tasks]
        objective_counts = Counter(str(task.get("status") or "unknown") for task in objective_tasks)
        lines += [
            f"## Objective `{_markdown_text(objective_id)}`",
            "",
            f"- Task-state counts: `{json.dumps(dict(sorted(objective_counts.items())), sort_keys=True, separators=(',', ':'))}`",
            f"- All task obligations currently satisfied: `{bool(objective_tasks) and all(str(task.get('status') or '') in success_statuses for task in objective_tasks)}`",
            "",
        ]
        for goal_cid, goal_tasks in sorted(goals.items()):
            ordered = sorted(
                goal_tasks,
                key=lambda task: (int(task.get("ordinal") or 0), str(task.get("task_alias") or "")),
            )
            body = ordered[0].get("body") if ordered else {}
            body = dict(body) if isinstance(body, Mapping) else {}
            goal_id = body.get("subgoal_id") or body.get("goal_id") or goal_cid
            counts = Counter(str(task.get("status") or "unknown") for task in ordered)
            lines += [
                f"### Goal `{_markdown_text(goal_id)}`",
                "",
                f"- Goal CID: `{_markdown_text(goal_cid)}`",
                f"- Parent goal: `{_markdown_text(body.get('parent_goal_id'))}`",
                f"- Task-state counts: `{json.dumps(dict(sorted(counts.items())), sort_keys=True, separators=(',', ':'))}`",
                f"- Task obligations satisfied: `{bool(ordered) and all(str(task.get('status') or '') in success_statuses for task in ordered)}`",
                "- Tasks: "
                + ", ".join(
                    f"`{_markdown_text(task.get('task_alias'))}`=`{_markdown_text(task.get('status'))}`@r{int(task.get('revision') or 0)}"
                    for task in ordered
                ),
                "",
            ]
    return ("\n".join(lines).rstrip() + "\n").encode("utf-8")


def _publish_runtime_projections(
    *,
    paths: Mapping[str, Path],
    snapshot: Mapping[str, Any],
    generation: Mapping[str, Any],
    tasks: Sequence[Mapping[str, Any]],
    owner_server_id: str,
    launch_id: str,
) -> dict[str, Any]:
    """Publish disposable views under a stale-writer guard; never mutate authority."""

    taskboard = _render_runtime_taskboard(snapshot=snapshot, generation=generation, tasks=tasks)
    objectives = _render_runtime_objectives(snapshot=snapshot, generation=generation, tasks=tasks)
    material = {
        "schema": RUNTIME_PROJECTION_RECEIPT_SCHEMA,
        "authority": False,
        "source_authority": "DuckDB through exclusive QuackStateServer@1",
        "launch_id": launch_id,
        "owner_server_id": owner_server_id,
        "store_id": str(generation.get("store_id") or ""),
        "database_uuid": str(generation.get("database_uuid") or ""),
        "store_generation": int(generation.get("generation") or 0),
        "fence_epoch": int(generation.get("fence_epoch") or 0),
        "store_revision": int(snapshot.get("revision") or 0),
        "event_cursor": int(snapshot.get("event_cursor") or 0),
        "database_projection_cid": str(snapshot.get("projection_cid") or ""),
        "plan_root_cid": str(snapshot.get("plan_root_cid") or ""),
        "repository_tree_id": str(snapshot.get("repository_tree_id") or ""),
        "renderer": RUNTIME_PROJECTION_RENDERER,
        "task_count": len(tasks),
        "artifacts": {
            "taskboard": {
                "path": str(paths["task_projection"]),
                "sha256": _sha256(taskboard),
                "bytes": len(taskboard),
            },
            "objectives": {
                "path": str(paths["objective_projection"]),
                "sha256": _sha256(objectives),
                "bytes": len(objectives),
            },
        },
    }
    material["receipt_cid"] = _sha256(_canonical_json_bytes(material))
    receipt = {**material, "projected_at": _utc_now()}
    lock_path = paths["projection_receipt"].with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        prior: dict[str, Any] = {}
        if paths["projection_receipt"].is_file():
            try:
                prior = _json_object(paths["projection_receipt"])
            except HandoffError:
                prior = {}
        same_database = bool(
            prior
            and prior.get("store_id") == material["store_id"]
            and prior.get("database_uuid") == material["database_uuid"]
        )
        if same_database:
            prior_position = (
                int(prior.get("store_generation") or 0),
                int(prior.get("store_revision") or 0),
                int(prior.get("event_cursor") or 0),
            )
            current_position = (
                material["store_generation"],
                material["store_revision"],
                material["event_cursor"],
            )
            if prior_position > current_position:
                raise HandoffError(
                    "stale runtime Markdown publisher refused to overwrite a newer database projection"
                )
            if (
                prior_position == current_position
                and prior.get("database_projection_cid") == material["database_projection_cid"]
            ):
                prior_artifacts = prior.get("artifacts")
                if (
                    isinstance(prior_artifacts, Mapping)
                    and dict(prior_artifacts) != material["artifacts"]
                ):
                    raise HandoffError(
                        "runtime Markdown projection is nondeterministic for one database snapshot"
                    )
        _atomic_bytes(paths["task_projection"], taskboard)
        _atomic_bytes(paths["objective_projection"], objectives)
        _atomic_json(paths["projection_receipt"], receipt)
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)
    return receipt


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HandoffError(f"cannot read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise HandoffError(f"JSON root must be an object: {path}")
    return value


def _process_argv(pid: int) -> tuple[str, ...]:
    try:
        payload = Path(f"/proc/{int(pid)}/cmdline").read_bytes()
    except OSError as exc:
        raise HandoffError("supervisor process command line is unavailable") from exc
    if not payload or len(payload) > 131_072:
        raise HandoffError("supervisor process command line is invalid")
    try:
        return tuple(
            item.decode("utf-8") for item in payload.rstrip(b"\x00").split(b"\x00") if item
        )
    except UnicodeDecodeError as exc:
        raise HandoffError("supervisor process command line is not UTF-8") from exc


def _argv_values(argv: Sequence[str], option: str) -> tuple[str, ...]:
    values: list[str] = []
    index = 0
    while index < len(argv):
        token = str(argv[index])
        if token == option:
            if index + 1 >= len(argv):
                raise HandoffError(f"supervisor process {option} has no value")
            values.append(str(argv[index + 1]))
            index += 2
            continue
        if token.startswith(option + "="):
            values.append(token.split("=", 1)[1])
        index += 1
    return tuple(values)


def _pid_alive(pid: int) -> bool:
    return pid > 1 and Path(f"/proc/{pid}").exists()


def _age_seconds(value: Any) -> float | None:
    text = str(value or "")
    if not text:
        return None
    try:
        return max(0.0, (datetime.now(UTC) - datetime.fromisoformat(text)).total_seconds())
    except ValueError:
        return None


def _client_matches(client_id: str, prefix: str) -> bool:
    return client_id == prefix or client_id.startswith(prefix + ":")


def _runtime_paths(board: Any) -> dict[str, Path]:
    program = board.resolved_database_program()
    root = board.path(board.runtime_paths["root"])
    raw = board.payload.get("runtime_paths")
    if not isinstance(raw, Mapping):
        raise HandoffError("scheduler has no runtime path contract")
    paths = {
        "root": root,
        "database": board.path(program.store_id),
        "state": board.path(board.runtime_paths["state"]),
        "logs": board.path(board.runtime_paths["logs"]),
        "evidence": board.path(str(raw["evidence"])),
        "owner": board.path(str(raw["quack_owner"])),
    }
    for name, path in paths.items():
        if name == "root":
            continue
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise HandoffError(f"runtime path {name} escapes the campaign root") from exc
    paths["broker_evidence"] = paths["evidence"] / "runtime/executor-bootstrap.json"
    paths["live_status"] = paths["evidence"] / "control-plane/live-status.json"
    paths["task_projection"] = paths["evidence"] / "control-plane/projections/current-taskboard.md"
    paths["objective_projection"] = (
        paths["evidence"] / "control-plane/projections/current-objectives.md"
    )
    paths["projection_receipt"] = paths["evidence"] / "control-plane/projections/receipt.json"
    paths["blocked_retry_sidecar"] = paths["evidence"] / "bootstrap/doep-030-lock-timeout-evidence.json"
    paths["blocked_retry_authorization"] = paths["evidence"] / "bootstrap/doep-030-lock-timeout-authorization.json"
    paths["blocked_retry_receipt"] = paths["evidence"] / "bootstrap/doep-030-blocked-retry-recovery.json"
    paths["bootstrap_receipt"] = paths["evidence"] / "bootstrap/bootstrap-materialization.json"
    paths["handoff_receipt"] = paths["evidence"] / "bootstrap/supervisor-handoff.json"
    paths["operator_pid"] = paths["state"] / "doep-handoff.pid"
    paths["owner_status"] = paths["owner"] / "quack-state-server.status.json"
    return paths


def _store_id(board: Any) -> str:
    value = str(board.resolved_database_program().store_generation or "").strip()
    if not value or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}", value) is None:
        raise HandoffError("database program has no compact store generation")
    return value


def _make_client(server: Any, board: Any, *, client_id: str) -> tuple[Any, Any, str]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.quack_state_client import (
        QuackStateClient,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
        TypedStateOwnerConnection,
    )

    identity = server.identity
    if identity is None:
        raise HandoffError("Quack owner has no process identity")
    allowed = (
        "whoami_metadata",
        "load_store_generation",
        "executor_control_snapshot",
        "executor_task_projection_page",
        "executor_task_projection_by_identity",
        "executor_retry_cooldown_page",
        "executor_retry_cooldown_by_task",
    )
    token, grant = server.issue_typed_client_grant_record(
        client_id=client_id,
        process_birth_id=identity.process_birth_id,
        allowed_operations=allowed,
        peer_pid=os.getpid(),
        ttl_seconds=GRANT_TTL_SECONDS,
    )
    store_id = _store_id(board)
    client = QuackStateClient(
        owner_id=client_id,
        store_id=store_id,
        process_birth_id=identity.process_birth_id,
        connection_factory=lambda _endpoint: TypedStateOwnerConnection(
            socket_path=server.typed_command_socket_path(),
            token=token,
            client_id=client_id,
            process_birth_id=identity.process_birth_id,
            store_id=store_id,
        ),
    )
    try:
        client.attach(
            board.resolved_database_program().quack_endpoint,
            server_id=identity.server_id,
        )
    except BaseException:
        client.close()
        server.revoke_typed_client_grant(grant.grant_id)
        raise
    return client, grant, token


def _make_blocked_retry_recovery_client(
    server: Any,
    board: Any,
    *,
    task_cid: str,
) -> tuple[Any, Any]:
    """Create the one operator-only client that may re-admit DOEP-030 once."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.quack_state_client import (
        QuackStateClient,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
        TYPED_DATABASE_BLOCKED_RETRY_RECOVERY_COMMAND,
        TypedStateOwnerConnection,
    )

    identity = server.identity
    if identity is None:
        raise HandoffError("Quack owner has no process identity")
    client_id = "doep-bootstrap:blocked-retry:doep-030"
    allowed_operations = (
        "whoami_metadata",
        "load_store_generation",
        "select_task_by_cid",
        "executor_retry_cooldown_by_task",
        "executor_insert_retry_cooldown",
        "executor_cas_task_status_receipt",
        "executor_insert_task_revision",
        "txn_load_generation",
        "txn_lookup_idempotency",
        "txn_advance_store_revision",
        "txn_record_idempotency",
    )
    token, grant = server.issue_typed_client_grant_record(
        client_id=client_id,
        process_birth_id=identity.process_birth_id,
        allowed_operations=allowed_operations,
        allowed_command_operations=(TYPED_DATABASE_BLOCKED_RETRY_RECOVERY_COMMAND,),
        entity_scopes={"task_cid": task_cid},
        peer_pid=os.getpid(),
        ttl_seconds=300.0,
    )
    store_id = _store_id(board)
    client = QuackStateClient(
        owner_id=client_id,
        store_id=store_id,
        process_birth_id=identity.process_birth_id,
        connection_factory=lambda _endpoint: TypedStateOwnerConnection(
            socket_path=server.typed_command_socket_path(),
            token=token,
            client_id=client_id,
            process_birth_id=identity.process_birth_id,
            store_id=store_id,
        ),
    )
    try:
        client.attach(
            board.resolved_database_program().quack_endpoint,
            server_id=identity.server_id,
        )
    except BaseException:
        client.close()
        server.revoke_typed_client_grant(grant.grant_id)
        raise
    return client, grant


def _validated_blocked_retry_events(
    payload: bytes,
    *,
    task_cid: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if not payload or len(payload) > 1_048_576:
        raise HandoffError("DOEP-030 portal event evidence is absent or exceeds its bound")
    events: dict[int, dict[str, Any]] = {}
    try:
        for raw_line in payload.splitlines():
            if not raw_line:
                continue
            value = json.loads(raw_line)
            if not isinstance(value, dict):
                raise HandoffError("DOEP-030 portal event is not an object")
            sequence = value.get("sequence")
            if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 1:
                raise HandoffError("DOEP-030 portal event sequence is invalid")
            if sequence in events:
                raise HandoffError("DOEP-030 portal event sequence is duplicated")
            events[sequence] = value
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HandoffError("DOEP-030 portal event evidence is malformed") from exc
    timeout = events.get(12, {})
    retained = events.get(13, {})
    finished = events.get(14, {})
    common = (
        timeout.get("event_id") == BLOCKED_RETRY_EVENT_IDS[12]
        and retained.get("event_id") == BLOCKED_RETRY_EVENT_IDS[13]
        and finished.get("event_id") == BLOCKED_RETRY_EVENT_IDS[14]
        and timeout.get("task_id") == BLOCKED_RETRY_TASK_ALIAS
        and timeout.get("canonical_task_cid") == task_cid
        and timeout.get("attempt") == 1
        and retained.get("task_id") == BLOCKED_RETRY_TASK_ALIAS
        and retained.get("canonical_task_cid") == task_cid
        and retained.get("attempt") == 1
        and finished.get("task_id") == BLOCKED_RETRY_TASK_ALIAS
        and finished.get("task_cid") == task_cid
        and finished.get("canonical_task_cid") == task_cid
        and finished.get("attempt") == 1
    )
    lock = timeout.get("lock")
    cleanup = retained.get("cleanup_result")
    retained_commit = retained.get("commit_result")
    finished_cleanup = finished.get("cleanup_result")
    finished_commit = finished.get("commit_result")
    merge = finished.get("merge_result")
    preservation = finished.get("failed_preservation_result")
    if not (
        common
        and timeout.get("type") == "implementation_protected_path_verification_lock_timeout"
        and timeout.get("reason") == BLOCKED_RETRY_REASON
        and isinstance(lock, Mapping)
        and lock.get("acquired") is False
        and lock.get("reason") == "lock_exists"
        and retained.get("type") == "protected_path_verification_deferred_worktree_retained"
        and isinstance(cleanup, Mapping)
        and cleanup.get("retained") is True
        and cleanup.get("cleaned") is False
        and cleanup.get("reason") == "verification_deferred_checkout_lease_active"
        and isinstance(retained_commit, Mapping)
        and retained_commit.get("committed") is False
        and retained_commit.get("reason")
        == "verification_deferred_checkout_lease_active"
        and finished.get("type") == "implementation_finished"
        and finished.get("reason") == BLOCKED_RETRY_REASON
        and finished.get("provider_dispatched") is True
        and finished.get("returncode") == 1
        and finished.get("deferred") is True
        and finished.get("attempt_consumed") is False
        and isinstance(finished_cleanup, Mapping)
        and finished_cleanup.get("retained") is True
        and finished_cleanup.get("cleaned") is False
        and isinstance(finished_commit, Mapping)
        and finished_commit.get("committed") is False
        and isinstance(merge, Mapping)
        and merge.get("merged") is False
        and merge.get("reason") == "not_attempted"
        and isinstance(preservation, Mapping)
        and preservation.get("retained") is True
        and preservation.get("preserved") is False
        and not finished.get("implementation_commit")
        and timeout.get("workspace_path") == retained.get("worktree_path")
        and retained.get("worktree_path") == finished.get("worktree_path")
        and retained.get("branch") == BLOCKED_RETRY_BRANCH
        and finished.get("branch") == BLOCKED_RETRY_BRANCH
        and finished.get("baseline_ref") == BLOCKED_RETRY_BASELINE
    ):
        raise HandoffError("DOEP-030 is not the exact retained lock-timeout failure admitted for retry")
    return timeout, retained, finished


def _blocked_retry_task_cid(population: Mapping[str, Any]) -> str:
    matches = [
        str(task.get("task_cid") or "")
        for task in population.get("tasks", ())
        if isinstance(task, Mapping) and task.get("task_alias") == BLOCKED_RETRY_TASK_ALIAS
    ]
    if len(matches) != 1 or matches[0] != BLOCKED_RETRY_TASK_CID:
        raise HandoffError("sealed DOEP population has no unique DOEP-030 identity")
    return matches[0]


def _prepare_blocked_retry_authorization(
    *,
    paths: Mapping[str, Path],
    task_cid: str,
    task_row: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    event_path = paths["state"] / BLOCKED_RETRY_ATTEMPT_RELATIVE / "portal-events.jsonl"
    try:
        event_bytes = event_path.read_bytes()
    except OSError as exc:
        raise HandoffError("DOEP-030 portal event evidence is unavailable") from exc
    timeout, retained, finished = _validated_blocked_retry_events(
        event_bytes,
        task_cid=task_cid,
    )
    try:
        task_body = json.loads(str(task_row.get("body_json") or ""))
    except json.JSONDecodeError as exc:
        raise HandoffError("blocked DOEP-030 task body is malformed") from exc
    terminal = task_body.get("completion_receipt") if isinstance(task_body, Mapping) else None
    if not isinstance(terminal, Mapping):
        raise HandoffError("blocked DOEP-030 has no terminal receipt")
    expected_revision = int(task_row.get("revision") or 0)
    if not (
        task_row.get("status") == "blocked"
        and expected_revision == 4
        and terminal.get("operation") == "database_portal_terminal_failure"
        and terminal.get("reason") == BLOCKED_RETRY_REASON
        and terminal.get("retryable") is False
        and terminal.get("attempt_number") == 1
        and terminal.get("control_expected_status") == "in_progress"
        and terminal.get("control_expected_revision") == 3
    ):
        raise HandoffError("blocked DOEP-030 terminal authority is outside the sealed retry")
    workspace_text = str(
        finished.get("worktree_path") or timeout.get("workspace_path") or ""
    ).strip()
    if not workspace_text or any(marker in workspace_text for marker in ("\x00", "\n", "\r")):
        raise HandoffError("DOEP-030 retained workspace identity is invalid")
    try:
        workspace_path = Path(workspace_text).resolve(strict=True)
        expected_workspace = (
            paths["root"] / "worktrees" / BLOCKED_RETRY_WORKSPACE_NAME
        ).resolve(strict=True)
    except OSError as exc:
        raise HandoffError("DOEP-030 retained workspace is unavailable") from exc
    if workspace_path != expected_workspace or not workspace_path.is_dir():
        raise HandoffError("DOEP-030 retained workspace is unavailable")
    sidecar_material = {
        "schema": BLOCKED_RETRY_EVIDENCE_SCHEMA,
        "task_alias": BLOCKED_RETRY_TASK_ALIAS,
        "task_cid": task_cid,
        "attempt": 1,
        "terminal_reason": BLOCKED_RETRY_REASON,
        "portal_events_path": str(event_path),
        "portal_events_sha256": _sha256(event_bytes),
        "timeout_event_id": str(timeout.get("event_id") or ""),
        "retained_event_id": str(retained.get("event_id") or ""),
        "finished_event_id": str(finished.get("event_id") or ""),
        "workspace_path": str(workspace_path),
        "workspace_branch": str(finished.get("branch") or ""),
        "workspace_baseline": str(finished.get("baseline_ref") or ""),
        "provider_dispatched": True,
        "provider_outcome": "completed_with_verification_deferred",
        "commit_observed": False,
        "merge_observed": False,
        "retained_candidate_admitted": False,
        "historical_candidate_fingerprint": "unavailable",
        "required_next_step": "fresh_portal_revalidation",
        "limitations": [
            "The historical retained workspace had no durable byte-level candidate fingerprint.",
            "Its bytes are not admitted as original provider output and are not completion evidence.",
            "This receipt authorizes one fresh bounded attempt; it does not authorize direct task completion.",
        ],
    }
    sidecar = {
        **sidecar_material,
        "evidence_id": _sha256(_canonical_json_bytes(sidecar_material)),
    }
    now_ms = int(time.time() * 1_000)
    authorized_at = _utc_now()
    authorization_material = {
        "schema": BLOCKED_RETRY_RECOVERY_SCHEMA,
        "operation": "operator_sealed_blocked_retry_authorization",
        "task_alias": BLOCKED_RETRY_TASK_ALIAS,
        "task_cid": task_cid,
        "expected_task_revision": expected_revision,
        "task_body": dict(task_body),
        "terminal_receipt": dict(terminal),
        "max_task_attempts_before": 1,
        "max_task_attempts_after": 2,
        "sidecar_evidence_id": sidecar["evidence_id"],
        "now_ms": now_ms,
        "authorized_at": authorized_at,
        "require_fresh_portal_revalidation": True,
        "authority_scope": "DOEP-030 blocked-to-retrying exactly once",
    }
    authorization = {
        **authorization_material,
        "operator_handoff_receipt_id": _sha256(_canonical_json_bytes(authorization_material)),
    }
    _atomic_json(paths["blocked_retry_sidecar"], sidecar)
    _atomic_json(paths["blocked_retry_authorization"], authorization)
    return sidecar, authorization


def _load_blocked_retry_authorization(
    *,
    paths: Mapping[str, Path],
    task_cid: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    sidecar = _json_object(paths["blocked_retry_sidecar"])
    authorization = _json_object(paths["blocked_retry_authorization"])
    sidecar_material = {key: value for key, value in sidecar.items() if key != "evidence_id"}
    authorization_material = {
        key: value
        for key, value in authorization.items()
        if key != "operator_handoff_receipt_id"
    }
    if not (
        sidecar.get("schema") == BLOCKED_RETRY_EVIDENCE_SCHEMA
        and sidecar.get("task_cid") == task_cid
        and sidecar.get("evidence_id") == _sha256(_canonical_json_bytes(sidecar_material))
        and authorization.get("schema") == BLOCKED_RETRY_RECOVERY_SCHEMA
        and authorization.get("task_cid") == task_cid
        and authorization.get("sidecar_evidence_id") == sidecar.get("evidence_id")
        and authorization.get("operator_handoff_receipt_id")
        == _sha256(_canonical_json_bytes(authorization_material))
    ):
        raise HandoffError("stored DOEP-030 retry authorization has drifted")
    return sidecar, authorization


def _objective_observation(
    paths: Mapping[str, Path], population: Mapping[str, Any]
) -> dict[str, Any]:
    """Read the objective through its canonical repository before Quack starts."""

    from ipfs_accelerate_py.agent_supervisor.task_sources.intent_repository import IntentRepository

    objective = population.get("objective")
    if not isinstance(objective, Mapping):
        raise HandoffError("sealed population has no objective contract")
    objective_id = str(objective.get("objective_id") or "")
    with IntentRepository(
        paths["database"],
        owner_id="doep-bootstrap-observer",
        session_id="doep-bootstrap-observer",
        install_schema=False,
    ) as repository:
        observed = repository.get_objective(objective_id)
    if observed is None or observed.get("title") != objective.get("title"):
        raise HandoffError("canonical objective differs from the sealed DOEP root")
    body = observed.get("body")
    if not isinstance(body, Mapping) or body.get("objective_cid") != objective.get("objective_cid"):
        raise HandoffError("canonical objective body differs from the sealed DOEP identity")
    return dict(observed)


def _seal_route_policy(
    server: Any,
    board: Any,
    population: Mapping[str, Any],
    objective_observation: Mapping[str, Any],
) -> tuple[Any, dict[str, Any]]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.task_execution_route_policy import (
        GROK_CODEX_EXECUTION_MODE,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.typed_database_task_source import (
        TypedDatabaseTaskSource,
    )

    client, grant, _token = _make_client(
        server,
        board,
        client_id="doep-state-owner:execution-route-policy",
    )
    try:
        with TypedDatabaseTaskSource(client, owns_client=True) as source:
            snapshot = source.snapshot()
            page = source.list_tasks(limit=500)
            if page.next_cursor:
                raise HandoffError("DOEP population exceeds the bounded typed task page")
            aliases = {task.task_alias for task in page.tasks}
            expected_aliases = {
                str(task["task_alias"])
                for task in population.get("tasks", ())
                if isinstance(task, Mapping)
            }
            if aliases != expected_aliases or len(aliases) != 85:
                raise HandoffError("typed task population differs from the sealed DOEP board")
            if (
                snapshot.plan_root_cid != population.get("plan_root_cid")
                or snapshot.repository_tree_id != population.get("repository_tree_id")
                or snapshot.goal_count != len(population.get("goals", ()))
                or snapshot.task_count != 85
                or snapshot.dependency_count != 233
            ):
                raise HandoffError("typed snapshot differs from the sealed DOEP identities")
            policy = source.seal_execution_route_policy(
                {alias: GROK_CODEX_EXECUTION_MODE for alias in aliases}
            )
            receipt = {
                "schema": "ipfs_accelerate_py/agent-supervisor/doep-bootstrap-materialization@1",
                "program_id": PROGRAM_ID,
                "verified_at": _utc_now(),
                "objective_id": population.get("objective", {}).get("objective_id"),
                "objective_cid": population.get("objective", {}).get("objective_cid"),
                "objective_revision": int(objective_observation["revision"]),
                "plan_revision": population.get("plan_revision"),
                "plan_root_cid": snapshot.plan_root_cid,
                "repository_tree_id": snapshot.repository_tree_id,
                "projection_cid": snapshot.projection_cid,
                "store_revision": snapshot.revision,
                "event_cursor": snapshot.event_cursor,
                "objective_count": snapshot.objective_count,
                "goal_count": snapshot.goal_count,
                "plan_count": snapshot.plan_count,
                "task_count": snapshot.task_count,
                "dependency_count": snapshot.dependency_count,
                "initial_ready_task_ids": [
                    task.task_alias for task in source.ready_tasks(limit=85).tasks
                ],
                "state_authority": "DuckDB through exclusive QuackStateServer@1",
                "ducklake_authority": False,
            }
            return policy, receipt
    finally:
        server.revoke_typed_client_grant(grant.grant_id)


class _BootstrapBroker:
    """Issue narrowly scoped, PID-bound grants to canonical lane processes."""

    def __init__(
        self,
        *,
        listener: socket.socket,
        server: Any,
        board: Any,
        paths: Mapping[str, Path],
        policy: Any,
        launch_id: str,
    ) -> None:
        self.listener = listener
        self.server = server
        self.board = board
        self.paths = paths
        self.policy = policy
        self.launch_id = launch_id
        self.stopping = threading.Event()
        self.failure = ""
        self._accepted: socket.socket | None = None
        self._lock = threading.Lock()
        self._grants: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._thread = threading.Thread(target=self._run, name="doep-bootstrap-broker", daemon=True)

    def start(self) -> None:
        identity = self.server.identity
        if identity is None:
            raise HandoffError("Quack owner has no broker identity")
        _atomic_json(
            self.paths["broker_evidence"],
            {
                "schema": BROKER_SCHEMA,
                "ready": False,
                "launch_id": self.launch_id,
                "operator_pid": os.getpid(),
                "updated_at": _utc_now(),
                "accepted_lane_count": 0,
                "accepted_supervisor_reader_count": 0,
                "expected_lane_count": int(self.board.max_lanes),
                "server_id": identity.server_id,
                "state_owner_process_birth_id": identity.process_birth_id,
                "execution_route_policy": self.policy.public_summary(),
                "current": [],
                "history": [],
            },
        )
        self._thread.start()

    def stop(self) -> None:
        self.stopping.set()
        with self._lock:
            accepted = self._accepted
        if accepted is not None:
            try:
                accepted.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        try:
            self.listener.close()
        except OSError:
            pass
        self._thread.join(timeout=5.0)
        with self._lock:
            grants = tuple(self._grants.values())
            self._grants.clear()
        for item in grants:
            grant_id = str(item.get("grant_id") or "")
            if grant_id:
                self.server.revoke_typed_client_grant(grant_id)

    def _validate_parent(self, *, peer_pid: int, client_id: str) -> None:
        from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import read_process_birth

        supervisor_prefix = f"database-implementation-supervisor:{OWNER_SESSION}"
        daemon_prefix = f"database-implementation-daemon:{OWNER_SESSION}"
        is_daemon = _client_matches(client_id, daemon_prefix)
        if not is_daemon and not _client_matches(client_id, supervisor_prefix):
            raise HandoffError("bootstrap client is not an admitted DOEP lane")
        peer_birth = read_process_birth(peer_pid)
        if peer_birth is None or int(peer_birth.parent_pid) <= 1:
            raise HandoffError("bootstrap peer has no live supervisor ancestry")
        if is_daemon:
            supervisor_pid = int(peer_birth.parent_pid)
            supervisor_birth = read_process_birth(supervisor_pid)
            if supervisor_birth is None or int(supervisor_birth.parent_pid) != os.getpid():
                raise HandoffError("executor is outside the admitted supervisor tree")
        else:
            supervisor_pid = peer_pid
            if int(peer_birth.parent_pid) != os.getpid():
                raise HandoffError("supervisor is outside the admitted supervisor tree")
        argv = _process_argv(supervisor_pid)
        expected_entry = str(
            (ROOT / "scripts/ops/agent_supervisor/implementation_supervisor_entry.py").resolve()
        )
        expected = {
            "--board-namespace": self.board.board_namespace,
            "--state-owner-bootstrap-fd": str(self.listener.fileno()),
            "--task-shard-count": str(int(self.board.max_lanes)),
        }
        if expected_entry not in argv or any(
            _argv_values(argv, key) != (value,) for key, value in expected.items()
        ):
            raise HandoffError("bootstrap parent differs from the sealed DOEP lane")
        sessions = _argv_values(argv, "--database-owner-session-id")
        shards = _argv_values(argv, "--task-shard-index")
        if len(sessions) != 1 or not sessions[0].startswith(OWNER_SESSION):
            raise HandoffError("bootstrap parent owner session differs")
        if len(shards) != 1 or shards[0] not in {
            str(index) for index in range(int(self.board.max_lanes))
        }:
            raise HandoffError("bootstrap parent shard is outside the sealed lane set")
        if is_daemon:
            daemon_argv = _process_argv(peer_pid)
            daemon_sessions = _argv_values(daemon_argv, "--owner-session-id")
            if (
                _argv_values(daemon_argv, "--task-shard-count") != (str(int(self.board.max_lanes)),)
                or _argv_values(daemon_argv, "--task-shard-index") != shards
                or len(daemon_sessions) != 1
                or not daemon_sessions[0].startswith(OWNER_SESSION)
            ):
                raise HandoffError("executor daemon differs from its sealed lane")

    def _admit(self, request: Mapping[str, Any], *, peer_pid: int, peer_uid: int) -> dict[str, Any]:
        from ipfs_accelerate_py.agent_supervisor.merge.database_worktree_registry import (
            process_birth_id,
        )
        from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
            OwnerLiveness,
            ProcessBirthIdentity,
            owner_liveness,
            read_process_birth,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.state_owner_bootstrap import (
            STATE_OWNER_BOOTSTRAP_REQUEST_SCHEMA,
            STATE_OWNER_BOOTSTRAP_RESPONSE_SCHEMA,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.typed_database_task_source import (
            daemon_required_owner_command_operations,
            daemon_required_owner_operations,
        )

        required = {"schema", "pid", "process_birth", "process_birth_id", "client_id", "store_id"}
        if (
            set(request) != required
            or request.get("schema") != STATE_OWNER_BOOTSTRAP_REQUEST_SCHEMA
        ):
            raise HandoffError("executor bootstrap request differs from its closed schema")
        raw_pid = request.get("pid")
        raw_birth = request.get("process_birth")
        if (
            isinstance(raw_pid, bool)
            or not isinstance(raw_pid, int)
            or raw_pid <= 1
            or not isinstance(raw_birth, Mapping)
        ):
            raise HandoffError("executor bootstrap request has no valid process birth")
        if raw_pid != peer_pid or peer_uid != os.geteuid():
            raise HandoffError("executor bootstrap peer credentials differ")
        observed = read_process_birth(raw_pid)
        supplied = ProcessBirthIdentity.from_dict(dict(raw_birth))
        supplied_birth_id = str(request.get("process_birth_id") or "")
        if (
            observed is None
            or observed != supplied
            or process_birth_id(observed) != supplied_birth_id
        ):
            raise HandoffError("executor bootstrap process birth is stale")
        client_id = str(request.get("client_id") or "")
        daemon_prefix = f"database-implementation-daemon:{OWNER_SESSION}"
        supervisor_prefix = f"database-implementation-supervisor:{OWNER_SESSION}"
        is_daemon = _client_matches(client_id, daemon_prefix)
        is_supervisor = _client_matches(client_id, supervisor_prefix)
        if not (is_daemon or is_supervisor) or request.get("store_id") != _store_id(self.board):
            raise HandoffError("executor bootstrap scope differs from the DOEP admission")
        self._validate_parent(peer_pid=raw_pid, client_id=client_id)
        with self._lock:
            prior = dict(self._grants.get(client_id) or {})
        prior_birth = prior.get("process_birth")
        if isinstance(prior_birth, Mapping):
            identity = ProcessBirthIdentity.from_dict(dict(prior_birth))
            liveness = owner_liveness(identity)
            if liveness is OwnerLiveness.ALIVE:
                raise HandoffError("prior lane process remains live during grant rotation")
            if liveness is OwnerLiveness.UNKNOWN and _pid_alive(
                int(getattr(identity, "pid", 0) or 0)
            ):
                raise HandoffError("prior lane process liveness is unknown")
            prior_grant = str(prior.get("grant_id") or "")
            if prior_grant:
                self.server.revoke_typed_client_grant(prior_grant)
        allowed_operations = (
            daemon_required_owner_operations()
            if is_daemon
            else (
                "executor_control_snapshot",
                "executor_task_projection_by_identity",
                "executor_task_projection_page",
                "load_store_generation",
                "whoami_metadata",
            )
        )
        allowed_commands = daemon_required_owner_command_operations() if is_daemon else ()
        token, grant = self.server.issue_typed_client_grant_record(
            client_id=client_id,
            process_birth_id=supplied_birth_id,
            allowed_operations=allowed_operations,
            allowed_command_operations=allowed_commands,
            peer_pid=raw_pid,
            ttl_seconds=GRANT_TTL_SECONDS,
        )
        owner_identity = self.server.identity
        if owner_identity is None:
            self.server.revoke_typed_client_grant(grant.grant_id)
            raise HandoffError("Quack owner lost identity during bootstrap")
        public = {
            "client_id": client_id,
            "process_birth": supplied.to_dict(),
            "process_birth_id": supplied_birth_id,
            "parent_pid": int(supplied.parent_pid),
            "admitted_at_ns": time.time_ns(),
            "execution_route_policy_id": self.policy.policy_id,
            "credential_transport": "private_inherited_socket",
            "client_role": "executor" if is_daemon else "supervisor_read",
        }
        try:
            with self._lock:
                self._grants[client_id] = {**public, "grant_id": grant.grant_id}
                self._history.append(public)
                self._history = self._history[-128:]
                safe_current = [
                    {key: value for key, value in item.items() if key != "grant_id"}
                    for item in self._grants.values()
                ]
                _atomic_json(
                    self.paths["broker_evidence"],
                    {
                        "schema": BROKER_SCHEMA,
                        "ready": True,
                        "launch_id": self.launch_id,
                        "operator_pid": os.getpid(),
                        "updated_at": _utc_now(),
                        "accepted_lane_count": sum(
                            _client_matches(key, daemon_prefix) for key in self._grants
                        ),
                        "accepted_supervisor_reader_count": sum(
                            _client_matches(key, supervisor_prefix) for key in self._grants
                        ),
                        "expected_lane_count": int(self.board.max_lanes),
                        "server_id": owner_identity.server_id,
                        "state_owner_process_birth_id": owner_identity.process_birth_id,
                        "execution_route_policy": self.policy.public_summary(),
                        "current": safe_current,
                        "history": list(self._history),
                    },
                )
        except BaseException:
            with self._lock:
                current = self._grants.get(client_id)
                if isinstance(current, Mapping) and current.get("grant_id") == grant.grant_id:
                    self._grants.pop(client_id, None)
            self.server.revoke_typed_client_grant(grant.grant_id)
            raise
        return {
            "schema": STATE_OWNER_BOOTSTRAP_RESPONSE_SCHEMA,
            "ok": True,
            "endpoint": self.board.resolved_database_program().quack_endpoint,
            "socket_path": str(self.server.typed_command_socket_path()),
            "store_id": _store_id(self.board),
            "server_id": owner_identity.server_id,
            "client_id": client_id,
            "process_birth_id": supplied_birth_id,
            "token": token,
            "execution_route_policy": self.policy.to_dict(),
        }

    def _run(self) -> None:
        from ipfs_accelerate_py.agent_supervisor.task_sources.state_owner_bootstrap import (
            STATE_OWNER_BOOTSTRAP_RESPONSE_SCHEMA,
            _receive_frame,
            _send_frame,
        )

        self.listener.settimeout(1.0)
        while not self.stopping.is_set():
            accepted: socket.socket | None = None
            try:
                accepted, _address = self.listener.accept()
                with self._lock:
                    self._accepted = accepted
                accepted.settimeout(30.0)
                raw_peer = accepted.getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
                )
                peer_pid, peer_uid, _peer_gid = struct.unpack("3i", raw_peer)
                response = self._admit(
                    _receive_frame(accepted), peer_pid=int(peer_pid), peer_uid=int(peer_uid)
                )
                _send_frame(accepted, response)
            except TimeoutError:
                continue
            except OSError as exc:
                if not self.stopping.is_set() and accepted is None:
                    self.failure = type(exc).__name__
                    os.kill(os.getpid(), signal.SIGTERM)
                    return
            except BaseException as exc:
                if accepted is None:
                    self.failure = type(exc).__name__
                    os.kill(os.getpid(), signal.SIGTERM)
                    return
                try:
                    _send_frame(
                        accepted,
                        {
                            "schema": STATE_OWNER_BOOTSTRAP_RESPONSE_SCHEMA,
                            "ok": False,
                            "error_class": type(exc).__name__,
                            "error": str(exc),
                        },
                    )
                except Exception:
                    pass
            finally:
                if accepted is not None:
                    with self._lock:
                        if self._accepted is accepted:
                            self._accepted = None
                    try:
                        accepted.close()
                    except OSError:
                        pass


class _LiveMonitor:
    def __init__(
        self,
        *,
        server: Any,
        board: Any,
        paths: Mapping[str, Path],
        launch_id: str,
    ) -> None:
        from ipfs_accelerate_py.agent_supervisor.task_sources.typed_database_task_source import (
            TypedDatabaseTaskSource,
        )

        self.server = server
        self.board = board
        self.paths = paths
        self.launch_id = launch_id
        self.stopping = threading.Event()
        self.failure = ""
        self.projection_failure = ""
        self.projection_receipt: dict[str, Any] = {}
        self.client, self.grant, _token = _make_client(
            server, board, client_id="doep-state-owner:live-monitor"
        )
        self.source = TypedDatabaseTaskSource(self.client, owns_client=True)
        self._thread = threading.Thread(target=self._run, name="doep-live-monitor", daemon=True)

    def start(self) -> None:
        self._write()
        self._thread.start()

    def stop(self) -> None:
        self.stopping.set()
        self._thread.join(timeout=10.0)
        try:
            self.source.close()
        finally:
            self.server.revoke_typed_client_grant(self.grant.grant_id)

    def _write(self) -> None:
        snapshot = None
        page = None
        generation = None
        for _attempt in range(4):
            before_generation = self.client.load_generation()
            before_snapshot = self.source.snapshot()
            candidate_page = self.source.list_tasks(limit=500)
            after_snapshot = self.source.snapshot()
            after_generation = self.client.load_generation()
            if (
                not candidate_page.next_cursor
                and before_generation.content_id == after_generation.content_id
                and before_snapshot.projection_cid == after_snapshot.projection_cid
                and before_snapshot.revision == after_snapshot.revision == candidate_page.revision
            ):
                snapshot = after_snapshot
                page = candidate_page
                generation = after_generation
                break
        if snapshot is None or page is None or generation is None:
            raise HandoffError("typed database state changed during the bounded live projection")
        ready = self.source.ready_tasks(limit=85)
        statuses = Counter(task.status for task in page.tasks)
        active = sorted(task.task_alias for task in page.tasks if task.status in ACTIVE_STATUSES)
        failures = sorted(task.task_alias for task in page.tasks if task.status in FAILED_STATUSES)
        terminal = sorted(
            task.task_alias for task in page.tasks if task.status in TERMINAL_STATUSES
        )
        owner_ready = bool(self.server.ready())
        owner_identity = self.server.identity
        try:
            self.projection_receipt = _publish_runtime_projections(
                paths=self.paths,
                snapshot=snapshot.to_dict(),
                generation=generation.to_record(),
                tasks=[task.to_dict() for task in page.tasks],
                owner_server_id="" if owner_identity is None else owner_identity.server_id,
                launch_id=self.launch_id,
            )
            self.projection_failure = ""
        except BaseException as exc:
            # Markdown is disposable observability. Projection failure may not
            # stop, mutate, or weaken the DuckDB/Quack task authority.
            self.projection_failure = f"{type(exc).__name__}: {exc}"
        projection = {
            "authority": False,
            "ready": bool(self.projection_receipt and not self.projection_failure),
            "error": self.projection_failure,
            "receipt_cid": str(self.projection_receipt.get("receipt_cid") or ""),
            "store_revision": int(self.projection_receipt.get("store_revision") or 0),
            "event_cursor": int(self.projection_receipt.get("event_cursor") or 0),
            "database_projection_cid": str(
                self.projection_receipt.get("database_projection_cid") or ""
            ),
            "taskboard_path": str(self.paths["task_projection"]),
            "objectives_path": str(self.paths["objective_projection"]),
            "receipt_path": str(self.paths["projection_receipt"]),
        }
        payload = {
            "schema": LIVE_STATUS_SCHEMA,
            "launch_id": self.launch_id,
            "updated_at": _utc_now(),
            "monitor_pid": os.getpid(),
            "healthy": bool(
                owner_ready and not failures and (active or ready.tasks or snapshot.terminal)
            ),
            "blocked": bool(failures),
            "owner_ready": owner_ready,
            "owner_server_id": "" if owner_identity is None else owner_identity.server_id,
            "plan_root_cid": snapshot.plan_root_cid,
            "repository_tree_id": snapshot.repository_tree_id,
            "projection_cid": snapshot.projection_cid,
            "store_revision": snapshot.revision,
            "event_cursor": snapshot.event_cursor,
            "objective_count": snapshot.objective_count,
            "goal_count": snapshot.goal_count,
            "plan_count": snapshot.plan_count,
            "task_count": snapshot.task_count,
            "dependency_count": snapshot.dependency_count,
            "status_counts": dict(sorted(statuses.items())),
            "ready_task_ids": [task.task_alias for task in ready.tasks],
            "active_task_ids": active,
            "failed_or_blocked_task_ids": failures,
            "terminal_task_ids": terminal,
            "terminal": snapshot.terminal,
            "credential_transport": "private_inherited_socket",
            "raw_token_in_evidence": False,
            "runtime_markdown_projection": projection,
            "ducklake": {
                "configured": True,
                "authority": False,
                "status": "unmeasured",
                "scheduling_prerequisite": False,
            },
        }
        _atomic_json(self.paths["live_status"], payload)

    def _run(self) -> None:
        while not self.stopping.wait(5.0):
            try:
                self._write()
            except BaseException as exc:
                self.failure = f"{type(exc).__name__}: {exc}"
                os.kill(os.getpid(), signal.SIGTERM)
                return


def _listener() -> socket.socket:
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    digest = hashlib.sha256(f"{ROOT}:{os.getpid()}:{time.time_ns()}".encode()).hexdigest()[:32]
    listener.bind("\x00ipfs-accelerate-doep-" + digest)
    listener.listen(16)
    return listener


def _lane_observations(
    paths: Mapping[str, Path],
    broker: Mapping[str, Any],
    *,
    operator_pid: int,
) -> list[dict[str, Any]]:
    """Verify each current daemon and supervisor by process-birth identity."""

    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        OwnerLiveness,
        ProcessBirthIdentity,
        owner_liveness,
        read_process_birth,
    )

    current = broker.get("current")
    current = current if isinstance(current, list) else []
    daemon_prefix = f"database-implementation-daemon:{OWNER_SESSION}"
    by_lane: dict[int, Mapping[str, Any]] = {}
    for record in current:
        if not isinstance(record, Mapping):
            continue
        client_id = str(record.get("client_id") or "")
        if not _client_matches(client_id, daemon_prefix):
            continue
        match = re.search(r":shard:(\d+)-of-(\d+)(?::|$)", client_id)
        if match is None or int(match.group(2)) != 4:
            continue
        by_lane[int(match.group(1))] = record
    observations: list[dict[str, Any]] = []
    for lane in range(4):
        record = by_lane.get(lane)
        status_path = paths["state"] / f"lane-{lane}/doep_lane_{lane}_supervisor_status.json"
        status = _json_object(status_path) if status_path.is_file() else {}
        supervisor_pid = int(status.get("supervisor_pid") or 0)
        daemon_birth_raw = record.get("process_birth") if isinstance(record, Mapping) else None
        status_daemon_birth = status.get("daemon_process_birth")
        daemon_alive = False
        if isinstance(daemon_birth_raw, Mapping):
            try:
                daemon_identity = ProcessBirthIdentity.from_dict(dict(daemon_birth_raw))
                daemon_alive = owner_liveness(daemon_identity) is OwnerLiveness.ALIVE
            except (TypeError, ValueError):
                daemon_alive = False
        supervisor_birth = read_process_birth(supervisor_pid) if supervisor_pid > 1 else None
        supervisor_alive = bool(
            supervisor_birth is not None
            and int(supervisor_birth.parent_pid) == operator_pid
            and _pid_alive(supervisor_pid)
        )
        heartbeat_age = _age_seconds(status.get("updated_at"))
        birth_matches = bool(
            isinstance(daemon_birth_raw, Mapping)
            and isinstance(status_daemon_birth, Mapping)
            and dict(daemon_birth_raw) == dict(status_daemon_birth)
        )
        live = bool(
            record is not None
            and status.get("status") == "running"
            and status.get("supervisor_pid_alive") is True
            and status.get("daemon_pid_alive") is True
            and heartbeat_age is not None
            and heartbeat_age <= 60.0
            and supervisor_alive
            and daemon_alive
            and birth_matches
            and int(record.get("parent_pid") or 0) == supervisor_pid
        )
        observations.append(
            {
                "lane": lane,
                "live": live,
                "supervisor_pid": supervisor_pid,
                "supervisor_birth_alive": supervisor_alive,
                "daemon_pid": int(daemon_birth_raw.get("pid") or 0)
                if isinstance(daemon_birth_raw, Mapping)
                else 0,
                "daemon_birth_alive": daemon_alive,
                "daemon_birth_matches_status": birth_matches,
                "status": str(status.get("status") or "missing"),
                "heartbeat_age_seconds": heartbeat_age,
                "restart_count": int(status.get("restart_count") or 0),
            }
        )
    return observations


def _build_server(board: Any, paths: Mapping[str, Path]) -> Any:
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import build_server

    program = board.resolved_database_program()
    endpoint = QUACK_RE.fullmatch(program.quack_endpoint)
    if endpoint is None:
        raise HandoffError("configured Quack endpoint is not loopback")
    return build_server(
        database_path=paths["database"],
        state_dir=paths["owner"],
        repository_root=ROOT,
        host=endpoint.group(1),
        port=int(endpoint.group(2)),
        repository_id=f"repository:{PROGRAM_ID}",
        store_id=_store_id(board),
        secret_handle=program.endpoint_secret_handle,
        allow_experimental=False,
        allow_legacy_board_unstall=False,
    )


def recover_blocked_lock_timeout() -> int:
    """Operator-seal the one historical DOEP-030 retry through Quack/CAS."""

    board, population, paths = _load()
    prior_pid = 0
    if paths["operator_pid"].is_file():
        try:
            prior_pid = int(paths["operator_pid"].read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            prior_pid = 0
    if _pid_alive(prior_pid):
        raise HandoffError(
            f"stop the live DOEP handoff operator at PID {prior_pid} before sealed recovery"
        )
    task_cid = _blocked_retry_task_cid(population)
    server = _build_server(board, paths)
    client = None
    grant = None
    try:
        identity = server.start()
        if not server.ready():
            raise HandoffError("Quack state owner did not become ready for blocked retry recovery")
        client, grant = _make_blocked_retry_recovery_client(
            server,
            board,
            task_cid=task_cid,
        )
        rows = client.execute("select_task_by_cid", {"task_cid": task_cid})
        if len(rows) != 1:
            raise HandoffError("DOEP-030 task authority is absent or ambiguous")
        task_row = dict(rows[0])
        if (
            paths["blocked_retry_authorization"].is_file()
            and paths["blocked_retry_sidecar"].is_file()
        ):
            sidecar, authorization = _load_blocked_retry_authorization(
                paths=paths,
                task_cid=task_cid,
            )
        else:
            # Both files are immutable once complete.  If the process stopped
            # between their two atomic renames, reconstruct the same evidence
            # from the still-blocked row and exact portal-event identities.
            sidecar, authorization = _prepare_blocked_retry_authorization(
                paths=paths,
                task_cid=task_cid,
                task_row=task_row,
            )
        event_path = Path(str(sidecar.get("portal_events_path") or ""))
        try:
            current_event_bytes = event_path.read_bytes()
        except OSError as exc:
            raise HandoffError("DOEP-030 retry evidence disappeared") from exc
        if _sha256(current_event_bytes) != sidecar.get("portal_events_sha256"):
            raise HandoffError("DOEP-030 portal evidence changed after authorization")
        _validated_blocked_retry_events(current_event_bytes, task_cid=task_cid)
        result = client.recover_blocked_task_retry(
            task_cid=task_cid,
            expected_task_revision=int(authorization["expected_task_revision"]),
            task_body=dict(authorization["task_body"]),
            terminal_receipt=dict(authorization["terminal_receipt"]),
            max_task_attempts_before=int(authorization["max_task_attempts_before"]),
            max_task_attempts_after=int(authorization["max_task_attempts_after"]),
            operator_handoff_receipt_id=str(
                authorization["operator_handoff_receipt_id"]
            ),
            sidecar_evidence_id=str(authorization["sidecar_evidence_id"]),
            now_ms=int(authorization["now_ms"]),
            require_fresh_portal_revalidation=True,
        )
        if not result.accepted:
            raise HandoffError(
                f"canonical DOEP-030 blocked retry was not accepted: {result.outcome.value}"
            )
        receipt_material = {
            "schema": BLOCKED_RETRY_RECOVERY_SCHEMA,
            "operation": "doep_030_blocked_retry_recovered",
            "recovered_at": _utc_now(),
            "owner_server_id": identity.server_id,
            "operator_handoff_receipt_id": authorization[
                "operator_handoff_receipt_id"
            ],
            "sidecar_evidence_id": sidecar["evidence_id"],
            "fresh_portal_revalidation_required": True,
            "retained_candidate_admitted": False,
            "result": result.to_dict(),
        }
        receipt_material["receipt_cid"] = _sha256(
            _canonical_json_bytes(receipt_material)
        )
        _atomic_json(paths["blocked_retry_receipt"], receipt_material)
        print(json.dumps(receipt_material, indent=2, sort_keys=True))
        return 0
    finally:
        try:
            if client is not None:
                client.close()
        finally:
            try:
                if grant is not None:
                    server.revoke_typed_client_grant(grant.grant_id)
            finally:
                server.stop()


def _load() -> tuple[Any, dict[str, Any], dict[str, Path]]:
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        load_configured_board,
    )

    board = load_configured_board(CONFIG, repo_root=ROOT)
    if board.board_namespace != PROGRAM_ID or int(board.max_lanes) != 4:
        raise HandoffError("scheduler configuration is not the sealed DOEP campaign")
    population = _json_object(BOARD)
    tasks = population.get("tasks")
    if (
        population.get("board_namespace") != PROGRAM_ID
        or not isinstance(tasks, list)
        or len(tasks) != 85
        or any(
            not isinstance(task, Mapping) or task.get("board_namespace") != PROGRAM_ID
            for task in tasks
        )
    ):
        raise HandoffError("task board is not the sealed DOEP population")
    paths = _runtime_paths(board)
    if not paths["database"].is_file():
        raise HandoffError("canonical DOEP DuckDB materialization is absent")
    return board, population, paths


def launch() -> int:
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        configured_board_launch_plan,
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        main as configured_board_main,
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner import (
        main as multi_supervisor_main,
    )

    board, population, paths = _load()
    preflight = int(
        configured_board_main(["--repo-root", str(ROOT), "--config", str(CONFIG), "preflight"])
    )
    if preflight != 0:
        return preflight
    prior_pid = 0
    if paths["operator_pid"].is_file():
        try:
            prior_pid = int(paths["operator_pid"].read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            prior_pid = 0
    if _pid_alive(prior_pid):
        raise HandoffError(f"DOEP handoff operator is already live at PID {prior_pid}")
    paths["state"].mkdir(parents=True, exist_ok=True, mode=0o700)
    paths["logs"].mkdir(parents=True, exist_ok=True, mode=0o700)
    paths["evidence"].mkdir(parents=True, exist_ok=True, mode=0o700)
    paths["owner"].mkdir(parents=True, exist_ok=True, mode=0o700)
    paths["operator_pid"].write_text(f"{os.getpid()}\n", encoding="utf-8")
    os.chmod(paths["operator_pid"], 0o600)
    objective_observation = _objective_observation(paths, population)
    server = _build_server(board, paths)
    listener: socket.socket | None = None
    broker: _BootstrapBroker | None = None
    monitor: _LiveMonitor | None = None
    prior_environment = dict(os.environ)
    result = 1
    try:
        identity = server.start()
        if not server.ready():
            raise HandoffError("Quack state owner did not become ready")
        policy, bootstrap_receipt = _seal_route_policy(
            server,
            board,
            population,
            objective_observation,
        )
        _atomic_json(paths["bootstrap_receipt"], bootstrap_receipt)
        launch_id = (
            "sha256:"
            + hashlib.sha256(
                f"{PROGRAM_ID}:{os.getpid()}:{identity.process_birth_id}:{time.time_ns()}".encode()
            ).hexdigest()
        )
        listener = _listener()
        broker = _BootstrapBroker(
            listener=listener,
            server=server,
            board=board,
            paths=paths,
            policy=policy,
            launch_id=launch_id,
        )
        broker.start()
        monitor = _LiveMonitor(
            server=server,
            board=board,
            paths=paths,
            launch_id=launch_id,
        )
        monitor.start()
        plan = configured_board_launch_plan(
            board, implement=True, detach=False, duration_seconds=float("inf")
        )
        runner_args = list(plan["argv"])
        for value in (
            "--database-owner-session-id",
            OWNER_SESSION,
            "--state-owner-bootstrap-fd",
            str(listener.fileno()),
            "--state-owner-bootstrap-store-id",
            _store_id(board),
        ):
            runner_args.append(f"--common-arg={value}")
        environment = dict(os.environ)
        python_paths: list[str] = []
        for item in (
            str(ACCELERATE_ROOT),
            str(ROOT),
            *environment.get("PYTHONPATH", "").split(os.pathsep),
        ):
            if item and item not in python_paths:
                python_paths.append(item)
        environment["PYTHONPATH"] = os.pathsep.join(python_paths)
        environment["PYTHONUNBUFFERED"] = "1"
        environment.update({str(key): str(value) for key, value in plan["environment"].items()})
        for secret_name in (
            "IPFS_ACCELERATE_AGENT_QUACK_TOKEN",
            "IPFS_ACCELERATE_AGENT_STATE_OWNER_SOCKET",
            "IPFS_ACCELERATE_AGENT_TYPED_STATE_OWNER_TOKEN",
            "IPFS_ACCELERATE_AGENT_TYPED_STATE_OWNER_SOCKET",
        ):
            environment.pop(secret_name, None)
        os.environ.clear()
        os.environ.update(environment)
        handoff = {
            "schema": OPERATOR_SCHEMA,
            "launch_id": launch_id,
            "started_at": _utc_now(),
            "operator_pid": os.getpid(),
            "program_id": PROGRAM_ID,
            "objective_id": population["objective"]["objective_id"],
            "objective_cid": population["objective"]["objective_cid"],
            "plan_root_cid": policy.plan_root_cid,
            "repository_tree_id": policy.repository_tree_id,
            "execution_route_policy": policy.public_summary(),
            "owner_identity": identity.to_dict(),
            "lanes": int(plan["lanes"]),
            "credential_transport": "private_inherited_socket",
            "raw_token_in_argv_or_environment": False,
            "canonical_runner": "configured_board_scheduler -> multi_supervisor_runner",
        }
        _atomic_json(paths["handoff_receipt"], handoff)
        print(json.dumps(handoff, sort_keys=True), flush=True)
        result = int(multi_supervisor_main(runner_args))
        if broker.failure:
            raise HandoffError(f"executor bootstrap broker failed closed: {broker.failure}")
        if monitor.failure:
            raise HandoffError(f"live monitor failed closed: {monitor.failure}")
        return result
    finally:
        os.environ.clear()
        os.environ.update(prior_environment)
        try:
            if monitor is not None:
                monitor.stop()
        finally:
            try:
                if broker is not None:
                    broker.stop()
                elif listener is not None:
                    listener.close()
            finally:
                try:
                    server.stop()
                finally:
                    try:
                        if paths["operator_pid"].read_text(encoding="utf-8").strip() == str(
                            os.getpid()
                        ):
                            paths["operator_pid"].unlink()
                    except (FileNotFoundError, OSError):
                        pass


def status(*, require_ready: bool) -> int:
    _board, population, paths = _load()
    live = _json_object(paths["live_status"]) if paths["live_status"].is_file() else {}
    broker = _json_object(paths["broker_evidence"]) if paths["broker_evidence"].is_file() else {}
    handoff = _json_object(paths["handoff_receipt"]) if paths["handoff_receipt"].is_file() else {}
    pid = int(live.get("monitor_pid") or handoff.get("operator_pid") or 0)
    age_seconds = _age_seconds(live.get("updated_at"))
    broker_age_seconds = _age_seconds(broker.get("updated_at"))
    lanes = _lane_observations(paths, broker, operator_pid=pid)
    launch_id = str(handoff.get("launch_id") or "")
    owner_identity = handoff.get("owner_identity")
    owner_identity = owner_identity if isinstance(owner_identity, Mapping) else {}
    owner_server_id = str(owner_identity.get("server_id") or "")
    progress_observed = bool(
        live.get("active_task_ids") or live.get("terminal_task_ids") or live.get("terminal") is True
    )
    ready = bool(
        _pid_alive(pid)
        and age_seconds is not None
        and age_seconds <= 20.0
        and launch_id
        and live.get("launch_id") == launch_id
        and broker.get("launch_id") == launch_id
        and int(handoff.get("operator_pid") or 0) == pid
        and int(broker.get("operator_pid") or 0) == pid
        and live.get("owner_server_id") == owner_server_id
        and broker.get("server_id") == owner_server_id
        and broker.get("ready") is True
        and live.get("healthy") is True
        and live.get("blocked") is False
        and live.get("owner_ready") is True
        and live.get("plan_root_cid") == population.get("plan_root_cid")
        and live.get("repository_tree_id") == population.get("repository_tree_id")
        and int(broker.get("accepted_lane_count") or 0) == 4
        and len(lanes) == 4
        and all(lane["live"] for lane in lanes)
        and progress_observed
    )
    output = {
        "schema": OPERATOR_SCHEMA,
        "command": "status",
        "ready": ready,
        "operator_pid": pid,
        "operator_alive": _pid_alive(pid),
        "status_age_seconds": age_seconds,
        "broker_evidence_age_seconds": broker_age_seconds,
        "progress_observed": progress_observed,
        "lanes": lanes,
        "task_authority": live,
        "bootstrap_broker": broker,
        "handoff": handoff,
    }
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if ready or not require_ready else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run")
    commands.add_parser("recover-blocked-lock-timeout")
    status_parser = commands.add_parser("status")
    status_parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            return launch()
        if args.command == "recover-blocked-lock-timeout":
            return recover_blocked_lock_timeout()
        return status(require_ready=bool(args.require_ready))
    except HandoffError as exc:
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "ok": False,
                    "error_class": type(exc).__name__,
                    "error": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
