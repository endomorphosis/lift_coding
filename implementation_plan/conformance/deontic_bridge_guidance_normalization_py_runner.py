#!/usr/bin/env python3
"""Python reference runner for deontic guidance normalization helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.bridge.deontic_norms import (
    _canonical_deontic_frame_symbol,
    _deontic_guidance_target_view,
    _normalized_guidance_text,
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
        if kind == "target_view":
            output: Any = _deontic_guidance_target_view(vector.get("row") or {})
        elif kind == "canonical_frame_symbol":
            output = _canonical_deontic_frame_symbol(vector.get("value"))
        elif kind == "normalized_guidance_text":
            output = _normalized_guidance_text(vector.get("value"))
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
