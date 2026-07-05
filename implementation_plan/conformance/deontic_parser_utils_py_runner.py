#!/usr/bin/env python3
"""Python reference runner for deontic parser utility parity vectors."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.deontic.utils.deontic_parser import (
    classify_legal_entity,
    classify_modal,
    extract_action_recipient,
    normalize_predicate_name,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors_path = Path(args.vectors)
    out_path = Path(args.out)

    payload = json.loads(vectors_path.read_text(encoding="utf-8"))

    modal_results: List[Dict[str, Any]] = []
    for case in payload.get("modalCases", []):
        modality, operator = classify_modal(case.get("input", ""))
        modal_results.append(
            {
                "id": case["id"],
                "modality": modality,
                "operator": operator,
            }
        )

    entity_results = [
        {
            "id": case["id"],
            "value": classify_legal_entity(case.get("input", "")),
        }
        for case in payload.get("entityCases", [])
    ]

    predicate_results = [
        {
            "id": case["id"],
            "value": normalize_predicate_name(case.get("input", "")),
        }
        for case in payload.get("predicateCases", [])
    ]

    recipient_results = [
        {
            "id": case["id"],
            "value": extract_action_recipient(case.get("input", "")),
        }
        for case in payload.get("recipientCases", [])
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "schemaVersion": payload.get("schemaVersion"),
                "modalResults": modal_results,
                "entityResults": entity_results,
                "predicateResults": predicate_results,
                "recipientResults": recipient_results,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
