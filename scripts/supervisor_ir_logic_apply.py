#!/usr/bin/env python3
"""Apply Intent/Legal/Security/UI + AST/KG/vector IR logic (domain-agnostic).

Not SCA-taskboard-specific. SCA is one optional work-item source.

Examples
--------
  # Explicit operations (any domain)
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit \\
    python3 scripts/supervisor_ir_logic_apply.py \\
      --domain contract_repair \\
      --op tools_dispatch --op ipfs_add --kind ambiguous_source_anchor

  # Inventory probe only (no work surfaces)
  PYTHONPATH=... python3 scripts/supervisor_ir_logic_apply.py --probe-only \\
      --domain planner

  # SCA residual findings (optional consumer)
  PYTHONPATH=... python3 scripts/supervisor_ir_logic_apply.py --source sca-findings
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = (
    REPO
    / "data"
    / "agent_supervisor"
    / "ir_logic"
    / "latest_apply_report.json"
)
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"


def _setup() -> None:
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
    ]


def _load_sca_findings(max_surfaces: int) -> list[dict[str, Any]]:
    want = {
        "observed_contract_incomplete",
        "ambiguous_source_anchor",
        "ambiguous_target_anchor",
        "ambiguous_path_class",
    }
    by_key: dict[str, dict[str, Any]] = {}
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
                or item.get("operation")
                or ""
            )
            if not key or key in by_key:
                continue
            by_key[key] = item
            if len(by_key) >= max_surfaces:
                return list(by_key.values())
    return list(by_key.values())


def main() -> int:
    _setup()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--domain",
        default="agent_supervisor",
        help="Work domain (planner, doctor, contract_repair, sca, …)",
    )
    parser.add_argument(
        "--consumer",
        default="generic",
        help="Consumer label (planner, doctor, symbolic_repair, …)",
    )
    parser.add_argument("--op", action="append", default=[], help="Operation name")
    parser.add_argument("--kind", default="work_item")
    parser.add_argument(
        "--source",
        choices=("", "sca-findings"),
        default="",
        help="Optional residual finding source (SCA is one consumer)",
    )
    parser.add_argument("--max-surfaces", type=int, default=8)
    parser.add_argument("--probe-only", action="store_true")
    parser.add_argument("--with-admission", action="store_true")
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Output JSON report path",
    )
    args = parser.parse_args()

    from ipfs_accelerate_py.agent_supervisor.proof.ir_integration import (
        IrIntegrationPolicy,
        probe_ir_integration,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.ir_logic_application import (
        DEFAULT_APPLY_FAMILIES,
        IrLogicApplyPolicy,
        IrWorkSurface,
        apply_logic_to_surfaces,
    )
    from ipfs_accelerate_py.agent_supervisor.planning.ir_logic_hooks import (
        prepare_planning_context,
        inject_ir_into_formal_plan_source,
    )
    from ipfs_accelerate_py.agent_supervisor.planning.ir_logic_consumers import (
        diagnose_with_ir_logic,
    )

    inventory = probe_ir_integration(
        IrIntegrationPolicy(domain=args.domain),
        domain=args.domain,
    )

    if args.probe_only:
        report = {
            "schema": "ipfs_accelerate_py/agent-supervisor/ir-logic-cli@1",
            "recorded_at": datetime.now(timezone.utc).isoformat(),
            "mode": "probe_only",
            "domain": args.domain,
            "inventory": inventory,
            "passed": bool(inventory.get("passed")),
            "llm_used": False,
            "model_call_count": 0,
            "grants_execution_authority": False,
        }
        out = Path(args.report)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"probe passed={report['passed']} domain={args.domain}")
        print(f"families={[k for k,v in (inventory.get('families') or {}).items() if v.get('available')]}")
        print(f"report={out}")
        return 0 if report["passed"] else 1

    surfaces: list[IrWorkSurface] = []
    if args.source == "sca-findings":
        for item in _load_sca_findings(args.max_surfaces):
            surfaces.append(
                IrWorkSurface.from_mapping(
                    {
                        **item,
                        "domain": args.domain if args.domain != "agent_supervisor" else "sca",
                        "consumer": args.consumer or "symbolic_repair",
                    }
                )
            )
    for op in args.op:
        surfaces.append(
            IrWorkSurface(
                operation=op,
                kind=args.kind,
                domain=args.domain,
                consumer=args.consumer,
            )
        )

    if not surfaces:
        # Default sample so CLI always exercises the stack without SCA
        surfaces = [
            IrWorkSurface(
                operation="demo.tools_dispatch",
                kind=args.kind,
                domain=args.domain,
                consumer=args.consumer,
                path="agent_supervisor/work_surfaces/demo/tools_dispatch.py",
                symbol="tools_dispatch",
            )
        ]

    apply_policy = IrLogicApplyPolicy(
        families=DEFAULT_APPLY_FAMILIES,
        evaluate_security=True,
        include_plan_admission=bool(args.with_admission),
        max_surfaces=int(args.max_surfaces),
    )
    apply_doc = apply_logic_to_surfaces(
        surfaces[: args.max_surfaces],
        policy=apply_policy,
        domain=args.domain,
        consumer=args.consumer,
    )

    # Exercise planner + doctor + formal-plan hooks on the first surface
    first = surfaces[0]
    plan_ctx = prepare_planning_context(
        {
            "operation": first.operation,
            "domain": args.domain,
            "apply_ir_logic": True,
            "path": first.path,
            "symbol": first.symbol,
            "contract_id": first.contract_id,
        },
        domain=args.domain,
        force=True,
    )
    doctor_doc = diagnose_with_ir_logic(
        {
            "finding_id": first.finding_id or f"cli:{first.operation}",
            "kind": first.kind,
            "operation": first.operation,
            "path": first.path,
            "symbol": first.symbol,
            "contract_id": first.contract_id,
            "domain": args.domain,
        },
        domain=args.domain,
    )
    formal_src = inject_ir_into_formal_plan_source(
        {
            "operation": first.operation,
            "domain": args.domain,
            "apply_ir_logic": True,
            "path": first.path,
            "symbol": first.symbol,
        },
        domain=args.domain,
    )

    passed = bool(apply_doc.get("passed")) and bool(inventory.get("passed"))
    report = {
        "schema": "ipfs_accelerate_py/agent-supervisor/ir-logic-cli@1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply",
        "domain": args.domain,
        "consumer": args.consumer,
        "source": args.source or "explicit_ops",
        "inventory": {
            "passed": inventory.get("passed"),
            "gates": inventory.get("gates"),
            "families": {
                k: {"available": v.get("available"), "live_apply": v.get("live_apply")}
                for k, v in (inventory.get("families") or {}).items()
            },
        },
        "apply": apply_doc,
        "planner_hook": {
            "ir_logic_bound": plan_ctx.get("ir_logic_bound"),
            "ir_logic_passed": plan_ctx.get("ir_logic_passed"),
            "family_ok": plan_ctx.get("ir_logic_family_ok"),
        },
        "doctor_hook": {
            "passed": (doctor_doc.get("ir_logic") or {}).get("passed"),
            "family_ok": (doctor_doc.get("ir_logic") or {}).get("family_ok"),
        },
        "formal_plan_hook": {
            "ir_logic_bound": formal_src.get("ir_logic_bound"),
            "ast_records": len(formal_src.get("ast_records") or []),
            "policy_records": len(formal_src.get("policy_records") or []),
            "evidence_records": len(formal_src.get("evidence_records") or []),
        },
        "passed": passed,
        "llm_used": False,
        "model_call_count": 0,
        "grants_execution_authority": False,
        "completion_authoritative": False,
        "notes": [
            "Domain-agnostic IR logic application CLI.",
            "SCA taskboard is optional via --source sca-findings.",
            "IR apply never grants execution authority.",
        ],
    }

    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")

    summary = apply_doc.get("summary") or {}
    print(
        f"passed={passed} domain={args.domain} surfaces={len(surfaces)} "
        f"families={list(DEFAULT_APPLY_FAMILIES)}"
    )
    print(
        f"  apply intent_ok={summary.get('intent_ok')} legal_ok={summary.get('legal_ok')} "
        f"security_ok={summary.get('security_ok')} ui_ok={summary.get('ui_ok')} "
        f"ast_ok={summary.get('ast_ok')} kg_ok={summary.get('knowledge_graph_ok')} "
        f"vec_ok={summary.get('vector_index_ok')}"
    )
    print(
        f"  planner_bound={plan_ctx.get('ir_logic_bound')} "
        f"doctor_ok={(doctor_doc.get('ir_logic') or {}).get('passed')} "
        f"formal_ast={len(formal_src.get('ast_records') or [])} "
        f"formal_policy={len(formal_src.get('policy_records') or [])}"
    )
    print(f"report={out}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
