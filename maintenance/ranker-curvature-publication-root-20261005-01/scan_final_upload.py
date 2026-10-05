"""Scan the exact new upload set with the already pinned complete classifier."""
import hashlib
import json
from pathlib import Path
import tempfile
import types

ROOT = Path(__file__).resolve().parent
HF = ROOT.parent / "terminal-ir-publication-20261004-01/huggingface"
HELPERS = {"archive": (HF / "build_evidence_archive_02.py", "f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036"),
    "classifier": (HF / "classify_and_prepare_public_archive_07.py", "dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8")}


def pin(path):
    path = Path(path).resolve(strict=True); raw = path.read_bytes()
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load(name):
    path, expected = HELPERS[name]; assert pin(path)["sha256"] == expected
    module = types.ModuleType("held_final_upload_" + name); module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    return module


def main():
    own = pin(__file__); plan_path = ROOT / "hf-plan-01.json"; plan_pin = pin(plan_path)
    assert plan_pin["sha256"] == "3c522b22d90598349a13378425613e8ee4840e59785e2343a31237503803d8b8"
    plan = json.loads(plan_path.read_bytes()); expected = [row["local"] for row in plan["files"]]
    assert len(expected) == 47 and all(pin(row["path"]) == row for row in expected)
    archive, classifier = load("archive"), load("classifier")
    scanner = archive.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in archive.PATTERNS if name != "private_key_pem"]
    budget = classifier.Budget(seconds=180, decoded_bytes=1024**3, container_bytes=16*1024**2, members=10000, depth=6)
    rows = []
    with tempfile.TemporaryDirectory(prefix="final-upload-scan-", dir=ROOT) as directory:
        for item in plan["files"]:
            inspection = classifier.Classifier(scanner, budget, Path(directory))
            with Path(item["local"]["path"]).open("rb") as stream:
                inspection.inspect(stream)
            assert not inspection.hits, "actual selected upload rejected by pinned credential/container classifier"
            rows.append({"remote": item["remote"], "local": item["local"], "scan_counts": dict(inspection.counts), "candidate_hits": 0})
    budget.check()
    assert pin(plan_path) == plan_pin and pin(__file__) == own
    assert all(pin(row["path"]) == row for row in expected)
    for path, expected_sha in HELPERS.values(): assert pin(path)["sha256"] == expected_sha
    output = ROOT / "final-upload-scan-01.json"; assert not output.exists()
    result = {"schema": "ranker-curvature-exact-final-upload-scan@1", "status": "passed",
        "plan": plan_pin, "scanner": own, "files": rows, "selected_files": len(rows),
        "selected_bytes": sum(row["local"]["bytes"] for row in rows), "candidate_hits": 0,
        "aggregate_decoded_bytes": budget.decoded, "recursive_members": budget.members,
        "bounded_complete_container_and_PEM_scan": True, "exact_available_cached_credential_veto": True,
        "universal_secret_free_claim": False, "remote_mutations": 0, "new_native_qualification_jobs": 0,
        "helper_pins": {name: pin(path) for name, (path, _) in HELPERS.items()}}
    output.write_text(json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({"receipt": pin(output), "selected_files": len(rows), "candidate_hits": 0,
        "aggregate_decoded_bytes": budget.decoded}))


if __name__ == "__main__": main()
