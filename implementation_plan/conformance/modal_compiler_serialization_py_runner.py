#!/usr/bin/env python3
"""Python reference runner for modal compiler config/ambiguity serialization."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from ipfs_datasets_py.logic.modal.compiler import (
    ModalCompilationAmbiguity,
    ModalCompilerConfig,
)


def _ambiguity(row: Dict[str, Any]) -> Dict[str, Any]:
    ambiguity = ModalCompilationAmbiguity(
        ambiguity_type=row.get("ambiguityType", ""),
        message=row.get("message", ""),
        candidate_ids=list(row.get("candidateIds", [])),
        severity=row.get("severity", "review"),
        metadata=dict(row.get("metadata", {})),
    )
    return ambiguity.to_dict()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors_path = Path(args.vectors)
    out_path = Path(args.out)

    payload = json.loads(vectors_path.read_text(encoding="utf-8"))
    rows = [
        {"id": row["id"], "dict": _ambiguity(row)}
        for row in payload.get("ambiguities", [])
    ]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "schemaVersion": payload.get("schemaVersion"),
                "configDefaults": asdict(ModalCompilerConfig()),
                "ambiguities": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
