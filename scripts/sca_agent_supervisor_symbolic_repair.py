#!/usr/bin/env python3
"""Run SCA symbolic_repair via ipfs_accelerate_py agent supervisor API.

Uses ``agent_supervisor.sca_symbolic_repair.run_symbolic_repair_stack`` with
policy from ``config/swissknife_symbolic_contract_assurance_supervisor.json``
(``symbolicRepairPolicy``).

This is the supervisor-native entry point (preferred over ad-hoc script chains).

Usage:
  export PATH="$HOME/.elan/bin:$HOME/.local/share/ipfs_datasets_py/theorem-provers/bin:$PATH"
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit:scripts \\
    python3 scripts/sca_agent_supervisor_symbolic_repair.py [--max-tasks 8]
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
    / "supervisor_symbolic_repair_stack_report.json"
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-tasks", type=int, default=0, help="Override policy maxTasks")
    parser.add_argument(
        "--stages",
        default="",
        help="Comma-separated stages (default: all from policy)",
    )
    parser.add_argument(
        "--inventory-only",
        action="store_true",
        help="Only probe supervisor logic inventory",
    )
    args = parser.parse_args(argv)

    os.chdir(REPO)
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "Mcp-Plus-Plus"),
        str(REPO / "scripts"),
    ]
    # Managed provers on PATH
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

    from ipfs_accelerate_py.agent_supervisor.sca_symbolic_repair import (
        load_policy_from_supervisor_profile,
        probe_supervisor_logic_inventory,
        run_symbolic_repair_stack,
        write_stack_report,
    )

    policy = load_policy_from_supervisor_profile(PROFILE)
    policy.repo_root = str(REPO)
    if args.max_tasks > 0:
        policy.max_tasks = args.max_tasks

    if args.inventory_only:
        inv = probe_supervisor_logic_inventory()
        print(json.dumps(inv, indent=2, default=str)[:4000])
        backends_ok = all(
            (inv.get("datasets_backends") or {}).get(k, {}).get("available")
            for k in ("ir", "tdfol", "cec", "smt", "hammer")
        )
        routes_ok = all((inv.get("routes_registered") or {}).values())
        print("PASSED" if backends_ok and routes_ok else "FAILED")
        return 0 if backends_ok and routes_ok else 1

    stages = None
    if args.stages.strip():
        stages = [s.strip() for s in args.stages.split(",") if s.strip()]

    print(
        f"policy all_families={policy.all_logic_families} "
        f"max_tasks={policy.max_tasks} "
        f"protocol_strict={policy.protocol_conformance_required} "
        f"kernel_itps={policy.kernel_itps}"
    )
    result = run_symbolic_repair_stack(policy, stages=stages)
    path = write_stack_report(result, REPORT)
    for stage in result.stages:
        print(
            f"  stage={stage.name:18} ok={stage.ok} "
            f"exit={stage.exit_code} err={stage.error[:80] if stage.error else ''}"
        )
    print(f"report={path}")
    print(f"snapshot={result.snapshot_id}")
    print("PASSED" if result.passed else "FAILED")
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
