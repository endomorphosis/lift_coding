#!/usr/bin/env python3
"""Crash-safe PCTDD g6 -> g7 source-binding successor.

This module is a narrow operator adapter over the existing DuckDB task and
coordination authorities.  It never materializes the Markdown board and it
never rewrites accepted task or goal definitions.  It copies one exact,
stopped g6 authority into a private stage, appends one plan-source revision,
records one operator migration evidence node, and retires only the two exact
stranded attempts identified by the sealed migration inventory.

The target is usable only after ``source-migration-receipt.json`` is linked
as the final marker.  Execution databases, read replicas, DuckLake files,
logs, worktrees, Quack owner material, and credentials outside the copied
control database are deliberately not copied.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import shutil
import socket
import stat
import subprocess
import tempfile
import time
import uuid
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timedelta
from datetime import time as datetime_time
from decimal import Decimal
from pathlib import Path, PurePosixPath
from typing import Any, Final

MIGRATION_SCHEMA: Final[str] = "pctdd/source-binding-successor-materialization@1"
EVIDENCE_SCHEMA: Final[str] = "pctdd/operator-control-plane-source-migration@1"
RECEIPT_SCHEMA: Final[str] = "pctdd/source-binding-migration-receipt@1"
CHECK_SCHEMA: Final[str] = "pctdd/source-binding-migration-check@1"
MIGRATION_EVIDENCE_KIND: Final[str] = "operator_control_plane_source_migration"
MIGRATION_MARKER: Final[str] = "source-migration-receipt.json"
PENDING_MARKER: Final[str] = ".source-migration-receipt.pending.json"
LOCK_NAME: Final[str] = ".pctdd-g7-source-migration.lock"
MAX_JSON_BYTES: Final[int] = 2 * 1024 * 1024
MAX_UNKNOWN_OUTCOME_REARMS: Final[int] = 3


class SourceBindingMigrationError(RuntimeError):
    """The source-only successor cannot be proven safe."""


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise SourceBindingMigrationError("migration value is not canonical JSON") from exc


def _identity(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


def _safe_relative(value: Any, *, noun: str) -> str:
    text = str(value or "").strip()
    path = PurePosixPath(text)
    if (
        not text
        or path.is_absolute()
        or "." in path.parts
        or ".." in path.parts
        or "\x00" in text
        or "\n" in text
        or "\r" in text
        or path.as_posix() != text
    ):
        raise SourceBindingMigrationError(f"{noun} is not a confined relative path")
    return text


def _confined(root: Path, value: Any, *, noun: str) -> Path:
    relative = _safe_relative(value, noun=noun)
    candidate = root / relative
    resolved_parent = candidate.parent.resolve()
    if not resolved_parent.is_relative_to(root.resolve()):
        raise SourceBindingMigrationError(f"{noun} escapes the repository")
    return resolved_parent / candidate.name


def _read_stable_file(
    path: Path,
    *,
    root: Path,
    noun: str,
    required_links: int | None = 1,
    maximum_bytes: int | None = None,
) -> tuple[bytes, str, int]:
    if not path.parent.resolve().is_relative_to(root.resolve()):
        raise SourceBindingMigrationError(f"{noun} escapes the repository")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise SourceBindingMigrationError(f"{noun} is absent or unsafe") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or (
            required_links is not None and int(before.st_nlink) != required_links
        ):
            raise SourceBindingMigrationError(
                f"{noun} is not a regular file with the required link count"
            )
        digest = hashlib.sha256()
        payload = bytearray()
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            digest.update(block)
            if maximum_bytes is not None:
                if len(payload) + len(block) > maximum_bytes:
                    raise SourceBindingMigrationError(f"{noun} exceeds its size bound")
                payload.extend(block)
        after = os.fstat(descriptor)
        identity_before = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_nlink,
        )
        identity_after = (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_nlink,
        )
        if identity_before != identity_after:
            raise SourceBindingMigrationError(f"{noun} changed while read")
        return bytes(payload), digest.hexdigest(), int(before.st_size)
    finally:
        os.close(descriptor)


def _stable_file(
    path: Path,
    *,
    root: Path,
    noun: str,
    required_links: int | None = 1,
) -> tuple[str, int]:
    _payload, digest, size = _read_stable_file(
        path,
        root=root,
        noun=noun,
        required_links=required_links,
    )
    return digest, size


def _load_json(
    path: Path,
    *,
    root: Path,
    noun: str,
    required_links: int = 1,
) -> dict[str, Any]:
    payload, _digest, _size = _read_stable_file(
        path,
        root=root,
        noun=noun,
        required_links=required_links,
        maximum_bytes=MAX_JSON_BYTES,
    )

    def closed(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise SourceBindingMigrationError(f"{noun} has duplicate key {key!r}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise SourceBindingMigrationError(f"{noun} has non-finite value {value!r}")

    try:
        value = json.loads(
            payload.decode("utf-8"),
            object_pairs_hook=closed,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SourceBindingMigrationError(f"{noun} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise SourceBindingMigrationError(f"{noun} must contain an object")
    return value


def _open_local_database(database: Path, *, read_only: bool) -> Any:
    """Open DuckDB with the supervisor's locked, no-external-access policy."""

    import duckdb
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
        connect_duckdb_with_policy,
    )

    return connect_duckdb_with_policy(duckdb, database, read_only=read_only)


def _open_control_target(target: Path | str) -> Any:
    """Open a local authority or authenticated Quack transport uniformly."""

    if isinstance(target, Path):
        return _open_local_database(target, read_only=True)
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
        open_duckdb_connection,
    )

    return open_duckdb_connection(target)


