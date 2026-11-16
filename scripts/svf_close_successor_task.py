#!/usr/bin/env python3
"""Close one blocked successor row after its dependency completed itself.

The command reads the board, the proof-ceiling plan, and, for an exhausted
child, that child's own receipt and payment files. It does not mark the parent
or the child completed, drop a dependency, refund a payment, or renew a clock.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path


ROOT = Path("/home/barberb/lift_coding")
BOARD = ROOT / "implementation_plan/docs/53-swissknife-visual-functional-mcplusplus.todo.md"
PLAN = ROOT / "data/agent_supervisor/swissknife_visual_functional/state/proof-ceiling-plan.json"
RUNTIME = ROOT / "data/agent_supervisor/swissknife_visual_functional/tasks"
SCHEMA = "swissknife.successor-closeout.v1"

ROWS = {
    "SVF-ST1023": {
        "depends_on": "SVF-1023",
        "acceptance": (
            "The declared result names the observed owner fields: completed status, "
            "queue unused, and no checkpoint. A preview completion is labeled as a preview. "
            "The parent visual task stays blocked until a new review passes on those terms. "
            "The parent task is not completed by this task."
        ),
    },
    "SVF-ST1032": {
        "depends_on": "SVF-1032",
        "acceptance": (
            "The failed call stays a request artifact and is not treated as an executed "
            "semantic proof. The later executed observation remains the semantic result. "
            "No sample, receipt, or content id is added by the planner. The parent task "
            "is not completed by this task."
        ),
    },
    "SVF-ST900": {
        "depends_on": "SVF-900",
        "acceptance": (
            "The task stays unselected until every unmet dependency is completed by its "
            "own evidence. No dependency is removed. The parent task is not completed by this task."
        ),
    },
    "SVF-STR1002": {"depends_on": "SVF-FINAL-R1002", "child": True},
    "SVF-STR1013": {"depends_on": "SVF-FINAL-R1013", "child": True},
    "SVF-STR1019": {"depends_on": "SVF-FINAL-R1019", "child": True},
    "SVF-STR1022": {"depends_on": "SVF-FINAL-R1022", "child": True},
    "SVF-STR1032": {
        "depends_on": "SVF-FINAL-R1032",
        "child": True,
        "acceptance": (
            "The child clock is not renewed. The unfinished parent is not treated as satisfied. "
            "This plan does not mark the child completed. The parent task is not completed by this task."
        ),
    },
    "SVF-STR1035": {"depends_on": "SVF-FINAL-R1035", "child": True},
    "SVF-STR1043": {"depends_on": "SVF-FINAL-R1043", "child": True},
}
CHILD_ACCEPTANCE = (
    "The child clock is not renewed. The completed parent receipt remains the parent evidence. "
    "This plan does not mark the child completed. The parent task is not completed by this task."
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _block(text: str, task_id: str) -> str:
    marker = f"## {task_id} "
    start = text.find(marker)
    if start < 0:
        start = text.find(f"## {task_id}\n")
    if start < 0:
        raise SystemExit(f"{task_id} is not on the board")
    end = text.find("\n## ", start + 1)
    return text[start:] if end < 0 else text[start:end]


def _status(text: str, task_id: str) -> str:
    for line in _block(text, task_id).splitlines():
        if line.startswith("- Status:"):
            return line.split(":", 1)[1].strip().lower()
    raise SystemExit(f"{task_id} has no status")


def _receipt_body(task_id: str, row: dict, child: dict | None) -> dict:
    body = {
        "schema": SCHEMA,
        "task_id": task_id,
        "depends_on": row["depends_on"],
        "dependency_completed_by_own_evidence": True,
        "acceptance_retained": True,
        "dependency_line_retained": True,
        "marked_parent_completed": False,
        "marked_child_completed": False,
        "clock_renewed": False,
        "payment_refunded": False,
        "work_complete": False,
        "completion_authority": False,
    }
    if child is not None:
        body["child_result_sha256"] = child["result_sha256"]
        body["child_payment_sha256"] = child["payment_sha256"]
    return body


def _child_evidence(dependency: str) -> dict:
    directory = RUNTIME / dependency
    receipt_path = directory / "receipt.json"
    result_path = directory / "source-only-result.json"
    if not receipt_path.is_file() or not result_path.is_file():
        raise SystemExit(f"{dependency} has no own receipt and parent-review result")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    result = json.loads(result_path.read_text(encoding="utf-8"))
    if (receipt.get("task_id") != dependency or receipt.get("work_complete") is not False
            or receipt.get("completion_authority") is not False):
        raise SystemExit(f"{dependency} receipt is not the child's own unfinished evidence")
    if (result.get("parent_review_satisfied") is not True or result.get("payment_refunded") is not False
            or result.get("clock_renewed") is not False or result.get("work_complete") is not False
            or result.get("completion_authority") is not False):
        raise SystemExit(f"{dependency} parent-review result renewed a clock or refunded a payment")
    payment = result.get("payments") or {}
    relative = payment.get("path") if isinstance(payment, dict) else None
    payment_path = ROOT / relative if isinstance(relative, str) else None
    if (not isinstance(relative, str) or payment_path is None or not payment_path.is_file()
            or _sha(payment_path) != payment.get("sha256")):
        raise SystemExit(f"{dependency} payment file no longer matches the recorded journal")
    for item in result.get("clock_files") or []:
        clock_path = ROOT / str(item.get("path") or "")
        if not clock_path.is_file() or _sha(clock_path) != item.get("sha256"):
            raise SystemExit(f"{dependency} clock file changed")
    return {"result_sha256": _sha(result_path), "payment_sha256": payment["sha256"]}


def evaluate(task_id: str) -> dict:
    row = ROWS.get(task_id)
    if row is None:
        raise SystemExit(f"{task_id} is not a successor closeout")
    text = BOARD.read_text(encoding="utf-8")
    block = _block(text, task_id)
    acceptance = row.get("acceptance") or CHILD_ACCEPTANCE
    if f"- Depends on: {row['depends_on']}" not in block.splitlines():
        raise SystemExit(f"{task_id} dependency line changed")
    if f"- Acceptance: {acceptance}" not in block:
        raise SystemExit(f"{task_id} acceptance line changed")
    if _status(text, row["depends_on"]) != "completed":
        raise SystemExit(f"{row['depends_on']} is not completed by its own evidence")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    if plan.get("work_complete") is not False or plan.get("completion_authority") is not False:
        raise SystemExit("proof-ceiling plan grants completion")
    child = _child_evidence(row["depends_on"]) if row.get("child") else None
    return _receipt_body(task_id, row, child)


def _write(path: Path, body: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    if path.is_file() and path.read_bytes() == raw:
        return
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".successor-closeout-")
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    body = evaluate(args.task_id)
    path = RUNTIME / args.task_id / "successor-receipt.json"
    if args.validate:
        if not path.is_file():
            raise SystemExit(f"{args.task_id} successor receipt is absent")
        recorded = json.loads(path.read_text(encoding="utf-8"))
        if recorded != body:
            raise SystemExit(f"{args.task_id} successor receipt does not match the board")
    else:
        _write(path, body)
    print(json.dumps({"task_id": args.task_id, "validated": True, "artifacts": 1,
                      "work_complete": False, "completion_authority": False}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
