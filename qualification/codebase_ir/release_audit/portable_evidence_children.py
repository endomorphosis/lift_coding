#!/usr/bin/env python3
"""Package and independently replay one declared level of public evidence custody."""

from __future__ import annotations

import argparse
import copy
import hashlib
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_children as children
import portable_archive as archive
import portable_review as portable
import release_matrix as matrix

BUILD_INPUT_SCHEMA = "codebase-ir-portable-evidence-children-build-input@1"
INPUT_SCHEMA = "codebase-ir-portable-evidence-children-input@1"
CAPSULE_SCHEMA = "codebase-ir-portable-evidence-children-capsule@1"
BUILD_REPORT_SCHEMA = "codebase-ir-portable-evidence-children-build@1"
REPORT_SCHEMA = "codebase-ir-portable-evidence-children-verification@1"
CAPSULE_FILENAME = "capsule_manifest.json"
TOOL_FILES = {"tools/portable_evidence_children.py", "tools/evidence_children.py", "tools/portable_archive.py",
              "tools/portable_review.py", "tools/release_matrix.py", "tools/snapshot_verify.py"}
MAX_OBJECTS = portable.MAX_OBJECTS
MAX_CAPSULE_MANIFEST_BYTES = 1024 * 1024
FALSE_FLAGS = (*children.FALSE_FLAGS, "git_executable_invoked", "original_paths_read", "network_access_performed")
OMISSIONS = {"recursive_evidence_expansion": True, "unselected_git_blob_bodies": True,
             "commit_ancestry": True, "owner_local_state": True, "runtime_environment": True,
             "full_runtime_closure": True, "producer_authentication": True, "numerical_checker_replay": True}


def fresh(output: Path, protected: list[Path]) -> None:
    archive.fresh(output, protected)
    matrix.need(all(p.stat().st_mode & 0o222 for p in output.parents),
                "output cannot descend from a sealed directory")


def local_pin(value: dict, capture: matrix.Capture) -> tuple[Path, bytes]:
    matrix.fields(value, {"path", "sha256", "size_bytes"}, "pinned original input")
    matrix.need(matrix.exact_hex(value["sha256"]) and type(value["size_bytes"]) is int
                and 0 <= value["size_bytes"] <= matrix.MAX_FILE_BYTES, "bounded exact original input pin required")
    path = matrix.canonical(value["path"])
    return path, capture.read(path, value["sha256"], value["size_bytes"])


def prior_report(report: dict, raw_input: bytes) -> None:
    matrix.need(report.get("schema") == children.SCHEMA and report.get("status") == "passed"
                and report.get("manifest_sha256") == matrix.sha(raw_input)
                and report.get("input_files_unchanged") is True
                and report.get("child_evidence_custody_inventory_produced") is True
                and report.get("git_object_verification_performed") is True
                and report.get("expansion_policy") == children.POLICY
                and all(report.get(flag) is False for flag in children.FALSE_FLAGS),
                "prior child report input/policy/authority binding refused")


def scoped_projection(report: dict, raw_input: bytes) -> dict:
    """Keep every custody decision and pin; normalize only relocatable input/copy locations and read costs."""
    prior_report(report, raw_input)
    keys = {"schema", "status", "ledger_sha256", "ledger", "scope", "expansion_policy", "supported_manifest_schemas",
            "manifest_dispositions", "child_dispositions", "manifest_count", "declared_child_count",
            "verified_child_count", "unique_child_body_count", "declared_child_bytes", "all_selected_children_verified",
            "child_evidence_custody_inventory_produced", "git_object_verification_performed", "input_files_unchanged",
            "git_input_stability", *children.FALSE_FLAGS}
    result = {key: copy.deepcopy(report[key]) for key in keys}
    result["repositories"] = [{key: row[key] for key in ("name", "commit")} for row in report["repositories"]]
    result["manifests"] = copy.deepcopy(report["manifests"])
    for parent in result["manifests"]:
        for child in parent["children"]:
            if child["retained_copy"] is not None:
                child["retained_copy"].pop("path")
    result["retained_copies"] = []
    for row in report["retained_copies"]:
        projected = {key: row[key] for key in ("relative_path", "sha256", "size_bytes")}
        if row["relative_path"] == "inputs/manifest.json":
            matrix.need(row["sha256"] == matrix.sha(raw_input) and row["size_bytes"] == len(raw_input),
                        "prior retained original input pin differs")
            projected.update(sha256="bound_original_or_rebased_input", size_bytes=None)
        result["retained_copies"].append(projected)
    for key in ("retained_before", "retained_after"):
        result[key] = copy.deepcopy(report[key])
        result[key]["bytes"] -= len(raw_input)
    input_rows = report["input_stability"]["files"]
    matrix.need(len(input_rows) == 1 and input_rows[0]["before_sha256"] == matrix.sha(raw_input)
                and input_rows[0]["after_sha256"] == matrix.sha(raw_input) and input_rows[0]["unchanged"] is True
                and report["input_stability"]["unchanged"] is True, "prior original input stability differs")
    result["input_stability"] = {"unchanged": True, "files": 1, "scope": report["input_stability"]["scope"]}
    result["bounds"] = {key: value for key, value in report["bounds"].items() if key.startswith("max_")}
    return result


