#!/usr/bin/env python3
"""Operate the bounded PCPR bootstrap over the existing supervisor services.

The Markdown files are immutable bootstrap inputs.  ``DatabaseTaskSource@1``
materializes their single repair task into DuckDB before a Quack owner exists;
after that transition Quack is the only mutation authority.  DuckLake is an
optional, rebuildable history projection and is never a scheduler, completion,
promotion, or release gate.  This module creates no supervisor, planner, task
database, event database, or controller family.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

ROOT: Final = Path(__file__).resolve().parents[1]
ACCEL_ROOT: Final = ROOT / "external" / "ipfs_accelerate"
DEFAULT_CONFIG: Final = Path(
    "config/proof_carrying_platform_qualification_and_release_v1_supervisor.json"
)
PROGRAM_ID: Final = "proof-carrying-platform-qualification-and-release-v1"
TASK_PREFIX: Final = "PCPR-"
BOOTSTRAP_TASK: Final = "PCPR-004"
ROOT_GOAL: Final = "PCPR-G000"
OPERATOR_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-platform-qualification-and-release-v1-operator@1"
)
POPULATION_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-platform-qualification-and-release-v1-population@1"
)
BOOTSTRAP_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-platform-qualification-and-release-v1-bootstrap@1"
)
DUCKLAKE_SCHEMA: Final = (
    "ipfs_accelerate_py/agent-supervisor/"
    "proof-carrying-platform-qualification-and-release-v1-ducklake-projection@1"
)
GOAL_RE: Final = re.compile(r"^## (PCPR-G\d{3})\s+(.+?)\s*$", re.MULTILINE)
QUACK_RE: Final = re.compile(
    r"^quack:(?://)?(127(?:\.\d{1,3}){3}|localhost):(\d{1,5})$",
    re.IGNORECASE,
)
READY_STATUSES: Final = frozenset(
    {"proposed", "admitted", "pending", "ready", "todo", "queued", "retrying"}
)
ACTIVE_STATUSES: Final = frozenset({"claimed", "in_progress", "running"})
COMPLETED_STATUSES: Final = frozenset({"completed", "skipped", "complete", "done"})
TERMINAL_STATUSES: Final = frozenset(
    {*COMPLETED_STATUSES, "cancelled", "failed", "quarantined", "rejected"}
)
FATAL_RE: Final = re.compile(
    r"(?:^|\b)(?:fatal|panic|traceback|quarantin(?:e|ed)|security failure)(?:\b|:)",
    re.IGNORECASE,
)
SOURCE_REPOSITORIES: Final = (
    ("ipfs_accelerate_py", Path("external/ipfs_accelerate")),
    ("ipfs_datasets_py", Path("external/ipfs_datasets")),
    ("ipfs_kit_py", Path("external/ipfs_kit")),
)


class OperatorError(RuntimeError):
    """Fail-closed PCPR bootstrap/operator error."""


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


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
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


def _atomic_pid(path: Path, pid: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(f"{int(pid)}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
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


def _safe_path(value: Any, *, field: str) -> Path:
    text = str(value or "").strip()
    relative = Path(text)
    if not text or relative.is_absolute() or ".." in relative.parts:
        raise OperatorError(f"{field} must be a safe repository-relative path")
    resolved = (ROOT / relative).resolve(strict=False)
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise OperatorError(f"{field} escapes the portfolio repository") from exc
    return resolved


def _git(
    *arguments: str,
    cwd: Path = ROOT,
    binary: bool = False,
    check: bool = True,
) -> str | bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=not binary,
        check=False,
    )
    if check and result.returncode != 0:
        error = result.stderr or result.stdout
        if isinstance(error, bytes):
            error = error.decode("utf-8", errors="replace")
        raise OperatorError(f"git {' '.join(arguments)} failed: {str(error).strip()}")
    return result.stdout


def _clean_git_identity(repository: Path, *, label: str) -> tuple[str, str]:
    status = str(
        _git("status", "--porcelain=v1", "--untracked-files=all", cwd=repository)
    ).strip()
    if status:
        raise OperatorError(f"{label} worktree is dirty; commit the exact source seal")
    head = str(_git("rev-parse", "HEAD", cwd=repository)).strip()
    tree = str(_git("rev-parse", "HEAD^{tree}", cwd=repository)).strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not re.fullmatch(
        r"[0-9a-f]{40}", tree
    ):
        raise OperatorError(f"{label} Git identity is not exact")
    return head, tree


def _source_forest() -> dict[str, Any]:
    """Seal the outer tree and exactly the three required initialized gitlinks."""

    outer_head, outer_tree = _clean_git_identity(ROOT, label="portfolio")
    repositories: list[dict[str, str]] = []
    for repository, relative in SOURCE_REPOSITORIES:
        path = (ROOT / relative).resolve()
        if not path.is_dir():
            raise OperatorError(f"required repository is not initialized: {relative}")
        head, tree = _clean_git_identity(path, label=repository)
        row = str(_git("ls-tree", outer_head, "--", relative.as_posix())).strip().split()
        if len(row) < 3 or row[0] != "160000" or row[1] != "commit" or row[2] != head:
            raise OperatorError(f"{repository} HEAD differs from the portfolio gitlink")
        repositories.append(
            {
                "repository": repository,
                "path": relative.as_posix(),
                "head": head,
                "tree": tree,
            }
        )
    forest: dict[str, Any] = {
        "schema": "proof-carrying-platform-source-forest@1",
        "portfolio": {"head": outer_head, "tree": outer_tree},
        "repositories": repositories,
        "repository_count": len(repositories),
    }
    forest["source_forest_root"] = _identity(forest)
    return forest


def _tracked_bytes(path: Path, *, head: str) -> bytes:
    try:
        relative = path.resolve().relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise OperatorError(f"authority input escapes the portfolio: {path}") from exc
    if path.is_symlink() or not path.is_file():
        raise OperatorError(f"authority input is not a regular file: {relative}")
    committed = _git("show", f"{head}:{relative}", binary=True)
    working = path.read_bytes()
    if not isinstance(committed, bytes) or committed != working:
        raise OperatorError(f"authority input differs from current HEAD: {relative}")
    return working


def _load_config(config_path: Path) -> tuple[Any, dict[str, Any]]:
    if str(ACCEL_ROOT) not in sys.path:
        sys.path.insert(0, str(ACCEL_ROOT))
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        load_configured_board,
    )

    board = load_configured_board(config_path, repo_root=ROOT)
    config = dict(board.payload)
    if board.board_namespace != PROGRAM_ID:
        raise OperatorError("configured board namespace is not the sealed PCPR program")
    if board.task_prefix.removeprefix("## ") != TASK_PREFIX:
        raise OperatorError("configured board task prefix must be PCPR-")
    program = board.resolved_database_program()
    if (
        program.authority_mode != "quack"
        or program.task_source_kind != "duckdb"
        or program.failover_policy != "fail_closed"
    ):
        raise OperatorError("PCPR requires fail-closed DuckDB authority through Quack")
    endpoint = QUACK_RE.fullmatch(program.quack_endpoint)
    if endpoint is None or not 1 <= int(endpoint.group(2)) <= 65535:
        raise OperatorError("PCPR Quack endpoint must be a bounded loopback URI")
    if not program.endpoint_secret_handle:
        raise OperatorError("PCPR requires an opaque Quack secret handle")
    projection = config.get("initial_projection")
    projection = projection if isinstance(projection, Mapping) else {}
    if int(projection.get("task_count") or -1) != 1:
        raise OperatorError("PCPR immutable bootstrap must declare exactly one task")
    ready = [str(item) for item in projection.get("ready_task_ids", ())]
    if ready != [BOOTSTRAP_TASK]:
        raise OperatorError(f"PCPR initial frontier must be exactly {BOOTSTRAP_TASK}")
    return board, config


def _metadata_value(value: Any) -> str:
    text = str(value or "").strip()
    return text[2:].lstrip() if text.startswith("**") else text


def _csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _goal_blocks(text: str) -> list[tuple[str, str, dict[str, str]]]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.todo_vector_index import (
        normalize_metadata_key,
    )

    matches = list(GOAL_RE.finditer(text))
    blocks: list[tuple[str, str, dict[str, str]]] = []
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
                    f"{match.group(1)} contains duplicate metadata {normalized}"
                )
            fields[normalized] = _metadata_value(value)
        blocks.append((match.group(1), match.group(2).strip(), fields))
    return blocks


def _run_validator(board: Any) -> dict[str, Any]:
    validator = board.path(board.validator_path)
    command = [sys.executable, str(validator), "--check-all"]
    result = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        check=False,
        timeout=180,
    )
    receipt = {
        "argv": [sys.executable, str(validator.relative_to(ROOT)), "--check-all"],
        "returncode": int(result.returncode),
        "stdout_digest": _identity(result.stdout),
        "stderr_digest": _identity(result.stderr),
    }
    if result.returncode != 0:
        raise OperatorError("sealed PCPR bootstrap validator failed")
    receipt["validation_receipt_id"] = _identity(receipt)
    return receipt


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

    forest = _source_forest()
    head = str(forest["portfolio"]["head"])
    tree = str(forest["portfolio"]["tree"])
    required_branch = str(config.get("merge_target_branch") or "").strip()
    branch = str(_git("branch", "--show-current")).strip()
    if required_branch and branch != required_branch:
        raise OperatorError(
            f"portfolio branch {branch!r} differs from configured {required_branch!r}"
        )
    sources = {
        "config": _tracked_bytes(board.config_path, head=head),
        "taskboard": _tracked_bytes(board.path(board.taskboard_path), head=head),
        "objectives": _tracked_bytes(board.path(board.objectives_path), head=head),
        "plan": _tracked_bytes(board.path(board.plan_path), head=head),
        "generator": _tracked_bytes(
            ROOT
            / "scripts/generate_proof_carrying_platform_qualification_and_release_board.py",
            head=head,
        ),
        "validator": _tracked_bytes(board.path(board.validator_path), head=head),
        "operator": _tracked_bytes(Path(__file__).resolve(), head=head),
    }
    source_identities = {
        name: _identity(value) for name, value in sorted(sources.items())
    }
    plan_root = content_identity(
        {
            "schema": "proof-carrying-platform-plan-root@1",
            "source_head": head,
            "repository_tree_id": tree,
            "source_forest_root": forest["source_forest_root"],
            "source_identities": source_identities,
        }
    )

    goals_parsed = _goal_blocks(sources["objectives"].decode("utf-8"))
    if not goals_parsed or goals_parsed[0][0] != ROOT_GOAL:
        raise OperatorError(f"objective heap must begin with {ROOT_GOAL}")
    goal_ids = [item[0] for item in goals_parsed]
    if len(goal_ids) != len(set(goal_ids)):
        raise OperatorError("objective heap contains duplicate goal IDs")
    goal_cids = {
        goal_id: content_identity(
            {
                "goal_id": goal_id,
                "title": title,
                "metadata": fields,
                "plan_root_cid": plan_root,
            }
        )
        for goal_id, title, fields in goals_parsed
    }
    goals: list[dict[str, Any]] = []
    goal_edges: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ordinal, (goal_id, title, fields) in enumerate(goals_parsed, start=1):
        parent = str(fields.get("parent") or "").strip()
        if parent and parent not in seen:
            raise OperatorError(f"{goal_id} parent must precede it: {parent}")
        dependencies = _csv(fields.get("depends_on"))
        unknown = [item for item in dependencies if item not in goal_cids]
        if unknown:
            raise OperatorError(f"{goal_id} has unknown dependencies: {unknown}")
        goal: dict[str, Any] = {
            "goal_cid": goal_cids[goal_id],
            "goal_id": goal_id,
            "goal_alias": goal_id,
            "title": title,
            "ordinal": ordinal,
            "status": str(fields.get("status") or "open").lower(),
            "objective_id": "objective:pcpr-root" if goal_id == ROOT_GOAL else "",
            "objective_alias": ROOT_GOAL,
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
        seen.add(goal_id)

    parsed = parse_todo_blocks(
        sources["taskboard"].decode("utf-8"), task_header_prefix="## PCPR-"
    )
    if [item[0] for item in parsed] != [BOOTSTRAP_TASK]:
        raise OperatorError(f"sealed bootstrap board must contain only {BOOTSTRAP_TASK}")
    task_id, title, source_line, raw_fields = parsed[0]
    fields = {key: _metadata_value(value) for key, value in raw_fields.items()}
    dependencies = _csv(fields.get("depends_on"))
    if dependencies:
        raise OperatorError(f"{BOOTSTRAP_TASK} cannot depend on a non-materialized task")
    goal_id = str(
        fields.get("subgoal_id") or fields.get("goal_id") or fields.get("goal") or ROOT_GOAL
    ).strip()
    if goal_id not in goal_cids:
        raise OperatorError(f"{BOOTSTRAP_TASK} refers to unknown goal {goal_id}")
    task_cid = content_identity(
        {
            "task_id": task_id,
            "title": title,
            "source_line": source_line,
            "metadata": fields,
            "plan_root_cid": plan_root,
            "repository_tree_id": tree,
        }
    )
    output_paths = _csv(fields.get("outputs") or fields.get("predicted_files"))
    task = dict(fields)
    task.update(
        {
            "task_cid": task_cid,
            "task_id": task_id,
            "task_alias": task_id,
            "title": title,
            "source_line": source_line,
            "goal_cid": goal_cids[goal_id],
            "goal_id": goal_id,
            "plan_cid": plan_root,
            "objective_id": "objective:pcpr-root",
            "ordinal": 1,
            "status": str(fields.get("status") or "todo").lower(),
            "priority": str(fields.get("priority") or "P0"),
            "dependencies": [],
            "depends_on": [],
            "outputs": [
                {
                    "path": path,
                    "effect_id": content_identity({"task_cid": task_cid, "path": path}),
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
            "owning_repository": "ipfs_accelerate_py",
        }
    )
    if task["status"] not in READY_STATUSES:
        raise OperatorError(f"{BOOTSTRAP_TASK} must materialize dependency-ready")
    projection = config.get("initial_projection")
    projection = projection if isinstance(projection, Mapping) else {}
    if int(projection.get("goal_count") or -1) != len(goals):
        raise OperatorError("configured initial goal count differs from objective heap")
    population = {
        "schema": POPULATION_SCHEMA,
        "repository_tree_id": tree,
        "source_head": head,
        "plan_root_cid": plan_root,
        "source_identities": source_identities,
        "source_forest": forest,
        "objectives": goals,
        "goal_edges": goal_edges,
        "plans": [
            {
                "plan_cid": plan_root,
                "plan_alias": "PCPR-PLAN-V1",
                "goal_cid": goal_cids[ROOT_GOAL],
                "status": "active",
                "source_head": head,
                "repository_tree_id": tree,
            }
        ],
        "tasks": [task],
        "task_cids_by_alias": {task_id: task_cid},
        "goal_cids_by_alias": goal_cids,
    }
    return population


def _runtime_paths(board: Any) -> dict[str, Path]:
    program = board.resolved_database_program()
    runtime = board.path(board.runtime_paths["root"])
    database = _safe_path(program.store_id, field="database_program.store_id")
    raw = board.payload.get("runtime_paths")
    raw = raw if isinstance(raw, Mapping) else {}
    evidence = _safe_path(
        raw.get("evidence") or runtime.relative_to(ROOT) / "evidence",
        field="runtime_paths.evidence",
    )
    owner = _safe_path(
        raw.get("quack_owner") or runtime.relative_to(ROOT) / "quack-owner",
        field="runtime_paths.quack_owner",
    )
    logs = _safe_path(
        raw.get("logs") or runtime.relative_to(ROOT) / "logs",
        field="runtime_paths.logs",
    )
    state = _safe_path(
        raw.get("state") or runtime.relative_to(ROOT) / "state",
        field="runtime_paths.state",
    )
    ducklake = board.payload.get("ducklake_projection_program")
    ducklake = ducklake if isinstance(ducklake, Mapping) else {}
    catalog = _safe_path(
        ducklake.get("catalog_path")
        or runtime.relative_to(ROOT) / "ducklake" / "catalog.duckdb",
        field="ducklake_projection_program.catalog_path",
    )
    data = _safe_path(
        ducklake.get("data_path") or runtime.relative_to(ROOT) / "ducklake" / "data",
        field="ducklake_projection_program.data_path",
    )
    for label, path in {
        "database": database,
        "evidence": evidence,
        "owner": owner,
        "logs": logs,
        "state": state,
        "ducklake_catalog": catalog,
        "ducklake_data": data,
    }.items():
        try:
            path.relative_to(runtime)
        except ValueError as exc:
            raise OperatorError(f"{label} must be below runtime_paths.root") from exc
    return {
        "runtime": runtime,
        "database": database,
        "evidence": evidence,
        "owner": owner,
        "logs": logs,
        "state": state,
        "bootstrap_receipt": evidence / "bootstrap" / "bootstrap-materialization.json",
        "ducklake_receipt": evidence / "bootstrap" / "ducklake-history-projection.json",
        "ducklake_catalog": catalog,
        "ducklake_data": data,
        "owner_status": owner / "quack-state-server.status.json",
    }


def _owner_liveness(status: Mapping[str, Any]) -> str:
    from ipfs_accelerate_py.agent_supervisor.merge.worktree_lifecycle import (
        OwnerLiveness,
        ProcessBirthIdentity,
        owner_liveness,
    )

    identity = status.get("identity")
    birth = identity.get("process_birth") if isinstance(identity, Mapping) else None
    if not isinstance(birth, Mapping):
        return "absent" if not identity else "unknown"
    try:
        observed = owner_liveness(ProcessBirthIdentity.from_dict(birth))
    except Exception:
        return "unknown"
    if observed is OwnerLiveness.ALIVE:
        return "alive"
    if observed is OwnerLiveness.DEAD:
        return "dead"
    return "unknown"


def _owner_observation(paths: Mapping[str, Path], board: Any) -> dict[str, Any]:
    if not paths["owner_status"].is_file():
        return {"lifecycle": "absent", "liveness": "absent", "ready": False}
    try:
        status = _json_object(paths["owner_status"])
    except OperatorError:
        return {"lifecycle": "malformed", "liveness": "unknown", "ready": False}
    lifecycle = str(status.get("lifecycle") or "unknown")
    liveness = _owner_liveness(status)
    identity = status.get("identity")
    identity = identity if isinstance(identity, Mapping) else {}
    program = board.resolved_database_program()
    endpoint_ok = str(identity.get("listen_uri") or "") == program.quack_endpoint
    store_ok = str(identity.get("store_id") or "") == program.store_id
    ready = lifecycle == "ready" and liveness == "alive" and endpoint_ok and store_ok
    return {
        "lifecycle": lifecycle,
        "liveness": liveness,
        "ready": ready,
        "endpoint_matches_config": endpoint_ok,
        "store_matches_config": store_ok,
        "identity": dict(identity),
        "read_replica": status.get("read_replica"),
        "raw": status,
    }


def _ducklake_projection(
    *, paths: Mapping[str, Path], population: Mapping[str, Any], control: Mapping[str, Any]
) -> dict[str, Any]:
    projection: dict[str, Any] = {
        "schema": DUCKLAKE_SCHEMA,
        "status": "unavailable",
        "reason_code": "ducklake_projection_unavailable",
        "authoritative": False,
        "scheduler_gate": False,
        "completion_gate": False,
        "source_head": population["source_head"],
        "repository_tree_id": population["repository_tree_id"],
        "source_forest_root": population["source_forest"]["source_forest_root"],
        "plan_root_cid": population["plan_root_cid"],
    }
    connection = None
    try:
        import duckdb

        paths["ducklake_catalog"].parent.mkdir(parents=True, exist_ok=True)
        paths["ducklake_data"].mkdir(parents=True, exist_ok=True)
        connection = duckdb.connect(":memory:")
        connection.execute("LOAD ducklake")
        catalog = str(paths["ducklake_catalog"]).replace("'", "''")
        data = str(paths["ducklake_data"]).replace("'", "''")
        connection.execute(
            f"ATTACH 'ducklake:{catalog}' AS pcpr_history (DATA_PATH '{data}')"
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS pcpr_history.bootstrap_history (
              event_id VARCHAR, observed_at_epoch DOUBLE, source_head VARCHAR,
              repository_tree_id VARCHAR, source_forest_root VARCHAR,
              plan_root_cid VARCHAR, projection_cid VARCHAR, task_count BIGINT,
              goal_count BIGINT, body_json VARCHAR
            )
            """
        )
        event_id = _identity(
            {
                "source_head": population["source_head"],
                "source_forest_root": population["source_forest"]["source_forest_root"],
                "plan_root_cid": population["plan_root_cid"],
                "projection_cid": control.get("projection_cid"),
            }
        )
        count = connection.execute(
            "SELECT COUNT(*) FROM pcpr_history.bootstrap_history WHERE event_id = ?",
            [event_id],
        ).fetchone()
        if count is None or int(count[0]) == 0:
            connection.execute(
                "INSERT INTO pcpr_history.bootstrap_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    event_id,
                    time.time(),
                    population["source_head"],
                    population["repository_tree_id"],
                    population["source_forest"]["source_forest_root"],
                    population["plan_root_cid"],
                    str(control.get("projection_cid") or ""),
                    int(control.get("task_count") or 0),
                    int(control.get("goal_count") or 0),
                    json.dumps(
                        {
                            "authority": "DatabaseTaskSource@1 via Quack after bootstrap",
                            "non_authoritative_projection": True,
                        },
                        sort_keys=True,
                    ),
                ],
            )
        projection.update({"status": "projected", "reason_code": "", "event_id": event_id})
    except Exception as exc:
        projection["error_class"] = type(exc).__name__
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
    projection["projection_receipt_id"] = _identity(projection)
    _atomic_json(paths["ducklake_receipt"], projection)
    return projection


