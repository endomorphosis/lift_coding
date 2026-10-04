"""Prepare separate weak TRAIN byte supervision and target-free source inputs."""

import copy
import hashlib
import json
import resource
import sys
import time
from collections import Counter
from pathlib import Path

ROOT = Path("/home/barberb/lift_coding")
REPO = ROOT / "external/ipfs_datasets"
CAMPAIGN = ROOT / "artifacts/autoformalization-alignment-20261003"
OUTPUT = CAMPAIGN / "canonical-codec-01"
OUTPUT_CAP = 4096
MAX_SECONDS = 120
MAX_RSS_KIB = 1024 * 1024
BLOCKED_STACKS = frozenset({"torch", "tensorflow", "jax", "transformers", "sentence_transformers",
                            "spacy", "sklearn", "numpy", "llama_cpp"})
PROPOSAL_FALSE_FIELDS = ("target_access", "model_executed", "source_fidelity_established",
                         "qualified", "proof_authority", "accepted")
MASK_FIELDS = ("weak_decoder_fit", "strong_semantic_fit", "contrastive_supervision", "proof_supervision",
               "fidelity_evaluation")
RETAINED_PATH = REPO / "workspace/learned-formula-staging/smoke-final-20260930/checkpoint.json"
RETAINED_SHA = "4876186f4a5fe3957640a2cff1a4e1b2046bc945d24e08d244973e641733384e"


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(raw(value)).hexdigest()


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


def load(path):
    return json.loads(Path(path).read_bytes())


def verified_record(path):
    value = load(path)
    assert value["content_sha256"] == digest({key: item for key, item in value.items()
                                             if key != "content_sha256"}), str(path)
    return value


def seal(value):
    value["content_sha256"] = digest(value)
    return value


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return binding(path)


def proposal_from_grounding(grounding, codec):
    assert grounding["outcome"] == "grounded_candidate"
    return {"schema": codec.PROPOSAL_SCHEMA, "source_sha256": grounding["preflight"]["source_sha256"],
            "canonical_ir": copy.deepcopy(grounding["canonical_ir"]), "anchors": copy.deepcopy(grounding["anchors"]),
            "facet_operators": copy.deepcopy(grounding["facet_operators"]),
            "single_rule_scope": grounding["single_rule_scope"],
            **{field: False for field in PROPOSAL_FALSE_FIELDS}}


def static_codec_assessment(codec, examples, legacy):
    rows = []
    for example in examples:
        source_oov = sorted(set(legacy._source_tokens(example["source_text"])) - set(codec["source_vocabulary"]))
        rule = legacy._rule(example["canonical_ir"])
        target_oov = [{"facet": field, "canonical_symbol": atom}
                      for field in legacy.FIELDS
                      for atom in (rule[field] if field in legacy.QUALIFIERS else [rule[field]])
                      if legacy._atom(field, atom) not in codec["target_vocabulary"]]
        item = {"id": example["id"], "source_compatible": False, "target_compatible": False,
                "source_token_count": None, "target_token_count": None,
                "source_failure": None, "target_failure": None,
                "source_oov_tokens": source_oov, "target_oov_typed_symbols": target_oov}
        try:
            source_ids = legacy.encode_source(codec, example["source_text"])
        except legacy.CodecError as error:
            item["source_failure"] = str(error)
        else:
            item.update(source_compatible=True, source_token_count=len(source_ids))
        try:
            target_ids = legacy.encode_target(codec, example["canonical_ir"])
        except legacy.CodecError as error:
            item["target_failure"] = str(error)
        else:
            assert legacy.decode_target(codec, target_ids) == example["canonical_ir"]
            item.update(target_compatible=True, target_token_count=len(target_ids))
        rows.append(item)
    return {"scope": "static_canonical_ir_and_casefold_source_token_transport_only_no_exact_anchor_output",
            "model_loaded": False, "learned_generation_executed": False,
            "source_compatible_count": sum(row["source_compatible"] for row in rows),
            "target_compatible_count": sum(row["target_compatible"] for row in rows),
            "rows": rows, "source_fidelity_established": False, "qualified": False, "proof_authority": False}


