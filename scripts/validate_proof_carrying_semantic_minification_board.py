#!/usr/bin/env python3
"""Fail-closed validation for the PCSM objective handoff and source forest."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = ROOT / "scripts/generate_proof_carrying_semantic_minification_board.py"
TASK_RE = re.compile(r"^## (PCSM-\d{3}) (.+)$", re.MULTILINE)
GOAL_RE = re.compile(r"^## (PCSM-G\d{3}) (.+)$", re.MULTILINE)


def load_generator() -> Any:
    spec = importlib.util.spec_from_file_location("pcsm_board_generator", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PCSM board generator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def git(*args: str, cwd: Path = ROOT) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=cwd, text=True, capture_output=True, check=False
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def task_blocks(text: str) -> list[tuple[str, str, dict[str, str]]]:
    matches = list(TASK_RE.finditer(text))
    blocks: list[tuple[str, str, dict[str, str]]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        fields: dict[str, str] = {}
        for line in text[match.end() : end].splitlines():
            stripped = line.strip()
            if not stripped.startswith("- ") or ":" not in stripped:
                continue
            key, value = stripped[2:].split(":", 1)
            normalized = key.strip().lower().replace(" ", "_")
            if normalized in fields:
                raise ValueError(f"{match.group(1)} duplicates field {normalized}")
            fields[normalized] = value.strip()
        blocks.append((match.group(1), match.group(2).strip(), fields))
    return blocks


def split_csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def check_acyclic(dependencies: dict[str, tuple[str, ...]]) -> list[str]:
    errors: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            errors.append(f"dependency cycle includes {task_id}")
            return
        if task_id in visited:
            return
        visiting.add(task_id)
        for dependency in dependencies.get(task_id, ()):
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in dependencies:
        visit(task_id)
    return errors


def validate() -> dict[str, Any]:
    generator = load_generator()
    errors: list[str] = []
    warnings: list[str] = []
    plan = generator.PLAN_PATH.read_text(encoding="utf-8")
    objectives = generator.OBJECTIVES_PATH.read_text(encoding="utf-8")
    board_text = generator.BOARD_PATH.read_text(encoding="utf-8")
    config = json.loads(
        generator.CONFIG_PATH.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )

    tasks = task_blocks(board_text)
    task_ids = tuple(item[0] for item in tasks)
    if task_ids != generator.INITIAL_IDS:
        errors.append("initial task IDs/order differ from the sealed 70-task projection")
    if len(task_ids) != 70 or len(set(task_ids)) != 70:
        errors.append("initial task population must be exactly 70 unique tasks")
    expected_titles = generator.PACKAGES
    for task_id, title, fields in tasks:
        if expected_titles.get(task_id) != title:
            errors.append(f"{task_id} title differs from blueprint")
        required = {
            "status",
            "is_schedulable",
            "owning_repository",
            "owned_paths",
            "objective",
            "depends_on",
            "risk_classification",
            "execution_mode",
            "allowed_effects",
            "prohibited_effects",
            "acceptance_criteria",
            "required_tests",
            "required_evidence",
            "rollback_procedure",
            "goal_id",
            "outputs",
            "validation",
            "board_namespace",
            "predicted_files",
            "allowed_paths",
            "acceptance",
        }
        missing = sorted(required - set(fields))
        if missing:
            errors.append(f"{task_id} missing fields: {', '.join(missing)}")
        if fields.get("status") != "todo" or fields.get("is_schedulable") != "true":
            errors.append(f"{task_id} is not an admitted todo")
        if fields.get("execution_mode") != "execute_with_confirmations":
            errors.append(f"{task_id} execution mode is not sealed")
        if fields.get("board_namespace") != generator.NAMESPACE:
            errors.append(f"{task_id} namespace differs")
        if fields.get("goal_id") != generator.goal_for(task_id):
            errors.append(f"{task_id} goal mapping differs")
        expected_owner, expected_source_scope, expected_receipt = generator.scope_for(
            task_id
        )
        expected_scoped_paths = f"{expected_source_scope}, {expected_receipt}"
        if fields.get("owning_repository") != expected_owner:
            errors.append(
                f"{task_id} owning repository is not the sealed Portal root authority"
            )
        if fields.get("owning_repository") in {
            "cross-repository",
            "endomorphosis/ipfs_accelerate_py",
            "endomorphosis/ipfs_datasets_py",
            "endomorphosis/ipfs_kit_py",
        }:
            errors.append(f"{task_id} uses a non-Portal repository authority token")
        for field in ("owned_paths", "predicted_files", "allowed_paths"):
            if fields.get(field) != expected_scoped_paths:
                errors.append(f"{task_id} {field} differs from its outer-root scope")
        if fields.get("outputs") != expected_receipt:
            errors.append(f"{task_id} output is not its outer campaign receipt")
        if fields.get("validation") != generator.validation_for(task_id):
            errors.append(f"{task_id} validation differs from its outer-root command")
        if not expected_receipt.startswith(
            "artifacts/proof_carrying_semantic_minification/receipts/"
        ):
            errors.append(f"{task_id} receipt escaped the outer campaign receipt root")
        if task_id not in {"PCSM-000", "PCSM-001", "PCSM-002", "PCSM-003", "PCSM-004"}:
            if not any(
                expected_source_scope == f"{root}/"
                or expected_source_scope.startswith(f"{root}/")
                for root in generator.WORKTREE_SUBMODULE_PATHS
            ):
                errors.append(f"{task_id} source scope is outside configured worktrees")

    dependencies = {
        task_id: split_csv(fields.get("depends_on", ""))
        for task_id, _title, fields in tasks
    }
    for task_id, values in dependencies.items():
        unknown = sorted(set(values) - set(task_ids))
        if unknown:
            errors.append(f"{task_id} has non-materialized initial dependencies: {unknown}")
    errors.extend(check_acyclic(dependencies))
    ready = [task_id for task_id in task_ids if not dependencies[task_id]]
    expected_ready = ["PCSM-000", "PCSM-001", "PCSM-002", "PCSM-003"]
    if ready != expected_ready:
        errors.append(f"initial readiness frontier differs: {ready}")

    task_fields = {task_id: fields for task_id, _title, fields in tasks}
    pcsm_080 = task_fields.get("PCSM-080", {})
    for phrase in (
        "closed owner-side PlanDelta admission path",
        "Markdown-only objective findings remain non-authoritative",
        "projection_only_task_count=0",
        "reseals the exact execution-route policy",
        "initial 70 remain the only executable population",
    ):
        if phrase not in " ".join(
            (pcsm_080.get("objective", ""), pcsm_080.get("acceptance", ""))
        ):
            errors.append(f"PCSM-080 is missing refill admission gate: {phrase}")

    goals = [item[0] for item in GOAL_RE.findall(objectives)]
    if goals != ["PCSM-G000", *(item[0] for item in generator.GOALS)]:
        errors.append("objective goal order/population differs")
    if len(goals) != 11 or len(set(goals)) != 11:
        errors.append("objective heap must have root plus ten unique subgoals")

    plan_ids = re.findall(r"^\| (PCSM-\d{3}) \|", plan, re.MULTILINE)
    if tuple(plan_ids) != tuple(generator.PACKAGES):
        errors.append("plan work-package ledger differs from all 96 blueprint IDs")
    for phrase in (
        "Python only for v1",
        "M3 `LEARNED_SEMANTIC_COMPRESSION`",
        "experimental_advisory_only",
        "PCSM-119",
        "Absolute population ceiling: 130",
        "Replan ceiling: 20",
        "40%",
        "DuckDB/`DatabaseTaskSource@1`",
        "Quack",
        "DuckLake",
        "canonical semantic CID",
        "typed PatchPlan",
        "deterministic linking",
        "selected-test false negatives",
        "current `TypedDatabaseTaskSource` cannot admit an objective refill",
        "projection_only_task_count=0",
        "initial 70 tasks are therefore the only executable population",
    ):
        if phrase not in plan:
            errors.append(f"plan is missing required invariant: {phrase}")

    expected_paths = {
        "taskboard_path": generator.BOARD_PATH.relative_to(ROOT).as_posix(),
        "objectives_path": generator.OBJECTIVES_PATH.relative_to(ROOT).as_posix(),
        "plan_path": generator.PLAN_PATH.relative_to(ROOT).as_posix(),
        "validator_path": "scripts/validate_proof_carrying_semantic_minification_board.py",
        "task_prefix": "PCSM-",
        "board_namespace": generator.NAMESPACE,
        "merge_target_branch": "agent/proof-carrying-semantic-minification-v1",
    }
    for field, expected in expected_paths.items():
        if config.get(field) != expected:
            errors.append(f"config {field} differs")
    if config.get("max_task_attempts") != 2:
        errors.append(
            "max_task_attempts must retain one bounded retry after the initial attempt"
        )
    if config.get("implementation_retry_budget") != 1:
        errors.append("implementation_retry_budget differs")
    if config.get("validation_retry_budget") != 2:
        errors.append("validation_retry_budget differs")
    submission = config.get("objective_submission") or {}
    if submission.get("campaign_count") != 1 or submission.get("submission_event") != "successful DuckDB materialization receipt":
        errors.append("objective submission must bind exactly one campaign to materialization")
    projection = config.get("initial_projection") or {}
    expected_projection = {
        "task_count": 70,
        "completed_task_ids": [],
        "ready_task_ids": expected_ready,
        "blocked_task_ids": [],
        "terminal_task_id": "PCSM-119",
        "goal_count": 11,
        "root_goal_id": "PCSM-G000",
    }
    for field, expected in expected_projection.items():
        if projection.get(field) != expected:
            errors.append(f"initial_projection.{field} differs")
    dependency_count = sum(len(values) for values in dependencies.values())
    if projection.get("task_dependency_count") != dependency_count:
        errors.append("initial dependency count differs")
    groups = config.get("task_groups") or {}
    grouped = [task_id for values in groups.values() for task_id in values]
    if Counter(grouped) != Counter(task_ids):
        errors.append("task_groups do not partition the initial task population")
    if config.get("worktree_submodule_paths") != list(
        generator.WORKTREE_SUBMODULE_PATHS
    ):
        errors.append("configured worktree submodule paths differ from board scope roots")

    if config.get("exit_when_all_tracks_terminal") is not False:
        errors.append("refill board must not exit at initial-drain terminal state")
    if config.get("objective_refill_enabled") is not True:
        errors.append("objective refill must be enabled")
    if config.get("codebase_refill_enabled") is not False:
        errors.append("unscoped codebase refill must be disabled")
    refill = config.get("refill_policy") or {}
    expected_tranches = [list(items) for items in generator.REFILL_TRANCHES]
    if refill.get("named_refill_tranches") != expected_tranches:
        errors.append("named refill tranches differ")
    derived = refill.get("derived_refill") or {}
    for field, expected in {
        "max_tasks_per_epoch": 10,
        "max_epochs": 20,
        "max_total_tasks": 130,
        "mutate_seed_board": False,
    }.items():
        if derived.get(field) != expected:
            errors.append(f"refill_policy.derived_refill.{field} differs")
    flattened_refills = [item for tranche in expected_tranches for item in tranche]
    if flattened_refills != list(generator.PACKAGES)[70:]:
        errors.append("refill tranches do not cover exactly the deferred 26 packages")
    budget = config.get("budget_policy") or {}
    for field, expected in {
        "max_initial_tasks": 70,
        "max_total_tasks": 130,
        "max_replan_epochs": 20,
        "max_automatically_generated_tasks_per_refill": 10,
        "max_frontier_model_calls": 130,
        "validation_token_and_compute_reserve_percent": 40,
    }.items():
        if budget.get(field) != expected:
            errors.append(f"budget_policy.{field} differs")

    program = config.get("database_program") or {}
    if program.get("authority_mode") != "quack" or program.get("task_source_kind") != "duckdb":
        errors.append("DuckDB + Quack authority program differs")
    if program.get("failover_policy") != "fail_closed":
        errors.append("control-plane failover must fail closed")
    ducklake = config.get("ducklake_projection_program") or {}
    if ducklake.get("authority") is not False or ducklake.get("scheduling_prerequisite") is not False:
        errors.append("DuckLake must remain non-authoritative and nonblocking")
    authority = config.get("authority_policy") or {}
    if authority.get("m3_status") != "experimental_advisory_only":
        errors.append("M3 status differs")

    binding = config.get("source_binding") or {}
    source_specs = (
        ("ipfs_accelerate", "external/ipfs_accelerate"),
        ("ipfs_datasets", "external/ipfs_datasets"),
        ("ipfs_kit", "external/ipfs_kit"),
        ("mcp_plus_plus", "Mcp-Plus-Plus"),
    )
    outer_head = git("rev-parse", "HEAD")
    outer_main = git("rev-parse", "origin/main")
    if subprocess.run(["git", "merge-base", "--is-ancestor", outer_main, outer_head], cwd=ROOT).returncode != 0:
        errors.append("outer branch does not descend from current outer origin/main")
    for prefix, relative in source_specs:
        repo = ROOT / relative
        planned = str(binding.get(f"{prefix}_planning_revision") or "")
        planned_tree = str(binding.get(f"{prefix}_planning_tree") or "")
        origin_main = str(binding.get(f"{prefix}_origin_main_revision") or "")
        if git("rev-parse", "HEAD", cwd=repo) != planned:
            errors.append(f"{prefix} nested HEAD differs from planning seal")
        if git("rev-parse", "HEAD^{tree}", cwd=repo) != planned_tree:
            errors.append(f"{prefix} nested tree differs from planning seal")
        if git("status", "--porcelain=v1", "--untracked-files=all", cwd=repo):
            errors.append(f"{prefix} nested worktree is dirty")
        row = git("ls-tree", outer_head, "--", relative).split()
        if len(row) < 3 or row[0] != "160000" or row[2] != planned:
            errors.append(f"{prefix} outer gitlink differs from planning seal")
        if origin_main:
            fetched_origin_main = git("rev-parse", "origin/main", cwd=repo)
            if origin_main != fetched_origin_main:
                errors.append(
                    f"{prefix} sealed origin/main differs from fetched origin/main"
                )
            ancestry = subprocess.run(
                ["git", "merge-base", "--is-ancestor", origin_main, planned],
                cwd=repo,
                capture_output=True,
            )
            if ancestry.returncode != 0:
                errors.append(f"{prefix} planning revision does not contain sealed origin/main")

    try:
        accelerator = ROOT / "external/ipfs_accelerate"
        if str(accelerator) not in sys.path:
            sys.path.insert(0, str(accelerator))
        from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
            load_configured_board,
        )

        loaded = load_configured_board(generator.CONFIG_PATH, repo_root=ROOT)
        if loaded.board_namespace != generator.NAMESPACE:
            errors.append("generic configured-board loader returned wrong namespace")
    except Exception as exc:
        errors.append(f"generic configured-board loader rejected PCSM: {type(exc).__name__}: {exc}")

    status = "passed" if not errors else "failed"
    return {
        "schema": "pcsm/board-validation@1",
        "status": status,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "task_count": len(tasks),
        "goal_count": len(goals),
        "package_count": len(generator.PACKAGES),
        "initial_ready_task_ids": ready,
        "deferred_task_count": sum(len(items) for items in generator.REFILL_TRANCHES),
        "source_head": git("rev-parse", "HEAD"),
        "source_tree": git("rev-parse", "HEAD^{tree}"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true", help="compatibility alias")
    parser.parse_args()
    try:
        result = validate()
    except Exception as exc:
        result = {
            "schema": "pcsm/board-validation@1",
            "status": "failed",
            "valid": False,
            "errors": [f"{type(exc).__name__}: {exc}"],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
