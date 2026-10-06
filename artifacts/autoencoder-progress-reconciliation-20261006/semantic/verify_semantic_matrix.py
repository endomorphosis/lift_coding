#!/usr/bin/env python3
"""Recheck pinned ordinary evidence and recompute scoped scalar observations.

No producing model/backend implementation is imported or replayed. Missing or
changed evidence is reported and refuses the retained matrix's currentness.
"""
import argparse
import hashlib
import json
from pathlib import Path


def observed(path):
    if not path.is_file():
        return {"path": str(path), "exists": False, "bytes": None, "sha256": None}
    raw = path.read_bytes()
    return {"path": str(path), "exists": True, "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest()}


def metrics(sources):
    def read(identity):
        return json.loads(Path(sources[identity]["path"]).read_bytes())
    contextual = read("contextual-evaluation")
    normative = read("normative-results")
    margins = read("modality-margins-results")
    expansion = read("source-only-expansion")
    joint = read("joint-condition-control")
    registration = read("original-modelmanager-registration")
    mirrors = read("original-dimension-mirrors")
    return {
        "original_contextual": [{"dimension": lane["dimension"],
            "reference_rows": lane["ir_metrics"]["rows"],
            "ordered_ir_exact": lane["ir_metrics"]["ordered_exact"],
            "canonical_ir_exact": lane["canonical_contract_exact"],
            "expected_rules": lane["ir_metrics"]["expected_rules"],
            "utf8_text_exact": lane["original_text_metrics"]["verbatim_utf8_exact"],
            "nfc_whitespace_text_exact": lane["original_text_metrics"]["nfc_whitespace_exact"],
            "all_reference_qualifiers_empty": lane["reference_qualifier_fields_all_empty"]}
            for lane in contextual["lanes"]],
        "exposed_v3_modality": [{"dimension": panel["dimension"], "arm": panel["arm"],
            "rows": panel["sample_count"], "exact": panel["exact_paragraphs"],
            "source_modality_correct": panel["per_field"]["modality"]["source_correct"],
            "combined_modality_correct": panel["per_field"]["modality"]["combined_correct"],
            "modality_sites": panel["per_field"]["modality"]["scored"]}
            for panel in margins["panels"]],
        "prospective_wording_selected": [{"dimension": panel["dimension"], "arm": panel["arm"],
            "rows": panel["sample_count"], "exact": panel["ordered_exact"],
            "token_ce": panel["token_cross_entropy"],
            "selected_last_same_tensor": panel["selected_last_identical_tensor_alias"]}
            for panel in normative["panels"] if panel["role"] == "selected"],
        "normative_execution": {key: normative[key] for key in (
            "local_native_encoders_executed", "native_source_vectors_per_width", "training_executed",
            "fresh_holdout", "checkpoint_promoted", "lake_executed", "logic_family_projections_executed")},
        "source_only64": {key: expansion[key] for key in (
            "source_rows", "train_rows", "development_rows", "selected_optimizer_updates",
            "actual_optimizer_updates", "new_selected_models", "masks")},
        "joint_conditioning64": {key: joint[key] for key in (
            "original_source_count", "unique_policy_model_forwards", "policy_outcomes", "semantic_masks",
            "accepted", "source_fidelity_established", "independent_semantic_review_completed")},
        "retained_original_registration": {key: registration[key] for key in (
            "before_count", "after_count", "new_checkpoint_count", "runtime_ready", "teacher_qualified",
            "proof_authority", "current_external_service_process_refreshed")},
        "retained_original_dimension_publication": {key: mirrors[key] for key in (
            "new_release_files", "new_repository_count", "original_model_manager_records_rewritten",
            "runtime_admitted", "models_changed_or_retrained")},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("fresh verification output required")
    matrix = json.loads(args.matrix.read_bytes())
    sources = matrix["sources"]
    observations = {identity: observed(Path(record["path"])) for identity, record in sources.items()}
    changed = [identity for identity, expected in sources.items()
               if observations[identity] != {key: expected[key] for key in ("path", "exists", "bytes", "sha256")}]
    new_metrics = None if changed else metrics(sources)
    agreed = new_metrics == matrix["recomputed_metric_panels"]
    result = {"schema": "autoencoder-semantic-matrix-ordinary-verification/v1",
        "matrix_pin": observed(args.matrix), "changed_source_ids": changed,
        "all_pinned_evidence_current": not changed, "scoped_metric_panels_recomputed_equal": agreed,
        "prior_entry_count": len(matrix["inherited_prior_entries"]),
        "new_contribution_count": len(matrix["new_contributions"]),
        "model_loaded": False, "model_inference_executed": False, "training_executed": False,
        "encoder_executed": False, "database_or_network_executed": False, "proof_authority": False,
        "scope": "Ordinary-byte and scalar-report consistency; no execution-origin attestation, production admission or exhaustive Git effective-tree review."}
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(observed(args.output)))
    raise SystemExit(0 if not changed and agreed else 2)


if __name__ == "__main__":
    main()
