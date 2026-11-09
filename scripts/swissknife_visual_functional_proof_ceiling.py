"""Record successor subgoals for a parked SwissKnife visual-functional frontier.

This adapter reads the board, the lane park records, and the latest review
majors. It asks the proof-ceiling planner for a proposal and writes that
proposal beside the lane state. It also appends missing child goals.

It does not change task status, drop a dependency, renew a clock, or grant
completion authority. A language model is not called from this path.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from ipfs_accelerate_py.agent_supervisor.planning.proof_ceiling_planner import (
    BlockedObservation,
    FrontierPlan,
    plan_blocked_frontier,
)


_COMPLETED = frozenset({"completed", "complete", "done"})
_READY = frozenset({"ready", "pending", "in_progress"})


def _records(text: str, prefix: str) -> dict[str, dict[str, str]]:
    records: dict[str, dict[str, str]] = {}
    current: dict[str, str] | None = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = None
            if not line.startswith(prefix):
                continue
            identity = line[3:].split(None, 1)[0]
            current = {}
            records[identity] = current
        elif current is not None and line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            current[key.strip().lower()] = value.strip()
    return records


def _ids(raw: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _latest_review(task_dir: Path) -> Path | None:
    root = task_dir / "verification"
    if not root.is_dir():
        return None
    newest: Path | None = None
    newest_mtime = -1
    for attempt in root.iterdir():
        review = attempt / "visual-review.json"
        if not review.is_file():
            continue
        try:
            mtime = review.stat().st_mtime_ns
        except OSError:
            continue
        if mtime >= newest_mtime:
            newest, newest_mtime = review, mtime
    return newest


def _major_text(review_path: Path | None) -> str:
    if review_path is None:
        return ""
    try:
        payload = json.loads(review_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError):
        return ""
    findings = ((payload.get("response") or {}).get("findings") or [])
    lines: list[str] = []
    for item in findings:
        if not isinstance(item, dict) or item.get("severity") not in {"blocker", "major"}:
            continue
        text = " ".join(str(item.get("description") or "").split())
        if text:
            lines.append(text.casefold())
    return "\n".join(lines)


def _owner_flags(text: str) -> dict[str, object]:
    queue = ("queue not used" in text or "queue was unused" in text) and (
        "checkpoint not returned" in text or "no checkpoint" in text
    )
    failed = (
        "owner-failure" in text
        or "no failed-call receipt" in text
        or "joins a receipt only for the later executed" in text
        or "does not observe the rejected" in text
    )
    flags: dict[str, object] = {}
    if queue:
        flags["owner_queue_used"] = False
        flags["owner_checkpoint_present"] = False
    if failed:
        flags["failed_outcome_joined"] = False
        flags["semantic_join"] = "executed_only"
    return flags


def _parent_id(task_id: str) -> str:
    marker = "SVF-FINAL-R"
    if task_id.startswith(marker) and task_id[len(marker):].isdigit():
        return "SVF-" + task_id[len(marker):]
    return ""


def collect_observations(root: Path, profile: dict) -> tuple[BlockedObservation, ...]:
    """Read the current frontier. Missing files yield an empty observation set."""

    root = Path(root)
    todo = root / str(profile.get("todoPath") or "")
    runtime = root / str(profile.get("runtimeRoot") or "")
    if not todo.is_file():
        return ()
    tasks = _records(todo.read_text(encoding="utf-8"), "## SVF-")
    attempts_path = runtime / "state" / "lane_resume_attempts.json"
    fixed: dict = {}
    if attempts_path.is_file():
        try:
            loaded = json.loads(attempts_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            loaded = {}
        if isinstance(loaded, dict) and isinstance(loaded.get("_validation_fixed_points"), dict):
            fixed = loaded["_validation_fixed_points"]
    observations: list[BlockedObservation] = []
    blocked_ids: set[str] = set()
    for task_id, fields in tasks.items():
        status = fields.get("status", "").lower()
        if status == "blocked":
            blocked_ids.add(task_id)
    for task_id, fields in tasks.items():
        status = fields.get("status", "").lower()
        goal_id = fields.get("goal id") or fields.get("goal_id") or ""
        if not goal_id:
            continue
        park = {}
        slot = fixed.get(task_id)
        if isinstance(slot, dict) and isinstance(slot.get("terminal_refusal_park"), dict):
            park = slot["terminal_refusal_park"]
        reason = str(park.get("reason") or "")
        parent = _parent_id(task_id)
        majors = ""
        if status == "blocked" and not parent:
            majors = _major_text(_latest_review(runtime / "tasks" / task_id))
        unmet = tuple(
            item for item in _ids(fields.get("depends on", ""))
            if tasks.get(item, {}).get("status", "").lower() not in _COMPLETED
        )
        flags = _owner_flags(majors)
        if status not in {"blocked", *_READY}:
            continue
        if status in _READY and not all(item in blocked_ids for item in unmet):
            continue
        if status == "blocked" and not reason and not flags:
            continue
        observations.append(BlockedObservation(
            task_id=task_id,
            goal_id=goal_id,
            status=status,
            park_reason=reason,
            parent_task_id=parent,
            parent_status=tasks.get(parent, {}).get("status", "").lower() if parent else "",
            unmet_dependencies=unmet if status in _READY else (),
            owner_queue_used=flags.get("owner_queue_used"),  # type: ignore[arg-type]
            owner_checkpoint_present=flags.get("owner_checkpoint_present"),  # type: ignore[arg-type]
            failed_outcome_joined=flags.get("failed_outcome_joined"),  # type: ignore[arg-type]
            semantic_join=str(flags.get("semantic_join") or ""),
        ))
    return tuple(observations)


def _heading_id(task_id: str, kind: str) -> str:
    suffix = {
        "owner_lacks_declared_queue": "C",
        "failed_outcome_not_semantic": "F",
        "exhausted_child_clock": "X",
        "dependency_blocked": "W",
        "bounded_refinement": "L",
    }[kind]
    if task_id.startswith("SVF-FINAL-R") and task_id[11:].isdigit():
        return f"SVF-GR{task_id[11:]}-{suffix}"
    digits = "".join(character for character in task_id if character.isdigit())
    if not digits:
        raise ValueError(f"task id has no goal digits: {task_id}")
    return f"SVF-G{digits}-{suffix}"


def _goal_section(heading: str, parent: str, title: str, acceptance: tuple[str, ...]) -> str:
    joined = " ".join(acceptance)
    return (
        f"\n## {heading} {title}\n\n"
        f"- Status: active\n"
        f"- Parent: {parent}\n"
        f"- Priority: P1\n"
        f"- Track: visual-functional\n"
        f"- Bundle: swissknife/visual-functional/{heading}\n"
        f"- Goal: {title}\n"
        f"- Evidence: \n"
        f"- Outputs: data/agent_supervisor/swissknife_visual_functional/state/proof-ceiling-plan.json\n"
        f"- Acceptance: {joined} The parent task is not completed by this goal.\n"
    )


def _atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=".proof-ceiling-")
    try:
        os.write(descriptor, payload)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.chmod(temporary, 0o644)
        os.replace(temporary, path)
        temporary = ""
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        if temporary:
            try:
                os.unlink(temporary)
            except OSError:
                pass


def render_goal_append(objectives_text: str, plan: FrontierPlan) -> str:
    """Return objectives text with one new active child per admitted subgoal."""

    existing = set()
    for line in objectives_text.splitlines():
        if line.startswith("## "):
            existing.add(line[3:].split(None, 1)[0])
    sections: list[str] = []
    for subgoal in plan.subgoals:
        if subgoal.source != "deterministic":
            continue
        heading = _heading_id(subgoal.blocked_task_id, subgoal.ceiling_kind)
        if heading in existing:
            continue
        parent = subgoal.parent_goal_id
        if parent not in existing and not parent.startswith("ceiling-"):
            continue
        sections.append(_goal_section(heading, parent, subgoal.title, subgoal.acceptance))
        existing.add(heading)
    if not sections:
        return objectives_text
    base = objectives_text if objectives_text.endswith("\n") else objectives_text + "\n"
    return base + "".join(sections)


def record_proof_ceiling_plan(root: Path, profile: dict) -> dict:
    """Write the plan when it changes. Return whether a new proposal was stored."""

    root = Path(root)
    observations = collect_observations(root, profile)
    plan = plan_blocked_frontier(observations)
    runtime = root / str(profile.get("runtimeRoot") or "")
    plan_path = runtime / "state" / "proof-ceiling-plan.json"
    previous = ""
    if plan_path.is_file():
        try:
            previous = str(json.loads(plan_path.read_text(encoding="utf-8")).get("content_id") or "")
        except (OSError, ValueError):
            previous = ""
    wrote_plan = previous != plan.content_id
    if wrote_plan:
        _atomic_bytes(plan_path, (json.dumps(plan.to_dict(), indent=2) + "\n").encode())
    objectives = root / str(profile.get("objectivePath") or "")
    wrote_goals = False
    if objectives.is_file():
        current = objectives.read_text(encoding="utf-8")
        updated = render_goal_append(current, plan)
        if updated != current:
            _atomic_bytes(objectives, updated.encode())
            wrote_goals = True
    return {
        "admitted": wrote_plan or wrote_goals,
        "task_ids": [item.blocked_task_id for item in plan.subgoals],
        "subgoal_count": len(plan.subgoals),
        "content_id": plan.content_id,
        "work_complete": False,
        "completion_authority": False,
    }


def _successor_task_id(task_id: str) -> str:
    if task_id.startswith("SVF-FINAL-R") and task_id[11:].isdigit():
        return "SVF-STR" + task_id[11:]
    if task_id.startswith("SVF-") and task_id[4:].isdigit():
        return "SVF-ST" + task_id[4:]
    return ""


def propose_successor_tasks(root: Path, profile: dict) -> list[dict]:
    """Blocked tasks for an idle frontier. They do not become selectable."""

    root = Path(root)
    observations = collect_observations(root, profile)
    plan = plan_blocked_frontier(observations)
    objectives = root / str(profile.get("objectivePath") or "")
    headings: set[str] = set()
    if objectives.is_file():
        for line in objectives.read_text(encoding="utf-8").splitlines():
            if line.startswith("## "):
                headings.add(line[3:].split(None, 1)[0])
    predicted = "data/agent_supervisor/swissknife_visual_functional/state/proof-ceiling-plan.json"
    proposals: list[dict] = []
    for subgoal in plan.subgoals:
        if subgoal.source != "deterministic":
            continue
        goal_id = _heading_id(subgoal.blocked_task_id, subgoal.ceiling_kind)
        task_id = _successor_task_id(subgoal.blocked_task_id)
        if not task_id or goal_id not in headings:
            continue
        acceptance = " ".join(subgoal.acceptance)
        proposals.append({
            "task_id": task_id,
            "title": subgoal.successor_task_title or subgoal.title,
            "status": "blocked",
            "depends_on": [subgoal.blocked_task_id],
            "goal_id": goal_id,
            "command": f"python3 scripts/swissknife_visual_functional_worker.py --task-id {task_id}",
            "validation": f"python3 scripts/swissknife_visual_functional_worker.py --validate --task-id {task_id}",
            "predicted_files": predicted,
            "acceptance": acceptance + " The parent task is not completed by this task.",
        })
    return proposals
