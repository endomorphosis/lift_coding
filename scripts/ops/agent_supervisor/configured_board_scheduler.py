#!/usr/bin/env python3
"""Thin portfolio entry for the canonical external configured-board runtime."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
ACCELERATE = ROOT / "external" / "ipfs_accelerate"
for path in (str(ACCELERATE), str(ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from ipfs_accelerate_py.agent_supervisor.runtime.configured_board_scheduler import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
