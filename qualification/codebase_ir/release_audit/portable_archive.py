#!/usr/bin/env python3
"""Deterministic bounded ZIP transport for an explicitly selected review capsule."""

from __future__ import annotations

import argparse
import stat
import struct
import sys
import time
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import portable_review as portable
import release_matrix as matrix

BUILD_INPUT_SCHEMA = "codebase-ir-portable-release-archive-build-input@1"
INPUT_SCHEMA = "codebase-ir-portable-release-archive-input@1"
REPORT_SCHEMA = "codebase-ir-portable-release-archive-verification@1"
BUILD_REPORT_SCHEMA = "codebase-ir-portable-release-archive-build@1"
MAX_MANIFEST_BYTES = 256 * 1024
MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = portable.MAX_FILES + portable.MAX_DIRECTORIES
MAX_CENTRAL_BYTES = MAX_ENTRIES * (46 + 1025)
LOCAL = struct.Struct("<4s5H3I2H")
CENTRAL = struct.Struct("<4s6H3I5H2I")
END = struct.Struct("<4s4H2IH")
FALSE_FLAGS = (*matrix.FALSE_FLAGS, "git_executable_invoked", "original_paths_read",
               "runtime_environment_qualified", "runtime_dependency_closure_qualified",
               "network_access_performed")


def name(value: object, *, directory: bool = False) -> str:
    matrix.need(type(value) is str and (not directory or value.endswith("/")), "exact archive member name required")
    relative = value[:-1] if directory else value
    matrix.relative(relative)
    matrix.need(not any(char in relative for char in ("\\", ":"))
                and all(ord(char) >= 32 and ord(char) != 127 for char in relative)
                and len(value.encode("utf-8")) <= 1025,
                "archive path control/platform alias refused")
    return value


class PinnedReader:
    """Two selected files at most; raw archive and equal-size stable reread bounded separately."""
    def __init__(self):
        self.rows = {}
        self.started = time.monotonic()

    def check_time(self):
        matrix.need(time.monotonic() - self.started <= matrix.MAX_SECONDS, "archive operation wall-time ceiling reached")

    def read(self, path: Path, limit: int, expected_sha: str | None = None, expected_size: int | None = None) -> bytes:
        self.check_time()
        matrix.canonical(str(path))
        if expected_sha is not None:
            matrix.need(matrix.exact_hex(expected_sha) and type(expected_size) is int
                        and 0 <= expected_size <= limit, "exact archive raw digest/size pin required")
        raw = matrix.Capture().read_body(path, limit)
        matrix.need(expected_sha is None or matrix.sha(raw) == expected_sha and len(raw) == expected_size,
                    "archive input raw digest/size differs")
        matrix.need(path in self.rows or len(self.rows) < 2, "archive input file-count ceiling reached")
        matrix.need(path not in self.rows or self.rows[path][0] == raw, "archive input changed between reads")
        self.rows[path] = raw, limit
        return raw

    def stability(self) -> dict:
        rows = []
        for path, (raw, _limit) in self.rows.items():
            self.check_time()
            after = matrix.Capture().read_body(path, len(raw))
            matrix.need(after == raw, "archive input drifted during verification")
            rows.append({"path": str(path), "sha256": matrix.sha(raw), "size_bytes": len(raw), "unchanged": True})
        return {"unchanged": True, "files": rows,
                "scope": "exact sequential bounded rereads; no atomic capture or producer authentication claim"}


def descriptor(value: object) -> dict:
    matrix.fields(value, {"path", "sha256", "size_bytes"}, "archive descriptor")
    matrix.need(matrix.exact_hex(value["sha256"]) and type(value["size_bytes"]) is int
                and 0 <= value["size_bytes"] <= MAX_ARCHIVE_BYTES, "exact bounded archive descriptor required")
    matrix.canonical(value["path"])
    return value


def fresh(output: Path, protected: list[Path]) -> None:
    portable.fresh(output, protected)
    matrix.need(output.parent.stat().st_mode & 0o222, "fresh archive output cannot descend from a sealed directory")


