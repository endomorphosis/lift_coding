#!/usr/bin/env python3
"""Materialize the sealed PCTDD program into its existing task authority.

The tracked Markdown documents are an immutable bootstrap projection only.
This adapter parses them with the agent-supervisor's canonical parsers and
materializes their semantic records through ``DatabaseTaskSource@1``.  It does
not issue task SQL and it does not create another scheduler or state owner.

``PCTDD-000`` is deliberately inserted as non-schedulable staged operator
work even though its Markdown display remains ``todo``.  ``materialize`` never
completes it.  A separate ``seal-controls`` stage must pass the sealed profile,
both validators, canonical preflight, and implementation dry-run at one exact
tree before the task source's compare-and-set completion gate may advance it.
Consequently Markdown status is never completion authority.

DuckLake is an optional, rebuildable bootstrap-history projection.  A missing
or unusable extension produces a typed-unavailable receipt and never changes
the DuckDB materialization, ready frontier, or completion decision.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Final

ROOT: Final[Path] = Path(__file__).resolve().parents[1]
ACCEL_ROOT: Final[Path] = ROOT / "external" / "ipfs_accelerate"
DEFAULT_CONFIG: Final[str] = (
    "config/agent_supervisor_parallel_content_sealing_"
    "proof_carrying_tdd_scheduler.json"
)
PROGRAM_ID: Final[str] = "parallel-content-sealing-proof-carrying-tdd-v1"
PLAN_ALIAS: Final[str] = "PCTDD-PLAN-V1.1"
VALIDATION_PROFILE_RELATIVE: Final[str] = (
    "config/parallel_content_sealing_proof_carrying_tdd_validation_profiles.json"
)
VALIDATION_DISPATCHER_RELATIVE: Final[str] = (
    "scripts/run_parallel_content_sealing_proof_carrying_tdd_validation.py"
)
CONFIGURED_SCHEDULER_RELATIVE: Final[str] = (
    "external/ipfs_accelerate/scripts/ops/agent_supervisor/configured_board_scheduler.py"
)
CONTROL_MANIFEST_RELATIVE: Final[str] = (
    "config/parallel_content_sealing_proof_carrying_tdd_control_manifest.json"
)
ROOT_GOAL_ID: Final[str] = "PCTDD-G000"
OPERATOR_TASK_ID: Final[str] = "PCTDD-000"
TASK_IDS: Final[tuple[str, ...]] = tuple(f"PCTDD-{index:03d}" for index in range(54))
INITIAL_READY: Final[tuple[str, ...]] = (
    "PCTDD-001",
    "PCTDD-002",
    "PCTDD-003",
    "PCTDD-004",
)
POPULATION_SCHEMA: Final[str] = (
    "ipfs_accelerate_py.agent_supervisor."
    "parallel-content-sealing-proof-carrying-tdd.population@1"
)
CHECK_SCHEMA: Final[str] = (
    "ipfs_accelerate_py.agent_supervisor."
    "parallel-content-sealing-proof-carrying-tdd.materializer-check@1"
)
BOOTSTRAP_SCHEMA: Final[str] = (
    "ipfs_accelerate_py.agent_supervisor."
    "parallel-content-sealing-proof-carrying-tdd.bootstrap-receipt@1"
)
DUCKLAKE_SCHEMA: Final[str] = (
    "ipfs_accelerate_py.agent_supervisor."
    "parallel-content-sealing-proof-carrying-tdd.ducklake-bootstrap-history@1"
)
CONTROL_EVIDENCE_SCHEMA: Final[str] = (
    "ipfs_accelerate_py.agent_supervisor."
    "parallel-content-sealing-proof-carrying-tdd.control-program-seal@1"
)
STAGED_SCHEMA: Final[str] = (
    "ipfs_accelerate_py.agent_supervisor."
    "parallel-content-sealing-proof-carrying-tdd.staged-materialization@1"
)
TASK_EXTRA_OUTPUTS: Final[dict[str, tuple[str, ...]]] = {
    "PCTDD-000": (CONTROL_MANIFEST_RELATIVE,),
    "PCTDD-049": (
        "benchmarks/agent_supervisor/parallel_content_sealing/pctdd_049_hash_seal_results.json",
    ),
    "PCTDD-050": (
        "benchmarks/agent_supervisor/proof_carrying_tdd/pctdd_050_pytest_proof_tdd_results.json",
    ),
    "PCTDD-052": (
        "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/fast_tdd/capstone_self_hosting.py",
        "artifacts/parallel_content_sealing_proof_carrying_tdd/capstone/PCTDD-052.json",
    ),
    "PCTDD-053": (
        "artifacts/parallel_content_sealing_proof_carrying_tdd/PCTDD-053.release.json",
        "docs/architecture/PARALLEL_CONTENT_SEALING_PROOF_CARRYING_TDD_RELEASE.md",
    ),
}
GOAL_RE: Final[re.Pattern[str]] = re.compile(
    r"^##[ \t]+(PCTDD-G\d{3})[ \t]+([^\n]+?)[ \t]*$", re.MULTILINE
)
SAFE_RELATIVE_RE: Final[re.Pattern[str]] = re.compile(r"^[^\x00\r\n]+$")


class MaterializationError(RuntimeError):
    """The sealed bootstrap program cannot be materialized safely."""


def _install_import_roots() -> None:
    """Expose the authoritative accelerator checkout without importing it."""

    for path in (ACCEL_ROOT, ROOT):
        value = str(path)
        if value not in sys.path:
            sys.path.insert(0, value)


def _json_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise MaterializationError("receipt is not canonical JSON") from exc


def _print_json(value: Mapping[str, Any]) -> None:
    sys.stdout.buffer.write(_json_bytes(value))


def _sha256(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _git(*arguments: str, binary: bool = False, cwd: Path = ROOT) -> str | bytes:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=cwd,
        capture_output=True,
        text=not binary,
        check=False,
    )
    if completed.returncode != 0:
        error = completed.stderr or completed.stdout
        if isinstance(error, bytes):
            error = error.decode("utf-8", errors="replace")
        raise MaterializationError(
            f"git {' '.join(arguments)} failed: {str(error).strip()}"
        )
    return completed.stdout


def _safe_relative(value: str | Path, *, field: str) -> str:
    text = str(value or "").strip()
    path = PurePosixPath(text)
    if (
        not text
        or SAFE_RELATIVE_RE.fullmatch(text) is None
        or path.is_absolute()
        or ".." in path.parts
        or "." in path.parts
    ):
        raise MaterializationError(f"{field} must be a safe repository-relative path")
    normalized = path.as_posix()
    if normalized != text:
        raise MaterializationError(f"{field} must be normalized")
    return normalized


def _repo_path(value: str | Path, *, field: str) -> Path:
    relative = _safe_relative(value, field=field)
    candidate = (ROOT / relative).resolve(strict=False)
    try:
        candidate.relative_to(ROOT)
    except ValueError as exc:
        raise MaterializationError(f"{field} escapes the repository") from exc
    return candidate


def _regular_file(path: Path, *, field: str) -> None:
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise MaterializationError(f"{field} is absent or unreadable") from exc
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
        raise MaterializationError(f"{field} must be a regular non-symlink file")


def _assert_clean_current_tree(config: Mapping[str, Any]) -> tuple[str, str, str]:
    status_output = str(
        _git("status", "--porcelain=v1", "--untracked-files=all")
    ).strip()
    if status_output:
        raise MaterializationError(
            "refusing a dirty worktree; commit the exact PCTDD controls first"
        )
    head = str(_git("rev-parse", "HEAD")).strip()
    tree = str(_git("rev-parse", "HEAD^{tree}")).strip()
    branch = str(_git("branch", "--show-current")).strip()
    expected_branch = str(config.get("merge_target_branch") or "").strip()
    if expected_branch and branch != expected_branch:
        raise MaterializationError(
            f"current branch {branch!r} differs from configured branch "
            f"{expected_branch!r}"
        )
    if re.fullmatch(r"[0-9a-f]{40}", head) is None:
        raise MaterializationError("current HEAD is not an exact Git commit")
    if re.fullmatch(r"[0-9a-f]{40}", tree) is None:
        raise MaterializationError("current tree is not an exact Git tree")
    return head, tree, branch


def _assert_source_unchanged(
    config: Mapping[str, Any],
    *,
    head: str,
    tree: str,
) -> None:
    current_head, current_tree, _branch = _assert_clean_current_tree(config)
    if current_head != head or current_tree != tree:
        raise MaterializationError("repository source changed during materialization")


def _tracked_bytes(path: Path, *, head: str, field: str) -> bytes:
    _regular_file(path, field=field)
    try:
        relative = path.relative_to(ROOT).as_posix()
    except ValueError as exc:
        raise MaterializationError(f"{field} escapes the repository") from exc
    working = path.read_bytes()
    recorded = _git("show", f"{head}:{relative}", binary=True)
    if not isinstance(recorded, bytes) or working != recorded:
        raise MaterializationError(f"{field} differs from current HEAD")
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if tracked.returncode != 0:
        raise MaterializationError(f"{field} is not tracked by Git")
    return working


def _load_json_bytes(raw: bytes, *, field: str) -> dict[str, Any]:
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise MaterializationError(f"{field} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicates)
    except MaterializationError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MaterializationError(f"{field} is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise MaterializationError(f"{field} root must be an object")
    return value


def _validated_profiles(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    dispatcher = ROOT / VALIDATION_DISPATCHER_RELATIVE
    spec = importlib.util.spec_from_file_location("pctdd_materializer_validation", dispatcher)
    if spec is None or spec.loader is None:
        raise MaterializationError("cannot load protected validation dispatcher")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        profiles = module.validate_profile_document(payload)
    except Exception as exc:
        raise MaterializationError(
            f"sealed validation profiles rejected: {type(exc).__name__}: {exc}"
        ) from exc
    return dict(profiles)


def _task_validation_binding(
    task_id: str,
    fields: Mapping[str, Any],
    output_paths: Sequence[str],
    profiles: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str]:
    profile = profiles.get(task_id)
    if not isinstance(profile, Mapping):
        raise MaterializationError(f"{task_id} has no resolved sealed validation profile")
    expected_profile_id = f"pctdd-validation/{PLAN_ALIAS}/{task_id}@1"
    if str(fields.get("validation_profile") or "") != expected_profile_id:
        raise MaterializationError(f"{task_id} validation profile binding differs")
    validation = str(
        fields.get("validation") or fields.get("validation_command") or ""
    ).strip()
    expected_validation = f"python {VALIDATION_DISPATCHER_RELATIVE} --task {task_id}"
    if validation != expected_validation:
        raise MaterializationError(
            f"{task_id} validation is unresolved prose or differs from its protected dispatcher"
        )
    expected_test_target = str(profile.get("required_test_target") or "")
    expected_receipt = (
        "artifacts/parallel_content_sealing_proof_carrying_tdd/receipts/"
        f"{task_id}.json"
    )
    expected_outputs = {
        expected_receipt,
        expected_test_target,
        *TASK_EXTRA_OUTPUTS.get(task_id, ()),
    }
    if set(output_paths) != expected_outputs:
        raise MaterializationError(
            f"{task_id} exact output manifest differs"
        )
    expected_role = "operator-only" if task_id == OPERATOR_TASK_ID else "grok-only"
    if str(fields.get("provider_role") or "") != expected_role:
        raise MaterializationError(f"{task_id} provider role is not current-parser exact")
    if str(fields.get("llm_context_budget_bytes") or "") != "24000":
        raise MaterializationError(f"{task_id} llm_context_budget_bytes differs")
    acceptance = str(fields.get("acceptance") or fields.get("acceptance_criteria") or "")
    if task_id != OPERATOR_TASK_ID and not all(
        phrase in acceptance
        for phrase in (
            "controller-owned validation authority independently executes",
            "implementation model cannot fall back",
            "worker-authored test alone is never sufficient",
            "protected baseline regressions",
        )
    ):
        raise MaterializationError(f"{task_id} lacks independent controller admission")
    return validation, expected_profile_id


def _load_board(config_path: Path) -> tuple[Any, dict[str, Any], bytes]:
    _install_import_roots()
    from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
        load_configured_board,
    )

    _regular_file(config_path, field="scheduler config")
    config_bytes = config_path.read_bytes()
    config_payload = _load_json_bytes(config_bytes, field="scheduler config")
    board = load_configured_board(config_path, repo_root=ROOT)
    if board.board_namespace != PROGRAM_ID:
        raise MaterializationError("scheduler board namespace is not PCTDD v1")
    if board.task_prefix.removeprefix("## ") != "PCTDD-":
        raise MaterializationError("scheduler task prefix is not PCTDD-")
    program = board.resolved_database_program()
    if program.authority_mode != "quack" or program.task_source_kind != "duckdb":
        raise MaterializationError("PCTDD requires DuckDB authority served through Quack")
    if program.failover_policy != "fail_closed":
        raise MaterializationError("PCTDD database authority must fail closed")
    if str(config_payload.get("accepted_plan_revision_alias") or "") != PLAN_ALIAS:
        raise MaterializationError("PCTDD plan revision is not the V1.1 amendment")
    if program.store_generation not in {
        "pctdd-v1-g6",
        "pctdd-v1-g7",
        "pctdd-v1-g8",
    }:
        raise MaterializationError(
            "PCTDD materialization requires the sealed g6, g7, or g8 store"
        )
    if program.store_generation == "pctdd-v1-g7" and not isinstance(
        config_payload.get("source_binding_successor_materialization"), Mapping
    ):
        raise MaterializationError("PCTDD g7 requires its sealed source-binding successor policy")
    if program.store_generation == "pctdd-v1-g8" and not isinstance(
        config_payload.get("source_provider_route_successor_materialization"),
        Mapping,
    ):
        raise MaterializationError(
            "PCTDD g8 requires its sealed source/provider-route successor policy"
        )
    if program.quack_endpoint != "quack:127.0.0.1:27278":
        raise MaterializationError("PCTDD materialization requires the sealed Quack endpoint")
    return board, config_payload, config_bytes


def _split_csv(value: Any) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _references(value: Any) -> list[str]:
    references = _split_csv(value)
    if len(references) == 1 and references[0].lower() in {
        "none",
        "null",
        "not_applicable",
        "not applicable",
    }:
        return []
    return references


def _assert_acyclic_dependencies(
    dependencies: Mapping[str, Sequence[str]],
) -> None:
    remaining = {
        task_id: set(required)
        for task_id, required in dependencies.items()
    }
    dependents: dict[str, set[str]] = {task_id: set() for task_id in remaining}
    for task_id, required in remaining.items():
        for dependency in required:
            dependents[dependency].add(task_id)
    ready = sorted(task_id for task_id, required in remaining.items() if not required)
    visited: set[str] = set()
    while ready:
        task_id = ready.pop(0)
        if task_id in visited:
            continue
        visited.add(task_id)
        for dependent in sorted(dependents[task_id]):
            remaining[dependent].discard(task_id)
            if not remaining[dependent] and dependent not in visited:
                ready.append(dependent)
        ready.sort()
    if len(visited) != len(remaining):
        cycle = sorted(set(remaining) - visited)
        raise MaterializationError(
            "task dependency graph contains a cycle: " + ", ".join(cycle)
        )


def _goal_blocks(text: str) -> list[tuple[str, str, dict[str, str]]]:
    _install_import_roots()
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
                raise MaterializationError(
                    f"{match.group(1)} contains duplicate field {normalized}"
                )
            fields[normalized] = value.strip()
        blocks.append((match.group(1), match.group(2).strip(), fields))
    return blocks


def _source_forest(board: Any, *, head: str, tree: str, branch: str) -> dict[str, Any]:
    # Bind remote configuration without copying a possibly credential-bearing
    # URL into public task evidence.
    root_origin = str(_git("config", "--get", "remote.origin.url")).strip()
    repositories: list[dict[str, Any]] = [
        {
            "authority": "workspace",
            "path": ".",
            "head": head,
            "tree": tree,
            "branch": branch,
            "origin_sha256": _sha256(root_origin.encode("utf-8")),
        }
    ]
    for relative in board.worktree_submodule_paths:
        submodule = _repo_path(relative, field="worktree_submodule_paths entry")
        if not (submodule / ".git").exists():
            raise MaterializationError(f"configured submodule is not initialized: {relative}")
        sub_head = str(_git("rev-parse", "HEAD", cwd=submodule)).strip()
        sub_tree = str(_git("rev-parse", "HEAD^{tree}", cwd=submodule)).strip()
        sub_branch = str(_git("branch", "--show-current", cwd=submodule)).strip()
        sub_origin = str(
            _git("config", "--get", "remote.origin.url", cwd=submodule)
        ).strip()
        tree_row = str(_git("ls-tree", head, "--", relative)).strip().split()
        if (
            len(tree_row) < 3
            or tree_row[0] != "160000"
            or tree_row[1] != "commit"
            or tree_row[2] != sub_head
        ):
            raise MaterializationError(
                f"configured submodule HEAD differs from outer gitlink: {relative}"
            )
        nested_status = str(
            _git("status", "--porcelain=v1", "--untracked-files=all", cwd=submodule)
        ).strip()
        if nested_status:
            raise MaterializationError(f"configured submodule is dirty: {relative}")
        repositories.append(
            {
                "authority": Path(relative).name,
                "path": relative,
                "head": sub_head,
                "tree": sub_tree,
                "branch": sub_branch,
                "origin_sha256": _sha256(sub_origin.encode("utf-8")),
                "gitlink": sub_head,
            }
        )
    payload: dict[str, Any] = {
        "schema": "pctdd-source-forest@1",
        "repositories": repositories,
    }
    _install_import_roots()
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        content_identity,
    )

    payload["source_forest_root"] = content_identity(payload)
    return payload


def _control_sources(
    board: Any,
    config_path: Path,
    *,
    head: str,
) -> dict[str, bytes]:
    paths: dict[str, Path] = {
        "config": config_path,
        "taskboard": board.path(board.taskboard_path),
        "objectives": board.path(board.objectives_path),
        "plan": board.path(board.plan_path),
        "validator": board.path(board.validator_path),
        "materializer": Path(__file__).resolve(),
        "dependency_seal": ROOT
        / "config/parallel_content_sealing_proof_carrying_tdd_dependencies.seal.json",
        "dependency_validator": ROOT
        / "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
    }
    for index, relative in enumerate(board.protected_paths):
        candidate = _repo_path(relative, field=f"protected_paths[{index}]")
        if candidate.is_file() and not candidate.is_symlink():
            paths.setdefault(f"protected:{relative}", candidate)
            continue
        if candidate.is_dir() and not candidate.is_symlink():
            listing = str(_git("ls-files", "--", relative)).splitlines()
            if not listing:
                raise MaterializationError(
                    f"protected directory has no tracked controls: {relative}"
                )
            for tracked_relative in listing:
                tracked_path = _repo_path(
                    tracked_relative,
                    field=f"tracked member of protected_paths[{index}]",
                )
                paths.setdefault(f"protected:{tracked_relative}", tracked_path)
            continue
        raise MaterializationError(
            f"protected path is absent, a symlink, or not a file/directory: {relative}"
        )
    sources: dict[str, bytes] = {}
    for name, path in sorted(paths.items()):
        sources[name] = _tracked_bytes(path, head=head, field=name)
    return sources


def _population(board: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    _install_import_roots()
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.task_identity import (
        canonical_task_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.todo_vector_index import (
        parse_todo_blocks,
    )
    head, tree, branch = _assert_clean_current_tree(config)
    source_forest = _source_forest(board, head=head, tree=tree, branch=branch)
    sources = _control_sources(board, board.config_path, head=head)
    source_identities = {
        name: _sha256(value) for name, value in sorted(sources.items())
    }
    profile_key = f"protected:{VALIDATION_PROFILE_RELATIVE}"
    if profile_key not in sources:
        raise MaterializationError("protected validation profile document is not sealed")
    profiles = _validated_profiles(
        _load_json_bytes(sources[profile_key], field="validation profiles")
    )
    plan_root = content_identity(
        {
            "schema": "pctdd-plan-root@1",
            "program_id": PROGRAM_ID,
            "plan_alias": PLAN_ALIAS,
            "source_head": head,
            "repository_tree_id": tree,
            "source_forest_root": source_forest["source_forest_root"],
            "source_identities": source_identities,
        }
    )

    try:
        objective_text = sources["objectives"].decode("utf-8")
        task_text = sources["taskboard"].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MaterializationError("objectives and taskboard must be UTF-8") from exc

    parsed_goals = _goal_blocks(objective_text)
    if not parsed_goals or parsed_goals[0][0] != ROOT_GOAL_ID:
        raise MaterializationError(f"objectives must begin with {ROOT_GOAL_ID}")
    goal_ids = [item[0] for item in parsed_goals]
    if len(goal_ids) != len(set(goal_ids)):
        raise MaterializationError("objectives contain duplicate goal IDs")
    goal_cids = {
        goal_id: content_identity(
            {
                "schema": "pctdd-goal@1",
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
        parent = str(fields.get("parent") or fields.get("parent_goal") or "").strip()
        if parent.lower() in {"none", "null", "root", "not_applicable", "not applicable"}:
            parent = ""
        if parent and parent not in observed_goals:
            raise MaterializationError(f"{goal_id} parent must precede it: {parent}")
        dependencies = _references(fields.get("depends_on"))
        unknown = sorted(set(dependencies) - set(goal_cids))
        if unknown:
            raise MaterializationError(f"{goal_id} has unknown dependencies: {unknown}")
        goal: dict[str, Any] = {
            "goal_cid": goal_cids[goal_id],
            "goal_id": goal_id,
            "goal_alias": goal_id,
            "title": title,
            "ordinal": ordinal,
            "status": str(fields.get("status") or "active").lower(),
            "objective_id": "objective:pctdd-root" if goal_id == ROOT_GOAL_ID else "",
            "objective_alias": ROOT_GOAL_ID,
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

    parsed_tasks = parse_todo_blocks(task_text, task_header_prefix="## PCTDD-")
    parsed_ids = tuple(item[0] for item in parsed_tasks)
    if parsed_ids != TASK_IDS:
        raise MaterializationError(
            "taskboard must contain exactly PCTDD-000 through PCTDD-053 in order"
        )
    canonical_cids: dict[str, str] = {}
    for task_id, title, _source_line, fields in parsed_tasks:
        outputs = tuple(_split_csv(fields.get("outputs")))
        identity = canonical_task_identity(
            {
                "task_id": task_id,
                "title": title,
                "outputs": outputs,
                "acceptance": str(
                    fields.get("acceptance") or fields.get("acceptance_criteria") or ""
                ),
                "metadata": fields,
            },
            board_namespace=board.board_namespace,
            source_path=board.path(board.taskboard_path),
        )
        canonical_cids[task_id] = identity.canonical_task_cid

    tasks: list[dict[str, Any]] = []
    dependency_aliases: dict[str, tuple[str, ...]] = {}
    for ordinal, (task_id, title, source_line, fields) in enumerate(
        parsed_tasks, start=1
    ):
        declared_status = str(fields.get("status") or "todo").strip().lower()
        if task_id != OPERATOR_TASK_ID and declared_status in {
            "complete",
            "completed",
            "done",
            "skipped",
        }:
            raise MaterializationError(
                f"{task_id} cannot claim completion from Markdown"
            )
        dependencies = tuple(_references(fields.get("depends_on")))
        unknown = sorted(set(dependencies) - set(canonical_cids))
        if unknown:
            raise MaterializationError(f"{task_id} has unknown dependencies: {unknown}")
        goal_id = str(
            fields.get("subgoal_id")
            or fields.get("goal_id")
            or fields.get("goal")
            or ROOT_GOAL_ID
        ).strip()
        if goal_id not in goal_cids:
            raise MaterializationError(f"{task_id} refers to unknown goal {goal_id}")
        output_paths = _split_csv(fields.get("outputs") or fields.get("predicted_files"))
        acceptance_text = str(
            fields.get("acceptance") or fields.get("acceptance_criteria") or ""
        ).strip()
        if not acceptance_text:
            raise MaterializationError(f"{task_id} has no acceptance criterion")
        validation, expected_profile_id = _task_validation_binding(
            task_id, fields, output_paths, profiles
        )
        acceptance: list[Mapping[str, Any] | str]
        if task_id == OPERATOR_TASK_ID:
            acceptance = [
                {
                    "criterion": acceptance_text,
                    "evidence_kind": "control_program_seal",
                }
            ]
        else:
            acceptance = [acceptance_text]
        task = dict(fields)
        task.update(
            {
                "task_cid": canonical_cids[task_id],
                "task_id": task_id,
                "task_alias": task_id,
                "title": title,
                "source_line": source_line,
                "goal_cid": goal_cids[goal_id],
                "goal_id": goal_id,
                "plan_cid": plan_root,
                "objective_id": "objective:pctdd-root",
                "ordinal": ordinal,
                # Markdown status is display metadata, never completion authority.
                # The operator task is staged as non-schedulable in_progress;
                # only seal-controls may advance it to completed.
                "status": "in_progress" if task_id == OPERATOR_TASK_ID else "todo",
                "declared_markdown_status": declared_status,
                "priority": str(fields.get("priority") or "P1"),
                "dependencies": [canonical_cids[item] for item in dependencies],
                "depends_on": [canonical_cids[item] for item in dependencies],
                "outputs": [
                    {
                        "path": path,
                        "effect_id": content_identity(
                            {"task_cid": canonical_cids[task_id], "path": path}
                        ),
                    }
                    for path in output_paths
                ],
                "acceptance": acceptance,
                "validations": [validation],
                "validation_profile_id": expected_profile_id,
                "accepted_plan_root_cid": plan_root,
                "base_revision": head,
                "base_repository_tree_id": tree,
            }
        )
        tasks.append(task)
        dependency_aliases[task_id] = dependencies

    _assert_acyclic_dependencies(dependency_aliases)

    projection = config.get("initial_projection")
    projection = projection if isinstance(projection, Mapping) else {}
    expected_task_count = int(projection.get("task_count") or len(tasks))
    expected_goal_count = int(projection.get("goal_count") or len(goals))
    dependency_count = sum(len(value) for value in dependency_aliases.values())
    expected_dependency_count = int(
        projection.get("task_dependency_count") or dependency_count
    )
    if expected_task_count != len(tasks) or len(tasks) != len(TASK_IDS):
        raise MaterializationError("configured initial task count is not exactly 54")
    if expected_goal_count != len(goals):
        raise MaterializationError("configured initial goal count differs from objectives")
    if expected_dependency_count != dependency_count:
        raise MaterializationError("configured task dependency count differs from board")
    configured_completed = tuple(
        str(item) for item in projection.get("completed_task_ids", ())
    )
    if configured_completed:
        raise MaterializationError(
            "initial_projection.completed_task_ids must be empty before operator sealing"
        )
    anticipated_ready = tuple(
        task_id
        for task_id in TASK_IDS
        if task_id != OPERATOR_TASK_ID
        and set(dependency_aliases[task_id]).issubset({OPERATOR_TASK_ID})
    )
    configured_ready = tuple(
        str(item) for item in projection.get("ready_task_ids", ())
    )
    post_completed = tuple(
        str(item) for item in projection.get("post_operator_completed_task_ids", ())
    )
    post_ready = tuple(
        str(item) for item in projection.get("post_operator_ready_task_ids", ())
    )
    if (
        anticipated_ready != INITIAL_READY
        or configured_ready
        or post_completed != (OPERATOR_TASK_ID,)
        or post_ready != INITIAL_READY
    ):
        raise MaterializationError(
            "staged and post-PCTDD-000 readiness projections differ"
        )

    return {
        "schema": POPULATION_SCHEMA,
        "program_id": PROGRAM_ID,
        "repository_tree_id": tree,
        "source_head": head,
        "source_branch": branch,
        "plan_root_cid": plan_root,
        "source_identities": source_identities,
        "source_forest": source_forest,
        "objectives": goals,
        "goal_edges": goal_edges,
        "plans": [
            {
                "plan_cid": plan_root,
                "plan_alias": PLAN_ALIAS,
                "goal_cid": goal_cids[ROOT_GOAL_ID],
                "status": "active",
                "source_head": head,
                "repository_tree_id": tree,
            }
        ],
        "tasks": tasks,
        "task_cids_by_alias": canonical_cids,
        "goal_cids_by_alias": goal_cids,
        "task_dependency_count": dependency_count,
        "post_operator_ready_task_ids": list(INITIAL_READY),
    }


def _safe_runtime_path(root: Path, value: str | Path, *, field: str) -> Path:
    candidate = _repo_path(value, field=field)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise MaterializationError(f"{field} must be below runtime_paths.root") from exc
    return candidate


def _runtime_paths(board: Any) -> dict[str, Path]:
    runtime = board.path(board.runtime_paths["root"])
    program = board.resolved_database_program()
    database = _safe_runtime_path(
        runtime, program.store_id, field="database_program.store_id"
    )
    raw_runtime = board.payload.get("runtime_paths")
    raw_runtime = raw_runtime if isinstance(raw_runtime, Mapping) else {}
    evidence = _safe_runtime_path(
        runtime,
        raw_runtime.get("evidence")
        or (Path(board.runtime_paths["root"]) / "evidence").as_posix(),
        field="runtime_paths.evidence",
    )
    raw_lake = board.payload.get("ducklake_projection_program")
    raw_lake = raw_lake if isinstance(raw_lake, Mapping) else {}
    ducklake_catalog = _safe_runtime_path(
        runtime,
        raw_lake.get("catalog_path")
        or (Path(board.runtime_paths["root"]) / "ducklake" / "catalog.ducklake").as_posix(),
        field="ducklake_projection_program.catalog_path",
    )
    ducklake_data = _safe_runtime_path(
        runtime,
        raw_lake.get("data_path")
        or (Path(board.runtime_paths["root"]) / "ducklake" / "data").as_posix(),
        field="ducklake_projection_program.data_path",
    )
    return {
        "runtime": runtime,
        "database": database,
        "bootstrap_receipt": evidence / "bootstrap" / "pctdd-bootstrap.json",
        "ducklake_receipt": evidence / "bootstrap" / "ducklake-bootstrap-history.json",
        "ducklake_catalog": ducklake_catalog,
        "ducklake_data": ducklake_data,
    }


def _ensure_private_directory(path: Path) -> None:
    pending: list[Path] = []
    cursor = path
    while cursor != ROOT and not cursor.exists():
        pending.append(cursor)
        cursor = cursor.parent
    try:
        cursor.relative_to(ROOT)
    except ValueError as exc:
        raise MaterializationError("runtime directory escapes repository") from exc
    if cursor.exists() and cursor.is_symlink():
        raise MaterializationError("runtime directory ancestry contains a symlink")
    for directory in reversed(pending):
        directory.mkdir(mode=0o700)
    path.chmod(0o700)


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    _ensure_private_directory(path.parent)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(temporary, flags, 0o600)
    try:
        payload = _json_bytes(value)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _read_receipt(path: Path) -> dict[str, Any]:
    _regular_file(path, field="bootstrap receipt")
    return _load_json_bytes(path.read_bytes(), field="bootstrap receipt")


def _persist_optional_ducklake_receipt(
    path: Path,
    projection: dict[str, Any],
) -> dict[str, Any]:
    """Persist projection health when possible without creating a gate."""

    projection["receipt_persisted"] = True
    projection["projection_receipt_id"] = _sha256(_json_bytes(projection))
    try:
        _atomic_json(path, projection)
    except Exception as exc:
        projection.update(
            {
                "receipt_persisted": False,
                "receipt_persistence_error_class": type(exc).__name__,
            }
        )
        projection["projection_receipt_id"] = _sha256(_json_bytes(projection))
    return projection


def _ducklake_projection(
    *,
    board: Any,
    paths: Mapping[str, Path],
    population: Mapping[str, Any],
    control_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Best-effort history projection; every failure is explicitly non-gating."""

    policy = board.payload.get("ducklake_projection_program")
    policy = policy if isinstance(policy, Mapping) else {}
    projection: dict[str, Any] = {
        "schema": DUCKLAKE_SCHEMA,
        "authoritative": False,
        "scheduling_gate": False,
        "completion_gate": False,
        "status": "typed_unavailable",
        "reason_code": "ducklake_projection_not_attempted",
        "source_head": str(population["source_head"]),
        "repository_tree_id": str(population["repository_tree_id"]),
        "plan_root_cid": str(population["plan_root_cid"]),
    }
    mode = str(policy.get("mode") or "disabled").strip().lower()
    if mode not in {"enabled_non_authoritative", "optional_non_authoritative"}:
        projection["reason_code"] = "ducklake_projection_disabled_by_policy"
        return _persist_optional_ducklake_receipt(
            paths["ducklake_receipt"], projection
        )
    try:
        _install_import_roots()
        import duckdb
        from ipfs_accelerate_py.agent_supervisor.integrations.ducklake_history_projection import (
            project_history,
        )

        authority_check = dict(project_history({"receipt": control_receipt}))
        if authority_check.get("authoritative") is not False:
            raise MaterializationError("DuckLake projection adapter leaked authority")
        catalog = paths["ducklake_catalog"]
        data_path = paths["ducklake_data"]
        _ensure_private_directory(catalog.parent)
        _ensure_private_directory(data_path)
        connection = duckdb.connect(":memory:")
        try:
            # LOAD only.  Materialization must never install or download an extension.
            connection.execute("LOAD ducklake")
            catalog_sql = str(catalog).replace("'", "''")
            data_sql = str(data_path).replace("'", "''")
            connection.execute(
                f"ATTACH 'ducklake:{catalog_sql}' AS pctdd_history "
                f"(DATA_PATH '{data_sql}')"
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS pctdd_history.bootstrap_history (
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
            event_payload = {
                "source_head": population["source_head"],
                "repository_tree_id": population["repository_tree_id"],
                "plan_root_cid": population["plan_root_cid"],
                "projection_cid": control_receipt.get("projection_cid"),
            }
            event_id = _sha256(_json_bytes(event_payload))
            exists = connection.execute(
                "SELECT COUNT(*) FROM pctdd_history.bootstrap_history WHERE event_id = ?",
                [event_id],
            ).fetchone()
            if exists is None or int(exists[0]) == 0:
                connection.execute(
                    "INSERT INTO pctdd_history.bootstrap_history VALUES "
                    "(?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                                "task_authority": "DuckDB/DatabaseTaskSource@1",
                                "state_owner_transport": "QuackStateServer@1",
                                "projection": "DuckLake/non-authoritative",
                            },
                            sort_keys=True,
                            separators=(",", ":"),
                        ),
                    ],
                )
            row_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM pctdd_history.bootstrap_history"
                ).fetchone()[0]
            )
            connection.execute("DETACH pctdd_history")
        finally:
            connection.close()
        projection.update(
            {
                "status": "available_non_authoritative",
                "reason_code": "",
                "event_id": event_id,
                "row_count": row_count,
                "adapter_observed": bool(authority_check.get("observed")),
                "catalog_path": catalog.relative_to(ROOT).as_posix(),
                "data_path": data_path.relative_to(ROOT).as_posix(),
            }
        )
    except Exception as exc:  # Optional projection must never gate task authority.
        projection.update(
            {
                "status": "typed_unavailable",
                "reason_code": "ducklake_projection_unavailable",
                "error_class": type(exc).__name__,
            }
        )
    return _persist_optional_ducklake_receipt(paths["ducklake_receipt"], projection)


