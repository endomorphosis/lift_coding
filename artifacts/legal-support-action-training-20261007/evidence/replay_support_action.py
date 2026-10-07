"""Standalone read-only CPU replay of two selected heads over three cohorts.

Only pinned source inputs and complete saved prediction panels are opened.
References, fitting, reselection and optimizer updates are excluded. Checkpoint
mirrors must retain the exact selected file bytes, not merely equal tensors.
"""
from contextlib import ExitStack
from hashlib import sha256
import argparse
import json
import math
import os
from pathlib import Path
import sys
import time
from unittest.mock import patch


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def load(reference):
    path = Path(reference["path"]).resolve()
    raw = path.read_bytes()
    actual = {"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    require(actual == reference, "artifact changed: " + reference["path"])
    return json.loads(raw)


def denied(*_args, **_kwargs):
    raise AssertionError("read-only replay reached a target, fitting, semantic parser or optimizer step")


def mkdir_durable(path):
    missing, current = [], path
    while not current.exists():
        missing.append(current)
        current = current.parent
    path.mkdir(parents=True, exist_ok=True)
    for created in reversed(missing):
        sync_directory(created.parent)


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--checkpoints-root", type=Path)
    parser.add_argument("--package-root", type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    root = Path(__file__).resolve().parent
    package_root = (args.package_root or root / "datasets").resolve()
    results_root = args.results.resolve()
    receipt_path = args.output.resolve()
    require(not receipt_path.exists(), "replay receipt already exists")
    # Set device/thread policy before importing Torch or numerical modules.
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["OMP_NUM_THREADS"] = "2"
    os.environ["MKL_NUM_THREADS"] = "2"
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(package_root))
    import torch
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_support_action as head
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_trigger_readout as trigger
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_span_decoder as donor
    from ipfs_datasets_py.logic.deontic.utils import deontic_parser
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    require(not torch.cuda.is_initialized() and torch.get_default_device().type == "cpu", "CPU replay required")
    source_ref = pin(Path(__file__))
    plan_ref = pin(root / "experiment-plan.json")
    plan = load(plan_ref)
    results_ref = pin(results_root / "training-results.json")
    results = load(results_ref)
    require(results["status"] == "completed" and results["plan"] == plan_ref, "completed pinned experiment required")
    producers = head.producer_pins()
    require(producers == results["producer_pins"] == plan["producer_pins"], "producer mismatch")
    barrier_ref = results["predictions_barrier"]
    barrier = load(barrier_ref)
    require(barrier["evaluation_references_parsed"] is False, "saved prediction barrier required")
    cohorts = {"fresh_final": plan["inputs"]["final"],
               "earlier_scope": plan["retention"]["earlier_scope"]["inputs"],
               "earlier_trigger": plan["retention"]["earlier_trigger"]["inputs"]}
    input_rows = {name: load(reference) for name, reference in cohorts.items()}
    require(all(len(rows) == 128 for rows in input_rows.values()), "three complete 128-row source cohorts required")
    arms = {}
    for kind in ("linear", "mlp"):
        selected_ref = pin(results_root / kind / "selected.json")
        selected = load(selected_ref)
        require(selected == results["arms"][kind]["selected"], "selection receipt differs")
        original = selected["checkpoint"]
        path = (args.checkpoints_root / kind / "checkpoint.json" if args.checkpoints_root
                else Path(original["path"]))
        checkpoint_ref = pin(path)
        require(checkpoint_ref["sha256"] == original["sha256"] and checkpoint_ref["bytes"] == original["bytes"],
                "selected checkpoint bytes differ")
        checkpoint = load(checkpoint_ref)
        rng_before_restore = torch.random.get_rng_state().clone()
        model, optimizer, steps, action_steps = head.restore_support_action_checkpoint(checkpoint)
        require(torch.equal(rng_before_restore, torch.random.get_rng_state()), "restore changed CPU RNG")
        require(steps == action_steps == selected["completed_updates"], "selected head counters differ")
        require(model.config.to_dict() == {"seed": plan["seed"], "head_kind": kind, "hidden": plan["hidden"]},
                "selected residual recipe differs")
        before = head.save_support_action_checkpoint(model, optimizer, steps=steps, action_steps=action_steps)
        require(before == checkpoint, "model/full Adam restoration differs")
        parent_raw = before["parent"]["json_utf8"].encode("utf-8")
        require(sha256(parent_raw).hexdigest() == plan["parent_checkpoint"]["sha256"]
                and len(parent_raw) == plan["parent_checkpoint"]["bytes"], "selected parent provenance differs from plan")
        mode_before = {name: module.training for name, module in model.named_modules()}
        flags_before = {name: parameter.requires_grad for name, parameter in model.named_parameters()}
        require(all(p.grad is None for p in model.parameters()), "unexpected restored gradients")
        states_before = {name: value.detach().clone() for name, value in model.state_dict().items()}
        rng_before_prediction = torch.random.get_rng_state().clone()
        cohort_receipts = {}
        with ExitStack() as stack:
            for owner, methods in (
                (head, ("SupportActionExample", "train_support_action_step", "_action_labels")),
                (trigger, ("TriggerReadoutExample", "train_trigger_readout_step")),
                (donor, ("ScopeSpanExample", "train_scope_span_step", "_labels")),
                (deontic_parser, ("extract_normative_elements", "analyze_normative_sentence", "classify_modal")),
                (torch.optim.AdamW, ("step",)),
            ):
                for method in methods:
                    stack.enter_context(patch.object(owner, method, denied))
            for cohort, rows in input_rows.items():
                expected_ref = barrier["panels"][kind + "/" + cohort]
                require(Path(expected_ref["path"]).resolve() == (results_root / kind / (cohort + "-predictions.json")).resolve(),
                        "expected prediction panel belongs to another result root")
                expected = load(expected_ref)
                require(expected["schema"] == "support-action-source-only-panel/v1"
                        and expected["references_accessed_by_inference"] is False, "source-only complete panel required")
                actual = []
                for row in rows:
                    require(set(row) == {"id", "source_group", "template", "condition_attachment", "source_text", "source_sha256"},
                            "closed source input row required")
                    prediction = head.predict_support_action(model, row["source_text"], row["condition_attachment"],
                        expected_source_sha256=row["source_sha256"])
                    require(prediction["model_executed"] and prediction["formal_output"] is None,
                            "executed zero-formal-authority prediction required")
                    require(not any(prediction[key] for key in ("source_semantics_verified", "accepted", "qualified", "formalized",
                        "proof_ready", "proof_authority", "target_access", "targets_used_at_inference")), "prediction gained authority/targets")
                    if prediction["proposal"]:
                        require(not any(prediction["proposal"]["masks"].values()), "proposal gained admission")
                    logits = prediction["modality_logits"]
                    require(type(logits) is list and len(logits) == 3 and all(type(v) is float and math.isfinite(v) for v in logits),
                            "finite source-only modality diagnostics required")
                    actual.append({"id": row["id"], "source_group": row["source_group"], "source_sha256": row["source_sha256"],
                                   "class_logits": logits, "prediction": prediction})
                require(len(actual) == len(expected["rows"]) == 128 and actual == expected["rows"],
                        "complete prediction dictionaries differ: " + kind + "/" + cohort)
                cohort_receipts[cohort] = {"cases": 128, "full_output_exact": 128,
                    "inputs": cohorts[cohort], "expected_complete_panel": expected_ref}
        after = head.save_support_action_checkpoint(model, optimizer, steps=steps, action_steps=action_steps)
        require(after == before == checkpoint, "model/full Adam/counters changed during replay")
        require(after["parent"]["json_utf8"].encode("utf-8") == parent_raw, "original full parent provenance bytes changed")
        require(mode_before == {name: module.training for name, module in model.named_modules()}, "model/parent mode changed")
        require(flags_before == {name: p.requires_grad for name, p in model.named_parameters()}
                and all(p.grad is None for p in model.parameters()), "gradient custody changed")
        state_after = model.state_dict()
        require(set(states_before) == set(state_after) and all(torch.equal(value, state_after[name]) for name, value in states_before.items()),
                "model/parent tensors changed")
        require(torch.equal(rng_before_prediction, torch.random.get_rng_state()), "inference changed CPU RNG")
        arms[kind] = {"checkpoint": checkpoint_ref, "original_selected_checkpoint": original, "selected_receipt": selected_ref,
            "support_steps": steps, "action_steps": action_steps, "cohorts": cohort_receipts,
            "complete_output_exact": 384, "new_heads_and_full_Adam_unchanged": True,
            "parent_full_checkpoint_bytes_unchanged": True, "model_parent_modes_and_rng_unchanged": True,
            "parent_sha256": sha256(parent_raw).hexdigest()}
    require(pin(Path(__file__)) == source_ref and head.producer_pins() == producers, "helper/producer changed during replay")
    receipt = {"schema": "support-action-read-only-complete-replay/v1", "status": "passed", "arms": arms,
        "complete_outputs_exact": 768, "cohorts_per_arm": 3, "rows_per_cohort": 128,
        "additional_optimizer_updates": 0, "references_opened": False, "training_targets_denied": True,
        "semantic_parsers_denied": True, "optimizer_step_denied": True, "training_lease_claimed": False,
        "threads": 2, "device": "cpu", "cuda_initialized": False, "producer_pins": producers,
        "source": source_ref, "plan": plan_ref, "training_results": results_ref, "prediction_barrier": barrier_ref,
        "elapsed_seconds": time.monotonic() - started, "receipt_file_and_parent_directory_fsync": True}
    mkdir_durable(receipt_path.parent)
    with receipt_path.open("x") as stream:
        json.dump(receipt, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(receipt_path.parent)
    print(json.dumps({"status": "passed", "complete_outputs_exact": 768, "receipt": pin(receipt_path)}))


if __name__ == "__main__":
    main()