def materialize(config_path: Path) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    board, config = _load_config(config_path)
    paths = _runtime_paths(board)
    owner = _owner_observation(paths, board)
    if owner["liveness"] in {"alive", "unknown"}:
        raise OperatorError("cannot open authoritative DuckDB while an owner may be live")
    population = _population(board, config)
    validation = _run_validator(board)
    database_exists = paths["database"].exists()
    receipt_exists = paths["bootstrap_receipt"].exists()
    if database_exists != receipt_exists:
        raise OperatorError("partial bootstrap state exists; operator review is required")
    if database_exists:
        if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
            raise OperatorError("bootstrap authority paths are not regular files")
        prior = _json_object(paths["bootstrap_receipt"])
        for key in ("source_head", "repository_tree_id", "plan_root_cid"):
            if prior.get(key) != population.get(key):
                raise OperatorError("existing DuckDB authority has a different source seal")
        prior_forest = prior.get("source_forest")
        if not isinstance(prior_forest, Mapping) or prior_forest.get(
            "source_forest_root"
        ) != population["source_forest"]["source_forest_root"]:
            raise OperatorError("existing DuckDB authority has a different source forest")
        with DatabaseTaskSource(
            paths["database"],
            owner_id="pcpr-bootstrap:verify-existing",
            install_schema=False,
            repository_tree_id=str(population["repository_tree_id"]),
            plan_root_cid=str(population["plan_root_cid"]),
        ) as source:
            snapshot = source.snapshot().to_dict()
            ready = [item.task_alias for item in source.ready_tasks(limit=10).tasks]
        if (
            int(snapshot["task_count"]) != 1
            or int(snapshot["goal_count"]) != len(population["objectives"])
            or ready != [BOOTSTRAP_TASK]
        ):
            raise OperatorError("existing DuckDB projection differs from the sealed board")
        return {
            "schema": OPERATOR_SCHEMA,
            "command": "materialize",
            "materialized": True,
            "idempotent_replay": True,
            "bootstrap_receipt": prior,
            "snapshot": snapshot,
        }

    paths["runtime"].mkdir(parents=True, exist_ok=True)
    with DatabaseTaskSource(
        paths["database"],
        owner_id="pcpr-bootstrap:single-writer",
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        control = dict(source.materialize(population))
        snapshot = source.snapshot().to_dict()
        ready = [item.task_alias for item in source.ready_tasks(limit=10).tasks]
    if (
        int(snapshot["task_count"]) != 1
        or int(snapshot["goal_count"]) != len(population["objectives"])
        or ready != [BOOTSTRAP_TASK]
    ):
        raise OperatorError("DuckDB materialization does not match the sealed projection")
    ducklake = _ducklake_projection(paths=paths, population=population, control=control)
    receipt: dict[str, Any] = {
        "schema": BOOTSTRAP_SCHEMA,
        "source_head": population["source_head"],
        "repository_tree_id": population["repository_tree_id"],
        "source_forest": population["source_forest"],
        "plan_root_cid": population["plan_root_cid"],
        "source_identities": population["source_identities"],
        "database_task_source_receipt": control,
        "projection_cid": snapshot["projection_cid"],
        "task_count": snapshot["task_count"],
        "goal_count": snapshot["goal_count"],
        "dependency_count": snapshot["dependency_count"],
        "initial_ready_task_ids": ready,
        "bootstrap_validation": validation,
        "authority": {
            "semantic_state": "DuckDB/DatabaseTaskSource@1",
            "state_owner_transport": "QuackStateServer@1",
            "ducklake": "optional_non_authoritative_bootstrap_history",
        },
        "ducklake_projection": ducklake,
    }
    receipt["bootstrap_receipt_id"] = _identity(receipt)
    _atomic_json(paths["bootstrap_receipt"], receipt)
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "materialize",
        "materialized": True,
        "idempotent_replay": False,
        "bootstrap_receipt": receipt,
        "snapshot": snapshot,
    }


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
    environment["PYTHONUNBUFFERED"] = "1"
    return environment


