"""Bounded weak TRAIN fitting with separate target-free typed/anchor generation."""

import hashlib
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
OUTPUT = CAMPAIGN / "typed-anchor-decoder-01"
SEEDS = (1729, 1730, 1731)
EPOCHS = 100
BATCH_SIZE = 8
LEARNING_RATE = 0.008
MAX_PHASE_SECONDS = 60
MAX_SECONDS = 300
MAX_RSS_KIB = 2 * 1024 * 1024
FALSE_FLAGS = {"qualified": False, "source_fidelity_established": False, "proof_authority": False,
               "accepted": False, "independent_semantic_review_completed": False}
TIMING_CANARY = {
    "schema": "typed-anchor-disposable-source-timing-canary/v1", "training_rows": 16, "tuning_rows": 0,
    "epochs": 5, "optimizer_updates": 10, "seed": 1729,
    "training_elapsed_seconds": 0.8448139620013535, "elapsed_seconds": 2.3103912390070036,
    "worker_cpu_seconds": 6.197779000000001, "max_rss_kib": 695040,
    "source_model_tensor_count": 12, "source_model_parameter_count": 44257,
    "rng_state_unchanged": True, "retained_weights": False, "saved_outputs": False,
    "development_quality_evaluated": False, "main_stage_updates_include_canary": False,
    "training_config": {"learning_rate": 0.008, "batch_size": 8, "hidden_size": 64,
                        "embedding_dim": 32, "device": "cpu", "dtype": "float32",
                        "torch_version": "2.13.0+cu130", "cpu_threads": 1},
    "evidence_scope": "inline_disposable_worker_observation_no_retained_weights",
    "input_bindings": [
        {"path": str(CAMPAIGN / "canonical-codec-01/train_weak_supervision.json"), "bytes": 333966,
         "sha256": "97a333821790db1ad11a542f918a32e583b9b4ab150b82cdd71bbd883bbc42ba"},
        {"path": str(CAMPAIGN / "canonical-codec-01/target_free_inputs.json"), "bytes": 1432297,
         "sha256": "134f9a3bf917f0613fb474c04d8a5e414da443b133e12149f026cd3b5aa9473d"}],
    "owner_binding": {"path": str(REPO / "ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_formula_learning.py"),
                      "bytes": 31271, "sha256": "bb5fad7e1410149be8e9fe649c5825ccff931ed2ab89c840c70c141b96c6a425"},
    **FALSE_FLAGS,
}


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


def numerical_state(model):
    return {name: value.detach().tolist() for name, value in model.state_dict().items()}


def parameters_metadata(model):
    parameters = dict(model.named_parameters())
    return {"tensor_count": len(parameters), "parameter_count": sum(value.numel() for value in parameters.values()),
            "all_cpu_float32": all(value.device.type == "cpu" and str(value.dtype) == "torch.float32"
                                   for value in parameters.values())}


def span_coordinates(anchors):
    return [{key: anchor[key] for key in ("field_path", "start", "end")} for anchor in anchors]


def encoder_forward_metadata(torch, values, result):
    assert torch.is_inference_mode_enabled()
    packed = values[0]
    encoded, hidden = result
    assert encoded.data.device.type == hidden.device.type == "cpu"
    assert encoded.data.dtype == hidden.dtype == torch.float32
    assert torch.isfinite(encoded.data).all() and torch.isfinite(hidden).all()
    return {"packed_token_count": packed.data.shape[0], "maximum_batch_size": int(packed.batch_sizes[0]),
            "hidden_width": hidden.shape[-1], "device": "cpu", "dtype": "float32",
            "inference_mode_enabled": True}


