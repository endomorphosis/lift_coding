#!/usr/bin/env python3
"""Fail-closed validation for the sealed PCPR bootstrap handoff.

The validator is read-only.  It validates the one-task configured-board
bootstrap and the descriptive 66-package campaign, but it never admits work,
opens the authoritative database, or treats board bookkeeping as release
qualification.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
GENERATOR_PATH = (
    ROOT / "scripts/generate_proof_carrying_platform_qualification_and_release_board.py"
)
TASK_HEADER_RE = re.compile(r"^## (PCPR-\d{3}) (.+)$", re.MULTILINE)


def load_generator() -> Any:
    spec = importlib.util.spec_from_file_location("pcpr_board_generator", GENERATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load PCPR bootstrap generator")
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


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def git_result(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def git(*args: str, cwd: Path = ROOT) -> str:
    completed = git_result(*args, cwd=cwd)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(detail or f"git {' '.join(args)} failed")
    return completed.stdout.strip()


def task_blocks(text: str) -> list[tuple[str, str, dict[str, str]]]:
    matches = list(TASK_HEADER_RE.finditer(text))
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


def contains_id_title_line(text: str, task_id: str, title: str) -> bool:
    return any(task_id in line and title in line for line in text.splitlines())


def committed_at_head(relative: str) -> bool:
    return git_result("cat-file", "-e", f"HEAD:{relative}").returncode == 0


def validate_source_forest(
    generator: Any,
    config: Mapping[str, Any],
    errors: list[str],
    warnings: list[str],
) -> tuple[list[dict[str, Any]], bool]:
    binding = config.get("source_binding")
    if not isinstance(binding, Mapping):
        errors.append("config source_binding must be an object")
        return [], False

    outer_head = git("rev-parse", "HEAD")
    outer_tree = git("rev-parse", "HEAD^{tree}")
    outer_origin_main = git("rev-parse", "origin/main")
    branch = git("branch", "--show-current")
    if branch != generator.REQUIRED_BRANCH:
        errors.append(
            f"outer branch differs: expected {generator.REQUIRED_BRANCH}, got {branch}"
        )
    if outer_origin_main != generator.OUTER_REQUIRED_ANCESTOR:
        errors.append("outer origin/main differs from the sealed current-main ancestor")
    if (
        git_result(
            "merge-base",
            "--is-ancestor",
            generator.OUTER_REQUIRED_ANCESTOR,
            outer_head,
        ).returncode
        != 0
    ):
        errors.append("outer HEAD does not descend from the sealed current-main ancestor")

    expected_binding = generator.render_config()["source_binding"]
    if dict(binding) != expected_binding:
        errors.append("config source_binding differs from the exact sealed forest")

    source_report: list[dict[str, Any]] = []
    for prefix, expected in generator.SOURCE_FOREST.items():
        relative = str(expected["path"])
        repo = ROOT / relative
        item: dict[str, Any] = {"repository": prefix, "path": relative}
        if not repo.is_dir():
            errors.append(f"missing nested repository: {relative}")
            item["valid"] = False
            source_report.append(item)
            continue
        try:
            top = git("rev-parse", "--show-toplevel", cwd=repo)
            head = git("rev-parse", "HEAD", cwd=repo)
            tree = git("rev-parse", "HEAD^{tree}", cwd=repo)
            origin_main = git("rev-parse", "origin/main", cwd=repo)
            dirty = git("status", "--porcelain=v1", "--untracked-files=all", cwd=repo)
            gitlink_row = git("ls-tree", outer_head, "--", relative).split()
            gitlink = gitlink_row[2] if len(gitlink_row) >= 3 else ""
        except RuntimeError as exc:
            errors.append(f"cannot inspect {relative}: {exc}")
            item["valid"] = False
            source_report.append(item)
            continue
        exact_top = Path(top).resolve() == repo.resolve()
        ancestry = (
            git_result(
                "merge-base", "--is-ancestor", origin_main, head, cwd=repo
            ).returncode
            == 0
        )
        expected_origin_main = expected.get("origin_main", expected["commit"])
        valid = all(
            (
                exact_top,
                head == expected["commit"],
                tree == expected["tree"],
                origin_main == expected_origin_main,
                ancestry,
                not dirty,
                gitlink == expected["commit"],
            )
        )
        item.update(
            {
                "valid": valid,
                "head": head,
                "tree": tree,
                "origin_main": origin_main,
                "gitlink": gitlink,
                "clean": not bool(dirty),
                "origin_main_is_ancestor": ancestry,
            }
        )
        if not exact_top:
            errors.append(f"{relative} is not an exact nested Git worktree")
        if head != expected["commit"] or tree != expected["tree"]:
            errors.append(f"{relative} HEAD/tree differs from the sealed source forest")
        if origin_main != expected_origin_main or not ancestry:
            errors.append(f"{relative} does not contain the sealed current origin/main")
        if dirty:
            errors.append(f"{relative} nested worktree is dirty")
        if gitlink != expected["commit"]:
            errors.append(f"{relative} outer gitlink differs from the sealed nested HEAD")
        source_report.append(item)

    protected = config.get("protected_paths")
    handoff_paths = set(protected) if isinstance(protected, list) else set()
    handoff_paths.update(
        {
            generator.relative(generator.PLAN_PATH),
            generator.relative(generator.OBJECTIVES_PATH),
            generator.relative(generator.BOARD_PATH),
            generator.relative(generator.CONFIG_PATH),
            generator.relative(generator.GENERATOR_PATH),
            generator.relative(generator.VALIDATOR_PATH),
        }
    )
    missing_commits = sorted(
        path for path in handoff_paths if not committed_at_head(str(path))
    )
    handoff_committed = not missing_commits
    if missing_commits:
        errors.append(
            "handoff control files are not committed at HEAD: "
            + ", ".join(missing_commits)
        )
    outer_dirty = git("status", "--porcelain=v1", "--untracked-files=all")
    if handoff_committed and outer_dirty:
        errors.append("committed PCPR handoff worktree is dirty")
    elif not handoff_committed and outer_dirty:
        warnings.append(
            "outer cleanliness is a final-seal gate after all handoff files are committed"
        )
    source_report.insert(
        0,
        {
            "repository": "portfolio",
            "path": ".",
            "head": outer_head,
            "tree": outer_tree,
            "origin_main": outer_origin_main,
            "branch": branch,
            "clean": not bool(outer_dirty),
            "handoff_committed": handoff_committed,
        },
    )
    return source_report, handoff_committed


def validate() -> dict[str, Any]:
    generator = load_generator()
    errors: list[str] = []
    warnings: list[str] = []

    required_files = (
        generator.PLAN_PATH,
        generator.OBJECTIVES_PATH,
        generator.BOARD_PATH,
        generator.CONFIG_PATH,
        generator.GENERATOR_PATH,
        generator.VALIDATOR_PATH,
        generator.RUNNER_PATH,
    )
    for path in required_files:
        if not path.is_file():
            errors.append(f"missing required handoff file: {path.relative_to(ROOT)}")

    if len(generator.REQUIRED_PACKAGES) != 66:
        errors.append("PCPR blueprint must contain exactly 66 required task IDs")
    if len(set(generator.REQUIRED_PACKAGES)) != 66:
        errors.append("PCPR blueprint contains duplicate task IDs")

    plan = (
        generator.PLAN_PATH.read_text(encoding="utf-8")
        if generator.PLAN_PATH.is_file()
        else ""
    )
    objectives = (
        generator.OBJECTIVES_PATH.read_text(encoding="utf-8")
        if generator.OBJECTIVES_PATH.is_file()
        else ""
    )
    board = (
        generator.BOARD_PATH.read_text(encoding="utf-8")
        if generator.BOARD_PATH.is_file()
        else ""
    )
    config: dict[str, Any] = {}
    if generator.CONFIG_PATH.is_file():
        try:
            config = load_json(generator.CONFIG_PATH)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"scheduler config is invalid: {type(exc).__name__}: {exc}")

    for label, text in (("plan", plan), ("objectives", objectives)):
        for task_id, title in generator.REQUIRED_PACKAGES.items():
            if not contains_id_title_line(text, task_id, title):
                errors.append(f"{label} is missing exact blueprint entry {task_id} {title}")

    campaign_corpus = f"{plan}\n{objectives}"
    for invariant in generator.TRUTH_INVARIANTS:
        if invariant not in campaign_corpus:
            errors.append(f"campaign documents are missing truth invariant: {invariant}")
    for invariant in generator.HARD_ZERO_INVARIANTS:
        if invariant not in campaign_corpus:
            errors.append(f"campaign documents are missing hard-zero invariant: {invariant}")
    for outcome in generator.CLOSED_RELEASE_OUTCOMES:
        if outcome not in campaign_corpus:
            errors.append(f"campaign documents are missing closed outcome: {outcome}")

    if board and board != generator.render_board():
        errors.append("bootstrap board differs from its deterministic generator")
    try:
        tasks = task_blocks(board)
    except ValueError as exc:
        errors.append(str(exc))
        tasks = []
    if [(item[0], item[1]) for item in tasks] != [
        (generator.BOOTSTRAP_TASK_ID, generator.BOOTSTRAP_TASK_TITLE)
    ]:
        errors.append("bootstrap board must contain only exact PCPR-004")
    if tasks:
        fields = tasks[0][2]
        required_task_fields = {
            "stable_task_id",
            "status",
            "completion",
            "is_schedulable",
            "goal_id",
            "owning_repository",
            "owned_paths",
            "objective",
            "depends_on",
            "risk_classification",
            "execution_mode",
            "allowed_effects",
            "prohibited_effects",
            "completion_contract",
            "acceptance_criteria",
            "required_tests",
            "required_evidence",
            "rollback_procedure",
            "outputs",
            "predicted_files",
            "validation",
            "board_namespace",
            "parallel_lane",
            "allowed_paths",
            "acceptance",
        }
        missing = sorted(required_task_fields - set(fields))
        if missing:
            errors.append(f"PCPR-004 missing fields: {', '.join(missing)}")
        expected_values = {
            "stable_task_id": generator.BOOTSTRAP_TASK_ID,
            "completion_contract": "admitted_current_tree_receipt",
            "status": "todo",
            "completion": "auto",
            "is_schedulable": "true",
            "goal_id": generator.BOOTSTRAP_GOAL_ID,
            "depends_on": "",
            "risk_classification": generator.BOOTSTRAP_RISK_CLASSIFICATION,
            "execution_mode": "execute_with_confirmations",
            "board_namespace": generator.NAMESPACE,
            "parallel_lane": generator.BOOTSTRAP_LANE,
        }
        for field, expected in expected_values.items():
            if fields.get(field) != expected:
                errors.append(f"PCPR-004 {field} differs from the sealed bootstrap")
        expected_write_scope = ", ".join(generator.BOOTSTRAP_ALLOWED_PATHS)
        for field in ("owned_paths", "outputs", "predicted_files", "allowed_paths"):
            if fields.get(field) != expected_write_scope:
                errors.append(
                    f"PCPR-004 {field} must equal the complete sealed write scope"
                )

    if config and config != generator.render_config():
        errors.append("scheduler config differs from its deterministic generator")
    if config:
        projection = config.get("initial_projection") or {}
        if projection.get("task_count") != 1 or projection.get("ready_task_ids") != [
            generator.BOOTSTRAP_TASK_ID
        ]:
            errors.append("initial projection must admit exactly ready PCPR-004")
        if (
            projection.get("goal_count") != 37
            or projection.get("root_goal_id") != generator.ROOT_GOAL_ID
        ):
            errors.append("initial projection must materialize all 37 goals under PCPR-G000")
        if config.get("max_lanes") != 1 or len(config.get("lanes") or []) != 1:
            errors.append("PCPR bootstrap must configure exactly one lane")
        if config.get("task_groups") != {
            generator.BOOTSTRAP_GOAL_ID: [generator.BOOTSTRAP_TASK_ID]
        }:
            errors.append("PCPR-004 task group must be PCPR-G110")
        if config.get("exit_when_all_tracks_terminal") is not False:
            errors.append("bootstrap drain must not imply PCPR objective satisfaction")
        for field in (
            "objective_refill_enabled",
            "codebase_refill_enabled",
            "objective_goal_refinement_enabled",
        ):
            if config.get(field) is not False:
                errors.append(f"{field} must remain false before PCPR-004 admission")
        budget = config.get("budget_policy") or {}
        expected_budget = {
            "max_initial_tasks": 80,
            "max_total_tasks": 140,
            "max_replan_epochs": 20,
            "max_automatically_generated_tasks_per_refill": 12,
        }
        for field, expected in expected_budget.items():
            if budget.get(field) != expected:
                errors.append(f"budget_policy.{field} differs")
        reserve = budget.get("validation_token_and_compute_reserve_percent")
        if isinstance(reserve, bool) or not isinstance(reserve, int) or reserve < 30:
            errors.append("validation token/compute reserve must be at least 30 percent")
        frontier_calls = budget.get("max_frontier_model_calls")
        if (
            isinstance(frontier_calls, bool)
            or not isinstance(frontier_calls, int)
            or frontier_calls < 1
            or frontier_calls > 80
        ):
            errors.append("frontier-model calls must have an explicit minimized bound")
        database = config.get("database_program") or {}
        if (
            database.get("authority_mode") != "quack"
            or database.get("task_source_kind") != "duckdb"
            or database.get("quack_endpoint") != "quack:127.0.0.1:47831"
            or database.get("owner_mode") != "exclusive"
            or database.get("failover_policy") != "fail_closed"
            or database.get("explicit_legacy") is not False
        ):
            errors.append("DuckDB/Quack exclusive fail-closed program differs")
        ducklake = config.get("ducklake_projection_program") or {}
        for field in (
            "authority",
            "scheduling_prerequisite",
            "acceptance_prerequisite",
            "completion_prerequisite",
            "release_prerequisite",
            "may_grant_authority",
        ):
            if ducklake.get(field) is not False:
                errors.append(f"DuckLake {field} must remain false")
        gate = ((config.get("refill_policy") or {}).get("activation_gate") or {})
        if gate != generator.render_config()["refill_policy"]["activation_gate"]:
            errors.append("refill activation is not exclusively gated by PCPR-004")
        if config.get("closed_release_outcomes") != list(
            generator.CLOSED_RELEASE_OUTCOMES
        ):
            errors.append("config closed release vocabulary differs")
        if config.get("hard_zero_invariants") != list(generator.HARD_ZERO_INVARIANTS):
            errors.append("config hard-zero invariants differ")

    source_forest: list[dict[str, Any]] = []
    handoff_committed = False
    if config:
        source_forest, handoff_committed = validate_source_forest(
            generator, config, errors, warnings
        )

    try:
        accelerator = ROOT / "external/ipfs_accelerate"
        if str(accelerator) not in sys.path:
            sys.path.insert(0, str(accelerator))
        from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (
            load_configured_board,
        )

        loaded = load_configured_board(generator.CONFIG_PATH, repo_root=ROOT)
        if loaded.board_namespace != generator.NAMESPACE or loaded.max_lanes != 1:
            errors.append("generic configured-board loader returned wrong PCPR identity")
        program = loaded.resolved_database_program()
        if program.authority_mode != "quack" or program.task_source_kind != "duckdb":
            errors.append("generic configured-board loader demoted DuckDB/Quack authority")
    except Exception as exc:
        errors.append(
            "generic configured-board loader rejected PCPR: "
            f"{type(exc).__name__}: {exc}"
        )

    status = "passed" if not errors else "failed"
    return {
        "schema": "pcpr/bootstrap-board-validation@1",
        "status": status,
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "board_namespace": generator.NAMESPACE,
        "bootstrap_task_ids": [item[0] for item in tasks],
        "bootstrap_task_count": len(tasks),
        "required_blueprint_task_count": len(generator.REQUIRED_PACKAGES),
        "max_initial_tasks": 80,
        "max_total_tasks": 140,
        "max_replan_epochs": 20,
        "max_tasks_per_refill": 12,
        "validation_reserve_percent": 30,
        "objective_refill_enabled": False,
        "codebase_refill_enabled": False,
        "handoff_committed": handoff_committed,
        "source_forest": source_forest,
        "release_qualified": False,
        "note": (
            "bootstrap validation is not supervisor promotion or PCPR release qualification"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true")
    arguments = parser.parse_args()
    if not arguments.check_all:
        result = {
            "schema": "pcpr/bootstrap-board-validation@1",
            "status": "failed",
            "valid": False,
            "errors": ["--check-all is required"],
            "warnings": [],
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2
    try:
        result = validate()
    except Exception as exc:
        result = {
            "schema": "pcpr/bootstrap-board-validation@1",
            "status": "failed",
            "valid": False,
            "errors": [f"validator exception: {type(exc).__name__}: {exc}"],
            "warnings": [],
        }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("valid") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
