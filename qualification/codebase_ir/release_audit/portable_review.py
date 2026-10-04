#!/usr/bin/env python3
"""Seal and verify selected release-review bytes; never execute bundled sources."""

from __future__ import annotations

import argparse
import copy
import hashlib
import os
import stat
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_matrix as matrix

BUNDLE_SCHEMA = "codebase-ir-portable-release-review@1"
REPORT_SCHEMA = "codebase-ir-portable-release-review-verification@1"
MANIFEST_FILENAME = "bundle_manifest.json"
MAX_FILES = 768
MAX_BYTES = 64 * 1024 * 1024
MAX_OBJECTS = 512
MAX_DIRECTORIES = 2048
TOOL_FILES = {"tools/portable_review.py", "tools/release_matrix.py", "tools/snapshot_verify.py"}
SPEC_FIELDS = {"schema", "repositories", "ledger", "released_documents", "local_documents",
               "selected_evidence", "source_profiles", "snapshot"}


def pin(path: str, raw: bytes) -> dict:
    return {"path": path, "sha256": matrix.sha(raw), "size_bytes": len(raw)}


def scoped_projection(report: dict) -> dict:
    """Exclude relocatable paths and measured execution costs, not review decisions."""
    source_keys = {"repository", "path", "sha256", "size_bytes", "profile", "origin_basis", "disposition"}
    return {key: report[key] for key in ("declared_counts", "reconstructed_claim_counts", "declared_summary_matches",
            "criteria", "criterion_source", "evidence", "evidence_dispositions", "source_dispositions", "released_documents")} | {
        "selected_sources": [{**{key: row[key] for key in source_keys}, "release_view": row["release_view"]}
                             for row in report["selected_sources"]]}


def prior_report(report: dict, expected_manifest_sha: str) -> None:
    matrix.need(report.get("schema") == matrix.SCHEMA and report.get("status") == "passed"
                and report.get("manifest_sha256") == expected_manifest_sha
                and report.get("input_files_unchanged") is True
                and report.get("snapshot_identity_stable") is True
                and all(report.get(flag) is False for flag in matrix.FALSE_FLAGS),
                "prior scoped reconciliation binding/authority refused")


def fresh(output: Path, protected: list[Path]) -> None:
    matrix.need(output.is_absolute() and str(output.resolve()) == str(output)
                and output.parent.resolve(strict=True) == output.parent
                and not any(part.is_symlink() for part in output.parents)
                and not output.exists() and not any(output.is_relative_to(path) for path in protected),
                "fresh output outside input bundle/scopes required")


class Writer:
    def __init__(self, root: Path):
        self.root, self.files, self.bytes = root, {}, 0

    def put(self, relative: str, raw: bytes) -> dict:
        matrix.relative(relative)
        matrix.need(relative not in self.files and len(self.files) < MAX_FILES - 1
                    and len(raw) <= matrix.MAX_FILE_BYTES and self.bytes + len(raw) <= MAX_BYTES,
                    "portable file/body/aggregate budget reached")
        target = self.root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        row = pin(relative, raw)
        self.files[relative] = row
        self.bytes += len(raw)
        return row


