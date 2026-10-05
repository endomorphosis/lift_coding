"""File-only producer for immutable per-check source and dependency profiles."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def pin(path):
    path = Path(path).resolve(strict=True)
    raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--theorem", action="append", default=[])
    parser.add_argument("--prior", action="append", default=[], help="ModuleName=passed-check-result.json")
    parser.add_argument("--negative", action="store_true")
    args = parser.parse_args()
    base = ROOT / "evidence/environment-01/environment-manifest.json"
    body = json.loads(base.read_bytes())
    destination = ROOT / "preparation" / (args.mode + "-producer")
    destination.mkdir()
    files = {row["path"]: row for row in body["files"]}
    sources = []
    for original in [args.source.resolve(strict=True), ROOT / "environment/bounded_analytic_checker.py"]:
        raw = original.read_bytes(); captured = destination / original.name
        with captured.open("xb") as stream: stream.write(raw)
        captured.chmod(0o444); sources.append({"original": pin(original), "captured": pin(captured)})
    source = sources[0]["captured"]
    files[source["path"]] = source
    body["selected_proof_sources"] = [source]
    body["profile_parent"] = pin(base)
    body["local_checked_modules"] = []
    for entry in args.prior:
        name, path = entry.split("=", 1)
        check_pin = pin(Path(path)); check = json.loads(Path(check_pin["path"]).read_bytes())
        assert check["status"] == "passed" and check["matches_expectation"] is True and check["expected_success"] is True
        assert check["axiom_report_error"] is None and check["post_call_binding_error"] is None
        compiled = []
        for row in check["compiled_artifacts"]:
            assert row.get("complete", True) is True
            exact = {key: row[key] for key in ("path", "bytes", "sha256")}
            assert pin(exact["path"]) == exact
            files[exact["path"]] = exact; compiled.append(exact)
            Path(exact["path"]).chmod(0o444)
        assert compiled and any(Path(row["path"]).name == name + ".olean" for row in compiled)
        for row in [check["augmented_source"], check["source"], check_pin]:
            assert pin(row["path"]) == row; files[row["path"]] = row
        library = str(Path(compiled[0]["path"]).parent)
        if library not in body["lean_path"]: body["lean_path"].insert(0, library)
        module = {"module": name, "package": "qualified-local-theorem", "source": check["augmented_source"], "compiled": compiled}
        assert not any(row["module"] == name for row in body["source_import_modules"])
        body["source_import_modules"].append(module)
        body["local_checked_modules"].append({"module": name, "qualification": check_pin, "environment": check["environment_manifest"]})
    body["files"] = [files[path] for path in sorted(files)]
    body["external_file_count"] = len(files)
    body["external_file_bytes"] = sum(row["bytes"] for row in files.values())
    body["per_check_sources"] = sources
    profile = destination / "environment-manifest.json"
    with profile.open("xb") as stream:
        stream.write((json.dumps(body, sort_keys=True, separators=(",", ":")) + "\n").encode())
    profile.chmod(0o444)
    specification = {"schema": "terminal-ranker-curvature-native-check-specification@1", "source": source,
                     "environment_manifest": pin(profile), "expected_success": not args.negative,
                     "theorem_names": args.theorem, "freeze_producer": pin(Path(__file__).resolve()),
                     "source_capture_scope": "individual held-byte copy; no atomic whole-live or loader-open trace"}
    target = ROOT / "preparation" / (args.mode + "-check-specification.json")
    with target.open("x") as stream: stream.write(json.dumps(specification, indent=2) + "\n")
    print(json.dumps({"specification": pin(target), "wrapper": sources[1]["captured"], "source": source,
                      "profile": pin(profile)}))


if __name__ == "__main__": main()