def canonical_source_receipt(reader, requests, owner, preflight, legacy, torch, calls, admission):
    """Caller-side warning/OOV filtering; the parent sees eligible source strings only."""
    rows, eligible_positions = [], []
    for position, request in enumerate(requests):
        warning = preflight.analyze_decoder_source(request["source_text"], context_text=request["context_text"],
            requires_context_resolution=request["requires_context_resolution"])
        encoding = {"outcome": "not_assessed", "reason": None, "token_count": None}
        outcome = "clarification_required" if warning["outcome"] == "clarification_required" else "source_blocked"
        submitted_position = None
        if warning["outcome"] == "unassessed":
            try:
                source_ids = legacy.encode_source(reader.codec, request["source_text"])
            except legacy.CodecError as error:
                encoding.update(outcome="unavailable", reason=str(error))
                outcome = "source_encoding_unavailable"
            else:
                encoding.update(outcome="admitted", token_count=len(source_ids))
                submitted_position = len(eligible_positions)
                eligible_positions.append(position)
                outcome = "decoder_unavailable"
        rows.append({"id": request["id"], "position": position, "preflight": warning,
                     "source_sha256": warning["source_sha256"], "context_sha256": warning["context"]["sha256"],
                     "encoding": encoding, "submitted_position": submitted_position,
                     "outcome": outcome, "decoder_row": None, **FALSE_FLAGS})
    before = owner.checkpoint_digest(numerical_state(reader.model))
    checkpoint_before = owner.checkpoint_digest(reader.checkpoint)
    rng_before = torch.get_rng_state().clone()
    backend = None
    observed_encoder_forwards = []

    def observe_encoder(module, values, result):
        observed_encoder_forwards.append(encoder_forward_metadata(torch, values, result))
        calls["source_only_generation_encoder_forwards"] += 1

    if eligible_positions:
        admission()
        hook = reader.model.encoder.register_forward_hook(observe_encoder)
        try:
            with torch.inference_mode():
                backend = reader.decode_formal_logic([requests[position]["source_text"] for position in eligible_positions])
        finally:
            hook.remove()
        calls["source_only_backend_calls"] += 1
        calls["source_only_backend_rows"] += len(eligible_positions)
        assert backend["target_access"] is False and backend["teacher_forcing"] is False
        assert backend["training_executed"] is False
        assert len(backend["rows"]) == len(eligible_positions)
        for position, decoder_row in zip(eligible_positions, backend["rows"], strict=True):
            assert decoder_row["source_sha256"] == rows[position]["source_sha256"]
            assert decoder_row["target_access"] is False and decoder_row["teacher_forcing"] is False
            assert decoder_row["training_executed"] is False
            rows[position]["decoder_row"] = decoder_row
            rows[position]["outcome"] = "decoder_proposal" if decoder_row["status"] == "decoded" else "decoder_abstained"
    after = owner.checkpoint_digest(numerical_state(reader.model))
    assert before == after == owner.checkpoint_digest(reader.checkpoint["model_state"])
    assert checkpoint_before == owner.checkpoint_digest(reader.checkpoint)
    assert torch.equal(rng_before, torch.get_rng_state())
    return seal({"schema": "alignment-typed-source-only-free-generation/v1", "checkpoint_sha256": checkpoint_before,
        "rows": rows, "row_count": len(rows), "submitted_positions": eligible_positions, "backend_result": backend,
        "model_state_before_sha256": before, "model_state_after_sha256": after, "rng_state_unchanged": True,
        "observed_generation_encoder_forwards": observed_encoder_forwards,
        "actual_numeric_generation_executed": bool(observed_encoder_forwards),
        "target_access": False, "teacher_forcing": False, "training_executed": False,
        "source_encoder_conditioning": True, "external_embedding_conditioning": False,
        "exact_anchor_output_supported": False, **FALSE_FLAGS})


