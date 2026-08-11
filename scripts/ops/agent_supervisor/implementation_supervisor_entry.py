#!/usr/bin/env python3
"""Delegate supervisor launches to the pinned accelerator submodule."""

from __future__ import annotations

import runpy
from pathlib import Path


CANONICAL_ENTRY = (
    Path(__file__).resolve().parents[3]
    / "external/ipfs_accelerate/scripts/ops/agent_supervisor/implementation_supervisor_entry.py"
)


if __name__ == "__main__":
    runpy.run_path(str(CANONICAL_ENTRY), run_name="__main__")
