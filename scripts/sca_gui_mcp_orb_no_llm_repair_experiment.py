#!/usr/bin/env python3
"""SCA/SwissKnife consumer of the general autonomous repair engine.

For reusable repair work prefer:

  python3 scripts/autonomous_supervisor_repair.py --source sca-board --swissknife-idl

This wrapper keeps the historical entrypoint and SCA evaluation report path.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [
        sys.executable,
        str(REPO / "scripts" / "autonomous_supervisor_repair.py"),
        "--source",
        "sca-board",
        "--swissknife-idl",
        "--domain",
        "sca",
        "--consumer",
        "symbolic_repair",
        "--report",
        str(
            REPO
            / "data/agent_supervisor/swissknife_contract_assurance/evaluation/"
            "gui_mcp_orb_no_llm_repair_experiment_report.json"
        ),
    ]
    env = dict(**{k: v for k, v in __import__("os").environ.items()})
    env["PYTHONPATH"] = ":".join(
        [
            str(REPO / "external" / "ipfs_accelerate"),
            str(REPO / "external" / "ipfs_datasets"),
            str(REPO / "external" / "ipfs_kit"),
            env.get("PYTHONPATH", ""),
        ]
    )
    return subprocess.call(cmd, cwd=str(REPO), env=env)


if __name__ == "__main__":
    raise SystemExit(main())
