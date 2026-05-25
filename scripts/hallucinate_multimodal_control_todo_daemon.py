#!/usr/bin/env python3
"""Run the ipfs_datasets_py todo implementation daemon for Hallucinate multimodal-control work."""

from __future__ import annotations

import json
import logging
import ast
import math
import os
import re
import shlex
import subprocess
import sys
import time
from hashlib import sha1
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
DEFAULT_TODO_PATH = REPO_ROOT / "hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md"
DEFAULT_OBJECTIVE_GOAL_HEAP_PATH = Path(
    os.environ.get(
        "HANDSFREE_HAO_OBJECTIVE_GOAL_HEAP_PATH",
        str(REPO_ROOT / "implementation_plan" / "docs" / "23-virtual-ai-os-objective-goal-heap.md"),
    )
)
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "discovery"
OBJECTIVE_BUNDLE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "objective_bundles"
VALIDATION_RETRY_BUDGET = 3
MERGE_RETRY_BUDGET = 3
OBJECTIVE_SCAN_MIN_OPEN_TASKS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_MIN_OPEN_TASKS", "5"))
OBJECTIVE_SCAN_MAX_FINDINGS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_MAX_FINDINGS", "5"))
OBJECTIVE_SCAN_COOLDOWN_SECONDS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_SCAN_COOLDOWN_SECONDS", "21600"))
OBJECTIVE_EMBEDDING_DIMENSIONS = int(os.environ.get("HANDSFREE_HAO_OBJECTIVE_EMBEDDING_DIMENSIONS", "64"))
OBJECTIVE_EMBEDDING_MIN_SCORE = float(os.environ.get("HANDSFREE_HAO_OBJECTIVE_EMBEDDING_MIN_SCORE", "0.62"))
CODEBASE_SCAN_MIN_OPEN_TASKS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_MIN_OPEN_TASKS", "5"))
CODEBASE_SCAN_MAX_FINDINGS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_MAX_FINDINGS", "5"))
CODEBASE_SCAN_COOLDOWN_SECONDS = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_COOLDOWN_SECONDS", "21600"))
CODEBASE_SCAN_MAX_FILE_BYTES = int(os.environ.get("HANDSFREE_HAO_CODEBASE_SCAN_MAX_FILE_BYTES", "262144"))
CODEBASE_SCAN_SUFFIXES = {
    ".cjs",
    ".css",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".py",
    ".rs",
    ".sh",
    ".ts",
    ".tsx",
    ".yaml",
    ".yml",
}
CODEBASE_SCAN_SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "node_modules",
    "playwright-report",
    "test-results",
}
CODEBASE_SCAN_SKIP_PREFIXES = (
    "data/hallucinate_multimodal_control/discovery/",
    "data/hallucinate_multimodal_control/state/",
    "data/hallucinate_multimodal_control/worktrees/",
    "data/meta_glasses_display_widgets/discovery/",
)

logger = logging.getLogger("hallucinate_multimodal_control_todo_daemon")


def hallucinate_multimodal_bootstrap_paths() -> dict[str, Path]:
    todo_path = Path(
        os.environ.get("HANDSFREE_HAO_TODO_PATH", str(DEFAULT_TODO_PATH))
    )
    state_dir = Path(
        os.environ.get("HANDSFREE_HAO_STATE_DIR", str(DEFAULT_STATE_DIR))
    )
    worktree_root = Path(
        os.environ.get("HANDSFREE_HAO_WORKTREE_ROOT", str(DEFAULT_WORKTREE_ROOT))
    )
    objective_goal_heap_path = Path(
        os.environ.get("HANDSFREE_HAO_OBJECTIVE_GOAL_HEAP_PATH", str(DEFAULT_OBJECTIVE_GOAL_HEAP_PATH))
    )
    return {
        "repo_root": REPO_ROOT,
        "todo_path": todo_path,
        "objective_goal_heap_path": objective_goal_heap_path,
        "state_dir": state_dir,
        "worktree_root": worktree_root,
    }


def ensure_hallucinate_multimodal_bootstrap_paths(
    paths: dict[str, Path] | None = None,
) -> dict[str, Path]:
    resolved = paths or hallucinate_multimodal_bootstrap_paths()
    resolved["state_dir"].mkdir(parents=True, exist_ok=True)
    resolved["worktree_root"].mkdir(parents=True, exist_ok=True)
    return resolved


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def _ensure_ipfs_accelerate_path() -> None:
    if str(IPFS_ACCELERATE_ROOT) not in sys.path:
        sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))


def _task_prefix_from_header(task_header_prefix: str) -> str:
    value = str(task_header_prefix or "## HAO-").strip()
    if value.startswith("## "):
        value = value[3:].strip()
    return value or "HAO-"


