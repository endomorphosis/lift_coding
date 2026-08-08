#!/usr/bin/env python3
"""Fail-closed validator for the deterministic contract-repair control plane."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "implementation_plan/docs/"
    "48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair-plan-2026-08-08.md"
)
OBJECTIVES_REL = (
    "implementation_plan/docs/"
    "48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.objectives.md"
)
TODO_REL = (
    "implementation_plan/docs/48-ipfs-accelerate-deterministic-swissknife-mcplusplus-repair.todo.md"
)
CONFIG_REL = "config/deterministic_swissknife_mcplusplus_repair_scheduler.json"
BOOTSTRAP_SEAL_REL = "config/deterministic_contract_repair_bootstrap_seal.json"
BOOTSTRAP_VALIDATION_REL = "config/deterministic_contract_repair_bootstrap_validation.json"
VALIDATOR_REL = "scripts/validate_deterministic_contract_repair_board.py"
BOARD_NAMESPACE = "deterministic-swissknife-mcplusplus-contract-repair-v1"
TASK_PREFIX = "DCR-"
GOAL_PREFIX = "DCR-G"
SCHEMA = (
    "ipfs_accelerate_py.agent_supervisor."
    "deterministic_swissknife_mcplusplus_repair.scheduler_config@1"
)

TASK_STATES = frozenset({"todo", "in_progress", "blocked", "completed"})
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
REQUIRED_GOAL_FIELDS = (
    "status",
    "parent",
    "depends on",
    "fib priority",
    "track",
    "priority",
    "bundle",
    "goal",
    "evidence",
    "outputs",
    "validation",
    "acceptance",
    "gap task",
    "refinement",
    "embedding query",
    "ast query",
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
ORDERED_IMPLEMENTATION_TASK_FIELDS = {
    "implementation mode": "ordered_provider",
    "runtime model calls": "0",
    "symbolic first": "true",
    "llm context budget bytes": "262144",
    "provider role": "grok-implement, codex-review",
    "context budget tokens": "16384",
}
PATH_TASK_FIELDS = (
    "outputs",
    "predicted files",
    "submodules",
    "generated artifacts",
)
EXPECTED_WORKTREE_ROOTS = (
    "Mcp-Plus-Plus",
    "external/ipfs_accelerate",
    "external/ipfs_datasets",
    "external/ipfs_kit",
    "swissknife",
)
REQUIRED_CONFIG_PATHS = {
    "taskboard_path": TODO_REL,
    "objectives_path": OBJECTIVES_REL,
    "plan_path": PLAN_REL,
    "validator_path": VALIDATOR_REL,
}
REQUIRED_PROTECTED_PATHS = frozenset(
    {
        PLAN_REL,
        OBJECTIVES_REL,
        TODO_REL,
        CONFIG_REL,
        VALIDATOR_REL,
        BOOTSTRAP_SEAL_REL,
        BOOTSTRAP_VALIDATION_REL,
        "data/agent_supervisor/deterministic_contract_repair/no-llm-policy.json",
        "data/agent_supervisor/deterministic_contract_repair/disposition-schema.json",
        "data/agent_supervisor/deterministic_contract_repair/root-policy.json",
        "data/agent_supervisor/deterministic_contract_repair/capabilities.json",
    }
)


class ValidationFailure(ValueError):
    """A control artifact cannot be parsed without weakening validation."""


def _normalize_field(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _content_id(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _read(relative: str) -> str:
    path = REPO_ROOT / relative
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ValidationFailure(f"cannot read {relative}: {type(exc).__name__}: {exc}") from exc


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationFailure(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_config() -> dict[str, Any]:
    try:
        payload = json.loads(
            _read(CONFIG_REL),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except json.JSONDecodeError as exc:
        raise ValidationFailure(f"invalid scheduler JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValidationFailure("scheduler JSON root must be an object")
    return payload


def _safe_relative(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value.strip().replace("\\", "/")
    if normalized.lower() in {"none", "n/a"}:
        return True
    path = PurePosixPath(normalized)
    return bool(
        normalized
        and "\x00" not in normalized
        and "\n" not in normalized
        and not path.is_absolute()
        and path.as_posix() not in {".", ".."}
        and ".." not in path.parts
        and not normalized.startswith("-")
        and not any(character in normalized for character in "*?[]{}")
        and not (path.parts and path.parts[0].endswith(":"))
    )


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _refs(value: str, *, goal: bool = False) -> list[str]:
    pattern = r"\bDCR-G\d{3}\b" if goal else r"\bDCR-\d{3}\b"
    return re.findall(pattern, value)


def _sections(
    text: str,
    *,
    id_pattern: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    header = re.compile(rf"(?m)^## ({id_pattern})(?:\s+([^\n]+))?\s*$")
    matches = list(header.finditer(text))
    records: list[dict[str, Any]] = []
    duplicate_fields: list[str] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        fields: dict[str, str] = {}
        for line in text[match.end() : end].splitlines():
            field_match = re.match(r"^- ([^:]+):(?:\s*(.*))?$", line)
            if field_match is None:
                continue
            name = _normalize_field(field_match.group(1))
            if name in fields:
                duplicate_fields.append(f"{match.group(1)}:{name}")
                continue
            fields[name] = (field_match.group(2) or "").strip()
        records.append(
            {
                "id": match.group(1),
                "title": (match.group(2) or "").strip(),
                "fields": fields,
            }
        )
    return records, duplicate_fields


def _wave_block(text: str, errors: list[str]) -> list[tuple[str, list[str]]]:
    section = re.search(
        r"(?ms)^## Parallel waves\s*$.*?^```(?:text)?\s*$\n(.*?)^```\s*$",
        text,
    )
    if section is None:
        errors.append("taskboard has no parseable Parallel waves block")
        return []
    waves: list[tuple[str, list[str]]] = []
    for line_number, raw in enumerate(section.group(1).splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        match = re.fullmatch(r"(W\d+)\s+(.+)", line)
        if match is None:
            errors.append(f"invalid wave line {line_number}: {raw!r}")
            continue
        task_ids = _refs(match.group(2))
        residue = re.sub(r"DCR-\d{3}|\||\s+", "", match.group(2))
        if not task_ids or residue:
            errors.append(f"invalid task population in {match.group(1)}: {raw!r}")
            continue
        waves.append((match.group(1), task_ids))
    expected_wave_ids = [f"W{index}" for index in range(len(waves))]
    actual_wave_ids = [wave_id for wave_id, _ in waves]
    if actual_wave_ids != expected_wave_ids:
        errors.append(
            f"wave IDs must be contiguous and ordered: expected {expected_wave_ids}, got {actual_wave_ids}"
        )
    flattened = [task_id for _, task_ids in waves for task_id in task_ids]
    duplicates = sorted({task_id for task_id in flattened if flattened.count(task_id) > 1})
    if duplicates:
        errors.append(f"tasks appear in more than one wave: {duplicates}")
    return waves


def _cycle(nodes: Iterable[str], dependencies: Mapping[str, set[str]]) -> list[str]:
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(node: str) -> list[str]:
        if node in visiting:
            start = visiting.index(node)
            return [*visiting[start:], node]
        if node in visited:
            return []
        visiting.append(node)
        for dependency in sorted(dependencies.get(node, set())):
            found = visit(dependency)
            if found:
                return found
        visiting.pop()
        visited.add(node)
        return []

    for node in sorted(nodes):
        found = visit(node)
        if found:
            return found
    return []


def _validate_records(
    todo_text: str,
    objectives_text: str,
    waves: list[tuple[str, list[str]]],
    errors: list[str],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    task_records, duplicate_task_fields = _sections(todo_text, id_pattern=r"DCR-\d{3}")
    goal_records, duplicate_goal_fields = _sections(
        objectives_text,
        id_pattern=r"DCR-G\d{3}",
    )
    if duplicate_task_fields:
        errors.append(f"duplicate task fields: {sorted(duplicate_task_fields)}")
    if duplicate_goal_fields:
        errors.append(f"duplicate goal fields: {sorted(duplicate_goal_fields)}")

    task_ids_in_order = [record["id"] for record in task_records]
    goal_ids_in_order = [record["id"] for record in goal_records]
    duplicate_task_ids = sorted(
        {task_id for task_id in task_ids_in_order if task_ids_in_order.count(task_id) > 1}
    )
    duplicate_goal_ids = sorted(
        {goal_id for goal_id in goal_ids_in_order if goal_ids_in_order.count(goal_id) > 1}
    )
    if duplicate_task_ids:
        errors.append(f"duplicate task headings: {duplicate_task_ids}")
    if duplicate_goal_ids:
        errors.append(f"duplicate goal headings: {duplicate_goal_ids}")

    tasks = {record["id"]: record for record in task_records}
    goals = {record["id"]: record for record in goal_records}
    expected_task_ids = [task_id for _, task_ids in waves for task_id in task_ids]
    if task_ids_in_order != expected_task_ids:
        errors.append(
            "task headings must exactly equal Parallel waves order: "
            f"missing={sorted(set(expected_task_ids) - set(task_ids_in_order))}, "
            f"extra={sorted(set(task_ids_in_order) - set(expected_task_ids))}"
        )

    task_dependencies: dict[str, set[str]] = {}
    referenced_goal_ids: set[str] = set()
    configured_roots = set(EXPECTED_WORKTREE_ROOTS)
    for task_id, record in tasks.items():
        fields = record["fields"]
        missing = [field for field in REQUIRED_TASK_FIELDS if field not in fields]
        if missing:
            errors.append(f"{task_id} missing task fields: {missing}")
        empty = [
            field
            for field in REQUIRED_TASK_FIELDS
            if field in fields and not fields[field] and field != "depends on"
        ]
        if empty:
            errors.append(f"{task_id} has empty required task fields: {empty}")
        if fields.get("status", "").lower() not in TASK_STATES:
            errors.append(f"{task_id} has invalid Status: {fields.get('status')!r}")
        if fields.get("completion", "").lower() not in {"auto", "manual"}:
            errors.append(f"{task_id} has invalid Completion: {fields.get('completion')!r}")
        for field in ("is schedulable", "review only"):
            if fields.get(field, "").lower() not in {"true", "false"}:
                errors.append(f"{task_id} {field} must be true or false")
        if fields.get("board namespace") != BOARD_NAMESPACE:
            errors.append(f"{task_id} has wrong Board namespace")
        for field, expected in ORDERED_IMPLEMENTATION_TASK_FIELDS.items():
            if fields.get(field, "").lower() != expected:
                errors.append(f"{task_id} must set {field}={expected!r}; got {fields.get(field)!r}")
        timeout = fields.get("implementation timeout seconds", "")
        if not timeout.isdigit() or int(timeout) < 1:
            errors.append(f"{task_id} implementation timeout must be a positive integer")
        for field in PATH_TASK_FIELDS:
            for path in _csv(fields.get(field, "")):
                if not _safe_relative(path):
                    errors.append(f"{task_id} {field} contains unsafe path {path!r}")
        for root in _csv(fields.get("submodules", "")):
            if root.lower() not in {"none", "n/a"} and root not in configured_roots:
                errors.append(f"{task_id} names unconfigured submodule {root!r}")

        dependencies = set(_refs(fields.get("depends on", "")))
        if fields.get("depends on") and not dependencies:
            errors.append(f"{task_id} Depends on is not empty or a DCR task list")
        missing_dependencies = sorted(dependencies - set(tasks))
        if missing_dependencies:
            errors.append(f"{task_id} has missing dependencies: {missing_dependencies}")
        if task_id in dependencies:
            errors.append(f"{task_id} depends on itself")
        task_dependencies[task_id] = dependencies

        goal_refs = _refs(fields.get("goal id", ""), goal=True)
        if len(goal_refs) != 1 or fields.get("goal id", "") != goal_refs[0]:
            errors.append(f"{task_id} Goal id must contain exactly one bare DCR goal ID")
        else:
            referenced_goal_ids.add(goal_refs[0])

    if set(goals) != referenced_goal_ids:
        errors.append(
            "goal headings must exactly equal task Goal id population: "
            f"missing={sorted(referenced_goal_ids - set(goals))}, "
            f"extra={sorted(set(goals) - referenced_goal_ids)}"
        )
    if not goal_ids_in_order or goal_ids_in_order[0] != "DCR-G000":
        errors.append("objective heap must begin with root goal DCR-G000")

    goal_dependencies: dict[str, set[str]] = {}
    for goal_id, record in goals.items():
        fields = record["fields"]
        missing = [field for field in REQUIRED_GOAL_FIELDS if field not in fields]
        if missing:
            errors.append(f"{goal_id} missing goal fields: {missing}")
        empty = [
            field
            for field in REQUIRED_GOAL_FIELDS
            if field in fields and not fields[field] and field not in {"parent", "depends on"}
        ]
        if empty:
            errors.append(f"{goal_id} has empty required goal fields: {empty}")
        if fields.get("status", "").lower() not in GOAL_STATES:
            errors.append(f"{goal_id} has invalid Status: {fields.get('status')!r}")
        fib_priority = fields.get("fib priority", "")
        if not fib_priority.isdigit() or int(fib_priority) < 1:
            errors.append(f"{goal_id} Fib priority must be a positive integer")
        parents = set(_refs(fields.get("parent", ""), goal=True))
        declared_dependencies = set(_refs(fields.get("depends on", ""), goal=True))
        if goal_id == "DCR-G000":
            if parents:
                errors.append("DCR-G000 must not have a parent")
        elif parents != {"DCR-G000"}:
            errors.append(f"{goal_id} must have exactly parent DCR-G000")
        missing_goal_refs = sorted((parents | declared_dependencies) - set(goals))
        if missing_goal_refs:
            errors.append(f"{goal_id} has missing goal references: {missing_goal_refs}")
        if goal_id in parents | declared_dependencies:
            errors.append(f"{goal_id} references itself")
        goal_dependencies[goal_id] = parents | declared_dependencies
        gap_refs = set(_refs(fields.get("gap task", "")))
        missing_gap_refs = sorted(gap_refs - set(tasks))
        if missing_gap_refs:
            errors.append(f"{goal_id} names missing gap tasks: {missing_gap_refs}")

    task_cycle = _cycle(tasks, task_dependencies)
    if task_cycle:
        errors.append(f"task dependency cycle: {' -> '.join(task_cycle)}")
    goal_cycle = _cycle(goals, goal_dependencies)
    if goal_cycle:
        errors.append(f"goal dependency cycle: {' -> '.join(goal_cycle)}")

    wave_index = {
        task_id: index for index, (_, task_ids) in enumerate(waves) for task_id in task_ids
    }
    task_order = {
        task_id: index
        for index, task_id in enumerate(task_id for _, task_ids in waves for task_id in task_ids)
    }
    for task_id, dependencies in task_dependencies.items():
        for dependency in dependencies:
            if dependency in wave_index and task_id in wave_index:
                if wave_index[dependency] > wave_index[task_id] or (
                    wave_index[dependency] == wave_index[task_id]
                    and task_order[dependency] >= task_order[task_id]
                ):
                    errors.append(
                        f"{task_id} dependency {dependency} is later in the wave schedule"
                    )
    return tasks, goals


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ("git", *args),
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return subprocess.CompletedProcess(("git", *args), 124, "", str(exc))


def _validate_config(
    config: Mapping[str, Any],
    waves: list[tuple[str, list[str]]],
    tasks: Mapping[str, Any],
    goals: Mapping[str, Any],
    errors: list[str],
) -> None:
    if config.get("schema") != SCHEMA:
        errors.append(f"scheduler schema must be {SCHEMA!r}")
    for field, expected in REQUIRED_CONFIG_PATHS.items():
        if config.get(field) != expected:
            errors.append(f"scheduler {field} must be {expected!r}")
    if config.get("task_prefix") != TASK_PREFIX:
        errors.append(f"scheduler task_prefix must be {TASK_PREFIX!r}")
    if config.get("goal_prefix") != GOAL_PREFIX:
        errors.append(f"scheduler goal_prefix must be {GOAL_PREFIX!r}")
    if config.get("board_namespace") != BOARD_NAMESPACE:
        errors.append("scheduler board_namespace mismatch")

    for field in (*REQUIRED_CONFIG_PATHS,):
        value = config.get(field)
        if not _safe_relative(value):
            errors.append(f"scheduler {field} is unsafe: {value!r}")
    protected = config.get("protected_paths")
    if not isinstance(protected, list) or any(not _safe_relative(item) for item in protected):
        errors.append("scheduler protected_paths must be a safe path list")
        protected_set: set[str] = set()
    else:
        protected_set = set(protected)
        if len(protected_set) != len(protected):
            errors.append("scheduler protected_paths contains duplicates")
    missing_protected = sorted(REQUIRED_PROTECTED_PATHS - protected_set)
    if missing_protected:
        errors.append(f"scheduler does not protect control paths: {missing_protected}")

    if config.get("max_lanes") != 8:
        errors.append("scheduler max_lanes must be 8")
    if config.get("strict_task_sharding") is not True:
        errors.append("scheduler strict_task_sharding must be true")
    for field in (
        "exit_when_all_tracks_terminal",
        "objective_refill_enabled",
        "codebase_refill_enabled",
    ):
        if not isinstance(config.get(field), bool):
            errors.append(f"scheduler {field} must be boolean")
    if config.get("objective_refill_enabled") is not False:
        errors.append("objective refill must remain disabled for the sealed board")
    if config.get("codebase_refill_enabled") is not False:
        errors.append("codebase refill must remain disabled for the sealed board")

    lanes = config.get("lanes")
    lane_seed_ids: list[str] = []
    if not isinstance(lanes, list) or len(lanes) != 8:
        errors.append("scheduler lanes must contain exactly eight entries")
    else:
        for index, lane in enumerate(lanes):
            if not isinstance(lane, dict):
                errors.append(f"scheduler lane {index} must be an object")
                continue
            if lane.get("index") != index or lane.get("strict_shard_remainder") != index:
                errors.append(f"scheduler lane {index} has an invalid strict shard index")
            if not re.fullmatch(r"dcr-lane-\d+", str(lane.get("name") or "")):
                errors.append(f"scheduler lane {index} has an unsafe name")
            initial_ids = lane.get("initial_task_ids")
            if not isinstance(initial_ids, list) or any(item not in tasks for item in initial_ids):
                errors.append(f"scheduler lane {index} has invalid initial_task_ids")
                continue
            for task_id in initial_ids:
                expected_shard = int(
                    hashlib.sha256(task_id.encode("utf-8")).hexdigest()[:8],
                    16,
                ) % 8
                if expected_shard != index:
                    errors.append(
                        f"scheduler lane {index} seed {task_id} belongs to shard "
                        f"{expected_shard}"
                    )
                lane_seed_ids.append(task_id)

    configured_waves = config.get("waves")
    normalized_configured_waves: list[tuple[str, list[str]]] = []
    if not isinstance(configured_waves, list):
        errors.append("scheduler waves must be a list")
    else:
        for index, wave in enumerate(configured_waves):
            if not isinstance(wave, dict):
                errors.append(f"scheduler waves[{index}] must be an object")
                continue
            wave_id = wave.get("id")
            task_ids = wave.get("task_ids")
            if not isinstance(wave_id, str) or not isinstance(task_ids, list):
                errors.append(f"scheduler waves[{index}] has invalid id/task_ids")
                continue
            normalized_configured_waves.append((wave_id, task_ids))
    if normalized_configured_waves != waves:
        errors.append("scheduler waves must exactly equal the taskboard Parallel waves block")

    projection = config.get("initial_projection")
    if not isinstance(projection, dict):
        errors.append("scheduler initial_projection must be an object")
    else:
        expected_projection = {
            "task_count": len(tasks),
            "terminal_task_id": waves[-1][1][-1] if waves and waves[-1][1] else "",
            "goal_count": len(goals),
            "root_goal_id": "DCR-G000",
        }
        for field, expected in expected_projection.items():
            if projection.get(field) != expected:
                errors.append(f"scheduler initial_projection.{field} must be {expected!r}")
        task_order = [task_id for _, task_ids in waves for task_id in task_ids]
        completed = {
            task_id
            for task_id, record in tasks.items()
            if record["fields"].get("status", "").lower() == "completed"
        }
        blocked = {
            task_id
            for task_id, record in tasks.items()
            if record["fields"].get("status", "").lower() == "blocked"
        }
        ready = {
            task_id
            for task_id, record in tasks.items()
            if record["fields"].get("status", "").lower() == "todo"
            and record["fields"].get("is schedulable", "").lower() == "true"
            and set(_refs(record["fields"].get("depends on", ""))) <= completed
        }
        expected_lists = {
            "completed_task_ids": [task_id for task_id in task_order if task_id in completed],
            "ready_task_ids": [task_id for task_id in task_order if task_id in ready],
            "blocked_task_ids": [task_id for task_id in task_order if task_id in blocked],
        }
        for field, expected in expected_lists.items():
            values = projection.get(field)
            if values != expected or len(expected) != len(set(expected)):
                errors.append(
                    f"scheduler initial_projection.{field} must exactly match "
                    f"task status/dependencies: {expected}"
                )
        if len(lane_seed_ids) != len(set(lane_seed_ids)):
            errors.append("scheduler lane initial_task_ids contain duplicates")
        if set(lane_seed_ids) != ready:
            errors.append(
                "scheduler lane initial_task_ids must exactly cover the ready frontier: "
                f"{sorted(ready)}"
            )

    provider = config.get("provider")
    if not isinstance(provider, dict):
        errors.append("scheduler provider must be an object")
    else:
        expected_provider = {
            "primary_provider_id": "grok_cli",
            "primary_model_id": "grok-4.5",
            "fallback_provider_id": "codex",
            "fallback_model_id": "gpt-5.6-terra",
            "fallback_trigger": "primary_quota_exhausted",
            "fallback_reasoning_effort": "high",
            "provider_fallback_for_other_failures": False,
        }
        for field, expected in expected_provider.items():
            if provider.get(field) != expected:
                errors.append(f"scheduler provider.{field} must be {expected!r}")
        if provider.get("max_concurrency") != 8:
            errors.append("scheduler provider.max_concurrency must equal eight lanes")
        forbidden_provider_keys = {
            "provider_id",
            "model_id",
            "allow_llm",
            "allow_remote_model_provider",
        }
        present = sorted(forbidden_provider_keys & set(provider))
        if present:
            errors.append(f"scheduler contains ambiguous legacy provider fields: {present}")

    policy = config.get("execution_policy")
    expected_policy = {
        "implementation_authoring_mode": "ordered_provider",
        "implementation_provider_role": "grok-implement, codex-review",
        "repair_runtime_mode": "deterministic_only",
        "symbolic_first": True,
        "repair_runtime_model_calls": 0,
        "repair_runtime_llm_calls": 0,
        "implementation_llm_context_budget_bytes": 262144,
        "implementation_context_budget_tokens": 16384,
        "provider_fallback_allowed_only_for_primary_quota_exhaustion": True,
        "completion_from_task_prose": False,
        "current_tree_reproof_required": True,
    }
    if not isinstance(policy, dict):
        errors.append("scheduler execution_policy must be an object")
    else:
        for field, expected in expected_policy.items():
            if policy.get(field) != expected:
                errors.append(f"scheduler execution_policy.{field} must be {expected!r}")
    floors = config.get("safety_floors")
    if not isinstance(floors, dict) or not floors:
        errors.append("scheduler safety_floors must be a nonempty object")
    elif any(isinstance(value, bool) or value != 0 for value in floors.values()):
        errors.append("every scheduler safety floor must be numeric zero")

    runtime = config.get("runtime_paths")
    required_runtime = ("root", "state", "worktrees", "merge_queue", "logs")
    if not isinstance(runtime, dict):
        errors.append("scheduler runtime_paths must be an object")
    else:
        runtime_root = runtime.get("root")
        if not _safe_relative(runtime_root):
            errors.append("scheduler runtime_paths.root is unsafe")
        root_parts = PurePosixPath(str(runtime_root)).parts if isinstance(runtime_root, str) else ()
        for field in required_runtime:
            value = runtime.get(field)
            if not _safe_relative(value):
                errors.append(f"scheduler runtime_paths.{field} is unsafe")
                continue
            if field != "root" and PurePosixPath(value).parts[: len(root_parts)] != root_parts:
                errors.append(f"scheduler runtime_paths.{field} is outside runtime root")

    for field in (
        "poll_interval_seconds",
        "daemon_interval_seconds",
        "check_interval_seconds",
        "stale_seconds",
        "watchdog_startup_grace_seconds",
        "implementation_timeout_seconds",
        "implementation_max_timeout_seconds",
        "implementation_log_stall_seconds",
    ):
        value = config.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            errors.append(f"scheduler {field} must be a nonnegative number")
    for field in (
        "max_restarts",
        "max_task_attempts",
        "implementation_retry_budget",
        "validation_retry_budget",
        "merge_retry_budget",
    ):
        value = config.get(field)
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            errors.append(f"scheduler {field} must be a positive integer")

    configured_roots = config.get("worktree_submodule_paths")
    if configured_roots != list(EXPECTED_WORKTREE_ROOTS):
        errors.append(
            "scheduler worktree_submodule_paths must contain the five reviewed roots in canonical order"
        )
    source = config.get("source_binding")
    if not isinstance(source, dict):
        errors.append("scheduler source_binding must be an object")
        return
    if source.get("bootstrap_seal_path") != BOOTSTRAP_SEAL_REL:
        errors.append("source_binding bootstrap_seal_path is not the reviewed seal")
    for field in (
        "record_recursive_repository_forest_at_launch",
        "changed_revision_requires_fresh_inventory_and_baseline",
    ):
        if source.get(field) is not True:
            errors.append(f"source_binding {field} must be true")
    try:
        bootstrap_validation = json.loads(
            _read(BOOTSTRAP_VALIDATION_REL),
            object_pairs_hook=_reject_duplicate_keys,
        )
    except (ValidationFailure, json.JSONDecodeError) as exc:
        errors.append(f"bootstrap validation receipt is unreadable: {exc}")
    else:
        expected_fields = {
            "schema",
            "board_namespace",
            "accelerator_commit",
            "task_ids",
            "test_files",
            "result",
            "runtime_model_calls",
            "artifacts_verified",
            "receipt_id",
        }
        if not isinstance(bootstrap_validation, dict) or set(bootstrap_validation) != expected_fields:
            errors.append("bootstrap validation receipt fields are not exact")
        else:
            receipt_body = dict(bootstrap_validation)
            receipt_id = receipt_body.pop("receipt_id")
            if receipt_id != _content_id(receipt_body):
                errors.append("bootstrap validation receipt identity is stale or forged")
            if bootstrap_validation.get("schema") != (
                "ipfs_accelerate_py/agent-supervisor/"
                "deterministic-repair-bootstrap-validation@1"
            ):
                errors.append("bootstrap validation receipt schema is invalid")
            if bootstrap_validation.get("board_namespace") != BOARD_NAMESPACE:
                errors.append("bootstrap validation receipt board namespace is invalid")
            if bootstrap_validation.get("accelerator_commit") != source.get(
                "ipfs_accelerate_planning_revision"
            ):
                errors.append("bootstrap validation receipt accelerator revision is stale")
            if bootstrap_validation.get("task_ids") != [
                "DCR-000",
                "DCR-001",
                "DCR-002",
                "DCR-003",
                "DCR-004",
            ]:
                errors.append("bootstrap validation receipt task population is invalid")
            if bootstrap_validation.get("result") != {
                "collected": 90,
                "passed": 90,
                "failed": 0,
                "warnings": 1,
            }:
                errors.append("bootstrap validation receipt result is not passing")
            if bootstrap_validation.get("runtime_model_calls") != 0:
                errors.append("bootstrap validation receipt has nonzero runtime model calls")
            if bootstrap_validation.get("artifacts_verified") is not True:
                errors.append("bootstrap artifact verification is not sealed")
            test_files = bootstrap_validation.get("test_files")
            if (
                not isinstance(test_files, list)
                or len(test_files) != 10
                or len(set(test_files)) != 10
                or any(not _safe_relative(item) for item in test_files)
                or any(not (REPO_ROOT / item).is_file() for item in test_files)
            ):
                errors.append("bootstrap validation test file set is incomplete")
    branch = _git("branch", "--show-current")
    expected_branch = str(source.get("accelerator_required_branch") or "")
    if branch.returncode != 0 or branch.stdout.strip() != expected_branch:
        errors.append(
            "source_binding accelerator_required_branch does not match the current branch"
        )
    if config.get("merge_target_branch") != expected_branch:
        errors.append("merge_target_branch does not match source_binding branch")
    ancestor = str(source.get("accelerator_required_ancestor") or "")
    if re.fullmatch(r"[0-9a-f]{40}", ancestor) is None:
        errors.append("source_binding accelerator_required_ancestor is not a commit ID")
    else:
        ancestor_check = _git("merge-base", "--is-ancestor", ancestor, "HEAD")
        if ancestor_check.returncode != 0:
            errors.append("source_binding accelerator_required_ancestor is not an ancestor of HEAD")

    bound_roots: list[str] = []
    for key, value in source.items():
        if key.endswith("_submodule_path") and isinstance(value, str):
            bound_roots.append(value)
            prefix = key[: -len("_submodule_path")]
            planning_revision = source.get(f"{prefix}_planning_revision")
            tree = _git("ls-tree", "HEAD", "--", value)
            match = re.fullmatch(
                rf"160000 commit ([0-9a-f]{{40}})\t{re.escape(value)}\n?",
                tree.stdout,
            )
            if tree.returncode != 0 or match is None:
                errors.append(f"source-bound root is not a current gitlink: {value}")
            elif (
                not isinstance(planning_revision, str)
                or re.fullmatch(r"[0-9a-f]{40}", planning_revision) is None
            ):
                errors.append(f"source_binding planning revision for {value} is invalid")
            else:
                try:
                    planning_check = subprocess.run(
                        (
                            "git",
                            "merge-base",
                            "--is-ancestor",
                            planning_revision,
                            match.group(1),
                        ),
                        cwd=REPO_ROOT / value,
                        text=True,
                        capture_output=True,
                        check=False,
                        timeout=30,
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    errors.append(
                        f"cannot validate planning revision for {value}: "
                        f"{type(exc).__name__}: {exc}"
                    )
                else:
                    if planning_check.returncode != 0:
                        errors.append(
                            f"source_binding planning revision for {value} "
                            "is not an ancestor of its current gitlink"
                        )
    if bound_roots != list(EXPECTED_WORKTREE_ROOTS):
        errors.append("source_binding must bind all five gitlinks in canonical order")


def validate() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    required_files = (PLAN_REL, OBJECTIVES_REL, TODO_REL, CONFIG_REL, VALIDATOR_REL)
    missing = [relative for relative in required_files if not (REPO_ROOT / relative).is_file()]
    if missing:
        errors.append(f"missing control files: {missing}")
        return {
            "schema": "dcr/board-validation@1",
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "counts": {"waves": 0, "tasks": 0, "goals": 0},
        }

    try:
        todo_text = _read(TODO_REL)
        objectives_text = _read(OBJECTIVES_REL)
        config = _load_config()
    except ValidationFailure as exc:
        errors.append(str(exc))
        return {
            "schema": "dcr/board-validation@1",
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "counts": {"waves": 0, "tasks": 0, "goals": 0},
        }

    waves = _wave_block(todo_text, errors)
    tasks, goals = _validate_records(todo_text, objectives_text, waves, errors)
    _validate_config(config, waves, tasks, goals, errors)
    return {
        "schema": "dcr/board-validation@1",
        "valid": not errors,
        "board_namespace": BOARD_NAMESPACE,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "waves": len(waves),
            "tasks": len(tasks),
            "goals": len(goals),
        },
        "task_ids": [task_id for _, task_ids in waves for task_id in task_ids],
        "goal_ids": list(goals),
        "control_sha256": {relative: _sha256(REPO_ROOT / relative) for relative in required_files},
        "execution_policy": {
            "primary_provider_id": "grok_cli",
            "primary_model_id": "grok-4.5",
            "fallback_provider_id": "codex",
            "fallback_model_id": "gpt-5.6-terra",
            "fallback_reasoning_effort": "high",
            "fallback_trigger": "primary_quota_exhausted",
            "repair_runtime_mode": "deterministic_only",
            "repair_runtime_model_calls": 0,
            "repair_runtime_llm_calls": 0,
        },
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the deterministic SwissKnife/MCP++ repair board"
    )
    parser.add_argument(
        "--check-all",
        action="store_true",
        help="Validate all control, DAG, scheduler, source-binding, and no-LLM invariants",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    _build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        report = validate()
    except Exception as exc:  # fail closed at the CLI boundary
        report = {
            "schema": "dcr/board-validation@1",
            "valid": False,
            "errors": [f"validator exception: {type(exc).__name__}: {exc}"],
            "warnings": [],
        }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report.get("valid") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
