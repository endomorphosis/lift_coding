#!/usr/bin/env python3
"""Probe Intent/Legal/Security/UI IR wiring into the agent supervisor.

Usage:
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit \\
    python3 scripts/sca_ir_integration_probe.py

Exit 0 when required IR gates pass under supervisor policy.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
REPORT = (
    REPO
    / "data"
    / "agent_supervisor"
    / "swissknife_contract_assurance"
    / "evaluation"
    / "supervisor_ir_integration_report.json"
)


def main() -> int:
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
    ]
    from ipfs_accelerate_py.agent_supervisor.sca_ir_integration import (
        load_ir_policy_from_supervisor_profile,
        probe_ir_integration,
    )
    from ipfs_accelerate_py.agent_supervisor.sca_symbolic_repair import (
        probe_supervisor_logic_inventory,
    )

    policy = load_ir_policy_from_supervisor_profile(
        REPO / "config" / "swissknife_symbolic_contract_assurance_supervisor.json"
    )
    ir = probe_ir_integration(policy)
    inv = probe_supervisor_logic_inventory(ir_policy=policy.to_dict())

    report = {
        "schema": "sca-ir-integration-probe@1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "passed": bool(ir.get("passed")),
        "ir_integration": ir,
        "inventory_ir": inv.get("ir_integration"),
        "analysis_families_expected": inv.get("analysis_families_expected"),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )

    print(f"report={REPORT}")
    print("families:", json.dumps(ir.get("families"), indent=2, default=str))
    print("gates:", json.dumps(ir.get("gates"), indent=2, default=str))
    print(
        "ui_ir:",
        "bridge_ok"
        if (ir.get("ui_ir") or {}).get("available")
        else "unavailable",
        "| full_ui_ux_ir=",
        (ir.get("ui_ir") or {}).get("full_ui_ux_ir_available"),
    )
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
