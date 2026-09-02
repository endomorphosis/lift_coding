#!/usr/bin/env python3
"""Execute one sealed PCTDD validation profile without a shell.

The task board contains only the task-bound dispatcher invocation.  Concrete
argv vectors live in the operator-protected profile document.  This module
does not interpret prose, aliases, pipes, redirects, expansion, or shell
operators; every child is launched through an argv-only ``subprocess.Popen``
with ``shell=False`` and a new process session for bounded tree termination.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Final, Iterator, Mapping, Sequence


ROOT: Final[Path] = Path(__file__).resolve().parents[1]
PROFILE_PATH: Final[Path] = (
    ROOT / "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json"
)
DEPENDENCY_SEAL_PATH: Final[Path] = (
    ROOT / "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json"
)
PCTDD_DUCKDB_EXTENSION_DIRECTORY_ENV: Final[str] = (
    "IPFS_ACCELERATE_PCTDD_DUCKDB_EXTENSION_DIRECTORY"
)
PLAN_REVISION: Final[str] = "PCTDD-PLAN-V1.1"
TASK_IDS: Final[tuple[str, ...]] = tuple(f"PCTDD-{n:03d}" for n in range(54))
TASK_RE: Final[re.Pattern[str]] = re.compile(r"^PCTDD-(?:0[0-4][0-9]|05[0-3])$")
FORBIDDEN_TOKENS: Final[frozenset[str]] = frozenset(
    {"&&", "||", ";", "|", "&", ">", ">>", "<", "<<"}
)
PYTEST_PHASE_FD_ENV: Final[str] = "PCTDD_PYTEST_PHASE_FD"
PYTEST_PHASE_NONCE_ENV: Final[str] = "PCTDD_PYTEST_PHASE_NONCE"
PYTEST_PHASE_EVENT_SCHEMA: Final[str] = "pctdd/pytest-phase-event@1"
PYTEST_PHASE_OUTCOME_SCHEMA: Final[str] = "pctdd/pytest-phase-outcome@2"
PYTEST_PHASE_STREAM_MAX_BYTES: Final[int] = 8 * 1024 * 1024
PYTEST_PHASE_FRAME_MAX_BYTES: Final[int] = 8 * 1024
VALIDATION_SUBREAPER_ROOT: Final[Path] = ROOT / "external/ipfs_accelerate"
VALIDATION_SUBREAPER_PATH: Final[Path] = (
    VALIDATION_SUBREAPER_ROOT
    / "ipfs_accelerate_py/agent_supervisor/todo_daemon/native_cli_subreaper.py"
)
VALIDATION_SUBREAPER_SHA256: Final[str] = (
    "sha256:bf6fb3338dde2c6a9973b2db4a0e432b55825fcd24a1416159b9cc9f6090e717"
)
# ``external/ipfs_accelerate/scripts`` is a regular Python package and shadows
# the repository-root ``scripts`` namespace once its package root is admitted.
# Admit this file's directory directly and import the evidence plugin by its
# exact module stem.  This avoids relying on namespace-package precedence in a
# sealed validation child.
PYTEST_PLUGIN_NAME: Final[str] = "run_parallel_content_sealing_proof_carrying_tdd_validation"
PYTEST_PREFIX: Final[tuple[str, ...]] = ("python", "-m", "pytest", "-q")
PYTEST_SUFFIX: Final[tuple[str, ...]] = ("--tb=short",)
OPERATOR_VALIDATORS: Final[tuple[tuple[str, ...], ...]] = (
    (
        "python",
        "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
        "--check-all",
    ),
    (
        "python",
        "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
        "--check-all",
    ),
)
DISALLOWED_REQUIRED_OUTCOMES: Final[tuple[str, ...]] = (
    "failed", "skipped", "xfail", "xpass", "error", "rerun",
)
PCTDD_002_EXCLUDED_NODE_IDS: Final[frozenset[str]] = frozenset(
    {
        "external/ipfs_accelerate/test/api/test_proof_reuse_locator_first_collection.py::test_plugin_collection_attaches_seed_in_read_mode",
        "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_direct_node_pickup_with_entry_point_autoload_modes[root-fallback]",
        "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_verified_hit_skips_before_fixtures_without_ipfs_or_daemon_touch",
    }
)
W1_BASELINE_COMMANDS: Final[dict[str, tuple[tuple[str, tuple[str, ...]], ...]]] = {
    "PCTDD-001": (
        (
            "protected_baseline_regression",
            (
                "external/ipfs_datasets/tests/unit/utils/test_cid_utils.py",
                "external/ipfs_datasets/tests/unit/logic/software_contracts/test_content_identity.py",
                "external/ipfs_datasets/tests/unit/logic/ir_core/test_identity.py",
                "external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py",
                "external/ipfs_accelerate/test/api/test_agent_supervisor_multiformats_identity.py",
                "external/ipfs_kit/tests/test_proof_certificate_store.py",
                "external/ipfs_kit/tests/test_semantic_state_root_cas.py",
            ),
        ),
    ),
    "PCTDD-002": (
        (
            "protected_baseline_regression",
            (
                "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_item_identity.py",
                "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py",
                "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_lookup.py",
                "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py",
                "external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py",
                "external/ipfs_accelerate/test/api/test_proof_reuse_runtime_composition.py",
                "external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py",
                "external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py",
                "external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity.py",
                "external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py",
            ),
        ),
        (
            "isolated_predecessor_regression",
            (
                "external/ipfs_accelerate/test/api/test_proof_reuse_locator_first_collection.py",
            ),
        ),
        (
            "explicit_green_predecessor_nodes",
            (
                "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_pyproject_declares_shared_pytest_entry_point",
                "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_direct_node_pickup_with_entry_point_autoload_modes[entry-point]",
                "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_missing_shared_plugin_executes_normally",
                "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_missing_store_and_multiformats_execute_normally",
                "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_explicit_off_mode_executes_normally",
                "external/ipfs_kit/tests/test_proof_reuse_bootstrap.py::test_coverage_execution_remains_available",
            ),
        ),
    ),
    "PCTDD-003": (
        (
            "protected_baseline_regression",
            (
                "external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py",
                "external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py",
                "external/ipfs_datasets/tests/unit_tests/logic/zkp/test_zkp_module.py",
                "external/ipfs_accelerate/test/api/test_proof_reuse_runner_pass_attestation.py",
                "external/ipfs_accelerate/test/api/incremental_sealing/test_trust.py",
                "external/ipfs_accelerate/test/api/incremental_sealing/test_backends.py",
                "external/ipfs_accelerate/test/api/incremental_sealing/test_provers.py",
            ),
        ),
    ),
    "PCTDD-004": (
        (
            "protected_baseline_regression",
            (
                "external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py",
                "external/ipfs_accelerate/test/api/incremental_sealing/test_trust.py",
            ),
        ),
    ),
}


def _phase_genesis_digest(nonce: str) -> str:
    return "sha256:" + hashlib.sha256(
        ("pctdd/pytest-phase-stream@1\0" + nonce).encode("utf-8")
    ).hexdigest()


class _AppendOnlyPytestPhasePlugin:
    """Emit immutable primitive phase observations to the parent dispatcher.

    The plugin never owns the final receipt, target normalization, population
    admission, or persistent report path.  Its pipe is append-only from the
    child's perspective: later test code cannot rewrite frames already
    observed by the parent.  This remains trusted-runner observation evidence,
    not a direct-execution proof against arbitrary hostile CPython code.
    """

    __slots__ = ("_digest", "_fd", "_nonce", "_sequence")

    def __init__(self, *, fd: int, nonce: str) -> None:
        self._fd = int(fd)
        self._nonce = nonce
        self._sequence = 0
        self._digest = _phase_genesis_digest(nonce)

    def _emit(self, kind: str, payload: Mapping[str, Any]) -> None:
        frame = {
            "schema": PYTEST_PHASE_EVENT_SCHEMA,
            "session_nonce": self._nonce,
            "sequence": self._sequence,
            "previous_digest": self._digest,
            "kind": kind,
            **dict(payload),
        }
        encoded = (
            json.dumps(frame, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
        if len(encoded) > PYTEST_PHASE_FRAME_MAX_BYTES:
            raise RuntimeError("pytest phase frame exceeds the sealed bound")
        view = memoryview(encoded)
        while view:
            written = os.write(self._fd, view)
            if written <= 0:
                raise RuntimeError("pytest phase pipe write made no progress")
            view = view[written:]
        self._digest = "sha256:" + hashlib.sha256(encoded[:-1]).hexdigest()
        self._sequence += 1

    def emit_configure(self, rootpath: str) -> None:
        self._emit("configure", {"rootpath": rootpath})

    def pytest_runtest_logreport(self, report: Any) -> None:
        wasxfail = bool(getattr(report, "wasxfail", False))
        outcome = str(getattr(report, "outcome", "unknown"))
        when = str(getattr(report, "when", "unknown"))
        if outcome == "rerun":
            disposition = "rerun"
        elif wasxfail and outcome == "skipped":
            disposition = "xfail"
        elif wasxfail:
            disposition = "xpass"
        elif outcome == "skipped":
            disposition = "skipped"
        elif outcome == "failed" and when in {"setup", "teardown"}:
            disposition = "error"
        elif outcome == "failed":
            disposition = "failed"
        elif outcome == "passed":
            disposition = "passed"
        else:
            disposition = outcome
        self._emit(
            "phase",
            {
                "node_id": str(getattr(report, "nodeid", ""))[:4096],
                "phase": when,
                "disposition": disposition,
            },
        )

    def pytest_sessionfinish(self, session: Any, exitstatus: Any) -> None:
        try:
            self._emit("finish", {"exitstatus": int(exitstatus)})
        finally:
            os.close(self._fd)


class ProfileError(ValueError):
    """Raised when an operator profile is unresolved or unsafe."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ProfileError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _confined_path(value: str, *, field: str) -> Path:
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise ProfileError(f"{field} must be a confined repository-relative path")
    resolved = (ROOT / raw).resolve(strict=False)
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ProfileError(f"{field} escapes the repository") from exc
    return resolved


