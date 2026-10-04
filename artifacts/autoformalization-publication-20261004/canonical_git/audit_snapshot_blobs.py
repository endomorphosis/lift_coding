"""Read selected snapshot histories against frozen currently fetched origin refs."""
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

BASE = Path("/home/barberb/lift_coding/artifacts/autoformalization-publication-20261004/canonical_git")


def main():
    selected = json.loads((BASE / "final-selection.json").read_text())
    results = []
    for snapshot in selected["snapshots"]:
        repo = snapshot["repository"]
        refs = subprocess.check_output(["git", "for-each-ref", "--format=%(refname) %(objectname)", "refs/remotes/origin"], cwd=repo).decode().splitlines()
        excluded = sorted({line.split()[1] for line in refs})
        with tempfile.TemporaryFile() as object_names:
            subprocess.run(["git", "rev-list", "--objects", snapshot["snapshot_commit"], "--not", *excluded], cwd=repo, stdout=object_names, check=True)
            object_names.seek(0)
            process = subprocess.Popen(["git", "cat-file", "--batch-check=%(objectname) %(objecttype) %(objectsize) %(rest)"], cwd=repo, stdin=object_names, stdout=subprocess.PIPE)
            count, blob_count, total, oversized = 0, 0, 0, []
            for line in process.stdout:
                parts = line.decode("utf-8", "surrogateescape").strip().split(" ", 3)
                oid, kind, size = parts[:3]
                size = int(size)
                count += 1
                if kind == "blob":
                    blob_count += 1
                    total += size
                    if size > 100 * 1024 * 1024:
                        oversized.append({"oid": oid, "bytes": size, "path": parts[3] if len(parts) == 4 else None})
            if process.wait() != 0:
                raise ValueError("Git object inspection failed")
        result = {"name": snapshot["name"], "repository": repo, "snapshot_commit": snapshot["snapshot_commit"], "selected_fetched_origin_refs": refs, "newly_reachable_object_count": count, "newly_reachable_blob_count": blob_count, "newly_reachable_blob_bytes": total, "blobs_over_100mib": oversized}
        results.append(result)
        print(json.dumps({"name": result["name"], "objects": count, "blobs": blob_count, "oversized": len(oversized)}), flush=True)
    report = {"schema": "canonical-newly-reachable-blob-audit/v1", "results": results, "origin_fetch_executed": False, "push_executed": False, "history_rewritten": False, "scope": "Selected snapshots minus only the explicit currently fetched origin-ref generations; unselected future merge histories are outside this audit."}
    def raw(value):
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    report["content_sha256"] = hashlib.sha256(raw(report)).hexdigest()
    path = BASE / "newly-reachable-blobs.json"
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw(report) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    print(json.dumps({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}), flush=True)


if __name__ == "__main__":
    main()
