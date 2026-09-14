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
import hashlib
import select
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
NATIVE_STOP_MARKERS: Final = ("HOLD", "OPERATOR_STOP", "watchdog.disabled", "watchdog.hold")
OPERATOR_TASK_ALIAS: Final = "PCTDD-000"
DEFAULT_MONITOR_SECONDS: Final = 180.0
MIN_STABLE_HEALTH_SECONDS: Final = 15.0
DEFAULT_STARTUP_BLOCKER_GRACE_SECONDS: Final = 15.0
MAX_JSON_BYTES: Final = 8 * 1024 * 1024
MAX_OWNER_LOG_BYTES: Final = 64 * 1024 * 1024
PRIVATE_FILE_STABLE_FIELDS: Final = (
    "st_dev",
    "st_ino",
    "st_mode",
    "st_size",
    "st_mtime_ns",
    "st_ctime_ns",
    "st_nlink",
    "st_uid",
)
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
CLOSED_TASK_STATUSES: Final = frozenset(
    READY_STATUSES
    | ACTIVE_STATUSES
    | WAITING_STATUSES
    | COMPLETED_STATUSES
    | FAILED_STATUSES
    | OTHER_TERMINAL_STATUSES
)
CANONICAL_TASK_ALIASES: Final = tuple(
    f"PCTDD-{index:03d}" for index in range(54)
)
OPERATOR_ACCEPTED_STATUSES: Final = frozenset(
    {"completed", "accepted"}
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


def _require_native_start_allowed(paths: Mapping[str, Path]) -> None:
    """Honor configured operator stops without changing read-only recovery APIs.

    Presence, including a dangling symlink, blocks new work. Unknown filesystem
    state is not permission to restart. Callers recheck at their spawn boundary;
    these observations do not replace the existing resume and owner fences.
    """

    for name in NATIVE_STOP_MARKERS:
        try:
            (paths["runtime"] / name).lstat()
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise OperatorError("native stop marker observation failed") from exc
        raise OperatorError("native start blocked by stop marker: " + name)


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
            # Dependency-owned capability resolvers may emit bounded human
            # diagnostics before the child CLI's final machine record.  Admit
            # only the final non-empty line as JSON; never scan earlier output
            # for a convenient-looking authority record.
            final_line = next(
                (
                    line.strip()
                    for line in reversed(stdout.splitlines())
                    if line.strip()
                ),
                "",
            )
            try:
                parsed = json.loads(
                    final_line,
                    object_pairs_hook=_reject_duplicate_keys,
                )
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


def _configured_board_preflight(config_path: Path) -> Mapping[str, Any]:
    """Run the current scheduler's non-mutating, current-tree preflight."""

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
    return report


def preflight(config_path: Path) -> dict[str, Any]:
    _load_board(config_path)
    operator_seal = _require_operator_seal(config_path)
    report = _configured_board_preflight(config_path)
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


def _stable_file_identity(left: Any, right: Any) -> bool:
    return all(
        getattr(left, field) == getattr(right, field)
        for field in PRIVATE_FILE_STABLE_FIELDS
    )


def _private_regular_file(
    observed: Any,
    *,
    minimum_size: int,
    maximum_size: int,
) -> bool:
    return bool(
        stat.S_ISREG(observed.st_mode)
        and observed.st_uid == os.geteuid()
        and stat.S_IMODE(observed.st_mode) == 0o600
        and observed.st_nlink == 1
        and minimum_size <= observed.st_size <= maximum_size
    )


def _read_owner_token(path: Path) -> str:
    """Read one stable private token descriptor without blocking on devices."""

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
        raise OperatorError("Quack token vault is unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if not _private_regular_file(before, minimum_size=8, maximum_size=512):
            raise OperatorError(
                "Quack token vault file is not a private regular file"
            )
        raw = bytearray()
        while len(raw) <= 512:
            chunk = os.read(descriptor, 513 - len(raw))
            if not chunk:
                break
            raw.extend(chunk)
        after = os.fstat(descriptor)
        if (
            len(raw) > 512
            or len(raw) != after.st_size
            or not _stable_file_identity(before, after)
        ):
            raise OperatorError("Quack token vault changed while being read")
        try:
            current = os.lstat(target)
        except OSError as exc:
            raise OperatorError(
                "Quack token vault changed while being read"
            ) from exc
        if not _stable_file_identity(after, current):
            raise OperatorError("Quack token vault changed while being read")
        token = bytes(raw).decode("ascii").strip()
    except (OSError, UnicodeError) as exc:
        raise OperatorError("Quack token vault cannot be read safely") from exc
    finally:
        os.close(descriptor)
    if TOKEN_RE.fullmatch(token) is None:
        raise OperatorError("Quack token vault material is malformed")
    return token


def _open_private_owner_log(path: Path) -> int:
    """Open one bounded private append log through a verified descriptor."""

    target = _contained(path)
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_APPEND
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
        | getattr(os, "O_NONBLOCK", 0)
    )
    try:
        descriptor = os.open(target, flags, 0o600)
    except OSError as exc:
        raise OperatorError("Quack owner log cannot be opened safely") from exc
    admitted = False
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or opened.st_nlink != 1
            or not 0 <= opened.st_size <= MAX_OWNER_LOG_BYTES
        ):
            raise OperatorError(
                "Quack owner log is not a bounded private regular file"
            )
        os.fchmod(descriptor, 0o600)
        private = os.fstat(descriptor)
        if (
            not _private_regular_file(
                private,
                minimum_size=0,
                maximum_size=MAX_OWNER_LOG_BYTES,
            )
            or any(
                getattr(opened, field) != getattr(private, field)
                for field in (
                    "st_dev",
                    "st_ino",
                    "st_size",
                    "st_mtime_ns",
                    "st_nlink",
                    "st_uid",
                )
            )
        ):
            raise OperatorError("Quack owner log changed while being opened")
        try:
            current = os.lstat(target)
        except OSError as exc:
            raise OperatorError(
                "Quack owner log changed while being opened"
            ) from exc
        if not _stable_file_identity(private, current):
            raise OperatorError("Quack owner log changed while being opened")
        admitted = True
        return descriptor
    except OSError as exc:
        raise OperatorError("Quack owner log cannot be opened safely") from exc
    finally:
        if not admitted:
            os.close(descriptor)


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
    task_aliases = [alias for _cid, alias, _ordinal, _state in records]
    task_ordinals = [ordinal for _cid, _alias, ordinal, _state in records]
    task_identity_rows = [
        (cid, alias, ordinal)
        for cid, alias, ordinal, _state in records
    ]
    task_statuses = [state for _cid, _alias, _ordinal, state in records]
    operator_statuses = [
        state
        for _cid, alias, _ordinal, state in records
        if alias == OPERATOR_TASK_ALIAS
    ]
    return {
        "status_counts": dict(sorted(counts.items())),
        "task_count": task_count,
        "task_aliases": task_aliases,
        "task_ordinals": task_ordinals,
        "task_statuses": task_statuses,
        "task_statuses_closed": all(
            state in CLOSED_TASK_STATUSES for state in task_statuses
        ),
        "task_identity_rows": (
            task_identity_rows
            if task_count == len(CANONICAL_TASK_ALIASES)
            else []
        ),
        "task_identity_unique": bool(
            len({cid for cid, _alias, _ordinal, _state in records}) == task_count
            and len(set(task_aliases)) == task_count
            and len(set(task_ordinals)) == task_count
        ),
        "operator_task_status": (
            operator_statuses[0] if len(operator_statuses) == 1 else ""
        ),
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


def _configured_task_identities(board: Any) -> tuple[tuple[str, str, int], ...]:
    """Derive current task CIDs through the existing scheduler authority."""

    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        _configured_board_task_records,
        _git_identity,
    )

    source_head, _source_tree = _git_identity(board.repo_root)
    records = _configured_board_task_records(board, source_head=source_head)
    identities = tuple(
        (
            str(record["canonical_task_cid"]),
            str(record["task_id"]),
            ordinal,
        )
        for ordinal, record in enumerate(records, start=1)
    )
    if tuple(alias for _cid, alias, _ordinal in identities) != CANONICAL_TASK_ALIASES:
        raise OperatorError("current configured board task population is not canonical")
    return identities


