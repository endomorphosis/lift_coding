"""Source-bound structural metadata and finite, measured loss ordering.

Native parsing/scanning supplies AST and graph observations. Learned vectors
remain candidates: this module does not infer contracts from a neural latent,
execute repository code, prove Python semantics, or prove optimizer convergence.
Only the explicit hydration function opens its caller-selected new catalog.
"""
from __future__ import annotations

from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re


SCHEMA = "terminal-codebase-training-metadata-projection@1"
LOSS_SCHEMA = "terminal-codebase-training-recorded-loss-check@1"
AUTHORITY = {"proof_authority": False, "execution_authority": False,
    "completion_authority": False, "formalization_authority": False,
    "source_semantics_verified": False, "source_model_equivalence_proved": False,
    "full_task_satisfaction_proved": False, "optimizer_convergence_proved": False}
MAX_TASKS = 32
MAX_SOURCES = 256
MAX_SOURCE_BYTES = 4_000_000
MAX_FUNCTIONS_PER_TASK = 1024
MAX_RUNS = 64
_TASK = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


class ProjectionError(ValueError):
    pass


def _require(value, message):
    if not value:
        raise ProjectionError(message)


def _wire(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ProjectionError("finite ordinary JSON projection required") from exc


def _copy(value):
    from benchmarks.agent_supervisor.container_coding.codebase_ir_metadata import _plain
    raw = _wire(value)
    _require(len(raw) <= 32_000_000, "complete producer artifact exceeds experiment bound")
    # Native to_dict values may contain tuples. Preserve their ordinary JSON
    # representation, with a larger bounded container allowance before the
    # existing lossless chunker restores the storage's unchanged row limits.
    detached = json.loads(raw)
    try:
        _plain(detached, budget=[1_000_000])
    except ValueError as exc:
        raise ProjectionError("bounded ordinary JSON projection required") from exc
    return detached


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _id(kind, task_id, payload):
    return _sha(_wire({"kind": kind, "task_id": task_id, "payload": payload}))


def _row(kind, task_id, payload, **fields):
    # The original native row is retained whole. The outer identity includes
    # task custody so identical source paths/functions in two tasks do not clash.
    return {"row_id": _id(kind, task_id, {"record": payload, **fields}),
        "task_id": task_id, "record": _copy(payload), **fields, **AUTHORITY}


def _path(value):
    _require(type(value) is str and bool(value) and "\\" not in value,
        "canonical task-relative source path required")
    path = PurePosixPath(value)
    _require(not path.is_absolute() and str(path) == value
        and all(part not in {".", "..", ".git", ".runtime"} for part in path.parts),
        "source path outside explicit task input scope")
    return value


def _sources(task_sources, instructions, task_features, inference):
    _require(type(task_sources) is dict and 1 <= len(task_sources) <= MAX_TASKS,
        "bounded explicit task source mapping required")
    _require(all(type(task_id) is str and _TASK.fullmatch(task_id) is not None
        for task_id in task_sources), "bounded canonical task identifier required")
    tasks = set(task_sources)
    _require(all(type(value) is dict and set(value) == tasks for value in
        (instructions, task_features, inference)), "source/instruction/feature/inference task sets differ")
    count, total, result = 0, 0, {}
    for task_id, sources in sorted(task_sources.items()):
        _require(type(task_id) is str and _TASK.fullmatch(task_id) is not None,
            "bounded canonical task identifier required")
        _require(type(sources) is dict and bool(sources), "nonempty explicit task source map required")
        _require(all(type(name) is str for name in sources), "canonical source path keys required")
        _require(type(instructions[task_id]) is str and bool(instructions[task_id])
            and len(instructions[task_id].encode()) <= 1_048_576, "bounded complete task instruction required")
        result[task_id] = {}
        for name, text in sorted(sources.items()):
            _path(name)
            _require(type(text) is str, "captured UTF-8 source text required")
            raw = text.encode("utf-8")
            _require(bool(raw), "nonempty captured source required")
            result[task_id][name] = raw
            count += 1
            total += len(raw)
    _require(count <= MAX_SOURCES and total <= MAX_SOURCE_BYTES,
        "explicit metadata source bounds exceeded")
    return result


def _checked_vectors(rows, found):
    _require(type(found) is dict and type(found.get("ranks")) is list,
        "complete per-task inference ranks required")
    ranks = found["ranks"]
    _require(len(ranks) == len(rows), "learned inference omitted source functions")
    features = {row["row_id"]: row for row in rows}
    _require(len(features) == len(rows), "duplicate source feature identity")
    observed = set()
    widths = set()
    for candidate in ranks:
        _require(type(candidate) is dict and candidate.get("row_id") in features,
            "learned vector has foreign source identity")
        key = candidate["row_id"]
        _require(key not in observed, "duplicate learned source vector")
        observed.add(key)
        original = features[key]
        _require(all(candidate.get(field) == original[field] for field in
            ("path", "symbol", "line")), "learned vector source binding differs")
        error, latent = candidate.get("reconstruction_error"), candidate.get("latent")
        _require(type(error) in (int, float) and math.isfinite(error) and error >= 0
            and type(latent) is list and 2 <= len(latent) <= 16
            and all(type(value) in (int, float) and math.isfinite(value) for value in latent),
            "bounded finite learned reconstruction/vector required")
        widths.add(len(latent))
        _require(all(candidate.get(field, False) is False for field in
            ("proof_authority", "formalization_authority", "completion_authority", "execution_authority")),
            "learned vector cannot claim authority")
    _require(observed == set(features), "learned vector inventory differs from source functions")
    _require(len(widths) == 1, "learned vector widths differ within a task")
    return ranks


def build_metadata_records(*, task_sources: dict, instructions: dict,
        task_features: dict, inference: dict, training_runs: list, provenance: dict) -> dict:
    """Build generic per-task records using exact admitted source bytes only.

    Feature rows must match native cold extraction; each source function retains
    a learned candidate vector. Contract rows preserve complete instructions as
    unresolved requirements. No learned rank controls extraction coverage.
    """
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as ae
    from ipfs_accelerate_py.agent_supervisor.analysis.program_ast_adapters import build_program_evidence_index
    from ipfs_accelerate_py.agent_supervisor.runtime.semantic_context_runtime import _scan_scoped_sources
    from ipfs_accelerate_py.agent_supervisor.runtime.supervisor_meta_index import public_replay_without_metadata

    captured = _sources(task_sources, instructions, task_features, inference)
    _require(type(training_runs) is list and 1 <= len(training_runs) <= MAX_RUNS
        and all(type(run) is dict for run in training_runs), "bounded explicit training run records required")
    _require(type(provenance) is dict and bool(provenance), "explicit experiment provenance required")
    records = {name: [] for name in ("sources", "instructions", "ast", "ast_indexes",
        "symbols", "kg", "semantic_indexes", "contracts", "features", "vectors",
        "frontiers", "training", "provenance")}
    for task_id, sources in captured.items():
        rows, unsupported = ae._features(sources, sorted(sources), MAX_FUNCTIONS_PER_TASK)
        _require(type(task_features[task_id]) is list
            and _wire(rows) == _wire(task_features[task_id]),
            "source-bound feature inventory differs from native re-extraction")
        ranks = _checked_vectors(rows, inference[task_id])
        # This native scope prevents AST mirroring from activating an unrelated
        # configured metadata owner. The explicit hydration below has its own owner.
        with public_replay_without_metadata():
            evidence = build_program_evidence_index(task_sources[task_id],
                max_source_bytes=MAX_SOURCE_BYTES, max_facts=20_000)
            scanner = _scan_scoped_sources(sources, repository_id="training-task:" + task_id,
                max_symbols=10_000)
        evidence_record = evidence.to_dict()
        for name, raw in sorted(sources.items()):
            records["sources"].append(_row("source", task_id,
                {"path": name, "source_text": raw.decode("utf-8"),
                 "source_sha256": _sha(raw), "bytes": len(raw)},
                observation_role="captured_task_input_only"))
        instruction = instructions[task_id]
        binding = {"instruction_text": instruction,
            "instruction_sha256": _sha(instruction.encode("utf-8"))}
        records["instructions"].append(_row("instruction", task_id, binding))
        records["contracts"].append(_row("unresolved_contract", task_id, binding,
            status="unresolved_task_requirement", source_behavior_proved=False,
            intent_ir_alignment_verified=False, residual_text_preserved=True))
        records["ast_indexes"].append(_row("ast_index", task_id, evidence_record,
            authority="structural_observation_only"))
        for result in evidence_record["results"]:
            for fact in result["facts"]:
                records["ast"].append(_row("ast_fact", task_id, fact,
                    source_path=result["path"], source_sha256=result["source_sha256"],
                    authority="structural_observation_only"))
        for symbol in scanner.symbols:
            records["symbols"].append(_row("symbol", task_id, symbol.to_dict(),
                authority="structural_observation_only"))
        for edge in scanner.edges:
            records["kg"].append(_row("kg_edge", task_id, edge.to_dict(),
                authority="structural_observation_only"))
        records["semantic_indexes"].append(_row("semantic_index", task_id, scanner.to_dict(),
            authority="structural_observation_only"))
        for feature in rows:
            records["features"].append(_row("feature", task_id, feature,
                feature_schema=ae.FEATURE_SCHEMA, authority="structural_observation_only"))
        for candidate in ranks:
            records["vectors"].append(_row("learned_vector", task_id, candidate,
                source_row_id=candidate["row_id"], authority="unverified_candidate_only",
                ranking_role="nomination_order_only", omission_authority=False,
                inference_descriptor_sha256=_sha(_wire(inference[task_id]))))
        records["frontiers"].append(_row("task_frontiers", task_id,
            {"unsupported_feature_sources": unsupported, "reconstruction_scope": "44_AST_feature_counts_only",
             "unproved": ["source_runtime_semantics", "learned_latent_to_logic_decoder",
                "intent_alignment", "full_task_satisfaction", "asymptotic_optimizer_convergence"]}))
    for ordinal, run in enumerate(training_runs):
        records["training"].append(_row("training_run", "experiment", run,
            ordinal=ordinal, measurement_role="caller_pinned_actual_training_record"))
    records["provenance"].append(_row("provenance", "experiment", provenance,
        schema=SCHEMA, source_files=len([row for row in records["sources"]])))
    # Return a detached complete object. Oversized producer rows are packaged
    # losslessly only by hydrate_and_verify_records, not silently truncated.
    return records


def hydrate_and_verify_records(*, records: dict, output: Path, source_snapshot: dict) -> dict:
    """Hydrate a new isolated DuckDB/DuckLake catalog and reopen it in a process."""
    from benchmarks.agent_supervisor.container_coding import codebase_ir_metadata as metadata
    from benchmarks.agent_supervisor.container_coding.terminal_codebase_supervisor_fixture import (
        bound_terminal_codebase_metadata_records, reconstruct_terminal_codebase_metadata_records,
    )
    bounded = bound_terminal_codebase_metadata_records(records)
    _require(_wire(reconstruct_terminal_codebase_metadata_records(bounded)) == _wire(records),
        "metadata packaging lost original source/training records")
    report = metadata.hydrate_codebase_ir_metadata(records=bounded, output=output,
        source_snapshot=source_snapshot)
    reopened = metadata.validate_codebase_ir_metadata(output=output, expected=report, fresh_process=True)
    restored = {}
    for family, descriptor in reopened["exports"].items():
        raw = (Path(output) / descriptor["relative_path"]).read_bytes()
        restored[family] = [json.loads(line)["payload"] for line in raw.splitlines()]
    recovered = reconstruct_terminal_codebase_metadata_records(restored)
    _require(_wire(recovered) == _wire(records), "fresh metadata reopen lost original producer records")
    _require(reopened["fresh_process_readback"]["verified"] is True,
        "metadata fresh process verification unavailable")
    return {"schema": SCHEMA, "status": "exact_native_metadata_replay",
        "records_sha256": _sha(_wire(records)), "family_counts": {k: len(v) for k, v in records.items()},
        "bounded_family_counts": reopened["family_counts"], "native_metadata": reopened,
        "complete_record_reconstruction": True, **AUTHORITY}


def recorded_loss_evidence(run: dict) -> dict:
    """Encode measured endpoint decimals as exact rationals; no optimizer theorem."""
    _require(type(run) is dict and type(run.get("metrics")) is dict,
        "explicit training run metrics required")
    original = _copy(run)
    pairs = []
    for name in ("before_reconstruction_loss", "after_reconstruction_loss"):
        value = original["metrics"].get(name)
        _require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
            "finite nonnegative measured reconstruction endpoints required")
        exact = Fraction(str(value))
        _require(max(len(str(exact.numerator)), len(str(exact.denominator))) <= 128,
            "bounded measured rational endpoint required")
        pairs.append({"decimal": str(value), "numerator": exact.numerator,
            "denominator": exact.denominator})
    before, after = pairs
    decreased = after["numerator"] * before["denominator"] < before["numerator"] * after["denominator"]
    return {"schema": LOSS_SCHEMA, "run_sha256": _sha(_wire(original)),
        "metrics_sha256": _sha(_wire(original["metrics"])), "before": before, "after": after,
        "recorded_endpoints_decreased": decreased,
        "claim_scope": "exact_ordering_of_supplied_measured_decimal_endpoints_only",
        "floating_point_measurement_accuracy_proved": False,
        "training_origin_authenticated_by_lean": False, **AUTHORITY}


