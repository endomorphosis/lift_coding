"""Bounded target-free replay of source preflight with retained native768 decoders."""

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
OUTPUT = CAMPAIGN / "preflight-decoder-01"
CONTROLS = ("none", "zero", "disabled", "rotate")
MAX_SECONDS = 180
MAX_RSS_KIB = 2 * 1024 * 1024


def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def binding(path):
    path = Path(path).absolute()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def verify(reference):
    current = binding(reference["path"])
    assert current["sha256"] == reference["sha256"], reference["path"]
    assert "bytes" not in reference or current["bytes"] == reference["bytes"], reference["path"]
    return current


def load(path):
    return json.loads(Path(path).read_bytes())


def verified_record(path):
    value = load(path)
    assert value["content_sha256"] == digest({key: item for key, item in value.items()
                                             if key != "content_sha256"}), str(path)
    return value


def save(path, value):
    with Path(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")
    return binding(path)


def seal(value):
    value["content_sha256"] = digest(value)
    return value


def effective_vectors(vectors, control):
    if control == "zero":
        return [[0.0] * 768 for _ in vectors]
    if control == "rotate":
        return vectors[1:] + vectors[:1]
    return vectors


def model_digest(reader, owner):
    return owner.checkpoint_digest({name: value.detach().tolist()
                                    for name, value in reader.model.state_dict().items()})


def compare_controls(baseline, changed, submitted_positions):
    changed_generation_positions, numerical_rows = [], 0
    maximum_difference = 0.0
    for position in submitted_positions:
        left, right = baseline["rows"][position]["decoder_row"], changed["rows"][position]["decoder_row"]
        if any(left[field] != right[field] for field in ("status", "reason", "canonical_ir")):
            changed_generation_positions.append(position)
        left_logits = left.get("span_diagnostics", {}).get("modality_logits")
        right_logits = right.get("span_diagnostics", {}).get("modality_logits")
        if left_logits is not None and right_logits is not None:
            assert len(left_logits) == len(right_logits) == 3
            maximum_difference = max(maximum_difference,
                                     max(abs(a - b) for a, b in zip(left_logits, right_logits, strict=True)))
            numerical_rows += 1
    return {"generation_changed_count": len(changed_generation_positions),
            "generation_changed_original_positions": changed_generation_positions,
            "modality_logit_comparison_rows": numerical_rows,
            "max_abs_modality_logit_difference": maximum_difference}


class ObservedDecoder:
    """Expose the real reader while checking each submitted numerical invocation."""

    def __init__(self, reader, owner, torch, calls, admission):
        self.reader = reader
        self.owner = owner
        self.torch = torch
        self.calls = calls
        self.admission = admission
        self.invocations = []

    def __getattr__(self, name):
        return getattr(self.reader, name)

    def decode_formal_logic(self, texts, latents=None, *, latent_ablation="none"):
        self.admission()
        assert latent_ablation in ("none", "disabled"), "wrapper must transform full-panel controls before filtering"
        before = model_digest(self.reader, self.owner)
        checkpoint_before = self.owner.checkpoint_digest(self.reader.checkpoint)
        rng_before = self.torch.get_rng_state().clone()
        with self.torch.inference_mode():
            assert self.torch.is_inference_mode_enabled()
            result = self.reader.decode_formal_logic(texts, latents, latent_ablation=latent_ablation)
        self.calls["inference_calls"] += 1
        self.calls["row_forward_calls"] += len(texts)
        after = model_digest(self.reader, self.owner)
        assert before == after == self.owner.checkpoint_digest(self.reader.checkpoint["model_state"])
        assert checkpoint_before == self.owner.checkpoint_digest(self.reader.checkpoint)
        assert self.torch.equal(rng_before, self.torch.get_rng_state())
        assert result["model_state_unchanged"] is True
        assert result["target_access"] is False and result["teacher_forcing"] is False
        assert result["training_executed"] is False
        self.invocations.append({"source_texts": list(texts), "latent_sha256": [digest(v) for v in latents],
                                 "owner_latent_ablation": latent_ablation,
                                 "model_state_before_sha256": before, "model_state_after_sha256": after,
                                 "checkpoint_before_sha256": checkpoint_before,
                                 "checkpoint_after_sha256": checkpoint_before, "rng_state_unchanged": True,
                                 "row_count": len(texts)})
        self.admission()
        return result


def main():
    started = time.monotonic()
    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    resource.setrlimit(resource.RLIMIT_CPU, (120, 130))
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    prior_path = CAMPAIGN / "source-grounding-validation-01/validation.json"
    prior = verified_record(prior_path)
    preserved = [verify(ref) for ref in prior["checked_file_bindings"]]
    assert len(preserved) == prior["checked_file_count"]
    raw_report_path = CAMPAIGN / "span-replay-01/report.json"
    raw_report = verified_record(raw_report_path)
    manifest_path = CAMPAIGN / "grounding-01/request_manifest.json"
    manifest = verified_record(manifest_path)
    input_path = CAMPAIGN / "richer-embedding-01/embedding_inputs.json"
    lane_path = CAMPAIGN / "richer-embedding-01/native768_embeddings.json"
    inputs, lane = load(input_path), load(lane_path)
    input_bindings = [binding(path) for path in (prior_path, raw_report_path, manifest_path, input_path, lane_path)]
    sys.path.insert(0, str(REPO))
    from ipfs_datasets_py.logic.formalization.autoencoder import (
        alignment_richer_embeddings as embeddings,
    )
    from ipfs_datasets_py.logic.legal_ir import canonical_decoder_preflight as preflight
    from ipfs_datasets_py.logic.legal_ir import canonical_span_decoder as wrapper
    from ipfs_datasets_py.optimizers.logic_theorem_optimizer import legal_span_dimensions as owner
    embeddings.validate_richer_embedding_inputs(inputs)
    embeddings.validate_embedding_lane(lane, inputs)
    assert lane["status"] == "produced" and lane["dimension"] == 768 and lane["lane_id"] == "native768"
    assert lane["backend_evidence"]["execution_kind"] == "observed_native"
    assert len(inputs["rows"]) == len(lane["receipts"]) == len(manifest["rows"]) == 34
    by_id = {row["id"]: row for row in lane["receipts"]}
    assert [row["id"] for row in inputs["rows"]] == [row["id"] for row in manifest["rows"]]
    vectors = [by_id[row["id"]]["embedding"] for row in inputs["rows"]]
    requests, preflights = [], []
    for input_row, source_row, vector in zip(inputs["rows"], manifest["rows"], vectors, strict=True):
        assert input_row["source_text"] == source_row["source_text"]
        assert input_row["source_sha256"] == source_row["source_sha256"]
        assert by_id[input_row["id"]]["embedding_sha256"] == digest(vector)
        assert source_row["declared_context"]["sha256"] == hashlib.sha256(
            source_row["declared_context"]["text"].encode("utf-8")).hexdigest()
        assert source_row["context_semantics_applied"] is False
        request = {"id": source_row["id"], "source_text": source_row["source_text"],
                   "context_text": source_row["declared_context"]["text"],
                   "requires_context_resolution": source_row["requires_context_resolution"]}
        requests.append(request)
        preflights.append(preflight.analyze_decoder_source(request["source_text"],
            context_text=request["context_text"], requires_context_resolution=request["requires_context_resolution"]))
    submitted_positions = [index for index, receipt in enumerate(preflights) if receipt["outcome"] == "unassessed"]
    blocked_positions = [index for index in range(34) if index not in submitted_positions]
    source_preflight_counts = dict(Counter(receipt["outcome"] for receipt in preflights))
    assert len(submitted_positions) == 24 and len(blocked_positions) == 10

    import torch
    assert torch.__version__ == "2.13.0+cu130"
    torch.set_num_threads(1)
    torch.set_default_dtype(torch.float32)
    torch.set_default_device("cpu")
    rng_before = torch.get_rng_state().clone()
    calls = {"optimizer_steps": 0, "inference_calls": 0, "row_forward_calls": 0}

    def forbid_step(*args, **kwargs):
        calls["optimizer_steps"] += 1
        raise RuntimeError("optimizer updates forbidden in wrapper replay")

    torch.optim.Adam.step = forbid_step

    def admission():
        assert time.monotonic() - started < MAX_SECONDS, "wrapper replay wall budget exceeded"
        assert resource.getrusage(resource.RUSAGE_SELF).ru_maxrss < MAX_RSS_KIB, "wrapper replay RSS budget exceeded"

    implementation_bindings = [binding(module.__file__) for module in (preflight, wrapper)]
    checkpoint_bindings = [verify(run["checkpoint_binding"]) for run in raw_report["runs"]]
    assert len(checkpoint_bindings) == len(raw_report["runs"]) == 9
    OUTPUT.mkdir(exist_ok=False)
    plan_binding = save(OUTPUT / "plan.json", seal({
        "schema": "alignment-preflight-decoder-replay-plan/v1", "runner_binding": binding(__file__),
        "input_bindings": input_bindings, "implementation_bindings": implementation_bindings,
        "checkpoint_bindings": checkpoint_bindings, "preserved_prior_binding_count": len(preserved),
        "requested_control_order": list(CONTROLS), "rotation_recipe": "full_34_input_order_next_row_then_filter",
        "rows": 34, "forwarded_rows_per_invocation": 24, "blocked_rows_per_invocation": 10,
        "preflight_counts": source_preflight_counts, "contexts_retained_but_unresolved": 2,
        "source_input_recipe": "exact_source_only_embeddings_with_declared_unresolved_context_in_preflight",
        "evaluation_role": "exposed_authored_development", "targets_used": False,
        "started_utc": started_utc,
        "training_executed": False, "new_encoder_calls": 0, "proof_calls": 0,
        "cpu_threads": 1, "device": "cpu", "dtype": "float32", "torch_version": torch.__version__,
        "max_seconds": MAX_SECONDS, "cpu_limit_seconds": [120, 130], "max_rss_kib": MAX_RSS_KIB,
        "rss_limit_kind": "cooperative_ru_maxrss_checks", "complete_dependency_manifest": False,
        "qualified": False, "source_fidelity_established": False, "proof_authority": False}))
    joins_binding = save(OUTPUT / "request_joins.json", seal({
        "schema": "alignment-preflight-decoder-input-joins/v1", "profile_id": lane["backend_evidence"]["profile_id"],
        "input_payload_sha256": inputs["payload_sha256"], "lane_payload_sha256": lane["payload_sha256"],
        "manifest_content_sha256": manifest["content_sha256"], "rows": [
            {"position": index, "id": row["id"], "source_sha256": row["source_sha256"],
             "embedding_sha256": by_id[row["id"]]["embedding_sha256"],
             "token_input_sha256": by_id[row["id"]]["token_input_sha256"],
             "context_sha256": source_row["declared_context"]["sha256"],
             "requires_context_resolution": source_row["requires_context_resolution"],
             "preflight_outcome": preflights[index]["outcome"], "forwarded": index in submitted_positions,
             "full_rotation_donor_position": (index + 1) % 34,
             "full_rotation_donor_id": inputs["rows"][(index + 1) % 34]["id"],
             "full_rotation_donor_embedding_sha256": digest(vectors[(index + 1) % 34])}
            for index, (row, source_row) in enumerate(zip(inputs["rows"], manifest["rows"], strict=True))]}))
    observed, raw_output_bindings = [], []
    parity_count = 0
    for run in raw_report["runs"]:
        admission()
        state = owner.load_checkpoint(run["checkpoint_binding"]["path"],
                                      expected_sha256=run["checkpoint_binding"]["sha256"])
        assert state["context_contract"]["representation_id"] == lane["backend_evidence"]["profile_id"]
        assert owner.checkpoint_digest(state) == run["checkpoint_payload_sha256"]
        state_before = owner.checkpoint_digest(state)
        reader = owner.DimensionalSpanDecoder(state)
        params = dict(reader.model.named_parameters())
        assert len(params) == 23 and sum(param.numel() for param in params.values()) == 33271
        assert all(param.device.type == "cpu" and param.dtype == torch.float32 for param in params.values())
        assert model_digest(reader, owner) == run["model_state_sha256"]
        proxy = ObservedDecoder(reader, owner, torch, calls, admission)
        results, output_bindings, summaries, parities = {}, {}, {}, {}
        for control in CONTROLS:
            raw_reference = verify(run["output_bindings"][control])
            raw_output_bindings.append(raw_reference)
            raw = load(raw_reference["path"])
            assert len(raw["rows"]) == 34
            result = wrapper.decode_with_preflight(proxy, requests, vectors, latent_ablation=control)
            wrapper.validate_preflight_decoding(result, requests, vectors)
            invocation = proxy.invocations[-1]
            assert invocation["source_texts"] == [requests[index]["source_text"] for index in submitted_positions]
            transformed = effective_vectors(vectors, control)
            assert invocation["latent_sha256"] == [digest(transformed[index]) for index in submitted_positions]
            assert invocation["owner_latent_ablation"] == ("disabled" if control == "disabled" else "none")
            assert result["submitted_positions"] == submitted_positions
            assert result["decoder_call_count"] == result["decoder_completion_count"] == 1
            assert result["backend_exception_type"] is None
            assert len(result["rows"]) == 34
            for index, row in enumerate(result["rows"]):
                assert row["id"] == requests[index]["id"]
                assert row["position"] == index
                assert row["preflight"] == preflights[index]
                assert row["original_latent_sha256"] == digest(vectors[index])
                assert row["effective_latent_sha256"] == digest(transformed[index])
                donor_position = (index + 1) % 34 if control == "rotate" else index
                assert row["latent_donor_position"] == donor_position
                assert row["latent_donor_id"] == requests[donor_position]["id"]
                if index in submitted_positions:
                    assert canonical_bytes(row["decoder_row"]) == canonical_bytes(raw["rows"][index]), (run["seed"], run["role"], control, index)
                    parity_count += 1
                else:
                    assert row["decoder_row"] is None
            parities[control] = {"raw_full_panel_binding": raw_reference,
                                 "submitted_original_positions": submitted_positions,
                                 "rows_bitwise_json_equal": len(submitted_positions),
                                 "preserved_fields": "complete_decoder_row_including_ir_scores_source_vector_hashes",
                                 "full_rotation_preserved": control == "rotate"}
            results[control] = result
            output_bindings[control] = save(OUTPUT / f"seed{run['seed']}-{run['role']}-{control}.json", result)
            summaries[control] = {"row_count": len(result["rows"]),
                                  "outcomes": dict(Counter(row["outcome"] for row in result["rows"])),
                                  "decoder_reasons": dict(Counter(row["decoder_row"]["reason"] for row in result["rows"]
                                                                 if row["decoder_row"] is not None)),
                                  "preflight_counts": source_preflight_counts,
                                  "qualified": False, "source_fidelity_established": False}
        fresh = owner.DimensionalSpanDecoder(state)
        fresh_params = dict(fresh.model.named_parameters())
        assert all(params[name].data_ptr() != fresh_params[name].data_ptr() for name in params)
        fresh_proxy = ObservedDecoder(fresh, owner, torch, calls, admission)
        repeated = wrapper.decode_with_preflight(fresh_proxy, requests, vectors, latent_ablation="none")
        wrapper.validate_preflight_decoding(repeated, requests, vectors)
        assert canonical_bytes(repeated) == canonical_bytes(results["none"])
        repeat_binding = save(OUTPUT / f"seed{run['seed']}-{run['role']}-none-private-reload.json", repeated)
        assert state_before == owner.checkpoint_digest(state)
        assert model_digest(reader, owner) == model_digest(fresh, owner) == run["model_state_sha256"]
        observed.append({"seed": run["seed"], "role": run["role"], "checkpoint_binding": run["checkpoint_binding"],
                         "model_state_sha256": run["model_state_sha256"], "model_state_unchanged": True,
                         "checkpoint_payload_unchanged": True, "model_tensor_count": 23, "model_parameter_count": 33271,
                         "output_bindings": output_bindings, "summaries": summaries, "raw_subset_parity": parities,
                         "control_comparisons": {control: compare_controls(results["none"], results[control], submitted_positions)
                                                 for control in CONTROLS[1:]},
                         "public_invocations": proxy.invocations, "private_reload_invocations": fresh_proxy.invocations,
                         "private_reload_binding": repeat_binding, "private_reload_bitwise_json_equal": True,
                         "private_models_disjoint_storage": True, "optimizer_resume_executed": False})
        del reader, fresh, params, fresh_params, proxy, fresh_proxy
    assert calls == {"optimizer_steps": 0, "inference_calls": 45, "row_forward_calls": 1080}
    assert parity_count == 864
    assert torch.equal(rng_before, torch.get_rng_state())
    for reference in preserved + input_bindings + implementation_bindings + checkpoint_bindings + raw_output_bindings:
        verify(reference)
    loaded_modules = []
    for name, module in sorted(sys.modules.items()):
        module_path = getattr(module, "__file__", None)
        if module_path and Path(module_path).is_relative_to(REPO) and Path(module_path).is_file():
            loaded_modules.append({"module_name": name, **binding(module_path)})
    admission()
    report = seal({"schema": "alignment-preflight-decoder-replay-report/v1", "status": "completed_unqualified",
        "runner_binding": binding(__file__), "plan_binding": plan_binding, "request_joins_binding": joins_binding,
        "implementation_bindings": implementation_bindings, "input_bindings": input_bindings,
        "source_bindings": preserved, "loaded_repository_modules": loaded_modules,
        "checkpoint_states_replayed": 9, "controls_per_state": 4, "runs": observed,
        "calls": calls, "primary_inference_calls": 36, "primary_row_forward_calls": 864,
        "private_reload_comparisons": 9, "private_reload_row_forward_calls": 216,
        "requested_rows_per_call": 34, "submitted_rows_per_call": 24, "blocked_rows_per_call": 10,
        "source_preflight_counts": source_preflight_counts, "raw_complete_row_parity_comparisons": parity_count,
        "raw_prior_row_forward_calls": 1530, "actual_row_forward_reduction": 450,
        "full_order_rotation_preserved": True, "rng_state_unchanged": True,
        "new_encoder_calls": 0, "proof_calls": 0, "training_executed": False,
        "authored_reference_semantics_read": False, "independent_semantic_review_completed": False,
        "source_fidelity_established": False, "qualified": False, "proof_authority": False,
        "original_validation_accessed": False, "sealed_final_test_accessed": False,
        "promotion_performed": False, "complete_dependency_manifest": False,
        "torch_version": torch.__version__, "cpu_threads": 1, "device": "cpu", "dtype": "float32",
        "started_utc": started_utc, "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "inference_mode_enabled_for_every_numerical_call": True,
        "worker_cpu_seconds": resource.getrusage(resource.RUSAGE_SELF).ru_utime
            + resource.getrusage(resource.RUSAGE_SELF).ru_stime,
        "elapsed_seconds": time.monotonic() - started, "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "limitations": ["Preflight warnings and unassessed rows do not establish output capability or semantic fidelity.",
                        "Context declarations are retained and blocked for clarification; no context binding was resolved.",
                        "Complete-row parity preserves raw decoder diagnostics only and gives no proof or promotion authority.",
                        "Constructed initialization controls and exposed authored development inputs are not final evaluation.",
                        "RSS is cooperatively checked; the external timeout and CPU limit bound worker duration.",
                        "Loaded repository files are observed bindings, not a complete transitive dependency manifest."]})
    reference = save(OUTPUT / "report.json", report)
    print(json.dumps({"report_binding": reference, "calls": calls, "raw_row_parity_comparisons": parity_count,
                      "elapsed_seconds": report["elapsed_seconds"], "max_rss_kib": report["max_rss_kib"]}, sort_keys=True))


if __name__ == "__main__":
    main()