def _require_runtime_resume_authority(
    authority: Mapping[str, Any],
    *,
    expected_task_identities: Sequence[tuple[str, str, int]],
) -> dict[str, Any]:
    """Admit only the canonical materialized program for runtime resume.

    Runtime resume intentionally does not reinterpret a historical bootstrap
    source seal as a current-source seal.  It instead requires the current
    configured-board preflight plus an authenticated query of the one existing
    task authority.  No Markdown task, generated appendix, cache, or worker
    claim can satisfy this gate.
    """

    raw_aliases = authority.get("task_aliases")
    raw_ordinals = authority.get("task_ordinals")
    raw_identities = authority.get("task_identity_rows")
    raw_statuses = authority.get("task_statuses")
    raw_status_counts = authority.get("status_counts")
    aliases = (
        tuple(str(item) for item in raw_aliases)
        if isinstance(raw_aliases, (list, tuple))
        else ()
    )
    ordinals = (
        tuple(raw_ordinals)
        if isinstance(raw_ordinals, (list, tuple))
        and all(isinstance(item, int) and not isinstance(item, bool) for item in raw_ordinals)
        else ()
    )
    identities = (
        tuple(tuple(item) for item in raw_identities)
        if isinstance(raw_identities, (list, tuple))
        and all(
            isinstance(item, (list, tuple))
            and len(item) == 3
            and isinstance(item[0], str)
            and isinstance(item[1], str)
            and isinstance(item[2], int)
            and not isinstance(item[2], bool)
            for item in raw_identities
        )
        else ()
    )
    statuses = (
        tuple(raw_statuses)
        if isinstance(raw_statuses, (list, tuple))
        and all(
            isinstance(item, str)
            and item == item.strip().lower()
            and item in CLOSED_TASK_STATUSES
            for item in raw_statuses
        )
        else ()
    )
    status_counts = (
        dict(raw_status_counts)
        if isinstance(raw_status_counts, Mapping)
        and all(
            isinstance(key, str)
            and key == key.strip().lower()
            and key in CLOSED_TASK_STATUSES
            and isinstance(value, int)
            and not isinstance(value, bool)
            and value >= 0
            for key, value in raw_status_counts.items()
        )
        else {}
    )
    computed_status_counts: dict[str, int] = {}
    for status in statuses:
        computed_status_counts[status] = computed_status_counts.get(status, 0) + 1
    expected_identities = tuple(expected_task_identities)
    operator_status = str(authority.get("operator_task_status") or "").lower()
    raw_task_count = authority.get("task_count")
    task_count = (
        raw_task_count
        if isinstance(raw_task_count, int) and not isinstance(raw_task_count, bool)
        else -1
    )
    raw_completed_count = authority.get("completed_count")
    completed_count = (
        raw_completed_count
        if isinstance(raw_completed_count, int)
        and not isinstance(raw_completed_count, bool)
        else -1
    )
    expected_completed_count = sum(
        1 for status in statuses if status in COMPLETED_STATUSES
    )
    if authority.get("authenticated_query") is not True:
        raise OperatorError("runtime resume lacks an authenticated Quack query")
    if (
        task_count != len(CANONICAL_TASK_ALIASES)
        or aliases != CANONICAL_TASK_ALIASES
        or ordinals != tuple(range(1, len(CANONICAL_TASK_ALIASES) + 1))
        or len(expected_identities) != len(CANONICAL_TASK_ALIASES)
        or identities != expected_identities
        or authority.get("task_identity_unique") is not True
        or len(statuses) != len(CANONICAL_TASK_ALIASES)
        or status_counts != computed_status_counts
        or sum(status_counts.values()) != len(CANONICAL_TASK_ALIASES)
        or authority.get("task_statuses_closed") is not True
        or completed_count != expected_completed_count
    ):
        raise OperatorError("runtime resume task population is not canonical")
    if (
        operator_status not in OPERATOR_ACCEPTED_STATUSES
        or not statuses
        or statuses[0] != operator_status
    ):
        raise OperatorError("runtime resume requires accepted PCTDD-000 controls")
    accepted_terminal = all(status in COMPLETED_STATUSES for status in statuses)
    if authority.get("accepted_terminal") is not accepted_terminal:
        raise OperatorError("runtime resume terminal projection is inconsistent")
    return {
        "authenticated_query": True,
        "canonical_task_count": len(CANONICAL_TASK_ALIASES),
        "canonical_task_population": True,
        "current_task_cid_binding": True,
        "operator_task_status": operator_status,
        "closed_task_status_population": True,
        "accepted_terminal": accepted_terminal,
        "direct_database_file_open": False,
    }


def _authenticated_projection(
    board: Any, paths: Mapping[str, Path], *, maintenance: bool = False,
) -> dict[str, Any]:
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
        if maintenance:
            connection.execute("BEGIN TRANSACTION")
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
        if maintenance:
            tasks["maintenance_task_rows"] = [[row[index] for index in range(8)] for row in connection.execute(
                "SELECT task_cid, task_alias, ordinal, status, revision, plan_cid, "
                "body_json, identity_json FROM tasks ORDER BY ordinal, task_alias"
            ).fetchall()]
            tasks["maintenance_block_rows"] = [[row[index] for index in range(8)] for row in connection.execute(
                "SELECT block_id, task_cid, blocker_kind, blocker_id, reason, "
                "created_at, cleared_at, state FROM task_blocks ORDER BY block_id"
            ).fetchall()]
            connection.execute("ROLLBACK")
            if _owner_projection(paths) != owner:
                raise OperatorError("maintenance owner changed during read transaction")
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


def _owner_recovery_lock(path: Path) -> Any:
    """Return the existing process-shared Quack one-winner authority."""

    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_owner_watchdog import (
        _OneWinnerLock,
    )

    return _OneWinnerLock(_contained(path))


