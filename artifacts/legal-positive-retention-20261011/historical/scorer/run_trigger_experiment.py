"""Matched frozen-backbone modality readouts; all inference is source-only."""
from contextlib import ExitStack
from hashlib import sha256
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import time
from unittest.mock import patch

import torch
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_span_decoder as donor_head
from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_trigger_readout as head
from ipfs_datasets_py.logic.deontic.utils import deontic_parser


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=sha256(raw).hexdigest())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode()


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def mkdir_durable(path):
    missing, current = [], path
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


def denied(*args, **kwargs):
    raise AssertionError("inference reached a training label, optimizer, or semantic parser")


def frozen_signature(result):
    raw = result["raw_prediction"]
    wire = result["prediction"]
    return dict(status=result["status"], blockers=result["blockers"],
        support_probability=result.get("support_probability"), support_threshold=result.get("support_threshold"),
        presence=raw["presence"] if raw else None, token_spans=raw["token_spans"] if raw else None,
        emitted_spans=wire["spans"] if wire else None,
        attachment=wire["condition_attachment"] if wire else None)


def collect(model, inputs, path, *, donor=False):
    records = []
    with ExitStack() as stack:
        for owner, methods in (
            (head, ("train_trigger_readout_step", "TriggerReadoutExample")),
            (donor_head, ("_labels", "train_scope_span_step", "ScopeSpanExample")),
            (deontic_parser, ("extract_normative_elements", "analyze_normative_sentence", "classify_modal")),
        ):
            for method in methods:
                stack.enter_context(patch.object(owner, method, denied))
        for row in inputs:
            assert set(row) == {"id", "source_group", "template", "condition_attachment", "source_text", "source_sha256"}
            assert sha256(row["source_text"].encode()).hexdigest() == row["source_sha256"]
            if donor:
                prediction = donor_head.predict_scope_span_decoder(model, row["source_text"], row["condition_attachment"],
                    expected_source_sha256=row["source_sha256"])
                batch, _ = donor_head._encoded_sources([row["source_text"]])
                with torch.no_grad():
                    logits = model(*batch)["modality"][0].tolist()
            else:
                prediction = head.predict_trigger_readout(model, row["source_text"], row["condition_attachment"],
                    expected_source_sha256=row["source_sha256"])
                logits = prediction["modality_logits"]
            assert prediction["model_executed"] and prediction["formal_output"] is None
            assert not any(prediction[key] for key in ("source_semantics_verified", "proof_ready", "proof_authority", "qualified", "accepted", "formalized", "target_access"))
            if prediction["proposal"]:
                assert not any(prediction["proposal"]["masks"].values())
            assert len(logits) == 3 and all(type(v) is float and math.isfinite(v) for v in logits)
            records.append(dict(id=row["id"], source_group=row["source_group"],
                source_sha256=row["source_sha256"], class_logits=logits, prediction=prediction))
    reference = write(path, dict(schema="trigger-readout-source-only-panel/v1", rows=records,
        references_accessed_by_inference=False))
    return records, reference


