"""Bounded SHA256 integrity seal over an explicit owned public-file allowlist.

This is storage integrity, not admission, proof, training-origin authentication,
loaded-code attestation, source equivalence or task completion authority.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat

MAX_FILES = 4096
MAX_FILE_BYTES = 256 * 1024**2
MAX_TOTAL_BYTES = 2 * 1024**3
MAX_JSON_BYTES = 8 * 1024**2


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode()


def read(path, maximum):
    path = Path(path)
    if not path.is_absolute() or path.resolve(strict=True) != path:
        raise ValueError("canonical regular input required")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError("bounded single-link regular file required")
        body = stream.read(maximum + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns, item.st_mode, item.st_nlink)
    if len(body) > maximum or identity(before) != identity(after) or identity(after) != identity(current):
        raise ValueError("file changed or grew during seal acquisition")
    return body, stat.S_IMODE(before.st_mode)


def loads(body):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field")
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError("nonfinite JSON")
    return json.loads(body, object_pairs_hook=unique, parse_constant=nonfinite)


def selection(config):
    if config.get("schema") != "terminal-codebase-ir-evidence-selection@1":
        raise ValueError("explicit public-file selection required")
    root = Path(config["root"])
    if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError("canonical existing owned root required")
    paths = config["files"]
    if not isinstance(paths, list) or not 1 <= len(paths) <= MAX_FILES or len(set(paths)) != len(paths):
        raise ValueError("bounded unique explicit file list required")
    for value in paths:
        if not isinstance(value, str):
            raise ValueError("relative file name required")
        path = PurePosixPath(value)
        if path.is_absolute() or str(path) != value or any(part in {".", "..", ".git"} for part in path.parts):
            raise ValueError("file outside owned selection")
    return root, sorted(paths)


def collect(config):
    root, paths = selection(config)
    rows, total = [], 0
    for name in paths:
        body, mode = read(root / name, MAX_FILE_BYTES)
        total += len(body)
        if total > MAX_TOTAL_BYTES:
            raise ValueError("total seal byte bound exceeded")
        rows.append({"path": name, "bytes": len(body), "mode": mode,
                     "sha256": hashlib.sha256(body).hexdigest()})
    return {"schema": "terminal-codebase-ir-evidence-integrity-seal@1", "root": str(root),
        "files": rows, "file_count": len(rows), "total_bytes": total,
        "file_set_sha256": hashlib.sha256(wire(rows)).hexdigest(),
        "scope": "explicit_public_artifact_storage_integrity_only",
        "authenticated_training_origin": False, "complete_transitive_loaded_code_closure": False,
        "source_model_equivalence_proved": False, "asymptotic_optimizer_convergence_proved": False,
        "full_task_satisfaction": False, "proof_authority": False}


def seal(config, target, *, verify=False):
    first = collect(config)
    if collect(config) != first:
        raise ValueError("selected file set changed between complete passes")
    if verify:
        body, _ = read(target, MAX_JSON_BYTES)
        if loads(body) != first:
            raise ValueError("retained seal differs from current selected files")
    else:
        body = wire(first)
        if len(body) > MAX_JSON_BYTES:
            raise ValueError("seal JSON bound exceeded")
        with Path(target).open("xb") as stream:
            stream.write(body)
            stream.flush()
            os.fchmod(stream.fileno(), 0o444)
            os.fsync(stream.fileno())
    return first


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    body, _ = read(args.config.absolute(), MAX_JSON_BYTES)
    result = seal(loads(body), args.manifest.absolute(), verify=args.verify)
    print(json.dumps({"verified": args.verify, "file_count": result["file_count"],
        "bytes": result["total_bytes"], "file_set_sha256": result["file_set_sha256"],
        "scope": result["scope"]}))


if __name__ == "__main__":
    main()
