"""Package six explicit AB Python changes against the local sealed baseline.

Uses a temporary index/object directory for the source diff. Only three needed
baseline originals enter the separate apply-check repository. The source HEAD,
index and selected files are witnessed before and after; no source Git mutation
or upstream operation occurs. The root runs this only after the final freeze.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

BASELINE = "a28c7f07fb18fc67e131b8275cf596b289a02551"
MODIFIED = (
    "ipfs_accelerate_py/agent_supervisor/runtime/checked_context_dispatch.py",
    "ipfs_accelerate_py/agent_supervisor/runtime/checked_observer_budget.py",
    "test/api/test_checked_context_dispatch.py",
)
NEW = (
    "ipfs_accelerate_py/agent_supervisor/runtime/checked_dispatch_evidence.py",
    "test/api/test_checked_dispatch_evidence.py",
    "test/api/test_checked_dispatch_evidence_broker_signer.py",
)
PATHS = (*MODIFIED, *NEW)
MAX_SOURCE_BYTES = 4 * 1024 * 1024
MAX_PATCH_BYTES = 4 * 1024 * 1024
SCHEMA = "terminal-dispatch-evidence-source-review-package@1"


def need(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def signature(info):
    return tuple(getattr(info, name) for name in (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns"))


def read_regular(path, maximum=MAX_SOURCE_BYTES):
    need(path.is_absolute() and path.resolve(strict=True) == path,
         "one canonical regular source or metadata path required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and 0 <= before.st_size <= maximum, "bounded single-link regular file required")
        chunks, remaining = [], maximum + 1
        while remaining:
            chunk = os.read(fd, min(remaining, 65536))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        raw = b"".join(chunks)
        need(len(raw) == before.st_size and signature(before) == signature(os.fstat(fd))
             == signature(path.lstat()), "selected file changed during bounded capture")
        return raw, signature(before), stat.S_IMODE(before.st_mode)
    finally:
        os.close(fd)


def pin(path, raw):
    return {"path": str(path), "bytes": len(raw), "sha256": digest(raw)}


def write_exclusive(path, raw, mode=0o600):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
        os.fsync(fd)
    finally:
        os.close(fd)


def git(cwd, *args, input_bytes=None, git_environment=None):
    environment = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    environment.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1")
    if git_environment is not None:
        environment.update(git_environment)
    completed = subprocess.run([
        "git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", *args,
    ], cwd=cwd, env=environment, input=input_bytes, capture_output=True, check=False)
    need(completed.returncode == 0, "bounded explicit Git review operation failed: " + args[0])
    return completed.stdout


def index_blob(cwd, relative, raw, *, git_environment):
    object_id = git(cwd, "hash-object", "-w", "--no-filters", "--stdin",
                    input_bytes=raw, git_environment=git_environment).decode("ascii").strip()
    need(re.fullmatch(r"[0-9a-f]{40}", object_id), "literal public Git blob identity required")
    git(cwd, "update-index", "--add", "--cacheinfo", "100644", object_id, relative,
        git_environment=git_environment)
    return object_id


def build_package(stage, output_name, *, expected_baseline=BASELINE):
    """Create one exclusive source-only review package; never promote changes."""
    need(re.fullmatch(r"review-package-[0-9]{2,4}\.json", output_name),
         "one bounded review-package-NN.json output name required")
    need(stage.is_absolute() and stage.resolve(strict=True) == stage,
         "canonical AB stage directory required")
    checkout = stage / "checkout"
    need(checkout.is_dir() and checkout.resolve(strict=True) == checkout, "canonical AB checkout required")
    report_path = stage / output_name
    output = stage / output_name[:-5]
    need(not report_path.exists() and not report_path.is_symlink()
         and not output.exists() and not output.is_symlink(), "review package paths must be new")
    head = git(checkout, "rev-parse", "--verify", "HEAD").decode("ascii").strip()
    need(head == expected_baseline, "AB local baseline HEAD differs")
    git_directory = Path(git(checkout, "rev-parse", "--absolute-git-dir").decode().strip())
    need(git_directory == checkout / ".git" and git_directory.resolve(strict=True) == git_directory,
         "isolated AB clone Git directory required")
    source_index = git_directory / "index"
    index_before, index_signature, _ = read_regular(source_index)
    head_before, head_signature, _ = read_regular(git_directory / "HEAD", maximum=4096)
    snapshots = {}
    rows = []
    for relative in PATHS:
        current, witness, mode = read_regular(checkout / relative)
        need(not mode & 0o111, "reviewed Python files must retain non-executable Git mode")
        snapshots[relative] = (current, witness, mode)
        baseline = None if relative in NEW else git(checkout, "show", head + ":" + relative)
        if baseline is not None:
            need(len(baseline) <= MAX_SOURCE_BYTES and baseline != current,
                 "each selected modified file must change its bounded baseline bytes")
        else:
            absent = subprocess.run(["git", "cat-file", "-e", head + ":" + relative],
                cwd=checkout, env={key: value for key, value in os.environ.items() if not key.startswith("GIT_")},
                capture_output=True, check=False)
            need(absent.returncode != 0, "new review file unexpectedly exists in local baseline")
        rows.append({"relative_path": relative, "new": relative in NEW, "source_mode": oct(mode),
            "baseline": None if baseline is None else {"bytes": len(baseline), "sha256": digest(baseline)},
            "current": pin(checkout / relative, current), "git_mode": "100644"})
    output.mkdir(mode=0o700)
    patch_path = output / "change.patch"
    source_objects = git_directory / "objects"
    need(source_objects.is_dir() and source_objects.resolve(strict=True) == source_objects,
         "canonical baseline object directory required")
    with tempfile.TemporaryDirectory(prefix=".explicit-index-", dir=output) as temporary:
        temporary_path = Path(temporary)
        object_directory = temporary_path / "objects"
        object_directory.mkdir(mode=0o700)
        environment = {"GIT_INDEX_FILE": str(temporary_path / "index"),
            "GIT_OBJECT_DIRECTORY": str(object_directory),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(source_objects)}
        git(checkout, "read-tree", head, git_environment=environment)
        for relative in PATHS:
            index_blob(checkout, relative, snapshots[relative][0], git_environment=environment)
        changed = git(checkout, "diff", "--cached", "--name-only", "--no-ext-diff", "--no-textconv",
            head, "--", *PATHS, git_environment=environment).decode().splitlines()
        need(set(changed) == set(PATHS) and len(changed) == len(PATHS), "patch must contain exactly six explicit paths")
        git(checkout, "diff", "--cached", "--check", head, "--", *PATHS, git_environment=environment)
        patch = git(checkout, "diff", "--cached", "--binary", "--no-ext-diff", "--no-textconv",
            head, "--", *PATHS, git_environment=environment)
        need(0 < len(patch) <= MAX_PATCH_BYTES, "bounded complete public source patch required")
        write_exclusive(patch_path, patch)
    scratch = output / "apply-check"
    scratch.mkdir(mode=0o700)
    git(scratch, "init", "--quiet")
    scratch_environment = {"GIT_INDEX_FILE": str(scratch / ".git" / "index")}
    for relative in MODIFIED:
        old = git(checkout, "show", head + ":" + relative)
        path = scratch / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        write_exclusive(path, old, mode=0o644)
        index_blob(scratch, relative, old, git_environment=scratch_environment)
    baseline_paths = git(scratch, "ls-files", git_environment=scratch_environment).decode().splitlines()
    need(set(baseline_paths) == set(MODIFIED) and len(baseline_paths) == len(MODIFIED),
         "scratch baseline must contain only three needed original paths")
    git(scratch, "update-index", "--refresh", "--", *MODIFIED,
        git_environment=scratch_environment)
    scratch_baseline_tree = git(scratch, "write-tree", git_environment=scratch_environment).decode("ascii").strip()
    need(re.fullmatch(r"[0-9a-f]{40}", scratch_baseline_tree), "exact scratch baseline tree required")
    git(scratch, "apply", "--index", "--check", "--whitespace=error-all", str(patch_path),
        git_environment=scratch_environment)
    git(scratch, "apply", "--index", "--whitespace=error-all", str(patch_path),
        git_environment=scratch_environment)
    for row in rows:
        relative = row["relative_path"]
        applied, _, applied_mode = read_regular(scratch / relative)
        need(applied == snapshots[relative][0] and not applied_mode & 0o111,
             "scratch application must match exact selected current bytes and Git executable mode")
        row["applied"] = pin(scratch / relative, applied)
    applied_paths = git(scratch, "ls-files", git_environment=scratch_environment).decode().splitlines()
    need(set(applied_paths) == set(PATHS) and len(applied_paths) == len(PATHS), "scratch application has unexpected paths")
    git(scratch, "diff", "--cached", "--check", scratch_baseline_tree, "--", *PATHS,
        git_environment=scratch_environment)
    git(scratch, "diff", "--check", git_environment=scratch_environment)
    for relative, (raw, witness, mode) in snapshots.items():
        current, after_signature, after_mode = read_regular(checkout / relative)
        need(current == raw and after_signature == witness and after_mode == mode,
             "AB selected source bytes or metadata changed while packaging")
    index_after, after_index_signature, _ = read_regular(source_index)
    head_after, after_head_signature, _ = read_regular(git_directory / "HEAD", maximum=4096)
    need(index_after == index_before and after_index_signature == index_signature,
         "AB source index changed while packaging")
    need(head_after == head_before and after_head_signature == head_signature
         and git(checkout, "rev-parse", "--verify", "HEAD").decode("ascii").strip() == head,
         "AB source HEAD changed while packaging")
    report = {"schema": SCHEMA, "qualified": True, "base_commit": head,
        "files": len(PATHS), "modified": len(MODIFIED), "new": len(NEW), "sources": rows,
        "patch": pin(patch_path, patch), "explicit_paths": list(PATHS),
        "exact_scratch_application": True, "scratch_baseline_paths": list(MODIFIED),
        "scratch_baseline_tree": scratch_baseline_tree,
        "scratch_change_whitespace_verified_against_explicit_baseline": True,
        "temporary_source_index_and_object_store": True,
        "source_index_unchanged": True, "source_index_pin": pin(source_index, index_before),
        "source_head_unchanged": True, "source_head_pin": pin(git_directory / "HEAD", head_before),
        "source_selected_bytes_unchanged": True, "source_git_objects_written": False,
        "git_executable_modes_match": True, "full_permission_bits_preserved_by_git_claimed": False,
        "production_promoted": False, "project_pushes": 0,
        "scope": "Six explicit runtime/test source changes over the AB local baseline; no runtime artifacts, credentials, database bodies or upstream writes."}
    raw_report = json.dumps(report, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"
    write_exclusive(report_path, raw_report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-name", default="review-package-01.json")
    arguments = parser.parse_args()
    os.umask(0o077)
    report = build_package(Path(__file__).resolve().parent, arguments.output_name)
    print(json.dumps({"qualified": report["qualified"], "files": report["files"],
        "patch": report["patch"], "report": arguments.output_name}, sort_keys=True))


if __name__ == "__main__":
    main()
