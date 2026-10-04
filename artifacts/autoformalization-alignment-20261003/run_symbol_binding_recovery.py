"""Recover static alias replay using the preserved, already-fitted TRAIN profile."""

import hashlib
import importlib.abc
import json
import os
import resource
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/home/barberb/lift_coding")
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = ROOT / "artifacts/autoformalization-alignment-20261003"
PARTIAL = CAMPAIGN / "symbol-binding-01"
OUTPUT = CAMPAIGN / "symbol-binding-recovery-01"
ORIGINAL_RUNNER = CAMPAIGN / "run_symbol_binding_assay.py"
ORIGINAL_RUNNER_SHA = "77f4625e7a63c6309dcbfef7abb253521f87ffbf2dc41691c152732fae9a491a"
PARTIAL_SHAS = {
    "plan.json": "1fea6c7d0b2d4299137c3e4e76f9a85415b353548d80a300e098b2263e201205",
    "train_alias_profile.json": "72a903993de9be49a4cf90db4f28f13b8ecfdf326013eeb640ef5107646a168f",
    "train_profile_manifest.json": "fc7d72464789afa3b0ccc8b414eb6ea7987b1fcaa639057c902443d696f73809",
}
PROFILE_CONTENT_SHA = "b2f897a33ca3e7c43b2879db4abb651653dedab587bc6f94364a6bd80bb06324"
PRIOR_VALIDATION = CAMPAIGN / "typed-anchor-decoder-validation-01/validation.json"
PRIOR_VALIDATION_SHA = "d38b0cf7e628a2e9a552735f0e7280ac2d19b635b41df6138368e3e29cddd20f"
RECOVERY = CAMPAIGN / "typed-anchor-decoder-recovery-01"
SUPERVISION = CAMPAIGN / "canonical-codec-01/train_weak_supervision.json"
SUPERVISION_SHA = "97a333821790db1ad11a542f918a32e583b9b4ab150b82cdd71bbd883bbc42ba"
REQUESTS = RECOVERY / "inference_requests.json"
REQUESTS_SHA = "1740f42c497901e974ec7cb8f8892bd6208f643c7708313000870ecde9f10595"
OUTCOMES = CAMPAIGN / "canonical-codec-01/all_request_outcomes.json"
MAIN_PLAN = ROOT / "implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md"
SEEDS = (1729, 1730, 1731)
ROLES = ("source_initial", "source_final", "source_final_anchor_initial", "source_final_anchor_final")
MAX_SECONDS = 60
MAX_RSS_KIB = 512 * 1024
FALSE_FLAGS = {field: False for field in (
    "model_executed", "prover_executed", "neural_training_executed", "encoder_executed",
    "source_fidelity_established", "qualified", "proof_authority", "accepted",
    "independent_semantic_review_completed")}
BLOCKED_MODEL_ROOTS = frozenset({
    "torch", "tensorflow", "jax", "transformers", "sentence_transformers", "spacy",
    "sklearn", "numpy", "llama_cpp", "onnxruntime", "vllm"})


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


def text_sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def binding(path):
    path = Path(path).absolute()
    checksum, size = hashlib.sha256(), 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            checksum.update(chunk)
            size += len(chunk)
    return {"path": str(path), "bytes": size, "sha256": checksum.hexdigest()}


def verify(reference):
    observed = binding(reference["path"])
    assert observed["sha256"] == reference["sha256"], reference["path"]
    assert "bytes" not in reference or observed["bytes"] == reference["bytes"], reference["path"]
    return observed


def verified_record(path):
    value = json.loads(Path(path).read_bytes())
    assert value["content_sha256"] == digest({key: item for key, item in value.items()
                                             if key != "content_sha256"}), str(path)
    return value


def seal(value):
    assert "content_sha256" not in value
    return {**value, "content_sha256": digest(value)}


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return binding(path)


class NoModelImports(importlib.abc.MetaPathFinder):
    """A static-only process cannot import numerical model execution stacks."""

    def __init__(self):
        self.attempts = []

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in BLOCKED_MODEL_ROOTS:
            self.attempts.append(fullname)
            raise RuntimeError("model stack import outside static binding assay: " + fullname)
        return None


