#!/usr/bin/env python3
"""Operate the sealed PCTDD configured board through existing authorities.

This is deliberately a thin campaign facade.  It does not implement a task
scheduler, a DuckDB writer, or a second state service.  Validation and
materialization are delegated to the sealed PCTDD tools; scheduling is
delegated to ``configured_board_scheduler``; and the exclusive database owner
is the existing loopback ``QuackStateServer`` process.

The only credential-bearing artifact is the Quack owner's mode-0600 token
vault.  The token is supplied in the private environment of trusted scheduler
children, never argv, JSON, logs, provider environments, or DuckLake.  Status
is accepted only after a live, authenticated Quack query matches the published
owner identity.  DuckLake remains an optional, rebuildable, non-authoritative
projection.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import stat
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import Any, Final

ROOT: Final = Path(__file__).resolve().parents[3]
ACCEL_ROOT: Final = ROOT / "external" / "ipfs_accelerate"
DEFAULT_CONFIG: Final = (
    ROOT
    / "config"
    / "agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"
)
DEPENDENCY_VALIDATOR: Final = (
    ROOT
    / "scripts"
    / "validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py"
)
BOARD_VALIDATOR: Final = (
    ROOT / "scripts" / "validate_parallel_content_sealing_proof_carrying_tdd_board.py"
)
MATERIALIZER: Final = (
    ROOT / "scripts" / "materialize_parallel_content_sealing_proof_carrying_tdd_program.py"
)
CONFIGURED_SCHEDULER: Final = (
    ACCEL_ROOT / "scripts" / "ops" / "agent_supervisor" / "configured_board_scheduler.py"
)
QUACK_SERVER: Final = (
    ACCEL_ROOT / "scripts" / "ops" / "agent_supervisor" / "quack_state_server.py"
)

OPERATOR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "parallel-content-sealing-proof-carrying-tdd-operator@1"
)
PROGRAM_ID: Final = "parallel-content-sealing-proof-carrying-tdd-v1"
TASK_PREFIX: Final = "PCTDD-"
DEFAULT_MONITOR_SECONDS: Final = 180.0
MAX_JSON_BYTES: Final = 8 * 1024 * 1024
QUACK_ENDPOINT_RE: Final = re.compile(
    r"^quack:(?://)?(127(?:\.\d{1,3}){3}|localhost|::1):(\d{1,5})$",
    re.IGNORECASE,
)
TOKEN_RE: Final = re.compile(r"^[A-Za-z0-9_-]{8,512}$")
ENV_NAME_RE: Final = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")

READY_STATUSES: Final = frozenset(
    {"proposed", "admitted", "pending", "ready", "todo", "queued", "retrying", "open"}
)
ACTIVE_STATUSES: Final = frozenset(
    {"claimed", "in_progress", "running", "implementing", "validating", "reviewing", "merging"}
)
WAITING_STATUSES: Final = frozenset({"waiting", "deferred"})
COMPLETED_STATUSES: Final = frozenset(
    {"completed", "complete", "done", "accepted", "skipped"}
)
FAILED_STATUSES: Final = frozenset(
    {"blocked", "failed", "quarantined", "rejected"}
)
OTHER_TERMINAL_STATUSES: Final = frozenset(
    {"cancelled", "superseded"}
)


class OperatorError(RuntimeError):
    """A typed, fail-closed PCTDD control-plane failure."""


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise OperatorError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_object(path: Path) -> dict[str, Any]:
    """Read one bounded regular JSON object without following a final symlink."""

    try:
        metadata = os.lstat(path)
    except OSError as exc:
        raise OperatorError(f"required JSON artifact is unavailable: {path}") from exc
    if (
        stat.S_ISLNK(metadata.st_mode)
        or not stat.S_ISREG(metadata.st_mode)
        or metadata.st_size > MAX_JSON_BYTES
    ):
        raise OperatorError(f"JSON artifact is not a bounded regular file: {path}")
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                OperatorError(f"non-finite JSON number: {value}")
            ),
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise OperatorError(f"JSON artifact is malformed: {path}") from exc
    if not isinstance(payload, dict):
        raise OperatorError(f"JSON artifact must be an object: {path}")
    return payload


def _contained(path: Path) -> Path:
    candidate = Path(os.path.abspath(path))
    try:
        candidate.relative_to(ROOT)
    except ValueError as exc:
        raise OperatorError(f"runtime path escapes the repository: {candidate}") from exc
    return candidate


def _private_directory(path: Path) -> Path:
    """Create an owned, non-linked, mode-0700 directory inside the checkout."""

    directory = _contained(path)
    directory.mkdir(parents=True, exist_ok=True)
    observed = os.lstat(directory)
    if (
        stat.S_ISLNK(observed.st_mode)
        or not stat.S_ISDIR(observed.st_mode)
        or observed.st_uid != os.geteuid()
    ):
        raise OperatorError(f"runtime directory custody is unsafe: {directory}")
    os.chmod(directory, 0o700)
    return directory


def _atomic_private_text(path: Path, text: str) -> None:
    target = _contained(path)
    _private_directory(target.parent)
    temporary = target.with_name(f".{target.name}.tmp.{os.getpid()}")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _ensure_import_path() -> None:
    for item in (str(ACCEL_ROOT), str(ROOT)):
        if item not in sys.path:
            sys.path.insert(0, item)


def _load_board(config_path: Path) -> tuple[Any, dict[str, Any]]:
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        load_configured_board,
    )

    config = _contained(config_path)
    board = load_configured_board(config, repo_root=ROOT)
    payload = dict(board.payload)
    prefix = str(board.task_prefix).removeprefix("## ").strip()
    if board.board_namespace != PROGRAM_ID or prefix != TASK_PREFIX:
        raise OperatorError("scheduler configuration is not the sealed PCTDD v1 board")
    program = board.resolved_database_program()
    if program.authority_mode != "quack" or program.task_source_kind != "duckdb":
        raise OperatorError("PCTDD requires DuckDB task authority served only through Quack")
    if program.failover_policy != "fail_closed":
        raise OperatorError("PCTDD Quack authority must fail closed")
    match = QUACK_ENDPOINT_RE.fullmatch(program.quack_endpoint)
    if match is None or not 1 <= int(match.group(2)) <= 65535:
        raise OperatorError("PCTDD Quack endpoint must be a bounded loopback URI")
    if not str(program.store_id).endswith(".duckdb"):
        raise OperatorError("database store_id must identify the sealed DuckDB file")
    if not str(program.endpoint_secret_handle).startswith("env://"):
        raise OperatorError("PCTDD requires an env:// opaque Quack secret handle")

    ducklake = payload.get("ducklake_projection_program")
    if ducklake is not None:
        if not isinstance(ducklake, Mapping):
            raise OperatorError("ducklake_projection_program must be an object")
        forbidden = (
            ducklake.get("authority") is True
            or ducklake.get("may_grant_authority") is True
            or ducklake.get("scheduling_prerequisite") is True
            or ducklake.get("completion_prerequisite") is True
        )
        if forbidden:
            raise OperatorError("DuckLake must remain non-authoritative and non-gating")
    return board, payload


def _runtime_paths(board: Any) -> dict[str, Path]:
    runtime = board.runtime_paths
    root = _contained(board.path(runtime["root"]))
    state = _contained(board.path(runtime["state"]))
    logs = _contained(board.path(runtime["logs"]))
    owner_value = runtime.get("quack_owner") or (
        Path(runtime["root"]) / "quack-owner"
    ).as_posix()
    owner = _contained(board.path(owner_value))
    program = board.resolved_database_program()
    database = _contained(board.path(program.store_id))
    return {
        "runtime": root,
        "state": state,
        "logs": logs,
        "owner": owner,
        "database": database,
        "owner_status": owner / "quack-state-server.status.json",
        "owner_pid": state / "pctdd-quack-owner.pid",
        "owner_log": logs / "pctdd-quack-owner.log",
        "master_pid": state / "configured-board-master.pid",
    }


def _python_environment(*, token: str = "", secret_handle: str = "") -> dict[str, str]:
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner import (
        scrub_state_credentials_from_environment,
    )

    environment = scrub_state_credentials_from_environment(
        os.environ,
        secret_handle=secret_handle,
    )
    ordered: list[str] = []
    for item in (
        str(ACCEL_ROOT),
        str(ROOT),
        *str(environment.get("PYTHONPATH") or "").split(os.pathsep),
    ):
        if item and item not in ordered:
            ordered.append(item)
    environment["PYTHONPATH"] = os.pathsep.join(ordered)
    environment["PYTHONUNBUFFERED"] = "1"
    if token:
        if not secret_handle.startswith("env://"):
            raise OperatorError("trusted child token transport requires an env:// handle")
        name = secret_handle.removeprefix("env://")
        if ENV_NAME_RE.fullmatch(name) is None:
            raise OperatorError("Quack env secret handle names an unsafe variable")
        environment[name] = token
        # This is the canonical Quack ATTACH credential name.  It is present
        # only in trusted supervisor children; provider subprocesses scrub it.
        environment["IPFS_ACCELERATE_AGENT_QUACK_TOKEN"] = token
    return environment


def _run(
    argv: Sequence[str],
    *,
    environment: Mapping[str, str] | None = None,
    timeout: float = 600.0,
) -> dict[str, Any]:
    completed = subprocess.run(
        list(argv),
        cwd=ROOT,
        env=dict(environment) if environment is not None else _python_environment(),
        text=True,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    stdout = completed.stdout.strip()
    parsed: Any = None
    if stdout:
        try:
            parsed = json.loads(stdout, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, OperatorError):
            parsed = None
    return {
        "returncode": int(completed.returncode),
        "json": parsed,
        "stdout": stdout[-12000:] if parsed is None else "",
        "stderr": completed.stderr.strip()[-4000:],
    }


def _require_success(result: Mapping[str, Any], operation: str) -> None:
    if int(result.get("returncode") or 0) != 0:
        raise OperatorError(f"{operation} failed")


def validate() -> dict[str, Any]:
    reports: dict[str, Any] = {}
    for name, path in (
        ("dependencies", DEPENDENCY_VALIDATOR),
        ("board", BOARD_VALIDATOR),
    ):
        if not path.is_file():
            raise OperatorError(f"missing sealed {name} validator: {path}")
        result = _run((sys.executable, str(path)), timeout=900.0)
        _require_success(result, f"{name} validation")
        reports[name] = result["json"] if result["json"] is not None else {
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        }
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "validate",
        "valid": True,
        "reports": reports,
    }


def materialize(config_path: Path) -> dict[str, Any]:
    board, _payload = _load_board(config_path)
    if not MATERIALIZER.is_file():
        raise OperatorError(f"missing sealed task materializer: {MATERIALIZER}")
    # The sealed materializer owns bootstrap writes before Quack starts.  Once
    # an owner is live, direct file materialization would violate exclusivity.
    paths = _runtime_paths(board)
    if paths["owner_status"].is_file():
        owner = _owner_projection(paths)
        if owner["liveness"] in {"alive", "unknown"}:
            raise OperatorError("refusing direct materialization while Quack owns DuckDB")
    result = _run((sys.executable, str(MATERIALIZER)), timeout=1200.0)
    _require_success(result, "PCTDD materialization")
    if not paths["database"].is_file():
        raise OperatorError("materializer returned success without the DuckDB authority")
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "materialize",
        "materialized": True,
        "database": str(paths["database"].relative_to(ROOT)),
        "duckdb_authoritative": True,
        "ducklake_authoritative": False,
        "materializer": result["json"] if result["json"] is not None else {
            "stdout": result["stdout"],
            "stderr": result["stderr"],
        },
    }


def preflight(config_path: Path) -> dict[str, Any]:
    _load_board(config_path)
    result = _run(
        (
            sys.executable,
            str(CONFIGURED_SCHEDULER),
            "--repo-root",
            str(ROOT),
            "--config",
            str(config_path),
            "preflight",
        ),
        timeout=900.0,
    )
    _require_success(result, "configured-board preflight")
    report = result["json"]
    if not isinstance(report, Mapping) or report.get("valid") is not True:
        raise OperatorError("configured-board preflight did not return valid=true")
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "preflight",
        "valid": True,
        "configured_board": report,
    }


def _owner_liveness(status_payload: Mapping[str, Any]) -> str:
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        OwnerLiveness,
        ProcessBirthIdentity,
        owner_liveness,
    )

    identity = status_payload.get("identity")
    birth = identity.get("process_birth") if isinstance(identity, Mapping) else None
    if not isinstance(birth, Mapping):
        return "absent"
    try:
        observed = owner_liveness(ProcessBirthIdentity.from_dict(birth))
    except Exception:
        return "unknown"
    if observed is OwnerLiveness.ALIVE:
        return "alive"
    if observed is OwnerLiveness.DEAD:
        return "dead"
    return "unknown"


def _owner_projection(paths: Mapping[str, Path]) -> dict[str, Any]:
    if not paths["owner_status"].is_file():
        return {"lifecycle": "absent", "liveness": "absent", "identity": {}}
    try:
        payload = _json_object(paths["owner_status"])
    except OperatorError:
        return {"lifecycle": "malformed", "liveness": "unknown", "identity": {}}
    identity = payload.get("identity")
    return {
        "lifecycle": str(payload.get("lifecycle") or "unknown"),
        "liveness": _owner_liveness(payload),
        "identity": dict(identity) if isinstance(identity, Mapping) else {},
    }


def _token_path(owner_dir: Path, secret_handle: str) -> Path:
    safe = secret_handle.replace(":", "_").replace("/", "_")
    return _contained(owner_dir / f"{safe}.quack-token")


def _read_owner_token(path: Path) -> str:
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise OperatorError("Quack token vault is unavailable") from exc
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.geteuid()
        or stat.S_IMODE(before.st_mode) != 0o600
        or before.st_nlink != 1
        or not 8 <= before.st_size <= 512
    ):
        raise OperatorError("Quack token vault file is not a private regular file")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise OperatorError("Quack token vault changed while opening")
        token = os.read(descriptor, 1024).decode("ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise OperatorError("Quack token vault cannot be read safely") from exc
    finally:
        os.close(descriptor)
    if TOKEN_RE.fullmatch(token) is None:
        raise OperatorError("Quack token vault material is malformed")
    return token


def _task_projection(connection: Any) -> dict[str, Any]:
    task_rows = connection.execute(
        "SELECT task_cid, task_alias, ordinal, status "
        "FROM tasks ORDER BY ordinal, task_alias"
    ).fetchall()
    dependency_rows = connection.execute(
        "SELECT task_cid, dependency_task_cid FROM task_dependencies"
    ).fetchall()
    block_rows = connection.execute(
        "SELECT task_cid FROM task_blocks WHERE state = 'active'"
    ).fetchall()

    records = [
        (str(row[0]), str(row[1]), int(row[2]), str(row[3]).strip().lower())
        for row in task_rows
    ]
    dependencies: dict[str, list[str]] = {}
    for row in dependency_rows:
        dependencies.setdefault(str(row[0]), []).append(str(row[1]))
    active_blocks = {str(row[0]) for row in block_rows}
    counts: dict[str, int] = {}
    for _cid, _alias, _ordinal, state in records:
        counts[state] = counts.get(state, 0) + 1

    completed_cids = {
        cid for cid, _alias, _ordinal, state in records if state in COMPLETED_STATUSES
    }
    ready_ids: list[str] = []
    waiting_ids: list[str] = []
    active_ids: list[str] = []
    blocked_ids: list[str] = []
    for cid, alias, _ordinal, state in records:
        if state in ACTIVE_STATUSES:
            active_ids.append(alias)
        if state in FAILED_STATUSES or cid in active_blocks:
            blocked_ids.append(alias)
            continue
        if state in WAITING_STATUSES:
            waiting_ids.append(alias)
            continue
        if state not in READY_STATUSES:
            continue
        unresolved = [dep for dep in dependencies.get(cid, ()) if dep not in completed_cids]
        if unresolved:
            waiting_ids.append(alias)
        else:
            ready_ids.append(alias)

    terminal_count = sum(
        count
        for state, count in counts.items()
        if state in COMPLETED_STATUSES | FAILED_STATUSES | OTHER_TERMINAL_STATUSES
    )
    task_count = len(records)
    return {
        "status_counts": dict(sorted(counts.items())),
        "task_count": task_count,
        "terminal_count": terminal_count,
        "completed_count": sum(counts.get(item, 0) for item in COMPLETED_STATUSES),
        "ready_count": len(ready_ids),
        "ready_task_ids": ready_ids[:100],
        "in_progress_count": len(active_ids),
        "in_progress_task_ids": active_ids[:100],
        "blocked_count": len(blocked_ids),
        "blocked_task_ids": blocked_ids[:100],
        "dependency_wait_count": len(waiting_ids),
        "dependency_wait_task_ids": waiting_ids[:100],
        "dependency_wait_is_blocker": False,
        "accepted_terminal": bool(
            task_count > 0
            and sum(counts.get(item, 0) for item in COMPLETED_STATUSES) == task_count
        ),
    }


def _authenticated_projection(board: Any, paths: Mapping[str, Path]) -> dict[str, Any]:
    owner = _owner_projection(paths)
    if owner["lifecycle"] != "ready" or owner["liveness"] != "alive":
        raise OperatorError("Quack owner is not live-ready")
    identity = owner["identity"]
    program = board.resolved_database_program()
    process_birth = identity.get("process_birth")
    process_birth = process_birth if isinstance(process_birth, Mapping) else {}
    if (
        identity.get("listen_uri") != program.quack_endpoint
        or identity.get("store_id") != program.store_id
        or identity.get("secret_handle") != program.endpoint_secret_handle
        or int(process_birth.get("pid") or 0) <= 1
    ):
        raise OperatorError("published Quack identity does not match the sealed program")
    token = _read_owner_token(
        _token_path(paths["owner"], program.endpoint_secret_handle)
    )
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
        open_quack_transport_connection,
    )

    connection = None
    try:
        connection = open_quack_transport_connection(
            program.quack_endpoint,
            token=token,
        )
        server_row = connection.execute(
            "SELECT server_id, store_id, database_uuid, process_birth_id, "
            "schema_revision, generation, status FROM state_servers "
            "WHERE server_id = ? ORDER BY generation DESC LIMIT 1",
            [str(identity.get("server_id") or "")],
        ).fetchone()
        if server_row is None:
            raise OperatorError("authenticated Quack query found no published owner")
        observed = {
            "server_id": str(server_row[0]),
            "store_id": str(server_row[1]),
            "database_uuid": str(server_row[2]),
            "process_birth_id": str(server_row[3]),
            "schema_revision": int(server_row[4]),
            "generation": int(server_row[5]),
            "status": str(server_row[6]),
        }
        for key in (
            "server_id",
            "store_id",
            "database_uuid",
            "process_birth_id",
            "schema_revision",
            "generation",
        ):
            expected = identity.get(key)
            if str(observed[key]) != str(expected):
                raise OperatorError(f"authenticated Quack identity mismatch: {key}")
        tasks = _task_projection(connection)
    finally:
        if connection is not None:
            connection.close()
    return {
        "authenticated_query": True,
        "transport": "quack_loopback_token_attach",
        "authority": "DuckDB/DatabaseTaskSource@1 via exclusive Quack owner",
        "direct_database_file_open": False,
        "identity": observed,
        **tasks,
    }


def _pid(path: Path) -> int:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    return int(value) if value.isdigit() else 0


def _pid_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _updated_age(payload: Mapping[str, Any]) -> float:
    text = str(payload.get("updated_at") or "").replace("Z", "+00:00")
    try:
        value = datetime.fromisoformat(text)
    except ValueError:
        return float("inf")
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return max(0.0, datetime.now(UTC).timestamp() - value.timestamp())


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower()).strip("-") or "pctdd"


def _supervisor_projection(board: Any, paths: Mapping[str, Path]) -> dict[str, Any]:
    master_pid = _pid(paths["master_pid"])
    state_prefix = _slug(str(board.task_prefix))
    freshness = max(
        120.0,
        float(board.payload.get("check_interval_seconds") or 20.0) * 4.0,
    )
    lanes: list[dict[str, Any]] = []
    for index in range(max(1, int(board.max_lanes))):
        lane_dir = paths["state"] / f"lane-{index}"
        prefix = f"{state_prefix}_lane_{index}"
        supervisor_pid = _pid(lane_dir / f"{prefix}_supervisor.pid")
        daemon_pid = _pid(lane_dir / f"{prefix}_managed_daemon.pid")
        status_path = lane_dir / f"{prefix}_supervisor_status.json"
        projection: dict[str, Any] = {}
        if status_path.is_file():
            try:
                payload = _json_object(status_path)
                projection = {
                    "status": str(payload.get("status") or "unknown"),
                    "updated_at": payload.get("updated_at"),
                    "age_seconds": _updated_age(payload),
                    "restart_count": int(payload.get("restart_count") or 0),
                }
            except (OperatorError, TypeError, ValueError):
                projection = {"status": "malformed", "age_seconds": float("inf")}
        live = (
            _pid_alive(supervisor_pid)
            and _pid_alive(daemon_pid)
            and bool(projection)
            and float(projection.get("age_seconds") or float("inf")) <= freshness
            and projection.get("status")
            not in {"blocked", "failed", "quarantined", "stopped", "malformed"}
        )
        lanes.append(
            {
                "index": index,
                "healthy": live,
                "supervisor_pid": supervisor_pid,
                "supervisor_alive": _pid_alive(supervisor_pid),
                "daemon_pid": daemon_pid,
                "daemon_alive": _pid_alive(daemon_pid),
                "projection": projection,
            }
        )
    healthy = sum(1 for item in lanes if item["healthy"])
    return {
        "master_pid": master_pid,
        "master_alive": _pid_alive(master_pid),
        "expected_lane_count": max(1, int(board.max_lanes)),
        "healthy_lane_count": healthy,
        "ready": _pid_alive(master_pid) and healthy == max(1, int(board.max_lanes)),
        "lanes": lanes,
    }


def _ducklake_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = payload.get("ducklake_projection_program")
    if not isinstance(raw, Mapping):
        return {
            "mode": "absent",
            "authoritative": False,
            "scheduler_gate": False,
        }
    catalog_text = str(raw.get("catalog_path") or "")
    data_text = str(raw.get("data_path") or "")
    catalog = _contained(ROOT / catalog_text) if catalog_text else None
    data = _contained(ROOT / data_text) if data_text else None
    return {
        "mode": str(raw.get("mode") or "configured_non_authoritative"),
        "authoritative": False,
        "scheduler_gate": False,
        "catalog_present": bool(catalog and catalog.is_file()),
        "data_present": bool(data and data.exists()),
    }


def status(config_path: Path) -> dict[str, Any]:
    board, payload = _load_board(config_path)
    paths = _runtime_paths(board)
    owner = _owner_projection(paths)
    authority: dict[str, Any]
    try:
        authority = _authenticated_projection(board, paths)
    except Exception as exc:
        authority = {
            "authenticated_query": False,
            "available": False,
            "reason_code": "authenticated_quack_query_unavailable",
            "error_class": type(exc).__name__,
        }
    else:
        authority["available"] = True
    supervisor = _supervisor_projection(board, paths)

    ready = int(authority.get("ready_count") or 0)
    active = int(authority.get("in_progress_count") or 0)
    blocked = int(authority.get("blocked_count") or 0)
    waiting = int(authority.get("dependency_wait_count") or 0)
    accepted_terminal = authority.get("accepted_terminal") is True
    if blocked:
        program_state = "blocked"
    elif accepted_terminal:
        program_state = "accepted_terminal"
    elif active:
        program_state = "running"
    elif ready:
        program_state = "schedulable"
    elif waiting:
        program_state = "stalled_dependency_frontier"
    elif authority.get("available") is True:
        program_state = "stalled_empty_frontier"
    else:
        program_state = "control_plane_unavailable"

    operational_ready = bool(
        owner["lifecycle"] == "ready"
        and owner["liveness"] == "alive"
        and authority.get("authenticated_query") is True
        and (supervisor["ready"] or accepted_terminal)
        and program_state not in {
            "blocked",
            "stalled_dependency_frontier",
            "stalled_empty_frontier",
            "control_plane_unavailable",
        }
    )
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "status",
        "operational_ready": operational_ready,
        "program_state": program_state,
        "state_owner": owner,
        "task_authority": authority,
        "supervisor": supervisor,
        "dependency_waits_are_not_blockers": True,
        "ducklake_projection": _ducklake_projection(payload),
    }


def _start_owner(board: Any, paths: Mapping[str, Path], *, timeout: float) -> dict[str, Any]:
    program = board.resolved_database_program()
    if not paths["database"].is_file():
        raise OperatorError("materialize the sealed DuckDB task store before launch")
    existing = _owner_projection(paths)
    if existing["lifecycle"] == "ready" and existing["liveness"] == "alive":
        _authenticated_projection(board, paths)
        return {"started": False, "already_running": True, "ready": True}
    if existing["liveness"] == "unknown":
        raise OperatorError("existing Quack owner liveness is unknown")

    for item in (paths["runtime"], paths["state"], paths["logs"], paths["owner"]):
        _private_directory(item)
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--config",
        str(board.config_path),
        "state-owner",
    ]
    descriptor = os.open(
        paths["owner_log"],
        os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    os.chmod(paths["owner_log"], 0o600)
    with os.fdopen(descriptor, "ab", buffering=0) as log:
        process = subprocess.Popen(
            argv,
            cwd=ROOT,
            env=_python_environment(secret_handle=program.endpoint_secret_handle),
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    _atomic_private_text(paths["owner_pid"], f"{process.pid}\n")
    deadline = time.monotonic() + max(1.0, timeout)
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise OperatorError("detached Quack owner exited before authenticated readiness")
        try:
            projection = _authenticated_projection(board, paths)
        except Exception:
            time.sleep(0.25)
            continue
        return {
            "started": True,
            "already_running": False,
            "detached": True,
            "ready": True,
            "pid": process.pid,
            "authenticated_query": projection["authenticated_query"],
            "log": str(paths["owner_log"].relative_to(ROOT)),
        }
    raise OperatorError("detached Quack owner did not reach authenticated readiness")


def _serve_state_owner(config_path: Path) -> dict[str, Any]:
    """Run the existing QuackStateServer with the pinned beta API adapter.

    The generic state-owner opens its DuckDB connection with the ordinary
    supervisor policy, which intentionally disables external access and locks
    the configuration before ``LOAD quack``.  Quack 1.5.5 therefore rejects
    the load with ``PermissionException``.  This bounded adapter changes only
    the owner connection/serve call: it loads the already-installed, sealed
    Quack extension before serving a loopback-only endpoint.  The existing
    server still owns migration, lease/fence, token vault, status, identity,
    stop, and cleanup semantics.
    """

    board, _payload = _load_board(config_path)
    paths = _runtime_paths(board)
    program = board.resolved_database_program()
    match = QUACK_ENDPOINT_RE.fullmatch(program.quack_endpoint)
    if match is None:
        raise OperatorError("state owner requires a sealed loopback endpoint")
    host, port = match.group(1), int(match.group(2))

    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        InProcessQuackTransport,
        build_server,
        listen_uri,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
        DuckDBConnection,
    )

    def owner_connection(path: Path) -> Any:
        import duckdb

        raw = duckdb.connect(
            str(path),
            config={
                "autoinstall_known_extensions": "false",
                "autoload_known_extensions": "false",
                "allow_unsigned_extensions": "false",
            },
        )
        try:
            # Quack's HTTP request path lazily needs the installed core
            # ``httpfs`` extension. Autoload stays disabled, so load that
            # exact local dependency explicitly before starting Quack.
            raw.execute("LOAD httpfs")
            raw.execute("LOAD quack")
        except BaseException:
            raw.close()
            raise
        return DuckDBConnection.wrap(raw)

    class LoopbackQuackTransport(InProcessQuackTransport):
        def start(
            self,
            connection: Any,
            *,
            host: str,
            port: int,
            token: str,
            identity: Any,
        ) -> Mapping[str, Any]:
            uri = listen_uri(host, port)
            connection.execute(
                "SELECT * FROM quack_serve(?, token := ?, "
                "allow_other_hostname := false, disable_ssl := true)",
                [uri, token],
            )
            self._started = True
            self._listen_uri = uri
            self._server_identity = {
                "server_id": identity.server_id,
                "store_id": identity.store_id,
                "database_uuid": identity.database_uuid,
                "schema_revision": identity.schema_revision,
                "schema_fingerprint": identity.schema_fingerprint,
                "generation": identity.generation,
                "process_birth_id": identity.process_birth_id,
                "listen_uri": uri,
            }
            return MappingProxyType(dict(self._server_identity))

        def stop(self, connection: Any | None = None) -> None:
            if connection is not None:
                try:
                    connection.execute("SELECT quack_stop()")
                except Exception:
                    pass
            super().stop(connection)

    for item in (paths["runtime"], paths["state"], paths["logs"], paths["owner"]):
        _private_directory(item)
    server = build_server(
        database_path=paths["database"],
        state_dir=paths["owner"],
        host=host,
        port=port,
        repository_id=f"repository:{PROGRAM_ID}",
        store_id=str(program.store_id),
        secret_handle=str(program.endpoint_secret_handle),
        transport=LoopbackQuackTransport(),
        connection_factory=owner_connection,
    )
    identity = server.start()
    stop_requested = {"value": False}

    def request_stop(_signum: int, _frame: Any) -> None:
        stop_requested["value"] = True

    previous_int = signal.signal(signal.SIGINT, request_stop)
    previous_term = signal.signal(signal.SIGTERM, request_stop)
    try:
        control = server.stop_control_path()
        while server.lifecycle.value == "ready" and not stop_requested["value"]:
            if control.is_file():
                break
            time.sleep(0.25)
        stopped = server.stop()
    finally:
        signal.signal(signal.SIGINT, previous_int)
        signal.signal(signal.SIGTERM, previous_term)
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "state-owner",
        "identity": identity.to_dict(),
        "stopped": stopped,
    }


def _scheduler_command(config_path: Path, *, dry_run: bool) -> tuple[str, ...]:
    command = [
        sys.executable,
        str(CONFIGURED_SCHEDULER),
        "--repo-root",
        str(ROOT),
        "--config",
        str(config_path),
        "launch",
        "--implement",
    ]
    if dry_run:
        command.append("--dry-run")
    return tuple(command)


def launch(
    config_path: Path,
    *,
    dry_run: bool,
    monitor_seconds: float = DEFAULT_MONITOR_SECONDS,
) -> dict[str, Any]:
    preflight_report = preflight(config_path)
    board, _payload = _load_board(config_path)
    if dry_run:
        result = _run(_scheduler_command(config_path, dry_run=True), timeout=900.0)
        _require_success(result, "configured-board implementation dry-run")
        return {
            "schema": OPERATOR_SCHEMA,
            "command": "launch",
            "mode": "dry_run",
            "valid": True,
            "preflight": preflight_report["configured_board"],
            "launch_plan": result["json"] if result["json"] is not None else {
                "stdout": result["stdout"],
                "stderr": result["stderr"],
            },
            "state_owner_started": False,
        }

    if not monitor_seconds > 0:
        raise OperatorError("--monitor-seconds must be positive")
    paths = _runtime_paths(board)
    owner = _start_owner(board, paths, timeout=min(120.0, monitor_seconds))
    token = _read_owner_token(
        _token_path(paths["owner"], board.resolved_database_program().endpoint_secret_handle)
    )
    result = _run(
        _scheduler_command(config_path, dry_run=False),
        environment=_python_environment(
            token=token,
            secret_handle=board.resolved_database_program().endpoint_secret_handle,
        ),
        timeout=900.0,
    )
    # Drop the sole in-memory copy owned by this operator as soon as the
    # canonical detached scheduler inherits its private environment.
    token = ""
    _require_success(result, "configured-board detached implementation launch")

    deadline = time.monotonic() + monitor_seconds
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = status(config_path)
        if last["operational_ready"] is True:
            return {
                "schema": OPERATOR_SCHEMA,
                "command": "launch",
                "mode": "real",
                "launched": True,
                "monitored": True,
                "state_owner": owner,
                "scheduler": result["json"] if result["json"] is not None else {
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                },
                "status": last,
            }
        if last.get("program_state") in {
            "blocked",
            "stalled_dependency_frontier",
            "stalled_empty_frontier",
        }:
            # Give newly launched lanes a short admission window before treating
            # an empty frontier as genuine; explicit blockers fail immediately.
            if last.get("program_state") == "blocked" or (
                deadline - time.monotonic() < monitor_seconds - 15.0
            ):
                raise OperatorError(
                    f"supervisor reached non-progress state: {last['program_state']}"
                )
        time.sleep(1.0)
    raise OperatorError("supervisor did not become healthy before the monitor deadline")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="repository-relative or absolute sealed scheduler configuration",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="run the sealed dependency and board validators")
    commands.add_parser("materialize", help="materialize goals/tasks into DuckDB")
    commands.add_parser("preflight", help="run canonical configured-board preflight")
    commands.add_parser(
        "state-owner",
        help="internal existing QuackStateServer loopback owner adapter",
    )
    launch_parser = commands.add_parser(
        "launch",
        help="dry-run or really launch the canonical detached supervisor",
    )
    mode = launch_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate/render without processes")
    mode.add_argument("--real", action="store_true", help="start Quack then the detached scheduler")
    launch_parser.add_argument(
        "--monitor-seconds",
        type=float,
        default=DEFAULT_MONITOR_SECONDS,
        help="positive health-monitoring window after a real launch",
    )
    status_parser = commands.add_parser(
        "status",
        help="authenticate to Quack and report task, master, and lane health",
    )
    status_parser.add_argument(
        "--require-ready",
        action="store_true",
        help="exit nonzero unless owner/query/supervisor are healthy and unstalled",
    )
    return parser


def _emit(payload: Mapping[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True), file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    config_path = arguments.config
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    try:
        if arguments.command == "validate":
            result = validate()
        elif arguments.command == "materialize":
            result = materialize(config_path)
        elif arguments.command == "preflight":
            result = preflight(config_path)
        elif arguments.command == "state-owner":
            result = _serve_state_owner(config_path)
        elif arguments.command == "launch":
            result = launch(
                config_path,
                dry_run=bool(arguments.dry_run),
                monitor_seconds=float(arguments.monitor_seconds),
            )
        elif arguments.command == "status":
            result = status(config_path)
            _emit(result)
            if arguments.require_ready and result["operational_ready"] is not True:
                return 1
            return 0
        else:  # pragma: no cover - argparse closes this vocabulary.
            raise OperatorError(f"unsupported command: {arguments.command}")
        _emit(result)
        return 0
    except OperatorError as exc:
        _emit(
            {
                "schema": OPERATOR_SCHEMA,
                "command": str(arguments.command),
                "ok": False,
                "error_class": type(exc).__name__,
                "error": str(exc),
            },
            stream=sys.stderr,
        )
        return 2
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
        # Unexpected third-party error text is not a trusted secret-redaction
        # surface.  Publish only the class and a fixed fail-closed message.
        _emit(
            {
                "schema": OPERATOR_SCHEMA,
                "command": str(arguments.command),
                "ok": False,
                "error_class": type(exc).__name__,
                "error": "operation failed closed",
            },
            stream=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
