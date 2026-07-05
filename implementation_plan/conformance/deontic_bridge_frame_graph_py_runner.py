#!/usr/bin/env python3
"""Python reference runner for deontic bridge frame-logic graph projection."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.bridge.deontic_norms import (
    _frame_logic_triples_from_deontic_records,
    _graph_data_from_triples,
)


def _graph_to_dict(graph: Any) -> Dict[str, Any] | None:
    if graph is None:
        return None
    return graph.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors_path = Path(args.vectors)
    out_path = Path(args.out)

    payload = json.loads(vectors_path.read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []

    for vector in payload.get("vectors", []):
        triples = _frame_logic_triples_from_deontic_records(
            vector["documentId"],
            norms=vector.get("norms") or [],
            formula_records=vector.get("formulaRecords") or [],
            coverage_records=vector.get("coverageRecords") or [],
        )
        graph = _graph_data_from_triples(
            triples,
            graph_id=vector.get("graphId"),
            metadata=vector.get("graphMetadata") or {},
        )
        rows.append(
            {
                "id": vector["id"],
                "triples": triples,
                "graph": _graph_to_dict(graph),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {"schemaVersion": payload.get("schemaVersion"), "results": rows},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
