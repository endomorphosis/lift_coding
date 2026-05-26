#!/usr/bin/env python3
"""Run the accelerator todo implementation daemon for display-widget work."""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
IPFS_DATASETS_ROOT = REPO_ROOT / "external" / "ipfs_datasets"
IPFS_ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
TODO_PATH = REPO_ROOT / "implementation_plan" / "docs" / "18-swissknife-meta-glasses-display-widgets.todo.md"
STATE_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "state"
DISCOVERY_DIR = REPO_ROOT / "data" / "meta_glasses_display_widgets" / "discovery"
LOCAL_JDK = REPO_ROOT / ".tools" / "jdk17" / "jdk-17.0.18+8"
LOCAL_ANDROID_SDK = REPO_ROOT / ".tools" / "android-sdk"
VALIDATION_RETRY_BUDGET = 3
META_DISPLAY_WORKTREE_SUBMODULE_PATHS = (
    "swissknife",
    "external/meta-wearables-dat-android",
    "external/meta-wearables-dat-ios",
)

logger = logging.getLogger("meta_glasses_display_todo_daemon")


def _with_default(argv: list[str], flag: str, value: str) -> list[str]:
    if flag in argv:
        return argv
    return [flag, value, *argv]


def _with_repeated_default(argv: list[str], flag: str, values: tuple[str, ...]) -> list[str]:
    if flag in argv:
        return argv
    defaults: list[str] = []
    for value in values:
        defaults.extend([flag, value])
    return [*defaults, *argv]


def _ensure_ipfs_accelerate_path() -> None:
    if str(IPFS_ACCELERATE_ROOT) not in sys.path:
        sys.path.insert(0, str(IPFS_ACCELERATE_ROOT))


def _ensure_runtime_pythonpath() -> None:
    _ensure_ipfs_accelerate_path()
    for path in (IPFS_DATASETS_ROOT,):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
    existing = os.environ.get("PYTHONPATH", "")
    paths = [str(IPFS_ACCELERATE_ROOT), str(IPFS_DATASETS_ROOT)]
    os.environ["PYTHONPATH"] = os.pathsep.join([*paths, existing] if existing else paths)


def _discovery_output_path(repo_root: Path, discovery_dir: Path) -> str:
    try:
        return discovery_dir.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return "data/meta_glasses_display_widgets/discovery"


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


def record_retry_budget_findings(
    *,
    todo_path: Path = TODO_PATH,
    events_path: Path = STATE_DIR / "meta_glasses_display_events.jsonl",
    strategy_path: Path = STATE_DIR / "meta_glasses_display_strategy.json",
    discovery_dir: Path = DISCOVERY_DIR,
    task_header_prefix: str = "## MGW-",
    retry_budget: int = VALIDATION_RETRY_BUDGET,
) -> list[dict[str, Any]]:
    """Turn repeated validation failures into accelerator backlog items."""

    _ensure_ipfs_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.backlog_refinery import (
        record_retry_budget_findings as record_retries,
        task_id_prefix,
        task_ids_from_todo_text,
    )

    if retry_budget <= 0 or not todo_path.exists():
        return []

    task_prefix = task_id_prefix(task_header_prefix)
    todo_text = todo_path.read_text(encoding="utf-8") if todo_path.exists() else ""
    task_ids = set(task_ids_from_todo_text(todo_text, task_prefix=task_prefix))
    validation_depends_on = ["MGW-014"] if "MGW-014" in task_ids else []
    findings = record_retries(
        todo_path=todo_path,
        events_path=events_path,
        strategy_path=strategy_path,
        discovery_dir=discovery_dir,
        task_header_prefix_value=task_header_prefix,
        task_prefix=task_prefix,
        validation_retry_budget=retry_budget,
        merge_retry_budget=0,
        validation_depends_on=validation_depends_on,
        validation_task_command_transform=with_android_validation_env,
        discovery_output_path=_discovery_output_path(REPO_ROOT, discovery_dir),
    )
    for finding in findings:
        if finding.get("failure_kind") == "validation":
            finding.pop("failure_kind", None)
    return findings


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    os.chdir(REPO_ROOT)
    _bootstrap_android_validation_env()
    enforce_android_validation_environment(TODO_PATH)
    _ensure_runtime_pythonpath()

    from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import (
        DEFAULT_IMPLEMENTATION_TIMEOUT_SECONDS,
        LLM_MERGE_RESOLVER_COMMAND_ENV,
        PortalImplementationDaemon,
        parse_args,
    )

    args = _with_default(args, "--todo-path", str(TODO_PATH))
    args = _with_default(args, "--state-dir", str(STATE_DIR))
    args = _with_default(args, "--task-prefix", "## MGW-")
    args = _with_default(args, "--state-prefix", "meta_glasses_display")
    args = _with_repeated_default(args, "--worktree-submodule-path", META_DISPLAY_WORKTREE_SUBMODULE_PATHS)
    parsed = parse_args(args)
    logging.basicConfig(
        level=getattr(logging, parsed.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if parsed.llm_merge_resolver_command:
        os.environ[LLM_MERGE_RESOLVER_COMMAND_ENV] = parsed.llm_merge_resolver_command
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
        worktree_submodule_paths=parsed.worktree_submodule_path or META_DISPLAY_WORKTREE_SUBMODULE_PATHS,
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
