"""Compare retained source paths with a target Git tree, without changing either.

History reachability and effective file retention are separate observations.
This command imports no model, compiler, or proof runtime and performs no fetch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess


MAX_BLOB_BYTES = 32 * 1024 * 1024


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.check_output(
        ["git", "--literal-pathspecs", "-C", str(repository), *arguments],
        stderr=subprocess.PIPE,
    )


def commit(repository: Path, revision: str) -> str:
    return git(repository, "rev-parse", "--verify", "--end-of-options",
               revision + "^{commit}").decode().strip()


def path_entry(repository: Path, revision: str, relative: str) -> dict | None:
    value = git(repository, "ls-tree", "-z", revision, "--", relative)
    if not value:
        return None
    records = value.rstrip(b"\0").split(b"\0")
    if len(records) != 1:
        raise ValueError("Select an individual source file, rather than a directory")
    header, name = records[0].split(b"\t", 1)
    mode, kind, object_id = header.decode().split()
    if name.decode() != relative or kind != "blob" or mode not in ("100644", "100755"):
        raise ValueError("Selected source must be an exact regular Git file")
    size = int(git(repository, "cat-file", "-s", object_id))
    if size > MAX_BLOB_BYTES:
        raise ValueError("Selected source exceeds the 32 MiB evidence-file bound")
    content = git(repository, "cat-file", "blob", object_id)
    if len(content) != size:
        raise ValueError("Git blob size changed during read")
    return {"mode": mode, "blob": object_id, "bytes": size,
            "sha256": hashlib.sha256(content).hexdigest()}


def review(repository: Path, source: str, target: str, paths: list[str]) -> dict:
    repository = Path(repository).resolve(strict=True)
    if not paths or len(paths) > 5000 or len(set(paths)) != len(paths):
        raise ValueError("Select between one and 5,000 distinct source paths")
    for relative in paths:
        parsed = PurePosixPath(relative)
        if (not relative or parsed.is_absolute() or str(parsed) != relative
                or any(part in ("..", ".git") for part in parsed.parts)):
            raise ValueError("Source paths must be normalized repository-relative paths")
    source_commit = commit(repository, source)
    target_commit = commit(repository, target)
    ancestry = subprocess.run(
        ["git", "-C", str(repository), "merge-base", "--is-ancestor",
         source_commit, target_commit], capture_output=True,
    )
    if ancestry.returncode not in (0, 1):
        raise RuntimeError("Git could not determine history reachability")
    entries = []
    for relative in sorted(paths):
        old = path_entry(repository, source_commit, relative)
        if old is None:
            raise ValueError("Selected path is absent from the source revision: " + relative)
        current = path_entry(repository, target_commit, relative)
        status = ("missing" if current is None else
                  "identical" if current == old else "modified")
        entries.append({"path": relative, "status": status,
                        "source": old, "target": current})
    counts = {status: sum(row["status"] == status for row in entries)
              for status in ("identical", "modified", "missing")}
    return {
        "schema": "autoencoder-effective-tree-review/v1",
        "repository": str(repository), "source_revision": source_commit,
        "target_revision": target_commit,
        "source_history_reachable_from_target": ancestry.returncode == 0,
        "paths": entries, "counts": counts,
        "scope": "Source presence only; modified files require review against later work.",
        "git_state_mutated": False, "model_executed": False,
        "semantic_qualification_granted": False, "lean_admission_granted": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", default="origin/main")
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-missing", action="store_true")
    args = parser.parse_args()
    result = review(args.repository, args.source, args.target, args.path)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(serialized)
    print(json.dumps({key: result[key] for key in (
        "source_revision", "target_revision",
        "source_history_reachable_from_target", "counts")}))
    if args.fail_on_missing and result["counts"]["missing"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
