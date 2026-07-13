#!/usr/bin/env python3
"""Build the resumable SwissKnife all-tools supervisor queue from its taskboards.

The parent taskboard deliberately summarizes SVD-082 through SVD-091 in one
section.  Their authoritative task metadata lives in the Profile G taskboard,
so this builder overlays those sections while retaining per-task source and
evidence provenance.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "data/swissknife_virtual_desktop/all_tools_supervisor_queue.json"
PRIMARY_TASKBOARD = (
    "implementation_plan/docs/"
    "37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md"
)
PROFILE_G_TASKBOARD = (
    "implementation_plan/docs/"
    "38-mcpplusplus-risk-consensus-scheduling-p2p-plan-2026-07-12.md"
)
FIRST_TASK = 27
LAST_TASK = 101


@dataclass(frozen=True)
class TaskboardSection:
    task_id: str
    title: str
    path: str
    line: int
    body: str
    metadata: dict[str, str]


def _parse_sections(path: str) -> dict[str, TaskboardSection]:
    source = (REPO_ROOT / path).read_text(encoding="utf-8")
    headings = list(re.finditer(r"^## (SVD-\d{3})\s+(.+?)\s*$", source, re.MULTILINE))
    sections: dict[str, TaskboardSection] = {}
    for index, heading in enumerate(headings):
        body_start = heading.end()
        body_end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        body = source[body_start:body_end]
        metadata: dict[str, str] = {}
        current_key: str | None = None
        for raw_line in body.splitlines():
            item = re.match(r"^- ([A-Za-z][A-Za-z -]+):\s*(.*)$", raw_line)
            if item:
                current_key = item.group(1).strip().lower().replace(" ", "_")
                metadata[current_key] = item.group(2).strip()
            elif current_key and (raw_line.startswith("  ") or raw_line.startswith("    ")):
                metadata[current_key] = f"{metadata[current_key]} {raw_line.strip()}".strip()
            elif raw_line.strip():
                current_key = None
        sections[heading.group(1)] = TaskboardSection(
            task_id=heading.group(1),
            title=heading.group(2).strip(),
            path=path,
            line=source.count("\n", 0, heading.start()) + 1,
            body=body,
            metadata=metadata,
        )
    return sections


def _split_references(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace("`", "").strip().rstrip(".")
    return [part.strip() for part in re.split(r"\s*[,;]\s*", normalized) if part.strip()]


def _split_validation(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace("`", "").strip().rstrip(".")
    return [part.strip() for part in re.split(r"\s*;\s*", normalized) if part.strip()]


def _dependencies(value: str) -> list[str]:
    if not value or value.lower() == "none":
        return []
    return re.findall(r"SVD-\d{3}", value)


def _status(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return {
        "done": "completed",
        "in_progress": "active",
        "running": "active",
        "blocked": "waiting",
    }.get(normalized, normalized)


def _owner(track: str) -> str:
    track = track.lower()
    if "dataset" in track:
        return "ipfs_datasets_py"
    if "storage" in track:
        return "ipfs_kit_py"
    if "accelerator" in track or "supervisor" in track:
        return "ipfs_accelerate_py"
    if "glasses" in track or "device" in track or "orb" in track:
        return "glasses"
    if "mcp" in track or "transport" in track or "specification" in track:
        return "mcp"
    if "app" in track or "desktop" in track or "ui" in track:
        return "apps"
    if "release" in track or "performance" in track or "ops" in track:
        return "platform"
    if "crypto" in track or "zkp" in track:
        return "zkp"
    return track.split(",", 1)[0].strip() or "platform"


def _anchor(task_id: str, title: str) -> str:
    slug = re.sub(r"[^a-z0-9 -]", "", f"{task_id} {title}".lower())
    return re.sub(r"[ -]+", "-", slug).strip("-")


def build_queue(previous: dict[str, Any] | None = None) -> dict[str, Any]:
    primary = _parse_sections(PRIMARY_TASKBOARD)
    profile_g = _parse_sections(PROFILE_G_TASKBOARD)
    sections = dict(primary)
    for task_number in range(82, 92):
        task_id = f"SVD-{task_number:03d}"
        sections[task_id] = profile_g[task_id]

    previous_tasks = (previous or {}).get("tasks", {})
    tasks: dict[str, Any] = {}
    for task_number in range(FIRST_TASK, LAST_TASK + 1):
        task_id = f"SVD-{task_number:03d}"
        section = sections.get(task_id)
        if section is None:
            raise ValueError(f"Missing authoritative taskboard section for {task_id}")
        metadata = section.metadata
        outputs = _split_references(metadata.get("outputs", ""))
        validation = _split_validation(metadata.get("validation", ""))
        if not validation and metadata.get("acceptance"):
            validation = [f"Acceptance evidence: {metadata['acceptance']}"]
        if not outputs or not validation:
            raise ValueError(f"{task_id} must declare outputs and validation")

        old = previous_tasks.get(task_id, {})
        evidence = old.get("evidence")
        if not evidence and _status(metadata.get("status", "waiting")) == "completed":
            evidence = {
                "declaration": "taskboard_completed",
                "declared_outputs": outputs,
            }
        task = {
            "title": section.title,
            "status": _status(metadata.get("status", "waiting")),
            "priority": metadata.get("priority", "P0"),
            "track": metadata.get("track", "unspecified"),
            "owner": old.get("owner") or _owner(metadata.get("track", "")),
            "depends_on": _dependencies(metadata.get("depends_on", "")),
            "outputs": outputs,
            "validation": validation,
            "evidence": evidence or {},
            "provenance": {
                "taskboard_path": section.path,
                "taskboard_line": section.line,
                "taskboard_heading": f"## {task_id} {section.title}",
                "taskboard_anchor": f"#{_anchor(task_id, section.title)}",
                "status_field": metadata.get("status", "waiting"),
                "evidence_outputs": outputs,
            },
        }
        tasks[task_id] = task

    # Dispatch readiness is derived from dependency state.  The declared label
    # remains in provenance so a stale "waiting" or premature "ready" label is
    # observable without making the resumable queue replay it.
    completed = {task_id for task_id, task in tasks.items() if task["status"] == "completed"}
    for task_id, task in tasks.items():
        if task["status"] in {"completed", "active", "failed", "stale"}:
            continue
        task["status"] = (
            "ready"
            if all(dependency in completed or int(dependency.removeprefix("SVD-")) < FIRST_TASK
                   for dependency in task["depends_on"])
            else "waiting"
        )

    dependency_graph: dict[str, list[str]] = {task_id: [] for task_id in tasks}
    for task_id, task in tasks.items():
        for dependency in task["depends_on"]:
            if dependency in dependency_graph:
                dependency_graph[dependency].append(task_id)

    states = ("completed", "ready", "waiting", "active", "failed", "stale")
    ids_by_state = {
        state: [task_id for task_id, task in tasks.items() if task["status"] == state]
        for state in states
    }
    summary: dict[str, Any] = {"task_count": len(tasks)}
    for state in states:
        summary[f"{state}_count"] = len(ids_by_state[state])
        summary[f"{state}_task_ids"] = ids_by_state[state]
    summary["blocked_count"] = 0
    summary["blocked_task_ids"] = []
    summary["recommended_task_id"] = "SVD-092"

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    return {
        "schema": "swissknife.all_tools_supervisor_queue.v1",
        "generated_at": generated_at,
        "taskboard_path": PRIMARY_TASKBOARD,
        "taskboard_paths": [PRIMARY_TASKBOARD, PROFILE_G_TASKBOARD],
        "supervisor": {
            "id": "ipfs_accelerate_py.agent_supervisor.swissknife_all_tools",
            "task_id_range": [f"SVD-{FIRST_TASK:03d}", f"SVD-{LAST_TASK:03d}"],
            "parser_contract": "markdown_headers_with_key_value_metadata",
            "resume_state_artifact": "data/swissknife_virtual_desktop/all_tools_supervisor_queue.json",
        },
        "summary": summary,
        "generated_evidence_root": "swissknife/test-results/virtual-desktop-ipfs-mcp-orb",
        "generated_evidence_globs": [
            "swissknife/test-results/virtual-desktop-ipfs-mcp-orb/*.json",
            "swissknife/test-results/virtual-desktop-ipfs-mcp-orb/*.md",
            "swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-screenshots/**",
            "swissknife/test-results/virtual-desktop-ipfs-mcp-orb/glasses-screenshots/**",
        ],
        "source_output_roots": [
            "swissknife/scripts",
            "swissknife/src/services",
            "swissknife/test",
            "swissknife/docs",
            "implementation_plan/docs",
            "data/swissknife_virtual_desktop",
        ],
        "resume_contract": {
            "completed_when": "status is completed, validation exits 0, and expected evidence artifacts exist",
            "ready_when": "all dependencies are completed or are completed baseline tasks from SVD-000 through SVD-026",
            "waiting_when": "the taskboard records waiting or an incomplete dependency prevents dispatch",
            "active_when": "a fresh supervisor observation names the task as running",
            "failed_when": "a fresh supervisor observation records a terminal non-zero attempt",
            "stale_when": "an observation exceeds its freshness window and must not replace taskboard state",
            "blocked_when": "required live MCP endpoint, ORB/IDL generator, release gate, or Meta glasses simulator validation path is unavailable",
            "evidence_churn_rule": "generated evidence artifacts are state checkpoints and must not be treated as source implementation churn",
            "accelerate_boundary_rule": "downstream release gates must respect SVD-031 if the compatibility endpoint remains bounded",
        },
        "provenance": {
            "status_authority": "taskboard metadata",
            "dependency_authority": "per-task Depends on fields",
            "evidence_authority": "per-task Outputs plus preserved evidence records",
            "profile_g_override_range": ["SVD-082", "SVD-091"],
            "profile_g_taskboard_path": PROFILE_G_TASKBOARD,
        },
        "tasks": tasks,
        "dependency_graph": dependency_graph,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true", help="Fail if the committed queue differs")
    args = parser.parse_args()
    previous = json.loads(args.output.read_text(encoding="utf-8")) if args.output.exists() else None
    queue = build_queue(previous)
    serialized = json.dumps(queue, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        # generated_at is intentionally informational and does not make --check nondeterministic.
        if current:
            current_queue = json.loads(current)
            queue["generated_at"] = current_queue.get("generated_at", queue["generated_at"])
            serialized = json.dumps(queue, indent=2, ensure_ascii=False) + "\n"
        if current != serialized:
            raise SystemExit(f"Queue is out of date: run {Path(__file__).relative_to(REPO_ROOT)}")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")


if __name__ == "__main__":
    main()
