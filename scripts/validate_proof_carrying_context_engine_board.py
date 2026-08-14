#!/usr/bin/env python3
"""Validate and project the Proof-Carrying Context Engine v0.1 board.

The Markdown objective heap and todo board remain authoritative operator inputs.
This script emits bounded JSON projections for schedulers and reviewers; it
does not admit work, grant effects, or prove completion.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))

from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (  # noqa: E402
    parse_goal_heap,
)
from ipfs_accelerate_py.agent_supervisor.runtime.artifact_store import (  # noqa: E402
    write_bundle_index_artifact,
)
from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (  # noqa: E402
    ConfiguredBoardError,
    load_configured_board,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
    split_csv,
)


OBJECTIVE_PATH = REPO_ROOT / "docs/architecture/proof_carrying_context_engine_v0_1.objectives.md"
TODO_PATH = REPO_ROOT / "docs/architecture/proof_carrying_context_engine_v0_1.todo.md"
CONFIG_PATH = REPO_ROOT / "config/proof_carrying_context_engine_v0_1_supervisor.json"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "artifacts/proof_carrying_context_engine/control"
TASK_PREFIX = "## PCCE-"
BOARD_NAMESPACE = "proof-carrying-context-engine-v0.1"
OBJECTIVE_ID = "PCCE-G000"
PLANNING_GENERATED_AT = "2026-08-14T00:00:00+00:00"

EXPECTED_TASK_IDS = (
    ["PCCE-000"]
    + [f"PCCE-{value:03d}" for value in range(1, 12)]
    + [f"PCCE-{value:03d}" for value in range(20, 26)]
    + [f"PCCE-{value:03d}" for value in range(30, 36)]
    + [f"PCCE-{value:03d}" for value in range(40, 45)]
    + [f"PCCE-{value:03d}" for value in range(50, 57)]
    + [f"PCCE-{value:03d}" for value in range(60, 69)]
    + [f"PCCE-{value:03d}" for value in range(70, 77)]
    + [f"PCCE-{value:03d}" for value in range(80, 84)]
)
EXPECTED_GOAL_IDS = ["PCCE-G000"] + [f"PCCE-G{value}" for value in range(100, 900, 100)]

REQUIRED_METADATA = {
    "status",
    "completion",
    "is schedulable",
    "review only",
    "owning repository",
    "owned paths",
    "objective",
    "depends on",
    "priority",
    "risk classification",
    "execution mode",
    "allowed effects",
    "prohibited effects",
    "acceptance criteria",
    "required tests",
    "required evidence",
    "rollback procedure",
    "assigned worktree",
    "final result cid or artifact identity",
    "goal id",
    "outputs",
    "validation",
    "board namespace",
    "bundle",
    "parallel lane",
    "resource class",
    "implementation timeout seconds",
    "predicted files",
    "conflict policy",
    "acceptance",
}

ALLOWED_TASK_STATUSES = {
    "todo",
    "queued",
    "proposed",
    "admitted",
    "ready",
    "in_progress",
    "running",
    "blocked",
    "completed",
    "failed",
    "rejected",
    "quarantined",
    "cancelled",
}
ALLOWED_REPOSITORIES = {
    "endomorphosis/ipfs_datasets_py",
    "endomorphosis/ipfs_kit_py",
    "endomorphosis/ipfs_accelerate_py",
    "endomorphosis/Mcp-Plus-Plus",
    "endomorphosis/lift_coding",
    "cross-repository",
}


def _git(*args: str, cwd: Path = REPO_ROOT) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def _sha256_json(payload: Any) -> str:
    raw = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _headings(path: Path, prefix: str) -> list[str]:
    result: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(prefix):
            result.append(line[3:].split(maxsplit=1)[0])
    return result


def _topological_order(task_ids: Iterable[str], edges: dict[str, list[str]]) -> list[str]:
    nodes = list(task_ids)
    followers: dict[str, list[str]] = defaultdict(list)
    indegree = {task_id: 0 for task_id in nodes}
    for task_id, dependencies in edges.items():
        for dependency in dependencies:
            followers[dependency].append(task_id)
            indegree[task_id] += 1
    ready = deque(sorted(task_id for task_id, count in indegree.items() if count == 0))
    ordered: list[str] = []
    while ready:
        task_id = ready.popleft()
        ordered.append(task_id)
        for follower in sorted(followers[task_id]):
            indegree[follower] -= 1
            if indegree[follower] == 0:
                ready.append(follower)
    return ordered


def _repository_identity(config: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "superproject_commit": _git("rev-parse", "HEAD"),
        "superproject_tree": _git("rev-parse", "HEAD^{tree}"),
        "branch": _git("branch", "--show-current"),
        "repositories": {},
    }
    for name, record in config["repositories"].items():
        relative = str(record["path"])
        path = REPO_ROOT / relative
        if not (path / ".git").exists():
            errors.append(f"uninitialized repository: {relative}")
            continue
        gitlink = _git("rev-parse", f"HEAD:{relative}")
        head = _git("rev-parse", "HEAD", cwd=path)
        dirty = _git("status", "--porcelain=v1", "--untracked-files=all", cwd=path)
        if gitlink != head:
            errors.append(f"gitlink/head mismatch for {relative}: {gitlink} != {head}")
        if dirty:
            errors.append(f"dirty governed repository at validation: {relative}")
        result["repositories"][name] = {
            "path": relative,
            "gitlink": gitlink,
            "head": head,
            "initial_commit": str(record["initial_commit"]),
            "dirty": bool(dirty),
        }
    return result


def _metadata_bool(value: Any, *, default: bool = False) -> bool:
    normalized = str(value or "").strip().casefold()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return default


def _bundle_index_projection(
    projected_tasks: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    source_sha256: str,
) -> dict[str, Any]:
    """Project the reviewed Markdown board into canonical bundle-index input.

    The projection deliberately points every bundle at the same protected
    source board.  ``bundle_supervisor`` materializes only the leased execution
    slice into each lane's private runtime board, so no generated shard can
    become a competing source of task intent.
    """

    bundles: dict[str, dict[str, Any]] = {}
    priority_weights = {"P0": 100, "P1": 80, "P2": 60, "P3": 40}
    for task in projected_tasks:
        metadata = dict(task["metadata"])
        bundle_key = metadata.get("bundle", "").strip()
        if not bundle_key:
            continue
        predicted_files = list(task["predicted_files"])
        allowed_paths = split_csv(metadata.get("allowed paths", ""))
        schedulable = _metadata_bool(metadata.get("is schedulable"), default=True)
        review_only = _metadata_bool(metadata.get("review only"), default=False)
        priority = metadata.get("priority", "P2").strip().upper()
        task_payload = {
            "task_id": task["task_id"],
            "canonical_task_key": task["canonical_task_key"],
            "canonical_task_cid": task["canonical_task_cid"],
            "title": task["title"],
            "objective": metadata.get("objective", ""),
            "goal_id": task["goal_id"],
            "parent_goal_ids": [OBJECTIVE_ID],
            "board_namespace": BOARD_NAMESPACE,
            "status": task["status"],
            "is_schedulable": schedulable,
            "review_only": review_only,
            "depends_on": list(task["dependencies"]),
            "dependencies": list(task["dependencies"]),
            "dependency_task_ids": list(task["dependencies"]),
            "outputs": list(task["outputs"]),
            "files": predicted_files,
            "predicted_files": predicted_files,
            "predicted_paths": predicted_files,
            "allowed_paths": allowed_paths or predicted_files,
            "validation_commands": [metadata.get("validation", "")],
            "priority": priority,
            "objective_priority": priority_weights.get(priority, 20),
            "risk_classification": metadata.get("risk classification", ""),
            "execution_mode": metadata.get("execution mode", ""),
            "resource_class": metadata.get("resource class", "cpu-small"),
            "resource_stage": metadata.get("resource stage", "implementation"),
            "implementation_timeout_seconds": int(
                metadata.get("implementation timeout seconds", "0") or 0
            ),
            "max_attempts": int(config["max_task_attempts"]),
            "metadata": metadata,
        }
        bundle = bundles.setdefault(
            bundle_key,
            {
                "bundle_key": bundle_key,
                "shard_path": str(TODO_PATH.relative_to(REPO_ROOT)),
                "parallel_lane": metadata.get("parallel lane", bundle_key),
                "bundle_strategy": "reviewed-manual-task-slice-v1",
                "conflict_policy": metadata.get("conflict policy", ""),
                "execution_authority": "agent-supervisor/v1",
                "is_schedulable": False,
                "review_only": True,
                "tasks": [],
            },
        )
        bundle["tasks"].append(task_payload)
        bundle["is_schedulable"] = bool(bundle["is_schedulable"] or schedulable)
        bundle["review_only"] = bool(bundle["review_only"] and review_only)

    payload: dict[str, Any] = {
        "schema": "ipfs_accelerate_py.agent_supervisor.reviewed-bundle-index@1",
        "generated_at": PLANNING_GENERATED_AT,
        "source_todo": str(TODO_PATH.relative_to(REPO_ROOT)),
        "source_todo_sha256": source_sha256,
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "authoritative": False,
        "authority_note": (
            "The protected Markdown board remains authoritative; this is a "
            "queryable scheduler projection only."
        ),
        "bundles": dict(sorted(bundles.items())),
    }
    payload["projection_id"] = _sha256_json(payload)
    return payload


def validate(*, output_dir: Path, write: bool) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    try:
        configured_board = load_configured_board(CONFIG_PATH, repo_root=REPO_ROOT)
    except ConfiguredBoardError as exc:
        errors.append(f"configured-board profile is invalid: {exc}")
        configured_board = None
    tasks = parse_task_file(TODO_PATH, TASK_PREFIX)
    goals = parse_goal_heap(OBJECTIVE_PATH.read_text(encoding="utf-8"))

    task_headings = _headings(TODO_PATH, TASK_PREFIX)
    duplicate_tasks = sorted(task_id for task_id, count in Counter(task_headings).items() if count != 1)
    if duplicate_tasks:
        errors.append(f"duplicate task headings: {duplicate_tasks}")
    if task_headings != EXPECTED_TASK_IDS:
        errors.append("task population/order differs from the sealed PCCE v0.1 board")

    goal_headings = _headings(OBJECTIVE_PATH, "## PCCE-G")
    duplicate_goals = sorted(goal_id for goal_id, count in Counter(goal_headings).items() if count != 1)
    if duplicate_goals:
        errors.append(f"duplicate goal headings: {duplicate_goals}")
    if goal_headings != EXPECTED_GOAL_IDS:
        errors.append("goal population/order differs from PCCE-G000 plus Epic A-H")

    task_by_id = {task.task_id: task for task in tasks}
    goal_ids = {goal.goal_id for goal in goals}
    dependencies: dict[str, list[str]] = {}
    path_owners: dict[str, list[str]] = defaultdict(list)
    projected_tasks: list[dict[str, Any]] = []

    protected = set(config["protected_paths"])
    for task_id in EXPECTED_TASK_IDS:
        task = task_by_id.get(task_id)
        if task is None:
            errors.append(f"missing parsed task: {task_id}")
            continue
        metadata = {str(key).lower(): str(value) for key, value in task.metadata.items()}
        missing_fields = sorted(REQUIRED_METADATA.difference(metadata))
        if missing_fields:
            errors.append(f"{task_id} missing fields: {missing_fields}")
        if task.status not in ALLOWED_TASK_STATUSES:
            errors.append(f"{task_id} unsupported status: {task.status}")
        if task_id == "PCCE-000" and task.status != "completed":
            errors.append("PCCE-000 must remain completed after the control-plane seal")
        if task_id != "PCCE-000" and task.status == "completed" and not metadata.get(
            "final result cid or artifact identity", ""
        ).strip():
            errors.append(f"{task_id} is completed without a final artifact identity")
        if task.board_namespace != BOARD_NAMESPACE:
            errors.append(f"{task_id} has wrong board namespace: {task.board_namespace}")
        owner = metadata.get("owning repository", "")
        if owner not in ALLOWED_REPOSITORIES:
            errors.append(f"{task_id} has unsupported owning repository: {owner}")
        goal_id = metadata.get("goal id", "")
        if goal_id not in goal_ids:
            errors.append(f"{task_id} references unknown goal: {goal_id}")
        if not task.outputs:
            errors.append(f"{task_id} has no Outputs")
        predicted = split_csv(metadata.get("predicted files", ""))
        owned = split_csv(metadata.get("owned paths", ""))
        allowed = split_csv(metadata.get("allowed paths", ""))
        if not predicted:
            errors.append(f"{task_id} has no Predicted files")
        if set(task.outputs).difference(predicted):
            errors.append(f"{task_id} Outputs are not all repeated in Predicted files")
        if set(predicted).difference(owned):
            errors.append(f"{task_id} Predicted files are not all repeated in Owned paths")
        if allowed and set(predicted).difference(allowed):
            errors.append(f"{task_id} Predicted files are not all repeated in Allowed paths")
        if task_id != "PCCE-000" and protected.intersection(predicted):
            errors.append(f"{task_id} owns protected operator inputs: {sorted(protected.intersection(predicted))}")
        for path in predicted:
            path_owners[path].append(task_id)
        unknown_dependencies = sorted(set(task.depends_on).difference(task_by_id))
        if unknown_dependencies:
            errors.append(f"{task_id} has unknown dependencies: {unknown_dependencies}")
        if task_id in task.depends_on:
            errors.append(f"{task_id} depends on itself")
        dependencies[task_id] = list(task.depends_on)
        projected_tasks.append(
            {
                "task_id": task.task_id,
                "canonical_task_key": task.canonical_task_key,
                "canonical_task_cid": task.canonical_task_cid,
                "title": task.title,
                "status": task.status,
                "goal_id": goal_id,
                "owning_repository": owner,
                "dependencies": list(task.depends_on),
                "outputs": list(task.outputs),
                "predicted_files": predicted,
                "metadata": dict(sorted(metadata.items())),
            }
        )

    exact_path_conflicts = {
        path: owners
        for path, owners in sorted(path_owners.items())
        if len(owners) > 1 and owners != ["PCCE-000"]
    }
    if exact_path_conflicts:
        warnings.append(
            "serialized tasks share exact paths; dependency/conflict admission must prevent overlap: "
            + json.dumps(exact_path_conflicts, sort_keys=True)
        )

    ordered = _topological_order(EXPECTED_TASK_IDS, dependencies)
    if len(ordered) != len(EXPECTED_TASK_IDS):
        errors.append("task dependency graph contains a cycle")
    if ordered and ordered[-1] != "PCCE-083":
        errors.append("PCCE-083 must be the unique terminal task")

    identity = _repository_identity(config, errors)
    projection: dict[str, Any] = {
        "schema": "ipfs_accelerate_py.agent_supervisor.derived-task-board-projection@1",
        "authoritative": False,
        "authority_note": "The Markdown objective heap, todo board, leases, receipts, validations, and merge evidence remain authoritative.",
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "source": {
            "objective_path": str(OBJECTIVE_PATH.relative_to(REPO_ROOT)),
            "todo_path": str(TODO_PATH.relative_to(REPO_ROOT)),
            "config_path": str(CONFIG_PATH.relative_to(REPO_ROOT)),
            "objective_sha256": "sha256:" + hashlib.sha256(OBJECTIVE_PATH.read_bytes()).hexdigest(),
            "todo_sha256": "sha256:" + hashlib.sha256(TODO_PATH.read_bytes()).hexdigest(),
        },
        "repository_identity": identity,
        "task_count": len(projected_tasks),
        "tasks": projected_tasks,
        "dependency_edges": [
            {"from": dependency, "to": task_id}
            for task_id in EXPECTED_TASK_IDS
            for dependency in dependencies.get(task_id, [])
        ],
        "topological_order": ordered,
        "warnings": warnings,
    }
    projection["projection_id"] = _sha256_json(projection)
    graph = {
        "schema": "ipfs_accelerate_py.agent_supervisor.derived-task-dependency-graph@1",
        "objective_id": OBJECTIVE_ID,
        "board_projection_id": projection["projection_id"],
        "nodes": EXPECTED_TASK_IDS,
        "edges": projection["dependency_edges"],
        "topological_order": ordered,
    }
    graph["graph_id"] = _sha256_json(graph)
    bundle_index = _bundle_index_projection(
        projected_tasks,
        config=config,
        source_sha256=projection["source"]["todo_sha256"],
    )

    if write and not errors:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "task_board.json").write_text(
            json.dumps(projection, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (output_dir / "task_dependency_graph.json").write_text(
            json.dumps(graph, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        write_bundle_index_artifact(output_dir / "bundle_index.json", bundle_index)

    return {
        "valid": not errors,
        "schema": "ipfs_accelerate_py.agent_supervisor.board-validation-result@1",
        "objective_id": OBJECTIVE_ID,
        "board_namespace": BOARD_NAMESPACE,
        "task_count": len(projected_tasks),
        "goal_count": len(goals),
        "projection_id": projection["projection_id"],
        "graph_id": graph["graph_id"],
        "bundle_index_id": bundle_index["projection_id"],
        "configured_board_valid": configured_board is not None,
        "output_dir": str(output_dir),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-all", action="store_true", help="Validate the sealed full board")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--write", action="store_true", help="Update derived JSON/query projections after validation")
    parser.add_argument("--no-write", action="store_true", help="Deprecated explicit read-only validation flag")
    args = parser.parse_args()
    if args.write and args.no_write:
        parser.error("--write and --no-write are mutually exclusive")
    result = validate(output_dir=args.output_dir.resolve(), write=args.write)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
