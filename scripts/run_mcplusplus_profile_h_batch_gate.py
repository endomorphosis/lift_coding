#!/usr/bin/env python3
"""Run XPH-111's fail-closed EVM batch-settlement evaluation gate."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcplusplus_profile_h.batch_gate import run_batch_gate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=ROOT / "swissknife/test-results/mcplusplus-profile-h-x402/batch.json")
    parser.add_argument("--state-dir", type=Path)
    args = parser.parse_args()
    if args.state_dir is None:
        with tempfile.TemporaryDirectory(prefix="xph-111-state-") as directory:
            report = run_batch_gate(state_dir=Path(directory))
    else:
        report = run_batch_gate(state_dir=args.state_dir)
    if report["gateResult"] != "pass" or report["rolloutDecision"]["decision"] != "disabled":
        print("FAIL: batch settlement did not fail closed", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"PASS: batch ledger controls proven; rollout remains disabled; evidence: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
