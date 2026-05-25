#!/usr/bin/env python3
"""Prepare or invoke an LLM merge-conflict resolver for HAO daemon failures."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_EVENTS_PATH = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_events.jsonl"


def iter_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def latest_failed_merge_event(events: list[dict[str, Any]], *, task_id: str | None = None) -> dict[str, Any] | None:
    for event in reversed(events):
        if str(event.get("type") or "") not in {"implementation_finished", "merge_reconciled"}:
            continue
        if task_id and str(event.get("task_id") or "") != task_id:
            continue
        merge_result = event.get("merge_result") or {}
        if not isinstance(merge_result, dict):
            continue
        if not merge_result.get("attempted") or merge_result.get("merged"):
            continue
        if str(merge_result.get("reason") or "") == "not_attempted":
            continue
        return event
    return None


def unmerged_paths(repo_root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return sorted(line.strip() for line in result.stdout.splitlines() if line.strip())


def compact_text(value: Any, *, limit: int = 2000) -> str:
    text = str(value or "")
    if len(text) <= limit:
        return text
    return text[:limit] + "\n...[truncated]"


def build_merge_prompt(*, event: dict[str, Any], repo_root: Path) -> str:
    merge_result = event.get("merge_result") or {}
    if not isinstance(merge_result, dict):
        merge_result = {}
    command = merge_result.get("command") or []
    if isinstance(command, list):
        command_text = shlex.join(str(part) for part in command)
    else:
        command_text = str(command)
    paths = unmerged_paths(repo_root)
    dirty_paths = merge_result.get("dirty_paths") or []
    return "\n".join(
        [
            "Resolve the HAO daemon merge conflict in this repository.",
            "",
            f"Task id: {event.get('task_id')}",
            f"Attempt: {event.get('attempt')}",
            f"Implementation branch: {merge_result.get('branch')}",
            f"Target branch: {merge_result.get('target_branch')}",
            f"Merge reason: {merge_result.get('reason')}",
            f"Merge command: {command_text}",
            f"Repository: {repo_root}",
            f"Unmerged paths: {', '.join(paths) or 'none reported by git'}",
            f"Dirty paths: {', '.join(str(item) for item in dirty_paths) or 'none recorded'}",
            "",
            "Rules:",
            "1. Inspect the conflicted files and the implementation branch before editing.",
            "2. Preserve the semantic intent of both sides when possible.",
            "3. Keep changes scoped to the task and conflict resolution.",
            "4. Run the task validation after resolving the conflict.",
            "5. Commit the merge resolution in the owning repository or submodule.",
            "6. Do not remove the task from blocked_tasks until validation passes.",
            "",
            "Merge stdout excerpt:",
            compact_text(merge_result.get("stdout")),
            "",
            "Merge stderr excerpt:",
            compact_text(merge_result.get("stderr")),
        ]
    )


def resolver_payload(*, events_path: Path, repo_root: Path, task_id: str | None = None) -> dict[str, Any]:
    event = latest_failed_merge_event(iter_jsonl(events_path), task_id=task_id)
    if event is None:
        return {
            "found": False,
            "task_id": task_id,
            "events_path": str(events_path),
            "repo_root": str(repo_root),
            "prompt": "",
        }
    merge_result = event.get("merge_result") or {}
    if not isinstance(merge_result, dict):
        merge_result = {}
    prompt = build_merge_prompt(event=event, repo_root=repo_root)
    return {
        "found": True,
        "task_id": str(event.get("task_id") or ""),
        "attempt": event.get("attempt"),
        "events_path": str(events_path),
        "repo_root": str(repo_root),
        "branch": str(merge_result.get("branch") or ""),
        "target_branch": str(merge_result.get("target_branch") or ""),
        "command": merge_result.get("command") or [],
        "reason": str(merge_result.get("reason") or ""),
        "dirty_paths": merge_result.get("dirty_paths") or [],
        "unmerged_paths": unmerged_paths(repo_root),
        "prompt": prompt,
    }


def invoke_llm_resolver(payload: dict[str, Any]) -> dict[str, Any]:
    command_template = os.environ.get("HANDSFREE_HAO_LLM_MERGE_RESOLVER_COMMAND", "").strip()
    if not command_template:
        return {
            **payload,
            "applied": False,
            "apply_error": "HANDSFREE_HAO_LLM_MERGE_RESOLVER_COMMAND is not set",
        }
    command = shlex.split(command_template)
    result = subprocess.run(
        command,
        cwd=payload.get("repo_root") or None,
        input=str(payload.get("prompt") or ""),
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        **payload,
        "applied": result.returncode == 0,
        "llm_command": command,
        "llm_returncode": result.returncode,
        "llm_stdout": compact_text(result.stdout),
        "llm_stderr": compact_text(result.stderr),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", default=None, help="Resolve the latest merge failure for this HAO task id.")
    parser.add_argument("--events-path", type=Path, default=DEFAULT_EVENTS_PATH)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--apply", action="store_true", help="Invoke the configured LLM resolver command.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = resolver_payload(
        events_path=args.events_path,
        repo_root=args.repo_root,
        task_id=args.task_id,
    )
    if args.apply and payload.get("found"):
        payload = invoke_llm_resolver(payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not payload.get("found"):
        return 1
    if args.apply and not payload.get("applied"):
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
