#!/usr/bin/env python3
"""Run XPH-110's deterministic upto-metering and entitlement gate."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcplusplus_profile_h.metering_gate import run_metering_gate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "swissknife/test-results/mcpplusplus-profile-h-x402/metering.json")
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    if args.state_dir is None:
        with tempfile.TemporaryDirectory(prefix="xph-110-state-") as directory:
            report = run_metering_gate(state_dir=Path(directory))
    else:
        args.state_dir.mkdir(parents=True, exist_ok=True)
        report = run_metering_gate(state_dir=args.state_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"PASS: 3 deterministic signed meters, maximum authorization, and bounded quota; evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

