"""Matched byte-order pilot; references never enter a prediction call."""
from contextlib import ExitStack
from hashlib import sha256
import argparse
import importlib.util
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import torch
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_span_decoder as head
from ipfs_datasets_py.logic.deontic.utils import deontic_parser


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def mkdir_durable(path):
    missing = []
    current = path
    while not current.exists():
        missing.append(current)
        current = current.parent
    path.mkdir(parents=True, exist_ok=True)
    for created in reversed(missing):
        sync_directory(created.parent)


def write(path, value):
    mkdir_durable(path.parent)
    with path.open("x") as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(path.parent)
    return pin(path)


def load(reference):
    assert pin(reference["path"]) == reference, "input artifact differs"
    return json.loads(Path(reference["path"]).read_text())


def forbidden(*args, **kwargs):
    raise AssertionError("Inference accessed TRAIN labels, optimizer or source parser")


def predict_inputs(model, inputs, path):
    records = []
    with ExitStack() as stack:
        for module, names in (
            (head, ("_labels", "train_scope_span_step", "ScopeSpanExample")),
            (deontic_parser, ("extract_normative_elements", "analyze_normative_sentence", "classify_modal")),
        ):
            for name in names:
                stack.enter_context(patch.object(module, name, forbidden))
        for row in inputs:
            assert set(row) == {"id", "source_group", "template", "condition_attachment", "source_text", "source_sha256"}
            assert sha256(row["source_text"].encode()).hexdigest() == row["source_sha256"]
            prediction = head.predict_scope_span_decoder(model, row["source_text"], row["condition_attachment"],
                expected_source_sha256=row["source_sha256"])
            assert prediction["model_executed"] and not prediction["target_access"]
            assert not any(prediction[k] for k in ("source_semantics_verified", "proof_ready", "qualified", "accepted", "formalized"))
            if prediction["proposal"] is not None:
                assert all(value == 0 for value in prediction["proposal"]["masks"].values())
                assert prediction["formal_output"] is None
            records.append({"id": row["id"], "source_group": row["source_group"],
                            "source_sha256": row["source_sha256"], "prediction": prediction})
    return records, write(path, {"schema": "scope-span-target-free-predictions/v1", "rows": records,
                                "references_accessed_by_inference": False})


def score_records(records, references, inputs):
    refs = {r["id"]: r for r in references}
    ins = {r["id"]: r for r in inputs}
    assert len(refs) == len(ins) == len(records) and set(refs) == set(ins) == {r["id"] for r in records}
    counts = dict(positive_count=0, positive_exact_count=0, positive_emitted_proposal_count=0,
                  positive_learned_refusal_count=0, positive_structural_block_count=0,
                  negative_count=0, negative_learned_refusal_count=0,
                  negative_incidental_block_count=0, negative_emitted_proposal_count=0)
    fields = {facet: 0 for facet in head.FACETS}
    categories, templates = {}, {}
    presence = {facet: dict(tp=0, fp=0, fn=0, tn=0, unavailable=0) for facet in head.OPTIONAL}
    modality_exact = all_spans_exact = 0
    for record in records:
        ref, row, result = refs[record["id"]], ins[record["id"]], record["prediction"]
        assert ref["source_group"] == record["source_group"]
        assert ref["source_sha256"] == record["source_sha256"]
        assert ref["independent_legal_review"] is False and not any(ref["admission_masks"].values())
        learned = result["status"] == "abstained" and result["blockers"] == ["learned_source_unsupported"]
        emitted = result["status"] == "predicted"
        if ref["supported"]:
            counts["positive_count"] += 1
            exact = emitted and result["prediction"] == ref["prediction"]
            counts["positive_exact_count"] += int(exact)
            counts["positive_emitted_proposal_count"] += int(emitted)
            counts["positive_learned_refusal_count"] += int(learned)
            counts["positive_structural_block_count"] += int(not emitted and not learned)
            template = templates.setdefault(row["template"], dict(count=0, exact=0))
            template["count"] += 1
            template["exact"] += int(exact)
            raw = result["raw_prediction"]
            available = raw is not None
            gold = ref["prediction"]
            modality_exact += int(available and raw["modality"] == gold["modality"])
            tokens = head.tokenize_source(row["source_text"])
            facet_matches = []
            for facet in head.FACETS:
                raw_span = "unavailable"
                if available:
                    if facet in head.OPTIONAL and not raw["presence"][facet]:
                        raw_span = None
                    else:
                        start, end = raw["token_spans"][facet]
                        if 0 <= start <= end < len(tokens):
                            raw_span = [tokens[start].start, tokens[end].end]
                equal = raw_span == gold["spans"][facet]
                fields[facet] += int(equal)
                facet_matches.append(equal)
            all_spans_exact += int(all(facet_matches))
            for facet in head.OPTIONAL:
                if not available:
                    presence[facet]["unavailable"] += 1
                else:
                    truth, predicted = gold["spans"][facet] is not None, raw["presence"][facet]
                    presence[facet][("t" if truth == predicted else "f") + ("p" if predicted else "n")] += 1
        else:
            assert ref.get("prediction") is None
            counts["negative_count"] += 1
            counts["negative_learned_refusal_count"] += int(learned)
            counts["negative_emitted_proposal_count"] += int(emitted)
            counts["negative_incidental_block_count"] += int(not learned and not emitted)
            category = categories.setdefault(ref["unsupported_category"], dict(count=0, learned_refusal=0, emitted=0, incidental_block=0))
            category["count"] += 1
            category["learned_refusal"] += int(learned)
            category["emitted"] += int(emitted)
            category["incidental_block"] += int(not learned and not emitted)
    total = len(records)
    mixed = counts["positive_exact_count"] + counts["negative_learned_refusal_count"]
    return {**counts, "case_count": total, "source_parent_groups": len({r["source_group"] for r in records}),
        "mixed_exact_count": mixed, "mixed_exact_rate": mixed / total,
        "positive_raw_modality_exact": modality_exact, "positive_raw_facet_span_exact": fields,
        "positive_raw_all_spans_exact": all_spans_exact, "raw_head_denominator": counts["positive_count"],
        "raw_head_accounting": "All supported examples including abstained/blocked outputs; missing raw fields are incorrect.",
        "optional_presence_confusion": presence, "negative_categories": categories, "positive_templates": templates,
        "attachment": "Explicit caller premise, not a learned endpoint.", "semantic_gold": False,
        "proposal_admission": "all masks zero; source context and meaning remain unresolved"}


