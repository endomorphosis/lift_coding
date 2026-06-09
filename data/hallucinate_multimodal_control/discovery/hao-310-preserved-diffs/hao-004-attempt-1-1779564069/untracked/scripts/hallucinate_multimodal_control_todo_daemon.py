#!/usr/bin/env python3
"""Run the ipfs_datasets_py todo implementation daemon for Hallucinate multimodal-control work."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
DEFAULT_TODO_PATH = (
    REPO_ROOT / "hallucinate_app" / "docs" / "MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.todo.md"
)
DEFAULT_STATE_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "state"
DEFAULT_WORKTREE_ROOT = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "worktrees"
DISCOVERY_DIR = REPO_ROOT / "data" / "hallucinate_multimodal_control" / "discovery"
VALIDATION_RETRY_BUDGET = 3

logger = logging.getLogger("hallucinate_multimodal_control_todo_daemon")


def hallucinate_multimodal_bootstrap_paths() -> dict[str, Path]:
    todo_path = Path(os.environ.get("HANDSFREE_HAO_TODO_PATH", str(DEFAULT_TODO_PATH)))
    state_dir = Path(os.environ.get("HANDSFREE_HAO_STATE_DIR", str(DEFAULT_STATE_DIR)))
    worktree_root = Path(os.environ.get("HANDSFREE_HAO_WORKTREE_ROOT", str(DEFAULT_WORKTREE_ROOT)))
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
    return datetime.now(UTC).isoformat()


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


def _consecutive_validation_failures(
    events: list[dict[str, Any]], task_id: str
) -> list[dict[str, Any]]:
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


def _task_ids_from_todo(todo_text: str) -> list[str]:
    task_ids: list[str] = []
    for line in todo_text.splitlines():
        if not line.startswith("## HAO-"):
            continue
        parts = line[3:].strip().split(" ", 1)
        if parts:
            task_ids.append(parts[0])
    return task_ids


def _next_hao_task_id(todo_text: str) -> str:
    highest = 0
    for task_id in _task_ids_from_todo(todo_text):
        try:
            highest = max(highest, int(task_id.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"HAO-{highest + 1:03d}"


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


def _write_retry_budget_discovery(
    *,
    discovery_dir: Path,
    follow_up_task_id: str,
    source_task_id: str,
    failed_command: str,
    failures: list[dict[str, Any]],
    retry_budget: int,
) -> Path:
    date = datetime.now(UTC).date().isoformat()
    path = (
        discovery_dir
        / f"{date}-{follow_up_task_id.lower()}-{source_task_id.lower()}-retry-budget.md"
    )
    discovery_dir.mkdir(parents=True, exist_ok=True)
    log_paths = [str(event.get("log_path") or "") for event in failures if event.get("log_path")]
    attempt_numbers = [
        str(event.get("attempt") or "") for event in failures if event.get("attempt")
    ]
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


def record_retry_budget_findings(
    *,
    todo_path: Path = DEFAULT_TODO_PATH,
    events_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_events.jsonl",
    strategy_path: Path = DEFAULT_STATE_DIR / "hallucinate_multimodal_control_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## HAO-",
    retry_budget: int = VALIDATION_RETRY_BUDGET,
) -> list[dict[str, Any]]:
    """Turn repeated validation failures into discovery-backed daemon backlog items."""

    if retry_budget <= 0 or not todo_path.exists():
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
    strategy = _load_strategy(strategy_path)
    blocked_tasks = [str(item) for item in strategy.get("blocked_tasks", []) if str(item).strip()]

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

    if not findings:
        return []

    todo_path.write_text(todo_text, encoding="utf-8")
    strategy["blocked_tasks"] = blocked_tasks
    strategy["last_retry_budget_guardrail_at"] = _utc_now()
    strategy["retry_budget_findings"] = findings
    _save_strategy(strategy_path, strategy)
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
        implementation_timeout=parsed.implementation_timeout
        or DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
        use_ephemeral_worktree=parsed.implement and not parsed.no_ephemeral_worktree,
        worktree_root=parsed.worktree_root,
    )

    while True:
        findings = record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        if findings:
            logger.warning(
                "Recorded Hallucinate retry-budget findings before daemon pass: %s", findings
            )
        result = daemon.run_once()
        findings = record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        if findings:
            logger.warning(
                "Recorded Hallucinate retry-budget findings after daemon pass: %s", findings
            )
        logger.info("Hallucinate multimodal-control daemon pass complete: %s", result)
        if parsed.once:
            break
        time.sleep(parsed.interval)


if __name__ == "__main__":
    main()
