"""Independent, data-only joins for the bounded native code AE experiment.

This module imports neither the supervisor nor its numerical trainer. It checks
provided manifests, extracted rows, native validation receipts and observed step
hash chains. It does not independently execute tensor arithmetic, read artifacts,
authenticate a step observer, or turn a consistent receipt into proof authority.
Canonical weight hashes must be produced with the native AE's sorted ASCII JSON
encoding. Loss monotonicity is deliberately not a qualification requirement.
"""
from __future__ import annotations

from collections import defaultdict
import hashlib
import json
import math
from pathlib import PurePosixPath
import re

SCHEMA = "terminal-codebase-ir-independent-training-review@1"
DOMAIN = "security-code@1"
WIDTH = 44
SPLITS = ("train", "validation", "evaluation")
_HASH = re.compile(r"[0-9a-f]{64}")


class TrainingEvidenceError(ValueError):
    """A supplied experiment record is malformed or has a contradictory join."""


def _require(condition, message):
    if not condition:
        raise TrainingEvidenceError(message)


def _wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def _sha(value):
    return hashlib.sha256(_wire(value)).hexdigest()


def _digest(value, label):
    _require(type(value) is str and _HASH.fullmatch(value) is not None,
             label + " requires an exact SHA256")
    return value


def _number(value, label, *, nonnegative=False):
    _require(type(value) in (int, float) and math.isfinite(value),
             label + " must be finite numeric evidence")
    _require(not nonnegative or value >= 0, label + " must be nonnegative")
    return float(value)


def _integer(value, label, low, high):
    _require(type(value) is int and low <= value <= high, label + " is out of bounds")
    return value


def _path(value):
    _require(type(value) is str and value, "source path must be nonempty")
    relative = PurePosixPath(value)
    _require(not relative.is_absolute() and relative.as_posix() == value
             and not any(part in {"..", ".git", ".runtime"} for part in relative.parts),
             "source path escapes its explicit scope")
    return value


def _mean(values):
    return math.fsum(values) / len(values)


def _close(left, right):
    return math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-12)


def _manifest(manifest):
    _require(type(manifest) is dict and type(manifest.get("tasks")) is list
             and 1 <= len(manifest["tasks"]) <= 64, "bounded explicit task manifest required")
    repository = manifest.get("captured_repository")
    _require(type(repository) is str and repository.startswith("/")
             and PurePosixPath(repository).as_posix() == repository
             and ".." not in PurePosixPath(repository).parts,
             "manifest requires its exact captured_repository")
    tasks, paths, source_groups = {}, {}, defaultdict(list)
    for task in manifest["tasks"]:
        _require(type(task) is dict and type(task.get("task_id")) is str
                 and task["task_id"] and task["task_id"] not in tasks,
                 "task IDs must be nonempty and exclusive")
        task_id, split = task["task_id"], task.get("split")
        _require(split in SPLITS, "task split must be train, validation or evaluation")
        sources = task.get("sources")
        _require(type(sources) is list and 1 <= len(sources) <= 256,
                 "task requires bounded explicit source rows")
        ledger, byte_count = {}, 0
        for row in sources:
            _require(type(row) is dict, "structured source row required")
            path = _path(row.get("path"))
            digest = _digest(row.get("sha256"), "source")
            size = _integer(row.get("bytes"), "source bytes", 0, 4_000_000)
            _require(path not in paths, "source paths must belong to one task only")
            paths[path] = task_id
            ledger[path] = digest
            byte_count += size
            source_groups[digest].append((task_id, split, path))
        tasks[task_id] = {"split": split, "ledger": ledger, "bytes": byte_count}
    _require(all(any(task["split"] == split for task in tasks.values()) for split in SPLITS),
             "all three task-exclusive splits are required")
    _require(not any(len({row[1] for row in group}) > 1 for group in source_groups.values()),
             "exact source bytes overlap between splits")
    ledger = {path: digest for task in tasks.values() if task["split"] == "train"
              for path, digest in task["ledger"].items()}
    _require(1 <= len(ledger) <= 256 and sum(task["bytes"] for task in tasks.values()
             if task["split"] == "train") <= 4_000_000,
             "training source ledger exceeds native bounds")
    return repository, tasks, ledger


