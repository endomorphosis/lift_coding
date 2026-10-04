"""Pin every canonical snapshot Git blob, preserving intentional source deletes.

One persistent cat-file process per repository streams raw blob bytes into SHA256.
The result binds the complete committed canonical tree, not semantic correctness
or physical original working-tree file contents outside the selected source pins.
Gitlinks are separately inventoried and remain publication-coordinator-owned.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

BASE = Path("/home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/canonical_git")
REPORTS = {"root": "snapshot-01", "datasets": "snapshot-datasets-04", "accelerate": "snapshot-03",
           "kit": "snapshot-02", "mcp_cpp": "snapshot-02", "hallucinate": "snapshot-02", "swissknife": "snapshot-02"}


def pin_snapshot(name):
    report_path = BASE / REPORTS[name] / (name + ".json")
    report_bytes = report_path.read_bytes()
    selected = json.loads(report_bytes)
    repository, snapshot = selected["repository"], selected["snapshot_commit"]
    tree = subprocess.check_output(["git", "ls-tree", "-r", "-z", snapshot], cwd=repository)
    entries, gitlinks = [], []
    for record in tree.split(b"\0"):
        if not record:
            continue
        metadata, path = record.split(b"\t", 1)
        mode, kind, oid = metadata.decode().split()
        row = {"path": os.fsdecode(path), "mode": mode, "git_oid": oid}
        if kind == "blob":
            entries.append(row)
        elif mode == "160000":
            gitlinks.append(row)
        else:
            raise ValueError("unexpected canonical tree entry type")
    process = subprocess.Popen(["git", "cat-file", "--batch"], cwd=repository,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    cache, pins = {}, []
    try:
        for row in entries:
            oid = row["git_oid"]
            if oid not in cache:
                process.stdin.write(oid.encode() + b"\n")
                process.stdin.flush()
                header = process.stdout.readline().decode().strip().split()
                if len(header) != 3 or header[:2] != [oid, "blob"]:
                    raise ValueError("canonical blob lookup mismatch")
                size = int(header[2])
                digest, remaining = hashlib.sha256(), size
                while remaining:
                    data = process.stdout.read(min(remaining, 1024 * 1024))
                    if not data:
                        raise ValueError("incomplete Git blob output")
                    digest.update(data)
                    remaining -= len(data)
                if process.stdout.read(1) != b"\n":
                    raise ValueError("Git blob terminator missing")
                cache[oid] = {"bytes": size, "sha256": digest.hexdigest()}
            pins.append({"state": "present", "path": row["path"], "mode": row["mode"],
                         "git_oid": oid, **cache[oid]})
        process.stdin.close()
        if process.wait() != 0:
            raise ValueError("Git batch lookup failed")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    present_paths = {row["path"] for row in pins}
    deleted = []
    for row in selected["selected_files"]:
        if row["state"] == "deleted":
            if row["path"] in present_paths:
                raise ValueError("intentional deleted path exists in canonical snapshot")
            deleted.append({"state": "deleted", "path": row["path"]})
    result = {"schema": "complete-canonical-snapshot-blob-pins/v1", "name": name,
              "repository": repository, "snapshot_commit": snapshot, "snapshot_ref": selected["snapshot_ref"],
              "snapshot_report_binding": {"path": str(report_path), "bytes": len(report_bytes),
                                          "sha256": hashlib.sha256(report_bytes).hexdigest()},
              "authoritative_source": {"snapshot_commit": snapshot, "selected_files": pins + deleted},
              "canonical_blob_path_count": len(pins), "unique_blob_count": len(cache),
              "intentional_deleted_path_count": len(deleted), "canonical_gitlinks_deferred": gitlinks,
              "unique_branch_only_additions_remain_allowed": True,
              "scope": "Raw committed snapshot blob paths and explicit selected deletions; no semantic or unchanged physical source-fidelity attestation.",
              "origin_push_executed": False, "training_executed": False}
    raw = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    result["content_sha256"] = hashlib.sha256(raw).hexdigest()
    output = BASE / "full-tree-pins-current"
    output.mkdir(mode=0o700, exist_ok=True)
    path = output / (name + ".json")
    with path.open("x", encoding="utf-8") as stream:
        os.chmod(path, 0o600)
        json.dump(result, stream, sort_keys=True, ensure_ascii=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"name": name, "blob_paths": len(pins), "unique_blobs": len(cache),
                      "intentional_deletes": len(deleted), "binding": {"path": str(path), "bytes": path.stat().st_size,
                                                                       "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", choices=list(REPORTS), required=True)
    args = parser.parse_args()
    os.umask(0o077)
    for name in args.targets:
        pin_snapshot(name)


if __name__ == "__main__":
    main()