def inventory(raw: bytes, digest: str) -> tuple[dict, dict[str, dict], set[str]]:
    matrix.need(matrix.exact_hex(digest) and matrix.sha(raw) == digest and len(raw) <= 1024 * 1024,
                "raw bundle manifest digest/byte ceiling differs")
    bundle = matrix.document(raw)
    matrix.need(bundle.get("schema") == portable.BUNDLE_SCHEMA
                and bundle.get("manifest_filename") == portable.MANIFEST_FILENAME,
                "selected portable review bundle schema required")
    files, directories = bundle.get("files"), bundle.get("directories")
    matrix.need(type(files) is list and len(files) < portable.MAX_FILES
                and type(directories) is list and len(directories) <= portable.MAX_DIRECTORIES,
                "bundle declared file/directory budget reached before member processing")
    selected = {portable.MANIFEST_FILENAME: {"path": portable.MANIFEST_FILENAME,
                "sha256": digest, "size_bytes": len(raw)}}
    total = len(raw)
    for row in files:
        matrix.fields(row, {"path", "sha256", "size_bytes"}, "selected bundle file")
        relative = name(row["path"])
        matrix.need(relative not in selected and matrix.exact_hex(row["sha256"])
                    and type(row["size_bytes"]) is int and 0 <= row["size_bytes"] <= matrix.MAX_FILE_BYTES,
                    "selected bundle duplicate/digest/body ceiling refused")
        total += row["size_bytes"]
        matrix.need(total <= portable.MAX_BYTES, "bundle aggregate body budget reached")
        selected[relative] = row
    dirs = set()
    for relative in directories:
        name(relative + "/" if type(relative) is str else relative, directory=True)
        matrix.need(relative not in dirs and relative not in selected, "duplicate/file-alias bundle directory refused")
        dirs.add(relative)
    matrix.need(all(parent.as_posix() in dirs for value in selected | {value: None for value in dirs}
                    for parent in Path(value).parents if parent != Path(".")), "declared bundle parent directory missing")
    return bundle, selected, dirs


def exact_seals(root: Path, selected: dict, directories: set[str], reader: portable.BundleReader) -> None:
    portable.population(root, set(selected), directories, reader)
    matrix.need(stat.S_IMODE(root.stat(follow_symlinks=False).st_mode) == 0o555, "exact bundle root seal required")
    for relative, mode in [(value, 0o444) for value in selected] + [(value, 0o555) for value in directories]:
        reader.time_check()
        matrix.need(stat.S_IMODE((root / relative).stat(follow_symlinks=False).st_mode) == mode,
                    "exact selected bundle file/directory seal required")


def encode(entries: dict[str, bytes]) -> bytes:
    """Canonical ZIP_STORED, UTF-8, Unix sealed modes, 1980-01-01 and no optional records."""
    matrix.need(0 < len(entries) <= MAX_ENTRIES, "archive entry-count ceiling reached")
    local_parts, central_parts, offset, payload = [], [], 0, 0
    for relative in sorted(entries):
        directory, raw = relative.endswith("/"), entries[relative]
        name(relative, directory=directory)
        matrix.need(type(raw) is bytes and (not directory or not raw)
                    and len(raw) <= matrix.MAX_FILE_BYTES, "bounded raw stored member required")
        payload += len(raw)
        matrix.need(payload <= portable.MAX_BYTES, "archive payload aggregate ceiling reached")
        encoded, crc = relative.encode("utf-8"), zlib.crc32(raw)
        local = LOCAL.pack(b"PK\x03\x04", 20, 0x800, 0, 0, 33, crc, len(raw), len(raw), len(encoded), 0) + encoded + raw
        mode = stat.S_IFDIR | 0o555 if directory else stat.S_IFREG | 0o444
        central_parts.append(CENTRAL.pack(b"PK\x01\x02", 0x314, 20, 0x800, 0, 0, 33,
                             crc, len(raw), len(raw), len(encoded), 0, 0, 0, 0,
                             mode << 16 | (0x10 if directory else 0), offset) + encoded)
        local_parts.append(local)
        offset += len(local)
        matrix.need(offset <= MAX_ARCHIVE_BYTES, "archive byte ceiling reached")
    central = b"".join(central_parts)
    matrix.need(len(central) <= MAX_CENTRAL_BYTES and offset + len(central) + END.size <= MAX_ARCHIVE_BYTES,
                "archive central/total byte ceiling reached")
    return b"".join(local_parts) + central + END.pack(b"PK\x05\x06", 0, 0, len(entries), len(entries), len(central), offset, 0)


