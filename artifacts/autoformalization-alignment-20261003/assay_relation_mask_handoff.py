"""Replay actual unavailable TRAIN review handoff without numerical work."""
from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

import assay_relation_readiness as io

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
OUTPUT = CAMPAIGN / "relation-mask-handoff-01"
PRIOR = CAMPAIGN / "masked-contrastive-01/validation.json"
PRIOR_SHA = "19de9aeffbc623ded1bebe8b32579e000129e238bdcc677d4f41bae67617fbf9"
DECLARATION = CAMPAIGN / "masked-contrastive-01/relations/declaration.json"
DECLARATION_SHA = "9983c2550d194a866853eb30601cb67461f711c35aa9f2599830c006ff442468"
DECLARATION_PINS = CAMPAIGN / "masked-contrastive-01/relations/expected_bindings.json"
DECLARATION_PINS_SHA = "c94b64516295031d70f8a617bf853992a4d6e18182440bdc5f5bc99d5ca0eba7"


def prepare_assay():
    """Construct only the current unavailable snapshot; create no review claims."""
    io.owners()
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_relation_mask_handoff as handoff,
    )

    io.require(Path(handoff.__file__).resolve() == REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_relation_mask_handoff.py",
               "canonical handoff owner required")
    prior, prior_binding = io.read(PRIOR, PRIOR_SHA)
    declaration, declaration_binding = io.read(DECLARATION, DECLARATION_SHA)
    pins, pins_binding = io.read(DECLARATION_PINS, DECLARATION_PINS_SHA)
    io.require(prior["checked_file_count"] == 224 and prior["labels_admitted"] == 0
               and prior["authenticated_relation_to_tensor_handoff_implemented"] is False,
               "preceding unadmitted generation differs")
    prepared = handoff.prepare_unavailable_relation_handoff(declaration, expected_declaration_bindings=pins)
    source_paths = [Path(__file__), Path(io.__file__), Path(handoff.__file__),
                    *(REPO / "ipfs_datasets_py/logic/formalization/autoencoder" / filename for filename in
                      ("alignment_lane_bundle.py", "alignment_stage_declarations.py", "alignment_relation_declarations.py"))]
    return {**prepared, "input_file_bindings": [prior_binding, declaration_binding, pins_binding],
            "source_bindings": [io.read(path, parse=False)[1] for path in source_paths]}


def main():
    prepared = prepare_assay()
    io.require(not OUTPUT.exists(), "fresh handoff preflight generation required")
    for selected in (*prepared["input_file_bindings"], *prepared["source_bindings"]):
        io.require(io.read(selected["path"], selected["sha256"], parse=False)[1] == selected, "selected preflight input changed")
    OUTPUT.mkdir(mode=0o700)
    artifacts = {name: io.save(OUTPUT, name + ".json", prepared[name])
                 for name in ("snapshot", "policy", "expected_bindings", "validation")}
    report = io.seal({
        "schema": "alignment-relation-mask-handoff-assay/v1", "created_utc": datetime.now(UTC).isoformat(),
        "status": "completed_unavailable_review_preflight_only",
        "input_file_bindings": prepared["input_file_bindings"], "source_bindings": prepared["source_bindings"],
        "artifacts": artifacts, "train_row_count": 16, "ordered_pair_count": 256,
        "objective_positive_pair_count": 0, "objective_permitted_negative_pair_count": 0,
        "admitted_positive_pair_count": 0, "admitted_permitted_negative_pair_count": 0,
        "actual_fit_authorized": False, "actual_review_process_selected": False,
        "authentic_review_packages_accessed": False, "human_reviews_authenticated": 0,
        "synthetic_fixture_snapshot_used_for_actual_train": False,
        "train_formal_payload_read": False, "query_reference_panel_accessed": False,
        "torch_imported": "torch" in sys.modules, "model_calls": 0, "encoder_calls": 0,
        "prover_calls": 0, "optimizer_updates": 0, "semantic_labels_admitted": 0,
        "source_fidelity_established": False, "proof_authority": False, "accepted": False, "qualified": False,
        "original_train_masks_modified": False, "old_objectives_or_checkpoints_modified": False,
        "authenticated_admission_adapter_implemented": False,
        "masks": dict.fromkeys(prepared["validation"]["masks"], 0),
        "dependency_binding_scope": "six_explicit_stdlib_owners_not_complete_dependency_closure",
    })
    io.require(report["torch_imported"] is False, "optional numerical stack entered unavailable preflight")
    for selected in (*prepared["input_file_bindings"], *prepared["source_bindings"], *artifacts.values()):
        io.require(io.read(selected["path"], selected["sha256"], parse=False)[1] == selected, "preflight input or artifact changed")
    report_binding = io.save(OUTPUT, "assay.json", report)
    for directory in (OUTPUT, OUTPUT.parent):
        descriptor = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    print(json.dumps({"assay_binding": report_binding, "ordered_pairs": 256, "admitted_pairs": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
