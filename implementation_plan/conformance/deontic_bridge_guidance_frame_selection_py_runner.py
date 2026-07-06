#!/usr/bin/env python3
"""Python reference runner for deontic guidance frame-candidate/selection helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.bridge.deontic_norms import (
    _deontic_guidance_frame_candidates,
    _selected_frame_from_deontic_compiler_guidance,
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
        context = vector.get("context") or {}
        norm = vector.get("norm") or {}
        if kind == "frame_candidates":
            output: Any = [
                {"source": source, "value": value}
                for source, value in _deontic_guidance_frame_candidates(context, norm=norm)
            ]
        elif kind == "selected_frame":
            output = _selected_frame_from_deontic_compiler_guidance(context, norm=norm)
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
