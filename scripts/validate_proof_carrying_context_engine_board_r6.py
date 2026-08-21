#!/usr/bin/env python3
"""Validate the PCCE r6 DuckDB drain board without rewriting r5 control files.

The r5 validator remains frozen and still binds the historical 0837254e
accelerator pin plus pending_external_launch_receipt. This r6 validator is the
configured-board preflight target: it proves the Markdown DAG, r6 scheduler
document, and admitted Epic A receipts are present so DuckDB can become
task authority. It never mutates protected r2-r5 receipts or the r5 scheduler.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import deque
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))

from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import (  # noqa: E402
    ConfiguredBoardError,
    load_configured_board,
)
from ipfs_accelerate_py.agent_supervisor.task_sources.todo_vector_index import (  # noqa: E402
    parse_todo_blocks,
)


CONFIG_PATH = REPO_ROOT / "config/proof_carrying_context_engine_v0_1_supervisor_r6.json"
TODO_PATH = REPO_ROOT / "docs/architecture/proof_carrying_context_engine_v0_1.todo.md"
OBJECTIVE_PATH = REPO_ROOT / "docs/architecture/proof_carrying_context_engine_v0_1.objectives.md"
RECEIPT_DIR = REPO_ROOT / "artifacts/proof_carrying_context_engine/receipts"
EXPECTED_TASK_IDS = (
    ["PCCE-000"]
    + [f"PCCE-{value:03d}" for value in range(1, 20)]
    + [f"PCCE-{value:03d}" for value in range(20, 26)]
    + [f"PCCE-{value:03d}" for value in range(30, 36)]
    + [f"PCCE-{value:03d}" for value in range(40, 46)]
    + [f"PCCE-{value:03d}" for value in range(50, 58)]
    + [f"PCCE-{value:03d}" for value in range(60, 69)]
    + [f"PCCE-{value:03d}" for value in range(70, 77)]
    + ["PCCE-079"]
    + [f"PCCE-{value:03d}" for value in range(80, 84)]
)
EXPECTED_GOAL_IDS = ["PCCE-G000"] + [f"PCCE-G{value}" for value in range(100, 900, 100)]
COMPLETED_TASK_IDS = [f"PCCE-{value:03d}" for value in range(20)]
READY_TASK_IDS = ["PCCE-020", "PCCE-022", "PCCE-023"]
BOOTSTRAP_RECEIPT_FILES = {
    "PCCE-000": "PCCE-000-r5.json",
    **{f"PCCE-{value:03d}": f"PCCE-{value:03d}.json" for value in range(1, 20)},
}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in str(value or "").split(",") if item.strip()]


def _topological_order(task_ids: list[str], dependencies: dict[str, list[str]]) -> list[str]:
    remaining = {task_id: list(dependencies.get(task_id, [])) for task_id in task_ids}
    ready = deque([task_id for task_id, deps in remaining.items() if not deps])
    ordered: list[str] = []
    while ready:
        current = ready.popleft()
        ordered.append(current)
        for task_id, deps in remaining.items():
            if current in deps:
                deps.remove(current)
                if not deps and task_id not in ordered and task_id not in ready:
                    ready.append(task_id)
    return ordered


def _goal_ids(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        if line.startswith("## PCCE-G") and " " in line:
            found.append(line[3:].split(" ", 1)[0])
    return found


def validate() -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        board = load_configured_board(CONFIG_PATH, repo_root=REPO_ROOT)
    except ConfiguredBoardError as exc:
        return {
            "valid": False,
            "schema": "proof-carrying-context-engine/r6-board-validation@1",
            "errors": [str(exc)],
            "warnings": warnings,
        }

    payload = dict(board.payload)
    program = board.resolved_database_program()
    if program.authority_mode != "quack" or program.task_source_kind != "duckdb":
        errors.append("r6 scheduler must select DuckDB authority served through Quack")
    if program.failover_policy != "fail_closed":
        errors.append("r6 Quack authority must fail closed")
    if program.explicit_legacy:
        errors.append("r6 must not select explicit legacy Markdown authority")
    if payload.get("merge_target_branch") != "agent/proof-carrying-context-engine-v0.1":
        errors.append("r6 merge target must remain agent/proof-carrying-context-engine-v0.1")
    if payload.get("recovery", {}).get("reuse_scheduler_r5_state") is True:
        errors.append("r6 must not reuse scheduler-r5 state")

    todo_text = TODO_PATH.read_text(encoding="utf-8")
    parsed = parse_todo_blocks(todo_text, task_header_prefix="## PCCE-")
    task_ids = [item[0] for item in parsed]
    if task_ids != EXPECTED_TASK_IDS:
        errors.append("todo board task identities differ from the sealed 67-task DAG")
    dependencies: dict[str, list[str]] = {}
    for task_id, _title, _line, fields in parsed:
        dependencies[task_id] = _split_csv(fields.get("depends_on"))
        unknown = [item for item in dependencies[task_id] if item not in EXPECTED_TASK_IDS]
        if unknown:
            errors.append(f"{task_id} has unknown dependencies: {unknown}")
    ordered = _topological_order(list(EXPECTED_TASK_IDS), dependencies)
    if len(ordered) != len(EXPECTED_TASK_IDS):
        errors.append("task dependency graph contains a cycle")
    if ordered and ordered[-1] != "PCCE-083":
        errors.append("PCCE-083 must be the unique terminal task")
    dependency_count = sum(len(items) for items in dependencies.values())
    if dependency_count != 121:
        errors.append(f"task dependency count is {dependency_count}, expected 121")

    goal_ids = _goal_ids(OBJECTIVE_PATH.read_text(encoding="utf-8"))
    if goal_ids != EXPECTED_GOAL_IDS:
        errors.append("objectives must contain PCCE-G000 and G100-G800 in order")

    receipt_digests: dict[str, str] = {}
    for task_id, relative in BOOTSTRAP_RECEIPT_FILES.items():
        path = RECEIPT_DIR / relative
        if not path.is_file():
            errors.append(f"admitted Epic A receipt missing: {relative}")
            continue
        payload_obj = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload_obj, dict):
            errors.append(f"{relative} is not a JSON object")
            continue
        if payload_obj.get("task_id") != task_id:
            errors.append(f"{relative} task_id mismatch")
        digest = str(payload_obj.get("content_id") or "")
        if not digest.startswith("sha256:"):
            errors.append(f"{relative} is missing a content_id")
        receipt_digests[task_id] = digest

    r5_config = REPO_ROOT / "config/proof_carrying_context_engine_v0_1_supervisor.json"
    r5_validator = REPO_ROOT / "scripts/validate_proof_carrying_context_engine_board.py"
    if not r5_config.is_file() or not r5_validator.is_file():
        errors.append("protected r5 control files are absent")

    projection = payload.get("initial_projection") if isinstance(payload.get("initial_projection"), dict) else {}
    if list(projection.get("completed_task_ids") or []) != COMPLETED_TASK_IDS:
        errors.append("r6 completed_task_ids must be exactly PCCE-000 through PCCE-019")
    if list(projection.get("ready_task_ids") or []) != READY_TASK_IDS:
        errors.append("r6 ready_task_ids must be PCCE-020, PCCE-022, PCCE-023")

    return {
        "valid": not errors,
        "schema": "proof-carrying-context-engine/r6-board-validation@1",
        "board_namespace": board.board_namespace,
        "task_count": len(task_ids),
        "goal_count": len(goal_ids),
        "dependency_count": dependency_count,
        "completed_task_ids": COMPLETED_TASK_IDS,
        "ready_task_ids": READY_TASK_IDS,
        "receipt_content_ids": receipt_digests,
        "markdown_is_authority": False,
        "r5_control_untouched": True,
        "errors": errors,
        "warnings": warnings,
        "todo_sha256": "sha256:" + hashlib.sha256(TODO_PATH.read_bytes()).hexdigest(),
        "r6_config_sha256": "sha256:" + hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-all", action="store_true")
    parser.parse_args()
    result = validate()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