def build(manifest: Path, manifest_sha: str, report: Path, report_sha: str, output: Path) -> dict:
    reader = matrix.Capture()
    manifest, report = matrix.canonical(str(manifest)), matrix.canonical(str(report))
    spec_raw, report_raw = reader.read(manifest, manifest_sha), reader.read(report, report_sha)
    spec, previous = matrix.document(spec_raw), matrix.document(report_raw)
    prior_report(previous, manifest_sha)
    matrix.output_scope(spec, output)
    fresh(output, [report.parent])
    objects = {}
    class TraceObjects(matrix.GitObjects):
        def command(self, args, limit):
            raw = super().command(args, limit)
            if len(args) == 3 and args[:2] in (["cat-file", "commit"], ["cat-file", "tree"], ["cat-file", "blob"]):
                key = self.name, args[2]
                value = {"kind": args[1], "raw": raw}
                matrix.need(key not in objects or objects[key] == value, "same Git identity produced conflicting bytes")
                objects[key] = value
                matrix.need(len(objects) <= MAX_OBJECTS, "portable Git object-count budget reached")
            return raw
    with patch.object(matrix, "GitObjects", TraceObjects):
        current = matrix.reconcile(manifest, expected_manifest_sha256=manifest_sha)
    matrix.need(matrix.json_bytes(scoped_projection(current)) == matrix.json_bytes(scoped_projection(previous)),
                "recomputed scoped matrix differs from pinned prior report")
    output.mkdir()
    root = output / "bundle"
    root.mkdir()
    writer = Writer(root)
    source_manifest = writer.put("inputs/original_spec.json", spec_raw)
    source_report = writer.put("inputs/original_report.json", report_raw)
    object_rows = []
    for (repository, oid), value in sorted(objects.items()):
        row = writer.put("git_objects/" + repository + "/" + oid, value["raw"])
        object_rows.append({**row, "repository": repository, "oid": oid, "kind": value["kind"]})
    documents = []
    for index, row in enumerate(spec["local_documents"]):
        raw = reader.read(matrix.canonical(row["path"]), row["sha256"], row["size_bytes"])
        documents.append({"name": row["name"], **writer.put(f"documents/{index:02d}" + Path(row["path"]).suffix, raw)})
    selected_copies = []
    for profile_index, profile in enumerate(spec["source_profiles"]):
        for file_index, row in enumerate(profile["files"]):
            raw = reader.read(matrix.canonical(row["retained_path"]), row["sha256"], row["size_bytes"])
            selected_copies.append({"profile_index": profile_index, "file_index": file_index,
                                   **writer.put(f"source_profiles/{profile_index:02d}/{file_index:03d}.py", raw)})
    snapshot = None
    if current["snapshot_before"]:
        original = Path(current["snapshot_before"]["snapshot_root"])
        raw = reader.read(original / "snapshot.json", current["snapshot_before"]["snapshot_manifest_sha256"])
        writer.put("retained_snapshot/snapshot.json", raw)
        for row in current["snapshot_before"]["files"]:
            relative = "retained_snapshot/" + row["repository"] + "/" + row["path"]
            writer.put(relative, reader.read(original / row["repository"] / row["path"], row["sha256"], row["bytes"]))
        for row in current["snapshot_before"]["namespace_directories"]:
            (root / "retained_snapshot" / row["repository"] / row["path"]).mkdir(parents=True, exist_ok=True)
        for value in current["snapshot_before"]["snapshot_roots"]:
            (root / "retained_snapshot" / Path(value).name).mkdir(parents=True, exist_ok=True)
        snapshot = {"path": "retained_snapshot", "sha256": current["snapshot_before"]["snapshot_sha256"]}
    repositories = [{key: row[key] for key in ("name", "commit", "package_roots")} for row in spec["repositories"]]
    for row in repositories:
        (root / "repository_roots" / row["name"]).mkdir(parents=True)
    implementation = []
    for relative in sorted(TOOL_FILES):
        source = Path(__file__).resolve().parent / Path(relative).name
        implementation.append(writer.put(relative, reader.read(source)))
    stability = reader.stability()
    matrix.need(stability["unchanged"], "source inputs changed during portable capture")
    directories = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_dir())
    matrix.need(len(directories) <= MAX_DIRECTORIES, "portable directory budget reached")
    bundle = {"schema": BUNDLE_SCHEMA, "manifest_filename": MANIFEST_FILENAME,
              "scope": "exact selected release-matrix review scope; original paths are inert provenance only",
              "source_manifest": source_manifest, "source_report": source_report,
              "repositories": repositories, "objects": object_rows, "local_documents": documents,
              "source_copies": selected_copies, "snapshot": snapshot, "implementation": implementation,
              "files": sorted(writer.files.values(), key=lambda row: row["path"]), "directories": directories,
              "omissions": {"unselected_blob_bodies": True, "commit_ancestry": True,
                            "evidence_children": True, "runtime_environment": True, "owner_local_state": True,
                            "full_runtime_closure": True}, **dict.fromkeys(matrix.FALSE_FLAGS, False)}
    bundle_raw = matrix.json_bytes(bundle)
    matrix.need(len(bundle_raw) <= 1024 * 1024 and writer.bytes + len(bundle_raw) <= MAX_BYTES,
                "portable bundle manifest/aggregate byte budget reached")
    (root / MANIFEST_FILENAME).write_bytes(bundle_raw)
    for path in root.rglob("*"):
        path.chmod(0o555 if path.is_dir() else 0o444)
    root.chmod(0o555)
    if snapshot:
        matrix.verify_snapshot(root / snapshot["path"], snapshot["sha256"])
    result = {"schema": "codebase-ir-portable-release-review-build@1", "status": "passed",
              "bundle": str(root), "bundle_manifest_sha256": matrix.sha(bundle_raw),
              "source_manifest_sha256": manifest_sha, "source_report_sha256": report_sha,
              "file_count": len(writer.files) + 1, "object_count": len(objects), "bytes": writer.bytes + len(bundle_raw),
              "source_dispositions": current["source_dispositions"], "evidence_dispositions": current["evidence_dispositions"],
              "source_stability": stability, "input_files_unchanged": True, **dict.fromkeys(matrix.FALSE_FLAGS, False)}
    (output / "bundle_build.json").write_bytes(matrix.json_bytes(result))
    return result