def _assert_materialized_source(paths: Mapping[str, Path]) -> dict[str, Any]:
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise OperatorError("materialize the sealed PCPR bootstrap before starting services")
    receipt = _json_object(paths["bootstrap_receipt"])
    forest = _source_forest()
    if (
        receipt.get("source_head") != forest["portfolio"]["head"]
        or receipt.get("repository_tree_id") != forest["portfolio"]["tree"]
        or not isinstance(receipt.get("source_forest"), Mapping)
        or receipt["source_forest"].get("source_forest_root")
        != forest["source_forest_root"]
    ):
        raise OperatorError("current source forest differs from the materialized seal")
    return receipt


def state_owner(config_path: Path) -> int:
    """Replace this process with the existing Quack owner ops facade."""

    board, _config = _load_config(config_path)
    paths = _runtime_paths(board)
    _assert_materialized_source(paths)
    current = _owner_observation(paths, board)
    if current["liveness"] in {"alive", "unknown"}:
        raise OperatorError("a Quack state owner is already live or cannot be fenced")
    endpoint = QUACK_RE.fullmatch(board.resolved_database_program().quack_endpoint)
    assert endpoint is not None
    program = board.resolved_database_program()
    facade = ACCEL_ROOT / "scripts" / "ops" / "agent_supervisor" / "quack_state_server.py"
    argv = [
        sys.executable,
        str(facade),
        "--database",
        str(paths["database"]),
        "--state-dir",
        str(paths["owner"]),
        "--repository-root",
        str(ROOT),
        "--host",
        endpoint.group(1),
        "--port",
        endpoint.group(2),
        "--store-id",
        program.store_id,
        "--repository-id",
        f"repository:{PROGRAM_ID}",
        "--secret-handle",
        program.endpoint_secret_handle,
        "--allow-experimental",
        "--json",
        "start",
    ]
    environment = _python_environment()
    # A raw credential must never be inherited by or supplied to the owner.
    environment.pop("IPFS_ACCELERATE_AGENT_QUACK_TOKEN", None)
    environment.pop("IPFS_ACCELERATE_AGENT_QUACK_TOKEN_FILE", None)
    os.execvpe(sys.executable, argv, environment)
    return 1