def _features(tasks, task_features):
    _require(type(task_features) is dict and set(task_features) == set(tasks),
             "feature tasks differ from the source manifest")
    identities, ast_groups, feature_groups = {}, defaultdict(list), defaultdict(list)
    for task_id, rows in task_features.items():
        _require(type(rows) is list and 1 <= len(rows) <= 1024,
                 "task requires bounded extracted function rows")
        expected = {}
        for row in rows:
            _require(type(row) is dict, "structured feature row required")
            path = _path(row.get("path"))
            _require(path in tasks[task_id]["ledger"], "feature source does not join its task")
            _require(type(row.get("symbol")) is str and row["symbol"],
                     "feature symbol must be nonempty")
            line = _integer(row.get("line"), "feature line", 1, 2**31 - 1)
            ast_hash = _digest(row.get("ast_sha256"), "AST")
            identity = {"path": path, "symbol": row["symbol"], "line": line,
                        "ast_sha256": ast_hash}
            row_id = _digest(row.get("row_id"), "feature row")
            _require(row_id == _sha(identity) and row_id not in identities,
                     "feature row identity is duplicated or changed")
            values = row.get("features")
            _require(type(values) is list and len(values) == WIDTH,
                     "native feature width must be 44")
            numbers = [_number(value, "feature value", nonnegative=True) for value in values]
            _require(math.isclose(math.fsum(value * value for value in numbers), 1.,
                                 rel_tol=1e-10, abs_tol=1e-12),
                     "native feature normalization differs")
            identities[row_id] = task_id
            expected[row_id] = row
            key = (task_id, tasks[task_id]["split"], row_id)
            ast_groups[ast_hash].append(key)
            feature_groups[_sha(numbers)].append(key)
        tasks[task_id]["rows"] = expected
    _require(sum(len(task["rows"]) for task in tasks.values()
                 if task["split"] == "train") <= 1024,
             "training function rows exceed the native bound")
    _require(not any(len({row[1] for row in group}) > 1 for group in ast_groups.values()),
             "exact AST functions overlap between splits")
    collisions = [{"normalized_feature_sha256": digest,
                   "rows": [{"task_id": task, "split": split, "row_id": row}
                            for task, split, row in sorted(group)]}
                  for digest, group in sorted(feature_groups.items())
                  if len({row[1] for row in group}) > 1]
    return collisions


def _ranking(value, rows, *, latent_width=None, latent_required=False, zero=False):
    _require(type(value) is dict and type(value.get("ranks")) is list,
             "complete structured ranking required")
    ranks = value["ranks"]
    _require(len(ranks) == len(rows), "ranking omitted or duplicated function rows")
    errors, seen = [], set()
    width = latent_width
    for rank in ranks:
        _require(type(rank) is dict and rank.get("row_id") in rows
                 and rank["row_id"] not in seen, "ranking row identity differs")
        row = rows[rank["row_id"]]
        _require(all(rank.get(key) == row[key] for key in ("path", "symbol", "line")),
                 "ranking source join differs")
        seen.add(rank["row_id"])
        error = _number(rank.get("reconstruction_error"), "reconstruction error", nonnegative=True)
        errors.append(error)
        latent = rank.get("latent")
        if latent_required or latent is not None:
            _require(type(latent) is list and 2 <= len(latent) <= 16,
                     "closed finite latent vector required")
            if width is None:
                width = len(latent)
            _require(len(latent) == width, "latent width changed within a run")
            values = [_number(value, "latent value") for value in latent]
            _require(all(abs(value) <= 1.0000001 for value in values),
                     "tanh latent exceeds its numerical range")
            if zero:
                _require(all(value == 0 for value in values), "zero-weight control has nonzero latent")
        if zero:
            expected_error = math.fsum(value * value for value in row["features"]) / WIDTH
            _require(math.isclose(error, expected_error, rel_tol=1e-6, abs_tol=1e-8),
                     "zero-weight control error differs from native features")
    _require(seen == set(rows), "ranking does not retain every function row")
    _require(ranks == sorted(ranks, key=lambda row: (-row["reconstruction_error"], row["row_id"])),
             "ranking order differs from the native error order")
    mean = _number(value.get("mean_reconstruction_error"), "mean reconstruction error", nonnegative=True)
    _require(_close(mean, _mean(errors)), "mean reconstruction error differs from its rows")
    return mean, width