def _start_owner(
    board: Any,
    paths: Mapping[str, Path],
    *,
    timeout: float,
    allow_sealed_initial_absence: bool = False,
) -> dict[str, Any]:
    """Adopt or recover Quack under its existing one-winner fence.

    A missing historical status is accepted only for a bootstrap whose strict
    operator seal was already checked.  Every ordinary recovery requires an
    exact dead process birth.  The shared watchdog lock is re-observed after
    acquisition, so concurrent bootstrap, resume, and managed-watchdog callers
    cannot all authorize a new owner from the same stale observation.
    """

    _require_native_start_allowed(paths)
    program = board.resolved_database_program()
    if not paths["database"].is_file():
        raise OperatorError("materialize the sealed DuckDB task store before launch")
    for item in (paths["runtime"], paths["state"], paths["logs"], paths["owner"]):
        _private_directory(item)
    deadline = time.monotonic() + max(1.0, timeout)
    winner = _owner_recovery_lock(
        paths["owner"] / ".managed-owner-recovery.lock"
    )
    lock_acquired = False
    while time.monotonic() < deadline:
        existing = _owner_projection(paths)
        if existing["lifecycle"] == "ready" and existing["liveness"] == "alive":
            _authenticated_projection(board, paths)
            return {
                "started": False,
                "already_running": True,
                "ready": True,
                "one_winner_lock_acquired": False,
            }
        if winner.acquire():
            lock_acquired = True
            break
        # A concurrent recovery winner may temporarily publish no status or a
        # starting status.  It alone may spawn; contenders wait and then adopt
        # its exact authenticated result instead of inferring absence.
        time.sleep(min(0.05, max(0.0, deadline - time.monotonic())))
    if not lock_acquired:
        raise OperatorError("Quack owner recovery lock remained contended")

    process: subprocess.Popen[bytes] | None = None
    process_record: Mapping[str, Any] | None = None
    owner_admitted = False
    try:
        existing = _owner_projection(paths)
        if existing["lifecycle"] == "ready" and existing["liveness"] == "alive":
            _authenticated_projection(board, paths)
            return {
                "started": False,
                "already_running": True,
                "ready": True,
                "one_winner_lock_acquired": True,
            }
        if existing["liveness"] == "unknown":
            raise OperatorError("existing Quack owner liveness is unknown")
        if existing["liveness"] == "alive":
            raise OperatorError("existing Quack owner is live but not healthy")
        if existing["liveness"] == "absent" and not allow_sealed_initial_absence:
            raise OperatorError("Quack owner absence is not recovery authority")
        if existing["liveness"] not in {"absent", "dead"}:
            raise OperatorError("existing Quack owner is not provably recoverable")

        if deadline - time.monotonic() <= 0:
            raise OperatorError("Quack owner recovery deadline expired")
        argv = [
            sys.executable,
            str(Path(__file__).resolve()),
            "--config",
            str(board.config_path),
            "state-owner",
        ]
        _require_native_start_allowed(paths)
        descriptor = _open_private_owner_log(paths["owner_log"])
        with os.fdopen(descriptor, "ab", buffering=0) as log:
            _require_native_start_allowed(paths)
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
        while time.monotonic() < deadline:
            if process.poll() is not None:
                _cleanup_owned_owner_pid(
                    paths["owner_pid"],
                    process_record["process_birth"],
                )
                raise OperatorError(
                    "detached Quack owner exited before authenticated readiness"
                )
            try:
                projection = _authenticated_projection(board, paths)
            except Exception:
                time.sleep(0.25)
                continue
            observed_owner = _owner_projection(paths)
            observed_identity = observed_owner.get("identity")
            observed_birth = (
                observed_identity.get("process_birth")
                if isinstance(observed_identity, Mapping)
                else None
            )
            if not isinstance(observed_birth, Mapping) or dict(observed_birth) != dict(
                process_record["process_birth"]
            ):
                raise OperatorError(
                    "authenticated Quack readiness names a different process birth"
                )
            owner_admitted = True
            return {
                "started": True,
                "already_running": False,
                "detached": True,
                "ready": True,
                "pid": process.pid,
                "authenticated_query": projection["authenticated_query"],
                "one_winner_lock_acquired": True,
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
    finally:
        try:
            if process is not None and not owner_admitted and process.poll() is None:
                _ensure_import_path()
                from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (
                    terminate_process_with_grace,
                )

                terminated = terminate_process_with_grace(
                    process,
                    grace_seconds=5.0,
                    kill_wait_seconds=5.0,
                )
                if (
                    not terminated.timed_out
                    and isinstance(process_record, Mapping)
                    and isinstance(process_record.get("process_birth"), Mapping)
                ):
                    _cleanup_owned_owner_pid(
                        paths["owner_pid"],
                        process_record["process_birth"],
                    )
        finally:
            winner.release()


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


def _reject_secret_echo(result: Mapping[str, Any], token: str) -> None:
    """Fail closed if a trusted child reflects its private Quack token."""

    try:
        encoded = json.dumps(result, sort_keys=True, default=str)
    except (TypeError, ValueError, RecursionError):
        encoded = str(result)
    if token and token in encoded:
        raise OperatorError("trusted scheduler child emitted private credential material")


def _exact_blocked_task_ids(
    authority: Mapping[str, Any],
    *,
    source: str,
    require_authenticated: bool,
) -> frozenset[str]:
    """Return one exact, bounded blocker set or reject its projection.

    The authenticated Quack projection contains the complete 54-task PCTDD
    population, so a count/list mismatch, duplicate, or foreign alias cannot
    be treated as startup-recovery evidence.
    """

    raw_count = authority.get("blocked_count", 0)
    raw_ids = authority.get("blocked_task_ids", [])
    if (
        isinstance(raw_count, bool)
        or not isinstance(raw_count, int)
        or raw_count < 0
        or raw_count > len(CANONICAL_TASK_ALIASES)
        or not isinstance(raw_ids, list)
    ):
        raise OperatorError(f"malformed {source} blocked-task projection")
    blocked_ids = tuple(raw_ids)
    if (
        len(blocked_ids) != raw_count
        or any(
            not isinstance(task_id, str)
            or task_id not in CANONICAL_TASK_ALIASES
            for task_id in blocked_ids
        )
    ):
        raise OperatorError(f"malformed {source} blocked-task projection")
    if len(set(blocked_ids)) != len(blocked_ids):
        raise OperatorError(f"malformed {source} blocked-task projection")
    if blocked_ids and (
        require_authenticated
        and authority.get("authenticated_query") is not True
    ):
        raise OperatorError(
            f"unauthenticated {source} blocked-task projection"
        )
    return frozenset(blocked_ids)


def _startup_blocker_grace_seconds(board: Any, monitor_seconds: float) -> float:
    """Bound detached-lane blocker recovery by policy and monitor deadline."""

    payload = getattr(board, "payload", None)
    raw_grace: Any = DEFAULT_STARTUP_BLOCKER_GRACE_SECONDS
    if isinstance(payload, Mapping) and "watchdog_startup_grace_seconds" in payload:
        raw_grace = payload["watchdog_startup_grace_seconds"]
    if (
        isinstance(raw_grace, bool)
        or not isinstance(raw_grace, (int, float))
        or not 0.0 <= float(raw_grace) < float("inf")
    ):
        raise OperatorError("invalid watchdog startup blocker grace")
    return min(float(raw_grace), monitor_seconds)


MAINTENANCE_OBSERVATION_SCHEMA = OPERATOR_SCHEMA + "/blocked-maintenance-observation@1"


class DiagnosedBlockedMaintenance(OperatorError):
    """Native launch completed infrastructure recovery; work remains blocked.

    This remains an OperatorError for ordinary command-line callers. Only the
    retained maintenance caller may consume the separate diagnostic outcome.
    It grants no callback, task, acceptance, or publication authority.
    """

    def __init__(self, observation: Mapping[str, Any]):
        super().__init__("infrastructure recovered; authenticated initial work remains blocked")
        self.observation = json.loads(json.dumps(observation))


def _maintenance_require(condition: bool, reason: str) -> None:
    if not condition:
        raise OperatorError("blocked maintenance observation refused: " + reason)


def _maintenance_read_source(path: Path, *, bound: int) -> bytes:
    """Read sealed source without depending on a newer runtime helper module."""
    _maintenance_require(not path.is_symlink(), "source path is a symlink")
    target = _contained(path)
    fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        _maintenance_require(stat.S_ISREG(before.st_mode) and before.st_uid == os.geteuid()
                             and before.st_nlink == 1 and 0 <= before.st_size <= bound,
                             "source is not a bounded owned regular file")
        raw = bytearray()
        while len(raw) <= bound:
            chunk = os.read(fd, min(65536, bound + 1 - len(raw)))
            if not chunk:
                break
            raw.extend(chunk)
        fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns",
                  "st_uid", "st_nlink")
        after, named = os.fstat(fd), target.lstat()
        _maintenance_require(all(getattr(before, key) == getattr(after, key) == getattr(named, key)
                                 for key in fields) and len(raw) == before.st_size,
                             "source changed during bounded read")
        return bytes(raw)
    finally:
        os.close(fd)


