#!/usr/bin/env python3
"""Python reference runner for modal decompiler temporal/operator helpers."""

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
    return {
        "operatorFeatureKeys": [
            decompiler._modal_operator_feature_key(symbol)
            for symbol in vector.get("symbols", [])
        ],
        "operatorPairFeatureKeys": [
            decompiler._modal_operator_pair_feature_key(pair[0], pair[1])
            for pair in vector.get("operatorPairs", [])
        ],
        "temporalClausePrefixRelations": [
            decompiler._temporal_clause_prefix_relation(prefix)
            for prefix in vector.get("prefixKeys", [])
        ],
        "temporalTransitionContextCues": [
            decompiler._temporal_transition_context_cues_from_text(text)
            for text in vector.get("contextTexts", [])
        ],
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
