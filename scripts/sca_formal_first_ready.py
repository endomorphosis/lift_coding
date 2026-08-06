#!/usr/bin/env python3
"""Formal-first readiness checks for the SCA SwissKnife contract-assurance board.

Usage:
  python3 scripts/sca_formal_first_ready.py --expect-phase formal_first_enablement
  python3 scripts/sca_formal_first_ready.py --check-parser-row-deferred
  python3 scripts/sca_formal_first_ready.py --expect-closeout
  python3 scripts/sca_formal_first_ready.py --list-ready-summary
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PROFILE = REPO_ROOT / "config" / "swissknife_symbolic_contract_assurance_supervisor.json"
BOARD = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "44-swissknife-symbolic-contract-assurance.todo.md"
)
PLAN = (
    REPO_ROOT
    / "implementation_plan"
    / "docs"
    / "47-sca-formal-first-improvement-plan-2026-08-06.md"
)
CLOSEOUT = (
    REPO_ROOT
    / "data"
    / "agent_supervisor"
    / "swissknife_contract_assurance"
    / "formal_first_enablement_closeout.json"
)

DEFERRED_TRACKS = frozenset(
    {
        "parser-failure-row-verification",
        "parser-failure-fan-in",
        "parser-failure-cluster-repair",
        "parser-failure-aggregate",
    }
)
GATE = "SCA-ENABLE-CLOSE"


def _load_profile() -> dict:
    return json.loads(PROFILE.read_text(encoding="utf-8"))


def _parse_tasks(text: str) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for match in re.finditer(
        r"^## (SCA-[^\n]+)\n((?:.*\n)*?)(?=^## |\Z)",
        text,
        re.M,
    ):
        body = match.group(2)

        def field(name: str, default: str = "") -> str:
            found = re.search(rf"^- {re.escape(name)}:\s*(.*)$", body, re.M)
            return found.group(1).strip() if found else default

        header = match.group(1).strip()
        task_id = header.split()[0]
        tasks.append(
            {
                "id": task_id,
                "header": header,
                "status": field("Status"),
                "track": field("Track"),
                "priority": field("Priority"),
                "depends": field("Depends on"),
                "selection_phase": field("Selection phase"),
                "selection_band": field("Selection band"),
            }
        )
    return tasks


def _task_completed(tasks: list[dict[str, str]], task_id: str) -> bool:
    for task in tasks:
        if task["id"] == task_id and task["status"] == "completed":
            return True
    return False


def check_phase(expected: str) -> list[str]:
    errors: list[str] = []
    if not PLAN.is_file():
        errors.append(f"missing plan: {PLAN}")
    profile = _load_profile()
    mode = str(profile.get("mode") or "")
    policy = profile.get("selectionPolicy") or {}
    phase = str(policy.get("phase") or "")
    gate = str(policy.get("gateTaskId") or "")
    if mode != expected and mode != "formal_first_enablement":
        # allow formal_first_enablement as the active mode name
        if expected == "formal_first_enablement" and mode != expected:
            errors.append(f"profile.mode={mode!r} want {expected!r}")
    if phase != expected:
        errors.append(f"selectionPolicy.phase={phase!r} want {expected!r}")
    if gate != GATE:
        errors.append(f"selectionPolicy.gateTaskId={gate!r} want {GATE!r}")
    deny = policy.get("denyTracks") or []
    if "parser-failure-row-verification" not in deny:
        errors.append("denyTracks must include parser-failure-row-verification")
    return errors


def check_parser_row_deferred() -> list[str]:
    errors: list[str] = []
    text = BOARD.read_text(encoding="utf-8")
    tasks = _parse_tasks(text)
    openish = {"todo", "active", "blocked", "ready"}
    bad = 0
    for task in tasks:
        if task["track"] not in DEFERRED_TRACKS:
            continue
        if task["status"] not in openish:
            continue
        depends = task["depends"]
        if GATE not in depends:
            bad += 1
            if bad <= 5:
                errors.append(
                    f"{task['id']} track={task['track']} missing depends {GATE}"
                )
        if task["priority"] not in {"P3", "P2"}:
            # allow P2 but prefer P3; flag P0/P1
            if task["priority"] in {"P0", "P1"}:
                bad += 1
                if bad <= 8:
                    errors.append(
                        f"{task['id']} still priority {task['priority']} (want P3)"
                    )
    row_open = sum(
        1
        for task in tasks
        if task["track"] == "parser-failure-row-verification"
        and task["status"] in openish
    )
    if row_open and bad:
        errors.append(
            f"parser-row open={row_open} demotion_issues={bad} "
            f"(showing up to 8 samples above)"
        )
    elif not any(task["track"] == "parser-failure-row-verification" for task in tasks):
        errors.append("no parser-failure-row-verification tasks found on board")
    return errors


def check_closeout() -> list[str]:
    errors: list[str] = []
    text = BOARD.read_text(encoding="utf-8")
    tasks = _parse_tasks(text)
    required = [
        "SCA-ENABLE-000",
        "SCA-ENABLE-001",
        "SCA-ENABLE-DOCTOR",
        "SCA-ENABLE-RPR",
        "SCA-218",
        "SCA-645",
        "SCA-606",
        "SCA-221",
    ]
    for task_id in required:
        status = next((t["status"] for t in tasks if t["id"] == task_id), "missing")
        if status not in {"completed", "blocked"}:
            errors.append(f"{task_id} status={status!r} (need completed or blocked)")
    if not CLOSEOUT.is_file():
        errors.append(f"missing closeout receipt: {CLOSEOUT}")
    else:
        try:
            payload = json.loads(CLOSEOUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"closeout JSON invalid: {exc}")
            payload = {}
        if payload.get("phase_after") not in {"symbolic_repair", "formal_first_enablement"}:
            # require explicit flip intent
            if payload.get("gate_closed") is not True:
                errors.append("closeout must set gate_closed=true")
    return errors


def list_ready_summary() -> int:
    text = BOARD.read_text(encoding="utf-8")
    tasks = _parse_tasks(text)
    completed = {t["id"] for t in tasks if t["status"] == "completed"}
    openish = {"todo", "active", "ready"}
    ready = []
    for task in tasks:
        if task["status"] not in openish:
            continue
        deps = [d.strip() for d in task["depends"].split(",") if d.strip()]
        if all(dep in completed for dep in deps):
            ready.append(task)
    by_track = Counter(t["track"] for t in ready)
    print(f"ready_tasks={len(ready)}")
    for track, count in by_track.most_common(25):
        flag = " DEFERRED" if track in DEFERRED_TRACKS else ""
        print(f"  {count:4d}  {track}{flag}")
    deferred_ready = [t for t in ready if t["track"] in DEFERRED_TRACKS]
    print(f"ready_in_deferred_tracks={len(deferred_ready)}")
    return 0 if not deferred_ready else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expect-phase",
        default="",
        help="Require selectionPolicy.phase / mode formal_first_enablement",
    )
    parser.add_argument(
        "--check-parser-row-deferred",
        action="store_true",
        help="Require open parser-row tasks depend on SCA-ENABLE-CLOSE",
    )
    parser.add_argument(
        "--expect-closeout",
        action="store_true",
        help="Require formal-first closeout checklist",
    )
    parser.add_argument(
        "--list-ready-summary",
        action="store_true",
        help="Print ready-task counts by track",
    )
    args = parser.parse_args(argv)

    if not any(
        [
            args.expect_phase,
            args.check_parser_row_deferred,
            args.expect_closeout,
            args.list_ready_summary,
        ]
    ):
        args.expect_phase = "formal_first_enablement"
        args.check_parser_row_deferred = True

    errors: list[str] = []
    if args.expect_phase:
        errors.extend(check_phase(args.expect_phase))
    if args.check_parser_row_deferred:
        errors.extend(check_parser_row_deferred())
    if args.expect_closeout:
        errors.extend(check_closeout())
    if args.list_ready_summary:
        # still report errors if any other flags set
        code = list_ready_summary()
        if errors:
            for err in errors:
                print(f"ERROR: {err}", file=sys.stderr)
            return 1
        return code

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1
    print("OK formal-first readiness checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