def _git(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if result.returncode:
        raise SourceBindingMigrationError(
            f"git {' '.join(arguments)} failed: {result.stderr.strip()}"
        )
    return result.stdout.strip()


def _policy(config: Mapping[str, Any]) -> dict[str, Any]:
    value = config.get("source_binding_successor_materialization")
    if not isinstance(value, Mapping):
        raise SourceBindingMigrationError("scheduler lacks a source-binding successor policy")
    policy = dict(value)
    if (
        policy.get("schema") != MIGRATION_SCHEMA
        or policy.get("migration_revision") != "PCTDD-SOURCE-G7"
        or policy.get("prior_store_generation") != "pctdd-v1-g6"
        or policy.get("target_store_generation") != "pctdd-v1-g7"
        or policy.get("target_quack_endpoint") != "quack:127.0.0.1:27278"
        or policy.get("receipt_marker") != MIGRATION_MARKER
    ):
        raise SourceBindingMigrationError("source-binding successor policy identity differs")
    coordination = policy.get("coordination_stores")
    if not isinstance(coordination, list) or [item.get("lane") for item in coordination if isinstance(item, Mapping)] != [0, 1, 2, 3]:
        raise SourceBindingMigrationError("source-binding policy must name four ordered lanes")
    return policy


def _source_binding(root: Path, population: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "source_head": str(population["source_head"]),
        "repository_tree_id": str(population["repository_tree_id"]),
        "current_plan_root_cid": str(population["plan_root_cid"]),
        "source_forest_root": str(population["source_forest"]["source_forest_root"]),
        "source_identities": dict(population["source_identities"]),
    }


def _assert_source_delta(
    root: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> None:
    anchor = str(policy["control_source_anchor_head"])
    current = str(population["source_head"])
    if _git(root, "rev-parse", "HEAD") != current:
        raise SourceBindingMigrationError("population source head is not current HEAD")
    if _git(root, "rev-parse", f"{anchor}^{{tree}}") != policy["control_source_anchor_tree"]:
        raise SourceBindingMigrationError("sealed control source anchor tree differs")
    _git(root, "merge-base", "--is-ancestor", anchor, current)
    if _git(root, "rev-parse", f"{current}^{{tree}}") != population["repository_tree_id"]:
        raise SourceBindingMigrationError("current source tree binding differs")
    status = _git(root, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise SourceBindingMigrationError("source-binding migration requires a clean tree")
    changed: dict[str, str] = {}
    output = _git(root, "diff", "--name-status", "--no-renames", anchor, current, "--")
    for line in output.splitlines():
        fields = line.split("\t")
        if len(fields) != 2 or fields[0] not in {"A", "M"} or fields[1] in changed:
            raise SourceBindingMigrationError(f"source migration delta is not control-only: {line}")
        changed[fields[1]] = fields[0]
    allowed = {str(item) for item in policy.get("operator_control_paths", ())}
    if not changed or not set(changed).issubset(allowed):
        raise SourceBindingMigrationError(
            "source migration changed paths outside operator controls: "
            + ", ".join(sorted(set(changed) - allowed))
        )
    for relative, expected in dict(policy["governed_gitlinks"]).items():
        if _git(root, "rev-parse", f"{current}:{relative}") != expected:
            raise SourceBindingMigrationError(f"governed gitlink differs: {relative}")


def _assert_listener_stopped(policy: Mapping[str, Any]) -> None:
    endpoint = str(policy["target_quack_endpoint"])
    _, host, port_text = endpoint.split(":", 2)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.settimeout(0.2)
        if probe.connect_ex((host, int(port_text))) == 0:
            raise SourceBindingMigrationError("the predecessor Quack listener is still active")


def _file_anchor(
    root: Path,
    record: Mapping[str, Any],
    *,
    noun: str,
) -> Path:
    path = _confined(root, record["path"], noun=noun)
    observed = _stable_file(path, root=root, noun=noun)
    expected = (str(record["sha256"]), int(record["size_bytes"]))
    if observed != expected:
        raise SourceBindingMigrationError(f"{noun} byte anchor differs")
    return path


def _copy_anchored_file(
    source: Path,
    target: Path,
    *,
    root: Path,
    record: Mapping[str, Any],
    noun: str,
) -> None:
    """Copy one sealed regular file while proving the source did not change."""

    expected = (str(record["sha256"]), int(record["size_bytes"]))
    if not source.parent.resolve().is_relative_to(root.resolve()):
        raise SourceBindingMigrationError(f"{noun} escapes the repository")
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    source_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    target_flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    source_fd = os.open(source, source_flags)
    target_fd: int | None = None
    try:
        before = os.fstat(source_fd)
        if not stat.S_ISREG(before.st_mode) or int(before.st_nlink) != 1:
            raise SourceBindingMigrationError(f"{noun} is not an exact regular source")
        target_fd = os.open(target, target_flags, 0o600)
        digest = hashlib.sha256()
        copied = 0
        while True:
            block = os.read(source_fd, 1024 * 1024)
            if not block:
                break
            digest.update(block)
            copied += len(block)
            view = memoryview(block)
            while view:
                written = os.write(target_fd, view)
                if written <= 0:
                    raise SourceBindingMigrationError(f"{noun} copy made no progress")
                view = view[written:]
        os.fsync(target_fd)
        after = os.fstat(source_fd)
        source_identity = (
            before.st_dev,
            before.st_ino,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
            before.st_nlink,
        )
        if source_identity != (
            after.st_dev,
            after.st_ino,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
            after.st_nlink,
        ):
            raise SourceBindingMigrationError(f"{noun} changed while copied")
        if (digest.hexdigest(), copied) != expected:
            raise SourceBindingMigrationError(f"{noun} byte anchor differs while copied")
    except BaseException:
        if target_fd is not None:
            os.close(target_fd)
            target_fd = None
        try:
            target.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        os.close(source_fd)
        if target_fd is not None:
            os.close(target_fd)


def _fsync_regular(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise SourceBindingMigrationError("staged database is not a regular file")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _checkpoint_database(database: Path) -> None:
    connection = _open_local_database(database, read_only=False)
    try:
        connection.execute("CHECKPOINT")
    finally:
        connection.close()
    wal = database.with_name(database.name + ".wal")
    if os.path.lexists(wal):
        raise SourceBindingMigrationError("private DuckDB WAL did not checkpoint")
    _fsync_regular(database)


def _canonical_cell(value: Any) -> dict[str, Any]:
    """Encode a DuckDB cell without collapsing SQL types or NULL values."""

    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean", "value": value}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        if not math.isfinite(value):
            raise SourceBindingMigrationError("database projection contains non-finite float")
        return {"type": "float64", "value": value.hex()}
    if isinstance(value, Decimal):
        return {"type": "decimal", "value": str(value)}
    if isinstance(value, str):
        return {"type": "text", "value": value}
    if isinstance(value, (bytes, bytearray, memoryview)):
        return {"type": "bytes", "value": bytes(value).hex()}
    if isinstance(value, datetime):
        return {"type": "datetime", "value": value.isoformat()}
    if isinstance(value, date):
        return {"type": "date", "value": value.isoformat()}
    if isinstance(value, datetime_time):
        return {"type": "time", "value": value.isoformat()}
    if isinstance(value, timedelta):
        return {
            "type": "timedelta",
            "days": int(value.days),
            "seconds": int(value.seconds),
            "microseconds": int(value.microseconds),
        }
    if isinstance(value, uuid.UUID):
        return {"type": "uuid", "value": str(value)}
    if isinstance(value, (list, tuple)):
        return {
            "type": "list" if isinstance(value, list) else "tuple",
            "value": [_canonical_cell(item) for item in value],
        }
    if isinstance(value, Mapping):
        entries = [
            {"key": _canonical_cell(key), "value": _canonical_cell(item)}
            for key, item in value.items()
        ]
        entries.sort(key=_canonical)
        return {"type": "mapping", "value": entries}
    raise SourceBindingMigrationError(
        f"database projection contains unsupported cell type {type(value).__name__}"
    )


def _canonical_row(row: Sequence[Any]) -> list[dict[str, Any]]:
    return [_canonical_cell(value) for value in row]


def _normalized_rows(connection: Any, table: str) -> dict[str, Any]:
    description = connection.execute(f"DESCRIBE SELECT * FROM {table}").fetchall()
    columns = [
        {"name": str(row[0]), "duckdb_type": str(row[1])}
        for row in description
    ]
    rows = [
        _canonical_row(row)
        for row in connection.execute(f"SELECT * FROM {table}").fetchall()
    ]
    rows.sort(key=_canonical)
    return {
        "columns": columns,
        "rows": rows,
        "row_hashes": sorted(
            _identity({"columns": columns, "row": row}) for row in rows
        ),
    }


def _control_projection(database: Path | str) -> dict[str, Any]:
    connection = _open_control_target(database)
    try:
        statuses = {
            str(status): int(count)
            for status, count in connection.execute(
                "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY status"
            ).fetchall()
        }
        plan = connection.execute(
            "SELECT plan_cid, plan_alias, status, revision, body_json FROM plans"
        ).fetchall()
        task_rows = connection.execute(
            "SELECT task_alias,task_cid,goal_cid,plan_cid,objective_id,ordinal,"
            "status,revision,priority,identity_json,body_json FROM tasks ORDER BY task_alias"
        ).fetchall()
        event_watermark, event_count = connection.execute(
            "SELECT COALESCE(MAX(global_sequence),0), COUNT(*) FROM domain_events"
        ).fetchone()
        counts = {
            name: int(connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
            for name in (
                "goals",
                "tasks",
                "task_dependencies",
                "completion_receipts",
                "evidence_nodes",
                "validation_results",
                "plan_revisions",
                "provider_invocations",
                "effect_claims",
                "merge_attempts",
            )
        }
        projection_tables = (
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
        )
        table_material = {
            table: _normalized_rows(connection, table) for table in projection_tables
        }
        events = connection.execute(
            "SELECT event_id,stream_id,sequence,global_sequence,event_type,task_cid,"
            "attempt_id,session_id,recorded_at,body_json FROM domain_events "
            "ORDER BY global_sequence"
        ).fetchall()
    finally:
        connection.close()
    definition_tables = {
        table: table_material[table]["rows"]
        for table in (
            "task_dependencies",
            "task_outputs",
            "task_acceptance",
            "task_validations",
        )
    }
    definition_tasks = []
    for (
        alias,
        cid,
        goal_cid,
        plan_cid,
        objective_id,
        ordinal,
        _status,
        _revision,
        priority,
        raw_identity,
        raw_body,
    ) in task_rows:
        body = json.loads(str(raw_body))
        body.pop("completion_receipt", None)
        definition_tasks.append(
            {
                "task_alias": alias,
                "task_cid": cid,
                "goal_cid": goal_cid,
                "plan_cid": plan_cid,
                "objective_id": objective_id,
                "ordinal": int(ordinal),
                "priority": priority,
                "identity": json.loads(str(raw_identity)),
                "definition_body": body,
                "dependencies": [
                    row
                    for row in definition_tables["task_dependencies"]
                    if row[0] == _canonical_cell(cid)
                ],
                "outputs": [
                    row
                    for row in definition_tables["task_outputs"]
                    if row[0] == _canonical_cell(cid)
                ],
                "acceptance": [
                    row
                    for row in definition_tables["task_acceptance"]
                    if row[0] == _canonical_cell(cid)
                ],
                "validations": [
                    row
                    for row in definition_tables["task_validations"]
                    if row[0] == _canonical_cell(cid)
                ],
            }
        )
    accepted_material = {
        table: {
            "columns": table_material[table]["columns"],
            "rows": table_material[table]["rows"],
        }
        for table in (
            "goals",
            "goal_edges",
            "task_dependencies",
            "task_outputs",
            "task_acceptance",
            "task_validations",
            "completion_receipts",
            "validation_results",
        )
    }
    return {
        "statuses": statuses,
        "plan": [list(row) for row in plan],
        "tasks": [
            {
                "task_alias": row[0],
                "task_cid": row[1],
                "status": row[6],
                "revision": int(row[7]),
            }
            for row in task_rows
        ],
        "task_definition_digest": _identity(definition_tasks),
        "accepted_tables_digest": _identity(accepted_material),
        "historical_row_hashes": {
            table: table_material[table]["row_hashes"]
            for table in (
                "goals",
                "goal_edges",
                "completion_receipts",
                "validation_results",
                "evidence_nodes",
                "plan_revisions",
            )
        },
        "event_watermark": int(event_watermark),
        "event_count": int(event_count),
        "event_prefix_digest": _identity([_canonical_row(row) for row in events]),
        "counts": counts,
    }


def _latest_state_server_from_connection(connection: Any) -> dict[str, Any]:
    row = connection.execute(
        "SELECT server_id,store_id,database_uuid,process_birth_id,listen_uri,"
        "extension_fingerprint,schema_revision,generation,started_at,stopped_at,"
        "status,revision FROM state_servers "
        "ORDER BY generation DESC,started_at DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise SourceBindingMigrationError("control store has no state-server identity")
    keys = (
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
    result = dict(zip(keys, row, strict=True))
    for key in ("schema_revision", "generation", "revision"):
        result[key] = int(result[key])
    return result


def _latest_state_server(database: Path | str) -> dict[str, Any]:
    connection = _open_control_target(database)
    try:
        return _latest_state_server_from_connection(connection)
    finally:
        connection.close()


def _coordination_projection(database: Path) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (
        read_coordination_registry_projection,
    )

    return dict(read_coordination_registry_projection(database))


def _assert_prior_anchor(
    root: Path,
    policy: Mapping[str, Any],
    *,
    _fenced_connection: Any | None = None,
) -> dict[str, Any]:
    if _fenced_connection is None:
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
            offline_state_server_fence,
        )

        control_record = dict(policy["prior_control_store"])
        control = _confined(root, control_record["path"], noun="stopped g6 control store")
        try:
            with offline_state_server_fence(
                database_path=control,
                connection_factory=lambda path: _open_local_database(
                    path, read_only=True
                ),
            ) as connection:
                return _assert_prior_anchor(
                    root,
                    policy,
                    _fenced_connection=connection,
                )
        except SourceBindingMigrationError:
            raise
        except Exception as exc:
            raise SourceBindingMigrationError(
                "g6 stopped authority could not be fenced"
            ) from exc

    _assert_listener_stopped(policy)
    control_record = dict(policy["prior_control_store"])
    control = _file_anchor(root, control_record, noun="stopped g6 control store")
    bootstrap = _file_anchor(
        root,
        dict(policy["prior_bootstrap_receipt"]),
        noun="historical g6 bootstrap receipt",
    )
    status_path = _file_anchor(
        root,
        dict(policy["prior_stopped_status"]),
        noun="stopped g6 Quack status",
    )
    del bootstrap
    if os.path.lexists(control.with_name(control.name + ".wal")):
        raise SourceBindingMigrationError("stopped g6 control store has a WAL")
    owner_dir = status_path.parent
    forbidden = (
        control.with_name(f".{control.name}.state-owner.json"),
        owner_dir / "quack-state-server.pid",
        owner_dir / "quack-state-server.owner.json",
        owner_dir / "quack-state-server.stop",
    )
    if any(os.path.lexists(path) for path in forbidden) or tuple(owner_dir.glob("*.quack-token")):
        raise SourceBindingMigrationError("stopped g6 owner artifacts indicate a live authority")
    status = _load_json(status_path, root=root, noun="stopped g6 Quack status")
    identity = status.get("identity")
    expected_owner = dict(policy["prior_owner_identity"])
    if (
        status.get("lifecycle") != "stopped"
        or status.get("interface") != "QuackStateServer@1"
        or not isinstance(identity, Mapping)
        or identity.get("status") != "stopped"
        or identity.get("database_uuid") != expected_owner["database_uuid"]
        or identity.get("server_id") != expected_owner["server_id"]
        or identity.get("process_birth_id") != expected_owner["process_birth_id"]
        or int(identity.get("generation") or 0) != int(expected_owner["generation"])
        or int(identity.get("fence_epoch") or 0) != int(expected_owner["fence_epoch"])
        or int(identity.get("schema_revision") or 0)
        != int(expected_owner["schema_revision"])
        or identity.get("listen_uri") != expected_owner["listen_uri"]
        or identity.get("extension_fingerprint")
        != expected_owner["extension_fingerprint"]
        or identity.get("started_at") != expected_owner["started_at"]
        or identity.get("store_id") != control_record["path"]
    ):
        raise SourceBindingMigrationError("stopped g6 Quack identity differs")

    latest_server = _latest_state_server_from_connection(_fenced_connection)
    required_server_fields = (
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
    if any(field not in expected_owner for field in required_server_fields):
        raise SourceBindingMigrationError("sealed predecessor owner row is incomplete")
    if latest_server != {field: expected_owner[field] for field in required_server_fields}:
        raise SourceBindingMigrationError("latest g6 state-server row differs")
    if (
        latest_server["status"] != "stopped"
        or not str(latest_server["stopped_at"] or "")
        or int(latest_server["revision"]) < 2
    ):
        raise SourceBindingMigrationError("latest g6 state-server row is not terminal")

    coordination: list[dict[str, Any]] = []
    for record_value in policy["coordination_stores"]:
        record = dict(record_value)
        database = _file_anchor(
            root,
            record,
            noun=f"g6 lane {record['lane']} coordination store",
        )
        wal_record = record.get("wal")
        wal: Path | None = None
        if isinstance(wal_record, Mapping):
            wal = _file_anchor(
                root,
                wal_record,
                noun=f"g6 lane {record['lane']} coordination WAL",
            )
        elif os.path.lexists(database.with_name(database.name + ".wal")):
            raise SourceBindingMigrationError(
                f"g6 lane {record['lane']} has an unsealed coordination WAL"
            )
        execution_record_value = (
            record.get("execution_observation")
            or record.get("execution_observation_store")
            or record.get("execution_store")
        )
        if not isinstance(execution_record_value, Mapping):
            raise SourceBindingMigrationError(
                f"g6 lane {record['lane']} lacks its sealed execution observation"
            )
        execution_record = dict(execution_record_value)
        execution = _file_anchor(
            root,
            execution_record,
            noun=f"g6 lane {record['lane']} execution observation",
        )
        execution_wal_record_value = execution_record.get("wal")
        execution_wal: Path | None = None
        if isinstance(execution_wal_record_value, Mapping):
            execution_wal = _file_anchor(
                root,
                execution_wal_record_value,
                noun=f"g6 lane {record['lane']} execution observation WAL",
            )
        elif os.path.lexists(execution.with_name(execution.name + ".wal")):
            raise SourceBindingMigrationError(
                f"g6 lane {record['lane']} has an unsealed execution observation WAL"
            )
        coordination.append(
            {
                "policy": record,
                "database": database,
                "wal": wal,
                "execution_record": execution_record,
                "execution_database": execution,
                "execution_wal_record": execution_wal_record_value,
                "execution_wal": execution_wal,
            }
        )

    control_projection = _control_projection(control)
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
        if control_projection[field] != expected_projection[field]:
            raise SourceBindingMigrationError(f"stopped g6 control projection differs: {field}")
    plan = control_projection["plan"]
    if (
        len(plan) != 1
        or plan[0][0] != policy["accepted_plan_root_cid"]
        or int(plan[0][3]) != int(policy["prior_plan_revision"])
    ):
        raise SourceBindingMigrationError("stopped g6 accepted plan differs")
    return {
        "control": control,
        "control_projection": control_projection,
        "coordination": coordination,
    }


def inspect_stopped_source_authority(
    *,
    root: Path,
    policy: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the exact predecessor snapshot under the canonical owner fence.

    Callers must consume this bounded snapshot; they must not reopen the
    predecessor control database to reconstruct any part of it.
    """

    return _assert_prior_anchor(root.resolve(), policy)


def capture_stopped_source_authority(
    *,
    root: Path,
    control_path: str,
    bootstrap_path: str,
    status_path: str,
    coordination_paths: Sequence[str],
    execution_observation_paths: Sequence[str],
) -> dict[str, Any]:
    """Capture the predecessor anchors needed to construct a sealed policy.

    This bootstrap capture accepts paths rather than expected hashes so the
    generator never has to open the source authority before obtaining the
    canonical Quack owner fence.  Every returned byte anchor, owner row, and
    control projection is observed during that one fenced window.
    """

    root = root.resolve()
    if len(coordination_paths) != 4 or len(execution_observation_paths) != 4:
        raise SourceBindingMigrationError(
            "source capture requires exactly four coordination and observation paths"
        )
    control = _confined(root, control_path, noun="capture control store")
    bootstrap = _confined(root, bootstrap_path, noun="capture bootstrap receipt")
    status_file = _confined(root, status_path, noun="capture stopped status")

    def record(path: Path, noun: str) -> dict[str, Any]:
        digest, size = _stable_file(path, root=root, noun=noun)
        return {
            "path": path.relative_to(root).as_posix(),
            "sha256": digest,
            "size_bytes": size,
        }

    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        offline_state_server_fence,
    )

    try:
        with offline_state_server_fence(
            database_path=control,
            connection_factory=lambda path: _open_local_database(path, read_only=True),
        ) as connection:
            control_record = record(control, "capture control store")
            bootstrap_record = record(bootstrap, "capture bootstrap receipt")
            status_record = record(status_file, "capture stopped status")
            status = _load_json(
                status_file,
                root=root,
                noun="capture stopped status",
            )
            identity = status.get("identity")
            latest = _latest_state_server_from_connection(connection)
            if not isinstance(identity, Mapping):
                raise SourceBindingMigrationError("captured stopped identity is absent")
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
            observed_identity = {
                field: (
                    int(identity[field])
                    if field in {"schema_revision", "generation"}
                    else identity[field]
                )
                for field in identity_fields
            }
            _assert_listener_stopped(
                {"target_quack_endpoint": latest["listen_uri"]}
            )
            if (
                status.get("interface") != "QuackStateServer@1"
                or status.get("lifecycle") != "stopped"
                or status.get("extension_fingerprint")
                != latest["extension_fingerprint"]
                or status.get("store_id") != latest["store_id"]
                or observed_identity
                != {field: latest[field] for field in identity_fields}
                or not str(latest.get("stopped_at") or "")
                or int(latest.get("revision") or 0) < 2
                or Path(str(status.get("database_path") or "")).resolve()
                != control.resolve()
            ):
                raise SourceBindingMigrationError(
                    "captured stopped status and authoritative owner row differ"
                )
            owner_dir = status_file.parent
            forbidden = (
                control.with_name(f".{control.name}.state-owner.json"),
                owner_dir / "quack-state-server.pid",
                owner_dir / "quack-state-server.owner.json",
                owner_dir / "quack-state-server.stop",
            )
            if any(os.path.lexists(path) for path in forbidden) or tuple(
                owner_dir.glob("*.quack-token")
            ):
                raise SourceBindingMigrationError(
                    "captured predecessor has live owner artifacts"
                )
            coordination_records: list[dict[str, Any]] = []
            for lane, (coordination_value, observation_value) in enumerate(
                zip(
                    coordination_paths,
                    execution_observation_paths,
                    strict=True,
                )
            ):
                coordination = _confined(
                    root,
                    coordination_value,
                    noun=f"capture lane {lane} coordination store",
                )
                observation = _confined(
                    root,
                    observation_value,
                    noun=f"capture lane {lane} execution observation",
                )
                coordination_record = record(
                    coordination,
                    f"capture lane {lane} coordination store",
                )
                coordination_wal = coordination.with_name(coordination.name + ".wal")
                if os.path.lexists(coordination_wal):
                    coordination_record["wal"] = record(
                        coordination_wal,
                        f"capture lane {lane} coordination WAL",
                    )
                observation_record = record(
                    observation,
                    f"capture lane {lane} execution observation",
                )
                observation_wal = observation.with_name(observation.name + ".wal")
                if os.path.lexists(observation_wal):
                    observation_record["wal"] = record(
                        observation_wal,
                        f"capture lane {lane} execution observation WAL",
                    )
                coordination_record.update(
                    {
                        "lane": lane,
                        "execution_observation": observation_record,
                    }
                )
                coordination_records.append(coordination_record)
            owner = dict(latest)
            owner["fence_epoch"] = int(identity.get("fence_epoch") or 0)
            if owner["fence_epoch"] <= 0:
                raise SourceBindingMigrationError(
                    "captured predecessor fence epoch is absent"
                )
            return {
                "prior_control_store": control_record,
                "prior_bootstrap_receipt": bootstrap_record,
                "prior_stopped_status": status_record,
                "prior_owner_identity": owner,
                "coordination_stores": coordination_records,
                "prior_control_projection": _control_projection(control),
            }
    except SourceBindingMigrationError:
        raise
    except Exception as exc:
        raise SourceBindingMigrationError(
            "stopped source authority capture failed closed"
        ) from exc


def _copy_with_optional_wal(
    source: Path,
    wal: Path | None,
    target: Path,
    *,
    root: Path,
    record: Mapping[str, Any],
    noun: str,
) -> None:
    _copy_anchored_file(source, target, root=root, record=record, noun=noun)
    if wal is not None:
        wal_record = record.get("wal")
        if not isinstance(wal_record, Mapping):
            raise SourceBindingMigrationError(f"{noun} WAL record is absent")
        _copy_anchored_file(
            wal,
            target.with_name(target.name + ".wal"),
            root=root,
            record=wal_record,
            noun=f"{noun} WAL",
        )
    # Opening read/write replays the copied WAL into the private stage only.
    _checkpoint_database(target)


def _active_claim(
    projection: Mapping[str, Any],
    expected: Mapping[str, Any],
) -> dict[str, Any]:
    claims = projection.get("task_claims")
    attempts = projection.get("task_attempts")
    if not isinstance(claims, list) or not isinstance(attempts, list):
        raise SourceBindingMigrationError("coordination projection lacks claims/attempts")
    matched = [item for item in claims if isinstance(item, Mapping) and item.get("claim_id") == expected["claim_id"]]
    matched_attempt = [item for item in attempts if isinstance(item, Mapping) and item.get("attempt_id") == expected["attempt_id"]]
    if len(matched) != 1 or len(matched_attempt) != 1:
        raise SourceBindingMigrationError("stranded claim or attempt is not unique")
    claim = dict(matched[0])
    attempt = dict(matched_attempt[0])
    checks = {
        "task_cid": expected["task_cid"],
        "attempt_id": expected["attempt_id"],
        "lease_id": expected["lease_id"],
        "owner_session_id": expected["owner_session_id"],
        "fencing_token": int(expected["fencing_token"]),
        "fence_epoch": int(expected["fence_epoch"]),
    }
    if any(claim.get(key) != value for key, value in checks.items()):
        raise SourceBindingMigrationError("stranded claim identity differs")
    if claim.get("state") != "accepted" or attempt.get("status") != "running":
        raise SourceBindingMigrationError("stranded claim is not the expected active attempt")
    return claim


def _expire_stranded_claim(
    database: Path,
    settlement: Mapping[str, Any],
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.merge.database_coordination import (
        DatabaseCoordinator,
    )

    before = _coordination_projection(database)
    claim = _active_claim(before, settlement)
    connection = _open_local_database(database, read_only=True)
    try:
        expiry_row = connection.execute(
            "SELECT expires_at_ms FROM task_claims WHERE claim_id=? AND attempt_id=?",
            [settlement["claim_id"], settlement["attempt_id"]],
        ).fetchone()
    finally:
        connection.close()
    if expiry_row is None:
        raise SourceBindingMigrationError("stranded claim expiry is absent")
    now_ms = max(int(expiry_row[0]) + 1, int(time.time() * 1000))
    with DatabaseCoordinator(database, clock_ms=lambda: now_ms) as coordinator:
        lease = coordinator.expire_task_claim(claim, now_ms=now_ms)
    after = _coordination_projection(database)
    after_claim = _active_claim_for_history(after, settlement)
    if after_claim.get("state") != "expired":
        raise SourceBindingMigrationError("stranded coordination claim was not expired")
    attempts = [
        item
        for item in after.get("task_attempts", ())
        if isinstance(item, Mapping) and item.get("attempt_id") == settlement["attempt_id"]
    ]
    if len(attempts) != 1 or attempts[0].get("status") != "expired":
        raise SourceBindingMigrationError("stranded coordination attempt was not expired")
    return {
        "task_alias": settlement["task_alias"],
        "task_cid": settlement["task_cid"],
        "claim_id": settlement["claim_id"],
        "attempt_id": settlement["attempt_id"],
        "lease_id": settlement["lease_id"],
        "fencing_token": int(settlement["fencing_token"]),
        "fence_epoch": int(settlement["fence_epoch"]),
        "expired_at_ms": now_ms,
        "lease_state": str(lease.state.value),
        "pre_projection_root": before["projection_root"],
        "post_projection_root": after["projection_root"],
    }


def _active_claim_for_history(
    projection: Mapping[str, Any], expected: Mapping[str, Any]
) -> dict[str, Any]:
    matched = [
        item
        for item in projection.get("task_claims", ())
        if isinstance(item, Mapping) and item.get("claim_id") == expected["claim_id"]
    ]
    if len(matched) != 1:
        raise SourceBindingMigrationError("stranded claim history is absent or ambiguous")
    return dict(matched[0])


def _assert_no_effectful_attempt_evidence(
    databases: Sequence[tuple[str, Path]],
    settlements: Sequence[Mapping[str, Any]],
) -> None:
    effect_tables = (
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
    for database_noun, database in databases:
        connection = _open_local_database(database, read_only=True)
        try:
            tables = {str(row[0]) for row in connection.execute("SHOW TABLES").fetchall()}
            for settlement in settlements:
                task_cid = str(settlement["task_cid"])
                attempt_id = str(settlement["attempt_id"])
                for table in effect_tables:
                    if table not in tables:
                        continue
                    columns = {
                        str(row[0])
                        for row in connection.execute(
                            f"DESCRIBE SELECT * FROM {table}"
                        ).fetchall()
                    }
                    predicates: list[str] = []
                    parameters: list[str] = []
                    if "attempt_id" in columns:
                        predicates.append("attempt_id = ?")
                        parameters.append(attempt_id)
                    elif "task_cid" in columns:
                        predicates.append("task_cid = ?")
                        parameters.append(task_cid)
                    if not predicates:
                        continue
                    count = int(
                        connection.execute(
                            f"SELECT COUNT(*) FROM {table} WHERE "
                            + " AND ".join(predicates),
                            parameters,
                        ).fetchone()[0]
                    )
                    if count:
                        raise SourceBindingMigrationError(
                            f"{settlement['task_alias']} has effectful evidence in "
                            f"{database_noun}:{table}"
                        )

                # Where this observation owns the exact attempt, prove it
                # stopped before provider/effect/worktree/merge/completion.
                if "database_task_attempts" in tables:
                    attempt_rows = connection.execute(
                        "SELECT task_cid,committed_phase,status,body_json "
                        "FROM database_task_attempts WHERE attempt_id=?",
                        [attempt_id],
                    ).fetchall()
                    if attempt_rows:
                        if len(attempt_rows) != 1:
                            raise SourceBindingMigrationError(
                                f"{settlement['task_alias']} execution attempt is ambiguous"
                            )
                        task, committed_phase, status, body_json = attempt_rows[0]
                        body = json.loads(str(body_json))
                        if (
                            str(task) != task_cid
                            or str(committed_phase) != "context"
                            or str(status) != "running"
                            or str(body.get("worktree_id") or "")
                        ):
                            raise SourceBindingMigrationError(
                                f"{settlement['task_alias']} execution observation is effectful"
                            )
                        phases = connection.execute(
                            "SELECT phase FROM attempt_phases WHERE attempt_id=? "
                            "ORDER BY revision",
                            [attempt_id],
                        ).fetchall()
                        if [str(row[0]) for row in phases] != ["claimed", "context"]:
                            raise SourceBindingMigrationError(
                                f"{settlement['task_alias']} execution phases exceed context"
                            )
        finally:
            connection.close()


def _verify_all_execution_observations(
    *,
    root: Path,
    prior: Mapping[str, Any],
    settlements: Sequence[Mapping[str, Any]],
    stage_root: Path,
) -> None:
    observations: list[tuple[str, Path]] = [("main-control", prior["control"])]
    observation_root = stage_root / ".execution-observation-verification"
    for item in prior["coordination"]:
        lane = int(item["policy"]["lane"])
        target = observation_root / f"lane-{lane}.duckdb"
        _copy_with_optional_wal(
            item["execution_database"],
            item["execution_wal"],
            target,
            root=root,
            record=item["execution_record"],
            noun=f"g6 lane {lane} execution observation",
        )
        observations.append((f"lane-{lane}-execution", target))
    _assert_no_effectful_attempt_evidence(observations, settlements)


def _main_migration_body(
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    coordination_settlements: Sequence[Mapping[str, Any]],
    prior_projection: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": EVIDENCE_SCHEMA,
        "migration_revision": policy["migration_revision"],
        "migration_kind": "exact_source_binding_successor",
        "prior_store_generation": policy["prior_store_generation"],
        "target_store_generation": policy["target_store_generation"],
        "accepted_plan_root_cid": policy["accepted_plan_root_cid"],
        "source_binding": _source_binding(Path(policy["repository_root"]), population),
        "prior_event_watermark": prior_projection["event_watermark"],
        "prior_event_prefix_digest": prior_projection["event_prefix_digest"],
        "prior_task_definition_digest": prior_projection["task_definition_digest"],
        "prior_accepted_tables_digest": prior_projection["accepted_tables_digest"],
        "coordination_settlements": [dict(item) for item in coordination_settlements],
        "rearm_policy": {
            "automatic_retry_admitted": False,
            "old_result_reusable": False,
            "stranded_attempts": [item["task_alias"] for item in coordination_settlements],
            "attempts_used": 1,
            "max_task_attempts": 2,
            "remaining_attempts": 1,
        },
        "copy_policy": dict(policy["copy_policy"]),
        "claim_boundaries": {
            "accepted_completion_changes": 0,
            "accepted_definition_changes": 0,
            "goal_changes": 0,
            "provider_invocation_changes": 0,
            "effect_claim_changes": 0,
            "merge_attempt_changes": 0,
            "worker_self_approval": False,
        },
    }


def _apply_control_suffix(
    database: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    coordination_settlements: Sequence[Mapping[str, Any]],
    prior_projection: Mapping[str, Any],
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
        database_retry_validation_spec_cid,
    )

    accepted_plan = str(policy["accepted_plan_root_cid"])
    with DatabaseTaskSource(
        database,
        owner_id="pctdd-source-g7:private-stage",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=accepted_plan,
    ) as source:
        operator = source.get_task("PCTDD-000")
        if operator is None or operator.status != "completed":
            raise SourceBindingMigrationError("PCTDD-000 historical completion differs")
        plan = source.get_plan(accepted_plan)
        if plan is None or int(plan["revision"]) != int(policy["prior_plan_revision"]):
            raise SourceBindingMigrationError("accepted plan is not at the sealed predecessor revision")
        source_binding = _source_binding(Path(policy["repository_root"]), population)
        plan_body = {
            "current_source_binding": source_binding,
            "source_binding_migration_revision": policy["migration_revision"],
            "accepted_plan_root_preserved": True,
            "accepted_definition_changes": 0,
            "accepted_completion_changes": 0,
        }
        plan_receipt = source.plans.append_revision(
            plan_cid=accepted_plan,
            expected_revision=int(policy["prior_plan_revision"]),
            body=plan_body,
            delta={
                "kind": "exact_source_binding_successor",
                "current_source_head": source_binding["source_head"],
                "current_repository_tree_id": source_binding["repository_tree_id"],
                "current_plan_root_cid": source_binding["current_plan_root_cid"],
            },
        )
        migration_body = _main_migration_body(
            population,
            policy,
            coordination_settlements,
            prior_projection,
        )
        migration_digest = content_identity(migration_body)
        evidence = source.record_evidence(
            task_cid=operator.task_cid,
            evidence_kind=MIGRATION_EVIDENCE_KIND,
            digest=migration_digest,
            body=migration_body,
        )
        status_receipts: list[dict[str, Any]] = []
        for settlement in coordination_settlements:
            task = source.get_task(str(settlement["task_alias"]))
            expected_revision = int(settlement["control_revision"])
            if task is None or task.status != "in_progress" or task.revision != expected_revision:
                raise SourceBindingMigrationError(
                    f"{settlement['task_alias']} control claim is no longer stranded"
                )
            prior_claim_receipt = task.body.get("completion_receipt")
            if not isinstance(prior_claim_receipt, Mapping):
                raise SourceBindingMigrationError("stranded task lacks its prior claim receipt")
            for field in (
                "task_cid",
                "attempt_id",
                "claim_id",
                "lease_id",
                "owner_session_id",
                "fencing_token",
                "fence_epoch",
            ):
                if prior_claim_receipt.get(field) != settlement[field]:
                    raise SourceBindingMigrationError(
                        f"{settlement['task_alias']} prior control receipt differs: {field}"
                    )
            validation_spec_cid = database_retry_validation_spec_cid(
                task.task_cid,
                task.validations,
            )
            if (
                prior_claim_receipt.get("schema")
                != "ipfs_accelerate_py/agent-supervisor/database-retry-budget@1"
                or prior_claim_receipt.get("validation_spec_cid")
                != validation_spec_cid
                or int(prior_claim_receipt.get("attempts_used") or -1) != 1
                or int(prior_claim_receipt.get("max_task_attempts") or -1) != 2
                or prior_claim_receipt.get("retry_exhausted") is not False
            ):
                raise SourceBindingMigrationError(
                    f"{settlement['task_alias']} prior retry budget differs"
                )
            raw_rearm_count = prior_claim_receipt.get("unknown_outcome_rearm_count", 0)
            if isinstance(raw_rearm_count, bool):
                raise SourceBindingMigrationError("prior unknown-outcome rearm count is malformed")
            prior_rearm_count = int(raw_rearm_count)
            if prior_rearm_count < 0:
                raise SourceBindingMigrationError("prior unknown-outcome rearm count is negative")
            next_rearm_count = prior_rearm_count + 1
            if next_rearm_count > MAX_UNKNOWN_OUTCOME_REARMS:
                raise SourceBindingMigrationError(
                    "source migration would exceed the unknown-outcome rearm limit"
                )
            blocked_receipt = {
                "schema": "pctdd/source-migration-stranded-attempt@1",
                "operation": "operator_source_migration_unknown_callback_blocked",
                "migration_digest": migration_digest,
                "task_cid": task.task_cid,
                "task_alias": task.task_alias,
                "previous_control_revision": task.revision,
                "attempt_id": settlement["attempt_id"],
                "claim_id": settlement["claim_id"],
                "lease_id": settlement["lease_id"],
                "owner_session_id": settlement["owner_session_id"],
                "fencing_token": int(settlement["fencing_token"]),
                "fence_epoch": int(settlement["fence_epoch"]),
                "coordination_post_projection_root": settlement["post_projection_root"],
                "automatic_retry_admitted": False,
                "old_result_reusable": False,
                "attempts_used": 1,
                "max_task_attempts": 2,
                "remaining_attempts": 1,
            }
            blocked = source.compare_and_set_status(
                task.task_cid,
                task.revision,
                "blocked",
                receipt=blocked_receipt,
            )
            rearm_receipt = {
                **blocked_receipt,
                "schema": "ipfs_accelerate_py/agent-supervisor/database-retry-budget@1",
                "operation": "operator_source_migration_rearmed",
                "validation_spec_cid": validation_spec_cid,
                "attempts_used": 1,
                "max_task_attempts": 2,
                "retry_exhausted": False,
                "unknown_outcome_rearm_count": next_rearm_count,
                "process_instance_id": "operator:pctdd-source-g7",
                "blocked_event_id": blocked.receipt_cid,
                "previous_control_revision": blocked.task.revision,
            }
            retrying = source.compare_and_set_status(
                task.task_cid,
                blocked.task.revision,
                "retrying",
                receipt=rearm_receipt,
            )
            status_receipts.append(
                {
                    "task_alias": task.task_alias,
                    "blocked_event_id": blocked.receipt_cid,
                    "retrying_event_id": retrying.receipt_cid,
                    "resulting_revision": retrying.task.revision,
                }
            )
    return {
        "plan_event_id": plan_receipt.event_id,
        "migration_evidence_event_id": evidence.event_id,
        "migration_digest": migration_digest,
        "status_receipts": status_receipts,
    }


def _verify_staged_successor(
    stage_root: Path,
    database: Path,
    coordination_paths: Sequence[Path],
    policy: Mapping[str, Any],
    prior_projection: Mapping[str, Any],
    suffix: Mapping[str, Any],
) -> dict[str, Any]:
    post = _control_projection(database)
    expected_statuses = dict(policy["target_control_projection"]["statuses"])
    if post["statuses"] != expected_statuses:
        raise SourceBindingMigrationError("g7 task status population differs")
    if post["task_definition_digest"] != prior_projection["task_definition_digest"]:
        raise SourceBindingMigrationError("g7 accepted task definitions changed")
    if post["accepted_tables_digest"] != prior_projection["accepted_tables_digest"]:
        raise SourceBindingMigrationError("g7 accepted goals/completions/validations changed")
    for table, prior_hashes in prior_projection["historical_row_hashes"].items():
        post_hashes = post["historical_row_hashes"].get(table, ())
        if Counter(prior_hashes) - Counter(post_hashes):
            raise SourceBindingMigrationError(
                f"g7 altered historical rows in {table}"
            )
    for key in ("completion_receipts", "validation_results", "goals", "tasks", "task_dependencies"):
        if post["counts"][key] != prior_projection["counts"][key]:
            raise SourceBindingMigrationError(f"g7 preserved count differs: {key}")
    if post["counts"]["evidence_nodes"] != prior_projection["counts"]["evidence_nodes"] + 1:
        raise SourceBindingMigrationError("g7 must append exactly one evidence node")
    if post["counts"]["plan_revisions"] != prior_projection["counts"]["plan_revisions"] + 1:
        raise SourceBindingMigrationError("g7 must append exactly one plan revision")
    expected_events = int(prior_projection["event_watermark"]) + 6
    if post["event_watermark"] != expected_events or post["event_count"] != prior_projection["event_count"] + 6:
        raise SourceBindingMigrationError("g7 control event suffix is not exactly six events")
    tasks = {item["task_alias"]: item for item in post["tasks"]}
    for alias, revision in dict(policy["target_control_projection"]["task_revisions"]).items():
        if tasks[alias]["status"] != "retrying" or tasks[alias]["revision"] != int(revision):
            raise SourceBindingMigrationError(f"g7 rearmed task differs: {alias}")
    plan = post["plan"]
    if len(plan) != 1 or int(plan[0][3]) != int(policy["prior_plan_revision"]) + 1:
        raise SourceBindingMigrationError("g7 plan revision did not advance exactly once")
    coordination = [_coordination_projection(path) for path in coordination_paths]
    return {
        "control_projection": post,
        "coordination_projection_roots": [item["projection_root"] for item in coordination],
        "control_store": {
            "sha256": _stable_file(database, root=stage_root, noun="staged g7 control")[0],
            "size_bytes": database.stat().st_size,
        },
        "coordination_stores": [
            {
                "lane": lane,
                "sha256": _stable_file(
                    path,
                    root=stage_root,
                    noun=f"staged g7 lane {lane}",
                )[0],
                "size_bytes": path.stat().st_size,
                "projection_root": coordination[lane]["projection_root"],
            }
            for lane, path in enumerate(coordination_paths)
        ],
        "suffix": dict(suffix),
    }


def _receipt(
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    prior_projection: Mapping[str, Any],
    verified: Mapping[str, Any],
) -> dict[str, Any]:
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "migration_revision": policy["migration_revision"],
        "prior_store_generation": policy["prior_store_generation"],
        "target_store_generation": policy["target_store_generation"],
        "accepted_plan_root_cid": policy["accepted_plan_root_cid"],
        "source_binding": _source_binding(Path(policy["repository_root"]), population),
        "prior_control_store": dict(policy["prior_control_store"]),
        "prior_owner_identity": dict(policy["prior_owner_identity"]),
        "prior_stopped_status": dict(policy["prior_stopped_status"]),
        "prior_event_watermark": prior_projection["event_watermark"],
        "prior_event_prefix_digest": prior_projection["event_prefix_digest"],
        "prior_task_definition_digest": prior_projection["task_definition_digest"],
        "historical_row_hashes": {
            table: list(hashes)
            for table, hashes in prior_projection["historical_row_hashes"].items()
        },
        "migration_event_watermark": verified["control_projection"]["event_watermark"],
        "migration_event_prefix_digest": verified["control_projection"]["event_prefix_digest"],
        "control_store": dict(verified["control_store"]),
        "coordination_stores": [dict(item) for item in verified["coordination_stores"]],
        "plan_revision_changes": 1,
        "evidence_node_changes": 1,
        "task_revision_changes": 4,
        "task_status_changes": 4,
        "goal_changes": 0,
        "accepted_definition_changes": 0,
        "accepted_completion_changes": 0,
        "provider_invocation_changes": 0,
        "effect_claim_changes": 0,
        "merge_attempt_changes": 0,
        "worker_self_approval": False,
        "rearmed_task_aliases": ["PCTDD-001", "PCTDD-029"],
        "preserved_retrying_task_aliases": ["PCTDD-018"],
        "ready_frontier": list(policy["target_control_projection"]["ready_frontier"]),
        "copied_artifact_classes": ["authoritative_control_store", "coordination_history"],
        "not_copied_artifact_classes": list(policy["copy_policy"]["not_copied"]),
        "suffix": dict(verified["suffix"]),
    }
    return {**receipt, "receipt_cid": _identity(receipt)}


def _write_new_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        payload = _canonical(value) + b"\n"
        view = memoryview(payload)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise SourceBindingMigrationError(
                    "source migration receipt write made no progress"
                )
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _store_relative_files() -> tuple[Path, ...]:
    return (
        Path("control.duckdb"),
        *(
            Path("state") / f"lane-{lane}" / "quack-lane-coordination.duckdb"
            for lane in range(4)
        ),
    )


def _receipt_store_record(
    relative: Path,
    receipt: Mapping[str, Any],
) -> Mapping[str, Any]:
    if relative == Path("control.duckdb"):
        return dict(receipt["control_store"])
    lane = int(relative.parts[1].split("-", 1)[1])
    records = {
        int(item["lane"]): item for item in receipt["coordination_stores"]
    }
    return dict(records[lane])


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _ensure_private_directory(path: Path) -> None:
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        pass
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise SourceBindingMigrationError("g7 publication directory is unsafe") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or int(metadata.st_uid) != int(os.geteuid())
        or stat.S_IMODE(metadata.st_mode) != 0o700
    ):
        raise SourceBindingMigrationError(
            "g7 publication directory is not private and owner-controlled"
        )


def _validate_published_store(
    *,
    root: Path,
    target_root: Path,
    receipt: Mapping[str, Any],
    relative: Path,
) -> None:
    path = target_root / relative
    try:
        metadata = os.stat(path, follow_symlinks=False)
    except OSError as exc:
        raise SourceBindingMigrationError(
            f"published g7 store is absent: {relative.as_posix()}"
        ) from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or int(metadata.st_uid) != int(os.geteuid())
        or stat.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise SourceBindingMigrationError(
            f"published g7 store is not private: {relative.as_posix()}"
        )
    record = _receipt_store_record(relative, receipt)
    observed = _stable_file(
        path,
        root=root,
        noun=f"published g7 {relative.as_posix()}",
        required_links=None,
    )
    if observed != (str(record["sha256"]), int(record["size_bytes"])):
        raise SourceBindingMigrationError(
            f"published g7 store differs: {relative.as_posix()}"
        )


def _validate_receipt_identity(
    receipt: Mapping[str, Any],
    *,
    root: Path,
    population: Mapping[str, Any],
) -> None:
    unhashed = dict(receipt)
    receipt_cid = str(unhashed.pop("receipt_cid", ""))
    if receipt.get("schema") != RECEIPT_SCHEMA or receipt_cid != _identity(unhashed):
        raise SourceBindingMigrationError("g7 source migration receipt identity differs")
    if receipt.get("source_binding") != _source_binding(root, population):
        raise SourceBindingMigrationError("g7 source migration receipt belongs to another source")


def _load_migration_marker(
    *,
    root: Path,
    target_root: Path,
    noun: str,
) -> dict[str, Any]:
    marker = target_root / MIGRATION_MARKER
    pending = target_root / PENDING_MARKER
    pending_exists = os.path.lexists(pending)
    receipt = _load_json(
        marker,
        root=root,
        noun=noun,
        required_links=2 if pending_exists else 1,
    )
    if pending_exists:
        marker_stat = os.stat(marker, follow_symlinks=False)
        pending_stat = os.stat(pending, follow_symlinks=False)
        if (
            not stat.S_ISREG(marker_stat.st_mode)
            or not stat.S_ISREG(pending_stat.st_mode)
            or (marker_stat.st_dev, marker_stat.st_ino)
            != (pending_stat.st_dev, pending_stat.st_ino)
        ):
            raise SourceBindingMigrationError(
                "g7 pending receipt is not the final marker hardlink"
            )
    return receipt


def _publication_files(target_root: Path) -> tuple[set[Path], set[Path]]:
    expected = set(_store_relative_files())
    present: set[Path] = set()
    unexpected: set[Path] = set()
    if not os.path.lexists(target_root):
        return present, unexpected
    for path in target_root.rglob("*"):
        if path.is_dir() and not path.is_symlink():
            continue
        relative = path.relative_to(target_root)
        if relative in expected:
            present.add(relative)
        elif relative not in {Path(PENDING_MARKER), Path(MIGRATION_MARKER)}:
            unexpected.add(relative)
    return present, unexpected


def _validate_published_stores(
    *,
    root: Path,
    target_root: Path,
    receipt: Mapping[str, Any],
) -> None:
    for relative in _store_relative_files():
        _validate_published_store(
            root=root,
            target_root=target_root,
            receipt=receipt,
            relative=relative,
        )


def _finish_pending_publication(
    *,
    root: Path,
    target_root: Path,
    population: Mapping[str, Any],
) -> bool:
    """Finish only an exact all-five-leaf, receipt-last interrupted publish."""

    if os.path.lexists(target_root):
        _ensure_private_directory(target_root)
    marker = target_root / MIGRATION_MARKER
    pending = target_root / PENDING_MARKER
    present, unexpected = _publication_files(target_root)
    if unexpected:
        raise SourceBindingMigrationError("g7 runtime contains unrecognized partial artifacts")
    expected = set(_store_relative_files())
    if os.path.lexists(marker):
        links = 2 if os.path.lexists(pending) else 1
        receipt = _load_json(
            marker,
            root=root,
            noun="g7 source migration marker",
            required_links=links,
        )
        _validate_receipt_identity(receipt, root=root, population=population)
        if present != expected:
            raise SourceBindingMigrationError("g7 marker exists without all five stores")
        _validate_published_stores(root=root, target_root=target_root, receipt=receipt)
        if os.path.lexists(pending):
            marker_stat = os.stat(marker, follow_symlinks=False)
            pending_stat = os.stat(pending, follow_symlinks=False)
            if (marker_stat.st_dev, marker_stat.st_ino) != (
                pending_stat.st_dev,
                pending_stat.st_ino,
            ):
                raise SourceBindingMigrationError("g7 pending marker is not the marker hardlink")
            pending.unlink()
            _fsync_directory(target_root)
        return True
    if present and present != expected:
        if not os.path.lexists(pending):
            raise SourceBindingMigrationError(
                "partial g7 store subset exists without a pending receipt"
            )
        receipt = _load_json(
            pending,
            root=root,
            noun="partial pending g7 source migration receipt",
        )
        _validate_receipt_identity(receipt, root=root, population=population)
        for relative in present:
            _validate_published_store(
                root=root,
                target_root=target_root,
                receipt=receipt,
                relative=relative,
            )
        # Still fail-closed as an authority (there is no final marker), but a
        # freshly rebuilt, byte-identical stage may fill the missing leaves.
        return False
    if present == expected:
        if not os.path.lexists(pending):
            raise SourceBindingMigrationError("all g7 stores exist without a pending receipt")
        receipt = _load_json(
            pending,
            root=root,
            noun="pending g7 source migration receipt",
        )
        _validate_receipt_identity(receipt, root=root, population=population)
        _validate_published_stores(root=root, target_root=target_root, receipt=receipt)
        os.link(pending, marker, follow_symlinks=False)
        _fsync_directory(target_root)
        pending.unlink()
        _fsync_directory(target_root)
        return True
    # A pending receipt written before the first leaf is safe to resume only
    # after the freshly rebuilt stage proves it is byte-identical.
    if present == set() and (
        not os.path.lexists(pending) or pending.is_file() and not pending.is_symlink()
    ):
        return False
    raise SourceBindingMigrationError("g7 pending publication state is malformed")


def _publish_stage(
    root: Path,
    stage_root: Path,
    target_root: Path,
    relative_files: Sequence[Path],
    receipt: Mapping[str, Any],
) -> None:
    if os.path.lexists(target_root / MIGRATION_MARKER):
        raise SourceBindingMigrationError("g7 migration marker already exists")
    _ensure_private_directory(target_root)
    pending = target_root / PENDING_MARKER
    if os.path.lexists(pending):
        pending_receipt = _load_json(
            pending,
            root=root,
            noun="pending g7 source migration receipt",
        )
        if pending_receipt != dict(receipt):
            raise SourceBindingMigrationError("pending g7 receipt differs from rebuilt stage")
    else:
        _write_new_json(pending, receipt)
        _fsync_directory(target_root)
    created: list[Path] = []
    for relative in relative_files:
        source = stage_root / relative
        target = target_root / relative
        current_parent = target_root
        for part in relative.parent.parts:
            current_parent = current_parent / part
            _ensure_private_directory(current_parent)
        if os.path.lexists(target):
            _validate_published_store(
                root=root,
                target_root=target_root,
                receipt=receipt,
                relative=relative,
            )
            continue
        _fsync_regular(source)
        os.link(source, target, follow_symlinks=False)
        created.append(target)
        _fsync_directory(target.parent)
    _validate_published_stores(root=root, target_root=target_root, receipt=receipt)
    marker = target_root / MIGRATION_MARKER
    os.link(pending, marker, follow_symlinks=False)
    _fsync_directory(target_root)
    pending.unlink()
    _fsync_directory(target_root)
    # The receipt is the last externally meaningful target leaf.
    if not all(os.path.lexists(path) for path in (*created, marker)):
        raise SourceBindingMigrationError("g7 publication did not retain all committed leaves")


def migrate_source_binding(
    *,
    root: Path,
    config: Mapping[str, Any],
    population: Mapping[str, Any],
) -> dict[str, Any]:
    """Create the fresh g7 successor; never touch the stopped g6 authority."""

    root = root.resolve()
    policy = _policy(config)
    policy["repository_root"] = str(root)
    _assert_source_delta(root, population, policy)
    target_root = _confined(root, policy["target_runtime_root"], noun="g7 runtime root")
    marker = target_root / MIGRATION_MARKER
    if os.path.lexists(marker):
        result = check_source_binding(
            root=root,
            config=config,
            population=population,
            allow_progressed=True,
        )
        pending = target_root / PENDING_MARKER
        if os.path.lexists(pending):
            # The check proved that this is the exact marker hardlink and used
            # Quack rather than direct DB reads if a live owner exists.
            _load_migration_marker(
                root=root,
                target_root=target_root,
                noun="completed g7 source migration marker",
            )
            pending.unlink()
            _fsync_directory(target_root)
        return result
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        offline_state_server_fence,
    )

    prior_control = _confined(
        root,
        policy["prior_control_store"]["path"],
        noun="stopped g6 control store",
    )
    predecessor_fence = offline_state_server_fence(
        database_path=prior_control,
        connection_factory=lambda path: _open_local_database(path, read_only=True),
    )
    predecessor_connection: Any | None = None
    lock_path = target_root.parent / LOCK_NAME
    lock_path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    descriptor: int | None = None
    stage_root: Path | None = None
    try:
        predecessor_connection = predecessor_fence.__enter__()
        prior = _assert_prior_anchor(
            root,
            policy,
            _fenced_connection=predecessor_connection,
        )
        descriptor = os.open(
            lock_path,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        deadline = time.monotonic() + 10.0
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic() >= deadline:
                    raise SourceBindingMigrationError("timed out acquiring g7 migration lock") from exc
                time.sleep(0.02)
        if _finish_pending_publication(
            root=root,
            target_root=target_root,
            population=population,
        ):
            return check_source_binding(
                root=root,
                config=config,
                population=population,
                allow_progressed=False,
            )
        stage_root = Path(
            tempfile.mkdtemp(prefix=".pctdd-g7-installing.", dir=target_root.parent)
        )
        stage_control = stage_root / "control.duckdb"
        _copy_anchored_file(
            prior["control"],
            stage_control,
            root=root,
            record=policy["prior_control_store"],
            noun="stopped g6 control store",
        )
        coordination_paths: list[Path] = []
        for item in prior["coordination"]:
            lane = int(item["policy"]["lane"])
            target = stage_root / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
            _copy_with_optional_wal(
                item["database"],
                item["wal"],
                target,
                root=root,
                record=item["policy"],
                noun=f"g6 lane {lane} coordination store",
            )
            coordination_paths.append(target)
        expected_settlements = [
            dict(record["settlement"])
            for record in policy["coordination_stores"]
            if isinstance(record, Mapping)
            and isinstance(record.get("settlement"), Mapping)
        ]
        _verify_all_execution_observations(
            root=root,
            prior=prior,
            settlements=expected_settlements,
            stage_root=stage_root,
        )
        settlements: list[dict[str, Any]] = []
        for item, path in zip(prior["coordination"], coordination_paths, strict=True):
            settlement = item["policy"].get("settlement")
            if isinstance(settlement, Mapping):
                settlements.append(_expire_stranded_claim(path, settlement))
                _checkpoint_database(path)
        if [item["task_alias"] for item in settlements] != ["PCTDD-001", "PCTDD-029"]:
            raise SourceBindingMigrationError("g7 did not settle the exact stranded task pair")
        # Add the sealed control revision/claim fields needed for exact CAS checks.
        by_alias = {
            str(item["task_alias"]): dict(item)
            for record in policy["coordination_stores"]
            if isinstance(record, Mapping)
            for item in ([record.get("settlement")] if isinstance(record.get("settlement"), Mapping) else [])
        }
        settlements = [{**item, **by_alias[item["task_alias"]]} for item in settlements]
        suffix = _apply_control_suffix(
            stage_control,
            population,
            policy,
            settlements,
            prior["control_projection"],
        )
        _checkpoint_database(stage_control)
        verified = _verify_staged_successor(
            stage_root,
            stage_control,
            coordination_paths,
            policy,
            prior["control_projection"],
            suffix,
        )
        receipt = _receipt(population, policy, prior["control_projection"], verified)
        relative_files = _store_relative_files()
        _assert_source_delta(root, population, policy)
        _assert_prior_anchor(
            root,
            policy,
            _fenced_connection=predecessor_connection,
        )
        _publish_stage(root, stage_root, target_root, relative_files, receipt)
        return {
            "schema": CHECK_SCHEMA,
            "valid": True,
            "mode": "migrate-source",
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
            shutil.rmtree(stage_root)
        if predecessor_connection is not None:
            predecessor_fence.__exit__(None, None, None)


def _migration_rows(database: Path | str, receipt: Mapping[str, Any]) -> dict[str, Any]:
    connection = _open_control_target(database)
    try:
        event_rows = connection.execute(
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
        historical_row_hashes = {
            table: _normalized_rows(connection, table)["row_hashes"]
            for table in receipt["historical_row_hashes"]
        }
    finally:
        connection.close()
    return {
        "migration_event_prefix_digest": _identity(
            [_canonical_row(row) for row in event_rows]
        ),
        "evidence": [list(row) for row in evidence],
        "plan": list(plan) if plan is not None else None,
        "historical_row_hashes": historical_row_hashes,
    }


def _assert_historical_manifests(
    rows: Mapping[str, Any], receipt: Mapping[str, Any]
) -> None:
    expected_manifests = receipt.get("historical_row_hashes")
    observed_manifests = rows.get("historical_row_hashes")
    if not isinstance(expected_manifests, Mapping) or not isinstance(
        observed_manifests, Mapping
    ):
        raise SourceBindingMigrationError("g7 historical manifests are absent")
    for table, expected_hashes in expected_manifests.items():
        observed_hashes = observed_manifests.get(table, ())
        if Counter(expected_hashes) - Counter(observed_hashes):
            raise SourceBindingMigrationError(
                f"g7 altered or lost sealed historical rows in {table}"
            )


def _live_g7_owner(
    *,
    root: Path,
    target_root: Path,
    policy: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> dict[str, Any] | None:
    status_path = target_root / "quack-owner" / "quack-state-server.status.json"
    if not os.path.lexists(status_path):
        return None
    status = _load_json(status_path, root=root, noun="g7 Quack owner status")
    lifecycle = str(status.get("lifecycle") or "")
    if lifecycle == "stopped":
        return None
    if lifecycle != "ready":
        raise SourceBindingMigrationError("g7 Quack owner lifecycle is not safely inspectable")
    identity = status.get("identity")
    if not isinstance(identity, Mapping):
        raise SourceBindingMigrationError("g7 Quack owner identity is absent")
    expected_store = str(
        (target_root / "control.duckdb").relative_to(root).as_posix()
    )
    expected_endpoint = str(policy["target_quack_endpoint"])
    expected_uuid = str(receipt["prior_owner_identity"]["database_uuid"])
    expected_extension = str(
        receipt["prior_owner_identity"].get("extension_fingerprint") or ""
    )
    if not expected_extension:
        raise SourceBindingMigrationError(
            "g7 receipt lacks the sealed Quack extension fingerprint"
        )
    try:
        database_path = Path(str(status["database_path"])).resolve()
    except (KeyError, OSError, ValueError) as exc:
        raise SourceBindingMigrationError("g7 owner database path is malformed") from exc
    if (
        status.get("interface") != "QuackStateServer@1"
        or identity.get("interface") != "StateServerIdentity@1"
        or identity.get("status") != "ready"
        or identity.get("listen_uri") != expected_endpoint
        or identity.get("extension_fingerprint") != expected_extension
        or status.get("extension_fingerprint") != expected_extension
        or identity.get("store_id") != expected_store
        or status.get("store_id") != expected_store
        or identity.get("database_uuid") != expected_uuid
        or database_path != (target_root / "control.duckdb").resolve()
        or int(status.get("port") or 0) != int(expected_endpoint.rsplit(":", 1)[1])
        or int(identity.get("generation") or 0)
        <= int(receipt["prior_owner_identity"]["generation"])
        or int(identity.get("fence_epoch") or 0)
        != int(identity.get("generation") or 0)
        or int(identity.get("fence_epoch") or 0)
        <= int(receipt["prior_owner_identity"].get("fence_epoch") or 0)
    ):
        raise SourceBindingMigrationError("live g7 Quack owner is not the exact successor")
    return dict(status)


def _ready_task_aliases(
    target: Path | str,
    *,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
) -> list[str]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    with DatabaseTaskSource(
        target,
        owner_id="pctdd-source-g7:check",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(policy["accepted_plan_root_cid"]),
    ) as source:
        return [item.task_alias for item in source.ready_tasks(limit=100).tasks]


def _verify_source_binding_target(
    *,
    root: Path,
    population: Mapping[str, Any],
    policy: Mapping[str, Any],
    receipt: Mapping[str, Any],
    control: Path,
    coordination: Sequence[Path],
    control_target: Path | str,
    live_owner: Mapping[str, Any] | None,
    allow_progressed: bool,
) -> dict[str, Any]:
    """Verify one control target while its local owner fence or Quack owns it."""

    rows = _migration_rows(control_target, receipt)
    if rows["migration_event_prefix_digest"] != receipt["migration_event_prefix_digest"]:
        raise SourceBindingMigrationError("g7 migration event prefix differs")
    if len(rows["evidence"]) != 1:
        raise SourceBindingMigrationError(
            "g7 must retain exactly one source-migration evidence node"
        )
    evidence_body = json.loads(str(rows["evidence"][0][3]))
    if (
        rows["evidence"][0][1] != MIGRATION_EVIDENCE_KIND
        or rows["evidence"][0][2] != receipt["suffix"]["migration_digest"]
        or _identity(evidence_body) != receipt["suffix"]["migration_digest"]
    ):
        raise SourceBindingMigrationError("g7 source-migration evidence differs")
    _assert_historical_manifests(rows, receipt)
    projection = _control_projection(control_target)
    if projection["task_definition_digest"] != receipt["prior_task_definition_digest"]:
        raise SourceBindingMigrationError("g7 immutable task definitions differ")
    plan = rows["plan"]
    if plan is None or int(plan[1]) < int(policy["prior_plan_revision"]) + 1:
        raise SourceBindingMigrationError("g7 source-bound plan revision is absent")
    plan_body = json.loads(str(plan[2]))
    if plan_body.get("current_source_binding") != _source_binding(root, population):
        raise SourceBindingMigrationError("g7 active plan source binding differs")
    if live_owner is None:
        for lane, path in enumerate(coordination):
            coordination_projection = _coordination_projection(path)
            record = dict(policy["coordination_stores"][lane])
            settlement = record.get("settlement")
            if isinstance(settlement, Mapping):
                claim = _active_claim_for_history(coordination_projection, settlement)
                if claim.get("state") != "expired":
                    raise SourceBindingMigrationError(
                        "g7 stranded claim history was not retained"
                    )
    if not allow_progressed:
        if (
            _stable_file(control, root=root, noun="g7 control store")[0]
            != receipt["control_store"]["sha256"]
        ):
            raise SourceBindingMigrationError("g7 control store changed before launch")
        for lane, path in enumerate(coordination):
            if (
                _stable_file(path, root=root, noun=f"g7 lane {lane} coordination")[0]
                != receipt["coordination_stores"][lane]["sha256"]
            ):
                raise SourceBindingMigrationError(
                    "g7 coordination store changed before launch"
                )
    if live_owner is not None:
        latest = _latest_state_server(control_target)
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
                raise SourceBindingMigrationError(
                    f"live g7 transport identity differs: {field}"
                )
        if (
            latest["stopped_at"] is not None
            or latest["status"] != "ready"
            or int(latest["revision"]) < 1
        ):
            raise SourceBindingMigrationError("live g7 transport is not ready")
    ready = _ready_task_aliases(
        control_target,
        population=population,
        policy=policy,
    )
    if not allow_progressed and ready != list(
        policy["target_control_projection"]["ready_frontier"]
    ):
        raise SourceBindingMigrationError("g7 initial ready frontier differs")
    return {
        "schema": CHECK_SCHEMA,
        "valid": True,
        "mode": "check-source-migration",
        "allow_progressed": bool(allow_progressed),
        "verification_transport": "quack" if live_owner is not None else "offline",
        "receipt": receipt,
        "ready_task_ids": ready,
    }


def check_source_binding(
    *,
    root: Path,
    config: Mapping[str, Any],
    population: Mapping[str, Any],
    allow_progressed: bool,
) -> dict[str, Any]:
    """Verify the migration marker and immutable prefix, including after progress."""

    root = root.resolve()
    policy = _policy(config)
    policy["repository_root"] = str(root)
    _assert_source_delta(root, population, policy)
    target_root = _confined(root, policy["target_runtime_root"], noun="g7 runtime root")
    if not os.path.lexists(target_root):
        raise SourceBindingMigrationError("g7 runtime root is absent")
    _ensure_private_directory(target_root)
    marker = target_root / MIGRATION_MARKER
    receipt = _load_migration_marker(
        root=root,
        target_root=target_root,
        noun="g7 source migration marker",
    )
    _validate_receipt_identity(receipt, root=root, population=population)
    control = target_root / "control.duckdb"
    coordination = [
        target_root / "state" / f"lane-{lane}" / "quack-lane-coordination.duckdb"
        for lane in range(4)
    ]
    live_owner = _live_g7_owner(
        root=root,
        target_root=target_root,
        policy=policy,
        receipt=receipt,
    )
    if live_owner is not None and not allow_progressed:
        raise SourceBindingMigrationError("initial migration verification cannot inspect a live owner")
    if live_owner is None:
        if not all(
            path.is_file() and not path.is_symlink() for path in (control, *coordination)
        ):
            raise SourceBindingMigrationError("g7 authoritative store set is incomplete")
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
            offline_state_server_fence,
        )

        try:
            with offline_state_server_fence(
                database_path=control,
                connection_factory=lambda path: _open_local_database(
                    path, read_only=True
                ),
            ):
                # Revalidate the receipt while the canonical owner fence is held.
                if _load_json(
                    marker,
                    root=root,
                    noun="fenced g7 source migration marker",
                ) != receipt:
                    raise SourceBindingMigrationError(
                        "g7 source migration marker changed before fenced inspection"
                    )
                return _verify_source_binding_target(
                    root=root,
                    population=population,
                    policy=policy,
                    receipt=receipt,
                    control=control,
                    coordination=coordination,
                    control_target=control,
                    live_owner=None,
                    allow_progressed=allow_progressed,
                )
        except SourceBindingMigrationError:
            raise
        except Exception as exc:
            raise SourceBindingMigrationError(
                "g7 offline authority could not be fenced"
            ) from exc
    return _verify_source_binding_target(
        root=root,
        population=population,
        policy=policy,
        receipt=receipt,
        control=control,
        coordination=coordination,
        control_target=str(policy["target_quack_endpoint"]),
        live_owner=live_owner,
        allow_progressed=allow_progressed,
    )


__all__ = (
    "CHECK_SCHEMA",
    "EVIDENCE_SCHEMA",
    "MIGRATION_SCHEMA",
    "RECEIPT_SCHEMA",
    "SourceBindingMigrationError",
    "capture_stopped_source_authority",
    "check_source_binding",
    "inspect_stopped_source_authority",
    "migrate_source_binding",
)