def _maintenance_source(config_path: Path) -> dict[str, Any]:
    """Observe source bytes without optional Git index refresh writes."""
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        _read_control_plane_source_snapshot, IMPORTED_CONTROL_PLANE_SOURCE, CONTROL_PLANE_SOURCE_PATHS,
    )
    source = _read_control_plane_source_snapshot()
    _maintenance_require(IMPORTED_CONTROL_PLANE_SOURCE.get("source_id") == source.get("source_id"),
                         "loaded runtime source differs from current source")
    _maintenance_require(bool(source.get("source_id")) and bool(source.get("control_plane_tree_id"))
                         and [item.get("path") for item in source.get("sources", [])] == list(CONTROL_PLANE_SOURCE_PATHS)
                         and all(item.get("available") is True for item in source.get("sources", [])),
                         "runtime source incomplete")
    roots = (ROOT, ACCEL_ROOT, ROOT / "external/ipfs_datasets", ROOT / "external/ipfs_kit")
    revisions = []
    for root in roots:
        result = subprocess.run(
            ["git", "--no-optional-locks", "-c", "diff.autoRefreshIndex=false", "-C", str(root),
             "rev-parse", "--show-toplevel", "HEAD"], capture_output=True, text=True, timeout=10,
            env=_python_environment(),
        )
        lines = result.stdout.splitlines()
        _maintenance_require(result.returncode == 0 and len(lines) == 2 and lines[0] == str(root)
                             and bool(re.fullmatch(r"[0-9a-f]{40}", lines[1])), "repository identity unavailable")
        revisions.append([str(root), lines[1]])
    _maintenance_require(source.get("repository_revision") == revisions[1][1],
                         "loaded runtime revision differs from adopted checkout")
    for item in source["sources"]:
        raw = _maintenance_read_source(ACCEL_ROOT / item["path"], bound=16 * 1024 * 1024)
        _maintenance_require(len(raw) == item["size_bytes"]
                             and hashlib.sha256(raw).hexdigest() == item["sha256"],
                             "loaded runtime bytes differ from adopted checkout")
    # The retained native driver may use an independently qualified identical
    # runtime checkout. Path provenance is not source-content identity: all
    # loaded/current/adopted file bytes and runtime revision were checked above.
    source = {key: value for key, value in source.items() if key != "repository_root"}
    files = []
    for path in (Path(__file__), config_path):
        raw = _maintenance_read_source(path, bound=MAX_JSON_BYTES)
        files.append([str(path), hashlib.sha256(raw).hexdigest()])
    return {"repositories": revisions, "files": files, "runtime": source}


def _maintenance_rows(authority: Mapping[str, Any]) -> tuple[dict[str, list[Any]], dict[str, list[Any]]]:
    rows = authority.get("maintenance_task_rows")
    blocks = authority.get("maintenance_block_rows")
    _maintenance_require(isinstance(rows, list) and isinstance(blocks, list), "full task/block rows missing")
    identities = authority.get("task_identity_rows")
    statuses = authority.get("task_statuses")
    _maintenance_require(isinstance(identities, list) and isinstance(statuses, list)
                         and len(rows) == len(identities) == len(statuses), "full task population differs")
    by_alias: dict[str, list[Any]] = {}
    for index, row in enumerate(rows):
        _maintenance_require(isinstance(row, list) and len(row) == 8
                             and row[:3] == list(identities[index]) and row[3] == statuses[index]
                             and type(row[4]) is int and row[4] >= 0
                             and all(isinstance(row[i], str) for i in (0, 1, 3, 5, 6, 7))
                             and row[1] not in by_alias, "task identity/status/revision differs")
        by_alias[row[1]] = row
    by_id: dict[str, list[Any]] = {}
    cids = {row[0] for row in rows}
    for row in blocks:
        _maintenance_require(isinstance(row, list) and len(row) == 8
                             and all(isinstance(row[i], str) for i in (0, 1, 2, 3, 4, 5, 7))
                             and (row[6] is None or isinstance(row[6], str))
                             and bool(row[0]) and row[0] not in by_id and row[1] in cids,
                             "block record malformed, duplicated or foreign")
        by_id[row[0]] = row
    return by_alias, by_id


def _maintenance_block_subset(baseline: Mapping[str, Any], current: Mapping[str, Any]) -> list[str]:
    old_tasks, old_blocks = _maintenance_rows(baseline)
    tasks, blocks = _maintenance_rows(current)
    old_ids = _exact_blocked_task_ids(baseline, source="maintenance baseline", require_authenticated=True)
    ids = _exact_blocked_task_ids(current, source="maintenance current", require_authenticated=True)
    _maintenance_require(bool(ids) and ids <= old_ids, "new or absent current blocker")
    # Resolution may remove blockers. Every surviving blocked task and every
    # current active block must still be the exact previously observed record.
    for alias in ids:
        _maintenance_require(tasks[alias] == old_tasks.get(alias), "surviving blocked task changed")
        cid = tasks[alias][0]
        _maintenance_require([row for row in blocks.values() if row[1] == cid and row[7] == "active"]
                             == [row for row in old_blocks.values() if row[1] == cid and row[7] == "active"],
                             "surviving task blocker population changed")
    for block_id, row in blocks.items():
        if row[7] == "active":
            _maintenance_require(row == old_blocks.get(block_id), "new or replaced active blocker")
    current_active = {row[1] for row in blocks.values() if row[7] == "active"}
    derived = {alias for alias, row in tasks.items() if row[3] in FAILED_STATUSES or row[0] in current_active}
    _maintenance_require(derived == ids, "blocked aliases differ from exact records")
    return sorted(ids)


def capture_maintenance_baseline(config_path: Path) -> dict[str, Any]:
    """Read the existing authority; never open its local database or mutate it.

    A source-bound maintenance driver may execute this reviewed observer before
    source adoption using the existing old owner's native transport and schema.
    Its outer custody/source gates must remain held across that observation.
    """
    board, _ = _load_board(config_path)
    paths = _runtime_paths(board)
    source = _maintenance_source(config_path)
    authority = _authenticated_projection(board, paths, maintenance=True)
    _require_runtime_resume_authority(authority, expected_task_identities=_configured_task_identities(board))
    _maintenance_rows(authority)
    _maintenance_require(_maintenance_source(config_path) == source, "source changed during baseline")
    return {"schema": MAINTENANCE_OBSERVATION_SCHEMA, "source": source,
            "authority": authority, "callback_settlement_claimed": False}


def _maintenance_process(pid: int) -> dict[str, Any]:
    """Positive kernel identity only; inaccessible or reused actors refuse."""
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import read_process_birth
    _maintenance_require(type(pid) is int and pid > 1, "invalid actor PID")
    before = read_process_birth(pid)
    _maintenance_require(before is not None, "actor is not positively live")
    root = Path("/proc") / str(pid)
    def bounded(name: str) -> bytes:
        with (root / name).open("rb") as handle:
            value = handle.read(131073)
        _maintenance_require(len(value) <= 131072, "actor metadata bound")
        return value
    fields = bounded("stat").decode().rsplit(")", 1)[1].split()
    value = {"birth": before.to_dict(), "uid": root.stat().st_uid,
             "argv": [part.decode() for part in bounded("cmdline").split(b"\0") if part],
             "cwd": os.readlink(root / "cwd"), "root": os.readlink(root / "root"),
             "exe": os.readlink(root / "exe"), "group": int(fields[2]), "session": int(fields[3]),
             "cgroup": bounded("cgroup").decode(),
             "namespaces": {name: os.readlink(root / "ns" / name) for name in ("mnt", "pid", "user")}}
    _maintenance_require(read_process_birth(pid) == before and fields[0] not in {"Z", "X", "T", "t"}
                         and value["uid"] == os.geteuid() and value["cwd"] == str(ROOT)
                         and value["root"] == os.readlink("/proc/self/root")
                         and value["exe"] == os.readlink("/proc/self/exe")
                         and value["namespaces"] == {name: os.readlink("/proc/self/ns/" + name)
                                                    for name in ("mnt", "pid", "user")},
                         "actor birth, execution or namespace differs")
    return value


def _maintenance_option(argv: Sequence[str], name: str, value: str) -> bool:
    return [argv[i + 1] for i, token in enumerate(argv[:-1]) if token == name] == [value]