def _loss_lean(evidence, *, negative: bool):
    _require(type(negative) is bool, "explicit loss control direction required")
    before, after = evidence["before"], evidence["after"]
    left, right = (before, after) if negative else (after, before)
    name = "false_reverse_endpoint_order" if negative else "measured_endpoint_decreased"
    return ("import Init\nset_option autoImplicit false\n"
        "-- Recorded decimals only; no training, source-equivalence or optimizer theorem.\n"
        "def exactLess (a b c d : Nat) : Prop := 0 < b ∧ 0 < d ∧ a * d < c * b\n"
        f"theorem {name} : exactLess {left['numerator']} {left['denominator']} "
        f"{right['numerator']} {right['denominator']} := by\n  unfold exactLess\n  decide\n"
        f"#print axioms {name}\n")


def _retain_loss_observation(path: Path, value: dict):
    """Retain each completed observation before a later qualification can fail."""
    with path.open("xb") as stream:
        stream.write(_wire(value))
        stream.flush()
        os.fsync(stream.fileno())
        os.fchmod(stream.fileno(), 0o444)


def _compile_lean(*, executable, filename, source, output, expected_success):
    """Run the actual native Lean binary with the pilot's one-thread setting.

    The bounded runner, CPU/wall limits and false-proposition refusal criteria
    retain the predecessor policy. Explicit -j1 prevents Lean from attempting a
    host-sized thread pool; it does not retry or reinterpret resource failures.
    """
    from benchmarks.agent_supervisor.container_coding import terminal_codebase_logic_qualification as native
    from ipfs_datasets_py.logic.backends.process import BoundedToolRunner, ToolRunRequest, ToolRunLimits

    pin = native._write(output / filename, source)
    object_file = str(PurePosixPath(filename).with_suffix(".olean"))
    command = ((str(executable), "-j", "1", "-o", object_file, filename) if expected_success
               else (str(executable), "-j", "1", filename))
    executable_pin = _sha(executable.read_bytes())
    limits = ToolRunLimits(timeout_seconds=20, cpu_seconds=20,
        max_input_bytes=262144, max_output_bytes=65536,
        max_workspace_bytes=16 * 1024 * 1024)
    run = BoundedToolRunner().run(ToolRunRequest(argv=command,
        input_files={filename: source}, output_paths=(object_file,) if expected_success else (),
        limits=limits))
    executable_unchanged = _sha(executable.read_bytes()) == executable_pin
    exact_command = tuple(run.command) == command
    bounded_result = (not any((run.timed_out, run.cancelled, run.unavailable,
        run.resource_exhausted, run.output_truncated, run.workspace_limit_exceeded))
        and executable_unchanged and exact_command)
    passed = run.ok and bounded_result
    expected_failure = (run.returncode is not None and run.returncode != 0
        and bounded_result
        and "Tactic `decide` proved that the proposition" in run.stdout and "is false" in run.stdout)
    compiled_artifacts = []
    for name, raw in run.output_files.items():
        with (output / name).open("xb") as stream:
            stream.write(raw)
        compiled_artifacts.append({"path": str(output / name), "sha256": _sha(raw), "bytes": len(raw)})
    if expected_success and not compiled_artifacts:
        passed = False
    return {"schema": "terminal-codebase-lean-check@1", "file": filename, "artifact": pin,
        "status": "passed" if passed else "rejected" if expected_failure else "inconclusive",
        "expected_success": expected_success,
        "matches_expectation": passed if expected_success else expected_failure,
        "compiled_artifacts": compiled_artifacts,
        "backend_executed": run.pid is not None, "pid": run.pid,
        "executable": str(executable), "executable_sha256": executable_pin,
        "executable_unchanged": executable_unchanged,
        "requested_command": list(command), "command": list(run.command),
        "exact_command": exact_command, "lean_threads": 1,
        "limits": {"timeout_seconds": limits.timeout_seconds, "cpu_seconds": limits.cpu_seconds,
            "max_input_bytes": limits.max_input_bytes, "max_output_bytes": limits.max_output_bytes,
            "max_workspace_bytes": limits.max_workspace_bytes},
        "returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
        "timed_out": run.timed_out, "cancelled": run.cancelled, "unavailable": run.unavailable,
        "output_truncated": run.output_truncated, "workspace_limit_exceeded": run.workspace_limit_exceeded,
        "resource_exhausted": run.resource_exhausted, "workspace_cleaned": run.workspace_cleaned,
        "termination_reason": run.termination_reason, "error": run.error,
        "elapsed_seconds": run.elapsed_seconds,
        "proof_scope": "kernel_checked_recorded_decimal_ordering_only", **AUTHORITY}


