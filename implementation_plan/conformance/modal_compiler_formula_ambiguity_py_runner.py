#!/usr/bin/env python3
"""Python reference runner for modal compiler formula ambiguity helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.modal.compiler import DeterministicModalCompiler
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_ir import (
    ModalIRDocument,
    ModalIRFormula,
    ModalIROperator,
    ModalIRPredicate,
    ModalIRProvenance,
)


def _provenance(row: Mapping[str, Any]) -> ModalIRProvenance:
    return ModalIRProvenance(
        source_id=str(row.get("sourceId") or row.get("source_id") or ""),
        start_char=int(row.get("startChar", row.get("start_char", 0))),
        end_char=int(row.get("endChar", row.get("end_char", 0))),
        citation=row.get("citation"),
    )


def _formula(row: Mapping[str, Any]) -> ModalIRFormula:
    operator = dict(row.get("operator") or {})
    predicate = dict(row.get("predicate") or {})
    return ModalIRFormula(
        formula_id=str(row.get("formulaId") or row.get("formula_id") or ""),
        operator=ModalIROperator(
            family=str(operator.get("family") or ""),
            system=str(operator.get("system") or ""),
            symbol=str(operator.get("symbol") or ""),
            label=str(operator.get("label") or operator.get("symbol") or ""),
        ),
        predicate=ModalIRPredicate(
            name=str(predicate.get("name") or ""),
            arguments=[str(arg) for arg in predicate.get("arguments", [])],
            role=predicate.get("role"),
        ),
        provenance=_provenance(row.get("provenance") or {}),
        conditions=[str(item) for item in row.get("conditions", [])],
        exceptions=[str(item) for item in row.get("exceptions", [])],
        metadata=dict(row.get("metadata", {})),
    )


def _document(row: Mapping[str, Any]) -> ModalIRDocument:
    return ModalIRDocument(
        document_id=str(row.get("id") or "compiler-formula-doc"),
        source=str(row.get("source") or "legal_text"),
        normalized_text=str(row.get("normalizedText") or row.get("normalized_text") or ""),
        formulas=[_formula(formula) for formula in row.get("formulas", [])],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.vectors).read_text(encoding="utf-8"))
    compiler = object.__new__(DeterministicModalCompiler)
    formula_rows: List[Dict[str, Any]] = []
    for row in payload.get("formulaDocuments", []):
        ambiguities = DeterministicModalCompiler._formula_ambiguities(
            compiler,
            _document(row),
        )
        formula_rows.append(
            {
                "id": row["id"],
                "ambiguities": [ambiguity.to_dict() for ambiguity in ambiguities],
            }
        )

    ranking_rows = [
        {
            "id": row["id"],
            "share": DeterministicModalCompiler._ranking_share(dict(row.get("candidate") or {})),
        }
        for row in payload.get("rankingShareCases", [])
    ]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "schemaVersion": payload.get("schemaVersion"),
                "formulaDocuments": formula_rows,
                "rankingShareCases": ranking_rows,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
