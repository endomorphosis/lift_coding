"""Compare retained source paths with a target Git tree, without changing either.

History reachability and effective file retention are separate observations.
This command imports no model, compiler, or proof runtime and performs no fetch.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess


MAX_BLOB_BYTES = 32 * 1024 * 1024


def _file_identity(info: os.stat_result) -> tuple:
    return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def working_entry(repository: Path, relative: str, expected: dict,
                  comparison: str, expected_revision: str) -> dict:
    """Hash one regular file through no-follow descriptors and endpoint fences.

    An absent target Git file compares against its retained source blob. These
    observations do not constitute an atomic snapshot across different files.
    """
    opened: list[int] = []
    witnesses: list[tuple[int, str, tuple, int]] = []
    flags = os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW | os.O_DIRECTORY

    def directory(parent: int, name: str) -> int:
        before = os.stat(name, dir_fd=parent, follow_symlinks=False)
        if not stat.S_ISDIR(before.st_mode):
            raise ValueError("Working-tree ancestors must be actual directories")
        child = os.open(name, flags, dir_fd=parent)
        opened.append(child)
        if _file_identity(os.fstat(child)) != _file_identity(before):
            raise ValueError("Working-tree directory changed before open")
        witnesses.append((parent, name, _file_identity(before), child))
        return child

    def fence() -> None:
        # Directory contents may change as unrelated agents work. Only their
        # physical identity/mode is bound; selected file metadata is bound fully.
        for parent, name, identity, child in witnesses:
            current = _file_identity(os.stat(name, dir_fd=parent, follow_symlinks=False))
            actual = _file_identity(os.fstat(child))
            if current[:3] != identity[:3] or actual[:3] != identity[:3]:
                raise ValueError("Working-tree ancestor changed during read")

    try:
        base = os.open("/", flags)
        opened.append(base)
        for part in repository.parts[1:]:
            base = directory(base, part)
        parts = PurePosixPath(relative).parts
        try:
            for part in parts[:-1]:
                base = directory(base, part)
            before = os.stat(parts[-1], dir_fd=base, follow_symlinks=False)
        except FileNotFoundError:
            fence()
            return {"status": "missing", "comparison_reference": comparison,
                    "expected_revision": expected_revision,
                    "mode": None, "bytes": None, "sha256": None}
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("Working-tree source must be a regular file")
        if before.st_size > MAX_BLOB_BYTES:
            raise ValueError("Working-tree source exceeds the 32 MiB evidence-file bound")
        descriptor = os.open(parts[-1], os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW
                             | os.O_NONBLOCK, dir_fd=base)
        opened.append(descriptor)
        identity = _file_identity(before)
        if _file_identity(os.fstat(descriptor)) != identity:
            raise ValueError("Working-tree file changed before open")
        count, digest = 0, hashlib.sha256()
        while True:
            block = os.read(descriptor, min(65536, before.st_size - count + 1))
            if not block:
                break
            count += len(block)
            if count > before.st_size:
                raise ValueError("Working-tree file grew during read")
            digest.update(block)
        if (count != before.st_size or _file_identity(os.fstat(descriptor)) != identity
                or _file_identity(os.stat(parts[-1], dir_fd=base,
                                          follow_symlinks=False)) != identity):
            raise ValueError("Working-tree file metadata changed during read")
        fence()
        mode = "100755" if before.st_mode & stat.S_IXUSR else "100644"
        actual = {"mode": mode, "bytes": count, "sha256": digest.hexdigest()}
        status = "identical" if all(actual[key] == expected[key] for key in actual) else "modified"
        return {"status": status, "comparison_reference": comparison,
                "expected_revision": expected_revision, **actual,
                "filesystem_mode": format(stat.S_IMODE(before.st_mode), "04o")}
    except OSError as error:
        raise ValueError("Cannot inspect stable regular working-tree source") from error
    finally:
        for descriptor in reversed(opened):
            os.close(descriptor)


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


def review(repository: Path, source: str, target: str, paths: list[str], *,
           working_tree: bool = False) -> dict:
    unresolved_repository = Path(repository).absolute()
    repository = Path(repository).resolve(strict=True)
    if working_tree and unresolved_repository != repository:
        raise ValueError("Working-tree repository must have a canonical directory path")
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
        entry = {"path": relative, "status": status, "source": old, "target": current}
        if working_tree:
            entry["working_tree"] = working_entry(
                repository, relative, current if current is not None else old,
                "target" if current is not None else "source",
                target_commit if current is not None else source_commit)
        entries.append(entry)
    counts = {status: sum(row["status"] == status for row in entries)
              for status in ("identical", "modified", "missing")}
    result = {
        "schema": "autoencoder-effective-tree-review/v1",
        "repository": str(repository), "source_revision": source_commit,
        "target_revision": target_commit,
        "source_history_reachable_from_target": ancestry.returncode == 0,
        "paths": entries, "counts": counts,
        "scope": "Source presence only; modified files require review against later work.",
        "git_state_mutated": False, "model_executed": False,
        "semantic_qualification_granted": False, "lean_admission_granted": False,
    }
    if working_tree:
        result["working_counts"] = {
            status: sum(row["working_tree"]["status"] == status for row in entries)
            for status in ("identical", "modified", "missing")}
        result["working_tree_scope"] = (
            "Current regular file SHA-256/bytes/mode against target, or retained source when "
            "target is absent; no-follow reads and endpoint fences, not an atomic tree snapshot.")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", default="origin/main")
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-missing", action="store_true")
    parser.add_argument("--working-tree", action="store_true")
    parser.add_argument("--fail-on-working-tree-missing", action="store_true")
    args = parser.parse_args()
    if args.fail_on_working_tree_missing and not args.working_tree:
        parser.error("--fail-on-working-tree-missing requires --working-tree")
    result = review(args.repository, args.source, args.target, args.path,
                    working_tree=args.working_tree)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        with args.output.open("x") as stream:
            stream.write(serialized)
    summary = {key: result[key] for key in (
        "source_revision", "target_revision",
        "source_history_reachable_from_target", "counts")}
    if args.working_tree:
        summary["working_counts"] = result["working_counts"]
        summary["working_paths"] = [{"path": row["path"], **row["working_tree"]}
                                    for row in result["paths"]]
    print(json.dumps(summary))
    if args.fail_on_missing and result["counts"]["missing"]:
        raise SystemExit(1)
    if args.fail_on_working_tree_missing and result["working_counts"]["missing"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
