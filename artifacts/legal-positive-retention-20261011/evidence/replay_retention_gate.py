"""Read-only selected-state replay: two objectives, five source-only cohorts.

The helper authenticates local result receipts and source inputs, restores the
complete selected checkpoints, and compares all 1,280 prediction dictionaries.
Exact downloaded checkpoint containers can replace local containers. It opens
no target-reference files, fits no model, and acquires no resource reservation.
"""
from contextlib import ExitStack
from hashlib import sha256
import argparse
import json
import math
import os
from pathlib import Path
import socket
import sys
import time
from unittest.mock import patch

ARMS = ("bce", "positive_margin")
COHORTS = ("fresh_final", "earlier_scope", "earlier_trigger", "earlier_support_action", "earlier_support_gate")
ROWS_PER_COHORT = 128


def require(condition, message):
    if not condition:
        raise ValueError(message)


def pin(path):
    path = Path(path).resolve()
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}


def same_bytes(left, right):
    return left["bytes"] == right["bytes"] and left["sha256"] == right["sha256"]


def load(reference, *, relocated_path=None):
    require(type(reference) is dict and set(reference) == {"path", "bytes", "sha256"}, "closed file reference required")
    path = Path(relocated_path or reference["path"]).resolve()
    raw = path.read_bytes()
    actual = {"path": str(path), "bytes": len(raw), "sha256": sha256(raw).hexdigest()}
    require(same_bytes(actual, reference), "artifact bytes changed: " + reference["path"])
    if relocated_path is None:
        require(actual == reference, "artifact path changed: " + reference["path"])
    return json.loads(raw)


def denied(*_args, **_kwargs):
    raise AssertionError("read-only replay reached TRAIN, teacher/hinge, selection, semantic parsing, gradients or optimizer update")


def network_denied(*_args, **_kwargs):
    raise AssertionError("offline replay attempted a socket connection or datagram")


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


def checkpoint_path(args, kind, original, results_root):
    explicit = args.bce_checkpoint if kind == "bce" else args.positive_margin_checkpoint
    if explicit is not None:
        return explicit.resolve()
    if args.checkpoints_root is not None:
        return (args.checkpoints_root / kind / "checkpoint.json").resolve()
    return results_root / kind / Path(original["path"]).name


