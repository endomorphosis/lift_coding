#!/usr/bin/env python3
"""Execute one sealed DOEP validation profile without a shell.

The worker-authored receipt is candidate evidence only.  The configured-board
controller owns validation admission and the task-completion CAS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "config/agent_supervisor_direct_objective_event_driven_planning_validation_profiles.json"
MAX_JSON_BYTES = 8 * 1024 * 1024


class ValidationError(RuntimeError):
    pass


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    metadata = os.lstat(path)
    if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode) or metadata.st_size > MAX_JSON_BYTES:
        raise ValidationError(f"unsafe or oversized JSON artifact: {path}")
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicates)
    if not isinstance(value, dict):
        raise ValidationError(f"JSON root is not an object: {path}")
    return value


def _contained(relative: str) -> Path:
    if not relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValidationError(f"unsafe profile path: {relative!r}")
    path = (ROOT / relative).resolve(strict=False)
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValidationError(f"profile path escapes repository: {relative!r}") from exc
    return path


def _digest(path: Path) -> str:
    if path.is_file():
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    return "directory"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True)
    args = parser.parse_args()
    result: dict[str, Any] = {
        "schema": "ipfs_accelerate_py/agent-supervisor/doep-validation-result@1",
        "task_id": args.task,
        "valid": False,
        "commands": [],
        "outputs": {},
        "completion_authoritative": False,
    }
    try:
        document = _read_json(PROFILE_PATH)
        profiles = document.get("profiles")
        if not isinstance(profiles, dict) or args.task not in profiles:
            raise ValidationError(f"unknown sealed task profile: {args.task}")
        profile = profiles[args.task]
        if not isinstance(profile, dict) or profile.get("task_id") != args.task:
            raise ValidationError("task/profile identity mismatch")
        plan_revision = str(document.get("plan_revision") or "")
        if not plan_revision or profile.get("plan_revision") != plan_revision:
            raise ValidationError("profile plan revision differs from its sealed document")
        if profile.get("shell") is not False:
            raise ValidationError("validation profile must seal shell=false")
        receipt_path = _contained(str(profile.get("receipt") or ""))
        receipt = _read_json(receipt_path)
        if receipt.get("schema") != "ipfs_accelerate_py/agent-supervisor/doep-task-receipt@1":
            raise ValidationError("candidate receipt schema mismatch")
        if receipt.get("task_id") != args.task or receipt.get("plan_revision") != plan_revision:
            raise ValidationError("candidate receipt identity mismatch")
        if receipt.get("candidate_status") not in {"implemented", "typed_non_success"}:
            raise ValidationError("candidate receipt has no closed candidate_status")
        if receipt.get("completion_authoritative") is not False:
            raise ValidationError("worker receipt may not claim completion authority")
        required = profile.get("required_outputs")
        if not isinstance(required, list) or not required:
            raise ValidationError("profile has no required outputs")
        for relative in required:
            path = _contained(str(relative))
            if not path.exists():
                raise ValidationError(f"missing required output: {relative}")
            result["outputs"][str(relative)] = _digest(path)
        commands = profile.get("commands")
        if not isinstance(commands, list) or not commands:
            raise ValidationError("profile has no commands")
        for command in commands:
            if not isinstance(command, dict) or not isinstance(command.get("argv"), list):
                raise ValidationError("validation command is not an argv record")
            argv = [str(item) for item in command["argv"]]
            if not argv or any("\x00" in item or "\n" in item or "\r" in item for item in argv):
                raise ValidationError("unsafe validation argv")
            timeout = int(command.get("timeout_seconds") or 1)
            completed = subprocess.run(argv, cwd=ROOT, shell=False, text=True, capture_output=True, timeout=timeout, check=False)
            command_result = {
                "argv": argv,
                "returncode": completed.returncode,
                "stdout_tail": completed.stdout[-4000:],
                "stderr_tail": completed.stderr[-4000:],
            }
            result["commands"].append(command_result)
            if completed.returncode != 0:
                raise ValidationError(f"validation command failed: {argv!r}")
        result["valid"] = True
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired, ValidationError) as exc:
        result["error"] = f"{type(exc).__name__}: {exc}"
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
