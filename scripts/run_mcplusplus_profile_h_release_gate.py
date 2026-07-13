#!/usr/bin/env python3
"""Run XPH-113's fail-closed Profile H testnet release gate."""

from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from mcplusplus_profile_h.release_gate import (  # noqa: E402
    generate_release_packet,
    write_json_atomic,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("testnet", "mainnet"), default="testnet")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "swissknife/test-results/mcpplusplus-profile-h-x402/release")
    parser.add_argument("--state-dir", type=Path,
                        help="retain non-secret ledger state for gate diagnosis")
    args = parser.parse_args()
    if args.state_dir is None:
        with tempfile.TemporaryDirectory(prefix="xph-113-state-") as directory:
            report, sbom = generate_release_packet(ROOT, Path(directory), mode=args.mode)
    else:
        report, sbom = generate_release_packet(ROOT, args.state_dir, mode=args.mode)

    write_json_atomic(args.output_dir / "sbom.cdx.json", sbom)
    for gate in report["gates"]:
        write_json_atomic(args.output_dir / f"{gate['name']}.json", gate)
    write_json_atomic(args.output_dir / "release-decision.json", report)
    if report["decision"] != "GO":
        print(f"NO_GO: {', '.join(report['observedNoGoConditions'])}; evidence: {args.output_dir}")
        return 1
    print(f"GO: Profile H is testnet-ready; mainnet remains disabled; evidence: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