def selection_score(summary, steps):
    return (summary["mixed_exact_count"], -summary["negative_emitted_proposal_count"],
            summary["positive_exact_count"], -steps)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    assert not torch.cuda.is_initialized() and torch.get_default_device().type == "cpu"
    plan = json.loads(args.plan.read_text())
    assert plan["runner"]["sha256"] == pin(Path(__file__))["sha256"]
    assert plan["producer_pins"] == head.producer_pins()
    assert plan["updates_per_arm"] == 240 and plan["batch_size"] == 16 and plan["seed"] == 24602
    out = args.output.resolve()
    assert not out.exists()
    mkdir_durable(out)
    inputs = load(plan["inputs"]["train"])
    references = load(plan["references"]["train"])
    by_input = {r["id"]: r for r in inputs}
    by_reference = {r["id"]: r for r in references}
    assert len(by_input) == len(by_reference) == 1024 and set(by_input) == set(by_reference)
    examples = {key: head.ScopeSpanExample(by_input[key]["source_text"], ref["supported"],
                                          ref.get("prediction")) for key, ref in by_reference.items()}
    spec = importlib.util.spec_from_file_location("scope_corpus_schedule", plan["builder"]["path"])
    builder = importlib.util.module_from_spec(spec)
    assert pin(plan["builder"]["path"]) == plan["builder"]
    spec.loader.exec_module(builder)
    schedule = builder.training_batches(inputs, references, seed=plan["seed"], updates=240)
    assert sha256(canonical(schedule)).hexdigest() == plan["schedule_canonical_sha256"]
    assert len(schedule) == 240 and all(len(batch) == 16 and sum(by_reference[key]["supported"] for key in batch) == 8 for batch in schedule)
    write(out / "training-schedule.json", schedule)
    selection_inputs = load(plan["inputs"]["selection"])
    # Final bytes are authenticated, never parsed before the selection barrier.
    assert pin(plan["references"]["final"]["path"]) == plan["references"]["final"]
    models = {name: head.ScopeSpanDecoder(head.ScopeSpanDecoderConfig(seed=24602, byte_kernel=kernel))
              for name, kernel in (("bytekernel1", 1), ("bytekernel3", 3))}
    point, ordered = models["bytekernel1"].state_dict(), models["bytekernel3"].state_dict()
    equal_names, expanded_names = [], []
    with torch.no_grad():
        for name, value in point.items():
            if value.shape == ordered[name].shape:
                ordered[name].copy_(value)
                equal_names.append(name)
            else:
                assert name in ("byte_convs.0.weight", "byte_convs.1.weight")
                assert value.ndim == 3 and value.shape[-1] == 1 and ordered[name].shape[-1] == 3
                ordered[name].zero_()
                ordered[name][:, :, 1:2].copy_(value)
                expanded_names.append(name)
    batch, _ = head._encoded_sources([by_input[key]["source_text"] for key in schedule[0]])
    with torch.no_grad():
        left, right = (models[name](*batch) for name in ("bytekernel1", "bytekernel3"))
    differences = {}
    for name in left:
        for subkey in left[name] if isinstance(left[name], dict) else [None]:
            a = left[name][subkey] if subkey is not None else left[name]
            b = right[name][subkey] if subkey is not None else right[name]
            assert torch.allclose(a, b, atol=1e-6, rtol=1e-5)
            differences[name + ("/" + subkey if subkey is not None else "")] = float((a - b).abs().max())
    init = write(out / "matched-initialization.json", {"common_parameter_names_exact": equal_names,
        "expanded_conv_parameters": expanded_names, "extra_conv_neighbors_initially_zero": True,
        "first_training_batch_logits_max_absolute_differences": differences,
        "parameter_counts": {name: sum(p.numel() for p in model.parameters()) for name, model in models.items()},
        "same_data_optimizer_update_and_selection_budget": True})
    init_inputs = [by_input[key] for key in schedule[0]]
    initial_predictions = {}
    for name, model in models.items():
        records, reference = predict_inputs(model, init_inputs, out / f"initial-predictions-{name}.json")
        initial_predictions[name] = (records, reference)
    pairs = zip(initial_predictions["bytekernel1"][0], initial_predictions["bytekernel3"][0], strict=True)
    parity_count = 0
    for a, b in pairs:
        assert a["id"] == b["id"]
        same = all(a["prediction"][key] == b["prediction"][key] for key in ("status", "prediction", "proposal", "blockers"))
        parity_count += int(same)
    assert parity_count == 16, "initial proposal transport differs despite matched weights"
    init_parity = write(out / "initial-proposal-parity.json", {"case_count": 16,
        "status_wire_proposal_and_blockers_exact": parity_count,
        "prediction_artifacts": {name: value[1] for name, value in initial_predictions.items()},
        "support_float_probabilities_not_required_bit_exact": True})
    arms = {}
    for name, model in models.items():
        directory = out / name
        optimizer = head.make_scope_span_optimizer(model, learning_rate=.003, weight_decay=0.0)
        selected, selections, losses = None, [], []
        for step in range(241):
            if step in (0, 120, 240):
                checkpoint = write(directory / f"checkpoint-{step}.json", head.save_scope_span_checkpoint(model, optimizer, steps=step))
                predictions, prediction_ref = predict_inputs(model, selection_inputs, directory / f"selection-predictions-{step}.json")
                # Durable predictions precede posthoc reference loading/scoring.
                selection_refs = load(plan["references"]["selection"])
                summary = score_records(predictions, selection_refs, selection_inputs)
                candidate = {"completed_updates": step, "summary": summary, "checkpoint": checkpoint,
                             "predictions": prediction_ref}
                selections.append(candidate)
                if selected is None or selection_score(summary, step) > selection_score(selected["summary"], selected["completed_updates"]):
                    selected = candidate
            if step == 240:
                break
            losses.append({"update": step + 1, **head.train_scope_span_step(model, optimizer, [examples[key] for key in schedule[step]])})
        write(directory / "losses.json", losses)
        write(directory / "selected.json", selected)
        arms[name] = {"selected": selected, "selection_candidates": selections, "completed_updates": 240,
                      "row_presentations": 3840, "positive_presentations": 1920, "negative_presentations": 1920}
    barrier = write(out / "both-selected-before-final.json", {"schema": "scope-pilot-final-reference-barrier/v1",
        "arms": arms, "final_references_parsed": False, "updates_completed": 480,
        "runner": pin(Path(__file__)), "plan": pin(args.plan)})
    final_inputs = load(plan["inputs"]["final"])
    collected = {}
    for name, arm in arms.items():
        checkpoint = load(arm["selected"]["checkpoint"])
        model, optimizer, steps = head.restore_scope_span_checkpoint(checkpoint)
        assert head.save_scope_span_checkpoint(model, optimizer, steps=steps) == checkpoint
        predictions, ref = predict_inputs(model, final_inputs, out / name / "final-predictions.json")
        collected[name] = predictions
        arm.update(final_predictions=ref, strict_model_and_full_Adam_restore_exact=True)
    write(out / "both-final-predictions-before-references.json", {name: arm["final_predictions"] for name, arm in arms.items()})
    final_refs = load(plan["references"]["final"])
    for name, arm in arms.items():
        arm["fresh_final"] = score_records(collected[name], final_refs, final_inputs)
    result = {"schema": "matched-scope-span-training-results/v1", "status": "completed", "arms": arms,
        "actual_optimizer_updates": 480, "additional_row_presentations": 7680,
        "source_derived_encoder_inputs": True, "latent_conditioned": False, "caller_attachment_learned": False,
        "engineering_targets_only": True, "independently_reviewed_law_gold": False,
        "existing_weights_changed": False, "semantic_admission": False, "Lake_executed": False,
        "final_reference_used_for_training_or_selection": False, "fresh_final_now_exposed": True,
        "plan": pin(args.plan), "runner": pin(Path(__file__)), "producer_pins": head.producer_pins(),
        "selection_barrier": barrier, "matched_initialization": init, "initial_proposal_parity": init_parity,
        "device": "cpu", "threads": 2, "cuda_initialized": torch.cuda.is_initialized(),
        "wall_seconds": time.monotonic() - started}
    result_ref = write(out / "training-results.json", result)
    write(out / "summary.json", {"schema": "scope-span-pilot-completion-summary/v1", "status": "completed",
        "training_results": result_ref, "actual_optimizer_updates": 480, "row_presentations": 7680,
        "final": {name: arm["fresh_final"] for name, arm in arms.items()},
        "source_semantics_verified": False, "proof_ready": False, "model_defaults_changed": False})
    print(json.dumps({"status": "completed", "actual_updates": 480,
                      "final": {name: arm["fresh_final"] for name, arm in arms.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
