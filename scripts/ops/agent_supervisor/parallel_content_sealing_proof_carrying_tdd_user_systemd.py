#!/usr/bin/env python3
"""Install the opt-in user-systemd PCTDD resume ensure units.

The installed oneshot has no lifecycle authority of its own.  It invokes only
the reviewed PCTDD operator's ``resume`` command, which retains current-tree,
Quack authentication, task-population, owner-recovery, and scheduler
serialization gates.  This module never reads a Quack token and never starts a
state owner or configured-board coordinator directly.

Importing this module performs no filesystem, process, systemd, database, or
network operation.  Installation and removal are explicit CLI operations.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import hashlib
import importlib.util
import json
import os
import pwd
import re
import secrets
import shutil
import stat
import subprocess
import sys
import time
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final

ROOT: Final = Path(__file__).resolve().parents[3]
INSTALLER_SCRIPT: Final = Path(__file__).resolve()
OPERATOR_SCRIPT: Final = (
    ROOT
    / "scripts"
    / "ops"
    / "agent_supervisor"
    / "parallel_content_sealing_proof_carrying_tdd.py"
)
SCHEDULER_CONFIG: Final = (
    ROOT
    / "config"
    / "agent_supervisor_parallel_content_sealing_proof_carrying_tdd_scheduler.json"
)
SERVICE_TEMPLATE: Final = (
    ROOT
    / "config"
    / "parallel_content_sealing_proof_carrying_tdd_ensure.service.in"
)
TIMER_TEMPLATE: Final = (
    ROOT
    / "config"
    / "parallel_content_sealing_proof_carrying_tdd_ensure.timer"
)
PLAN_PATH: Final = (
    ROOT
    / "docs"
    / "architecture"
    / "PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_PLAN.md"
)

SERVICE_NAME: Final = "ipfs-accelerate-pctdd-ensure.service"
TIMER_NAME: Final = "ipfs-accelerate-pctdd-ensure.timer"
UNIT_SCHEMA: Final = "PCTDDUserSystemdEnsure@1"
RECEIPT_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/pctdd-user-systemd-ensure@1"
)
MONITOR_SECONDS: Final = 180
# Bound the complete reviewed recovery envelope: two current-tree preflights
# (up to 900s each), resume-lock serialization (monitor + 30s), owner recovery
# (120s), detached scheduler launch (up to 900s), the monitor window, and a
# bounded margin for validation and process handoff.
TIMEOUT_SECONDS: Final = 3600
LEGACY_SERVICE_REVISIONS: Final = (
    (
        300,
        "sha256:b153a19680f7c700d07ccc87bafc2bd587911a0dbd60c8cea6128eea3c9d2ee8",
    ),
)
# The prior timer had only a boot-relative bootstrap. Exact bytes are retained
# as the sole migration predecessor; arbitrary installed timers remain foreign.
LEGACY_TIMER_SHA256: Final = "75446294cc9559269850bebc5ee1f704ecb199dd2c33eeb0b8801dff0a9e69e7"
RENAME_EXCHANGE: Final = 2
MAX_UNIT_BYTES: Final = 64 * 1024
MAX_CONTROL_BYTES: Final = 8 * 1024 * 1024
SHA256_RE: Final = re.compile(r"^[0-9a-f]{40}$")
TEMPLATE_TOKEN_RE: Final = re.compile(r"@[A-Z][A-Z0-9_]*@")


class EnsureError(RuntimeError):
    """A closed, non-secret ensure failure."""

    def __init__(self, reason_code: str) -> None:
        if not re.fullmatch(r"[a-z][a-z0-9_]{2,95}", reason_code):
            reason_code = "ensure_operation_failed"
        self.reason_code = reason_code
        super().__init__(reason_code)


class UserSystemdUnavailable(EnsureError):
    """Typed external-capability terminal for user systemd or linger."""


def _load_operator() -> Any:
    spec = importlib.util.spec_from_file_location(
        "_pctdd_reviewed_operator_for_user_systemd",
        OPERATOR_SCRIPT,
    )
    if spec is None or spec.loader is None:
        raise EnsureError("reviewed_operator_unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(path))


def _exact_config(path: Path) -> Path:
    candidate = _absolute(path)
    if candidate != _absolute(SCHEDULER_CONFIG):
        raise EnsureError("noncanonical_scheduler_config")
    return candidate


def _stable_regular_bytes(
    path: Path,
    *,
    max_bytes: int,
    private: bool = False,
) -> tuple[bytes, os.stat_result]:
    target = _absolute(path)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(target, flags)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise EnsureError("owned_artifact_unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_nlink != 1
            or before.st_size < 0
            or before.st_size > max_bytes
            or (private and stat.S_IMODE(before.st_mode) != 0o600)
        ):
            raise EnsureError("owned_artifact_custody_invalid")
        payload = bytearray()
        while len(payload) <= max_bytes:
            chunk = os.read(
                descriptor,
                min(64 * 1024, max_bytes + 1 - len(payload)),
            )
            if not chunk:
                break
            payload.extend(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise EnsureError("owned_artifact_read_failed") from exc
    finally:
        os.close(descriptor)
    if len(payload) > max_bytes:
        raise EnsureError("owned_artifact_too_large")
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
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise EnsureError("owned_artifact_changed_during_read")
    try:
        observed = os.lstat(target)
    except OSError as exc:
        raise EnsureError("owned_artifact_changed_during_read") from exc
    if (
        (observed.st_dev, observed.st_ino) != (after.st_dev, after.st_ino)
        or stat.S_ISLNK(observed.st_mode)
    ):
        raise EnsureError("owned_artifact_changed_during_read")
    return bytes(payload), after


def _utf8_template(path: Path) -> str:
    payload, _evidence = _stable_regular_bytes(path, max_bytes=MAX_UNIT_BYTES)
    try:
        text = payload.decode("utf-8")
    except UnicodeError as exc:
        raise EnsureError("unit_template_not_utf8") from exc
    if "\r" in text or "\x00" in text or not text.endswith("\n"):
        raise EnsureError("unit_template_not_canonical")
    return text


def _systemd_quote(value: str) -> str:
    if not value or any(ord(character) < 0x20 for character in value):
        raise EnsureError("unsafe_systemd_argument")
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%")
    return f'"{escaped}"'


def _systemd_directive_path(value: str) -> str:
    if not value or not value.startswith("/") or any(
        ord(character) < 0x20 or ord(character) == 0x7F for character in value
    ):
        raise EnsureError("unsafe_systemd_directive_path")
    return (
        value.replace("\\", "\\x5c")
        .replace(" ", "\\x20")
        .replace("%", "%%")
    )


def _exact_repo_file(path: Path) -> Path:
    absolute = _absolute(path)
    try:
        relative = absolute.relative_to(_absolute(ROOT))
    except ValueError as exc:
        raise EnsureError("repository_artifact_outside_root") from exc
    cursor = _absolute(ROOT)
    for component in relative.parts:
        cursor /= component
        try:
            observed = os.lstat(cursor)
        except OSError as exc:
            raise EnsureError("repository_artifact_unavailable") from exc
        if stat.S_ISLNK(observed.st_mode):
            raise EnsureError("repository_artifact_symlinked")
    if not absolute.is_file():
        raise EnsureError("repository_artifact_unavailable")
    return absolute


def _python_executable() -> Path:
    candidate = Path(sys.executable)
    try:
        resolved = candidate.resolve(strict=True)
        observed = resolved.stat()
    except OSError as exc:
        raise EnsureError("python_executable_unavailable") from exc
    if (
        not stat.S_ISREG(observed.st_mode)
        or not os.access(resolved, os.X_OK)
        or observed.st_uid not in {0, os.geteuid()}
        or stat.S_IMODE(observed.st_mode) & 0o022
    ):
        raise EnsureError("python_executable_custody_invalid")
    return resolved


def _render_units() -> dict[str, bytes]:
    repository = _absolute(ROOT)
    operator = _exact_repo_file(OPERATOR_SCRIPT)
    config = _exact_repo_file(SCHEDULER_CONFIG)
    plan = _exact_repo_file(PLAN_PATH)
    python = _python_executable()
    template = _utf8_template(SERVICE_TEMPLATE)
    plan_uri = plan.as_uri().replace("%", "%%")
    replacements = {
        "@PLAN_URI@": plan_uri,
        "@REPOSITORY_DIRECTORY@": _systemd_directive_path(str(repository)),
        "@PYTHON_EXECUTABLE@": _systemd_quote(str(python)),
        "@OPERATOR_SCRIPT@": _systemd_quote(str(operator)),
        "@SCHEDULER_CONFIG@": _systemd_quote(str(config)),
        "@MONITOR_SECONDS@": str(MONITOR_SECONDS),
        "@TIMEOUT_SECONDS@": str(TIMEOUT_SECONDS),
    }
    for token, value in replacements.items():
        if template.count(token) != 1:
            raise EnsureError("unit_template_token_mismatch")
        template = template.replace(token, value)
    if TEMPLATE_TOKEN_RE.search(template):
        raise EnsureError("unit_template_token_unresolved")
    timer = _utf8_template(TIMER_TEMPLATE)

    service_lines = template.splitlines()
    exec_lines = [line for line in service_lines if line.startswith("ExecStart=")]
    # Ignore hostile PYTHON* environment and unsafe script-directory imports,
    # while retaining the reviewed user-site dependency authority where the
    # pinned DuckDB/Quack runtime is installed.  ``-I`` would also suppress
    # that authority and make every systemd ensure fail before authentication.
    expected_exec = (
        "ExecStart="
        f"{_systemd_quote(str(python))} -E -P {_systemd_quote(str(operator))} "
        f"--config {_systemd_quote(str(config))} resume "
        f"--monitor-seconds {MONITOR_SECONDS}"
    )
    forbidden_directives = (
        "ExecStartPre=",
        "ExecStartPost=",
        "ExecReload=",
        "Environment=",
        "EnvironmentFile=",
    )
    if (
        exec_lines != [expected_exec]
        or any(line.startswith(forbidden_directives) for line in service_lines)
        or " state-owner" in expected_exec
        or " launch " in expected_exec
        or "token" in expected_exec.lower()
        or "secret" in expected_exec.lower()
        or "Restart=no" not in service_lines
        or "KillMode=process" not in service_lines
        or "Type=oneshot" not in service_lines
    ):
        raise EnsureError("service_template_claim_boundary_invalid")
    timer_lines = timer.splitlines()
    required_timer_lines = {
        "OnActiveSec=3min",
        "OnUnitActiveSec=10min",
        "AccuracySec=30s",
        "RandomizedDelaySec=45s",
        "Persistent=true",
        f"Unit={SERVICE_NAME}",
        "WantedBy=timers.target",
    }
    if not required_timer_lines.issubset(set(timer_lines)):
        raise EnsureError("timer_template_policy_invalid")
    scheduled = [line for line in timer_lines if line.startswith("On")]
    if scheduled != ["OnActiveSec=3min", "OnUnitActiveSec=10min"]:
        raise EnsureError("timer_template_policy_invalid")
    return {
        SERVICE_NAME: template.encode("utf-8"),
        TIMER_NAME: timer.encode("utf-8"),
    }


def _migratable_unit_payloads(
    units: Mapping[str, bytes],
) -> dict[str, tuple[bytes, ...]]:
    """Return the closed set of previously sealed unit revisions."""

    service = units.get(SERVICE_NAME)
    if not isinstance(service, bytes):
        raise EnsureError("rendered_service_unavailable")
    current = f"TimeoutStartSec={TIMEOUT_SECONDS}\n".encode("ascii")
    if service.count(current) != 1:
        raise EnsureError("rendered_service_timeout_ambiguous")
    predecessors: list[bytes] = []
    for legacy_timeout, expected_sha256 in LEGACY_SERVICE_REVISIONS:
        predecessor = service.replace(
            current,
            f"TimeoutStartSec={legacy_timeout}\n".encode("ascii"),
        )
        observed_sha256 = "sha256:" + hashlib.sha256(predecessor).hexdigest()
        if observed_sha256 != expected_sha256:
            raise EnsureError("sealed_predecessor_derivation_mismatch")
        predecessors.append(predecessor)
    timer = units.get(TIMER_NAME)
    anchor = b"OnActiveSec=3min\n"
    if not isinstance(timer, bytes) or timer.count(anchor) != 1:
        raise EnsureError("rendered_timer_anchor_ambiguous")
    previous_timer = timer.replace(anchor, b"OnBootSec=3min\n")
    if hashlib.sha256(previous_timer).hexdigest() != LEGACY_TIMER_SHA256:
        raise EnsureError("sealed_timer_predecessor_derivation_mismatch")
    return {SERVICE_NAME: tuple(predecessors), TIMER_NAME: (previous_timer,)}


def _subprocess_environment(*, systemd: bool) -> dict[str, str]:
    allowed = {"LANG", "LC_ALL", "LC_CTYPE", "TZ"}
    # Select by public variable name so constructing the child environment never
    # iterates over (and therefore never reads) unrelated credential values.
    environment: dict[str, str] = {}
    for name in sorted(allowed):
        value = os.environ.get(name)
        if isinstance(value, str):
            environment[name] = value
    environment["PATH"] = "/usr/bin:/bin"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    if systemd:
        try:
            home = Path(pwd.getpwuid(os.getuid()).pw_dir)
        except (KeyError, OSError) as exc:
            raise UserSystemdUnavailable("user_home_unavailable") from exc
        runtime = Path("/run/user") / str(os.getuid())
        try:
            runtime_status = os.lstat(runtime)
            bus_status = os.lstat(runtime / "bus")
        except OSError as exc:
            raise UserSystemdUnavailable("user_systemd_bus_unavailable") from exc
        if (
            stat.S_ISLNK(runtime_status.st_mode)
            or not stat.S_ISDIR(runtime_status.st_mode)
            or runtime_status.st_uid != os.geteuid()
            or stat.S_IMODE(runtime_status.st_mode) & 0o077
            or stat.S_ISLNK(bus_status.st_mode)
            or not stat.S_ISSOCK(bus_status.st_mode)
            or bus_status.st_uid != os.geteuid()
        ):
            raise UserSystemdUnavailable("user_systemd_bus_custody_invalid")
        environment["HOME"] = str(_absolute(home))
        environment["XDG_RUNTIME_DIR"] = str(runtime)
        environment["DBUS_SESSION_BUS_ADDRESS"] = f"unix:path={runtime}/bus"
        xdg_config = os.environ.get("XDG_CONFIG_HOME", "")
        if xdg_config:
            config_path = Path(xdg_config)
            if not config_path.is_absolute():
                raise UserSystemdUnavailable("xdg_config_home_not_absolute")
            environment["XDG_CONFIG_HOME"] = str(_absolute(config_path))
    return environment


def _resolve_executable(name: str, *, capability: bool) -> Path:
    error_type = UserSystemdUnavailable if capability else EnsureError
    candidate = shutil.which(name, path="/usr/bin:/bin")
    if not candidate:
        raise error_type(f"{name}_unavailable")
    try:
        resolved = Path(candidate).resolve(strict=True)
        observed = resolved.stat()
    except OSError as exc:
        raise error_type(f"{name}_unavailable") from exc
    if (
        not stat.S_ISREG(observed.st_mode)
        or not os.access(resolved, os.X_OK)
        or observed.st_uid not in {0, os.geteuid()}
        or stat.S_IMODE(observed.st_mode) & 0o022
    ):
        raise error_type(f"{name}_custody_invalid")
    return resolved


def _run_process(
    argv: Sequence[str],
    *,
    systemd: bool,
    capability_probe: bool = False,
    capture_stdout: bool = False,
    timeout: float = 15.0,
    environment: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(
            tuple(argv),
            cwd=ROOT,
            env=(
                dict(environment)
                if environment is not None
                else _subprocess_environment(systemd=systemd)
            ),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE if capture_stdout else subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        if capability_probe:
            raise UserSystemdUnavailable("user_systemd_probe_failed") from exc
        raise EnsureError("external_process_outcome_unknown") from exc


def _current_source_revision() -> tuple[str, str]:
    git = _resolve_executable("git", capability=False)
    result = _run_process(
        (str(git), "rev-parse", "HEAD", "HEAD^{tree}"),
        systemd=False,
        capture_stdout=True,
    )
    if result.returncode != 0:
        raise EnsureError("source_identity_probe_failed")
    try:
        values = result.stdout.decode("ascii").splitlines()
    except UnicodeError as exc:
        raise EnsureError("source_identity_probe_failed") from exc
    if len(values) != 2 or not all(SHA256_RE.fullmatch(value) for value in values):
        raise EnsureError("source_identity_probe_failed")
    return values[0], values[1]


def _tracked_control_roots(source_head: str) -> dict[str, str]:
    git = _resolve_executable("git", capability=False)
    controls = (
        INSTALLER_SCRIPT,
        OPERATOR_SCRIPT,
        SCHEDULER_CONFIG,
        SERVICE_TEMPLATE,
        TIMER_TEMPLATE,
        PLAN_PATH,
    )
    roots: dict[str, str] = {}
    for control in controls:
        path = _exact_repo_file(control)
        try:
            relative = path.relative_to(_absolute(ROOT)).as_posix()
        except ValueError as exc:  # pragma: no cover - guarded above
            raise EnsureError("repository_artifact_outside_root") from exc
        working, _evidence = _stable_regular_bytes(
            path,
            max_bytes=MAX_CONTROL_BYTES,
        )
        result = _run_process(
            (str(git), "show", f"{source_head}:{relative}"),
            systemd=False,
            capture_stdout=True,
        )
        if (
            result.returncode != 0
            or len(result.stdout) > MAX_CONTROL_BYTES
            or result.stdout != working
        ):
            raise EnsureError("ensure_control_not_exactly_tracked")
        roots[relative] = "sha256:" + hashlib.sha256(working).hexdigest()
    return dict(sorted(roots.items()))


def _validate_current_controls(config_path: Path) -> dict[str, Any]:
    config = _exact_config(config_path)
    operator = _load_operator()
    before_head, before_tree = _current_source_revision()
    board, payload = operator._load_board(config)
    report = operator._configured_board_preflight(config)
    revalidated_board, revalidated_payload = operator._load_board(config)
    after_head, after_tree = _current_source_revision()
    configuration_root = getattr(board, "configuration_root", None)
    revalidated_root = getattr(revalidated_board, "configuration_root", None)
    report_root = report.get("repo_root") if isinstance(report, Mapping) else None
    report_config = report.get("config_path") if isinstance(report, Mapping) else None
    if (
        not isinstance(report, Mapping)
        or report.get("valid") is not True
        or not isinstance(report_root, str)
        or not report_root
        or _absolute(Path(report_root)) != _absolute(ROOT)
        or not isinstance(report_config, str)
        or not report_config
        or _absolute(Path(report_config)) != config
        or str(report.get("board_namespace") or "")
        != "parallel-content-sealing-proof-carrying-tdd-v1"
        or not isinstance(configuration_root, str)
        or not configuration_root
        or revalidated_root != configuration_root
        or revalidated_payload != payload
        or (before_head, before_tree) != (after_head, after_tree)
    ):
        raise EnsureError("current_control_preflight_changed_or_rejected")
    return {
        "source_head": after_head,
        "source_tree": after_tree,
        "configuration_root": configuration_root,
        "control_roots": _tracked_control_roots(after_head),
    }


def _require_stable_validation(
    baseline: Mapping[str, Any],
    config_path: Path,
) -> dict[str, Any]:
    current = _validate_current_controls(config_path)
    if dict(current) != dict(baseline):
        raise EnsureError("current_controls_changed_before_external_write")
    return current


def _require_user_systemd() -> dict[str, Any]:
    systemctl = _resolve_executable("systemctl", capability=True)
    loginctl = _resolve_executable("loginctl", capability=True)
    environment = _subprocess_environment(systemd=True)
    manager = _run_process(
        (str(systemctl), "--user", "--no-pager", "is-system-running"),
        systemd=True,
        capability_probe=True,
        capture_stdout=True,
        environment=environment,
    )
    manager_state = manager.stdout.decode("ascii", errors="ignore").strip()
    if manager.returncode not in {0, 1} or manager_state not in {"running", "degraded"}:
        raise UserSystemdUnavailable("user_systemd_manager_unavailable")
    linger = _run_process(
        (
            str(loginctl),
            "show-user",
            str(os.getuid()),
            "--property=Linger",
            "--value",
        ),
        systemd=True,
        capability_probe=True,
        capture_stdout=True,
        environment=environment,
    )
    linger_state = linger.stdout.decode("ascii", errors="ignore").strip().lower()
    if linger.returncode != 0:
        raise UserSystemdUnavailable("linger_capability_unavailable")
    if linger_state != "yes":
        raise UserSystemdUnavailable("linger_not_enabled")
    return {
        "systemctl": str(systemctl),
        "loginctl": str(loginctl),
        "manager_state": manager_state,
        "linger_enabled": True,
        "_environment": environment,
    }


def _default_unit_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg:
        base = Path(xdg)
        if not base.is_absolute():
            raise EnsureError("xdg_config_home_not_absolute")
    else:
        try:
            base = Path(pwd.getpwuid(os.getuid()).pw_dir) / ".config"
        except (KeyError, OSError) as exc:
            raise EnsureError("user_home_unavailable") from exc
    return _absolute(base / "systemd" / "user")


def _normalized_unit_dir(value: Path | None) -> Path:
    directory = _absolute(value if value is not None else _default_unit_dir())
    if directory == Path(directory.anchor):
        raise EnsureError("unsafe_unit_directory")
    try:
        directory.relative_to(_absolute(ROOT))
    except ValueError:
        pass
    else:
        raise EnsureError("unit_directory_must_be_external")
    return directory


def _require_systemctl_unit_dir(directory: Path) -> None:
    if directory != _normalized_unit_dir(_default_unit_dir()):
        raise EnsureError("systemctl_actions_require_default_unit_directory")


def _validate_directory_component(path: Path, *, final: bool) -> os.stat_result:
    try:
        observed = os.lstat(path)
    except OSError as exc:
        raise EnsureError("unit_directory_custody_invalid") from exc
    if stat.S_ISLNK(observed.st_mode) or not stat.S_ISDIR(observed.st_mode):
        raise EnsureError("unit_directory_custody_invalid")
    if final and (
        observed.st_uid != os.geteuid() or stat.S_IMODE(observed.st_mode) & 0o022
    ):
        raise EnsureError("unit_directory_custody_invalid")
    return observed


def _ensure_unit_dir(directory: Path) -> Path:
    target = _normalized_unit_dir(directory)
    missing: list[Path] = []
    cursor = target
    while True:
        try:
            _validate_directory_component(cursor, final=cursor == target)
            break
        except EnsureError:
            try:
                os.lstat(cursor)
            except FileNotFoundError:
                missing.append(cursor)
                parent = cursor.parent
                if parent == cursor:
                    raise EnsureError("unit_directory_custody_invalid") from None
                cursor = parent
                continue
            raise
    for component in reversed(missing):
        try:
            os.mkdir(component, 0o700)
        except FileExistsError:
            pass
        except OSError as exc:
            raise EnsureError("unit_directory_create_failed") from exc
        observed = _validate_directory_component(component, final=True)
        if observed.st_uid != os.geteuid():
            raise EnsureError("unit_directory_custody_invalid")
    _validate_directory_component(target, final=True)
    return target


def _existing_unit_dir(directory: Path) -> Path | None:
    target = _normalized_unit_dir(directory)
    try:
        os.lstat(target)
    except FileNotFoundError:
        return None
    _validate_directory_component(target, final=True)
    return target


@contextmanager
def _unit_directory_lock(directory: Path) -> Iterator[int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(directory, flags)
    except OSError as exc:
        raise EnsureError("unit_directory_lock_unavailable") from exc
    try:
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISDIR(observed.st_mode)
            or observed.st_uid != os.geteuid()
            or stat.S_IMODE(observed.st_mode) & 0o022
        ):
            raise EnsureError("unit_directory_custody_invalid")
        deadline = time.monotonic() + 10.0
        while True:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise EnsureError("unit_directory_lock_contended") from None
                time.sleep(0.05)
        yield descriptor
    except OSError as exc:
        raise EnsureError("unit_directory_lock_unavailable") from exc
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def _inspect_unit(
    path: Path,
    expected: bytes,
    *,
    migratable: Sequence[bytes] = (),
) -> str:
    try:
        payload, _evidence = _stable_regular_bytes(
            path,
            max_bytes=MAX_UNIT_BYTES,
            private=True,
        )
    except FileNotFoundError:
        return "absent"
    if payload != expected:
        if payload in migratable:
            return "migratable"
        raise EnsureError("unrecognized_existing_unit_content")
    return "exact"


def _fsync_directory(descriptor: int) -> None:
    try:
        os.fsync(descriptor)
    except OSError as exc:
        raise EnsureError("unit_directory_sync_failed") from exc


def _unit_name(value: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or "/" in value
        or "\x00" in value
        or (os.altsep is not None and os.altsep in value)
    ):
        raise EnsureError("unsafe_unit_name")
    return value


def _require_unit_directory_binding(directory: Path, directory_fd: int) -> None:
    try:
        path_stat = os.lstat(directory)
        descriptor_stat = os.fstat(directory_fd)
    except OSError as exc:
        raise EnsureError("unit_directory_changed_during_install") from exc
    if (
        stat.S_ISLNK(path_stat.st_mode)
        or not stat.S_ISDIR(path_stat.st_mode)
        or not stat.S_ISDIR(descriptor_stat.st_mode)
        or path_stat.st_uid != os.geteuid()
        or descriptor_stat.st_uid != os.geteuid()
        or stat.S_IMODE(path_stat.st_mode) & 0o022
        or stat.S_IMODE(descriptor_stat.st_mode) & 0o022
        or (path_stat.st_dev, path_stat.st_ino)
        != (descriptor_stat.st_dev, descriptor_stat.st_ino)
    ):
        raise EnsureError("unit_directory_changed_during_install")


def _stable_private_unit_bytes_at(
    directory_fd: int,
    name: str,
) -> tuple[bytes, os.stat_result]:
    unit_name = _unit_name(name)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(unit_name, flags, dir_fd=directory_fd)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise EnsureError("owned_artifact_unavailable") from exc
    try:
        before = os.fstat(descriptor)
        if (
            not stat.S_ISREG(before.st_mode)
            or before.st_uid != os.geteuid()
            or before.st_nlink != 1
            or before.st_size < 0
            or before.st_size > MAX_UNIT_BYTES
            or stat.S_IMODE(before.st_mode) != 0o600
        ):
            raise EnsureError("owned_artifact_custody_invalid")
        payload = bytearray()
        while len(payload) <= MAX_UNIT_BYTES:
            chunk = os.read(
                descriptor,
                min(64 * 1024, MAX_UNIT_BYTES + 1 - len(payload)),
            )
            if not chunk:
                break
            payload.extend(chunk)
        after = os.fstat(descriptor)
    except OSError as exc:
        raise EnsureError("owned_artifact_read_failed") from exc
    finally:
        os.close(descriptor)
    if len(payload) > MAX_UNIT_BYTES:
        raise EnsureError("owned_artifact_too_large")
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
    if any(getattr(before, field) != getattr(after, field) for field in stable_fields):
        raise EnsureError("owned_artifact_changed_during_read")
    try:
        observed = os.stat(
            unit_name,
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise EnsureError("owned_artifact_changed_during_read") from exc
    if (
        stat.S_ISLNK(observed.st_mode)
        or (observed.st_dev, observed.st_ino) != (after.st_dev, after.st_ino)
    ):
        raise EnsureError("owned_artifact_changed_during_read")
    return bytes(payload), after


def _inspect_unit_at(
    directory_fd: int,
    name: str,
    expected: bytes,
    *,
    migratable: Sequence[bytes] = (),
) -> str:
    try:
        payload, _evidence = _stable_private_unit_bytes_at(directory_fd, name)
    except FileNotFoundError:
        return "absent"
    if payload == expected:
        return "exact"
    if payload in migratable:
        return "migratable"
    raise EnsureError("unrecognized_existing_unit_content")


def _temporary_unit_name(name: str, purpose: str) -> str:
    return _unit_name(
        f".{_unit_name(name)}.{purpose}.{os.getpid()}.{secrets.token_hex(16)}"
    )


def _unlink_owned_unit_at(
    directory_fd: int,
    name: str,
    expected_stat: os.stat_result,
) -> None:
    try:
        observed = os.stat(
            _unit_name(name),
            dir_fd=directory_fd,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return
    except OSError as exc:
        raise EnsureError("owned_temporary_cleanup_failed") from exc
    if (
        stat.S_ISLNK(observed.st_mode)
        or (observed.st_dev, observed.st_ino)
        != (expected_stat.st_dev, expected_stat.st_ino)
    ):
        raise EnsureError("owned_temporary_changed_before_cleanup")
    try:
        os.unlink(_unit_name(name), dir_fd=directory_fd)
    except OSError as exc:
        raise EnsureError("owned_temporary_cleanup_failed") from exc


def _create_private_temporary_at(
    directory_fd: int,
    name: str,
    payload: bytes,
) -> os.stat_result:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    flags |= getattr(os, "O_NOFOLLOW", 0)
    descriptor = -1
    created_stat: os.stat_result | None = None
    try:
        descriptor = os.open(
            _unit_name(name),
            flags,
            0o600,
            dir_fd=directory_fd,
        )
        created_stat = os.fstat(descriptor)
        written = 0
        while written < len(payload):
            count = os.write(descriptor, payload[written:])
            if count <= 0:
                raise OSError("short unit write")
            written += count
        os.fsync(descriptor)
        observed = os.fstat(descriptor)
        if (
            not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != os.geteuid()
            or observed.st_nlink != 1
            or stat.S_IMODE(observed.st_mode) != 0o600
            or observed.st_size != len(payload)
        ):
            raise EnsureError("atomic_unit_custody_invalid")
        return observed
    except (EnsureError, OSError) as exc:
        if created_stat is not None:
            _unlink_owned_unit_at(directory_fd, name, created_stat)
        if isinstance(exc, EnsureError):
            raise
        raise EnsureError("atomic_unit_write_failed") from exc
    finally:
        if descriptor >= 0:
            os.close(descriptor)


def _atomic_private_create(name: str, payload: bytes, directory_fd: int) -> None:
    temporary = _temporary_unit_name(name, "tmp")
    temporary_stat = _create_private_temporary_at(
        directory_fd,
        temporary,
        payload,
    )
    try:
        os.link(
            temporary,
            _unit_name(name),
            src_dir_fd=directory_fd,
            dst_dir_fd=directory_fd,
            follow_symlinks=False,
        )
        _unlink_owned_unit_at(directory_fd, temporary, temporary_stat)
        _fsync_directory(directory_fd)
    except FileExistsError:
        raise
    except (EnsureError, OSError) as exc:
        if isinstance(exc, EnsureError):
            raise
        raise EnsureError("atomic_unit_write_failed") from exc
    finally:
        _unlink_owned_unit_at(directory_fd, temporary, temporary_stat)


def _rename_exchange_at(directory_fd: int, left: str, right: str) -> None:
    try:
        renameat2 = ctypes.CDLL(None, use_errno=True).renameat2
    except (AttributeError, OSError) as exc:
        raise EnsureError("atomic_unit_exchange_unavailable") from exc
    renameat2.argtypes = (
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_int,
        ctypes.c_char_p,
        ctypes.c_uint,
    )
    renameat2.restype = ctypes.c_int
    result = renameat2(
        directory_fd,
        os.fsencode(_unit_name(left)),
        directory_fd,
        os.fsencode(_unit_name(right)),
        RENAME_EXCHANGE,
    )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.ENOSYS, errno.EINVAL, errno.EOPNOTSUPP}:
        raise EnsureError("atomic_unit_exchange_unavailable")
    raise EnsureError("atomic_unit_exchange_failed")


def _atomic_private_replace(
    name: str,
    payload: bytes,
    previous_payloads: Sequence[bytes],
    directory_fd: int,
) -> None:
    """Replace one exact sealed predecessor without an unowned overwrite."""

    previous, previous_stat = _stable_private_unit_bytes_at(
        directory_fd,
        name,
    )
    if previous not in previous_payloads:
        raise EnsureError("unrecognized_existing_unit_content")
    temporary = _temporary_unit_name(name, "upgrade")
    temporary_stat = _create_private_temporary_at(
        directory_fd,
        temporary,
        payload,
    )
    exchanged = False
    try:
        revalidated, revalidated_stat = _stable_private_unit_bytes_at(
            directory_fd,
            name,
        )
        if (
            revalidated != previous
            or (revalidated_stat.st_dev, revalidated_stat.st_ino)
            != (previous_stat.st_dev, previous_stat.st_ino)
        ):
            raise EnsureError("owned_unit_changed_before_upgrade")
        _rename_exchange_at(directory_fd, temporary, name)
        exchanged = True
        try:
            displaced, displaced_stat = _stable_private_unit_bytes_at(
                directory_fd,
                temporary,
            )
            if (
                displaced != previous
                or (displaced_stat.st_dev, displaced_stat.st_ino)
                != (previous_stat.st_dev, previous_stat.st_ino)
            ):
                raise EnsureError("owned_unit_changed_before_upgrade")
        except EnsureError as displaced_error:
            try:
                _rename_exchange_at(directory_fd, temporary, name)
            except EnsureError as rollback_error:
                raise EnsureError("atomic_unit_upgrade_rollback_failed") from (
                    rollback_error
                )
            exchanged = False
            _unlink_owned_unit_at(directory_fd, temporary, temporary_stat)
            raise EnsureError("owned_unit_changed_before_upgrade") from (
                displaced_error
            )
        _unlink_owned_unit_at(directory_fd, temporary, displaced_stat)
        exchanged = False
        _fsync_directory(directory_fd)
    except (EnsureError, OSError) as exc:
        if isinstance(exc, EnsureError):
            raise
        raise EnsureError("atomic_unit_upgrade_failed") from exc
    finally:
        if not exchanged:
            try:
                _unlink_owned_unit_at(
                    directory_fd,
                    temporary,
                    temporary_stat,
                )
            except EnsureError:
                # After a successful exchange, the predecessor inode—not the
                # created temporary inode—occupies this name and is removed in
                # the success path above.
                if _inspect_unit_at(directory_fd, name, payload) != "exact":
                    raise


def _install_exact_units(
    directory: Path,
    units: Mapping[str, bytes],
) -> tuple[list[str], list[str], list[str]]:
    created: list[str] = []
    existing: list[str] = []
    upgraded: list[str] = []
    migratable = _migratable_unit_payloads(units)
    with _unit_directory_lock(directory) as directory_fd:
        _require_unit_directory_binding(directory, directory_fd)
        states = {
            name: _inspect_unit_at(
                directory_fd,
                name,
                payload,
                migratable=migratable.get(name, ()),
            )
            for name, payload in sorted(units.items())
        }
        for name, payload in sorted(units.items()):
            if states[name] == "exact":
                existing.append(name)
                continue
            if states[name] == "migratable":
                _atomic_private_replace(
                    name,
                    payload,
                    migratable[name],
                    directory_fd,
                )
                if _inspect_unit_at(directory_fd, name, payload) != "exact":
                    raise EnsureError("published_unit_verification_failed")
                upgraded.append(name)
                continue
            try:
                _atomic_private_create(name, payload, directory_fd)
            except FileExistsError:
                if _inspect_unit_at(directory_fd, name, payload) != "exact":
                    raise EnsureError("concurrent_unrecognized_unit_publish") from None
                existing.append(name)
            else:
                if _inspect_unit_at(directory_fd, name, payload) != "exact":
                    raise EnsureError("published_unit_verification_failed")
                created.append(name)
        _require_unit_directory_binding(directory, directory_fd)
    return created, existing, upgraded


def _systemctl_action(capability: Mapping[str, Any], *arguments: str) -> None:
    path = str(capability.get("systemctl") or "")
    environment = capability.get("_environment")
    if not path or not isinstance(environment, Mapping):
        raise EnsureError("systemctl_action_unavailable")
    result = _run_process(
        (path, "--user", "--no-pager", *arguments),
        systemd=True,
        capture_stdout=False,
        timeout=60.0,
        environment={str(key): str(value) for key, value in environment.items()},
    )
    if result.returncode != 0:
        raise EnsureError("systemctl_action_failed")


def _remove_exact_unit(
    path: Path,
    expected: bytes,
    directory_fd: int,
) -> bool:
    if _inspect_unit(path, expected) == "absent":
        return False
    before = os.lstat(path)
    if _inspect_unit(path, expected) != "exact":  # pragma: no cover - closed above
        raise EnsureError("unrecognized_existing_unit_content")
    current = os.lstat(path)
    if (before.st_dev, before.st_ino) != (current.st_dev, current.st_ino):
        raise EnsureError("owned_unit_changed_before_removal")
    try:
        path.unlink()
    except OSError as exc:
        raise EnsureError("owned_unit_removal_failed") from exc
    _fsync_directory(directory_fd)
    return True


def _unit_hashes(units: Mapping[str, bytes]) -> dict[str, str]:
    return {
        name: "sha256:" + hashlib.sha256(payload).hexdigest()
        for name, payload in sorted(units.items())
    }


def validate_environment(
    config_path: Path,
    *,
    unit_dir: Path | None,
) -> dict[str, Any]:
    directory = _normalized_unit_dir(unit_dir)
    validation = _validate_current_controls(config_path)
    capability = _require_user_systemd()
    units = _render_units()
    _require_stable_validation(validation, config_path)
    return {
        "schema": RECEIPT_SCHEMA,
        "command": "validate",
        "valid": True,
        "source_binding": validation,
        "user_systemd": {
            "manager_state": capability["manager_state"],
            "linger_enabled": capability["linger_enabled"],
        },
        "unit_dir": str(directory),
        "unit_roots": _unit_hashes(units),
        "external_writes": False,
        "credential_material_accessed": False,
    }


def install(
    config_path: Path,
    *,
    unit_dir: Path | None,
    daemon_reload: bool,
    enable: bool,
) -> dict[str, Any]:
    if enable and not daemon_reload:
        raise EnsureError("enable_requires_explicit_daemon_reload")
    directory = _normalized_unit_dir(unit_dir)
    if daemon_reload or enable:
        _require_systemctl_unit_dir(directory)
    validation = _validate_current_controls(config_path)
    capability = _require_user_systemd()
    units = _render_units()
    _require_stable_validation(validation, config_path)
    directory = _ensure_unit_dir(directory)
    created, existing, upgraded = _install_exact_units(directory, units)
    if daemon_reload:
        _systemctl_action(capability, "daemon-reload")
    if enable:
        _systemctl_action(capability, "enable", "--now", TIMER_NAME)
        # enable --now leaves an already-active elapsed timer untouched. Restart
        # only the timer to establish its OnActiveSec bootstrap; the service is
        # still invoked later through its unchanged native resume admission.
        _require_stable_validation(validation, config_path)
        _systemctl_action(capability, "restart", TIMER_NAME)
    return {
        "schema": RECEIPT_SCHEMA,
        "command": "install",
        "valid": True,
        "source_binding": validation,
        "user_systemd": {
            "manager_state": capability["manager_state"],
            "linger_enabled": capability["linger_enabled"],
        },
        "unit_dir": str(directory),
        "unit_roots": _unit_hashes(units),
        "created": created,
        "already_exact": existing,
        "upgraded_from_sealed_predecessor": upgraded,
        "daemon_reload": bool(daemon_reload),
        "timer_enabled_and_started": bool(enable),
        "timer_activation_anchor_rearmed": bool(enable),
        "oneshot_command": "reviewed_operator_resume_only",
        "direct_owner_or_master_launch": False,
        "credential_material_accessed": False,
    }


def uninstall(
    config_path: Path,
    *,
    unit_dir: Path | None,
    daemon_reload: bool,
    disable: bool,
) -> dict[str, Any]:
    if disable and not daemon_reload:
        raise EnsureError("disable_requires_explicit_daemon_reload")
    directory = _normalized_unit_dir(unit_dir)
    if daemon_reload or disable:
        _require_systemctl_unit_dir(directory)
    validation = _validate_current_controls(config_path)
    capability = _require_user_systemd()
    units = _render_units()
    _require_stable_validation(validation, config_path)
    directory = _existing_unit_dir(directory)
    if directory is None:
        return {
            "schema": RECEIPT_SCHEMA,
            "command": "uninstall",
            "valid": True,
            "source_binding": validation,
            "removed": [],
            "already_absent": sorted(units),
            "daemon_reload": False,
            "timer_disabled_and_stopped": False,
            "credential_material_accessed": False,
        }
    removed: list[str] = []
    daemon_reloaded = False
    with _unit_directory_lock(directory) as directory_fd:
        states = {
            name: _inspect_unit(directory / name, payload)
            for name, payload in sorted(units.items())
        }
        if disable and any(state != "exact" for state in states.values()):
            raise EnsureError("disable_requires_complete_exact_unit_pair")
        if disable:
            _systemctl_action(capability, "disable", "--now", TIMER_NAME)
        for name, payload in sorted(units.items()):
            if _remove_exact_unit(directory / name, payload, directory_fd):
                removed.append(name)
        if daemon_reload and any(state == "exact" for state in states.values()):
            _systemctl_action(capability, "daemon-reload")
            daemon_reloaded = True
    return {
        "schema": RECEIPT_SCHEMA,
        "command": "uninstall",
        "valid": True,
        "source_binding": validation,
        "removed": removed,
        "already_absent": sorted(set(units) - set(removed)),
        "daemon_reload": daemon_reloaded,
        "timer_disabled_and_stopped": bool(disable),
        "credential_material_accessed": False,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SCHEDULER_CONFIG)
    parser.add_argument(
        "--unit-dir",
        type=Path,
        help="explicit user unit directory; defaults to XDG_CONFIG_HOME/systemd/user",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("validate", help="probe controls, user systemd, linger, and templates")
    install_parser = commands.add_parser("install", help="install exact inert unit files")
    install_parser.add_argument("--daemon-reload", action="store_true")
    install_parser.add_argument("--enable", action="store_true")
    uninstall_parser = commands.add_parser(
        "uninstall",
        help="remove only exact owned unit files",
    )
    uninstall_parser.add_argument("--daemon-reload", action="store_true")
    uninstall_parser.add_argument("--disable", action="store_true")
    return parser


def _emit(payload: Mapping[str, Any], *, stream: Any = sys.stdout) -> None:
    print(json.dumps(dict(payload), indent=2, sort_keys=True), file=stream)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    try:
        if arguments.command == "validate":
            result = validate_environment(
                arguments.config,
                unit_dir=arguments.unit_dir,
            )
        elif arguments.command == "install":
            result = install(
                arguments.config,
                unit_dir=arguments.unit_dir,
                daemon_reload=bool(arguments.daemon_reload),
                enable=bool(arguments.enable),
            )
        elif arguments.command == "uninstall":
            result = uninstall(
                arguments.config,
                unit_dir=arguments.unit_dir,
                daemon_reload=bool(arguments.daemon_reload),
                disable=bool(arguments.disable),
            )
        else:  # pragma: no cover - argparse closes the vocabulary
            raise EnsureError("unknown_command")
    except UserSystemdUnavailable as exc:
        _emit(
            {
                "schema": RECEIPT_SCHEMA,
                "command": str(arguments.command),
                "valid": False,
                "terminal": "typed_external_capability_unavailable",
                "reason_code": exc.reason_code,
                "external_writes": False,
                "credential_material_accessed": False,
            },
            stream=sys.stderr,
        )
        return 3
    except EnsureError as exc:
        _emit(
            {
                "schema": RECEIPT_SCHEMA,
                "command": str(arguments.command),
                "valid": False,
                "terminal": "fail_closed",
                "reason_code": exc.reason_code,
                "credential_material_accessed": False,
            },
            stream=sys.stderr,
        )
        return 2
    _emit(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
