#!/usr/bin/env python3
"""Lift-coding entry for PCCE implementation tracks.

Keep the control checkout as cwd/repo root and load supervisor code from the
accelerate gitlink. Do not re-root into external/ipfs_accelerate.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
ACCEL_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"
if str(ACCEL_ROOT) not in sys.path:
    sys.path.insert(0, str(ACCEL_ROOT))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor import (  # noqa: E402
    main,
)


if __name__ == "__main__":
    raise SystemExit(main())
