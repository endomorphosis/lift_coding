"""Independent file/member and frozen credential scan; no native proof reruns."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import time
import types

ROOT = Path(__file__).resolve().parent
EXPECTED_MANIFEST = "1e7e5c92b4d1bcad035aab75d77ddfc9fd650d9c306fb52e1045b681fdb744bf"
EXPECTED_CLOSED = "6a5b53f221d8241f7a51048fdb9cc2c9e05b1d61cbee712d5fedc689399faaa3"
EXPECTED_SHARD = "9904cedd6e8b45f69e4a1ba5f7505444b8cdcbaf116817d0e09a3c548ee31ffb"
BLOCK = 1024 * 1024


def pin(path):
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        digest = hashlib.sha256()
        count = 0
        while data := os.read(fd, BLOCK):
            count += len(data)
            digest.update(data)
        fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
        assert all(getattr(before, key) == getattr(os.fstat(fd), key) == getattr(path.lstat(), key) for key in fields)
        return {"path": str(path), "bytes": count, "sha256": digest.hexdigest()}
    finally:
        os.close(fd)


class DigestReader:
    def __init__(self, stream):
        self.stream = stream
        self.digest = hashlib.sha256()
        self.count = 0

    def read(self, size=-1):
        assert 0 <= size <= BLOCK
        data = self.stream.read(size)
        self.digest.update(data)
        self.count += len(data)
        assert self.count <= 1024 * 1024
        return data


def frozen(path, expected, name):
    binding = pin(path)
    assert binding["sha256"] == expected
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
    assert pin(path) == binding
    return module, binding


def main():
    started = time.monotonic()
    manifest_path = ROOT / "package/manifest.json"
    closed_path = ROOT / "closed.json"
    manifest_pin = pin(manifest_path)
    closed_pin = pin(closed_path)
    assert manifest_pin["sha256"] == EXPECTED_MANIFEST
    assert closed_pin["sha256"] == EXPECTED_CLOSED
    manifest = json.loads(manifest_path.read_bytes())
    closed = json.loads(closed_path.read_bytes())
    assert closed["status"] == "passed_local_frozen_package"
    assert closed["error"] is None and closed["cleanup_errors"] == []
    assert closed["remote_mutations"] == closed["model_optimizer_prover_native_SQL_jobs"] == 0
    assert len(manifest["files"]) == 41 and len(manifest["data_shards"]) == 1
    assert len(manifest["exclusions"]) == 2
    assert all(row["kind"] == "transient_lock" for row in manifest["exclusions"])
    assert sum(row["files"] for row in manifest["scope_counts"]) == 41
    assert len(manifest["scope_counts"]) == 2 and manifest["direct_live_source_files"] == []
    rows = {row["member"]: row for row in manifest["files"]}
    assert len(rows) == len(manifest["files"])
    for row in manifest["files"]:
        assert pin(Path(row["source_path"])) == {"path": row["source_path"], "bytes": row["bytes"], "sha256": row["sha256"]}
        assert row["source_stat_before"] == row["source_stat_after"] and not row["scan_hits"]
    shard = manifest["data_shards"][0]
    shard_path = Path(shard["path"])
    shard_pin = pin(shard_path)
    assert shard_pin["sha256"] == EXPECTED_SHARD
    assert shard_pin == {key: shard[key] for key in ("path", "bytes", "sha256")}
    assert shard_pin["bytes"] <= 256 * 1024 * 1024
    zstd_pin = pin(Path(manifest["zstd_executable"]["path"]))
    assert zstd_pin == manifest["zstd_executable"]
    child = subprocess.Popen([zstd_pin["path"], "--quiet", "-d", "--stdout", str(shard_path)],
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, start_new_session=True)
    seen = set()
    decoded = DigestReader(child.stdout)
    try:
        with tarfile.open(fileobj=decoded, mode="r|") as archive:
            for member in archive:
                assert member.isfile() and member.name in rows and member.name not in seen
                row = rows[member.name]
                assert member.size == row["bytes"]
                assert member.mode == 0o644 and member.uid == member.gid == member.mtime == 0
                stream = archive.extractfile(member)
                digest = hashlib.sha256()
                count = 0
                while block := stream.read(BLOCK):
                    digest.update(block)
                    count += len(block)
                assert count == row["bytes"] and digest.hexdigest() == row["sha256"]
                seen.add(member.name)
        while decoded.read(BLOCK):
            pass
        assert child.wait(timeout=30) == 0
    finally:
        if child.poll() is None:
            os.killpg(child.pid, 9)
            child.wait()
        child.stdout.close()
    assert seen == set(rows)
    assert decoded.count == shard["tar_bytes"] and decoded.digest.hexdigest() == shard["tar_sha256"]
    olean_rows = [row for row in rows.values() if "/evidence/lean-01/" in row["member"] and row["member"].endswith(".olean")]
    assert [row["bytes"] for row in olean_rows] == [29336]
    checks = manifest["closed_review_and_file_seal_checks"]
    assert len(checks) == 1 and checks[0]["sealed_files"] == 38
    review = json.loads(Path(checks[0]["qualified_review"]["path"]).read_bytes())
    assert review["native_lean_calls"] == 2 and review["native_public_plan_metrics_calls"] == 2
    assert review["counter_scope_correction"]["historical_value"] == 0
    assert len(review["outer_attempts"]) == 2
    for binding in review["outer_attempts"]:
        assert any(row["source_path"] == binding["path"] and row["sha256"] == binding["sha256"] for row in rows.values())
    assert review["full_task_satisfaction"] == "unknown" and review["RPI_macrocriteria"] == {"open": 32, "qualified": 0}
    for binding in manifest["previous_frozen_package_preserved"].values():
        if isinstance(binding, dict):
            assert pin(Path(binding["path"])) == binding
    api, helper_pin = frozen(ROOT.parent / "build_evidence_archive_02.py",
                            "f72c1ea8efb3d04a67eca31af333d73b2079fd9cfbcfd7439580f87d56e53036", "review_frozen_archive_helper")
    classifier, classifier_pin = frozen(ROOT.parent / "classify_and_prepare_public_archive_07.py",
                            "dd457cb927270f53617781de1f576d1de1fac76b86191d769f4f923fa966a1f8", "review_frozen_archive_classifier")
    scanner = api.Scanner()
    scanner.patterns = [(name, pattern) for name, pattern in api.PATTERNS if name != "private_key_pem"]
    budget = classifier.Budget(seconds=30, decoded_bytes=8 * 1024**2,
                               container_bytes=1024**2, members=1000, depth=6)
    scan_inputs = [ROOT / "build_package.py", ROOT / "freeze.json", closed_path, manifest_path, shard_path]
    scan_results = []
    for path in scan_inputs:
        inspection = classifier.Classifier(scanner, budget, ROOT)
        with path.open("rb") as stream:
            inspection.inspect(stream)
        assert not inspection.hits
        scan_results.append({"binding": pin(path), "scan_hits": [], "scan_counts": dict(inspection.counts)})
    assert pin(manifest_path) == manifest_pin and pin(closed_path) == closed_pin and pin(shard_path) == shard_pin
    assert pin(Path(zstd_pin["path"])) == zstd_pin
    result = {
        "schema": "terminal-source-model-frozen-package-file-only-review@1", "status": "passed",
        "manifest": manifest_pin, "package_closure": closed_pin, "data_shard": shard_pin,
        "file_count": len(rows), "two_qualification_root_files": 41, "direct_live_source_files": 0,
        "all_source_files_exact_current_readback": True, "decoded_member_bytes_exact_readback": True,
        "decoded_tar_bytes": decoded.count, "decoded_tar_sha256": decoded.digest.hexdigest(),
        "excluded_transient_lock_count": 2, "all_2_qualification_outer_attempts_retained": True,
        "final_complete_olean_bytes": [29336],
        "claims_from_unchanged_closed_native_review": {"strict_bounds": 8, "structural_clauses": 4,
            "input_byte_frame": True, "native_lean_calls": 2, "outer_placeholder_correction_preserved": True},
        "file_seal_resolution": "absolute_captured_evidence_paths",
        "historical_ephemeral_input_paths_reverified": False, "old_CAP08_full_closure_duplicated": False,
        "credential_classification_scope": "Frozen audited classifier07 per-source and full archive result; review additionally scans5 new producer/metadata/package inputs.",
        "extra_scans": scan_results, "scanner_helper": helper_pin, "scanner_classifier": classifier_pin,
        "exact_available_cached_credential_veto": True, "scan_budget_decoded_bytes": budget.decoded,
        "scan_budget_members": budget.members, "universal_secret_absence_claimed": False,
        "retained_evidence_scope": "Single authored16-request source execution and8 finite metric inequalities; all global claims open.",
        "native_SQL_model_optimizer_prover_jobs": 0, "remote_mutations": 0,
        "full_task_satisfaction": "unknown", "whole_source_equivalence_proved": False,
        "model_convergence_proved": False, "reviewer": pin(Path(__file__).resolve()),
        "review_preparation_failures_preserved_in_tool_history": ["First code-generation command SyntaxError before any review source writes; followup invocation FileNotFoundError because no reviewer existed."],
        "actual_file_only_review_elapsed_seconds": time.monotonic() - started,
    }
    target = ROOT / "file-only-review-01.json"
    with target.open("xb") as output:
        output.write(json.dumps(result, sort_keys=True, separators=(",", ":")).encode() + b"\n")
        output.flush()
        os.fsync(output.fileno())
    print(json.dumps({"status": result["status"], "review": pin(target),
                      "elapsed_seconds": result["actual_file_only_review_elapsed_seconds"]}))


if __name__ == "__main__":
    main()