def _maintenance_daemon_command(board: Any, wrapper: Mapping[str, Any], daemon: Mapping[str, Any]) -> None:
    """Reconstruct the exact existing native command without starting a wrapper.

    Config parsing and the non-plan-bound command renderer are pure. Deliberately
    bypass the supervisor constructor, which has unrelated stateful work.
    """
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (
        PortalImplementationSupervisor, parse_args, supervisor_config_from_args,
    )
    argv = wrapper["argv"]
    entry = str(ROOT / "scripts/ops/agent_supervisor/implementation_supervisor_entry.py")
    _maintenance_require(len(argv) > 2 and argv[1] == entry, "native wrapper entry differs")
    config = supervisor_config_from_args(parse_args(list(argv[2:])), repo_root=ROOT)
    _maintenance_require(not config.plan_bound_dispatch and config.daemon_script_path is None
                         and config.database_program is not None
                         and config.database_program == board.resolved_database_program()
                         and config.task_prefix == board.task_prefix
                         and config.board_namespace == board.board_namespace
                         and config.task_shard_count == int(board.max_lanes),
                         "native daemon configured scope differs")
    renderer = object.__new__(PortalImplementationSupervisor)
    renderer.config = config
    renderer.board_namespace = board.board_namespace
    expected = renderer._build_daemon_command()
    _maintenance_require(renderer._commands_match_with_verified_executable_alias(daemon["argv"], expected),
                         "native daemon command differs")


def _maintenance_cohort_identity(cohort: Mapping[str, Any]) -> dict[str, Any]:
    """Owner PPID is observational; its stable birth survives caller exit.

    Native Quack liveness binds PID, start ticks and boot. The owner's launch
    parent can exit after a qualified handoff. Preserve the full observations
    in receipts while comparing that exact native immutable birth definition.
    Lane direct-parent relationships remain part of the compared identity.
    """
    value = json.loads(json.dumps(cohort))
    owner_birth = value["owner"]["birth"]
    value["owner"]["birth"] = {key: owner_birth[key] for key in ("pid", "start_time_ticks", "boot_id")}
    return value


class _BlockedMaintenanceMonitor:
    """Retain the actual launched cohort while native observations qualify it."""
    def __init__(self, config_path: Path, board: Any, paths: Mapping[str, Path],
                 baseline: Mapping[str, Any], admitted_identity: Mapping[str, Any]):
        _maintenance_require(baseline.get("schema") == MAINTENANCE_OBSERVATION_SCHEMA
                             and baseline.get("callback_settlement_claimed") is False,
                             "baseline schema differs")
        self.config_path, self.board, self.paths = config_path, board, paths
        self.baseline = json.loads(json.dumps(baseline))
        self.admitted_identity = json.loads(json.dumps(admitted_identity))
        self.expected = _configured_task_identities(board)
        _require_runtime_resume_authority(self.baseline["authority"], expected_task_identities=self.expected)
        _maintenance_rows(self.baseline["authority"])
        self.source = _maintenance_source(config_path)
        self.master_pid = 0
        self.fds: dict[int, int] = {}
        self.cohort: dict[str, Any] | None = None
        self.since: float | None = None
        self.last: dict[str, Any] | None = None

    def close(self) -> None:
        for descriptor in self.fds.values():
            os.close(descriptor)
        self.fds.clear()

    def bind_launch(self, result: Mapping[str, Any]) -> None:
        payload = result.get("json")
        if isinstance(payload, Mapping) and type(payload.get("master_pid")) is int:
            pid = payload["master_pid"]
        else:
            # The existing non-plan-bound native launcher emits these exact
            # terminal key=value records after its printed launch plan.
            values = re.findall(r"^master_pid=([1-9][0-9]*)$", str(result.get("stdout") or ""), re.M)
            _maintenance_require(len(values) == 1, "native launched master receipt unavailable")
            pid = int(values[0])
        self.master_pid = pid
        self.launched_master = self.actor(pid)
        argv = self.launched_master["argv"]
        _maintenance_require("ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner" in argv
                             and _maintenance_option(argv, "--repo-root", str(ROOT))
                             and _maintenance_option(argv, "--master-dir", str(self.paths["runtime"])),
                             "launched master scope differs")

    def actor(self, pid: int) -> dict[str, Any]:
        value = _maintenance_process(pid)
        if pid not in self.fds:
            descriptor = os.pidfd_open(pid, 0)
            try:
                _maintenance_require(_maintenance_process(pid) == value, "actor changed while retaining pidfd")
                self.fds[pid] = descriptor
            except BaseException:
                os.close(descriptor)
                raise
        _maintenance_require(not select.select([self.fds[pid]], [], [], 0)[0], "retained actor exited")
        return value

    def observe(self, advisory: Mapping[str, Any], now: float, *, allow_resolved: bool = False) -> None:
        authority = _authenticated_projection(self.board, self.paths, maintenance=True)
        _require_runtime_resume_authority(authority, expected_task_identities=self.expected)
        identity = authority["identity"]
        _maintenance_require(identity == self.admitted_identity, "newly admitted owner changed")
        old_identity = self.baseline["authority"]["identity"]
        _maintenance_require(all(identity[key] == old_identity[key] for key in
                                ("store_id", "database_uuid", "listen_uri", "schema_revision", "extension_fingerprint"))
                             and type(identity["generation"]) is int
                             and identity["generation"] > old_identity["generation"], "owner store/generation differs")
        _maintenance_require(_maintenance_source(self.config_path) == self.source, "source changed")
        _maintenance_rows(authority)
        current_ids = _exact_blocked_task_ids(authority, source="maintenance current", require_authenticated=True)
        if not current_ids and not allow_resolved:
            self.since, self.last = None, None
            return
        remaining = (_maintenance_block_subset(self.baseline["authority"], authority) if current_ids else [])
        supervisor = _supervisor_projection(self.board, self.paths)
        lanes = supervisor.get("lanes", [])
        if not (supervisor.get("ready") is True and supervisor.get("master_pid") == self.master_pid
                and len(lanes) == int(self.board.max_lanes) == 4
                and all(lane.get("healthy") is True for lane in lanes)):
            self.since, self.last = None, None
            return
        master = self.actor(self.master_pid)
        _maintenance_require(master == self.launched_master, "launched master changed")
        published, _ = _exact_live_owner_identity(self.board, _owner_projection(self.paths))
        _maintenance_require(all(str(published.get(key)) == str(value)
                                 for key, value in identity.items() if key != "revision")
                             and int(published.get("revision", -1)) + 1 == identity["revision"],
                             "authenticated and published owner differ")
        owner = self.actor(published["process_birth"]["pid"])
        from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import ProcessBirthIdentity
        from ipfs_accelerate_py.agent_supervisor.runtime.quack_owner_watchdog import process_births_match
        _maintenance_require(process_births_match(ProcessBirthIdentity.from_dict(owner["birth"]),
                                                  ProcessBirthIdentity.from_dict(published["process_birth"])),
                             "owner birth differs")
        actors = {"master": master, "owner": owner, "lanes": []}
        for index, lane in enumerate(lanes):
            _maintenance_require(lane["index"] == index, "lane population differs")
            wrapper = self.actor(lane["supervisor_pid"])
            daemon = self.actor(lane["daemon_pid"])
            directory = self.paths["state"] / f"lane-{index}"
            prefix = f"{_slug(str(self.board.task_prefix))}_lane_{index}"
            _maintenance_require(wrapper["birth"]["parent_pid"] == self.master_pid
                                 and daemon["birth"]["parent_pid"] == wrapper["birth"]["pid"]
                                 and str(ROOT / "scripts/ops/agent_supervisor/implementation_supervisor_entry.py") in wrapper["argv"]
                                 and all(_maintenance_option(actor["argv"], "--state-dir", str(directory))
                                         and _maintenance_option(actor["argv"], "--state-prefix", prefix)
                                         for actor in (wrapper, daemon))
                                 and _maintenance_option(wrapper["argv"], "--task-shard-index", str(index)),
                                 "lane parent or native scope differs")
            _maintenance_daemon_command(self.board, wrapper, daemon)
            projection = _json_object(directory / (prefix + "_supervisor_status.json"))
            runtime = self.source["runtime"]
            _maintenance_require(projection.get("supervisor_pid") == wrapper["birth"]["pid"]
                                 and projection.get("control_plane_source_id") == runtime["source_id"]
                                 and projection.get("control_plane_current_source_id") == runtime["source_id"]
                                 and projection.get("control_plane_source_tree_id") == runtime["control_plane_tree_id"]
                                 and projection.get("control_plane_update_pending") is False,
                                 "lane loaded source differs")
            actors["lanes"].append({"index": index, "wrapper": wrapper, "daemon": daemon})
        for retained in [master, owner, *(actor for lane in actors["lanes"] for actor in (lane["wrapper"], lane["daemon"]))]:
            _maintenance_require(self.actor(retained["birth"]["pid"]) == retained,
                                 "cohort changed before observation completed")
        _maintenance_require(_maintenance_source(self.config_path) == self.source,
                             "source changed before observation completed")
        final_owner, _ = _exact_live_owner_identity(self.board, _owner_projection(self.paths))
        _maintenance_require(final_owner == published, "owner changed before observation completed")
        if self.cohort is None:
            self.cohort, self.since = actors, now
        else:
            _maintenance_require(_maintenance_cohort_identity(actors) == _maintenance_cohort_identity(self.cohort),
                                 "retained launch cohort changed")
            if self.since is None:
                self.since = now
        self.last = {"schema": MAINTENANCE_OBSERVATION_SCHEMA,
                     "outcome": ("infrastructure_recovered_work_blocked" if remaining else "infrastructure_cohort_verified"),
                     "operational_ready": False,
                     "callback_settlement_claimed": False, "task_acceptance_claimed": False,
                     "baseline": self.baseline, "source": self.source, "cohort": actors,
                     "authority": authority, "remaining_blocked_task_ids": remaining,
                     "stable_health_seconds": now - self.since}

    def raise_diagnosed(self, advisory: Mapping[str, Any]) -> dict[str, Any]:
        # Freshly repeat all gates at the actual native refusal boundary. No
        # earlier status JSON, exception text, or fixture count can issue this.
        self.observe(advisory, time.monotonic(), allow_resolved=True)
        _maintenance_require(self.last is not None
                             and self.last["stable_health_seconds"] >= MIN_STABLE_HEALTH_SECONDS,
                             "infrastructure stability window incomplete")
        if self.last["remaining_blocked_task_ids"]:
            raise DiagnosedBlockedMaintenance(self.last)
        # A blocker may resolve after the advisory status was sampled. Keep
        # the same cohort's infrastructure timer, then require ordinary native
        # readiness and repeat custody after that read before returning success.
        return self.resolved_readiness(MIN_STABLE_HEALTH_SECONDS)

    def resolved_readiness(self, minimum_stable_seconds: float = 0.0) -> dict[str, Any]:
        ready = status(self.config_path)
        authority = ready.get("task_authority", {})
        _require_runtime_resume_authority(authority, expected_task_identities=self.expected)
        _maintenance_require(ready.get("operational_ready") is True
                             and authority.get("identity") == self.admitted_identity,
                             "resolved boundary lacks ordinary native readiness")
        self.observe(ready, time.monotonic(), allow_resolved=True)
        _maintenance_require(self.last is not None and not self.last["remaining_blocked_task_ids"]
                             and self.last["stable_health_seconds"] >= minimum_stable_seconds,
                             "resolved boundary changed during readiness observation")
        return ready