def _pid(path: Path) -> int:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return 0
    return int(raw) if raw.isdigit() else 0


def _pid_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def start_state_owner_daemon(config_path: Path) -> dict[str, Any]:
    board, _config = _load_config(config_path)
    paths = _runtime_paths(board)
    _assert_materialized_source(paths)
    observed = _owner_observation(paths, board)
    if observed["ready"] is True:
        return {
            "schema": OPERATOR_SCHEMA,
            "command": "state-owner-daemon",
            "already_running": True,
            "ready": True,
        }
    if observed["liveness"] in {"alive", "unknown"}:
        raise OperatorError("an unready state-owner process cannot be safely replaced")
    pid_path = paths["state"] / "pcpr-state-owner.pid"
    prior = _pid(pid_path)
    if _pid_alive(prior):
        raise OperatorError("a detached state-owner PID is alive but not ready")
    log_path = paths["logs"] / "pcpr-state-owner.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--config",
        str(config_path),
        "state-owner",
    ]
    with log_path.open("ab", buffering=0) as handle:
        process = subprocess.Popen(
            argv,
            cwd=ROOT,
            env=_python_environment(),
            stdin=subprocess.DEVNULL,
            stdout=handle,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            close_fds=True,
        )
    _atomic_pid(pid_path, process.pid)
    deadline = time.monotonic() + 90.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise OperatorError("detached Quack owner exited before readiness")
        current = status(config_path)
        if (
            current["state_owner"]["ready"] is True
            and current["task_authority"].get("available") is True
            and current["task_authority"].get("quack_bound") is True
        ):
            return {
                "schema": OPERATOR_SCHEMA,
                "command": "state-owner-daemon",
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
    raise OperatorError("detached Quack owner did not become ready within 90 seconds")


def _task_status(connection: Any) -> dict[str, Any]:
    count_rows = connection.execute(
        "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY status"
    ).fetchall()
    counts = {str(row[0]): int(row[1]) for row in count_rows}
    task_rows = connection.execute(
        "SELECT task_cid, task_alias, ordinal, status FROM tasks ORDER BY ordinal, task_alias"
    ).fetchall()
    dependency_rows = connection.execute(
        "SELECT task_cid, dependency_task_cid FROM task_dependencies"
    ).fetchall()
    block_rows = connection.execute(
        "SELECT task_cid FROM task_blocks WHERE state = 'active'"
    ).fetchall()
    status_by_cid = {str(row[0]): str(row[3]) for row in task_rows}
    dependencies: dict[str, list[str]] = {}
    for task_cid, dependency_cid in dependency_rows:
        dependencies.setdefault(str(task_cid), []).append(str(dependency_cid))
    blocked = {str(row[0]) for row in block_rows}
    ready = [
        str(row[1])
        for row in task_rows
        if str(row[3]) in READY_STATUSES
        and str(row[0]) not in blocked
        and all(
            status_by_cid.get(dependency) in COMPLETED_STATUSES
            for dependency in dependencies.get(str(row[0]), ())
        )
    ]
    active = [str(row[1]) for row in task_rows if str(row[3]) in ACTIVE_STATUSES]
    pcpr = next(
        (
            {
                "task_cid": str(row[0]),
                "task_alias": str(row[1]),
                "status": str(row[3]),
                "dependency_ready": str(row[1]) in ready,
                "active": str(row[1]) in active,
            }
            for row in task_rows
            if str(row[1]) == BOOTSTRAP_TASK
        ),
        None,
    )
    status_blocked = sum(count for value, count in counts.items() if value == "blocked")
    return {
        "status_counts": counts,
        "task_count": sum(counts.values()),
        "dependency_ready_task_ids": ready,
        "active_task_ids": active,
        "blocked_count": len(blocked) + status_blocked,
        "terminal_count": sum(counts.get(item, 0) for item in TERMINAL_STATUSES),
        "bootstrap_task": pcpr,
        "bootstrap_task_active_or_ready": bool(
            pcpr and (pcpr["active"] or pcpr["dependency_ready"])
        ),
    }


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def _task_projection(
    *, paths: Mapping[str, Path], owner: Mapping[str, Any]
) -> dict[str, Any]:
    connection = None
    try:
        if owner["ready"] is True:
            raw = owner.get("read_replica")
            replica = raw if isinstance(raw, Mapping) else {}
            expected = paths["database"].with_name(
                f"{paths['database'].stem}.read-replica{paths['database'].suffix}"
            )
            observed = Path(str(replica.get("path") or ""))
            identity = owner.get("identity")
            identity = identity if isinstance(identity, Mapping) else {}
            if (
                replica.get("authority") != "non_authoritative_read_replica"
                or replica.get("live") is not True
                or observed != expected
                or str(replica.get("source_database_path") or "") != str(paths["database"])
                or str(replica.get("server_id") or "") != str(identity.get("server_id") or "")
                or int(replica.get("generation") or 0) != int(identity.get("generation") or 0)
                or not expected.is_file()
            ):
                raise OperatorError("live Quack checkpoint projection is not identity-bound")
            digest, size = _sha256_file(expected)
            if digest != str(replica.get("sha256") or "") or size != int(
                replica.get("size_bytes") or -1
            ):
                raise OperatorError("live Quack checkpoint digest or size differs")
            import duckdb

            connection = duckdb.connect(str(expected), read_only=True)
            return {
                "available": True,
                "quack_bound": True,
                "authoritative": False,
                "transport": "quack_owner_checkpointed_read_replica",
                "authority": "DuckDB/DatabaseTaskSource@1 via live Quack owner",
                "refresh_sequence": int(replica.get("refresh_sequence") or 0),
                **_task_status(connection),
            }
        if owner["liveness"] in {"absent", "dead"} and paths["database"].is_file():
            from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import (
                open_duckdb_connection,
            )

            connection = open_duckdb_connection(paths["database"])
            return {
                "available": True,
                "quack_bound": False,
                "authoritative": True,
                "transport": "direct_offline",
                **_task_status(connection),
            }
        return {"available": False, "reason_code": "quack_authority_unavailable"}
    except Exception as exc:
        return {
            "available": False,
            "reason_code": "task_projection_probe_failed",
            "error_class": type(exc).__name__,
        }
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass


def _parse_time(value: Any) -> float:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.timestamp()
    except (TypeError, ValueError):
        return 0.0


def _log_findings(paths: Mapping[str, Path]) -> dict[str, Any]:
    candidates: list[Path] = []
    for root in (paths["logs"], paths["state"]):
        if root.is_dir():
            candidates.extend(path for path in root.rglob("*.log") if path.is_file())
    candidates = sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)[:24]
    observations: list[dict[str, Any]] = []
    fatal_count = 0
    for path in candidates:
        try:
            size = path.stat().st_size
            with path.open("rb") as handle:
                handle.seek(max(0, size - 131_072))
                tail = handle.read(131_072)
            matches = len(FATAL_RE.findall(tail.decode("utf-8", errors="replace")))
            fatal_count += matches
            observations.append(
                {
                    "path": str(path.relative_to(ROOT)),
                    "size_bytes": size,
                    "mtime": path.stat().st_mtime,
                    "tail_digest": _identity(tail),
                    "fatal_or_quarantine_matches": matches,
                }
            )
        except OSError:
            continue
    return {"files": observations, "fatal_or_quarantine_count": fatal_count}


