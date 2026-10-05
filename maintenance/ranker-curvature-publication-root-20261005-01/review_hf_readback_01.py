"""Rejoin the completed publication receipts and freshly read the public HF tree.

Only bounded JSON evidence and committed path metadata are read. No SDK logs,
cached credentials, model jobs, native qualification jobs, or remote writes.
"""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import urllib.request

ROOT = Path(__file__).resolve().parent
COMMIT = "8b7b8c896749e0ca3884114cedbed782a88f4702"
PARENT = "af2ef515e4f69f504f466e3f3146e5dfcfea8c2d"
REPO = "Publicus/codebase-ir-proof-index"


def read(path):
    path = Path(path).absolute()
    assert path.resolve(strict=True) == path
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_size <= 32 * 1024**2
        chunks = []
        while block := os.read(fd, 1024**2):
            chunks.append(block)
        raw = b"".join(chunks)
        keys = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        signature = lambda row: tuple(getattr(row, key) for key in keys)
        assert signature(before) == signature(os.fstat(fd)) == signature(path.lstat())
        assert len(raw) == before.st_size
        return raw
    finally:
        os.close(fd)


def pin(path):
    raw = read(path)
    return {"path": str(Path(path).absolute()), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def load(path):
    return json.loads(read(path))


def fetch(suffix):
    url = "https://huggingface.co/api/datasets/" + REPO + suffix
    request = urllib.request.Request(url, headers={"User-Agent": "ranker-curvature-readback/1"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(4 * 1024**2 + 1)
    assert len(raw) <= 4 * 1024**2
    return url, json.loads(raw)


def save(path, value):
    with path.open("xb") as stream:
        stream.write((json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode())
        stream.flush()
        os.fsync(stream.fileno())


def main():
    receipt_root = ROOT / "hf-publication-01"
    documents = [ROOT / "hf-plan-01.json", ROOT / "final-upload-scan-01.json",
                 ROOT / "hf-publication-invocation-01.json",
                 ROOT / "hf-publication-outer-01/closed.json",
                 receipt_root / "remote-before.json", receipt_root / "commit-observed.json",
                 receipt_root / "verified-files.json", receipt_root / "closed.json"]
    before_pins = [pin(path) for path in documents]
    plan, scan, invocation, outer, before, observed, verified, closed = [load(path) for path in documents]
    assert before_pins[0]["sha256"] == "3c522b22d90598349a13378425613e8ee4840e59785e2343a31237503803d8b8"
    assert before_pins[2]["sha256"] == "87a9346a639adbe7734617e9dd09e64264a2a47aee85b17738210f2750d4773c"
    assert plan["repo_id"] == REPO and plan["expected_parent_commit"] == PARENT
    assert scan["status"] == "passed" and scan["candidate_hits"] == 0
    assert outer["status"] == "closed_phase" and outer["returncode"] == 0
    assert outer["input_pins_unchanged"] and outer["cleanup_errors"] == []
    assert closed["status"] == "PUBLISHED_AND_VERIFIED" and closed["remote_readback_verified"]
    assert closed["commit"] == observed["commit"] == verified["commit"] == COMMIT
    assert closed["parent"] == observed["parent"] == before["commit"] == PARENT
    assert closed["prior_immutable_remote_files_preserved"] == 180
    expected = {row["remote"]: row["local"] for row in plan["files"]}
    assert len(expected) == len(plan["files"]) == len(verified["files"]) == 47
    assert sum(row["bytes"] for row in expected.values()) == 51345329
    actual = {row["remote"]["path"]: row for row in verified["files"]}
    assert set(actual) == set(expected)
    for name, binding in expected.items():
        row = actual[name]
        assert pin(binding["path"]) == binding == row["expected"]
        assert row["remote"]["bytes"] == binding["bytes"]
        if row["remote"]["lfs_sha256"] is not None:
            assert row["remote"]["lfs_sha256"] == binding["sha256"]
            assert row["verification_method"] == "committed_LFS_SHA256_and_size"
        else:
            assert row["verification_method"] == "downloaded_small_file_SHA256_and_size"

    main_url, main_info = fetch("/revision/main")
    assert main_info["sha"] == COMMIT
    # This repository has fewer than one API tree page. Reject pagination rather
    # than silently treating a partial tree as complete.
    tree_url = "https://huggingface.co/api/datasets/" + REPO + "/tree/" + COMMIT + "?recursive=true&expand=false"
    with urllib.request.urlopen(urllib.request.Request(tree_url, headers={"User-Agent": "ranker-curvature-readback/1"}), timeout=30) as response:
        assert not response.headers.get("Link")
        raw = response.read(4 * 1024**2 + 1)
    assert len(raw) <= 4 * 1024**2
    tree = {row["path"]: row for row in json.loads(raw) if row["type"] == "file"}
    mutable = set(closed["mutable_paths_explicitly_updated"])
    assert len(mutable) == 2 and len(before["files"]) == 182
    preserved = 0
    for name, row in before["files"].items():
        if name in mutable:
            continue
        remote = tree[name]
        assert remote["size"] == row["bytes"] and remote["oid"] == row["blob_id"]
        assert remote.get("lfs", {}).get("oid") == row["lfs_sha256"]
        preserved += 1
    assert preserved == 180
    for name, binding in expected.items():
        remote = tree[name]
        assert remote["size"] == binding["bytes"]
        assert remote["oid"] == actual[name]["remote"]["blob_id"]
        assert remote.get("lfs", {}).get("oid") == actual[name]["remote"]["lfs_sha256"]
    assert len(tree) == 227
    assert [pin(path) for path in documents] == before_pins
    for binding in expected.values():
        assert pin(binding["path"]) == binding
    result = {"schema": "ranker-curvature-public-HF-readback-join@1", "status": "passed",
              "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "producer": pin(Path(__file__).resolve()), "commit": COMMIT, "parent": PARENT,
              "public_main_readback_url": main_url, "public_tree_readback_url": tree_url,
              "selected_files": 47, "selected_bytes": 51345329,
              "verification_methods": dict(collections.Counter(row["verification_method"] for row in actual.values())),
              "prior_immutable_files_preserved": preserved, "committed_total_regular_files": len(tree),
              "receipt_pins_before_after": before_pins,
              "all_selected_local_pins_rechecked": True, "fresh_public_main_matches_commit": True,
              "raw_SDK_logs_read": False, "model_training_calls": 0, "prover_calls": 0,
              "remote_mutations": 0, "proof_authority": False,
              "execution_authority": False, "completion_authority": False}
    target = ROOT / "hf-public-readback-01.json"
    save(target, result)
    print(json.dumps({"status": result["status"], "commit": COMMIT, "receipt": pin(target)}))


if __name__ == "__main__":
    main()
