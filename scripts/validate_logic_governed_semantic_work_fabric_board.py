#!/usr/bin/env python3
"""Fail-closed validator for the LGSWF bootstrap board.

The validator is read-only.  It proves the declarative legacy projection is
internally consistent; it does not admit a task, activate a plan, or prove any
product capability.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))

from generate_logic_governed_semantic_work_fabric_board import (  # noqa: E402
    ACCELERATOR_BASE,
    BOARD_NAMESPACE,
    DATASETS_BASE,
    GOALS,
    PLANNING_BASE,
    SEMANTIC_BOOTSTRAP,
    TASKS,
    dependency_projection,
    projection,
    render_objectives,
    render_todo,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
    split_csv,
)


TODO_PATH = REPO_ROOT / "docs/architecture/logic_governed_semantic_work_fabric.todo.md"
OBJECTIVES_PATH = REPO_ROOT / "docs/architecture/logic_governed_semantic_work_fabric.objectives.md"
PLAN_PATH = REPO_ROOT / "docs/architecture/LOGIC_GOVERNED_SEMANTIC_WORK_FABRIC_PLAN.md"
CONFIG_PATH = REPO_ROOT / "config/agent_supervisor_logic_governed_semantic_work_fabric.json"
PROJECTION_PATH = REPO_ROOT / "artifacts/logic_governed_semantic_work_fabric/control/task-board.json"
DEPENDENCY_PATH = REPO_ROOT / "artifacts/logic_governed_semantic_work_fabric/control/task-dependency-graph.json"
REVISION_PATH = REPO_ROOT / "artifacts/logic_governed_semantic_work_fabric/baseline/revision-comparison.json"
SCAN_FAILURE_PATH = REPO_ROOT / "artifacts/logic_governed_semantic_work_fabric/baseline/semantic-scan-bootstrap-failures.json"
BOOTSTRAP_PATH = REPO_ROOT / "artifacts/logic_governed_semantic_work_fabric/control/board-bootstrap.json"


REQUIRED_FIELDS = {
    "stable task id",
    "status",
    "completion",
    "is schedulable",
    "review only",
    "parent goal id",
    "subgoal id",
    "goal id",
    "owning repository",
    "owned paths",
    "base revision",
    "base semantic-state root",
    "base plan revision",
    "objective",
    "depends on",
    "read scope",
    "write scope",
    "external effect scope",
    "relevant symbol ids",
    "capsule cids",
    "contract and obligation cids",
    "resource demand",
    "model-route class",
    "permitted effects",
    "prohibited effects",
    "completion contract",
    "validation requirements",
    "proof requirements",
    "lease requirements",
    "rollback or compensation",
    "required evidence",
    "final result identity",
    "priority",
    "track",
    "outputs",
    "validation",
    "board namespace",
    "bundle",
    "parallel lane",
    "resource class",
    "resource stage",
    "estimated tokens",
    "implementation timeout seconds",
    "predicted files",
    "allowed paths",
    "interfaces",
    "allow concurrent with",
    "conflict policy",
    "preconditions",
    "effects",
    "evidence subset",
    "symbolic first",
    "llm context budget bytes",
    "acceptance",
    "embedding query",
}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain an object")
    return payload


def _safe_relative(value: str) -> bool:
    path = Path(value)
    return bool(
        value
        and value not in {".", ".."}
        and not path.is_absolute()
        and ".." not in path.parts
        and "~" not in value
        and "\x00" not in value
        and not any(character in value for character in "*?[]{}")
    )


def _reachable(adjacency: dict[str, set[str]], source: str, target: str) -> bool:
    pending = [source]
    seen: set[str] = set()
    while pending:
        node = pending.pop()
        if node == target:
            return True
        if node in seen:
            continue
        seen.add(node)
        pending.extend(adjacency.get(node, ()))
    return False


def _normalize_todo_progress(text: str) -> str:
    """Mask the only mutable field in the legacy task projection.

    The implementation supervisor records accepted work by changing ``Status``
    from ``todo`` to ``completed``.  Every other byte remains protected by the
    deterministic generator comparison below.  Unknown lifecycle values are
    intentionally not masked and therefore fail closed.
    """

    return re.sub(
        r"(?m)^- Status: (?:todo|completed)$",
        "- Status: <accepted-progress>",
        text.rstrip(),
    )


def validate() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required_paths = (
        TODO_PATH,
        OBJECTIVES_PATH,
        PLAN_PATH,
        CONFIG_PATH,
        PROJECTION_PATH,
        DEPENDENCY_PATH,
        REVISION_PATH,
        SCAN_FAILURE_PATH,
        BOOTSTRAP_PATH,
    )
    for path in required_paths:
        if not path.is_file():
            errors.append(f"missing required control file: {path.relative_to(REPO_ROOT)}")
    if errors:
        return {"valid": False, "errors": errors, "warnings": warnings}

    expected_ids = [task.task_id for task in TASKS]
    expected_goal_ids = [goal[0] for goal in GOALS]
    if len(expected_ids) != len(set(expected_ids)):
        errors.append("generator contains duplicate task IDs")
    if len(expected_goal_ids) != len(set(expected_goal_ids)):
        errors.append("generator contains duplicate goal IDs")

    actual_todo = TODO_PATH.read_text(encoding="utf-8")
    if _normalize_todo_progress(actual_todo) != _normalize_todo_progress(render_todo()):
        errors.append(
            "todo Markdown differs from its protected deterministic generator "
            "outside accepted Status progress"
        )
    if OBJECTIVES_PATH.read_text(encoding="utf-8").rstrip() != render_objectives().rstrip():
        errors.append("objective heap differs from its protected deterministic generator")
    if _load_json(PROJECTION_PATH) != projection():
        errors.append("task-board projection differs from generator")
    if _load_json(DEPENDENCY_PATH) != dependency_projection():
        errors.append("dependency projection differs from generator")

    parsed = parse_task_file(TODO_PATH, task_header_prefix="## LGSWF-")
    actual_ids = [task.task_id for task in parsed]
    if actual_ids != expected_ids:
        errors.append("parsed task IDs/order differ from generator")
    parsed_by_id = {task.task_id: task for task in parsed}
    expected_id_set = set(expected_ids)
    goal_id_set = set(expected_goal_ids)

    adjacency: dict[str, set[str]] = defaultdict(set)
    indegree = {task_id: 0 for task_id in expected_ids}
    owned: dict[str, set[str]] = {}
    completed_ids: set[str] = set()
    for task in parsed:
        metadata = task.metadata
        missing = sorted(REQUIRED_FIELDS - set(metadata))
        if missing:
            errors.append(f"{task.task_id} missing fields: {', '.join(missing)}")
            continue
        if metadata["stable task id"] != task.task_id:
            errors.append(f"{task.task_id} stable task ID mismatch")
        if metadata["parent goal id"] != "LGSWF-G000":
            errors.append(f"{task.task_id} parent goal mismatch")
        if metadata["subgoal id"] not in goal_id_set or metadata["goal id"] != metadata["subgoal id"]:
            errors.append(f"{task.task_id} subgoal mismatch")
        if metadata["board namespace"] != BOARD_NAMESPACE:
            errors.append(f"{task.task_id} board namespace mismatch")
        if not re.fullmatch(r"[0-9a-f]{40}", metadata["base revision"]):
            errors.append(f"{task.task_id} base revision is not exact")
        if task.task_id != "LGSWF-000" and metadata["base semantic-state root"] != SEMANTIC_BOOTSTRAP:
            errors.append(f"{task.task_id} unexpected bootstrap semantic root")
        try:
            vector = json.loads(metadata["resource demand"])
        except json.JSONDecodeError:
            errors.append(f"{task.task_id} resource demand is not canonical JSON")
            vector = {}
        required_vector = {
            "cpu_concurrency", "ram_mib", "gpu_memory_mib", "disk_mib",
            "network", "subprocesses", "worktree_slots", "model_input_tokens",
            "provider_concurrency", "prover_concurrency", "merge_slots",
            "persistence_mib_per_second",
        }
        if not required_vector.issubset(vector):
            errors.append(f"{task.task_id} resource vector incomplete")
        paths = split_csv(metadata["owned paths"])
        if paths != split_csv(metadata["outputs"]) or paths != split_csv(metadata["allowed paths"]):
            errors.append(f"{task.task_id} owned/output/allowed path mismatch")
        if not paths or any(not _safe_relative(path) for path in paths):
            errors.append(f"{task.task_id} has unsafe or empty owned path")
        owned[task.task_id] = set(paths)
        if task.task_id == "LGSWF-000":
            if task.status != "completed" or metadata["is schedulable"] != "false":
                errors.append("LGSWF-000 must be completed and unschedulable")
        elif task.status not in {"todo", "completed"} or metadata["is schedulable"] != "true":
            errors.append(
                f"{task.task_id} must be todo or completed and retain its generated "
                "schedulability contract"
            )
        if task.status == "completed":
            completed_ids.add(task.task_id)
        for dependency in task.depends_on:
            if dependency not in expected_id_set:
                errors.append(f"{task.task_id} references unknown dependency {dependency}")
                continue
            adjacency[dependency].add(task.task_id)
            indegree[task.task_id] += 1

    for task in parsed:
        if task.task_id not in completed_ids:
            continue
        missing_dependencies = sorted(set(task.depends_on) - completed_ids)
        if missing_dependencies:
            errors.append(
                f"{task.task_id} is completed before dependencies: "
                f"{', '.join(missing_dependencies)}"
            )
        missing_outputs = sorted(
            path
            for path in owned.get(task.task_id, set())
            if not (REPO_ROOT / path).is_file()
        )
        if missing_outputs:
            errors.append(
                f"{task.task_id} is completed with missing declared outputs: "
                f"{', '.join(missing_outputs)}"
            )

    ready = sorted(
        task_id for task_id, degree in indegree.items()
        if degree == 0 and task_id != "LGSWF-000"
    )
    # LGSWF-000 is already accepted and therefore removes one predecessor.
    ready_after_bootstrap = sorted(
        task.task_id for task in parsed
        if task.task_id != "LGSWF-000"
        and all(dependency == "LGSWF-000" for dependency in task.depends_on)
    )
    expected_ready = ["LGSWF-001", "LGSWF-002", "LGSWF-003", "LGSWF-004"]
    if ready_after_bootstrap != expected_ready:
        errors.append(f"unexpected initial ready frontier: {ready_after_bootstrap}")

    queue = deque(task_id for task_id, degree in indegree.items() if degree == 0)
    visited = 0
    degrees = dict(indegree)
    while queue:
        node = queue.popleft()
        visited += 1
        for successor in adjacency.get(node, ()):
            degrees[successor] -= 1
            if degrees[successor] == 0:
                queue.append(successor)
    if visited != len(expected_ids):
        errors.append("task dependency graph contains a cycle")

    for index, left in enumerate(expected_ids):
        for right in expected_ids[index + 1 :]:
            overlap = owned.get(left, set()) & owned.get(right, set())
            if overlap and not (
                _reachable(adjacency, left, right)
                or _reachable(adjacency, right, left)
            ):
                errors.append(
                    f"unordered overlapping writes {left}/{right}: {sorted(overlap)}"
                )

    # All post-bootstrap product mutations must be downstream of the root-and-plan gate.
    for task_id in expected_ids:
        if task_id.startswith("LGSWF-0") and int(task_id.split("-")[1]) < 10:
            continue
        if not _reachable(adjacency, "LGSWF-009", task_id):
            errors.append(f"{task_id} is not gated by canonical roots and PlanRevision r1")

    config = _load_json(CONFIG_PATH)
    initial = config.get("initial_projection") or {}
    if initial.get("task_count") != len(TASKS) or initial.get("goal_count") != len(GOALS):
        errors.append("config projection counts mismatch")
    if initial.get("ready_task_ids") != expected_ready:
        errors.append("config initial ready task list mismatch")
    if config.get("max_lanes") != 2 or config.get("strict_task_sharding") is not False:
        errors.append("bootstrap must use two dynamic inventory lanes")
    if config.get("objective_refill_enabled") or config.get("codebase_refill_enabled"):
        errors.append("bootstrap refill must remain disabled")
    protected = set(config.get("protected_paths") or ())
    required_protected = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in required_paths
        if path not in {REVISION_PATH, SCAN_FAILURE_PATH, BOOTSTRAP_PATH}
    } | {
        "artifacts/logic_governed_semantic_work_fabric/baseline/revision-comparison.json",
        "artifacts/logic_governed_semantic_work_fabric/baseline/semantic-scan-bootstrap-failures.json",
        "artifacts/logic_governed_semantic_work_fabric/control/board-bootstrap.json",
        "scripts/generate_logic_governed_semantic_work_fabric_board.py",
        "scripts/validate_logic_governed_semantic_work_fabric_board.py",
    }
    if not required_protected.issubset(protected):
        errors.append("config does not protect every control authority")

    revision = _load_json(REVISION_PATH)
    authority = revision.get("implementation_authority") or {}
    if ((authority.get("accelerator") or {}).get("commit") != ACCELERATOR_BASE):
        errors.append("accelerator checked authority mismatch")
    if ((authority.get("datasets") or {}).get("commit") != DATASETS_BASE):
        errors.append("datasets checked authority mismatch")
    scan = _load_json(SCAN_FAILURE_PATH)
    if scan.get("canonical_semantic_state_root") is not None or scan.get("status") != "semantic_analysis_inconclusive":
        errors.append("bootstrap scan evidence must not claim a canonical root")
    bootstrap = _load_json(BOOTSTRAP_PATH)
    if bootstrap.get("planning_base") != PLANNING_BASE or bootstrap.get("completion_authoritative") is not False:
        errors.append("bootstrap receipt authority mismatch")

    if "agent_supervisor/semantic_state/" in render_todo():
        errors.append("board attempts to scaffold absent accelerator semantic_state package")
    for forbidden in (
        "new semantic index", "new capsule compiler", "new proof cache",
        "new plan-revision store", "new objective tracker", "new daemon framework",
        "new GUI", "another MCP++ profile",
    ):
        if forbidden in render_todo().lower():
            warnings.append(f"review non-goal phrase in generated board: {forbidden}")

    return {
        "schema": "ipfs_accelerate_py.agent_supervisor.logic-governed-semantic-work-fabric.board-validation@1",
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "task_count": len(parsed),
        "goal_count": len(GOALS),
        "completed_task_ids": sorted(completed_ids),
        "initial_ready_task_ids": ready_after_bootstrap,
        "planning_base": PLANNING_BASE,
        "accelerator_base": ACCELERATOR_BASE,
        "datasets_base": DATASETS_BASE,
        "semantic_bootstrap_status": scan.get("status"),
        "product_fabric_complete": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-all", action="store_true")
    args = parser.parse_args()
    if not args.check_all:
        parser.error("--check-all is required")
    report = validate()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