def verify_diagnosed_blocked_maintenance(config_path: Path, observation: Mapping[str, Any]) -> dict[str, Any]:
    """Fresh read-only verification of the previously diagnosed exact cohort."""
    _maintenance_require(observation.get("schema") == MAINTENANCE_OBSERVATION_SCHEMA
                         and observation.get("outcome") == "infrastructure_recovered_work_blocked"
                         and observation.get("operational_ready") is False
                         and observation.get("callback_settlement_claimed") is False
                         and observation.get("stable_health_seconds", 0) >= MIN_STABLE_HEALTH_SECONDS,
                         "diagnosed observation shape differs")
    board, _ = _load_board(config_path)
    check = _BlockedMaintenanceMonitor(config_path, board, _runtime_paths(board), observation["baseline"], observation["authority"]["identity"])
    try:
        _maintenance_require(check.source == observation["source"], "diagnosed source changed")
        check.master_pid = observation["cohort"]["master"]["birth"]["pid"]
        check.launched_master = observation["cohort"]["master"]
        check.cohort = observation["cohort"]
        check.observe({}, time.monotonic(), allow_resolved=True)
        _maintenance_require(check.last is not None, "diagnosed infrastructure is not healthy")
        if not check.last["remaining_blocked_task_ids"]:
            check.resolved_readiness()
            check.last["outcome"] = "infrastructure_recovered_work_unblocked"
            check.last["operational_ready"] = True
        return {"original_diagnosis": json.loads(json.dumps(observation)),
                "current_verification": check.last}
    finally:
        check.close()


