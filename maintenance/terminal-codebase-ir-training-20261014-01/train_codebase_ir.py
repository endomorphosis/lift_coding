"""Task-exclusive Terminal Bench structural-AE pilot, using the native trainer.

Captured public code is parsed but never imported or executed. Learned vectors
are candidate metadata. This experiment does not admit a supervisor worker or
prove source behavior, optimizer convergence, or benchmark task satisfaction.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
RUNS = (("primary-1729", 1729, 32), ("replay-1729", 1729, 32),
        ("seed-2718", 2718, 32), ("seed-31415", 31415, 32),
        ("short-1729-8", 1729, 8))
POLICY = {"schema": "terminal-codebase-ir-training-policy@1", "runs": list(RUNS),
    "latent_width": 8, "input_width": 44, "optimizer": "native_torch_Adam_lr_0.02",
    "max_optimizer_steps": 136, "max_functions": 1024, "torch_intraop_threads": 1, "lean_threads": 1,
    "cpu_seconds_hard_limit": 180, "address_space_bytes_hard_limit": 12 * 1024**3,
    "file_bytes_hard_limit": 256 * 1024**2, "outer_deadline_seconds": 300,
    "checkpoint_selection": "predeclared_primary_seed_final_epoch_no_holdout_selection",
    "training_only_ledger": True, "source_execution": False,
    "hidden_verifier_inputs": False, "network_calls_permitted": 0,
    "native_admission_integration": False, "global_durable_budget": False,
    "proof_authority": False, "source_model_equivalence_proved": False,
    "asymptotic_optimizer_convergence_proved": False, "full_task_satisfaction": False}


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path, maximum=4_000_000):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("canonical input required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > maximum:
            raise ValueError("bounded single-link regular input required")
        raw = stream.read(maximum + 1)
        end = os.fstat(stream.fileno())
    if len(raw) > maximum or (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
        info.st_ctime_ns) != (end.st_dev, end.st_ino, end.st_size, end.st_mtime_ns, end.st_ctime_ns):
        raise ValueError("input grew or changed during acquisition")
    return raw


def write(path, value):
    raw = wire(value)
    with Path(path).open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fchmod(stream.fileno(), 0o444)
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(raw), "sha256": sha(raw)}


def validate_manifest(manifest):
    if manifest.get("schema") != "terminal-codebase-ir-corpus@1":
        raise ValueError("frozen task-exclusive corpus required")
    tasks = manifest["tasks"]
    if not isinstance(tasks, list) or not 3 <= len(tasks) <= 16:
        raise ValueError("bounded task corpus required")
    task_ids, paths, splits = set(), set(), set()
    source_splits = {}
    for task in tasks:
        task_id, split = task["task_id"], task["split"]
        if task_id in task_ids or split not in {"train", "validation", "evaluation"}:
            raise ValueError("task-exclusive fixed split required")
        task_ids.add(task_id)
        splits.add(split)
        if not task["sources"]:
            raise ValueError("no source for task")
        if (task["instruction"]["path"] != task_id + "/instruction.md"
                or task["environment"]["path"] != task_id + "/environment/Dockerfile"
                or any(not pin["path"].startswith(task_id + "/environment/")
                       or not pin["path"].endswith(".py") for pin in task["sources"])):
            raise ValueError("explicit public source, instruction and environment roles required")
        for pin in [*task["sources"], task["instruction"], task["environment"]]:
            path = PurePosixPath(pin["path"])
            if (path.is_absolute() or str(path) != pin["path"] or path.parts[0] != task_id
                    or any(part in {"..", ".git", "tests", "solution"} for part in path.parts)
                    or path in paths or type(pin["bytes"]) is not int or not 0 < pin["bytes"] <= 1_000_000
                    or len(pin["sha256"]) != 64
                    or any(c not in "0123456789abcdef" for c in pin["sha256"])):
                raise ValueError("explicit bounded public task input required")
            paths.add(path)
        for pin in task["sources"]:
            prior = source_splits.setdefault(pin["sha256"], split)
            if prior != split:
                raise ValueError("crosssplit source leakage")
    if splits != {"train", "validation", "evaluation"}:
        raise ValueError("all fixed task splits required")
    return manifest


def capture(manifest, destination):
    validate_manifest(manifest)
    repository = Path(manifest["repository"]["path"])
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip()
    if head != manifest["repository"]["head"]:
        raise ValueError("Terminal Bench commit changed")
    selected, total = [], 0
    for task in manifest["tasks"]:
        for pin in [*task["sources"], task["instruction"], task["environment"]]:
            raw = read(repository / pin["path"], 1_000_000)
            total += len(raw)
            if sha(raw) != pin["sha256"] or len(raw) != pin["bytes"] or total > 4_000_000:
                raise ValueError("public source provenance or corpus bound changed")
            identity = head + ":" + pin["path"]
            tracked_size = int(subprocess.check_output(["git", "cat-file", "-s", identity], cwd=repository))
            if tracked_size != len(raw) or subprocess.check_output(["git", "show", identity], cwd=repository) != raw:
                raise ValueError("selected file differs from committed pre-edit public task")
            selected.append((pin, raw))
    destination.mkdir(mode=0o700)
    for pin, raw in selected:
        target = destination / pin["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
            os.fchmod(stream.fileno(), 0o444)
    if subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repository, text=True).strip() != head:
        raise ValueError("Terminal Bench commit changed during capture")
    return {**manifest, "captured_repository": str(destination),
            "captured_bytes": total, "selection": "only_named_public_environment_source_instruction_Dockerfile"}


def extract_tasks(ae, manifest, repository):
    features, sources, instructions = {}, {}, {}
    for task in manifest["tasks"]:
        ledger = ae._ledger({pin["path"]: pin["sha256"] for pin in task["sources"]})
        raw = ae._sources(repository, ledger)
        rows, unsupported = ae._features(raw, sorted(ledger), 1024)
        if unsupported:
            raise ValueError("selected native feature source unsupported; no silent omission")
        features[task["task_id"]] = rows
        sources[task["task_id"]] = {name: body.decode("utf-8") for name, body in raw.items()}
        pin = task["instruction"]
        body = read(repository / pin["path"])
        if sha(body) != pin["sha256"]:
            raise ValueError("public instruction changed")
        instructions[task["task_id"]] = body.decode("utf-8")
    seen = {}
    for task in manifest["tasks"]:
        for row in features[task["task_id"]]:
            prior = seen.setdefault(row["ast_sha256"], task["split"])
            if prior != task["split"]:
                raise ValueError("crosssplit function AST leakage")
    return features, sources, instructions


def weights_hash(ae, parameters):
    return ae._sha(ae._json([value.detach().tolist() for value in parameters]))


@contextmanager
def observe_steps(torch, ae, maximum):
    """Observe calls to the original optimizer; retain no trainable replacement."""
    original = torch.optim.Adam.step
    steps = []
    def observed(optimizer, *args, **kwargs):
        if len(steps) >= maximum:
            raise ValueError("predeclared optimizer step budget exceeded")
        parameters = [p for group in optimizer.param_groups for p in group["params"]]
        before = weights_hash(ae, parameters)
        result = original(optimizer, *args, **kwargs)
        steps.append({"step": len(steps) + 1, "before_weights_sha256": before,
                      "after_weights_sha256": weights_hash(ae, parameters)})
        return result
    torch.optim.Adam.step = observed
    try:
        yield steps
    finally:
        torch.optim.Adam.step = original


def seeded_parameters(torch, seed, width, latent):
    generator = torch.Generator(device="cpu").manual_seed(seed)
    return [(torch.randn(width, latent, generator=generator) * 0.1), torch.zeros(latent),
            (torch.randn(latent, width, generator=generator) * 0.1), torch.zeros(width)]


def check_parameters(torch, weights, width, latent):
    if not isinstance(weights, list) or len(weights) != 4:
        raise ValueError("closed native checkpoint required")
    parameters = [torch.tensor(value, dtype=torch.float32, device="cpu") for value in weights]
    for value, shape in zip(parameters, [(width, latent), (latent,), (latent, width), (width,)]):
        if tuple(value.shape) != shape or not torch.isfinite(value).all():
            raise ValueError("finite exact tensor shapes required")
    return parameters


def training_batch(task_features, paths):
    # Preserve the trainer's sorted file paths and native AST traversal within
    # each file. Float32 matrix arithmetic can differ with another batch shape.
    return [row for path in paths for rows in task_features.values() for row in rows if row["path"] == path]


def partition_inference(found, rows):
    identities = {row["row_id"] for row in rows}
    ranks = [row for row in found["ranks"] if row["row_id"] in identities]
    if len(ranks) != len(rows):
        raise ValueError("whole-batch partition lost source functions")
    return {**found, "ranks": ranks,
            "mean_reconstruction_error": sum(row["reconstruction_error"] for row in ranks) / len(ranks)}


def evaluate(ae, torch, *, descriptor, task_features, tasks):
    checkpoint_path = Path(descriptor["output"]) / "checkpoint.json"
    raw = read(checkpoint_path)
    if sha(raw) != descriptor["checkpoint_sha256"]:
        raise ValueError("trained checkpoint changed before heldout inference")
    checkpoint = json.loads(raw)
    width, latent = checkpoint["input_width"], checkpoint["latent_width"]
    trained = check_parameters(torch, checkpoint["weights"], width, latent)
    initial = seeded_parameters(torch, descriptor["metrics"]["seed"], width, latent)
    initial_hash = weights_hash(ae, initial)
    if initial_hash != descriptor["metrics"]["initial_weights_sha256"]:
        raise ValueError("untrained control differs from actual native initialization")
    zeros = [torch.zeros_like(value) for value in trained]
    result = []
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    try:
        train_rows = training_batch(task_features, descriptor["paths"])
        training = {name: ae._inference(torch, train_rows, values)
                    for name, values in (("trained", trained), ("untrained", initial), ("zero_weights", zeros))}
        for task in tasks:
            rows = task_features[task["task_id"]]
            panel = {name: partition_inference(training[name], rows) if task["split"] == "train"
                     else ae._inference(torch, rows, values)
                     for name, values in (("trained", trained), ("untrained", initial), ("zero_weights", zeros))}
            result.append({"run_id": descriptor["run_id"], "task_id": task["task_id"],
                "split": task["split"], "feature_count": len(rows),
                "initial_weights_sha256": initial_hash,
                "train_inference_batch": "complete_sorted_training_scope_partitioned_after_forward",
                **panel,
                "deterministic_identity": {"mean_reconstruction_error": 0.0,
                    "input_width": width, "retained_width": width,
                    "representation": "uncompressed_exact_structural_features", "proof_authority": False}})
    finally:
        torch.set_num_threads(previous)
    if read(checkpoint_path) != raw:
        raise ValueError("trained checkpoint changed during heldout inference")
    return result


def run(output, manifest_path):
    resource.setrlimit(resource.RLIMIT_CPU, (POLICY["cpu_seconds_hard_limit"], POLICY["cpu_seconds_hard_limit"]))
    resource.setrlimit(resource.RLIMIT_AS, (POLICY["address_space_bytes_hard_limit"], POLICY["address_space_bytes_hard_limit"]))
    resource.setrlimit(resource.RLIMIT_FSIZE, (POLICY["file_bytes_hard_limit"], POLICY["file_bytes_hard_limit"]))
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as ae
    import torch
    import numpy
    from independent_training_review import verify_training_evidence
    from metadata_projections import build_metadata_records, hydrate_and_verify_records, qualify_recorded_losses
    if torch.get_default_dtype() != torch.float32:
        raise ValueError("native untransferred initialization requires float32 default")
    manifest_raw = read(manifest_path)
    manifest = validate_manifest(json.loads(manifest_raw))
    if output.resolve() != output or output.exists():
        raise ValueError("fresh canonical experiment namespace required")
    output.mkdir(mode=0o700)
    write(output / "policy.json", POLICY)
    captured = capture(manifest, output / "captured-sources")
    write(output / "captured-manifest.json", captured)
    repository = Path(captured["captured_repository"])
    torch_module, kernel, batching = ae._dependencies()
    # Torch exposes its version as a str subclass. Catalog rows require exact
    # ordinary JSON types; normalize through the same finite evidence encoding.
    implementation = json.loads(wire(ae._implementation(torch_module, kernel, batching)))
    write(output / "runtime.json", {"python": sys.version, "executable": sys.executable,
        "torch_version": torch.__version__, "torch_module": torch.__file__,
        "numpy_version": numpy.__version__, "implementation": implementation,
        "training_script_sha256": sha(read(Path(__file__).resolve()))})
    features, sources, instructions = extract_tasks(ae, captured, repository)
    write(output / "task-features.json", features)
    train_ledger = {pin["path"]: pin["sha256"] for task in manifest["tasks"] if task["split"] == "train"
                    for pin in task["sources"]}
    reports, evaluations = [], []
    started = time.monotonic()
    for run_id, seed, epochs in RUNS:
        print(json.dumps({"stage": "native_training_start", "run_id": run_id, "seed": seed,
                          "epochs": epochs}), flush=True)
        with observe_steps(torch, ae, epochs) as observed:
            descriptor = ae.train_codebase_autoencoder(repository=repository, paths=sorted(train_ledger),
                source_hashes=train_ledger, output=output / run_id / "code-autoencoder",
                epochs=epochs, latent_dim=8, seed=seed, max_functions=1024)
        validated = ae.validate_codebase_autoencoder(repository=repository, expected_receipt=descriptor)
        report = {**descriptor, "paths": sorted(train_ledger), "run_id": run_id,
                  "observed_steps": observed, "validation": validated}
        write(output / (run_id + "-report.json"), report)
        panel = evaluate(ae, torch, descriptor=report, task_features=features, tasks=manifest["tasks"])
        write(output / (run_id + "-evaluation.json"), panel)
        ae.validate_codebase_autoencoder(repository=repository, expected_receipt=descriptor)
        reports.append(report)
        evaluations.extend(panel)
        print(json.dumps({"stage": "native_training_complete", "run_id": run_id,
            "observed_optimizer_steps": len(observed), "training_mse_before": descriptor["metrics"]["before_reconstruction_loss"],
            "training_mse_after": descriptor["metrics"]["after_reconstruction_loss"]}), flush=True)
    review = verify_training_evidence(manifest=captured, task_features=features,
                                     training_runs=reports, evaluations=evaluations)
    write(output / "training-review.json", review)
    lean = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean")
    logic = qualify_recorded_losses(training_runs=reports, output=output / "logic", lean_executable=lean)
    write(output / "logic-report.json", logic)
    primary = {row["task_id"]: row["trained"] for row in evaluations if row["run_id"] == "primary-1729"}
    records = build_metadata_records(task_sources=sources, instructions=instructions,
        task_features=features, inference=primary, training_runs=reports,
        provenance={"corpus_manifest_sha256": sha(manifest_raw), "captured_manifest": captured,
                    "review": review, "logic_report": logic, "policy": POLICY})
    metadata = hydrate_and_verify_records(records=records, output=output / "metadata",
        source_snapshot={"schema": "terminal-codebase-ir-training-source-snapshot@1",
            "manifest_sha256": sha(manifest_raw), "captured_manifest": captured,
            "implementation": implementation, "primary_checkpoint_sha256": reports[0]["checkpoint_sha256"]})
    write(output / "metadata-report.json", metadata)
    repeated, _, _ = extract_tasks(ae, captured, repository)
    if repeated != features or read(manifest_path) != manifest_raw or ae._implementation(torch_module, kernel, batching) != implementation:
        raise ValueError("source, frozen corpus, or numerical implementation changed")
    for report in reports:
        descriptor = {key: value for key, value in report.items()
                      if key not in {"paths", "run_id", "observed_steps", "validation"}}
        ae.validate_codebase_autoencoder(repository=repository, expected_receipt=descriptor)
    elapsed = time.monotonic() - started
    summary = {"schema": "terminal-codebase-ir-training-experiment@1", "completed": True,
        "corpus_manifest_sha256": sha(manifest_raw), "policy": POLICY,
        "training_review": review, "logic": logic, "metadata": metadata,
        "optimizer_steps": sum(len(report["observed_steps"]) for report in reports),
        "elapsed_training_evaluation_metadata_seconds": elapsed,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "latent_width": 8, "feature_width": 44,
        "source_execution": False, "source_model_equivalence_proved": False,
        "asymptotic_optimizer_convergence_proved": False, "full_task_satisfaction": False,
        "official_terminal_bench_harness_executed": False, "supervisor_native_admission_executed": False,
        "provider_token_savings_measured": False, "global_durable_budget": False}
    write(output / "result.json", summary)
    print(json.dumps({"stage": "experiment_complete", "optimizer_steps": summary["optimizer_steps"],
                      "peak_rss_kib": summary["peak_rss_kib"]}), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=ROOT / "corpus-manifest-01.json")
    args = parser.parse_args()
    try:
        run(args.output.absolute(), args.manifest.absolute())
    except Exception as error:
        if args.output.is_dir() and not (args.output / "failure.json").exists():
            write(args.output / "failure.json", {"error_type": type(error).__name__, "error": str(error),
                "completed": False, "source_model_equivalence_proved": False,
                "asymptotic_optimizer_convergence_proved": False, "full_task_satisfaction": False})
        raise


if __name__ == "__main__":
    main()