def _runs(repository, tasks, ledger, training_runs):
    _require(type(training_runs) is list and 1 <= len(training_runs) <= 32,
             "bounded native training runs required")
    rows = {row_id: row for task in tasks.values() if task["split"] == "train"
            for row_id, row in task["rows"].items()}
    result = {}
    for run in training_runs:
        _require(type(run) is dict and type(run.get("run_id")) is str and run["run_id"]
                 and run["run_id"] not in result, "exclusive run IDs required")
        run_id = run["run_id"]
        _require(run.get("schema") == "supervisor-code-autoencoder-descriptor@1"
                 and run.get("domain") == DOMAIN and run.get("repository") == repository,
                 "native descriptor domain or captured repository differs")
        _require(run.get("source_hashes") == ledger and type(run.get("paths")) in (list, tuple)
                 and len(run["paths"]) == len(ledger) and set(run["paths"]) == set(ledger),
                 "native training ledger must contain all training sources and no holdout sources")
        _require(run.get("source_count") == len(ledger) and run.get("sample_count") == len(rows),
                 "native descriptor source or function count differs")
        _digest(run.get("checkpoint_sha256"), "checkpoint")
        _digest(run.get("receipt_sha256"), "receipt")
        _require(run.get("authority") == "unverified_candidate_only"
                 and run.get("proof_authority") is False
                 and type(run.get("provider_calls")) is int and run["provider_calls"] == 0,
                 "native descriptor authority or provider scope differs")
        metrics = run.get("metrics")
        _require(type(metrics) is dict, "native training metrics required")
        epochs = _integer(metrics.get("epochs"), "epochs", 1, 32)
        seed = _integer(metrics.get("seed"), "seed", 0, 2**31 - 1)
        _require(run.get("epochs_completed") == epochs, "epoch counts disagree")
        initial = _digest(metrics.get("initial_weights_sha256"), "initial weights")
        final = _digest(metrics.get("final_weights_sha256"), "final weights")
        _require(initial != final, "checkpoint weights did not change")
        microbatches = (len(rows) + 127) // 128
        _require(metrics.get("microbatch_count") == microbatches
                 and metrics.get("native_kernel_calls") == epochs * microbatches,
                 "native kernel and microbatch counts disagree")
        for name in ("native_objective_losses", "native_gradient_norms"):
            values = metrics.get(name)
            _require(type(values) is list and len(values) == epochs,
                     "native epoch metric coverage differs")
            numbers = [_number(value, name, nonnegative=name == "native_gradient_norms") for value in values]
            if name == "native_gradient_norms":
                _require(any(value > 0 for value in numbers), "no positive native gradient observed")
        before = _number(metrics.get("before_reconstruction_loss"), "training before MSE", nonnegative=True)
        after = _number(metrics.get("after_reconstruction_loss"), "training after MSE", nonnegative=True)
        _require(metrics.get("holdout_evaluated") is False
                 and metrics.get("training_scope") == "transductive_admitted_code_functions",
                 "native transductive receipt was relabeled as holdout evaluation")
        steps = run.get("observed_steps")
        _require(type(steps) is list and len(steps) == epochs,
                 "observed optimizer step count differs from epochs")
        previous = initial
        for number, step in enumerate(steps, start=1):
            _require(type(step) is dict and type(step.get("step")) is int and step["step"] == number,
                     "optimizer step order differs")
            before_hash = _digest(step.get("before_weights_sha256"), "step before weights")
            after_hash = _digest(step.get("after_weights_sha256"), "step after weights")
            _require(before_hash == previous and before_hash != after_hash,
                     "optimizer weight hash chain broke or has no update")
            previous = after_hash
        _require(previous == final, "optimizer step chain does not reach final weights")
        _ranking({"ranks": run.get("ranks"), "mean_reconstruction_error": after}, rows)
        checked = run.get("validation")
        _require(type(checked) is dict and checked.get("status") == "verified"
                 and checked.get("domain") == DOMAIN
                 and checked.get("receipt_sha256") == run["receipt_sha256"]
                 and checked.get("source_count") == len(ledger)
                 and checked.get("sample_count") == len(rows)
                 and checked.get("authority") == "unverified_candidate_only"
                 and all(checked.get(name) is False for name in
                         ("proof_authority", "formalization_authority", "omission_authority")),
                 "native validation receipt binding differs")
        _ranking({"ranks": checked.get("ranks"), "mean_reconstruction_error": after}, rows,
                 latent_required=True)
        _require([{key: rank[key] for key in ("row_id", "path", "symbol", "line", "reconstruction_error")}
                  for rank in checked["ranks"]] == run["ranks"],
                 "native validation and descriptor ranks differ")
        result[run_id] = {"run": run, "seed": seed, "epochs": epochs, "initial": initial,
                          "final": final, "training_before": before, "training_after": after}
    return result