def main():
    started = time.monotonic()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    resource.setrlimit(resource.RLIMIT_CPU, (60, 65))

    def admission():
        assert time.monotonic() - started < MAX_SECONDS, "preparation wall budget exceeded"
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < MAX_RSS_KIB, "preparation RSS budget exceeded"

    class NoModelStacks:
        attempts = []

        def find_spec(self, fullname, path=None, target=None):
            if fullname.partition(".")[0] in BLOCKED_STACKS:
                self.attempts.append(fullname)
                raise ImportError("model stack forbidden in deterministic codec preparation: " + fullname)
            return None

    blocker = NoModelStacks()
    sys.meta_path.insert(0, blocker)
    prior_path = CAMPAIGN / "preflight-decoder-validation-01/validation.json"
    prior = verified_record(prior_path)
    preserved = [verify(ref) for ref in prior["checked_file_bindings"]]
    assert len(preserved) == prior["checked_file_count"] == 311
    extra_prior_bindings = [verify(ref) for ref in prior["new_implementation_test_bindings"]]
    manifest_path = CAMPAIGN / "grounding-01/request_manifest.json"
    construction_path = CAMPAIGN / "grounding-01/constructed_receipts.json"
    panel_path = CAMPAIGN / "richer-01/panel.json"
    review_path = CAMPAIGN / "richer-review-admission-02/receipt_private.json"
    inputs_path = CAMPAIGN / "richer-embedding-01/embedding_inputs.json"
    manifest, construction = verified_record(manifest_path), verified_record(construction_path)
    inputs, panel, reviews = load(inputs_path), load(panel_path), load(review_path)
    assert reviews["item_count"] == 34 and reviews["status_counts"]["pending"] == 34
    assert reviews["declared_completed_annotation_count"] == reviews["submission_count"] == 0
    assert reviews["independent_fidelity_available"] is False
    # Only identities, partition/group metadata and source hashes are queried
    # from this authored panel; authored canonical target values are never used.
    panel_metadata = [{key: row[key] for key in ("id", "input_sha256", "source_sha256", "group_id", "split", "row_kind")}
                      for row in panel["rows"]]
    del panel
    metadata_by_input = {row["input_sha256"]: row for row in panel_metadata}
    source_by_id = {row["id"]: row for row in inputs["rows"]}
    request_by_id = {row["id"]: row for row in manifest["rows"]}
    grounded_by_id = {row["id"]: row for row in construction["rows"]}
    assert len(metadata_by_input) == len(source_by_id) == len(request_by_id) == len(grounded_by_id) == 34
    assert set(source_by_id) == set(request_by_id) == set(grounded_by_id)
    train_metadata = [row for row in panel_metadata if row["split"] == "train"]
    dev_metadata = [row for row in panel_metadata if row["split"] == "validation"]
    assert len(train_metadata) == 16 and len(dev_metadata) == 18
    for field in ("id", "input_sha256", "source_sha256", "group_id"):
        assert {row[field] for row in train_metadata}.isdisjoint({row[field] for row in dev_metadata}), field
    assert all(row["row_kind"] == "positive" for row in train_metadata)
    assert sum(row["row_kind"] == "positive" for row in dev_metadata) == 8
    lane_paths = {name: CAMPAIGN / f"richer-embedding-01/{name}_embeddings.json"
                  for name in ("legacy8", "native384", "native768")}
    input_bindings = [binding(path) for path in (prior_path, manifest_path, construction_path, panel_path,
                                                review_path, inputs_path, *lane_paths.values())]
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_richer_embeddings as embeddings,
    )
    from ipfs_datasets_py.logic.legal_ir import canonical_byte_codec as codec
    from ipfs_datasets_py.logic.legal_ir import canonical_source_grounding as grounding
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_codec as legacy
    embeddings.validate_richer_embedding_inputs(inputs)
    lanes = {name: load(path) for name, path in lane_paths.items()}
    for lane in lanes.values():
        embeddings.validate_embedding_lane(lane, inputs)
        assert lane["status"] == "produced"
    lanes_by_id = {name: {row["id"]: row for row in lane["receipts"]} for name, lane in lanes.items()}
    implementation_bindings = [binding(module.__file__) for module in (codec, grounding, legacy, embeddings)]
    retained_binding = verify({"path": str(RETAINED_PATH), "bytes": 2826559, "sha256": RETAINED_SHA})
    retained = load(RETAINED_PATH)
    implementation_paths = {
        "canonical_contracts.py": REPO / "ipfs_datasets_py/logic/legal_ir/canonical_contracts.py",
        "legal_formula_codec.py": Path(legacy.__file__),
        "legal_formula_learning.py": REPO / "ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_formula_learning.py",
        "legal_ir_grammar_decoder.py": REPO / "ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_ir_grammar_decoder.py",
        "tree_pin.py": REPO / "ipfs_datasets_py/logic/autoformal/tree_pin.py",
    }
    retained_implementation_bindings = [verify({"path": str(implementation_paths[name]), "sha256": checksum})
                                        for name, checksum in retained["implementation"]["files"].items()]
    legacy.validate_codec(retained["codec"])
    assert codec.VOCAB_SIZE == 259 and codec.PAD_ID == 0 and codec.BOS_ID == 1 and codec.EOS_ID == 2
    assert codec.BYTE_OFFSET == 3
    OUTPUT.mkdir(exist_ok=False)
    plan_binding = save(OUTPUT / "plan.json", seal({
        "schema": "alignment-canonical-byte-preparation-plan/v1", "runner_binding": binding(__file__),
        "input_bindings": input_bindings, "implementation_bindings": implementation_bindings,
        "retained_checkpoint_binding": retained_binding, "retained_implementation_bindings": retained_implementation_bindings,
        "preserved_prior_binding_count": len(preserved), "extra_prior_bindings": extra_prior_bindings,
        "rows": 34, "training_weak_rows": 16, "development_positive_denominator": 8,
        "output_cap": OUTPUT_CAP, "output_cap_origin": "fixed_opt_in_policy_before_development_capacity_measurement",
        "development_previously_exposed": True, "output_cap_selected_by_training_algorithm": False,
        "alphabet_origin": "fixed_256_UTF8_bytes_plus_PAD_BOS_EOS_no_corpus_fitting",
        "train_capacity_checked_before_development": True,
        "weak_label_origin": "source_parser_derived_with_frozen_TRAIN_supervised_atom_catalog",
        "upstream_vocabulary_provenance": manifest["vocabulary_provenance"],
        "upstream_vocabulary_sha256": manifest["vocabulary_sha256"],
        "review_state": "all_34_pending_no_semantic_authority", "target_free_input_lane_dimensions": [8, 384, 768],
        "model_calls": 0, "encoder_calls": 0, "prover_calls": 0, "neural_training_calls": 0,
        "max_seconds": MAX_SECONDS, "max_rss_kib": MAX_RSS_KIB, "cpu_limit_seconds": [60, 65],
        "rss_guard_is_hard_limit": False, "started_utc": started_utc,
        "qualified": False, "source_fidelity_established": False, "proof_authority": False}))
    inference_rows, outcome_rows, proposal_records = [], [], {}
    for source in inputs["rows"]:
        admission()
        identity = source["id"]
        request, ground = request_by_id[identity], grounded_by_id[identity]["grounding"]
        metadata = metadata_by_input[source["input_sha256"]]
        assert identity == "sha256:" + metadata["input_sha256"]
        assert metadata["source_sha256"] == request["source_sha256"] == source["source_sha256"]
        assert request["source_text"] == source["source_text"]
        assert grounded_by_id[identity]["source_sha256"] == source["source_sha256"]
        grounding.validate_grounded_source(ground)
        row_embeddings = {}
        for name, lane in lanes.items():
            receipt = lanes_by_id[name][identity]
            assert receipt["input_sha256"] == source["input_sha256"]
            assert receipt["source_sha256"] == source["source_sha256"]
            assert receipt["embedding_sha256"] == digest(receipt["embedding"])
            row_embeddings[name] = {"dimension": lane["dimension"], "profile_id": lane["backend_evidence"]["profile_id"],
                "embedding": copy.deepcopy(receipt["embedding"]), "embedding_sha256": receipt["embedding_sha256"],
                "token_input_sha256": receipt["token_input_sha256"], "backend_input_id": receipt["backend_input_id"],
                "input_recipe": lane["input_recipe"], "context_applied": False,
                "representation_kind": "raw_linguistic_features" if name == "legacy8" else "raw_model_embedding"}
        inference_rows.append({"id": identity, "input_sha256": source["input_sha256"],
            "source_sha256": source["source_sha256"], "source_text": source["source_text"],
            "context_text": request["declared_context"]["text"],
            "context_sha256": request["declared_context"]["sha256"],
            "requires_context_resolution": request["requires_context_resolution"],
            "context_applied": False, "embeddings": row_embeddings})
        fit = int(metadata["split"] == "train" and ground["outcome"] == "grounded_candidate")
        masks = {field: 0 for field in MASK_FIELDS}
        masks["weak_decoder_fit"] = fit
        outcome_rows.append({"id": identity, "authored_row_id": metadata["id"], "group_id": metadata["group_id"],
            "split": metadata["split"], "row_kind": metadata["row_kind"], "source_sha256": source["source_sha256"],
            "grounding_outcome": ground["outcome"], "review_status": "pending", "masks": masks,
            "source_grounding_sha256": ground["content_sha256"], "candidate_supervision_available": bool(fit),
            "negative_gold_sequence_created": False, "source_fidelity_established": False,
            "qualified": False, "proof_authority": False})
        if ground["outcome"] == "grounded_candidate":
            proposal_records[identity] = {"proposal": proposal_from_grounding(ground, codec),
                "source_text": source["source_text"], "metadata": metadata,
                "source_grounding_sha256": ground["content_sha256"]}
    assert len(proposal_records) == 22
    assert sum(row["masks"]["weak_decoder_fit"] for row in outcome_rows) == 16
    inference_binding = save(OUTPUT / "target_free_inputs.json", seal({
        "schema": "alignment-canonical-byte-target-free-inputs/v1", "row_count": 34,
        "source_recipe": "exact_source_only_vectors_and_declared_unresolved_context",
        "lane_bindings": {name: binding(path) for name, path in lane_paths.items()},
        "rows": inference_rows, "contains_canonical_ir": False, "contains_target_token_ids": False,
        "training_executed": False, "source_fidelity_established": False, "qualified": False, "proof_authority": False}))
    outcome_binding = save(OUTPUT / "all_request_outcomes.json", seal({
        "schema": "alignment-canonical-byte-preparation-outcomes/v1", "row_count": 34, "rows": outcome_rows,
        "review_binding": binding(review_path), "source_fidelity_established": False,
        "qualified": False, "proof_authority": False}))
    train_ids = [row["id"] for row in outcome_rows if row["split"] == "train"]
    dev_ids = [row["id"] for row in outcome_rows if row["split"] == "validation" and row["id"] in proposal_records]
    assert len(train_ids) == 16 and len(dev_ids) == 6
    encoded_records = {}
    # Finish and freeze all TRAIN capacity/supervision before examining DEV capacity.
    for split_ids in (train_ids, dev_ids):
        for identity in split_ids:
            item = proposal_records[identity]
            proposal, source_text = item["proposal"], item["source_text"]
            codec.validate_proposal(proposal, source_text)
            ids = codec.encode_proposal(proposal, source_text, output_cap=OUTPUT_CAP)
            decoded = codec.decode_proposal(ids, source_text, output_cap=OUTPUT_CAP)
            assert raw(decoded) == raw(proposal)
            assert ids[0] == codec.BOS_ID and ids[-1] == codec.EOS_ID and codec.PAD_ID not in ids
            wire_bytes = bytes(value - codec.BYTE_OFFSET for value in ids[1:-1])
            wire = json.loads(wire_bytes)
            assert raw(wire) == wire_bytes and wire["schema"] == codec.WIRE_SCHEMA
            inspected = codec.inspect_encoding(proposal, source_text, output_cap=OUTPUT_CAP)
            old_ceiling = codec.inspect_encoding(proposal, source_text, output_cap=512)
            encoded_records[identity] = {"id": identity, "group_id": item["metadata"]["group_id"],
                "source_sha256": proposal["source_sha256"], "source_grounding_sha256": item["source_grounding_sha256"],
                "proposal": proposal, "proposal_sha256": digest(proposal), "byte_token_ids": ids,
                "byte_token_ids_sha256": digest(ids), "byte_token_count_including_BOS_EOS": len(ids),
                "wire_utf8_bytes": len(wire_bytes), "full_public_proposal_json_bytes": len(raw(proposal)),
                "canonical_ir_only_json_bytes": len(raw(proposal["canonical_ir"])),
                "inspection": inspected, "same_numeric_512_ceiling_new_byte_unit_inspection": old_ceiling,
                "lossless_full_proposal_roundtrip": True, "roundtrip_scope": "output_transport_integrity_only",
                "weak_label_origin": "source_parser_derived_with_frozen_TRAIN_supervised_atom_catalog",
                "independent_semantic_review_completed": False, "source_fidelity_established": False,
                "qualified": False, "proof_authority": False}
        if split_ids is train_ids:
            train_group_counts = Counter(proposal_records[identity]["metadata"]["group_id"] for identity in train_ids)
            supervision_binding = save(OUTPUT / "train_weak_supervision.json", seal({
                "schema": "alignment-canonical-byte-weak-supervision/v1", "split": "train", "row_count": 16,
                "target_free_input_binding": inference_binding, "output_cap": OUTPUT_CAP,
                "rows": [{**encoded_records[identity], "masks": {**{field: 0 for field in MASK_FIELDS}, "weak_decoder_fit": 1},
                          "group_loss_weight": 1.0 / train_group_counts[proposal_records[identity]["metadata"]["group_id"]],
                          "next_token_loss_mask": [1] * (len(encoded_records[identity]["byte_token_ids"]) - 1),
                          "next_token_loss_mask_scope": "weak_bytes_and_EOS_excludes_BOS_no_padding"}
                         for identity in train_ids], "neural_training_executed": False,
                "source_fidelity_established": False, "qualified": False, "proof_authority": False}))
    dev_binding = save(OUTPUT / "development_transport_diagnostics.json", seal({
        "schema": "alignment-canonical-byte-development-transport/v1", "split": "validation",
        "positive_denominator": 8, "constructed_candidate_count": 6, "unavailable_positive_count": 2,
        "rows": [{**encoded_records[identity], "masks": {field: 0 for field in MASK_FIELDS}} for identity in dev_ids],
        "training_or_checkpoint_selection_allowed": False, "model_inference_executed": False,
        "source_fidelity_established": False, "qualified": False, "proof_authority": False}))
    train_examples = [{"id": identity, "source_text": proposal_records[identity]["source_text"],
                       "canonical_ir": proposal_records[identity]["proposal"]["canonical_ir"]} for identity in train_ids]
    all_examples = train_examples + [{"id": identity, "source_text": proposal_records[identity]["source_text"],
                                     "canonical_ir": proposal_records[identity]["proposal"]["canonical_ir"]}
                                    for identity in dev_ids]
    refitted_codec = legacy.fit_codec(train_examples)
    typed_codec_binding = save(OUTPUT / "train_refitted_typed_atom_codec.json", refitted_codec)
    refitted_assessment = static_codec_assessment(refitted_codec, all_examples, legacy)
    retained_assessment = static_codec_assessment(retained["codec"], all_examples, legacy)
    baseline_binding = save(OUTPUT / "existing_codec_static_baselines.json", seal({
        "schema": "alignment-canonical-byte-existing-codec-comparison/v1",
        "train_refitted_codec_binding": typed_codec_binding, "train_refit_example_ids": train_ids,
        "train_refitted_codec_sha256": digest(refitted_codec), "train_source_vocabulary_sha256": digest(refitted_codec["source_vocabulary"]),
        "train_target_vocabulary_sha256": digest(refitted_codec["target_vocabulary"]),
        "train_refitted_no_neural_checkpoint": refitted_assessment,
        "retained_checkpoint_binding": retained_binding, "retained_lineage": retained["lineage_id"],
        "retained_implementation_bindings": retained_implementation_bindings,
        "retained_checkpoint_unmodified_codec": retained_assessment,
        "source_fidelity_established": False, "qualified": False, "proof_authority": False}))
    assert not blocker.attempts
    assert not (set(sys.modules) & BLOCKED_STACKS)
    for reference in preserved + extra_prior_bindings + input_bindings + implementation_bindings + retained_implementation_bindings + [retained_binding]:
        verify(reference)
    loaded_modules = []
    for name, module in sorted(sys.modules.items()):
        module_path = getattr(module, "__file__", None)
        if module_path and Path(module_path).is_relative_to(REPO) and Path(module_path).is_file():
            loaded_modules.append({"module_name": name, **binding(module_path)})
    capacities = {}
    for split_name, split_ids in (("train", train_ids), ("validation", dev_ids)):
        rr = [encoded_records[identity] for identity in split_ids]
        capacities[split_name] = {"rows": len(rr), "full_roundtrips": len(rr),
            "min_byte_tokens_including_BOS_EOS": min(row["byte_token_count_including_BOS_EOS"] for row in rr),
            "max_byte_tokens_including_BOS_EOS": max(row["byte_token_count_including_BOS_EOS"] for row in rr),
            "min_full_proposal_json_bytes": min(row["full_public_proposal_json_bytes"] for row in rr),
            "max_full_proposal_json_bytes": max(row["full_public_proposal_json_bytes"] for row in rr),
            "anchor_count": sum(len(row["proposal"]["anchors"]) for row in rr),
            "qualifier_list_sizes": {field: sorted(Counter(len(row["proposal"]["canonical_ir"]["rules"][0][field])
                                                         for row in rr).items()) for field in ("conditions", "exceptions", "temporal")},
            "same_numeric_512_byte_ceiling_outcomes": dict(Counter(row["same_numeric_512_ceiling_new_byte_unit_inspection"]["outcome"] for row in rr))}
    admission()
    report = seal({"schema": "alignment-canonical-byte-preparation-report/v1", "status": "prepared_unqualified",
        "runner_binding": binding(__file__), "plan_binding": plan_binding, "target_free_inputs_binding": inference_binding,
        "all_request_outcomes_binding": outcome_binding, "train_weak_supervision_binding": supervision_binding,
        "development_transport_binding": dev_binding, "existing_codec_baselines_binding": baseline_binding,
        "source_bindings": preserved, "extra_prior_bindings": extra_prior_bindings,
        "implementation_bindings": implementation_bindings, "input_bindings": input_bindings,
        "loaded_repository_modules": loaded_modules, "complete_dependency_manifest": False,
        "row_count": 34, "all_row_grounding_outcomes": dict(Counter(row["grounding_outcome"] for row in outcome_rows)),
        "weak_fit_rows": 16, "train_group_count": len({row["group_id"] for row in train_metadata}),
        "development_positive_rows": 8, "development_positive_group_count": len({row["group_id"] for row in dev_metadata if row["row_kind"] == "positive"}),
        "development_other_rows": 10, "embedding_lane_joins": {name: len(lane["receipts"]) for name, lane in lanes.items()},
        "embedding_lane_dimensions": {name: lane["dimension"] for name, lane in lanes.items()},
        "embedding_profiles": {name: lane["backend_evidence"]["profile_id"] for name, lane in lanes.items()},
        "new_codec_profile": codec.CODEC_PROFILE, "vocabulary_size": 259, "output_cap": OUTPUT_CAP,
        "capacity_by_partition": capacities, "full_proposal_roundtrips": 22,
        "roundtrip_measurement_scope": "static_exact_transport_integrity_no_generated_predictions",
        "static_refitted_source_compatible": refitted_assessment["source_compatible_count"],
        "static_refitted_target_compatible": refitted_assessment["target_compatible_count"],
        "static_retained_source_compatible": retained_assessment["source_compatible_count"],
        "static_retained_target_compatible": retained_assessment["target_compatible_count"],
        "raw_train_source_vocabulary_sha256": digest(refitted_codec["source_vocabulary"]),
        "raw_train_target_vocabulary_sha256": digest(refitted_codec["target_vocabulary"]),
        "authored_panel_metadata_accessed": True, "authored_target_values_used": False,
        "weak_label_origin": "source_parser_derived_with_frozen_TRAIN_supervised_atom_catalog",
        "upstream_atom_catalog_supervised_from_TRAIN": True, "train_capacity_frozen_before_development": True,
        "development_previously_exposed": True, "output_cap_origin": "fixed_predeclared_opt_in_policy_4096",
        "output_cap_selected_by_training_algorithm": False,
        "calls": {"proposal_validations": 22, "byte_encodes": 22, "byte_decodes": 22,
                  "grounding_validation_replays": 34, "capacity_inspections": 44,
                  "typed_vocabulary_fits": 1, "models": 0,
                  "encoders": 0, "provers": 0, "neural_training": 0},
        "call_count_scope": "runner_explicit_calls_excludes_nested_helper_revalidation",
        "blocked_model_import_attempts": len(blocker.attempts), "independent_reviews_completed": 0,
        "strong_semantic_supervision_rows": 0, "contrastive_supervision_rows": 0, "proof_supervision_rows": 0,
        "fidelity_evaluation_reference_rows": 0, "negative_gold_sequences_created": 0,
        "qualified": False, "source_fidelity_established": False, "proof_authority": False,
        "training_executed": False, "checkpoint_promoted": False, "default_compiler_replaced": False,
        "original_validation_accessed": False, "sealed_final_test_accessed": False,
        "started_utc": started_utc, "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": time.monotonic() - started, "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "limitations": ["Fixed byte coverage and lossless roundtrips establish transport capacity, not autoformalization accuracy.",
                        "The 16 prepared TRAIN labels are source-parser weak supervision with an upstream supervised TRAIN atom catalog.",
                        "All 34 independent semantic reviews remain pending; all strong semantic and proof masks are zero.",
                        "The six DEV candidates are exposed transport diagnostics; two unavailable positives stay in the DEV8 denominator.",
                        "A numeric 512 ceiling in byte units is a capacity comparison, not compatibility with prior whole-string tokenizers.",
                        "The TRAIN-refitted typed atom codec has no newly trained neural checkpoint and does not output exact anchors.",
                        "Raw 8D features and 384D/768D embeddings are joined without executing learned autoencoder endpoints."]})
    report_binding = save(OUTPUT / "report.json", report)
    print(json.dumps({"report_binding": report_binding, "capacity_by_partition": capacities,
                      "full_proposal_roundtrips": 22, "weak_fit_rows": 16,
                      "elapsed_seconds": report["elapsed_seconds"], "max_rss_kib": report["max_rss_kib"]}, sort_keys=True))


if __name__ == "__main__":
    main()
