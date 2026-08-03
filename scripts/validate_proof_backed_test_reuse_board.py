#!/usr/bin/env python3
"""Fail-closed preflight for the proof-backed test-reuse program."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path, PurePosixPath
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
for key, value in {
    "IPFS_ACCELERATE_DUCKDB_ONLY": "1",
    "IPFS_ACCEL_SKIP_CORE": "1",
    "IPFS_KIT_DISABLE": "1",
    "IPFS_DATASETS_AUTO_INSTALL": "false",
    "IPFS_AUTO_INSTALL": "false",
    "IPFS_DATASETS_PY_MINIMAL_IMPORTS": "1",
    "IPFS_TEST_PROOF_REUSE_MODE": "off",
    "PYTHONDONTWRITEBYTECODE": "1",
}.items():
    os.environ.setdefault(key, value)
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))

from ipfs_accelerate_py.agent_supervisor.objectives.objective_graph import (  # noqa: E402
    materialize_task_dependency_dag,
    parse_goal_heap,
)
from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (  # noqa: E402
    parse_task_file,
)


PLAN_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "46-proof-backed-test-reuse-plan-2026-07-31.md"
)
OBJECTIVE_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "46-proof-backed-test-reuse.objectives.md"
)
TODO_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "46-proof-backed-test-reuse.todo.md"
)
CONFIG_PATH = REPO_ROOT / "config" / "proof_backed_test_reuse_supervisor.json"

EXPECTED_GOAL_IDS = frozenset(
    {
        "PTR-G000",
        "PTR-G010",
        "PTR-G020",
        "PTR-G030",
        "PTR-G040",
        "PTR-G050",
        "PTR-G060",
        "PTR-G070",
        "PTR-G080",
        "PTR-G090",
        "PTR-G100",
        "PTR-G110",
    }
)
EXPECTED_TASK_IDS = frozenset(
    {
        "PTR-000",
        "PTR-001",
        "PTR-002",
        "PTR-003",
        "PTR-010",
        "PTR-011",
        "PTR-012",
        "PTR-020",
        "PTR-021",
        "PTR-022",
        "PTR-030",
        "PTR-031",
        "PTR-040",
        "PTR-041",
        "PTR-042",
        "PTR-043",
        "PTR-050",
        "PTR-051",
        "PTR-052",
        "PTR-053",
        "PTR-060",
        "PTR-061",
        "PTR-070",
        "PTR-080",
        "PTR-081",
        "PTR-090",
        "PTR-091",
        "PTR-092",
        "PTR-093",
        "PTR-100",
        "PTR-101",
        "PTR-102",
        "PTR-110",
        "PTR-111",
        "PTR-112",
        "PTR-120",
        "PTR-121",
        "PTR-122",
        "PTR-130",
    }
)
INITIAL_READY = frozenset({"PTR-001", "PTR-002", "PTR-003"})
EXTENSION_TASK_IDS = frozenset(
    {
        "PTR-110",
        "PTR-111",
        "PTR-112",
        "PTR-120",
        "PTR-121",
        "PTR-122",
        "PTR-130",
    }
)
EXTENSION_WAVE_ONE = frozenset({"PTR-110", "PTR-111", "PTR-112"})
GOAL_STATES = frozenset(
    {
        "active",
        "provisionally_complete",
        "verified_complete",
        "analysis_inconclusive",
        "blocked",
        "reopened",
    }
)
TASK_STATES = frozenset({"todo", "in_progress", "blocked", "completed"})
REQUIRED_GOAL_FIELDS = (
    "status",
    "parent",
    "depends_on",
    "fib_priority",
    "track",
    "priority",
    "bundle",
    "goal",
    "evidence",
    "outputs",
    "validation",
    "acceptance",
    "gap_task",
    "refinement",
    "embedding_query",
    "ast_query",
)
REQUIRED_TASK_FIELDS = (
    "status",
    "completion",
    "is schedulable",
    "review only",
    "priority",
    "track",
    "depends on",
    "goal id",
    "outputs",
    "validation",
    "board namespace",
    "bundle",
    "parallel lane",
    "resource class",
    "implementation timeout seconds",
    "predicted files",
    "predicted symbols",
    "interfaces",
    "submodules",
    "generated artifacts",
    "conflict policy",
    "symbolic first",
    "llm context budget bytes",
    "provider role",
    "context budget tokens",
    "preconditions",
    "effects",
    "evidence subset",
    "acceptance",
)
REQUIRED_DIRECT_TASK_DEPENDENCIES = {
    "PTR-090": frozenset({"PTR-061", "PTR-070", "PTR-081"}),
    "PTR-100": frozenset({"PTR-091", "PTR-092", "PTR-093"}),
    "PTR-102": frozenset({"PTR-091", "PTR-092", "PTR-093", "PTR-101"}),
    "PTR-120": frozenset({"PTR-110", "PTR-111", "PTR-112"}),
    "PTR-121": frozenset({"PTR-110", "PTR-111", "PTR-112"}),
    "PTR-122": frozenset({"PTR-102", "PTR-110", "PTR-111", "PTR-112"}),
    "PTR-130": frozenset({"PTR-120", "PTR-121", "PTR-122"}),
}
REQUIRED_DATASETS_TASKS = frozenset(
    {"PTR-040", "PTR-041", "PTR-042", "PTR-070"}
)
REQUIRED_KIT_TASKS = frozenset({"PTR-080", "PTR-081"})
EXPECTED_PROTECTED_PATHS = frozenset(
    {
        "implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md",
        "implementation_plan/docs/46-proof-backed-test-reuse.objectives.md",
        "implementation_plan/docs/46-proof-backed-test-reuse.todo.md",
        "config/proof_backed_test_reuse_supervisor.json",
        "scripts/validate_proof_backed_test_reuse_board.py",
        "scripts/proof_backed_test_reuse_supervisor.py",
    }
)
EXPECTED_SUBMODULES = (
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
)


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _csv(value: object) -> tuple[str, ...]:
    text = str(value or "")
    return tuple(item.strip() for item in text.split(",") if item.strip())


def _semicolon_terms(value: object) -> tuple[str, ...]:
    text = str(value or "")
    return tuple(item.strip() for item in text.split(";") if item.strip())


def _safe_relative_paths(values: Iterable[str], *, field: str) -> list[str]:
    errors: list[str] = []
    for raw in values:
        value = str(raw).strip().replace("\\", "/")
        path = PurePosixPath(value)
        if (
            not value
            or "\x00" in value
            or ";" in value
            or path.is_absolute()
            or ".." in path.parts
            or path.as_posix() in {".", ".."}
            or (path.parts and path.parts[0].endswith(":"))
        ):
            errors.append(f"{field} contains unsafe path {raw!r}")
    return errors


def _cycle_nodes(edges: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cycle: set[str] = set()

    def visit(node: str, lineage: tuple[str, ...]) -> None:
        if node in visited:
            return
        if node in visiting:
            if node in lineage:
                cycle.update(lineage[lineage.index(node) :])
            cycle.add(node)
            return
        visiting.add(node)
        for dependency in edges.get(node, ()):
            visit(dependency, (*lineage, node))
        visiting.remove(node)
        visited.add(node)

    for item in sorted(edges):
        visit(item, ())
    return tuple(sorted(cycle))


def _ancestors(node: str, edges: dict[str, tuple[str, ...]]) -> frozenset[str]:
    result: set[str] = set()
    stack = list(edges.get(node, ()))
    while stack:
        dependency = stack.pop()
        if dependency in result:
            continue
        result.add(dependency)
        stack.extend(edges.get(dependency, ()))
    return frozenset(result)


def _bool_text(value: object) -> bool | None:
    normalized = str(value or "").strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    return None


def validate(
    objective_path: Path,
    todo_path: Path,
    config_path: Path,
    plan_path: Path,
) -> dict[str, object]:
    errors: list[str] = []
    for label, path in (
        ("plan", plan_path),
        ("objective", objective_path),
        ("task board", todo_path),
        ("configuration", config_path),
    ):
        if not path.is_file():
            errors.append(f"{label} file is missing: {path}")
    if errors:
        return {
            "schema": "ipfs_accelerate_py/proof-backed-test-reuse-preflight@1",
            "valid": False,
            "errors": errors,
        }

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return {
            "schema": "ipfs_accelerate_py/proof-backed-test-reuse-preflight@1",
            "valid": False,
            "errors": [f"configuration is not valid JSON: {exc}"],
        }

    expected_config = {
        "profileId": "proof-backed-test-reuse-v1",
        "integrationBranch": "agent/proof-backed-test-reuse",
        "taskPrefix": "## PTR-",
        "boardNamespace": "proof-backed-test-reuse-v1",
    }
    for field, expected in expected_config.items():
        if config.get(field) != expected:
            errors.append(
                f"configuration {field} must be {expected!r}, got "
                f"{config.get(field)!r}"
            )
    parallel = config.get("parallelRuntime")
    if not isinstance(parallel, dict):
        errors.append("configuration parallelRuntime must be an object")
        parallel = {}
    if parallel.get("laneCount") != 3:
        errors.append("parallelRuntime.laneCount must be 3")
    if parallel.get("strictTaskSharding") is not True:
        errors.append("parallelRuntime.strictTaskSharding must be true")
    if parallel.get("objectiveRefillEnabled") is not False:
        errors.append("objective refill must be disabled for the sealed board")
    if parallel.get("codebaseRefillEnabled") is not False:
        errors.append("codebase refill must be disabled for the sealed board")
    if tuple(parallel.get("worktreeSubmodulePaths") or ()) != EXPECTED_SUBMODULES:
        errors.append(
            "worktreeSubmodulePaths must contain exactly the three outer "
            "IPFS Python repositories"
        )
    protected_paths = frozenset(parallel.get("protectedPaths") or ())
    if protected_paths != EXPECTED_PROTECTED_PATHS:
        errors.append(
            "protectedPaths mismatch: expected "
            f"{sorted(EXPECTED_PROTECTED_PATHS)}, got {sorted(protected_paths)}"
        )
    optional_capabilities = config.get("optionalCapabilities")
    if not isinstance(optional_capabilities, dict) or optional_capabilities.get(
        "launchGate"
    ) is not False:
        errors.append("optional proof infrastructure must not be a launch gate")
    objective_projection = config.get("objectiveProjection")
    if not isinstance(objective_projection, dict):
        errors.append("configuration objectiveProjection must be an object")
        objective_projection = {}
    if objective_projection.get("mode") != "reviewed_bounded_closeout":
        errors.append(
            "objectiveProjection.mode must be reviewed_bounded_closeout"
        )
    if frozenset(objective_projection.get("implementationTaskIds") or ()) != (
        EXTENSION_TASK_IDS
    ):
        errors.append(
            "objectiveProjection implementation task inventory mismatch"
        )
    if frozenset(
        objective_projection.get("initialClaimableTaskIds") or ()
    ) != EXTENSION_WAVE_ONE:
        errors.append(
            "objectiveProjection initial claimable task inventory mismatch"
        )
    if objective_projection.get("authorityWriter") != "outer_controller_only":
        errors.append(
            "objective completion authority writer must be the outer controller"
        )
    if objective_projection.get("workerLaneReconciliationEnabled") is not False:
        errors.append("worker-lane objective reconciliation must remain disabled")
    if objective_projection.get("autonomousGapGenerationEnabled") is not False:
        errors.append("autonomous objective-gap generation must remain disabled")
    if objective_projection.get("artifactLocation") != "state_root":
        errors.append("objective completion artifacts must live under state root")
    if objective_projection.get("reconciliationPhases") != 3:
        errors.append("objective closeout must declare exactly three phases")
    if objective_projection.get("closeoutControllerTaskId") != "PTR-121":
        errors.append("objective closeout controller task must be PTR-121")
    if objective_projection.get("operatorHandoffTaskId") != "PTR-130":
        errors.append("objective operator handoff task must be PTR-130")
    projection_path_fields = (
        "gatePathSuffix",
        "evidencePathSuffix",
        "lifecycleProjectionPathSuffix",
        "candidateObjectivePathSuffix",
        "supervisorHealthInputPathSuffix",
        "statusPathSuffix",
    )
    projection_paths = tuple(
        str(objective_projection.get(field) or "")
        for field in projection_path_fields
    )
    errors.extend(
        _safe_relative_paths(
            projection_paths,
            field="objectiveProjection state-root paths",
        )
    )
    if len(set(projection_paths)) != len(projection_paths):
        errors.append("objectiveProjection state-root paths must be unique")
    common_environment = parallel.get("commonEnvironment") or {}
    if common_environment.get("IPFS_TEST_PROOF_REUSE_MODE") != "off":
        errors.append("implementation validation must force proof reuse off")

    objective_text = objective_path.read_text(encoding="utf-8")
    raw_goal_headers = re.findall(
        r"^## (PTR-G\d{3})\s+\S.*$", objective_text, flags=re.MULTILINE
    )
    goals = parse_goal_heap(objective_text)
    goal_ids = [goal.goal_id for goal in goals]
    goal_id_set = set(goal_ids)
    if len(raw_goal_headers) != len(goals):
        errors.append(
            "objective header/parser count mismatch: "
            f"headers={len(raw_goal_headers)} parsed={len(goals)}"
        )
    if len(goal_ids) != len(goal_id_set):
        duplicate_ids = sorted(
            item for item in goal_id_set if goal_ids.count(item) > 1
        )
        errors.append(f"duplicate goal ids: {duplicate_ids}")
    if goal_id_set != EXPECTED_GOAL_IDS:
        errors.append(
            "goal inventory mismatch: missing="
            f"{sorted(EXPECTED_GOAL_IDS - goal_id_set)} extra="
            f"{sorted(goal_id_set - EXPECTED_GOAL_IDS)}"
        )

    goal_parent_edges: dict[str, tuple[str, ...]] = {}
    goal_dependency_edges: dict[str, tuple[str, ...]] = {}
    for goal in goals:
        if not re.fullmatch(r"PTR-G\d{3}", goal.goal_id):
            errors.append(f"invalid goal id: {goal.goal_id}")
        missing = [name for name in REQUIRED_GOAL_FIELDS if name not in goal.fields]
        if missing:
            errors.append(f"{goal.goal_id} missing fields: {missing}")
        status = str(goal.fields.get("status") or "").strip()
        if status not in GOAL_STATES:
            errors.append(f"{goal.goal_id} has noncanonical status {status!r}")
        parent = str(goal.fields.get("parent") or "").strip()
        parents = (parent,) if parent else ()
        goal_parent_edges[goal.goal_id] = parents
        if parent and parent not in goal_id_set:
            errors.append(f"{goal.goal_id} has unknown parent {parent!r}")
        dependencies = _csv(goal.fields.get("depends_on"))
        goal_dependency_edges[goal.goal_id] = dependencies
        for dependency in dependencies:
            if dependency not in goal_id_set:
                errors.append(
                    f"{goal.goal_id} has unknown goal dependency {dependency!r}"
                )
        try:
            fib_priority = int(str(goal.fields.get("fib_priority") or ""))
            if fib_priority < 1:
                raise ValueError
        except ValueError:
            errors.append(f"{goal.goal_id} has invalid fib priority")
        outputs = _csv(goal.fields.get("outputs"))
        if not outputs:
            errors.append(f"{goal.goal_id} has no outputs")
        errors.extend(
            f"{goal.goal_id}: {item}"
            for item in _safe_relative_paths(outputs, field="outputs")
        )
        for name in (
            "goal",
            "evidence",
            "validation",
            "acceptance",
            "gap_task",
            "refinement",
            "embedding_query",
            "ast_query",
        ):
            if not str(goal.fields.get(name) or "").strip():
                errors.append(f"{goal.goal_id} has empty {name}")
        required_evidence = _csv(goal.fields.get("evidence"))
        acceptance_criteria = _semicolon_terms(
            goal.fields.get("acceptance_criteria")
        )
        if acceptance_criteria != required_evidence:
            errors.append(
                f"{goal.goal_id} machine acceptance criteria must exactly "
                "match Evidence in order: expected "
                f"{list(required_evidence)}, got {list(acceptance_criteria)}"
            )
    parent_cycles = _cycle_nodes(goal_parent_edges)
    if parent_cycles:
        errors.append(f"goal parent cycle: {list(parent_cycles)}")
    dependency_cycles = _cycle_nodes(goal_dependency_edges)
    if dependency_cycles:
        errors.append(f"goal dependency cycle: {list(dependency_cycles)}")
    roots = sorted(
        goal_id for goal_id, parents in goal_parent_edges.items() if not parents
    )
    if roots != ["PTR-G000"]:
        errors.append(f"expected only PTR-G000 as root, got {roots}")

    todo_text = todo_path.read_text(encoding="utf-8")
    raw_task_headers = re.findall(
        r"^## (PTR-\d{3})\s+\S.*$", todo_text, flags=re.MULTILINE
    )
    ambiguous_headers = re.findall(
        r"^## (PTR-(?!G\d{3}\b|\d{3}\b)\S+).*$",
        todo_text,
        flags=re.MULTILINE,
    )
    if ambiguous_headers:
        errors.append(f"ambiguous PTR headings: {ambiguous_headers}")
    tasks = parse_task_file(todo_path, "## PTR-")
    task_ids = [task.task_id for task in tasks]
    task_id_set = set(task_ids)
    if len(raw_task_headers) != len(tasks):
        errors.append(
            "task header/parser count mismatch: "
            f"headers={len(raw_task_headers)} parsed={len(tasks)}"
        )
    if len(task_ids) != len(task_id_set):
        duplicate_ids = sorted(
            item for item in task_id_set if task_ids.count(item) > 1
        )
        errors.append(f"duplicate task ids: {duplicate_ids}")
    if task_id_set != EXPECTED_TASK_IDS:
        errors.append(
            "task inventory mismatch: missing="
            f"{sorted(EXPECTED_TASK_IDS - task_id_set)} extra="
            f"{sorted(task_id_set - EXPECTED_TASK_IDS)}"
        )

    task_by_id = {task.task_id: task for task in tasks}
    task_edges: dict[str, tuple[str, ...]] = {}
    predicted_by_task: dict[str, frozenset[str]] = {}
    task_records: list[dict[str, object]] = []
    canonical_task_cids: list[str] = []
    for task in tasks:
        if not re.fullmatch(r"PTR-\d{3}", task.task_id):
            errors.append(f"invalid task id: {task.task_id}")
        missing = [
            name for name in REQUIRED_TASK_FIELDS if name not in task.metadata
        ]
        if missing:
            errors.append(f"{task.task_id} missing fields: {missing}")
        if task.status not in TASK_STATES:
            errors.append(
                f"{task.task_id} has noncanonical normalized status "
                f"{task.status!r}"
            )
        if task.priority not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"{task.task_id} has invalid priority {task.priority!r}")
        goal_id = str(task.metadata.get("goal id") or "").strip()
        if goal_id not in goal_id_set:
            errors.append(f"{task.task_id} has unknown goal id {goal_id!r}")
        dependencies = tuple(task.depends_on)
        task_edges[task.task_id] = tuple(
            dependency for dependency in dependencies if dependency in task_id_set
        )
        for dependency in dependencies:
            if dependency == task.task_id:
                errors.append(f"{task.task_id} depends on itself")
            elif dependency not in task_id_set:
                errors.append(
                    f"{task.task_id} has unknown dependency {dependency!r}"
                )
        if not task.outputs:
            errors.append(f"{task.task_id} has no outputs")
        errors.extend(
            f"{task.task_id}: {item}"
            for item in _safe_relative_paths(task.outputs, field="outputs")
        )
        predicted_files = _csv(task.metadata.get("predicted files"))
        predicted_by_task[task.task_id] = frozenset(predicted_files)
        if not predicted_files:
            errors.append(f"{task.task_id} has no predicted files")
        errors.extend(
            f"{task.task_id}: {item}"
            for item in _safe_relative_paths(
                predicted_files, field="predicted files"
            )
        )
        if set(task.outputs) != set(predicted_files):
            errors.append(
                f"{task.task_id} outputs and predicted files must match exactly"
            )
        validation_text = str(task.metadata.get("validation") or "").strip()
        if not task.validation or not validation_text:
            errors.append(f"{task.task_id} has no validation command")
        elif not validation_text.startswith("IPFS_TEST_PROOF_REUSE_MODE=off "):
            errors.append(
                f"{task.task_id} validation does not force proof reuse off"
            )
        if not task.acceptance:
            errors.append(f"{task.task_id} has empty acceptance")
        if task.board_namespace != "proof-backed-test-reuse-v1":
            errors.append(
                f"{task.task_id} has unexpected board namespace "
                f"{task.board_namespace!r}"
            )
        # This field describes whether the task is executable work, not its
        # current lifecycle state. Completion updates must not rewrite the
        # task contract or canonical execution role.
        expected_schedulable = task.task_id != "PTR-000"
        schedulable = _bool_text(task.metadata.get("is schedulable"))
        if schedulable is None or schedulable != expected_schedulable:
            errors.append(
                f"{task.task_id} is schedulable must be "
                f"{str(expected_schedulable).lower()}"
            )
        if _bool_text(task.metadata.get("review only")) is not False:
            errors.append(f"{task.task_id} review only must be false")
        if _bool_text(task.metadata.get("symbolic first")) is not True:
            errors.append(f"{task.task_id} symbolic first must be true")
        if str(task.metadata.get("allow concurrent with") or "").strip():
            errors.append(
                f"{task.task_id} must not override dependency/file conflicts"
            )
        try:
            timeout = int(
                str(task.metadata.get("implementation timeout seconds") or "")
            )
            if timeout < 300 or timeout > 10800:
                raise ValueError
        except ValueError:
            errors.append(f"{task.task_id} has invalid implementation timeout")
        try:
            context_budget = int(
                str(task.metadata.get("llm context budget bytes") or "")
            )
            if context_budget < 4096 or context_budget > 65536:
                raise ValueError
        except ValueError:
            errors.append(f"{task.task_id} has invalid LLM context budget")
        provider_role = str(task.metadata.get("provider role") or "").strip()
        try:
            context_budget_tokens = int(
                str(task.metadata.get("context budget tokens") or "")
            )
            if task.task_id == "PTR-000":
                if context_budget_tokens != 0:
                    raise ValueError
            elif context_budget_tokens < 1024 or context_budget_tokens > 16384:
                raise ValueError
        except ValueError:
            errors.append(f"{task.task_id} has invalid context budget tokens")
        if task.task_id == "PTR-000":
            if provider_role != "operator-only":
                errors.append("PTR-000 provider role must be operator-only")
        elif lane_count := int(parallel.get("laneCount") or 0):
            shard_index = int(task.task_id.rsplit("-", 1)[1]) % lane_count
            lane_provider = str(parallel.get("providers", [])[shard_index])
            expected_role = (
                "grok-implement"
                if lane_provider in {"grok", "grok-build"}
                else "codex-implement"
            )
            if provider_role != expected_role:
                errors.append(
                    f"{task.task_id} provider role {provider_role!r} does not "
                    f"match shard {shard_index} provider {lane_provider!r}"
                )
        submodules = frozenset(_csv(task.metadata.get("submodules")))
        if not submodules.issubset(EXPECTED_SUBMODULES):
            errors.append(
                f"{task.task_id} has unexpected submodules {sorted(submodules)}"
            )
        if task.task_id in REQUIRED_DATASETS_TASKS and (
            "external/ipfs_datasets" not in submodules
        ):
            errors.append(f"{task.task_id} must declare external/ipfs_datasets")
        if task.task_id in REQUIRED_KIT_TASKS and (
            "external/ipfs_kit" not in submodules
        ):
            errors.append(f"{task.task_id} must declare external/ipfs_kit")
        canonical_task_cids.append(str(task.canonical_task_cid or ""))
        task_records.append(
            {
                "task_id": task.task_id,
                "title": task.title,
                "status": task.status,
                "goal_id": goal_id,
                "depends_on": list(task.depends_on),
                "outputs": list(task.outputs),
                "acceptance": task.acceptance,
                "board_namespace": task.board_namespace,
                "canonical_task_cid": task.canonical_task_cid,
            }
        )

    if not all(canonical_task_cids):
        errors.append("one or more canonical task CIDs are empty")
    if len(canonical_task_cids) != len(set(canonical_task_cids)):
        errors.append("canonical task CIDs are not unique")
    task_cycles = _cycle_nodes(task_edges)
    if task_cycles:
        errors.append(f"task dependency cycle: {list(task_cycles)}")
    for task_id, required_dependencies in REQUIRED_DIRECT_TASK_DEPENDENCIES.items():
        missing_dependencies = sorted(
            required_dependencies.difference(task_edges.get(task_id, ()))
        )
        if missing_dependencies:
            errors.append(
                f"{task_id} missing required direct dependencies: "
                f"{missing_dependencies}"
            )

    completed_ids = {
        task.task_id for task in tasks if task.status == "completed"
    }
    claimable_task_ids = {
        task.task_id
        for task in tasks
        if task.status == "todo"
        and set(task.depends_on).issubset(completed_ids)
    }
    configured_initial_ready = frozenset(
        str(task_id)
        for task_id in (
            parallel.get("initialClaimableTaskIds") or ()
        )
    )
    if configured_initial_ready != INITIAL_READY:
        errors.append(
            "configured initial claimable tasks mismatch: expected "
            f"{sorted(INITIAL_READY)}, got "
            f"{sorted(configured_initial_ready)}"
        )
    if completed_ids == {"PTR-000"}:
        if claimable_task_ids != INITIAL_READY:
            errors.append(
                "initial claimable tasks mismatch: expected "
                f"{sorted(INITIAL_READY)}, got "
                f"{sorted(claimable_task_ids)}"
            )
    else:
        if "PTR-000" not in completed_ids:
            errors.append("progressed board must retain PTR-000 completion")
        for task_id in sorted(completed_ids):
            missing_completed_dependencies = sorted(
                set(task_edges.get(task_id, ())).difference(completed_ids)
            )
            if missing_completed_dependencies:
                errors.append(
                    f"{task_id} completed before dependencies "
                    f"{missing_completed_dependencies}"
                )
    legacy_task_ids = EXPECTED_TASK_IDS - EXTENSION_TASK_IDS
    extension_unstarted = all(
        task_by_id[task_id].status == "todo"
        for task_id in EXTENSION_TASK_IDS
    )
    if legacy_task_ids.issubset(completed_ids) and extension_unstarted:
        if claimable_task_ids != EXTENSION_WAVE_ONE:
            errors.append(
                "reviewed objective-completion expansion claimable tasks "
                f"must be {sorted(EXTENSION_WAVE_ONE)}, got "
                f"{sorted(claimable_task_ids)}"
            )
    lane_count = int(parallel.get("laneCount") or 0)
    initial_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in INITIAL_READY
    } if lane_count > 0 else set()
    if initial_shards != {0, 1, 2}:
        errors.append(
            f"initial tasks do not cover all three numeric shards: "
            f"{sorted(initial_shards)}"
        )
    extension_wave_shards = {
        int(task_id.rsplit("-", 1)[1]) % lane_count
        for task_id in EXTENSION_WAVE_ONE
    } if lane_count > 0 else set()
    if extension_wave_shards != {0, 1, 2}:
        errors.append(
            "objective-completion expansion wave does not cover all three "
            f"numeric shards: {sorted(extension_wave_shards)}"
        )

    unordered_conflicts: list[dict[str, object]] = []
    task_ancestors = {
        task_id: _ancestors(task_id, task_edges) for task_id in task_ids
    }
    for index, left in enumerate(sorted(task_ids)):
        for right in sorted(task_ids)[index + 1 :]:
            if left in task_ancestors[right] or right in task_ancestors[left]:
                continue
            overlap = sorted(predicted_by_task[left] & predicted_by_task[right])
            if overlap:
                unordered_conflicts.append(
                    {"left": left, "right": right, "paths": overlap}
                )
    if unordered_conflicts:
        errors.append(
            "unordered tasks have predicted-file conflicts: "
            + json.dumps(unordered_conflicts, sort_keys=True)
        )

    dependency_graph = materialize_task_dependency_dag(task_records)
    if dependency_graph.invalid_task_cids:
        errors.append(
            "typed dependency graph has invalid task CIDs: "
            f"{list(dependency_graph.invalid_task_cids)}"
        )
    if dependency_graph.repair_evidence:
        errors.append(
            "typed dependency graph requires repair: "
            + json.dumps(
                [item.to_dict() for item in dependency_graph.repair_evidence],
                sort_keys=True,
            )
        )

    return {
        "schema": "ipfs_accelerate_py/proof-backed-test-reuse-preflight@1",
        "valid": not errors,
        "errors": errors,
        "plan_path": str(plan_path),
        "plan_sha256": _sha256(plan_path),
        "objective_path": str(objective_path),
        "objective_sha256": _sha256(objective_path),
        "goal_count": len(goals),
        "root_goal_ids": roots,
        "todo_path": str(todo_path),
        "todo_sha256": _sha256(todo_path),
        "task_count": len(tasks),
        "completed_task_count": len(completed_ids),
        "initial_ready_task_ids": sorted(INITIAL_READY),
        "initial_ready_shards": sorted(initial_shards),
        "reviewed_extension_task_ids": sorted(EXTENSION_TASK_IDS),
        "reviewed_extension_wave_one_task_ids": sorted(EXTENSION_WAVE_ONE),
        "reviewed_extension_wave_one_shards": sorted(extension_wave_shards),
        "current_claimable_task_ids": sorted(claimable_task_ids),
        "current_claimable_shards": sorted(
            {
                int(task_id.rsplit("-", 1)[1]) % lane_count
                for task_id in claimable_task_ids
            }
            if lane_count > 0
            else set()
        ),
        "unordered_predicted_file_conflicts": unordered_conflicts,
        "dependency_graph_id": _canonical_sha256(dependency_graph.to_dict()),
        "configuration_path": str(config_path),
        "configuration_sha256": _sha256(config_path),
        "optional_proof_infrastructure_is_launch_gate": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan-path", type=Path, default=PLAN_PATH)
    parser.add_argument("--objective-path", type=Path, default=OBJECTIVE_PATH)
    parser.add_argument("--todo-path", type=Path, default=TODO_PATH)
    parser.add_argument("--config-path", type=Path, default=CONFIG_PATH)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = validate(
        args.objective_path.resolve(),
        args.todo_path.resolve(),
        args.config_path.resolve(),
        args.plan_path.resolve(),
    )
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    sys.stdout.write(payload)
    return 0 if result["valid"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
