#!/usr/bin/env python3
"""Fail-closed validator for the sealed VerifiedGuiOptimizer work board.

The configured-board launcher executes this program as ``--check-all`` and
accepts the board only when stdout is one JSON object with ``valid: true``.
This validator deliberately uses only the Python standard library so that
control-plane validation does not import either product code or optional
provider dependencies.
"""

from __future__ import annotations

import hashlib
import json
import re
import shlex
import subprocess
import sys
from collections.abc import Iterable, Mapping
from pathlib import Path, PurePosixPath
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path("config/verified_gui_optimizer_scheduler.json")
SCHEMA = (
    "ipfs_accelerate_py.agent_supervisor."
    "verified_gui_optimizer.scheduler_config@1"
)
BOARD_NAMESPACE = "verified-gui-optimizer-v1"
MERGE_BRANCH = "feature/verified-gui-optimizer"
TASK_PREFIX = "VGO-"
TARGET_SOURCE = "swissknife/web/js/apps/agent-supervisor.js"

TASK_IDS = (
    "VGO-000",
    "VGO-001",
    "VGO-002",
    "VGO-003",
    "VGO-009",
    "VGO-010",
    "VGO-011",
    "VGO-012",
    "VGO-016",
    "VGO-020",
    "VGO-021",
    "VGO-023",
    "VGO-027",
    "VGO-030",
    "VGO-031",
    "VGO-032",
    "VGO-034",
    "VGO-040",
    "VGO-041",
    "VGO-043",
    "VGO-045",
    "VGO-050",
    "VGO-051",
    "VGO-053",
    "VGO-054",
    "VGO-060",
    "VGO-061",
    "VGO-062",
    "VGO-068",
    "VGO-070",
    "VGO-071",
    "VGO-072",
    "VGO-075",
    "VGO-080",
    "VGO-081",
    "VGO-083",
    "VGO-086",
    "VGO-090",
    "VGO-091",
    "VGO-093",
    "VGO-096",
    "VGO-099",
)
GOAL_IDS = (
    "VGO-G000",
    "VGO-G010",
    "VGO-G020",
    "VGO-G030",
    "VGO-G040",
    "VGO-G050",
    "VGO-G060",
    "VGO-G070",
    "VGO-G080",
    "VGO-G090",
    "VGO-G100",
    "VGO-G110",
)
EXPECTED_WAVES = (
    ("VGO-000",),
    ("VGO-001", "VGO-009"),
    ("VGO-002",),
    ("VGO-003", "VGO-010", "VGO-011"),
    ("VGO-012", "VGO-016"),
    ("VGO-020", "VGO-021", "VGO-023", "VGO-027"),
    ("VGO-030", "VGO-031", "VGO-032", "VGO-034"),
    ("VGO-040", "VGO-043", "VGO-045"),
    ("VGO-041", "VGO-050", "VGO-051", "VGO-061"),
    ("VGO-054", "VGO-062"),
    ("VGO-053",),
    ("VGO-060", "VGO-070", "VGO-071", "VGO-075"),
    ("VGO-068",),
    ("VGO-072",),
    ("VGO-083", "VGO-086"),
    ("VGO-080",),
    ("VGO-081",),
    ("VGO-090", "VGO-096"),
    ("VGO-091",),
    ("VGO-093",),
    ("VGO-099",),
)

TASK_REQUIRED_FIELDS = (
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
    "resource stage",
    "implementation timeout seconds",
    "predicted files",
    "interfaces",
    "conflict policy",
    "preconditions",
    "effects",
    "evidence subset",
    "acceptance",
)
GOAL_REQUIRED_FIELDS = (
    "status",
    "parent",
    "depends on",
    "fib priority",
    "priority",
    "track",
    "bundle",
    "direct child goals",
    "producing tasks",
    "goal",
    "evidence",
    "outputs",
    "validation",
    "acceptance",
    "conflict policy",
)

CONTROL_PATHS = frozenset(
    {
        "implementation_plan/docs/49-verified-gui-optimizer-plan-2026-08-11.md",
        "implementation_plan/docs/49-verified-gui-optimizer.objectives.md",
        "implementation_plan/docs/49-verified-gui-optimizer.todo.md",
        CONFIG_PATH.as_posix(),
        "scripts/validate_verified_gui_optimizer_board.py",
        "scripts/ops/agent_supervisor/implementation_supervisor_entry.py",
        "scripts/ops/verified_gui_optimizer_vgo001_oracle.py",
        "scripts/ops/verified_gui_optimizer_vgo009_oracle.py",
        "scripts/ops/verified_gui_optimizer_status.py",
        "implementation_plan/evidence/verified_gui_optimizer/provider_route/provider_fallback_policy_authorization_20260812.json",
        "implementation_plan/evidence/verified_gui_optimizer/provider_route/local_profile_lifecycle_root_pin_20260812.json",
        "implementation_plan/evidence/verified_gui_optimizer/provider_route/local_profile_lifecycle_witness_20260812.json",
        "implementation_plan/evidence/verified_gui_optimizer/recovery/provider_capsule_retry_amendment_20260812.json",
    }
)
ALLOWED_OUTPUT_PREFIXES = (
    "swissknife/",
    "external/ipfs_datasets/",
    "external/ipfs_accelerate/",
    "implementation_plan/evidence/verified_gui_optimizer/",
)
ALLOWED_OUTPUT_FILES = frozenset(
    {
        "scripts/gui-opt",
        "scripts/gui_opt.py",
    }
)
PROHIBITED_DEPENDENCY_PATTERNS = (
    "semantic-index",
    "semantic_index",
    "proof-cache",
    "proof_cache",
    "formal_verification_cache",
    "model-routing",
    "model_routing",
    "model_router",
    "knowledge_graphs/adapters/code_evidence",
)