def score(records, references, inputs):
    refs, sources = ({r["id"]: r for r in values} for values in (references, inputs))
    assert len(refs) == len(sources) == len(records) and set(refs) == set(sources) == {r["id"] for r in records}
    counts = dict(positive_count=0, positive_exact_count=0, positive_learned_refusal_count=0,
        positive_structural_block_count=0, positive_emitted_proposal_count=0,
        negative_count=0, negative_learned_refusal_count=0, negative_incidental_block_count=0,
        negative_emitted_proposal_count=0, positive_raw_modality_exact=0,
        positive_raw_all_spans_exact=0, nonempty_condition_count=0, nonempty_condition_exact_count=0)
    confusion = {gold: {pred: 0 for pred in donor_head.MODALITIES} for gold in donor_head.MODALITIES}
    facets = {facet: dict(count=0, exact=0, nonempty_count=0, nonempty_exact=0) for facet in donor_head.FACETS}
    categories, templates, ce = {}, {}, []
    for row in records:
        ref, source, result = refs[row["id"]], sources[row["id"]], row["prediction"]
        assert ref["source_group"] == row["source_group"] and ref["source_sha256"] == row["source_sha256"]
        assert ref["independent_legal_review"] is False and not any(ref["admission_masks"].values())
        emitted = result["status"] == "predicted"
        refused = result["status"] == "abstained" and result["blockers"] == ["learned_source_unsupported"]
        if ref["supported"]:
            gold, raw = ref["prediction"], result["raw_prediction"]
            exact = emitted and result["prediction"] == gold
            counts["positive_count"] += 1
            counts["positive_exact_count"] += int(exact)
            counts["positive_emitted_proposal_count"] += int(emitted)
            counts["positive_learned_refusal_count"] += int(refused)
            counts["positive_structural_block_count"] += int(not emitted and not refused)
            assert raw is not None
            confusion[gold["modality"]][raw["modality"]] += 1
            counts["positive_raw_modality_exact"] += int(gold["modality"] == raw["modality"])
            logits = row["class_logits"]
            highest = max(logits)
            ce.append(highest + math.log(sum(math.exp(x-highest) for x in logits)) - logits[donor_head.MODALITIES.index(gold["modality"])])
            tokens = donor_head.tokenize_source(source["source_text"])
            matches = []
            for facet in donor_head.FACETS:
                expected = gold["spans"][facet]
                predicted = "invalid"
                if facet in donor_head.OPTIONAL and not raw["presence"][facet]:
                    predicted = None
                else:
                    a, b = raw["token_spans"][facet]
                    if 0 <= a <= b < len(tokens):
                        predicted = [tokens[a].start, tokens[b].end]
                equal = predicted == expected
                matches.append(equal)
                facets[facet]["count"] += 1
                facets[facet]["exact"] += int(equal)
                facets[facet]["nonempty_count"] += int(expected is not None)
                facets[facet]["nonempty_exact"] += int(expected is not None and equal)
            counts["positive_raw_all_spans_exact"] += int(all(matches))
            present = gold["spans"]["condition"] is not None
            counts["nonempty_condition_count"] += int(present)
            counts["nonempty_condition_exact_count"] += int(present and exact)
            entry = templates.setdefault(source["template"], dict(count=0, class_exact=0, proposal_exact=0))
            entry["count"] += 1
            entry["class_exact"] += int(gold["modality"] == raw["modality"])
            entry["proposal_exact"] += int(exact)
        else:
            assert ref.get("prediction") is None
            counts["negative_count"] += 1
            counts["negative_learned_refusal_count"] += int(refused)
            counts["negative_emitted_proposal_count"] += int(emitted)
            counts["negative_incidental_block_count"] += int(not emitted and not refused)
            entry = categories.setdefault(ref["unsupported_category"], dict(count=0, learned_refusal=0, emitted=0, incidental_block=0))
            entry["count"] += 1
            entry["learned_refusal"] += int(refused)
            entry["emitted"] += int(emitted)
            entry["incidental_block"] += int(not emitted and not refused)
    return {**counts, "case_count": len(records), "source_parent_groups": len({r["source_group"] for r in records}),
        "positive_class_CE": sum(ce)/len(ce), "class_confusion": confusion,
        "positive_raw_facet_span_exact": facets, "negative_categories": categories, "positive_templates": templates,
        "raw_head_denominator": "all supported rows, including refusals and structural blocks",
        "caller_attachment_learned": False, "legal_gold": False, "admission_masks": "all five zero"}


def selection_score(summary, steps):
    return summary["positive_raw_modality_exact"], summary["positive_exact_count"], -steps