def decode(raw: bytes) -> dict[str, bytes]:
    """Pre-bound EOCD and central directory before allocating any member inventory."""
    matrix.need(type(raw) is bytes and END.size <= len(raw) <= MAX_ARCHIVE_BYTES, "bounded raw ZIP archive required")
    signature, disk, start_disk, disk_count, count, central_size, central_offset, comment_size = END.unpack_from(raw, len(raw) - END.size)
    matrix.need(signature == b"PK\x05\x06" and disk == start_disk == comment_size == 0
                and disk_count == count and 0 < count <= MAX_ENTRIES
                and 0 < central_size <= MAX_CENTRAL_BYTES
                and central_offset + central_size == len(raw) - END.size,
                "ZIP end/count/central boundary, ZIP64 or trailing data refused")
    position, local_offset, total, file_count, directory_count, entries = central_offset, 0, 0, 0, 0, {}
    previous = None
    for _index in range(count):
        matrix.need(position + CENTRAL.size <= central_offset + central_size, "truncated central directory")
        values = CENTRAL.unpack_from(raw, position)
        (signature, made, needed, flags, method, clock, date, crc, compressed, size,
         name_size, extra_size, comment_size, start_disk, internal, external, offset) = values
        matrix.need(signature == b"PK\x01\x02" and made == 0x314 and needed == 20
                    and flags == 0x800 and method == clock == extra_size == comment_size == start_disk == internal == 0
                    and date == 33 and 0 < name_size <= 1025 and compressed == size <= matrix.MAX_FILE_BYTES
                    and offset == local_offset and position + CENTRAL.size + name_size <= central_offset + central_size,
                    "ZIP unsupported codec/encryption/type/size/order/header metadata refused")
        encoded = raw[position + CENTRAL.size:position + CENTRAL.size + name_size]
        try:
            relative = encoded.decode("utf-8")
        except UnicodeError as exc:
            raise matrix.MatrixRefusal("strict UTF-8 ZIP names required") from exc
        directory = relative.endswith("/")
        name(relative, directory=directory)
        matrix.need(relative not in entries and (previous is None or previous < relative), "ZIP duplicate/unsorted member refused")
        previous = relative
        mode = stat.S_IFDIR | 0o555 if directory else stat.S_IFREG | 0o444
        matrix.need(external == mode << 16 | (0x10 if directory else 0)
                    and (not directory or size == crc == 0), "ZIP symlink/nonregular/unsealed member refused")
        directory_count += int(directory)
        file_count += int(not directory)
        total += size
        matrix.need(directory_count <= portable.MAX_DIRECTORIES and file_count <= portable.MAX_FILES
                    and total <= portable.MAX_BYTES, "ZIP member population/payload budget reached")
        matrix.need(local_offset + LOCAL.size <= central_offset, "ZIP local header outside payload")
        header = LOCAL.unpack_from(raw, local_offset)
        matrix.need(header == (b"PK\x03\x04", needed, flags, method, clock, date, crc, compressed, size, name_size, 0),
                    "ZIP local/central header mismatch refused")
        body_offset = local_offset + LOCAL.size + name_size
        matrix.need(body_offset + size <= central_offset
                    and raw[local_offset + LOCAL.size:body_offset] == encoded,
                    "ZIP local name/body boundary differs")
        body = raw[body_offset:body_offset + size]
        matrix.need(zlib.crc32(body) == crc, "ZIP stored member CRC differs")
        entries[relative] = body
        local_offset, position = body_offset + size, position + CENTRAL.size + name_size
    matrix.need(position == central_offset + central_size and local_offset == central_offset,
                "ZIP unselected padding/central/local population refused")
    return entries


