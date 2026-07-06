#!/usr/bin/env python3
"""Python reference runner for modal decompiler helper parity vectors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.modal.decompiler import (
    DecodedModalPhrase,
    DecodedModalText,
    decode_modal_ir_document,
    decoded_modal_phrase_slot_text_map,
    modal_formula_to_text,
    modal_text_token_similarity,
)
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_ir import (
    ModalIRDocument,
    ModalIRFormula,
    ModalIROperator,
    ModalIRPredicate,
    ModalIRProvenance,
)


def _make_decoded_modal_text(payload: Dict[str, Any]) -> DecodedModalText:
    phrases = [
        DecodedModalPhrase(
            text=str(phrase.get("text", "")),
            slot=str(phrase.get("slot", "")),
            spans=phrase.get("spans", []),
            fixed=bool(phrase.get("fixed", False)),
            provenance_only=bool(phrase.get("provenanceOnly", False)),
        )
        for phrase in payload.get("phrases", [])
    ]
    return DecodedModalText(
        source_id=str(payload.get("sourceId", "doc")),
        text=str(payload.get("text", "")),
        phrases=phrases,
        support_span=payload.get("supportSpan", [0, 0]),
    )


def _make_formula(payload: Dict[str, Any]) -> ModalIRFormula:
    operator_payload = payload.get("operator", {})
    predicate_payload = payload.get("predicate", {})
    provenance_payload = payload.get("provenance", {})
    return ModalIRFormula(
        formula_id=str(payload.get("formulaId", "formula")),
        operator=ModalIROperator(
            family=str(operator_payload.get("family", "")),
            system=str(operator_payload.get("system", "")),
            symbol=str(operator_payload.get("symbol", "")),
            label=str(operator_payload.get("label", "")),
        ),
        predicate=ModalIRPredicate(
            name=str(predicate_payload.get("name", "")),
            arguments=[str(item) for item in predicate_payload.get("arguments", [])],
            role=predicate_payload.get("role"),
        ),
        provenance=ModalIRProvenance(
            source_id=str(provenance_payload.get("sourceId", "source")),
            start_char=int(provenance_payload.get("startChar", 0)),
            end_char=int(provenance_payload.get("endChar", 0)),
            citation=provenance_payload.get("citation"),
        ),
        conditions=[str(item) for item in payload.get("conditions", [])],
        exceptions=[str(item) for item in payload.get("exceptions", [])],
        metadata=payload.get("metadata", {}),
    )


def _make_document(payload: Dict[str, Any]) -> ModalIRDocument:
    return ModalIRDocument(
        document_id=str(payload.get("documentId", "document")),
        source=str(payload.get("source", "")),
        normalized_text=str(payload.get("normalizedText", payload.get("sourceText", ""))),
        formulas=[_make_formula(formula) for formula in payload.get("formulas", [])],
        metadata=payload.get("metadata", {}),
    )


def _decoded_document_summary(payload: Dict[str, Any], slot_subset_keys: List[str]) -> Dict[str, Any]:
    decoded = decode_modal_ir_document(_make_document(payload))
    data = decoded.to_dict()
    slot_map = decoded_modal_phrase_slot_text_map(decoded)
    return {
        "source_id": data["source_id"],
        "text": data["text"],
        "support_span": data["support_span"],
        "reconstruction_similarity": data["reconstruction_similarity"],
        "modal_span_coverage": data["modal_span_coverage"],
        "reconstruction_strategy": data["reconstruction_strategy"],
        "parser_warnings": data["parser_warnings"],
        "missing_slots": data["missing_slots"],
        "formulas": data["formulas"],
        "slot_subset": {
            key: slot_map[key]
            for key in slot_subset_keys
            if key in slot_map
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors_path = Path(args.vectors)
    out_path = Path(args.out)
    payload = json.loads(vectors_path.read_text(encoding="utf-8"))

    similarity_rows: List[Dict[str, Any]] = []
    for case in payload.get("similarityCases", []):
        similarity_rows.append(
            {
                "id": case["id"],
                "similarity": modal_text_token_similarity(case.get("left", ""), case.get("right", "")),
            }
        )

    slot_map_rows: List[Dict[str, Any]] = []
    for case in payload.get("slotMapCases", []):
        decoded = _make_decoded_modal_text(case.get("decoded", {}))
        slot_map_rows.append(
            {
                "id": case["id"],
                "slotMap": decoded_modal_phrase_slot_text_map(
                    decoded,
                    include_fixed=bool(case.get("includeFixed", False)),
                    include_provenance_only=bool(case.get("includeProvenanceOnly", True)),
                ),
            }
        )

    formula_render_rows: List[Dict[str, Any]] = []
    for case in payload.get("formulaRenderCases", []):
        formula_render_rows.append(
            {
                "id": case["id"],
                "text": modal_formula_to_text(_make_formula(case.get("formula", {}))),
            }
        )

    decoded_document_rows: List[Dict[str, Any]] = []
    for case in payload.get("decodedDocumentCases", []):
        decoded_document_rows.append(
            {
                "id": case["id"],
                "summary": _decoded_document_summary(
                    case.get("document", {}),
                    [str(item) for item in case.get("slotSubsetKeys", [])],
                ),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "schemaVersion": payload.get("schemaVersion"),
                "similarityResults": similarity_rows,
                "slotMapResults": slot_map_rows,
                "formulaRenderResults": formula_render_rows,
                "decodedDocumentResults": decoded_document_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
