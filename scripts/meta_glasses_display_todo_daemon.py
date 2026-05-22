#!/usr/bin/env python3
"""Run the ipfs_datasets_py todo implementation daemon for display-widget work."""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
DISCOVERY_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "discovery"
LOCAL_JDK = REPO_ROOT / ".tools" / "jdk17" / "jdk-17.0.18+8"
LOCAL_ANDROID_SDK = REPO_ROOT / ".tools" / "android-sdk"
VALIDATION_RETRY_BUDGET = 3

logger = logging.getLogger("meta_glasses_display_todo_daemon")


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def _unique_path_entries(entries: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for entry in entries:
        if not entry or entry in seen:
            continue
        seen.add(entry)
        unique.append(entry)
    return unique


def android_validation_environment(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return the repo-local Android validation environment contract."""

    local_jdk = repo_root / ".tools" / "jdk17" / "jdk-17.0.18+8"
    local_android_sdk = repo_root / ".tools" / "android-sdk"
    env: dict[str, str] = {}
    path_entries: list[str] = []
    missing: list[str] = []

    if (local_jdk / "bin" / "java").exists():
        env["JAVA_HOME"] = str(local_jdk)
        path_entries.append(str(local_jdk / "bin"))
    else:
        missing.append(str(local_jdk / "bin" / "java"))

    if local_android_sdk.exists():
        env["ANDROID_HOME"] = str(local_android_sdk)
        env["ANDROID_SDK_ROOT"] = str(local_android_sdk)
        for candidate in (
            local_android_sdk / "platform-tools",
            local_android_sdk / "cmdline-tools" / "latest" / "bin",
            local_android_sdk / "cmdline-tools" / "bin",
        ):
            if candidate.exists():
                path_entries.append(str(candidate))
    else:
        missing.append(str(local_android_sdk))

    return {
        "env": env,
        "path_entries": _unique_path_entries(path_entries),
        "missing": missing,
        "repo_root": str(repo_root),
    }


def _bootstrap_android_validation_env(repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    contract = android_validation_environment(repo_root)
    env = dict(contract["env"])
    path_entries = list(contract["path_entries"])
    for key, value in env.items():
        os.environ[key] = value
    if path_entries:
        current_path = os.environ.get("PATH", "")
        existing_entries = current_path.split(os.pathsep) if current_path else []
        os.environ["PATH"] = os.pathsep.join(_unique_path_entries([*path_entries, *existing_entries]))
    contract["effective_path"] = os.environ.get("PATH", "")
    return contract


def _android_env_assignment_prefix(repo_root: Path = REPO_ROOT) -> str:
    contract = android_validation_environment(repo_root)
    env = dict(contract["env"])
    assignments = [
        f"{key}={env[key]}"
        for key in ("JAVA_HOME", "ANDROID_HOME", "ANDROID_SDK_ROOT")
        if key in env
    ]
    path_entries = list(contract["path_entries"])
    if path_entries:
        assignments.append(f"PATH={os.pathsep.join(path_entries)}:$PATH")
    return " ".join(assignments)


def _validation_command_needs_android_env(command: str) -> bool:
    normalized = " ".join(command.split())
    if "./gradlew" not in normalized:
        return False
    if "mobile/android" not in normalized and "cd android" not in normalized:
        return False
    return "JAVA_HOME=" not in normalized and "org.gradle.java.home" not in normalized


def with_android_validation_env(command: str, repo_root: Path = REPO_ROOT) -> str:
    if not _validation_command_needs_android_env(command):
        return command
    prefix = _android_env_assignment_prefix(repo_root)
    if not prefix:
        return command
    return command.replace("./gradlew", f"env {prefix} ./gradlew", 1)


def enforce_android_validation_environment(todo_path: Path = TODO_PATH, repo_root: Path = REPO_ROOT) -> bool:
    """Rewrite bare Android Gradle validations to use the repo-local JDK/SDK."""

    if not todo_path.exists():
        return False

    lines = todo_path.read_text(encoding="utf-8").splitlines(keepends=True)
    changed = False
    updated_lines: list[str] = []
    for line in lines:
        if not line.startswith("- Validation:"):
            updated_lines.append(line)
            continue

        newline = "\n" if line.endswith("\n") else ""
        body = line[len("- Validation:") :].strip()
        commands = [item.strip() for item in body.split(";")]
        updated_commands = [with_android_validation_env(command, repo_root) for command in commands]
        if updated_commands != commands:
            changed = True
            updated_lines.append("- Validation: " + "; ".join(updated_commands) + newline)
        else:
            updated_lines.append(line)

    if not changed:
        return False

    todo_path.write_text("".join(updated_lines), encoding="utf-8")
    return True


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


def _task_ids_from_todo(todo_text: str) -> list[str]:
    task_ids: list[str] = []
    for line in todo_text.splitlines():
        if not line.startswith("## MGW-"):
            continue
        parts = line[3:].strip().split(" ", 1)
        if parts:
            task_ids.append(parts[0])
    return task_ids


def _next_mgw_task_id(todo_text: str) -> str:
    highest = 0
    for task_id in _task_ids_from_todo(todo_text):
        try:
            highest = max(highest, int(task_id.split("-", 1)[1]))
        except (IndexError, ValueError):
            continue
    return f"MGW-{highest + 1:03d}"


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
    date = datetime.now(timezone.utc).date().isoformat()
    path = discovery_dir / f"{date}-mgw-014-{source_task_id.lower()}-retry-budget.md"
    discovery_dir.mkdir(parents=True, exist_ok=True)
    log_paths = [str(event.get("log_path") or "") for event in failures if event.get("log_path")]
    attempt_numbers = [str(event.get("attempt") or "") for event in failures if event.get("attempt")]
    content = f"""# MGW-014 Retry-Budget Finding: {source_task_id}

Date: {date}
Task: MGW-014 Add supervisor validation-environment and retry-budget guardrails
Source task: {source_task_id}
Follow-up task: {follow_up_task_id}
Retry budget: {retry_budget}
Observed consecutive validation failures: {len(failures)}

## Evidence

- Failed command: `{failed_command}`
- Attempts: {", ".join(attempt_numbers) or "not recorded"}
- Logs: {", ".join(log_paths) or "not recorded"}

## Guardrail Result

The display-widget daemon retry budget classified this as backlog work instead of allowing
another implementation attempt to run against the same validation failure. The source task
is added to the strategy `blocked_tasks` list and the follow-up task below is appended to
the MGW todo board for normal daemon parsing.
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
    if "data/meta_glasses_display_widgets/discovery" not in outputs:
        outputs.append("data/meta_glasses_display_widgets/discovery")
    validation = with_android_validation_env(failed_command)
    return f"""## {follow_up_task_id} Resolve validation retry-budget failure for {source_task.task_id}

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: {", ".join(depends_on)}
- Outputs: {", ".join(outputs)}
- Validation: {validation}
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in {source_task.task_id}. Use evidence in {discovery_path} to fix the validation blocker, then remove {source_task.task_id} from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.
"""


def record_retry_budget_findings(
    *,
    todo_path: Path = TODO_PATH,
    events_path: Path = STATE_DIR / "meta_glasses_display_events.jsonl",
    strategy_path: Path = STATE_DIR / "meta_glasses_display_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## MGW-",
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

        follow_up_task_id = _next_mgw_task_id(todo_text)
        discovery_path = _write_retry_budget_discovery(
            discovery_dir=discovery_dir,
            follow_up_task_id=follow_up_task_id,
            source_task_id=task.task_id,
            failed_command=failed_command,
            failures=failures,
            retry_budget=retry_budget,
        )
        depends_on = ["MGW-014"] if "MGW-014" in task_ids else list(task.depends_on)
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
        finding = {
            "source_task_id": task.task_id,
            "follow_up_task_id": follow_up_task_id,
            "failure_count": len(failures),
            "failed_command": failed_command,
            "discovery_path": str(discovery_path),
        }
        findings.append(finding)

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
    os.chdir(REPO_ROOT)
    _bootstrap_android_validation_env()
    enforce_android_validation_environment(TODO_PATH)
    sys.path.insert(0, str(IPFS_DATASETS_ROOT))
    existing = os.environ.get("PYTHONPATH", "")
    os.environ["PYTHONPATH"] = os.pathsep.join(
        [str(IPFS_DATASETS_ROOT), existing] if existing else [str(IPFS_DATASETS_ROOT)]
    )

    from ipfs_datasets_py.optimizers.todo_daemon.implementation_daemon import (
        DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
        PortalImplementationDaemon,
        parse_args,
    )

    args = _with_default(args, "--todo-path", str(TODO_PATH))
    args = _with_default(args, "--state-dir", str(STATE_DIR))
    args = _with_default(args, "--task-prefix", "## MGW-")
    args = _with_default(args, "--state-prefix", "meta_glasses_display")
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
        findings = record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        if findings:
            logger.warning("Recorded validation retry-budget findings before daemon pass: %s", findings)
        result = daemon.run_once()
        findings = record_retry_budget_findings(
            todo_path=parsed.todo_path,
            events_path=events_path,
            strategy_path=strategy_path,
            discovery_dir=DISCOVERY_DIR,
            task_header_prefix=parsed.task_prefix,
        )
        if findings:
            logger.warning("Recorded validation retry-budget findings after daemon pass: %s", findings)
        logger.info("Display-widget implementation daemon pass complete: %s", result)
        if parsed.once:
            break
        time.sleep(parsed.interval)


if __name__ == "__main__":
    main()
