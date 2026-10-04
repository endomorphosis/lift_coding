"""Resume only the missing anchor head and replay preserved source/head states."""

import hashlib
import importlib.util
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
PARTIAL = CAMPAIGN / "typed-anchor-decoder-01"
OUTPUT = CAMPAIGN / "typed-anchor-decoder-recovery-01"
INVENTORY_PATH = OUTPUT / "interrupted_stage_inventory.json"
INVENTORY_SHA = "cd5dda84d3b3cc1cc24709073e25540f56c7c431f0565e9c0187cf51314e653a"
ORIGINAL_RUNNER = CAMPAIGN / "run_typed_anchor_decoder.py"
ORIGINAL_RUNNER_SHA = "d362651092b415fab289184b2a0cd8ea15a9bca83828ac77d9680aadea1a8bef"
SEEDS = (1729, 1730, 1731)
EPOCHS = 100
MAX_SECONDS = 300
MAX_RSS_KIB = 2 * 1024 * 1024
THREAD_ENVIRONMENT = {"OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
FALSE_FLAGS = {"qualified": False, "source_fidelity_established": False, "proof_authority": False,
               "accepted": False, "independent_semantic_review_completed": False}


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


def main():
    started = time.monotonic()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    resource.setrlimit(resource.RLIMIT_CPU, (240, 250))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.environ.update(THREAD_ENVIRONMENT)
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

    def admission():
        assert time.monotonic() - started < MAX_SECONDS, "recovery wall budget exceeded"
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < MAX_RSS_KIB, "recovery RSS budget exceeded"

    inventory_binding = verify({"path": str(INVENTORY_PATH), "sha256": INVENTORY_SHA})
    inventory = verified_record(INVENTORY_PATH)
    partial_bindings = [verify(ref) for ref in inventory["interrupted_stage_bindings"]]
    assert len(partial_bindings) == 36
    assert {ref["path"] for ref in partial_bindings} == {str(path) for path in PARTIAL.iterdir() if path.is_file()}
    assert inventory["partial_stage_durable_optimizer_steps"] == {"source": 600, "anchors": 400}
    original_runner_binding = verify({"path": str(ORIGINAL_RUNNER), "sha256": ORIGINAL_RUNNER_SHA})
    spec = importlib.util.spec_from_file_location("frozen_typed_anchor_assay", ORIGINAL_RUNNER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    prior_path = CAMPAIGN / "canonical-codec-validation-01/validation.json"
    prior = verified_record(prior_path)
    preserved = [verify(ref) for ref in prior["checked_file_bindings"]]
    assert len(preserved) == prior["checked_file_count"] == 336
    extra_prior = [verify(ref) for ref in prior["new_implementation_test_bindings"]]
    inputs_path = CAMPAIGN / "canonical-codec-01/target_free_inputs.json"
    supervision_path = CAMPAIGN / "canonical-codec-01/train_weak_supervision.json"
    outcomes_path = CAMPAIGN / "canonical-codec-01/all_request_outcomes.json"
    typed_codec_path = CAMPAIGN / "canonical-codec-01/train_refitted_typed_atom_codec.json"
    development_path = CAMPAIGN / "canonical-codec-01/development_transport_diagnostics.json"
    inputs, supervision, outcomes = (verified_record(path) for path in (inputs_path, supervision_path, outcomes_path))
    requests = [{"id": row["id"], "source_text": row["source_text"], "context_text": row["context_text"],
                 "requires_context_resolution": row["requires_context_resolution"]} for row in inputs["rows"]]
    assert len(requests) == 34 and len({row["id"] for row in requests}) == 34
    request_by_id = {request["id"]: request for request in requests}
    outcome_by_id = {row["id"]: row for row in outcomes["rows"]}
    assert set(request_by_id) == set(outcome_by_id)
    anchor_examples = []
    for row in supervision["rows"]:
        assert row["masks"]["weak_decoder_fit"] == 1 and outcome_by_id[row["id"]]["split"] == "train"
        assert all(row["masks"][field] == 0 for field in ("strong_semantic_fit", "contrastive_supervision", "proof_supervision", "fidelity_evaluation"))
        request = request_by_id[row["id"]]
        assert request["context_text"] == "" and request["requires_context_resolution"] is False
        anchor_examples.append({"id": row["id"], "source_text": request["source_text"], "proposal": row["proposal"]})
    assert len(anchor_examples) == 16
    prepared_codec = load(typed_codec_path)
    del inputs
    input_bindings = [binding(path) for path in (prior_path, inputs_path, supervision_path, outcomes_path, typed_codec_path)]
    development_binding = binding(development_path)
    sys.path.insert(0, str(REPO))
    import torch

    from ipfs_datasets_py.logic.legal_ir import canonical_decoder_preflight as preflight
    from ipfs_datasets_py.logic.legal_ir import canonical_typed_anchors as anchors
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_codec as legacy
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_formula_learning as owner
    assert torch.__version__ == "2.13.0+cu130"
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.set_default_device("cpu")
    rng_before = torch.get_rng_state().clone()
    helper_paths = [Path(module.__file__) for module in (preflight, anchors, legacy, owner)] + [
        REPO / "ipfs_datasets_py/logic/legal_ir/canonical_byte_codec.py",
        REPO / "ipfs_datasets_py/logic/legal_ir/canonical_source_guards.py",
        REPO / "ipfs_datasets_py/logic/legal_ir/canonical_contracts.py",
        REPO / "ipfs_datasets_py/logic/autoformal/tree_pin.py",
        REPO / "ipfs_datasets_py/optimizers/logic_theorem_optimizer/legal_ir_grammar_decoder.py",
        REPO / "tests/unit/logic/legal_ir/test_canonical_typed_anchors.py"]
    implementation_bindings = [binding(path) for path in sorted(set(helper_paths))]
    original_plan = verified_record(PARTIAL / "plan.json")
    for reference in original_plan["implementation_bindings"]:
        verify(reference)
    assert original_plan["seeds"] == list(SEEDS)
    assert original_plan["source_epochs_requested_per_seed"] == original_plan["anchor_epochs_requested_per_seed"] == 100
    assert set(path.name for path in OUTPUT.iterdir()) == {"interrupted_stage_inventory.json"}
    requests_binding = save(OUTPUT / "inference_requests.json", seal({
        "schema": "alignment-typed-anchor-source-requests/v1", "row_count": 34, "rows": requests,
        "target_access": False, "contains_embeddings": False, "contains_target_tokens": False,
        "contains_canonical_ir": False, **FALSE_FLAGS}))
    plan_binding = save(OUTPUT / "plan.json", seal({
        "schema": "alignment-typed-anchor-recovery-plan/v1", "runner_binding": binding(__file__),
        "frozen_helper_runner_binding": original_runner_binding, "interrupted_inventory_binding": inventory_binding,
        "interrupted_stage_bindings": partial_bindings, "input_bindings": input_bindings,
        "development_binding_hashed_not_parsed_for_fit": development_binding,
        "implementation_bindings": implementation_bindings, "extra_prior_bindings": extra_prior,
        "preserved_prior_binding_count": 336, "inference_requests_binding": requests_binding,
        "source_fit_calls": 0, "recovery_anchor_seed": 1731, "anchor_epochs_requested": 100,
        "anchor_optimizer_updates_expected": 200, "anchor_training_rows": 16, "tuning_rows": 0,
        "anchor_start_state": "preserved_seed1731_zero_step_head_bound_to_preserved_source_final",
        "source_epochs_already_completed_per_seed": 100, "anchor_epochs_requested_per_seed": 100,
        "learning_rate": 0.008, "batch_size": 8, "maximum_seconds_per_fit": 60,
        "output_selection": "last_completed_TRAIN_updates_only_no_development_selection",
        "weak_label_origin": "source_parser_derived_with_frozen_TRAIN_supervised_atom_catalog",
        "source_loss_normalization": "mean_cross_entropy_over_non_PAD_next_tokens_per_batch",
        "anchor_loss_normalization": "mean_start_end_cross_entropy_per_anchor_per_batch",
        "prepared_group_loss_weights_consumed": False,
        "external_embedding_conditioning": False, "new_encoder_calls": 0, "prover_calls": 0,
        "cpu_threads": 1, "cpu_interop_threads": 1, "native_thread_environment": THREAD_ENVIRONMENT,
        "device": "cpu", "dtype": "float32", "torch_version": torch.__version__,
        "max_seconds": MAX_SECONDS, "cpu_limit_seconds": [240, 250], "max_rss_kib": MAX_RSS_KIB,
        "failed_attempt": inventory["failed_attempt"], "timing_canary": helper.TIMING_CANARY,
        "started_utc": started_utc, **FALSE_FLAGS}))
    optimizer_steps = {"source": 0, "anchors": 0, "outside_fit": 0}
    active_fit = [False]
    original_step = torch.optim.Adam.step

    def counted_step(optimizer, *args, **kwargs):
        if not active_fit[0]:
            optimizer_steps["outside_fit"] += 1
            raise RuntimeError("optimizer step outside declared missing-head TRAIN recovery")
        optimizer_steps["anchors"] += 1
        return original_step(optimizer, *args, **kwargs)

    torch.optim.Adam.step = counted_step
    calls = {"source_only_backend_calls": 0, "source_only_backend_rows": 0,
             "pipeline_calls": 0, "private_reload_calls": 0, "pipeline_parent_backend_calls": 0,
             "pipeline_parent_backend_rows": 0, "observed_anchor_numeric_forwards": 0,
             "source_only_generation_encoder_forwards": 0, "pipeline_generation_encoder_forwards": 0,
             "pipeline_anchor_feature_encoder_forwards": 0}
    partial_by_path = {ref["path"]: ref for ref in partial_bindings}

    def preserved_checkpoint_reference(seed, kind, role):
        return partial_by_path[str(PARTIAL / f"seed{seed}-{kind}-{role}-checkpoint.json")]

    runs, saved_results = [], {}
    for seed in SEEDS:
        admission()
        source_initial_binding = preserved_checkpoint_reference(seed, "source", "initial")
        source_final_binding = preserved_checkpoint_reference(seed, "source", "final")
        source_initial = owner.load_checkpoint(source_initial_binding["path"], expected_sha256=source_initial_binding["sha256"])
        source_final = owner.load_checkpoint(source_final_binding["path"], expected_sha256=source_final_binding["sha256"])
        assert source_initial["progress"]["optimizer_steps"] == 0
        assert source_final["progress"] == {"epochs_completed": 100, "row_cursor": 0, "optimizer_steps": 200}
        assert source_initial["codec"] == source_final["codec"] == prepared_codec
        assert source_initial["tuning_pair_count"] == source_final["tuning_pair_count"] == 0
        assert source_final["parent_checkpoint_sha256"] == owner.checkpoint_digest(source_initial)
        anchor_initial_binding = preserved_checkpoint_reference(seed, "anchor", "initial")
        anchor_initial = anchors.load_checkpoint(source_final, anchor_initial_binding["path"], expected_sha256=anchor_initial_binding["sha256"])
        assert anchor_initial["progress"]["optimizer_steps"] == 0
        if seed == 1731:
            active_fit[0] = True
            recovered = anchors.train_anchor_decoder(source_final, anchor_examples, epochs=100, max_seconds=60,
                learning_rate=0.008, batch_size=8, seed=1731, checkpoint=anchor_initial)
            active_fit[0] = False
            anchor_final = recovered["checkpoint"]
            anchor_final_binding = anchors.save_checkpoint(source_final, anchor_final, OUTPUT / "seed1731-anchor-final-checkpoint.json")
            anchor_final_report_binding = save(OUTPUT / "seed1731-anchor-final-training-report.json", recovered["report"])
            anchor_final = anchors.load_checkpoint(source_final, anchor_final_binding["path"], expected_sha256=anchor_final_binding["sha256"])
        else:
            anchor_final_binding = preserved_checkpoint_reference(seed, "anchor", "final")
            anchor_final = anchors.load_checkpoint(source_final, anchor_final_binding["path"], expected_sha256=anchor_final_binding["sha256"])
            anchor_final_report_binding = partial_by_path[str(PARTIAL / f"seed{seed}-anchor-final-training-report.json")]
        assert anchor_final["parent_anchor_checkpoint_sha256"] == anchors.checkpoint_digest(anchor_initial)
        source_outputs, source_models, original_generation_parity = {}, {}, {}
        for role, checkpoint in (("source_initial", source_initial), ("source_final", source_final)):
            reader = owner.LearnedLegalFormulaDecoder(checkpoint)
            source_models[role] = helper.parameters_metadata(reader.model)
            assert source_models[role] == {"tensor_count": 12, "parameter_count": 44257, "all_cpu_float32": True}
            output = helper.canonical_source_receipt(reader, requests, owner, preflight, legacy, torch, calls, admission)
            source_outputs[role] = save(OUTPUT / f"seed{seed}-{role}-generation.json", output)
            saved_results[(seed, role)] = output
            original_reference = partial_by_path[str(PARTIAL / f"seed{seed}-{role}-generation.json")]
            original_output = load(original_reference["path"])
            original_generation_parity[role] = {"binding": original_reference,
                "complete_backend_bitwise_json_equal": raw(output["backend_result"]) == raw(original_output["backend_result"])}
            assert original_generation_parity[role]["complete_backend_bitwise_json_equal"]
            del reader
        pipeline_outputs, pipeline_state_checks, pipeline_models = {}, {}, {}
        for role, head_checkpoint in (("source_final_anchor_initial", anchor_initial), ("source_final_anchor_final", anchor_final)):
            reader = anchors.TypedAnchorDecoder(source_final, head_checkpoint)
            output, state_checks = helper.observed_pipeline_receipt(reader, requests, owner, anchors, torch, calls, admission)
            calls["pipeline_calls"] += 1
            assert raw(output["parent_backend"]) == raw(saved_results[(seed, "source_final")]["backend_result"])
            assert state_checks["source_model_state_before_sha256"] == owner.checkpoint_digest(source_final["model_state"])
            assert state_checks["anchor_model_state_before_sha256"] == anchors.checkpoint_digest(head_checkpoint["model_state"])
            source_model, head_model = reader.parent.model, reader.model
            pipeline_models[role] = {"source": helper.parameters_metadata(source_model), "anchors": helper.parameters_metadata(head_model)}
            assert pipeline_models[role]["source"] == {"tensor_count": 12, "parameter_count": 44257, "all_cpu_float32": True}
            assert pipeline_models[role]["anchors"] == {"tensor_count": 8, "parameter_count": 4354, "all_cpu_float32": True}
            assert all(parameter.grad is None and not parameter.requires_grad for parameter in source_model.parameters())
            pipeline_outputs[role] = save(OUTPUT / f"seed{seed}-{role}-generation.json", output)
            pipeline_state_checks[role] = state_checks
            saved_results[(seed, role)] = output
            original_path = str(PARTIAL / f"seed{seed}-{role}-generation.json")
            if original_path in partial_by_path:
                original_output = load(original_path)
                original_generation_parity[role] = {"binding": partial_by_path[original_path],
                    "complete_receipt_bitwise_json_equal": raw(output) == raw(original_output)}
                assert original_generation_parity[role]["complete_receipt_bitwise_json_equal"]
            if role == "source_final_anchor_final":
                fresh_source = owner.load_checkpoint(source_final_binding["path"], expected_sha256=source_final_binding["sha256"])
                fresh_head = anchors.load_checkpoint(fresh_source, anchor_final_binding["path"], expected_sha256=anchor_final_binding["sha256"])
                fresh = anchors.TypedAnchorDecoder(fresh_source, fresh_head)
                for model, fresh_model in ((source_model, fresh.parent.model), (head_model, fresh.model)):
                    parameters, fresh_parameters = dict(model.named_parameters()), dict(fresh_model.named_parameters())
                    assert parameters.keys() == fresh_parameters.keys()
                    assert all(parameters[name].data_ptr() != fresh_parameters[name].data_ptr() for name in parameters)
                repeated, reload_state_checks = helper.observed_pipeline_receipt(fresh, requests, owner, anchors, torch, calls, admission)
                calls["private_reload_calls"] += 1
                assert raw(repeated) == raw(output) and reload_state_checks == state_checks
                reload_binding = save(OUTPUT / f"seed{seed}-source-final-anchor-final-private-reload.json", repeated)
                del fresh, fresh_source, fresh_head
            del reader, source_model, head_model
        original_training_reports = {name: partial_by_path[str(PARTIAL / f"seed{seed}-{name}-training-report.json")]
                                     for name in ("source-initial", "source-final", "anchor-initial")}
        anchor_report = load(anchor_final_report_binding["path"])
        source_report = load(original_training_reports["source-final"]["path"])
        runs.append({"seed": seed, "source_initial_checkpoint_binding": source_initial_binding,
            "source_final_checkpoint_binding": source_final_binding,
            "source_initial_training_report_binding": original_training_reports["source-initial"],
            "source_final_training_report_binding": original_training_reports["source-final"],
            "anchor_initial_checkpoint_binding": anchor_initial_binding, "anchor_final_checkpoint_binding": anchor_final_binding,
            "anchor_initial_training_report_binding": original_training_reports["anchor-initial"],
            "anchor_final_training_report_binding": anchor_final_report_binding,
            "source_generation_bindings": source_outputs, "pipeline_generation_bindings": pipeline_outputs,
            "source_models": source_models, "pipeline_models": pipeline_models,
            "pipeline_state_checks": pipeline_state_checks, "private_reload_state_checks": reload_state_checks,
            "private_reload_binding": reload_binding, "private_models_disjoint_storage": True,
            "private_reload_bitwise_json_equal": True,
            "pipeline_parent_generation_bitwise_equal_source_final_canonical_only": True,
            "original_completed_generation_parity": original_generation_parity,
            "source_progress": source_final["progress"], "anchor_progress": anchor_final["progress"],
            "source_stopped_reason": source_report["stopped_reason"], "anchor_stopped_reason": anchor_report["stopped_reason"],
            "source_training_reexecuted_in_recovery": False, "anchor_training_reexecuted_in_recovery": seed == 1731})
        del source_initial, source_final, anchor_initial, anchor_final
    # All twelve primary and three private generation receipts are saved before
    # the six DEV weak proposal bodies enter this process.
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
                reference = reference_proposals[identity]
                canonical_exact += canonical == reference["canonical_ir"]
                anchored_exact += candidate is not None and raw(candidate) == raw(reference)
                if candidate is not None:
                    anchor_exact += raw(candidate["anchors"]) == raw(reference["anchors"])
                    span_coordinate_exact += raw(helper.span_coordinates(candidate["anchors"])) == raw(helper.span_coordinates(reference["anchors"]))
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
    assert optimizer_steps["outside_fit"] == optimizer_steps["source"] == 0
    assert optimizer_steps["anchors"] == recovered["checkpoint"]["progress"]["optimizer_steps"]
    training_plan_complete = all(run[f"{phase}_progress"] == {"epochs_completed": 100, "row_cursor": 0, "optimizer_steps": 200}
                                 for run in runs for phase in ("source", "anchor"))
    lineage_steps = sum(run[f"{phase}_progress"]["optimizer_steps"] for run in runs for phase in ("source", "anchor"))
    known_optimizer_updates = 1000 + optimizer_steps["anchors"] + helper.TIMING_CANARY["optimizer_updates"]
    total_update_bounds = {"minimum": known_optimizer_updates, "maximum": known_optimizer_updates + 200}
    assert torch.equal(rng_before, torch.get_rng_state())
    for reference in preserved + extra_prior + input_bindings + implementation_bindings + partial_bindings + [development_binding, inventory_binding, original_runner_binding]:
        verify(reference)
    assert {ref["path"] for ref in partial_bindings} == {str(path) for path in PARTIAL.iterdir() if path.is_file()}
    loaded_modules = []
    for name, module in sorted(sys.modules.items()):
        module_path = getattr(module, "__file__", None)
        if module_path and Path(module_path).is_relative_to(REPO) and Path(module_path).is_file():
            loaded_modules.append({"module_name": name, **binding(module_path)})
    admission()
    report = seal({"schema": "alignment-typed-anchor-weak-fitting-recovery-report/v1",
        "status": "completed_unqualified" if training_plan_complete else "completed_with_incomplete_requested_training_unqualified",
        "runner_binding": binding(__file__), "frozen_helper_runner_binding": original_runner_binding,
        "plan_binding": plan_binding, "interrupted_inventory_binding": inventory_binding,
        "interrupted_stage_bindings": partial_bindings, "failed_attempt": inventory["failed_attempt"],
        "inference_requests_binding": requests_binding, "posthoc_weak_diagnostics_binding": diagnostic_binding,
        "runs": runs, "source_bindings": preserved, "extra_prior_bindings": extra_prior,
        "input_bindings": input_bindings, "development_binding": development_binding,
        "implementation_bindings": implementation_bindings, "loaded_repository_modules": loaded_modules,
        "complete_dependency_manifest": False, "training_rows": 16, "training_group_count": 4, "tuning_rows": 0,
        "training_plan_complete": training_plan_complete,
        "source_loss_normalization": "mean_cross_entropy_over_non_PAD_next_tokens_per_batch",
        "anchor_loss_normalization": "mean_start_end_cross_entropy_per_anchor_per_batch",
        "prepared_group_loss_weights_consumed": False, "training_anchor_count": 124, "training_anchors_per_group": 31,
        "calls": calls, "optimizer_steps": optimizer_steps,
        "optimizer_step_scope": "observed_recovery_process_only_source_fit_not_reexecuted",
        "completed_checkpoint_lineage_optimizer_steps": lineage_steps,
        "partial_stage_durable_optimizer_steps": {"source": 600, "anchors": 400},
        "interrupted_unsaved_optimizer_step_bounds": {"minimum": 0, "maximum": 200},
        "total_optimizer_update_bounds_including_canary": total_update_bounds, "timing_canary": helper.TIMING_CANARY,
        "private_reload_comparisons": 3, "primary_generation_receipts": 12, "all_requests_per_stage": 34,
        "proposal_flag_scope": "transport_validation_only_not_generation_provenance",
        "actual_numeric_generation_executed": bool(calls["source_only_generation_encoder_forwards"]
                                                   or calls["pipeline_generation_encoder_forwards"]
                                                   or calls["observed_anchor_numeric_forwards"]),
        "external_embedding_conditioning": False, "new_encoder_calls": 0, "prover_calls": 0,
        "training_executed": optimizer_steps["anchors"] > 0,
        "teacher_forcing_scope": "TRAIN_anchor_supervision_and_TRAIN_metrics_only_in_recovery",
        "development_used_for_fit_or_selection": False, "development_previously_exposed": True,
        "authored_reference_ir_used": False, "checkpoint_promoted": False, "default_compiler_replaced": False,
        "original_validation_accessed": False, "sealed_final_test_accessed": False,
        "strong_semantic_supervision_rows": 0, "contrastive_supervision_rows": 0, "proof_supervision_rows": 0,
        "independent_reviews_completed": 0, "rng_state_unchanged": True,
        "torch_version": torch.__version__, "cpu_threads": 1, "cpu_interop_threads": 1,
        "native_thread_environment": THREAD_ENVIRONMENT, "device": "cpu", "dtype": "float32",
        "started_utc": started_utc, "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": time.monotonic() - started, "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "worker_cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        "limitations": ["The initial attempt hit its CPU limit; its final unsaved anchor update count remains unknown within0..200.",
                        "The preserved checkpoint lineages contain exactly the recorded completed updates; attempted experimental updates include the unknown interruption interval.",
                        "All learned supervision is parser-derived weak TRAIN labeling with an upstream TRAIN-supervised atom catalog.",
                        "Posthoc agreement with prepared TRAIN/DEV labels is not independently reviewed source fidelity.",
                        "The nested proposal model_executed=False flag describes static transport validation; observed numerical execution is recorded separately.",
                        "This source-only baseline does not consume 8D,384D,768D or Leanstral conditioning vectors.",
                        "All34 semantic reviews remain pending; no generated output gains acceptance or proof authority."], **FALSE_FLAGS})
    report_binding = save(OUTPUT / "report.json", report)
    print(json.dumps({"report_binding": report_binding, "optimizer_steps": optimizer_steps,
                      "completed_checkpoint_lineage_optimizer_steps": lineage_steps,
                      "total_optimizer_update_bounds_including_canary": total_update_bounds,
                      "calls": calls, "elapsed_seconds": report["elapsed_seconds"],
                      "max_rss_kib": report["max_rss_kib"], "worker_cpu_seconds": report["worker_cpu_seconds"]}, sort_keys=True))


if __name__ == "__main__":
    main()