def qualify_recorded_losses(*, training_runs: list, output: Path, lean_executable: Path) -> dict:
    """Compile actual finite measurement claims and rejected reverse-order controls.

    Caller retains the actual training receipt/checkpoint/source provenance.
    Native Lean proves the supplied rational order and authenticates none of it.
    Increasing/unchanged recorded loss is preserved without a decrease theorem.
    """
    _require(type(training_runs) is list and 1 <= len(training_runs) <= MAX_RUNS,
        "bounded explicit training run list required")
    output, lean_executable = Path(output), Path(lean_executable)
    _require(output.is_absolute() and output.resolve() == output and not output.exists()
        and output.parent.is_dir(), "fresh canonical external Lean output required")
    _require(lean_executable.is_absolute() and lean_executable.is_file()
        and lean_executable.resolve() == lean_executable,
        "installed canonical native Lean executable required")
    observations = [recorded_loss_evidence(run) for run in training_runs]
    _require(len({row["run_sha256"] for row in observations}) == len(observations),
        "duplicate training run loss evidence")
    output.mkdir(mode=0o700)
    rows = []
    for ordinal, evidence in enumerate(observations):
        checks = []
        folder = output / f"run-{ordinal:03d}"
        folder.mkdir(mode=0o700)
        _retain_loss_observation(folder / "loss-evidence.json", evidence)
        if evidence["recorded_endpoints_decreased"]:
            for negative, filename in ((False, "MeasuredLoss.lean"), (True, "FalseReverseLoss.lean")):
                try:
                    checked = _compile_lean(executable=lean_executable,
                        filename=filename, source=_loss_lean(evidence, negative=negative),
                        output=folder, expected_success=not negative)
                except Exception as error:
                    # No process result can be invented when the native helper
                    # raises. Preserve the observed exception and completed prior
                    # receipts, then propagate the original failure unchanged.
                    _retain_loss_observation(folder / (Path(filename).stem + ".exception.json"),
                        {"schema": LOSS_SCHEMA, "file": filename,
                         "error_type": type(error).__name__, "error": str(error),
                         "native_check_returned": False, **AUTHORITY})
                    _retain_loss_observation(folder / "run-observation.json",
                        {"evidence": evidence, "checks": checks,
                         "status": "native_check_exception", **AUTHORITY})
                    raise
                _retain_loss_observation(folder / (Path(filename).stem + ".check.json"), checked)
                checks.append(checked)
            _retain_loss_observation(folder / "run-observation.json",
                {"evidence": evidence, "checks": checks,
                 "status": "kernel_checked_recorded_order" if all(
                    check["matches_expectation"] for check in checks) else "native_check_not_qualified",
                 **AUTHORITY})
            _require(all(check["matches_expectation"] for check in checks),
                "native Lean measured ordering or false-control check failed")
        else:
            _retain_loss_observation(folder / "run-observation.json",
                {"evidence": evidence, "checks": checks,
                 "status": "recorded_loss_not_decreased", **AUTHORITY})
        rows.append({"evidence": evidence, "checks": checks,
            "status": "kernel_checked_recorded_order" if checks else "recorded_loss_not_decreased",
            **AUTHORITY})
    report = {"schema": LOSS_SCHEMA, "rows": rows,
        "native_lean_processes": sum(len(row["checks"]) for row in rows),
        "positive_compiles": sum(bool(row["checks"]) for row in rows),
        "rejected_reverse_controls": sum(bool(row["checks"]) for row in rows),
        "claim_scope": "finite_recorded_measurement_ordering_only", **AUTHORITY}
    with (output / "qualification.json").open("xb") as stream:
        stream.write(_wire(report))
    return report


__all__ = ["ProjectionError", "AUTHORITY", "build_metadata_records",
    "hydrate_and_verify_records", "recorded_loss_evidence", "qualify_recorded_losses"]
