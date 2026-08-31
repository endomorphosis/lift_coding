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
CONTROL_GENERATOR: Final = (
    ROOT / "scripts" / "generate_parallel_content_sealing_proof_carrying_tdd_controls.py"
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
OWNER_PID_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/pctdd-quack-owner-process@1"
)
PROGRAM_ID: Final = "parallel-content-sealing-proof-carrying-tdd-v1"
TASK_PREFIX: Final = "PCTDD-"
DEFAULT_MONITOR_SECONDS: Final = 180.0
MIN_STABLE_HEALTH_SECONDS: Final = 15.0
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
    """Read one stable bounded JSON object through its checked descriptor."""

    target = _contained(path)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(target, flags)
    except OSError as exc:
        raise OperatorError(f"required JSON artifact is unavailable: {target}") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_nlink != 1
            or not 0 <= before.st_size <= MAX_JSON_BYTES
        ):
            raise OperatorError(
                f"JSON artifact is not a bounded regular file: {target}"
            )
        raw = bytearray()
        while len(raw) <= MAX_JSON_BYTES:
            chunk = os.read(
                descriptor,
                min(64 * 1024, MAX_JSON_BYTES + 1 - len(raw)),
            )
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise OperatorError(f"JSON artifact cannot be read safely: {target}") from exc
    finally:
        os.close(descriptor)
    if len(raw) > MAX_JSON_BYTES:
        raise OperatorError(f"JSON artifact is not a bounded regular file: {target}")
    stable_fields = (
        "st_dev",
        "st_ino",
        "st_mode",
        "st_size",
        "st_mtime_ns",
        "st_ctime_ns",
        "st_nlink",
        "st_uid",
    )
    if (
        any(getattr(before, key) != getattr(after, key) for key in stable_fields)
        or len(raw) != after.st_size
    ):
        raise OperatorError(f"JSON artifact changed while being read: {target}")
    try:
        current = os.lstat(target)
    except OSError as exc:
        raise OperatorError(f"JSON artifact changed while being read: {target}") from exc
    if (current.st_dev, current.st_ino) != (after.st_dev, after.st_ino):
        raise OperatorError(f"JSON artifact changed while being read: {target}")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=lambda value: (_ for _ in ()).throw(
                OperatorError(f"non-finite JSON number: {value}")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise OperatorError(f"JSON artifact is malformed: {target}") from exc
    if not isinstance(payload, dict):
        raise OperatorError(f"JSON artifact must be an object: {target}")
    return payload


def _contained(path: Path) -> Path:
    """Confine a runtime path and reject every existing linked component."""

    root = Path(os.path.abspath(ROOT))
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise OperatorError(f"runtime path escapes the repository: {candidate}") from exc
    components = (
        root,
        *(
            root / Path(*relative.parts[:index])
            for index in range(1, len(relative.parts) + 1)
        ),
    )
    for index, component in enumerate(components):
        try:
            observed = os.lstat(component)
        except FileNotFoundError:
            break
        except OSError as exc:
            raise OperatorError(
                f"runtime path custody cannot be verified: {component}"
            ) from exc
        is_intermediate = index == 0 or index < len(components) - 1
        if (
            stat.S_ISLNK(observed.st_mode)
            or (is_intermediate and not stat.S_ISDIR(observed.st_mode))
            or observed.st_uid != os.geteuid()
        ):
            raise OperatorError(f"runtime path custody is unsafe: {component}")
    return candidate


def _repository_relative_argument(path: Path) -> str:
    """Return the confined relative spelling required by sealed child CLIs."""

    return _contained(path).relative_to(ROOT).as_posix()


def _private_directory(path: Path) -> Path:
    """Create an owned, non-linked, mode-0700 directory inside the checkout."""

    directory = _contained(path)
    root = Path(os.path.abspath(ROOT))
    current = root
    for component in directory.relative_to(root).parts:
        current /= component
        try:
            os.mkdir(current, 0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            raise OperatorError(
                f"runtime directory cannot be created safely: {current}"
            ) from exc
        try:
            observed = os.lstat(current)
        except OSError as exc:
            raise OperatorError(
                f"runtime directory custody cannot be verified: {current}"
            ) from exc
        if (
            stat.S_ISLNK(observed.st_mode)
            or not stat.S_ISDIR(observed.st_mode)
            or observed.st_uid != os.geteuid()
        ):
            raise OperatorError(f"runtime directory custody is unsafe: {current}")
    os.chmod(directory, 0o700)
    _contained(directory)
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
    process = subprocess.Popen(
        list(argv),
        cwd=ROOT,
        env=dict(environment) if environment is not None else _python_environment(),
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
        close_fds=True,
    )
    try:
        stdout_text, stderr_text = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _ensure_import_path()
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (
            terminate_process_with_grace,
        )

        terminated = terminate_process_with_grace(
            process,
            grace_seconds=5.0,
            kill_wait_seconds=5.0,
        )
        process.communicate()
        if terminated.timed_out:
            raise OperatorError(
                "operator child process tree did not terminate"
            ) from exc
        raise OperatorError("operator child process timed out") from exc
    stdout = stdout_text.strip()
    parsed: Any = None
    if stdout:
        try:
            parsed = json.loads(stdout, object_pairs_hook=_reject_duplicate_keys)
        except (json.JSONDecodeError, OperatorError):
            parsed = None
    return {
        "returncode": int(process.returncode or 0),
        "json": parsed,
        "stdout": stdout[-12000:] if parsed is None else "",
        "stderr": stderr_text.strip()[-4000:],
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
    result = _run(
        (
            sys.executable,
            str(MATERIALIZER),
            "materialize",
            "--config",
            _repository_relative_argument(config_path),
        ),
        timeout=1200.0,
    )
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


def capture_g9_inputs() -> dict[str, Any]:
    """Run the explicit stopped-g8 capture/final-control generation pass."""

    if not CONTROL_GENERATOR.is_file() or CONTROL_GENERATOR.is_symlink():
        raise OperatorError("missing sealed PCTDD control generator")
    result = _run(
        (sys.executable, str(CONTROL_GENERATOR), "--capture-g9-inputs"),
        timeout=300.0,
    )
    _require_success(result, "g9 stopped-predecessor capture")
    payload = result.get("json")
    if (
        not isinstance(payload, Mapping)
        or payload.get("capture_status") != "sealed_stopped_g8_capture"
        or payload.get("tasks") != 54
    ):
        raise OperatorError("g9 capture returned no sealed 54-task control package")
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "capture-g9-inputs",
        "ok": True,
        "capture": dict(payload),
    }


def seal_controls(config_path: Path) -> dict[str, Any]:
    board, _payload = _load_board(config_path)
    paths = _runtime_paths(board)
    if paths["owner_status"].is_file():
        owner = _owner_projection(paths)
        if owner["liveness"] in {"alive", "unknown"}:
            raise OperatorError("refusing direct operator sealing while Quack owns DuckDB")
    result = _run(
        (
            sys.executable,
            str(MATERIALIZER),
            "seal-controls",
            "--config",
            _repository_relative_argument(config_path),
        ),
        timeout=7200.0,
    )
    _require_success(result, "PCTDD staged operator control sealing")
    payload = result.get("json")
    if not isinstance(payload, Mapping) or payload.get("operator_controls_sealed") is not True:
        raise OperatorError("materializer did not produce an admitted operator seal")
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "seal-controls",
        "operator_controls_sealed": True,
        "materializer": payload,
    }


def _require_operator_seal(config_path: Path) -> Mapping[str, Any]:
    board, _payload = _load_board(config_path)
    paths = _runtime_paths(board)
    environment = _operator_seal_check_environment(board, paths)
    result = _run(
        (
            sys.executable,
            str(MATERIALIZER),
            "check-sealed",
            "--config",
            _repository_relative_argument(config_path),
        ),
        environment=environment,
        timeout=900.0,
    )
    _require_success(result, "PCTDD operator seal check")
    payload = result.get("json")
    if (
        not isinstance(payload, Mapping)
        or payload.get("valid") is not True
        or payload.get("operator_controls_sealed") is not True
    ):
        raise OperatorError("PCTDD-000 is not sealed at the exact current source")
    return payload


def preflight(config_path: Path) -> dict[str, Any]:
    _load_board(config_path)
    operator_seal = _require_operator_seal(config_path)
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
        "operator_seal": operator_seal,
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


def _exact_live_owner_identity(
    board: Any,
    owner: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Any]:
    """Return the sealed live-owner identity or fail before credential use."""

    if owner.get("lifecycle") != "ready" or owner.get("liveness") != "alive":
        raise OperatorError("Quack owner is not live-ready")
    identity = owner.get("identity")
    if not isinstance(identity, Mapping):
        raise OperatorError("published Quack identity is unavailable")
    program = board.resolved_database_program()
    process_birth = identity.get("process_birth")
    process_birth = process_birth if isinstance(process_birth, Mapping) else {}
    if (
        identity.get("status") != "ready"
        or identity.get("listen_uri") != program.quack_endpoint
        or identity.get("store_id") != program.store_id
        or identity.get("secret_handle") != program.endpoint_secret_handle
        or int(process_birth.get("pid") or 0) <= 1
        or int(process_birth.get("start_time_ticks") or 0) <= 0
    ):
        raise OperatorError("published Quack identity does not match the sealed program")
    return identity, program


def _operator_seal_check_environment(
    board: Any,
    paths: Mapping[str, Path],
) -> dict[str, str]:
    """Build the private environment for the trusted sealed-board checker.

    A live DuckDB owner may only be inspected through authenticated Quack.
    Therefore the token is read only for an exact ready+alive identity and is
    inherited only by the trusted materializer ``check-sealed`` child.  A
    stopped or absent owner keeps the ordinary scrubbed environment.  Every
    ambiguous or transitional projection fails closed before either a token
    read or a direct database open can occur.
    """

    owner = _owner_projection(paths)
    lifecycle = str(owner.get("lifecycle") or "unknown")
    liveness = str(owner.get("liveness") or "unknown")
    if lifecycle == "ready" and liveness == "alive":
        _identity, program = _exact_live_owner_identity(board, owner)
        token = _read_owner_token(
            _token_path(paths["owner"], program.endpoint_secret_handle)
        )
        return _python_environment(
            token=token,
            secret_handle=program.endpoint_secret_handle,
        )
    if liveness in {"alive", "unknown"} or lifecycle in {
        "starting",
        "ready",
        "stopping",
        "unknown",
        "malformed",
    }:
        raise OperatorError(
            "operator seal check requires an exact ready+alive or stopped owner"
        )
    return _python_environment()


def _cross_check_owner_lifecycle(
    owner: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    """Bind a stopped JSON projection to the fenced authoritative DB row."""

    result = dict(owner)
    result["lifecycle_consistent"] = None
    liveness = str(owner.get("liveness") or "unknown")
    if liveness == "alive":
        result["authoritative_lifecycle"] = {
            "available": False,
            "reason": "deferred_to_authenticated_live_owner",
            "direct_database_file_open": False,
        }
        return result
    if liveness == "unknown":
        result["authoritative_lifecycle"] = {
            "available": False,
            "reason": "owner_liveness_unknown",
            "direct_database_file_open": False,
        }
        return result

    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        inspect_state_server_lifecycle,
    )

    inspection = inspect_state_server_lifecycle(database_path=paths["database"])
    result["authoritative_lifecycle"] = inspection
    if inspection.get("available") is not True:
        return result
    latest = inspection.get("latest")
    latest_status = (
        str(latest.get("status") or "") if isinstance(latest, Mapping) else ""
    )
    if liveness in {"absent", "dead"} and latest_status in {"starting", "ready"}:
        result["lifecycle"] = "stale"
        result["lifecycle_consistent"] = False
        result["reason_code"] = "authoritative_server_owner_not_live"
        return result
    identity = owner.get("identity")
    if not isinstance(latest, Mapping) or not isinstance(identity, Mapping):
        result["lifecycle_consistent"] = latest is None and identity in (None, {})
        if result["lifecycle_consistent"] is False:
            result["reason_code"] = "status_projection_lifecycle_mismatch"
        return result
    consistent = all(
        str(latest.get(key)) == str(identity.get(key))
        for key in (
            "server_id",
            "store_id",
            "database_uuid",
            "process_birth_id",
            "listen_uri",
            "extension_fingerprint",
            "schema_revision",
            "generation",
            "started_at",
        )
    ) and (
        str(latest.get("status") or "")
        == str(owner.get("lifecycle") or "")
        == str(identity.get("status") or "")
    )
    if str(latest.get("status") or "") == "stopped":
        try:
            revisions_current = int(latest.get("revision")) >= int(
                identity.get("revision")
            )
        except (TypeError, ValueError):
            revisions_current = False
        consistent = (
            consistent
            and revisions_current
            and latest.get("stopped_at") is not None
        )
    result["lifecycle_consistent"] = bool(consistent)
    if not consistent:
        result["reason_code"] = "status_projection_lifecycle_mismatch"
    return result


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
    identity, program = _exact_live_owner_identity(board, owner)
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
            "listen_uri, extension_fingerprint, schema_revision, generation, "
            "started_at, status, revision FROM state_servers "
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
            "listen_uri": str(server_row[4]),
            "extension_fingerprint": str(server_row[5]),
            "schema_revision": int(server_row[6]),
            "generation": int(server_row[7]),
            "started_at": str(server_row[8]),
            "status": str(server_row[9]),
            "revision": int(server_row[10]),
        }
        for key in (
            "server_id",
            "store_id",
            "database_uuid",
            "process_birth_id",
            "listen_uri",
            "extension_fingerprint",
            "schema_revision",
            "generation",
            "started_at",
        ):
            expected = identity.get(key)
            if str(observed[key]) != str(expected):
                raise OperatorError(f"authenticated Quack identity mismatch: {key}")
        if (
            observed["status"] != "ready"
            or str(identity.get("status") or "") != "ready"
            or observed["revision"] != int(identity.get("revision") or 0) + 1
        ):
            raise OperatorError(
                "authenticated Quack lifecycle differs from the ready projection"
            )
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


