"""File-only closure of actual bounded real-ranker qualification evidence."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[2]
EXCLUSIONS = (ROOT / "environment/mathlib4", ROOT / "environment/cache")


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()


def pin(path):
    path = Path(path).resolve(strict=True)
    before = path.stat(); raw = path.read_bytes(); after = path.stat()
    signature = lambda value: tuple(getattr(value, "st_" + key) for key in
        ("dev", "ino", "mode", "nlink", "size", "mtime_ns", "ctime_ns"))
    assert stat.S_ISREG(before.st_mode) and signature(before) == signature(after), str(path)
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(path):
    return json.loads(Path(path).read_bytes())


def inventory():
    files, symlinks = [], []
    def visit(path):
        for item in sorted(path.iterdir()):
            if item in EXCLUSIONS:
                continue
            if item.is_symlink():
                assert item.name.endswith("current") and item.is_relative_to(ROOT / "evidence")
                assert "fixtures" in item.parts
                before = item.lstat(); target = os.readlink(item); raw = target.encode("utf-8")
                actual = item.resolve(strict=True)
                assert actual.parent == item.parent and actual.is_dir() and not actual.is_symlink()
                assert before == item.lstat() and target == os.readlink(item)
                symlinks.append({"path": str(item), "target": target, "bytes": len(raw),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "stat": [getattr(before, "st_" + key) for key in
                        ("dev", "ino", "mode", "nlink", "size", "mtime_ns", "ctime_ns")]})
            elif item.is_dir():
                visit(item)
            else:
                files.append(pin(item))
    visit(ROOT)
    return {"files": sorted(files, key=lambda row: row["path"]),
            "fixture_symlinks": sorted(symlinks, key=lambda row: row["path"])}


def verify_inherited():
    request = read(ROOT / "preparation/request.json")
    for row in request["strict_old_inputs"] + request["protected_live_sources"]:
        assert pin(row["path"]) == row
    seal = request["prior_trace_seal"]
    assert pin(seal["path"]) == seal
    prior = read(seal["path"])
    assert len(prior["files"]) == 203
    for row in prior["files"]:
        assert pin(row["path"]) == row
    return {"strict_old_inputs": len(request["strict_old_inputs"]),
            "protected_live_sources": len(request["protected_live_sources"]), "prior_sealed_files": 203}


def live_guards():
    results = {}
    for name, directory in (("root", WORKSPACE), ("child", WORKSPACE / "external/ipfs_accelerate")):
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=directory, text=True).strip()
        index = subprocess.check_output(["git", "rev-parse", "--git-path", "index"], cwd=directory, text=True).strip()
        path = Path(index)
        if not path.is_absolute(): path = directory / path
        results[name] = {"head": head, "index_sha256": pin(path)["sha256"]}
    expected = read(WORKSPACE / "maintenance/ranker-trace-private-git-preparation-20261005-01/root-publication-closed.json")["original_checkout_guards"]
    for name, value in results.items():
        assert all(value[key] == expected[name][key] for key in value)
    return results


def main():
    target = ROOT / "qualified-review-01.json"; seal_path = ROOT / "file-only-seal-01.json"
    assert not target.exists() and not seal_path.exists()
    before = inventory(); old = verify_inherited(); guards = live_guards()
    known_aliases = {
        "9c6498a790cae04ec3f5e7869f0692d66c0e5a87376fe0f131199c08acac8483": ROOT / "run_curvature_controls-v0.py",
        "e0f01a3bc3646e88a080c7ebb9c7499d8a27bd80fe399b94400cd3def6fde8e1": ROOT / "run_curvature_controls-v1.py",
        "d3646eddac798ecd740d392895d6a8a7e7c0592128aef3c5ded83d0db9cdba41": ROOT / "environment/bounded_analytic_checker-v1.py",
        "4325915d199615161ca2c70cb836b3d48e299c0713ec03771a638df6f730ca6d": ROOT / "environment/test_bounded_analytic_checker-v1.py",
        "c3fbf74b6bd9c7e8db84f153a098c9d3c52bb2a81df35712cea7b5f38c2e5d29": ROOT / "environment/test_bounded_lean_chunks-v1.py",
        "0cc6a6460d841568f100e68c136346aa4dd1f7b8b0936a1dc4eeedede11e7c22": ROOT / "environment/bounded_analytic_checker-v5.py",
    }
    phases, aliases, native, test_count = [], [], [], 0
    for path in sorted((ROOT / "preparation").glob("*-invocation.json")):
        iv = read(path); mode = iv["mode"]
        owned_path = ROOT / "evidence" / mode / "closed.json"
        outer_path = ROOT / "evidence" / (mode + "-closed.json")
        owned, outer = read(owned_path), read(outer_path)
        assert owned["invocation"] == outer["invocation"] == pin(path)
        assert owned["cleanup_errors"] == outer["cleanup_errors"] == []
        assert owned["root_release_returned"] is True
        assert owned["final_resource_state"]["active_lease_count"] == 0
        assert owned["final_resource_state"]["waiting_request_count"] == 0
        assert owned["blocked_imports"] == []
        assert all(row["matches"] is True and row["before"] == row["after"] for row in owned["selected_owned_imports"])
        assert all(owned[key] == 0 for key in ("fit_calls", "autoencoder_fit_calls", "gradient_evaluations", "optimizer_updates"))
        for descriptor in iv["inputs"]:
            current = pin(descriptor["path"])
            if current != descriptor:
                alias = pin(known_aliases[descriptor["sha256"]])
                assert alias["bytes"] == descriptor["bytes"] and alias["sha256"] == descriptor["sha256"]
                aliases.append({"mode": mode, "historical_admitted_descriptor": descriptor,
                    "retained_exact_byte_alias": alias, "current_original_path": current,
                    "original_path_still_matches_claimed": False, "historical_load_origin_authenticated": False})
        if owned["status"] == "passed":
            assert outer["returncode"] == 0 and owned["primary_error"] is None and outer["primary_error"] is None
            assert owned["old348_protected4_prior203_unchanged"] is True
        else:
            assert owned["status"] == "failed" and outer["returncode"] != 0 and owned["primary_error"]
        if "selected_test_count" in owned:
            assert owned["pytest_returncode"] == 0
            calls = [row for row in read(ROOT / "evidence" / mode / "phases.json") if row["phase"] == "call"]
            assert len(calls) == owned["selected_test_count"] and all(row["outcome"] == "passed" for row in calls)
            test_count += len(calls)
        for descriptor in owned["native_proof_checks"]:
            assert pin(descriptor["path"]) == descriptor
            check = read(descriptor["path"])
            assert check["native_invocations"] == 1
            native.append({"mode": mode, "check": descriptor, "status": check["status"],
                "matches_expectation": check["matches_expectation"], "native_calls": check["native_invocations"]})
        phases.append({"mode": mode, "status": owned["status"], "owned": pin(owned_path),
            "outer": pin(outer_path), "test_calls": owned.get("selected_test_count", 0),
            "native_preparation_calls": owned["native_preparation_calls"]})
    assert len(phases) == 38 and len(native) == 19
    assert sum(row["status"] == "passed" for row in native) == 10
    assert sum(row["status"] == "rejected" for row in native) == 1
    assert sum(row["status"] == "inconclusive" for row in native) == 8
    assert test_count == 249 and sum(row["native_preparation_calls"] for row in phases) == 1
    mapping = ROOT / "math/qualified-proof-mapping-01.json"
    assert pin(mapping)["sha256"] == "770239755a018a1d75f8ee1bce81c959d1f0724c17d1036aac717531d68b3964"
    joins_path = ROOT / "evidence/cache-joins-02/cache-join-result.json"; joins = read(joins_path)
    assert joins["pure_lookup_metrics"] == {"same_query_hits": 10, "changed_dimension_queries": 230, "changed_dimension_misses": 230}
    readback_path = ROOT / "evidence/metadata-01/metadata-readback.json"; readback = read(readback_path)
    assert readback["status"] == "passed" and readback["fresh_process_readback"]["verified"] is True
    assert readback["all_payload_rows_read_back_exactly"] is True and readback["prior4348_payload_rows_preserved_exactly"] is True
    assert readback["metadata_family_count"] == 32 and readback["metadata_row_count"] == 4378
    assert inventory() == before and verify_inherited() == old and live_guards() == guards
    review = {"schema": "ranker-real-curvature-closed-qualification-review@1", "status": "passed",
        "scope": "exact original four-pair eighty-coordinate stated real objective and advisory stored proofs",
        "file_only_review": True, "atomic_whole_source_snapshot_claimed": False,
        "dependency_bodies_rehashed_in_this_file_only_review": False,
        "phases": phases, "retained_historical_byte_aliases": aliases, "native_attempts": native,
        "inherited_inputs_unchanged_before_after": old, "original_checkout_guards": guards,
        "native_lean_calls": 19, "qualified_positive_native_lean_checks": 10,
        "genuine_negative_native_lean_checks": 1, "inconclusive_native_lean_checks_retained": 8,
        "selected_pure_test_executions": 249, "cache_v2_tests": {"new": 17, "prior_repeated": 59, "actual_phase": 76},
        "new_public_fits": 0, "new_autoencoder_fits": 0, "new_ranker_training_trace_replays": 0,
        "new_optimizer_updates": 0, "new_gradient_evaluations": 0, "one_original_feature_preparation": 1,
        "all_failed_attempts_retained": True, "all_failed_owned_phase_count": sum(row["status"] == "failed" for row in phases),
        "native_solver_and_metadata_limits_unchanged": True, "all_owned_leases_drained": True,
        "qualified_mathematical_mapping": pin(mapping), "numeric_binding": pin(ROOT / "evidence/numeric-01/numeric-binding.json"),
        "cache_joins": pin(joins_path), "cache_same_query_hits": 10, "cache_changed_dimension_misses": 230,
        "native_metadata_readback": pin(readback_path), "metadata_family_count": 32, "metadata_payloads": 4378,
        "prior4348_payloads_preserved_exactly": True, "contracts_payloads_unchanged": True,
        "original_real_profile_curvature_qualified": True, "original_real_one_step_descent_qualified": True,
        "multivariate_Frechet_Hessian_identity_proved": False, "python_ranker_source_equivalence_proved": False,
        "binary64_error_bound_proved": False, "historical_execution_origin_proved": False,
        "global_optimizer_convergence_proved": False, "global_autoencoder_convergence_proved": False,
        "proof_authority": False, "execution_authority": False, "completion_authority": False,
        "planner_activation": False, "official_benchmark_score": None,
        "full_task_satisfaction": "unknown", "all32_governing_RPI_exits": "OPEN"}
    target.write_bytes(wire(review) + b"\n")
    final = inventory(); files = final["files"]
    seal = {"schema": "ranker-real-curvature-file-only-seal@1", "review": pin(target), "files": files,
        "file_inventory_sha256": hashlib.sha256(wire(files)).hexdigest(), "regular_file_count": len(files),
        "regular_file_bytes": sum(row["bytes"] for row in files), "excluded_dependency_subtrees": list(map(str, EXCLUSIONS)),
        "fixture_symlinks": final["fixture_symlinks"],
        "fixture_symlink_inventory_sha256": hashlib.sha256(wire(final["fixture_symlinks"])).hexdigest(),
        "scope": "new owned regular files and exact no-follow pytest convenience aliases; two dependency trees excluded before descent; seal is a fixed addition"}
    seal_path.write_bytes(wire(seal) + b"\n")
    print(json.dumps({"review": pin(target), "seal": pin(seal_path), "files": len(files), "bytes": seal["regular_file_bytes"]}))


if __name__ == "__main__": main()
