"""Check the real declaration workflow with the frozen packet and no submissions."""

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
OUTPUT = CAMPAIGN / "binding-review-admission-01"
PACKET_DIRECTORY = CAMPAIGN / "binding-review-packet-01"
PACKET_PATH = PACKET_DIRECTORY / "reviewer_items.json"
PACKET_FILE_SHA = "8a8303ea83fe22899f798703e7931b1f48a8aa0afb01c7d6980a7d3e9301701e"
PACKET_CONTENT_SHA = "a8f465c7950e34ce11f69a5a900d79895f5e19545a2082da75eb9ddf59815655"
PRIOR_VALIDATION = CAMPAIGN / "symbol-binding-validation-01/validation.json"
PRIOR_VALIDATION_SHA = "8dafcff5672a5ead9310321d8fc30c4faaf1075296b5d3d4fc34311ebd30aaf3"
MAIN_PLAN = ROOT / "implementation_plan/docs/49-autoformalization-joint-embeddings-improvement-plan-2026-10-03.md"
MAX_SECONDS = 60
MAX_RSS_KIB = 512 * 1024
MASK_FIELDS = ("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision",
               "proof_supervision", "fidelity_evaluation")
AUTHORITY_FIELDS = (
    "qualified", "accepted", "source_fidelity_established", "proof_authority",
    "independent_semantic_review_completed", "reviewer_identity_authenticated",
    "reviewer_independence_authenticated", "semantic_gold_created",
    "actual_training_or_evaluation_admission", "source_author_independence_authenticated")
FALSE_FLAGS = {field: False for field in AUTHORITY_FIELDS}
MODEL_ROOTS = frozenset({"torch", "tensorflow", "jax", "transformers", "sentence_transformers",
                         "spacy", "numpy", "sklearn", "onnxruntime", "llama_cpp", "vllm"})
NEW_OWNER_PATHS = (
    "ipfs_datasets_py/logic/legal_ir/canonical_binding_review.py",
    "ipfs_datasets_py/logic/legal_ir/canonical_binding_review_workflow.py",
    "scripts/ops/legal_ir/record_binding_reviews.py",
)
NEW_TEST_PATHS = (
    "tests/unit/logic/legal_ir/test_canonical_binding_review.py",
    "tests/unit/logic/legal_ir/test_canonical_binding_review_workflow.py",
)
HELPER_PATHS = (
    "ipfs_datasets_py/logic/formalization/autoencoder/alignment_richer_review_admission.py",
    "ipfs_datasets_py/logic/formalization/autoencoder/alignment_richer_review_workflow.py",
)
LAUNCH_PARENT_RESOURCE = None


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


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        assert key not in result, "duplicate JSON key: " + key
        result[key] = value
    return result


def reject_nonfinite(value):
    raise ValueError("nonfinite JSON value: " + value)


def read_json(path):
    return json.loads(Path(path).read_bytes().decode("utf-8"), object_pairs_hook=unique_pairs,
                      parse_constant=reject_nonfinite)


def check_checksum(value, key="content_sha256"):
    assert value[key] == digest({name: item for name, item in value.items() if name != key})
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
    def __init__(self):
        self.attempts = []

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".", 1)[0] in MODEL_ROOTS:
            self.attempts.append(fullname)
            raise RuntimeError("model import outside review readiness: " + fullname)
        return None


def zero_masks(value):
    return (type(value) is dict and set(value) == set(MASK_FIELDS)
            and all(type(item) is int and item == 0 for item in value.values()))


def object_keys(value):
    if type(value) is dict:
        return set(value).union(*(object_keys(item) for item in value.values()))
    if type(value) is list:
        return set().union(*(object_keys(item) for item in value))
    return set()


