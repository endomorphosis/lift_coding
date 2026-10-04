"""Replay six identity views and check declaration contract test evidence."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
DIRECTORY = CAMPAIGN / "representation-boundary-01"
PRIOR = CAMPAIGN / "statement-scope-01/validation.json"
PRIOR_SHA = "18716b2fd89ba5195b89f07a8fab70390e42cbc51916b11315a67649c1cc257b"
ASSAY = DIRECTORY / "assay.json"
ASSAY_SHA = "dbe89fd5fe8dbbc1a7ab1a751350b3d0804d6d2b9c8b4a6eb2a0aa81b20a412f"
NEW_FILES = (
    "ipfs_datasets_py/logic/formalization/autoencoder/alignment_lane_bundle.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/alignment_stage_declarations.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_lane_bundle.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_stage_declarations.py",
)
LEGACY_TESTS = (
    "tests/unit/logic/formalization/autoencoder/test_alignment_richer_embeddings.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_context_embeddings.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_checkpoint_representations.py",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def binding(path):
    path = Path(path)
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def load(path, expected_sha=None):
    if expected_sha is not None:
        require(binding(path)["sha256"] == expected_sha, "selected file changed: " + str(path))
    value = json.loads(Path(path).read_bytes())
    if "content_sha256" in value:
        require(value["content_sha256"] == digest({k: v for k, v in value.items() if k != "content_sha256"}),
                "content seal changed: " + str(path))
    return value


def main():
    prior = load(PRIOR, PRIOR_SHA)
    checked = {}

    def check(expected):
        require(binding(expected["path"]) == expected, "file binding changed: " + expected["path"])
        checked[expected["path"]] = expected

    for expected in prior["checked_file_bindings"]:
        check(expected)
    require(len(checked) == prior["checked_file_count"] == 89, "prior89 accounting differs")
    assay = load(ASSAY, ASSAY_SHA)
    require(assay["total_vector_count"] == 204 and assay["raw_vector_count"] == assay["derived_vector_count"] == 102,
            "saved204 accounting differs")
    require(assay["view_zero_mask_values"] == 30 and all(type(mask) is int and mask == 0 for mask in assay["masks"].values()),
            "saved view masks changed")
    require(all(assay[name] == 0 for name in ("model_calls", "encoder_calls", "prover_calls", "optimizer_updates", "labels_admitted")),
            "saved execution/admission counts changed")
    for expected in (*assay["input_file_bindings"].values(), assay["checkpoint_file_binding"],
                     *assay["code_bindings"], assay["expected_bindings_file"], assay["source_context_joins_file"]):
        check(expected)
    for outputs in assay["artifacts"].values():
        for expected in outputs.values():
            check(expected)
    pins = load(assay["expected_bindings_file"]["path"])
    joins = load(assay["source_context_joins_file"]["path"])
    # This helper guards optional imports and reads selected historical metadata.
    # It never parses checkpoint weights or writes any replay artifact.
    sys.path.insert(0, str(CAMPAIGN))
    import assay_lane_identity as runner

    prepared = runner.prepare_assay()
    require(raw(prepared["input_file_bindings"]) == raw(assay["input_file_bindings"])
            and prepared["checkpoint_file_binding"] == assay["checkpoint_file_binding"]
            and prepared["code_bindings"] == assay["code_bindings"], "historical source/code/checkpoint replay differs")
    require(raw(prepared["expected_bindings"]) == raw(pins["views"])
            and raw(prepared["source_context_joins"]) == raw(joins["rows"]), "external input/producer selection replay differs")
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.formalization.autoencoder import alignment_lane_bundle as lane
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_stage_declarations as stages,
    )

    vectors = 0
    for name, outputs in assay["artifacts"].items():
        bundle = load(outputs["bundle"]["path"])
        saved = load(outputs["validation"]["path"])
        require(raw(bundle) == raw(prepared["bundles"][name]), "view transcription replay differs")
        receipt = lane.validate_lane_bundle(bundle, expected_bindings=pins["views"][name])
        require(raw(receipt) == raw(saved), "saved identity receipt differs from exact replay")
        require(receipt["row_count"] == receipt["available_count"] == 34
                and receipt["unavailable_count"] == receipt["zero_ablation_count"] == 0, "view outcome accounting differs")
        require(all(receipt[flag] is False for flag in lane.FALSE), "identity receipt promoted authority")
        require(receipt["verification_status"] == receipt["admission_status"] == "pending"
                and all(type(mask) is int and mask == 0 for mask in receipt["masks"].values()), "identity admission/mask changed")
        vectors += len(bundle["rows"])
    require(vectors == 204, "vector replay count differs")
    require(all(callable(getattr(stages, name, None)) for name in (
        "validate_fit_declaration", "validate_rank_declaration", "validate_score_declaration")), "stage API missing")
    xml_path = DIRECTORY / "targeted-tests-final.xml"
    suite = ET.parse(xml_path).getroot().find("testsuite")
    require(suite is not None, "targeted suite evidence missing")
    counts = {key: int(suite.attrib[key]) for key in ("tests", "errors", "failures", "skipped")}
    require(counts["tests"] > 0 and counts["errors"] == counts["failures"] == counts["skipped"] == 0,
            "targeted test suite did not fully pass")
    test_groups = {}
    for relative in (*NEW_FILES[2:], *LEGACY_TESTS):
        tree = ast.parse((REPO / relative).read_text())
        names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
        test_groups[relative] = sum(case.attrib["name"].split("[", 1)[0] in names for case in suite.findall("testcase"))
    require(test_groups[NEW_FILES[2]] == 158, "new158 identity test evidence differs")
    require(all(count > 0 for count in test_groups.values()), "required suite not represented")
    ruff_path = DIRECTORY / "ruff-final.txt"
    require(ruff_path.read_text().strip() == "All checks passed!", "Ruff evidence failed")
    command_path = DIRECTORY / "test-command-final.json"
    command = load(command_path)
    require(command["targeted_exit_code"] == command["ruff_exit_code"] == 0, "recorded check exit codes differ")
    document = ROOT / "implementation_plan/docs/53-autoformalization-representation-and-stage-boundaries-2026-10-04.md"
    output = DIRECTORY / "validation.json"
    links = []
    for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", document.read_text()):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (document.parent / target.split("#", 1)[0]).resolve()
        require(path == output or path.is_file(), "document local link missing")
        links.append(str(path))
        if path != output:
            checked[str(path)] = binding(path)
    for path in [*(REPO / name for name in (*NEW_FILES, *LEGACY_TESTS)), Path(__file__),
                 CAMPAIGN / "assay_lane_identity.py", PRIOR, ASSAY, document, xml_path, ruff_path,
                 command_path, DIRECTORY / "targeted-tests-final.txt", DIRECTORY / "plan.json",
                 DIRECTORY / "targeted-tests.xml", DIRECTORY / "targeted-tests.txt",
                 DIRECTORY / "ruff.txt", DIRECTORY / "test-command.json"]:
        checked[str(path)] = binding(path)
    result = {
        "schema": "autoformalization-representation-boundary-validation/v1", "status": "passed_declared_boundaries_only",
        "created_utc": datetime.now(UTC).isoformat(), "checked_file_count": len(checked),
        "checked_file_bindings": sorted(checked.values(), key=lambda value: value["path"]),
        "prior_scope_generation_binding": binding(PRIOR), "prior89_file_bindings_rechecked": True,
        "previous554_file_chain_rechecked": False, "complete_dependency_manifest": False,
        "prior_existing_legacy_manifest_mismatch_preserved": prior["existing_legacy_failure"],
        "legacy_manifest_mismatch_retested_this_stage": False,
        "document_binding": binding(document), "local_link_count": len(links), "assay_binding": binding(ASSAY),
        "targeted_test_counts": counts, "tests_by_source_function_names": test_groups,
        "test_scope": "new lane and stage declarations plus unchanged raw/context/checkpoint representation contracts",
        "test_fixtures_semantic_gold": False, "ruff_checked_files": 6,
        "initial_ruff_import_format_failure_preserved": True, "final_ruff_passed": True,
        "representation_identity_declarations_implemented": True, "fit_rank_score_declarations_implemented": True,
        "isolated_numerical_stage_workers_implemented": False, "masked_contrastive_loss_implemented": False,
        "reference_file_inaccessibility_established": False, "ranking_file_durability_established": False,
        "producer_runtime_attestation_established": False, "semantic_label_admission_implemented": False,
        "view_count": 6, "raw_vectors_replayed": 102, "derived_vectors_replayed": 102,
        "total_vectors_preserved": vectors, "original_input_count": 34, "view_zero_mask_values": 30,
        "source_context_join_recipe_distinguished_from_authored_recipe": True,
        "checkpoint_weights_deserialized": False, "learned_projection_reexecuted": False,
        "historical_training_metadata_deserialized": True, "human_reviews_or_query_reference_panel_read": False,
        "existing_original_train_masks_unchanged": True, "broad_pilot_family_count": 40,
        "labels_admitted": 0, "formal_targets_admitted": 0, "model_calls": 0, "encoder_calls": 0,
        "prover_calls": 0, "optimizer_updates": 0, "source_fidelity_established": False, "proof_authority": False,
        "leanstral_runtime_qualified": False, "production_defaults_changed": False, "existing_decoder_checkpoints_modified": False,
        "renderer_preview_inspected": False,
        "seal_recipe": "SHA256 sorted compact UTF8 JSON excluding content_sha256; ensure_ascii=False; allow_nan=False",
    }
    result["content_sha256"] = digest(result)
    with output.open("xb") as stream:
        stream.write(raw(result) + b"\n")
    require(all(Path(path).is_file() for path in links), "final local link missing")
    print(raw({"validation_binding": binding(output), "checked_files": len(checked), "tests": counts,
               "vectors_preserved": vectors, "labels_admitted": 0}).decode())


if __name__ == "__main__":
    # Reset inherited launcher high-water RSS accounting for the assay's
    # fresh-worker resource check; this child performs only static validation.
    child = os.fork()
    if child == 0:
        main()
        sys.stdout.flush()
        os._exit(0)
    _, status = os.waitpid(child, 0)
    sys.exit(os.waitstatus_to_exitcode(status))
