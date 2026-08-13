#!/usr/bin/env python3
"""Run SCA symbolic planning via ipfs_accelerate_py agent supervisor.

Uses ``agent_supervisor.sca_symbolic_planning`` with policy from
``symbolicPlanningPolicy`` (and shared allLogicFamilies with repair).

Usage:
  export PATH="$HOME/.elan/bin:$HOME/.local/share/ipfs_datasets_py/theorem-provers/bin:$PATH"
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit:scripts \\
    python3 scripts/sca_agent_supervisor_symbolic_planning.py [--max-tasks 8]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PROFILE = REPO / "config" / "swissknife_symbolic_contract_assurance_supervisor.json"
REPORT = (
    REPO
    / "data"
    / "agent_supervisor"
    / "swissknife_contract_assurance"
    / "evaluation"
    / "supervisor_symbolic_planning_stack_report.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-tasks", type=int, default=0)
    args = parser.parse_args(argv)

    os.chdir(REPO)
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "scripts"),
    ]
    managed = (
        Path.home()
        / ".local"
        / "share"
        / "ipfs_datasets_py"
        / "theorem-provers"
        / "bin"
    )
    if managed.is_dir():
        os.environ["PATH"] = str(managed) + os.pathsep + os.environ.get("PATH", "")
    elan = Path.home() / ".elan" / "bin"
    if elan.is_dir():
        os.environ["PATH"] = str(elan) + os.pathsep + os.environ.get("PATH", "")

    from ipfs_accelerate_py.agent_supervisor.sca_symbolic_planning import (
        load_planning_policy_from_supervisor_profile,
        run_symbolic_planning_stack,
        write_planning_report,
    )

    policy = load_planning_policy_from_supervisor_profile(PROFILE)
    policy.repo_root = str(REPO)
    if args.max_tasks > 0:
        policy.max_tasks = args.max_tasks

    print(
        f"planning all_families={policy.all_logic_families} "
        f"all_property_kinds={policy.all_property_kinds} "
        f"max_tasks={policy.max_tasks}"
    )
    report = run_symbolic_planning_stack(policy)
    path = write_planning_report(report, REPORT, repo_root=REPO)
    gates = report.get("gates") or {}
    print("gates", json.dumps(gates, sort_keys=True))
    print(
        f"selected={report.get('selected_count')} "
        f"portfolios={len(report.get('portfolios') or [])}"
    )
    for p in (report.get("portfolios") or [])[:6]:
        if "error" in p:
            print(f"  ERR {p.get('contract_id')}: {p.get('error')}")
            continue
        print(
            f"  {str(p.get('kind',''))[:24]:24} {str(p.get('operation',''))[:24]:24} "
            f"families={len(p.get('analysis_families') or [])} "
            f"pks={len(p.get('property_kinds') or [])} "
            f"steps={len(p.get('ordered_planning_steps') or [])}"
        )
    print(f"report={path}")
    print("PASSED" if report.get("passed") else "FAILED")
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
