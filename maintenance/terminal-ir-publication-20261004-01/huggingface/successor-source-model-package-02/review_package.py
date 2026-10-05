"""File-only package readback; no network, SQL, model or prover execution."""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parent
EXPECTED_MANIFEST = "e980fb03189a435d140a757629079b04cee4663993eafc3c1665a312210cbc5f"
EXPECTED_CLOSED = "49cec904cf7f0d7b013d5f26909480eee87e436f4f19bce79a7693d5dc897ac3"
EXPECTED_SHARD = "15495a34a39169648fed3ef9bc5041fdd76e5d59a711a92ac61d1fed65ab2352"
BLOCK = 1024 * 1024


def pin(path):
    assert path.is_absolute() and path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode)
        digest = hashlib.sha256()
        count = 0
        while data := os.read(fd, BLOCK):
            count += len(data)
            digest.update(data)
        assert before == os.fstat(fd) == path.lstat()
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
        assert self.count <= 256 * 1024 * 1024
        return data


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
    assert len(manifest["files"]) == 417 and len(manifest["data_shards"]) == 1
    assert len(manifest["exclusions"]) == 18
    assert all(row["kind"] == "transient_lock" for row in manifest["exclusions"])
    assert sum(row["files"] for row in manifest["scope_counts"]) == 411
    assert len(manifest["scope_counts"]) == 6 and len(manifest["six_source_test_files"]) == 6
    rows = {row["member"]: row for row in manifest["files"]}
    assert len(rows) == len(manifest["files"])
    for row in manifest["files"]:
        assert pin(Path(row["source_path"])) == {"path": row["source_path"], "bytes": row["bytes"], "sha256": row["sha256"]}
        assert row["source_stat_before"] == row["source_stat_after"]
        assert not row["scan_hits"]
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
        assert child.wait(timeout=60) == 0
    finally:
        if child.poll() is None:
            os.killpg(child.pid, 9)
            child.wait()
        child.stdout.close()
    assert seen == set(rows)
    assert decoded.count == shard["tar_bytes"] and decoded.digest.hexdigest() == shard["tar_sha256"]
    final_olean_rows = [row for row in rows.values() if "/evidence/actual-08/lean/" in row["member"] and row["member"].endswith(".olean")]
    assert sorted(row["bytes"] for row in final_olean_rows) == [15480, 102536]
    checks = manifest["closed_review_and_file_seal_checks"]
    assert checks[0]["direct_review_reference_pins_verified"] == 82
    review = json.loads(Path(checks[0]["path"]).read_bytes())
    assert len(review["outer_attempts"]) == 12
    for attempt in review["outer_attempts"]:
        for binding in (attempt["outer"], attempt["owned"]):
            assert any(row["source_path"] == binding["path"] and row["sha256"] == binding["sha256"] for row in rows.values())
    assert review["metadata"]["families"] == 26 and review["metadata"]["producer_rows"] == 4216
    assert pin(manifest_path) == manifest_pin and pin(closed_path) == closed_pin and pin(shard_path) == shard_pin
    assert pin(Path(zstd_pin["path"])) == zstd_pin
    result = {
        "schema": "terminal-source-model-frozen-package-file-only-review@1", "status": "passed",
        "manifest": manifest_pin, "package_closure": closed_pin, "data_shard": shard_pin,
        "file_count": len(rows), "six_qualification_root_files": 411, "six_source_test_files": 6,
        "all_source_files_exact_current_readback": True, "decoded_member_bytes_exact_readback": True,
        "decoded_tar_bytes": decoded.count, "decoded_tar_sha256": decoded.digest.hexdigest(),
        "excluded_transient_lock_count": 18, "all_12_qualification_outer_attempts_retained": True,
        "final_complete_olean_bytes": [15480, 102536],
        "metadata_claims_from_unchanged_closed_native_review": {"families": 26, "rows": 4216},
        "historical_relative_seal_resolution": "captured_evidence_beside_each_seal",
        "historical_ephemeral_input_paths_reverified": False, "old_CAP08_full_closure_duplicated": False,
        "credential_classification_scope": "frozen audited classifier07 result; this review does not repeat classification",
        "native_SQL_model_optimizer_prover_jobs": 0, "remote_mutations": 0,
        "full_task_satisfaction": "unknown", "whole_source_equivalence_proved": False,
        "model_convergence_proved": False, "reviewer": pin(Path(__file__).resolve()),
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