def selected_entries(entries: dict[str, bytes], bundle_digest: str) -> tuple[dict, dict, set]:
    matrix.need(portable.MANIFEST_FILENAME in entries, "selected bundle manifest missing from archive")
    bundle, selected, directories = inventory(entries[portable.MANIFEST_FILENAME], bundle_digest)
    matrix.need(set(entries) == set(selected) | {value + "/" for value in directories},
                "ZIP members differ from exact selected bundle file/directory population")
    for relative, row in selected.items():
        body = entries[relative]
        matrix.need(len(body) == row["size_bytes"] and matrix.sha(body) == row["sha256"], "ZIP selected body raw digest/size differs")
    return bundle, selected, directories


def summary(review: dict, count: int) -> dict:
    return {"file_count": review["file_count"], "directory_count": count,
            "object_count": review["object_count"], "bundle_bytes": review["bytes"],
            "source_dispositions": review["source_dispositions"],
            "evidence_dispositions": review["evidence_dispositions"], "omissions": review["omissions"]}


def protected_original_scopes(original: dict) -> list[Path]:
    # Historical paths protect output lexically; no historical location is opened.
    scopes = [Path(row["root"]) for row in original["repositories"]]
    if original["snapshot"]:
        scopes.append(Path(original["snapshot"]["root"]))
    scopes.extend(Path(row[key]).parent for row in original["local_documents"] for key in ("path", "observed_path"))
    scopes.extend(Path(row["retained_path"]).parent for profile in original["source_profiles"] for row in profile["files"])
    return scopes


def build(manifest: Path, output: Path) -> dict:
    reader = PinnedReader()
    manifest = matrix.canonical(str(manifest))
    raw = reader.read(manifest, MAX_MANIFEST_BYTES)
    spec = matrix.document(raw)
    matrix.fields(spec, {"schema", "bundle_root", "bundle_manifest_sha256"}, "archive build input")
    matrix.need(spec["schema"] == BUILD_INPUT_SCHEMA and matrix.exact_hex(spec["bundle_manifest_sha256"]),
                "archive build schema/bundle digest required")
    root = matrix.canonical(spec["bundle_root"], directory=True)
    fresh(output, [root, manifest])
    source = portable.BundleReader(root)
    matrix.need((root / portable.MANIFEST_FILENAME).stat(follow_symlinks=False).st_size <= 1024 * 1024,
                "bundle manifest byte ceiling reached before capture")
    bundle_raw = source.read(root / portable.MANIFEST_FILENAME, spec["bundle_manifest_sha256"])
    bundle, selected, directories = inventory(bundle_raw, spec["bundle_manifest_sha256"])
    exact_seals(root, selected, directories, source)
    original = matrix.document(source.body(bundle["source_manifest"]))
    matrix.need(not any(output.is_relative_to(path) for path in protected_original_scopes(original)),
                "archive build output lies in original input scope")
    output.mkdir()
    review = portable.verify(root, spec["bundle_manifest_sha256"], output / "source_verification")
    entries = {value + "/": b"" for value in directories}
    for relative, row in selected.items():
        entries[relative] = source.body(row)
    archive_raw = encode(entries)
    selected_entries(decode(archive_raw), spec["bundle_manifest_sha256"])
    matrix.need(source.stability()["unchanged"], "source capsule bytes changed during archive encoding")
    exact_seals(root, selected, directories, source)
    stability = reader.stability()
    archive_path = output / "portable_review.zip"
    with archive_path.open("xb") as stream:
        stream.write(archive_raw)
    archive_path.chmod(0o444)
    archive_pin = {"path": str(archive_path), "sha256": matrix.sha(archive_raw), "size_bytes": len(archive_raw)}
    verify_spec = {"schema": INPUT_SCHEMA, "archive": archive_pin,
                   "bundle_manifest_sha256": spec["bundle_manifest_sha256"]}
    (output / "archive_input.json").write_bytes(matrix.json_bytes(verify_spec))
    result = {"schema": BUILD_REPORT_SCHEMA, "status": "passed", "manifest_sha256": matrix.sha(raw),
              "archive_sha256": archive_pin["sha256"], "archive_bytes": len(archive_raw),
              "bundle_manifest_sha256": spec["bundle_manifest_sha256"],
              "codec": "canonical ZIP_STORED UTF-8 Unix sealed modes; no optional records",
              "input_files_unchanged": True, "input_stability": stability,
              "source_capsule_stability": source.stability(), "portable_scope_complete": True,
              "archive_roundtrip_verified": False, **summary(review, len(directories)),
              **dict.fromkeys(FALSE_FLAGS, False)}
    matrix.need(result["source_capsule_stability"]["unchanged"], "late source capsule byte drift refused")
    exact_seals(root, selected, directories, source)
    reader.stability()
    (output / "portable_archive_build.json").write_bytes(matrix.json_bytes(result))
    return result


