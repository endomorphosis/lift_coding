#!/usr/bin/env python3
"""Run AF-005 freeze-check and qualify under the sealed validation environment."""
from __future__ import annotations

import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

PYTHON = "/usr/bin/python3.12"
PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"


def main() -> int:
    root = Path(".").resolve()
    snap = root / "papers/completion/autoformalization/receipts/snapshots/AF-005"
    home = Path(tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-"))
    for sub in (".cache", ".config", ".local/share", ".local/state"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    commands = [
        {
            "name": "freeze-check",
            "argv": [
                "env",
                "-i",
                f"PATH={PATH}",
                f"HOME={str(home)}",
                "PYTHONDONTWRITEBYTECODE=1",
                PYTHON,
                "papers/completion/autoformalization/receipts/snapshots/AF-005/freeze_annotation_evidence.py",
                "--root",
                ".",
                "--check",
            ],
            "script": "papers/completion/autoformalization/receipts/snapshots/AF-005/freeze_annotation_evidence.py",
        },
        {
            "name": "qualify",
            "argv": [
                "env",
                "-i",
                f"PATH={PATH}",
                f"HOME={str(home)}",
                "PYTHONDONTWRITEBYTECODE=1",
                PYTHON,
                "papers/completion/autoformalization/receipts/snapshots/AF-005/qualify_annotation_evidence.py",
                "--root",
                ".",
            ],
            "script": "papers/completion/autoformalization/receipts/snapshots/AF-005/qualify_annotation_evidence.py",
        },
    ]
    version = subprocess.check_output([PYTHON, "-V"], text=True).strip()
    results = []
    failed = False
    for command in commands:
        started = datetime.now(timezone.utc)
        proc = subprocess.run(command["argv"], cwd=str(root), capture_output=True, text=True)
        finished = datetime.now(timezone.utc)
        stdout_path = snap / f"{command['name']}.stdout.log"
        stderr_path = snap / f"{command['name']}.stderr.log"
        stdout_path.write_text(proc.stdout)
        stderr_path.write_text(proc.stderr)
        results.append(
            {
                "name": command["name"],
                "argv": command["argv"],
                "script_artifact": command["script"],
                "cwd": ".",
                "exit_code": proc.returncode,
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "stdout_log": str(stdout_path.relative_to(root)),
                "stderr_log": str(stderr_path.relative_to(root)),
                "stdout_bytes": len(proc.stdout.encode("utf-8")),
                "stderr_bytes": len(proc.stderr.encode("utf-8")),
            }
        )
        print(f"{command['name']} exit={proc.returncode}")
        if proc.stdout:
            print(proc.stdout, end="" if proc.stdout.endswith("\n") else "\n")
        if proc.stderr:
            print(proc.stderr, end="" if proc.stderr.endswith("\n") else "\n")
        if proc.returncode != 0:
            failed = True
    audit = {
        "schema": "paper-af005-validation-execution/v1",
        "python": PYTHON,
        "python_version": version,
        "path": PATH,
        "home": str(home),
        "cwd": ".",
        "provider_invoked": False,
        "independent_annotations_created": 0,
        "native_state_modified": False,
        "commands": results,
    }
    (snap / "validation-execution.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps({"home": str(home), "python_version": version, "failed": failed}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
