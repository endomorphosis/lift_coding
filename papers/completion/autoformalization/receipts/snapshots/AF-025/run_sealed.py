#!/usr/bin/env python3
"""Run AF-025 packet checks under a sealed PATH and private HOME."""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[5]
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PYTHON = "/usr/bin/python3.12"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_step(name: str, argv_tail: list[str], home: Path) -> dict:
    stdout_path = HERE / "logs" / f"{name}.stdout.log"
    stderr_path = HERE / "logs" / f"{name}.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "/usr/bin/env", "-i",
        f"PATH={SEALED_PATH}",
        f"HOME={home}",
        f"XDG_CACHE_HOME={home / '.cache'}",
        f"XDG_CONFIG_HOME={home / '.config'}",
        f"XDG_DATA_HOME={home / '.local/share'}",
        f"XDG_STATE_HOME={home / '.local/state'}",
        "PYTHONDONTWRITEBYTECODE=1",
        "PYTHONNOUSERSITE=1",
        "LANG=C.UTF-8",
        PYTHON,
        *argv_tail,
    ]
    started = utc_now()
    t0 = time.perf_counter()
    proc = subprocess.run(
        argv,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - t0
    finished = utc_now()
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    meta = {
        "argv": argv,
        "cwd": ".",
        "elapsed_seconds": elapsed,
        "env": {
            "HOME": str(home),
            "LANG": "C.UTF-8",
            "PATH": SEALED_PATH,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        },
        "exit_code": proc.returncode,
        "finished_at": finished,
        "name": name,
        "started_at": started,
    }
    (HERE / "logs" / f"{name}.meta.json").write_text(
        json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return meta


def main() -> int:
    home = Path(tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-af025-"))
    os.makedirs(home / ".cache", exist_ok=True)
    os.makedirs(home / ".config", exist_ok=True)
    os.makedirs(home / ".local" / "share", exist_ok=True)
    os.makedirs(home / ".local" / "state", exist_ok=True)
    version = run_step("python_version", ["-V"], home)
    parse = run_step(
        "json_parse",
        [
            "-S",
            "-c",
            "import json,pathlib; json.loads(pathlib.Path('papers/completion/autoformalization/evidence/final_reproduction.json').read_text()); json.loads(pathlib.Path('papers/completion/autoformalization/submission/checksums.json').read_text())",
        ],
        home,
    )
    check = run_step(
        "check_outputs",
        ["-S", str((HERE / "check_outputs.py").relative_to(REPO_ROOT))],
        home,
    )
    report = {
        "python_version": version,
        "json_parse": parse,
        "check_outputs": check,
        "home": str(home),
        "ok": all(step["exit_code"] == 0 for step in (version, parse, check)),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