def _launch_scheduler_and_monitor(
    config_path: Path,
    *,
    board: Any,
    paths: Mapping[str, Path],
    owner: Mapping[str, Any],
    initial_authority: Mapping[str, Any],
    monitor_seconds: float,
    command: str,
    mode: str,
    runtime_admission: Mapping[str, Any] | None = None,
    maintenance_baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Launch the one configured scheduler and monitor authoritative progress."""

    _require_native_start_allowed(paths)
    maintenance = (
        _BlockedMaintenanceMonitor(config_path, board, paths, maintenance_baseline, initial_authority["identity"])
        if maintenance_baseline is not None else None
    )
    try:
        initial_completed = int(initial_authority.get("completed_count") or 0)
        initial_blocked_ids = _exact_blocked_task_ids(
            initial_authority,
            source="initial",
            require_authenticated=True,
        )
        startup_blocker_grace = _startup_blocker_grace_seconds(
            board,
            monitor_seconds,
        )
        program = board.resolved_database_program()
        token = _read_owner_token(_token_path(paths["owner"], program.endpoint_secret_handle))
        _require_native_start_allowed(paths)
        result = _run(
            _scheduler_command(config_path, dry_run=False),
            environment=_python_environment(
                token=token,
                secret_handle=program.endpoint_secret_handle,
            ),
            timeout=900.0,
        )
        try:
            _reject_secret_echo(result, token)
        finally:
            # Drop the sole in-memory copy owned by this operator as soon as the
            # canonical detached scheduler inherits its private environment.
            token = ""
        _require_success(result, "configured-board detached implementation launch")
        if maintenance is not None:
            maintenance.bind_launch(result)

        monitor_started = time.monotonic()
        deadline = monitor_started + monitor_seconds
        startup_blocker_deadline = monitor_started + startup_blocker_grace
        last: dict[str, Any] = {}
        healthy_since: float | None = None
        healthy_processes: tuple[int, ...] = ()
        progress_observed = False
        def maintenance_boundary_response() -> dict[str, Any]:
            assert maintenance is not None
            ready = maintenance.raise_diagnosed(last)
            authority = ready["task_authority"]
            ready_progress = progress_observed or bool(
                int(authority.get("in_progress_count") or 0) > 0
                or int(authority.get("completed_count") or 0) > initial_completed
                or authority.get("accepted_terminal") is True
            )
            _maintenance_require(ready_progress, "resolved boundary lacks authoritative progress")
            response = {
                "schema": OPERATOR_SCHEMA, "command": command, "mode": mode,
                "launched": True, "already_running": False, "accepted_terminal": False,
                "process_health_claimed": True, "monitored": True,
                "stable_health_seconds": maintenance.last["stable_health_seconds"],
                "authoritative_progress_observed": True,
                "initial_completed_count": initial_completed, "state_owner": dict(owner),
                "scheduler": result["json"] if result["json"] is not None else {
                    "stdout": result["stdout"], "stderr": result["stderr"],
                }, "status": ready,
            }
            if runtime_admission is not None:
                response["runtime_admission"] = dict(runtime_admission)
            return response
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
            if (
                authority.get("authenticated_query") is True
                and authority.get("accepted_terminal") is True
                and last.get("program_state") == "accepted_terminal"
            ):
                response = {
                    "schema": OPERATOR_SCHEMA,
                    "command": command,
                    "mode": mode,
                    "launched": True,
                    "already_running": False,
                    "accepted_terminal": True,
                    "process_health_claimed": False,
                    "monitored": True,
                    "authoritative_progress_observed": True,
                    "initial_completed_count": initial_completed,
                    "state_owner": dict(owner),
                    "scheduler": result["json"] if result["json"] is not None else {
                        "stdout": result["stdout"],
                        "stderr": result["stderr"],
                    },
                    "status": last,
                }
                if runtime_admission is not None:
                    response["runtime_admission"] = dict(runtime_admission)
                return response
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
            if maintenance is not None:
                maintenance.observe(last, now, allow_resolved=True)
            expected_lane_count = int(supervisor.get("expected_lane_count") or 0)
            all_lanes_live = bool(
                expected_lane_count > 0
                and len(lanes) == expected_lane_count
                and all(
                    isinstance(lane, Mapping) and lane.get("healthy") is True
                    for lane in lanes
                )
            )
            if (
                last["operational_ready"] is True
                and progress_observed
                and supervisor.get("master_alive") is True
                and supervisor.get("ready") is True
                and all_lanes_live
                and process_signature
                and all(process_id > 1 for process_id in process_signature)
            ):
                if healthy_processes != process_signature:
                    healthy_processes = process_signature
                    healthy_since = now
                elif healthy_since is not None and (
                    now - healthy_since >= MIN_STABLE_HEALTH_SECONDS
                ):
                    response = {
                        "schema": OPERATOR_SCHEMA,
                        "command": command,
                        "mode": mode,
                        "launched": True,
                        "already_running": False,
                        "accepted_terminal": False,
                        "process_health_claimed": True,
                        "monitored": True,
                        "stable_health_seconds": now - healthy_since,
                        "authoritative_progress_observed": True,
                        "initial_completed_count": initial_completed,
                        "state_owner": dict(owner),
                        "scheduler": result["json"] if result["json"] is not None else {
                            "stdout": result["stdout"],
                            "stderr": result["stderr"],
                        },
                        "status": last,
                    }
                    if runtime_admission is not None:
                        response["runtime_admission"] = dict(runtime_admission)
                    return response
            else:
                healthy_since = None
                healthy_processes = ()
            if last.get("program_state") in {
                "blocked",
                "stalled_dependency_frontier",
                "stalled_empty_frontier",
            }:
                # Give newly launched lanes a short admission window before treating
                # an empty frontier as genuine. Exact blockers already present in
                # the authenticated pre-launch authority may be reconciled by those
                # lanes during the bounded startup window. New, additional, or
                # malformed blockers remain immediate fail-closed terminals.
                if last.get("program_state") == "blocked":
                    current_blocked_ids = _exact_blocked_task_ids(
                        authority,
                        source="current",
                        require_authenticated=True,
                    )
                    if not current_blocked_ids:
                        raise OperatorError(
                            "malformed current blocked-task projection"
                        )
                    new_blocked_ids = current_blocked_ids - initial_blocked_ids
                    if new_blocked_ids:
                        joined = ", ".join(sorted(new_blocked_ids))
                        raise OperatorError(
                            "supervisor reported new blocked task after detached "
                            f"launch: {joined}"
                        )
                    if time.monotonic() >= startup_blocker_deadline:
                        if maintenance is not None:
                            return maintenance_boundary_response()
                        raise OperatorError(
                            "initial authenticated blockers persisted through the "
                            "bounded startup recovery window"
                        )
                elif deadline - time.monotonic() < monitor_seconds - 15.0:
                    raise OperatorError(
                        f"supervisor reached non-progress state: {last['program_state']}"
                    )
            time.sleep(1.0)
        if last.get("program_state") == "blocked":
            if maintenance is not None:
                return maintenance_boundary_response()
            raise OperatorError(
                "initial authenticated blockers persisted through the bounded "
                "startup recovery window"
            )
        if maintenance is not None and last.get("operational_ready") is True:
            return maintenance_boundary_response()
        if not progress_observed:
            raise OperatorError(
                "supervisor remained live but made no authoritative task progress "
                "before the monitor deadline"
            )
        raise OperatorError(
            "supervisor did not sustain healthy, unblocked execution before the "
            "monitor deadline"
        )
    finally:
        if maintenance is not None:
            maintenance.close()


def launch(
    config_path: Path,
    *,
    dry_run: bool,
    monitor_seconds: float = DEFAULT_MONITOR_SECONDS,
) -> dict[str, Any]:
    if dry_run:
        # A dry-run is deliberately side-effect free: it validates the sealed
        # controls before asking the configured scheduler to render its plan,
        # and it never starts or recovers the live state owner.
        preflight_report = preflight(config_path)
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
    # The configured-board gate is non-mutating and must pass before any
    # config-derived directory, database owner, or scheduler side effect.  A
    # stale ready row whose exact process birth is dead may still need Quack
    # recovery before the strict historical seal can query the live authority;
    # all other bootstrap states run the strict seal before and after recovery.
    board, payload = _load_board(config_path)
    _configured_board_preflight(config_path)
    revalidated_board, revalidated_payload = _load_board(config_path)
    if (
        revalidated_payload != payload
        or getattr(revalidated_board, "configuration_root", None)
        != getattr(board, "configuration_root", None)
    ):
        raise OperatorError("scheduler configuration changed before owner recovery")
    board = revalidated_board
    paths = _runtime_paths(board)
    initial_owner = _owner_projection(paths)
    preflight_report: Mapping[str, Any] | None = None
    seal_can_precede_owner = not (
        initial_owner.get("liveness") in {"alive", "unknown"}
        or initial_owner.get("lifecycle")
        in {"starting", "ready", "stopping", "unknown", "malformed"}
    ) or (
        initial_owner.get("lifecycle") == "ready"
        and initial_owner.get("liveness") == "alive"
    )
    if seal_can_precede_owner:
        preflight_report = preflight(config_path)
        sealed_board, sealed_payload = _load_board(config_path)
        if (
            sealed_payload != payload
            or getattr(sealed_board, "configuration_root", None)
            != getattr(board, "configuration_root", None)
            or _runtime_paths(sealed_board) != paths
        ):
            raise OperatorError("scheduler configuration changed before owner recovery")
        board = sealed_board
    owner = _start_owner(
        board,
        paths,
        timeout=min(120.0, monitor_seconds),
        allow_sealed_initial_absence=bool(
            preflight_report is not None
            and initial_owner.get("lifecycle") == "absent"
            and initial_owner.get("liveness") == "absent"
        ),
    )
    # Always repeat the strict seal against the resulting authenticated owner.
    preflight_report = preflight(config_path)
    revalidated_board, revalidated_payload = _load_board(config_path)
    if (
        revalidated_payload != payload
        or getattr(revalidated_board, "configuration_root", None)
        != getattr(board, "configuration_root", None)
        or _runtime_paths(revalidated_board) != paths
    ):
        raise OperatorError("scheduler configuration changed during owner recovery")
    initial_authority = _authenticated_projection(revalidated_board, paths)
    return _launch_scheduler_and_monitor(
        config_path,
        board=revalidated_board,
        paths=paths,
        owner=owner,
        initial_authority=initial_authority,
        monitor_seconds=monitor_seconds,
        command="launch",
        mode="real",
    )


def _resume_locked(
    config_path: Path,
    *,
    board: Any,
    payload: Mapping[str, Any],
    paths: Mapping[str, Path],
    monitor_seconds: float,
    maintenance_baseline: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resume one current runtime while the operator serialization is held."""

    configured_preflight = _configured_board_preflight(config_path)
    revalidated_board, revalidated_payload = _load_board(config_path)
    if (
        revalidated_payload != payload
        or getattr(revalidated_board, "configuration_root", None)
        != getattr(board, "configuration_root", None)
        or _runtime_paths(revalidated_board) != paths
    ):
        raise OperatorError("scheduler configuration changed during runtime resume")
    _require_native_start_allowed(paths)
    owner = _start_owner(
        revalidated_board,
        paths,
        timeout=min(120.0, monitor_seconds),
    )
    post_owner_board, post_owner_payload = _load_board(config_path)
    if (
        post_owner_payload != payload
        or getattr(post_owner_board, "configuration_root", None)
        != getattr(board, "configuration_root", None)
        or _runtime_paths(post_owner_board) != paths
    ):
        raise OperatorError("scheduler configuration changed during owner recovery")
    revalidated_board = post_owner_board
    expected_task_identities = _configured_task_identities(revalidated_board)
    authority = _authenticated_projection(revalidated_board, paths)
    admission = _require_runtime_resume_authority(
        authority,
        expected_task_identities=expected_task_identities,
    )
    supervisor = _supervisor_projection(revalidated_board, paths)
    if admission["accepted_terminal"] is True:
        return {
            "schema": OPERATOR_SCHEMA,
            "command": "resume",
            "mode": "runtime_resume",
            "valid": True,
            "launched": False,
            "already_running": bool(supervisor.get("master_alive") is True),
            "accepted_terminal": True,
            "process_health_claimed": False,
            "monitored": False,
            "state_owner": dict(owner),
            "configured_board_preflight": dict(configured_preflight),
            "runtime_admission": admission,
            "supervisor": supervisor,
        }
    if supervisor.get("master_alive") is True:
        if supervisor.get("ready") is not True:
            raise OperatorError(
                "existing configured-board coordinator is live but not healthy"
            )
        blocked_task_ids = _exact_blocked_task_ids(
            authority,
            source="runtime resume",
            require_authenticated=True,
        )
        if blocked_task_ids:
            raise OperatorError(
                "existing configured-board coordinator is healthy but the "
                "authoritative board is blocked: "
                + ", ".join(sorted(blocked_task_ids))
            )
        return {
            "schema": OPERATOR_SCHEMA,
            "command": "resume",
            "mode": "runtime_resume",
            "valid": True,
            "launched": False,
            "already_running": True,
            "monitored": False,
            "state_owner": dict(owner),
            "configured_board_preflight": dict(configured_preflight),
            "runtime_admission": admission,
            "supervisor": supervisor,
        }
    return _launch_scheduler_and_monitor(
        config_path,
        board=revalidated_board,
        paths=paths,
        owner=owner,
        initial_authority=authority,
        monitor_seconds=monitor_seconds,
        command="resume",
        mode="runtime_resume",
        runtime_admission=admission,
        maintenance_baseline=maintenance_baseline,
    )


def _maintain_accepted_submodule_before_resume(
    config_path: Path, *, board: Any, payload: Mapping[str, Any], paths: Mapping[str, Path]
) -> Mapping[str, Any]:
    """Self-repair accepted dependency checkout drift under the resume guard.

    This never repairs a Git lock, changes the executing accelerator, or admits
    task/callback results. The runtime helper creates its own fresh preflight and
    allows only one clean, declared datasets/kit descendant gitlink mismatch.
    """
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.runtime.accepted_submodule_maintenance import (
        maintain_accepted_configured_submodule,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import exclusive_file_lock

    winner = _owner_recovery_lock(paths["owner"] / ".managed-owner-recovery.lock")
    if not winner.acquire():
        raise OperatorError("accepted dependency maintenance owner guard is contended")
    try:
        with exclusive_file_lock(paths["owner"] / "write-transaction.lock", timeout_seconds=30):
            def guard() -> None:
                current_board, current_payload = _load_board(config_path)
                if (current_payload != payload or _runtime_paths(current_board) != paths or
                    getattr(current_board, "configuration_root", None) != getattr(board, "configuration_root", None)):
                    raise OperatorError("scheduler configuration changed during dependency maintenance")
                _require_native_start_allowed(paths)

            guard()
            return maintain_accepted_configured_submodule(
                board,
                archive_root=Path.home() / ".local/state/ipfs-taskboard-native-maintenance",
                custody_guard=guard,
            )
    finally:
        winner.release()


def resume(
    config_path: Path,
    *,
    monitor_seconds: float = DEFAULT_MONITOR_SECONDS,
) -> dict[str, Any]:
    """Ensure the accepted runtime is live after current-tree evolution.

    This is distinct from bootstrap ``launch``: it does not pretend an old
    source-bound PCTDD-000 receipt seals later accepted implementation commits.
    The current configured-board preflight and authenticated canonical task
    population are its fail-closed resume authority.
    """

    if not monitor_seconds > 0:
        raise OperatorError("--monitor-seconds must be positive")
    board, payload = _load_board(config_path)
    maintenance_needed = False
    try:
        _configured_board_preflight(config_path)
    except OperatorError as rejected_preflight:
        # Pure assessment precedes even config-derived state directory creation.
        # Only the exact admissible checkout mismatch reaches the native guards;
        # the mutating helper independently repeats assessment under those guards.
        try:
            _ensure_import_path()
            from ipfs_accelerate_py.agent_supervisor.runtime.accepted_submodule_maintenance import (
                assess_accepted_configured_submodule,
            )
            assessment = assess_accepted_configured_submodule(board)
            maintenance_needed = assessment.get("needed") is True
            if not maintenance_needed:
                raise rejected_preflight
        except Exception:
            raise rejected_preflight
    revalidated_board, revalidated_payload = _load_board(config_path)
    if (
        revalidated_payload != payload
        or getattr(revalidated_board, "configuration_root", None)
        != getattr(board, "configuration_root", None)
    ):
        raise OperatorError("scheduler configuration changed before runtime resume")
    board = revalidated_board
    paths = _runtime_paths(board)
    _require_native_start_allowed(paths)
    _private_directory(paths["state"])
    _ensure_import_path()
    from ipfs_accelerate_py.agent_supervisor.merge.checkout_lock import (
        serialized_lock_update,
    )

    lock_path = paths["state"] / "pctdd-runtime-resume.lock"
    try:
        with serialized_lock_update(
            lock_path,
            timeout_seconds=max(30.0, monitor_seconds + 30.0),
        ):
            revalidated_board, revalidated_payload = _load_board(config_path)
            revalidated_paths = _runtime_paths(revalidated_board)
            if (
                revalidated_payload != payload
                or getattr(revalidated_board, "configuration_root", None)
                != getattr(board, "configuration_root", None)
                or revalidated_paths != paths
            ):
                raise OperatorError(
                    "scheduler configuration changed before runtime resume"
                )
            _require_native_start_allowed(revalidated_paths)
            if maintenance_needed:
                _maintain_accepted_submodule_before_resume(
                    config_path, board=revalidated_board, payload=revalidated_payload,
                    paths=revalidated_paths,
                )
            return _resume_locked(
                config_path,
                board=board,
                payload=payload,
                paths=paths,
                monitor_seconds=monitor_seconds,
            )
    except TimeoutError as exc:
        raise OperatorError("timed out serializing runtime resume") from exc
    except RuntimeError as exc:
        if isinstance(exc, OperatorError):
            raise
        raise OperatorError("runtime resume serialization is unavailable") from exc


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
    resume_parser = commands.add_parser(
        "resume",
        help=(
            "recover/adopt Quack and ensure the existing configured scheduler "
            "after accepted source evolution"
        ),
    )
    resume_parser.add_argument(
        "--monitor-seconds",
        type=float,
        default=DEFAULT_MONITOR_SECONDS,
        help="positive health-monitoring window after a runtime resume",
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
        elif arguments.command == "resume":
            result = resume(
                config_path,
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
