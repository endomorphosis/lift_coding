#!/usr/bin/env python3
"""Run XPH-109's fail-closed three-seller Profile H interoperability gate."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / "src", ROOT / "external/ipfs_kit", ROOT / "external/ipfs_datasets",
             ROOT / "external/ipfs_accelerate"):
    sys.path.insert(0, str(path))

from mcplusplus_profile_h.interop import (  # noqa: E402
    MockFacilitator, TestnetFacilitator, load_testnet_payload_from_env, run_interop,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="machine-readable evidence path")
    parser.add_argument("--mode", choices=("mock", "testnet"), default="mock")
    parser.add_argument("--facilitator-url", help="HTTPS x402 facilitator base URL (testnet mode)")
    parser.add_argument("--state-dir", type=Path, help="retain non-secret harness state for diagnosis")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "testnet":
        if not args.facilitator_url:
            raise SystemExit("--facilitator-url is required in testnet mode")
        facilitator = TestnetFacilitator(args.facilitator_url)
        payload = load_testnet_payload_from_env()
    else:
        facilitator, payload = MockFacilitator(), None
    with tempfile.TemporaryDirectory(prefix="xph-109-state-") if args.state_dir is None else _nullcontext(args.state_dir) as directory:
        report = asyncio.run(run_interop(state_dir=Path(directory), facilitator=facilitator,
                                         supplied_payload=payload))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(args.output)
    print(f"PASS: SwissKnife paid 3 sellers over HTTP and libp2p; evidence: {args.output}")
    return 0


class _nullcontext:
    def __init__(self, value: Path) -> None:
        self.value = value
    def __enter__(self) -> Path:
        self.value.mkdir(parents=True, exist_ok=True)
        return self.value
    def __exit__(self, *_args: object) -> None:
        return None


if __name__ == "__main__":
    raise SystemExit(main())