def _supervisor_status(board: Any, paths: Mapping[str, Path]) -> dict[str, Any]:
    master_pid = _pid(paths["state"] / "configured-board-master.pid")
    prefix = board.task_prefix.removeprefix("## ").rstrip("-").lower()
    expected = max(1, int(board.max_lanes))
    freshness = max(
        120.0, float(board.payload.get("check_interval_seconds") or 20.0) * 6.0
    )
    lanes: list[dict[str, Any]] = []
    bad_lane = False
    for index in range(expected):
        lane_dir = paths["state"] / f"lane-{index}"
        supervisor_pid = _pid(lane_dir / f"{prefix}_lane_{index}_supervisor.pid")
        daemon_pid = _pid(lane_dir / f"{prefix}_lane_{index}_managed_daemon.pid")
        status_path = lane_dir / f"{prefix}_lane_{index}_supervisor_status.json"
        projection: dict[str, Any] = {"status": "absent"}
        fresh = False
        bound = False
        if status_path.is_file():
            try:
                raw = _json_object(status_path)
                timestamp = _parse_time(raw.get("updated_at")) or status_path.stat().st_mtime
                age = max(0.0, time.time() - timestamp)
                state = str(raw.get("status") or "unknown").lower()
                fresh = age <= freshness
                pid_fields_match = (
                    int(raw.get("supervisor_pid") or supervisor_pid) == supervisor_pid
                    and int(raw.get("daemon_pid") or daemon_pid) == daemon_pid
                )
                bound = pid_fields_match and state not in {
                    "blocked",
                    "failed",
                    "quarantined",
                    "stopped",
                }
                projection = {
                    "status": state,
                    "updated_at": raw.get("updated_at"),
                    "age_seconds": age,
                    "restart_count": raw.get("restart_count"),
                }
            except (OperatorError, OSError, TypeError, ValueError):
                projection = {"status": "malformed"}
        supervisor_alive = _pid_alive(supervisor_pid) and fresh and bound
        daemon_alive = _pid_alive(daemon_pid) and fresh and bound
        bad_lane = bad_lane or projection["status"] in {
            "blocked",
            "failed",
            "quarantined",
            "malformed",
        }
        lanes.append(
            {
                "lane_index": index,
                "supervisor_pid": supervisor_pid,
                "supervisor_alive": supervisor_alive,
                "daemon_pid": daemon_pid,
                "daemon_alive": daemon_alive,
                "projection": projection,
            }
        )
    logs = _log_findings(paths)
    live_lanes = sum(1 for lane in lanes if lane["supervisor_alive"])
    live_daemons = sum(1 for lane in lanes if lane["daemon_alive"])
    no_fatal = not bad_lane and logs["fatal_or_quarantine_count"] == 0
    return {
        "ready": (
            _pid_alive(master_pid)
            and live_lanes == expected
            and live_daemons == expected
            and no_fatal
        ),
        "master_pid": master_pid,
        "master_alive": _pid_alive(master_pid),
        "expected_lane_count": expected,
        "live_lane_count": live_lanes,
        "live_daemon_count": live_daemons,
        "lanes": lanes,
        "logs": logs,
        "no_fatal_or_quarantine": no_fatal,
    }


