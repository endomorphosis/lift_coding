#!/usr/bin/env python3
"""Python reference runner for regex/legal modal compiler family emission."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.optimizers.logic_theorem_optimizer.legal_modal_parser import (
    LegalModalParser,
)
from ipfs_datasets_py.optimizers.logic_theorem_optimizer.modal_registry import (
    DEFAULT_MODAL_REGISTRY,
)


def _row(parser: LegalModalParser, vector: Dict[str, Any]) -> Dict[str, Any]:
    text = str(vector.get("text") or "")
    citation = str(vector.get("citation") or "")
    source = str(vector.get("source") or "legal_text")
    document_id = str(vector.get("documentId") or "doc")
    normalized_text = parser.normalize_text(text)
    modal_ir = parser.parse(
        text,
        document_id=document_id,
        citation=citation,
        source=source,
    )
    families = [str(formula.operator.family) for formula in modal_ir.formulas]
    ambiguity_types = ["missing_modal_formula"] if normalized_text and not families else []
    return {
        "id": vector["id"],
        "normalizedText": normalized_text,
        "parserName": "legal_modal_parser_v1",
        "formulaFamilies": families,
        "formulaCount": len(families),
        "ambiguityTypes": ambiguity_types,
        "metadata": {
            "citation": citation,
            "deterministic_parser": str(
                modal_ir.metadata.get("deterministic_parser") or "legal_modal_parser_v1"
            ),
            "modal_family_counts": dict(Counter(families)),
            "parser_backend": "regex",
            "segment_count": int(modal_ir.metadata.get("segment_count") or 0),
            "ambiguity_count": len(ambiguity_types),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.vectors).read_text(encoding="utf-8"))
    modal_parser = LegalModalParser(registry=DEFAULT_MODAL_REGISTRY)
    rows = [_row(modal_parser, vector) for vector in payload.get("vectors", [])]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
