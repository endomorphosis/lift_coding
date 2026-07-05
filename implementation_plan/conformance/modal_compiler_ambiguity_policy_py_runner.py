#!/usr/bin/env python3
"""Python reference runner for modal compiler ambiguity policy helpers."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "external" / "ipfs_datasets"))

from ipfs_datasets_py.logic.modal import compiler


def _evaluate(predicted: str, target: str) -> Dict[str, Any]:
    return {
        "priorityTargets": list(compiler._priority_signal_free_adaptive_ambiguity_targets(predicted)),
        "requiredTargets": list(compiler._compiler_required_adaptive_ambiguity_targets(predicted)),
        "signalFreeTargets": list(compiler._signal_free_adaptive_ambiguity_targets(predicted)),
        "policyTargets": list(compiler._compiler_ambiguity_policy_targets(predicted)),
        "refinedMarginBuffer": compiler._compiler_refined_modal_family_cue_margin_buffer(predicted, target),
        "weakTypedSelfMarginBuffer": compiler._compiler_weak_typed_self_family_cue_margin_buffer(predicted, target),
        "isPrioritySignalFreePair": compiler._is_priority_signal_free_adaptive_ambiguity_pair(predicted, target),
        "isCompilerRequiredPair": compiler._is_compiler_required_adaptive_ambiguity_pair(predicted, target),
        "isCompilerAmbiguityPolicyPair": compiler._is_compiler_ambiguity_policy_pair(predicted, target),
        "isSignalFreeAdaptivePair": compiler._is_signal_free_adaptive_ambiguity_pair(predicted, target),
        "prefersContestedZeroMarginPair": compiler._prefers_contested_zero_margin_adaptive_ambiguity_pair(predicted, target),
        "supportsSignalFreeAdaptivePair": compiler._supports_signal_free_adaptive_ambiguity_pair(predicted, target),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vectors", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.vectors).read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []
    for vector in payload.get("vectors", []):
        rows.append(
            {
                "id": vector["id"],
                **_evaluate(
                    str(vector.get("predictedFamily") or ""),
                    str(vector.get("targetFamily") or ""),
                ),
            }
        )

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