def required_directories(files: set[str], names: set[str]) -> set[str]:
    directories = {"repository_roots", *("repository_roots/" + name for name in names)}
    for relative in files:
        directories.update(parent.as_posix() for parent in Path(relative).parents if parent != Path("."))
    return directories


def descriptor_from(row: dict) -> dict:
    return {key: row[key] for key in ("path", "sha256", "size_bytes")}


def inventory(raw: bytes, digest: str) -> tuple[dict, dict[str, dict], set[str]]:
    matrix.need(matrix.exact_hex(digest) and matrix.sha(raw) == digest
                and len(raw) <= MAX_CAPSULE_MANIFEST_BYTES, "capsule raw manifest pin/byte ceiling differs")
    value = matrix.document(raw)
    matrix.fields(value, {"schema", "manifest_filename", "expansion_policy", "source_manifest", "source_report",
                          "original_inputs", "repositories", "objects", "retained_views", "implementation",
                          "files", "directories", "omissions", *children.FALSE_FLAGS}, "child capsule manifest")
    matrix.need(value["schema"] == CAPSULE_SCHEMA and value["manifest_filename"] == CAPSULE_FILENAME
                and value["expansion_policy"] == children.POLICY
                and all(value[key] is False for key in children.FALSE_FLAGS)
                and value["omissions"] == OMISSIONS
                and all(type(item) is bool for item in value["omissions"].values()), "capsule policy/authority/omissions differ")
    files, directories = value["files"], value["directories"]
    matrix.need(type(value["objects"]) is list and len(value["objects"]) <= MAX_OBJECTS
                and type(value["retained_views"]) is list and len(value["retained_views"]) <= portable.MAX_FILES
                and type(value["implementation"]) is list and len(value["implementation"]) == len(TOOL_FILES),
                "capsule object/view/tool population ceiling reached before body reads")
    matrix.need(type(files) is list and len(files) < portable.MAX_FILES
                and type(directories) is list and len(directories) <= portable.MAX_DIRECTORIES,
                "capsule declared file/directory ceiling reached")
    selected = {CAPSULE_FILENAME: portable.pin(CAPSULE_FILENAME, raw)}
    total = len(raw)
    for row in files:
        matrix.fields(row, {"path", "sha256", "size_bytes"}, "capsule file pin")
        name = archive.name(row["path"])
        matrix.need(name not in selected and matrix.exact_hex(row["sha256"])
                    and type(row["size_bytes"]) is int and 0 <= row["size_bytes"] <= matrix.MAX_FILE_BYTES,
                    "capsule duplicate/digest/file ceiling differs")
        total += row["size_bytes"]
        matrix.need(total <= portable.MAX_BYTES, "capsule aggregate byte ceiling reached")
        selected[name] = row
    dirs = set()
    for name in directories:
        archive.name(name + "/" if type(name) is str else name, directory=True)
        matrix.need(name not in dirs and name not in selected, "duplicate/file-alias capsule directory")
        dirs.add(name)
    matrix.need(all(parent.as_posix() in dirs for name in selected | {name: None for name in dirs}
                    for parent in Path(name).parents if parent != Path(".")), "capsule parent directory missing")
    return value, selected, dirs