def verify_training_evidence(*, manifest: dict, task_features: dict,
                             training_runs: list[dict], evaluations: list[dict]) -> dict:
    """Check explicit experiment joins and report empirical outcomes honestly.

    ``qualified`` concerns receipt consistency only. Caller-supplied native
    validation and optimizer observations are not authenticated by this module.
    The evaluation panel never participates in an acceptance criterion here.
    """
    repository, tasks, ledger = _manifest(manifest)
    collisions = _features(tasks, task_features)
    runs = _runs(repository, tasks, ledger, training_runs)
    _require(type(evaluations) is list and len(evaluations) == len(runs) * len(tasks),
             "every run requires every task evaluation")
    panels, seen, widths = defaultdict(lambda: defaultdict(list)), set(), {}
    evaluation_fingerprints = defaultdict(dict)
    for evaluation in evaluations:
        _require(type(evaluation) is dict, "structured task evaluation required")
        run_id, task_id = evaluation.get("run_id"), evaluation.get("task_id")
        _require(run_id in runs and task_id in tasks and (run_id, task_id) not in seen,
                 "evaluation run/task join is missing or duplicated")
        seen.add((run_id, task_id))
        task, run = tasks[task_id], runs[run_id]
        _require(evaluation.get("split") == task["split"]
                 and type(evaluation.get("feature_count")) is int
                 and evaluation["feature_count"] == len(task["rows"]),
                 "evaluation split or function count differs")
        _require(evaluation.get("initial_weights_sha256") == run["initial"],
                 "untrained control does not bind the native initial weights")
        values = {}
        for name in ("trained", "untrained", "zero_weights"):
            values[name], width = _ranking(evaluation.get(name), task["rows"],
                latent_width=widths.get(run_id), latent_required=True, zero=name == "zero_weights")
            widths[run_id] = width
        identity = evaluation.get("deterministic_identity")
        _require(type(identity) is dict and type(identity.get("mean_reconstruction_error")) in (int, float)
                 and identity["mean_reconstruction_error"] == 0,
                 "deterministic extraction identity must reconstruct uncompressed features exactly")
        values["deterministic_identity"] = 0.
        evaluation_fingerprints[run_id][task_id] = _sha({name: evaluation[name]
            for name in ("trained", "untrained", "zero_weights", "deterministic_identity")})
        panels[run_id][task["split"]].append({"task_id": task_id, "feature_count": len(task["rows"]),
                                             "errors": values})
    summaries = []
    for run_id, run in runs.items():
        splits = {}
        for split in SPLITS:
            panel = panels[run_id][split]
            count = sum(row["feature_count"] for row in panel)
            weighted = {name: math.fsum(row["errors"][name] * row["feature_count"] for row in panel) / count
                        for name in ("trained", "untrained", "zero_weights", "deterministic_identity")}
            if split == "train":
                _require(_close(weighted["trained"], run["training_after"])
                         and _close(weighted["untrained"], run["training_before"]),
                         "training evaluation differs from native before/after MSE")
            splits[split] = {"task_count": len(panel), "feature_count": count,
                "function_weighted_mean_reconstruction_error": weighted,
                "task_macro_mean_reconstruction_error": {name: _mean([row["errors"][name] for row in panel])
                    for name in weighted},
                "trained_improves_untrained": weighted["trained"] < weighted["untrained"],
                "trained_improves_zero_weights": weighted["trained"] < weighted["zero_weights"],
                "trained_matches_uncompressed_identity": weighted["trained"] == 0,
                "tasks": sorted(panel, key=lambda row: row["task_id"])}
        summaries.append({"run_id": run_id, "seed": run["seed"], "epochs": run["epochs"],
            "optimizer_steps": run["epochs"], "initial_weights_sha256": run["initial"],
            "final_weights_sha256": run["final"],
            "training_mse_decreased": run["training_after"] < run["training_before"], "splits": splits})
    groups = defaultdict(list)
    for run_id, run in runs.items():
        groups[(run["seed"], run["epochs"], widths[run_id])].append(run_id)
    replays = []
    for (seed, epochs, width), run_ids in sorted(groups.items()):
        if len(run_ids) < 2:
            continue
        originals = [runs[run_id] for run_id in run_ids]
        _require(len({row["initial"] for row in originals}) == 1
                 and len({row["final"] for row in originals}) == 1,
                 "same-seed epoch replay changed parameter hashes")
        _require(all(evaluation_fingerprints[run_id] == evaluation_fingerprints[run_ids[0]]
                     for run_id in run_ids),
                 "same-seed epoch replay changed task inference")
        replays.append({"seed": seed, "epochs": epochs, "latent_width": width,
                       "run_ids": sorted(run_ids), "exact_parameter_hash_match": True,
                       "exact_task_numeric_output_match": True})
    return {"schema": SCHEMA, "qualified": True,
        "qualification_scope": "provided data joins, step hash chains and finite numeric observations",
        "artifact_bytes_independently_read": False, "tensor_forward_independently_reexecuted": False,
        "step_observer_authenticated": False, "native_validation_receipts_bound": True,
        "manifest_sha256": _sha(manifest), "training_ledger_sha256": _sha(ledger),
        "task_features_sha256": _sha(task_features), "training_run_count": len(runs),
        "optimizer_steps_total": sum(run["epochs"] for run in runs.values()),
        "training_feature_count": sum(len(task["rows"]) for task in tasks.values() if task["split"] == "train"),
        "all_function_rows_retained": True, "task_splits_exclusive": True,
        "exact_source_cross_split_overlap": False, "exact_ast_cross_split_overlap": False,
        "normalized_feature_cross_split_collisions": collisions,
        "feature_collision_is_source_leakage": False,
        "collision_interpretation": "distinct programs can share the lossy 44-feature representation",
        "reproducibility": {"exact_replay_pairs_observed": bool(replays), "groups": replays},
        "runs": sorted(summaries, key=lambda row: row["run_id"]),
        "native_objective_monotonicity_required": False,
        "claims": {"source_to_model_equivalence_proved": False,
                   "asymptotic_optimizer_convergence_proved": False,
                   "full_task_satisfaction_proved": False, "provider_token_savings_proved": False,
                   "learned_features_have_proof_authority": False,
                   "generalization_beyond_measured_tasks_proved": False}}