def observed_pipeline_receipt(reader, requests, owner, anchors, torch, calls, admission):
    """Observe real parent batches and anchor numerical forwards separately."""
    source_model, head_model = reader.parent.model, reader.model
    source_before = owner.checkpoint_digest(numerical_state(source_model))
    head_before = anchors.checkpoint_digest(numerical_state(head_model))
    source_checkpoint_before = owner.checkpoint_digest(reader.parent.checkpoint)
    anchor_checkpoint_before = anchors.checkpoint_digest(reader.checkpoint)
    rng_before = torch.get_rng_state().clone()
    parent_calls, head_calls = [], []
    generation_encoder_forwards, anchor_feature_encoder_forwards = [], []
    active_generation = [False]
    original_decode = reader.parent.decode_formal_logic

    def observed_parent(texts):
        admission()
        assert torch.is_inference_mode_enabled()
        before = owner.checkpoint_digest(numerical_state(source_model))
        active_generation[0] = True
        try:
            result = original_decode(texts)
        finally:
            active_generation[0] = False
        after = owner.checkpoint_digest(numerical_state(source_model))
        assert before == after == source_before
        parent_calls.append({"row_count": len(texts), "source_sha256": [hashlib.sha256(text.encode()).hexdigest() for text in texts],
                             "model_state_before_sha256": before, "model_state_after_sha256": after,
                             "inference_mode_enabled": True})
        calls["pipeline_parent_backend_calls"] += 1
        calls["pipeline_parent_backend_rows"] += len(texts)
        return result

    def observe_encoder(module, values, result):
        observed = encoder_forward_metadata(torch, values, result)
        if active_generation[0]:
            generation_encoder_forwards.append(observed)
            calls["pipeline_generation_encoder_forwards"] += 1
        else:
            anchor_feature_encoder_forwards.append(observed)
            calls["pipeline_anchor_feature_encoder_forwards"] += 1

    def observe_head(module, values, result):
        assert torch.is_inference_mode_enabled()
        assert len(values) == 2
        encoded, queries = values
        assert encoded.device.type == queries.device.type == "cpu"
        assert encoded.dtype == queries.dtype == torch.float32
        assert all(value.device.type == "cpu" and value.dtype == torch.float32 and torch.isfinite(value).all()
                   for value in result)
        head_calls.append({"source_token_count": encoded.shape[0], "leaf_query_count": queries.shape[0],
                           "inference_mode_enabled": True, "device": "cpu", "dtype": "float32"})
        calls["observed_anchor_numeric_forwards"] += 1

    reader.parent.decode_formal_logic = observed_parent
    hook = head_model.register_forward_hook(observe_head)
    encoder_hook = source_model.encoder.register_forward_hook(observe_encoder)
    try:
        admission()
        with torch.inference_mode():
            output = reader.decode_proposals(requests)
    finally:
        hook.remove()
        encoder_hook.remove()
        reader.parent.decode_formal_logic = original_decode
    assert len(output["rows"]) == 34
    assert output["parent_invocation_count"] == output["parent_completion_count"] == len(parent_calls)
    assert output["parent_submitted_row_count"] == sum(call["row_count"] for call in parent_calls)
    assert output["anchor_invocation_count"] == len(head_calls)
    assert output["target_access"] is False and output["teacher_forcing"] is False
    assert output["training_executed"] is False
    assert output["proposal_flag_scope"] == "transport_validation_only_not_generation_provenance"
    assert source_before == owner.checkpoint_digest(numerical_state(source_model))
    assert head_before == anchors.checkpoint_digest(numerical_state(head_model))
    assert source_checkpoint_before == owner.checkpoint_digest(reader.parent.checkpoint)
    assert anchor_checkpoint_before == anchors.checkpoint_digest(reader.checkpoint)
    assert torch.equal(rng_before, torch.get_rng_state())
    return output, {"source_model_state_before_sha256": source_before, "source_model_state_after_sha256": source_before,
        "anchor_model_state_before_sha256": head_before, "anchor_model_state_after_sha256": head_before,
        "source_checkpoint_before_sha256": source_checkpoint_before, "source_checkpoint_after_sha256": source_checkpoint_before,
        "anchor_checkpoint_before_sha256": anchor_checkpoint_before, "anchor_checkpoint_after_sha256": anchor_checkpoint_before,
        "rng_state_unchanged": True, "observed_parent_batches": parent_calls,
        "observed_anchor_numeric_forwards": head_calls,
        "observed_generation_encoder_forwards": generation_encoder_forwards,
        "observed_anchor_feature_encoder_forwards": anchor_feature_encoder_forwards,
        "actual_numeric_generation_executed": bool(generation_encoder_forwards or head_calls),
        "proposal_flag_scope": "transport_validation_only_not_generation_provenance"}