def replay(args):
    started = time.monotonic()
    root = Path(__file__).resolve().parent
    package_root = (args.package_root or root / "datasets").resolve()
    results_root = args.results.resolve()
    receipt_path = args.output.resolve()
    require(not receipt_path.exists(), "replay receipt already exists")
    require(not (args.checkpoints_root and (args.bce_checkpoint or args.positive_margin_checkpoint)),
            "choose checkpoint root or explicit checkpoint paths")
    require((args.bce_checkpoint is None) == (args.positive_margin_checkpoint is None),
            "both explicit objective checkpoint paths are required")
    # No numerical import or network call precedes the declared CPU/offline policy.
    os.environ.update(CUDA_VISIBLE_DEVICES="", OMP_NUM_THREADS="2", MKL_NUM_THREADS="2",
                      HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_DATASETS_OFFLINE="1",
                      TOKENIZERS_PARALLELISM="false", PYTHONDONTWRITEBYTECODE="1")
    sys.dont_write_bytecode = True
    source_ref = pin(Path(__file__))
    plan_ref = pin((args.plan or root / "experiment-plan.json").resolve())
    plan = load(plan_ref)
    results_ref = pin(results_root / "training-results.json")
    results = load(results_ref)
    require(plan["schema"] == "support-retention-objective-matched-plan/v1" and plan["arms"] == list(ARMS),
            "current two-objective plan required")
    require(results["schema"] == "support-retention-training-results/v1" and results["status"] == "completed"
            and same_bytes(results["plan"], plan_ref), "completed pinned experiment required")
    require(results["runner"] == plan["runner"], "completed runner binding differs")
    require(plan["seed"] == 24606 and plan["hidden"] == 32 and plan["support_threshold"] == .5
            and plan["retention_lambda"] == {"bce": 0.0, "positive_margin": 1.0}, "closed objective recipe required")
    require(set(plan["retention"]) == set(COHORTS[1:]) and set(results["arms"]) == set(ARMS),
            "two selected arms and all five cohorts required")
    selection_barrier_ref = results["selection_barrier"]
    require(Path(selection_barrier_ref["path"]).name == "both-selected-before-final-and-retention.json",
            "selection barrier filename differs")
    selection_barrier_path = results_root / "both-selected-before-final-and-retention.json"
    selection_barrier = load(selection_barrier_ref, relocated_path=selection_barrier_path)
    require(selection_barrier["schema"] == "support-retention-final-reference-barrier/v1"
            and selection_barrier["references_parsed"] is False
            and selection_barrier["actual_optimizer_calls"] == 480, "saved selection barrier required")
    barrier_ref = results["predictions_barrier"]
    require(Path(barrier_ref["path"]).name == "all-final-and-retention-predictions-before-reference-joins.json",
            "prediction barrier filename differs")
    barrier_path = results_root / "all-final-and-retention-predictions-before-reference-joins.json"
    barrier = load(barrier_ref, relocated_path=barrier_path)
    require(barrier["schema"] == "support-retention-output-barrier/v1"
            and barrier["evaluation_references_parsed"] is False, "saved source-only prediction barrier required")
    require(set(barrier["panels"]) == {kind + "/" + cohort for kind in ("parent", *ARMS) for cohort in COHORTS},
            "complete fifteen-panel saved barrier required")
    cohorts = {"fresh_final": plan["inputs"]["final"],
               **{cohort: plan["retention"][cohort]["inputs"] for cohort in COHORTS[1:]}}
    input_rows = {name: load(reference) for name, reference in cohorts.items()}
    for name, rows in input_rows.items():
        require(type(rows) is list and len(rows) == ROWS_PER_COHORT
                and len({row["id"] for row in rows}) == ROWS_PER_COHORT, "complete unique source cohort required: " + name)
        for row in rows:
            require(type(row) is dict and set(row) == {"id", "source_group", "template", "condition_attachment", "source_text", "source_sha256"},
                    "closed source input row required")
            require(type(row["source_text"]) is str and sha256(row["source_text"].encode("utf-8")).hexdigest() == row["source_sha256"],
                    "source digest differs: " + row["id"])
            require(type(row["condition_attachment"]) is str and row["condition_attachment"] in ("rule", "statement"),
                    "explicit caller attachment required")
    sys.path.insert(0, str(package_root))
    import torch
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_retention_gate as head
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_retention_selection as selection
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_support_gate as reference
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_trigger_readout as trigger
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_support_action as action
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_span_decoder as donor
    from ipfs_datasets_py.logic.deontic.utils import deontic_parser
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    require(not torch.cuda.is_initialized() and torch.get_default_device().type == "cpu", "CPU replay required")
    producers = head.producer_pins()
    require(producers == results["producer_pins"] == plan["producer_pins"], "producer mismatch")
    require(same_bytes(pin(Path(selection.__file__)), plan["selection_policy"]), "selection source differs from plan")
    arms, denied_names = {}, None
    original_results_root = Path(barrier_ref["path"]).parent.resolve()
    for kind in ARMS:
        selected_ref = pin(results_root / kind / "selected.json")
        selected = load(selected_ref)
        require(selected == results["arms"][kind]["selected"] == selection_barrier["arms"][kind]["selected"],
                "selected receipt differs from completed results/barrier")
        original = selected["checkpoint"]
        steps_expected = selected["completed_updates"]
        require(type(steps_expected) is int and steps_expected in (0, 120, 240), "original selected progress required")
        require(Path(original["path"]).resolve() == original_results_root / kind / ("checkpoint-" + str(steps_expected) + ".json"),
                "selected checkpoint belongs to another result tree")
        checkpoint_ref = pin(checkpoint_path(args, kind, original, results_root))
        require(same_bytes(checkpoint_ref, original), "selected checkpoint container bytes differ")
        checkpoint = load(checkpoint_ref)
        rng_before_restore = torch.random.get_rng_state().clone()
        model, optimizer, steps = head.restore_retention_gate_checkpoint(checkpoint)
        require(torch.equal(rng_before_restore, torch.random.get_rng_state()), "restore changed CPU RNG")
        require(steps == steps_expected and model.config.to_dict() == {
            "seed": plan["seed"], "mode": "predicted_trigger", "hidden": plan["hidden"], "objective": kind},
                "selected residual objective/counters differ")
        require(checkpoint["profile"]["retention_lambda"] == plan["retention_lambda"][kind], "selected loss coefficient differs")
        before = head.save_retention_gate_checkpoint(model, optimizer, steps=steps)
        require(before == checkpoint, "model/full Adam restoration differs")
        parent_raw = before["parent"]["json_utf8"].encode("utf-8")
        require(sha256(parent_raw).hexdigest() == plan["parent_checkpoint"]["sha256"]
                and len(parent_raw) == plan["parent_checkpoint"]["bytes"], "selected parent provenance differs from plan")
        modes_before = {name: module.training for name, module in model.named_modules()}
        flags_before = {name: parameter.requires_grad for name, parameter in model.named_parameters()}
        require(all(parameter.grad is None for parameter in model.parameters()), "unexpected restored gradients")
        states_before = {name: value.detach().clone() for name, value in model.state_dict().items()}
        rng_before_prediction = torch.random.get_rng_state().clone()
        cohort_receipts = {}
        with ExitStack() as stack:
            names = []
            for owner, methods in (
                (head, ("RetentionGateExample", "train_retention_gate_step", "make_retention_gate_optimizer",
                        "_parent_emission_mask", "_positive_margin_penalty")),
                (reference, ("SupportGateExample", "train_support_gate_step", "make_support_gate_optimizer")),
                (action, ("SupportActionExample", "train_support_action_step", "make_support_action_optimizer", "_action_labels")),
                (trigger, ("TriggerReadoutExample", "train_trigger_readout_step", "make_trigger_readout_optimizer")),
                (donor, ("ScopeSpanExample", "train_scope_span_step", "make_scope_span_optimizer", "_labels")),
                (selection, ("SelectionConfig", "summarize_cases", "make_panel", "validate_panel", "retention_report", "eligible", "rank", "select")),
                (deontic_parser, tuple(name for name, value in vars(deontic_parser).items()
                                       if not name.startswith("__") and callable(value))),
                (torch.optim.AdamW, ("step", "zero_grad")),
                (torch.Tensor, ("backward", "cuda")),
                (torch.autograd, ("backward", "grad")),
                (torch.nn.Module, ("cuda",)),
                (torch.cuda, ("init", "set_device")),
            ):
                for method in methods:
                    stack.enter_context(patch.object(owner, method, denied))
                    names.append(getattr(owner, "__name__", type(owner).__name__) + "." + method)
            denied_names = names
            for cohort, rows in input_rows.items():
                expected_ref = barrier["panels"][kind + "/" + cohort]
                require(Path(expected_ref["path"]).resolve() == original_results_root / kind / (cohort + "-predictions.json"),
                        "expected prediction panel belongs to another original result tree")
                panel_path = results_root / kind / (cohort + "-predictions.json")
                expected = load(expected_ref, relocated_path=panel_path)
                require(type(expected) is dict and set(expected) == {"schema", "rows", "references_accessed_by_inference"}
                        and expected["schema"] == "support-retention-source-only-panel/v1"
                        and expected["references_accessed_by_inference"] is False, "source-only complete panel required")
                actual = []
                for row in rows:
                    prediction = head.predict_retention_gate(model, row["source_text"], row["condition_attachment"],
                                                             expected_source_sha256=row["source_sha256"])
                    require(prediction["model_executed"] and prediction["formal_output"] is None,
                            "executed zero-formal-authority prediction required")
                    require(not any(prediction[key] for key in ("source_semantics_verified", "accepted", "qualified", "formalized",
                                "proof_ready", "proof_authority", "target_access", "targets_used_at_inference")),
                            "prediction gained authority/targets")
                    if prediction["proposal"]:
                        require(not any(prediction["proposal"]["masks"].values()), "proposal gained admission")
                    logits = prediction["modality_logits"]
                    require(type(logits) is list and len(logits) == 3 and all(type(value) is float and math.isfinite(value) for value in logits),
                            "finite source-only modality diagnostics required")
                    actual.append({"id": row["id"], "source_group": row["source_group"], "source_sha256": row["source_sha256"],
                                   "class_logits": logits, "prediction": prediction})
                require(len(actual) == len(expected["rows"]) == ROWS_PER_COHORT and actual == expected["rows"],
                        "complete prediction dictionaries differ: " + kind + "/" + cohort)
                require(same_bytes(pin(panel_path), expected_ref), "saved panel changed during replay")
                cohort_receipts[cohort] = {"cases": ROWS_PER_COHORT, "full_output_exact": ROWS_PER_COHORT,
                    "inputs": cohorts[cohort], "original_expected_complete_panel": expected_ref,
                    "read_complete_panel": pin(panel_path)}
        after = head.save_retention_gate_checkpoint(model, optimizer, steps=steps)
        require(after == before == checkpoint, "model/full Adam/counters changed during replay")
        require(after["parent"]["json_utf8"].encode("utf-8") == parent_raw, "original full parent bytes changed")
        require(modes_before == {name: module.training for name, module in model.named_modules()}, "model/parent mode changed")
        require(flags_before == {name: parameter.requires_grad for name, parameter in model.named_parameters()}
                and all(parameter.grad is None for parameter in model.parameters()), "gradient custody changed")
        state_after = model.state_dict()
        require(set(states_before) == set(state_after) and all(torch.equal(value, state_after[name]) for name, value in states_before.items()),
                "model/parent tensors changed")
        require(torch.equal(rng_before_prediction, torch.random.get_rng_state()), "inference changed CPU RNG")
        require(not torch.cuda.is_initialized(), "CUDA initialized during replay")
        require(pin(checkpoint_ref["path"]) == checkpoint_ref and pin(selected_ref["path"]) == selected_ref,
                "selected receipt/checkpoint container changed during replay")
        arms[kind] = {"checkpoint": checkpoint_ref, "original_selected_checkpoint": original, "selected_receipt": selected_ref,
            "objective": kind, "retention_lambda": model.config.retention_lambda, "support_steps": steps,
            "new_action_updates": 0, "parent_action_steps": model.parent_action_steps, "cohorts": cohort_receipts,
            "complete_output_exact": 640, "new_gate_full_Adam_and_counters_unchanged": True,
            "parent_full_checkpoint_bytes_unchanged": True, "model_parent_tensors_modes_flags_and_rng_unchanged": True,
            "parent_sha256": sha256(parent_raw).hexdigest()}
        del model, optimizer, before, after, checkpoint, states_before, state_after
    require(pin(Path(__file__)) == source_ref and head.producer_pins() == producers, "helper/producer changed during replay")
    require(pin(results_root / "training-results.json") == results_ref and pin(plan_ref["path"]) == plan_ref,
            "results/plan changed during replay")
    require(same_bytes(pin(selection_barrier_path), selection_barrier_ref)
            and same_bytes(pin(barrier_path), barrier_ref), "barrier bytes changed during replay")
    require(all(pin(reference["path"]) == reference for reference in cohorts.values()),
            "source cohort bytes changed during replay")
    receipt = {"schema": "support-retention-read-only-complete-replay/v1", "status": "passed", "arms": arms,
        "complete_outputs_exact": 1280, "cohorts_per_arm": 5, "rows_per_cohort": ROWS_PER_COHORT,
        "additional_optimizer_updates": 0, "target_reference_files_opened": False, "training_targets_denied": True,
        "TRAIN_teacher_and_hinge_denied": True, "selection_schema_and_reselection_denied": True,
        "semantic_parser_callables_denied": True, "gradient_and_optimizer_updates_denied": True,
        "socket_connections_and_datagrams_denied": True, "offline_environment": True,
        "training_lease_claimed": False, "threads": 2, "interop_threads": 1, "device": "cpu", "cuda_initialized": False,
        "producer_pins": producers, "denied_prediction_entrypoints": denied_names,
        "source": source_ref, "plan": plan_ref, "training_results": results_ref,
        "original_selection_barrier": selection_barrier_ref, "read_selection_barrier": pin(selection_barrier_path),
        "original_prediction_barrier": barrier_ref, "read_prediction_barrier": pin(barrier_path),
        "source_only_replay_qualifies_legal_semantics": False, "default_promotion": False,
        "elapsed_seconds": time.monotonic() - started, "receipt_file_and_parent_directory_fsync": True}
    mkdir_durable(receipt_path.parent)
    with receipt_path.open("x") as stream:
        json.dump(receipt, stream, ensure_ascii=False, allow_nan=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(receipt_path.parent)
    print(json.dumps({"status": "passed", "complete_outputs_exact": 1280, "receipt": pin(receipt_path)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True, help="Completed runner result tree containing receipts/panels")
    parser.add_argument("--output", type=Path, required=True, help="New replay receipt path; existing files are refused")
    parser.add_argument("--plan", type=Path, help="Exact experiment plan, defaults beside this helper")
    parser.add_argument("--package-root", type=Path, help="Exact producer source tree, defaults to adjacent datasets")
    parser.add_argument("--checkpoints-root", type=Path, help="Exact mirrors at ROOT/{bce,positive_margin}/checkpoint.json")
    parser.add_argument("--bce-checkpoint", type=Path, help="Exact downloaded selected BCE container; supply both explicit paths")
    parser.add_argument("--positive-margin-checkpoint", type=Path, help="Exact downloaded selected positive-margin container")
    args = parser.parse_args()
    with ExitStack() as stack:
        for method in ("connect", "connect_ex", "sendto", "sendmsg"):
            if hasattr(socket.socket, method):
                stack.enter_context(patch.object(socket.socket, method, network_denied))
        for method in ("create_connection", "getaddrinfo", "gethostbyname", "gethostbyname_ex", "gethostbyaddr", "getnameinfo"):
            if hasattr(socket, method):
                stack.enter_context(patch.object(socket, method, network_denied))
        replay(args)


if __name__ == "__main__":
    main()
