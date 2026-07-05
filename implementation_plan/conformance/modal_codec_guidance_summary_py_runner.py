#!/usr/bin/env python3
"""Python reference runner for modal codec guidance summary helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.modal import codec


def _evaluate(vector: Dict[str, Any]) -> Dict[str, Any]:
    guidance = vector.get("guidance") or {}
    summary = codec._compiler_guidance_summary(guidance)
    overlay_terms = codec._compiler_guidance_surface_overlay_terms(summary)
    source_text = str(vector.get("sourceText") or "")
    penalty = vector.get("sourceCopyPenalty") or {}
    return {
        "numericDistribution": codec._numeric_distribution(vector.get("numericDistribution")),
        "numericSignedMapping": codec._numeric_signed_mapping(vector.get("numericSignedMapping")),
        "guidanceSummary": summary,
        "featureStrings": codec._compiler_guidance_feature_strings(summary),
        "surfaceOverlayTerms": overlay_terms,
        "sourceGroundedSurfaceOverlayTerms": codec._source_grounded_guidance_surface_overlay_terms(
            overlay_terms,
            source_text=source_text,
        ),
        "appliedSurfaceOverlay": codec._apply_compiler_guidance_surface_overlay(
            str(vector.get("structuralDecodedText") or ""),
            overlay_terms,
            source_text=source_text,
        ),
        "sourceCopyRewardHackPenalty": codec._source_copy_reward_hack_penalty(
            source_span_copy_ratio=float(penalty.get("sourceSpanCopyRatio") or 0.0),
            text_reconstruction_similarity=float(penalty.get("textReconstructionSimilarity") or 0.0),
            structural_text_similarity=float(penalty.get("structuralTextSimilarity") or 0.0),
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.vectors).read_text(encoding="utf-8"))
    rows = [
        {"id": vector["id"], **_evaluate(vector)}
        for vector in payload.get("vectors", [])
    ]

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {"schemaVersion": payload.get("schemaVersion"), "results": rows},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
