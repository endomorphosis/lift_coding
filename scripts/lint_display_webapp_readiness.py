#!/usr/bin/env python3
"""Lint a display-webapp readiness JSON descriptor."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from handsfree.display_webapp_compat import evaluate_display_webapp_readiness


def _load_payload(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Readiness file does not exist: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate display-webapp readiness for smart-glasses constraints."
    )
    parser.add_argument(
        "readiness_file",
        nargs="?",
        default="config/display_webapp_readiness.example.json",
        help="Path to readiness JSON descriptor.",
    )
    args = parser.parse_args()

    payload = _load_payload(Path(args.readiness_file))
    result = evaluate_display_webapp_readiness(payload)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
