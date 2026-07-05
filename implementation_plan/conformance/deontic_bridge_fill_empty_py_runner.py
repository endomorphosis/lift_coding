#!/usr/bin/env python3
"""Python reference runner for deontic bridge fill/slot helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from ipfs_datasets_py.logic.bridge.deontic_norms import (
    _copy_slot_value,
    _fill_empty_field,
    _value_is_present,
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
        if kind == "value_is_present":
            output: Any = _value_is_present(vector.get("value"))
        elif kind == "copy_slot_value":
            output = _copy_slot_value(vector.get("value"))
        elif kind == "fill_empty_field":
            target = dict(vector.get("target") or {})
            source = dict(vector.get("source") or {})
            key = str(vector.get("key") or "")
            _fill_empty_field(target, source, key)
            output = target
        else:
            output = None

        rows.append(
            {
                "id": vector["id"],
                "kind": kind,
                "output": output,
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
