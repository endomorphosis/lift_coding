#!/usr/bin/env python3
"""Intended NS-008 qualification residual provider.

Stdlib-only process invoked through ResidualProviderInvocation. Reads the
sealed prompt JSON from stdin, nominates a bounded edit, and writes a
body-free nomination JSON to stdout. This is not a production model identity
and does not claim write, semantic, or completion authority.
"""

from __future__ import annotations

import json
import os
import sys


PROVIDER_ID = "ns-008-qualification-residual-provider@1"
PROVIDER_REVISION = "ns-008-residual-provider-v1"
BUG = "return a - b"
FIX = "return a + b"


def main() -> int:
    raw = sys.stdin.read()
    try:
        surface = json.loads(raw)
    except json.JSONDecodeError:
        print(
            json.dumps(
                {
                    "provider_id": PROVIDER_ID,
                    "provider_revision": PROVIDER_REVISION,
                    "ok": False,
                    "reason_code": "malformed_sealed_prompt",
                }
            )
        )
        return 2

    packet_cid = (
        os.environ.get("IPFS_ACCELERATE_AGENT_TASK_PACKET_CID")
        or surface.get("packet_cid")
        or ""
    )
    mode = os.environ.get("IPFS_ACCELERATE_AGENT_TASK_PROVIDER_MODE", "nominate_add_fix")
    write_paths = list(surface.get("write_paths") or [])
    nomination: dict[str, object]
    if mode == "unknown_effect":
        nomination = {
            "path": "outside_lease/secret.toml",
            "replacement": "not-admitted",
            "reason_code": "unknown_provider_effect",
        }
    else:
        nomination = {
            "path": "pkg/core.py",
            "bug": BUG,
            "replacement_span": FIX,
            "reason_code": "nominated_add_fix",
        }
    payload = {
        "provider_id": PROVIDER_ID,
        "provider_revision": PROVIDER_REVISION,
        "admitted_production": False,
        "nomination_only": True,
        "semantic_authority": False,
        "write_authority": False,
        "completion_authority": False,
        "packet_cid": packet_cid,
        "task_id": surface.get("task_id"),
        "write_paths": write_paths,
        "nomination": nomination,
        "closes_claim": False,
    }
    json.dump(payload, sys.stdout, sort_keys=True, separators=(",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