def _owner_process_record(pid: int) -> dict[str, Any]:
    """Capture the detached owner's PID-reuse-resistant process identity."""

    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        read_process_birth,
    )

    try:
        birth = read_process_birth(int(pid))
    except OSError as exc:
        raise OperatorError("detached Quack owner process birth is unobservable") from exc
    if birth is None or birth.pid != int(pid) or birth.start_time_ticks <= 0:
        raise OperatorError("detached Quack owner exited before identity capture")
    return {
        "schema": OWNER_PID_SCHEMA,
        "pid": int(pid),
        "process_birth": birth.to_dict(),
        "recorded_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        ),
    }


def _write_owner_process_record(path: Path, record: Mapping[str, Any]) -> None:
    if (
        record.get("schema") != OWNER_PID_SCHEMA
        or int(record.get("pid") or 0) <= 1
        or not isinstance(record.get("process_birth"), Mapping)
        or int(record["process_birth"].get("pid") or 0) != int(record["pid"])
        or int(record["process_birth"].get("start_time_ticks") or 0) <= 0
    ):
        raise OperatorError("refusing malformed Quack owner process record")
    _atomic_private_text(
        path,
        json.dumps(dict(record), sort_keys=True, separators=(",", ":")) + "\n",
    )


def _cleanup_owned_owner_pid(
    path: Path,
    process_birth: Mapping[str, Any],
) -> bool:
    """Remove only the exact process record owned by the calling child."""

    target = _contained(path)
    try:
        before = os.lstat(target)
    except FileNotFoundError:
        return False
    except OSError:
        return False
    if (
        stat.S_ISLNK(before.st_mode)
        or not stat.S_ISREG(before.st_mode)
        or before.st_uid != os.geteuid()
        or before.st_nlink != 1
        or before.st_size > MAX_JSON_BYTES
    ):
        return False
    try:
        payload = _json_object(target)
    except OperatorError:
        return False
    recorded = payload.get("process_birth")
    if (
        payload.get("schema") != OWNER_PID_SCHEMA
        or not isinstance(recorded, Mapping)
        or int(payload.get("pid") or 0) != int(process_birth.get("pid") or 0)
        or dict(recorded) != dict(process_birth)
    ):
        return False
    try:
        current = os.lstat(target)
    except OSError:
        return False
    if (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
        return False
    try:
        target.unlink()
    except OSError:
        return False
    return True


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
    owner = _cross_check_owner_lifecycle(_owner_projection(paths), paths)
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
        if owner.get("liveness") == "alive":
            owner["authoritative_lifecycle"] = {
                "available": True,
                "reason": "authenticated_live_quack_query",
                "direct_database_file_open": False,
                "latest": dict(authority.get("identity") or {}),
            }
            owner["lifecycle_consistent"] = True
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
    try:
        process_record = _owner_process_record(process.pid)
        _write_owner_process_record(paths["owner_pid"], process_record)
    except Exception:
        _ensure_import_path()
        from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (
            terminate_process_with_grace,
        )

        terminate_process_with_grace(
            process,
            grace_seconds=5.0,
            kill_wait_seconds=5.0,
        )
        raise
    deadline = time.monotonic() + max(1.0, timeout)
    while time.monotonic() < deadline:
        if process.poll() is not None:
            _cleanup_owned_owner_pid(
                paths["owner_pid"],
                process_record["process_birth"],
            )
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
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (
        terminate_process_with_grace,
    )

    terminated = terminate_process_with_grace(
        process,
        grace_seconds=5.0,
        kill_wait_seconds=5.0,
    )
    if not terminated.timed_out:
        _cleanup_owned_owner_pid(
            paths["owner_pid"],
            process_record["process_birth"],
        )
    raise OperatorError("detached Quack owner did not reach authenticated readiness")


def _serve_state_owner(config_path: Path) -> dict[str, Any]:
    """Run the existing QuackStateServer's reviewed real transport path.

    The authoritative writer remains external-access-disabled.  The state
    server checkpoints it into a verified read-only replica and loads the
    already-qualified Quack/httpfs extensions only on that transport replica.
    Mutation results therefore carry the exact fresh-replica proof required by
    remote clients instead of the deliberately non-admissible injected-test
    observation.
    """

    board, _payload = _load_board(config_path)
    paths = _runtime_paths(board)
    program = board.resolved_database_program()
    match = QUACK_ENDPOINT_RE.fullmatch(program.quack_endpoint)
    if match is None:
        raise OperatorError("state owner requires a sealed loopback endpoint")
    host, port = match.group(1), int(match.group(2))

    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        current_process_birth,
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        build_server,
    )

    for item in (paths["runtime"], paths["state"], paths["logs"], paths["owner"]):
        _private_directory(item)
    owned_birth = current_process_birth().to_dict()
    server: Any | None = None
    identity: Any | None = None
    stopped: Mapping[str, Any] | None = None
    stop_requested = {"value": False}

    def request_stop(_signum: int, _frame: Any) -> None:
        stop_requested["value"] = True

    previous_int: Any | None = None
    previous_term: Any | None = None
    try:
        server = build_server(
            database_path=paths["database"],
            state_dir=paths["owner"],
            host=host,
            port=port,
            repository_id=f"repository:{PROGRAM_ID}",
            store_id=str(program.store_id),
            secret_handle=str(program.endpoint_secret_handle),
        )
        identity = server.start()
        previous_int = signal.signal(signal.SIGINT, request_stop)
        previous_term = signal.signal(signal.SIGTERM, request_stop)
        control = server.stop_control_path()
        service_mutations = getattr(server, "service_mutation_inbox", None)
        if not callable(service_mutations):
            raise OperatorError(
                "Quack owner lacks the reviewed closed mutation-inbox authority"
            )
        while server.lifecycle.value == "ready" and not stop_requested["value"]:
            if control.is_file():
                break
            processed = int(service_mutations())
            time.sleep(0.01 if processed else 0.05)
        stopped = server.stop()
        return {
            "schema": OPERATOR_SCHEMA,
            "command": "state-owner",
            "identity": identity.to_dict(),
            "stopped": stopped,
        }
    finally:
        if previous_int is not None:
            signal.signal(signal.SIGINT, previous_int)
        if previous_term is not None:
            signal.signal(signal.SIGTERM, previous_term)
        if server is not None and server.lifecycle.value in {
            "starting",
            "ready",
            "stopping",
        }:
            try:
                server.stop()
            except Exception:
                pass
        _cleanup_owned_owner_pid(paths["owner_pid"], owned_birth)


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
    initial_authority = _authenticated_projection(board, paths)
    initial_completed = int(initial_authority.get("completed_count") or 0)
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
    healthy_since: float | None = None
    healthy_processes: tuple[int, ...] = ()
    progress_observed = False
    while time.monotonic() < deadline:
        last = status(config_path)
        authority = last.get("task_authority")
        authority = authority if isinstance(authority, Mapping) else {}
        progress_observed = progress_observed or bool(
            int(authority.get("in_progress_count") or 0) > 0
            or int(authority.get("completed_count") or 0) > initial_completed
            or authority.get("accepted_terminal") is True
        )
        supervisor = last.get("supervisor")
        supervisor = supervisor if isinstance(supervisor, Mapping) else {}
        lanes = supervisor.get("lanes")
        lanes = lanes if isinstance(lanes, list) else []
        process_signature = (
            int(supervisor.get("master_pid") or 0),
            *(
                process_id
                for lane in lanes
                if isinstance(lane, Mapping)
                for process_id in (
                    int(lane.get("supervisor_pid") or 0),
                    int(lane.get("daemon_pid") or 0),
                )
            ),
        )
        now = time.monotonic()
        if (
            last["operational_ready"] is True
            and progress_observed
            and process_signature
            and all(process_id > 1 for process_id in process_signature)
        ):
            if healthy_processes != process_signature:
                healthy_processes = process_signature
                healthy_since = now
            elif healthy_since is not None and (
                now - healthy_since >= MIN_STABLE_HEALTH_SECONDS
            ):
                return {
                    "schema": OPERATOR_SCHEMA,
                    "command": "launch",
                    "mode": "real",
                    "launched": True,
                    "monitored": True,
                    "stable_health_seconds": now - healthy_since,
                    "authoritative_progress_observed": True,
                    "initial_completed_count": initial_completed,
                    "state_owner": owner,
                    "scheduler": result["json"] if result["json"] is not None else {
                        "stdout": result["stdout"],
                        "stderr": result["stderr"],
                    },
                    "status": last,
                }
        else:
            healthy_since = None
            healthy_processes = ()
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
    if not progress_observed:
        raise OperatorError(
            "supervisor remained live but made no authoritative task progress "
            "before the monitor deadline"
        )
    raise OperatorError(
        "supervisor did not sustain healthy, unblocked execution before the "
        "monitor deadline"
    )


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
    commands.add_parser("materialize", help="stage goals/tasks in DuckDB with PCTDD-000 incomplete")
    commands.add_parser(
        "capture-g9-inputs",
        help="capture an exactly stopped g8 and regenerate final g9 controls",
    )
    commands.add_parser(
        "seal-controls",
        help="run the sealed profile, validators, preflight, and dry-run before completing PCTDD-000",
    )
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
        elif arguments.command == "capture-g9-inputs":
            result = capture_g9_inputs()
        elif arguments.command == "seal-controls":
            result = seal_controls(config_path)
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
