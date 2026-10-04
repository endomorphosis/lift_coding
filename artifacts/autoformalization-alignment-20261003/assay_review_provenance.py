"""Replay unavailable review-provenance inputs without creating keys or reviews."""
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
OUTPUT = CAMPAIGN / "review-provenance-01"
PRIOR = CAMPAIGN / "relation-mask-handoff-01/verification.json"
PRIOR_SHA = "e127039aa2e7d84fba5890b7e9f7a2c600d9ba06466ca5033fcec89e92af2e00"
DECLARATION = CAMPAIGN / "masked-contrastive-01/relations/declaration.json"
DECLARATION_SHA = "9983c2550d194a866853eb30601cb67461f711c35aa9f2599830c006ff442468"
DECLARATION_PINS = CAMPAIGN / "masked-contrastive-01/relations/expected_bindings.json"
DECLARATION_PINS_SHA = "c94b64516295031d70f8a617bf853992a4d6e18182440bdc5f5bc99d5ca0eba7"
HANDOFF_FILES = {
    "snapshot": ("snapshot.json", "f1cb36f8a7a1f2bd1fd4964e3f5ae4218bae7a2ead864bf2449d3fbba477af6c"),
    "policy": ("policy.json", "7d0d82f4b4299fa5041d1c9849eeff18717fd4608cb007eaafa28f0bbbdca91d"),
    "receipt": ("validation.json", "65554adc2b5f4066b3efba26429d8219ca88eeb4f91f200d12e66e8b73d632c2"),
    "expected_bindings": ("expected_bindings.json", "92f2c443cdc10b4bf849aa9d52caf6e6022dc564894f2075768b6a85226671ff"),
}


def prepare_assay():
    """Keep actual TRAIN proof/review/fit authority unavailable, without crypto."""
    io.owners()
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_review_provenance as owner,
    )

    io.require(Path(owner.__file__).resolve() == REPO / "ipfs_datasets_py/logic/formalization/autoencoder/alignment_review_provenance.py",
               "canonical review provenance owner required")
    prior, prior_binding = io.read(PRIOR, PRIOR_SHA)
    declaration, declaration_binding = io.read(DECLARATION, DECLARATION_SHA)
    pins, pins_binding = io.read(DECLARATION_PINS, DECLARATION_PINS_SHA)
    selected = [prior_binding, declaration_binding, pins_binding]
    handoff = {}
    for role, (filename, sha) in HANDOFF_FILES.items():
        handoff[role], observed = io.read(CAMPAIGN / "relation-mask-handoff-01" / filename, sha)
        selected.append(observed)
    handoff_pins = handoff.pop("expected_bindings")
    io.require(prior["checked_file_count"] == 245 and prior["human_reviews_authenticated"] == 0
               and prior["actual_fit_authorized"] is False, "preceding245 unavailable review state differs")
    prepared = owner.prepare_unavailable_review_provenance(declaration, handoff,
        expected_declaration_bindings=pins, expected_handoff_bindings=handoff_pins)
    paths = [Path(__file__), Path(io.__file__), Path(owner.__file__),
             *(REPO / "ipfs_datasets_py/logic/formalization/autoencoder" / filename for filename in
               ("alignment_lane_bundle.py", "alignment_stage_declarations.py", "alignment_relation_declarations.py",
                "alignment_relation_mask_handoff.py"))]
    io.require(not {"torch", "cryptography"}.intersection(sys.modules), "optional numerical/crypto stack entered unavailable preflight")
    return {**prepared, "input_file_bindings": selected,
            "source_bindings": [io.read(path, parse=False)[1] for path in paths]}


def main():
    prepared = prepare_assay()
    io.require(not OUTPUT.exists(), "fresh review-provenance generation required")
    for selected in (*prepared["input_file_bindings"], *prepared["source_bindings"]):
        io.require(io.read(selected["path"], selected["sha256"], parse=False)[1] == selected, "selected unavailable input changed")
    OUTPUT.mkdir(mode=0o700)
    directory = OUTPUT / "unavailable"
    directory.mkdir(mode=0o700)
    artifacts = {name: io.save(directory, name + ".json", prepared[name])
                 for name in ("registry", "policy", "attestations", "expected_bindings", "verification")}
    report = io.seal({
        "schema": "alignment-review-provenance-unavailable-assay/v1", "created_utc": datetime.now(UTC).isoformat(),
        "status": "completed_unavailable_registry_preflight_only",
        "input_file_bindings": prepared["input_file_bindings"], "source_bindings": prepared["source_bindings"],
        "artifacts": artifacts, "train_row_count": 16, "ordered_pair_count": 256,
        "actual_registry_selected": False, "actual_review_process_selected": False,
        "authentic_review_packages_accessed": False, "human_reviews_authenticated": 0,
        "attestations_submitted": 0, "signature_verification_calls": 0, "keys_initialized": 0,
        "cryptography_imported": "cryptography" in sys.modules, "torch_imported": "torch" in sys.modules,
        "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
        "semantic_labels_admitted": 0, "admitted_positive_pair_count": 0, "admitted_negative_pair_count": 0,
        "actual_fit_authorized": False, "source_fidelity_established": False, "proof_authority": False,
        "accepted": False, "qualified": False, "formal_target_body_read": False, "query_reference_panel_accessed": False,
        "original_train_masks_modified": False, "existing_losses_or_checkpoints_modified": False,
        "masks": dict.fromkeys(prepared["verification"]["masks"], 0),
        "dependency_binding_scope": "seven_explicit_stdlib_owners_not_complete_dependency_closure",
    })
    for selected in (*prepared["input_file_bindings"], *prepared["source_bindings"], *artifacts.values()):
        io.require(io.read(selected["path"], selected["sha256"], parse=False)[1] == selected, "unavailable publication input changed")
    saved = io.save(directory, "assay.json", report)
    for path in (directory, OUTPUT, OUTPUT.parent):
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        os.fsync(descriptor)
        os.close(descriptor)
    print(json.dumps({"assay_binding": saved, "ordered_pairs": 256, "attestations": 0, "admitted_pairs": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
