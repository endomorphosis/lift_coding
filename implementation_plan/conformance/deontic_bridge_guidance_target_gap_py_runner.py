#!/usr/bin/env python3
"""Python reference runner for deontic guidance target/gap helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.bridge.deontic_norms import (
    _canonical_deontic_gap_key,
    _canonical_deontic_target_view,
    _deontic_guidance_component_gaps,
    _deontic_guidance_underrepresented_components,
    _guidance_gap_quality_gate_passes,
)


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
        kind = vector.get("kind")
        if kind == "canonical_target_view":
            output: Any = _canonical_deontic_target_view(vector.get("value"))
        elif kind == "canonical_gap_key":
            output = _canonical_deontic_gap_key(vector.get("value"))
        elif kind == "gap_quality_gate":
            output = _guidance_gap_quality_gate_passes(vector.get("value"))
        elif kind == "component_gaps":
            output = _deontic_guidance_component_gaps(vector.get("row") or {})
        elif kind == "underrepresented_components":
            output = _deontic_guidance_underrepresented_components(vector.get("row") or {})
        else:
            output = None

        rows.append({"id": vector["id"], "kind": kind, "output": output})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
