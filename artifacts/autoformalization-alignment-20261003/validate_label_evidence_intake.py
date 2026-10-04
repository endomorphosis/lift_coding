"""Validate saved diagnostic intake, source pins and bounded test evidence."""
from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = Path(__file__).resolve().parent
DIRECTORY = CAMPAIGN / "label-evidence-intake-01"
PRIOR_SHA = "f5946e57f40af8ede75ad80a00773fd540dd8df2364cf7d484e7208a086b22f3"
PACKAGE_SHA = "6d5b4d084a44e291f89a373bb645b409db44f6eb0d7626d463a18a5f068f9130"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def binding(path):
    path = Path(path)
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def check_binding(expected):
    require(binding(expected["path"]) == expected, "file binding changed: " + expected["path"])


def load(path):
    value = json.loads(Path(path).read_bytes())
    if "content_sha256" in value:
        require(value["content_sha256"] == digest({k: v for k, v in value.items()
                                                   if k != "content_sha256"}), "content seal mismatch")
    return value


def main():
    prior_path = CAMPAIGN / "implementation-backlog-02/validation.json"
    require(binding(prior_path)["sha256"] == PRIOR_SHA, "prior planning generation changed")
    prior = load(prior_path)
    checked = {}
    for entry in (*prior["referenced_file_bindings"], prior["backlog_binding"], prior["main_plan_binding"]):
        check_binding(entry)
        checked[entry["path"]] = entry
    package_path = DIRECTORY / "empty_evidence_package.json"
    require(binding(package_path)["sha256"] == PACKAGE_SHA, "empty evidence input changed")
    package = load(package_path)
    require(package["items"] == [], "real intake must remain an empty readiness check")
    report_path = DIRECTORY / "intake/report_private.json"
    report = load(report_path)
    for entry in (*report["source_bindings"], report["packet_binding"], report["recording_report_binding"],
                  report["recording_receipt_binding"], report["package_binding"], report["intake_receipt_binding"]):
        check_binding(entry)
        checked[entry["path"]] = entry
    require(report["original_submission_bindings"] == [] and report["selected_process_binding"] is None
            and report["selected_metadata_file_bindings"] == {}, "readiness must not select or fabricate reviews")
    require(report["input_file_bindings_verified"] is True and report["recording_generation_replayed"] is True,
            "saved file workflow did not verify/replay the selected generation")
    require(report["complete_dependency_manifest"] is False, "partial dependency scope required")
    receipt = load(report["intake_receipt_binding"]["path"])
    require(receipt["item_count"] == 64 and receipt["declared_package_item_count"] == 0
            and receipt["status"] == "pending", "empty64 accounting differs")
    require(all(row["recording_status"] == "pending" and row["declared_evidence"] is None
                for row in receipt["items"]), "original pending items changed")
    require(sum(len(row["masks"]) for row in receipt["items"]) == 320, "mask count differs")
    for value in (report, receipt, *receipt["items"]):
        require(value["verification_status"] == value["admission_status"] == "pending", "admission promoted")
        require(all(type(mask) is int and mask == 0 for mask in value["masks"].values()), "mask promoted")
        for flag in ("qualified", "accepted", "source_fidelity_established", "proof_authority",
                     "reviewer_identity_authenticated", "reviewer_independence_authenticated", "semantic_gold_created",
                     "actual_training_or_evaluation_admission"):
            require(value[flag] is False, "authority promoted: " + flag)
    for value in (report, receipt):
        require(all(type(value[name]) is int and value[name] == 0 for name in (
            "human_reviews_authenticated", "independent_reviews_authenticated", "formal_targets_admitted",
            "model_calls", "provider_calls", "encoder_calls", "prover_calls")), "execution/review counts changed")
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir import canonical_label_evidence_intake as core

    packet = json.loads(Path(report["packet_binding"]["path"]).read_bytes())
    recorded = json.loads(Path(report["recording_receipt_binding"]["path"]).read_bytes())
    replay = core.validate_label_evidence_intake(packet, {"receipt": recorded, "reviewed_payloads": []},
        package, expected_bindings=report["expected_bindings"], selected_process_binding=None)
    require(raw(replay) == raw(receipt), "saved intake differs from exact dictionary replay")
    train = load(CAMPAIGN / "canonical-codec-01/train_weak_supervision.json")
    require(len(train["rows"]) == 16 and all(row["masks"] == prior["original_train_masks"]
                                             for row in train["rows"]), "original weak TRAIN masks changed")
    matrix = load(prior["family_planning_matrix_binding"]["path"])
    require(matrix["family_count"] == 40 and all(row["admitted_labels"] == 0 for row in matrix["rows"]),
            "broad family planning/admission changed")
    xml_path = DIRECTORY / "targeted-tests.xml"
    suite = ET.parse(xml_path).getroot().find("testsuite")
    require(suite is not None, "test suite evidence unavailable")
    test_counts = {key: int(suite.attrib[key]) for key in ("tests", "errors", "failures", "skipped")}
    require(test_counts["tests"] > 0 and test_counts["errors"] == test_counts["failures"] == 0,
            "targeted test evidence contains failures/errors")
    ruff_path = DIRECTORY / "ruff.txt"
    require(ruff_path.read_text().strip() == "All checks passed!", "Ruff evidence did not pass")
    document = ROOT / "implementation_plan/docs/51-autoformalization-review-evidence-intake-2026-10-04.md"
    validation_path = DIRECTORY / "validation.json"
    link_checks = []
    for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", document.read_text()):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (document.parent / target.split("#", 1)[0]).resolve()
        require(path == validation_path or path.is_file(), "missing local document link")
        link_checks.append(str(path))
        if path != validation_path:
            checked[str(path)] = binding(path)
    for path in (Path(__file__), prior_path, package_path, report_path, xml_path, ruff_path, document,
                 DIRECTORY / "targeted-tests.txt", DIRECTORY / "cli-result.txt",
                 REPO / "tests/unit/logic/legal_ir/test_canonical_label_evidence_intake.py",
                 REPO / "tests/unit/logic/legal_ir/test_canonical_label_evidence_intake_workflow.py"):
        checked[str(path)] = binding(path)
    result = {
        "schema": "autoformalization-label-evidence-intake-validation/v1", "status": "passed_diagnostic_intake_only",
        "created_utc": datetime.now(UTC).isoformat(), "checked_file_bindings": sorted(checked.values(), key=lambda b: b["path"]),
        "checked_file_count": len(checked), "document_binding": binding(document), "local_link_count": len(link_checks),
        "prior_planning_generation_binding": binding(prior_path), "prior48_referenced_files_rechecked": True,
        "previous554_file_chain_rechecked": False, "complete_dependency_manifest": False,
        "intake_report_binding": binding(report_path), "targeted_test_counts": test_counts,
        "test_scope": "new core/workflow/CLI plus unchanged recorder core/workflow; synthetic test declarations",
        "ruff_checked_files": 5, "diagnostic_intake_implemented": True, "semantic_label_admission_implemented": False,
        "annotation_schema_scope": "existing canonical normative packet only", "all40_annotation_schemas_implemented": False,
        "broad_pilot_family_count": 40, "original_packet_items": 64, "zero_mask_values": 320,
        "original_weak_train_rows": 16, "original_train_masks_unchanged": True, "actual_evidence_package_items": 0,
        "selected_human_review_process": None, "actual_review_submissions_created": 0, "labels_admitted": 0,
        "formal_targets_admitted": 0, "optimizer_updates": 0, "model_calls": 0, "prover_calls": 0,
        "source_fidelity_established": False, "proof_authority": False, "production_defaults_changed": False,
        "existing_decoder_checkpoints_modified": False, "renderer_preview_inspected": False,
        "seal_recipe": "SHA256 sorted compact UTF8 JSON excluding content_sha256; ensure_ascii=False; allow_nan=False",
    }
    result["content_sha256"] = digest(result)
    with validation_path.open("xb") as stream:
        stream.write(raw(result) + b"\n")
    require(all(Path(path).is_file() for path in link_checks), "final document link missing")
    print(json.dumps({"validation": binding(validation_path), "checked_files": len(checked),
                      "tests": test_counts, "items_pending": 64, "zero_mask_values": 320,
                      "labels_admitted": 0}, sort_keys=True))


if __name__ == "__main__":
    main()
