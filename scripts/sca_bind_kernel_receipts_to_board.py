#!/usr/bin/env python3
"""Bind claim KERNEL_VERIFIED receipts into SCA repair board + RPR readiness.

Reads ``evaluation/kernel_reconstruction_pipeline_report.json`` and:

1. Writes per-claim receipt JSON under ``evaluation/claim_kernel_receipts/``
2. Annotates matching SCA-REPAIR tasks in the generated repair board with
   kernel evidence (non-authoritative completion notes — board remains
   ``completion_authoritative: false`` until external re-proof)
3. Extends ``rpr_admission_ready.json`` with claim-kernel evidence index and
   optional RPR admit previews for tasks that already bind snapshot +
   counterexample + reproof

Does **not** auto-complete repair tasks or grant LLM write authority beyond
proposal_only RPR policy.

Usage:
  PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets:scripts \\
    python3 scripts/sca_bind_kernel_receipts_to_board.py
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
SCA = REPO / "data" / "agent_supervisor" / "swissknife_contract_assurance"
KERNEL_REPORT = SCA / "evaluation" / "kernel_reconstruction_pipeline_report.json"
BOARD = SCA / "generated" / "ipfs_accelerate_contract_repairs.todo.md"
RPR_READY = SCA / "rpr_admission_ready.json"
RECEIPTS_DIR = SCA / "evaluation" / "claim_kernel_receipts"
BIND_REPORT = SCA / "evaluation" / "claim_kernel_board_bind_report.json"
SUMMARY = SCA / "baseline" / "runtime_components" / "summary.json"


def _setup() -> None:
    sys.path[:0] = [
        str(REPO / "external" / "ipfs_accelerate"),
        str(REPO / "external" / "ipfs_datasets"),
        str(REPO / "scripts"),
    ]


def _load_snapshot() -> str:
    if SUMMARY.exists():
        return str(
            json.loads(SUMMARY.read_text(encoding="utf-8")).get("snapshot_id") or ""
        )
    return ""


def collect_claim_receipts(kernel_doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten claim-bound kernel successes from pipeline report."""
    receipts: list[dict[str, Any]] = []
    snapshot = str(kernel_doc.get("snapshot_id") or "")
    for row in kernel_doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        contract_id = str(row.get("contract_id") or "")
        finding_id = str(row.get("finding_id") or "")
        op = str(row.get("operation") or "")
        kind = str(row.get("kind") or "")
        for att in row.get("kernel_attempts") or []:
            if not isinstance(att, dict):
                continue
            obl = str(att.get("obligation_id") or "")
            family = str(att.get("family") or "")
            for target, key in (
                ("lean", "claim_bound_lean"),
                ("coq", "claim_bound_coq"),
                ("isabelle", "claim_bound_isabelle"),
            ):
                bound = att.get(key) or {}
                if not isinstance(bound, dict) or not bound.get("claim_kernel_verified"):
                    continue
                rid = (
                    f"claim-kernel:{target}:"
                    f"{hashlib.sha256((obl + family + target).encode()).hexdigest()[:20]}"
                )
                receipts.append(
                    {
                        "schema": "sca-claim-kernel-receipt@1",
                        "receipt_id": rid,
                        "authority_scope": bound.get("authority_scope")
                        or "observation_bound_operator_semantics@1",
                        "target_itp": target,
                        "claim_kernel_verified": True,
                        "completion_authoritative": False,
                        "snapshot_id": snapshot or bound.get("snapshot_id") or "",
                        "obligation_id": obl,
                        "family": family,
                        "contract_id": contract_id or att.get("contract_id") or "",
                        "finding_id": finding_id or att.get("finding_id") or "",
                        "operation": op,
                        "finding_kind": kind,
                        "environment_lock": bound.get("environment_lock") or {},
                        "lean_expected_statement": bound.get("lean_expected_statement")
                        or bound.get("coq_expected_statement")
                        or bound.get("isabelle_expected_statement"),
                        "encoding": bound.get("encoding") or {},
                        "status": bound.get("status"),
                        "assurance": bound.get("assurance"),
                        "recorded_at": datetime.now(timezone.utc).isoformat(),
                        "source_report": str(KERNEL_REPORT),
                    }
                )
    return receipts