class DuplicateKeyError(ValueError):
    """Raised when the supposedly sealed JSON repeats a field."""


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_object_without_duplicates,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path}: root must be an object")
    return value


def _split_csv(value: str) -> list[str]:
    normalized = str(value or "").strip()
    if normalized.lower() in {"", "-", "none", "n/a"}:
        return []
    return [
        item.strip().strip("`'\"")
        for item in normalized.split(",")
        if item.strip().strip("`'\"")
    ]


def _parse_markdown_records(
    path: Path,
    heading_pattern: re.Pattern[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    records: dict[str, dict[str, Any]] = {}
    errors: list[str] = []
    current_id = ""
    current_title = ""
    current_line = 0
    current_metadata: dict[str, str] = {}

    def flush() -> None:
        nonlocal current_id, current_title, current_line, current_metadata
        if not current_id:
            return
        if current_id in records:
            errors.append(f"{path}: duplicate heading {current_id}")
        else:
            records[current_id] = {
                "title": current_title,
                "line": current_line,
                "metadata": dict(current_metadata),
            }
        current_id = ""
        current_title = ""
        current_line = 0
        current_metadata = {}

    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if line.startswith("## "):
            flush()
            match = heading_pattern.fullmatch(line)
            if match is not None:
                current_id = match.group("id")
                current_title = match.group("title").strip()
                current_line = line_number
            elif line.startswith("## VGO-"):
                errors.append(f"{path}:{line_number}: malformed VGO heading")
            continue
        if not current_id:
            continue
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        key, value = stripped[2:].split(":", 1)
        normalized_key = key.strip().lower()
        if normalized_key in current_metadata:
            errors.append(
                f"{path}:{line_number}: {current_id} repeats metadata "
                f"field {normalized_key!r}"
            )
        current_metadata[normalized_key] = value.strip()
    flush()
    return records, errors


def _safe_relative_path(value: str) -> bool:
    if not value or "\x00" in value or "\\" in value or "://" in value:
        return False
    if any(character in value for character in "*?[]{}"):
        return False
    path = PurePosixPath(value)
    return bool(
        not path.is_absolute()
        and value not in {".", ".."}
        and ".." not in path.parts
        and not (path.parts and path.parts[0].endswith(":"))
    )


def _allowed_output_path(value: str) -> bool:
    return _safe_relative_path(value) and (
        value in ALLOWED_OUTPUT_FILES
        or any(value.startswith(prefix) for prefix in ALLOWED_OUTPUT_PREFIXES)
    )


def _task_shard(task_id: str, lane_count: int = 4) -> int:
    """Match ImplementationDaemon._task_belongs_to_shard exactly."""

    digest = hashlib.sha256(task_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % lane_count


def _cycle_nodes(graph: Mapping[str, Iterable[str]]) -> set[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    cyclic: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cyclic.add(node)
            return
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph.get(node, ()):
            if dependency in graph:
                visit(dependency)
                if dependency in cyclic:
                    cyclic.add(node)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    return cyclic


def _command_version(command: str) -> str:
    try:
        result = subprocess.run(
            [command, "--version"],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def _validate_config(config: Mapping[str, Any], errors: list[str]) -> None:
    exact_scalars = {
        "schema": SCHEMA,
        "taskboard_path": (
            "implementation_plan/docs/49-verified-gui-optimizer.todo.md"
        ),
        "objectives_path": (
            "implementation_plan/docs/49-verified-gui-optimizer.objectives.md"
        ),
        "plan_path": (
            "implementation_plan/docs/49-verified-gui-optimizer-plan-2026-08-11.md"
        ),
        "validator_path": "scripts/validate_verified_gui_optimizer_board.py",
        "task_prefix": TASK_PREFIX,
        "board_namespace": BOARD_NAMESPACE,
        "merge_target_branch": MERGE_BRANCH,
        "max_lanes": 4,
        "strict_task_sharding": True,
        "exit_when_all_tracks_terminal": True,
        "objective_refill_enabled": False,
        "codebase_refill_enabled": False,
        "retry_budget_guardrail_enabled": False,
        "dependency_guardrail_enabled": False,
        "reconciliation_guardrail_enabled": False,
        "poll_interval_seconds": 5,
        "daemon_interval_seconds": 30,
        "check_interval_seconds": 20,
        "stale_seconds": 900,
        "watchdog_startup_grace_seconds": 300,
        "max_restarts": 3,
        "max_task_attempts": 4,
        "implementation_retry_budget": 3,
        "validation_retry_budget": 3,
        "merge_retry_budget": 3,
        "implementation_timeout_seconds": 7200,
        "implementation_max_timeout_seconds": 14400,
        "implementation_log_stall_seconds": 600,
    }
    for field, expected in exact_scalars.items():
        if config.get(field) != expected:
            errors.append(
                f"config.{field} must equal {expected!r}, got "
                f"{config.get(field)!r}"
            )

    source = config.get("source_binding")
    expected_source = {
        "accelerator_required_ancestor": (
            "ce448eae6ab5706832d3ae88b041f9d38ac82ae8"
        ),
        "accelerator_required_branch": MERGE_BRANCH,
        "ipfs_accelerate_submodule_path": "external/ipfs_accelerate",
        "ipfs_accelerate_planning_revision": (
            "4784c932f87aafbd949714c05439836ab0f446a7"
        ),
        "ipfs_datasets_submodule_path": "external/ipfs_datasets",
        "ipfs_datasets_planning_revision": (
            "a2f5400b7cb89c8481819379a1b7b9959fe81d45"
        ),
        "swissknife_submodule_path": "swissknife",
        "swissknife_planning_revision": (
            "26f06277888b09a3e7c9b4a3b844001f1dbc0841"
        ),
    }
    if not isinstance(source, Mapping):
        errors.append("config.source_binding must be an object")
        source = {}
    for field, expected in expected_source.items():
        if source.get(field) != expected:
            errors.append(f"config.source_binding.{field} is not sealed")
    for field in (
        "require_initialized_gitlinks",
        "require_superproject_gitlink_equals_nested_head",
        "require_clean_nested_worktree_at_task_start",
        "record_recursive_repository_forest_at_launch",
        "changed_revision_requires_fresh_inventory_and_baseline",
    ):
        if source.get(field) is not True:
            errors.append(f"config.source_binding.{field} must be true")
    if source.get("planning_revision_is_runtime_completion_evidence") is not False:
        errors.append(
            "config.source_binding.planning_revision_is_runtime_completion_evidence "
            "must be false"
        )

    expected_submodules = [
        "external/ipfs_accelerate",
        "external/ipfs_datasets",
        "swissknife",
    ]
    if config.get("worktree_submodule_paths") != expected_submodules:
        errors.append("config.worktree_submodule_paths is not the sealed list")

    protected = config.get("protected_paths")
    if not isinstance(protected, list):
        errors.append("config.protected_paths must be a list")
    else:
        if len(protected) != len(set(protected)):
            errors.append("config.protected_paths contains duplicates")
        missing = sorted(CONTROL_PATHS - set(protected))
        if missing:
            errors.append(f"config.protected_paths omits {missing}")
        for value in protected:
            if not isinstance(value, str) or not _safe_relative_path(value):
                errors.append(f"unsafe protected path: {value!r}")

    runtime = config.get("runtime_paths")
    expected_runtime = {
        "root": "data/agent_supervisor/verified_gui_optimizer",
        "state": "data/agent_supervisor/verified_gui_optimizer/state",
        "worktrees": "data/agent_supervisor/verified_gui_optimizer/worktrees",
        "merge_queue": (
            "data/agent_supervisor/verified_gui_optimizer/merge-queue"
        ),
        "logs": "data/agent_supervisor/verified_gui_optimizer/logs",
    }
    if not isinstance(runtime, Mapping):
        errors.append("config.runtime_paths must be an object")
        runtime = {}
    for field, expected in expected_runtime.items():
        value = runtime.get(field)
        if value != expected:
            errors.append(f"config.runtime_paths.{field} is not sealed")
        if isinstance(value, str) and field != "root":
            root_parts = PurePosixPath(expected_runtime["root"]).parts
            if PurePosixPath(value).parts[: len(root_parts)] != root_parts:
                errors.append(f"config.runtime_paths.{field} escapes runtime root")
    if runtime.get("generated_runtime_artifacts_are_completion_authority") is not False:
        errors.append("generated runtime artifacts cannot be completion authority")

    lanes = config.get("lanes")
    if not isinstance(lanes, list) or len(lanes) != 4:
        errors.append("config.lanes must contain four entries")
    else:
        for index, lane in enumerate(lanes):
            if not isinstance(lane, Mapping):
                errors.append(f"config.lanes[{index}] must be an object")
                continue
            expected = {
                "index": index,
                "name": f"vgo-lane-{index}",
                "strict_shard_remainder": index,
            }
            for field, value in expected.items():
                if lane.get(field) != value:
                    errors.append(f"config.lanes[{index}].{field} is invalid")
            for task_id in lane.get("initial_task_ids", []):
                if task_id not in TASK_IDS or _task_shard(task_id) != index:
                    errors.append(
                        f"config.lanes[{index}] has a cross-shard initial task "
                        f"{task_id!r}"
                    )

    provider = config.get("provider")
    expected_provider = {
        "primary_provider_id": "grok_cli",
        "primary_model_id": "grok-4.5",
        "fallback_provider_id": "codex",
        "fallback_model_id": "gpt-5.6-terra",
        "fallback_trigger": "primary_quota_or_auth_unavailable",
        "fallback_reasoning_effort": "high",
        "route_authorization_path": (
            "implementation_plan/evidence/verified_gui_optimizer/"
            "provider_route/"
            "provider_fallback_policy_authorization_20260812.json"
        ),
        "max_concurrency": 4,
        "secrets_from_environment_only": True,
        "secrets_in_argv_prompts_logs_or_receipts": False,
    }
    if not isinstance(provider, Mapping):
        errors.append("config.provider must be an object")
        provider = {}
    for field, expected in expected_provider.items():
        if provider.get(field) != expected:
            errors.append(f"config.provider.{field} violates ordered policy")
    if "provider_id" in provider or "model_id" in provider:
        errors.append("ordered provider policy cannot mix legacy provider fields")

    dependency_policy = config.get("dependency_policy")
    if not isinstance(dependency_policy, Mapping):
        errors.append("config.dependency_policy must be an object")
    else:
        if dependency_policy.get("standalone_subsystem") is not True:
            errors.append("VerifiedGuiOptimizer must remain standalone")
        for field in (
            "semantic_index_dependency_allowed",
            "prior_semantic_capsule_dependency_allowed",
            "proof_cache_dependency_allowed",
            "model_routing_dependency_allowed",
        ):
            if dependency_policy.get(field) is not False:
                errors.append(f"config.dependency_policy.{field} must be false")

    toolchain = config.get("toolchain_policy")
    expected_toolchain = {
        "node_version": "v22.19.0",
        "npm_version": "10.8.2",
        "bin_path": (
            "data/agent_supervisor/verified_gui_optimizer/"
            "toolchain/node_modules/.bin"
        ),
        "swissknife_dependency_source": "swissknife/node_modules",
        "install_from_committed_lock_only": True,
    }
    if not isinstance(toolchain, Mapping):
        errors.append("config.toolchain_policy must be an object")
        toolchain = {}
    for field, expected in expected_toolchain.items():
        if toolchain.get(field) != expected:
            errors.append(f"config.toolchain_policy.{field} is not sealed")
    node_version = _command_version("node")
    npm_version = _command_version("npm")
    if node_version != expected_toolchain["node_version"]:
        errors.append(
            "active Node toolchain must be v22.19.0; prepend the sealed "
            "runtime toolchain bin to PATH"
        )
    if npm_version != expected_toolchain["npm_version"]:
        errors.append(
            "active npm toolchain must be 10.8.2; prepend the sealed "
            "runtime toolchain bin to PATH"
        )
    for relative in (
        "swissknife/node_modules/.bin/vitest",
        "swissknife/node_modules/.bin/playwright",
        "swissknife/node_modules/@ucans/ucans",
    ):
        if not (REPO_ROOT / relative).exists():
            errors.append(
                f"missing lock-provisioned shared SwissKnife dependency {relative}"
            )

    scope = config.get("scope_policy")
    if not isinstance(scope, Mapping):
        errors.append("config.scope_policy must be an object")
    else:
        if scope.get("selected_source") != TARGET_SOURCE:
            errors.append("config scope must bind the selected Agent Supervisor source")
        if scope.get("optimize_all_applications") is not False:
            errors.append("config scope cannot authorize all-application optimization")
        if scope.get("arbitrary_repository_code_execution_during_scan") is not False:
            errors.append("static scanning cannot execute arbitrary repository code")
        if scope.get("production_credentials_or_services_in_tests") is not False:
            errors.append("tests cannot use production credentials or services")

    initial = config.get("initial_projection")
    expected_initial = {
        "task_count": 42,
        "completed_task_ids": ["VGO-000"],
        "ready_task_ids": ["VGO-001", "VGO-002", "VGO-009"],
        "blocked_task_ids": [],
        "terminal_task_id": "VGO-099",
        "goal_count": 12,
        "root_goal_id": "VGO-G000",
    }
    if not isinstance(initial, Mapping):
        errors.append("config.initial_projection must be an object")
    else:
        for field, expected in expected_initial.items():
            if initial.get(field) != expected:
                errors.append(f"config.initial_projection.{field} is not sealed")

    raw_waves = config.get("waves")
    if not isinstance(raw_waves, list) or len(raw_waves) != len(EXPECTED_WAVES):
        errors.append("config.waves must contain the twenty-one sealed waves")
    else:
        seen: list[str] = []
        for index, (row, expected_ids) in enumerate(zip(raw_waves, EXPECTED_WAVES)):
            if not isinstance(row, Mapping):
                errors.append(f"config.waves[{index}] must be an object")
                continue
            if row.get("index") != index:
                errors.append(f"config.waves[{index}].index is invalid")
            task_ids = row.get("task_ids")
            if task_ids != list(expected_ids):
                errors.append(f"config.waves[{index}].task_ids is not sealed")
            if isinstance(task_ids, list):
                seen.extend(task_ids)
        if len(seen) != len(TASK_IDS) or set(seen) != set(TASK_IDS):
            errors.append("config waves do not cover every task exactly once")


def _validate_tasks(
    records: Mapping[str, Mapping[str, Any]],
    config: Mapping[str, Any],
    errors: list[str],
) -> None:
    if tuple(records) != TASK_IDS:
        errors.append(
            "task headings must be the exact ordered 42-ID sealed projection"
        )
    wave_by_task = {
        task_id: wave_index
        for wave_index, wave in enumerate(EXPECTED_WAVES)
        for task_id in wave
    }
    dependencies: dict[str, list[str]] = {}
    statuses: dict[str, str] = {}
    tasks_by_goal: dict[str, list[str]] = {goal_id: [] for goal_id in GOAL_IDS}
    predicted_owner_by_wave: dict[tuple[int, str], str] = {}
    for task_id, record in records.items():
        metadata = record["metadata"]
        title = str(record.get("title") or "").strip()
        if not title:
            errors.append(f"{task_id}: title must be nonempty")
        for field in TASK_REQUIRED_FIELDS:
            if field not in metadata:
                errors.append(f"{task_id}: missing metadata field {field!r}")
            elif field not in {"depends on"} and not metadata[field].strip():
                errors.append(f"{task_id}: metadata field {field!r} is empty")
        status = metadata.get("status", "").lower()
        statuses[task_id] = status
        expected_completion = "auto"
        expected_review_only = "false"
        if task_id == "VGO-000" and status != "completed":
            errors.append("VGO-000: status must remain completed")
        elif task_id != "VGO-000" and status not in {"pending", "completed"}:
            errors.append(
                f"{task_id}: status must be pending or completed, got {status!r}"
            )
        if metadata.get("completion", "").lower() != expected_completion:
            errors.append(f"{task_id}: completion must be {expected_completion}")
        no_change_completion = metadata.get(
            "no-change completion", "forbidden"
        ).strip().lower()
        if no_change_completion != "forbidden":
            errors.append(
                f"{task_id}: no-change completion must be forbidden on the "
                "sealed implementation board"
            )
        if metadata.get("is schedulable", "").lower() != "true":
            errors.append(f"{task_id}: Is schedulable must be true")
        if metadata.get("review only", "").lower() != expected_review_only:
            errors.append(
                f"{task_id}: Review only must be {expected_review_only}"
            )
        if metadata.get("board namespace") != BOARD_NAMESPACE:
            errors.append(f"{task_id}: board namespace mismatch")
        goal_id = metadata.get("goal id", "")
        if goal_id not in GOAL_IDS:
            errors.append(f"{task_id}: unknown Goal id {goal_id!r}")
        else:
            tasks_by_goal[goal_id].append(task_id)

        try:
            timeout = int(metadata.get("implementation timeout seconds", ""))
        except ValueError:
            timeout = 0
        max_timeout = int(config.get("implementation_max_timeout_seconds") or 0)
        if timeout < 1 or timeout > max_timeout:
            errors.append(
                f"{task_id}: Implementation timeout seconds must be in "
                f"[1, {max_timeout}]"
            )

        task_dependencies = _split_csv(metadata.get("depends on", ""))
        dependencies[task_id] = task_dependencies
        if task_id == "VGO-000" and task_dependencies:
            errors.append("VGO-000 must be the only dependency-free root task")
        if task_id != "VGO-000" and not task_dependencies:
            errors.append(f"{task_id}: non-root task must declare a dependency")
        for dependency in task_dependencies:
            if dependency not in TASK_IDS:
                errors.append(f"{task_id}: unknown dependency {dependency!r}")
                continue
            if dependency == task_id:
                errors.append(f"{task_id}: cannot depend on itself")
                continue
            if wave_by_task.get(dependency, 999) >= wave_by_task.get(task_id, -1):
                errors.append(
                    f"{task_id}: dependency {dependency} is not in an earlier wave"
                )

        outputs = _split_csv(metadata.get("outputs", ""))
        predicted = _split_csv(metadata.get("predicted files", ""))
        if not outputs:
            errors.append(f"{task_id}: Outputs must declare at least one path")
        if not predicted:
            errors.append(f"{task_id}: Predicted files must declare at least one path")
        for field_name, paths in (("Outputs", outputs), ("Predicted files", predicted)):
            if len(paths) != len(set(paths)):
                errors.append(f"{task_id}: {field_name} contains duplicate paths")
            for path in paths:
                control_seal_path = task_id == "VGO-000" and path in CONTROL_PATHS
                if not _allowed_output_path(path) and not control_seal_path:
                    errors.append(
                        f"{task_id}: {field_name} path is outside narrow roots: {path!r}"
                    )
                if path in CONTROL_PATHS and task_id != "VGO-000":
                    errors.append(
                        f"{task_id}: task cannot overwrite protected control path {path!r}"
                    )
        if not set(outputs).issubset(set(predicted)):
            errors.append(f"{task_id}: every Output must also be a Predicted file")
        for path in predicted:
            owner_key = (wave_by_task.get(task_id, -1), path)
            prior_owner = predicted_owner_by_wave.get(owner_key)
            if prior_owner is not None and prior_owner != task_id:
                errors.append(
                    f"{task_id}: Predicted file {path!r} is also owned by "
                    f"same-wave task {prior_owner}"
                )
            else:
                predicted_owner_by_wave[owner_key] = task_id

        dependency_fields = [
            metadata.get("outputs", ""),
            metadata.get("predicted files", ""),
            metadata.get("interfaces", ""),
            metadata.get("implementation dependencies", ""),
            metadata.get("reuse modules", ""),
        ]
        dependency_material = "\n".join(dependency_fields).lower()
        for pattern in PROHIBITED_DEPENDENCY_PATTERNS:
            if pattern in dependency_material:
                errors.append(
                    f"{task_id}: prohibited prior-module dependency {pattern!r}"
                )

        declared_lane = metadata.get("parallel lane", "")
        match = re.fullmatch(r"vgo-lane-([0-3])", declared_lane)
        if match is None:
            errors.append(
                f"{task_id}: Parallel lane must be one of vgo-lane-0..3"
            )
        elif int(match.group(1)) != _task_shard(task_id):
            errors.append(
                f"{task_id}: declared Parallel lane conflicts with stable hash shard"
            )

    cyclic = sorted(_cycle_nodes(dependencies))
    if cyclic:
        errors.append(f"task dependency graph is cyclic at {cyclic}")
    roots = sorted(task_id for task_id, deps in dependencies.items() if not deps)
    if roots != ["VGO-000"]:
        errors.append(f"task dependency roots must equal ['VGO-000'], got {roots}")
    if records and TARGET_SOURCE not in (
        REPO_ROOT
        / str(config.get("taskboard_path") or "")
    ).read_text(encoding="utf-8"):
        errors.append("taskboard must explicitly bind the selected Agent Supervisor source")

    # The implementation daemon commits status transitions into the sealed
    # taskboard.  A relaunch must admit that durable progress, while rejecting
    # forged completion that precedes any declared dependency.
    for task_id, status in statuses.items():
        if status != "completed":
            continue
        incomplete_dependencies = sorted(
            dependency
            for dependency in dependencies.get(task_id, [])
            if statuses.get(dependency) != "completed"
        )
        if incomplete_dependencies:
            errors.append(
                f"{task_id}: completed status is not dependency-closed; "
                f"pending dependencies {incomplete_dependencies}"
            )
    initial = config.get("initial_projection")
    initial_completed = (
        initial.get("completed_task_ids", [])
        if isinstance(initial, Mapping)
        else []
    )
    for task_id in initial_completed:
        if statuses.get(str(task_id)) != "completed":
            errors.append(
                f"config initial completed task {task_id!r} is not completed "
                "in the durable taskboard"
            )


def _validate_goals(
    records: Mapping[str, Mapping[str, Any]],
    task_records: Mapping[str, Mapping[str, Any]],
    errors: list[str],
) -> None:
    if tuple(records) != GOAL_IDS:
        errors.append("goal headings must be the exact ordered 12-ID goal heap")
    graph: dict[str, list[str]] = {}
    parents: dict[str, str] = {}
    direct_children: dict[str, list[str]] = {}
    producing_by_goal: dict[str, list[str]] = {}
    producing_mentions: set[str] = set()
    all_task_outputs = {
        path
        for task_record in task_records.values()
        for path in _split_csv(task_record["metadata"].get("outputs", ""))
    }

    def output_is_declared(output: str, declarations: Iterable[str]) -> bool:
        """Match exact files and directory prefixes explicitly ending in `/`."""

        for declaration in declarations:
            if output == declaration:
                return True
            if declaration.endswith("/") and output.startswith(declaration):
                return True
            if output.endswith("/") and declaration.startswith(output):
                return True
        return False

    def normalize_validation_path(
        cwd: PurePosixPath,
        raw: str,
    ) -> tuple[str, str | None]:
        if not raw or "\x00" in raw or "\\" in raw or "://" in raw:
            return "", "invalid validation path token"
        candidate = PurePosixPath(raw)
        if candidate.is_absolute():
            return "", "validation path must be repository-relative"
        parts = list(cwd.parts if str(cwd) != "." else ())
        for part in candidate.parts:
            if part in {"", "."}:
                continue
            if part == "..":
                if not parts:
                    return "", "validation path escapes the repository"
                parts.pop()
            else:
                parts.append(part)
        return "/".join(parts), None

    def referenced_validation_paths(
        command: str,
    ) -> tuple[set[str], list[str]]:
        """Extract paths from sealed atomic ``;`` / ``&&`` commands.

        A semicolon is an explicit scheduler command boundary, so each atom
        starts at the repository root. Within an atom, only a pure ``&&``
        chain is accepted and an optional ``cd`` must be its first segment.
        This mirrors the board's fail-closed validation-command grammar
        without importing mutable supervisor/product code.
        """

        paths: set[str] = set()
        path_errors: list[str] = []

        atoms: list[str] = []
        current: list[str] = []
        in_single_quote = False
        in_double_quote = False
        escaped = False

        def flush_atom() -> None:
            atom = "".join(current).strip()
            if atom:
                atoms.append(atom)
            else:
                path_errors.append("validation has an empty command atom")
            current.clear()

        for character in command.strip():
            if escaped:
                if character in {"\n", "\r"} and not in_single_quote:
                    path_errors.append(
                        "validation must not contain line continuation syntax"
                    )
                current.append(character)
                escaped = False
                continue
            if character == "\\" and not in_single_quote:
                current.append(character)
                escaped = True
                continue
            if character == "'" and not in_double_quote:
                in_single_quote = not in_single_quote
                current.append(character)
                continue
            if character == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
                current.append(character)
                continue
            if character == ";" and not in_single_quote and not in_double_quote:
                flush_atom()
                continue
            if character in {"\n", "\r"} and not in_single_quote:
                path_errors.append("validation must not contain shell newlines")
            current.append(character)
        flush_atom()
        if in_single_quote or in_double_quote or escaped:
            path_errors.append("validation contains unterminated shell quoting")

        for atom in atoms:
            try:
                lexer = shlex.shlex(
                    atom,
                    posix=True,
                    punctuation_chars=";&|()<>",
                )
                lexer.whitespace_split = True
                lexer.commenters = ""
                tokens = list(lexer)
            except ValueError as exc:
                path_errors.append(f"cannot parse validation command: {exc}")
                continue
            if (
                not tokens
                or tokens[0] == "&&"
                or tokens[-1] == "&&"
                or any(
                    token != "&&"
                    and any(character in token for character in ";&|()<>")
                    for token in tokens
                )
            ):
                path_errors.append("validation uses unsupported shell structure")
                continue
            segments: list[list[str]] = [[]]
            malformed = False
            for token in tokens:
                if token == "&&":
                    if not segments[-1]:
                        malformed = True
                        break
                    segments.append([])
                    continue
                segments[-1].append(token)
            if malformed or not segments[-1]:
                path_errors.append("validation has a malformed && chain")
                continue

            cwd = PurePosixPath(".")
            for index, segment in enumerate(segments):
                if segment[0] == "cd":
                    if index != 0 or len(segment) != 2:
                        path_errors.append(
                            "validation cd must be the first segment with one path"
                        )
                        continue
                    normalized, problem = normalize_validation_path(cwd, segment[1])
                    if problem:
                        path_errors.append(problem)
                    else:
                        cwd = PurePosixPath(normalized or ".")
                    continue
                for token in segment:
                    if (
                        token.startswith("-")
                        or "/" not in token
                        or re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", token)
                        or any(character in token for character in "$*?[]{}")
                    ):
                        continue
                    normalized, problem = normalize_validation_path(cwd, token)
                    if problem:
                        path_errors.append(problem)
                    elif normalized:
                        paths.add(normalized)
        return paths, path_errors

    for goal_id, record in records.items():
        metadata = record["metadata"]
        if not str(record.get("title") or "").strip():
            errors.append(f"{goal_id}: title must be nonempty")
        for field in GOAL_REQUIRED_FIELDS:
            if field not in metadata:
                errors.append(f"{goal_id}: missing metadata field {field!r}")
            elif field not in {"parent", "depends on", "direct child goals", "producing tasks"} and not metadata[field].strip():
                errors.append(f"{goal_id}: metadata field {field!r} is empty")
        if metadata.get("status", "").lower() != "pending":
            errors.append(f"{goal_id}: status must be pending at launch")
        parent_values = _split_csv(metadata.get("parent", ""))
        if goal_id == "VGO-G000":
            if parent_values:
                errors.append("VGO-G000 must not have a parent")
            parents[goal_id] = ""
        else:
            if len(parent_values) != 1 or parent_values[0] not in GOAL_IDS:
                errors.append(f"{goal_id}: Parent must name one declared goal")
                parents[goal_id] = ""
            else:
                parents[goal_id] = parent_values[0]
        dependencies = _split_csv(metadata.get("depends on", ""))
        graph[goal_id] = dependencies
        for dependency in dependencies:
            if dependency not in GOAL_IDS:
                errors.append(f"{goal_id}: unknown goal dependency {dependency!r}")
            if dependency == goal_id:
                errors.append(f"{goal_id}: cannot depend on itself")
        children = _split_csv(metadata.get("direct child goals", ""))
        direct_children[goal_id] = children
        for child in children:
            if child not in GOAL_IDS:
                errors.append(f"{goal_id}: unknown direct child {child!r}")

        producing_tasks = _split_csv(metadata.get("producing tasks", ""))
        producing_by_goal[goal_id] = producing_tasks
        owned_outputs: set[str] = set()
        for task_id in producing_tasks:
            if task_id not in TASK_IDS:
                errors.append(f"{goal_id}: unknown producing task {task_id!r}")
            else:
                producing_mentions.add(task_id)
                task_record = task_records.get(task_id)
                if task_record is not None:
                    task_goal = task_record["metadata"].get("goal id", "")
                    if task_goal != goal_id:
                        errors.append(
                            f"{goal_id}: producing task {task_id} has primary "
                            f"Goal id {task_goal!r}"
                        )
                    owned_outputs.update(
                        _split_csv(task_record["metadata"].get("outputs", ""))
                    )

        goal_outputs = _split_csv(metadata.get("outputs", ""))
        if len(goal_outputs) != len(set(goal_outputs)):
            errors.append(f"{goal_id}: Outputs contains duplicate paths")
        for output in goal_outputs:
            if not _safe_relative_path(output):
                errors.append(f"{goal_id}: unsafe Output path {output!r}")
            elif not output_is_declared(output, owned_outputs):
                errors.append(
                    f"{goal_id}: Output {output!r} is not owned by a "
                    "declared producing task"
                )

        validation_paths, path_errors = referenced_validation_paths(
            metadata.get("validation", "")
        )
        for problem in path_errors:
            errors.append(f"{goal_id}: {problem}")
        for relative in sorted(validation_paths):
            if (
                relative not in CONTROL_PATHS
                and not output_is_declared(relative, all_task_outputs)
                and not (REPO_ROOT / relative).exists()
            ):
                errors.append(
                    f"{goal_id}: Validation references undeclared path "
                    f"{relative!r}"
                )

    for task_id, task_record in task_records.items():
        primary_goal = task_record["metadata"].get("goal id", "")
        if (
            primary_goal in records
            and task_id not in producing_by_goal.get(primary_goal, [])
        ):
            errors.append(
                f"{task_id}: primary Goal id {primary_goal} does not list the "
                "task in Producing tasks"
            )

    for goal_id, parent in parents.items():
        if not parent:
            continue
        if goal_id not in direct_children.get(parent, []):
            errors.append(
                f"{goal_id}: Parent {parent} does not list it as a direct child"
            )
    for parent, children in direct_children.items():
        for child in children:
            if parents.get(child) != parent:
                errors.append(
                    f"{parent}: direct child {child} has Parent {parents.get(child)!r}"
                )
    parent_graph = {
        goal_id: [parent] if parent else [] for goal_id, parent in parents.items()
    }
    cyclic = sorted(_cycle_nodes(parent_graph))
    if cyclic:
        errors.append(f"goal parent graph is cyclic at {cyclic}")
    dependency_cycles = sorted(_cycle_nodes(graph))
    if dependency_cycles:
        errors.append(f"goal dependency graph is cyclic at {dependency_cycles}")
    missing_task_mentions = sorted(set(task_records) - producing_mentions)
    if missing_task_mentions:
        errors.append(
            "goal heap Producing tasks omits declared tasks: "
            f"{missing_task_mentions}"
        )

    root_metadata = records.get("VGO-G000", {}).get("metadata", {})
    root_claims = "\n".join(
        (
            root_metadata.get("acceptance", ""),
            root_metadata.get("conflict policy", ""),
        )
    ).lower()
    for required_claim in (
        "exactly 15",
        "final receipt",
        "dependency audit",
        "integrity rather than truth",
        "proof cache",
    ):
        if required_claim not in root_claims:
            errors.append(
                f"VGO-G000: final acceptance boundary omits {required_claim!r}"
            )


def validate() -> dict[str, Any]:
    errors: list[str] = []
    config_file = REPO_ROOT / CONFIG_PATH
    try:
        config = _load_json(config_file)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return {
            "schema": "verified-gui-optimizer-board-validation@1",
            "valid": False,
            "errors": [f"cannot load scheduler config: {type(exc).__name__}: {exc}"],
            "summary": {"task_count": 0, "goal_count": 0, "wave_count": 0},
        }

    _validate_config(config, errors)
    required_paths = {
        CONFIG_PATH.as_posix(),
        str(config.get("taskboard_path") or ""),
        str(config.get("objectives_path") or ""),
        str(config.get("plan_path") or ""),
        str(config.get("validator_path") or ""),
        "scripts/ops/agent_supervisor/implementation_supervisor_entry.py",
        "scripts/ops/verified_gui_optimizer_status.py",
    }
    for relative in sorted(required_paths):
        if not relative or not _safe_relative_path(relative):
            errors.append(f"invalid required control path {relative!r}")
        elif not (REPO_ROOT / relative).is_file():
            errors.append(f"missing required control file {relative}")

    task_records: dict[str, dict[str, Any]] = {}
    goal_records: dict[str, dict[str, Any]] = {}
    task_path = REPO_ROOT / str(config.get("taskboard_path") or "")
    goal_path = REPO_ROOT / str(config.get("objectives_path") or "")
    plan_path = REPO_ROOT / str(config.get("plan_path") or "")
    if task_path.is_file():
        task_records, parse_errors = _parse_markdown_records(
            task_path,
            re.compile(
                r"^## (?P<id>VGO-[0-9]{3}) (?P<title>\S.*)$"
            ),
        )
        errors.extend(parse_errors)
        _validate_tasks(task_records, config, errors)
    if goal_path.is_file():
        goal_records, parse_errors = _parse_markdown_records(
            goal_path,
            re.compile(
                r"^## (?P<id>VGO-G[0-9]{3}) (?P<title>\S.*)$"
            ),
        )
        errors.extend(parse_errors)
        _validate_goals(goal_records, task_records, errors)
    if plan_path.is_file():
        plan_text = plan_path.read_text(encoding="utf-8")
        for required_text in (
            "VerifiedGuiOptimizer",
            "Agent Supervisor",
            TARGET_SOURCE,
            "formally verified",
            "heuristic",
            "human review",
        ):
            if required_text.lower() not in plan_text.lower():
                errors.append(f"plan is missing required scope/evidence text {required_text!r}")

    unique_errors = sorted(dict.fromkeys(errors))
    return {
        "schema": "verified-gui-optimizer-board-validation@1",
        "valid": not unique_errors,
        "errors": unique_errors,
        "summary": {
            "task_count": len(task_records),
            "goal_count": len(goal_records),
            "wave_count": len(config.get("waves", []))
            if isinstance(config.get("waves"), list)
            else 0,
            "strict_lane_count": int(config.get("max_lanes") or 0),
            "selected_source": TARGET_SOURCE,
            "refill_enabled": bool(
                config.get("objective_refill_enabled")
                or config.get("codebase_refill_enabled")
            ),
        },
    }


def main(argv: list[str]) -> int:
    if argv != ["--check-all"]:
        report = {
            "schema": "verified-gui-optimizer-board-validation@1",
            "valid": False,
            "errors": ["usage: validate_verified_gui_optimizer_board.py --check-all"],
            "summary": {"task_count": 0, "goal_count": 0, "wave_count": 0},
        }
        print(json.dumps(report, sort_keys=True, separators=(",", ":")))
        return 2
    try:
        report = validate()
    except Exception as exc:  # Fail closed while preserving the JSON-only contract.
        report = {
            "schema": "verified-gui-optimizer-board-validation@1",
            "valid": False,
            "errors": [f"validator exception: {type(exc).__name__}: {exc}"],
            "summary": {"task_count": 0, "goal_count": 0, "wave_count": 0},
        }
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0 if report.get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
