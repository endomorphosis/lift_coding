#!/usr/bin/env python3
"""Run AF-012 T3 proof-head measurement and checks under a sealed PATH."""
from __future__ import annotations

import json
import os
import subprocess
import sys
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


def run_step(name: str, script: Path, home: Path) -> dict:
    stdout_path = HERE / "logs" / f"{name}.stdout.log"
    stderr_path = HERE / "logs" / f"{name}.stderr.log"
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    argv = [
        "/usr/bin/env",
        "-i",
        f"PATH={SEALED_PATH}",
        f"HOME={home}",
        "PYTHONDONTWRITEBYTECODE=1",
        "LANG=C.UTF-8",
        "PYTHONPATH=external/ipfs_datasets",
        "IPFS_AUTO_INSTALL=false",
        "IPFS_DATASETS_AUTO_INSTALL=false",
        PYTHON,
        str(script.relative_to(REPO_ROOT)),
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
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    finished = utc_now()
    stdout_path.write_text(proc.stdout, encoding="utf-8")
    stderr_path.write_text(proc.stderr, encoding="utf-8")
    meta = {
        "argv": argv,
        "cwd": ".",
        "elapsed_ms": elapsed_ms,
        "env": {"HOME": str(home), "PATH": SEALED_PATH, "PYTHONPATH": "external/ipfs_datasets"},
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
    home = Path(tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-af012-"))
    measure = run_step("run", HERE / "run_t3_proof_heads.py", home)
    check = run_step("check_outputs", HERE / "check_outputs.py", home)
    report = {
        "home": str(home),
        "run": measure,
        "check_outputs": check,
        "ok": measure["exit_code"] == 0 and check["exit_code"] == 0,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
