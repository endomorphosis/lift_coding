#!/usr/bin/env python3.12
"""Force-stage LGSWF-010 declared outputs ignored by the bare 'core' gitignore rule."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUB = ROOT / "external" / "ipfs_accelerate"
PATHS = [
    "ipfs_accelerate_py/agent_supervisor/core/world_snapshot_contracts.py",
    "test/agent_supervisor/core/test_world_snapshot_contracts.py",
]
RECEIPT = "artifacts/logic_governed_semantic_work_fabric/receipts/LGSWF-010.json"
OUT = ROOT / "_force_stage_lgswf010.out"


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def main() -> int:
    lines: list[str] = []
    env = os.environ.copy()
    env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
    lines.append(f"sub_exists={SUB.is_dir()}")
    for rel in PATHS:
        target = SUB / rel
        lines.append(f"exists {rel}: {target.is_file()} bytes={target.stat().st_size if target.is_file() else 0}")
        ignore = run(["git", "check-ignore", "-v", "--", rel], cwd=SUB)
        lines.append(f"ignore {rel}: rc={ignore.returncode} out={ignore.stdout.strip()!r}")
        add = run(["git", "--literal-pathspecs", "add", "--force", "--", rel], cwd=SUB)
        lines.append(f"add -f {rel}: rc={add.returncode} err={add.stderr.strip()[-200:]!r}")
        ls = run(["git", "ls-files", "--stage", "--", rel], cwd=SUB)
        lines.append(f"ls-files {rel}: {ls.stdout.strip()!r}")
    rec = run(["git", "add", "--", RECEIPT], cwd=ROOT)
    lines.append(f"receipt add: rc={rec.returncode} err={rec.stderr.strip()[-200:]!r}")
    st = run(
        [
            "git",
            "status",
            "--short",
            "--",
            RECEIPT,
            "external/ipfs_accelerate",
        ],
        cwd=ROOT,
    )
    lines.append(f"super status:\n{st.stdout}")
    # Validation
    env["PYTHONPATH"] = str(SUB) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    test = subprocess.run(
        [
            "/usr/bin/python3.12",
            "-m",
            "pytest",
            "-q",
            "external/ipfs_accelerate/test/agent_supervisor/core/test_world_snapshot_contracts.py",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    lines.append(f"pytest rc={test.returncode}")
    lines.append(test.stdout[-2000:])
    lines.append(test.stderr[-2000:])
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(OUT.read_text(encoding="utf-8"))
    return int(test.returncode)


if __name__ == "__main__":
    sys.exit(main())
