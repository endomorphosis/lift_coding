"""Seal explicit public evidence only; never run source, storage, or checker jobs."""
from pathlib import Path
import ast
import hashlib
import json
import xml.etree.ElementTree as ET

R = Path(__file__).resolve().parent


def wire(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False).encode() + b"\n"


def pin(path):
    path = Path(path)
    assert path.is_file() and not path.is_symlink() and path.stat().st_size <= 16 * 1024**2, str(path)
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def read(name):
    return json.loads((R / name).read_bytes())


def main():
    assert not (R / "evidence-manifest.json").exists(), "already sealed"
    selected = ["baseline-manifest.json", "experiment-plan.json", "runtime-source-pins.json",
        "final-source-pins.json", "source-manifest.json", "changes.patch", "predecessor-preservation.json",
        "run-final.py", "final-tests-01.xml", "final-tests-01-run.json", "final-tests-01.stdout", "final-tests-01.stderr",
        "qualify-public-revision-cache.py", "qualify-public-revision-cache-01.py", "qualify-public-revision-cache-02.py",
        "actual-public-revision-01-history.json", "actual-public-revision-02-history.json",
        "actual-02-helper-pin.json", "actual-03-helper-pin.json", "actual-02-run.json", "actual-03-run.json",
        "actual-public-revision-01.stderr", "actual-public-revision-02.stderr", "actual-public-revision-03.stdout", "actual-public-revision-03.stderr",
        "metadata-agent-validation.json", "metadata-tests-01.xml", "metadata-tests-02.xml", "metadata-tests-02-run.json",
        "agent-proof-cache-01.xml", "result-summary.json", "next-work.json", "boundary-independent-review.json", "seal-evidence.py"]
    for relative in ["qualification.json", "checker-environment.json", "lean-checks.json", "dimensions.json",
            "cache-report.json", "advisory-packet.json", "cache/manifest.json", "cache/metadata/manifest.json",
            "cache/artifact.bin", "lean/RevisionCacheModel.olean",
            "lean/RevisionCacheModel.lean", "lean/IncorrectModel.lean", "repository/callee.py", "repository/caller.py"]:
        selected.append("actual-public-revision-03/" + relative)
    files = [pin(R / relative) for relative in selected]
    sources = read("final-source-pins.json")["files"]
    package = read("source-manifest.json")
    assert len(sources) == len(package["files"]) == 4
    for expected, row in zip(sources, package["files"], strict=True):
        assert pin(expected["path"]) == expected
        assert pin(row["final_capture"])["sha256"] == expected["sha256"]
        assert row["baseline"] == "absent" and row["ast_parsed"] is True
        ast.parse(Path(expected["path"]).read_bytes())
        files.append(pin(row["final_capture"]))
    assert package["scratch_apply_check"] is True and package["scratch_applied_bytes_match"] is True
    assert package["original_index_or_remotes_mutated"] is False
    assert pin(R / "changes.patch") == package["patch"]
    baseline = read("baseline-manifest.json")
    assert all(row["exists"] is False for row in baseline["new_sources"])
    predecessor = read("predecessor-preservation.json")
    assert predecessor["all_checks_passed"] is True and predecessor["count"] == 81
    for row in predecessor["checks"]:
        assert row["verified"] is True
        assert pin(row["path"]) == {key: row[key] for key in ("path", "bytes", "sha256")}
    assert pin(baseline["sealed_predecessor"]["path"]) == baseline["sealed_predecessor"]
    for row in baseline["dependencies"]:
        assert pin(row["path"]) == row
    xml = ET.parse(R / "final-tests-01.xml").getroot()
    cases = xml.findall(".//testcase")
    assert len(cases) == len({(case.attrib["classname"], case.attrib["name"]) for case in cases}) == 84
    assert not any(xml.findall(".//" + name) for name in ("failure", "error", "skipped"))
    test_run = read("final-tests-01-run.json")
    assert test_run["returncode"] == 0 and test_run["before_source_pins"] == test_run["after_source_pins"] == sources
    actual = read("actual-public-revision-03/qualification.json")
    assert actual["qualified"] is True and actual["warm_hit"]["status"] == "hit"
    assert actual["fresh_process_cache_lookup"]["status"] == "hit"
    assert actual["cache_report"]["metadata"]["fresh_process_readback"]["verified"] is True
    assert actual["cache_report"]["metadata"]["row_count"] == 36 and actual["unsupported_count"] == 1
    assert sum(actual["family_counts"].values()) == 36 and len(actual["family_counts"]) == 12
    assert len(actual["independent_dimension_misses"]) == 6
    assert all(row["status"] == "miss" for row in actual["independent_dimension_misses"].values())
    assert len(actual["native_invalidations"]) == 6
    assert all(row["cache_stale"] and row["roundtrip_identical"] for row in actual["native_invalidations"].values())
    assert actual["callee_only_source_miss"] == actual["dependency_edge_miss"] == "source_changed"
    assert actual["lean_positive"] == "passed" and actual["lean_negative"] == "rejected"
    assert "[propext]" in actual["lean_axiom_inventory"]
    for row in actual["lean_source_and_object_pins"]:
        assert pin(row["path"]) == row
    assert pin(R / "actual-public-revision-03/cache/artifact.bin")["sha256"] == actual["lean_source_and_object_pins"][1]["sha256"]
    for key in ("source_equivalence_proved", "full_task_satisfaction", "model_convergence_proved",
            "token_savings_measured", "toolrunner_network_isolation_enforced", "proof_authority",
            "execution_authority", "completion_authority", "source_semantics_verified", "production_activated"):
        assert actual[key] is False
    assert actual["training_steps"] == actual["provider_calls"] == 0
    packet = (R / "actual-public-revision-03/advisory-packet.json").read_bytes()
    measured = actual["advisory_packet_local_count"]
    assert len(packet) == measured["bytes"] == 4573 and hashlib.sha256(packet).hexdigest() == measured["sha256"]
    assert measured["tokens"] == 1566
    assert read("actual-03-run.json")["returncode"] == 0
    assert pin(R / "qualify-public-revision-cache.py") == read("actual-03-helper-pin.json")
    result = read("result-summary.json")
    assert result["qualified"] is True and result["distinct_final_tests_passed"] == 84
    assert result["preserved_predecessor_checks"] == 81
    assert result["qualification"] == pin(R / "actual-public-revision-03/qualification.json")
    assert result["source_package"] == pin(R / "source-manifest.json")
    assert result["predecessor_preservation"] == pin(R / "predecessor-preservation.json")
    for key in ("full_task_satisfaction", "source_equivalence_proved", "model_convergence_proved",
            "new_token_savings_measured", "provider_token_usage_measured", "network_isolation_enforced",
            "loaded_module_code_attested", "transitive_producer_closure_attested"):
        assert result[key] is False
    review = read("boundary-independent-review.json")
    assert review["review_passed"] is True and review["blockers"] == []
    assert review["all_checks_passed"] is True and review["check_count"] == len(review["checks"]) == 270
    for row in review["critical_artifact_pins"]:
        assert pin(row["path"]) == row
    # Recheck every explicitly named file after all validation, before sealing.
    assert all(pin(row["path"]) == row for row in files)
    manifest = {"schema": "terminal-revision-cache-evidence-seal@1", "all_named_guards_passed": True,
        "file_count": len(files), "files": files, "final_source_pins": sources,
        "final_distinct_passed_cases": 84, "predecessor_checks_rechecked": 81,
        "selected_actual": "actual-public-revision-03", "native_metadata_rows": 36,
        "checked_model_scope": "generated_mathematical_integer_model_only",
        "source_equivalence_proved": False, "full_task_satisfaction": False,
        "model_convergence_proved": False, "new_token_savings_measured": False,
        "native_supervisor_admission_integrated": False, "network_isolation_enforced": False,
        "private_database_archive_raw_worker_log_bodies_read": False,
        "runtime_or_test_or_checker_jobs_run_by_sealer": False}
    with (R / "evidence-manifest.json").open("xb") as stream:
        stream.write(wire(manifest))
    print(json.dumps({"sealed": True, "file_count": len(files), "sha256": pin(R / "evidence-manifest.json")["sha256"]}))


if __name__ == "__main__":
    main()