def status(config_path: Path) -> dict[str, Any]:
    board, _config = _load_config(config_path)
    paths = _runtime_paths(board)
    owner = _owner_observation(paths, board)
    authority = _task_projection(paths=paths, owner=owner)
    supervisor = _supervisor_status(board, paths)
    ducklake: dict[str, Any] = {
        "status": "absent",
        "authoritative": False,
        "scheduler_gate": False,
    }
    if paths["ducklake_receipt"].is_file():
        try:
            receipt = _json_object(paths["ducklake_receipt"])
            ducklake.update(
                {
                    "status": str(receipt.get("status") or "unknown"),
                    "projection_receipt_id": str(
                        receipt.get("projection_receipt_id") or ""
                    ),
                }
            )
        except OperatorError:
            ducklake["status"] = "malformed"
    hard_failure = (
        int(authority.get("status_counts", {}).get("failed", 0))
        + int(authority.get("status_counts", {}).get("quarantined", 0))
        + int(supervisor["logs"]["fatal_or_quarantine_count"])
    )
    ready = bool(
        paths["bootstrap_receipt"].is_file()
        and owner["ready"] is True
        and authority.get("available") is True
        and authority.get("quack_bound") is True
        and supervisor["ready"] is True
        and int(authority.get("blocked_count") or 0) == 0
        and authority.get("bootstrap_task_active_or_ready") is True
        and hard_failure == 0
    )
    return {
        "schema": OPERATOR_SCHEMA,
        "command": "status",
        "ready": ready,
        "materialized": paths["database"].is_file()
        and paths["bootstrap_receipt"].is_file(),
        "state_owner": {key: value for key, value in owner.items() if key != "raw"},
        "task_authority": authority,
        "supervisor": supervisor,
        "blocked_count": int(authority.get("blocked_count") or 0),
        "bootstrap_task_active_or_ready": bool(
            authority.get("bootstrap_task_active_or_ready")
        ),
        "hard_failure_count": hard_failure,
        "no_fatal_or_quarantine": hard_failure == 0
        and supervisor["no_fatal_or_quarantine"] is True,
        "ducklake_projection": ducklake,
    }


