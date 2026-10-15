"""Bounded authored breadth qualification; no models or repository code execution."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import shutil
import stat
import time

from ipfs_accelerate_py.agent_supervisor.runtime.repository_source_view import (
    RepositoryViewError, create_repository_view, load_repository_view,
    restore_repository_view,
)


def tree(root):
    result = {"": {"kind": "directory", "mode": stat.S_IMODE(root.stat().st_mode)}}
    for path in sorted(root.rglob("*")):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            result[name] = {"kind": "symlink", "target": path.readlink().as_posix()}
        elif path.is_dir():
            result[name] = {"kind": "directory", "mode": stat.S_IMODE(path.stat().st_mode)}
        else:
            data = path.read_bytes()
            result[name] = {"kind": "file", "mode": stat.S_IMODE(path.stat().st_mode),
                            "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "stress")
    output = parser.parse_args().output
    output.mkdir(exist_ok=False)
    source = output / "source"
    source.mkdir()
    for index in range(1024):
        directory = source / f"module_{index // 64:02d}"
        directory.mkdir(exist_ok=True)
        if index % 2 == 0:
            raw = ("# Retained original explanatory comment.\n" * 40
                   + f"VALUE = {index}\ndef calculate(value):\n    return value + VALUE\n").encode()
            path = directory / f"file_{index:04d}.py"
        else:
            raw = bytes(range(256)) * 4
            path = directory / f"file_{index:04d}.bin"
        path.write_bytes(raw)
    (source / ".settings").write_bytes(b"mode=authored-fixture\n")
    (source / "empty").mkdir()
    (source / "entry.py").symlink_to("module_00/file_0000.py")
    before = tree(source)
    started = time.monotonic()
    receipt = create_repository_view(source, output / "package")
    capture_seconds = time.monotonic() - started
    digest = receipt["manifest_sha256"]
    manifest = load_repository_view(output / "package", expected_manifest_sha256=digest)
    limit_rejected = None
    try:
        create_repository_view(source, output / "refused-package", max_files=128)
    except RepositoryViewError as error:
        limit_rejected = error.code
    shutil.rmtree(source)
    started = time.monotonic()
    restored = output / "restored"
    restore = restore_repository_view(output / "package", restored, expected_manifest_sha256=digest)
    restore_seconds = time.monotonic() - started
    exact = tree(restored) == before
    compact = output / "compact"
    restore_repository_view(output / "package", compact, expected_manifest_sha256=digest, representation="compact")
    compact_exact = all(hashlib.sha256((compact / path).read_bytes()).hexdigest() == entry["compact_sha256"]
        for path, entry in manifest["entries"].items() if entry["kind"] == "file")
    result = {"schema": "repository-source-view-breadth-qualification@1",
        "authored_only": True, "provider_calls": 0, "containers_started": 0,
        "capture": receipt, "restore": restore,
        "source_removed_before_restore": not source.exists(),
        "original_tree_exact": exact, "compact_files_match_manifest": compact_exact,
        "entry_limit_error": limit_rejected,
        "limit_rejection_published_no_package": not (output / "refused-package").exists(),
        "capture_seconds": capture_seconds, "restore_seconds": restore_seconds,
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "qualified": exact and compact_exact and limit_rejected == "entry_limit"
            and not (output / "refused-package").exists()}
    (output / "qualification.json").write_text(json.dumps(result, indent=2) + "\n")
    shutil.rmtree(restored)
    shutil.rmtree(compact)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["qualified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
