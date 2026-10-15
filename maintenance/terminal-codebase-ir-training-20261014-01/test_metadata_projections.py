"""Coverage, source binding, authority and measured-order qualification controls."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import metadata_projections as projection


def _inputs():
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as ae
    source = "import math\n\ndef add_one(n):\n    return math.floor(n) + 1\n"
    rows, _ = ae._features({"public.py": source.encode()}, ["public.py"], 1024)
    ranks = [{**{key: row[key] for key in ("row_id", "path", "symbol", "line")},
        "latent": [0.2, -0.1], "reconstruction_error": 0.01} for row in rows]
    return {"task_sources": {"first": {"public.py": source}},
        "instructions": {"first": "Increment the exact integer. Preserve μ and every original clause.\n"},
        "task_features": {"first": rows}, "inference": {"first": {"ranks": ranks}},
        "training_runs": [{"run_id": "authored-control", "metrics": {
            "before_reconstruction_loss": 0.25, "after_reconstruction_loss": 0.01}}],
        "provenance": {"schema": "authored-projection-test@1", "actual_training_executed": False}}


def test_native_ast_kg_preserve_full_instructions_and_advisory_vectors():
    request = _inputs()
    records = projection.build_metadata_records(**request)
    assert records["ast"] and records["symbols"] and records["kg"]
    assert records["sources"][0]["record"]["source_text"] == request["task_sources"]["first"]["public.py"]
    contract = records["contracts"][0]
    assert contract["record"]["instruction_text"] == request["instructions"]["first"]
    assert contract["status"] == "unresolved_task_requirement"
    assert contract["source_behavior_proved"] is False
    assert records["vectors"][0]["record"] == request["inference"]["first"]["ranks"][0]
    assert all(row[field] is False for rows in records.values() for row in rows
        for field in projection.AUTHORITY)
    assert all(row["omission_authority"] is False for row in records["vectors"])
    request["inference"]["first"]["ranks"][0]["latent"][0] = 99
    assert records["vectors"][0]["record"]["latent"][0] == 0.2


def test_identical_source_rows_from_distinct_tasks_have_distinct_metadata_custody():
    request = _inputs()
    for key in ("task_sources", "instructions", "task_features", "inference"):
        request[key]["second"] = deepcopy(request[key]["first"])
    records = projection.build_metadata_records(**request)
    assert len(records["features"]) == len(records["vectors"]) == 2
    assert len({row["row_id"] for row in records["features"]}) == 2
    assert len({row["row_id"] for row in records["vectors"]}) == 2
    assert len({row["source_row_id"] for row in records["vectors"]}) == 1


@pytest.mark.parametrize("mutation", ["changed_source", "foreign_source", "omitted_vector",
    "duplicated_vector", "nonfinite_vector", "forged_authority", "changed_feature", "escaped_path"])
def test_source_drift_and_incomplete_or_forged_vector_cannot_project_current(mutation):
    request = _inputs()
    if mutation == "changed_source":
        request["task_sources"]["first"]["public.py"] = "def add_one(n):\n    return n + 2\n"
    elif mutation == "foreign_source":
        request["inference"]["first"]["ranks"][0]["path"] = "foreign.py"
    elif mutation == "omitted_vector":
        request["inference"]["first"]["ranks"].clear()
    elif mutation == "duplicated_vector":
        request["inference"]["first"]["ranks"].append(deepcopy(request["inference"]["first"]["ranks"][0]))
    elif mutation == "nonfinite_vector":
        request["inference"]["first"]["ranks"][0]["latent"][0] = float("nan")
    elif mutation == "forged_authority":
        request["inference"]["first"]["ranks"][0]["proof_authority"] = True
    elif mutation == "changed_feature":
        request["task_features"]["first"][0]["features"][0] += 0.1
    else:
        request["task_sources"]["first"]["../foreign.py"] = request["task_sources"]["first"].pop("public.py")
    with pytest.raises(projection.ProjectionError):
        projection.build_metadata_records(**request)


def test_zero_feature_loss_is_not_source_semantic_equivalence():
    from ipfs_datasets_py.logic.formalization.autoencoder.security import codebase_autoencoder as ae
    first, _ = ae._features({"same.py": b"def adjust(n):\n    return n + 1\n"}, ["same.py"], 1024)
    second, _ = ae._features({"same.py": b"def adjust(n):\n    return n + 2\n"}, ["same.py"], 1024)
    assert first[0]["features"] == second[0]["features"]
    assert first[0]["ast_sha256"] != second[0]["ast_sha256"]
    assert first[0]["row_id"] != second[0]["row_id"]


@pytest.mark.parametrize("before,after,decreased", [(0.1, 0.01, True),
    (0.01, 0.01, False), (0.01, 0.1, False), (0, 0, False)])
def test_rational_measurement_order_preserves_increases_and_unchanged_loss(before, after, decreased):
    report = projection.recorded_loss_evidence({"metrics": {
        "before_reconstruction_loss": before, "after_reconstruction_loss": after}})
    assert report["recorded_endpoints_decreased"] is decreased
    assert all(report[field] is False for field in projection.AUTHORITY)
    assert report["training_origin_authenticated_by_lean"] is False


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.1, True, "0.1"])
def test_invalid_measured_endpoints_cannot_become_formal_loss_claim(value):
    with pytest.raises(projection.ProjectionError):
        projection.recorded_loss_evidence({"metrics": {
            "before_reconstruction_loss": value, "after_reconstruction_loss": 0.01}})


def test_actual_native_lean_checks_exact_order_and_rejects_false_reverse(tmp_path):
    lean = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean")
    report = projection.qualify_recorded_losses(training_runs=[
        {"run_id": "decreased-control", "metrics": {
            "before_reconstruction_loss": 0.25, "after_reconstruction_loss": 0.01}},
        {"run_id": "increased-control", "metrics": {
            "before_reconstruction_loss": 0.01, "after_reconstruction_loss": 0.25}}],
        output=tmp_path / "lean", lean_executable=lean)
    assert report["native_lean_processes"] == 2
    assert report["positive_compiles"] == report["rejected_reverse_controls"] == 1
    assert report["rows"][0]["status"] == "kernel_checked_recorded_order"
    assert report["rows"][1]["status"] == "recorded_loss_not_decreased"
    assert report["rows"][1]["checks"] == []
    assert all(check["backend_executed"] and check["matches_expectation"]
        for check in report["rows"][0]["checks"])
    assert all(check["command"][1:3] == ["-j", "1"] and check["lean_threads"] == 1
        and check["exact_command"] and check["executable_unchanged"]
        for check in report["rows"][0]["checks"])
    assert all(report[field] is False for field in projection.AUTHORITY)


@pytest.mark.parametrize("failure", ["positive", "negative", "exception"])
def test_failed_native_loss_checks_retain_exact_diagnostics_before_rejection(tmp_path, monkeypatch, failure):
    lean = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean")
    run = {"run_id": "authored-diagnostic-control", "metrics": {
        "before_reconstruction_loss": 0.25, "after_reconstruction_loss": 0.01}}
    observed = []
    def authored_failure(**request):
        name = request["filename"]
        if failure == "exception" and name == "FalseReverseLoss.lean":
            raise OSError("authored native helper exception")
        receipt = {"file": name, "status": "authored_failure_control",
            "matches_expectation": not ((failure == "positive" and request["expected_success"])
                or (failure == "negative" and not request["expected_success"])),
            "backend_executed": False, "stderr": "retained original diagnostic μ",
            "returncode": 99, "authored_control": True}
        observed.append(receipt)
        return receipt
    monkeypatch.setattr(projection, "_compile_lean", authored_failure)
    output = tmp_path / "failed"
    with pytest.raises(OSError if failure == "exception" else projection.ProjectionError):
        projection.qualify_recorded_losses(training_runs=[run], output=output, lean_executable=lean)
    folder = output / "run-000"
    assert json.loads((folder / "loss-evidence.json").read_bytes()) == projection.recorded_loss_evidence(run)
    retained = json.loads((folder / "run-observation.json").read_bytes())
    assert retained["checks"] == observed
    assert retained["status"] == ("native_check_exception" if failure == "exception" else "native_check_not_qualified")
    for receipt in observed:
        path = folder / (Path(receipt["file"]).stem + ".check.json")
        assert json.loads(path.read_bytes()) == receipt
        assert path.stat().st_mode & 0o222 == 0
    if failure == "exception":
        exception = json.loads((folder / "FalseReverseLoss.exception.json").read_bytes())
        assert exception["error_type"] == "OSError"
        assert exception["native_check_returned"] is False
    assert not (output / "qualification.json").exists()
    assert all(retained[field] is False for field in projection.AUTHORITY)


@pytest.mark.parametrize("fault", ["timed_out", "cancelled", "unavailable", "resource_exhausted",
    "output_truncated", "workspace_limit_exceeded", "no_false_proposition", "wrong_command"])
def test_false_control_diagnostic_text_cannot_override_native_process_refusal(tmp_path, monkeypatch, fault):
    from ipfs_datasets_py.logic.backends.process import BoundedToolRunner
    lean = Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1/bin/lean")
    observed = []
    def authored_result(_self, request):
        observed.append(request)
        data = dict(command=request.argv, returncode=1, ok=False, pid=123,
            stdout="Tactic `decide` proved that the proposition is false",
            stderr="authored process refusal control", elapsed_seconds=0.1, output_files={},
            timed_out=False, cancelled=False, unavailable=False, resource_exhausted=False,
            output_truncated=False, workspace_limit_exceeded=False, workspace_cleaned=True,
            termination_reason="authored_control", error="")
        if fault == "no_false_proposition":
            data["stdout"] = "unknown unrelated compiler error"
        elif fault == "wrong_command":
            data["command"] = (str(lean), "FalseReverseLoss.lean")
        else:
            data[fault] = True
        return SimpleNamespace(**data)
    monkeypatch.setattr(BoundedToolRunner, "run", authored_result)
    result = projection._compile_lean(executable=lean, filename="FalseReverseLoss.lean",
        source="authored process-result qualification control\n", output=tmp_path, expected_success=False)
    request = observed[0]
    assert request.argv == (str(lean), "-j", "1", "FalseReverseLoss.lean")
    assert request.limits.timeout_seconds == request.limits.cpu_seconds == 20
    assert request.limits.max_workspace_bytes == 16 * 1024 * 1024
    assert request.limits.max_input_bytes == 262144 and request.limits.max_output_bytes == 65536
    assert result["matches_expectation"] is False and result["status"] == "inconclusive"
    assert result["stderr"] == "authored process refusal control"
    assert all(result[field] is False for field in projection.AUTHORITY)