def _argv(value: Any, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ProfileError(f"{field} must be a non-empty argv array")
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item or item.strip() != item:
            raise ProfileError(f"{field}[{index}] must be a non-empty exact string")
        if item in FORBIDDEN_TOKENS or "\n" in item or "\r" in item or "\x00" in item:
            raise ProfileError(f"{field}[{index}] contains forbidden shell syntax")
        result.append(item)
    if result[0] != "python":
        raise ProfileError(f"{field} must use the sealed python launcher")
    return tuple(result)


def _pytest_targets(args: tuple[str, ...], *, field: str) -> tuple[str, ...]:
    if args[:4] != PYTEST_PREFIX or args[-1:] != PYTEST_SUFFIX or len(args) < 6:
        raise ProfileError(
            f"{field} must be exactly python -m pytest -q <explicit targets> --tb=short"
        )
    targets = args[4:-1]
    for index, target in enumerate(targets):
        if target.startswith("-"):
            raise ProfileError(f"{field} contains an unsealed pytest option")
        file_part = target.split("::", 1)[0]
        if not file_part.endswith(".py"):
            raise ProfileError(f"{field} target {index} is not an exact Python test path/node")
        _confined_path(file_part, field=f"{field}.target[{index}]")
    if len(set(targets)) != len(targets):
        raise ProfileError(f"{field} contains duplicate test targets")
    return targets


def _validate_exclusions(task_id: str, value: Any) -> None:
    if not isinstance(value, list):
        raise ProfileError(f"{task_id}.known_baseline_exclusions must be a list")
    if task_id != "PCTDD-002" and value:
        raise ProfileError(f"{task_id} may not carry unrelated baseline exclusions")
    expected_keys = {
        "node_id",
        "observed_outcome",
        "reason_code",
        "treatment",
        "authoritative_acceptance",
    }
    seen: set[str] = set()
    for index, record in enumerate(value):
        if not isinstance(record, Mapping) or set(record) != expected_keys:
            raise ProfileError(f"{task_id}.known_baseline_exclusions[{index}] fields differ")
        node_id = str(record.get("node_id") or "")
        if not node_id or node_id in seen or "::" not in node_id:
            raise ProfileError(f"{task_id} has malformed or duplicate baseline exclusion")
        seen.add(node_id)
        _confined_path(node_id.split("::", 1)[0], field=f"{task_id}.baseline_exclusion")
        if record.get("authoritative_acceptance") is not False:
            raise ProfileError(f"{task_id} baseline exclusion cannot become acceptance")
        for key in ("observed_outcome", "reason_code", "treatment"):
            if not isinstance(record.get(key), str) or not str(record[key]).strip():
                raise ProfileError(f"{task_id} baseline exclusion {key} differs")
    if task_id == "PCTDD-002" and seen != PCTDD_002_EXCLUDED_NODE_IDS:
        raise ProfileError("PCTDD-002 typed predecessor observation set differs")


def validate_profile_document(payload: Any) -> dict[str, Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        raise ProfileError("profile document must be an object")
    allowed_top = {"schema", "plan_revision", "dispatcher", "execution", "profiles"}
    unknown_top = sorted(set(payload) - allowed_top)
    if unknown_top:
        raise ProfileError(f"unknown profile-document fields: {unknown_top}")
    if payload.get("schema") != "pctdd/task-validation-profiles@1":
        raise ProfileError("profile schema differs")
    if payload.get("plan_revision") != PLAN_REVISION:
        raise ProfileError("profile plan revision differs")
    if payload.get("dispatcher") != Path(__file__).resolve().relative_to(ROOT).as_posix():
        raise ProfileError("profile dispatcher differs")
    if payload.get("execution") != "argv-only subprocess with shell=False":
        raise ProfileError("profile execution policy differs")
    profiles = payload.get("profiles")
    if not isinstance(profiles, Mapping) or tuple(sorted(profiles)) != TASK_IDS:
        raise ProfileError("profiles must cover exactly PCTDD-000 through PCTDD-053")
    profile_ids: set[str] = set()
    test_targets: set[str] = set()
    validated: dict[str, Mapping[str, Any]] = {}
    for task_id in TASK_IDS:
        profile = profiles.get(task_id)
        if not isinstance(profile, Mapping):
            raise ProfileError(f"{task_id} profile must be an object")
        allowed = {
            "task_id", "profile_id", "shell", "required_test_target",
            "required_acceptance", "known_baseline_exclusions", "commands",
        }
        unknown = sorted(set(profile) - allowed)
        if unknown:
            raise ProfileError(f"{task_id} has unknown profile fields: {unknown}")
        if profile.get("task_id") != task_id:
            raise ProfileError(f"{task_id} profile task binding differs")
        expected_id = f"pctdd-validation/{PLAN_REVISION}/{task_id}@1"
        if profile.get("profile_id") != expected_id:
            raise ProfileError(f"{task_id} profile identity differs")
        if expected_id in profile_ids:
            raise ProfileError(f"duplicate profile identity: {expected_id}")
        profile_ids.add(expected_id)
        if profile.get("shell") is not False:
            raise ProfileError(f"{task_id} must bind shell=false")
        target = profile.get("required_test_target")
        if not isinstance(target, str) or not target.endswith(".py"):
            raise ProfileError(f"{task_id} requires one exact Python test target")
        _confined_path(target, field=f"{task_id}.required_test_target")
        if target in test_targets:
            raise ProfileError(f"test target is not uniquely owned: {target}")
        test_targets.add(target)
        required_acceptance = profile.get("required_acceptance")
        if required_acceptance != {
            "controller_owned_independent_validation": True,
            "machine_readable_pytest_phase_evidence": True,
            "disallowed_outcomes": list(DISALLOWED_REQUIRED_OUTCOMES),
            "worker_authored_test_is_sufficient_alone": False,
        }:
            raise ProfileError(f"{task_id} required acceptance policy differs")
        _validate_exclusions(task_id, profile.get("known_baseline_exclusions"))
        commands = profile.get("commands")
        if not isinstance(commands, list) or not commands:
            raise ProfileError(f"{task_id} requires at least one concrete command")
        for index, command in enumerate(commands):
            if not isinstance(command, Mapping):
                raise ProfileError(f"{task_id}.commands[{index}] must be an object")
            if set(command) != {"argv", "cwd", "timeout_seconds", "evidence_policy"}:
                raise ProfileError(f"{task_id}.commands[{index}] fields differ")
            args = _argv(command.get("argv"), field=f"{task_id}.commands[{index}].argv")
            evidence_policy = command.get("evidence_policy")
            if not isinstance(evidence_policy, str) or not evidence_policy:
                raise ProfileError(f"{task_id}.commands[{index}].evidence_policy differs")
            if index == 0:
                expected = (*PYTEST_PREFIX, target, *PYTEST_SUFFIX)
                if args != expected or evidence_policy != "required_acceptance":
                    raise ProfileError(
                        f"{task_id} first command must be its exact isolated required-acceptance pytest target"
                    )
            elif task_id == "PCTDD-000":
                if index > len(OPERATOR_VALIDATORS) or args != OPERATOR_VALIDATORS[index - 1]:
                    raise ProfileError("PCTDD-000 validator command grammar differs")
                if evidence_policy != "operator_validator":
                    raise ProfileError("PCTDD-000 validator evidence policy differs")
            else:
                baseline_targets = _pytest_targets(
                    args, field=f"{task_id}.commands[{index}].argv"
                )
                if target in baseline_targets:
                    raise ProfileError(f"{task_id} baseline command repeats its worker target")
                if evidence_policy not in {
                    "protected_baseline_regression",
                    "isolated_predecessor_regression",
                    "explicit_green_predecessor_nodes",
                }:
                    raise ProfileError(f"{task_id} baseline evidence policy differs")
                if task_id in W1_BASELINE_COMMANDS:
                    expected_w1 = W1_BASELINE_COMMANDS[task_id]
                    if (
                        index > len(expected_w1)
                        or (evidence_policy, baseline_targets) != expected_w1[index - 1]
                    ):
                        raise ProfileError(f"{task_id} exact W1 baseline command differs")
            cwd = command.get("cwd")
            if cwd != ".":
                raise ProfileError(f"{task_id}.commands[{index}].cwd must be repository root")
            _confined_path(cwd, field=f"{task_id}.commands[{index}].cwd")
            timeout = command.get("timeout_seconds")
            if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 21600:
                raise ProfileError(f"{task_id}.commands[{index}].timeout_seconds differs")
        if task_id == "PCTDD-000" and len(commands) != 3:
            raise ProfileError("PCTDD-000 must run required acceptance plus both validators")
        if task_id != "PCTDD-000" and len(commands) < 2:
            raise ProfileError(f"{task_id} requires a protected baseline regression command")
        if task_id in W1_BASELINE_COMMANDS and len(commands) != len(W1_BASELINE_COMMANDS[task_id]) + 1:
            raise ProfileError(f"{task_id} exact W1 baseline command population differs")
        validated[task_id] = profile
    return validated


def load_profiles(path: Path = PROFILE_PATH) -> dict[str, Mapping[str, Any]]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"cannot load sealed profile document: {exc}") from exc
    return validate_profile_document(payload)


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _sealed_duckdb_extension_directory() -> str:
    """Return the content-verified Quack/DuckLake directory from the seal."""

    try:
        payload = json.loads(
            DEPENDENCY_SEAL_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
        )
        capabilities = payload["environment"]["capabilities"]
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise ProfileError(f"cannot resolve sealed DuckDB extension bindings: {exc}") from exc
    directories: set[Path] = set()
    for name in ("quack", "ducklake"):
        record = capabilities.get(name)
        if not isinstance(record, Mapping):
            raise ProfileError(f"dependency seal omits {name} extension binding")
        raw_directory = str(record.get("extension_directory") or "").strip()
        raw_path = str(record.get("install_path") or "").strip()
        claimed_sha256 = str(record.get("install_sha256") or "").strip().lower()
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", claimed_sha256):
            raise ProfileError(f"dependency seal has malformed {name} extension SHA-256")
        try:
            directory = Path(raw_directory).resolve(strict=True)
            extension = Path(raw_path).resolve(strict=True)
            extension.relative_to(directory)
        except (OSError, ValueError) as exc:
            raise ProfileError(f"sealed {name} extension path is unavailable or escapes") from exc
        if not directory.is_dir() or not extension.is_file():
            raise ProfileError(f"sealed {name} extension binding is not a directory/file pair")
        if extension.name != f"{name}.duckdb_extension":
            raise ProfileError(f"sealed {name} extension filename differs")
        actual_sha256 = _sha256_path(extension)
        if actual_sha256 != claimed_sha256:
            raise ProfileError(f"sealed {name} extension bytes differ")
        directories.add(directory)
    if len(directories) != 1:
        raise ProfileError("Quack and DuckLake must share one sealed extension directory")
    return str(next(iter(directories)))


def pytest_configure(config: Any) -> None:
    """Register the append-only observer without exposing receipt authority."""

    raw_fd = os.environ.get(PYTEST_PHASE_FD_ENV, "").strip()
    nonce = os.environ.get(PYTEST_PHASE_NONCE_ENV, "").strip()
    if not raw_fd and not nonce:
        return
    if not re.fullmatch(r"[1-9][0-9]{0,9}", raw_fd) or not re.fullmatch(
        r"[0-9a-f]{64}", nonce
    ):
        raise RuntimeError("pytest phase transport binding is malformed")
    fd = int(raw_fd)
    os.set_inheritable(fd, False)
    plugin = _AppendOnlyPytestPhasePlugin(fd=fd, nonce=nonce)
    os.environ.pop(PYTEST_PHASE_FD_ENV, None)
    os.environ.pop(PYTEST_PHASE_NONCE_ENV, None)
    plugin.emit_configure(str(Path(str(config.rootpath)).resolve(strict=False)))
    config.pluginmanager.register(
        plugin,
        name="pctdd-append-only-phase-observer-v1",
    )


@contextmanager
def _sealed_validation_environment() -> Iterator[tuple[dict[str, str], str, dict[str, Any]]]:
    accelerator = ROOT / "external/ipfs_accelerate"
    if str(accelerator) not in sys.path:
        sys.path.insert(0, str(accelerator))
    from ipfs_accelerate_py.agent_supervisor.validation.validation_runtime import (
        build_validation_environment,
        sealed_validation_python_runner,
        validation_environment_for_runner,
        validation_python_launcher_environment,
    )

    environment = build_validation_environment(os.environ)
    # HOME/XDG remain neutral.  Expose only the exact content-verified local
    # extension directory so validation can reproduce the sealed capability
    # without network installation or ambient user configuration.
    environment[PCTDD_DUCKDB_EXTENSION_DIRECTORY_ENV] = (
        _sealed_duckdb_extension_directory()
    )
    import_roots = [
        str(ROOT / "scripts"),
        str(ROOT),
        str(ROOT / "external/ipfs_accelerate"),
        str(ROOT / "external/ipfs_datasets"),
        str(ROOT / "external/ipfs_kit"),
    ]
    approved = [item for item in environment.get("PYTHONPATH", "").split(os.pathsep) if item]
    environment["PYTHONPATH"] = os.pathsep.join(dict.fromkeys((*import_roots, *approved)))

    def sealed_runner_marker() -> None:
        return None

    sealed_validation_python_runner(sealed_runner_marker)
    environment = validation_environment_for_runner(environment, sealed_runner_marker)
    with validation_python_launcher_environment(environment) as (child, receipt):
        yield child, child["PYTHON"], {
            "mode": receipt.mode,
            "content_sha256": receipt.content_sha256,
            "interpreter_sha256": receipt.interpreter_sha256,
            "policy_sha256": receipt.policy_sha256,
            "sealed": receipt.sealed,
        }


def _terminate_process(process: subprocess.Popen[Any]) -> None:
    accelerator = ROOT / "external/ipfs_accelerate"
    if str(accelerator) not in sys.path:
        sys.path.insert(0, str(accelerator))
    from ipfs_accelerate_py.agent_supervisor.todo_daemon import core as process_core
    from ipfs_accelerate_py.agent_supervisor.todo_daemon.supervisor_runtime import (
        terminate_process_with_grace,
    )

    if process.poll() is None:
        result = terminate_process_with_grace(
            process,
            grace_seconds=5.0,
            kill_wait_seconds=5.0,
        )
        fenced = not result.timed_out
    else:
        # The session leader may have exited while a descendant deliberately
        # retains the append-only FD.  The owned process group remains the
        # stable kernel fence even after its leader has been reaped.
        process_core._terminate_owned_process_group(
            process.pid,
            grace_seconds=5.0,
        )
        fenced = not process_core._process_group_has_live_members(process.pid)
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        fenced = False
    if not fenced:
        raise ProfileError("validation process group did not reach a fenced terminal")


def _run_child(
    args: Sequence[str],
    *,
    cwd: Path,
    environment: Mapping[str, str],
    timeout_seconds: int,
    phase_pipe: tuple[int, int] | None = None,
) -> tuple[int, bytes, bool]:
    pipe_result: dict[str, Any] = {
        "bytes": b"",
        "error": "",
        "overflow": False,
    }
    reader: threading.Thread | None = None
    reader_stop = threading.Event()
    pass_fds: tuple[int, ...] = ()
    try:
        try:
            if VALIDATION_SUBREAPER_PATH.is_symlink():
                raise OSError("subreaper source must not be a symlink")
            subreaper = VALIDATION_SUBREAPER_PATH.resolve(strict=True)
            subreaper.relative_to(VALIDATION_SUBREAPER_ROOT.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise ProfileError("sealed validation subreaper is unavailable") from exc
        if not subreaper.is_file() or subreaper.is_symlink():
            raise ProfileError("sealed validation subreaper is not a regular source file")
        if _sha256_path(subreaper) != VALIDATION_SUBREAPER_SHA256:
            raise ProfileError("sealed validation subreaper bytes differ")
    except BaseException:
        # Ownership of the caller-created evidence pipe transfers with this
        # call.  Integrity preflight happens before the reader thread starts,
        # so close both ends here on every prelaunch rejection.
        for fd in phase_pipe or ():
            try:
                os.close(fd)
            except OSError:
                pass
        raise
    if phase_pipe is not None:
        read_fd, write_fd = phase_pipe
        pass_fds = (write_fd,)
        os.set_blocking(read_fd, False)
        pipe_result["eof"] = False
        pipe_result["unterminated"] = False

        def read_phase_stream() -> None:
            content = bytearray()
            try:
                while True:
                    try:
                        chunk = os.read(read_fd, 65536)
                    except BlockingIOError:
                        if not reader_stop.wait(0.05):
                            continue
                        # The wrapper has reached its terminal.  Retry once so
                        # a just-closed writer is observed as real EOF instead
                        # of being mislabeled as a leaked descendant FD.
                        try:
                            chunk = os.read(read_fd, 65536)
                        except BlockingIOError:
                            pipe_result["unterminated"] = True
                            break
                    if not chunk:
                        pipe_result["eof"] = True
                        break
                    if len(content) + len(chunk) > PYTEST_PHASE_STREAM_MAX_BYTES:
                        pipe_result["overflow"] = True
                        continue
                    content.extend(chunk)
            except OSError as exc:
                pipe_result["error"] = type(exc).__name__
            finally:
                try:
                    os.close(read_fd)
                except OSError:
                    pass
                pipe_result["bytes"] = bytes(content)

        reader = threading.Thread(
            target=read_phase_stream,
            name="pctdd-phase-stream-reader",
            daemon=True,
        )
        reader.start()
    try:
        subreaper_args = [str(args[0]), "-I", str(subreaper)]
        if phase_pipe is not None:
            subreaper_args.extend(("--pass-fd", str(phase_pipe[1])))
        subreaper_args.extend(("--", *[str(value) for value in args]))
        process = subprocess.Popen(
            subreaper_args,
            cwd=cwd,
            env=dict(environment),
            shell=False,
            stdin=subprocess.DEVNULL,
            # Reserve stdout for the dispatcher's closed JSON evidence records.
            # Pytest/tool diagnostics remain bounded and hashed by the outer
            # recovery runner on stderr, so prose can never confuse admission.
            stdout=sys.stderr,
            stderr=sys.stderr,
            start_new_session=True,
            close_fds=True,
            pass_fds=pass_fds,
        )
    except BaseException:
        if phase_pipe is not None:
            try:
                os.close(phase_pipe[1])
            except OSError:
                pass
            if reader is not None:
                reader_stop.set()
                reader.join(timeout=5.0)
        raise
    if phase_pipe is not None:
        try:
            os.close(phase_pipe[1])
        except OSError:
            pass
    try:
        process.communicate(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        try:
            _terminate_process(process)
        except BaseException:
            reader_stop.set()
            if reader is not None:
                reader.join(timeout=5.0)
            raise
        returncode = 124
    except BaseException:
        try:
            _terminate_process(process)
        finally:
            reader_stop.set()
            if reader is not None:
                reader.join(timeout=5.0)
        raise
    else:
        returncode = int(process.returncode or 0)
    try:
        # Successful children may still have daemonized descendants.  Fence
        # the entire owned session before the parent writes or admits evidence.
        _terminate_process(process)
    except BaseException:
        reader_stop.set()
        if reader is not None:
            reader.join(timeout=5.0)
        raise
    if reader is not None:
        reader_stop.set()
        reader.join(timeout=5.0)
    transport_integrity = bool(
        reader is None
        or (
            not reader.is_alive()
            and pipe_result.get("eof") is True
            and pipe_result.get("unterminated") is False
            and pipe_result.get("overflow") is False
            and not pipe_result.get("error")
        )
    )
    return returncode, bytes(pipe_result.get("bytes") or b""), transport_integrity


def _parse_pytest_phase_stream(
    raw: bytes,
    *,
    nonce: str,
) -> tuple[Path, tuple[dict[str, str], ...], int, str, int]:
    """Validate the closed append-only stream produced by the child plugin."""

    if not raw or len(raw) > PYTEST_PHASE_STREAM_MAX_BYTES or not raw.endswith(b"\n"):
        raise ProfileError("required pytest phase stream is absent or unbounded")
    expected_sequence = 0
    expected_digest = _phase_genesis_digest(nonce)
    rootpath: Path | None = None
    finish_status: int | None = None
    phases: list[dict[str, str]] = []
    split_frames = raw.split(b"\n")
    if split_frames[-1] != b"" or any(b"\r" in line for line in split_frames[:-1]):
        raise ProfileError("required pytest phase stream framing is not canonical LF")
    lines = split_frames[:-1]
    for index, line in enumerate(lines):
        if not line or len(line) + 1 > PYTEST_PHASE_FRAME_MAX_BYTES:
            raise ProfileError("required pytest phase frame is malformed")
        try:
            frame = json.loads(
                line.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_keys,
            )
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise ProfileError("required pytest phase frame is not canonical JSON") from exc
        base_fields = {
            "schema",
            "session_nonce",
            "sequence",
            "previous_digest",
            "kind",
        }
        if (
            not isinstance(frame, Mapping)
            or frame.get("schema") != PYTEST_PHASE_EVENT_SCHEMA
            or frame.get("session_nonce") != nonce
            or type(frame.get("sequence")) is not int
            or frame.get("sequence") != expected_sequence
            or frame.get("previous_digest") != expected_digest
            or json.dumps(frame, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
            != line
        ):
            raise ProfileError("required pytest phase frame chain differs")
        kind = frame.get("kind")
        if kind == "configure":
            if index != 0 or rootpath is not None or set(frame) != base_fields | {
                "rootpath"
            }:
                raise ProfileError("required pytest configure frame differs")
            raw_rootpath = frame.get("rootpath")
            if not isinstance(raw_rootpath, str) or not raw_rootpath:
                raise ProfileError("required pytest rootpath is absent")
            try:
                rootpath = Path(raw_rootpath).resolve(strict=True)
                rootpath.relative_to(ROOT.resolve(strict=True))
            except (OSError, ValueError) as exc:
                raise ProfileError("required pytest rootpath escapes the repository") from exc
        elif kind == "phase":
            if (
                rootpath is None
                or finish_status is not None
                or set(frame)
                != base_fields | {"node_id", "phase", "disposition"}
                or not isinstance(frame.get("node_id"), str)
                or not frame.get("node_id")
                or len(frame["node_id"]) > 4096
                or frame.get("phase") not in {"setup", "call", "teardown"}
                or frame.get("disposition")
                not in {"passed", *DISALLOWED_REQUIRED_OUTCOMES}
            ):
                raise ProfileError("required pytest phase observation differs")
            phases.append(
                {
                    "node_id": str(frame["node_id"]),
                    "phase": str(frame["phase"]),
                    "disposition": str(frame["disposition"]),
                }
            )
        elif kind == "finish":
            if (
                index != len(lines) - 1
                or rootpath is None
                or finish_status is not None
                or set(frame) != base_fields | {"exitstatus"}
                or type(frame.get("exitstatus")) is not int
            ):
                raise ProfileError("required pytest finish frame differs")
            finish_status = int(frame["exitstatus"])
        else:
            raise ProfileError("required pytest phase frame kind is unknown")
        expected_digest = "sha256:" + hashlib.sha256(line).hexdigest()
        expected_sequence += 1
    if rootpath is None or finish_status is None or not phases:
        raise ProfileError("required pytest phase stream is incomplete")
    return (
        rootpath,
        tuple(phases),
        finish_status,
        "sha256:" + hashlib.sha256(raw).hexdigest(),
        expected_sequence,
    )


def _write_parent_phase_evidence(
    path: Path,
    *,
    raw_stream: bytes,
    nonce: str,
    target: str,
    returncode: int,
    transport_integrity: bool,
) -> None:
    """Aggregate raw observations and persist the only authoritative receipt."""

    if not transport_integrity:
        raise ProfileError("required pytest append-only transport is incomplete")
    rootpath, reports, finish_status, stream_sha256, event_count = (
        _parse_pytest_phase_stream(raw_stream, nonce=nonce)
    )
    if finish_status != returncode:
        raise ProfileError("required pytest finish/child status binding differs")
    target_path = _confined_path(target, field="required_test_target")
    try:
        nested_alias = target_path.relative_to(rootpath).as_posix()
    except ValueError as exc:
        raise ProfileError("required pytest target is outside reported rootpath") from exc
    aliases = {target, nested_alias}

    counts = {name: 0 for name in ("passed", *DISALLOWED_REQUIRED_OUTCOMES)}
    phases_by_node: dict[str, dict[str, str]] = {}
    for report in reports:
        raw_node_id = report["node_id"]
        canonical_node_id = raw_node_id
        for alias in sorted(aliases, key=lambda item: (-len(item), item)):
            if raw_node_id == alias:
                canonical_node_id = target
                break
            if raw_node_id.startswith(alias + "::"):
                canonical_node_id = target + raw_node_id[len(alias) :]
                break
        phase = report["phase"]
        node_phases = phases_by_node.setdefault(canonical_node_id, {})
        if not (
            canonical_node_id == target
            or canonical_node_id.startswith(target + "::")
        ):
            raise ProfileError("required pytest phase stream contains an off-target node")
        if phase in node_phases:
            raise ProfileError("required pytest phase stream contains a duplicate phase")
        expected_phase = ("setup", "call", "teardown")[len(node_phases)]
        if phase != expected_phase:
            raise ProfileError("required pytest phase stream contains reordered phases")
        node_phases[phase] = report["disposition"]
        counts[report["disposition"]] += 1
    fully_passed = sum(
        1
        for phases in phases_by_node.values()
        if phases == {"setup": "passed", "call": "passed", "teardown": "passed"}
    )
    payload = {
        "schema": PYTEST_PHASE_OUTCOME_SCHEMA,
        "required_test_target": target,
        "collector_integrity": True,
        "event_stream_sha256": stream_sha256,
        "event_count": event_count,
        "exitstatus": returncode,
        "test_count": len(phases_by_node),
        "phase_count": len(reports),
        "fully_passed_test_count": fully_passed,
        "counts": dict(sorted(counts.items())),
        "node_ids": sorted(phases_by_node),
    }
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _load_required_phase_evidence(path: Path, *, target: str) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicate_keys)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProfileError(f"required pytest phase evidence is unavailable: {exc}") from exc
    expected_fields = {
        "schema", "required_test_target", "exitstatus", "test_count",
        "phase_count", "fully_passed_test_count", "counts", "node_ids",
        "collector_integrity", "event_stream_sha256", "event_count",
    }
    if (
        not isinstance(payload, Mapping)
        or set(payload) != expected_fields
        or payload.get("schema") != "pctdd/pytest-phase-outcome@2"
    ):
        raise ProfileError("required pytest phase evidence schema differs")
    if (
        payload.get("required_test_target") != target
        or payload.get("collector_integrity") is not True
        or not isinstance(payload.get("event_stream_sha256"), str)
        or re.fullmatch(
            r"sha256:[0-9a-f]{64}", str(payload.get("event_stream_sha256"))
        )
        is None
        or type(payload.get("event_count")) is not int
        or not isinstance(payload.get("exitstatus"), int)
        or isinstance(payload.get("exitstatus"), bool)
        or payload.get("exitstatus") != 0
    ):
        raise ProfileError("required pytest phase evidence target/exit binding differs")
    counts = payload.get("counts")
    expected_count_keys = {"passed", *DISALLOWED_REQUIRED_OUTCOMES}
    if not isinstance(counts, Mapping) or set(counts) != expected_count_keys:
        raise ProfileError("required pytest phase counts are absent")
    try:
        raw_numbers = [
            *(counts.get(name) for name in expected_count_keys),
            payload.get("test_count"),
            payload.get("phase_count"),
            payload.get("fully_passed_test_count"),
            payload.get("event_count"),
        ]
        if not all(isinstance(value, int) and not isinstance(value, bool) for value in raw_numbers):
            raise TypeError("phase counts must be exact JSON integers")
        normalized_counts = {name: counts[name] for name in expected_count_keys}
        test_count = payload["test_count"]
        phase_count = payload["phase_count"]
        fully_passed = payload["fully_passed_test_count"]
        event_count = payload["event_count"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ProfileError("required pytest phase counts are malformed") from exc
    if any(value < 0 for value in normalized_counts.values()):
        raise ProfileError("required pytest phase counts are malformed")
    node_ids = payload.get("node_ids")
    nodes_are_exact = (
        isinstance(node_ids, list)
        and len(node_ids) == test_count
        and all(isinstance(item, str) and item for item in node_ids)
        and len(set(node_ids)) == test_count
        and node_ids == sorted(node_ids)
        and all(item == target or item.startswith(target + "::") for item in node_ids)
    )
    nonzero = [
        name for name in DISALLOWED_REQUIRED_OUTCOMES
        if normalized_counts[name]
    ]
    complete = (
        test_count > 0
        and fully_passed == test_count
        and phase_count == test_count * 3
        and normalized_counts["passed"] == phase_count
        and sum(normalized_counts.values()) == phase_count
        and event_count == phase_count + 2
        and nodes_are_exact
    )
    if nonzero or not complete:
        raise ProfileError(
            "required pytest phase evidence is not an all-pass population: "
            + ",".join(nonzero or ("incomplete_phases",))
        )
    return {
        "schema": payload["schema"],
        "sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "collector_integrity": True,
        "event_stream_sha256": payload["event_stream_sha256"],
        "event_count": event_count,
        "test_count": test_count,
        "phase_count": phase_count,
        "fully_passed_test_count": fully_passed,
        "counts": dict(sorted(normalized_counts.items())),
    }


def run_profile(task_id: str, *, profile_path: Path = PROFILE_PATH) -> int:
    if not TASK_RE.fullmatch(task_id):
        raise ProfileError("task must be exactly PCTDD-000 through PCTDD-053")
    profile = load_profiles(profile_path)[task_id]
    with _sealed_validation_environment() as (environment, python, launcher_receipt):
        for index, raw in enumerate(profile["commands"]):
            args = list(_argv(raw["argv"], field=f"{task_id}.commands[{index}].argv"))
            args[0] = python
            cwd = _confined_path(str(raw["cwd"]), field=f"{task_id}.commands[{index}].cwd")
            started = time.monotonic()
            phase_evidence: dict[str, Any] | None = None
            with tempfile.TemporaryDirectory(prefix="pctdd-validation-") as temporary:
                report_path = Path(temporary) / "pytest-phase-report.json"
                child_environment = dict(environment)
                child_environment.pop(PYTEST_PHASE_FD_ENV, None)
                child_environment.pop(PYTEST_PHASE_NONCE_ENV, None)
                phase_pipe: tuple[int, int] | None = None
                nonce = ""
                if index == 0:
                    phase_pipe = os.pipe()
                    nonce = secrets.token_hex(32)
                    child_environment[PYTEST_PHASE_FD_ENV] = str(phase_pipe[1])
                    child_environment[PYTEST_PHASE_NONCE_ENV] = nonce
                    args = [*args[:3], "-p", PYTEST_PLUGIN_NAME, *args[3:]]
                returncode, raw_stream, transport_integrity = _run_child(
                    args,
                    cwd=cwd,
                    environment=child_environment,
                    timeout_seconds=int(raw["timeout_seconds"]),
                    phase_pipe=phase_pipe,
                )
                if index == 0 and returncode == 0:
                    try:
                        _write_parent_phase_evidence(
                            report_path,
                            raw_stream=raw_stream,
                            nonce=nonce,
                            target=str(profile["required_test_target"]),
                            returncode=returncode,
                            transport_integrity=transport_integrity,
                        )
                        phase_evidence = _load_required_phase_evidence(
                            report_path,
                            target=str(profile["required_test_target"]),
                        )
                    except ProfileError as exc:
                        print(
                            json.dumps(
                                {
                                    "task_id": task_id,
                                    "profile_id": profile["profile_id"],
                                    "step": index,
                                    "status": "failed",
                                    "reason_code": "required_pytest_phase_evidence_rejected",
                                    "message": str(exc),
                                },
                                sort_keys=True,
                            )
                        )
                        return 1
            print(
                json.dumps(
                    {
                        "task_id": task_id,
                        "profile_id": profile["profile_id"],
                        "step": index,
                        "evidence_policy": raw["evidence_policy"],
                        "status": (
                            "timeout" if returncode == 124
                            else "passed" if returncode == 0
                            else "failed"
                        ),
                        "returncode": returncode,
                        "elapsed_seconds": round(time.monotonic() - started, 6),
                        "pytest_phase_evidence": phase_evidence,
                        "validation_python_launcher": launcher_receipt,
                    },
                    sort_keys=True,
                )
            )
            if returncode != 0:
                return returncode
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", choices=TASK_IDS)
    parser.add_argument("--check-profiles", action="store_true")
    args = parser.parse_args(argv)
    if args.check_profiles:
        profiles = load_profiles()
        print(json.dumps({"schema": "pctdd/validation-profile-check@1", "plan_revision": PLAN_REVISION, "profile_count": len(profiles), "shell": False, "status": "valid"}, sort_keys=True))
        return 0
    if not args.task:
        parser.error("--task is required unless --check-profiles is used")
    return run_profile(args.task)


if __name__ == "__main__":
    raise SystemExit(main())
