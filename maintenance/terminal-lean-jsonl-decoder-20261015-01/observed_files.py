"""Bounded observations of four explicitly authored JSONL artifact files.

Serialized observations are historical evidence, never a capability or a claim
that the described files still exist.  ``reobserve_bundle`` performs the live
check.  No repository traversal, credential discovery, or file execution occurs.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import stat


MAX_FILE_BYTES = 65_536
FILE_PATHS = (
    "input_data/requests_bucket_1.jsonl",
    "input_data/requests_bucket_2.jsonl",
    "output_data/plan_b1.jsonl",
    "output_data/plan_b2.jsonl",
)
INPUT_PATHS = FILE_PATHS[:2]
OUTPUT_PATHS = FILE_PATHS[2:]
DIRECTORY_PATHS = ("input_data", "output_data")
OBSERVATION_SCHEMA = "terminal-owned-jsonl-file-observation@1"
COMPARISON_SCHEMA = "terminal-owned-jsonl-file-comparison@1"
IDENTITY_FIELDS = (
    "device", "inode", "mode", "uid", "gid", "nlink", "size",
    "mtime_ns", "ctime_ns",
)
_CLAIMS = {
    "historical_byte_observation": True,
    "current_authority": False,
    "execution_receipt": False,
    "formal_proof": False,
    "task_satisfaction": False,
}


class ObservationError(ValueError):
    """A bounded artifact observation or evidence comparison was refused."""


def _wire(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _root_name(root: Path | str) -> str:
    if not isinstance(root, (Path, str)):
        raise ObservationError("root must be an explicit absolute path")
    name = os.fspath(root)
    if (not name or "\x00" in name or not name.startswith("/")
            or name.startswith("//") or name == "/"
            or os.path.normpath(name) != name
            or ".." in name.split("/")):
        raise ObservationError("root must be a canonical absolute non-root path")
    return name


def _identity(value: os.stat_result) -> dict:
    return {
        "device": value.st_dev, "inode": value.st_ino,
        "mode": value.st_mode, "uid": value.st_uid, "gid": value.st_gid,
        "nlink": value.st_nlink, "size": value.st_size,
        "mtime_ns": value.st_mtime_ns, "ctime_ns": value.st_ctime_ns,
    }


def _owned_directory(value: os.stat_result) -> None:
    if not stat.S_ISDIR(value.st_mode) or value.st_uid != os.geteuid():
        raise ObservationError("artifact directories must be user-owned directories")


def _owned_file(value: os.stat_result) -> None:
    if not stat.S_ISREG(value.st_mode):
        raise ObservationError("artifact must be a regular file")
    if value.st_uid != os.geteuid() or value.st_nlink != 1:
        raise ObservationError("artifact must be user-owned with exactly one link")
    if not 0 <= value.st_size <= MAX_FILE_BYTES:
        raise ObservationError("artifact exceeds the byte bound")


def _same_named_descriptor(parent: int, name: str, fd: int, expected: dict,
                           *, full: bool = True) -> None:
    current = _identity(os.fstat(fd))
    named = _identity(os.stat(name, dir_fd=parent, follow_symlinks=False))
    fields = IDENTITY_FIELDS if full else ("device", "inode", "mode", "uid", "gid")
    if any(current[key] != expected[key] or named[key] != expected[key]
           for key in fields):
        raise ObservationError("artifact generation changed during observation")


def _open_directory(parent: int, name: str) -> tuple[int, dict]:
    before = os.stat(name, dir_fd=parent, follow_symlinks=False)
    if not stat.S_ISDIR(before.st_mode):
        raise ObservationError("symlink or non-directory path component refused")
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                 dir_fd=parent)
    try:
        expected = _identity(before)
        _same_named_descriptor(parent, name, fd, expected)
        return fd, expected
    except BaseException:
        os.close(fd)
        raise


def _inventory(fd: int, expected: tuple[str, ...]) -> None:
    if set(os.listdir(fd)) != set(expected):
        raise ObservationError("artifact directory has a missing or unknown leaf")


def _read_bytes(fd: int) -> bytes:
    """Read at most the declared global bound plus one overflow byte."""
    chunks = []
    remaining = MAX_FILE_BYTES + 1
    while remaining:
        block = os.read(fd, min(16_384, remaining))
        if not block:
            break
        chunks.append(block)
        remaining -= len(block)
    raw = b"".join(chunks)
    if len(raw) > MAX_FILE_BYTES:
        raise ObservationError("artifact grew beyond the byte bound")
    return raw


def observe_bundle(*, root: Path) -> dict:
    """Read exactly four owned artifacts with descriptor and generation guards.

    Every path component is opened relative to its parent without following
    symlinks.  All four descriptors remain open until the final guard; their
    named entries, metadata, directory inventory, and owned root are rechecked.
    UTF-8 is deliberately not required here: rejected parser inputs must retain
    their exact bytes too.
    """
    name = _root_name(root)
    descriptors: list[int] = []
    ancestry = []
    try:
        fd = os.open("/", os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        descriptors.append(fd)
        for component in name[1:].split("/"):
            child, identity = _open_directory(fd, component)
            descriptors.append(child)
            ancestry.append((fd, component, child, identity))
            fd = child
        root_fd = fd
        root_identity = _identity(os.fstat(root_fd))
        _owned_directory(os.fstat(root_fd))
        _inventory(root_fd, DIRECTORY_PATHS)
        directories = {}
        directory_handles = {}
        for directory in DIRECTORY_PATHS:
            child, identity = _open_directory(root_fd, directory)
            descriptors.append(child)
            _owned_directory(os.fstat(child))
            directories[directory] = identity
            directory_handles[directory] = child
            expected_names = tuple(path.split("/")[1] for path in FILE_PATHS
                                   if path.startswith(directory + "/"))
            _inventory(child, expected_names)
        files = {}
        open_files = []
        for path in FILE_PATHS:
            directory, leaf = path.split("/")
            parent = directory_handles[directory]
            before = os.stat(leaf, dir_fd=parent, follow_symlinks=False)
            _owned_file(before)
            expected = _identity(before)
            child = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
                            | os.O_NONBLOCK, dir_fd=parent)
            descriptors.append(child)
            _owned_file(os.fstat(child))
            _same_named_descriptor(parent, leaf, child, expected)
            raw = _read_bytes(child)
            if len(raw) != expected["size"]:
                raise ObservationError("artifact size disagrees with bytes read")
            _same_named_descriptor(parent, leaf, child, expected)
            open_files.append((parent, leaf, child, expected))
            files[path] = {
                "payload_b64": base64.b64encode(raw).decode("ascii"),
                "sha256": _sha(raw), "bytes": len(raw), "identity": expected,
            }
        for parent, leaf, child, expected in open_files:
            _owned_file(os.fstat(child))
            _same_named_descriptor(parent, leaf, child, expected)
        for directory in DIRECTORY_PATHS:
            child = directory_handles[directory]
            expected_names = tuple(path.split("/")[1] for path in FILE_PATHS
                                   if path.startswith(directory + "/"))
            _inventory(child, expected_names)
            _same_named_descriptor(root_fd, directory, child, directories[directory])
        _inventory(root_fd, DIRECTORY_PATHS)
        for parent, component, child, expected in ancestry:
            # Ancestors may legitimately have unrelated directory activity;
            # retained named identity still prohibits path redirection.
            _same_named_descriptor(parent, component, child, expected,
                                   full=(child == root_fd))
        if _identity(os.fstat(root_fd)) != root_identity:
            raise ObservationError("owned root generation changed")
        report = {
            "schema": OBSERVATION_SCHEMA, "root": name,
            "observer": {"pid": os.getpid(), "uid": os.geteuid()},
            "root_identity": root_identity, "directories": directories,
            "files": files, "claims": dict(_CLAIMS),
        }
        validate_bundle(report)
        return report
    except ObservationError:
        raise
    except OSError as exc:
        raise ObservationError("bounded artifact observation failed") from exc
    finally:
        for descriptor in reversed(descriptors):
            os.close(descriptor)


def _keys(value: object, names: tuple[str, ...] | set[str], label: str) -> dict:
    if type(value) is not dict or set(value) != set(names):
        raise ObservationError(f"invalid {label} fields")
    return value


def _plain_int(value: object, *, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _validate_identity(value: object, *, directory: bool) -> dict:
    result = _keys(value, IDENTITY_FIELDS, "identity")
    if any(not _plain_int(result[key]) for key in IDENTITY_FIELDS):
        raise ObservationError("invalid identity integer")
    if not result["inode"] or not result["nlink"]:
        raise ObservationError("invalid zero identity")
    is_kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not is_kind(result["mode"]):
        raise ObservationError("identity has wrong file type")
    if not directory and (result["nlink"] != 1 or result["size"] > MAX_FILE_BYTES):
        raise ObservationError("invalid bounded regular-file identity")
    return result


def _decode_record(record: dict) -> bytes:
    encoded = record["payload_b64"]
    if type(encoded) is not str or len(encoded) > ((MAX_FILE_BYTES + 2) // 3) * 4:
        raise ObservationError("invalid bounded base64 payload")
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ObservationError("invalid base64 payload") from exc
    if base64.b64encode(raw).decode("ascii") != encoded:
        raise ObservationError("base64 payload is not canonical")
    return raw


def validate_bundle(report: dict) -> None:
    """Validate serialized evidence only; this performs no current-file check."""
    _keys(report, ("schema", "root", "observer", "root_identity", "directories",
                   "files", "claims"), "observation")
    if report["schema"] != OBSERVATION_SCHEMA or type(report["schema"]) is not str:
        raise ObservationError("unknown observation schema")
    if type(report["root"]) is not str:
        raise ObservationError("historical root must be a JSON string")
    _root_name(report["root"])
    observer = _keys(report["observer"], ("pid", "uid"), "observer")
    if not _plain_int(observer["pid"], minimum=1) or not _plain_int(observer["uid"]):
        raise ObservationError("invalid historical observer")
    root_identity = _validate_identity(report["root_identity"], directory=True)
    if root_identity["uid"] != observer["uid"]:
        raise ObservationError("root is not owned by recorded observer")
    directories = _keys(report["directories"], DIRECTORY_PATHS, "directories")
    for directory in DIRECTORY_PATHS:
        identity = _validate_identity(directories[directory], directory=True)
        if identity["uid"] != observer["uid"]:
            raise ObservationError("directory is not owned by recorded observer")
    files = _keys(report["files"], FILE_PATHS, "files")
    for path in FILE_PATHS:
        record = _keys(files[path], ("payload_b64", "sha256", "bytes", "identity"),
                       "file")
        identity = _validate_identity(record["identity"], directory=False)
        if identity["uid"] != observer["uid"]:
            raise ObservationError("file is not owned by recorded observer")
        raw = _decode_record(record)
        if (not _plain_int(record["bytes"]) or record["bytes"] != len(raw)
                or record["bytes"] != identity["size"] or len(raw) > MAX_FILE_BYTES
                or type(record["sha256"]) is not str
                or record["sha256"] != _sha(raw)):
            raise ObservationError("retained artifact byte binding is invalid")
    claims = _keys(report["claims"], set(_CLAIMS), "claims")
    if any(type(claims[key]) is not bool or claims[key] != expected
           for key, expected in _CLAIMS.items()):
        raise ObservationError("observation authority claims are invalid")


def decode_file(report: dict, path: str) -> bytes:
    """Return one exact retained body after validating evidence, not the disk."""
    validate_bundle(report)
    if type(path) is not str or path not in FILE_PATHS:
        raise ObservationError("path is outside the four-file contract")
    return _decode_record(report["files"][path])


def compare_bundles(before: dict, after: dict) -> dict:
    """Compare all four historical records, preserving byte/custody distinctions."""
    validate_bundle(before)
    validate_bundle(after)
    roots_equal = (before["root"] == after["root"]
                   and before["root_identity"] == after["root_identity"])
    directories_equal = before["directories"] == after["directories"]
    files = {}
    for path in FILE_PATHS:
        left, right = before["files"][path], after["files"][path]
        equal_bytes = _decode_record(left) == _decode_record(right)
        equal_identity = left["identity"] == right["identity"]
        files[path] = {"bytes_equal": equal_bytes, "identity_equal": equal_identity,
                       "same_file_generation": equal_bytes and equal_identity}
    inputs_equal = all(files[path]["bytes_equal"] for path in INPUT_PATHS)
    input_custody = (roots_equal and before["directories"]["input_data"]
                     == after["directories"]["input_data"])
    return {
        "schema": COMPARISON_SCHEMA,
        "before_sha256": _sha(_wire(before)), "after_sha256": _sha(_wire(after)),
        "roots_equal": roots_equal, "directory_generations_equal": directories_equal,
        "inputs_bytes_equal": inputs_equal,
        "unchanged_inputs": (input_custody and all(
            files[path]["same_file_generation"] for path in INPUT_PATHS)),
        "same_file_generations": (roots_equal and directories_equal and all(
            files[path]["same_file_generation"] for path in FILE_PATHS)),
        "files": files, "claims": dict(_CLAIMS),
    }


def reobserve_bundle(expected: dict, *, root: Path) -> dict:
    """Actually reread the owned root and require every recorded generation.

    Returning a fresh observation means the comparison succeeded during this
    call.  It creates no expiry, grant, worker permission, or future authority.
    """
    validate_bundle(expected)
    if _root_name(root) != expected["root"]:
        raise ObservationError("reobservation root differs from recorded root")
    current = observe_bundle(root=root)
    comparison = compare_bundles(expected, current)
    if not comparison["same_file_generations"]:
        raise ObservationError("current artifact generation differs from evidence")
    return current
