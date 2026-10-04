"""Replay pinned stage artifacts and retain prior-file and test evidence."""
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
DIRECTORY = CAMPAIGN / "stage-workflow-01"
PRIOR = CAMPAIGN / "representation-boundary-01/validation.json"
PRIOR_SHA = "f9cbd4a7daf87304ee187b0dac242777ba1f9f93769b7c401a893948d7e9055e"
DOCUMENT = ROOT / "implementation_plan/docs/54-autoformalization-pinned-stage-workflows-2026-10-04.md"
NEW_SOURCE = (
    "ipfs_datasets_py/logic/formalization/autoencoder/alignment_stage_workflow.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/alignment_raw_ranking.py",
    "scripts/ops/autoencoder/run_alignment_stage.py",
)
NEW_TESTS = (
    "tests/unit/logic/formalization/autoencoder/test_alignment_stage_workflow.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_raw_ranking.py",
)
PRIOR_TESTS = (
    "tests/unit/logic/formalization/autoencoder/test_alignment_lane_bundle.py",
    "tests/unit/logic/formalization/autoencoder/test_alignment_stage_declarations.py",
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
    if type(value) is dict and "content_sha256" in value:
        require(value["content_sha256"] == digest({k: v for k, v in value.items() if k != "content_sha256"}),
                "content seal changed: " + str(path))
    return value


def iter_bindings(value):
    if type(value) is dict:
        if set(value) == {"path", "bytes", "sha256"}:
            yield value
        else:
            for item in value.values():
                yield from iter_bindings(item)
    elif type(value) is list:
        for item in value:
            yield from iter_bindings(item)


def main():
    require(len(sys.argv) == 2, "explicit frozen assay file SHA required")
    assay_sha = sys.argv[1]
    require(re.fullmatch(r"[0-9a-f]{64}", assay_sha), "canonical assay file SHA required")
    prior = load(PRIOR, PRIOR_SHA)
    checked = {}

    def check(expected):
        require(binding(expected["path"]) == expected, "file binding changed: " + expected["path"])
        checked[expected["path"]] = expected

    for expected in prior["checked_file_bindings"]:
        check(expected)
    require(len(checked) == prior["checked_file_count"] == 134, "prior134 accounting differs")
    assay_path = DIRECTORY / "assay.json"
    assay = load(assay_path, assay_sha)
    for expected in iter_bindings(assay):
        check(expected)
    # Exact stage replay checks are completed against the runner's final schema.
    replay = replay_assay(assay)
    xml_path = DIRECTORY / "targeted-tests.xml"
    suite = ET.parse(xml_path).getroot().find("testsuite")
    require(suite is not None, "targeted suite evidence missing")
    counts = {key: int(suite.attrib[key]) for key in ("tests", "errors", "failures", "skipped")}
    require(counts["tests"] > 0 and counts["errors"] == counts["failures"] == counts["skipped"] == 0,
            "targeted tests did not fully pass")
    groups = {}
    owners = {}
    for relative in (*NEW_TESTS, *PRIOR_TESTS):
        tree = ast.parse((REPO / relative).read_text())
        names = {node.name for node in tree.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
        for name in names:
            require(name not in owners, "test function name ambiguous across selected source files")
            owners[name] = relative
        groups[relative] = sum(case.attrib["name"].split("[", 1)[0] in names for case in suite.findall("testcase"))
    require(all(value > 0 for value in groups.values()) and sum(groups.values()) == counts["tests"],
            "test source-group accounting differs")
    ruff_path = DIRECTORY / "ruff-final.txt"
    require(ruff_path.read_text().strip() == "All checks passed!", "Ruff evidence failed")
    command_path = DIRECTORY / "test-command-final.json"
    command = load(command_path)
    require(command["targeted_exit_code"] == command["ruff_exit_code"] == 0, "check exit evidence differs")
    output = DIRECTORY / "validation.json"
    links = []
    for target in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", DOCUMENT.read_text()):
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (DOCUMENT.parent / target.split("#", 1)[0]).resolve()
        require(path == output or path.is_file(), "document local link missing: " + str(path))
        links.append(str(path))
        if path != output:
            checked[str(path)] = binding(path)
    for path in [*(REPO / name for name in (*NEW_SOURCE, *NEW_TESTS, *PRIOR_TESTS)), Path(__file__),
                 CAMPAIGN / "assay_stage_workflows.py", PRIOR, assay_path, DOCUMENT,
                 xml_path, DIRECTORY / "targeted-tests.txt", ruff_path, command_path,
                 DIRECTORY / "ruff.txt", DIRECTORY / "test-command.json"]:
        checked[str(path)] = binding(path)
    result = {
        "schema": "autoformalization-stage-workflow-validation/v1",
        "status": "passed_diagnostic_stage_workflows_only",
        "created_utc": datetime.now(UTC).isoformat(),
        "checked_file_count": len(checked),
        "checked_file_bindings": sorted(checked.values(), key=lambda value: value["path"]),
        "prior_representation_generation_binding": binding(PRIOR),
        "prior134_file_bindings_rechecked": True,
        "previous554_file_chain_rechecked": False,
        "complete_dependency_manifest": False,
        "prior_existing_legacy_manifest_mismatch_preserved": prior["prior_existing_legacy_manifest_mismatch_preserved"],
        "legacy_manifest_mismatch_retested_this_stage": False,
        "document_binding": binding(DOCUMENT), "local_link_count": len(links),
        "assay_binding": binding(assay_path), "assay_external_selection_sha256": assay_sha,
        "targeted_test_counts": counts, "tests_by_source_function_names": groups,
        "test_function_names_checked_unique_across_selected_sources": True,
        "test_fixtures_semantic_gold": False, "final_ruff_passed": True,
        "prepublication_evidence_collection_errors_corrected": [
            "test log files had not yet been copied; no validation receipt written",
            "JUnit classname values empty under /dev/null config; grouping changed to checked-unique source function names",
        ],
        "diagnostic_stage_replay": replay,
        "os_reference_file_confinement_established": False,
        "derivative_exclusion_authenticated": False,
        "semantic_label_admission_implemented": False,
        "masked_contrastive_loss_implemented": False,
        "broad_pilot_family_count": 40, "broad_pilot_semantic_evaluation_executed": False,
        "labels_admitted": 0, "formal_targets_admitted": 0,
        "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "optimizer_updates": 0,
        "source_fidelity_established": False, "proof_authority": False,
        "leanstral_runtime_qualified": False, "production_defaults_changed": False,
        "existing_decoder_checkpoints_modified": False, "existing_original_train_masks_unchanged": True,
        "renderer_preview_inspected": False,
        "seal_recipe": "SHA256 sorted compact UTF8 JSON excluding content_sha256; ensure_ascii=False; allow_nan=False",
    }
    result["content_sha256"] = digest(result)
    for expected in checked.values():
        require(binding(expected["path"]) == expected, "final file recheck differs")
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw(result) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    require(all(Path(path).is_file() for path in links), "final local link missing")
    print(raw({"validation_binding": binding(output), "checked_files": len(checked), "tests": counts,
               "diagnostic_stage_replay": replay, "labels_admitted": 0}).decode())


def replay_assay(assay):
    # Install the runner's stdlib-only namespace/import boundary before owners.
    sys.path.insert(0, str(CAMPAIGN))
    import assay_stage_workflows as runner

    prepared = runner.prepare_assay()
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_raw_ranking as ranking,
    )
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_stage_declarations as stages,
    )

    objects = {}
    for selected in iter_bindings(assay):
        path = Path(selected["path"])
        if path.suffix == ".json" and path.is_relative_to(DIRECTORY):
            objects[str(path)] = load(path, selected["sha256"])
    reports = [value for value in objects.values()
               if type(value) is dict and value.get("schema") == "alignment-stage-workflow/v1"]
    require(len(reports) == 5, "three rank/one fit/one score workflow reports required")
    require(sorted(report["stage"] for report in reports) == ["fit", "rank", "rank", "rank", "score"],
            "stage report distribution differs")
    by_value = {digest(value): value for value in objects.values()}
    totals = {"raw_rank_view_count": 0, "ranked_query_view_count": 0,
              "returned_hit_count": 0, "similarity_evaluation_count": 0,
              "fit_executed_updates": 0, "fidelity_scored_query_count": 0}
    original_queries, original_train, lane_ids = set(), set(), set()
    for report in reports:
        require(report["selected_file_bindings_verified"] is True and report["os_sandbox"] is False
                and report["child_isolation"] == "trusted_resource_bounded_subprocess",
                "workflow file/process scope changed")
        require(all(report[name] is False for name in ("training_executed", "scoring_executed", "qualified", "accepted",
                    "source_fidelity_established", "semantic_label_admission", "proof_authority",
                    "reviewer_identity_authenticated", "split_provenance_authenticated")),
                "workflow promoted semantic or production authority")
        require(all(type(mask) is int and mask == 0 for mask in report["masks"].values())
                and all(report[name] == 0 for name in ("model_calls", "encoder_calls", "prover_calls",
                                                     "optimizer_updates", "fidelity_scores_created")),
                "workflow execution or supervision changed")
        require(report["worker_usage"]["peak_rss_kib"] * 1024 < report["resource_limits"]["address_space_bytes"],
                "measured peak RSS exceeds declared address-space cap")
        validation = load(report["artifacts"]["validation"]["path"])
        declaration = by_value[validation["declaration_sha256"]]
        selected_values = [objects[item["path"]] for item in report["selected_file_bindings"]]
        expected_candidates = [value for value in selected_values if value == validation["role_bindings"]]
        require(len(expected_candidates) == 1, "independently selected role bindings missing or ambiguous")
        expected = expected_candidates[0]
        validator = getattr(stages, "validate_" + report["stage"] + "_declaration")
        require(raw(validator(declaration, expected_bindings=expected)) == raw(validation),
                "saved declaration validation differs from exact replay")
        if report["stage"] == "rank":
            query_bundle = by_value[declaration["lane_validation"]["bundle_sha256"]]
            bank_bundle = by_value[declaration["frozen_bank"]["lane_validation"]["bundle_sha256"]]

            def lane_pins(bundle, selected_values):
                wanted = {"profile_sha256": digest(bundle["profile"]),
                          "producer_receipt_sha256": digest(bundle["producer_receipt"]),
                          "inputs": [{"id": row["id"], "input_sha256": row["input_sha256"]}
                                     for row in bundle["rows"]]}
                matches = [value for value in selected_values if value == wanted]
                require(len(matches) == 1, "independently selected lane pins missing or ambiguous")
                return matches[0]

            replay = ranking.rank_raw_source_bundles(declaration, query_bundle, bank_bundle,
                expected_bindings=expected, expected_query_lane=lane_pins(query_bundle, selected_values),
                expected_bank_lane=lane_pins(bank_bundle, selected_values))
            saved = load(report["artifacts"]["saved_rankings"]["path"])
            diagnostic = load(report["artifacts"]["raw_ranking_diagnostic"]["path"])
            require(raw(replay["saved_rankings"]) == raw(saved)
                    and raw(replay["diagnostic_receipt"]) == raw(diagnostic), "exact raw cosine replay differs")
            require(diagnostic["query_count"] == diagnostic["ranked_query_count"] == 18
                    and diagnostic["bank_row_count"] == diagnostic["eligible_candidate_count"] == 16,
                    "historical18-query/16-TRAIN outcome accounting differs")
            require(diagnostic["returned_hit_count"] == 54 and diagnostic["similarity_evaluation_count"] == 288,
                    "top3 exhaustive comparison accounting differs")
            require(all(diagnostic[name] is False for name in ranking.FALSE)
                    and all(type(mask) is int and mask == 0 for mask in diagnostic["masks"].values()),
                    "raw diagnostic authority or masks changed")
            require(report["ranking_operation_executed"] is True, "raw workflow failed to record its computation")
            lane_ids.add(diagnostic["lane_id"])
            original_queries.update(row["id"] for row in query_bundle["rows"])
            original_train.update(row["id"] for row in bank_bundle["rows"])
            totals["raw_rank_view_count"] += 1
            totals["ranked_query_view_count"] += diagnostic["ranked_query_count"]
            totals["returned_hit_count"] += diagnostic["returned_hit_count"]
            totals["similarity_evaluation_count"] += diagnostic["similarity_evaluation_count"]
        elif report["stage"] == "fit":
            require(validation["status"] == "blocked_no_contrastive_admission"
                    and validation["proposed_optimizer_updates"] == 960
                    and validation["optimizer_updates"] == 0 and report["ranking_operation_executed"] is False,
                    "fit must retain proposed960 and executed0 updates")
        else:
            require(validation["status"] == "blocked_no_admitted_fidelity_references"
                    and validation["unavailable_reference_count"] == 18
                    and validation["admitted_reference_count"] == validation["scored_query_count"] == 0,
                    "score must preserve18 unavailable references and compute no fidelity")
            require(report["pre_reference_saved_integrity_checked"] is True
                    and report["ranking_operation_executed"] is False, "score saved-generation gate missing")
            order = report["read_order"]
            saved_paths = [path for path in order if type(objects[path]) is dict
                           and objects[path].get("schema") == "alignment-saved-ranking-bindings/v1"]
            reference_paths = [path for path in order if type(objects[path]) is dict
                               and objects[path].get("schema") in {stages.SCORE_SCHEMA,
                                   "alignment-scoring-reference-bindings/v1"}]
            require(len(saved_paths) == 1 and len(reference_paths) == 2
                    and all(order.index(saved_paths[0]) < order.index(path) for path in reference_paths),
                    "references opened before durable saved integrity gate")
    require(lane_ids == {"legacy8", "native384", "native768"}
            and len(original_queries) == 18 and len(original_train) == 16
            and original_queries.isdisjoint(original_train), "raw lane/cohort identity accounting differs")
    totals.update(original_query_count=18, original_train_count=16, saved_generations_replayed=5,
                  ranking_values_recomputed=True, no_models_or_weights_loaded=True,
                  os_reference_confinement_verified=False, derivative_provenance_verified=False)
    # Reconstruct the new source-only inputs from the frozen historical sources.
    for filename, payload in prepared["inputs"].items():
        matches = [value for path, value in objects.items() if Path(path).name == Path(filename).name]
        require(len(matches) == 1 and raw(matches[0]) == raw(payload), "historical input transcription replay differs")
    totals["historical_input_transcriptions_replayed"] = len(prepared["inputs"])
    saved384 = next(value for value in objects.values() if type(value) is dict
                    and value.get("schema") == "alignment-saved-ranking-bindings/v1"
                    and value["rank_declaration"]["lane_validation"]["lane_id"] == "native384")
    for filename, payload in runner.prepare_score_inputs(saved384).items():
        matches = [value for path, value in objects.items() if Path(path).name == Path(filename).name]
        require(len(matches) == 1 and raw(matches[0]) == raw(payload), "unavailable-reference score transcription differs")
    totals["unavailable_reference_score_inputs_replayed"] = 3
    return totals


if __name__ == "__main__":
    main()