class BundleReader(matrix.Capture):
    def __init__(self, root: Path):
        super().__init__()
        self.root = root

    def body(self, descriptor: dict) -> bytes:
        matrix.fields(descriptor, {"path", "sha256", "size_bytes"}, "bundle file pin")
        matrix.relative(descriptor["path"])
        matrix.need(matrix.exact_hex(descriptor["sha256"]) and type(descriptor["size_bytes"]) is int,
                    "exact bundle file digest/byte pin required")
        path = self.root / descriptor["path"]
        matrix.need(path.is_relative_to(self.root), "bundle path escapes declared root")
        return self.read(path, descriptor["sha256"], descriptor["size_bytes"])


def population(root: Path, files: set[str], directories: set[str], reader: BundleReader) -> None:
    """Stream a bounded no-follow inventory; reapply before and after processing."""
    matrix.need(not root.stat().st_mode & 0o222, "bundle root must be sealed read-only")
    actual_files, actual_directories, pending = set(), set(), [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                reader.time_check()
                info = entry.stat(follow_symlinks=False)
                matrix.need(not info.st_mode & 0o222 and not stat.S_ISLNK(info.st_mode), "unsealed/symlink bundle entry refused")
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                if stat.S_ISREG(info.st_mode):
                    matrix.need(len(actual_files) < MAX_FILES, "actual bundle file-count ceiling reached")
                    actual_files.add(relative)
                else:
                    matrix.need(stat.S_ISDIR(info.st_mode) and len(actual_directories) < MAX_DIRECTORIES,
                                "nonregular/directory-budget bundle entry refused")
                    actual_directories.add(relative)
                    pending.append(path)
    matrix.need(actual_files == files and actual_directories == directories, "portable exact file/directory population differs")


def verify(bundle_root: Path, expected_sha: str, output: Path) -> dict:
    root = matrix.canonical(str(bundle_root), directory=True)
    fresh(output, [root])
    matrix.need(matrix.exact_hex(expected_sha), "explicit raw bundle-manifest SHA256 required")
    reader = BundleReader(root)
    matrix.need((root / MANIFEST_FILENAME).stat(follow_symlinks=False).st_size <= 1024 * 1024,
                "portable manifest byte ceiling reached before read")
    raw = reader.read(root / MANIFEST_FILENAME, expected_sha)
    matrix.need(len(raw) <= 1024 * 1024, "portable manifest byte ceiling reached")
    bundle = matrix.document(raw)
    matrix.fields(bundle, {"schema", "manifest_filename", "scope", "source_manifest", "source_report", "repositories",
                           "objects", "local_documents", "source_copies", "snapshot", "implementation", "files", "directories",
                           "omissions", *matrix.FALSE_FLAGS}, "bundle manifest")
    matrix.need(bundle["schema"] == BUNDLE_SCHEMA and bundle["manifest_filename"] == MANIFEST_FILENAME
                and all(bundle[flag] is False for flag in matrix.FALSE_FLAGS), "bundle schema/authority refused")
    matrix.need(type(bundle["omissions"]) is dict
                and set(bundle["omissions"]) == {"unselected_blob_bodies", "commit_ancestry", "evidence_children",
                    "runtime_environment", "owner_local_state", "full_runtime_closure"}
                and all(value is True for value in bundle["omissions"].values()), "review omissions must remain explicit")
    matrix.need(type(bundle["files"]) is list and len(bundle["files"]) < MAX_FILES
                and type(bundle["directories"]) is list and len(bundle["directories"]) <= MAX_DIRECTORIES,
                "portable file/directory population budget reached")
    matrix.need(all(type(row) is dict and type(row.get("size_bytes")) is int
                    and 0 <= row["size_bytes"] <= matrix.MAX_FILE_BYTES for row in bundle["files"])
                and len(raw) + sum(row["size_bytes"] for row in bundle["files"]) <= MAX_BYTES,
                "declared portable aggregate/body budget reached before reads")
    declared, raw_files = {}, {}
    for row in bundle["files"]:
        matrix.need(type(row) is dict and type(row.get("path")) is str and row["path"] not in declared
                    and row["path"] != MANIFEST_FILENAME, "duplicate/unexpected bundle file pin")
        raw_files[row["path"]] = reader.body(row)
        declared[row["path"]] = row
    directories = set()
    for value in bundle["directories"]:
        matrix.relative(value)
        matrix.need(value not in directories, "duplicate bundle directory")
        directories.add(value)
    population(root, set(declared) | {MANIFEST_FILENAME}, directories, reader)
    def descriptor(value):
        matrix.fields(value, {"path", "sha256", "size_bytes"}, "manifest descriptor")
        matrix.need(matrix.json_bytes(value) == matrix.json_bytes(declared.get(value["path"])),
                    "descriptor differs from exact bundled file pin")
        return raw_files[value["path"]]
    source_manifest_raw, previous_raw = descriptor(bundle["source_manifest"]), descriptor(bundle["source_report"])
    spec, previous = matrix.document(source_manifest_raw), matrix.document(previous_raw)
    matrix.fields(spec, SPEC_FIELDS, "original release scope")
    prior_report(previous, matrix.sha(source_manifest_raw))
    # Lexical protection only: historical locations may no longer exist and are not read.
    original_scopes = [Path(row["root"]) for row in spec["repositories"]]
    if spec["snapshot"]:
        original_scopes.append(Path(spec["snapshot"]["root"]))
    original_scopes.extend(Path(row[key]).parent for row in spec["local_documents"] for key in ("path", "observed_path"))
    original_scopes.extend(Path(row["retained_path"]).parent for profile in spec["source_profiles"] for row in profile["files"])
    matrix.need(not any(output.is_relative_to(path) for path in original_scopes), "output lies in original source/artifact scope")
    repositories = [{key: row[key] for key in ("name", "commit", "package_roots")} for row in spec["repositories"]]
    matrix.need(matrix.json_bytes(repositories) == matrix.json_bytes(bundle["repositories"]), "repository commit/scope differs from original input")
    store = {}
    matrix.need(type(bundle["objects"]) is list and len(bundle["objects"]) <= MAX_OBJECTS, "portable object budget reached")
    referenced = {bundle["source_manifest"]["path"], bundle["source_report"]["path"]}
    for row in bundle["objects"]:
        matrix.fields(row, {"repository", "oid", "kind", "path", "sha256", "size_bytes"}, "Git object pin")
        matrix.need(type(row["repository"]) is str and row["repository"] in {x["name"] for x in repositories}
                    and matrix.exact_hex(row["oid"], 40) and row["kind"] in {"commit", "tree", "blob"}
                    and row["path"] == "git_objects/" + row["repository"] + "/" + row["oid"], "Git object identity/scope malformed")
        object_raw = descriptor({key: row[key] for key in ("path", "sha256", "size_bytes")})
        matrix.need(hashlib.sha1(row["kind"].encode() + b" " + str(len(object_raw)).encode() + b"\0" + object_raw).hexdigest() == row["oid"],
                    "portable Git object body identity differs")
        key = row["repository"], row["oid"]
        matrix.need(key not in store, "duplicate portable Git identity")
        store[key] = {"kind": row["kind"], "raw": object_raw}
        referenced.add(row["path"])
    rebased = copy.deepcopy(spec)
    for row in rebased["repositories"]:
        row["root"] = str(root / "repository_roots" / row["name"])
    matrix.need(type(bundle["local_documents"]) is list and len(bundle["local_documents"]) == len(spec["local_documents"]),
                "portable local document population differs")
    for index, (old, captured) in enumerate(zip(rebased["local_documents"], bundle["local_documents"], strict=True)):
        matrix.fields(captured, {"name", "path", "sha256", "size_bytes"}, "bundled working document")
        matrix.need(captured["name"] == old["name"] and captured["sha256"] == old["sha256"]
                    and captured["size_bytes"] == old["size_bytes"]
                    and captured["path"] == f"documents/{index:02d}" + Path(old["path"]).suffix, "working document capture binding differs")
        descriptor({key: captured[key] for key in ("path", "sha256", "size_bytes")})
        referenced.add(captured["path"])
        old["path"] = str(root / captured["path"])
        old["observed_path"] = old["path"] if old["source_basis"] == "current_working_source" else str(root / "inert_observation" / str(index))
    expected_copies = [(a, b, row) for a, profile in enumerate(spec["source_profiles"]) for b, row in enumerate(profile["files"])]
    matrix.need(type(bundle["source_copies"]) is list and len(bundle["source_copies"]) == len(expected_copies), "selected retained-copy population differs")
    for (a, b, old), row in zip(expected_copies, bundle["source_copies"], strict=True):
        matrix.fields(row, {"profile_index", "file_index", "path", "sha256", "size_bytes"}, "selected retained-copy pin")
        matrix.need(type(row["profile_index"]) is int and type(row["file_index"]) is int
                    and row["profile_index"] == a and row["file_index"] == b
                    and row["path"] == f"source_profiles/{a:02d}/{b:03d}.py"
                    and row["sha256"] == old["sha256"] and row["size_bytes"] == old["size_bytes"], "retained-copy binding differs")
        descriptor({key: row[key] for key in ("path", "sha256", "size_bytes")})
        referenced.add(row["path"])
        rebased["source_profiles"][a]["files"][b]["retained_path"] = str(root / row["path"])
    namespace_directories = []
    if spec["snapshot"] is None:
        matrix.need(bundle["snapshot"] is None, "unexpected selected snapshot")
    else:
        matrix.fields(bundle["snapshot"], {"path", "sha256"}, "portable snapshot")
        matrix.need(bundle["snapshot"] == {"path": "retained_snapshot", "sha256": spec["snapshot"]["sha256"]}, "portable snapshot identity differs")
        rebased["snapshot"]["root"] = str(root / "retained_snapshot")
        snapshot = matrix.verify_snapshot(root / "retained_snapshot", bundle["snapshot"]["sha256"])
        matrix.need([Path(value).name for value in snapshot["snapshot_roots"]]
                    == [Path(value).name for value in previous["snapshot_before"]["snapshot_roots"]],
                    "portable snapshot repository-root population differs")
        namespace_directories = ["retained_snapshot/" + row["repository"] + "/" + row["path"] for row in snapshot["namespace_directories"]]
        referenced.add("retained_snapshot/snapshot.json")
        referenced.update("retained_snapshot/" + row["repository"] + "/" + row["path"] for row in snapshot["files"])
    matrix.need(type(bundle["implementation"]) is list and len(bundle["implementation"]) == len(TOOL_FILES), "portable verifier tool population differs")
    tool_paths = set()
    for row in bundle["implementation"]:
        descriptor(row)
        tool_paths.add(row["path"])
    matrix.need(tool_paths == TOOL_FILES, "only owned standalone verifier modules allowed")
    referenced.update(tool_paths)
    matrix.need(referenced == set(declared), "unselected blob/source/tool body in review bundle")
    needed_directories = {"repository_roots", *("repository_roots/" + row["name"] for row in repositories)}
    for value in set(declared) | set(namespace_directories):
        path = Path(value)
        needed_directories.update(parent.as_posix() for parent in path.parents if parent != Path("."))
        if value in namespace_directories:
            needed_directories.add(value)
    if spec["snapshot"]:
        needed_directories.update("retained_snapshot/" + Path(value).name for value in previous["snapshot_before"]["snapshot_roots"])
    matrix.need(directories == needed_directories, "unselected directory in portable review bundle")
    used = set()
    class OfflineObjects(matrix.GitObjects):
        def __init__(self, repo_spec, capture):
            matrix.fields(repo_spec, {"name", "root", "commit", "package_roots"}, "repository")
            matrix.need(type(repo_spec["name"]) is str and repo_spec["name"].isidentifier()
                        and matrix.exact_hex(repo_spec["commit"], 40), "offline repository identity malformed")
            self.name, self.root, self.commit = repo_spec["name"], matrix.canonical(repo_spec["root"], directory=True), repo_spec["commit"]
            self.packages, self.capture = repo_spec["package_roots"], capture
            matrix.need(type(self.packages) is list and 1 <= len(self.packages) <= 8
                        and all(type(x) is str and x.isidentifier() for x in self.packages)
                        and len(set(self.packages)) == len(self.packages), "offline package ownership malformed")
            self.commands, self.cache, self.trees = 0, {}, {}
            raw = self.command(["cat-file", "commit", self.commit], matrix.MAX_FILE_BYTES)
            capture.reserve(len(raw))
            first = raw.split(b"\n", 1)[0]
            matrix.need(first.startswith(b"tree ") and matrix.exact_hex(first[5:].decode("ascii"), 40), "offline commit tree malformed")
            self.root_tree = first[5:].decode("ascii")

        def command(self, args, limit):
            self.capture.time_check()
            self.commands += 1
            self.capture.git_commands += 1
            matrix.need(self.capture.git_commands <= matrix.MAX_COMMANDS and len(args) == 3 and args[0] == "cat-file", "offline object-query budget/syntax refused")
            key = self.name, args[2]
            matrix.need(key in store, "required scoped Git object absent from portable bundle")
            value = store[key]
            if args[1] == "-s":
                return str(len(value["raw"])).encode() + b"\n"
            matrix.need(args[1] == value["kind"] and len(value["raw"]) <= limit, "offline object kind/byte limit differs")
            used.add(key)
            return value["raw"]
    output.mkdir()
    input_path = output / "rebased_review_input.json"
    input_path.write_bytes(matrix.json_bytes(rebased))
    with patch.object(matrix, "GitObjects", OfflineObjects):
        recomputed = matrix.reconcile(input_path)
    matrix.need(used == set(store), "unselected or unused captured Git object refused")
    matrix.need(matrix.json_bytes(scoped_projection(recomputed)) == matrix.json_bytes(scoped_projection(previous)),
                "portable recomputation contradicts original scoped decisions")
    stability = reader.stability()
    matrix.need(stability["unchanged"], "portable input bytes drifted during verification")
    population(root, set(declared) | {MANIFEST_FILENAME}, directories, reader)
    result = {"schema": REPORT_SCHEMA, "status": "passed", "bundle_manifest_sha256": expected_sha,
              "source_manifest_sha256": matrix.sha(source_manifest_raw), "source_report_sha256": matrix.sha(previous_raw),
              "scope": "relocated selected byte review only; no original path reads or Git executable required",
              "declared_counts": recomputed["declared_counts"], "reconstructed_claim_counts": recomputed["reconstructed_claim_counts"],
              "criterion_source": recomputed["criterion_source"], "criteria": recomputed["criteria"],
              "evidence_dispositions": recomputed["evidence_dispositions"], "source_dispositions": recomputed["source_dispositions"],
              "evidence": recomputed["evidence"], "selected_sources": recomputed["selected_sources"],
              "file_count": len(declared) + 1, "object_count": len(store), "bytes": reader.total_bytes,
              "git_executable_invoked": False, "original_paths_read": False,
              "input_files_unchanged": True, "input_stability": stability,
              "runtime_environment_qualified": False, "runtime_dependency_closure_qualified": False,
              "portable_scope_complete": True, "omissions": bundle["omissions"], **dict.fromkeys(matrix.FALSE_FLAGS, False)}
    (output / "portable_review.json").write_bytes(matrix.json_bytes(result))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--manifest", type=Path, required=True)
    build_parser.add_argument("--manifest-sha256", required=True)
    build_parser.add_argument("--report", type=Path, required=True)
    build_parser.add_argument("--report-sha256", required=True)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--bundle", type=Path, required=True)
    verify_parser.add_argument("--bundle-manifest-sha256", required=True)
    for item in (build_parser, verify_parser):
        item.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    started = time.monotonic()
    try:
        if args.operation == "build":
            result = build(args.manifest, args.manifest_sha256, args.report, args.report_sha256, args.output)
        else:
            result = verify(args.bundle, args.bundle_manifest_sha256, args.output)
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
        print("portable review refused: " + str(exc), file=sys.stderr)
        return 2
    print(matrix.json_bytes({"status": result["status"], "bundle_manifest_sha256": result["bundle_manifest_sha256"],
                             "file_count": result["file_count"], "seconds": round(time.monotonic() - started, 3)}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
