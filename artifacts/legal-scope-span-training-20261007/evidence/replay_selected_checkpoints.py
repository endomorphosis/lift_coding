"""Read-only CPU checkpoint replay. No references or optimizer steps."""
from contextlib import ExitStack
from hashlib import sha256
import argparse
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path)
    parser.add_argument("--threads", type=int, choices=(1, 2), default=2)
    args = parser.parse_args()
    started = time.monotonic()
    sys.path.insert(0, str(args.package_root))
    import torch
    from ipfs_datasets_py.logic.formalization.autoencoder import legal_scope_span_decoder as head
    from ipfs_datasets_py.logic.deontic.utils import deontic_parser
    torch.set_num_threads(args.threads)
    torch.use_deterministic_algorithms(True)
    assert not torch.cuda.is_initialized()
    inputs = json.loads(args.inputs.read_text())
    arms = {}

    def denied(*a, **kw):
        raise AssertionError("read-only replay reached training or semantic parser")

    for name in ("bytekernel1", "bytekernel3"):
        selected = json.loads((args.results / name / "selected.json").read_text())
        path = (args.checkpoint_root / name / "checkpoint.json") if args.checkpoint_root else Path(selected["checkpoint"]["path"])
        raw = path.read_bytes()
        assert sha256(raw).hexdigest() == selected["checkpoint"]["sha256"]
        checkpoint = json.loads(raw)
        ambient = torch.random.get_rng_state().clone()
        model, optimizer, steps = head.restore_scope_span_checkpoint(checkpoint)
        assert torch.equal(ambient, torch.random.get_rng_state())
        assert steps == selected["completed_updates"]
        assert head.save_scope_span_checkpoint(model, optimizer, steps=steps) == checkpoint
        expected = json.loads((args.results / name / "final-predictions.json").read_text())["rows"]
        assert len(expected) == len(inputs) == 128
        actual = []
        with ExitStack() as stack:
            for owner, names in (
                (head, ("_labels", "ScopeSpanExample", "train_scope_span_step")),
                (deontic_parser, ("extract_normative_elements", "analyze_normative_sentence", "classify_modal")),
                (optimizer, ("step",)),
            ):
                for method in names:
                    stack.enter_context(patch.object(owner, method, denied))
            for row in inputs:
                result = head.predict_scope_span_decoder(model, row["source_text"], row["condition_attachment"],
                    expected_source_sha256=row["source_sha256"])
                assert result["formal_output"] is None
                assert not any(result[key] for key in ("accepted", "qualified", "formalized", "proof_ready", "proof_authority", "source_semantics_verified", "target_access"))
                if result["proposal"]:
                    assert not any(result["proposal"]["masks"].values())
                actual.append(dict(id=row["id"], source_group=row["source_group"], source_sha256=row["source_sha256"], prediction=result))
        differences = []
        for index, (got, want) in enumerate(zip(actual, expected)):
            if got != want:
                differences.append(dict(index=index, changed_prediction_keys=[key for key in got["prediction"]
                    if got["prediction"][key] != want["prediction"][key]],
                    support_probability_difference=got["prediction"].get("support_probability", 0)-want["prediction"].get("support_probability", 0)))
        if differences:
            print(json.dumps(dict(arm=name, threads=args.threads, differing_count=len(differences), differences=differences)))
        assert actual == expected, name + " full output replay differs"
        assert head.save_scope_span_checkpoint(model, optimizer, steps=steps) == checkpoint
        assert torch.equal(ambient, torch.random.get_rng_state())
        arms[name] = dict(checkpoint_sha256=sha256(raw).hexdigest(), selected_steps=steps,
            full_output_exact=len(actual), cases=len(actual), model_and_full_Adam_unchanged=True,
            ambient_rng_unchanged=True)
    receipt = dict(schema="scope-span-read-only-checkpoint-replay/v1", status="passed", arms=arms,
        device="cpu", threads=args.threads, cuda_initialized=torch.cuda.is_initialized(),
        additional_optimizer_updates=0, references_opened=False, source_parsers_denied=True,
        training_lease_claimed=False, producer_pins=head.producer_pins(), elapsed_seconds=time.monotonic()-started)
    with args.receipt.open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