def _task_aliases(source: Any) -> tuple[str, ...]:
    page = source.list_tasks(limit=1000)
    return tuple(item.task_alias for item in page.tasks)


def _verify_materialized_source(
    source: Any,
    population: Mapping[str, Any],
    *,
    operator_completed: bool,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    snapshot = source.snapshot().to_dict()
    if int(snapshot["task_count"]) != len(population["tasks"]):
        raise MaterializationError("DuckDB task population is not exactly 54")
    if int(snapshot["goal_count"]) != len(population["objectives"]):
        raise MaterializationError("DuckDB goal population differs from objectives")
    if int(snapshot["dependency_count"]) != int(population["task_dependency_count"]):
        raise MaterializationError("DuckDB dependency population differs from board")
    aliases = _task_aliases(source)
    if aliases != TASK_IDS:
        raise MaterializationError("DuckDB task aliases differ from sealed board")
    operator = source.get_task(OPERATOR_TASK_ID)
    expected_statuses = (
        {"completed", "complete", "done"} if operator_completed else {"in_progress"}
    )
    if operator is None or operator.status not in expected_statuses:
        raise MaterializationError(
            "PCTDD-000 completion stage differs from the requested verification"
        )
    ready = tuple(item.task_alias for item in source.ready_tasks(limit=100).tasks)
    expected_ready = INITIAL_READY if operator_completed else ()
    if ready != expected_ready:
        raise MaterializationError(
            "DuckDB ready frontier differs from the operator seal stage"
        )
    return snapshot, ready


def check(config_path: Path) -> dict[str, Any]:
    board, config, config_bytes = _load_board(config_path)
    population = _population(board, config)
    _assert_source_unchanged(
        config,
        head=str(population["source_head"]),
        tree=str(population["repository_tree_id"]),
    )
    return {
        "schema": CHECK_SCHEMA,
        "valid": True,
        "mode": "check",
        "program_id": PROGRAM_ID,
        "config_sha256": _sha256(config_bytes),
        "source_head": population["source_head"],
        "repository_tree_id": population["repository_tree_id"],
        "source_forest_root": population["source_forest"]["source_forest_root"],
        "plan_root_cid": population["plan_root_cid"],
        "task_count": len(population["tasks"]),
        "goal_count": len(population["objectives"]),
        "dependency_count": population["task_dependency_count"],
        "operator_completion_authority": "DatabaseTaskSource.record_evidence+CAS",
        "post_operator_ready_task_ids": list(INITIAL_READY),
        "ducklake_authoritative": False,
    }


def materialize(config_path: Path) -> dict[str, Any]:
    _install_import_roots()
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    board, config, _config_bytes = _load_board(config_path)
    population = _population(board, config)
    generation = board.resolved_database_program().store_generation
    if generation == "pctdd-v1-g8":
        return _migrate_source_provider_route(config=config, population=population)
    if generation == "pctdd-v1-g7":
        return _migrate_source_binding(config=config, population=population)
    _assert_source_unchanged(
        config,
        head=str(population["source_head"]),
        tree=str(population["repository_tree_id"]),
    )
    paths = _runtime_paths(board)
    database = paths["database"]
    receipt_path = paths["bootstrap_receipt"]
    if database.exists() or receipt_path.exists():
        if not database.is_file() or database.is_symlink() or not receipt_path.is_file():
            raise MaterializationError(
                "partial or unsafe bootstrap state exists; operator review is required"
            )
        prior = _read_receipt(receipt_path)
        for key in ("source_head", "repository_tree_id", "plan_root_cid"):
            if prior.get(key) != population.get(key):
                raise MaterializationError(
                    "existing DuckDB authority is bound to another source tree or plan"
                )
        with DatabaseTaskSource(
            database,
            owner_id="pctdd-bootstrap:verify-existing",
            install_schema=False,
            repository_tree_id=str(population["repository_tree_id"]),
            plan_root_cid=str(population["plan_root_cid"]),
        ) as source:
            sealed = prior.get("operator_controls_sealed") is True
            snapshot, ready = _verify_materialized_source(
                source,
                population,
                operator_completed=sealed,
            )
        _assert_source_unchanged(
            config,
            head=str(population["source_head"]),
            tree=str(population["repository_tree_id"]),
        )
        return {
            "schema": BOOTSTRAP_SCHEMA,
            "mode": "materialize",
            "materialized": True,
            "operator_controls_sealed": sealed,
            "idempotent_replay": True,
            "bootstrap_receipt": prior,
            "snapshot": snapshot,
            "ready_task_ids": list(ready),
        }

    _ensure_private_directory(paths["runtime"])
    _ensure_private_directory(database.parent)
    with DatabaseTaskSource(
        database,
        owner_id="pctdd-bootstrap:single-writer",
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        control_receipt = dict(
            source.materialize(
                population,
                repository_tree_id=str(population["repository_tree_id"]),
                plan_root_cid=str(population["plan_root_cid"]),
            )
        )
        before = source.get_task(OPERATOR_TASK_ID)
        if before is None or before.status != "in_progress" or before.revision < 1:
            raise MaterializationError("PCTDD-000 was not ingested as staged operator work")
        _assert_source_unchanged(
            config,
            head=str(population["source_head"]),
            tree=str(population["repository_tree_id"]),
        )
        snapshot, ready = _verify_materialized_source(
            source,
            population,
            operator_completed=False,
        )
    _assert_source_unchanged(
        config,
        head=str(population["source_head"]),
        tree=str(population["repository_tree_id"]),
    )
    bootstrap: dict[str, Any] = {
        "schema": BOOTSTRAP_SCHEMA,
        "program_id": PROGRAM_ID,
        "source_head": population["source_head"],
        "repository_tree_id": population["repository_tree_id"],
        "source_forest": population["source_forest"],
        "source_identities": population["source_identities"],
        "plan_root_cid": population["plan_root_cid"],
        "database_task_source_receipt": control_receipt,
        "operator_controls_sealed": False,
        "operator_stage": "materialized_pending_profile_validators_preflight_dry_run",
        "projection_cid": snapshot["projection_cid"],
        "task_count": snapshot["task_count"],
        "goal_count": snapshot["goal_count"],
        "dependency_count": snapshot["dependency_count"],
        "initial_ready_task_ids": [],
        "authority": {
            "tasks_and_goals": "DuckDB/DatabaseTaskSource@1",
            "live_state_owner_transport": "QuackStateServer@1",
            "ducklake": "optional_non_authoritative_history_projection",
            "markdown_completion_authority": False,
        },
        "ducklake_projection": {
            "status": "not_attempted_before_operator_seal",
            "authoritative": False,
            "scheduling_gate": False,
            "completion_gate": False,
        },
    }
    bootstrap["bootstrap_receipt_id"] = content_identity(bootstrap)
    _atomic_json(receipt_path, bootstrap)
    return {
        "schema": BOOTSTRAP_SCHEMA,
        "mode": "materialize",
        "materialized": True,
        "operator_controls_sealed": False,
        "idempotent_replay": False,
        "bootstrap_receipt": bootstrap,
        "snapshot": snapshot,
        "ready_task_ids": list(ready),
    }


def _operator_command_receipt(
    argv: Sequence[str],
    *,
    label: str,
    timeout_seconds: int,
) -> dict[str, Any]:
    dispatcher = ROOT / VALIDATION_DISPATCHER_RELATIVE
    spec = importlib.util.spec_from_file_location(
        "pctdd_operator_validation_runtime",
        dispatcher,
    )
    if spec is None or spec.loader is None:
        raise MaterializationError("cannot load protected validation runtime")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    with module._sealed_validation_environment() as (environment, python, launcher):
        command = list(argv)
        if not command or command[0] != "python":
            raise MaterializationError(f"{label} does not use the sealed Python placeholder")
        command[0] = python
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            close_fds=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            module._terminate_process(process)
            process.communicate()
            raise MaterializationError(f"{label} timed out")
    stdout = bytes(stdout or b"")
    stderr = bytes(stderr or b"")
    if process.returncode != 0:
        diagnostic = (stderr or stdout)[-2000:].decode("utf-8", errors="replace")
        raise MaterializationError(f"{label} failed: {diagnostic}")
    return {
        "label": label,
        "argv": list(argv),
        "returncode": int(process.returncode),
        "stdout_sha256": _sha256(stdout),
        "stderr_sha256": _sha256(stderr),
        "validation_python_launcher": launcher,
        "stdout_tail": stdout[-1048576:].decode("utf-8", errors="replace"),
    }


def _json_receipt_output(receipt: Mapping[str, Any], *, label: str) -> Mapping[str, Any]:
    tail = str(receipt.get("stdout_tail") or "").strip()
    def reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise MaterializationError(f"{label} JSON contains duplicate key {key!r}")
            result[key] = value
        return result
    try:
        payload = json.loads(tail, object_pairs_hook=reject_duplicates)
    except json.JSONDecodeError as exc:
        raise MaterializationError(f"{label} did not return a JSON object") from exc
    if not isinstance(payload, Mapping):
        raise MaterializationError(f"{label} JSON output is not an object")
    return payload


def check_sealed(config_path: Path) -> dict[str, Any]:
    _install_import_roots()
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    board, config, _config_bytes = _load_board(config_path)
    population = _population(board, config)
    generation = board.resolved_database_program().store_generation
    if generation == "pctdd-v1-g8":
        migration = _check_source_provider_route(
            config=config,
            population=population,
            allow_progressed=True,
        )
        if migration.get("valid") is not True:
            raise MaterializationError(
                "PCTDD g8 source/provider-route successor is not admitted"
            )
        return {
            **migration,
            "mode": "check-sealed",
            "operator_controls_sealed": True,
            "operator_seal_kind": "accepted_source_provider_route_successor",
            "source_head": population["source_head"],
            "repository_tree_id": population["repository_tree_id"],
        }
    if generation == "pctdd-v1-g7":
        migration = _check_source_binding(
            config=config,
            population=population,
            allow_progressed=True,
        )
        if migration.get("valid") is not True:
            raise MaterializationError(
                "PCTDD g7 source-binding successor is not admitted"
            )
        # PCTDD-000 remains historically completed; the g7 migration adds one
        # operator-owned evidence node bound to this exact source without
        # reopening or rewriting that accepted completion.  A successful
        # independent migration verification is therefore the successor seal
        # consumed by the configured-board launch gate.
        return {
            **migration,
            "mode": "check-sealed",
            "operator_controls_sealed": True,
            "operator_seal_kind": "accepted_source_binding_successor",
            "source_head": population["source_head"],
            "repository_tree_id": population["repository_tree_id"],
        }
    paths = _runtime_paths(board)
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise MaterializationError("PCTDD authority has not been materialized and sealed")
    receipt = _read_receipt(paths["bootstrap_receipt"])
    if receipt.get("operator_controls_sealed") is not True:
        raise MaterializationError("PCTDD-000 staged controls are not sealed")
    for key in ("source_head", "repository_tree_id", "plan_root_cid"):
        if receipt.get(key) != population.get(key):
            raise MaterializationError("operator seal receipt belongs to another source")
    with DatabaseTaskSource(
        paths["database"],
        owner_id="pctdd-bootstrap:check-sealed",
        install_schema=False,
        repository_tree_id=str(population["repository_tree_id"]),
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        snapshot, ready = _verify_materialized_source(
            source,
            population,
            operator_completed=True,
        )
    return {
        "schema": CHECK_SCHEMA,
        "valid": True,
        "mode": "check-sealed",
        "source_head": population["source_head"],
        "repository_tree_id": population["repository_tree_id"],
        "operator_controls_sealed": True,
        "snapshot": snapshot,
        "ready_task_ids": list(ready),
    }


def _recover_operator_completion_receipt(
    task: Any,
    *,
    exact_head: str,
    exact_tree: str,
    plan_root_cid: str,
    content_identity: Any,
) -> tuple[str, str]:
    receipt = task.body.get("completion_receipt") if isinstance(task.body, Mapping) else None
    expected_fields = {
        "schema",
        "evidence_digest",
        "evidence_event_id",
        "source_head",
        "repository_tree_id",
        "plan_root_cid",
    }
    if not isinstance(receipt, Mapping) or set(receipt) != expected_fields:
        raise MaterializationError("completed PCTDD-000 receipt shape differs")
    if (
        receipt.get("schema") != CONTROL_EVIDENCE_SCHEMA
        or receipt.get("source_head") != exact_head
        or receipt.get("repository_tree_id") != exact_tree
        or receipt.get("plan_root_cid") != plan_root_cid
        or not str(receipt.get("evidence_digest") or "")
        or not str(receipt.get("evidence_event_id") or "")
    ):
        raise MaterializationError("completed PCTDD-000 receipt binding differs")
    control_evidence_digest = str(receipt["evidence_digest"])
    transition_evidence_digest = content_identity(
        {
            "task_cid": task.task_cid,
            "revision": task.revision,
            "receipt": dict(receipt),
            "evidence_digests": [control_evidence_digest],
        }
    )
    completion_receipt_cid = content_identity(
        {
            "namespace": "completion-receipt",
            "task_cid": task.task_cid,
            "revision": task.revision,
            "evidence_digest": transition_evidence_digest,
        }
    )
    return control_evidence_digest, completion_receipt_cid


def seal_operator_controls(config_path: Path) -> dict[str, Any]:
    _install_import_roots()
    from ipfs_accelerate_py.agent_supervisor.task_sources.control_plane_contracts import (
        content_identity,
    )
    from ipfs_accelerate_py.agent_supervisor.task_sources.database_task_source import (
        DatabaseTaskSource,
    )

    board, config, _config_bytes = _load_board(config_path)
    population = _population(board, config)
    paths = _runtime_paths(board)
    if not paths["database"].is_file() or not paths["bootstrap_receipt"].is_file():
        raise MaterializationError("materialize the staged authority before seal-controls")
    prior = _read_receipt(paths["bootstrap_receipt"])
    if prior.get("operator_controls_sealed") is True:
        return check_sealed(config_path)
    if prior.get("operator_stage") != "materialized_pending_profile_validators_preflight_dry_run":
        raise MaterializationError("operator staging receipt differs")
    for key in ("source_head", "repository_tree_id", "plan_root_cid"):
        if prior.get(key) != population.get(key):
            raise MaterializationError("staged authority belongs to another source")

    exact_head = str(population["source_head"])
    exact_tree = str(population["repository_tree_id"])
    configured_scheduler = ROOT / CONFIGURED_SCHEDULER_RELATIVE
    prerequisites = (
        (
            "sealed_pctdd_000_profile",
            (
                "python",
                VALIDATION_DISPATCHER_RELATIVE,
                "--task",
                OPERATOR_TASK_ID,
            ),
            3600,
            False,
        ),
        (
            "dependency_validator",
            (
                "python",
                "scripts/validate_parallel_content_sealing_proof_carrying_tdd_dependencies.py",
                "--check-all",
            ),
            900,
            True,
        ),
        (
            "board_validator",
            (
                "python",
                "scripts/validate_parallel_content_sealing_proof_carrying_tdd_board.py",
                "--check-all",
            ),
            900,
            True,
        ),
        (
            "configured_board_preflight",
            (
                "python",
                configured_scheduler.relative_to(ROOT).as_posix(),
                "--repo-root",
                ".",
                "--config",
                config_path.relative_to(ROOT).as_posix(),
                "preflight",
            ),
            900,
            True,
        ),
        (
            "configured_board_implementation_dry_run",
            (
                "python",
                configured_scheduler.relative_to(ROOT).as_posix(),
                "--repo-root",
                ".",
                "--config",
                config_path.relative_to(ROOT).as_posix(),
                "launch",
                "--implement",
                "--dry-run",
            ),
            900,
            False,
        ),
    )
    receipts: list[dict[str, Any]] = []
    for label, command, timeout_seconds, require_valid_json in prerequisites:
        _assert_source_unchanged(config, head=exact_head, tree=exact_tree)
        receipt = _operator_command_receipt(
            command,
            label=label,
            timeout_seconds=timeout_seconds,
        )
        if require_valid_json:
            payload = _json_receipt_output(receipt, label=label)
            if payload.get("valid") is not True:
                raise MaterializationError(f"{label} did not report valid=true")
            receipt["reported_schema"] = str(payload.get("schema") or "")
            receipt["reported_source_head"] = str(payload.get("source_head") or "")
            receipt["reported_source_tree"] = str(payload.get("source_tree") or "")
            if label != "configured_board_preflight":
                if (
                    receipt["reported_source_head"] != exact_head
                    or receipt["reported_source_tree"] != exact_tree
                ):
                    raise MaterializationError(
                        f"{label} evidence belongs to another source"
                    )
            else:
                # The current configured-board preflight does not publish
                # these fields.  If a successor does, never ignore them.
                if receipt["reported_source_head"] not in {"", exact_head}:
                    raise MaterializationError(
                        "configured_board_preflight source_head differs"
                    )
                if receipt["reported_source_tree"] not in {"", exact_tree}:
                    raise MaterializationError(
                        "configured_board_preflight source_tree differs"
                    )
                checks = {
                    str(item.get("name") or ""): item.get("passed")
                    for item in payload.get("checks", ())
                    if isinstance(item, Mapping)
                }
                if checks.get("checkout_clean") is not True:
                    raise MaterializationError(
                        "configured_board_preflight lacks a passing clean-checkout check"
                    )
                if checks.get("configured_submodules") is not True:
                    raise MaterializationError(
                        "configured_board_preflight lacks passing exact-submodule checks"
                    )
            receipt["operator_observed_source_head"] = exact_head
            receipt["operator_observed_source_tree"] = exact_tree
        receipt.pop("stdout_tail", None)
        receipts.append(receipt)
        _assert_source_unchanged(config, head=exact_head, tree=exact_tree)

    with DatabaseTaskSource(
        paths["database"],
        owner_id="pctdd-bootstrap:seal-controls",
        install_schema=False,
        repository_tree_id=exact_tree,
        plan_root_cid=str(population["plan_root_cid"]),
    ) as source:
        before = source.get_task(OPERATOR_TASK_ID)
        recovered_after_cas = False
        if before is None:
            raise MaterializationError("PCTDD-000 is absent from the staged authority")
        if before.status == "in_progress":
            control_evidence = {
                "schema": CONTROL_EVIDENCE_SCHEMA,
                "task_id": OPERATOR_TASK_ID,
                "task_cid": before.task_cid,
                "task_revision": before.revision,
                "source_head": exact_head,
                "repository_tree_id": exact_tree,
                "source_forest_root": population["source_forest"]["source_forest_root"],
                "plan_root_cid": population["plan_root_cid"],
                "source_identities": population["source_identities"],
                "prerequisite_receipts": receipts,
                "claim": "the exact tracked g6 controls passed the sealed profile, both validators, preflight, and implementation dry-run before completion",
                "claim_limit": "does not establish any ordinary implementation task or make DuckLake authoritative",
            }
            evidence_digest = content_identity(control_evidence)
            evidence_receipt = source.record_evidence(
                task_cid=before.task_cid,
                evidence_kind="control_program_seal",
                digest=evidence_digest,
                body=control_evidence,
            )
            cas = source.compare_and_set_status(
                before.task_cid,
                before.revision,
                "completed",
                receipt={
                    "schema": CONTROL_EVIDENCE_SCHEMA,
                    "evidence_digest": evidence_digest,
                    "evidence_event_id": evidence_receipt.event_id,
                    "source_head": exact_head,
                    "repository_tree_id": exact_tree,
                    "plan_root_cid": population["plan_root_cid"],
                },
                evidence_digests=(evidence_digest,),
            )
            if not cas.changed or cas.task.status != "completed":
                raise MaterializationError("PCTDD-000 evidence-gated CAS did not complete")
            completion_receipt_cid = cas.receipt_cid
        elif before.status in {"completed", "complete", "done"}:
            # Recover the sole crash window after the authoritative CAS and
            # before publication of the rebuildable bootstrap receipt.  The
            # CAS receipt is checked against this exact tree and its CID is
            # recomputed from the current authority's canonical codec.
            evidence_digest, completion_receipt_cid = (
                _recover_operator_completion_receipt(
                    before,
                    exact_head=exact_head,
                    exact_tree=exact_tree,
                    plan_root_cid=str(population["plan_root_cid"]),
                    content_identity=content_identity,
                )
            )
            recovered_after_cas = True
        else:
            raise MaterializationError("PCTDD-000 is not at a sealable operator stage")
        if not completion_receipt_cid:
            raise MaterializationError("PCTDD-000 completion receipt CID is absent")
        snapshot, ready = _verify_materialized_source(
            source,
            population,
            operator_completed=True,
        )

    ducklake = _ducklake_projection(
        board=board,
        paths=paths,
        population=population,
        control_receipt=prior.get("database_task_source_receipt") or {},
    )
    _assert_source_unchanged(config, head=exact_head, tree=exact_tree)
    bootstrap = dict(prior)
    bootstrap.update(
        {
            "operator_controls_sealed": True,
            "operator_stage": "sealed_ready_for_supervisor",
            "pctdd_000_evidence_digest": evidence_digest,
            "pctdd_000_completion_receipt_cid": completion_receipt_cid,
            "operator_prerequisite_receipts": receipts,
            "operator_receipt_recovered_after_cas": recovered_after_cas,
            "projection_cid": snapshot["projection_cid"],
            "initial_ready_task_ids": list(ready),
            "ducklake_projection": ducklake,
        }
    )
    bootstrap.pop("bootstrap_receipt_id", None)
    bootstrap["bootstrap_receipt_id"] = content_identity(bootstrap)
    _atomic_json(paths["bootstrap_receipt"], bootstrap)
    return {
        "schema": BOOTSTRAP_SCHEMA,
        "mode": "seal-controls",
        "materialized": True,
        "operator_controls_sealed": True,
        "bootstrap_receipt": bootstrap,
        "snapshot": snapshot,
        "ready_task_ids": list(ready),
    }


def _arguments(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs="?",
        choices=(
            "check",
            "materialize",
            "seal-controls",
            "migrate-source",
            "check-source-migration",
            "check-sealed",
        ),
        default="materialize",
        help="check, stage materialization, seal operator controls, or verify the seal",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="alias for the non-mutating check command",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="repository-relative scheduler configuration",
    )
    return parser.parse_args(argv)


def _source_successor_module() -> Any:
    """Load the bounded g7 adapter without creating another task authority."""

    path = ROOT / "scripts/pctdd_g7_source_binding_successor.py"
    spec = importlib.util.spec_from_file_location("pctdd_g7_source_binding_successor", path)
    if spec is None or spec.loader is None:
        raise MaterializationError("cannot load the sealed PCTDD g7 source successor")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise MaterializationError(
            f"cannot load PCTDD g7 source successor: {type(exc).__name__}: {exc}"
        ) from exc
    return module


def _source_provider_route_successor_module() -> Any:
    """Load the bounded g8 adapter without creating another task authority."""

    path = ROOT / "scripts/pctdd_g8_provider_route_successor.py"
    spec = importlib.util.spec_from_file_location(
        "pctdd_g8_provider_route_successor", path
    )
    if spec is None or spec.loader is None:
        raise MaterializationError(
            "cannot load the sealed PCTDD g8 source/provider-route successor"
        )
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise MaterializationError(
            "cannot load PCTDD g8 source/provider-route successor: "
            f"{type(exc).__name__}: {exc}"
        ) from exc
    return module


def _migrate_source_binding(
    *, config: Mapping[str, Any], population: Mapping[str, Any]
) -> dict[str, Any]:
    module = _source_successor_module()
    try:
        return dict(
            module.migrate_source_binding(
                root=ROOT,
                config=config,
                population=population,
            )
        )
    except Exception as exc:
        raise MaterializationError(
            f"PCTDD g7 source migration refused: {type(exc).__name__}: {exc}"
        ) from exc


def _check_source_binding(
    *,
    config: Mapping[str, Any],
    population: Mapping[str, Any],
    allow_progressed: bool,
) -> dict[str, Any]:
    module = _source_successor_module()
    try:
        return dict(
            module.check_source_binding(
                root=ROOT,
                config=config,
                population=population,
                allow_progressed=allow_progressed,
            )
        )
    except Exception as exc:
        raise MaterializationError(
            f"PCTDD g7 source migration check refused: {type(exc).__name__}: {exc}"
        ) from exc


def _migrate_source_provider_route(
    *, config: Mapping[str, Any], population: Mapping[str, Any]
) -> dict[str, Any]:
    module = _source_provider_route_successor_module()
    try:
        return dict(
            module.migrate_source_provider_route(
                root=ROOT,
                config=config,
                population=population,
            )
        )
    except Exception as exc:
        raise MaterializationError(
            "PCTDD g8 source/provider-route migration refused: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def _check_source_provider_route(
    *,
    config: Mapping[str, Any],
    population: Mapping[str, Any],
    allow_progressed: bool,
) -> dict[str, Any]:
    module = _source_provider_route_successor_module()
    try:
        return dict(
            module.check_source_provider_route(
                root=ROOT,
                config=config,
                population=population,
                allow_progressed=allow_progressed,
            )
        )
    except Exception as exc:
        raise MaterializationError(
            "PCTDD g8 source/provider-route migration check refused: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def main(argv: Sequence[str] | None = None) -> int:
    arguments = _arguments(argv)
    try:
        config_path = _repo_path(arguments.config, field="--config")
        command = "check" if arguments.check else arguments.command
        if command == "check":
            result = check(config_path)
        elif command == "materialize":
            result = materialize(config_path)
        elif command == "seal-controls":
            result = seal_operator_controls(config_path)
        elif command in {"migrate-source", "check-source-migration"}:
            board, config, _config_bytes = _load_board(config_path)
            generation = board.resolved_database_program().store_generation
            if generation not in {"pctdd-v1-g7", "pctdd-v1-g8"}:
                raise MaterializationError(
                    f"{command} requires the sealed g7 or g8 configuration"
                )
            population = _population(board, config)
            if command == "migrate-source" and generation == "pctdd-v1-g8":
                result = _migrate_source_provider_route(
                    config=config,
                    population=population,
                )
            elif command == "migrate-source":
                result = _migrate_source_binding(config=config, population=population)
            elif generation == "pctdd-v1-g8":
                result = _check_source_provider_route(
                    config=config,
                    population=population,
                    allow_progressed=False,
                )
            else:
                result = _check_source_binding(
                    config=config,
                    population=population,
                    allow_progressed=False,
                )
        else:
            result = check_sealed(config_path)
    except Exception as exc:
        _print_json(
            {
                "schema": CHECK_SCHEMA,
                "valid": False,
                "error_code": "pctdd_materialization_refused",
                "error_class": type(exc).__name__,
                "message": str(exc)[:1000],
            }
        )
        return 1
    _print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
