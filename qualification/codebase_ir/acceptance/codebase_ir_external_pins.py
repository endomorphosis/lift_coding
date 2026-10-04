"""Bounded byte pins for explicitly nominated interpreter dependency files.

Reading these files does not import or execute them. A manifest is an observed
file inventory, never an attestation or a transitive runtime-closure claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import sysconfig
from pathlib import Path
from typing import Any

SCHEMA = "codebase-ir-external-dependency-manifest@1"
MAX_FILES = 1024
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024
DIGEST = re.compile(r"[0-9a-f]{64}\Z")


def interpreter_site_roots() -> list[Path]:
    prefix = Path(sys.prefix).resolve(strict=True)
    roots = sorted({Path(sysconfig.get_path(name)).resolve(strict=True) for name in ("purelib", "platlib")})
    if any(not root.is_relative_to(prefix) or root.name not in {"site-packages", "dist-packages"} for root in roots):
        raise ValueError("current interpreter site-package roots must be inside its prefix")
    return roots


def _exact_digest(value: Any) -> bool:
    return type(value) is str and DIGEST.fullmatch(value) is not None


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key in external dependency input")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise ValueError("nonfinite JSON value in external dependency input: " + value)


def _bounded_document(path: Path, limit: int) -> bytes:
    if path.is_symlink():
        raise ValueError("bounded regular external dependency input required")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("bounded regular external dependency input required")
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
        if len(raw) > limit:
            raise ValueError("external dependency input exceeds byte cap")
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise ValueError("external dependency input changed during bounded read")
        return raw


def _parse_document(raw: bytes) -> Any:
    return json.loads(raw, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)


def read_file_pin(path: Path, *, roots: list[Path], expected: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read one exact canonical regular file, refusing aliases and byte drift."""
    if (not path.is_absolute() or not any(path.is_relative_to(root) for root in roots)
            or path.resolve(strict=True) != path or any(part.is_symlink() for part in (path, *path.parents))):
        raise ValueError("dependency file has foreign, noncanonical or symlink path")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ValueError("dependency must be an exact regular file")
        if before.st_size > MAX_FILE_BYTES:
            raise ValueError("dependency exceeds per-file byte cap")
        digest, count = hashlib.sha256(), 0
        while block := os.read(descriptor, 1024 * 1024):
            count += len(block)
            if count > MAX_FILE_BYTES:
                raise ValueError("dependency exceeds per-file byte cap")
            digest.update(block)
        after = os.fstat(descriptor)
        if ((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
                != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
                or count != before.st_size):
            raise ValueError("dependency changed during bounded read")
        pin = {"sha256": digest.hexdigest(), "size_bytes": count}
        if expected is not None and pin != expected:
            raise ValueError("dependency manifest digest or size drift")
        return pin
    finally:
        os.close(descriptor)


def validate_manifest(document: Any, *, roots: list[Path]) -> dict[str, dict[str, Any]]:
    if (type(document) is not dict or set(document) != {"schema", "site_packages_roots", "source_report_sha256", "files"}
            or document["schema"] != SCHEMA or not _exact_digest(document["source_report_sha256"])
            or document["site_packages_roots"] != [str(root) for root in roots]):
        raise ValueError("external manifest schema or interpreter site roots differ")
    rows = document["files"]
    if type(rows) is not list or not rows or len(rows) > MAX_FILES:
        raise ValueError("external manifest file count is outside bounded profile")
    pins, total = {}, 0
    for row in rows:
        if (type(row) is not dict or set(row) != {"path", "sha256", "size_bytes"}
                or type(row["path"]) is not str or not _exact_digest(row["sha256"])
                or type(row["size_bytes"]) is not int or row["size_bytes"] < 0
                or row["size_bytes"] > MAX_FILE_BYTES):
            raise ValueError("external manifest file fields or types differ")
        path = Path(row["path"])
        if str(path) != row["path"] or row["path"] in pins:
            raise ValueError("duplicate or noncanonical dependency spelling")
        total += row["size_bytes"]
        if total > MAX_TOTAL_BYTES:
            raise ValueError("external manifest exceeds total byte cap")
        expected = {key: row[key] for key in ("sha256", "size_bytes")}
        pins[row["path"]] = read_file_pin(path, roots=roots, expected=expected)
    return pins


def capture_external_manifest(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    raw = _bounded_document(path, MAX_MANIFEST_BYTES)
    roots = interpreter_site_roots()
    pins = validate_manifest(_parse_document(raw), roots=roots)
    return pins, {"manifest_path": str(path.resolve()), "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "schema": SCHEMA, "site_packages_roots": [str(root) for root in roots],
        "file_count": len(pins), "total_bytes": sum(pin["size_bytes"] for pin in pins.values()),
        "max_files": MAX_FILES, "max_file_bytes": MAX_FILE_BYTES, "max_total_bytes": MAX_TOTAL_BYTES,
        "scope": "explicit_observed_files_only", "imports_performed": False, "runtime_closure_proven": False}


def compare_external_pins(before: dict[str, dict[str, Any]], following: dict[str, dict[str, Any]], *, roots: list[Path]) -> list[dict[str, Any]]:
    if len(following) > MAX_FILES:
        raise ValueError("loaded external dependency file count exceeds bounded profile")
    rows, total = [], 0
    for path, following_pin in sorted(following.items()):
        pin = read_file_pin(Path(path), roots=roots)
        total += pin["size_bytes"]
        if total > MAX_TOTAL_BYTES:
            raise ValueError("loaded external dependencies exceed total byte cap")
        if any(following_pin.get(key) != pin[key] for key in pin):
            raise ValueError("loaded external dependency changed during post-read")
        prior = before.get(path)
        unchanged = prior is not None and all(prior.get(key) == pin[key] for key in pin)
        rows.append({"path": path, "before": prior, "after": following_pin,
            "unchanged": unchanged, "late_import": prior is None})
        if prior is not None and not unchanged:
            raise ValueError("pre-pinned external dependency bytes changed during run")
    return rows


def manifest_from_report(report_path: Path, output: Path) -> dict[str, Any]:
    if output.exists():
        raise ValueError("external manifest output must be fresh")
    raw = _bounded_document(report_path, MAX_REPORT_BYTES)
    report = _parse_document(raw)
    if (type(report) is not dict or report.get("schema") != "codebase-ir-finite-planning-qualification@1"
            or report.get("status") != "passed" or type(report.get("external_dependency_pins")) is not list):
        raise ValueError("successful observed planning report required")
    roots = interpreter_site_roots()
    rows = []
    for observed in report["external_dependency_pins"]:
        if type(observed) is not dict or type(observed.get("after")) is not dict:
            raise ValueError("source report external file observation fields differ")
        after = observed.get("after", {})
        rows.append({"path": observed.get("path"), "sha256": after.get("sha256"), "size_bytes": after.get("size_bytes")})
    document = {"schema": SCHEMA, "source_report_sha256": hashlib.sha256(raw).hexdigest(),
        "site_packages_roots": [str(root) for root in roots], "files": sorted(rows, key=lambda row: row["path"])}
    validate_manifest(document, roots=roots)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(document, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    if len(encoded) > MAX_MANIFEST_BYTES:
        raise ValueError("generated external manifest exceeds byte cap")
    with output.open("xb") as stream:
        stream.write(encoded)
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        document = manifest_from_report(args.from_report, args.output)
    except (ValueError, OSError, TypeError) as exc:
        parser.exit(2, f"external manifest refused: {exc}\n")
    print(json.dumps({"manifest": str(args.output.resolve()), "file_count": len(document["files"]),
        "imports_performed": False, "runtime_closure_proven": False}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
