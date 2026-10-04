"""Check saved scope declarations, prior pins and targeted test evidence."""
from __future__ import annotations

import ast
import re
import sys
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

from assay_statement_scope import (
    CAMPAIGN,
    DIRECTORY,
    GENERATION,
    GENERATION_SHA,
    PACKET,
    PACKET_SHA,
    REPO,
    REQUESTS,
    REQUESTS_SHA,
    ROOT,
    binding,
    candidate_declaration,
    digest,
    load_pinned,
    raw,
    require,
)

PRIOR = CAMPAIGN / "label-evidence-intake-01/validation.json"
PRIOR_SHA = "93af71fc0495e7da02533e787588284dd4490c87fe39964c06b427623b231264"
ASSAY = DIRECTORY / "saved-candidate-assay.json"
ASSAY_SHA = "68738c04be7af08bc154c6cac6ecd0a5641697b2ddb5da0d33e44cb30df55679"


def main():
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir.canonical_byte_codec import validate_proposal
    from ipfs_datasets_py.logic.legal_ir.canonical_contracts import BridgeView
    from ipfs_datasets_py.logic.legal_ir.canonical_statement_scope import (
        assess_flat_profile_compatibility,
        validate_scope_declaration,
    )
    from ipfs_datasets_py.logic.legal_ir.canonical_statement_scope_bridge import (
        prepare_scope_bridge_view,
        validate_scope_bridge_view,
    )

    prior = load_pinned(PRIOR, PRIOR_SHA)
    checked = {}
    for expected in prior["checked_file_bindings"]:
        require(binding(Path(expected["path"])) == expected, "prior intake file binding changed")
        checked[expected["path"]] = expected
    require(len(checked) == prior["checked_file_count"] == 70, "prior70 accounting differs")
    assay = load_pinned(ASSAY, ASSAY_SHA)
    generation = load_pinned(GENERATION, GENERATION_SHA)
    requests = load_pinned(REQUESTS, REQUESTS_SHA)
    packet = load_pinned(PACKET, PACKET_SHA)
    for expected in assay["input_bindings"]:
        require(binding(Path(expected["path"])) == expected, "assay input binding changed")
        checked[expected["path"]] = expected
    require(len(assay["rows"]) == len(generation["rows"]) == len(requests["rows"]) == 34,
            "saved34 accounting differs")
    require(len(packet["items"]) == 64 and assay["current64_exact_input_joins"] == 0,
            "current64 accounting differs")
    require(all(all(value is None for value in row["annotation"].values()) for row in packet["items"]),
            "current64 annotations changed")
    packet_inputs = {item["input_sha256"] for item in packet["items"]}
    replays = 0
    for row, saved in zip(assay["rows"], generation["rows"], strict=True):
        require(row["position"] == saved["position"] and row["saved_id"] == saved["id"]
                and row["saved_outcome"] == saved["outcome"], "saved row identity/order differs")
        original = requests["rows"][saved["position"]]
        require(original["id"] == saved["id"], "original request identity differs")
        if saved.get("proposal") is None:
            require(row["declaration"] is row["validation_summary"] is row["flat_assessment"]
                    is row["bridge_view"] is row["scope_payload_roundtrip_exact"] is None,
                    "absent candidate gained invented scope data")
            continue
        request = row["declaration"]["input"]
        role = "declared_context" if original["context_text"] else "required_unavailable" if original["requires_context_resolution"] else "none_required"
        require(request["source_text"] == original["source_text"] and request["context"]["text"] == original["context_text"]
                and request["context"]["role"] == role, "declaration original request input differs")
        require(digest(request) not in packet_inputs, "old request gained current64 join")
        proposal = validate_proposal(saved["proposal"], request["source_text"])
        declaration = candidate_declaration(proposal, request)
        require(raw(row["declaration"]) == raw(declaration), "candidate declaration replay differs")
        validation = validate_scope_declaration(request, declaration, expected_input_sha256=digest(request))
        require(raw({k: v for k, v in validation.items() if k != "declaration"}) == raw(row["validation_summary"]),
                "validation summary replay differs")
        assessment = assess_flat_profile_compatibility(declaration)
        require(raw(assessment) == raw(row["flat_assessment"]), "flat compatibility replay differs")
        require(all(profile["status"] == "unavailable" and profile["standalone_scope_roundtrip_lossless"] is False
                    for profile in assessment["profiles"].values()), "unassessed scope became compatible")
        view = prepare_scope_bridge_view(request, declaration, expected_input_sha256=digest(request))
        require(raw(view.to_dict()) == raw(row["bridge_view"]), "scope view replay differs")
        restored = BridgeView.from_dict(row["bridge_view"])
        require(raw(restored.to_dict()["payload"]) == raw(declaration)
                and restored.payload_cid == view.payload_cid, "scope payload/CID roundtrip differs")
        bridge_receipt = validate_scope_bridge_view(row["bridge_view"], request, expected_input_sha256=digest(request))
        require(raw(bridge_receipt) == raw(row["bridge_validation"]), "bridge validation replay differs")
        for value in (validation, assessment, bridge_receipt):
            require(all(type(mask) is int and mask == 0 for mask in value["masks"].values()), "scope mask promoted")
            require(all(value[flag] is False for flag in (
                "accepted", "qualified", "source_fidelity_established", "proof_authority", "normalization_approved",
                "lowering_authorized", "semantic_equivalence_assessed", "training_executed", "model_executed")),
                "scope authority promoted")
            require(value["model_calls"] == value["prover_calls"] == 0, "scope execution count changed")
        replays += 1
    require(replays == 17 and assay["zero_mask_values"] == 85, "scope replay accounting differs")
    xml_path = DIRECTORY / "targeted-tests.xml"
    suite = ET.parse(xml_path).getroot().find("testsuite")
    require(suite is not None, "targeted suite evidence missing")
    counts = {key: int(suite.attrib[key]) for key in ("tests", "errors", "failures", "skipped")}
    failure_name = "test_existing_adapter_registry_is_composed_without_new_families"
    failures = [case for case in suite.findall("testcase") if case.find("failure") is not None]
    require(counts["tests"] > 0 and counts["errors"] == counts["skipped"] == 0
            and counts["failures"] == len(failures) == 1 and failures[0].attrib["name"] == failure_name,
            "unexpected targeted failure or error")
    new_test_names = set()
    for name in ("canonical_statement_scope", "canonical_statement_scope_bridge"):
        tree = ast.parse((REPO / f"tests/unit/logic/legal_ir/test_{name}.py").read_text())
        new_test_names.update(node.name for node in tree.body if isinstance(node, ast.FunctionDef)
                              and node.name.startswith("test_"))
    new_cases = [case for case in suite.findall("testcase")
                 if case.attrib["name"].split("[", 1)[0] in new_test_names]
    require(len(new_cases) == 115 and all(case.find("failure") is None for case in new_cases),
            "new115 test evidence differs")
    baseline_path = DIRECTORY / "independent-legacy-failure.txt"
    baseline = baseline_path.read_text()
    require(failure_name in baseline and "ui_ux_ir_formalization" in baseline and "1 failed" in baseline,
            "independent legacy mismatch evidence missing")
    ruff_path = DIRECTORY / "ruff.txt"
    require(ruff_path.read_text().strip() == "All checks passed!", "Ruff did not pass")
    document = ROOT / "implementation_plan/docs/52-autoformalization-statement-scope-coverage-2026-10-04.md"
    output = DIRECTORY / "validation.json"
    links = []
    for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", document.read_text()):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (document.parent / target.split("#", 1)[0]).resolve()
        require(path == output or path.is_file(), "scope document local link missing")
        links.append(str(path))
        if path != output:
            checked[str(path)] = binding(path)
    new_files = [
        REPO / "ipfs_datasets_py/logic/legal_ir/canonical_statement_scope.py",
        REPO / "ipfs_datasets_py/logic/legal_ir/canonical_statement_scope_bridge.py",
        REPO / "tests/unit/logic/legal_ir/test_canonical_statement_scope.py",
        REPO / "tests/unit/logic/legal_ir/test_canonical_statement_scope_bridge.py",
        CAMPAIGN / "assay_statement_scope.py", Path(__file__), PRIOR, ASSAY, document, xml_path, ruff_path,
        DIRECTORY / "targeted-tests.txt", DIRECTORY / "test-command.json", baseline_path,
    ]
    for name in ("canonical_byte_codec", "canonical_source_grounding", "canonical_typed_bridge"):
        new_files.append(REPO / f"tests/unit/logic/legal_ir/test_{name}.py")
    for path in new_files:
        checked[str(path)] = binding(path)
    result = {
        "schema": "autoformalization-statement-scope-validation/v1",
        "status": "passed_scope_diagnostics_with_existing_legacy_manifest_failure",
        "created_utc": datetime.now(UTC).isoformat(), "checked_file_count": len(checked),
        "checked_file_bindings": sorted(checked.values(), key=lambda value: value["path"]),
        "prior_intake_generation_binding": binding(PRIOR), "prior70_file_bindings_rechecked": True,
        "previous554_file_chain_rechecked": False, "complete_dependency_manifest": False,
        "document_binding": binding(document), "local_link_count": len(links), "assay_binding": binding(ASSAY),
        "targeted_test_counts": counts, "test_scope": "new scope and bridge plus unchanged byte/source/typed bridge contracts",
        "passing_test_count": counts["tests"] - counts["failures"],
        "new_scope_and_bridge_tests_passed": len(new_cases),
        "existing_legacy_failure": {"test_name": failure_name,
                                    "reason": "test expects six bridges; current manifest adds ui_ux_ir_formalization",
                                    "reproduced_without_scope_tests": True, "owner_or_test_changed": False,
                                    "evidence_binding": binding(baseline_path)},
        "test_fixtures_semantic_gold": False, "ruff_checked_files": 6,
        "implemented_profile": "normative-occurrence-scope/v1", "implemented_family": "deontic",
        "all40_family_scope_schemas_implemented": False, "broad_pilot_family_count": 40,
        "scope_declaration_transport_implemented": True, "legacy_compatibility_diagnostics_implemented": True,
        "semantic_normalization_policy_implemented": False, "richer_executable_lowering_implemented": False,
        "typed_binder_semantics_implemented": False, "semantic_label_admission_implemented": False,
        "historical_source_request_count": 34, "saved_candidates_replayed": replays,
        "exact_scope_bridge_roundtrips": replays, "scope_candidate_coverage": "unassessed",
        "original_current_packet_items": 64, "current64_exact_input_joins": 0, "current64_annotations_blank": True,
        "zero_logical_candidate_mask_values": 85, "original_current64_zero_mask_values": 320,
        "original_weak_train_masks_unchanged": True, "labels_admitted": 0, "formal_targets_admitted": 0,
        "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
        "history_model_execution_replayed": False, "historical_predictions_authenticated": False,
        "source_fidelity_established": False, "proof_authority": False, "normalization_approved": False,
        "lowering_authorized": False, "production_defaults_changed": False, "existing_decoder_checkpoints_modified": False,
        "renderer_preview_inspected": False,
        "seal_recipe": "SHA256 sorted compact UTF8 JSON excluding content_sha256; ensure_ascii=False; allow_nan=False",
    }
    result["content_sha256"] = digest(result)
    with output.open("xb") as stream:
        stream.write(raw(result) + b"\n")
    require(all(Path(path).is_file() for path in links), "final document link missing")
    print(raw({"validation_binding": binding(output), "checked_files": len(checked), "tests": counts,
               "exact_scope_roundtrips": replays, "labels_admitted": 0}).decode())


if __name__ == "__main__":
    main()
