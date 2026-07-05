#!/usr/bin/env python3
"""Python reference runner for deontic bridge decoded-text extraction."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from types import SimpleNamespace
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.bridge.deontic_norms import _decoded_text_from_capability_view


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
        document = vector.get("document", {})
        raw_views = document.get("views", {})
        views = {
            name: SimpleNamespace(payload=(value or {}).get("payload", {}))
            for name, value in raw_views.items()
            if isinstance(value, dict)
        }
        doc_obj = SimpleNamespace(views=views)
        rows.append(
            {
                "id": vector["id"],
                "output": _decoded_text_from_capability_view(doc_obj),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
