#!/usr/bin/env python3
"""Python reference runner for modal compiler family-token canonicalization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.modal.compiler import _canonical_modal_family_token


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
      value = vector.get("input", "")
      rows.append({
          "id": vector["id"],
          "output": _canonical_modal_family_token(value),
      })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