def assert_frozen_panels(left, right):
    assert len(left) == len(right)
    for a, b in zip(left, right, strict=True):
        assert a["id"] == b["id"]
        assert frozen_signature(a["prediction"]) == frozen_signature(b["prediction"]), a["id"]
    return len(left)


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
    assert plan["runner"] == pin(Path(__file__)) and plan["producer_pins"] == head.producer_pins()
    assert plan["updates_per_arm"] == 240 and plan["batch_size"] == 16 and plan["seed"] == 24603
    output = args.output.resolve()
    assert not output.exists()
    mkdir_durable(output)
    train_inputs, train_refs = (load(plan[key]["train"]) for key in ("inputs", "references"))
    sources, refs = ({r["id"]: r for r in values} for values in (train_inputs, train_refs))
    assert len(sources) == len(refs) == 1024 and set(sources) == set(refs)
    examples = {key: head.TriggerReadoutExample(sources[key]["source_text"], ref["supported"],
        ref["prediction"]["modality"] if ref["supported"] else None) for key, ref in refs.items()}
    assert pin(plan["builder"]["path"]) == plan["builder"]
    spec = importlib.util.spec_from_file_location("trigger_corpus_schedule", plan["builder"]["path"])
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    schedule = builder.training_batches(train_inputs, train_refs, seed=24603, updates=240)
    assert sha256(canonical(schedule)).hexdigest() == plan["schedule_canonical_sha256"]
    assert len(schedule) == 240 and all(len(batch) == 16 and sum(refs[key]["supported"] for key in batch)==8 for batch in schedule)
    write(output/"training-schedule.json", schedule)
    selection_inputs = load(plan["inputs"]["selection"])
    assert pin(plan["references"]["final"]["path"]) == plan["references"]["final"]
    parent_raw = Path(plan["donor_checkpoint"]["path"]).read_bytes()
    assert pin(plan["donor_checkpoint"]["path"]) == plan["donor_checkpoint"]
    parent_json = json.loads(parent_raw)
    parent, parent_optimizer, parent_steps = donor_head.restore_scope_span_checkpoint(parent_json)
    assert parent_steps == 240
    models = {mode: head.FrozenTriggerReadout(parent_raw, expected_donor_sha256=plan["donor_checkpoint"]["sha256"],
        config=head.TriggerReadoutConfig(seed=24603, mode=mode)) for mode in ("global", "predicted_trigger")}
    first_inputs = [sources[key] for key in schedule[0]]
    initial = {}
    parent_panel, parent_ref = collect(parent, first_inputs, output/"initial-donor-predictions.json", donor=True)
    for mode, model in models.items():
        records, ref = collect(model, first_inputs, output/f"initial-{mode}-predictions.json")
        assert_frozen_panels(records, parent_panel)
        assert all(a["class_logits"]==b["class_logits"] and all(a["prediction"][k]==b["prediction"][k]
            for k in ("status", "prediction", "proposal", "blockers", "raw_prediction"))
            for a,b in zip(records,parent_panel,strict=True))
        initial[mode] = ref
    # Compare exact adapter tensors only; mode changes evidence, not parameters.
    state = [model.state_dict() for model in models.values()]
    assert state[0].keys()==state[1].keys() and all(torch.equal(state[0][k],state[1][k]) for k in state[0])
    parameter_counts={mode:dict(total=sum(p.numel() for p in model.parameters()),
        trainable=sum(p.numel() for p in model.parameters() if p.requires_grad)) for mode,model in models.items()}
    assert parameter_counts["global"]==parameter_counts["predicted_trigger"]
    write(output/"matched-initialization.json", dict(parameter_counts=parameter_counts,
        all_initial_tensor_values_exact=True, initial_donor_full_core_and_logits_parity=16,
        donor_prediction=parent_ref, readout_predictions=initial, donor_steps=240,
        adapter_Adam_fresh=True, donor_Adam_continuation_claimed=False))
    donor_selection, donor_selection_ref = collect(parent,selection_inputs,output/"donor-selection-predictions.json",donor=True)
    train_panels, selection_panels, arms = {}, {}, {}
    for mode,model in models.items():
        directory=output/mode
        optimizer=head.make_trigger_readout_optimizer(model,learning_rate=.003,weight_decay=0)
        chosen,candidates,losses=None,[],[]
        for step in range(241):
            if step in (0,120,240):
                checkpoint=write(directory/f"checkpoint-{step}.json",head.save_trigger_readout_checkpoint(model,optimizer,steps=step))
                records,record_ref=collect(model,selection_inputs,directory/f"selection-predictions-{step}.json")
                assert_frozen_panels(records,donor_selection)
                selection_panels[(mode,step)]=records
                summary=score(records,load(plan["references"]["selection"]),selection_inputs)
                candidate=dict(completed_updates=step,summary=summary,checkpoint=checkpoint,predictions=record_ref)
                candidates.append(candidate)
                if chosen is None or selection_score(summary,step)>selection_score(chosen["summary"],chosen["completed_updates"]):
                    chosen=candidate
            if step==240:
                break
            update_result=head.train_trigger_readout_step(model,optimizer,[examples[key] for key in schedule[step]],gradient_clip=5)
            assert update_result["optimizer_step_executed"] is True
            assert update_result["supported_examples"]==8 and update_result["unsupported_examples"]==8
            losses.append(dict(update=step+1,**update_result))
        train_panels[mode],train_ref=collect(model,train_inputs,directory/"last-TRAIN-predictions.json")
        train_summary=score(train_panels[mode],train_refs,train_inputs)
        write(directory/"losses.json",losses)
        write(directory/"selected.json",chosen)
        arms[mode]=dict(selected=chosen,selection_candidates=candidates,completed_updates=240,training_input_records=3840,
            encoded_optimizer_source_presentations=1920,positive_training_records=1920,
            ignored_negative_training_records=1920,last_TRAIN=train_summary,last_TRAIN_predictions=train_ref)
    for step in (0,120,240):assert_frozen_panels(selection_panels[("global",step)],selection_panels[("predicted_trigger",step)])
    assert_frozen_panels(train_panels["global"],train_panels["predicted_trigger"])
    barrier=write(output/"both-selected-before-final.json",dict(schema="trigger-readout-final-reference-barrier/v1",
        arms=arms,final_references_parsed=False,updates_completed=480,runner=pin(Path(__file__)),plan=pin(args.plan)))
    final_inputs=load(plan["inputs"]["final"])
    panels={}
    for mode,arm in arms.items():
        checkpoint=load(arm["selected"]["checkpoint"])
        model,optimizer,step=head.restore_trigger_readout_checkpoint(checkpoint)
        assert head.save_trigger_readout_checkpoint(model,optimizer,steps=step)==checkpoint
        panels[mode],reference=collect(model,final_inputs,output/mode/"final-predictions.json")
        assert head.save_trigger_readout_checkpoint(model,optimizer,steps=step)==checkpoint
        arm.update(final_predictions=reference,strict_model_and_full_Adam_restore_exact=True)
    panels["donor"],donor_final_ref=collect(parent,final_inputs,output/"donor-final-predictions.json",donor=True)
    assert_frozen_panels(panels["global"],panels["donor"])
    assert_frozen_panels(panels["predicted_trigger"],panels["donor"])
    write(output/"all-final-predictions-before-references.json",dict(
        adapter_panels={mode:arm["final_predictions"] for mode,arm in arms.items()},donor=donor_final_ref))
    final_refs=load(plan["references"]["final"])
    for mode,arm in arms.items():arm["fresh_final"]=score(panels[mode],final_refs,final_inputs)
    assert donor_head.save_scope_span_checkpoint(parent,parent_optimizer,steps=parent_steps)==parent_json
    result=dict(schema="matched-trigger-readout-training-results/v1",status="completed",arms=arms,
        donor_fresh_final=score(panels["donor"],final_refs,final_inputs),donor_final_predictions=donor_final_ref,
        donor_selection=score(donor_selection,load(plan["references"]["selection"]),selection_inputs),donor_selection_predictions=donor_selection_ref,
        actual_optimizer_updates=480,training_input_records=7680,encoded_optimizer_source_presentations=3840,
        negative_input_records_ignored_by_adapter=3840,donor_all_fields_and_full_Adam_unchanged=True,
        frozen_selection_rows_verified=768,frozen_last_TRAIN_rows_verified=1024,frozen_final_rows_verified=256,
        source_only=True,latent_conditioned=False,caller_attachment_learned=False,legal_gold=False,
        semantic_admission=False,Lake_executed=False,existing_weights_changed=False,
        final_references_used_for_training_or_selection=False,fresh_final_now_exposed=True,
        plan=pin(args.plan),runner=pin(Path(__file__)),producer_pins=head.producer_pins(),selection_barrier=barrier,
        device="cpu",threads=2,cuda_initialized=torch.cuda.is_initialized(),wall_seconds=time.monotonic()-started)
    reference=write(output/"training-results.json",result)
    write(output/"summary.json",dict(schema="trigger-readout-pilot-completion/v1",status="completed",training_results=reference,
        actual_optimizer_updates=480,training_input_records=7680,encoded_optimizer_source_presentations=3840,
        negative_input_records_ignored_by_adapter=3840,final={mode:arm["fresh_final"] for mode,arm in arms.items()},
        donor_fresh_final=result["donor_fresh_final"],proof_ready=False,source_semantics_verified=False,model_defaults_changed=False))
    print(json.dumps(dict(status="completed",updates=480,final={mode:arm["fresh_final"] for mode,arm in arms.items()})))


if __name__=="__main__":
    main()