def write_receipt_files(receipts: list[dict[str, Any]]) -> list[str]:
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    paths: list[str] = []
    index: list[dict[str, Any]] = []
    for rec in receipts:
        rid = rec["receipt_id"].replace(":", "_")
        path = RECEIPTS_DIR / f"{rid}.json"
        path.write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
        paths.append(str(path))
        index.append(
            {
                "receipt_id": rec["receipt_id"],
                "path": str(path),
                "contract_id": rec.get("contract_id"),
                "finding_id": rec.get("finding_id"),
                "family": rec.get("family"),
                "target_itp": rec.get("target_itp"),
            }
        )
    index_path = RECEIPTS_DIR / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "schema": "sca-claim-kernel-receipt-index@1",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "count": len(index),
                "receipts": index,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    paths.append(str(index_path))
    return paths


def annotate_board(board_text: str, receipts: list[dict[str, Any]]) -> tuple[str, int]:
    """Append kernel evidence blocks under matching SCA-REPAIR tasks."""
    if not board_text.strip():
        return board_text, 0

    # Group receipts by contract_id, operation suffix, and finding_id
    by_contract: dict[str, list[dict[str, Any]]] = {}
    by_operation: dict[str, list[dict[str, Any]]] = {}
    by_finding: dict[str, list[dict[str, Any]]] = {}
    for r in receipts:
        cid = str(r.get("contract_id") or "")
        fid = str(r.get("finding_id") or "")
        op = str(r.get("operation") or "")
        if ":" in cid:
            op = op or cid.split(":", 1)[-1]
        if cid:
            by_contract.setdefault(cid, []).append(r)
        if op:
            by_operation.setdefault(op, []).append(r)
            # also package-less contract keys used on some boards
            by_contract.setdefault(op, []).append(r)
        if fid:
            by_finding.setdefault(fid, []).append(r)

    # Split into task sections (## SCA-REPAIR-...)
    parts = re.split(r"(?=^## SCA-REPAIR-)", board_text, flags=re.MULTILINE)
    if len(parts) <= 1:
        # append global section
        block = _global_kernel_section(receipts)
        return board_text.rstrip() + "\n\n" + block + "\n", 0

    annotated = 0
    out: list[str] = []
    for part in parts:
        if not part.startswith("## SCA-REPAIR-"):
            out.append(part)
            continue
        # Extract contract / finding lines
        cid_m = re.search(r"^- Contract IDs:\s*(.+)$", part, re.MULTILINE)
        fid_m = re.search(r"^- Finding ID:\s*(.+)$", part, re.MULTILINE)
        contracts = [
            c.strip()
            for c in (cid_m.group(1).split(",") if cid_m else [])
            if c.strip()
        ]
        finding = fid_m.group(1).strip() if fid_m else ""
        matched: list[dict[str, Any]] = []
        for c in contracts:
            matched.extend(by_contract.get(c, []))
            if ":" in c:
                matched.extend(by_operation.get(c.split(":", 1)[-1], []))
        if finding:
            matched.extend(by_finding.get(finding, []))
        # unique by receipt_id
        seen: set[str] = set()
        uniq: list[dict[str, Any]] = []
        for r in matched:
            rid = r["receipt_id"]
            if rid not in seen:
                seen.add(rid)
                uniq.append(r)
        if not uniq:
            out.append(part)
            continue
        # Remove prior auto kernel block if re-running
        part = re.sub(
            r"\n- Claim kernel evidence \(auto\):.*?(?=\n- |\n## |\n<!-- |\Z)",
            "\n",
            part,
            flags=re.DOTALL,
        )
        lines = [
            "- Claim kernel evidence (auto):",
            f"  - count: {len(uniq)}",
            "  - authority_scope: observation_bound_operator_semantics@1",
            "  - completion_authoritative: false",
        ]
        for r in uniq:
            lines.append(
                f"  - {r['target_itp']}: {r['receipt_id']} "
                f"family={r.get('family')} "
                f"lock={(r.get('environment_lock') or {}).get('lock_id', '')}"
            )
        # Insert after Snapshot ID line if present, else before HTML comment
        insert = "\n".join(lines) + "\n"
        if re.search(r"^- Snapshot ID:", part, re.MULTILINE):
            part = re.sub(
                r"(^- Snapshot ID:.*\n)",
                r"\1" + insert,
                part,
                count=1,
                flags=re.MULTILINE,
            )
        elif "<!-- contract-repair-task-v1:" in part:
            part = part.replace(
                "<!-- contract-repair-task-v1:",
                insert + "<!-- contract-repair-task-v1:",
                1,
            )
        else:
            part = part.rstrip() + "\n" + insert
        out.append(part)
        annotated += 1

    # Header note
    text = "".join(out)
    if "Claim kernel receipts bound:" not in text[:800]:
        text = re.sub(
            r"(- Open task count: \d+\n)",
            r"\1- Claim kernel receipts bound: "
            + str(len(receipts))
            + " (observation_bound; non-authoritative completion)\n",
            text,
            count=1,
        )
    return text, annotated