def main():
    started, started_cpu = time.monotonic(), time.process_time()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    resource.setrlimit(resource.RLIMIT_CPU, (60, 65))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    guard = NoModelImports()
    assert not any(name.split(".", 1)[0] in MODEL_ROOTS for name in sys.modules)
    sys.meta_path.insert(0, guard)
    assert not OUTPUT.exists(), "fresh readiness stage required"
    OUTPUT.mkdir(mode=0o700)
    journal_path = OUTPUT / "resource_observations.jsonl"
    journal_path.touch(exist_ok=False)
    snapshots = []

    def observe(label):
        snapshot = {"label": label, "elapsed_wall_seconds": time.monotonic() - started,
                    "resource_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    "linux_current_rss_kib": None, "linux_peak_hwm_kib": None,
                    "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        if Path("/proc/self/status").exists():
            for line in Path("/proc/self/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    snapshot["linux_current_rss_kib"] = int(line.split()[1])
                elif line.startswith("VmHWM:"):
                    snapshot["linux_peak_hwm_kib"] = int(line.split()[1])
        snapshots.append(snapshot)
        with journal_path.open("a", encoding="utf-8") as stream:
            stream.write(raw(snapshot).decode("utf-8") + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        assert time.monotonic() - started < MAX_SECONDS, "readiness wall budget exceeded"
        assert all(snapshot[field] is None or snapshot[field] < MAX_RSS_KIB for field in (
            "resource_ru_maxrss_kib", "linux_current_rss_kib", "linux_peak_hwm_kib")), "readiness worker RSS budget exceeded"

    def observed_read(path, *, sealed=True):
        observe("before_read:" + str(path))
        value = read_json(path)
        if sealed:
            check_checksum(value)
        observe("after_read:" + str(path))
        return value

    observe("initial_fresh_worker_baseline")
    runner_binding = binding(__file__)
    prior_validation_binding = verify({"path": str(PRIOR_VALIDATION), "sha256": PRIOR_VALIDATION_SHA})
    prior = observed_read(PRIOR_VALIDATION)
    observe("before_prior483_hash_verification")
    preserved = [verify(reference) for reference in prior["checked_file_bindings"]]
    assert len(preserved) == len({reference["path"] for reference in preserved}) == prior["checked_file_count"] == 483
    assert all(reference["path"] != str(MAIN_PLAN) for reference in preserved)
    previous_owner_test = [verify(reference) for reference in prior["new_implementation_test_bindings"]]
    assert all(reference in preserved for reference in previous_owner_test)
    frozen_documentation = [verify(reference) for reference in prior["documentation_bindings"]
                            if reference["path"] != str(MAIN_PLAN)]
    historical_main_plan_reference = next(reference for reference in prior["documentation_bindings"]
                                          if reference["path"] == str(MAIN_PLAN))
    observe("after_prior483_hash_verification")
    packet_binding = verify({"path": str(PACKET_PATH), "sha256": PACKET_FILE_SHA})
    packet = observed_read(PACKET_PATH, sealed=False)
    assert digest(packet) == PACKET_CONTENT_SHA
    packet_sha_before = digest(packet)
    private_path = PACKET_DIRECTORY / "organizer_manifest_private.json"
    public_manifest_path = PACKET_DIRECTORY / "reviewer_manifest.json"
    preparation_report_path = PACKET_DIRECTORY / "report.json"
    preparation_plan_path = PACKET_DIRECTORY / "plan.json"
    packet_bindings = [packet_binding] + [binding(path) for path in (
        private_path, public_manifest_path, preparation_report_path, preparation_plan_path)]
    preserved_by_path = {reference["path"]: reference for reference in preserved}
    assert all(reference == preserved_by_path[reference["path"]] for reference in packet_bindings)
    organizer, manifest, preparation_report, preparation_plan = (observed_read(path) for path in (
        private_path, public_manifest_path, preparation_report_path, preparation_plan_path))
    assert manifest["reviewer_payload_binding"] == packet_binding
    assert manifest["item_count"] == 64 and manifest["blank_annotations"] is True
    assert manifest["candidate_reference_blind"] is True and manifest["split_and_group_blind"] is True
    assert manifest["reviewer_submissions_created"] is False
    assert preparation_report["reviewer_payload_binding"] == packet_binding
    assert preparation_report["organizer_manifest_binding"] == binding(private_path)
    assert preparation_report["items"] == 64 and preparation_report["source_groups"] == 16
    assert preparation_report["new_64_reviews_completed"] == 0
    assert preparation_report["semantic_gold_created"] is False
    assert preparation_plan["source_group_assignments_frozen_before_annotation"] is True
    assert preparation_plan["sealed_final_test_created"] is False
    assert preparation_plan["source_author_independence_authenticated"] is False
    assert preparation_plan["previously_exposed_compositions_possible"] is True
    assert len(packet["items"]) == len(organizer["rows"]) == 64
    public_by_id = {item["item_id"]: item for item in packet["items"]}
    private_by_id = {row["item_id"]: row for row in organizer["rows"]}
    assert len(public_by_id) == len(private_by_id) == 64 and set(public_by_id) == set(private_by_id)
    assert len({item["source_sha256"] for item in packet["items"]}) == 64
    assert len({item["input_sha256"] for item in packet["items"]}) == 64
    annotation_fields = {"interpretation_status", "ambiguity", "unsupported_meaning", "normative_rules",
                         "freeform_qualifier_scope", "notes", "reviewer_id", "reviewed_at_utc"}
    joins = []
    for identity, item in public_by_id.items():
        metadata = private_by_id[identity]
        assert set(item) == {"item_id", "source_text", "source_sha256", "input_sha256", "context", "annotation"}
        assert set(item["annotation"]) == annotation_fields
        assert all(value is None for value in item["annotation"].values())
        assert item["source_sha256"] == metadata["source_sha256"] == text_sha(item["source_text"])
        assert item["context"] == {"role": "none_required", "text": "", "bindings": {}, "sha256": text_sha("")}
        assert item["input_sha256"] == metadata["input_sha256"] == digest({"source_text": item["source_text"], "context": item["context"]})
        assert identity == "binding-review-item-" + hashlib.sha256(
            b"authored-binding-review-v1\0" + bytes.fromhex(item["input_sha256"])).hexdigest()[:24]
        assert zero_masks(metadata["masks"])
        assert metadata["review_status"] == "pending" and metadata["semantic_gold_created"] is False
        assert metadata["natural_source"] is False and metadata["source_origin"] == "programmatically_authored_controlled_English_fixture"
        prefix, actor_index, pair_index = metadata["group_id"].split(":")
        assert prefix == "authored-binding-composition-v1" and actor_index in ("0", "1", "2", "3") and pair_index in ("0", "1", "2", "3")
        expected_split = "proposed_train" if (int(actor_index) - int(pair_index)) % 4 in (0, 1) else "proposed_development"
        assert metadata["proposed_split"] == expected_split
        assert type(metadata["variant_index"]) is int and 0 <= metadata["variant_index"] <= 3
        joins.append({"item_id": identity, "source_sha256": item["source_sha256"],
                      "context_sha256": item["context"]["sha256"], "input_sha256": item["input_sha256"],
                      "immutable_envelope_sha256": digest({name: value for name, value in item.items() if name != "annotation"}),
                      "group_id": metadata["group_id"], "proposed_split": metadata["proposed_split"],
                      "variant_index": metadata["variant_index"], "masks": metadata["masks"],
                      "blank_annotation": True, "review_status": "pending"})
    joins.sort(key=lambda row: row["item_id"])
    group_counts = Counter(row["group_id"] for row in joins)
    split_counts = Counter(row["proposed_split"] for row in joins)
    assert len(group_counts) == 16 and set(group_counts.values()) == {4}
    assert split_counts == {"proposed_train": 32, "proposed_development": 32}
    assert all({row["variant_index"] for row in joins if row["group_id"] == group} == {0, 1, 2, 3}
               for group in group_counts)
    assert organizer["model_candidates_included"] is False and organizer["original_reviews_completed"] == 0
    organizer_sha_before = digest(organizer)
    new_implementation_test_bindings = [binding(REPO / path) for path in (*NEW_OWNER_PATHS, *NEW_TEST_PATHS)]
    helper_bindings = [binding(REPO / path) for path in HELPER_PATHS]
    assert all(reference == preserved_by_path[reference["path"]] for reference in helper_bindings)
    join_binding = save(OUTPUT / "packet_joins_private.json", seal({
        "schema": "alignment-binding-review-readiness-private-joins/v1", "organizer_private": True,
        "packet_binding": packet_binding, "organizer_manifest_binding": binding(private_path),
        "item_count": 64, "source_groups": 16, "proposed_split_counts": dict(split_counts),
        "rows": joins, "source_group_assignments_frozen_before_annotation": True,
        "group_and_split_metadata_supplied_to_recording_api": False, **FALSE_FLAGS}))
    plan_binding = save(OUTPUT / "plan.json", seal({
        "schema": "alignment-binding-review-recording-readiness-plan/v1", "runner_binding": runner_binding,
        "prior_validation_binding": prior_validation_binding, "preserved_prior_checked_file_count": 483,
        "previous_new_owner_test_bindings": previous_owner_test,
        "previous_new_owner_test_bindings_already_in_prior483": True,
        "frozen_documentation_bindings": frozen_documentation,
        "mutable_main_plan_historical_reference": historical_main_plan_reference,
        "mutable_main_plan_file_accessed": False,
        "packet_bindings": packet_bindings, "packet_file_sha256": PACKET_FILE_SHA,
        "reviewer_packet_sha256": PACKET_CONTENT_SHA, "private_join_binding": join_binding,
        "new_implementation_test_bindings": new_implementation_test_bindings, "helper_bindings": helper_bindings,
        "workflow": "canonical_binding_review_workflow.run_binding_review_recording",
        "workflow_output_directory": str(OUTPUT / "recording"), "submission_bindings": [],
        "expected_item_count": 64, "expected_status_counts": {"pending": 64},
        "actual_reviews_to_generate": 0, "reviewer_identities_to_generate": 0,
        "adjudications_to_generate": 0, "semantic_targets_to_generate": 0,
        "all_fit_and_evaluation_masks": "zero_before_and_after_recording",
        "recording_api_inputs": "public_blank_packet_only_no_organizer_groups_splits_candidates_or_targets",
        "public_submission_guide": "neutral_contract_only_no_completed_examples_or_source_specific_answers",
        "interpretation_scope": "workflow_readiness_only_not_review_authentication_or_semantic_admission",
        "model_calls": 0, "provider_calls": 0, "encoder_calls": 0, "prover_calls": 0,
        "optimizer_updates": 0, "profile_fit_calls": 0, "candidate_redecoding_calls": 0,
        "resource_measurement_scope": "fresh_forked_static_worker",
        "launch_parent_resource_observation": LAUNCH_PARENT_RESOURCE,
        "wall_limit_seconds": MAX_SECONDS, "cpu_limit_seconds": [60, 65], "rss_limit_kib": MAX_RSS_KIB,
        "started_utc": started_utc, **FALSE_FLAGS}))
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.legal_ir import canonical_binding_review as adapter
    from ipfs_datasets_py.logic.legal_ir import canonical_binding_review_workflow as workflow

    assert Path(adapter.__file__) == REPO / NEW_OWNER_PATHS[0]
    assert Path(workflow.__file__) == REPO / NEW_OWNER_PATHS[1]
    preparation_validation = adapter.validate_blank_packet(packet, expected_packet_sha256=PACKET_CONTENT_SHA)
    assert preparation_validation["reviewer_packet_sha256"] == PACKET_CONTENT_SHA
    assert preparation_validation["item_count"] == 64
    observe("before_real_workflow_zero_submission_call")
    workflow_report = workflow.run_binding_review_recording(
        packet_path=PACKET_PATH, expected_packet_file_sha256=PACKET_FILE_SHA,
        submission_bindings=[], output_directory=OUTPUT / "recording", repository_root=REPO)
    observe("after_real_workflow_zero_submission_call")
    workflow_report_binding = binding(OUTPUT / "recording/report_private.json")
    saved_workflow_report = observed_read(workflow_report_binding["path"])
    assert raw(saved_workflow_report) == raw(workflow_report)
    assert workflow_report["packet_binding"] == packet_binding
    assert workflow_report["submission_bindings"] == [] and workflow_report["submission_count"] == 0
    assert workflow_report["organizer_manifest_accessed"] is False
    assert workflow_report["candidate_or_reference_accessed"] is False
    assert workflow_report["source_only_packet"] is True
    for reference in workflow_report["source_bindings"]:
        assert reference in new_implementation_test_bindings + helper_bindings
        verify(reference)
    receipt_binding = verify(workflow_report["receipt_binding"])
    guide_binding = verify(workflow_report["submission_guide_binding"])
    receipt = observed_read(receipt_binding["path"], sealed=False)
    check_checksum(receipt, "receipt_sha256")
    guide = observed_read(guide_binding["path"], sealed=False)
    saved_validation = adapter.validate_recording(receipt, packet, [], expected_packet_sha256=PACKET_CONTENT_SHA)
    assert raw(saved_validation) == raw(workflow_report["recording_validation"])
    assert raw(guide) == raw(adapter.submission_guide())
    assert receipt["item_count"] == len(receipt["items"]) == 64
    assert receipt["status"] == "pending" and receipt["submission_count"] == 0
    assert receipt["submissions"] == [] and receipt["status_counts"]["pending"] == 64
    assert all(value == 0 for key, value in receipt["status_counts"].items() if key != "pending")
    assert all(type(value) is int and value == 0 for value in receipt["interpretation_status_counts"].values())
    assert zero_masks(receipt["masks"]) and zero_masks(saved_validation["masks"])
    assert all(type(receipt[field]) is int and receipt[field] == 0 for field in (
        "declared_completed_annotation_count", "human_reviews_authenticated", "independent_reviews_authenticated",
        "qualified_training_pairs", "model_calls", "provider_calls", "encoder_calls", "prover_calls"))
    assert [row["item_id"] for row in receipt["items"]] == sorted(public_by_id)
    receipt_joins = []
    for row in receipt["items"]:
        original = public_by_id[row["item_id"]]
        envelope = {name: value for name, value in original.items() if name != "annotation"}
        assert all(row[name] == value for name, value in envelope.items())
        assert row["review_input_envelope_sha256"] == digest(envelope)
        assert row["status"] == "pending" and row["consensus_interpretation_status"] is None
        assert all(type(row[field]) is int and row[field] == 0 for field in (
            "complete_declaration_count", "pending_declaration_count", "meaning_signature_count"))
        assert row["received_declarations"] == [] and zero_masks(row["masks"])
        assert row["external_adjudication_status"] == "pending" and row["independent_adjudication_completed"] is False
        assert all(row[field] is False for field in AUTHORITY_FIELDS)
        receipt_joins.append({"item_id": row["item_id"], "source_sha256": row["source_sha256"],
                              "input_sha256": row["input_sha256"], "review_input_envelope_sha256": row["review_input_envelope_sha256"],
                              "status": row["status"], "masks": row["masks"]})
    assert all(all(value[field] is False for field in AUTHORITY_FIELDS) for value in (receipt, saved_validation, guide))
    forbidden_public_keys = {"canonical_ir", "proposal", "target", "reference", "expected_answer",
                             "group_id", "proposed_split", "variant_index", "actor_surface",
                             "action_surface", "object_surface", "organizer_manifest_sha256"}
    assert not forbidden_public_keys.intersection(object_keys(guide))
    encoded_guide = raw(guide).decode("utf-8")
    assert all(row["group_id"] not in encoded_guide and row["proposed_split"] not in encoded_guide for row in joins)
    assert all(item["source_text"] not in encoded_guide for item in packet["items"])
    assert guide["generated_reviews"] == 0 and guide["submissions_created"] is False
    assert receipt["authored_reference_scoring_executed"] is False
    assert receipt["candidate_aware_computation"] is False and receipt["reference_used_to_resolve_disputes"] is False
    assert receipt["automatic_adjudication"] is False and receipt["training_executed"] is False
    assert digest(packet) == packet_sha_before and digest(organizer) == organizer_sha_before
    assert all(all(value is None for value in item["annotation"].values()) for item in packet["items"])
    observe("before_final_immutable_file_verification")
    for reference in preserved + previous_owner_test + frozen_documentation + packet_bindings + helper_bindings + new_implementation_test_bindings + [
            runner_binding, prior_validation_binding, join_binding, plan_binding, workflow_report_binding, receipt_binding, guide_binding]:
        verify(reference)
    assert guard.attempts == []
    assert not any(name.split(".", 1)[0] in MODEL_ROOTS for name in sys.modules)
    observe("final_fresh_worker_resource_observation")
    journal_binding = binding(journal_path)
    report = seal({
        "schema": "alignment-binding-review-recording-readiness-report/v1", "status": "completed_zero_submission_readiness",
        "runner_binding": runner_binding, "plan_binding": plan_binding,
        "prior_validation_binding": prior_validation_binding, "source_bindings": preserved,
        "preserved_prior_checked_file_count": 483, "previous_new_owner_test_bindings": previous_owner_test,
        "previous_new_owner_test_bindings_already_in_prior483": True,
        "new_implementation_test_bindings": new_implementation_test_bindings, "helper_bindings": helper_bindings,
        "frozen_documentation_bindings": frozen_documentation,
        "mutable_main_plan_historical_reference": historical_main_plan_reference,
        "mutable_main_plan_file_accessed": False, "mutable_main_plan_preservation_required": False,
        "packet_bindings": packet_bindings, "packet_file_sha256": PACKET_FILE_SHA,
        "reviewer_packet_sha256": PACKET_CONTENT_SHA, "private_join_binding": join_binding,
        "workflow_report_binding": workflow_report_binding, "receipt_binding": receipt_binding,
        "public_submission_guide_binding": guide_binding,
        "packet_preparation_validation": preparation_validation, "saved_recording_validation": saved_validation,
        "input_item_count": 64, "exact_source_context_input_receipt_joins": receipt_joins,
        "exact_source_context_input_receipt_join_count": 64,
        "source_groups": 16, "variants_per_group": 4, "proposed_split_counts": dict(split_counts),
        "wrapper_organizer_manifest_accessed_for_private_joins": True,
        "workflow_organizer_manifest_accessed": False,
        "group_and_split_metadata_supplied_to_recording_api": False,
        "public_guide_contains_private_group_split_values": False,
        "public_guide_contains_candidates_or_source_specific_answers": False,
        "submission_count": 0, "actual_reviews_created": 0, "declared_completed_annotation_count": 0,
        "human_reviews_authenticated": 0, "independent_reviews_authenticated": 0,
        "reviewer_identity_attestations_created": False, "adjudications_completed": 0,
        "status_counts": receipt["status_counts"], "interpretation_status_counts": receipt["interpretation_status_counts"],
        "blank_original_annotation_count": 64, "all320_receipt_mask_values_zero": True,
        "all320_organizer_draft_mask_values_zero": True, "masks": {name: 0 for name in MASK_FIELDS},
        "workflow_runs": 1, "saved_receipt_validation_runs": 1,
        "receipt_exact_public_validator_recomputation": True,
        "original_packet_and_organizer_objects_unchanged": True, "prior_file_bindings_unchanged": True,
        "candidate_reference_payloads_supplied_to_recording": False,
        "query_reference_used_to_establish_meaning": False,
        "model_calls": 0, "provider_calls": 0, "encoder_calls": 0, "prover_calls": 0,
        "optimizer_updates": 0, "profile_fit_calls": 0, "candidate_redecoding_calls": 0,
        "model_import_attempts": guard.attempts, "model_execution_stacks_loaded": [],
        "training_executed": False, "automatic_adjudication": False, "submissions_created": False,
        "natural_source_corpus": False, "previously_exposed_compositions_possible": True,
        "independent_blind_quality_study": False, "sealed_final_test_created": False,
        "interpretation_scope": "static_zero_submission_workflow_readiness_only",
        "dependency_binding_scope": "483_prior_campaign_files_plus_explicit_new_owners_helpers_and_tests_not_all_Python_imports",
        "resource_journal_binding": journal_binding, "resource_observations": snapshots,
        "resource_measurement_scope": "fresh_forked_static_worker", "launch_parent_resource_observation": LAUNCH_PARENT_RESOURCE,
        "wall_seconds": time.monotonic() - started, "cpu_seconds": time.process_time() - started_cpu,
        "worker_resource_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "worker_linux_current_rss_kib": snapshots[-1]["linux_current_rss_kib"],
        "worker_linux_peak_hwm_kib": snapshots[-1]["linux_peak_hwm_kib"],
        "wall_limit_seconds": MAX_SECONDS, "cpu_limit_seconds": [60, 65], "rss_limit_kib": MAX_RSS_KIB,
        "runtime_python_executable": sys.executable, "runtime_python_version": sys.version,
        "started_utc": started_utc, "finished_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **FALSE_FLAGS})
    report_binding = save(OUTPUT / "report_private.json", report)
    print(json.dumps({"report_binding": report_binding, "receipt_binding": receipt_binding,
                      "public_submission_guide_binding": guide_binding, "item_count": 64,
                      "submission_count": 0, "status_counts": report["status_counts"],
                      "wall_seconds": report["wall_seconds"], "cpu_seconds": report["cpu_seconds"],
                      "worker_resource_ru_maxrss_kib": report["worker_resource_ru_maxrss_kib"],
                      "worker_linux_peak_hwm_kib": report["worker_linux_peak_hwm_kib"]}, sort_keys=True))


if __name__ == "__main__":
    LAUNCH_PARENT_RESOURCE = {"pid": os.getpid(),
                              "resource_ru_maxrss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                              "resource_measurement_scope": "launcher_before_fresh_worker_fork"}
    worker_pid = os.fork()
    if worker_pid:
        _, worker_status = os.waitpid(worker_pid, 0)
        raise SystemExit(os.waitstatus_to_exitcode(worker_status))
    main()
    sys.stdout.flush()
    os._exit(0)