def unavailable_reason(row, role):
    outcome = row["outcome"]
    if outcome == "source_blocked":
        return "source_preflight_blocked"
    if outcome == "clarification_required":
        return "context_clarification_required"
    if outcome == "source_encoding_unavailable":
        return "retained_source_codec_OOV"
    if role in ("source_initial", "source_final"):
        return "canonical_only_output_has_no_anchor_contract"
    if outcome == "anchor_abstained":
        return "prior_anchor_abstention"
    if outcome in ("parent_abstained", "parent_unavailable"):
        return "prior_parent_abstention_or_unavailability"
    raise AssertionError("unexpected proposal-unavailable original outcome: " + outcome)


def aggregate(rows):
    counts = {
        "row_count": len(rows),
        "original_generation_outcome_counts": dict(sorted(Counter(row["original_generation_outcome"] for row in rows).items())),
        "binding_outcome_counts": dict(sorted(Counter(row["binding_outcome"] for row in rows).items())),
        "binding_unavailable_reason_counts": dict(sorted(Counter(row["binding_unavailable_reason"] for row in rows
                                                                 if row["binding_unavailable_reason"] is not None).items())),
        "original_full_proposal_count": sum(row["candidate_proposal_sha256"] is not None for row in rows),
        "candidate_output_withheld_count": sum(row["candidate_output_withheld"] for row in rows),
        "candidate_output_available_count": sum(row["output_proposal"] is not None for row in rows),
        "leaf_count": sum(row["assessment"]["leaf_count"] for row in rows if row["assessment"] is not None),
        "leaf_outcome_counts": {}, "by_split": {}, "by_row_kind": {},
    }
    leaf_counts = Counter()
    for row in rows:
        if row["assessment"] is not None:
            leaf_counts.update(row["assessment"]["leaf_outcome_counts"])
    counts["leaf_outcome_counts"] = dict(sorted(leaf_counts.items()))
    for dimension in ("split", "row_kind"):
        for label in sorted({row[dimension] for row in rows}):
            subset = [row for row in rows if row[dimension] == label]
            counts["by_" + dimension][label] = {
                "row_count": len(subset),
                "binding_outcome_counts": dict(sorted(Counter(row["binding_outcome"] for row in subset).items())),
                "original_full_proposal_count": sum(row["candidate_proposal_sha256"] is not None for row in subset),
                "candidate_output_withheld_count": sum(row["candidate_output_withheld"] for row in subset),
                "candidate_output_available_count": sum(row["output_proposal"] is not None for row in subset),
            }
    assert sum(counts["binding_outcome_counts"].values()) == len(rows)
    assert counts["original_full_proposal_count"] == counts["candidate_output_available_count"] + counts["candidate_output_withheld_count"]
    return counts


