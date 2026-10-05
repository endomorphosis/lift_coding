"""Freeze one additive source against the already qualified analytic closure.

This producer only reads files and copies new inputs. It never modifies prior
qualification sources, permissions, artifacts, or the external Mathlib closure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
PRIOR = ROOT.with_name("ranker-real-curvature-20261005-01")


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--theorem", action="append", required=True)
    args = parser.parse_args()
    base = PRIOR / "preparation/lean-original-descent-01-producer/environment-manifest.json"
    assert pin(base)["sha256"] == "329b993f9c09e978c2c46b173670a93195ddf720c9462472824eae283a7ac341"
    body = json.loads(base.read_bytes())
    checker = PRIOR / "preparation/lean-original-descent-01-producer/bounded_analytic_checker.py"
    retention = PRIOR / "preparation/lean-original-descent-01-producer/RetainLeanProof.py"
    assert pin(checker)["sha256"] == "04015267ed110533a7406c0b39c38b88a974a1d80259fd5755a99ef908a8a8b4"
    assert pin(retention)["sha256"] == "ccdf7df547844ac5d39cc077c8a14194fd06f7bb51838d80ffa9d7f349999e66"
    destination = ROOT / "preparation" / (args.mode + "-producer")
    destination.mkdir()
    files = {row["path"]: row for row in body["files"]}
    sources = []
    for original in (args.source.resolve(strict=True), checker, retention, Path(__file__).resolve()):
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
    body["selected_proof_sources"] = [sources[0]["captured"]]
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
        "expected_success": True, "theorem_names": args.theorem,
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