def original_scopes(spec: dict, original: dict) -> list[Path]:
    matrix.fields(original, {"manifest", "report"}, "original provenance paths")
    scopes = []
    for name in ("manifest", "report"):
        value = original[name]
        matrix.need(type(value) is str and Path(value).is_absolute() and str(Path(value)) == value
                    and ".." not in Path(value).parts, "canonical absolute provenance label required")
        scopes.append(Path(value).parent)
    matrix.fields(spec, {"schema", "repositories", "ledger", "selected_evidence", "expansion_policy"}, "original child input")
    matrix.need(spec["schema"] == children.INPUT_SCHEMA and spec["expansion_policy"] == children.POLICY
                and type(spec["repositories"]) is list and 1 <= len(spec["repositories"]) <= 4,
                "original child repository/policy scope malformed")
    for row in spec["repositories"]:
        matrix.fields(row, {"name", "root", "commit", "package_roots"}, "original repository")
        root = row["root"]
        matrix.need(type(root) is str and Path(root).is_absolute() and str(Path(root)) == root
                    and ".." not in Path(root).parts, "absolute lexical original repository scope required")
        scopes.append(Path(root))
    return scopes


class OfflineObjects(matrix.GitObjects):
    """Only the object transport is replaced; inherited tree/blob identity and pathname checks remain active."""
    store: dict = {}
    used: set = set()

    def __init__(self, spec: dict, capture: matrix.Capture):
        matrix.fields(spec, {"name", "root", "commit", "package_roots"}, "offline repository")
        self.name, self.commit = spec["name"], spec["commit"]
        self.root = matrix.canonical(spec["root"], directory=True)
        self.packages, self.capture = spec["package_roots"], capture
        self.commands, self.cache, self.trees, self.executable = 0, {}, {}, None
        raw = self.command(["cat-file", "commit", self.commit], matrix.MAX_FILE_BYTES)
        capture.reserve(len(raw))
        matrix.need(hashlib.sha1(b"commit " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == self.commit,
                    "offline commit exact object identity differs")
        first = raw.split(b"\n", 1)[0]
        matrix.need(first.startswith(b"tree ") and matrix.exact_hex(first[5:].decode("ascii"), 40),
                    "offline commit root tree malformed")
        self.root_tree = first[5:].decode("ascii")

    def command(self, args: list[str], limit: int) -> bytes:
        self.capture.time_check()
        self.commands += 1
        self.capture.git_commands += 1
        matrix.need(self.capture.git_commands <= matrix.MAX_COMMANDS and len(args) == 3
                    and args[0] == "cat-file", "offline object command budget/syntax refused")
        key = self.name, args[2]
        matrix.need(key in self.store, "required selected object absent from capsule")
        kind, raw = self.store[key]["kind"], self.store[key]["raw"]
        if args[1] == "-s":
            return str(len(raw)).encode() + b"\n"
        matrix.need(args[1] == kind and len(raw) <= limit, "offline object kind/byte ceiling differs")
        self.used.add(key)
        return raw


def verify_capsule(root: Path, digest: str, output: Path) -> dict:
    root = matrix.canonical(str(root), directory=True)
    fresh(output, [root])
    reader = portable.BundleReader(root)
    raw = reader.read_body(root / CAPSULE_FILENAME, MAX_CAPSULE_MANIFEST_BYTES)
    reader.reserve(len(raw))
    reader.cache[root / CAPSULE_FILENAME] = raw
    capsule, selected, directories = inventory(raw, digest)
    archive.exact_seals(root, selected, directories, reader)
    bodies = {}
    for relative, row in selected.items():
        bodies[relative] = reader.body(row)
    def body(descriptor: dict) -> bytes:
        matrix.fields(descriptor, {"path", "sha256", "size_bytes"}, "exact selected descriptor")
        matrix.need(descriptor == selected.get(descriptor["path"]), "descriptor differs from selected file pin")
        return bodies[descriptor["path"]]
    source_raw, report_raw = body(capsule["source_manifest"]), body(capsule["source_report"])
    spec, previous = matrix.document(source_raw), matrix.document(report_raw)
    prior_report(previous, source_raw)
    fresh(output, original_scopes(spec, capsule["original_inputs"]))
    repositories = [{key: row[key] for key in ("name", "commit", "package_roots")} for row in spec["repositories"]]
    matrix.need(capsule["repositories"] == repositories, "capsule repository commits/ownership differ")
    matrix.need(type(capsule["objects"]) is list and len(capsule["objects"]) <= MAX_OBJECTS,
                "capsule object population ceiling reached")
    store, referenced = {}, {capsule["source_manifest"]["path"], capsule["source_report"]["path"]}
    for row in capsule["objects"]:
        matrix.fields(row, {"repository", "oid", "kind", "path", "sha256", "size_bytes"}, "selected object")
        matrix.need(type(row["repository"]) is str and row["repository"] in {r["name"] for r in repositories}
                    and matrix.exact_hex(row["oid"], 40) and row["kind"] in {"commit", "tree", "blob"}
                    and row["path"] == "git_objects/" + row["repository"] + "/" + row["oid"],
                    "capsule Git object identity/scope malformed")
        object_raw = body(descriptor_from(row))
        matrix.need(hashlib.sha1(row["kind"].encode() + b" " + str(len(object_raw)).encode() + b"\0" + object_raw).hexdigest() == row["oid"],
                    "capsule Git object body identity differs")
        key = row["repository"], row["oid"]
        matrix.need(key not in store, "duplicate capsule Git identity")
        store[key] = {"kind": row["kind"], "raw": object_raw}
        referenced.add(row["path"])
    matrix.need(type(capsule["retained_views"]) is list and len(capsule["retained_views"]) <= portable.MAX_FILES,
                "bounded retained-view population required")
    views = {}
    for row in capsule["retained_views"]:
        matrix.fields(row, {"relative_path", "path", "sha256", "size_bytes"}, "retained evidence view")
        matrix.relative(row["relative_path"])
        matrix.need(row["relative_path"] not in views and row["path"] == "retained/" + row["relative_path"],
                    "duplicate/misbound retained evidence view")
        body(descriptor_from(row))
        views[row["relative_path"]] = descriptor_from(row)
        referenced.add(row["path"])
    matrix.need(type(capsule["implementation"]) is list and len(capsule["implementation"]) == len(TOOL_FILES),
                "capsule verifier implementation population differs")
    tools = set()
    for row in capsule["implementation"]:
        body(row)
        matrix.need(row["path"] not in tools, "duplicate capsule tool")
        tools.add(row["path"])
    matrix.need(tools == TOOL_FILES, "only selected owned verifier modules allowed")
    referenced.update(tools)
    matrix.need(referenced == set(selected) - {CAPSULE_FILENAME}, "unselected capsule file body refused")
    matrix.need(directories == required_directories(set(selected), {r["name"] for r in repositories}),
                "unselected capsule directory refused")
    rebased = copy.deepcopy(spec)
    for row in rebased["repositories"]:
        row["root"] = str(root / "repository_roots" / row["name"])
    rebased_raw = matrix.json_bytes(rebased)
    output.mkdir()
    (output / "replay_input").mkdir()
    input_path = output / "replay_input/manifest.json"
    input_path.write_bytes(rebased_raw)
    used = set()
    class StoreObjects(OfflineObjects):
        pass
    StoreObjects.store, StoreObjects.used = store, used
    with patch.object(matrix, "GitObjects", StoreObjects):
        recomputed = children.audit(input_path, output / "recomputed")
    matrix.need(used == set(store), "unselected or unused capsule Git object refused")
    matrix.need(matrix.json_bytes(scoped_projection(previous, source_raw))
                == matrix.json_bytes(scoped_projection(recomputed, rebased_raw)),
                "offline custody decisions differ from pinned prior report")
    expected_views = {}
    for row in recomputed["retained_copies"]:
        name, sha, size = row["relative_path"], row["sha256"], row["size_bytes"]
        if name == "inputs/manifest.json":
            sha, size = matrix.sha(source_raw), len(source_raw)
        expected_views[name] = {"path": "retained/" + name, "sha256": sha, "size_bytes": size}
    matrix.need(views == expected_views, "selected evidence view population/pins differ from offline rederivation")
    # The unchanged audit's transport label is corrected for this store-backed replay.
    recomputed.update(read_only_git_invoked=False, object_query_backend="offline_capsule")
    replay_path = output / "recomputed/evidence_children.json"
    replay_raw = matrix.json_bytes(recomputed)
    replay_path.write_bytes(replay_raw)
    matrix.need(reader.stability()["unchanged"], "capsule bytes drifted during offline replay")
    archive.exact_seals(root, selected, directories, reader)
    stability = reader.stability()
    matrix.need(stability["unchanged"], "late capsule byte drift refused")
    archive.exact_seals(root, selected, directories, reader)
    result = {"schema": "codebase-ir-portable-evidence-children-capsule-verification@1", "status": "passed",
              "capsule_manifest_sha256": digest, "source_manifest_sha256": matrix.sha(source_raw),
              "source_report_sha256": matrix.sha(report_raw), "ledger_sha256": previous["ledger_sha256"],
              "input_files_unchanged": True, "portable_child_scope_complete": True,
              "child_evidence_custody_inventory_produced": True, "git_object_verification_performed": True,
              "scope": "relocated declared one-level child evidence bytes and scoped decisions; no original path or Git access",
              "expansion_policy": children.POLICY, "file_count": len(selected), "directory_count": len(directories),
              "object_count": len(store), "capsule_bytes": sum(row["size_bytes"] for row in selected.values()),
              "omissions": OMISSIONS, "restored_custody": {"path": str(replay_path), "sha256": matrix.sha(replay_raw), "size_bytes": len(replay_raw)},
              "input_stability": stability, **custody_summary(previous), **dict.fromkeys(FALSE_FLAGS, False)}
    (output / "capsule_verification.json").write_bytes(matrix.json_bytes(result))
    return result


def custody_summary(report: dict) -> dict:
    return {key: report[key] for key in ("manifest_count", "declared_child_count", "verified_child_count",
            "unique_child_body_count", "declared_child_bytes", "manifest_dispositions", "child_dispositions",
            "all_selected_children_verified")}


def archive_members(entries: dict[str, bytes], digest: str) -> tuple[dict, dict, set]:
    matrix.need(CAPSULE_FILENAME in entries, "selected child capsule manifest absent from archive")
    capsule, selected, directories = inventory(entries[CAPSULE_FILENAME], digest)
    matrix.need(set(entries) == set(selected) | {name + "/" for name in directories},
                "archive differs from exact child capsule member population")
    for name, row in selected.items():
        matrix.need(len(entries[name]) == row["size_bytes"] and matrix.sha(entries[name]) == row["sha256"],
                    "archive selected child capsule file digest/size differs")
    return capsule, selected, directories


def build(manifest: Path, output: Path) -> dict:
    capture = matrix.Capture()
    manifest = matrix.canonical(str(manifest))
    raw = capture.read_body(manifest, archive.MAX_MANIFEST_BYTES)
    capture.reserve(len(raw))
    capture.cache[manifest] = raw
    spec = matrix.document(raw)
    matrix.fields(spec, {"schema", "source_manifest", "source_report"}, "child capsule build input")
    matrix.need(spec["schema"] == BUILD_INPUT_SCHEMA, "child capsule build input schema differs")
    original_manifest, source_raw = local_pin(spec["source_manifest"], capture)
    original_report, report_raw = local_pin(spec["source_report"], capture)
    source, previous = matrix.document(source_raw), matrix.document(report_raw)
    prior_report(previous, source_raw)
    children.input_spec(source)
    fresh(output, [manifest.parent, original_manifest.parent, original_report.parent,
                   *(Path(r["root"]) for r in source["repositories"])])
    objects = {}
    class TraceObjects(matrix.GitObjects):
        def command(self, args, limit):
            selected = len(args) == 3 and args[:2] in (["cat-file", "commit"], ["cat-file", "tree"], ["cat-file", "blob"])
            key = self.name, args[2] if len(args) == 3 else None
            if selected:
                matrix.need(key in objects or len(objects) < MAX_OBJECTS, "child capsule object count reached before body read")
            body = super().command(args, limit)
            if selected:
                value = {"kind": args[1], "raw": body}
                matrix.need(key not in objects or objects[key] == value, "same Git object identity produced conflicting bytes")
                objects[key] = value
            return body
    output.mkdir()
    with patch.object(matrix, "GitObjects", TraceObjects):
        current = children.audit(original_manifest, output / "source_rederivation")
    matrix.need(matrix.json_bytes(scoped_projection(previous, source_raw))
                == matrix.json_bytes(scoped_projection(current, source_raw)),
                "recaptured child custody decisions differ from pinned prior report")
    root = output / "capsule"
    root.mkdir()
    writer = portable.Writer(root)
    views = []
    for row in current["retained_copies"]:
        body = capture.read(matrix.canonical(row["path"]), row["sha256"], row["size_bytes"])
        views.append({"relative_path": row["relative_path"], **writer.put("retained/" + row["relative_path"], body)})
    object_rows = []
    for (repository, oid), value in sorted(objects.items()):
        row = writer.put("git_objects/" + repository + "/" + oid, value["raw"])
        object_rows.append({**row, "repository": repository, "oid": oid, "kind": value["kind"]})
    implementation = []
    for relative in sorted(TOOL_FILES):
        path = Path(__file__).resolve().parent / Path(relative).name
        implementation.append(writer.put(relative, capture.read(path)))
    source_report = writer.put("provenance/child_audit.json", report_raw)
    source_manifest = writer.files["retained/inputs/manifest.json"]
    matrix.need(source_manifest["sha256"] == matrix.sha(source_raw), "captured original input differs")
    names = {r["name"] for r in source["repositories"]}
    directories = required_directories(set(writer.files), names)
    matrix.need(len(directories) <= portable.MAX_DIRECTORIES, "child capsule directory ceiling reached")
    for relative in sorted(directories, key=lambda n: (len(Path(n).parts), n)):
        (root / relative).mkdir(exist_ok=True)
    value = {"schema": CAPSULE_SCHEMA, "manifest_filename": CAPSULE_FILENAME, "expansion_policy": children.POLICY,
             "source_manifest": source_manifest, "source_report": source_report,
             "original_inputs": {"manifest": str(original_manifest), "report": str(original_report)},
             "repositories": [{key: row[key] for key in ("name", "commit", "package_roots")} for row in source["repositories"]],
             "objects": object_rows, "retained_views": views, "implementation": implementation,
             "files": sorted(writer.files.values(), key=lambda r: r["path"]), "directories": sorted(directories),
             "omissions": OMISSIONS, **dict.fromkeys(children.FALSE_FLAGS, False)}
    capsule_raw = matrix.json_bytes(value)
    digest = matrix.sha(capsule_raw)
    capsule, selected, dirs = inventory(capsule_raw, digest)
    (root / CAPSULE_FILENAME).write_bytes(capsule_raw)
    for name in selected:
        (root / name).chmod(0o444)
    for name in dirs:
        (root / name).chmod(0o555)
    root.chmod(0o555)
    verification = verify_capsule(root, digest, output / "source_verification")
    capsule_reader = portable.BundleReader(root)
    entries = {name + "/": b"" for name in dirs}
    for name, row in selected.items():
        entries[name] = capsule_reader.body(row)
    archive_raw = archive.encode(entries)
    archive_members(archive.decode(archive_raw), digest)
    matrix.need(capsule_reader.stability()["unchanged"] and capture.stability()["unchanged"],
                "child capsule/original inputs changed during encoding")
    archive.exact_seals(root, selected, dirs, capsule_reader)
    archive_path = output / "evidence_children.zip"
    with archive_path.open("xb") as stream:
        stream.write(archive_raw)
    archive_path.chmod(0o444)
    pin = {"path": str(archive_path), "sha256": matrix.sha(archive_raw), "size_bytes": len(archive_raw)}
    verify_spec = {"schema": INPUT_SCHEMA, "archive": pin, "capsule_manifest_sha256": digest}
    (output / "archive_input.json").write_bytes(matrix.json_bytes(verify_spec))
    matrix.need(capture.stability()["unchanged"] and capsule_reader.stability()["unchanged"],
                "late child build input/capsule drift refused")
    archive.exact_seals(root, selected, dirs, capsule_reader)
    written_reader = archive.PinnedReader()
    written_reader.read(archive_path, len(archive_raw), pin["sha256"], pin["size_bytes"])
    written_spec = matrix.json_bytes(verify_spec)
    written_reader.read(output / "archive_input.json", len(written_spec), matrix.sha(written_spec), len(written_spec))
    stability = capture.stability()
    matrix.need(stability["unchanged"] and capsule_reader.stability()["unchanged"]
                and written_reader.stability()["unchanged"], "final written archive/build input drift refused")
    archive.exact_seals(root, selected, dirs, capsule_reader)
    result = {"schema": BUILD_REPORT_SCHEMA, "status": "passed", "manifest_sha256": matrix.sha(raw),
              "archive_sha256": pin["sha256"], "archive_bytes": len(archive_raw), "capsule_manifest_sha256": digest,
              "input_files_unchanged": True, "input_stability": stability,
              "build_read_only_git_invoked": True, "archive_roundtrip_verified": False,
              "portable_child_scope_complete": True, "child_evidence_custody_inventory_produced": True,
              "git_object_verification_performed": True, "source_manifest_sha256": matrix.sha(source_raw),
              "source_report_sha256": matrix.sha(report_raw), "ledger_sha256": current["ledger_sha256"],
              **{key: verification[key] for key in ("file_count", "directory_count", "object_count", "capsule_bytes", "omissions")},
              **custody_summary(current), **dict.fromkeys(children.FALSE_FLAGS, False)}
    (output / "portable_evidence_children_build.json").write_bytes(matrix.json_bytes(result))
    return result


def verify(manifest: Path, output: Path) -> dict:
    reader = archive.PinnedReader()
    manifest = matrix.canonical(str(manifest))
    raw = reader.read(manifest, archive.MAX_MANIFEST_BYTES)
    spec = matrix.document(raw)
    matrix.fields(spec, {"schema", "archive", "capsule_manifest_sha256"}, "child archive verification input")
    matrix.need(spec["schema"] == INPUT_SCHEMA and matrix.exact_hex(spec["capsule_manifest_sha256"]),
                "child archive input schema/capsule hash required")
    pin = archive.descriptor(spec["archive"])
    archive_path = Path(pin["path"])
    fresh(output, [manifest.parent, archive_path.parent])
    raw_archive = reader.read(archive_path, archive.MAX_ARCHIVE_BYTES, pin["sha256"], pin["size_bytes"])
    entries = archive.decode(raw_archive)
    capsule, selected, directories = archive_members(entries, spec["capsule_manifest_sha256"])
    original = matrix.document(entries[capsule["source_manifest"]["path"]])
    fresh(output, original_scopes(original, capsule["original_inputs"]))
    output.mkdir()
    root = output / "capsule"
    root.mkdir()
    for name in sorted(directories, key=lambda n: (len(Path(n).parts), n)):
        (root / name).mkdir()
    for name in sorted(selected):
        with (root / name).open("xb") as stream:
            stream.write(entries[name])
        (root / name).chmod(0o444)
    for name in directories:
        (root / name).chmod(0o555)
    root.chmod(0o555)
    review = verify_capsule(root, spec["capsule_manifest_sha256"], output / "restored_verification")
    review_path = output / "restored_verification/capsule_verification.json"
    review_raw = matrix.Capture().read_body(review_path, matrix.MAX_FILE_BYTES)
    matrix.need(review_raw == matrix.json_bytes(review), "restored verification report copy differs")
    final_reader = portable.BundleReader(root)
    for row in selected.values():
        final_reader.body(row)
    matrix.need(reader.stability()["unchanged"] and final_reader.stability()["unchanged"],
                "original archive/restored capsule drift refused")
    archive.exact_seals(root, selected, directories, final_reader)
    stability = reader.stability()
    matrix.need(stability["unchanged"], "late original archive drift refused")
    result = {"schema": REPORT_SCHEMA, "status": "passed", "manifest_sha256": matrix.sha(raw),
              "archive_sha256": pin["sha256"], "archive_bytes": len(raw_archive),
              "capsule_manifest_sha256": spec["capsule_manifest_sha256"],
              "scope": "offline one-level released child evidence capsule archive restoration; no semantic replay",
              "expansion_policy": children.POLICY, "archive_roundtrip_verified": True,
              "portable_child_scope_complete": True, "child_evidence_custody_inventory_produced": True,
              "git_object_verification_performed": True, "input_files_unchanged": True,
              "input_stability": stability, "restored_verification": {
                  "path": str(review_path), "sha256": matrix.sha(review_raw), "size_bytes": len(review_raw)},
              **{key: review[key] for key in ("source_manifest_sha256", "source_report_sha256", "ledger_sha256",
                  "file_count", "directory_count", "object_count", "capsule_bytes", "omissions")},
              **custody_summary(review), **dict.fromkeys(FALSE_FLAGS, False)}
    matrix.need(reader.stability()["unchanged"] and final_reader.stability()["unchanged"],
                "final original archive/restored capsule drift refused")
    archive.exact_seals(root, selected, directories, final_reader)
    (output / "portable_evidence_children.json").write_bytes(matrix.json_bytes(result))
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    for operation in ("build", "verify"):
        item = sub.add_parser(operation)
        item.add_argument("--manifest", type=Path, required=True)
        item.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.manifest, args.output) if args.operation == "build" else verify(args.manifest, args.output)
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
        print("portable child evidence refused: " + str(exc), file=sys.stderr)
        return 2
    print(matrix.json_bytes({key: result[key] for key in ("status", "manifest_sha256", "archive_sha256",
                           "capsule_manifest_sha256", "file_count", "object_count", "verified_child_count")}).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
