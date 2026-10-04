"""Reconcile unavailable-review handoff and its engineering-only test evidence."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import stat
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

import assay_relation_mask_handoff as assay

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
DIRECTORY = CAMPAIGN / "relation-mask-handoff-01"
DOCUMENT = ROOT / "implementation_plan/docs/56-autoformalization-relation-mask-handoff-2026-10-04.md"
SOURCES = (
    "tests/unit/logic/formalization/autoencoder/test_alignment_relation_mask_handoff.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_relation_declarations.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_lane_bundle.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_stage_declarations.py",
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def binding(path):
    data = Path(path).read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def bindings(value):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            yield value
        else:
            for item in value.values():
                yield from bindings(item)
    elif type(value) is list:
        for item in value:
            yield from bindings(item)


def main():
    require(len(sys.argv) == 2 and re.fullmatch(r"[0-9a-f]{64}", sys.argv[1]), "explicit saved assay file SHA required")
    prior, prior_binding = assay.io.read(assay.PRIOR, assay.PRIOR_SHA)
    checked = {}

    def check(expected):
        require(binding(expected["path"]) == expected, "bound file changed: " + expected["path"])
        checked[expected["path"]] = expected

    for selected in prior["checked_file_bindings"]:
        check(selected)
    require(len(checked) == prior["checked_file_count"] == 224, "preceding224 accounting differs")
    check(prior_binding)
    report, report_binding = assay.io.read(DIRECTORY / "assay.json", sys.argv[1])
    check(report_binding)
    for selected in bindings(report):
        check(selected)
    prepared = assay.prepare_assay()
    saved = {}
    for name in ("snapshot", "policy", "expected_bindings", "validation"):
        saved[name], selected = assay.io.read(report["artifacts"][name]["path"], report["artifacts"][name]["sha256"])
        check(selected)
        require(raw(saved[name]) == raw(prepared[name]), "complete unavailable handoff replay differs: " + name)
    require(report["input_file_bindings"] == prepared["input_file_bindings"]
            and report["source_bindings"] == prepared["source_bindings"], "preflight source selections differ")
    receipt = saved["validation"]
    for name in ("objective_positive_mask", "objective_permitted_negative_mask", "admitted_positive_mask", "admitted_permitted_negative_mask"):
        matrix = receipt[name]
        require(type(matrix) is list and len(matrix) == 16 and all(type(row) is list and len(row) == 16 for row in matrix)
                and all(cell is False for row in matrix for cell in row), "actual handoff enabled a pair or dropped an anchor")
    require(receipt["actual_fit_authorized"] is False, "real fitting authorized by preflight")
    masks = {"weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation"}
    for value in (receipt, report):
        require(type(value["masks"]) is dict and set(value["masks"]) == masks
                and all(type(mask) is int and mask == 0 for mask in value["masks"].values()), "supervision promoted")
    require(report["ordered_pair_count"] == 256 and report["train_row_count"] == 16
            and report["human_reviews_authenticated"] == report["semantic_labels_admitted"] == report["optimizer_updates"] == 0
            and report["torch_imported"] is False, "actual preflight activity differs")
    suite = ET.parse(DIRECTORY / "tests.xml").getroot().find("testsuite")
    require(suite is not None, "targeted JUnit suite missing")
    counts = {name: int(suite.attrib[name]) for name in ("tests", "errors", "failures", "skipped")}
    require(counts["tests"] > 276 and counts["errors"] == counts["failures"] == counts["skipped"] == 0, "targeted tests failed")
    symbols, source_counts = {}, {}
    for relative in SOURCES:
        tree = ast.parse((REPO / relative).read_text())
        names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
        require(names, "test source has no top-level test functions")
        for name in names:
            require(name not in symbols, "ambiguous selected test function")
            symbols[name] = relative
        source_counts[relative] = sum(case.attrib["name"].split("[", 1)[0] in names for case in suite.findall("testcase"))
        require(source_counts[relative] > 0, "selected source test cases missing")
        check(binding(REPO / relative))
    require(sum(source_counts.values()) == counts["tests"], "test source attribution differs")
    command, _ = assay.io.read(DIRECTORY / "test-command.json")
    require(command["exit_code"] == 0, "targeted test command failed")
    lint, _ = assay.io.read(DIRECTORY / "ruff-02-command.json")
    require(lint["exit_code"] == 0 and len(lint["files"]) == 4
            and (DIRECTORY / "ruff-02.txt").read_text().strip() == "All checks passed!", "new code lint failed")
    for selected in lint["checked_source_bindings"]:
        check(selected)
    output = DIRECTORY / "verification.json"
    links = []
    for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", DOCUMENT.read_text()):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (DOCUMENT.parent / target.split("#", 1)[0]).resolve()
        require(path == output or path.is_file(), "local documentation link missing: " + str(path))
        links.append(str(path))
        if path != output:
            check(binding(path))
    for path in (DOCUMENT, Path(__file__), DIRECTORY / "tests.xml", DIRECTORY / "tests.txt",
                 DIRECTORY / "test-command.json", DIRECTORY / "ruff-command.json", DIRECTORY / "ruff.txt",
                 DIRECTORY / "ruff-02-command.json", DIRECTORY / "ruff-02.txt"):
        check(binding(path))
    for path in DIRECTORY.iterdir():
        require(path.is_file() and not path.is_symlink() and stat.S_IMODE(path.stat().st_mode) == 0o600,
                "private regular preflight artifact required")
    require(stat.S_IMODE(DIRECTORY.stat().st_mode) == 0o700, "private preflight directory required")
    result = {
        "schema": "autoformalization-relation-mask-handoff-validation/v1",
        "status": "passed_unavailable_review_preflight_and_synthetic_structure_only",
        "prepublication_verifier_corrections": ["overall_verification_filename_separated_from_existing_compiler_validation_receipt"],
        "created_utc": datetime.now(UTC).isoformat(), "checked_file_count": len(checked),
        "checked_file_bindings": sorted(checked.values(), key=lambda selected: selected["path"]),
        "prior_masked_generation_binding": prior_binding, "prior224_file_bindings_rechecked": True,
        "older554_file_chain_rechecked": False, "complete_dependency_manifest": False,
        "assay_binding": report_binding, "document_binding": binding(DOCUMENT), "local_link_count": len(links),
        "targeted_test_counts": counts, "test_counts_by_source_function_names": source_counts,
        "new_handoff_test_count": source_counts[SOURCES[0]], "final_ruff_passed": True, "ruff_checked_files": 4,
        "saved_unavailable_handoff_exact_replay": True, "ordered_train_rows": 16, "ordered_pairs": 256,
        "objective_true_cells": 0, "admitted_true_cells": 0, "objective_unknown_pairs": 256,
        "actual_fit_authorized": False, "authenticated_review_process_selected": False,
        "human_reviews_authenticated": 0, "semantic_labels_admitted": 0,
        "authenticated_admission_adapter_implemented": False, "torch_imported": False,
        "numerical_objectives_executed": 0, "encoder_calls": 0, "model_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
        "masks": dict.fromkeys(sorted(masks), 0), "existing_train_masks_modified": False,
        "existing_losses_or_checkpoints_modified": False, "production_defaults_changed": False,
        "source_fidelity_established": False, "proof_authority": False, "qualified": False,
        "test_fixtures_semantic_gold": False, "actual_train_uses_synthetic_review_assertions": False,
        "semantic_profiles_separate_from_representation_profiles": True, "family_coercion_executed": False,
        "broad_pilot_family_count": 40, "broad_pilot_semantic_evaluation_executed": False,
        "prior_existing_legacy_manifest_mismatch_preserved": prior["prior_existing_legacy_manifest_mismatch_preserved"],
        "legacy_manifest_mismatch_retested_this_stage": False,
        "prior_standalone_numerical_launcher_ordering_limitation_preserved": True,
        "standalone_numerical_launcher_qualified": False, "os_reference_confinement_established": False,
        "derivative_exclusion_authenticated": False, "renderer_preview_inspected": False,
    }
    for selected in checked.values():
        check(selected)
    selected = assay.io.save(DIRECTORY, "verification.json", assay.io.seal(result))
    descriptor = os.open(DIRECTORY, os.O_RDONLY | os.O_DIRECTORY)
    os.fsync(descriptor)
    os.close(descriptor)
    print(json.dumps({"validation_binding": selected, "checked_files": len(checked), "targeted_tests": counts["tests"],
                      "new_tests": source_counts[SOURCES[0]], "actual_train_pairs": 256, "admitted_pairs": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
