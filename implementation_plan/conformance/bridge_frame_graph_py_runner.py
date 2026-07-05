#!/usr/bin/env python3
"""Python reference runner for FOL/TDFOL and CEC/DCEC bridge graph parity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.bridge.cec_dcec import (
    _dcec_frame_logic_triples,
    _graph_data_from_triples as _dcec_graph_data_from_triples,
)
from ipfs_datasets_py.logic.bridge.fol_tdfol import (
    _graph_data_from_triples as _tdfol_graph_data_from_triples,
    _tdfol_frame_logic_triples,
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
        bridge = vector["bridge"]
        if bridge == "fol_tdfol":
            triples = _tdfol_frame_logic_triples(
                vector["documentId"],
                formula_records=vector.get("formulaRecords") or [],
            )
            graph = _tdfol_graph_data_from_triples(
                triples,
                graph_id=vector.get("graphId"),
                metadata=vector.get("graphMetadata") or {},
            )
        elif bridge == "cec_dcec":
            triples = _dcec_frame_logic_triples(
                vector["documentId"],
                records=vector.get("records") or [],
            )
            graph = _dcec_graph_data_from_triples(
                triples,
                graph_id=vector.get("graphId"),
                metadata=vector.get("graphMetadata") or {},
            )
        else:
            raise ValueError(f"Unsupported bridge: {bridge}")
        rows.append(
            {
                "id": vector["id"],
                "bridge": bridge,
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
