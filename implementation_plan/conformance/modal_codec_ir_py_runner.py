#!/usr/bin/env python3
"""Python reference runner for modal-IR helper outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.modal.codec import (
    decode_modal_ir_text,
    target_family_distribution_for_modal_ir,
    target_family_for_modal_ir,
)
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_ir import (
    ModalIRDocument,
    ModalIRFormula,
    ModalIROperator,
    ModalIRPredicate,
    ModalIRProvenance,
)


def _make_modal_ir(doc_payload: Dict[str, Any]) -> ModalIRDocument:
    formulas: List[ModalIRFormula] = []
    for idx, formula in enumerate(doc_payload.get("formulas", [])):
        operator_payload = formula.get("operator", {})
        predicate_payload = formula.get("predicate", {})
        formulas.append(
            ModalIRFormula(
                formula_id=f"f{idx}",
                operator=ModalIROperator(
                    family=str(operator_payload.get("family", "unknown")),
                    system=str(operator_payload.get("system", "")),
                    symbol=str(operator_payload.get("symbol", "?")),
                    label=str(operator_payload.get("symbol", "?")),
                ),
                predicate=ModalIRPredicate(
                    name=str(predicate_payload.get("name", "predicate")),
                    arguments=[str(arg) for arg in predicate_payload.get("arguments", [])],
                    role=None,
                ),
                provenance=ModalIRProvenance(
                    source_id="corpus",
                    start_char=0,
                    end_char=0,
                    citation=None,
                ),
            )
        )

    return ModalIRDocument(
        document_id="corpus-doc",
        source="corpus",
        normalized_text="",
        formulas=formulas,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors_path = Path(args.vectors)
    out_path = Path(args.out)

    payload = json.loads(vectors_path.read_text(encoding="utf-8"))
    rows = []
    for vector in payload.get("vectors", []):
        modal_ir = _make_modal_ir(vector.get("modalIr", {}))
        rows.append(
            {
                "id": vector["id"],
                "decodedText": decode_modal_ir_text(modal_ir),
                "targetFamily": target_family_for_modal_ir(modal_ir),
                "targetFamilyDistribution": target_family_distribution_for_modal_ir(modal_ir),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
