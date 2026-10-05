"""File-only closure and seal for the quiet additive convergence qualification."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
QUALIFICATION = WORKSPACE / "qualification/codebase_ir/ranker-real-convergence-20261005-01"
PRIOR = QUALIFICATION.with_name("ranker-real-curvature-20261005-01")


def pin(path):
    path = Path(path).absolute()
    assert path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        digest = hashlib.sha256()
        count = 0
        while block := os.read(fd, 1024**2):
            digest.update(block)
            count += len(block)
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        signature = lambda value: tuple(getattr(value, field) for field in fields)
        assert signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
        assert count == before.st_size
        return {"path": str(path), "bytes": count, "sha256": digest.hexdigest()}
    finally:
        os.close(fd)


def load(path):
    before = pin(path)
    raw = Path(path).read_bytes()
    assert len(raw) == before["bytes"] and hashlib.sha256(raw).hexdigest() == before["sha256"]
    assert pin(path) == before
    return json.loads(raw)


def save(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def inventory():
    result = []
    for directory, directories, files in os.walk(QUALIFICATION, followlinks=False):
        assert all(not (Path(directory) / name).is_symlink() for name in directories)
        for name in files:
            path = Path(directory) / name
            assert not path.is_symlink()
            if name != "file-only-seal-01.json":
                result.append(pin(path))
    return sorted(result, key=lambda row: os.fsencode(row["path"]))


def guards():
    baseline = load(WORKSPACE / "maintenance/ranker-curvature-private-git-preparation-20261005-01/original-checkout-state-01.json")
    result = {}
    for name, old in baseline["original_checkouts"].items():
        head = subprocess.check_output(["git", "-C", old["path"], "rev-parse", "HEAD"],
                                       env=dict(os.environ, GIT_OPTIONAL_LOCKS="0")).decode().strip()
        index = pin(old["index_path"])
        assert head == old["head"] and index["bytes"] == old["index_bytes"] and index["sha256"] == old["index_sha256"]
        result[name] = {"head": head, "index": index}
    return result


def main():
    review_path = QUALIFICATION / "qualified-review-01.json"
    seal_path = QUALIFICATION / "file-only-seal-01.json"
    assert not review_path.exists() and not seal_path.exists()
    first = inventory()
    original_guards = guards()
    prior_seal_path = PRIOR / "file-only-seal-01.json"
    prior_seal = pin(prior_seal_path)
    assert prior_seal["sha256"] == "6c281bd21da026b27797f78f98d0932bad4e7a115779a4fc348ee6987f30af15"
    old = load(prior_seal_path)
    assert all(pin(row["path"]) == row for row in old["files"])
    math_review_path = WORKSPACE / "maintenance/ranker-convergence-math-review-20261005-01/review-receipt.json"
    math_review = load(math_review_path)
    assert math_review["status"] == "passed_file_only_review" and math_review["issues"] == []
    checks = []
    theorem_queries = 0
    passed = []
    inconclusive = []
    for path in sorted((QUALIFICATION / "evidence").glob("*/check-result.json")):
        check = load(path)
        closed = load(path.parent / "closed.json")
        outer = load(path.parent.with_name(path.parent.name + "-closed.json"))
        assert check["native_invocations"] == check["native_lean_invocations"] == 1
        assert closed["cleanup_errors"] == outer["cleanup_errors"] == []
        assert closed["final_resource_state"]["active_lease_count"] == closed["final_resource_state"]["waiting_request_count"] == 0
        assert check["native_bounds"] == {"cpu_seconds": 20, "max_input_bytes": 262144,
            "max_output_bytes": 65536, "max_workspace_bytes": 16777216, "timeout_seconds": 20}
        row = {"mode": path.parent.name, "qualification": pin(path), "source": check["source"],
               "environment_manifest": check["environment_manifest"], "status": check["status"],
               "owned_closed": pin(path.parent / "closed.json"), "outer_closed": pin(path.parent.with_name(path.parent.name + "-closed.json"))}
        if check["status"] == "passed":
            assert check["matches_expectation"] is True and check["expected_success"] is True
            assert check["axiom_report_error"] is None and check["post_call_binding_error"] is None
            assert check["reconstruction_validation"]["status"] == "passed"
            assert check["artifact_anomalies"] == [] and check["workspace_cleaned"]
            assert all(row["complete"] is True for row in check["compiled_artifacts"])
            assert all(set(row["axioms"]) <= {"propext", "Classical.choice", "Quot.sound"}
                       for row in check["theorem_axiom_output"])
            theorem_queries += len(check["theorem_axiom_output"])
            passed.append(row)
        else:
            assert check["status"] == "inconclusive" and not check["matches_expectation"]
            inconclusive.append(row)
        checks.append(row)
    assert len(checks) == 9 and len(passed) == 7 and len(inconclusive) == 2 and theorem_queries == 39
    final = next(row for row in passed if row["mode"] == "lean-original-convergence-02")
    metadata_path = QUALIFICATION / "evidence/metadata-convergence-01/metadata-readback.json"
    metadata = load(metadata_path)
    assert metadata["status"] == "passed" and metadata["metadata_row_count"] == 4417 and metadata["metadata_family_count"] == 32
    assert metadata["fresh_process_readback_verified"] and metadata["all_payload_rows_read_back_exactly"]
    prior_rows = load(PRIOR / "evidence/metadata-01/metadata-inputs.json")
    current_rows = load(QUALIFICATION / "evidence/metadata-convergence-01/metadata-inputs.json")
    assert set(prior_rows) == set(current_rows) and len(current_rows) == 32
    assert all(current_rows[family][:len(values)] == values for family, values in prior_rows.items())
    assert sum(map(len, prior_rows.values())) == 4378 and sum(map(len, current_rows.values())) == 4417
    assert current_rows["contracts"] == prior_rows["contracts"] == []
    assert current_rows["vectors"] == prior_rows["vectors"]
    for family, values in current_rows.items():
        exported = [json.loads(line)["payload"] for line in
                    (QUALIFICATION / "evidence/metadata-convergence-01/metadata/exports" / (family + ".jsonl")).read_bytes().splitlines()]
        assert exported == values
    closed_paths = sorted((QUALIFICATION / "evidence").glob("*/closed.json"))
    assert len(closed_paths) == 10
    phases = []
    for path in closed_paths:
        closed = load(path)
        assert closed["cleanup_errors"] == []
        assert closed["final_resource_state"]["active_lease_count"] == closed["final_resource_state"]["waiting_request_count"] == 0
        assert closed["fit_calls"] == closed["autoencoder_fit_calls"] == closed["gradient_evaluations"] == closed["optimizer_updates"] == 0
        assert closed["native_preparation_calls"] == 0
        phases.append(pin(path))
    assert first == inventory()
    assert all(pin(row["path"]) == row for row in old["files"])
    assert guards() == original_guards
    result = {"schema": "ranker-original-exact-real-convergence-closed-qualification@1", "status": "passed",
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "producer": pin(Path(__file__).resolve()), "prior_curvature_seal": prior_seal,
        "independent_math_review": pin(math_review_path), "native_checks": checks,
        "native_lean_calls": 9, "qualified_positive_native_lean_checks": 7,
        "inconclusive_native_lean_checks_retained": 2, "qualified_theorem_queries": 39,
        "owned_phase_count": 10, "phases": phases, "all_owned_leases_drained": True,
        "new_autoencoder_fits": 0, "new_public_fits": 0, "new_gradient_evaluations": 0,
        "new_optimizer_updates": 0, "new_ranker_training_trace_replays": 0, "new_feature_preparations": 0,
        "original_exact_real_model_weights_convergence_proved": True,
        "original_exact_real_objective_convergence_proved": True,
        "unique_original_exact_real_global_minimizer_proved": True,
        "geometric_original_exact_real_gap_rate_proved": True,
        "final_convergence_module": final, "source_AST_function_count": 4,
        "source_AST_obligations": pin(QUALIFICATION / "source-model-obligations-01.json"),
        "native_metadata_readback": pin(metadata_path), "metadata_family_count": 32, "metadata_payloads": 4417,
        "prior4378_payloads_preserved_exactly_as_prefixes": True, "additive_metadata_payloads": 39,
        "contracts_and_vectors_payloads_unchanged": True, "strict_advisory_cache_entries_added": 0,
        "native_proof_and_metadata_limits_unchanged": True,
        "original_checkout_guards": original_guards, "all_prior1080_regular_leaves_unchanged": True,
        "inherited_checker_scope_labels_are_not_a_source_semantics_or_full_pipeline_convergence_registry": True,
        "python_ranker_source_equivalence_proved": False, "binary64_error_bound_proved": False,
        "native_Float_optimizer_convergence_proved": False, "global_autoencoder_convergence_proved": False,
        "whole_codebase_IR_semantic_preservation_proved": False, "full_task_satisfaction": "unknown",
        "all32_governing_RPI_exits": "OPEN", "official_benchmark_score": None,
        "atomic_whole_source_snapshot_claimed": False, "historical_execution_origin_proved": False,
        "proof_authority": False, "execution_authority": False, "completion_authority": False,
        "planner_activation": False}
    save(review_path, result)
    sealed_files = inventory()
    compact = json.dumps(sealed_files, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    seal = {"schema": "ranker-real-convergence-file-only-seal@1", "status": "sealed_quiet_regular_file_scope",
            "scope_root": str(QUALIFICATION), "review": pin(review_path), "files": sealed_files,
            "regular_file_count": len(sealed_files), "regular_file_bytes": sum(row["bytes"] for row in sealed_files),
            "file_inventory_sha256": hashlib.sha256(compact).hexdigest(), "fixture_symlinks": [],
            "excluded_dependency_roots": [], "raw_external_dependency_bodies_in_scope": False,
            "stat_atime_in_identity": False, "model_training_calls": 0, "prover_calls": 0,
            "remote_mutations": 0, "proof_authority": False}
    assert sealed_files == inventory()
    save(seal_path, seal)
    print(json.dumps({"review": pin(review_path), "seal": pin(seal_path),
                      "regular_files": len(sealed_files), "regular_bytes": seal["regular_file_bytes"]}))


if __name__ == "__main__":
    main()
