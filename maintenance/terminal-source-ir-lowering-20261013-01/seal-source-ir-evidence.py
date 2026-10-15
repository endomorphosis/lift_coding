"""Seal explicit source/public qualification artifacts; never traverse databases."""
import hashlib
import json
import os
from pathlib import Path
import stat

S = Path(__file__).resolve().parent
MAX_BYTES = 16 * 1024**2


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False).encode()


def pin(path):
    path = Path(path)
    assert path.is_absolute() and path.resolve(strict=True) == path
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    def identity(value):
        return tuple(getattr(value, name) for name in ("st_dev", "st_ino", "st_mode", "st_uid",
            "st_gid", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"))
    try:
        before = os.fstat(descriptor)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink == 1 and before.st_size <= MAX_BYTES
        with os.fdopen(os.dup(descriptor), "rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        assert len(raw) <= MAX_BYTES and identity(before) == identity(os.fstat(descriptor)) == identity(path.lstat())
    finally:
        os.close(descriptor)
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    assert not (S / "evidence-manifest.json").exists()
    baseline = json.loads((S / "baseline-manifest.json").read_bytes())
    assert pin(Path(baseline["sealed_predecessor"]["path"])) == baseline["sealed_predecessor"]
    predecessor = json.loads(Path(baseline["sealed_predecessor"]["path"]).read_bytes())
    for row in [*baseline["dependencies"], *predecessor["files"]]:
        assert pin(Path(row["path"])) == {key: row[key] for key in ("path", "bytes", "sha256")}
    runtime = json.loads((S / "runtime-source-pins.json").read_bytes())["files"]
    assert [pin(Path(row["path"])) for row in runtime] == runtime
    result = json.loads((S / "result.json").read_bytes())
    actual = json.loads((S / "actual-qualification.json").read_bytes())
    tests = json.loads((S / "tests-run.json").read_bytes())
    review = json.loads((S / "independent-review.json").read_bytes())
    assert result["qualified"] and actual["qualified"] and tests["unique_tests"] == 104
    assert tests["returncode"] == 0 and tests["pins_unchanged_at_endpoints"]
    assert not any(tests[name] for name in ("failure", "error", "skipped"))
    assert review["qualified"] is True

    names = ["baseline-manifest.json", "runtime-source-pins.json", "source-manifest.json",
        "experiment-plan.json", "next-work.json", "result.json", "excluded-history.json",
        "independent-review.json", "patch-validation.json", "predecessor-preservation.json", "changes.patch",
        "tests.xml", "tests-run.json", "tests.stdout", "tests.stderr",
        "projection-agent-validation.json", "projection-tests-01.xml", "projection-tests-02.xml",
        "projection-tests-02-run.json", "projection-tests-02.stdout", "projection-tests-02.stderr",
        "agent-lowering-01.xml", "agent-lowering-02-pins.json", "agent-lowering-03.xml", "agent-lowering-03-pins.json",
        "qualify-public-source-ir.py", "qualify-public-source-ir-02.py", "qualify-public-source-ir-03.py",
        "cold-validate-source-ir.py", "seal-source-ir-evidence.py", "actual-qualification.json",
        "actual-run.json", "actual.stdout", "actual.stderr", "actual-02-run.json", "actual-02.stdout", "actual-02.stderr",
        "actual-03-run.json", "actual-03.stdout", "actual-03.stderr"]
    paths = [S / name for name in names]
    checkout = S.parent / "terminal-token-reduction-20261007-01/checkout"
    for row in runtime:
        path = Path(row["path"])
        paths.extend([path, S / "final" / path.relative_to(checkout)])
    native_names = ["captured_source.py", "compiled.json", "translation.json", "frontend.json", "manifest.json",
        "source_ast.json", "source_syntax.json", "native_target.json", "process_policy.json", "tool_policy.json",
        "IntegerLowering.lean", "IntegerLowering.olean", "lean_process.json", "lean_certificate.json", "result.json"]
    for number in (2, 3):
        output = S / ("actual-public-lowering-0" + str(number))
        paths.extend(output / name for name in ("head.json", "tool-policy.json", "wrong-goal-summary.json",
            "cold-validation.json", "cold-validation.stderr"))
        qualified = output / "qualified"
        paths.extend(qualified / name for name in ("result.json", "projection.json", "native-proof.json",
            "cache-dimensions.json", "cache-report.json", "checked-object.olean"))
        for directory in (qualified / "native-lowering", output / "wrong-goal"):
            paths.extend(directory / name for name in native_names)
        paths.extend(output / "controls" / name for name in ("TargetMismatch.lean", "Inspect.lean",
            "target-mismatch.json", "axiom-inventory.json"))
    selected = S / "actual-public-lowering-03/qualified"
    paths.extend(selected / "candidate-cache" / name for name in ("manifest.json", "artifact.bin"))
    # Only manifest-declared bounded public JSON exports are read. Native
    # databases, CAS and DuckLake/Parquet bodies are intentionally not traversed.
    for output, report in ((selected / "metadata", actual["metadata"]),
            (selected / "candidate-cache/metadata", json.loads((selected / "cache-report.json").read_bytes())["metadata"])):
        paths.append(output / "manifest.json")
        for family, declared in report["exports"].items():
            relative = declared["relative_path"]
            assert relative == "exports/" + family + ".jsonl"
            path = output / relative
            value = pin(path)
            assert value["bytes"] == declared["bytes"] and "sha256:" + value["sha256"] == declared["sha256"]
            paths.append(path)
    unique = sorted(set(paths), key=str)
    rows = [pin(path) for path in unique]
    assert [pin(path) for path in unique] == rows
    assert [pin(Path(row["path"])) for row in runtime] == runtime
    assert pin(Path(baseline["sealed_predecessor"]["path"])) == baseline["sealed_predecessor"]
    seal = {"schema": "terminal-source-ir-evidence-seal@1", "stage": str(S), "files": rows,
        "explicit_named_file_count": len(rows), "recursive_traversal": False,
        "database_and_cas_bodies_hashed": False, "native_storage_verified_by_actual_readback": True,
        "private_database_or_auth_data_included": False, "raw_worker_or_model_transcripts_included": False,
        "selected_qualification": "actual-public-lowering-03", "prior_attempts_retained_and_excluded": True,
        "selected_native_lean_processes": 6, "stage_native_lean_processes": 12,
        "unique_tests": 104, "training_steps": 0, "provider_calls": 0,
        "source_body_executed": False, "proof_authority": False,
        "source_semantics_verified": False, "training_convergence_proved": False}
    raw = wire(seal)
    with (S / "evidence-manifest.json").open("xb") as stream:
        stream.write(raw)
    (S / "evidence-manifest.json").chmod(0o600)
    assert [pin(path) for path in unique] == rows
    print(json.dumps({"sealed_files": len(rows), "seal_sha256": hashlib.sha256(raw).hexdigest(),
        "qualified": True, "unique_tests": 104}))


if __name__ == "__main__":
    main()
