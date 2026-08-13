#!/usr/bin/env python3
"""Apply Intent/Legal/Security/UI logic to intermediate representations (SCA).

Usage:
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit \\
    python3 scripts/sca_ir_logic_apply.py [--max-surfaces 4] [--with-admission]

Exit 0 when IR logic application passes for selected residual findings.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"
REPORT = SCA / "evaluation" / "supervisor_ir_logic_apply_report.json"


def _load_findings(max_surfaces: int) -> list[dict]:
    want = {
        "observed_contract_incomplete",
        "ambiguous_source_anchor",
        "ambiguous_target_anchor",
        "ambiguous_path_class",
    }
    by_key: dict[str, dict] = {}
    for rel in (
        "baseline/runtime_components/contract_findings.json",
        "baseline/runtime_components/findings.json",
    ):
        path = SCA / rel
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for item in doc.get("findings") or []:
            if not isinstance(item, dict):
                continue
            kind = str(item.get("kind") or item.get("reason_code") or "")
            if kind not in want:
                continue
            key = str(
                item.get("finding_id")
                or item.get("id")
                or item.get("contract_id")
                or ""
            )
            by_key[key or str(len(by_key))] = item
    return list(by_key.values())[:max_surfaces]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-surfaces", type=int, default=4)
    parser.add_argument(
        "--with-admission",
        action="store_true",
        help="Also run fail-closed plan admission over compiled IR constraints",
    )
    parser.add_argument(
        "--op",
        default="",
        help="Optional single operation to apply (skips residual findings load)",
    )
    args = parser.parse_args()

    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
    ]
    from ipfs_accelerate_py.agent_supervisor.proof.ir_logic_application import (
        IrLogicApplyPolicy,
        IrWorkSurface,
        apply_logic_to_ir,
        apply_logic_to_surfaces,
        load_apply_policy_from_supervisor_profile,
    )

    policy = load_apply_policy_from_supervisor_profile(
        str(REPO / "config" / "swissknife_symbolic_contract_assurance_supervisor.json")
    )
    policy.max_surfaces = args.max_surfaces
    if args.with_admission:
        policy.include_plan_admission = True

    if args.op:
        report = apply_logic_to_surfaces(
            [
                IrWorkSurface(
                    operation=args.op,
                    contract_id=f"contract:{args.op}",
                    kind="observed_contract_incomplete",
                    domain="sca",
                    consumer="symbolic_repair",
                )
            ],
            policy=policy,
            domain="sca",
            consumer="symbolic_repair",
        )
    else:
        findings = _load_findings(args.max_surfaces)
        # SCA residual findings — one domain of the general IR applicator
        report = apply_logic_to_surfaces(
            findings,
            policy=policy,
            domain="sca",
            consumer="symbolic_repair",
        )

    REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(f"report={REPORT}")
    print("selected", report.get("selected_count"), "passed", report.get("passed"))
    print("summary", report.get("summary"))
    for row in report.get("rows") or []:
        op = row.get("operation")
        print(
            f"  {op}: family_ok={row.get('family_ok')} "
            f"gates={row.get('gates')}"
        )
    print("PASSED" if report.get("passed") else "FAILED")
    return 0 if report.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
