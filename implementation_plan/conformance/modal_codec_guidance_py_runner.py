#!/usr/bin/env python3
"""Python reference runner for modal codec compiler-guidance helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.modal import codec


def _evaluate(guidance: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "routeFeatures": codec._compiler_guidance_route_features(guidance),
        "viewGapFeatures": codec._compiler_guidance_view_gap_features(guidance),
        "neo4jProjectionTarget": codec._compiler_guidance_implies_neo4j_projection_target(guidance),
        "frameLogicTargetRoutes": sorted(codec._compiler_guidance_frame_logic_target_routes(guidance)),
        "frameLogicTarget": codec._compiler_guidance_implies_frame_logic_target(guidance),
        "frameAuditFeatures": codec._compiler_guidance_frame_audit_features(guidance),
        "featureStrings": codec._compiler_guidance_feature_strings(guidance),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    vectors_path = Path(args.vectors)
    out_path = Path(args.out)

    payload = json.loads(vectors_path.read_text(encoding="utf-8"))
    rows = []
    for vector in payload.get("vectors", []):
        rows.append({"id": vector["id"], **_evaluate(vector.get("guidance", {}))})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps({"schemaVersion": payload.get("schemaVersion"), "results": rows}, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
