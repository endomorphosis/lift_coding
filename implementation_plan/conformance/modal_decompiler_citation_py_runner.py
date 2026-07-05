#!/usr/bin/env python3
"""Python reference runner for modal decompiler citation helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.modal import decompiler


def _evaluate(vector: Dict[str, Any]) -> Dict[str, Any]:
    delimiter_kinds = [
        decompiler._citation_section_delimiter_kind(value)
        for value in vector.get("delimiterKinds", [])
    ]
    signatures = [
        decompiler._citation_section_component_signature(
            number=item.get("number", ""),
            suffix=item.get("suffix", ""),
            suffix_kind=item.get("suffixKind", ""),
        )
        for item in vector.get("signatures", [])
    ]
    profiles = [
        decompiler._citation_section_component_profile(
            component_count=int(item.get("componentCount", 0)),
            suffix_component_count=int(item.get("suffixComponentCount", 0)),
            is_range=bool(item.get("isRange", False)),
        )
        for item in vector.get("profiles", [])
    ]
    source_ids = vector.get("sourceIds", [])

    return {
        "canonical": decompiler._canonical_usc_citation(
            vector.get("title", ""),
            vector.get("section", ""),
        ),
        "coordinate": decompiler._title_section_coordinate(
            vector.get("title", ""),
            vector.get("section", ""),
        ),
        "delimiterTokens": decompiler._citation_section_delimiter_tokens(
            vector.get("delimiterSection", "")
        ),
        "delimiterKinds": delimiter_kinds,
        "signatures": signatures,
        "profiles": profiles,
        "sourceIdCitations": [
            decompiler._source_id_inferred_citation(source_id)
            for source_id in source_ids
        ],
        "inferredCitations": decompiler._inferred_citations_from_source_ids(source_ids),
    }


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
        rows.append({"id": vector["id"], **_evaluate(vector)})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