def verify(manifest: Path, output: Path) -> dict:
    reader = PinnedReader()
    manifest = matrix.canonical(str(manifest))
    raw = reader.read(manifest, MAX_MANIFEST_BYTES)
    spec = matrix.document(raw)
    matrix.fields(spec, {"schema", "archive", "bundle_manifest_sha256"}, "archive verify input")
    matrix.need(spec["schema"] == INPUT_SCHEMA and matrix.exact_hex(spec["bundle_manifest_sha256"]),
                "archive verification schema/bundle digest required")
    row = descriptor(spec["archive"])
    archive_path = Path(row["path"])
    fresh(output, [manifest, archive_path.parent])
    archive_raw = reader.read(archive_path, MAX_ARCHIVE_BYTES, row["sha256"], row["size_bytes"])
    entries = decode(archive_raw)
    bundle, selected, directories = selected_entries(entries, spec["bundle_manifest_sha256"])
    original = matrix.document(entries[bundle["source_manifest"]["path"]])
    matrix.need(not any(output.is_relative_to(path) for path in protected_original_scopes(original)),
                "archive output lies in original input scope")
    output.mkdir()
    restored = output / "bundle"
    restored.mkdir()
    for relative in sorted(directories, key=lambda value: (len(Path(value).parts), value)):
        (restored / relative).mkdir()
    for relative in sorted(selected):
        with (restored / relative).open("xb") as stream:
            stream.write(entries[relative])
        (restored / relative).chmod(0o444)
    for relative in directories:
        (restored / relative).chmod(0o555)
    restored.chmod(0o555)
    review = portable.verify(restored, spec["bundle_manifest_sha256"], output / "restored_verification")
    exact_seals(restored, selected, directories, portable.BundleReader(restored))
    stability = reader.stability()
    review_path = output / "restored_verification/portable_review.json"
    review_raw = review_path.read_bytes()
    result = {"schema": REPORT_SCHEMA, "status": "passed", "manifest_sha256": matrix.sha(raw),
              "archive_sha256": row["sha256"], "archive_bytes": len(archive_raw),
              "bundle_manifest_sha256": spec["bundle_manifest_sha256"],
              "codec": "canonical ZIP_STORED UTF-8 Unix sealed modes; no optional records",
              "scope": "exact selected review capsule local archive roundtrip; no runtime replay",
              "restored_bundle": str(restored), "restored_verification": {
                  "path": str(review_path), "sha256": matrix.sha(review_raw), "size_bytes": len(review_raw)},
              "input_files_unchanged": True, "input_stability": stability,
              "archive_roundtrip_verified": True, "portable_scope_complete": True,
              **summary(review, len(directories)), **dict.fromkeys(FALSE_FLAGS, False)}
    # Report publication requires both original archive/spec and restored capsule stability.
    reader.stability()
    final_reader = portable.BundleReader(restored)
    for pin in selected.values():
        final_reader.body(pin)
    matrix.need(final_reader.stability()["unchanged"], "restored capsule late byte drift refused")
    exact_seals(restored, selected, directories, final_reader)
    (output / "portable_archive.json").write_bytes(matrix.json_bytes(result))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("build", "verify"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        result = (build if args.operation == "build" else verify)(args.manifest, args.output)
    except (ValueError, OSError, TypeError, KeyError, RecursionError, UnicodeError, struct.error) as exc:
        print("portable archive refused: " + str(exc), file=sys.stderr)
        return 2
    print(matrix.json_bytes({"status": result["status"], "archive_sha256": result["archive_sha256"],
                             "file_count": result["file_count"], "seconds": round(time.monotonic() - started, 3)}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