def main():
    started, started_cpu = time.monotonic(), time.process_time()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    resource.setrlimit(resource.RLIMIT_CPU, (60, 65))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    guard = NoModelImports()
    assert not any(name.split(".", 1)[0] in BLOCKED_MODEL_ROOTS for name in sys.modules)
    sys.meta_path.insert(0, guard)

    assert not OUTPUT.exists(), "fresh recovery stage required"
    OUTPUT.mkdir()
    journal_path = OUTPUT / "resource_observations.jsonl"
    journal_path.touch(exist_ok=False)
    resource_observations = []

    def observe_resource(label):
        snapshot = {"label": label, "elapsed_wall_seconds": time.monotonic() - started,
                    "resource_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    "linux_current_rss_kib": None, "linux_peak_hwm_kib": None,
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        status_path = Path("/proc/self/status")
        if status_path.exists():
            for line in status_path.read_text().splitlines():
                if line.startswith("VmRSS:"):
                    snapshot["linux_current_rss_kib"] = int(line.split()[1])
                elif line.startswith("VmHWM:"):
                    snapshot["linux_peak_hwm_kib"] = int(line.split()[1])
        resource_observations.append(snapshot)
        with journal_path.open("a", encoding="utf-8") as stream:
            stream.write(raw(snapshot).decode("utf-8") + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        return snapshot

    def admission(label="admission"):
        snapshot = observe_resource(label)
        assert time.monotonic() - started < MAX_SECONDS, "static recovery wall budget exceeded"
        assert snapshot["resource_ru_maxrss_kib"] < MAX_RSS_KIB, "static recovery resource RSS budget exceeded"
        assert all(snapshot[field] is None or snapshot[field] < MAX_RSS_KIB
                   for field in ("linux_current_rss_kib", "linux_peak_hwm_kib")), "static recovery Linux RSS budget exceeded"

    def observed_load(path):
        admission("before_read:" + str(path))
        result = verified_record(path)
        admission("after_read:" + str(path))
        return result

    admission("initial_resource_baseline")
    original_runner_binding = verify({"path": str(ORIGINAL_RUNNER), "sha256": ORIGINAL_RUNNER_SHA})
    assert {path.name for path in PARTIAL.iterdir()} == set(PARTIAL_SHAS)
    partial_bindings = [verify({"path": str(PARTIAL / name), "sha256": checksum})
                        for name, checksum in sorted(PARTIAL_SHAS.items())]
    partial_by_name = {Path(reference["path"]).name: reference for reference in partial_bindings}
    failed_attempt = {
        "status": "stopped_before_first_candidate_body_read",
        "runner_binding": original_runner_binding, "exit_code": 1,
        "failure_type": "AssertionError", "failure_message": "static assay RSS budget exceeded",
        "rejected_threshold_rss_kib": MAX_RSS_KIB,
        "observed_failed_peak_rss_kib": None, "failure_cause": "unknown",
        "saved_file_count": 3, "profile_fit_calls": 1, "candidate_body_reads": 0,
        "gate_assessment_calls": 0, "model_calls": 0, "optimizer_updates": 0, "prover_calls": 0,
        "evidence_scope": "observed_tool_exit_and_traceback_plus_immutable_partial_inventory"}
    # No saved candidate or DEV reference body is read before the profile and plan
    # are frozen. File hashes authenticate bytes without parsing candidate bodies.
    runner_binding = binding(__file__)
    prior_validation_binding = verify({"path": str(PRIOR_VALIDATION), "sha256": PRIOR_VALIDATION_SHA})
    supervision_binding = verify({"path": str(SUPERVISION), "sha256": SUPERVISION_SHA})
    requests_binding = verify({"path": str(REQUESTS), "sha256": REQUESTS_SHA})
    outcomes_binding = binding(OUTCOMES)
    supervision, requests_record, outcomes = (observed_load(path) for path in (SUPERVISION, REQUESTS, OUTCOMES))
    requests, outcome_rows = requests_record["rows"], outcomes["rows"]
    assert len(requests) == len(outcome_rows) == 34
    assert len({row["id"] for row in requests}) == 34
    assert all(set(request) == {"id", "source_text", "context_text", "requires_context_resolution"} for request in requests)
    request_by_id = {row["id"]: row for row in requests}
    outcome_by_id = {row["id"]: row for row in outcome_rows}
    assert set(request_by_id) == set(outcome_by_id)
    examples, fit_manifest_rows = [], []
    for row in supervision["rows"]:
        request = request_by_id[row["id"]]
        metadata = outcome_by_id[row["id"]]
        assert metadata["split"] == "train" and metadata["row_kind"] == "positive"
        assert row["masks"]["weak_decoder_fit"] == 1
        assert all(row["masks"][field] == 0 for field in ("strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation"))
        assert row["independent_semantic_review_completed"] is False
        assert request["context_text"] == "" and request["requires_context_resolution"] is False
        assert row["source_sha256"] == metadata["source_sha256"] == text_sha(request["source_text"])
        assert row["proposal_sha256"] == digest(row["proposal"])
        examples.append({"id": row["id"], "source_text": request["source_text"], "proposal": row["proposal"]})
        fit_manifest_rows.append({
            "id": row["id"], "group_id": row["group_id"], "source_sha256": row["source_sha256"],
            "proposal_sha256": row["proposal_sha256"], "anchor_count": len(row["proposal"]["anchors"]),
            "weak_label_origin": row["weak_label_origin"], "masks": row["masks"],
            "independent_semantic_review_completed": False})
    assert len(examples) == 16 and len({row["id"] for row in examples}) == 16
    assert {row["id"] for row in examples} == {row["id"] for row in outcome_rows if row["split"] == "train"}
    source_requests_digest = digest(requests)
    training_examples_digest = digest(examples)
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir import canonical_byte_codec as byte_codec
    from ipfs_datasets_py.logic.legal_ir import canonical_symbol_bindings as checker

    implementation_bindings = [binding(module.__file__) for module in (checker, byte_codec)]
    test_binding = binding(REPO / "tests/unit/logic/legal_ir/test_canonical_symbol_bindings.py")
    profile = observed_load(PARTIAL / "train_alias_profile.json")
    profile_sha = PROFILE_CONTENT_SHA
    original_plan = observed_load(PARTIAL / "plan.json")
    original_fit_manifest = observed_load(PARTIAL / "train_profile_manifest.json")
    assert original_plan["profile_content_sha256"] == profile_sha
    assert original_plan["profile_binding"] == partial_by_name["train_alias_profile.json"]
    assert original_plan["fit_manifest_binding"] == partial_by_name["train_profile_manifest.json"]
    assert original_plan["profile_fitting_calls_predeclared"] == 1
    assert original_plan["runner_binding"] == original_runner_binding
    for reference in original_plan["implementation_bindings"] + [original_plan["new_test_binding"]]:
        verify(reference)
    assert profile["training_manifest_sha256"] == training_examples_digest
    assert profile["training_pair_count"] == len(examples)
    assert profile["training_anchor_count"] == sum(row["anchor_count"] for row in fit_manifest_rows)
    assert checker.validate_profile(profile, expected_profile_sha256=profile_sha) == profile
    assert profile["training_supervision_consumed"] is True and profile["query_reference_accessed"] is False
    profile_binding = partial_by_name["train_alias_profile.json"]
    fit_manifest_binding = partial_by_name["train_profile_manifest.json"]
    assert original_fit_manifest["rows"] == fit_manifest_rows
    assert original_fit_manifest["training_manifest_sha256"] == training_examples_digest
    assert original_fit_manifest["row_count"] == 16
    assert original_plan["implementation_bindings"] == implementation_bindings
    assert original_plan["new_test_binding"] == test_binding
    candidate_specs = []
    for seed in SEEDS:
        for role in ROLES:
            candidate_specs.append({"seed": seed, "role": role, "is_private_repeat": False,
                                    "binding": binding(RECOVERY / f"seed{seed}-{role}-generation.json")})
        candidate_specs.append({
            "seed": seed, "role": "source_final_anchor_final", "is_private_repeat": True,
            "binding": binding(RECOVERY / f"seed{seed}-source-final-anchor-final-private-reload.json")})
    plan_binding = save(OUTPUT / "plan.json", seal({
        "schema": "alignment-static-source-symbol-binding-recovery-plan/v1", "runner_binding": runner_binding,
        "original_runner_binding": original_runner_binding, "interrupted_stage_bindings": partial_bindings,
        "original_plan_binding": partial_by_name["plan.json"], "failed_attempt": failed_attempt,
        "recovery_profile_fit_calls": 0, "original_completed_profile_fit_calls": 1,
        "prior_validation_binding": prior_validation_binding, "preserved_prior_checked_file_count": 444,
        "preserved_prior_typed_implementation_test_file_count": 2,
        "profile_binding": profile_binding, "profile_content_sha256": profile_sha,
        "fit_manifest_binding": fit_manifest_binding, "input_bindings": [supervision_binding, requests_binding, outcomes_binding],
        "implementation_bindings": implementation_bindings, "new_test_binding": test_binding,
        "saved_candidate_bindings_hashed_not_parsed_before_freeze": candidate_specs,
        "profile_fitting_calls_predeclared": 0, "profile_fit_split": "preserved_train_profile_reused_without_refitting",
        "profile_fit_pair_count": 16, "training_supervision_consumed": True,
        "weak_correspondence_origin": "source_parser_derived_with_frozen_TRAIN_supervised_atom_catalog",
        "query_reference_accessed": False, "authored_reference_ir_accessed": False,
        "development_reference_ir_accessed": False, "development_weak_proposal_accessed": False,
        "candidate_independent_profile": True, "normalization": profile["normalization"],
        "primary_receipt_count": 12, "primary_row_slots": 408,
        "private_repeat_receipt_count": 3, "private_repeat_row_slots": 102,
        "all_row_slots": 510, "rows_per_receipt": 34,
        "canonical_only_outputs": "binding_unavailable_without_synthesized_anchors",
        "known_single_alias_mismatch": "binding_inconsistent_and_candidate_output_withheld_in_opt_in_filter_only",
        "unknown_or_ambiguous_alias": "binding_unassessed_and_candidate_retained_for_unqualified_review",
        "all_known_single_aliases_match": "binding_consistent_and_candidate_retained_for_unqualified_review",
        "output_scope": "new_opt_in_static_filter_receipts_original_candidates_immutable",
        "semantic_scope": "observed_TRAIN_literal_facet_symbol_agreement_only",
        "expected_result_hypothesis_not_admission_rule": "48_primary_TRAIN_candidates_consistent_and_one_primary_DEV_candidate_inconsistent",
        "weak_gold_comparison_requested": False, "candidate_redecoding_calls": 0,
        "model_calls": 0, "encoder_calls": 0, "optimizer_updates": 0, "prover_calls": 0,
        "max_seconds": MAX_SECONDS, "cpu_limit_seconds": [60, 65], "max_rss_kib": MAX_RSS_KIB,
        "started_utc": started_utc, **FALSE_FLAGS}))
    profile_plan_freeze_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    # All profile-fitting inputs and the selected filtering policy are now
    # durable. Previously saved model candidates can be opened only below.
    prior = observed_load(PRIOR_VALIDATION)
    preserved = [verify(reference) for reference in prior["checked_file_bindings"]]
    assert len(preserved) == prior["checked_file_count"] == 444
    extra_prior = [verify(reference) for reference in prior["new_implementation_test_bindings"]]
    assert len(extra_prior) == 2
    frozen_documentation = [verify(reference) for reference in prior["documentation_bindings"]
                            if reference["path"] != str(MAIN_PLAN)]
    mutable_main_plan_before = binding(MAIN_PLAN)
    recovery_report_binding = verify(prior["report_binding"])
    recovery_report = observed_load(recovery_report_binding["path"])
    expected_candidate_bindings = {}
    for run in recovery_report["runs"]:
        for role, reference in run["source_generation_bindings"].items():
            expected_candidate_bindings[(run["seed"], role, False)] = reference
        for role, reference in run["pipeline_generation_bindings"].items():
            expected_candidate_bindings[(run["seed"], role, False)] = reference
        expected_candidate_bindings[(run["seed"], "source_final_anchor_final", True)] = run["private_reload_binding"]
    assert len(expected_candidate_bindings) == 15
    assert all(spec["binding"] == expected_candidate_bindings[(spec["seed"], spec["role"], spec["is_private_repeat"])]
               for spec in candidate_specs)
    calls = {"profile_fitting": 0, "primary_assessments": 0, "private_repeat_assessments": 0,
             "saved_assessment_validation_recomputations": 0, "candidate_redecoding": 0,
             "model": 0, "encoder": 0, "optimizer_updates": 0, "prover": 0}
    records, primary_by_seed_role = [], {}
    primary_rows, private_rows, primary_contradictions = [], [], []
    for spec in candidate_specs:
        admission("before_receipt:" + str(spec["seed"]) + ":" + spec["role"])
        original_binding = verify(spec["binding"])
        original = observed_load(original_binding["path"])
        assert len(original["rows"]) == 34
        assert [row["id"] for row in original["rows"]] == [request["id"] for request in requests]
        rows = []
        for position, original_row in enumerate(original["rows"]):
            request = requests[position]
            metadata = outcome_by_id[request["id"]]
            assert original_row["position"] == position
            assert original_row["source_sha256"] == metadata["source_sha256"] == text_sha(request["source_text"])
            assert original_row["context_sha256"] == text_sha(request["context_text"])
            assert all(original.get(field, False) is False for field in ("target_access", "teacher_forcing", "training_executed", "accepted", "qualified", "proof_authority", "source_fidelity_established"))
            proposal = original_row.get("proposal")
            before_row_sha = digest(original_row)
            assessment, proposal_sha, reason = None, None, None
            if proposal is None:
                outcome = "binding_unavailable"
                reason = unavailable_reason(original_row, spec["role"])
            else:
                assert spec["role"] == "source_final_anchor_final"
                assert original_row["outcome"] == "anchored_proposal"
                proposal_sha = digest(proposal)
                assessment = checker.assess_bindings(request["source_text"], proposal, profile,
                                                     expected_profile_sha256=profile_sha)
                calls["private_repeat_assessments" if spec["is_private_repeat"] else "primary_assessments"] += 1
                outcome = assessment["outcome"]
                assert assessment["proposal_sha256"] == proposal_sha
                assert assessment["profile_sha256"] == profile_sha
                assert assessment["query_reference_accessed"] is False
                assert assessment["proposal_changed"] is False and assessment["canonical_ir_repaired"] is False
                assert all(assessment[field] is False for field in (
                    "model_executed", "prover_executed", "source_fidelity_established", "qualified",
                    "proof_authority", "accepted", "independent_semantic_review_completed"))
                assert all(leaf["source_text"] == request["source_text"][leaf["start"]:leaf["end"]]
                           for leaf in assessment["leaves"])
            withheld = outcome == "binding_inconsistent"
            output_proposal = None if withheld else proposal
            if output_proposal is not None:
                assert digest(output_proposal) == proposal_sha
            assert digest(original_row) == before_row_sha
            assert profile["content_sha256"] == profile_sha
            rows.append({
                "id": request["id"], "position": position, "source_sha256": original_row["source_sha256"],
                "context_sha256": original_row["context_sha256"], "request_sha256": digest(request),
                "split": metadata["split"], "group_id": metadata["group_id"], "row_kind": metadata["row_kind"],
                "review_status": metadata["review_status"], "original_generation_outcome": original_row["outcome"],
                "original_generation_row_sha256": before_row_sha, "candidate_proposal_sha256": proposal_sha,
                "binding_outcome": outcome, "binding_unavailable_reason": reason, "assessment": assessment,
                "candidate_output_withheld": withheld, "output_proposal": output_proposal,
                "output_scope": "opt_in_static_filter_only_original_candidate_artifact_preserved",
                "candidate_unchanged": True, "canonical_ir_repaired": False,
                "query_reference_accessed": False, **FALSE_FLAGS})
        record = seal({
            "schema": "alignment-saved-candidate-symbol-binding-assessments/v1",
            "seed": spec["seed"], "role": spec["role"], "is_private_repeat": spec["is_private_repeat"],
            "original_generation_binding": original_binding, "source_requests_binding": requests_binding,
            "profile_binding": profile_binding, "profile_content_sha256": profile_sha,
            "row_count": len(rows), "rows": rows, "counts": aggregate(rows),
            "training_supervision_consumed_by_separate_profile_fit": True,
            "query_reference_accessed": False, "authored_reference_ir_accessed": False,
            "assessment_scope": "static_observed_TRAIN_alias_consistency_only",
            "original_generation_execution": "previously_saved_model_outputs_not_reexecuted",
            "proposal_transport_flags_scope": "structural_transport_not_generation_provenance",
            **FALSE_FLAGS})
        label = "private-repeat" if spec["is_private_repeat"] else "primary"
        output_binding = save(OUTPUT / f"seed{spec['seed']}-{spec['role']}-{label}-bindings.json", record)
        # Re-read the durable result and use the public receipt recomputation
        # validator; this proves static receipt integrity, not semantic accuracy.
        durable = observed_load(output_binding["path"])
        for row in durable["rows"]:
            if row["assessment"] is not None:
                proposal = original["rows"][row["position"]]["proposal"]
                assert checker.validate_bindings(row["assessment"], requests[row["position"]]["source_text"],
                                                 proposal, profile, expected_profile_sha256=profile_sha) == row["assessment"]
                calls["saved_assessment_validation_recomputations"] += 1
        private_parity = None
        if spec["is_private_repeat"]:
            corresponding = primary_by_seed_role[(spec["seed"], spec["role"])]
            private_parity = raw(rows) == raw(corresponding["rows"])
            assert private_parity
            assert record["counts"] == corresponding["counts"]
            private_rows.extend(rows)
        else:
            primary_by_seed_role[(spec["seed"], spec["role"])] = record
            primary_rows.extend(rows)
            for row in rows:
                if row["binding_outcome"] == "binding_inconsistent":
                    primary_contradictions.append({
                        "seed": spec["seed"], "role": spec["role"], "id": row["id"], "position": row["position"],
                        "split": row["split"], "candidate_proposal_sha256": row["candidate_proposal_sha256"],
                        "original_generation_binding": original_binding, "assessment_binding": output_binding,
                        "known_alias_mismatch_leaves": [leaf for leaf in row["assessment"]["leaves"]
                                                        if leaf["outcome"] == "known_alias_mismatch"],
                        "comparison_scope": "TRAIN_alias_correspondence_not_query_gold",
                        "candidate_output_withheld": True, **FALSE_FLAGS})
        records.append({
            "seed": spec["seed"], "role": spec["role"], "is_private_repeat": spec["is_private_repeat"],
            "original_generation_binding": original_binding, "assessment_binding": output_binding,
            "counts": record["counts"], "private_repeat_exact_row_json_equal_primary": private_parity})
        verify(original_binding)
        verify(profile_binding)
        admission("after_receipt:" + str(spec["seed"]) + ":" + spec["role"])
    assert len(primary_rows) == 408 and len(private_rows) == 102
    assert calls["primary_assessments"] == aggregate(primary_rows)["original_full_proposal_count"]
    assert calls["private_repeat_assessments"] == aggregate(private_rows)["original_full_proposal_count"]
    assert calls["saved_assessment_validation_recomputations"] == calls["primary_assessments"] + calls["private_repeat_assessments"]
    assert digest(requests) == source_requests_digest and digest(examples) == training_examples_digest
    assert checker.validate_profile(observed_load(profile_binding["path"]), expected_profile_sha256=profile_sha) == profile
    assert {path.name for path in PARTIAL.iterdir()} == set(PARTIAL_SHAS)
    admission("before_final_preservation_hashes")
    for reference in preserved + extra_prior + frozen_documentation + implementation_bindings + partial_bindings + [
            original_runner_binding,
            test_binding, runner_binding, plan_binding, fit_manifest_binding, prior_validation_binding,
            supervision_binding, requests_binding, outcomes_binding, recovery_report_binding]:
        verify(reference)
    assert guard.attempts == []
    assert not any(name.split(".", 1)[0] in BLOCKED_MODEL_ROOTS for name in sys.modules)
    admission("final_resource_observation")
    resource_journal_binding = binding(journal_path)
    report = seal({
        "schema": "alignment-static-source-symbol-binding-report/v1", "status": "completed_static_saved_candidate_recovery_assay",
        "original_runner_binding": original_runner_binding, "interrupted_stage_bindings": partial_bindings,
        "original_plan_binding": partial_by_name["plan.json"], "failed_attempt": failed_attempt,
        "recovery_profile_fit_calls": 0, "original_completed_profile_fit_calls": 1,
        "resource_journal_binding": resource_journal_binding, "resource_observations": resource_observations,
        "runner_binding": runner_binding, "plan_binding": plan_binding, "profile_binding": profile_binding,
        "profile_content_sha256": profile_sha, "fit_manifest_binding": fit_manifest_binding,
        "prior_validation_binding": prior_validation_binding, "source_bindings": preserved,
        "preserved_prior_checked_file_count": len(preserved), "extra_prior_typed_implementation_test_bindings": extra_prior,
        "frozen_prior_documentation_bindings": frozen_documentation,
        "mutable_main_plan_prior_reference": next(reference for reference in prior["documentation_bindings"]
                                                  if reference["path"] == str(MAIN_PLAN)),
        "mutable_main_plan_observed_before_binding": mutable_main_plan_before,
        "mutable_main_plan_preservation_required": False,
        "input_bindings": [supervision_binding, requests_binding, outcomes_binding],
        "recovery_report_binding": recovery_report_binding, "implementation_bindings": implementation_bindings,
        "new_test_binding": test_binding, "assessment_records": records,
        "primary_receipt_count": 12, "private_repeat_receipt_count": 3, "rows_per_receipt": 34,
        "primary_counts": aggregate(primary_rows), "private_repeat_counts": aggregate(private_rows),
        "all_saved_receipt_counts": aggregate(primary_rows + private_rows),
        "primary_recognized_alias_contradictions": primary_contradictions,
        "private_repeat_exact_row_json_equal_primary_count": sum(record["private_repeat_exact_row_json_equal_primary"] is True for record in records),
        "profile_pair_count": profile["training_pair_count"], "profile_anchor_observation_count": profile["training_anchor_count"],
        "profile_alias_entry_count": profile["alias_entry_count"], "profile_ambiguous_alias_count": profile["ambiguous_alias_count"],
        "training_supervision_consumed": True, "query_reference_accessed": False,
        "authored_reference_ir_accessed": False, "development_reference_ir_accessed": False,
        "development_weak_proposal_accessed": False, "weak_gold_comparison_performed": False,
        "weak_correspondence_origin": "source_parser_derived_with_frozen_TRAIN_supervised_atom_catalog",
        "normalization": profile["normalization"], "observed_calls": calls,
        "model_import_attempts": guard.attempts, "model_execution_stacks_loaded": [],
        "source_bindings_unchanged": True, "original_candidate_artifacts_unchanged": True,
        "profile_frozen_before_candidate_body_access": True,
        "original_profile_reused_without_refitting": True,
        "original_partial_files_unchanged": True,
        "profile_plan_freeze_utc": profile_plan_freeze_utc,
        "semantic_scope": "observed_TRAIN_literal_facet_symbol_agreement_only",
        "candidate_withholding_scope": "new_opt_in_static_filter_only_original_saved_candidates_preserved",
        "unknown_alias_policy": "unassessed_candidate_retained_without_acceptance",
        "consistent_alias_policy": "candidate_retained_without_fidelity_or_acceptance",
        "limitations": [
            "Weak TRAIN aliases can encode mistakes and are not independent semantic gold.",
            "Known alias agreement does not verify whole-source interpretation, contextual scope, or qualifier logic.",
            "Unknown and colliding aliases remain unassessed; this checker does not infer missing meanings.",
            "Canonical-only and prior abstained outputs lack a full anchor contract and remain unavailable to this gate.",
            "Receipt recomputation and reload parity establish deterministic static consistency, not source fidelity."],
        "independently_reviewed_fidelity_rows": 0, "qualified_output_rows": 0,
        "accepted_output_rows": 0, "checkpoint_promotions": 0,
        "started_utc": started_utc, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "wall_seconds": time.monotonic() - started, "cpu_seconds": time.process_time() - started_cpu,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "linux_current_rss_kib_at_final_observation": resource_observations[-1]["linux_current_rss_kib"],
        "linux_peak_hwm_kib_at_final_observation": resource_observations[-1]["linux_peak_hwm_kib"],
        "runtime_python_executable": sys.executable, "max_seconds": MAX_SECONDS,
        "cpu_limit_seconds": [60, 65], "max_rss_kib": MAX_RSS_KIB, **FALSE_FLAGS})
    report_binding = save(OUTPUT / "report.json", report)
    print(json.dumps({"report_binding": report_binding, "profile_content_sha256": profile_sha,
                      "primary_counts": report["primary_counts"], "private_repeat_counts": report["private_repeat_counts"],
                      "observed_calls": calls, "wall_seconds": report["wall_seconds"],
                      "cpu_seconds": report["cpu_seconds"], "peak_rss_kib": report["peak_rss_kib"]}, sort_keys=True))


if __name__ == "__main__":
    main()
