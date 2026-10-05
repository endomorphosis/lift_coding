"""Freeze one additive source and qualified local modules against the analytic closure.

This producer only reads files and copies new inputs. It never modifies prior
qualification sources, permissions, artifacts, or the external Mathlib closure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.with_name("ranker-real-convergence-20261005-01")
CURVATURE = ROOT.with_name("ranker-real-curvature-20261005-01")
SOURCE_SLICES = ROOT.with_name("ranker-source-semantics-20261005-01")
QUALIFIED_IMPORTS = {
    "RealStableFactor": (PRIOR / "evidence/lean-stable-factor-01/check-result.json", "25adf30103c3d7455df5c7fff9eedf6b9e4ceb1fbd5263e919247ed18588e0f5"),
    "TypedNumericSlice": (SOURCE_SLICES / "evidence/lean-typed-scalar-02/check-result.json", "1e11d2917e3087dc2e231bdf6b329416518eb74542d6e83074d000ee7f8a0e23"),
}


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def write(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def main():
    if not __debug__:
        raise RuntimeError("optimized Python would disable profile freeze gates")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--expected-source-sha256", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--theorem", action="append", default=[])
    parser.add_argument("--negative", action="store_true")
    parser.add_argument("--prior", action="append", default=[])
    parser.add_argument("--objective-check-sha256")
    args = parser.parse_args()
    assert args.negative or args.theorem, "positive theorem names required"
    assert re.fullmatch(r"lean-[a-z0-9-]+", args.mode), "mode must be a bounded local basename"
    assert re.fullmatch(r"[0-9a-f]{64}", args.expected_source_sha256)
    source = args.source.resolve(strict=True)
    assert source.is_relative_to(ROOT) and source.suffix == ".lean" and not args.source.is_symlink()
    assert pin(source)["sha256"] == args.expected_source_sha256, "externally reviewed source pin required"
    prior_entries = [entry.split("=", 1) for entry in args.prior]
    assert all(len(entry) == 2 for entry in prior_entries)
    names = [entry[0] for entry in prior_entries]
    assert len(names) == len(set(names)) and set(names) in (
        {"RealStableFactor", "TypedNumericSlice"},
        {"RealStableFactor", "TypedNumericSlice", "ObjectiveScalarIR"},
    ), "exact objective scalar qualified imports required"
    assert ("ObjectiveScalarIR" in names) == (args.objective_check_sha256 is not None)
    if args.objective_check_sha256 is not None:
        assert re.fullmatch(r"[0-9a-f]{64}", args.objective_check_sha256)
    base = PRIOR / "preparation/lean-original-convergence-02-producer/environment-manifest.json"
    base_pin = pin(base)
    assert base_pin["sha256"] == "c9cf0ff47f85d562eb3c2f3dcd604f2f850f99b8f8e8e42a9bd063f668ed3084"
    base_raw = base.read_bytes()
    assert len(base_raw) == base_pin["bytes"] and hashlib.sha256(base_raw).hexdigest() == base_pin["sha256"]
    body = json.loads(base_raw)
    checker = CURVATURE / "preparation/lean-original-descent-01-producer/bounded_analytic_checker.py"
    retention = CURVATURE / "preparation/lean-original-descent-01-producer/RetainLeanProof.py"
    assert pin(checker)["sha256"] == "04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4"
    assert pin(retention)["sha256"] == "ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66"
    destination = ROOT / "preparation" / (args.mode + "-producer")
    destination.mkdir()
    files = {row["path"]: row for row in body["files"]}
    sources = []
    for original in (source, checker, retention, Path(__file__).resolve()):
        before = pin(original)
        raw = original.read_bytes()
        captured = destination / original.name
        with captured.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        captured.chmod(0o444)
        held = pin(captured)
        assert pin(original) == before and (held["bytes"], held["sha256"]) == (before["bytes"], before["sha256"])
        sources.append({"original": before, "captured": held})
        files[held["path"]] = held
    executable = pin(Path(sys.executable).resolve(strict=True))
    assert executable["sha256"] == "1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f"
    files[executable["path"]] = executable
    for name, value in prior_entries:
        check_path = Path(value).resolve(strict=True)
        check_pin = pin(check_path)
        if name in QUALIFIED_IMPORTS:
            expected_path, expected_sha = QUALIFIED_IMPORTS[name]
            assert check_path == expected_path and check_pin["sha256"] == expected_sha
        else:
            assert name == "ObjectiveScalarIR" and check_path.is_relative_to(ROOT / "evidence")
            assert check_path.name == "check-result.json" and check_pin["sha256"] == args.objective_check_sha256
        check_raw = check_path.read_bytes()
        assert len(check_raw) == check_pin["bytes"] and hashlib.sha256(check_raw).hexdigest() == check_pin["sha256"]
        check = json.loads(check_raw)
        assert check["status"] == "passed" and check["matches_expectation"] is True
        assert check["expected_success"] is True
        assert check["axiom_report_error"] is None and check["post_call_binding_error"] is None
        assert Path(check["source"]["path"]).stem == name
        assert not any(row["module"] == name for row in body["source_import_modules"])
        compiled = []
        for row in check["compiled_artifacts"]:
            assert row["complete"] is True
            exact = {key: row[key] for key in ("path", "bytes", "sha256")}
            assert pin(exact["path"]) == exact
            files[exact["path"]] = exact
            compiled.append(exact)
        assert compiled and any(Path(row["path"]).name == name + ".olean" for row in compiled)
        for row in [check["source"], check["augmented_source"], check["environment_manifest"], check_pin]:
            assert pin(row["path"]) == row
            files[row["path"]] = row
        library = str(Path(compiled[0]["path"]).parent)
        if library not in body["lean_path"]:
            body["lean_path"].insert(0, library)
        body["source_import_modules"].append({"module": name, "package": "qualified-local-theorem",
            "source": check["augmented_source"], "compiled": compiled})
        body["local_checked_modules"].append({"module": name, "qualification": check_pin,
            "environment": check["environment_manifest"]})
    body["selected_proof_sources"] = [sources[0]["captured"]]
    assert sources[0]["original"]["sha256"] == args.expected_source_sha256
    body["profile_parent"] = pin(base)
    body["per_check_sources"] = sources
    body["files"] = [files[name] for name in sorted(files)]
    body["external_file_count"] = len(files)
    body["external_file_bytes"] = sum(row["bytes"] for row in files.values())
    # Preserve every qualified local import and every native retention bound.
    assert body["native_per_file_capture_bytes_unchanged"] == 65536
    assert body["root_reconstructed_external_module_aggregate_max_bytes"] == 3997696
    profile = destination / "environment-manifest.json"
    write(profile, body)
    profile.chmod(0o444)
    specification = {"schema": "terminal-ranker-curvature-native-check-specification@1",
        "source": sources[0]["captured"], "environment_manifest": pin(profile),
        "expected_success": not args.negative, "theorem_names": args.theorem,
        "freeze_producer": sources[3]["captured"], "retention_helper": sources[2]["captured"],
        "python_executable": executable,
        "source_capture_scope": "individual held-byte copies; no whole-live atomic or loader-open claim"}
    target = ROOT / "preparation" / (args.mode + "-check-specification.json")
    write(target, specification)
    print(json.dumps({"specification": pin(target), "wrapper": sources[1]["captured"],
        "source": sources[0]["captured"], "profile": pin(profile),
        "retention_helper": sources[2]["captured"], "python_executable": executable}))


if __name__ == "__main__":
    main()
