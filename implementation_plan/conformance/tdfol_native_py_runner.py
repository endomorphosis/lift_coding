#!/usr/bin/env python3
"""Python reference runner for native TDFOL vector execution."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.TDFOL.tdfol_core import ProofStatus, TDFOLKnowledgeBase
from ipfs_datasets_py.logic.TDFOL.tdfol_parser import parse_tdfol
from ipfs_datasets_py.logic.TDFOL.tdfol_prover import TDFOLProver


def _reason_for_status(status: ProofStatus) -> str:
    if status == ProofStatus.PROVED:
        return "proved"
    if status == ProofStatus.DISPROVED:
        return "refuted"
    return "unknown"


def _run_native_tdfol(axioms: List[str], goal: str) -> Dict[str, Any]:
    if not axioms:
        return {
            "status": "unknown",
            "reason": "unknown",
            "proverId": "tdfol-native",
            "metadata": {"route": "empty", "simulated": False},
        }

    obligations = set()
    prohibitions = set()
    for axiom in axioms:
        m_obl = re.match(r"^O\((.+)\)$", axiom)
        if m_obl:
            obligations.add(str(m_obl.group(1) or "").strip())
        m_proh = re.match(r"^F\((.+)\)$", axiom)
        if m_proh:
            prohibitions.add(str(m_proh.group(1) or "").strip())
    overlap = sorted(obligations.intersection(prohibitions))
    if overlap:
        return {
            "status": "refuted",
            "reason": "refuted",
            "proverId": "tdfol-native",
            "metadata": {"route": "deontic-contradiction", "simulated": False, "atom": overlap[0]},
        }

    kb = TDFOLKnowledgeBase()
    parsed_axioms = [parse_tdfol(axiom) for axiom in axioms]
    for formula in parsed_axioms:
        kb.add_axiom(formula)

    proof_goal = parse_tdfol(goal) if goal else parsed_axioms[0]
    proof = TDFOLProver(kb).prove(proof_goal, timeout_ms=5000)
    reason = _reason_for_status(proof.status)
    return {
        "status": reason,
        "reason": reason,
        "proverId": "tdfol-native",
        "metadata": {
            "route": "tdfol-native-proof",
            "simulated": False,
            "nativeStatus": proof.status.value if isinstance(proof.status, ProofStatus) else str(proof.status),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.vectors).read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []

    for vector in payload.get("vectors", []):
        input_payload = dict(vector.get("input") or {})
        tdfol = dict(input_payload.get("tdfol") or {})
        axioms = [str(item or "").strip() for item in tdfol.get("axioms", []) if str(item or "").strip()]
        goal = str(tdfol.get("goal") or "").strip()
        try:
            outcome = _run_native_tdfol(axioms, goal)
        except Exception as exc:
            outcome = {
                "status": "error",
                "reason": "error",
                "proverId": "tdfol-native",
                "metadata": {"route": "native-error", "simulated": False, "error": f"{exc.__class__.__name__}: {exc}"},
            }
        rows.append({"id": vector.get("id"), **outcome})

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