def main():
    started = time.monotonic()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    resource.setrlimit(resource.RLIMIT_CPU, (240, 250))
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

    def admission():
        assert time.monotonic() - started < MAX_SECONDS, "typed-anchor wall budget exceeded"
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < MAX_RSS_KIB, "typed-anchor RSS budget exceeded"

    prior_path = CAMPAIGN / "canonical-codec-validation-01/validation.json"
    prior = verified_record(prior_path)
    preserved = [verify(ref) for ref in prior["checked_file_bindings"]]
    assert len(preserved) == prior["checked_file_count"] == 336
    extra_prior = [verify(ref) for ref in prior["new_implementation_test_bindings"]]
    for reference in [*TIMING_CANARY["input_bindings"], TIMING_CANARY["owner_binding"]]:
        verify(reference)
    inputs_path = CAMPAIGN / "canonical-codec-01/target_free_inputs.json"
    supervision_path = CAMPAIGN / "canonical-codec-01/train_weak_supervision.json"
    outcomes_path = CAMPAIGN / "canonical-codec-01/all_request_outcomes.json"
    typed_codec_path = CAMPAIGN / "canonical-codec-01/train_refitted_typed_atom_codec.json"
    development_path = CAMPAIGN / "canonical-codec-01/development_transport_diagnostics.json"
    inputs, supervision, outcomes = (verified_record(path) for path in (inputs_path, supervision_path, outcomes_path))
    prepared_codec = load(typed_codec_path)
    requests = [{"id": row["id"], "source_text": row["source_text"], "context_text": row["context_text"],
                 "requires_context_resolution": row["requires_context_resolution"]} for row in inputs["rows"]]
    assert len(requests) == 34 and len({row["id"] for row in requests}) == 34
    request_by_id = {request["id"]: request for request in requests}
    outcome_by_id = {row["id"]: row for row in outcomes["rows"]}
    assert set(request_by_id) == set(outcome_by_id)
    train_examples, anchor_examples = [], []
    for row in supervision["rows"]:
        assert row["masks"]["weak_decoder_fit"] == 1
        assert all(row["masks"][field] == 0 for field in ("strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation"))
        assert outcome_by_id[row["id"]]["split"] == "train"
        request = request_by_id[row["id"]]
        assert request["context_text"] == "" and request["requires_context_resolution"] is False
        train_examples.append({"id": row["id"], "source_text": request["source_text"],
                               "canonical_ir": row["proposal"]["canonical_ir"]})
        anchor_examples.append({"id": row["id"], "source_text": request["source_text"], "proposal": row["proposal"]})
    assert len(train_examples) == len(anchor_examples) == 16
    del inputs
    input_bindings = [binding(path) for path in (prior_path, inputs_path, supervision_path, outcomes_path, typed_codec_path)]
    # The DEV proposal file is pinned by bytes here; its labels are parsed only
    # after all independent source/pipeline outputs have been written.
    development_binding = binding(development_path)
    sys.path.insert(0, str(REPO))
    import torch

    from ipfs_datasets_py.logic.legal_ir import canonical_decoder_preflight as preflight
    from ipfs_datasets_py.logic.legal_ir import canonical_typed_anchors as anchors
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_codec as legacy
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_learning as owner
    assert torch.__version__ == "2.13.0+cu130"
    torch.set_num_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.set_default_device("cpu")
    rng_before = torch.get_rng_state().clone()
    assert legacy.fit_codec(train_examples) == prepared_codec
    helper_paths = [Path(module.__file__) for module in (preflight, anchors, legacy, owner)] + [
        REPO / "ipfs_datasets_py/logic/legal_ir/canonical_byte_codec.py",
        REPO / "ipfs_datasets_py/logic/legal_ir/canonical_source_guards.py",
        REPO / "ipfs_datasets_py/logic/legal_ir/canonical_contracts.py",
        REPO / "ipfs_datasets_py/logic/autoformal/tree_pin.py",
        REPO / "ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_ir_grammar_decoder.py",
        REPO / "tests/unit/logic/legal_ir/test_canonical_typed_anchors.py",
    ]
    implementation_bindings = [binding(path) for path in sorted(set(helper_paths))]
    optimizer_steps = {"source": 0, "anchors": 0, "outside_fit": 0}
    active_fit = [None]
    original_step = torch.optim.Adam.step

    def counted_step(optimizer, *args, **kwargs):
        phase = active_fit[0]
        if phase not in ("source", "anchors"):
            optimizer_steps["outside_fit"] += 1
            raise RuntimeError("optimizer step outside declared weak TRAIN fitting phase")
        optimizer_steps[phase] += 1
        return original_step(optimizer, *args, **kwargs)

    torch.optim.Adam.step = counted_step
    OUTPUT.mkdir(exist_ok=False)
    requests_binding = save(OUTPUT / "inference_requests.json", seal({
        "schema": "alignment-typed-anchor-source-requests/v1", "row_count": 34, "rows": requests,
        "target_access": False, "contains_embeddings": False, "contains_target_tokens": False,
        "contains_canonical_ir": False, **FALSE_FLAGS}))
    plan_binding = save(OUTPUT / "plan.json", seal({
        "schema": "alignment-typed-anchor-weak-fitting-plan/v1", "runner_binding": binding(__file__),
        "input_bindings": input_bindings, "development_binding_hashed_not_parsed_for_fit": development_binding,
        "implementation_bindings": implementation_bindings, "inference_requests_binding": requests_binding,
        "preserved_prior_binding_count": 336, "extra_prior_bindings": extra_prior,
        "seeds": list(SEEDS), "source_epochs_requested_per_seed": EPOCHS, "anchor_epochs_requested_per_seed": EPOCHS,
        "expected_source_optimizer_steps_per_seed": 200, "expected_anchor_optimizer_steps_per_seed": 200,
        "training_rows": 16, "training_group_count": 4, "tuning_rows": 0,
        "learning_rate": LEARNING_RATE, "batch_size": BATCH_SIZE, "source_hidden_size": 64,
        "source_embedding_dim": 32, "maximum_seconds_per_fit": MAX_PHASE_SECONDS,
        "states": ["source_initial", "source_final", "source_final_anchor_initial", "source_final_anchor_final"],
        "output_selection": "last_completed_TRAIN_updates_only_no_development_selection",
        "weak_label_origin": "source_parser_derived_with_frozen_TRAIN_supervised_atom_catalog",
        "source_loss_normalization": "mean_cross_entropy_over_non_PAD_next_tokens_per_batch",
        "anchor_loss_normalization": "mean_start_end_cross_entropy_per_anchor_per_batch",
        "prepared_group_loss_weights_consumed": False,
        "external_embedding_conditioning": False, "new_encoder_calls": 0, "prover_calls": 0,
        "cpu_threads": 1, "device": "cpu", "dtype": "float32", "torch_version": torch.__version__,
        "max_seconds": MAX_SECONDS, "cpu_limit_seconds": [240, 250], "max_rss_kib": MAX_RSS_KIB,
        "timing_canary": TIMING_CANARY, "started_utc": started_utc, **FALSE_FLAGS}))
    calls = {"source_only_backend_calls": 0, "source_only_backend_rows": 0,
             "pipeline_calls": 0, "private_reload_calls": 0, "pipeline_parent_backend_calls": 0,
             "pipeline_parent_backend_rows": 0, "observed_anchor_numeric_forwards": 0,
             "source_only_generation_encoder_forwards": 0, "pipeline_generation_encoder_forwards": 0,
             "pipeline_anchor_feature_encoder_forwards": 0}
    runs, saved_results = [], {}
    for seed in SEEDS:
        admission()
        active_fit[0] = "source"
        initial_result = owner.train_decoder(train_examples, [], epochs=1, max_seconds=0,
            learning_rate=LEARNING_RATE, batch_size=BATCH_SIZE, seed=seed, hidden_size=64, embedding_dim=32)
        source_initial = initial_result["checkpoint"]
        assert source_initial["progress"]["optimizer_steps"] == 0
        assert source_initial["codec"] == prepared_codec and source_initial["tuning_pair_count"] == 0
        source_initial_binding = owner.save_checkpoint(source_initial, OUTPUT / f"seed{seed}-source-initial-checkpoint.json")
        source_initial = owner.load_checkpoint(source_initial_binding["path"], expected_sha256=source_initial_binding["sha256"])
        source_initial_report_binding = save(OUTPUT / f"seed{seed}-source-initial-training-report.json", initial_result["report"])
        final_result = owner.train_decoder(train_examples, [], epochs=EPOCHS, max_seconds=MAX_PHASE_SECONDS,
            learning_rate=LEARNING_RATE, batch_size=BATCH_SIZE, seed=seed, hidden_size=64, embedding_dim=32,
            checkpoint=source_initial)
        source_final = final_result["checkpoint"]
        active_fit[0] = None
        assert source_final["codec"] == prepared_codec and source_final["tuning_pair_count"] == 0
        assert source_final["parent_checkpoint_sha256"] == owner.checkpoint_digest(source_initial)
        source_final_binding = owner.save_checkpoint(source_final, OUTPUT / f"seed{seed}-source-final-checkpoint.json")
        source_final = owner.load_checkpoint(source_final_binding["path"], expected_sha256=source_final_binding["sha256"])
        source_final_report_binding = save(OUTPUT / f"seed{seed}-source-final-training-report.json", final_result["report"])
        source_outputs = {}
        source_models = {}
        for role, checkpoint in (("source_initial", source_initial), ("source_final", source_final)):
            reader = owner.LearnedLegalFormulaDecoder(checkpoint)
            source_models[role] = parameters_metadata(reader.model)
            assert source_models[role]["all_cpu_float32"]
            assert source_models[role]["tensor_count"] == 12 and source_models[role]["parameter_count"] == 44257
            output = canonical_source_receipt(reader, requests, owner, preflight, legacy, torch, calls, admission)
            source_outputs[role] = save(OUTPUT / f"seed{seed}-{role}-generation.json", output)
            saved_results[(seed, role)] = output
            del reader
        active_fit[0] = "anchors"
        initial_anchor_result = anchors.train_anchor_decoder(source_final, anchor_examples,
            epochs=1, max_seconds=0, learning_rate=LEARNING_RATE, batch_size=BATCH_SIZE, seed=seed)
        anchor_initial = initial_anchor_result["checkpoint"]
        assert anchor_initial["progress"]["optimizer_steps"] == 0
        anchor_initial_binding = anchors.save_checkpoint(source_final, anchor_initial, OUTPUT / f"seed{seed}-anchor-initial-checkpoint.json")
        anchor_initial = anchors.load_checkpoint(source_final, anchor_initial_binding["path"], expected_sha256=anchor_initial_binding["sha256"])
        anchor_initial_report_binding = save(OUTPUT / f"seed{seed}-anchor-initial-training-report.json", initial_anchor_result["report"])
        final_anchor_result = anchors.train_anchor_decoder(source_final, anchor_examples,
            epochs=EPOCHS, max_seconds=MAX_PHASE_SECONDS, learning_rate=LEARNING_RATE,
            batch_size=BATCH_SIZE, seed=seed, checkpoint=anchor_initial)
        anchor_final = final_anchor_result["checkpoint"]
        active_fit[0] = None
        assert anchor_final["parent_anchor_checkpoint_sha256"] == anchors.checkpoint_digest(anchor_initial)
        anchor_final_binding = anchors.save_checkpoint(source_final, anchor_final, OUTPUT / f"seed{seed}-anchor-final-checkpoint.json")
        anchor_final = anchors.load_checkpoint(source_final, anchor_final_binding["path"], expected_sha256=anchor_final_binding["sha256"])
        anchor_final_report_binding = save(OUTPUT / f"seed{seed}-anchor-final-training-report.json", final_anchor_result["report"])
        pipeline_outputs, pipeline_state_checks, pipeline_models = {}, {}, {}
        for role, head_checkpoint in (("source_final_anchor_initial", anchor_initial), ("source_final_anchor_final", anchor_final)):
            reader = anchors.TypedAnchorDecoder(source_final, head_checkpoint)
            source_model, head_model = reader.parent.model, reader.model
            output, state_checks = observed_pipeline_receipt(reader, requests, owner, anchors, torch, calls, admission)
            calls["pipeline_calls"] += 1
            assert raw(output["parent_backend"]) == raw(saved_results[(seed, "source_final")]["backend_result"])
            assert state_checks["source_model_state_before_sha256"] == owner.checkpoint_digest(source_final["model_state"])
            assert state_checks["anchor_model_state_before_sha256"] == anchors.checkpoint_digest(head_checkpoint["model_state"])
            pipeline_outputs[role] = save(OUTPUT / f"seed{seed}-{role}-generation.json", output)
            saved_results[(seed, role)] = output
            pipeline_models[role] = {"source": parameters_metadata(source_model), "anchors": parameters_metadata(head_model)}
            assert all(item["all_cpu_float32"] for item in pipeline_models[role].values())
            assert pipeline_models[role]["source"]["tensor_count"] == 12 and pipeline_models[role]["source"]["parameter_count"] == 44257
            assert pipeline_models[role]["anchors"]["tensor_count"] == 8 and pipeline_models[role]["anchors"]["parameter_count"] == 4354
            assert all(parameter.grad is None and not parameter.requires_grad for parameter in source_model.parameters())
            pipeline_state_checks[role] = state_checks
            if role == "source_final_anchor_final":
                reloaded_source = owner.load_checkpoint(source_final_binding["path"], expected_sha256=source_final_binding["sha256"])
                reloaded_head = anchors.load_checkpoint(reloaded_source, anchor_final_binding["path"], expected_sha256=anchor_final_binding["sha256"])
                fresh = anchors.TypedAnchorDecoder(reloaded_source, reloaded_head)
                for model, fresh_model in ((source_model, fresh.parent.model), (head_model, fresh.model)):
                    parameters, fresh_parameters = dict(model.named_parameters()), dict(fresh_model.named_parameters())
                    assert parameters.keys() == fresh_parameters.keys()
                    assert all(parameters[name].data_ptr() != fresh_parameters[name].data_ptr() for name in parameters)
                repeated, reload_state_checks = observed_pipeline_receipt(fresh, requests, owner, anchors, torch, calls, admission)
                calls["private_reload_calls"] += 1
                assert raw(repeated) == raw(output)
                assert reload_state_checks == state_checks
                reload_binding = save(OUTPUT / f"seed{seed}-source-final-anchor-final-private-reload.json", repeated)
                del fresh, reloaded_source, reloaded_head
            del reader, source_model, head_model
        runs.append({"seed": seed, "source_initial_checkpoint_binding": source_initial_binding,
            "source_final_checkpoint_binding": source_final_binding,
            "source_initial_training_report_binding": source_initial_report_binding,
            "source_final_training_report_binding": source_final_report_binding,
            "anchor_initial_checkpoint_binding": anchor_initial_binding, "anchor_final_checkpoint_binding": anchor_final_binding,
            "anchor_initial_training_report_binding": anchor_initial_report_binding,
            "anchor_final_training_report_binding": anchor_final_report_binding,
            "source_generation_bindings": source_outputs, "pipeline_generation_bindings": pipeline_outputs,
            "source_models": source_models, "pipeline_models": pipeline_models,
            "pipeline_state_checks": pipeline_state_checks, "private_reload_binding": reload_binding,
            "private_reload_state_checks": reload_state_checks,
            "private_models_disjoint_storage": True, "private_reload_bitwise_json_equal": True,
            "pipeline_parent_generation_bitwise_equal_source_final_canonical_only": True,
            "source_progress": source_final["progress"], "anchor_progress": anchor_final["progress"],
            "source_stopped_reason": final_result["report"]["stopped_reason"],
            "anchor_stopped_reason": final_anchor_result["report"]["stopped_reason"]})
        del source_initial, source_final, anchor_initial, anchor_final
    # All model generations are saved before any DEV proposal supervision is read.
    development = verified_record(development_path)
    assert len(development["rows"]) == 6 and development["positive_denominator"] == 8
    reference_proposals = {row["id"]: row["proposal"] for row in [*supervision["rows"], *development["rows"]]}
    diagnostics = []
    for (seed, role), result in saved_results.items():
        partition_counts = {}
        for split, denominator in (("train", 16), ("validation", 8)):
            positions = [index for index, request in enumerate(requests)
                         if outcome_by_id[request["id"]]["split"] == split
                         and outcome_by_id[request["id"]]["row_kind"] == "positive"]
            assert len(positions) == denominator
            compared = canonical_exact = anchored_exact = anchor_exact = span_coordinate_exact = 0
            for position in positions:
                identity = requests[position]["id"]
                if identity not in reference_proposals:
                    continue
                compared += 1
                row = result["rows"][position]
                candidate = row.get("proposal")
                decoder_row = row.get("decoder_row", row.get("parent_row"))
                canonical = candidate["canonical_ir"] if candidate is not None else decoder_row.get("canonical_ir") if decoder_row else None
                canonical_exact += canonical == reference_proposals[identity]["canonical_ir"]
                anchored_exact += candidate is not None and raw(candidate) == raw(reference_proposals[identity])
                if candidate is not None:
                    anchor_exact += raw(candidate["anchors"]) == raw(reference_proposals[identity]["anchors"])
                    span_coordinate_exact += raw(span_coordinates(candidate["anchors"])) == raw(span_coordinates(reference_proposals[identity]["anchors"]))
            partition_counts[split] = {"positive_denominator": denominator, "weak_reference_available": compared,
                "weak_canonical_exact_count": canonical_exact, "weak_full_proposal_exact_count": anchored_exact,
                "weak_complete_anchor_exact_count": anchor_exact, "weak_span_coordinate_exact_count": span_coordinate_exact,
                "independent_fidelity_value": None, "reference_role": "parser_derived_weak_diagnostic_not_independent_gold"}
        diagnostics.append({"seed": seed, "role": role, "row_count": 34,
            "all_row_outcomes": dict(Counter(row["outcome"] for row in result["rows"])),
            "partition_diagnostics": partition_counts, **FALSE_FLAGS})
    diagnostic_binding = save(OUTPUT / "posthoc_weak_diagnostics.json", seal({
        "schema": "alignment-typed-anchor-posthoc-weak-diagnostics/v1", "rows": diagnostics,
        "all_generation_saved_before_development_supervision_read": True, "used_for_fit_or_checkpoint_selection": False,
        "authored_reference_ir_used": False, "all_request_denominator": 34, "development_positive_denominator": 8,
        "development_unavailable_positive_count": 2, **FALSE_FLAGS}))
    assert optimizer_steps["outside_fit"] == 0 and active_fit[0] is None
    assert optimizer_steps["source"] == sum(run["source_progress"]["optimizer_steps"] for run in runs)
    assert optimizer_steps["anchors"] == sum(run["anchor_progress"]["optimizer_steps"] for run in runs)
    training_plan_complete = all(run[f"{phase}_progress"] == {"epochs_completed": EPOCHS, "row_cursor": 0, "optimizer_steps": 200}
                                 for run in runs for phase in ("source", "anchor"))
    assert torch.equal(rng_before, torch.get_rng_state())
    for reference in preserved + extra_prior + input_bindings + implementation_bindings + [development_binding]:
        verify(reference)
    loaded_modules = []
    for name, module in sorted(sys.modules.items()):
        module_path = getattr(module, "__file__", None)
        if module_path and Path(module_path).is_relative_to(REPO) and Path(module_path).is_file():
            loaded_modules.append({"module_name": name, **binding(module_path)})
    admission()
    report = seal({"schema": "alignment-typed-anchor-weak-fitting-report/v1", "status": "completed_unqualified" if training_plan_complete else "completed_with_incomplete_requested_training_unqualified",
        "runner_binding": binding(__file__), "plan_binding": plan_binding, "inference_requests_binding": requests_binding,
        "posthoc_weak_diagnostics_binding": diagnostic_binding, "runs": runs, "source_bindings": preserved,
        "extra_prior_bindings": extra_prior, "input_bindings": input_bindings,
        "development_binding": development_binding, "implementation_bindings": implementation_bindings,
        "loaded_repository_modules": loaded_modules, "complete_dependency_manifest": False,
        "training_rows": 16, "training_group_count": 4, "tuning_rows": 0,
        "training_plan_complete": training_plan_complete,
        "source_loss_normalization": "mean_cross_entropy_over_non_PAD_next_tokens_per_batch",
        "anchor_loss_normalization": "mean_start_end_cross_entropy_per_anchor_per_batch",
        "prepared_group_loss_weights_consumed": False,
        "training_anchor_count": 124, "training_anchors_per_group": 31,
        "calls": calls, "optimizer_steps": optimizer_steps, "timing_canary": TIMING_CANARY,
        "observed_training_steps_main_plus_disposable_canary": sum(optimizer_steps.values()) + TIMING_CANARY["optimizer_updates"],
        "private_reload_comparisons": 3, "all_requests_per_stage": 34,
        "proposal_flag_scope": "transport_validation_only_not_generation_provenance",
        "actual_numeric_generation_executed": bool(calls["source_only_generation_encoder_forwards"]
                                                   or calls["pipeline_generation_encoder_forwards"]
                                                   or calls["observed_anchor_numeric_forwards"]),
        "external_embedding_conditioning": False, "new_encoder_calls": 0, "prover_calls": 0,
        "training_executed": True, "teacher_forcing_scope": "TRAIN_token_and_anchor_supervision_and_TRAIN_metrics_only",
        "development_used_for_fit_or_selection": False, "development_previously_exposed": True,
        "authored_reference_ir_used": False, "checkpoint_promoted": False, "default_compiler_replaced": False,
        "original_validation_accessed": False, "sealed_final_test_accessed": False,
        "strong_semantic_supervision_rows": 0, "contrastive_supervision_rows": 0, "proof_supervision_rows": 0,
        "independent_reviews_completed": 0, "rng_state_unchanged": True,
        "torch_version": torch.__version__, "cpu_threads": 1, "device": "cpu", "dtype": "float32",
        "started_utc": started_utc, "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": time.monotonic() - started, "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "worker_cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        "limitations": ["All learned supervision is parser-derived weak TRAIN labeling with an upstream TRAIN-supervised atom catalog.",
                        "Posthoc TRAIN/DEV comparisons measure agreement with prepared weak labels, not independently reviewed source meaning.",
                        "This source-only baseline does not consume 8D, 384D, 768D or Leanstral conditioning vectors.",
                        "Source initial/final canonical generation and initial/final anchor-head pipelines are separate output scopes.",
                        "The typed source codec remains closed to unknown source words or typed target symbols.",
                        "All 34 semantic reviews remain pending; no generated output gains acceptance or proof authority."], **FALSE_FLAGS})
    report_binding = save(OUTPUT / "report.json", report)
    print(json.dumps({"report_binding": report_binding, "optimizer_steps": optimizer_steps,
                      "calls": calls, "elapsed_seconds": report["elapsed_seconds"],
                      "max_rss_kib": report["max_rss_kib"]}, sort_keys=True))


if __name__ == "__main__":
    main()
