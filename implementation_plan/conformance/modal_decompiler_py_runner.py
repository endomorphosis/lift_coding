#!/usr/bin/env python3
"""Python reference runner for modal decompiler helper parity vectors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.modal.decompiler import (
    DecodedModalPhrase,
    DecodedModalText,
    decoded_modal_phrase_slot_text_map,
    modal_text_token_similarity,
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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "schemaVersion": payload.get("schemaVersion"),
                "similarityResults": similarity_rows,
                "slotMapResults": slot_map_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