def _discovery_output_path(repo_root: Path, discovery_dir: Path) -> str:
    try:
        return discovery_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "data/hallucinate_multimodal_control/discovery"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            event = json.loads(raw_line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _consecutive_validation_failures(events: list[dict[str, Any]], task_id: str) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for event in reversed(events):
        if str(event.get("type") or "") != "implementation_finished":
            continue
        if str(event.get("task_id") or "") != task_id:
            continue
        validation = event.get("validation_result") or {}
        if not isinstance(validation, dict) or not validation.get("attempted"):
            break
        if validation.get("passed", False):
            break
        failures.append(event)
    failures.reverse()
    return failures


def _event_merge_result(event: dict[str, Any]) -> dict[str, Any]:
    merge_result = event.get("merge_result") or {}
    return merge_result if isinstance(merge_result, dict) else {}


def _consecutive_merge_failures(events: list[dict[str, Any]], task_id: str) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for event in reversed(events):
        event_type = str(event.get("type") or "")
        if event_type not in {"implementation_finished", "merge_reconciled"}:
            continue
        if str(event.get("task_id") or "") != task_id:
            continue

        merge_result = _event_merge_result(event)
        if event_type == "merge_reconciled" and event.get("resolved", False):
            break
        if event_type == "implementation_finished":
            validation = event.get("validation_result") or {}
            if isinstance(validation, dict) and validation.get("attempted") and not validation.get("passed", False):
                break
            if merge_result.get("merged", False):
                break

        if not merge_result.get("attempted", False):
            continue
        if merge_result.get("merged", False):
            break
        if str(merge_result.get("reason") or "") == "not_attempted":
            continue
        failures.append(event)

    failures.reverse()
    return failures


def _task_ids_from_todo(todo_text: str) -> list[str]:
    task_ids: list[str] = []
    for line in todo_text.splitlines():
        if not line.startswith("## HAO-"):
            continue
        parts = line[3:].strip().split(" ", 1)
        if parts:
            task_ids.append(parts[0])
    return task_ids


def _task_statuses_from_todo(todo_text: str) -> dict[str, str]:
    statuses: dict[str, str] = {}
    current_task_id = ""
    for line in todo_text.splitlines():
        if line.startswith("## HAO-"):
            parts = line[3:].strip().split(" ", 1)
            current_task_id = parts[0] if parts else ""
            continue
        if current_task_id and line.startswith("- Status:"):
            statuses[current_task_id] = line.split(":", 1)[1].strip().lower()
            current_task_id = ""
    return statuses


def _open_task_count(todo_text: str) -> int:
    statuses = _task_statuses_from_todo(todo_text)
    return sum(1 for status in statuses.values() if status not in {"completed", "blocked"})


def _open_task_count_from_state(todo_text: str, state_path: Path | None) -> int | None:
    """Return daemon-resolved open task count when state matches the current todo board."""

    if state_path is None or not state_path.exists():
        return None
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    task_ids = set(_task_ids_from_todo(todo_text))
    statuses = payload.get("task_statuses") or {}
    if not isinstance(statuses, dict):
        return None
    normalized = {str(task_id): str(status).lower() for task_id, status in statuses.items()}
    if set(normalized) != task_ids:
        return None

    try:
        state_task_count = int(payload.get("task_count") or 0)
    except (TypeError, ValueError):
        return None
    if state_task_count != len(task_ids):
        return None

    return sum(1 for status in normalized.values() if status not in {"completed", "blocked"})


def _effective_open_task_count(todo_text: str, state_path: Path | None = None) -> int:
    state_open_count = _open_task_count_from_state(todo_text, state_path)
    if state_open_count is not None:
        return state_open_count
    return _open_task_count(todo_text)


def _next_hao_task_id(todo_text: str) -> str:
    highest = 0
    for task_id in _task_ids_from_todo(todo_text):
        try:
            highest = max(highest, int(task_id.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"HAO-{highest + 1:03d}"


def _parse_iso_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _load_strategy(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"blocked_tasks": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"blocked_tasks": []}
    return payload if isinstance(payload, dict) else {"blocked_tasks": []}


def _save_strategy(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _git_toplevel_for_path(cwd: Path) -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return Path(result.stdout.strip()).resolve()


def _repo_relative_path(repo: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return ""


def _repo_relative_path_safe(relative: str) -> bool:
    if not relative or relative.startswith("/") or "\0" in relative:
        return False
    return ".." not in Path(relative).parts


def _path_status(repo: Path, relative: str) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", relative],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _unmerged_worktree_paths(repo: Path) -> set[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def _commit_specific_generated_path(repo: Path, relative: str, *, subject: str) -> dict[str, Any]:
    if not _repo_relative_path_safe(relative):
        return {"committed": False, "reason": "unsafe_path", "repo": str(repo), "path": relative}
    unmerged = _unmerged_worktree_paths(repo)
    if unmerged and relative not in unmerged:
        return {
            "committed": False,
            "reason": "repo_has_unrelated_unmerged_paths",
            "repo": str(repo),
            "path": relative,
            "unmerged_paths": sorted(unmerged),
        }
    status = _path_status(repo, relative)
    if not status:
        return {"committed": False, "reason": "no_changes", "repo": str(repo), "path": relative}
    add = subprocess.run(
        ["git", "add", "--", relative],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if add.returncode != 0:
        return {
            "committed": False,
            "reason": "git_add_failed",
            "repo": str(repo),
            "path": relative,
            "returncode": add.returncode,
            "stdout": add.stdout[-4000:],
            "stderr": add.stderr[-4000:],
        }
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", relative],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if staged.returncode == 0:
        return {"committed": False, "reason": "no_staged_changes", "repo": str(repo), "path": relative}
    commit = subprocess.run(
        [
            "git",
            "-c",
            "user.name=Hallucinate Todo Daemon",
            "-c",
            "user.email=hallucinate-todo-daemon@example.invalid",
            "commit",
            "-m",
            subject,
            "--",
            relative,
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if commit.returncode != 0:
        return {
            "committed": False,
            "reason": "git_commit_failed",
            "repo": str(repo),
            "path": relative,
            "returncode": commit.returncode,
            "stdout": commit.stdout[-4000:],
            "stderr": commit.stderr[-4000:],
        }
    commit_ref = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    ).stdout.strip()
    return {
        "committed": True,
        "repo": str(repo),
        "path": relative,
        "commit": commit_ref,
        "status": status,
    }


def _parent_git_toplevel_for_repo(repo: Path) -> Path | None:
    parent = _git_toplevel_for_path(repo.resolve().parent)
    if parent is None or parent.resolve() == repo.resolve():
        return None
    try:
        repo.resolve().relative_to(parent.resolve())
    except ValueError:
        return None
    return parent


def _commit_parent_gitlink_updates(child_repo: Path, *, subject: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    current = child_repo.resolve()
    repo_root = REPO_ROOT.resolve()
    while current != repo_root:
        parent = _parent_git_toplevel_for_repo(current)
        if parent is None:
            break
        relative = _repo_relative_path(parent, current)
        if not relative:
            break
        results.append(_commit_specific_generated_path(parent, relative, subject=subject))
        current = parent.resolve()
    return results


def _commit_generated_retry_budget_outputs(paths: list[Path], *, subject: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path in paths:
        repo = _git_toplevel_for_path(path.parent)
        if repo is None:
            results.append({"committed": False, "reason": "not_in_git_repo", "path": str(path)})
            continue
        relative = _repo_relative_path(repo, path)
        if not relative:
            results.append({"committed": False, "reason": "path_outside_repo", "path": str(path), "repo": str(repo)})
            continue
        result = _commit_specific_generated_path(repo, relative, subject=subject)
        if result.get("committed"):
            parent_results = _commit_parent_gitlink_updates(repo, subject=subject)
            if parent_results:
                result["parent_gitlink_commits"] = parent_results
        results.append(result)
    return results


def _write_retry_budget_discovery(
    *,
    discovery_dir: Path,
    follow_up_task_id: str,
    source_task_id: str,
    failed_command: str,
    failures: list[dict[str, Any]],
    retry_budget: int,
) -> Path:
    date = datetime.now(timezone.utc).date().isoformat()
    path = discovery_dir / f"{date}-{follow_up_task_id.lower()}-{source_task_id.lower()}-retry-budget.md"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    log_paths = [str(event.get("log_path") or "") for event in failures if event.get("log_path")]
    attempt_numbers = [str(event.get("attempt") or "") for event in failures if event.get("attempt")]
    content = f"""# {follow_up_task_id} Retry-Budget Finding: {source_task_id}

Date: {date}
Source task: {source_task_id}
Follow-up task: {follow_up_task_id}
Retry budget: {retry_budget}
Observed consecutive validation failures: {len(failures)}

## Evidence

- Failed command: `{failed_command}`
- Attempts: {", ".join(attempt_numbers) or "not recorded"}
- Logs: {", ".join(log_paths) or "not recorded"}

## Guardrail Result

The Hallucinate multimodal-control daemon classified this as backlog work instead of
allowing another implementation attempt to loop on the same validation failure. The
source task is added to the strategy `blocked_tasks` list and the follow-up task below
is appended to the HAO board for normal daemon parsing.
"""
    path.write_text(content, encoding="utf-8")
    return path


def _merge_command_label(merge_result: dict[str, Any]) -> str:
    command = merge_result.get("command")
    if isinstance(command, list) and command:
        return shlex.join(str(part) for part in command)
    if command:
        return str(command)
    reason = str(merge_result.get("reason") or "merge_failed")
    return f"git merge ({reason})"


def _write_merge_retry_budget_discovery(
    *,
    discovery_dir: Path,
    follow_up_task_id: str,
    source_task_id: str,
    merge_result: dict[str, Any],
    failures: list[dict[str, Any]],
    retry_budget: int,
) -> Path:
    date = datetime.now(timezone.utc).date().isoformat()
    path = discovery_dir / f"{date}-{follow_up_task_id.lower()}-{source_task_id.lower()}-merge-retry-budget.md"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    dirty_paths = merge_result.get("dirty_paths") or []
    dirty_paths_text = ", ".join(str(path) for path in dirty_paths) if isinstance(dirty_paths, list) else str(dirty_paths)
    attempts = [str(event.get("attempt") or "") for event in failures if event.get("attempt")]
    content = f"""# {follow_up_task_id} Merge Retry-Budget Finding: {source_task_id}

Date: {date}
Source task: {source_task_id}
Follow-up task: {follow_up_task_id}
Retry budget: {retry_budget}
Observed consecutive merge failures: {len(failures)}

## Evidence

- Merge command: `{_merge_command_label(merge_result)}`
- Merge reason: `{str(merge_result.get("reason") or "not recorded")}`
- Dirty paths: {dirty_paths_text or "not recorded"}
- Attempts: {", ".join(attempts) or "not recorded"}
- Branch: `{str(merge_result.get("branch") or "not recorded")}`
- Main worktree: `{str(merge_result.get("main_worktree_path") or "not recorded")}`

## Guardrail Result

The Hallucinate multimodal-control daemon classified this as backlog work instead
of retrying the same merge reconciliation indefinitely. The source task is added
to the strategy `blocked_tasks` list and the follow-up task below is appended to
the HAO board for normal daemon parsing.
"""
    path.write_text(content, encoding="utf-8")
    return path


def _retry_budget_task_block(
    *,
    follow_up_task_id: str,
    source_task: Any,
    failed_command: str,
    discovery_path: Path,
    depends_on: list[str],
) -> str:
    outputs = list(getattr(source_task, "outputs", []) or [])
    if "data/hallucinate_multimodal_control/discovery" not in outputs:
        outputs.append("data/hallucinate_multimodal_control/discovery")
    return f"""## {follow_up_task_id} Resolve validation retry-budget failure for {source_task.task_id}

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: {", ".join(depends_on)}
- Outputs: {", ".join(outputs)}
- Validation: {failed_command}
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in {source_task.task_id}. Use evidence in {discovery_path} to fix the validation blocker, then remove {source_task.task_id} from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.
"""


def _merge_retry_budget_task_block(
    *,
    follow_up_task_id: str,
    source_task: Any,
    discovery_path: Path,
    strategy_path: Path,
    depends_on: list[str],
) -> str:
    outputs = list(getattr(source_task, "outputs", []) or [])
    if "data/hallucinate_multimodal_control/discovery" not in outputs:
        outputs.append("data/hallucinate_multimodal_control/discovery")
    validation_source = "\n".join(
        [
            "import json, pathlib",
            f"strategy = json.loads(pathlib.Path({str(strategy_path)!r}).read_text(encoding='utf-8'))",
            f"assert {source_task.task_id!r} not in strategy.get('blocked_tasks', [])",
        ]
    )
    validation_command = f"python3 -c {shlex.quote(f'exec({validation_source!r})')}"
    return f"""## {follow_up_task_id} Resolve merge retry-budget failure for {source_task.task_id}

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: {", ".join(depends_on)}
- Outputs: {", ".join(outputs)}
- Validation: {validation_command}
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in {source_task.task_id}. Use evidence in {discovery_path} to fix the merge blocker, verify the intended implementation changes are actually committed in their owning repository or submodule, run `python3 scripts/hallucinate_multimodal_control_merge_conflict_resolver.py --task-id {source_task.task_id} --apply` when the conflict is semantic, then remove {source_task.task_id} from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.
"""


def _path_is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _codebase_scan_path_skipped(path: Path, *, repo_root: Path) -> bool:
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        relative = path.as_posix()
    if any(relative == prefix.rstrip("/") or relative.startswith(prefix) for prefix in CODEBASE_SCAN_SKIP_PREFIXES):
        return True
    return any(part in CODEBASE_SCAN_SKIP_PARTS for part in path.parts)


def _discover_git_worktrees(repo_root: Path) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    def add_if_worktree(candidate: Path) -> None:
        top = _git_toplevel_for_path(candidate)
        if top is None:
            return
        resolved = top.resolve()
        if not _path_is_under(resolved, repo_root):
            return
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            roots.append(resolved)

    add_if_worktree(repo_root)
    for current, dirnames, _filenames in os.walk(repo_root):
        current_path = Path(current)
        dirnames[:] = [
            dirname
            for dirname in dirnames
            if dirname not in CODEBASE_SCAN_SKIP_PARTS
            and not _codebase_scan_path_skipped(current_path / dirname, repo_root=repo_root)
        ]
        if current_path != repo_root and (current_path / ".git").exists():
            add_if_worktree(current_path)
            dirnames[:] = []
            continue
    return roots


def _tracked_files(repo: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    files: list[Path] = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative = raw_path.decode("utf-8", errors="surrogateescape")
        if not _repo_relative_path_safe(relative):
            continue
        path = repo / relative
        if path.is_file():
            files.append(path)
    return files


def _root_relative_path(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _file_is_scan_candidate(path: Path, *, repo_root: Path) -> bool:
    if _codebase_scan_path_skipped(path, repo_root=repo_root):
        return False
    if "-codebase-scan-" in path.name or "retry-budget" in path.name:
        return False
    if path.name == "todo.md" or path.name.endswith(".todo.md"):
        return False
    if path.suffix.lower() not in CODEBASE_SCAN_SUFFIXES:
        return False
    try:
        if path.stat().st_size > CODEBASE_SCAN_MAX_FILE_BYTES:
            return False
    except OSError:
        return False
    return True


def _scan_fingerprint(*, kind: str, root_relative_path: str, line_number: int, snippet: str) -> str:
    normalized = " ".join(snippet.strip().split())
    payload = f"{kind}\0{root_relative_path}\0{line_number}\0{normalized}"
    return sha1(payload.encode("utf-8")).hexdigest()


def _scan_track_for_path(path: str) -> str:
    lowered = path.lower()
    if "/test/" in lowered or lowered.startswith("tests/") or "test_" in Path(lowered).name:
        return "quality"
    if "ui" in Path(lowered).parts or "frontend" in Path(lowered).parts:
        return "ui"
    if lowered.endswith((".md", ".rst")):
        return "docs"
    if lowered.endswith((".py", ".rs", ".sh")):
        return "runtime"
    return "ops"


def _scan_validation_for_path(root_relative_path: str) -> str:
    quoted = shlex.quote(root_relative_path)
    suffix = Path(root_relative_path).suffix.lower()
    if suffix == ".py":
        return f"python3 -m py_compile {quoted}"
    if suffix in {".json"}:
        return f"python3 -m json.tool {quoted} >/dev/null"
    if suffix in {".yaml", ".yml"}:
        return f"python3 -c {shlex.quote('import pathlib, sys; p=pathlib.Path(sys.argv[1]); assert p.read_text(encoding=\"utf-8\").strip()')} {quoted}"
    return f"test -f {quoted}"


def _scan_findings_in_file(path: Path, *, repo_root: Path) -> list[dict[str, Any]]:
    root_relative = _root_relative_path(repo_root, path)
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    findings: list[dict[str, Any]] = []
    in_fenced_block = False
    scan_fences = path.suffix.lower() in {".md", ".rst"}
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if scan_fences and (stripped.startswith("```") or stripped.startswith("~~~")):
            in_fenced_block = not in_fenced_block
            continue
        if in_fenced_block:
            continue
        if not stripped:
            continue
        lowered = stripped.lower()
        kind = ""
        priority = "P2"
        summary = ""
        if re.search(r"\b(todo|fixme|hack|xxx)\b", stripped, flags=re.IGNORECASE):
            kind = "annotated_followup"
            priority = "P2" if re.search(r"\b(fixme|hack|xxx)\b", stripped, flags=re.IGNORECASE) else "P3"
            summary = f"Resolve code annotation in {root_relative}:{index}"
        elif re.search(r"\bexcept\s*:\s*$", stripped) or re.search(r"\bexcept\s+Exception\b", stripped):
            window = "\n".join(lines[index : min(len(lines), index + 3)]).lower()
            if "pass" in window or "return none" in window:
                kind = "swallowed_exception"
                priority = "P1"
                summary = f"Review swallowed exception path in {root_relative}:{index}"
        elif "assert false" in lowered or "raise notimplementederror" in lowered:
            kind = "placeholder_runtime_path"
            priority = "P1"
            summary = f"Replace placeholder runtime path in {root_relative}:{index}"
        if not kind:
            continue
        fingerprint = _scan_fingerprint(
            kind=kind,
            root_relative_path=root_relative,
            line_number=index,
            snippet=stripped,
        )
        findings.append(
            {
                "kind": kind,
                "priority": priority,
                "track": _scan_track_for_path(root_relative),
                "root_relative_path": root_relative,
                "line_number": index,
                "snippet": stripped[:240],
                "summary": summary,
                "validation": _scan_validation_for_path(root_relative),
                "fingerprint": fingerprint,
            }
        )
    return findings


def _scan_codebase_findings(
    repo_root: Path,
    *,
    max_findings: int,
    seen_fingerprints: set[str],
    exhaustive: bool = False,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for git_root in _discover_git_worktrees(repo_root):
        for path in _tracked_files(git_root):
            if not _file_is_scan_candidate(path, repo_root=repo_root):
                continue
            for finding in _scan_findings_in_file(path, repo_root=repo_root):
                if finding["fingerprint"] in seen_fingerprints:
                    continue
                if len(findings) < max_findings:
                    findings.append(finding)
                    seen_fingerprints.add(str(finding["fingerprint"]))
                    continue
                if not exhaustive:
                    return findings
    return findings


def _split_objective_terms(value: str) -> list[str]:
    terms: list[str] = []
    for raw in re.split(r"[,;]", value):
        term = " ".join(raw.strip().split())
        if term:
            terms.append(term)
    return terms


def _objective_tokens(value: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9]+", value.lower()) if len(token) > 1]


def _objective_text_embedding(value: str, *, dimensions: int = OBJECTIVE_EMBEDDING_DIMENSIONS) -> list[float]:
    vector = [0.0] * max(1, dimensions)
    for token in _objective_tokens(value):
        digest = sha1(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % len(vector)
        vector[index] += 1.0
    norm = math.sqrt(sum(item * item for item in vector))
    if norm == 0:
        return vector
    return [item / norm for item in vector]


def _objective_cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))


def _objective_symbol_terms(path: Path, text: str) -> set[str]:
    suffix = path.suffix.lower()
    symbols: set[str] = set()
    if suffix == ".py":
        try:
            tree = ast.parse(text)
        except SyntaxError:
            tree = None
        if tree is not None:
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    symbols.add(node.name)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        symbols.add(alias.name)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    symbols.add(node.module)
                    for alias in node.names:
                        symbols.add(f"{node.module}.{alias.name}")
    elif suffix in {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"}:
        for match in re.finditer(
            r"\b(?:class|function|interface|type|const|let|var)\s+([A-Za-z_$][\w$]*)",
            text,
        ):
            symbols.add(match.group(1))
        for match in re.finditer(r"\bexport\s+\{([^}]+)\}", text):
            for raw in match.group(1).split(","):
                symbol = raw.strip().split(" as ", 1)[0].strip()
                if symbol:
                    symbols.add(symbol)
    elif suffix in {".md", ".rst"}:
        for line in text.splitlines():
            stripped = line.strip("#= ")
            if line.startswith("#") and stripped:
                symbols.add(stripped)
    elif suffix == ".json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            payload = None

        def collect_json_keys(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    symbols.add(str(key))
                    collect_json_keys(item)
            elif isinstance(value, list):
                for item in value:
                    collect_json_keys(item)

        collect_json_keys(payload)
    expanded: set[str] = set()
    for symbol in symbols:
        expanded.add(symbol)
        expanded.add(" ".join(_objective_tokens(symbol)))
    return {item.lower() for item in expanded if item.strip()}


def _parse_objective_goal_heap(text: str) -> list[dict[str, Any]]:
    goals: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    header_pattern = re.compile(r"^##\s+(VAIOS-G\d+)\s+(.+?)\s*$")
    for line in text.splitlines():
        header = header_pattern.match(line)
        if header:
            if current is not None:
                goals.append(current)
            current = {
                "goal_id": header.group(1),
                "title": header.group(2).strip(),
                "fields": {},
            }
            continue
        if current is None or not line.startswith("- ") or ":" not in line:
            continue
        key, value = line[2:].split(":", 1)
        normalized_key = re.sub(r"[^a-z0-9]+", "_", key.strip().lower()).strip("_")
        current["fields"][normalized_key] = value.strip()
    if current is not None:
        goals.append(current)
    return goals


def _objective_goal_status(goal: dict[str, Any]) -> str:
    fields = goal.get("fields") or {}
    return str(fields.get("status") or "active").strip().lower()


def _objective_goal_priority(goal: dict[str, Any]) -> tuple[int, str]:
    fields = goal.get("fields") or {}
    try:
        fib_priority = int(str(fields.get("fib_priority") or "999999").strip())
    except ValueError:
        fib_priority = 999999
    return fib_priority, str(goal.get("goal_id") or "")


def _objective_goal_required_evidence(goal: dict[str, Any]) -> list[str]:
    fields = goal.get("fields") or {}
    return _split_objective_terms(str(fields.get("evidence") or fields.get("required_evidence") or ""))


def _objective_goal_parent_ids(goal: dict[str, Any]) -> list[str]:
    fields = goal.get("fields") or {}
    parents = _split_objective_terms(str(fields.get("parents") or fields.get("parent") or ""))
    return [parent for parent in parents if parent]


def _objective_goal_bundle_key(goal: dict[str, Any], missing_terms: list[str]) -> str:
    fields = goal.get("fields") or {}
    explicit = str(fields.get("bundle") or "").strip()
    if explicit:
        return explicit.strip("/ ")
    track = str(fields.get("track") or "ops").strip().lower() or "ops"
    roots = _split_objective_terms(str(fields.get("outputs") or ""))
    root = "general"
    for candidate in roots:
        first = candidate.split("/", 1)[0].strip()
        if first and first not in {"data", "tests"}:
            root = first
            break
    fingerprint = sha1("|".join([str(goal.get("goal_id") or ""), *missing_terms]).encode("utf-8")).hexdigest()[:8]
    return f"objective/{track}/{root}/{fingerprint}"


def _safe_bundle_key(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip("/ ").lower()).strip("-")
    return safe or "objective-general"


def _objective_goal_graph(goals: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = {str(goal.get("goal_id") or ""): goal for goal in goals if str(goal.get("goal_id") or "")}
    edges: list[dict[str, str]] = []
    children: dict[str, list[str]] = {goal_id: [] for goal_id in nodes}
    roots: list[str] = []
    for goal_id, goal in nodes.items():
        parents = [parent for parent in _objective_goal_parent_ids(goal) if parent]
        if not parents:
            roots.append(goal_id)
        for parent in parents:
            edges.append({"from": parent, "to": goal_id, "kind": "refines"})
            children.setdefault(parent, []).append(goal_id)
    depths: dict[str, int] = {}

    def depth_for(goal_id: str, seen: set[str] | None = None) -> int:
        if goal_id in depths:
            return depths[goal_id]
        seen = set(seen or set())
        if goal_id in seen:
            depths[goal_id] = 0
            return 0
        seen.add(goal_id)
        parents = _objective_goal_parent_ids(nodes.get(goal_id, {}))
        if not parents:
            depths[goal_id] = 0
            return 0
        known_parents = [parent for parent in parents if parent in nodes]
        if not known_parents:
            depths[goal_id] = 1
            return 1
        depths[goal_id] = 1 + max(depth_for(parent, seen) for parent in known_parents)
        return depths[goal_id]

    for goal_id in nodes:
        depth_for(goal_id)
    return {
        "nodes": sorted(nodes),
        "edges": edges,
        "children": {key: sorted(value) for key, value in children.items() if value},
        "roots": sorted(roots),
        "depths": depths,
    }


def _objective_evidence_methods(present_evidence: dict[str, Any]) -> list[str]:
    methods: set[str] = set()
    for paths in present_evidence.values():
        values = paths if isinstance(paths, list) else [paths]
        for value in values:
            match = re.search(r"\((path|exact|ast|embedding)(?::[^)]*)?\)\s*$", str(value))
            if match:
                methods.add(match.group(1))
    return sorted(methods)


def _objective_bundle_path(bundle_dir: Path, bundle_key: str) -> Path:
    return bundle_dir / f"{_safe_bundle_key(bundle_key)}.todo.md"


def _objective_bundle_dir(repo_root: Path, bundle_dir: Path | None) -> Path:
    if bundle_dir is not None:
        return bundle_dir
    return repo_root / "data" / "hallucinate_multimodal_control" / "objective_bundles"


def _objective_goal_fingerprint(goal: dict[str, Any], missing_terms: list[str]) -> str:
    payload = "\0".join(
        [
            "objective_goal_gap",
            str(goal.get("goal_id") or ""),
            str(goal.get("title") or ""),
            *[" ".join(term.lower().split()) for term in missing_terms],
        ]
    )
    return sha1(payload.encode("utf-8")).hexdigest()


def _objective_evidence_path_skipped(path: Path, *, repo_root: Path) -> bool:
    root_relative = _root_relative_path(repo_root, path)
    parts = set(Path(root_relative).parts)
    if "-objective-gap-" in path.name or path.name == "index.json":
        return True
    if {"discovery", "objective_bundles"} & parts:
        return True
    if root_relative.startswith("data/hallucinate_multimodal_control/"):
        return True
    return False


def _objective_candidate_files(repo_root: Path, *, objective_path: Path) -> list[Path]:
    objective_resolved = objective_path.resolve()
    files: list[Path] = []
    for git_root in _discover_git_worktrees(repo_root):
        for path in _tracked_files(git_root):
            if path.resolve() == objective_resolved:
                continue
            if _objective_evidence_path_skipped(path, repo_root=repo_root):
                continue
            if not _file_is_scan_candidate(path, repo_root=repo_root):
                continue
            files.append(path)
    return files


def _objective_evidence_index(
    repo_root: Path,
    *,
    objective_path: Path,
    terms: list[str],
) -> dict[str, list[str]]:
    normalized_terms = [term for term in dict.fromkeys(terms) if term.strip()]
    evidence = {term: [] for term in normalized_terms}
    if not normalized_terms:
        return evidence
    term_tokens = {term: set(_objective_tokens(term)) for term in normalized_terms}
    term_embeddings = {term: _objective_text_embedding(term) for term in normalized_terms}
    for term in normalized_terms:
        if not _repo_relative_path_safe(term):
            continue
        candidate = repo_root / term
        if candidate.exists():
            evidence[term].append(f"{Path(term).as_posix()} (path)")
    lowered_terms = {term: term.lower() for term in normalized_terms}
    for path in _objective_candidate_files(repo_root, objective_path=objective_path):
        root_relative = _root_relative_path(repo_root, path)
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        symbols = _objective_symbol_terms(path, text)
        symbol_text = " ".join(sorted(symbols))
        document_embedding = _objective_text_embedding(f"{root_relative}\n{symbol_text}\n{text[:12000]}")
        document_tokens = set(_objective_tokens(f"{root_relative}\n{symbol_text}\n{text[:12000]}"))
        haystack = f"{root_relative}\n{text}".lower()
        for term, lowered in lowered_terms.items():
            if len(evidence[term]) >= 3:
                continue
            if lowered in haystack:
                evidence[term].append(f"{root_relative} (exact)")
                continue
            normalized_symbol = " ".join(_objective_tokens(term))
            if normalized_symbol and (
                normalized_symbol in symbols
                or any(normalized_symbol in symbol or symbol in normalized_symbol for symbol in symbols)
            ):
                evidence[term].append(f"{root_relative} (ast)")
                continue
            overlap = term_tokens[term] & document_tokens
            required_overlap = max(1, min(2, len(term_tokens[term])))
            embedding_score = _objective_cosine(term_embeddings[term], document_embedding)
            overlap_ratio = len(overlap) / max(1, len(term_tokens[term]))
            embedding_threshold = OBJECTIVE_EMBEDDING_MIN_SCORE
            if overlap_ratio >= 0.75:
                embedding_threshold = min(embedding_threshold, 0.30)
            if len(overlap) >= required_overlap and embedding_score >= embedding_threshold:
                evidence[term].append(f"{root_relative} (embedding:{embedding_score:.2f})")
    return evidence


def _scan_objective_goal_findings(
    repo_root: Path,
    *,
    objective_path: Path,
    max_findings: int,
    seen_fingerprints: set[str],
) -> list[dict[str, Any]]:
    if max_findings <= 0 or not objective_path.exists():
        return []
    goals = [
        goal
        for goal in _parse_objective_goal_heap(objective_path.read_text(encoding="utf-8"))
        if _objective_goal_status(goal) in {"active", "todo", "open"}
    ]
    if not goals:
        return []
    graph = _objective_goal_graph(goals)
    required_terms: list[str] = []
    for goal in goals:
        required_terms.extend(_objective_goal_required_evidence(goal))
    evidence = _objective_evidence_index(repo_root, objective_path=objective_path, terms=required_terms)

    findings: list[dict[str, Any]] = []
    for goal in sorted(goals, key=_objective_goal_priority):
        terms = _objective_goal_required_evidence(goal)
        missing_terms = [term for term in terms if not evidence.get(term)]
        if not missing_terms:
            continue
        fingerprint = _objective_goal_fingerprint(goal, missing_terms)
        if fingerprint in seen_fingerprints:
            continue
        fields = goal.get("fields") or {}
        present_evidence = {term: evidence.get(term, []) for term in terms if evidence.get(term)}
        bundle_key = _objective_goal_bundle_key(goal, missing_terms)
        findings.append(
            {
                "kind": "objective_goal_gap",
                "fingerprint": fingerprint,
                "goal_id": str(goal.get("goal_id") or ""),
                "title": str(goal.get("title") or ""),
                "summary": f"Close virtual AI OS objective gap: {goal.get('title')}",
                "priority": str(fields.get("priority") or "P2"),
                "track": str(fields.get("track") or "ops"),
                "missing_evidence": missing_terms,
                "present_evidence": present_evidence,
                "evidence_methods": _objective_evidence_methods(present_evidence),
                "objective_path": _root_relative_path(repo_root, objective_path),
                "outputs": _split_objective_terms(str(fields.get("outputs") or "")),
                "validation": str(fields.get("validation") or f"test -f {_root_relative_path(repo_root, objective_path)}"),
                "goal": str(fields.get("goal") or ""),
                "refinement": str(fields.get("refinement") or ""),
                "gap_task": str(fields.get("gap_task") or ""),
                "parent_goal_ids": _objective_goal_parent_ids(goal),
                "graph_depth": graph["depths"].get(str(goal.get("goal_id") or ""), 0),
                "bundle_key": bundle_key,
                "parallel_lane": str(fields.get("parallel_lane") or bundle_key),
                "embedding_query": str(fields.get("embedding_query") or fields.get("goal") or goal.get("title") or ""),
                "ast_query": str(fields.get("ast_query") or ", ".join(terms)),
                "conflict_policy": str(
                    fields.get("conflict_policy")
                    or "prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts"
                ),
                "refinement_depth": str(fields.get("refinement_depth") or graph["depths"].get(str(goal.get("goal_id") or ""), 0)),
            }
        )
        seen_fingerprints.add(fingerprint)
        if len(findings) >= max_findings:
            break
    return findings


def _write_objective_goal_discovery(
    *,
    discovery_dir: Path,
    follow_up_task_id: str,
    finding: dict[str, Any],
) -> Path:
    date = datetime.now(timezone.utc).date().isoformat()
    short_fingerprint = str(finding["fingerprint"])[:12]
    path = discovery_dir / f"{date}-{follow_up_task_id.lower()}-objective-gap-{short_fingerprint}.md"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    missing = "\n".join(f"- {term}" for term in finding.get("missing_evidence", [])) or "- none"
    present_items: list[str] = []
    present_evidence = finding.get("present_evidence") or {}
    if isinstance(present_evidence, dict):
        for term, paths in present_evidence.items():
            joined = ", ".join(str(item) for item in paths) if isinstance(paths, list) else str(paths)
            present_items.append(f"- {term}: {joined}")
    present = "\n".join(present_items) if present_items else "- none found for this goal"
    parents = ", ".join(str(item) for item in finding.get("parent_goal_ids", [])) or "none"
    evidence_methods = ", ".join(str(item) for item in finding.get("evidence_methods", [])) or "none"
    content = f"""# {follow_up_task_id} Objective Goal Gap

Date: {date}
Fingerprint: {finding["fingerprint"]}
Kind: {finding["kind"]}
Goal id: {finding["goal_id"]}
Goal title: {finding["title"]}
Objective heap: {finding["objective_path"]}
Priority: {finding["priority"]}
Track: {finding["track"]}
Parent goals: {parents}
Graph depth: {finding.get("graph_depth", 0)}
Bundle: {finding.get("bundle_key", "objective/general")}
Bundle shard: {finding.get("bundle_shard", "not assigned")}
Parallel lane: {finding.get("parallel_lane", finding.get("bundle_key", "objective/general"))}
Evidence methods: {evidence_methods}
Embedding query: {finding.get("embedding_query", "")}
AST query: {finding.get("ast_query", "")}
Conflict policy: {finding.get("conflict_policy", "")}

## Goal

{finding.get("goal") or finding["title"]}

## Missing Evidence

{missing}

## Present Evidence

{present}

## Suggested Handling

{finding.get("gap_task") or "Close the missing evidence with a focused code, test, or documentation change."}

If the gap is too broad for one task, refine `{finding["goal_id"]}` in the objective
heap by adding child goals with concrete evidence terms, then keep the generated
todo task small enough for the supervisor to validate.
"""
    path.write_text(content, encoding="utf-8")
    return path


def _objective_goal_task_block(
    *,
    follow_up_task_id: str,
    finding: dict[str, Any],
    discovery_path: Path,
    depends_on: list[str],
) -> str:
    outputs = ["data/hallucinate_multimodal_control/discovery", finding["objective_path"]]
    outputs.extend(str(item) for item in finding.get("outputs", []) if str(item).strip())
    unique_outputs = list(dict.fromkeys(outputs))
    missing = ", ".join(str(item) for item in finding.get("missing_evidence", []))
    refinement = str(finding.get("refinement") or "Refine the objective heap if the gap needs smaller child goals.")
    parents = ", ".join(str(item) for item in finding.get("parent_goal_ids", [])) or "none"
    bundle_key = str(finding.get("bundle_key") or "objective/general")
    bundle_shard = str(finding.get("bundle_shard") or f"data/hallucinate_multimodal_control/objective_bundles/{_safe_bundle_key(bundle_key)}.todo.md")
    return f"""## {follow_up_task_id} {finding["summary"]}

- Status: todo
- Completion: manual
- Priority: {finding["priority"]}
- Track: {finding["track"]}
- Depends on: {", ".join(depends_on)}
- Outputs: {", ".join(unique_outputs)}
- Validation: {finding["validation"]}
- Bundle: {bundle_key}
- Bundle shard: {bundle_shard}
- Graph parents: {parents}
- Graph depth: {finding.get("graph_depth", 0)}
- Parallel lane: {finding.get("parallel_lane", bundle_key)}
- Conflict policy: {finding.get("conflict_policy", "prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts")}
- Acceptance: Objective scan filed this gap for {finding["goal_id"]}. Use evidence in {discovery_path}, add code/tests/docs or child goals that prove the missing evidence terms are covered ({missing}), and keep the supervisor-fed backlog aligned with the virtual AI OS objective heap. {refinement}
"""


def _write_objective_bundle_shards(
    *,
    bundle_dir: Path,
    repo_root: Path,
    todo_path: Path,
    records: list[dict[str, Any]],
) -> list[Path]:
    if not records:
        return []

    bundle_dir.mkdir(parents=True, exist_ok=True)
    generated_paths: list[Path] = []
    source_todo = _root_relative_path(repo_root, todo_path)
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        finding = record.get("finding") or {}
        bundle_key = str(finding.get("bundle_key") or "objective/general")
        groups.setdefault(bundle_key, []).append(record)

    for bundle_key, bundle_records in sorted(groups.items()):
        shard_path = _objective_bundle_path(bundle_dir, bundle_key)
        if shard_path.exists():
            shard_text = shard_path.read_text(encoding="utf-8")
        else:
            shard_text = (
                f"# Objective Bundle: {bundle_key}\n\n"
                f"Source todo: {source_todo}\n"
                "Purpose: bundle objective-generated tasks so parallel daemons can work one lane at a time.\n"
                "Conflict policy: keep edits inside this bundle when possible; use the LLM merge resolver for semantic conflicts.\n"
            )

        changed = False
        for record in bundle_records:
            task_id = str(record.get("follow_up_task_id") or "")
            if task_id and f"## {task_id} " in shard_text:
                continue
            task_block = str(record.get("task_block") or "").strip()
            if not task_block:
                continue
            shard_text = shard_text.rstrip() + "\n\n" + task_block + "\n"
            changed = True

        if changed or not shard_path.exists():
            shard_path.write_text(shard_text, encoding="utf-8")
            generated_paths.append(shard_path)

    index_path = bundle_dir / "index.json"
    if index_path.exists():
        try:
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            index_payload = {}
    else:
        index_payload = {}
    if not isinstance(index_payload, dict):
        index_payload = {}
    bundles = index_payload.get("bundles")
    if not isinstance(bundles, dict):
        bundles = {}

    for bundle_key, bundle_records in sorted(groups.items()):
        shard_path = _objective_bundle_path(bundle_dir, bundle_key)
        bundle_info = bundles.get(bundle_key)
        if not isinstance(bundle_info, dict):
            bundle_info = {}
        existing_tasks = bundle_info.get("tasks")
        task_map: dict[str, dict[str, Any]] = {}
        if isinstance(existing_tasks, list):
            for item in existing_tasks:
                if isinstance(item, dict) and str(item.get("task_id") or ""):
                    task_map[str(item["task_id"])] = item
        for record in bundle_records:
            finding = record.get("finding") or {}
            task_id = str(record.get("follow_up_task_id") or "")
            if not task_id:
                continue
            task_map[task_id] = {
                "task_id": task_id,
                "goal_id": str(finding.get("goal_id") or ""),
                "graph_depth": finding.get("graph_depth", 0),
                "parent_goal_ids": finding.get("parent_goal_ids", []),
                "missing_evidence": finding.get("missing_evidence", []),
                "discovery_path": str(record.get("discovery_path") or ""),
            }
        bundles[bundle_key] = {
            "bundle_key": bundle_key,
            "shard_path": _root_relative_path(repo_root, shard_path),
            "parallel_lane": str((bundle_records[0].get("finding") or {}).get("parallel_lane") or bundle_key),
            "conflict_policy": str((bundle_records[0].get("finding") or {}).get("conflict_policy") or ""),
            "tasks": [task_map[key] for key in sorted(task_map)],
        }

    index_payload["generated_at"] = _utc_now()
    index_payload["source_todo"] = source_todo
    index_payload["bundles"] = bundles
    index_path.write_text(json.dumps(index_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    generated_paths.append(index_path)
    return generated_paths


def _write_codebase_scan_discovery(*, discovery_dir: Path, follow_up_task_id: str, finding: dict[str, Any]) -> Path:
    date = datetime.now(timezone.utc).date().isoformat()
    short_fingerprint = str(finding["fingerprint"])[:12]
    path = discovery_dir / f"{date}-{follow_up_task_id.lower()}-codebase-scan-{short_fingerprint}.md"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    content = f"""# {follow_up_task_id} Codebase Scan Finding

Date: {date}
Fingerprint: {finding["fingerprint"]}
Kind: {finding["kind"]}
Source: {finding["root_relative_path"]}:{finding["line_number"]}
Priority: {finding["priority"]}
Track: {finding["track"]}

## Evidence

```text
{finding["snippet"]}
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.
"""
    path.write_text(content, encoding="utf-8")
    return path


def _codebase_scan_task_block(
    *,
    follow_up_task_id: str,
    finding: dict[str, Any],
    discovery_path: Path,
    depends_on: list[str],
) -> str:
    outputs = ["data/hallucinate_multimodal_control/discovery", str(finding["root_relative_path"])]
    return f"""## {follow_up_task_id} {finding["summary"]}

- Status: todo
- Completion: manual
- Priority: {finding["priority"]}
- Track: {finding["track"]}
- Depends on: {", ".join(depends_on)}
- Outputs: {", ".join(outputs)}
- Validation: {finding["validation"]}
- Acceptance: Codebase scan filed this finding from {finding["root_relative_path"]}:{finding["line_number"]}. Use evidence in {discovery_path}, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.
"""


def record_objective_goal_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    state_path: Path | None = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_task_state.json",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    objective_path: Path = DEFAULT_OBJECTIVE_GOAL_HEAP_PATH,
    bundle_dir: Path | None = None,
    task_header_prefix: str = "## HAO-",
    repo_root: Path = REPO_ROOT,
    min_open_tasks: int = OBJECTIVE_SCAN_MIN_OPEN_TASKS,
    max_findings: int = OBJECTIVE_SCAN_MAX_FINDINGS,
    cooldown_seconds: int = OBJECTIVE_SCAN_COOLDOWN_SECONDS,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Feed the HAO board from missing evidence in the virtual-AI-OS objective heap."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (
        record_objective_backlog_findings as accelerator_record_objective_backlog_findings,
    )

    task_prefix = _task_prefix_from_header(task_header_prefix)
    todo_text = todo_path.read_text(encoding="utf-8") if todo_path.exists() else ""
    depends_on = ["HAO-013"] if "HAO-013" in _task_ids_from_todo(todo_text) else []
    return accelerator_record_objective_backlog_findings(
        repo_root=repo_root,
        objective_path=objective_path,
        todo_path=todo_path,
        discovery_dir=discovery_dir,
        bundle_dir=_objective_bundle_dir(repo_root, bundle_dir),
        strategy_path=strategy_path,
        state_path=state_path,
        task_prefix=task_prefix,
        depends_on=depends_on,
        min_open_tasks=min_open_tasks,
        max_findings=max_findings,
        cooldown_seconds=cooldown_seconds,
        force=force,
        summary_prefix="Close virtual AI OS objective gap",
        discovery_output_path=_discovery_output_path(repo_root, discovery_dir),
        commit_outputs=True,
        commit_subject="HAO: record objective goal backlog findings",
    )

    if max_findings <= 0 or not todo_path.exists() or not objective_path.exists():
        return []
    todo_text = todo_path.read_text(encoding="utf-8")
    task_ids = set(_task_ids_from_todo(todo_text))
    open_task_count = _effective_open_task_count(todo_text, state_path)
    if not force and open_task_count > min_open_tasks:
        return []

    effective_bundle_dir = _objective_bundle_dir(repo_root, bundle_dir)
    strategy = _load_strategy(strategy_path)
    now = datetime.now(timezone.utc)
    task_count = len(task_ids)
    drained_backlog = open_task_count == 0
    try:
        last_drained_scan_task_count = int(strategy.get("last_drained_objective_goal_scan_task_count") or -1)
    except (TypeError, ValueError):
        last_drained_scan_task_count = -1
    drained_scan_due = drained_backlog and last_drained_scan_task_count != task_count
    last_scan_at = _parse_iso_timestamp(str(strategy.get("last_objective_goal_scan_at") or ""))
    if (
        not force
        and not drained_scan_due
        and last_scan_at is not None
        and (now - last_scan_at).total_seconds() < cooldown_seconds
    ):
        return []

    seen = {
        str(item)
        for item in strategy.get("objective_goal_seen_fingerprints", [])
        if str(item).strip()
    }
    findings = _scan_objective_goal_findings(
        repo_root,
        objective_path=objective_path,
        max_findings=max_findings,
        seen_fingerprints=seen,
    )
    strategy["last_objective_goal_scan_at"] = _utc_now()
    strategy["last_objective_goal_scan_mode"] = "drained_exhaustive" if drained_scan_due else "low_backlog"
    if drained_backlog:
        strategy["last_drained_objective_goal_scan_task_count"] = task_count
    strategy["objective_goal_seen_fingerprints"] = sorted(seen)
    if not findings:
        strategy["last_objective_goal_scan_findings"] = []
        _save_strategy(strategy_path, strategy)
        return []

    generated_paths: list[Path] = []
    appended: list[dict[str, Any]] = []
    bundle_records: list[dict[str, Any]] = []
    depends_on = ["HAO-013"] if "HAO-013" in task_ids else []
    for finding in findings:
        finding = dict(finding)
        follow_up_task_id = _next_hao_task_id(todo_text)
        finding["bundle_shard"] = _root_relative_path(
            repo_root,
            _objective_bundle_path(effective_bundle_dir, str(finding.get("bundle_key") or "objective/general")),
        )
        discovery_path = _write_objective_goal_discovery(
            discovery_dir=discovery_dir,
            follow_up_task_id=follow_up_task_id,
            finding=finding,
        )
        task_block = _objective_goal_task_block(
            follow_up_task_id=follow_up_task_id,
            finding=finding,
            discovery_path=discovery_path,
            depends_on=depends_on,
        )
        todo_text = todo_text.rstrip() + "\n\n" + task_block.strip() + "\n"
        task_ids.add(follow_up_task_id)
        generated_paths.append(discovery_path)
        bundle_records.append(
            {
                "follow_up_task_id": follow_up_task_id,
                "task_block": task_block,
                "finding": finding,
                "discovery_path": discovery_path,
            }
        )
        appended.append(
            {
                "follow_up_task_id": follow_up_task_id,
                "fingerprint": finding["fingerprint"],
                "kind": finding["kind"],
                "goal_id": finding["goal_id"],
                "missing_evidence": finding["missing_evidence"],
                "bundle_key": finding.get("bundle_key"),
                "bundle_shard": finding.get("bundle_shard"),
                "graph_depth": finding.get("graph_depth"),
                "parent_goal_ids": finding.get("parent_goal_ids", []),
                "discovery_path": str(discovery_path),
            }
        )

    todo_path.write_text(todo_text, encoding="utf-8")
    generated_paths.extend(
        _write_objective_bundle_shards(
            bundle_dir=effective_bundle_dir,
            repo_root=repo_root,
            todo_path=todo_path,
            records=bundle_records,
        )
    )
    strategy["last_objective_goal_scan_findings"] = appended
    _save_strategy(strategy_path, strategy)
    generated_paths.insert(0, todo_path)
    commit_results = _commit_generated_retry_budget_outputs(
        generated_paths,
        subject="HAO: record objective goal backlog findings",
    )
    logger.info("Committed objective-goal generated outputs: %s", commit_results)
    return appended


def record_codebase_scan_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    state_path: Path | None = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_task_state.json",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## HAO-",
    repo_root: Path = REPO_ROOT,
    min_open_tasks: int = CODEBASE_SCAN_MIN_OPEN_TASKS,
    max_findings: int = CODEBASE_SCAN_MAX_FINDINGS,
    cooldown_seconds: int = CODEBASE_SCAN_COOLDOWN_SECONDS,
    force: bool = False,
) -> list[dict[str, Any]]:
    """Feed the HAO board with static codebase scan findings when backlog runs low."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (
        record_codebase_scan_findings as accelerator_record_codebase_scan_findings,
    )

    task_prefix = _task_prefix_from_header(task_header_prefix)
    todo_text = todo_path.read_text(encoding="utf-8") if todo_path.exists() else ""
    depends_on = ["HAO-013"] if "HAO-013" in _task_ids_from_todo(todo_text) else []
    return accelerator_record_codebase_scan_findings(
        todo_path=todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        repo_root=repo_root,
        task_prefix=task_prefix,
        depends_on=depends_on,
        min_open_tasks=min_open_tasks,
        max_findings=max_findings,
        cooldown_seconds=cooldown_seconds,
        force=force,
        discovery_output_path=_discovery_output_path(repo_root, discovery_dir),
        skip_prefixes=CODEBASE_SCAN_SKIP_PREFIXES,
        commit_outputs=True,
        commit_subject="HAO: record codebase scan backlog findings",
    )

    if max_findings <= 0 or not todo_path.exists():
        return []
    todo_text = todo_path.read_text(encoding="utf-8")
    task_ids = set(_task_ids_from_todo(todo_text))
    open_task_count = _effective_open_task_count(todo_text, state_path)
    if not force and open_task_count > min_open_tasks:
        return []

    strategy = _load_strategy(strategy_path)
    now = datetime.now(timezone.utc)
    task_count = len(task_ids)
    drained_backlog = open_task_count == 0
    try:
        last_drained_scan_task_count = int(strategy.get("last_drained_codebase_scan_task_count") or -1)
    except (TypeError, ValueError):
        last_drained_scan_task_count = -1
    drained_scan_due = drained_backlog and last_drained_scan_task_count != task_count
    last_scan_at = _parse_iso_timestamp(str(strategy.get("last_codebase_scan_at") or ""))
    if (
        not force
        and not drained_scan_due
        and last_scan_at is not None
        and (now - last_scan_at).total_seconds() < cooldown_seconds
    ):
        return []

    seen = {
        str(item)
        for item in strategy.get("codebase_scan_seen_fingerprints", [])
        if str(item).strip()
    }
    findings = _scan_codebase_findings(
        repo_root,
        max_findings=max_findings,
        seen_fingerprints=seen,
        exhaustive=drained_scan_due,
    )
    strategy["last_codebase_scan_at"] = _utc_now()
    strategy["last_codebase_scan_mode"] = "drained_exhaustive" if drained_scan_due else "low_backlog"
    if drained_backlog:
        strategy["last_drained_codebase_scan_task_count"] = task_count
    strategy["codebase_scan_seen_fingerprints"] = sorted(seen)
    if not findings:
        strategy["last_codebase_scan_findings"] = []
        _save_strategy(strategy_path, strategy)
        return []

    generated_paths: list[Path] = []
    appended: list[dict[str, Any]] = []
    depends_on = ["HAO-013"] if "HAO-013" in task_ids else []
    for finding in findings:
        follow_up_task_id = _next_hao_task_id(todo_text)
        discovery_path = _write_codebase_scan_discovery(
            discovery_dir=discovery_dir,
            follow_up_task_id=follow_up_task_id,
            finding=finding,
        )
        task_block = _codebase_scan_task_block(
            follow_up_task_id=follow_up_task_id,
            finding=finding,
            discovery_path=discovery_path,
            depends_on=depends_on,
        )
        todo_text = todo_text.rstrip() + "\n\n" + task_block.strip() + "\n"
        task_ids.add(follow_up_task_id)
        generated_paths.append(discovery_path)
        appended.append(
            {
                "follow_up_task_id": follow_up_task_id,
                "fingerprint": finding["fingerprint"],
                "kind": finding["kind"],
                "source": f"{finding['root_relative_path']}:{finding['line_number']}",
                "discovery_path": str(discovery_path),
            }
        )

    todo_path.write_text(todo_text, encoding="utf-8")
    strategy["last_codebase_scan_findings"] = appended
    _save_strategy(strategy_path, strategy)
    generated_paths.insert(0, todo_path)
    commit_results = _commit_generated_retry_budget_outputs(
        generated_paths,
        subject="HAO: record codebase scan backlog findings",
    )
    logger.info("Committed codebase-scan generated outputs: %s", commit_results)
    return appended


def record_retry_budget_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    events_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_events.jsonl",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## HAO-",
    retry_budget: int = VALIDATION_RETRY_BUDGET,
    merge_retry_budget: int = MERGE_RETRY_BUDGET,
) -> list[dict[str, Any]]:
    """Turn repeated validation or merge failures into discovery-backed daemon backlog items."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (
        record_retry_budget_findings as accelerator_record_retry_budget_findings,
    )

    task_prefix = _task_prefix_from_header(task_header_prefix)
    todo_text = todo_path.read_text(encoding="utf-8") if todo_path.exists() else ""
    validation_depends_on = ["HAO-013"] if "HAO-013" in _task_ids_from_todo(todo_text) else []
    inferred_repo_root = _git_toplevel_for_path(todo_path.parent) or REPO_ROOT
    findings = accelerator_record_retry_budget_findings(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        task_header_prefix_value=task_header_prefix,
        task_prefix=task_prefix,
        validation_retry_budget=retry_budget,
        merge_retry_budget=merge_retry_budget,
        validation_depends_on=validation_depends_on,
        discovery_output_path=_discovery_output_path(inferred_repo_root, discovery_dir),
        commit_outputs=True,
        repo_root=inferred_repo_root,
        commit_subject="HAO: record retry-budget guardrail outputs",
    )
    for finding in findings:
        if finding.get("failure_kind") == "validation":
            finding.pop("failure_kind", None)
    return findings

    if not todo_path.exists():
        return []

    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import parse_task_file

    tasks = parse_task_file(todo_path, task_header_prefix)
    if not tasks:
        return []

    todo_text = todo_path.read_text(encoding="utf-8")
    task_ids = set(_task_ids_from_todo(todo_text))
    completed_task_ids = {task.task_id for task in tasks if task.status == "completed"}
    events = _iter_jsonl(events_path)
    findings: list[dict[str, Any]] = []
    generated_paths: list[Path] = []
    strategy = _load_strategy(strategy_path)
    blocked_tasks = [str(item) for item in strategy.get("blocked_tasks", []) if str(item).strip()]

    if retry_budget > 0:
        for task in tasks:
            if task.task_id in completed_task_ids:
                continue
            marker = f"retry-budget failure for {task.task_id}"
            if marker in todo_text:
                continue
            failures = _consecutive_validation_failures(events, task.task_id)
            if len(failures) < retry_budget:
                continue
            latest_validation = failures[-1].get("validation_result") or {}
            failed_command = str(latest_validation.get("failed_command") or "")
            if not failed_command:
                continue

            follow_up_task_id = _next_hao_task_id(todo_text)
            discovery_path = _write_retry_budget_discovery(
                discovery_dir=discovery_dir,
                follow_up_task_id=follow_up_task_id,
                source_task_id=task.task_id,
                failed_command=failed_command,
                failures=failures,
                retry_budget=retry_budget,
            )
            generated_paths.append(discovery_path)
            depends_on = ["HAO-013"] if "HAO-013" in task_ids else list(task.depends_on)
            task_block = _retry_budget_task_block(
                follow_up_task_id=follow_up_task_id,
                source_task=task,
                failed_command=failed_command,
                discovery_path=discovery_path,
                depends_on=depends_on,
            )
            todo_text = todo_text.rstrip() + "\n\n" + task_block.strip() + "\n"
            task_ids.add(follow_up_task_id)
            if task.task_id not in blocked_tasks:
                blocked_tasks.append(task.task_id)
            findings.append(
                {
                    "source_task_id": task.task_id,
                    "follow_up_task_id": follow_up_task_id,
                    "failure_count": len(failures),
                    "failed_command": failed_command,
                    "discovery_path": str(discovery_path),
                }
            )

    for task in tasks:
        if merge_retry_budget <= 0:
            break
        if task.task_id in completed_task_ids:
            continue
        marker = f"merge retry-budget failure for {task.task_id}"
        if marker in todo_text:
            continue
        failures = _consecutive_merge_failures(events, task.task_id)
        if len(failures) < merge_retry_budget:
            continue
        latest_merge_result = _event_merge_result(failures[-1])
        if not latest_merge_result:
            continue

        follow_up_task_id = _next_hao_task_id(todo_text)
        discovery_path = _write_merge_retry_budget_discovery(
            discovery_dir=discovery_dir,
            follow_up_task_id=follow_up_task_id,
            source_task_id=task.task_id,
            merge_result=latest_merge_result,
            failures=failures,
            retry_budget=merge_retry_budget,
        )
        generated_paths.append(discovery_path)
        depends_on = list(task.depends_on)
        task_block = _merge_retry_budget_task_block(
            follow_up_task_id=follow_up_task_id,
            source_task=task,
            discovery_path=discovery_path,
            strategy_path=strategy_path,
            depends_on=depends_on,
        )
        todo_text = todo_text.rstrip() + "\n\n" + task_block.strip() + "\n"
        task_ids.add(follow_up_task_id)
        if task.task_id not in blocked_tasks:
            blocked_tasks.append(task.task_id)
        findings.append(
            {
                "source_task_id": task.task_id,
                "follow_up_task_id": follow_up_task_id,
                "failure_count": len(failures),
                "failed_command": _merge_command_label(latest_merge_result),
                "discovery_path": str(discovery_path),
                "failure_kind": "merge",
            }
        )

    if not findings:
        return []

    todo_path.write_text(todo_text, encoding="utf-8")
    strategy["blocked_tasks"] = blocked_tasks
    strategy["last_retry_budget_guardrail_at"] = _utc_now()
    strategy["retry_budget_findings"] = findings
    _save_strategy(strategy_path, strategy)
    generated_paths.insert(0, todo_path)
    commit_results = _commit_generated_retry_budget_outputs(
        generated_paths,
        subject="HAO: record retry-budget guardrail outputs",
    )
    logger.info("Committed retry-budget generated outputs: %s", commit_results)
    return findings


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    paths = ensure_hallucinate_multimodal_bootstrap_paths()
    os.chdir(REPO_ROOT)
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(IPFS_DATASETS_ROOT), existing] if existing else [str(IPFS_DATASETS_ROOT)]
    )

    args = _with_default(args, "--todo-path", str(paths["todo_path"]))
    args = _with_default(args, "--state-dir", str(paths["state_dir"]))
    args = _with_default(args, "--task-prefix", "## HAO-")
    args = _with_default(args, "--state-prefix", "hallucinate_multimodal_control")
    args = _with_default(args, "--worktree-root", str(paths["worktree_root"]))

    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import (
        DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
        PortalImplementationDaemon,
        parse_args,
    )

    parsed = parse_args(args)
    logging.basicConfig(
        level=getattr(logging, parsed.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    state_path = parsed.state_dir / f"{parsed.state_prefix}_task_state.json"
    strategy_path = parsed.state_dir / f"{parsed.state_prefix}_strategy.json"
    events_path = parsed.state_dir / f"{parsed.state_prefix}_events.jsonl"
    daemon = PortalImplementationDaemon(
        todo_path=parsed.todo_path,
        state_path=state_path,
        strategy_path=strategy_path,
        events_path=events_path,
        repo_root=REPO_ROOT,
        task_header_prefix=parsed.task_prefix,
        implement=parsed.implement,
        implementation_command=parsed.implementation_command or None,
        implementation_timeout=parsed.implementation_timeout or DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
        use_ephemeral_worktree=parsed.implement and not parsed.no_ephemeral_worktree,
        worktree_root=parsed.worktree_root,
    )

    while True:
        objective_findings = record_objective_goal_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            objective_path=paths["objective_goal_heap_path"],
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
        )
        if objective_findings:
            logger.warning("Recorded Hallucinate objective-goal findings before daemon pass: %s", objective_findings)
        scan_findings = record_codebase_scan_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
        )
        if scan_findings:
            logger.warning("Recorded Hallucinate codebase-scan findings before daemon pass: %s", scan_findings)
        findings = record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        if findings:
            logger.warning("Recorded Hallucinate retry-budget findings before daemon pass: %s", findings)
        result = daemon.run_once()
        findings = record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        if findings:
            logger.warning("Recorded Hallucinate retry-budget findings after daemon pass: %s", findings)
        objective_findings = record_objective_goal_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            objective_path=paths["objective_goal_heap_path"],
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
        )
        if objective_findings:
            logger.warning("Recorded Hallucinate objective-goal findings after daemon pass: %s", objective_findings)
        scan_findings = record_codebase_scan_findings(
            todo_path=parsed.todo_path,
            state_path=state_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
            repo_root=REPO_ROOT,
        )
        if scan_findings:
            logger.warning("Recorded Hallucinate codebase-scan findings after daemon pass: %s", scan_findings)
        logger.info("Hallucinate multimodal-control daemon pass complete: %s", result)
        if parsed.once:
            break
        time.sleep(parsed.interval)


if __name__ == "__main__":
    main()
