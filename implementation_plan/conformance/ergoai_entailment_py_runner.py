#!/usr/bin/env python3
"""Run ErgoAI standard-fragment entailment vectors in Python and emit JSON results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _prove(formula: str, axioms: List[str]) -> bool:
    known = set(axioms)
    if formula in known:
        return True

    changed = True
    while changed:
        changed = False
        for axiom in list(known):
            if "→" not in axiom:
                continue
            ant, cons = [part.strip() for part in axiom.split("→", 1)]
            if ant in known and cons not in known:
                known.add(cons)
                changed = True
                if cons == formula:
                    return True
    return False


def _run(vectors: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for vector in vectors:
        results.append(
            {
                "id": vector["id"],
                "isProved": _prove(vector["formula"], vector.get("axioms", [])),
            }
        )
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors_path = Path(args.vectors)
    out_path = Path(args.out)

    payload = json.loads(vectors_path.read_text(encoding="utf-8"))
    results = {
        "schemaVersion": payload.get("schemaVersion"),
        "results": _run(payload.get("vectors", [])),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
