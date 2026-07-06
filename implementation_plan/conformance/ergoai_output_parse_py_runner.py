#!/usr/bin/env python3
"""Run Python Ergo output binding parsing over JSON cases and emit JSON results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def _parse_ergo_output(output: str) -> List[Dict[str, Any]]:
    bindings: List[Dict[str, Any]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        binding: Dict[str, Any] = {}
        for part in line.split(","):
            part = part.strip()
            if "=" in part:
                var, _, val = part.partition("=")
                var = var.strip()
                if var.startswith("?"):
                    binding[var] = val.strip()
        if binding:
            bindings.append(binding)
    return bindings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    cases_path = Path(args.cases)
    out_path = Path(args.out)

    payload = json.loads(cases_path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    results = []
    for case in cases:
        results.append(
            {
                "id": case["id"],
                "bindings": _parse_ergo_output(case.get("output", "")),
            }
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