def _global_kernel_section(receipts: list[dict[str, Any]]) -> str:
    lines = [
        "## Claim kernel evidence (auto)",
        "",
        f"- Receipt count: {len(receipts)}",
        "- Authority scope: observation_bound_operator_semantics@1",
        "- Completion authoritative: false",
    ]
    for r in receipts[:50]:
        lines.append(
            f"- {r['receipt_id']}: {r.get('contract_id')} / {r.get('family')} / {r.get('target_itp')}"
        )
    return "\n".join(lines)


def update_rpr_ready(
    receipts: list[dict[str, Any]],
    *,
    snapshot_id: str,
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.sca_rpr_admission import (
        admit_implement_task,
        write_readiness_receipt,
    )

    # Preview RPR admission for each unique contract with kernel evidence
    previews: list[dict[str, Any]] = []
    by_contract: dict[str, list[dict[str, Any]]] = {}
    for r in receipts:
        by_contract.setdefault(str(r.get("contract_id") or ""), []).append(r)

    board_tasks = _parse_board_tasks(BOARD.read_text() if BOARD.exists() else "")
    for task in board_tasks:
        cid = str((task.get("contract_ids") or [""])[0] if task.get("contract_ids") else "")
        kernel_recs = by_contract.get(cid) or by_contract.get(
            str(task.get("contract_id") or "")
        ) or []
        if not kernel_recs:
            continue
        # Build implement-shaped task for admit_implement_task
        probe_task = {
            "task_id": task.get("task_id"),
            "snapshot_id": task.get("snapshot_id") or snapshot_id,
            "counterexample_id": task.get("counterexample_id"),
            "reproof_command": (task.get("reproof_commands") or ["python3 scripts/sca_kernel_reconstruction_pipeline.py"])[0],
            "finding_id": task.get("finding_id"),
            "contract_id": cid or task.get("contract_id"),
            "write_paths": task.get("write_paths") or [],
            "validation_commands": task.get("validation_commands")
            or ["python3 scripts/sca_symbolic_repair_ready.py"],
            "doctor_disposition": "transform_receipt",
            "kernel_claim_receipt_ids": [r["receipt_id"] for r in kernel_recs],
        }
        result = admit_implement_task(probe_task, current_snapshot_id=snapshot_id)
        if hasattr(result, "to_dict"):
            previews.append(
                {
                    "task_id": task.get("task_id"),
                    "contract_id": cid,
                    "admission": result.to_dict(),
                    "kernel_receipt_ids": [r["receipt_id"] for r in kernel_recs],
                    "admitted": result.__class__.__name__ == "AdmittedTargetPacket",
                }
            )
        else:
            previews.append(
                {
                    "task_id": task.get("task_id"),
                    "admission": str(result),
                    "admitted": False,
                }
            )

    admitted_n = sum(1 for p in previews if p.get("admitted"))
    receipt = write_readiness_receipt(
        RPR_READY,
        doctor_bridge_ok=True,
        ready=True,
        extra={
            "enable_tasks": ["SCA-ENABLE-DOCTOR", "SCA-ENABLE-RPR", "SCA-KERNEL-CLAIM-BIND"],
            "source": "sca_bind_kernel_receipts_to_board",
            "claim_kernel_receipts": {
                "count": len(receipts),
                "directory": str(RECEIPTS_DIR),
                "index": str(RECEIPTS_DIR / "index.json"),
                "authority_scope": "observation_bound_operator_semantics@1",
                "completion_authoritative": False,
            },
            "rpr_admit_previews": {
                "tasks_with_kernel_evidence": len(previews),
                "admitted": admitted_n,
                "rejected": len(previews) - admitted_n,
                "previews": previews[:40],
            },
            "policy_note": (
                "Kernel claim receipts bind observation-bound KERNEL_VERIFIED "
                "evidence for residual SCA; LLM implement remains proposal_only "
                "and still requires snapshot+counterexample+reproof admission."
            ),
        },
    )
    return {
        "rpr_ready_path": str(RPR_READY),
        "receipt": receipt,
        "admit_previews": previews,
        "admitted": admitted_n,
    }


def _parse_board_tasks(text: str) -> list[dict[str, Any]]:
    """Best-effort parse of SCA-REPAIR tasks from markdown + HTML comment payloads."""
    tasks: list[dict[str, Any]] = []
    # Prefer HTML comment payloads
    for m in re.finditer(
        r"<!-- contract-repair-task-v1:([A-Za-z0-9+/=]+) -->", text
    ):
        try:
            raw = base64.b64decode(m.group(1))
            data = json.loads(raw.decode("utf-8"))
            if isinstance(data, dict):
                tasks.append(data)
        except Exception:  # noqa: BLE001
            continue
    if tasks:
        return tasks
    # Fallback: markdown fields
    for part in re.split(r"(?=^## SCA-REPAIR-)", text, flags=re.MULTILINE):
        if not part.startswith("## SCA-REPAIR-"):
            continue
        task: dict[str, Any] = {}
        tm = re.match(r"^## (SCA-REPAIR-\S+)", part)
        if tm:
            task["task_id"] = tm.group(1)
        for key, pattern in (
            ("snapshot_id", r"^- Snapshot ID:\s*(.+)$"),
            ("finding_id", r"^- Finding ID:\s*(.+)$"),
            ("counterexample_id", r"^- Counterexample ID:\s*(.+)$"),
        ):
            mm = re.search(pattern, part, re.MULTILINE)
            if mm:
                task[key] = mm.group(1).strip()
        cm = re.search(r"^- Contract IDs:\s*(.+)$", part, re.MULTILINE)
        if cm:
            task["contract_ids"] = [c.strip() for c in cm.group(1).split(",") if c.strip()]
            task["contract_id"] = task["contract_ids"][0] if task["contract_ids"] else ""
        rm = re.search(r"^- Re-proof:\s*(.+)$", part, re.MULTILINE)
        if rm:
            task["reproof_commands"] = [rm.group(1).strip()]
        if task.get("task_id"):
            tasks.append(task)
    return tasks


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--kernel-report",
        type=Path,
        default=KERNEL_REPORT,
        help="Path to kernel reconstruction report",
    )
    parser.add_argument(
        "--skip-board",
        action="store_true",
        help="Do not annotate repair board markdown",
    )
    parser.add_argument(
        "--skip-rpr",
        action="store_true",
        help="Do not update rpr_admission_ready.json",
    )
    args = parser.parse_args(argv)
    _setup()

    if not args.kernel_report.exists():
        print(f"FAILED missing kernel report {args.kernel_report}")
        return 1

    kernel_doc = json.loads(args.kernel_report.read_text(encoding="utf-8"))
    snapshot_id = str(kernel_doc.get("snapshot_id") or _load_snapshot())
    receipts = collect_claim_receipts(kernel_doc)
    print(f"claim_receipts={len(receipts)} snapshot={snapshot_id}")

    paths = write_receipt_files(receipts)
    print(f"wrote_receipts={len(paths)} dir={RECEIPTS_DIR}")

    board_annotated = 0
    if not args.skip_board and BOARD.exists():
        text = BOARD.read_text(encoding="utf-8")
        new_text, board_annotated = annotate_board(text, receipts)
        BOARD.write_text(new_text, encoding="utf-8")
        print(f"board_tasks_annotated={board_annotated} path={BOARD}")
    elif not BOARD.exists():
        print(f"board_missing={BOARD}")

    rpr_info: dict[str, Any] = {"skipped": True}
    if not args.skip_rpr:
        rpr_info = update_rpr_ready(receipts, snapshot_id=snapshot_id)
        print(
            f"rpr_ready={rpr_info.get('rpr_ready_path')} "
            f"admit_previews={len(rpr_info.get('admit_previews') or [])} "
            f"admitted={rpr_info.get('admitted')}"
        )

    report = {
        "schema": "sca-claim-kernel-board-bind@1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_id": snapshot_id,
        "completion_authoritative": False,
        "receipt_count": len(receipts),
        "receipt_paths": paths,
        "board_tasks_annotated": board_annotated,
        "board_path": str(BOARD),
        "rpr": {
            "path": str(RPR_READY),
            "admitted_previews": rpr_info.get("admitted"),
            "preview_count": len(rpr_info.get("admit_previews") or []),
        },
        "notes": [
            "Claim kernel receipts are observation_bound_operator_semantics@1.",
            "Board completion remains non-authoritative; external re-proof still required.",
            "RPR admit still requires snapshot + counterexample + reproof; kernel receipts are bound evidence only.",
            "LLM implement stays proposal_only.",
        ],
        "passed": len(receipts) >= 1 and (args.skip_board or board_annotated >= 0),
    }
    BIND_REPORT.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    BIND_REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"report={BIND_REPORT}")
    print("PASSED" if report["passed"] else "FAILED")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
