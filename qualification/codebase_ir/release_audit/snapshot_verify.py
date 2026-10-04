"""Pure bounded verification of a sealed runtime-demand generation."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


class SnapshotError(ValueError):
    pass


def _sha(value: object) -> bool:
    return type(value) is str and re.fullmatch("[0-9a-f]{64}", value) is not None


def _canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode()


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotError("duplicate snapshot JSON key")
        result[key] = value
    return result


def _bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise SnapshotError("snapshot file type or byte bound refused")
    with path.open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise SnapshotError("snapshot file grew beyond byte bound")
    return raw


def _relative(value: object) -> Path:
    if type(value) is not str:
        raise SnapshotError("snapshot relative path must be text")
    path = Path(value)
    if (path.is_absolute() or not path.parts or len(path.parts) > 32 or path.as_posix() != value
            or any(part.startswith(".") or part in {"state", "workspace", "artifacts", "__pycache__"}
                   for part in path.parts) or not path.parts[0].isidentifier()):
        raise SnapshotError("snapshot relative path outside package ownership")
    return path


def verify_snapshot(
    root: Path,
    expected_sha256: str,
    *,
    expected_roots: list[Path] | None = None,
    max_files: int = 512,
    max_bytes: int = 16777216,
    max_file_bytes: int = 2097152,
) -> dict:
    """Bind exact bytes/file set and canonical import roots to one generation hash."""
    if (root.resolve() != root or not root.is_dir() or not _sha(expected_sha256)
            or any(type(limit) is not int or limit <= 0 for limit in (max_files, max_bytes, max_file_bytes))):
        raise SnapshotError("canonical snapshot root, SHA256 and positive exact bounds required")
    manifest_path = root / "snapshot.json"
    raw = _bounded(manifest_path, 1048576)
    try:
        manifest = json.loads(raw, object_pairs_hook=_unique_pairs)
    except json.JSONDecodeError as exc:
        raise SnapshotError("invalid snapshot JSON") from exc
    fields = {"schema", "generation", "parent_snapshot_sha256", "files", "namespace_directories", "snapshot_sha256"}
    if (type(manifest) is not dict or set(manifest) != fields
            or manifest["schema"] != "codebase-ir-runtime-demand/v1"
            or type(manifest["generation"]) is not int or manifest["generation"] < 0
            or manifest["snapshot_sha256"] != expected_sha256
            or (manifest["parent_snapshot_sha256"] is not None and not _sha(manifest["parent_snapshot_sha256"]))
            or type(manifest["files"]) is not list or len(manifest["files"]) > max_files
            or type(manifest["namespace_directories"]) is not list
            or len(manifest["namespace_directories"]) > max_files):
        raise SnapshotError("invalid snapshot manifest schema, identity or bounds")
    body = {key: value for key, value in manifest.items() if key != "snapshot_sha256"}
    if hashlib.sha256(_canonical(body)).hexdigest() != expected_sha256:
        raise SnapshotError("snapshot canonical manifest identity differs")
    roots = sorted(path for path in root.iterdir() if path.is_dir())
    if (not roots or any(path.is_symlink() or path.resolve() != path or not path.name.isidentifier() for path in roots)
            or expected_roots is not None and set(roots) != set(expected_roots)):
        raise SnapshotError("snapshot repository import roots differ")
    repositories = {path.name for path in roots}
    expected, bytes_read = set(), 0
    for row in manifest["files"]:
        if (type(row) is not dict or set(row) != {"repository", "path", "sha256", "bytes"}
                or type(row["repository"]) is not str or row["repository"] not in repositories
                or type(row["bytes"]) is not int or not 0 <= row["bytes"] <= max_file_bytes
                or not _sha(row["sha256"])):
            raise SnapshotError("invalid snapshot file pin")
        relative = _relative(row["path"])
        path = root / row["repository"] / relative
        if path.resolve() != path or path in expected:
            raise SnapshotError("snapshot path alias or duplicate file refused")
        expected.add(path)
        bytes_read += row["bytes"]
        if bytes_read > max_bytes:
            raise SnapshotError("snapshot aggregate byte bound refused")
        data = _bounded(path, row["bytes"])
        if len(data) != row["bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise SnapshotError("snapshot source bytes differ from exact pin")
    namespaces = set()
    for row in manifest["namespace_directories"]:
        if (type(row) is not dict or set(row) != {"repository", "path"}
                or type(row["repository"]) is not str or row["repository"] not in repositories):
            raise SnapshotError("invalid snapshot namespace directory")
        path = root / row["repository"] / _relative(row["path"])
        if not path.is_dir() or path.resolve() != path or path in namespaces:
            raise SnapshotError("snapshot namespace directory missing or aliased")
        namespaces.add(path)
    actual = set()
    directories = {root, *roots}
    for path in expected | namespaces:
        directories.update(parent for parent in path.parents if parent.is_relative_to(root))
        if path in namespaces:
            directories.add(path)
    for path in root.rglob("*"):
        if path.is_symlink() or path.stat().st_mode & 0o222:
            raise SnapshotError("snapshot generation is not sealed read-only")
        if not path.is_file() and not path.is_dir():
            raise SnapshotError("snapshot contains non-regular filesystem entry")
        if path.is_dir() and path not in directories:
            raise SnapshotError("unexpected snapshot directory")
        if path.is_file() and path != manifest_path:
            if path not in expected:
                raise SnapshotError("unexpected snapshot file")
            actual.add(path)
    if actual != expected or root.stat().st_mode & 0o222:
        raise SnapshotError("snapshot exact file set or root seal differs")
    return {"schema": "codebase-ir-snapshot-verification/v1", "snapshot_root": str(root),
            "snapshot_sha256": expected_sha256, "snapshot_manifest_sha256": hashlib.sha256(raw).hexdigest(),
            "generation": manifest["generation"], "snapshot_roots": [str(path) for path in roots],
            "files": manifest["files"], "namespace_directories": manifest["namespace_directories"],
            "file_count": len(expected), "bytes": bytes_read, "verified": True}
