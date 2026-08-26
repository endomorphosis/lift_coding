#!/usr/bin/env python3
"""Bootstrap and operate the PCSM DuckDB + Quack control plane.

The authority split is deliberately narrow:

* ``DatabaseTaskSource@1`` over DuckDB is transactional task/goal authority.
* one fenced loopback Quack process exclusively owns the DuckDB file while
  supervisors are running;
* DuckLake is an optional, rebuildable history projection and is never read by
  readiness, completion, promotion, or release gates.

The Markdown plan, objectives, and task board are immutable bootstrap inputs.
This operator never mutates their status fields and never publishes the raw
Quack authentication token.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import socket
import stat as stat_module
import subprocess
import sys
import threading
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

ROOT: Final = Path(__file__).resolve().parents[1]
ACCEL_ROOT: Final = ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_CONFIG: Final = Path(
    "config/proof_carrying_semantic_minification_v1_supervisor.json"
)
RUNTIME_RELATIVE: Final = Path(
    "data/agent_supervisor/proof_carrying_semantic_minification_v1"
)
BOOTSTRAP_RECEIPT_NAME: Final = "bootstrap-materialization.json"
DUCKLAKE_RECEIPT_NAME: Final = "ducklake-history-projection.json"
OPERATOR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-operator@1"
)
POPULATION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-population@1"
)
BOOTSTRAP_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-bootstrap@1"
)
DATABASE_TASK_SOURCE_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/database-task-source@1"
)
DUCKLAKE_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-ducklake-projection@1"
)
GOAL_RE: Final = re.compile(r"^## (PCSM-G\d{3}) (.+)$", re.MULTILINE)
QUACK_ENDPOINT_RE: Final = re.compile(
    r"^quack:(?://)?(127(?:\.\d{1,3}){3}|localhost):(\d{1,5})$",
    re.IGNORECASE,
)
READY_STATUSES: Final = (
    "proposed",
    "admitted",
    "pending",
    "ready",
    "todo",
    "queued",
    "retrying",
)
COMPLETED_STATUSES: Final = ("completed", "skipped", "complete", "done")
ACTIVE_STATUSES: Final = ("claimed", "in_progress", "running")
TERMINAL_STATUSES: Final = (
    *COMPLETED_STATUSES,
    "cancelled",
    "failed",
    "quarantined",
    "rejected",
)
OWNER_DML_PREFIXES: Final = (
    "UPDATE ",
    "DELETE ",
    "MERGE ",
    "INSERT OR REPLACE",
    "INSERT OR IGNORE",
)
OWNER_DAEMON_COMMAND: Final = "state-owner-daemon"
EXECUTOR_OWNER_SESSION_BASE: Final = "pcsm-v1-executor"
INTERNAL_CLIENT_GRANT_TTL_SECONDS: Final = 86_400.0
EXECUTOR_BOOTSTRAP_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-executor-bootstrap@1"
)
OWNER_RESTART_ADMISSION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-owner-restart-admission@1"
)
OWNER_RESTART_RECEIPT_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-owner-restart-receipt@1"
)
OWNER_DATABASE_VERIFICATION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-owner-database-verification@1"
)
QUACK_STATE_SERVER_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/quack-state-server@1"
)
QUACK_STATE_SERVER_INTERFACE: Final = "QuackStateServer@1"
STATE_SERVER_IDENTITY_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/state-server-identity@1"
)
STATE_SERVER_IDENTITY_INTERFACE: Final = "StateServerIdentity@1"
HANDOFF_REPAIR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-semantic-minification-handoff-repair@1"
)
HANDOFF_REPAIR_PATH: Final = (
    ROOT
    / "artifacts"
    / "proof_carrying_semantic_minification"
    / "handoff"
    / "supervisor-restart-repair.json"
)
HANDOFF_REPAIR_MAX_TASK_ATTEMPTS: Final = 2
HANDOFF_REPAIR_TASK_CID: Final = (
    "baguqeera6mvj3326qcksmlmwafo3s7ppd4s22vnbsn4tjnk4ylbjyqiesypa"
)
HANDOFF_REPAIR_COMPLETION_RECEIPT_ID: Final = (
    "sha256:e00019f28ba2031bf94076661378b1de877c843512c7a41071968a56001361a3"
)
HANDOFF_REPAIR_SOURCE_ATTEMPT: Final = {
    "attempt_id": "attempt:53a9ee3f434e4551932f258aa9c903c6",
    "claim_id": "claim:617b52197f564c58ade577daf8430602",
    "lease_id": "lease:b562bfc2ae884a958362697b3c5c7185",
    "owner_session_id": "pcsm-v1-executor:shard:0-of-4:track:ef26cb9db64a",
    "attempt_number": 1,
    "fencing_token": 1,
    "fence_epoch": 1,
    "task_revision": 4,
}
HANDOFF_REPAIR_REQUIRED_VALIDATIONS: Final = frozenset(
    {
        (
            ".",
            (
                "python",
                "-m",
                "py_compile",
                "scripts/run_agent_supervisor_proof_carrying_semantic_minification.py",
                "scripts/generate_proof_carrying_semantic_minification_board.py",
                "scripts/validate_proof_carrying_semantic_minification_board.py",
            ),
        ),
        (
            ".",
            (
                "python",
                "scripts/generate_proof_carrying_semantic_minification_board.py",
                "--check",
            ),
        ),
        (
            ".",
            (
                "python",
                "scripts/validate_proof_carrying_semantic_minification_board.py",
                "--check-all",
            ),
        ),
        (
            ".",
            (
                "env",
                "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:"
                "external/ipfs_kit:Mcp-Plus-Plus",
                "python",
                "-m",
                "pytest",
                "-q",
                "external/ipfs_datasets/tests/proof_context",
            ),
        ),
        (
            "external/ipfs_accelerate",
            (
                "python",
                "-m",
                "pytest",
                "-q",
                "test/api/test_agent_supervisor_database_portal_bridge.py",
                "test/api/test_agent_supervisor_merge_train.py",
                "test/api/test_agent_supervisor_task_attempt_limit.py",
                "test/api/test_agent_supervisor_multi_supervisor_shutdown.py",
            ),
        ),
    }
)
_RESTART_IMMUTABLE_SOURCE_NAMES: Final = frozenset(
    {"objectives", "plan", "taskboard"}
)
_RESTART_REPAIR_SOURCE_NAMES: Final = frozenset(
    {"config", "generator", "operator", "validator"}
)
_RESTART_ALLOWED_SOURCE_BINDING_FIELDS: Final = frozenset(
    {
        "ipfs_accelerate_origin_main_revision",
        "ipfs_accelerate_planning_revision",
        "ipfs_accelerate_planning_tree",
        "ipfs_datasets_planning_revision",
        "ipfs_datasets_planning_tree",
    }
)
_RESTART_SOURCE_FOREST_REPOSITORIES: Final = frozenset(
    {"ipfs_accelerate", "ipfs_datasets", "ipfs_kit", "mcp_plus_plus"}
)
_RESTART_SOURCE_FOREST_ENTRY_FIELDS: Final = frozenset(
    {"repository", "path", "head", "tree", "access"}
)


class OperatorError(RuntimeError):
    """Fail-closed PCSM operator error."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _identity(value: Any) -> str:
    payload = value if isinstance(value, bytes) else _canonical_bytes(value)
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _atomic_json(path: Path, payload: Mapping[str, Any], *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        os.chmod(path, mode)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorError(f"cannot read JSON object: {path}") from exc
    if not isinstance(value, dict):
        raise OperatorError(f"JSON root must be an object: {path}")
    return value


def _safe_path(root: Path, value: Any, *, field: str) -> Path:
    text = str(value or "").strip()
    relative = Path(text)
    if not text or relative.is_absolute() or ".." in relative.parts:
        raise OperatorError(f"{field} must be a safe repository-relative path")
    resolved = (root / relative).resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise OperatorError(f"{field} escapes repository") from exc
    return resolved


def _ensure_private_runtime_directory(path: Path) -> None:
    """Create or harden one same-user runtime directory for lane sidecars."""

    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    nofollow = getattr(os, "O_NOFOLLOW", None)
    if nofollow is None:
        raise OperatorError("private runtime directories require no-follow access")
    before = path.stat(follow_symlinks=False)
    flags = (
        os.O_RDONLY
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_CLOEXEC", 0)
        | nofollow
    )
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise OperatorError(f"runtime directory cannot be opened safely: {path}") from exc
    try:
        opened = os.fstat(descriptor)
        if (
            not stat_module.S_ISDIR(opened.st_mode)
            or opened.st_uid != os.geteuid()
            or (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise OperatorError(f"runtime directory is not an owned directory: {path}")
        os.fchmod(descriptor, 0o700)
        hardened = os.fstat(descriptor)
        named = path.stat(follow_symlinks=False)
        if (
            stat_module.S_IMODE(hardened.st_mode) != 0o700
            or (named.st_dev, named.st_ino) != (hardened.st_dev, hardened.st_ino)
            or named.st_uid != os.geteuid()
        ):
            raise OperatorError(f"runtime directory could not be hardened: {path}")
    finally:
        os.close(descriptor)


def _git(*arguments: str, check: bool = True, binary: bool = False) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        capture_output=True,
        text=not binary,
        check=False,
    )
    if check and completed.returncode != 0:
        error = completed.stderr or completed.stdout
        if isinstance(error, bytes):
            error = error.decode("utf-8", errors="replace")
        raise OperatorError(
            f"git {' '.join(arguments)} failed: {str(error).strip()}"
        )
    return completed.stdout


def _assert_clean_current_tree(config: Mapping[str, Any]) -> tuple[str, str]:
    status_output = str(
        _git("status", "--porcelain=v1", "--untracked-files=all")
    ).strip()
    if status_output:
        raise OperatorError(
            "refusing to materialize from a dirty worktree; commit the exact "
            "plan, board, configuration, validator, and operator first"
        )
    head = str(_git("rev-parse", "HEAD")).strip()
    tree = str(_git("rev-parse", "HEAD^{tree}")).strip()
    branch = str(_git("branch", "--show-current")).strip()
    required_branch = str(config.get("merge_target_branch") or "").strip()
    if required_branch and branch != required_branch:
        raise OperatorError(
            f"execution branch {branch!r} differs from configured branch "
            f"{required_branch!r}"
        )
    binding = config.get("source_binding")
    binding = binding if isinstance(binding, Mapping) else {}
    ancestor = str(binding.get("accelerator_required_ancestor") or "").strip()
    if ancestor:
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ancestor, "HEAD"],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            raise OperatorError("configured accelerator base is not an ancestor")
    return head, tree


def _tracked_bytes(path: Path, *, head: str) -> bytes:
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise OperatorError(f"authority input escapes repository: {path}") from exc
    if path.is_symlink() or not path.is_file():
        raise OperatorError(f"authority input is not a regular file: {relative}")
    working = path.read_bytes()
    recorded = _git("show", f"{head}:{relative}", binary=True)
    if not isinstance(recorded, bytes) or working != recorded:
        raise OperatorError(f"authority input differs from current HEAD: {relative}")
    return working


def _git_commit_tree(
    commit: Any,
    *,
    field: str,
    repository: Path = ROOT,
) -> str:
    revision = str(commit or "").strip()
    if re.fullmatch(r"[0-9a-f]{40}", revision) is None:
        raise OperatorError(f"{field} must be an exact Git commit")
    try:
        object_type = subprocess.run(
            ["git", "cat-file", "-t", revision],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
        tree_result = subprocess.run(
            ["git", "rev-parse", f"{revision}^{{tree}}"],
            cwd=repository,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise OperatorError(f"{field} is unavailable") from exc
    tree = tree_result.stdout.strip()
    if (
        object_type.returncode != 0
        or object_type.stdout.strip() != "commit"
        or tree_result.returncode != 0
        or re.fullmatch(r"[0-9a-f]{40}", tree) is None
    ):
        raise OperatorError(f"{field} is not an available Git commit")
    return tree


def _git_is_ancestor(
    ancestor: Any,
    descendant: Any,
    *,
    field: str,
    repository: Path = ROOT,
) -> None:
    older = str(ancestor or "").strip()
    newer = str(descendant or "").strip()
    if not older or not newer:
        raise OperatorError(f"{field} has an empty revision")
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", older, newer],
        cwd=repository,
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.returncode == 0:
        return
    if completed.returncode == 1:
        raise OperatorError(f"{field} is not monotonic")
    raise OperatorError(f"cannot verify {field}")


def _git_blob_at(*, head: str, path: Path, field: str) -> bytes:
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise OperatorError(f"{field} escapes repository") from exc
    try:
        value = _git("show", f"{head}:{relative}", binary=True)
    except OperatorError as exc:
        raise OperatorError(f"{field} is absent from the sealed source") from exc
    if not isinstance(value, bytes):
        raise OperatorError(f"{field} could not be read as bytes")
    return value


def _json_mapping_bytes(value: bytes, *, field: str) -> dict[str, Any]:
    try:
        decoded = json.loads(value.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OperatorError(f"{field} must be a JSON object") from exc
    if not isinstance(decoded, dict):
        raise OperatorError(f"{field} must be a JSON object")
    return decoded


def _exact_int(value: Any, *, field: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise OperatorError(f"{field} must be an integer >= {minimum}")
    return value


def _restart_source_paths(board: Any) -> dict[str, Path]:
    return {
        "config": board.config_path,
        "taskboard": board.path(board.taskboard_path),
        "objectives": board.path(board.objectives_path),
        "plan": board.path(board.plan_path),
        "validator": board.path(board.validator_path),
        "generator": (
            ROOT / "scripts/generate_proof_carrying_semantic_minification_board.py"
        ),
        "operator": Path(__file__).resolve(),
    }


def _restart_static_config(config: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    try:
        normalized = json.loads(_canonical_bytes(config))
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise OperatorError(f"{label} config is not canonical JSON") from exc
    if not isinstance(normalized, dict):
        raise OperatorError(f"{label} config must be an object")
    source_binding = normalized.get("source_binding")
    if not isinstance(source_binding, dict):
        raise OperatorError(f"{label} config has no source_binding object")
    for field in _RESTART_ALLOWED_SOURCE_BINDING_FIELDS:
        source_binding.pop(field, None)
    normalized.pop("max_task_attempts", None)
    return normalized


def _verified_restart_forest_transition(
    bootstrap_forest: Any,
    current_forest: Mapping[str, Any],
    *,
    bootstrap_head: str,
    current_head: str,
) -> dict[str, Any]:
    if not isinstance(bootstrap_forest, Mapping):
        raise OperatorError("bootstrap source forest is absent")
    bootstrap_body = dict(bootstrap_forest)
    bootstrap_root = str(bootstrap_body.pop("source_forest_root", "") or "")
    if (
        set(bootstrap_body)
        != {"source_head", "nested_repositories", "cross_repository_writes"}
        or bootstrap_body.get("cross_repository_writes") is not True
        or re.fullmatch(r"sha256:[0-9a-f]{64}", bootstrap_root) is None
        or _identity(bootstrap_body) != bootstrap_root
        or bootstrap_body.get("source_head") != bootstrap_head
    ):
        raise OperatorError("bootstrap source forest identity is invalid")
    current_body = dict(current_forest)
    current_root = str(current_body.pop("source_forest_root", "") or "")
    if (
        set(current_body)
        != {"source_head", "nested_repositories", "cross_repository_writes"}
        or current_body.get("cross_repository_writes") is not True
        or re.fullmatch(r"sha256:[0-9a-f]{64}", current_root) is None
        or _identity(current_body) != current_root
        or current_body.get("source_head") != current_head
    ):
        raise OperatorError("current source forest identity is invalid")
    prior_items = bootstrap_forest.get("nested_repositories")
    current_items = current_forest.get("nested_repositories")
    if not isinstance(prior_items, list) or not isinstance(current_items, list):
        raise OperatorError("restart source forests have no nested repositories")
    if any(
        not isinstance(item, Mapping)
        or set(item) != _RESTART_SOURCE_FOREST_ENTRY_FIELDS
        for item in (*prior_items, *current_items)
    ):
        raise OperatorError("restart source forest entry is malformed")
    prior = {str(item.get("repository") or ""): item for item in prior_items}
    current = {str(item.get("repository") or ""): item for item in current_items}
    if (
        len(prior) != len(prior_items)
        or len(current) != len(current_items)
        or set(prior) != _RESTART_SOURCE_FOREST_REPOSITORIES
        or set(current) != _RESTART_SOURCE_FOREST_REPOSITORIES
    ):
        raise OperatorError("restart source forest repository set changed")
    transitions: list[dict[str, Any]] = []
    for repository_name in sorted(prior):
        older = prior[repository_name]
        newer = current[repository_name]
        if not isinstance(older, Mapping) or not isinstance(newer, Mapping):
            raise OperatorError("restart source forest entry is malformed")
        path = str(older.get("path") or "")
        if (
            path != str(newer.get("path") or "")
            or older.get("access") != newer.get("access")
        ):
            raise OperatorError(
                f"{repository_name} restart source authority changed"
            )
        nested = _safe_path(ROOT, path, field=f"{repository_name}.path")
        old_head = str(older.get("head") or "")
        new_head = str(newer.get("head") or "")
        old_tree = _git_commit_tree(
            old_head,
            field=f"{repository_name}.bootstrap_head",
            repository=nested,
        )
        new_tree = _git_commit_tree(
            new_head,
            field=f"{repository_name}.current_head",
            repository=nested,
        )
        if (
            old_tree != str(older.get("tree") or "")
            or new_tree != str(newer.get("tree") or "")
        ):
            raise OperatorError(f"{repository_name} restart tree binding changed")
        _git_is_ancestor(
            old_head,
            new_head,
            field=f"{repository_name} bootstrap-to-current lineage",
            repository=nested,
        )
        transitions.append(
            {
                "repository": repository_name,
                "path": path,
                "bootstrap_head": old_head,
                "bootstrap_tree": old_tree,
                "current_head": new_head,
                "current_tree": new_tree,
                "changed": old_head != new_head,
            }
        )
    return {
        "bootstrap_source_forest_root": bootstrap_root,
        "current_source_forest_root": current_root,
        "repositories": transitions,
    }


def _verified_handoff_repair(
    *,
    bootstrap_receipt_id: str,
    plan_root_cid: str,
    bootstrap_attempt_limit: int,
    current_attempt_limit: int,
    current_source_identities: Mapping[str, str],
    forest_transition: Mapping[str, Any],
    current_source_binding: Mapping[str, Any],
    current_head: str,
) -> dict[str, Any]:
    payload = _json_mapping_bytes(
        _tracked_bytes(HANDOFF_REPAIR_PATH, head=current_head),
        field="PCSM handoff repair receipt",
    )
    expected_fields = {
        "schema",
        "reason",
        "bootstrap_receipt_id",
        "plan_root_cid",
        "task_alias",
        "task_cid",
        "source_attempt",
        "source_completion_receipt_id",
        "max_task_attempts_before",
        "max_task_attempts_after",
        "current_authority_source_identities",
        "accelerate_origin_main_merge",
        "datasets_current_head_receipt",
        "validations",
        "historical_receipt_preserved",
        "manual_database_mutation",
        "receipt_id",
    }
    body = dict(payload)
    receipt_id = str(body.pop("receipt_id", "") or "")
    source_attempt = payload.get("source_attempt")
    datasets_receipt = payload.get("datasets_current_head_receipt")
    accelerate_merge = payload.get("accelerate_origin_main_merge")
    validations = payload.get("validations")
    listed_identities = payload.get("current_authority_source_identities")
    if (
        set(payload) != expected_fields
        or payload.get("schema") != HANDOFF_REPAIR_SCHEMA
        or payload.get("reason")
        != "pcsm_010_current_head_validation_handoff_repair"
        or payload.get("bootstrap_receipt_id") != bootstrap_receipt_id
        or payload.get("plan_root_cid") != plan_root_cid
        or payload.get("task_alias") != "PCSM-010"
        or payload.get("task_cid") != HANDOFF_REPAIR_TASK_CID
        or not isinstance(source_attempt, Mapping)
        or dict(source_attempt) != HANDOFF_REPAIR_SOURCE_ATTEMPT
        or any(
            type(source_attempt.get(field)) is not int
            for field in (
                "attempt_number",
                "fencing_token",
                "fence_epoch",
                "task_revision",
            )
        )
        or payload.get("source_completion_receipt_id")
        != HANDOFF_REPAIR_COMPLETION_RECEIPT_ID
        or type(payload.get("max_task_attempts_before")) is not int
        or type(payload.get("max_task_attempts_after")) is not int
        or payload.get("max_task_attempts_before") != bootstrap_attempt_limit
        or payload.get("max_task_attempts_after") != current_attempt_limit
        or bootstrap_attempt_limit != 1
        or current_attempt_limit != HANDOFF_REPAIR_MAX_TASK_ATTEMPTS
        or not isinstance(listed_identities, Mapping)
        or set(listed_identities) != _RESTART_REPAIR_SOURCE_NAMES
        or dict(listed_identities)
        != {
            name: current_source_identities[name]
            for name in sorted(_RESTART_REPAIR_SOURCE_NAMES)
        }
        or not isinstance(datasets_receipt, Mapping)
        or not isinstance(accelerate_merge, Mapping)
        or not isinstance(validations, list)
        or not validations
        or payload.get("historical_receipt_preserved") is not True
        or payload.get("manual_database_mutation") is not False
        or re.fullmatch(r"sha256:[0-9a-f]{64}", receipt_id) is None
        or _identity(body) != receipt_id
    ):
        raise OperatorError("PCSM handoff repair receipt is not admitted")
    observed_validations: set[tuple[str, tuple[str, ...]]] = set()
    for index, validation in enumerate(validations):
        if not isinstance(validation, Mapping) or set(validation) != {
            "cwd",
            "command",
            "outcome",
            "summary",
            "measurement_status",
        }:
            raise OperatorError(f"PCSM handoff validation {index} is malformed")
        command = validation.get("command")
        cwd = validation.get("cwd")
        if (
            not isinstance(cwd, str)
            or not cwd
            or not isinstance(command, list)
            or not command
            or any(not isinstance(item, str) or not item for item in command)
            or validation.get("outcome") != "passed"
            or validation.get("measurement_status") != "measured"
            or not isinstance(validation.get("summary"), str)
            or not validation.get("summary")
        ):
            raise OperatorError(f"PCSM handoff validation {index} is not passed")
        observed_validations.add((cwd, tuple(command)))
    if (
        len(observed_validations) != len(validations)
        or observed_validations != HANDOFF_REPAIR_REQUIRED_VALIDATIONS
    ):
        raise OperatorError("PCSM handoff validations are not the exact required set")

    transition_items = forest_transition.get("repositories")
    transition_fields = {
        "repository",
        "path",
        "bootstrap_head",
        "bootstrap_tree",
        "current_head",
        "current_tree",
        "changed",
    }
    if (
        not isinstance(transition_items, list)
        or any(
            not isinstance(item, Mapping) or set(item) != transition_fields
            for item in transition_items
        )
    ):
        raise OperatorError("PCSM handoff forest transition is malformed")
    dataset_transition = next(
        (
            item
            for item in transition_items
            if item.get("repository") == "ipfs_datasets"
        ),
        None,
    )
    accelerator_transition = next(
        (
            item
            for item in transition_items
            if item.get("repository") == "ipfs_accelerate"
        ),
        None,
    )
    changed_repositories = {
        str(item.get("repository") or "")
        for item in transition_items
        if item.get("changed") is True
    }
    if set(datasets_receipt) != {"path", "identity", "source_commit", "source_tree"}:
        raise OperatorError("PCSM datasets handoff receipt binding is not exact")
    receipt_path = str(datasets_receipt.get("path") or "")
    receipt_identity = str(datasets_receipt.get("identity") or "")
    if (
        not isinstance(dataset_transition, Mapping)
        or dataset_transition.get("changed") is not True
        or changed_repositories != {"ipfs_accelerate", "ipfs_datasets"}
        or receipt_path
        != "artifacts/proof_carrying_semantic_minification/handoff/"
        "datasets-proof-context-current-head.json"
    ):
        raise OperatorError("PCSM datasets handoff transition is not exact")
    if (
        not isinstance(accelerator_transition, Mapping)
        or accelerator_transition.get("changed") is not True
        or set(accelerate_merge)
        != {
            "bootstrap_commit",
            "origin_main_commit",
            "merged_commit",
            "merged_tree",
        }
        or accelerate_merge.get("bootstrap_commit")
        != accelerator_transition.get("bootstrap_head")
        or accelerate_merge.get("merged_commit")
        != accelerator_transition.get("current_head")
        or accelerate_merge.get("merged_tree")
        != accelerator_transition.get("current_tree")
        or accelerate_merge.get("origin_main_commit")
        != current_source_binding.get("ipfs_accelerate_origin_main_revision")
    ):
        raise OperatorError("PCSM accelerator origin/main transition is not exact")
    accelerator_repository = _safe_path(
        ROOT,
        str(accelerator_transition.get("path") or ""),
        field="accelerate_origin_main_merge.path",
    )
    _git_is_ancestor(
        accelerate_merge.get("origin_main_commit"),
        accelerate_merge.get("merged_commit"),
        field="accelerator origin/main merge lineage",
        repository=accelerator_repository,
    )
    merge_parents = subprocess.run(
        [
            "git",
            "show",
            "-s",
            "--format=%P",
            str(accelerate_merge.get("merged_commit") or ""),
        ],
        cwd=accelerator_repository,
        text=True,
        capture_output=True,
        check=False,
    )
    if (
        merge_parents.returncode != 0
        or set(merge_parents.stdout.strip().split())
        != {
            str(accelerate_merge.get("bootstrap_commit") or ""),
            str(accelerate_merge.get("origin_main_commit") or ""),
        }
    ):
        raise OperatorError("PCSM accelerator transition is not the exact merge")
    current_dataset_receipt = _safe_path(
        ROOT,
        receipt_path,
        field="datasets_current_head_receipt.path",
    )
    receipt_bytes = _tracked_bytes(current_dataset_receipt, head=current_head)
    receipt_body = _json_mapping_bytes(
        receipt_bytes,
        field="datasets current-head receipt",
    )
    receipt_source = receipt_body.get("source_binding")
    historical_receipt = receipt_body.get("historical_receipt")
    if (
        _identity(receipt_bytes) != receipt_identity
        or receipt_body.get("schema")
        != "lift_coding.proof-carrying-semantic-minification."
        "datasets-package-current-head@1"
        or receipt_body.get("status") != "qualified_current_head"
        or receipt_body.get("authority") != "composed_workspace_validation_only"
        or datasets_receipt.get("source_commit")
        != dataset_transition.get("current_head")
        or datasets_receipt.get("source_tree")
        != dataset_transition.get("current_tree")
        or not isinstance(receipt_source, Mapping)
        or receipt_source.get("repository") != "ipfs_datasets_py"
        or receipt_source.get("commit")
        != dataset_transition.get("current_head")
        or receipt_source.get("tree")
        != dataset_transition.get("current_tree")
        or receipt_source.get("origin_main_is_ancestor") is not True
        or receipt_source.get("origin_main_commit")
        != current_source_binding.get("ipfs_datasets_origin_main_revision")
        or not isinstance(historical_receipt, Mapping)
        or historical_receipt.get("preserved_unchanged") is not True
    ):
        raise OperatorError("PCSM datasets current-head receipt changed identity")
    return payload


def _owner_restart_admission(
    board: Any,
    config: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> dict[str, Any]:
    """Admit the exact bootstrap or one receipt-bound descendant repair."""

    current_head, current_tree = _assert_clean_current_tree(config)
    bootstrap = _json_object(paths["bootstrap_receipt"])
    if bootstrap.get("schema") != BOOTSTRAP_SCHEMA:
        raise OperatorError("owner restart bootstrap schema is not admitted")
    bootstrap_receipt_id = str(bootstrap.get("bootstrap_receipt_id") or "")
    bootstrap_body = dict(bootstrap)
    bootstrap_body.pop("bootstrap_receipt_id", None)
    if (
        re.fullmatch(r"sha256:[0-9a-f]{64}", bootstrap_receipt_id) is None
        or _identity(bootstrap_body) != bootstrap_receipt_id
    ):
        raise OperatorError("owner restart bootstrap receipt identity is invalid")
    bootstrap_head = str(bootstrap.get("source_head") or "")
    bootstrap_tree = str(bootstrap.get("repository_tree_id") or "")
    if _git_commit_tree(bootstrap_head, field="bootstrap source_head") != bootstrap_tree:
        raise OperatorError("bootstrap source tree does not match its commit")
    _git_is_ancestor(
        bootstrap_head,
        current_head,
        field="bootstrap-to-current source ancestry",
    )

    plan_root_cid = str(bootstrap.get("plan_root_cid") or "")
    database_receipt = bootstrap.get("database_task_source_receipt")
    if (
        not isinstance(database_receipt, Mapping)
        or database_receipt.get("schema") != DATABASE_TASK_SOURCE_SCHEMA
        or database_receipt.get("repository_tree_id") != bootstrap_tree
        or database_receipt.get("plan_root_cid") != plan_root_cid
    ):
        raise OperatorError("bootstrap database authority roots are inconsistent")
    task_cids_raw = database_receipt.get("task_cids")
    if not isinstance(task_cids_raw, list):
        raise OperatorError("bootstrap database task identities are absent")
    if any(not isinstance(item, str) or not item for item in task_cids_raw):
        raise OperatorError("bootstrap database task identities are invalid")
    task_cids = tuple(task_cids_raw)
    database_task_count = _exact_int(
        database_receipt.get("task_count"),
        field="bootstrap database task_count",
        minimum=1,
    )
    database_goal_count = _exact_int(
        database_receipt.get("goal_count"),
        field="bootstrap database goal_count",
        minimum=1,
    )
    database_plan_count = _exact_int(
        database_receipt.get("plan_count"),
        field="bootstrap database plan_count",
        minimum=1,
    )
    if (
        len(set(task_cids)) != len(task_cids)
        or database_task_count != len(task_cids)
    ):
        raise OperatorError("bootstrap database task identities are invalid")

    source_identities = bootstrap.get("source_identities")
    source_paths = _restart_source_paths(board)
    if (
        not isinstance(source_identities, Mapping)
        or set(source_identities) != set(source_paths)
    ):
        raise OperatorError("bootstrap source identity key set is not exact")
    bootstrap_sources: dict[str, bytes] = {}
    current_sources: dict[str, bytes] = {}
    current_source_identities: dict[str, str] = {}
    for name, path in source_paths.items():
        expected = str(source_identities.get(name) or "")
        bootstrap_bytes = _git_blob_at(
            head=bootstrap_head,
            path=path,
            field=f"bootstrap {name}",
        )
        if (
            re.fullmatch(r"sha256:[0-9a-f]{64}", expected) is None
            or _identity(bootstrap_bytes) != expected
        ):
            raise OperatorError(f"bootstrap {name} bytes differ from their seal")
        current_bytes = _tracked_bytes(path, head=current_head)
        if name in _RESTART_IMMUTABLE_SOURCE_NAMES and _identity(current_bytes) != expected:
            raise OperatorError(f"current {name} bytes differ from bootstrap")
        bootstrap_sources[name] = bootstrap_bytes
        current_sources[name] = current_bytes
        current_source_identities[name] = _identity(current_bytes)

    bootstrap_config = _json_mapping_bytes(
        bootstrap_sources["config"],
        field="bootstrap config",
    )
    current_config = _json_mapping_bytes(
        current_sources["config"],
        field="current config",
    )
    if _canonical_bytes(current_config) != _canonical_bytes(config):
        raise OperatorError("loaded config differs from tracked current config")
    if _canonical_bytes(
        _restart_static_config(bootstrap_config, label="bootstrap")
    ) != _canonical_bytes(_restart_static_config(current_config, label="current")):
        raise OperatorError(
            "current config changes fields outside the admitted accelerator/datasets "
            "bindings and retry policy"
        )
    bootstrap_attempt_limit = _exact_int(
        bootstrap_config.get("max_task_attempts"),
        field="bootstrap max_task_attempts",
        minimum=1,
    )
    current_attempt_limit = _exact_int(
        current_config.get("max_task_attempts"),
        field="current max_task_attempts",
        minimum=1,
    )
    current_forest = _source_forest(current_config, head=current_head)
    forest_transition = _verified_restart_forest_transition(
        bootstrap.get("source_forest"),
        current_forest,
        bootstrap_head=bootstrap_head,
        current_head=current_head,
    )
    exact_bootstrap = (
        current_head == bootstrap_head
        and current_tree == bootstrap_tree
        and current_attempt_limit == bootstrap_attempt_limit
        and all(
            current_source_identities[name] == str(source_identities[name])
            for name in source_paths
        )
    )
    repair: dict[str, Any] = {}
    if not exact_bootstrap:
        current_source_binding = current_config.get("source_binding")
        if not isinstance(current_source_binding, Mapping):
            raise OperatorError("current source_binding is absent")
        repair = _verified_handoff_repair(
            bootstrap_receipt_id=bootstrap_receipt_id,
            plan_root_cid=plan_root_cid,
            bootstrap_attempt_limit=bootstrap_attempt_limit,
            current_attempt_limit=current_attempt_limit,
            current_source_identities=current_source_identities,
            forest_transition=forest_transition,
            current_source_binding=current_source_binding,
            current_head=current_head,
        )
    admission: dict[str, Any] = {
        "schema": OWNER_RESTART_ADMISSION_SCHEMA,
        "mode": "exact_bootstrap" if exact_bootstrap else "verified_handoff_repair",
        "bootstrap_receipt_id": bootstrap_receipt_id,
        "bootstrap_source_head": bootstrap_head,
        "bootstrap_source_tree": bootstrap_tree,
        "current_source_head": current_head,
        "current_source_tree": current_tree,
        "plan_root_cid": plan_root_cid,
        "max_task_attempts_before": bootstrap_attempt_limit,
        "max_task_attempts_after": current_attempt_limit,
        "source_identities": current_source_identities,
        "forest_transition": forest_transition,
        "handoff_repair_receipt_id": str(repair.get("receipt_id") or ""),
        "handoff_repair": repair,
        "database_authority": {
            "receipt_identity": _identity(database_receipt),
            "schema": DATABASE_TASK_SOURCE_SCHEMA,
            "repository_tree_id": bootstrap_tree,
            "source_head": bootstrap_head,
            "plan_root_cid": plan_root_cid,
            "projection_cid": str(database_receipt.get("projection_cid") or ""),
            "task_cids": sorted(task_cids),
            "task_count": len(task_cids),
            "goal_count": database_goal_count,
            "plan_count": database_plan_count,
        },
    }
    admission["admission_id"] = _identity(admission)
    return admission


def _source_forest(config: Mapping[str, Any], *, head: str) -> dict[str, Any]:
    """Verify the exact clean four-repository PCSM source forest."""

    binding = config.get("source_binding")
    if not isinstance(binding, Mapping):
        raise OperatorError("source_binding must be an object")
    if binding.get("require_origin_main_as_ancestor") is not True:
        raise OperatorError("source forest requires origin/main ancestry")
    nested: list[dict[str, str]] = []
    configured_repositories = (
        (
            "ipfs_accelerate",
            ("ipfs_accelerate_submodule_path",),
            ("ipfs_accelerate_planning_revision",),
            ("ipfs_accelerate_planning_tree",),
            ("ipfs_accelerate_origin_main_revision",),
        ),
        (
            "ipfs_datasets",
            ("ipfs_datasets_submodule_path", "datasets_submodule_path"),
            ("ipfs_datasets_planning_revision", "datasets_planning_revision"),
            ("ipfs_datasets_planning_tree", "datasets_planning_tree"),
            ("ipfs_datasets_origin_main_revision",),
        ),
        (
            "ipfs_kit",
            ("ipfs_kit_submodule_path", "kit_submodule_path"),
            ("ipfs_kit_planning_revision", "kit_planning_revision"),
            ("ipfs_kit_planning_tree", "kit_planning_tree"),
            ("ipfs_kit_origin_main_revision",),
        ),
        (
            "mcp_plus_plus",
            ("mcp_plus_plus_submodule_path",),
            ("mcp_plus_plus_planning_revision",),
            ("mcp_plus_plus_planning_tree",),
            ("mcp_plus_plus_origin_main_revision",),
        ),
    )

    def binding_value(fields: Sequence[str], *, field: str) -> Any:
        present = [binding.get(name) for name in fields if binding.get(name) not in (None, "")]
        if not present:
            return None
        if any(value != present[0] for value in present[1:]):
            raise OperatorError(f"{field} has conflicting canonical and legacy values")
        return present[0]

    for (
        prefix,
        path_fields,
        revision_fields,
        tree_fields,
        origin_fields,
    ) in configured_repositories:
        raw_path = binding_value(
            path_fields,
            field=f"source_binding.{prefix}_submodule_path",
        )
        raw_revision = binding_value(
            revision_fields,
            field=f"source_binding.{prefix}_planning_revision",
        )
        raw_tree = binding_value(
            tree_fields,
            field=f"source_binding.{prefix}_planning_tree",
        )
        raw_origin = binding_value(
            origin_fields,
            field=f"source_binding.{prefix}_origin_main_revision",
        )
        if any(value in (None, "") for value in (raw_path, raw_revision, raw_tree, raw_origin)):
            raise OperatorError(f"{prefix} source binding is incomplete")
        nested_path = _safe_path(
            ROOT,
            raw_path,
            field=f"source_binding.{prefix}_submodule_path",
        )
        if not nested_path.is_dir():
            raise OperatorError(f"{prefix} submodule is not initialized")
        nested_status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=nested_path,
            text=True,
            capture_output=True,
            check=False,
        )
        if nested_status.returncode != 0 or nested_status.stdout.strip():
            raise OperatorError(f"{prefix} nested worktree is not clean")
        nested_head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=nested_path,
            text=True,
            capture_output=True,
            check=False,
        )
        nested_tree = subprocess.run(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=nested_path,
            text=True,
            capture_output=True,
            check=False,
        )
        revision = nested_head.stdout.strip()
        tree = nested_tree.stdout.strip()
        if (
            nested_head.returncode != 0
            or nested_tree.returncode != 0
            or revision != str(raw_revision)
            or tree != str(raw_tree)
        ):
            raise OperatorError(f"{prefix} nested revision differs from its seal")
        origin_main = subprocess.run(
            ["git", "rev-parse", "origin/main"],
            cwd=nested_path,
            text=True,
            capture_output=True,
            check=False,
        )
        if (
            origin_main.returncode != 0
            or origin_main.stdout.strip() != str(raw_origin)
        ):
            raise OperatorError(
                f"{prefix} configured origin/main differs from its fetched ref"
            )
        _git_is_ancestor(
            raw_origin,
            revision,
            field=f"{prefix} origin/main-to-planning lineage",
            repository=nested_path,
        )
        relative = nested_path.relative_to(ROOT).as_posix()
        tree_row = str(_git("ls-tree", head, "--", relative)).strip().split()
        if (
            len(tree_row) < 3
            or tree_row[0] != "160000"
            or tree_row[1] != "commit"
            or tree_row[2] != revision
        ):
            raise OperatorError(f"{prefix} gitlink differs from its nested HEAD")
        nested.append(
            {
                "repository": prefix,
                "path": relative,
                "head": revision,
                "tree": tree,
                "access": "supervisor_scoped_cross_repository_worktree",
            }
        )
    if {item["repository"] for item in nested} != _RESTART_SOURCE_FOREST_REPOSITORIES:
        raise OperatorError("source forest does not contain the exact four repositories")
    result: dict[str, Any] = {
        "source_head": head,
        "nested_repositories": nested,
        "cross_repository_writes": True,
    }
    result["source_forest_root"] = _identity(result)
    return result


def _load_config(config_path: Path) -> tuple[Any, dict[str, Any]]:
    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        load_configured_board,
    )

    board = load_configured_board(config_path, repo_root=ROOT)
    payload = dict(board.payload)
    if board.task_prefix.removeprefix("## ") != "PCSM-":
        raise OperatorError("PCSM operator requires task_prefix='PCSM-'")
    if board.board_namespace != "proof-carrying-semantic-minification-v1":
        raise OperatorError("scheduler board_namespace is not the PCSM v1 namespace")
    program = board.resolved_database_program()
    if program.authority_mode != "quack" or program.task_source_kind != "duckdb":
        raise OperatorError("PCSM requires DuckDB task authority served through Quack")
    if program.failover_policy != "fail_closed":
        raise OperatorError("PCSM Quack authority must fail closed")
    if QUACK_ENDPOINT_RE.fullmatch(program.quack_endpoint) is None:
        raise OperatorError("PCSM Quack endpoint must be a bounded loopback URI")
    return board, payload


def _control_plane_store_id(program: Any) -> str:
    """Return the compact transactional identity, not the database pathname."""

    value = str(program.store_generation or "").strip()
    if not value or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,255}", value) is None:
        raise OperatorError("database program has no compact control-plane store identity")
    return value


def _run_board_validator(board: Any) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, str(board.path(board.validator_path)), "--check-all"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                item
                for item in (
                    str(ACCEL_ROOT),
                    str(ROOT),
                    os.environ.get("PYTHONPATH", ""),
                )
                if item
            ),
        },
    )
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise OperatorError("PCSM board validator did not return JSON") from exc
    if (
        completed.returncode != 0
        or not isinstance(payload, dict)
        or payload.get("valid") is not True
    ):
        raise OperatorError("PCSM board validator rejected the committed handoff")
    return payload


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _goal_blocks(text: str) -> list[tuple[str, str, dict[str, str]]]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.todo_vector_index import (
        normalize_metadata_key,
    )

    matches = list(GOAL_RE.finditer(text))
    result: list[tuple[str, str, dict[str, str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        fields: dict[str, str] = {}
        for line in text[match.end() : end].splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ":" not in stripped:
                continue
            key, value = stripped[2:].split(":", 1)
            normalized = normalize_metadata_key(key)
            if normalized in fields:
                raise OperatorError(
                    f"{match.group(1)} contains duplicate metadata field {normalized}"
                )
            fields[normalized] = value.strip()
        result.append((match.group(1), match.group(2).strip(), fields))
    return result


def _population(board: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.todo_vector_index import (
        parse_todo_blocks,
    )
    from ipfs_accelerate_py.agent_supervisor.validation.validation_commands import (
        split_validation_commands,
    )

    head, tree = _assert_clean_current_tree(config)
    source_forest = _source_forest(config, head=head)
    sources = {
        "config": _tracked_bytes(board.config_path, head=head),
        "taskboard": _tracked_bytes(board.path(board.taskboard_path), head=head),
        "objectives": _tracked_bytes(board.path(board.objectives_path), head=head),
        "plan": _tracked_bytes(board.path(board.plan_path), head=head),
        "validator": _tracked_bytes(board.path(board.validator_path), head=head),
        "generator": _tracked_bytes(
            ROOT / "scripts/generate_proof_carrying_semantic_minification_board.py",
            head=head,
        ),
        "operator": _tracked_bytes(Path(__file__).resolve(), head=head),
    }
    plan_root = content_identity(
        {
            "schema": "pcsm-plan-root@1",
            "source_head": head,
            "repository_tree_id": tree,
            "sources": {
                name: _identity(value) for name, value in sorted(sources.items())
            },
        }
    )

    objective_text = sources["objectives"].decode("utf-8")
    parsed_goals = _goal_blocks(objective_text)
    if not parsed_goals or parsed_goals[0][0] != "PCSM-G000":
        raise OperatorError("objectives must begin with root PCSM-G000")
    if len({item[0] for item in parsed_goals}) != len(parsed_goals):
        raise OperatorError("objectives contain duplicate goal IDs")
    goal_cids = {
        goal_id: content_identity(
            {
                "goal_id": goal_id,
                "title": title,
                "metadata": fields,
                "plan_root_cid": plan_root,
            }
        )
        for goal_id, title, fields in parsed_goals
    }
    goals: list[dict[str, Any]] = []
    goal_edges: list[dict[str, Any]] = []
    observed_goals: set[str] = set()
    for ordinal, (goal_id, title, fields) in enumerate(parsed_goals, start=1):
        parent = str(fields.get("parent") or "").strip()
        if parent and parent not in observed_goals:
            raise OperatorError(f"{goal_id} parent must precede it: {parent}")
        dependencies = _split_csv(fields.get("depends_on"))
        unknown = [item for item in dependencies if item not in goal_cids]
        if unknown:
            raise OperatorError(f"{goal_id} has unknown goal dependencies: {unknown}")
        goal = {
            "goal_cid": goal_cids[goal_id],
            "goal_id": goal_id,
            "goal_alias": goal_id,
            "title": title,
            "ordinal": ordinal,
            "status": str(fields.get("status") or "open").lower(),
            "objective_id": "objective:pcsm-root" if goal_id == "PCSM-G000" else "",
            "objective_alias": "PCSM-G000",
            "priority": str(fields.get("priority") or "P0"),
            "body": dict(fields),
        }
        if parent:
            goal["parent_goal_cid"] = goal_cids[parent]
            goal_edges.append(
                {
                    "parent_goal_cid": goal_cids[parent],
                    "child_goal_cid": goal_cids[goal_id],
                    "edge_kind": "goal_parent",
                }
            )
        for dependency in dependencies:
            goal_edges.append(
                {
                    "parent_goal_cid": goal_cids[dependency],
                    "child_goal_cid": goal_cids[goal_id],
                    "edge_kind": "goal_dependency",
                }
            )
        goals.append(goal)
        observed_goals.add(goal_id)

    task_text = sources["taskboard"].decode("utf-8")
    parsed_tasks = parse_todo_blocks(task_text, task_header_prefix="## PCSM-")
    if not parsed_tasks:
        raise OperatorError("task board contains no PCSM tasks")
    task_ids = [item[0] for item in parsed_tasks]
    if len(task_ids) != len(set(task_ids)):
        raise OperatorError("task board contains duplicate PCSM task IDs")
    task_cids = {
        task_id: content_identity(
            {
                "task_id": task_id,
                "title": title,
                "source_line": source_line,
                "metadata": fields,
                "plan_root_cid": plan_root,
                "repository_tree_id": tree,
            }
        )
        for task_id, title, source_line, fields in parsed_tasks
    }
    tasks: list[dict[str, Any]] = []
    observed_tasks: set[str] = set()
    for ordinal, (task_id, title, source_line, fields) in enumerate(
        parsed_tasks, start=1
    ):
        dependencies = _split_csv(fields.get("depends_on"))
        unknown = [item for item in dependencies if item not in task_cids]
        if unknown:
            raise OperatorError(f"{task_id} has unknown dependencies: {unknown}")
        future = [item for item in dependencies if item not in observed_tasks]
        if future:
            raise OperatorError(
                f"{task_id} dependencies must precede it for atomic ingestion: {future}"
            )
        goal_id = str(
            fields.get("subgoal_id")
            or fields.get("goal_id")
            or fields.get("goal")
            or "PCSM-G000"
        ).strip()
        if goal_id not in goal_cids:
            raise OperatorError(f"{task_id} refers to unknown goal {goal_id}")
        output_paths = _split_csv(fields.get("outputs") or fields.get("predicted_files"))
        task = dict(fields)
        if fields.get("owning_repository") != "ipfs_accelerate_py":
            raise OperatorError(
                f"{task_id} does not use the sealed Portal root execution authority"
            )
        task.update(
            {
                "task_cid": task_cids[task_id],
                "task_id": task_id,
                "task_alias": task_id,
                "title": title,
                "source_line": source_line,
                "goal_cid": goal_cids[goal_id],
                "goal_id": goal_id,
                "plan_cid": plan_root,
                "objective_id": "objective:pcsm-root",
                "ordinal": ordinal,
                "status": str(fields.get("status") or "todo").lower(),
                "priority": str(fields.get("priority") or "P1"),
                "dependencies": [task_cids[item] for item in dependencies],
                "depends_on": [task_cids[item] for item in dependencies],
                "outputs": [
                    {
                        "path": path,
                        "effect_id": content_identity(
                            {"task_cid": task_cids[task_id], "path": path}
                        ),
                    }
                    for path in output_paths
                ],
                "acceptance": [
                    str(fields.get("acceptance") or fields.get("acceptance_subset") or "")
                ],
                "validations": list(
                    split_validation_commands(str(fields.get("validation") or ""))
                ),
                "accepted_plan_root_cid": plan_root,
                "base_revision": head,
                "base_repository_tree_id": tree,
                # PCSM task paths and receipts are outer-root-relative and may
                # span several configured submodules. DatabasePortalBridge's
                # owner is the execution worktree scope; semantic authority is
                # governed independently by the sealed campaign plan.
                "owning_repository": "ipfs_accelerate_py",
            }
        )
        tasks.append(task)
        observed_tasks.add(task_id)

    projection = config.get("initial_projection")
    projection = projection if isinstance(projection, Mapping) else {}
    expected_tasks = projection.get("task_count")
    expected_goals = projection.get("goal_count")
    expected_dependencies = projection.get("task_dependency_count")
    if expected_tasks is not None and int(expected_tasks) != len(tasks):
        raise OperatorError("task count differs from configured initial projection")
    if expected_goals is not None and int(expected_goals) != len(goals):
        raise OperatorError("goal count differs from configured initial projection")
    dependency_count = sum(
        len(_split_csv(item[3].get("depends_on"))) for item in parsed_tasks
    )
    if expected_dependencies is not None and int(expected_dependencies) != dependency_count:
        raise OperatorError(
            "task dependency count differs from configured initial projection"
        )
    return {
        "schema": POPULATION_SCHEMA,
        "repository_tree_id": tree,
        "source_head": head,
        "plan_root_cid": plan_root,
        "source_identities": {
            name: _identity(value) for name, value in sorted(sources.items())
        },
        "source_forest": source_forest,
        "objectives": goals,
        "goal_edges": goal_edges,
        "plans": [
            {
                "plan_cid": plan_root,
                "plan_alias": "PCSM-PLAN-V1",
                "goal_cid": goal_cids["PCSM-G000"],
                "status": "active",
                "source_head": head,
                "repository_tree_id": tree,
            }
        ],
        "tasks": tasks,
        "task_cids_by_alias": task_cids,
        "goal_cids_by_alias": goal_cids,
    }


def _runtime_paths(board: Any) -> dict[str, Path]:
    program = board.resolved_database_program()
    database = _safe_path(ROOT, program.store_id, field="database_program.store_id")
    runtime = board.path(board.runtime_paths["root"])
    try:
        database.relative_to(runtime)
    except ValueError as exc:
        raise OperatorError("DuckDB authority store must be below runtime_paths.root") from exc
    raw_runtime = board.payload.get("runtime_paths")
    raw_runtime = raw_runtime if isinstance(raw_runtime, Mapping) else {}
    evidence = _safe_path(
        ROOT,
        raw_runtime.get("evidence") or runtime.relative_to(ROOT) / "evidence",
        field="runtime_paths.evidence",
    )
    owner = _safe_path(
        ROOT,
        raw_runtime.get("quack_owner") or runtime.relative_to(ROOT) / "quack-owner",
        field="runtime_paths.quack_owner",
    )
    raw_ducklake = board.payload.get("ducklake_projection_program")
    raw_ducklake = raw_ducklake if isinstance(raw_ducklake, Mapping) else {}
    ducklake_catalog = _safe_path(
        ROOT,
        raw_ducklake.get("catalog_path")
        or runtime.relative_to(ROOT) / "ducklake" / "catalog.duckdb",
        field="ducklake_projection_program.catalog_path",
    )
    ducklake_data = _safe_path(
        ROOT,
        raw_ducklake.get("data_path")
        or runtime.relative_to(ROOT) / "ducklake" / "data",
        field="ducklake_projection_program.data_path",
    )
    for label, path in (
        ("evidence", evidence),
        ("quack_owner", owner),
        ("ducklake_catalog", ducklake_catalog),
        ("ducklake_data", ducklake_data),
    ):
        try:
            path.relative_to(runtime)
        except ValueError as exc:
            raise OperatorError(f"{label} must be below runtime_paths.root") from exc
    return {
        "runtime": runtime,
        "database": database,
        "owner": owner,
        "bootstrap_receipt": evidence / "bootstrap" / BOOTSTRAP_RECEIPT_NAME,
        "ducklake_receipt": evidence / "bootstrap" / DUCKLAKE_RECEIPT_NAME,
        "ducklake_catalog": ducklake_catalog,
        "ducklake_data": ducklake_data,
    }


def _ducklake_projection(
    *,
    paths: Mapping[str, Path],
    population: Mapping[str, Any],
    control_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Append one non-authoritative bootstrap observation to DuckLake."""

    projection: dict[str, Any] = {
        "schema": DUCKLAKE_SCHEMA,
        "authoritative": False,
        "scheduler_gate": False,
        "completion_gate": False,
        "status": "unavailable",
        "reason_code": "ducklake_projection_unavailable",
        "source_head": str(population["source_head"]),
        "repository_tree_id": str(population["repository_tree_id"]),
        "plan_root_cid": str(population["plan_root_cid"]),
    }
    try:
        import duckdb

        catalog = paths["ducklake_catalog"]
        data_path = paths["ducklake_data"]
        catalog.parent.mkdir(parents=True, exist_ok=True)
        data_path.mkdir(parents=True, exist_ok=True)
        memory = duckdb.connect(":memory:")
        try:
            memory.execute("LOAD ducklake")
            catalog_sql = str(catalog).replace("'", "''")
            data_sql = str(data_path).replace("'", "''")
            memory.execute(
                f"ATTACH 'ducklake:{catalog_sql}' AS pcsm_history "
                f"(DATA_PATH '{data_sql}')"
            )
            memory.execute(
                """
                CREATE TABLE IF NOT EXISTS pcsm_history.bootstrap_history (
                    event_id VARCHAR,
                    observed_at_epoch DOUBLE,
                    source_head VARCHAR,
                    repository_tree_id VARCHAR,
                    plan_root_cid VARCHAR,
                    projection_cid VARCHAR,
                    task_count BIGINT,
                    goal_count BIGINT,
                    body_json VARCHAR
                )
                """
            )
            event_id = _identity(
                {
                    "source_head": population["source_head"],
                    "plan_root_cid": population["plan_root_cid"],
                    "projection_cid": control_receipt.get("projection_cid"),
                }
            )
            existing = memory.execute(
                "SELECT COUNT(*) FROM pcsm_history.bootstrap_history WHERE event_id = ?",
                [event_id],
            ).fetchone()
            if existing is None or int(existing[0]) == 0:
                memory.execute(
                    """
                    INSERT INTO pcsm_history.bootstrap_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        event_id,
                        time.time(),
                        population["source_head"],
                        population["repository_tree_id"],
                        population["plan_root_cid"],
                        str(control_receipt.get("projection_cid") or ""),
                        int(control_receipt.get("task_count") or 0),
                        int(control_receipt.get("goal_count") or 0),
                        json.dumps(
                            {
                                "authority": "DuckDB/DatabaseTaskSource@1",
                                "transport": "QuackStateServer@1",
                                "projection": "DuckLake/non-authoritative",
                            },
                            sort_keys=True,
                        ),
                    ],
                )
            row_count = int(
                memory.execute(
                    "SELECT COUNT(*) FROM pcsm_history.bootstrap_history"
                ).fetchone()[0]
            )
            memory.execute("DETACH pcsm_history")
        finally:
            memory.close()
        projection.update(
            {
                "status": "available",
                "reason_code": "",
                "event_id": event_id,
                "row_count": row_count,
                "catalog_path": str(catalog.relative_to(ROOT)),
                "data_path": str(data_path.relative_to(ROOT)),
            }
        )
    except Exception as exc:
        # This projection is optional by contract. Preserve a typed absence and
        # never use it to reject a valid DuckDB materialization.
        projection["error_class"] = type(exc).__name__
    projection["projection_receipt_id"] = _identity(projection)
    _atomic_json(paths["ducklake_receipt"], projection)
    return projection


def materialize(config_path: Path) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    board, config = _load_config(config_path)
    board_validation = _run_board_validator(board)
    paths = _runtime_paths(board)
    population = _population(board, config)
    receipt_path = paths["bootstrap_receipt"]
    if paths["database"].exists() or receipt_path.exists():
        if not paths["database"].is_file() or not receipt_path.is_file():
            raise OperatorError("partial bootstrap state exists; operator review required")
        prior = _json_object(receipt_path)
        exact = all(
            prior.get(key) == population.get(key)
            for key in ("source_head", "repository_tree_id", "plan_root_cid")
        )
        if not exact:
            raise OperatorError(
                "existing DuckDB authority is bound to a different source tree or plan"
            )
        with DatabaseTaskSource(
            paths["database"],
            owner_id="pcsm-bootstrap:verify-existing",
            install_schema=False,
            repository_tree_id=str(population["repository_tree_id"]),
            plan_root_cid=str(population["plan_root_cid"]),
        ) as source:
            snapshot = source.snapshot().to_dict()
        if int(snapshot["task_count"]) != len(population["tasks"]):
            raise OperatorError("existing DuckDB task population differs from sealed board")
        return {
            "schema": OPERATOR_SCHEMA,
            "command": "materialize",
            "idempotent_replay": True,
            "materialized": True,
            "bootstrap_receipt": prior,
            "snapshot": snapshot,
            "board_validation": board_validation,
        }

    _ensure_private_runtime_directory(paths["runtime"])
    with DatabaseTaskSource(
        paths["database"],
        owner_id="pcsm-bootstrap:single-writer",
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        control_receipt = dict(source.materialize(population))
        snapshot = source.snapshot().to_dict()
        ready_ids = [item.task_alias for item in source.ready_tasks(limit=100).tasks]
    if int(snapshot["task_count"]) != len(population["tasks"]):
        raise OperatorError("DuckDB materialization task count is not exact")
    if int(snapshot["goal_count"]) != len(population["objectives"]):
        raise OperatorError("DuckDB materialization goal count is not exact")
    projection = config.get("initial_projection")
    projection = projection if isinstance(projection, Mapping) else {}
    expected_ready = [str(item) for item in projection.get("ready_task_ids", ())]
    if ready_ids != expected_ready:
        raise OperatorError(
            "initial DuckDB readiness frontier differs from the sealed projection"
        )
    ducklake = _ducklake_projection(
        paths=paths,
        population=population,
        control_receipt=control_receipt,
    )
    receipt = {
        "schema": BOOTSTRAP_SCHEMA,
        "source_head": population["source_head"],
        "repository_tree_id": population["repository_tree_id"],
        "plan_root_cid": population["plan_root_cid"],
        "source_identities": population["source_identities"],
        "source_forest": population["source_forest"],
        "database_task_source_receipt": control_receipt,
        "projection_cid": snapshot["projection_cid"],
        "task_count": snapshot["task_count"],
        "goal_count": snapshot["goal_count"],
        "dependency_count": snapshot["dependency_count"],
        "initial_ready_task_ids": ready_ids,
        "board_validation": board_validation,
        "authority": {
            "semantic_state": "DuckDB/DatabaseTaskSource@1",
            "state_owner_transport": "QuackStateServer@1",
            "ducklake": "optional_non_authoritative_history_projection",
        },
        "ducklake_projection": ducklake,
    }
    receipt["bootstrap_receipt_id"] = _identity(receipt)
    _atomic_json(receipt_path, receipt)
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "materialize",
        "idempotent_replay": False,
        "materialized": True,
        "bootstrap_receipt": receipt,
        "snapshot": snapshot,
    }


def _verify_control_plane(path: Path) -> Any:
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_migrations import (
        MigrationRunReport,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_schema import (
        CONTROL_PLANE_MIGRATION_VERSION,
        load_control_plane_catalog,
        verify_installed_schema,
    )

    # PCSM uses the canonical full control-plane schema revision ``1``.  The
    # smaller datasets-authoritative operational profile is deliberately not
    # selected: the generic multi-supervisor rejects that profile for live
    # Quack operation, and the PCSM board needs the full proof/evidence tables.
    verification = verify_installed_schema(path)
    fingerprint = str(verification.get("schema_fingerprint") or "")
    if not fingerprint:
        raise OperatorError("existing full control plane has no schema fingerprint")
    return MigrationRunReport(
        from_version=CONTROL_PLANE_MIGRATION_VERSION,
        to_version=CONTROL_PLANE_MIGRATION_VERSION,
        receipts=(),
        schema_fingerprint=fingerprint,
        catalog_fingerprint=load_control_plane_catalog().fingerprint(),
        changed=False,
    )


def _normalized_owner_dml(sql: str) -> str:
    normalized = " ".join(str(sql or "").strip().upper().split())
    if not normalized.startswith(OWNER_DML_PREFIXES):
        raise OperatorError("mutation inbox accepts only the closed owner-DML vocabulary")
    if ";" in normalized.rstrip(";"):
        raise OperatorError("mutation inbox accepts exactly one SQL statement")
    return normalized


def _process_mutations(server: Any, mutation_dir: Path) -> None:
    mutation_dir.mkdir(parents=True, exist_ok=True)
    for request in sorted(mutation_dir.glob("*.request.json")):
        done = request.with_name(request.name.replace(".request.json", ".done.json"))
        try:
            try:
                payload = json.loads(request.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                # The client creates a tiny same-filesystem request. A partial
                # read is retried rather than converted into a false failure.
                continue
            if not isinstance(payload, Mapping):
                raise OperatorError("mutation request must be an object")
            sql = str(payload.get("sql") or "")
            _normalized_owner_dml(sql)
            parameters = payload.get("parameters")
            if parameters is not None and (
                isinstance(parameters, (str, bytes, bytearray))
                or not isinstance(parameters, (Mapping, Sequence))
            ):
                raise OperatorError("mutation parameters must be a mapping or sequence")
            owner_connection = getattr(server, "_connection", None)
            if owner_connection is None:
                raise OperatorError("state-owner connection is unavailable")
            result = (
                owner_connection.execute(sql)
                if parameters is None
                else owner_connection.execute(sql, parameters)
            )
            rowcount = -1
            try:
                if getattr(result, "description", None):
                    result.fetchall()
                elif hasattr(result, "rowcount"):
                    rowcount = int(result.rowcount)
            except Exception:
                pass
            _atomic_json(done, {"ok": True, "rowcount": rowcount})
        except Exception as exc:
            _atomic_json(
                done,
                {
                    "ok": False,
                    "error": f"{type(exc).__name__}: mutation rejected",
                },
            )
        try:
            request.unlink()
        except FileNotFoundError:
            pass


def _build_state_owner(board: Any, paths: Mapping[str, Path]) -> Any:
    """Build the canonical writer-owner/read-replica Quack boundary."""

    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        build_server,
    )

    program = board.resolved_database_program()
    endpoint = QUACK_ENDPOINT_RE.fullmatch(program.quack_endpoint)
    if endpoint is None:
        raise OperatorError("configured Quack endpoint is not loopback")
    host = endpoint.group(1)
    port = int(endpoint.group(2))
    if not 1 <= port <= 65535:
        raise OperatorError("configured Quack port is out of range")
    return build_server(
        database_path=paths["database"],
        state_dir=paths["owner"],
        repository_root=ROOT,
        host=host,
        port=port,
        repository_id=(
            "repository:lift_coding/proof-carrying-semantic-minification-v1"
        ),
        store_id=_control_plane_store_id(program),
        secret_handle=program.endpoint_secret_handle,
        allow_experimental=False,
        migrate=_verify_control_plane,
        allow_legacy_board_unstall=False,
    )


def state_owner(config_path: Path) -> int:
    from ipfs_accelerate_py.agent_supervisor.runtime.quack_state_server import (
        ServerLifecycle,
    )

    board, config = _load_config(config_path)
    paths = _runtime_paths(board)
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise OperatorError("materialize the sealed PCSM board before starting Quack")
    restart_admission = _owner_restart_admission(board, config, paths)
    prior_owner = _owner_restart_prior_status(
        paths["owner"] / "quack-state-server.status.json"
    )
    _require_prior_owner_continuity(restart_admission, prior_owner)
    server = _build_state_owner(board, paths)
    try:
        identity = server.start()
        ready = server.ready()
        route_policy_provider = _ExecutionRoutePolicyProvider(
            server=server,
            board=board,
            restart_admission=restart_admission,
        )
        route_policy_provider.seal()
        after_head, after_tree = _assert_clean_current_tree(config)
        if (
            after_head != restart_admission["current_source_head"]
            or after_tree != restart_admission["current_source_tree"]
        ):
            raise OperatorError("owner restart source changed during admission")
        restart_receipt = _owner_restart_receipt(
            restart_admission,
            identity,
            expected_store_id=_control_plane_store_id(
                board.resolved_database_program()
            ),
            prior_owner=prior_owner,
            database_verification=route_policy_provider.database_verification,
        )
        restart_receipt_path = (
            paths["runtime"]
            / "evidence"
            / "runtime"
            / "owner-restarts"
            / (
                f"{int(identity.generation):020d}-"
                f"{restart_receipt['receipt_id'].removeprefix('sha256:')}.json"
            )
        )
        _atomic_json(restart_receipt_path, restart_receipt)
    except Exception:
        try:
            server.stop()
        except Exception:
            pass
        raise
    print(
        json.dumps(
            {
                "schema": OPERATOR_SCHEMA,
                "command": "state-owner",
                "ready": True,
                "identity": identity.to_dict(),
                "live": ready,
                "mutation_dir": str((paths["owner"] / "mutations").relative_to(ROOT)),
                "restart_receipt": str(restart_receipt_path.relative_to(ROOT)),
                "restart_receipt_id": restart_receipt["receipt_id"],
            },
            sort_keys=True,
        ),
        flush=True,
    )
    stopped = {"value": False}

    def request_stop(_signum: int, _frame: Any) -> None:
        stopped["value"] = True

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    mutation_dir = paths["owner"] / "mutations"
    control_path = server.stop_control_path()
    while server.lifecycle is ServerLifecycle.READY and not stopped["value"]:
        if control_path.is_file():
            break
        _process_mutations(server, mutation_dir)
        time.sleep(0.05)
    result = server.stop()
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


def _executor_client_bindings(board: Any) -> dict[str, int]:
    lanes = max(1, int(board.max_lanes))
    if lanes == 1:
        owners = ((EXECUTOR_OWNER_SESSION_BASE, 0),)
    else:
        owners = tuple(
            (
                f"{EXECUTOR_OWNER_SESSION_BASE}:shard:{index}-of-{lanes}:"
                "track:"
                + hashlib.sha256(
                    f"{board.board_namespace}-{index}".encode()
                ).hexdigest()[:12],
                index,
            )
            for index in range(lanes)
        )
    return {
        f"database-implementation-daemon:{owner}": index
        for owner, index in owners
    }


def _executor_client_ids(board: Any) -> frozenset[str]:
    return frozenset(_executor_client_bindings(board))


def _supervisor_client_bindings(board: Any) -> dict[str, int]:
    return {
        client_id.replace(
            "database-implementation-daemon:",
            "database-implementation-supervisor:",
            1,
        ): lane_index
        for client_id, lane_index in _executor_client_bindings(board).items()
    }


def _owner_restart_prior_status(path: Path) -> dict[str, Any]:
    """Admit only a stopped or provably dead prior combined owner."""

    from ipfs_accelerate_py.agent_supervisor.merge.database_worktree_registry import (
        process_birth_id,
    )
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        ProcessBirthIdentity,
    )

    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return {
            "state": "absent",
            "status_identity": "",
            "server_id": "",
            "database_uuid": "",
            "store_id": "",
            "schema_revision": 0,
            "schema_fingerprint": "",
            "generation": 0,
            "fence_epoch": 0,
            "process_birth_id": "",
        }
    except OSError as exc:
        raise OperatorError("prior state-owner status cannot be inspected") from exc
    if (
        not stat_module.S_ISREG(metadata.st_mode)
        or metadata.st_uid != os.getuid()
        or metadata.st_nlink != 1
        or stat_module.S_IMODE(metadata.st_mode) != 0o600
    ):
        raise OperatorError("prior state-owner status is not a private regular file")
    payload = _json_object(path)
    if (
        payload.get("schema") != QUACK_STATE_SERVER_SCHEMA
        or payload.get("interface") != QUACK_STATE_SERVER_INTERFACE
    ):
        raise OperatorError("prior state-owner status schema is not admitted")
    lifecycle = str(payload.get("lifecycle") or "")
    liveness = _owner_liveness(payload)
    if lifecycle == "ready" and liveness in {"alive", "unknown"}:
        raise OperatorError(
            f"prior ready state owner has {liveness} process-birth liveness"
        )
    if lifecycle != "stopped" and liveness != "dead":
        raise OperatorError("prior state owner is neither stopped nor dead")
    identity = payload.get("identity")
    if (
        not isinstance(identity, Mapping)
        or identity.get("schema") != STATE_SERVER_IDENTITY_SCHEMA
        or identity.get("interface") != STATE_SERVER_IDENTITY_INTERFACE
    ):
        raise OperatorError("prior state-owner identity schema is not admitted")
    birth_payload = identity.get("process_birth")
    try:
        birth = (
            ProcessBirthIdentity.from_dict(dict(birth_payload))
            if isinstance(birth_payload, Mapping)
            else None
        )
    except Exception as exc:
        raise OperatorError("prior state-owner process birth is malformed") from exc
    claimed_birth_id = str(identity.get("process_birth_id") or "")
    if birth is None or process_birth_id(birth) != claimed_birth_id:
        raise OperatorError("prior state-owner process birth identity differs")
    schema_revision = _exact_int(
        identity.get("schema_revision"),
        field="prior state-owner schema_revision",
        minimum=1,
    )
    generation = _exact_int(
        identity.get("generation"),
        field="prior state-owner generation",
        minimum=1,
    )
    fence_epoch = _exact_int(
        identity.get("fence_epoch"),
        field="prior state-owner fence_epoch",
        minimum=1,
    )
    result = {
        "state": "stopped" if lifecycle == "stopped" else "dead",
        "lifecycle": lifecycle,
        "liveness": liveness,
        "status_identity": _identity(payload),
        "server_id": str(identity.get("server_id") or ""),
        "database_uuid": str(identity.get("database_uuid") or ""),
        "store_id": str(identity.get("store_id") or ""),
        "schema_revision": schema_revision,
        "schema_fingerprint": str(identity.get("schema_fingerprint") or ""),
        "generation": generation,
        "fence_epoch": fence_epoch,
        "process_birth_id": claimed_birth_id,
    }
    if (
        not result["server_id"]
        or not result["database_uuid"]
        or not result["store_id"]
        or re.fullmatch(r"sha256:[0-9a-f]{64}", result["schema_fingerprint"])
        is None
        or not result["process_birth_id"]
        or str(payload.get("store_id") or "") != result["store_id"]
    ):
        raise OperatorError("prior state-owner identity is incomplete")
    return result


def _require_prior_owner_continuity(
    admission: Mapping[str, Any],
    prior_owner: Mapping[str, Any],
) -> None:
    """Require durable owner continuity for every descendant-source restart."""

    if admission.get("mode") != "verified_handoff_repair":
        return
    if prior_owner.get("state") not in {"stopped", "dead"}:
        raise OperatorError(
            "descendant owner restart requires a stopped or dead prior identity"
        )
    if any(
        not prior_owner.get(field)
        for field in (
            "server_id",
            "database_uuid",
            "store_id",
            "schema_fingerprint",
            "process_birth_id",
        )
    ):
        raise OperatorError("descendant owner restart has incomplete prior continuity")
    for field in ("schema_revision", "generation", "fence_epoch"):
        _exact_int(
            prior_owner.get(field),
            field=f"prior state-owner {field}",
            minimum=1,
        )


def _restart_database_verification(source: Any, admission: Mapping[str, Any]) -> dict[str, Any]:
    """Reproduce the immutable population and exact repair source task."""

    authority = admission.get("database_authority")
    if not isinstance(authority, Mapping):
        raise OperatorError("restart admission has no database authority")
    snapshot = source.snapshot()
    page = source.list_tasks(limit=500)
    if page.next_cursor:
        raise OperatorError("restart database task population exceeds its bound")
    task_cids = sorted(str(task.task_cid) for task in page.tasks)
    expected_task_cids = sorted(str(item) for item in authority.get("task_cids", ()))
    if (
        task_cids != expected_task_cids
        or int(snapshot.task_count) != int(authority.get("task_count") or 0)
        or int(snapshot.goal_count) != int(authority.get("goal_count") or 0)
        or int(snapshot.plan_count) != int(authority.get("plan_count") or 0)
        or snapshot.plan_root_cid != authority.get("plan_root_cid")
        or snapshot.repository_tree_id != authority.get("repository_tree_id")
    ):
        raise OperatorError("restart database population differs from bootstrap")

    repair = admission.get("handoff_repair")
    task_projection: dict[str, Any] = {}
    if isinstance(repair, Mapping) and repair:
        task = source.get_task(str(repair.get("task_alias") or ""))
        attempt = repair.get("source_attempt")
        receipt = (
            task.body.get("completion_receipt")
            if task is not None and isinstance(task.body, Mapping)
            else None
        )
        if (
            task is None
            or task.task_cid != repair.get("task_cid")
            or task.status != "blocked"
            or not isinstance(attempt, Mapping)
            or int(task.revision) != int(attempt.get("task_revision") or 0)
            or not isinstance(receipt, Mapping)
            or _identity(receipt) != HANDOFF_REPAIR_COMPLETION_RECEIPT_ID
            or receipt.get("operation") != "database_portal_terminal_failure"
            or receipt.get("reason") != "portal_provider_failed"
            or receipt.get("retryable") is not False
            or receipt.get("control_expected_status") != "in_progress"
            or receipt.get("control_expected_revision") != int(task.revision) - 1
            or any(
                receipt.get(field) != attempt.get(field)
                for field in (
                    "attempt_id",
                    "claim_id",
                    "lease_id",
                    "owner_session_id",
                    "attempt_number",
                    "fencing_token",
                    "fence_epoch",
                )
            )
        ):
            raise OperatorError("restart repair source task changed authority")
        task_projection = {
            "task_alias": task.task_alias,
            "task_cid": task.task_cid,
            "status": task.status,
            "revision": int(task.revision),
            "terminal_receipt_identity": _identity(receipt),
            "attempt_identity": dict(attempt),
        }

    verification: dict[str, Any] = {
        "schema": OWNER_DATABASE_VERIFICATION_SCHEMA,
        "bootstrap_database_receipt_identity": str(
            authority.get("receipt_identity") or ""
        ),
        "repository_tree_id": snapshot.repository_tree_id,
        "plan_root_cid": snapshot.plan_root_cid,
        "task_cids": task_cids,
        "task_count": int(snapshot.task_count),
        "goal_count": int(snapshot.goal_count),
        "plan_count": int(snapshot.plan_count),
        "store_revision": int(snapshot.revision),
        "repair_source_task": task_projection,
    }
    verification["verification_id"] = _identity(verification)
    return verification


def _owner_restart_receipt(
    admission: Mapping[str, Any],
    identity: Any,
    *,
    expected_store_id: str,
    prior_owner: Mapping[str, Any],
    database_verification: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind one admitted descendant restart to its newly fenced owner."""

    _require_prior_owner_continuity(admission, prior_owner)
    admission_id = str(admission.get("admission_id") or "")
    admission_body = dict(admission)
    admission_body.pop("admission_id", None)
    authority = admission.get("database_authority")
    if (
        admission.get("schema") != OWNER_RESTART_ADMISSION_SCHEMA
        or re.fullmatch(r"sha256:[0-9a-f]{64}", admission_id) is None
        or _identity(admission_body) != admission_id
        or not isinstance(authority, Mapping)
    ):
        raise OperatorError("owner restart admission identity is invalid")
    verification_id = str(database_verification.get("verification_id") or "")
    verification_body = dict(database_verification)
    verification_body.pop("verification_id", None)
    verified_task_cids = database_verification.get("task_cids")
    authority_task_cids = authority.get("task_cids")
    if (
        database_verification.get("schema") != OWNER_DATABASE_VERIFICATION_SCHEMA
        or re.fullmatch(r"sha256:[0-9a-f]{64}", verification_id) is None
        or _identity(verification_body) != verification_id
        or str(
            database_verification.get("bootstrap_database_receipt_identity") or ""
        )
        != str(authority.get("receipt_identity") or "")
        or str(database_verification.get("plan_root_cid") or "")
        != str(admission.get("plan_root_cid") or "")
        or str(database_verification.get("repository_tree_id") or "")
        != str(admission.get("bootstrap_source_tree") or "")
        or not isinstance(verified_task_cids, list)
        or not isinstance(authority_task_cids, list)
        or verified_task_cids != sorted(str(item) for item in authority_task_cids)
        or type(database_verification.get("task_count")) is not int
        or database_verification.get("task_count") != authority.get("task_count")
        or type(database_verification.get("goal_count")) is not int
        or database_verification.get("goal_count") != authority.get("goal_count")
        or type(database_verification.get("plan_count")) is not int
        or database_verification.get("plan_count") != authority.get("plan_count")
    ):
        raise OperatorError("bound restart database verification is invalid")
    store_id = str(getattr(identity, "store_id", "") or "")
    database_uuid = str(getattr(identity, "database_uuid", "") or "")
    generation = _exact_int(
        getattr(identity, "generation", None),
        field="new state-owner generation",
        minimum=1,
    )
    fence_epoch = _exact_int(
        getattr(identity, "fence_epoch", None),
        field="new state-owner fence_epoch",
        minimum=1,
    )
    schema_revision = _exact_int(
        getattr(identity, "schema_revision", None),
        field="new state-owner schema_revision",
        minimum=1,
    )
    if (
        store_id != expected_store_id
        or not database_uuid
        or not str(getattr(identity, "server_id", "") or "")
        or generation < 1
        or fence_epoch < 1
        or schema_revision < 1
        or not str(getattr(identity, "schema_fingerprint", "") or "")
        or not str(getattr(identity, "process_birth_id", "") or "")
    ):
        raise OperatorError("new state-owner identity is invalid")
    prior_generation = int(prior_owner.get("generation") or 0)
    prior_fence_epoch = int(prior_owner.get("fence_epoch") or 0)
    if prior_generation and (
        generation <= prior_generation
        or fence_epoch <= prior_fence_epoch
        or str(prior_owner.get("server_id") or "")
        == str(getattr(identity, "server_id", "") or "")
        or str(prior_owner.get("database_uuid") or "") != database_uuid
        or str(prior_owner.get("store_id") or "") != store_id
        or int(prior_owner.get("schema_revision") or 0) != schema_revision
        or str(prior_owner.get("schema_fingerprint") or "")
        != str(getattr(identity, "schema_fingerprint", "") or "")
        or str(prior_owner.get("process_birth_id") or "")
        == str(getattr(identity, "process_birth_id", "") or "")
    ):
        raise OperatorError("new state-owner fence does not advance prior owner")
    receipt: dict[str, Any] = {
        "schema": OWNER_RESTART_RECEIPT_SCHEMA,
        "admission_id": str(admission.get("admission_id") or ""),
        "mode": str(admission.get("mode") or ""),
        "bootstrap_receipt_id": str(admission.get("bootstrap_receipt_id") or ""),
        "bootstrap_source_head": str(admission.get("bootstrap_source_head") or ""),
        "bootstrap_source_tree": str(admission.get("bootstrap_source_tree") or ""),
        "current_source_head": str(admission.get("current_source_head") or ""),
        "current_source_tree": str(admission.get("current_source_tree") or ""),
        "plan_root_cid": str(admission.get("plan_root_cid") or ""),
        "handoff_repair_receipt_id": str(
            admission.get("handoff_repair_receipt_id") or ""
        ),
        "max_task_attempts_before": int(
            admission.get("max_task_attempts_before") or 0
        ),
        "max_task_attempts_after": int(
            admission.get("max_task_attempts_after") or 0
        ),
        "prior_state_owner": dict(prior_owner),
        "database_verification": dict(database_verification),
        "state_owner": {
            "server_id": str(getattr(identity, "server_id", "") or ""),
            "store_id": store_id,
            "database_uuid": database_uuid,
            "schema_revision": schema_revision,
            "schema_fingerprint": str(
                getattr(identity, "schema_fingerprint", "") or ""
            ),
            "generation": generation,
            "fence_epoch": fence_epoch,
            "process_birth_id": str(
                getattr(identity, "process_birth_id", "") or ""
            ),
        },
    }
    receipt["receipt_id"] = _identity(receipt)
    return receipt


def _process_argv(pid: int) -> tuple[str, ...]:
    try:
        payload = Path(f"/proc/{int(pid)}/cmdline").read_bytes()
    except OSError as exc:
        raise OperatorError("executor parent command line is unavailable") from exc
    if not payload or len(payload) > 131_072:
        raise OperatorError("executor parent command line is invalid")
    try:
        return tuple(
            item.decode("utf-8")
            for item in payload.rstrip(b"\x00").split(b"\x00")
            if item
        )
    except UnicodeDecodeError as exc:
        raise OperatorError("executor parent command line is not UTF-8") from exc


def _argv_values(argv: Sequence[str], option: str) -> tuple[str, ...]:
    values: list[str] = []
    index = 0
    while index < len(argv):
        token = str(argv[index])
        if token == option:
            if index + 1 >= len(argv):
                raise OperatorError(f"executor parent {option} has no value")
            values.append(str(argv[index + 1]))
            index += 2
            continue
        if token.startswith(option + "="):
            values.append(token.split("=", 1)[1])
        index += 1
    return tuple(values)


class _ExecutionRoutePolicyProvider:
    """Seal the current exact task population through the typed owner surface."""

    def __init__(
        self,
        *,
        server: Any,
        board: Any,
        restart_admission: Mapping[str, Any],
    ) -> None:
        self.server = server
        self.board = board
        self.restart_admission = dict(restart_admission)
        self.database_verification: dict[str, Any] = {}
        self._lock = threading.Lock()

    def seal(self) -> Any:
        from ipfs_accelerate_py.agent_supervisor.task_sources.quack_state_client import (
            QuackStateClient,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.task_execution_route_policy import (
            GROK_CODEX_EXECUTION_MODE,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.typed_database_task_source import (
            TypedDatabaseTaskSource,
        )
        from ipfs_accelerate_py.agent_supervisor.task_sources.typed_state_owner import (
            TypedStateOwnerConnection,
        )

        with self._lock:
            identity = self.server.identity
            if identity is None:
                raise OperatorError("state owner has no route-policy identity")
            client_id = "pcsm-state-owner:execution-route-policy"
            store_id = _control_plane_store_id(
                self.board.resolved_database_program()
            )
            allowed_operations = (
                "whoami_metadata",
                "load_store_generation",
                "executor_control_snapshot",
                "executor_task_projection_page",
                "executor_task_projection_by_identity",
            )
            token, grant = self.server.issue_typed_client_grant_record(
                client_id=client_id,
                process_birth_id=identity.process_birth_id,
                allowed_operations=allowed_operations,
                peer_pid=os.getpid(),
                ttl_seconds=300.0,
            )
            client = QuackStateClient(
                owner_id=client_id,
                store_id=store_id,
                process_birth_id=identity.process_birth_id,
                connection_factory=lambda _endpoint: TypedStateOwnerConnection(
                    socket_path=self.server.typed_command_socket_path(),
                    token=token,
                    client_id=client_id,
                    process_birth_id=identity.process_birth_id,
                    store_id=store_id,
                ),
            )
            try:
                client.attach(
                    self.board.resolved_database_program().quack_endpoint,
                    server_id=identity.server_id,
                )
                with TypedDatabaseTaskSource(client, owns_client=True) as source:
                    page = source.list_tasks(limit=500)
                    if page.next_cursor:
                        raise OperatorError(
                            "execution route exceeds the bounded typed task page"
                        )
                    self.database_verification = _restart_database_verification(
                        source,
                        self.restart_admission,
                    )
                    return source.seal_execution_route_policy(
                        {
                            task.task_alias: GROK_CODEX_EXECUTION_MODE
                            for task in page.tasks
                        }
                    )
            finally:
                try:
                    client.close()
                finally:
                    self.server.revoke_typed_client_grant(grant.grant_id)


class _ExecutorBootstrapBroker:
    """Issue distinct exact-birth typed grants to the four canonical lanes."""

    def __init__(
        self,
        *,
        channel: socket.socket,
        server: Any,
        board: Any,
        paths: Mapping[str, Path],
        initial_execution_route_policy: Any,
    ) -> None:
        self.channel = channel
        self.server = server
        self.board = board
        self.paths = paths
        self.execution_route_policy = initial_execution_route_policy
        self.allowed_client_ids = _executor_client_ids(board)
        self.allowed_supervisor_client_ids = frozenset(
            _supervisor_client_bindings(board)
        )
        self.stopping = threading.Event()
        self.failure = ""
        self._accepted: socket.socket | None = None
        self._lock = threading.Lock()
        self._grants: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._thread = threading.Thread(
            target=self._run,
            name="pcsm-executor-bootstrap",
            daemon=True,
        )

    @property
    def evidence_path(self) -> Path:
        return self.paths["runtime"] / "evidence" / "runtime" / "executor-bootstrap.json"

    def start(self) -> None:
        self._thread.start()

    def _fail(self, exc: BaseException | str) -> None:
        self.failure = exc if isinstance(exc, str) else type(exc).__name__
        master_pid_path = (
            self.paths["runtime"] / "state" / "configured-board-master.pid"
        )
        deadline = time.monotonic() + 10.0
        while not self.stopping.is_set() and time.monotonic() < deadline:
            if _read_pid(master_pid_path) == os.getpid():
                os.kill(os.getpid(), signal.SIGTERM)
                return
            time.sleep(0.05)

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
                accepted.close()
            except OSError:
                pass
        try:
            self.channel.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.channel.close()
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
        if self._thread.is_alive():
            raise OperatorError("executor bootstrap broker did not stop")

    def _validate_parent(
        self,
        *,
        peer_pid: int,
        bootstrap_fd: int,
        client_id: str,
    ) -> None:
        from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
            read_process_birth,
        )

        executor_bindings = _executor_client_bindings(self.board)
        supervisor_bindings = _supervisor_client_bindings(self.board)
        is_executor = client_id in executor_bindings
        lane_index = (
            executor_bindings.get(client_id)
            if is_executor
            else supervisor_bindings.get(client_id)
        )
        if lane_index is None:
            raise OperatorError("bootstrap client has no admitted lane binding")
        peer_birth = read_process_birth(peer_pid)
        if peer_birth is None or int(peer_birth.parent_pid) <= 1:
            raise OperatorError("bootstrap peer has no live supervisor ancestry")
        if is_executor:
            supervisor_pid = int(peer_birth.parent_pid)
            supervisor_birth = read_process_birth(supervisor_pid)
            if supervisor_birth is None or int(supervisor_birth.parent_pid) != os.getpid():
                raise OperatorError(
                    "executor is outside the admitted multi-supervisor tree"
                )
        else:
            supervisor_pid = peer_pid
            if int(peer_birth.parent_pid) != os.getpid():
                raise OperatorError(
                    "supervisor is outside the admitted multi-supervisor tree"
                )
        argv = _process_argv(supervisor_pid)
        expected_entry = str(
            (ROOT / "scripts/ops/agent_supervisor/implementation_supervisor_entry.py")
            .resolve()
        )
        if expected_entry not in argv:
            raise OperatorError("executor parent is not the configured supervisor entry")
        if _argv_values(argv, "--board-namespace") != (self.board.board_namespace,):
            raise OperatorError("executor parent board namespace differs")
        if _argv_values(argv, "--state-owner-bootstrap-fd") != (str(bootstrap_fd),):
            raise OperatorError("executor parent bootstrap descriptor differs")
        owner_session_id = client_id.removeprefix(
            "database-implementation-daemon:"
            if is_executor
            else "database-implementation-supervisor:"
        )
        expected_count = str(max(1, int(self.board.max_lanes)))
        if _argv_values(argv, "--database-owner-session-id") != (
            owner_session_id,
        ):
            raise OperatorError("executor parent owner session differs from its lane")
        if _argv_values(argv, "--task-shard-count") != (expected_count,) or (
            _argv_values(argv, "--task-shard-index") != (str(lane_index),)
        ):
            raise OperatorError("executor parent shard differs from its lane")
        if is_executor:
            daemon_argv = _process_argv(peer_pid)
            if _argv_values(daemon_argv, "--owner-session-id") != (
                owner_session_id,
            ):
                raise OperatorError("executor owner session differs from its lane")
            if _argv_values(daemon_argv, "--task-shard-count") != (
                expected_count,
            ) or _argv_values(daemon_argv, "--task-shard-index") != (
                str(lane_index),
            ):
                raise OperatorError("executor shard differs from its lane")

    def _admit(
        self,
        request: Mapping[str, Any],
        *,
        peer_pid: int,
        peer_uid: int,
    ) -> dict[str, Any]:
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
            _DAEMON_REQUIRED_OWNER_COMMAND_OPERATIONS,
            _DAEMON_REQUIRED_OWNER_OPERATIONS,
        )

        required = {
            "schema",
            "pid",
            "process_birth",
            "process_birth_id",
            "client_id",
            "store_id",
        }
        if set(request) != required or request.get("schema") != (
            STATE_OWNER_BOOTSTRAP_REQUEST_SCHEMA
        ):
            raise OperatorError("executor bootstrap request differs from its closed schema")
        pid = int(request.get("pid") or 0)
        raw_birth = request.get("process_birth")
        if pid <= 1 or not isinstance(raw_birth, Mapping):
            raise OperatorError("executor bootstrap request has no process birth")
        if pid != peer_pid or peer_uid != os.geteuid():
            raise OperatorError("executor bootstrap SO_PEERCRED identity differs")
        observed = read_process_birth(pid)
        supplied = ProcessBirthIdentity.from_dict(dict(raw_birth))
        supplied_birth_id = str(request.get("process_birth_id") or "")
        if (
            observed is None
            or observed != supplied
            or process_birth_id(observed) != supplied_birth_id
        ):
            raise OperatorError("executor bootstrap process birth is stale")
        client_id = str(request.get("client_id") or "")
        store_id = _control_plane_store_id(self.board.resolved_database_program())
        is_executor = client_id in self.allowed_client_ids
        is_supervisor = client_id in self.allowed_supervisor_client_ids
        if (
            not (is_executor or is_supervisor)
            or request.get("store_id") != store_id
        ):
            raise OperatorError("executor bootstrap scope differs from its admission")
        self._validate_parent(
            peer_pid=pid,
            bootstrap_fd=self.channel.fileno(),
            client_id=client_id,
        )

        with self._lock:
            prior = dict(self._grants.get(client_id) or {})
        prior_birth = prior.get("process_birth")
        if isinstance(prior_birth, Mapping):
            prior_identity = ProcessBirthIdentity.from_dict(dict(prior_birth))
            if owner_liveness(prior_identity) is not OwnerLiveness.DEAD:
                raise OperatorError("prior lane executor remains live during rotation")
            prior_grant_id = str(prior.get("grant_id") or "")
            if prior_grant_id:
                self.server.revoke_typed_client_grant(prior_grant_id)

        # A route policy is immutable for one materialized plan epoch. Claims and
        # lifecycle writes advance the task-store revision, but they do not change
        # the admitted task population. Re-sealing here would make a restarted
        # process disagree with the lane's stable Quack sidecar authority. A
        # population-changing refill must instead quiesce the lanes, seal a new
        # policy, and relaunch them as an explicit epoch transition.
        execution_route_policy = self.execution_route_policy
        allowed_operations = (
            tuple(sorted(_DAEMON_REQUIRED_OWNER_OPERATIONS))
            if is_executor
            else (
                "executor_control_snapshot",
                "executor_task_projection_by_identity",
                "executor_task_projection_page",
                "load_store_generation",
                "whoami_metadata",
            )
        )
        allowed_command_operations = (
            tuple(sorted(_DAEMON_REQUIRED_OWNER_COMMAND_OPERATIONS))
            if is_executor
            else ()
        )
        token, grant = self.server.issue_typed_client_grant_record(
            client_id=client_id,
            process_birth_id=supplied_birth_id,
            allowed_operations=allowed_operations,
            allowed_command_operations=allowed_command_operations,
            peer_pid=pid,
            ttl_seconds=INTERNAL_CLIENT_GRANT_TTL_SECONDS,
        )
        identity = self.server.identity
        if identity is None:
            self.server.revoke_typed_client_grant(grant.grant_id)
            raise OperatorError("state owner lost identity during bootstrap")
        record = {
            "client_id": client_id,
            "process_birth": supplied.to_dict(),
            "process_birth_id": supplied_birth_id,
            "parent_pid": int(supplied.parent_pid),
            "admitted_at_ns": time.time_ns(),
            "execution_route_policy_id": execution_route_policy.policy_id,
            "credential_transport": "private_inherited_socket",
            "client_role": "executor" if is_executor else "supervisor_read",
        }
        try:
            with self._lock:
                self._grants[client_id] = {**record, "grant_id": grant.grant_id}
                self._history.append(record)
                self._history = self._history[-128:]
                evidence = {
                    "schema": EXECUTOR_BOOTSTRAP_SCHEMA,
                    "ready": True,
                    "accepted_lane_count": sum(
                        client in self.allowed_client_ids for client in self._grants
                    ),
                    "accepted_supervisor_reader_count": sum(
                        client in self.allowed_supervisor_client_ids
                        for client in self._grants
                    ),
                    "expected_lane_count": len(self.allowed_client_ids),
                    "server_id": identity.server_id,
                    "state_owner_process_birth_id": identity.process_birth_id,
                    "execution_route_policy": execution_route_policy.public_summary(),
                    "current": [
                        {
                            key: value
                            for key, value in item.items()
                            if key != "grant_id"
                        }
                        for item in self._grants.values()
                    ],
                    "history": list(self._history),
                }
                _atomic_json(self.evidence_path, evidence)
        except BaseException:
            self.server.revoke_typed_client_grant(grant.grant_id)
            raise
        return {
            "schema": STATE_OWNER_BOOTSTRAP_RESPONSE_SCHEMA,
            "ok": True,
            "endpoint": self.board.resolved_database_program().quack_endpoint,
            "socket_path": str(self.server.typed_command_socket_path()),
            "store_id": store_id,
            "server_id": identity.server_id,
            "client_id": client_id,
            "process_birth_id": supplied_birth_id,
            "token": token,
            "execution_route_policy": execution_route_policy.to_dict(),
        }

    def _run(self) -> None:
        import struct

        from ipfs_accelerate_py.agent_supervisor.task_sources.state_owner_bootstrap import (
            _receive_frame,
            _send_frame,
        )

        self.channel.settimeout(1.0)
        while not self.stopping.is_set():
            accepted: socket.socket | None = None
            try:
                accepted, _address = self.channel.accept()
                with self._lock:
                    self._accepted = accepted
                accepted.settimeout(30.0)
                peer = accepted.getsockopt(
                    socket.SOL_SOCKET,
                    socket.SO_PEERCRED,
                    struct.calcsize("3i"),
                )
                peer_pid, peer_uid, _peer_gid = struct.unpack("3i", peer)
                response = self._admit(
                    _receive_frame(accepted),
                    peer_pid=int(peer_pid),
                    peer_uid=int(peer_uid),
                )
                _send_frame(accepted, response)
            except TimeoutError:
                if accepted is not None:
                    self._fail("executor_bootstrap_request_timeout")
                    return
            except OSError as exc:
                if not self.stopping.is_set():
                    self._fail(exc)
                    return
            except BaseException as exc:
                self._fail(exc)
                return
            finally:
                if accepted is not None:
                    with self._lock:
                        if self._accepted is accepted:
                            self._accepted = None
                    try:
                        accepted.close()
                    except OSError:
                        pass


def _bootstrap_listener() -> socket.socket:
    """Create one private inherited Linux rendezvous listener."""

    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    identity = hashlib.sha256(
        f"{ROOT}:{os.getpid()}:{time.time_ns()}".encode()
    ).hexdigest()[:32]
    listener.bind("\x00ipfs-accelerate-pcsm-" + identity)
    listener.listen(16)
    return listener


def _quarantine_stale_executor_bootstrap(paths: Mapping[str, Path]) -> None:
    evidence = paths["runtime"] / "evidence" / "runtime" / "executor-bootstrap.json"
    if not evidence.exists():
        return
    if evidence.is_symlink() or not evidence.is_file():
        raise OperatorError("executor bootstrap evidence is not a regular file")
    quarantine = evidence.with_name(
        f"executor-bootstrap.superseded.{time.time_ns()}.json"
    )
    evidence.replace(quarantine)


def _owner_liveness(status_payload: Mapping[str, Any]) -> str:
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        OwnerLiveness,
        ProcessBirthIdentity,
        owner_liveness,
    )

    identity = status_payload.get("identity")
    if not isinstance(identity, Mapping):
        return "absent"
    birth_payload = identity.get("process_birth")
    if not isinstance(birth_payload, Mapping):
        return "unknown"
    try:
        observed = owner_liveness(ProcessBirthIdentity.from_dict(birth_payload))
    except Exception:
        return "unknown"
    if observed is OwnerLiveness.ALIVE:
        return "alive"
    if observed is OwnerLiveness.DEAD:
        return "dead"
    return "unknown"


def _task_status(connection: Any) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY status"
    ).fetchall()
    counts = {str(row[0]): int(row[1]) for row in rows}
    # The current Quack table transport supports simple scans but can reject a
    # correlated NOT EXISTS plan as unimplemented.  Read the three canonical
    # relations separately and calculate this read-only projection locally;
    # task/dependency/block rows remain authoritative in DuckDB.
    task_rows = connection.execute(
        "SELECT task_cid, task_alias, ordinal, status "
        "FROM tasks ORDER BY ordinal, task_alias"
    ).fetchall()
    dependency_rows = connection.execute(
        "SELECT task_cid, dependency_task_cid FROM task_dependencies"
    ).fetchall()
    blocked_rows = connection.execute(
        "SELECT task_cid FROM task_blocks WHERE state = 'active'"
    ).fetchall()
    status_by_cid = {str(row[0]): str(row[3]) for row in task_rows}
    dependencies_by_cid: dict[str, list[str]] = {}
    for row in dependency_rows:
        dependencies_by_cid.setdefault(str(row[0]), []).append(str(row[1]))
    actively_blocked = {str(row[0]) for row in blocked_rows}
    ready_ids = [
        str(row[1])
        for row in task_rows
        if str(row[3]) in READY_STATUSES
        and str(row[0]) not in actively_blocked
        and all(
            status_by_cid.get(dependency) in COMPLETED_STATUSES
            for dependency in dependencies_by_cid.get(str(row[0]), ())
        )
    ][:100]
    active_rows = connection.execute(
        "SELECT task_alias FROM tasks WHERE status IN (?, ?, ?) "
        "ORDER BY ordinal, task_alias LIMIT 100",
        list(ACTIVE_STATUSES),
    ).fetchall()
    return {
        "status_counts": counts,
        "dependency_ready_task_ids": ready_ids,
        "active_task_ids": [str(row[0]) for row in active_rows],
        "blocked_count": int(counts.get("blocked", 0)),
        "terminal_count": sum(counts.get(item, 0) for item in TERMINAL_STATUSES),
        "task_count": sum(counts.values()),
    }


def _supervisor_status(
    board: Any,
    paths: Mapping[str, Path],
    owner: Mapping[str, Any],
) -> dict[str, Any]:
    state_dir = paths["runtime"] / "state"
    master_pid_path = state_dir / "configured-board-master.pid"
    master_pid = _read_pid(master_pid_path)
    identity = owner.get("identity")
    process_birth = identity.get("process_birth") if isinstance(identity, Mapping) else None
    owner_pid = int(process_birth.get("pid") or 0) if isinstance(process_birth, Mapping) else 0
    owner_server_id = str(identity.get("server_id") or "") if isinstance(identity, Mapping) else ""
    owner_process_birth_id = (
        str(identity.get("process_birth_id") or "")
        if isinstance(identity, Mapping)
        else ""
    )
    lanes: list[dict[str, Any]] = []
    freshness_limit = max(
        120.0,
        float(board.payload.get("check_interval_seconds") or 20.0) * 4.0,
    )
    for index in range(max(1, int(board.max_lanes))):
        lane_dir = state_dir / f"lane-{index}"
        supervisor_pid = _read_pid(lane_dir / f"pcsm_lane_{index}_supervisor.pid")
        daemon_pid = _read_pid(lane_dir / f"pcsm_lane_{index}_managed_daemon.pid")
        status_path = lane_dir / f"pcsm_lane_{index}_supervisor_status.json"
        lane_status: dict[str, Any] = {}
        projection_fresh = False
        projection_bound = False
        if status_path.is_file():
            try:
                observed = _json_object(status_path)
                updated_at = str(observed.get("updated_at") or "")
                try:
                    parsed = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    if parsed.tzinfo is None:
                        parsed = parsed.replace(tzinfo=UTC)
                    age_seconds = max(
                        0.0,
                        datetime.now(UTC).timestamp() - parsed.timestamp(),
                    )
                except (TypeError, ValueError):
                    age_seconds = float("inf")
                projection_fresh = age_seconds <= freshness_limit
                projection_bound = (
                    int(observed.get("supervisor_pid") or 0) == supervisor_pid
                    and int(observed.get("daemon_pid") or 0) == daemon_pid
                    and observed.get("supervisor_pid_alive") is True
                    and observed.get("daemon_pid_alive") is True
                    and str(observed.get("status") or "")
                    not in {"blocked", "failed", "quarantined", "stopped"}
                )
                lane_status = {
                    key: observed.get(key)
                    for key in (
                        "status",
                        "updated_at",
                        "restart_count",
                        "daemon_running",
                    )
                    if key in observed
                }
                lane_status["age_seconds"] = age_seconds
            except OperatorError:
                lane_status = {"status": "malformed"}
        lanes.append(
            {
                "lane_index": index,
                "supervisor_pid": supervisor_pid,
                "supervisor_alive": (
                    _pid_alive(supervisor_pid)
                    and projection_fresh
                    and projection_bound
                ),
                "daemon_pid": daemon_pid,
                "daemon_alive": (
                    _pid_alive(daemon_pid)
                    and projection_fresh
                    and projection_bound
                ),
                "projection": lane_status,
            }
        )
    bootstrap_path = paths["runtime"] / "evidence" / "runtime" / "executor-bootstrap.json"
    bootstrap: dict[str, Any] = {"ready": False, "accepted_lane_count": 0}
    if bootstrap_path.is_file():
        try:
            observed_bootstrap = _json_object(bootstrap_path)
            bootstrap = {
                "ready": observed_bootstrap.get("ready") is True,
                "accepted_lane_count": int(
                    observed_bootstrap.get("accepted_lane_count") or 0
                ),
                "expected_lane_count": int(
                    observed_bootstrap.get("expected_lane_count") or 0
                ),
                "execution_route_policy": observed_bootstrap.get(
                    "execution_route_policy"
                ),
                "server_id": str(observed_bootstrap.get("server_id") or ""),
                "state_owner_process_birth_id": str(
                    observed_bootstrap.get("state_owner_process_birth_id") or ""
                ),
            }
        except (OperatorError, TypeError, ValueError):
            bootstrap = {"ready": False, "accepted_lane_count": 0}
    expected = max(1, int(board.max_lanes))
    live_lanes = sum(item["supervisor_alive"] for item in lanes)
    live_daemons = sum(item["daemon_alive"] for item in lanes)
    return {
        "ready": (
            _pid_alive(master_pid)
            and master_pid == owner_pid
            and live_lanes == expected
            and live_daemons == expected
            and bootstrap.get("ready") is True
            and int(bootstrap.get("accepted_lane_count") or 0) == expected
            and bootstrap.get("server_id") == owner_server_id
            and bootstrap.get("state_owner_process_birth_id")
            == owner_process_birth_id
        ),
        "master_pid": master_pid,
        "master_alive": _pid_alive(master_pid),
        "same_process_as_state_owner": bool(master_pid and master_pid == owner_pid),
        "expected_lane_count": expected,
        "live_lane_count": live_lanes,
        "live_daemon_count": live_daemons,
        "lanes": lanes,
        "executor_bootstrap": bootstrap,
    }


def status(config_path: Path) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
        open_duckdb_connection,
    )

    board, _config = _load_config(config_path)
    paths = _runtime_paths(board)
    state_status_path = paths["owner"] / "quack-state-server.status.json"
    owner_status: dict[str, Any] = {}
    if state_status_path.is_file():
        try:
            owner_status = _json_object(state_status_path)
        except OperatorError:
            owner_status = {"lifecycle": "malformed"}
    liveness = _owner_liveness(owner_status)
    lifecycle = str(owner_status.get("lifecycle") or "absent")
    live_ready = lifecycle == "ready" and liveness == "alive"
    task_projection: dict[str, Any] = {
        "available": False,
        "reason_code": "control_plane_unavailable",
    }
    connection = None
    try:
        if live_ready:
            read_replica = owner_status.get("read_replica")
            read_replica = read_replica if isinstance(read_replica, Mapping) else {}
            expected_replica = paths["database"].with_name(
                f"{paths['database'].stem}.read-replica{paths['database'].suffix}"
            )
            observed_path = Path(str(read_replica.get("path") or ""))
            if (
                read_replica.get("authority") != "non_authoritative_read_replica"
                or read_replica.get("live") is not True
                or observed_path != expected_replica
                or not expected_replica.is_file()
            ):
                raise OperatorError("current state-owner read projection is unavailable")
            import duckdb

            connection = duckdb.connect(str(expected_replica), read_only=True)
            task_projection = {
                "available": True,
                "transport": "quack_owner_checkpointed_read_replica",
                "authoritative": False,
                "authority": "DuckDB/DatabaseTaskSource@1 via live Quack owner",
                "scheduler_gate": False,
                "refresh_sequence": int(read_replica.get("refresh_sequence") or 0),
                **_task_status(connection),
            }
        elif paths["database"].is_file() and liveness in {"absent", "dead"}:
            connection = open_duckdb_connection(paths["database"])
            task_projection = {
                "available": True,
                "transport": "direct_offline",
                "authoritative": True,
                **_task_status(connection),
            }
    except Exception as exc:
        task_projection = {
            "available": False,
            "reason_code": "control_plane_probe_failed",
            "error_class": type(exc).__name__,
        }
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
    ducklake: dict[str, Any] = {
        "status": "absent",
        "authoritative": False,
        "scheduler_gate": False,
    }
    if paths["ducklake_receipt"].is_file():
        try:
            observed = _json_object(paths["ducklake_receipt"])
            ducklake = {
                "status": str(observed.get("status") or "unknown"),
                "authoritative": False,
                "scheduler_gate": False,
                "projection_receipt_id": str(
                    observed.get("projection_receipt_id") or ""
                ),
            }
        except OperatorError:
            ducklake["status"] = "malformed"
    supervisor = _supervisor_status(board, paths, owner_status)
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "status",
        "materialized": paths["database"].is_file()
        and paths["bootstrap_receipt"].is_file(),
        "state_owner": {
            "ready": live_ready,
            "lifecycle": lifecycle,
            "liveness": liveness,
            "identity": owner_status.get("identity"),
        },
        "supervisor": supervisor,
        "task_authority": task_projection,
        "ducklake_projection": ducklake,
    }


def _pid_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid(path: Path) -> int:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    return int(raw) if raw.isdigit() else 0


def _write_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    temporary.write_text(f"{int(pid)}\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def _python_environment() -> dict[str, str]:
    environment = dict(os.environ)
    ordered: list[str] = []
    for item in (
        str(ACCEL_ROOT),
        str(ROOT),
        *environment.get("PYTHONPATH", "").split(os.pathsep),
    ):
        if item and item not in ordered:
            ordered.append(item)
    environment["PYTHONPATH"] = os.pathsep.join(ordered)
    return environment


def start_state_owner_daemon(config_path: Path) -> dict[str, Any]:
    board, _config = _load_config(config_path)
    paths = _runtime_paths(board)
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise OperatorError("materialize the sealed PCSM board before starting Quack")
    current = status(config_path)
    if (
        current["state_owner"]["ready"] is True
        and current["supervisor"]["ready"] is True
    ):
        return {
            "schema": OPERATOR_SCHEMA,
            "command": OWNER_DAEMON_COMMAND,
            "already_running": True,
            "ready": True,
        }
    if current["state_owner"]["ready"] is True:
        raise OperatorError(
            "a Quack owner exists outside the canonical combined supervisor launch"
        )
    pid_path = paths["runtime"] / "state" / "pcsm-state-owner.pid"
    prior_pid = _read_pid(pid_path)
    if _pid_alive(prior_pid):
        raise OperatorError("a state-owner process exists but is not live-ready")
    log_path = paths["runtime"] / "logs" / "pcsm-supervisor.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--config",
        str(config_path),
        "launch-supervisor",
    ]
    with log_path.open("ab", buffering=0) as log_handle:
        process = subprocess.Popen(
            argv,
            cwd=ROOT,
            env=_python_environment(),
            stdin=subprocess.DEVNULL,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    _write_pid(pid_path, process.pid)
    deadline = time.monotonic() + 180.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise OperatorError("detached PCSM supervisor exited before readiness")
        observed = status(config_path)
        if (
            observed["state_owner"]["ready"] is True
            and observed["supervisor"]["ready"] is True
            and observed["task_authority"].get("available") is True
        ):
            return {
                "schema": OPERATOR_SCHEMA,
                "command": OWNER_DAEMON_COMMAND,
                "already_running": False,
                "detached": True,
                "ready": True,
                "pid": process.pid,
                "pid_path": str(pid_path.relative_to(ROOT)),
                "log_path": str(log_path.relative_to(ROOT)),
            }
        time.sleep(0.25)
    try:
        process.terminate()
    except OSError:
        pass
    raise OperatorError("detached PCSM supervisor did not become ready")


def launch_supervisor(
    config_path: Path,
    *,
    dry_run: bool = False,
    duration_seconds: float = float("inf"),
) -> int:
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        configured_board_launch_plan,
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        main as configured_board_main,
    )
    from ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner import (
        main as multi_supervisor_main,
    )

    board, config = _load_config(config_path)
    paths = _runtime_paths(board)
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise OperatorError("materialize the sealed PCSM board before launch")
    restart_admission = _owner_restart_admission(board, config, paths)
    common = ["--repo-root", str(ROOT), "--config", str(config_path)]
    preflight = int(configured_board_main([*common, "preflight"]))
    if preflight != 0:
        return preflight
    preflight_head, preflight_tree = _assert_clean_current_tree(config)
    if (
        preflight_head != restart_admission["current_source_head"]
        or preflight_tree != restart_admission["current_source_tree"]
    ):
        raise OperatorError("owner restart source changed during preflight")
    if dry_run:
        plan = configured_board_launch_plan(
            board,
            implement=True,
            detach=False,
            duration_seconds=duration_seconds,
        )
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "command": "launch-supervisor",
                    "dry_run": True,
                    "board_namespace": plan["board_namespace"],
                    "lanes": plan["lanes"],
                    "authority_mode": plan["database_program"]["authority_mode"],
                    "task_source_kind": plan["database_program"]["task_source_kind"],
                    "credential_transport": "private_inherited_socket",
                    "restart_admission_mode": restart_admission["mode"],
                    "restart_admission_id": restart_admission["admission_id"],
                    "max_task_attempts_before": restart_admission[
                        "max_task_attempts_before"
                    ],
                    "max_task_attempts_after": restart_admission[
                        "max_task_attempts_after"
                    ],
                },
                sort_keys=True,
            )
        )
        return 0
    if duration_seconds != float("inf") and duration_seconds <= 0:
        raise OperatorError("supervisor duration must be positive")

    prior_owner = _owner_restart_prior_status(
        paths["owner"] / "quack-state-server.status.json"
    )
    _require_prior_owner_continuity(restart_admission, prior_owner)
    _ensure_private_runtime_directory(paths["runtime"])
    _ensure_private_runtime_directory(paths["runtime"] / "state")
    _quarantine_stale_executor_bootstrap(paths)
    server = _build_state_owner(board, paths)
    listener: socket.socket | None = None
    broker: _ExecutorBootstrapBroker | None = None
    prior_environment = dict(os.environ)
    result = 1
    try:
        identity = server.start()
        ready = server.ready()
        route_policy_provider = _ExecutionRoutePolicyProvider(
            server=server,
            board=board,
            restart_admission=restart_admission,
        )
        route_policy = route_policy_provider.seal()
        after_head, after_tree = _assert_clean_current_tree(config)
        if (
            after_head != restart_admission["current_source_head"]
            or after_tree != restart_admission["current_source_tree"]
        ):
            raise OperatorError("owner restart source changed during admission")
        restart_receipt = _owner_restart_receipt(
            restart_admission,
            identity,
            expected_store_id=_control_plane_store_id(
                board.resolved_database_program()
            ),
            prior_owner=prior_owner,
            database_verification=route_policy_provider.database_verification,
        )
        restart_receipt_path = (
            paths["runtime"]
            / "evidence"
            / "runtime"
            / "owner-restarts"
            / (
                f"{int(identity.generation):020d}-"
                f"{restart_receipt['receipt_id'].removeprefix('sha256:')}.json"
            )
        )
        _atomic_json(restart_receipt_path, restart_receipt)
        listener = _bootstrap_listener()
        broker = _ExecutorBootstrapBroker(
            channel=listener,
            server=server,
            board=board,
            paths=paths,
            initial_execution_route_policy=route_policy,
        )
        broker.start()
        plan = configured_board_launch_plan(
            board,
            implement=True,
            detach=False,
            duration_seconds=duration_seconds,
        )
        for lane_index in range(int(plan["lanes"])):
            _ensure_private_runtime_directory(
                paths["runtime"] / "state" / f"lane-{lane_index}"
            )
        runner_args = list(plan["argv"])
        for value in (
            "--database-owner-session-id",
            EXECUTOR_OWNER_SESSION_BASE,
            "--state-owner-bootstrap-fd",
            str(listener.fileno()),
            "--state-owner-bootstrap-store-id",
            _control_plane_store_id(board.resolved_database_program()),
        ):
            runner_args.append(f"--common-arg={value}")
        environment = _python_environment()
        environment.update(
            {str(key): str(value) for key, value in plan["environment"].items()}
        )
        for secret_name in (
            "IPFS_ACCELERATE_AGENT_QUACK_TOKEN",
            "IPFS_ACCELERATE_AGENT_STATE_OWNER_SOCKET",
            "IPFS_ACCELERATE_AGENT_TYPED_STATE_OWNER_TOKEN",
            "IPFS_ACCELERATE_AGENT_TYPED_STATE_OWNER_SOCKET",
        ):
            environment.pop(secret_name, None)
        os.environ.clear()
        os.environ.update(environment)
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "command": "launch-supervisor",
                    "ready": True,
                    "identity": identity.to_dict(),
                    "live": ready,
                    "lanes": int(plan["lanes"]),
                    "execution_route_policy": route_policy.public_summary(),
                    "owner_restart_receipt": restart_receipt,
                    "owner_restart_receipt_path": str(
                        restart_receipt_path.relative_to(ROOT)
                    ),
                    "credential_transport": "private_inherited_socket",
                    "raw_token_in_argv_or_environment": False,
                },
                sort_keys=True,
            ),
            flush=True,
        )
        result = int(multi_supervisor_main(runner_args))
        if broker.failure:
            raise OperatorError(
                f"executor bootstrap broker failed closed: {broker.failure}"
            )
        return result
    finally:
        os.environ.clear()
        os.environ.update(prior_environment)
        if broker is not None:
            try:
                broker.stop()
            except Exception:
                if result == 0:
                    raise
        elif listener is not None:
            listener.close()
        server.stop()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="repository-relative or absolute configured-board JSON",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "materialize",
        help="seal the committed Markdown bootstrap into DuckDB and DuckLake",
    )
    commands.add_parser(
        "state-owner",
        help="serve the materialized DuckDB authority through fenced loopback Quack",
    )
    commands.add_parser(
        OWNER_DAEMON_COMMAND,
        help="start the session-independent Quack owner and configured supervisor",
    )
    status_parser = commands.add_parser(
        "status",
        help="report owner liveness and durable task readiness without exposing tokens",
    )
    status_parser.add_argument(
        "--require-ready",
        action="store_true",
        help="exit nonzero unless Quack is live and task authority is queryable",
    )
    launch_parser = commands.add_parser(
        "launch-supervisor",
        help="preflight and launch the existing configured-board supervisor",
    )
    launch_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="render and validate the launch without starting workers",
    )
    launch_parser.add_argument(
        "--duration-seconds",
        type=float,
        default=float("inf"),
        help="optional positive supervisor runtime bound",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    config_path = arguments.config
    if not config_path.is_absolute():
        config_path = ROOT / config_path
    try:
        if arguments.command == "materialize":
            result = materialize(config_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.command == "state-owner":
            return state_owner(config_path)
        if arguments.command == OWNER_DAEMON_COMMAND:
            result = start_state_owner_daemon(config_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.command == "status":
            result = status(config_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            if arguments.require_ready and not (
                result["state_owner"]["ready"]
                and result["supervisor"]["ready"]
                and result["task_authority"].get("available") is True
            ):
                return 1
            return 0
        if arguments.command == "launch-supervisor":
            return launch_supervisor(
                config_path,
                dry_run=bool(arguments.dry_run),
                duration_seconds=float(arguments.duration_seconds),
            )
        raise OperatorError(f"unsupported command: {arguments.command}")
    except OperatorError as exc:
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "command": str(arguments.command),
                    "ok": False,
                    "error_class": type(exc).__name__,
                    "error": str(exc),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    except Exception as exc:
        # Third-party transport exception text is not a trusted secret-
        # redaction surface, so unexpected failures publish only their class.
        print(
            json.dumps(
                {
                    "schema": OPERATOR_SCHEMA,
                    "command": str(arguments.command),
                    "ok": False,
                    "error_class": type(exc).__name__,
                    "error": "operation failed closed",
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