def launch_supervisor(
    config_path: Path,
    *,
    dry_run: bool,
    foreground: bool,
    duration_seconds: float,
) -> int:
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        main as configured_board_main,
    )

    board, _config = _load_config(config_path)
    paths = _runtime_paths(board)
    _assert_materialized_source(paths)
    owner = _owner_observation(paths, board)
    if not dry_run and owner["ready"] is not True:
        raise OperatorError("Quack state owner must be live-ready before supervisor launch")
    if not dry_run:
        projection = _task_projection(paths=paths, owner=owner)
        if projection.get("available") is not True or projection.get("quack_bound") is not True:
            raise OperatorError("supervisor launch requires current Quack-bound task authority")
    if duration_seconds != float("inf") and duration_seconds <= 0:
        raise OperatorError("duration-seconds must be positive")
    common = ["--repo-root", str(ROOT), "--config", str(config_path)]
    preflight = int(configured_board_main([*common, "preflight"]))
    if preflight != 0:
        return preflight
    arguments = [*common, "launch", "--implement"]
    if dry_run:
        arguments.append("--dry-run")
    if foreground:
        arguments.append("--foreground")
    if duration_seconds != float("inf"):
        arguments.extend(["--duration-seconds", str(duration_seconds)])
    return int(configured_board_main(arguments))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("materialize")
    commands.add_parser("state-owner")
    commands.add_parser("state-owner-daemon")
    status_parser = commands.add_parser("status")
    status_parser.add_argument("--require-ready", action="store_true")
    launch = commands.add_parser("launch-supervisor")
    launch.add_argument("--dry-run", action="store_true")
    launch.add_argument("--foreground", action="store_true")
    launch.add_argument("--duration-seconds", type=float, default=float("inf"))
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
        if arguments.command == "state-owner-daemon":
            result = start_state_owner_daemon(config_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if arguments.command == "status":
            result = status(config_path)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if not arguments.require_ready or result["ready"] else 1
        if arguments.command == "launch-supervisor":
            return launch_supervisor(
                config_path,
                dry_run=bool(arguments.dry_run),
                foreground=bool(arguments.foreground),
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
