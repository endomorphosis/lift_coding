#!/usr/bin/env python3
"""Put lane_resume.py back to its registered pin before the SVF supervisor starts.

The registered bytes are the submodule HEAD. A drifted copy exits the
supervisor with status 78. This does not update the pin and does not run
goal redesign or sealed-source restore.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path("/home/barberb/lift_coding")
REPO = ROOT / "external" / "ipfs_accelerate"
REL = "ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py"
PIN = "fb6fd7e56126e59c78287908a92832151da872a373ec5ec9f6cbf9f7f08a5d07"


def main() -> int:
    path = REPO / REL
    current = hashlib.sha256(path.read_bytes()).hexdigest()
    if current == PIN:
        return 0
    pinned = subprocess.check_output(["git", "-C", str(REPO), "show", f"HEAD:{REL}"])
    if hashlib.sha256(pinned).hexdigest() != PIN:
        print("pinned lane_resume bytes are not HEAD", file=sys.stderr)
        return 78
    mode = path.stat().st_mode & 0o777
    temporary = path.with_name(path.name + ".pinrestore")
    temporary.write_bytes(pinned)
    os.chmod(temporary, mode)
    os.replace(temporary, path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != PIN:
        print("lane_resume pin restore failed", file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
