#!/usr/bin/env python3
"""General autonomous (no-LLM) agent supervisor repair CLI.

Reusable across domains. SCA is one optional work-item source.

Examples
--------
  # SCA board residuals (SwissKnife GUI ↔ MCP++ / package MCP)
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit \\
    python3 scripts/autonomous_supervisor_repair.py --source sca-board

  # Explicit operations (any domain)
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:external/ipfs_kit \\
    python3 scripts/autonomous_supervisor_repair.py \\
      --domain contract_repair \\
      --op tools_dispatch --op ipfs_add --kind ambiguous_source_anchor

  # Load SwissKnife IDL methods into alias registry
  PYTHONPATH=... python3 scripts/autonomous_supervisor_repair.py \\
      --source sca-board --swissknife-idl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
DEFAULT_REPORT = (
    REPO
    / "data"
    / "agent_supervisor"
    / "autonomous_repair"
    / "latest_report.json"
)
SCA_BOARD = (
    REPO
    / "data"
    / "agent_supervisor"
    / "swissknife_contract_assurance"
    / "generated"
    / "ipfs_accelerate_contract_repairs.todo.md"
)
SWISS_IDL = (
    REPO / "swissknife" / "src" / "services" / "ipfs" / "ipfs-idl-descriptors.ts"
)


def _setup() -> None:
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "external" / "ipfs_kit"),
        str(REPO / "Mcp-Plus-Plus"),
    ]


def _parse_sca_board(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    chunks = re.split(r"\n## (SCA-REPAIR-\S+)\s+", text)
    items: list[dict[str, Any]] = []
    if len(chunks) < 3:
        return items
    for i in range(1, len(chunks), 2):
        tid = chunks[i].strip()
        body = chunks[i + 1] if i + 1 < len(chunks) else ""
        title = body.splitlines()[0].strip() if body else ""
        m_contract = re.search(r"- Contract IDs:\s*(.+)", body)
        m_reason = re.search(r"- Reason codes:\s*(.+)", body)
        write_paths = re.findall(r"- Write paths:\s*(.+)", body)
        contract = (m_contract.group(1).strip() if m_contract else "").split(",")[0].strip()
        reasons = (
            [r.strip() for r in m_reason.group(1).split(",") if r.strip()]
            if m_reason
            else []
        )
        package, _, op = contract.partition(":")
        if not op and " for handler:" in title:
            op = title.split(" for handler:", 1)[-1].strip()
        items.append(
            {
                "work_id": tid,
                "task_id": tid,
                "operation": op or contract,
                "contract_id": contract,
                "package": package,
                "kind": reasons[0] if reasons else "ambiguous_source_anchor",
                "reason_codes": reasons,
                "write_paths": [p.strip() for p in write_paths],
                "path": write_paths[0].strip() if write_paths else "",
                "domain": "sca",
                "metadata": {"source": "sca-board", "title": title},
            }
        )
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        choices=("sca-board", "ops", "json"),
        default="ops",
        help="Work-item source (default: ops)",
    )
    parser.add_argument("--op", action="append", default=[], help="Operation name")
    parser.add_argument("--kind", default="work_item", help="Finding/work kind")
    parser.add_argument("--domain", default="agent_supervisor")
    parser.add_argument("--consumer", default="autonomous_repair")
    parser.add_argument("--json-items", default="", help="JSON file of work items")
    parser.add_argument(
        "--swissknife-idl",
        action="store_true",
        help="Load SwissKnife ipfs-idl-descriptors methods into alias registry",
    )
    parser.add_argument("--max-items", type=int, default=32)
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT),
        help="Output report path",
    )
    parser.add_argument(
        "--allow-code-edit-materialize",
        action="store_true",
        help="Mark single-path edit plans materialize_ready (still non-authoritative)",
    )
    parser.add_argument(
        "--edit-plan-dir",
        default="",
        help="Directory for body-free admitted edit plan JSON files",
    )
    parser.add_argument(
        "--materialize",
        action="store_true",
        help="After planning (or from --edit-plan-dir), apply materialize_ready plans",
    )
    parser.add_argument(
        "--materialize-only",
        action="store_true",
        help="Only materialize existing edit plans (skip repair analysis)",
    )
    parser.add_argument(
        "--write-package-bindings",
        action="store_true",
        help="Also write package-local surface_identity_bindings.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Materialize gates only; do not write binding catalogs",
    )
    args = parser.parse_args()
    _setup()

    from ipfs_accelerate_py.agent_supervisor.autonomous_repair import (
        AutonomousRepairPolicy,
        default_mcp_idl_alias_registry,
        run_autonomous_repair,
    )
    from ipfs_accelerate_py.agent_supervisor.autonomous_repair.interface_alias_registry import (
        load_idl_methods_from_typescript,
    )

    items: list[dict[str, Any]] = []
    if args.source == "sca-board":
        items = _parse_sca_board(SCA_BOARD)
        args.domain = args.domain if args.domain != "agent_supervisor" else "sca"
    elif args.source == "json":
        path = Path(args.json_items)
        doc = json.loads(path.read_text(encoding="utf-8"))
        raw = doc if isinstance(doc, list) else doc.get("items") or doc.get("rows") or []
        items = list(raw)
    else:
        for op in args.op:
            items.append(
                {
                    "work_id": f"op:{op}",
                    "operation": op,
                    "kind": args.kind,
                    "domain": args.domain,
                    "contract_id": f"surface:{op}",
                }
            )

    from ipfs_accelerate_py.agent_supervisor.autonomous_repair.materialize import (
        MaterializePolicy,
        materialize_edit_plan_dir,
    )

    registry = default_mcp_idl_alias_registry()
    if args.swissknife_idl and SWISS_IDL.is_file():
        methods = load_idl_methods_from_typescript(
            SWISS_IDL.read_text(encoding="utf-8")
        )
        registry.add_idl_methods(methods, source="swissknife_idl")
        print(f"loaded swissknife idl methods={len(methods)}")

    edit_plan_dir = Path(
        args.edit_plan_dir
        or (
            REPO
            / "data"
            / "agent_supervisor"
            / "autonomous_repair"
            / "edit_plans"
        )
    )

    out: dict[str, Any] = {}
    if not args.materialize_only:
        if not items and args.source != "ops":
            pass
        if not items:
            print("No work items. Use --source sca-board or --op NAME", file=sys.stderr)
            return 2
        policy = AutonomousRepairPolicy(
            domain=args.domain,
            consumer=args.consumer,
            max_items=args.max_items,
            allow_code_edit_materialize=bool(
                args.allow_code_edit_materialize or args.materialize
            ),
            require_zero_model_calls=True,
        )
        report = run_autonomous_repair(
            items,
            repo_root=REPO,
            policy=policy,
            alias_registry=registry,
            edit_plan_dir=edit_plan_dir,
        )
        out = report.to_dict()
    else:
        out = {
            "schema": "autonomous-repair-materialize-only@1",
            "passed": True,
            "llm_used": False,
            "model_call_count": 0,
            "summary": {},
            "rows": [],
        }

    if args.materialize or args.materialize_only:
        mat_policy = MaterializePolicy(
            domain=args.domain,
            dry_run=bool(args.dry_run),
            write_package_bindings=bool(args.write_package_bindings),
            write_data_catalog=True,
        )
        mat = materialize_edit_plan_dir(
            edit_plan_dir,
            repo_root=REPO,
            policy=mat_policy,
            alias_registry=registry,
            materialize_ready_only=True,
        )
        out["materialize"] = mat
        out["passed"] = bool(out.get("passed", True)) and bool(mat.get("passed"))
        print(
            f"materialize applied={mat['summary'].get('applied')} "
            f"rejected={mat['summary'].get('rejected')} "
            f"files={mat['summary'].get('files_written')}"
        )
        for rec in mat.get("receipts") or []:
            print(
                f"  mat {rec.get('operation', '')[:36]:36} "
                f"status={rec.get('status')} reasons={rec.get('reasons')}"
            )

    out["cli"] = {
        "source": args.source,
        "swissknife_idl": bool(args.swissknife_idl),
        "materialize": bool(args.materialize or args.materialize_only),
        "dry_run": bool(args.dry_run),
        "write_package_bindings": bool(args.write_package_bindings),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    report_path.write_text(
        json.dumps(out, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    if args.source == "sca-board" or args.materialize_only:
        sca_copy = (
            REPO
            / "data/agent_supervisor/swissknife_contract_assurance/evaluation/"
            "autonomous_supervisor_repair_report.json"
        )
        sca_copy.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        sca_copy.write_text(
            json.dumps(out, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )
        print(f"sca_report={sca_copy}")

    print(f"report={report_path}")
    if out.get("summary"):
        print(
            f"passed={out.get('passed')} llm_used={out.get('llm_used')} "
            f"model_calls={out.get('model_call_count')} "
            f"items={out['summary'].get('item_count')}"
        )
        if out["summary"].get("disposition_counts"):
            print("dispositions=", out["summary"]["disposition_counts"])
        surfaces = out["summary"].get("surface_resolution") or {}
        if surfaces:
            print(
                "surfaces resolved/ambiguous/missing=",
                surfaces.get("resolved_count"),
                surfaces.get("ambiguous_count"),
                surfaces.get("missing_count"),
            )
        print(
            "edit_plans=",
            out["summary"].get("edit_plans_count"),
            "materialize_ready=",
            out["summary"].get("materialize_ready_count"),
            "dir=",
            out["summary"].get("edit_plan_dir"),
        )
        for row in out.get("rows") or []:
            ep = row.get("edit_plan") or {}
            print(
                f"  {row['work_id'][:28]:28} {row['operation'][:36]:36} "
                f"disp={row['disposition']} "
                f"surface={(row.get('surface') or {}).get('status')} "
                f"idl={row.get('idl_matched_methods')} "
                f"edit={ep.get('plan_id', '-')[:22]} "
                f"mat_ready={ep.get('materialize_ready', False)}"
            )
    print("PASSED" if out.get("passed") and not out.get("llm_used") else "FAILED")
    return 0 if out.get("passed") and not out.get("llm_used") else 1


if __name__ == "__main__":
    raise SystemExit(main())
