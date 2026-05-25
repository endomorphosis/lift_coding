#!/usr/bin/env python3
"""Run the ipfs_datasets_py todo implementation daemon for Hallucinate multimodal-control work."""

from __future__ import annotations

import json
import logging
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
DEFAULT_TODO_PATH = REPO_ROOT / "hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md"
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "discovery"
VALIDATION_RETRY_BUDGET = 3
MERGE_RETRY_BUDGET = 3
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
    "data/hallucinate_multimodal_control/state/",
    "data/hallucinate_multimodal_control/worktrees/",
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
    return {
        "repo_root": REPO_ROOT,
        "todo_path": todo_path,
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
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in {source_task.task_id}. Use evidence in {discovery_path} to fix the merge blocker, verify the intended implementation changes are actually committed in their owning repository or submodule, then remove {source_task.task_id} from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.
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
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
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


def _scan_codebase_findings(repo_root: Path, *, max_findings: int, seen_fingerprints: set[str]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for git_root in _discover_git_worktrees(repo_root):
        for path in _tracked_files(git_root):
            if not _file_is_scan_candidate(path, repo_root=repo_root):
                continue
            for finding in _scan_findings_in_file(path, repo_root=repo_root):
                if finding["fingerprint"] in seen_fingerprints:
                    continue
                findings.append(finding)
                seen_fingerprints.add(str(finding["fingerprint"]))
                if len(findings) >= max_findings:
                    return findings
    return findings


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


def record_codebase_scan_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
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

    if max_findings <= 0 or not todo_path.exists():
        return []
    todo_text = todo_path.read_text(encoding="utf-8")
    task_ids = set(_task_ids_from_todo(todo_text))
    if not force and _open_task_count(todo_text) > min_open_tasks:
        return []

    strategy = _load_strategy(strategy_path)
    now = datetime.now(timezone.utc)
    last_scan_at = _parse_iso_timestamp(str(strategy.get("last_codebase_scan_at") or ""))
    if not force and last_scan_at is not None and (now - last_scan_at).total_seconds() < cooldown_seconds:
        return []

    seen = {
        str(item)
        for item in strategy.get("codebase_scan_seen_fingerprints", [])
        if str(item).strip()
    }
    findings = _scan_codebase_findings(repo_root, max_findings=max_findings, seen_fingerprints=seen)
    strategy["last_codebase_scan_at"] = _utc_now()
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
        scan_findings = record_codebase_scan_findings(
            todo_path=parsed.todo_path,
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
        scan_findings = record_codebase_scan_findings(
            todo_path=parsed.todo_path,
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
