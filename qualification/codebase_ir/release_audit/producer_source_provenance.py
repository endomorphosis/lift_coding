#!/usr/bin/env python3
"""Recover declared historical producer bytes from explicit same-parent public custody."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_children as children
import portable_archive as archive
import portable_evidence_children as child_capsule
import portable_review as portable
import producer_source_bindings as bindings
import release_matrix as matrix

BUILD_INPUT_SCHEMA = "codebase-ir-producer-source-provenance-build-input@1"
INPUT_SCHEMA = "codebase-ir-producer-source-provenance-input@1"
CAPSULE_SCHEMA = "codebase-ir-producer-source-provenance-capsule@1"
REPORT_SCHEMA = "codebase-ir-producer-source-provenance-verification@1"
CAPSULE_FILENAME = "provenance_capsule.json"
POLICY = "same_parent_explicit_child_sha_only@1"
EVIDENCE_ID = "behavioral-native-supervision"
TOOL_FILES = {*bindings.TOOL_FILES, "tools/producer_source_provenance.py"}
MAX_FILES, MAX_DIRECTORIES, MAX_OBJECTS, MAX_SOURCES = 320, 384, 160, 32
BINDINGS = (
    "producer_capsule_manifest_sha256",
    "custody_capsule_manifest_sha256",
    "producer_source_input_sha256",
    "producer_source_report_sha256",
)
FALSE_FLAGS = (
    *bindings.FALSE_FLAGS,
    "historical_source_substitution_performed",
    "historical_source_execution_authenticated",
    "historical_original_path_commit_authenticated",
)
OMISSIONS = {
    "unselected_public_children": True,
    "unreferenced_historical_sources": True,
    "original_path_historical_commit": True,
    "producer_execution_authentication": True,
    "source_dependency_closure": True,
    "runtime_environment": True,
}


def build_spec(raw: bytes) -> dict:
    spec = matrix.document(raw)
    matrix.fields(
        spec,
        {
            "schema",
            "producer_source_input",
            "producer_source_report",
            "producer_capsule_manifest",
            "custody_capsule_manifest",
            "selected_source_paths",
        },
        "provenance build input",
    )
    matrix.need(spec["schema"] == BUILD_INPUT_SCHEMA, "provenance build schema differs")
    for key in (
        "producer_source_input",
        "producer_source_report",
        "producer_capsule_manifest",
        "custody_capsule_manifest",
    ):
        pin = spec[key]
        matrix.fields(pin, {"path", "sha256", "size_bytes"}, "provenance original pin")
        limit = (
            child_capsule.MAX_CAPSULE_MANIFEST_BYTES
            if key.endswith("capsule_manifest")
            else matrix.MAX_FILE_BYTES
        )
        matrix.need(
            matrix.exact_hex(pin["sha256"])
            and type(pin["size_bytes"]) is int
            and 0 <= pin["size_bytes"] <= limit,
            "bounded provenance original pin required",
        )
        matrix.canonical(pin["path"])
    paths = spec["selected_source_paths"]
    matrix.need(
        type(paths) is list and 1 <= len(paths) <= MAX_SOURCES,
        "bounded selected source paths required",
    )
    for path in paths:
        archive.name(path)
    matrix.need(len(set(paths)) == len(paths), "duplicate selected source path")
    return spec


def source_input(raw: bytes) -> dict:
    value = matrix.document(raw)
    matrix.fields(
        value,
        {"schema", "archive", "capsule_manifest_sha256", "custody_capsule_manifest_sha256"},
        "prior producer verification input",
    )
    matrix.need(value["schema"] == bindings.INPUT_SCHEMA, "prior producer input schema differs")
    pin = value["archive"]
    matrix.fields(pin, {"path", "sha256", "size_bytes"}, "inert prior archive descriptor")
    matrix.need(
        type(pin["path"]) is str
        and Path(pin["path"]).is_absolute()
        and str(Path(pin["path"])) == pin["path"]
        and ".." not in Path(pin["path"]).parts
        and matrix.exact_hex(pin["sha256"])
        and type(pin["size_bytes"]) is int
        and 0 <= pin["size_bytes"] <= archive.MAX_ARCHIVE_BYTES
        and all(
            matrix.exact_hex(value[key])
            for key in ("capsule_manifest_sha256", "custody_capsule_manifest_sha256")
        ),
        "prior archive input pin/label differs",
    )
    return value


def producer_data(cap: dict, read) -> dict:
    original = {}
    for row in cap["custody_files"]:
        matrix.need(row["original_relative_path"] not in original, "duplicate prior custody view")
        original[row["original_relative_path"]] = read(child_capsule.descriptor_from(row))
    spec = bindings.build_spec(read(cap["source_manifest"]))
    return bindings.custody(
        spec, original[child_capsule.CAPSULE_FILENAME], lambda pin: original[pin["path"]]
    )


def candidates(
    data: dict, old_child_raw: bytes, source_paths: list[str], read
) -> tuple[list[dict], dict]:
    """Inspect one explicit parent declaration list; never follow body paths or scan other sources."""
    receipt = next(row for row in data["receipts"] if row["evidence_id"] == EVIDENCE_ID)
    raw = read(
        {
            "path": "custody/retained/manifests/" + EVIDENCE_ID + ".json",
            "sha256": receipt["parent"]["sha256"],
            "size_bytes": receipt["parent"]["size_bytes"],
        }
    )
    schema, declared = children.explicit_files(raw)
    matrix.need(
        schema in children.SUPPORTED and declared is not None,
        "selected historical parent must have a supported explicit child list",
    )
    matrix.need(len(declared) <= children.MAX_CHILDREN, "historical declaration count ceiling")
    child_cap, child_selected, _dirs = child_capsule.inventory(
        old_child_raw, matrix.sha(old_child_raw)
    )
    claims = receipt["claims"]
    result = []
    for path in source_paths:
        found = [row for row in claims if row["path"] == path]
        matrix.need(
            len(found) == 1, "selected historical claim must have one exact original membership"
        )
        claim = found[0]
        matches = [row for row in declared if row["sha256"] == claim["sha256"]]
        matrix.need(len(matches) <= MAX_SOURCES, "matching historical candidate count ceiling")
        selected = []
        for child in matches:
            child_path = archive.name(
                (Path(receipt["parent"]["path"]).parent / child["path"]).as_posix()
            )
            relative = (
                "retained/children/"
                + receipt["parent"]["repository"]
                + "/"
                + receipt["parent"]["commit"]
                + "/"
                + child_path
            )
            pin = child_selected.get(relative)
            matrix.need(
                pin is not None
                and pin["sha256"] == child["sha256"]
                and pin["size_bytes"] == child["bytes"],
                "historical child declaration has no exact prior retained view",
            )
            views = [row for row in child_cap["retained_views"] if row["path"] == relative]
            matrix.need(
                len(views) == 1 and child_capsule.descriptor_from(views[0]) == pin,
                "historical child role differs from earlier capsule",
            )
            selected.append(
                {
                    "child_relative_path": child["path"],
                    "evidence_path": child_path,
                    "repository": receipt["parent"]["repository"],
                    "commit": receipt["parent"]["commit"],
                    "sha256": child["sha256"],
                    "size_bytes": child["bytes"],
                    "retained_pin": pin,
                }
            )
        result.append(
            {
                "source_path": path,
                "expected_sha256": claim["sha256"],
                "expected_size_bytes": claim["size_bytes"],
                "candidates": selected,
            }
        )
    return result, child_selected


def provenance_review(
    data: dict, current: dict, selections: list[dict], objects, historical
) -> dict:
    rebuilt, _source_bodies = bindings.scan(data, objects)
    matrix.need(
        all(current[key] == value for key, value in rebuilt.items()),
        "committed source dispositions differ from independent offline proofs",
    )
    rows = []
    for selection in selections:
        memberships = [
            row
            for row in rebuilt["source_memberships"]
            if row["evidence_id"] == EVIDENCE_ID and row["path"] == selection["source_path"]
        ]
        matrix.need(len(memberships) == 1, "one exact selected current membership required")
        committed = memberships[0]
        matrix.need(
            committed["disposition"] == "different"
            and committed["expected_sha256"] == selection["expected_sha256"]
            and committed["expected_size_bytes"] == selection["expected_size_bytes"]
            and committed["sha_check_disposition"] == "different",
            "historical selection is not a committed SHA gap",
        )
        restored = []
        for candidate in selection["candidates"]:
            observed, raw = objects.blob(candidate["evidence_path"])
            matrix.need(
                raw is not None
                and observed["sha256"] == candidate["sha256"]
                and observed["size_bytes"] == candidate["size_bytes"]
                and historical(candidate) == raw
                and (
                    selection["expected_size_bytes"] is None
                    or len(raw) == selection["expected_size_bytes"]
                ),
                "historical selected retained body/tree proof differs",
            )
            restored.append(
                {
                    key: candidate[key]
                    for key in (
                        "child_relative_path",
                        "evidence_path",
                        "repository",
                        "commit",
                        "sha256",
                        "size_bytes",
                    )
                }
                | {
                    "git_blob": observed["git_blob"],
                    "claim_sha_matches": True,
                    "declared_size_disposition": "undeclared"
                    if selection["expected_size_bytes"] is None
                    else "matching",
                }
            )
        rows.append(
            {
                "evidence_id": EVIDENCE_ID,
                "source_path": selection["source_path"],
                "expected_sha256": selection["expected_sha256"],
                "expected_size_bytes": selection["expected_size_bytes"],
                "committed_membership": committed,
                "historical_candidates": restored,
                "historical_disposition": "historical-source-recovered"
                if restored
                else "historical-source-unavailable",
                "unavailable_scope": None
                if restored
                else "no_matching_digest_in_selected_parent_explicit_children",
                "historical_execution_authenticated": False,
                "original_path_historical_commit_authenticated": False,
            }
        )
    unique_views = {c["evidence_path"]: c for row in rows for c in row["historical_candidates"]}
    return {
        "policy": POLICY,
        "release_commit": objects.commit,
        "repository": objects.name,
        "ledger_sha256": rebuilt["ledger_sha256"],
        "selected_source_count": len(rows),
        "historical_dispositions": dict(Counter(row["historical_disposition"] for row in rows)),
        "recovered_historical_source_count": sum(
            bool(row["historical_candidates"]) for row in rows
        ),
        "unavailable_historical_source_count": sum(
            not row["historical_candidates"] for row in rows
        ),
        "all_selected_historical_sources_recovered": all(
            row["historical_candidates"] for row in rows
        ),
        "retained_historical_source_bytes": sum(c["size_bytes"] for c in unique_views.values()),
        "historical_candidate_membership_count": sum(
            len(row["historical_candidates"]) for row in rows
        ),
        "unique_historical_view_count": len(unique_views),
        "committed_source_dispositions": rebuilt["source_dispositions"],
        "committed_all_selected_sources_verified": rebuilt["all_selected_sources_verified"],
        "historical_sources": rows,
    }


def inventory(raw: bytes, digest: str) -> tuple[dict, dict, set]:
    matrix.need(
        matrix.exact_hex(digest)
        and matrix.sha(raw) == digest
        and len(raw) <= child_capsule.MAX_CAPSULE_MANIFEST_BYTES,
        "provenance capsule raw pin differs",
    )
    cap = matrix.document(raw)
    matrix.fields(
        cap,
        {
            "schema",
            "manifest_filename",
            "source_manifest",
            "producer_source_input",
            "producer_source_report",
            "producer_capsule_manifest",
            "custody_capsule_manifest",
            "producer_files",
            "historical_views",
            "historical_objects",
            "implementation",
            "expected_review",
            "files",
            "directories",
            "original_input_paths",
            "omissions",
            *FALSE_FLAGS,
        },
        "provenance capsule",
    )
    matrix.need(
        cap["schema"] == CAPSULE_SCHEMA
        and cap["manifest_filename"] == CAPSULE_FILENAME
        and cap["omissions"] == OMISSIONS
        and all(type(value) is bool for value in cap["omissions"].values())
        and all(cap[flag] is False for flag in FALSE_FLAGS),
        "provenance capsule scope/authority differs",
    )
    matrix.need(
        type(cap["files"]) is list
        and len(cap["files"]) < MAX_FILES
        and type(cap["directories"]) is list
        and len(cap["directories"]) <= MAX_DIRECTORIES
        and type(cap["historical_views"]) is list
        and len(cap["historical_views"]) <= MAX_SOURCES * MAX_SOURCES
        and type(cap["historical_objects"]) is list
        and len(cap["historical_objects"]) <= MAX_OBJECTS
        and type(cap["producer_files"]) is list
        and len(cap["producer_files"]) <= bindings.MAX_FILES
        and type(cap["implementation"]) is list
        and len(cap["implementation"]) == len(TOOL_FILES),
        "provenance population ceiling reached before body reads",
    )
    files, size = {CAPSULE_FILENAME: portable.pin(CAPSULE_FILENAME, raw)}, len(raw)
    for pin in cap["files"]:
        matrix.fields(pin, {"path", "sha256", "size_bytes"}, "provenance capsule file")
        path = archive.name(pin["path"])
        matrix.need(
            path not in files
            and matrix.exact_hex(pin["sha256"])
            and type(pin["size_bytes"]) is int
            and 0 <= pin["size_bytes"] <= matrix.MAX_FILE_BYTES,
            "provenance file pin/alias/size differs",
        )
        size += pin["size_bytes"]
        matrix.need(size <= portable.MAX_BYTES, "provenance aggregate capsule byte ceiling")
        files[path] = pin
    dirs = set()
    for path in cap["directories"]:
        archive.name(path + "/", directory=True)
        matrix.need(
            path not in dirs and path not in files, "provenance directory duplicate/file alias"
        )
        dirs.add(path)
    matrix.need(
        all(
            p.as_posix() in dirs
            for path in files | {d: None for d in dirs}
            for p in Path(path).parents
            if p != Path(".")
        ),
        "provenance parent directory missing",
    )
    return cap, files, dirs


def seal(root: Path, files: dict, dirs: set) -> None:
    for path in files:
        (root / path).chmod(0o444)
    for path in sorted(dirs, key=lambda x: len(Path(x).parts), reverse=True):
        (root / path).mkdir(parents=True, exist_ok=True)
        (root / path).chmod(0o555)
    root.chmod(0o555)


def offline_store(
    producer_cap: dict, producer_read, additions: list[dict], read
) -> tuple[type, set]:
    store, used = {}, set()
    rows = [(row, producer_read) for row in producer_cap["objects"]] + [
        (row, read) for row in additions
    ]
    matrix.need(len(rows) <= MAX_OBJECTS, "provenance object ceiling before reads")
    for row, getter in rows:
        matrix.fields(
            row,
            {"repository", "oid", "kind", "path", "sha256", "size_bytes"},
            "provenance Git object",
        )
        matrix.need(
            row["repository"] == producer_cap["repository"]["name"]
            and matrix.exact_hex(row["oid"], 40)
            and row["kind"] in {"commit", "tree", "blob"},
            "provenance object identity scope differs",
        )
        raw = getter(child_capsule.descriptor_from(row))
        matrix.need(
            hashlib.sha1(
                row["kind"].encode() + b" " + str(len(raw)).encode() + b"\0" + raw
            ).hexdigest()
            == row["oid"],
            "provenance independent Git object identity differs",
        )
        key = row["repository"], row["oid"]
        matrix.need(key not in store, "duplicate provenance Git identity")
        store[key] = {"kind": row["kind"], "raw": raw}

    class Store(child_capsule.OfflineObjects):
        pass

    Store.store, Store.used = store, used
    return Store, used


def prior_binding(
    input_raw: bytes,
    report_raw: bytes,
    producer_raw: bytes,
    child_raw: bytes,
    producer_entries: dict,
    current: dict,
) -> None:
    spec, report = source_input(input_raw), matrix.document(report_raw)
    matrix.need(
        report.get("schema") == bindings.REPORT_SCHEMA
        and report.get("status") == "passed"
        and report.get("manifest_sha256") == matrix.sha(input_raw)
        and report.get("input_files_unchanged") is True
        and report.get("producer_source_inventory_produced") is True
        and report.get("git_object_verification_performed") is True
        and report.get("portable_producer_scope_complete") is True
        and report.get("archive_roundtrip_verified") is True
        and report.get("input_stability", {}).get("unchanged") is True
        and all(report.get(flag) is False for flag in bindings.FALSE_FLAGS),
        "prior producer report scope/input differs",
    )
    encoded = archive.encode(producer_entries)
    matrix.need(
        matrix.sha(encoded) == spec["archive"]["sha256"] == report["archive_sha256"]
        and len(encoded) == spec["archive"]["size_bytes"] == report["archive_bytes"]
        and matrix.sha(producer_raw)
        == spec["capsule_manifest_sha256"]
        == report["capsule_manifest_sha256"]
        and matrix.sha(child_raw)
        == spec["custody_capsule_manifest_sha256"]
        == report["custody_capsule_manifest_sha256"],
        "prior producer archive/header input/report binding differs",
    )
    for key, value in current.items():
        if key not in {"schema", "input_stability"}:
            matrix.need(report.get(key) == value, "prior producer report decisions differ: " + key)


def bindings_for(cap: dict, body) -> dict:
    return {
        "producer_capsule_manifest_sha256": matrix.sha(body(cap["producer_capsule_manifest"])),
        "custody_capsule_manifest_sha256": matrix.sha(body(cap["custody_capsule_manifest"])),
        "producer_source_input_sha256": matrix.sha(body(cap["producer_source_input"])),
        "producer_source_report_sha256": matrix.sha(body(cap["producer_source_report"])),
    }


def capsule_verify(root: Path, digest: str, output: Path) -> dict:
    child_capsule.fresh(output, [root])
    reader = portable.BundleReader(root)
    raw = reader.read_body(root / CAPSULE_FILENAME, child_capsule.MAX_CAPSULE_MANIFEST_BYTES)
    reader.reserve(len(raw))
    reader.cache[root / CAPSULE_FILENAME] = raw
    cap, files, dirs = inventory(raw, digest)
    archive.exact_seals(root, files, dirs, reader)
    referenced = {CAPSULE_FILENAME}

    def body(pin):
        matrix.fields(pin, {"path", "sha256", "size_bytes"}, "provenance selected body")
        matrix.need(pin == files.get(pin["path"]), "provenance selected body descriptor differs")
        referenced.add(pin["path"])
        return reader.body(pin)

    source_raw = body(cap["source_manifest"])
    source = matrix.document(source_raw)
    # Captured build paths are lexical protected labels; offline replay never opens them.
    matrix.fields(
        source,
        {
            "schema",
            "producer_source_input",
            "producer_source_report",
            "producer_capsule_manifest",
            "custody_capsule_manifest",
            "selected_source_paths",
        },
        "inert original provenance input",
    )
    matrix.need(source["schema"] == BUILD_INPUT_SCHEMA, "captured provenance build schema differs")
    paths = source["selected_source_paths"]
    matrix.need(
        type(paths) is list and 1 <= len(paths) <= MAX_SOURCES and len(set(paths)) == len(paths),
        "captured source selection count/duplicates differ",
    )
    for path in paths:
        archive.name(path)
    hashes = bindings_for(cap, body)
    protected = []
    matrix.fields(
        cap["original_input_paths"],
        {
            "build_manifest",
            "producer_source_input",
            "producer_source_report",
            "producer_capsule_manifest",
            "custody_capsule_manifest",
        },
        "provenance original labels",
    )
    for name, path in cap["original_input_paths"].items():
        matrix.need(
            type(path) is str
            and Path(path).is_absolute()
            and str(Path(path)) == path
            and ".." not in Path(path).parts,
            "absolute lexical provenance original label required",
        )
        protected.append(Path(path).parent)
        if name != "build_manifest":
            matrix.fields(
                source[name], {"path", "sha256", "size_bytes"}, "inert captured original pin"
            )
            matrix.need(
                source[name]["path"] == path
                and source[name]["sha256"]
                == hashes[
                    name.replace("capsule_manifest", "capsule_manifest_sha256")
                    if name.endswith("capsule_manifest")
                    else name + "_sha256"
                ]
                and source[name]["size_bytes"] == cap[name]["size_bytes"],
                "captured original pin binding differs",
            )
    producer_raw = body(cap["producer_capsule_manifest"])
    producer_cap, producer_files, producer_dirs = bindings.inventory(
        producer_raw, hashes["producer_capsule_manifest_sha256"]
    )
    producer_entries, producer_map = {}, {}
    for row in cap["producer_files"]:
        matrix.fields(
            row, {"original_relative_path", "path", "sha256", "size_bytes"}, "copied producer view"
        )
        original = archive.name(row["original_relative_path"])
        matrix.need(
            original not in producer_map
            and row["path"] == "producer/" + original
            and portable.pin(original, body(child_capsule.descriptor_from(row)))
            == producer_files.get(original),
            "copied producer exact descriptor/alias differs",
        )
        producer_map[original] = child_capsule.descriptor_from(row)
        producer_entries[original] = body(producer_map[original])
    matrix.need(set(producer_map) == set(producer_files), "copied producer population differs")
    for path in producer_dirs:
        producer_entries[path + "/"] = b""
    data = producer_data(producer_cap, lambda pin: producer_entries[pin["path"]])
    protected.extend(data["scopes"])
    for path in producer_cap["original_input_paths"].values():
        protected.append(Path(path).parent)
    child_capsule.fresh(output, protected)
    output.mkdir()
    current = bindings.capsule_verify(
        root / "producer",
        hashes["producer_capsule_manifest_sha256"],
        output / "producer_reverification",
    )
    reports = matrix.Capture()
    producer_report_path = output / "producer_reverification/producer_source_custody.json"
    current_raw = matrix.json_bytes(current)
    producer_report_raw = reports.read(
        producer_report_path, matrix.sha(current_raw), len(current_raw)
    )
    child_raw = body(cap["custody_capsule_manifest"])
    matrix.need(
        child_raw == producer_entries["custody/" + child_capsule.CAPSULE_FILENAME],
        "old child header differs between independently bound scopes",
    )
    prior_binding(
        body(cap["producer_source_input"]),
        body(cap["producer_source_report"]),
        producer_raw,
        child_raw,
        producer_entries,
        current,
    )
    selections, _child_selected = candidates(
        data, child_raw, paths, lambda pin: producer_entries[pin["path"]]
    )
    views = {}
    for row in cap["historical_views"]:
        matrix.fields(
            row, {"evidence_path", "path", "sha256", "size_bytes"}, "selected historical body"
        )
        matrix.need(
            row["evidence_path"] not in views
            and row["path"] == "historical/" + archive.name(row["evidence_path"]),
            "historical copied view alias/duplicate",
        )
        views[row["evidence_path"]] = body(child_capsule.descriptor_from(row))
    wanted = {c["evidence_path"] for row in selections for c in row["candidates"]}
    matrix.need(set(views) == wanted, "historical exact selected view population differs")
    for row in cap["historical_objects"]:
        matrix.need(
            row["path"] == "historical_git_objects/" + row["repository"] + "/" + row["oid"],
            "historical Git object path differs",
        )
    Store, used = offline_store(
        producer_cap, lambda pin: producer_entries[pin["path"]], cap["historical_objects"], body
    )
    objects = Store(
        {**data["repository"], "root": str(root / "repository_roots" / data["repository"]["name"])},
        matrix.Capture(),
    )
    review = provenance_review(
        data, current, selections, objects, lambda candidate: views[candidate["evidence_path"]]
    )
    matrix.need(
        review == cap["expected_review"] and used == set(Store.store),
        "provenance decisions/used proof population differ",
    )
    tool_names = set()
    for pin in cap["implementation"]:
        matrix.need(pin["path"] not in tool_names, "duplicate provenance tool")
        tool_names.add(pin["path"])
        body(pin)
    matrix.need(
        tool_names == TOOL_FILES and referenced == set(files),
        "provenance unused file/tool population differs",
    )
    matrix.need(
        dirs
        == child_capsule.required_directories(set(files), {objects.name})
        | {"producer/" + path for path in producer_dirs},
        "provenance exact directory scope differs",
    )
    matrix.need(reader.stability()["unchanged"], "provenance selected input drift")
    archive.exact_seals(root, files, dirs, reader)
    result = {
        "schema": "codebase-ir-producer-source-provenance-capsule-verification@1",
        "status": "passed",
        "capsule_manifest_sha256": digest,
        **hashes,
        **review,
        "input_files_unchanged": True,
        "producer_source_provenance_inventory_produced": True,
        "git_object_verification_performed": True,
        "committed_source_dispositions_preserved": True,
        "portable_selected_provenance_verified": True,
        "file_count": len(files),
        "directory_count": len(dirs),
        "object_count": len(Store.store),
        "capsule_bytes": sum(pin["size_bytes"] for pin in files.values()),
        "omissions": OMISSIONS,
        "scope": "same-parent explicit historical source bytes; original committed source discrepancies and execution gaps retained",
        "producer_reverification": {
            "path": str(producer_report_path),
            "sha256": matrix.sha(producer_report_raw),
            "size_bytes": len(producer_report_raw),
        },
        **dict.fromkeys(FALSE_FLAGS, False),
    }
    matrix.need(
        reader.stability()["unchanged"] and reports.stability()["unchanged"],
        "final provenance retained bytes/report drift",
    )
    archive.exact_seals(root, files, dirs, reader)
    (output / "producer_source_provenance_custody.json").write_bytes(matrix.json_bytes(result))
    return result


def build(manifest: Path, output: Path) -> dict:
    capture = matrix.Capture()
    manifest = matrix.canonical(str(manifest))
    raw = capture.read_body(manifest, archive.MAX_MANIFEST_BYTES)
    capture.reserve(len(raw))
    capture.cache[manifest] = raw
    spec = build_spec(raw)
    originals = {
        name: child_capsule.local_pin(spec[name], capture)
        for name in (
            "producer_source_input",
            "producer_source_report",
            "producer_capsule_manifest",
            "custody_capsule_manifest",
        )
    }
    producer_root, child_root = (
        originals["producer_capsule_manifest"][0].parent,
        originals["custody_capsule_manifest"][0].parent,
    )
    matrix.need(
        originals["producer_capsule_manifest"][0].name == bindings.CAPSULE_FILENAME
        and originals["custody_capsule_manifest"][0].name == child_capsule.CAPSULE_FILENAME,
        "selected capsule filename differs",
    )
    producer_cap, producer_files, producer_dirs = bindings.inventory(
        originals["producer_capsule_manifest"][1], spec["producer_capsule_manifest"]["sha256"]
    )
    old_cap, child_files, child_dirs = child_capsule.inventory(
        originals["custody_capsule_manifest"][1], spec["custody_capsule_manifest"]["sha256"]
    )
    reader, old_reader = portable.BundleReader(producer_root), portable.BundleReader(child_root)
    archive.exact_seals(producer_root, producer_files, producer_dirs, reader)
    archive.exact_seals(child_root, child_files, child_dirs, old_reader)
    protected = [
        manifest.parent,
        producer_root,
        child_root,
        *[path.parent for path, _raw in originals.values()],
    ]
    data = producer_data(producer_cap, reader.body)
    protected.extend(data["scopes"])
    protected.extend(Path(path).parent for path in producer_cap["original_input_paths"].values())
    child_capsule.fresh(output, protected)
    selections, _ = candidates(
        data, originals["custody_capsule_manifest"][1], spec["selected_source_paths"], reader.body
    )
    known = {(row["repository"], row["oid"]) for row in producer_cap["objects"]}
    planned_views, planned_objects = {}, {}
    prior_child_report = matrix.document(
        reader.body(
            next(
                child_capsule.descriptor_from(row)
                for row in producer_cap["custody_files"]
                if row["original_relative_path"] == "provenance/child_audit.json"
            )
        )
    )
    parent = next(row for row in prior_child_report["manifests"] if row["id"] == EVIDENCE_ID)
    object_rows = {(row["repository"], row["oid"]): row for row in old_cap["objects"]}
    matrix.need(len(object_rows) == len(old_cap["objects"]), "old capsule Git object duplicate")
    for selection in selections:
        for candidate in selection["candidates"]:
            matches = [
                row
                for row in parent["children"]
                if row["declared_relative_path"] == candidate["child_relative_path"]
            ]
            matrix.need(
                len(matches) == 1
                and matches[0]["disposition"] == "verified"
                and matches[0]["expected_sha256"] == candidate["sha256"]
                and matches[0]["expected_size_bytes"] == candidate["size_bytes"],
                "historical candidate was not verified in previous public child custody",
            )
            planned_views[candidate["evidence_path"]] = candidate["retained_pin"]
            key = candidate["repository"], matches[0]["git_blob"]
            if key not in known:
                matrix.need(
                    key in object_rows and len(known) < MAX_OBJECTS,
                    "selected historical object unavailable/over ceiling",
                )
                row = object_rows[key]
                matrix.fields(
                    row,
                    {"repository", "oid", "kind", "path", "sha256", "size_bytes"},
                    "selected historical object",
                )
                matrix.need(
                    row["kind"] == "blob"
                    and row["repository"] == key[0]
                    and row["oid"] == key[1]
                    and row["path"] == "git_objects/" + key[0] + "/" + key[1]
                    and child_capsule.descriptor_from(row) == child_files.get(row["path"]),
                    "historical source proof role differs from selected old capsule",
                )
                planned_objects[key] = row
                known.add(key)
    tool_paths = {
        name: matrix.canonical(str(Path(__file__).parent / Path(name).name)) for name in TOOL_FILES
    }
    planned_files = (
        len(producer_files) + len(planned_views) + len(planned_objects) + len(TOOL_FILES) + 4
    )
    planned_bytes = (
        sum(pin["size_bytes"] for pin in producer_files.values())
        + len(raw)
        + len(originals["producer_source_input"][1])
        + len(originals["producer_source_report"][1])
        + sum(pin["size_bytes"] for pin in planned_views.values())
        + sum(pin["size_bytes"] for pin in planned_objects.values())
        + sum(path.stat().st_size for path in tool_paths.values())
        + child_capsule.MAX_CAPSULE_MANIFEST_BYTES
    )
    matrix.need(
        planned_files <= MAX_FILES and planned_bytes <= portable.MAX_BYTES,
        "planned provenance file/byte ceiling before historical payload reads",
    )
    historical = {path: old_reader.body(pin) for path, pin in planned_views.items()}
    additions = [
        (
            {**row, "path": "historical_git_objects/" + row["repository"] + "/" + row["oid"]},
            old_reader.body(child_capsule.descriptor_from(row)),
        )
        for row in planned_objects.values()
    ]
    output.mkdir()
    root = output / "capsule"
    root.mkdir()
    writer = portable.Writer(root)
    cap = {
        "schema": CAPSULE_SCHEMA,
        "manifest_filename": CAPSULE_FILENAME,
        "source_manifest": writer.put("inputs/build_manifest.json", raw),
        "producer_files": [],
        "historical_views": [],
        "historical_objects": [],
        "implementation": [],
        "omissions": OMISSIONS,
        "original_input_paths": {
            "build_manifest": str(manifest),
            **{name: str(path) for name, (path, _body) in originals.items()},
        },
        **dict.fromkeys(FALSE_FLAGS, False),
    }
    for name in ("producer_source_input", "producer_source_report"):
        cap[name] = writer.put("inputs/" + name + ".json", originals[name][1])
    for path, pin in producer_files.items():
        cap["producer_files"].append(
            {"original_relative_path": path, **writer.put("producer/" + path, reader.body(pin))}
        )
    cap["producer_capsule_manifest"] = writer.files["producer/" + bindings.CAPSULE_FILENAME]
    cap["custody_capsule_manifest"] = writer.files[
        "producer/custody/" + child_capsule.CAPSULE_FILENAME
    ]
    matrix.need(
        cap["custody_capsule_manifest"]["sha256"] == spec["custody_capsule_manifest"]["sha256"],
        "selected old capsule headers disagree",
    )
    for path, body in sorted(historical.items()):
        cap["historical_views"].append(
            {"evidence_path": path, **writer.put("historical/" + path, body)}
        )
    for row, body in additions:
        cap["historical_objects"].append(
            {
                "repository": row["repository"],
                "oid": row["oid"],
                "kind": row["kind"],
                **writer.put(row["path"], body),
            }
        )
    for path in sorted(TOOL_FILES):
        tool = tool_paths[path]
        cap["implementation"].append(writer.put(path, capture.read(tool)))
    current = producer_cap["expected_review"]
    Store, used = offline_store(
        producer_cap,
        reader.body,
        cap["historical_objects"],
        lambda pin: (root / pin["path"]).read_bytes(),
    )
    repo_root = root / "repository_roots" / data["repository"]["name"]
    repo_root.mkdir(parents=True)
    objects = Store({**data["repository"], "root": str(repo_root)}, matrix.Capture())
    cap["expected_review"] = provenance_review(
        data, current, selections, objects, lambda candidate: historical[candidate["evidence_path"]]
    )
    matrix.need(used == set(Store.store), "unused selected historical Git objects")
    cap["files"] = list(writer.files.values())
    dirs = child_capsule.required_directories(
        set(writer.files) | {CAPSULE_FILENAME}, {objects.name}
    ) | {"producer/" + path for path in producer_dirs}
    matrix.need(
        len(writer.files) < MAX_FILES and len(dirs) <= MAX_DIRECTORIES,
        "final provenance population ceiling",
    )
    cap["directories"] = sorted(dirs)
    header_raw = matrix.json_bytes(cap)
    matrix.need(
        len(header_raw) <= child_capsule.MAX_CAPSULE_MANIFEST_BYTES,
        "provenance header byte ceiling",
    )
    (root / CAPSULE_FILENAME).write_bytes(header_raw)
    files = {**writer.files, CAPSULE_FILENAME: portable.pin(CAPSULE_FILENAME, header_raw)}
    seal(root, files, dirs)
    copied = capsule_verify(root, matrix.sha(header_raw), output / "build_reverification")
    reports = matrix.Capture()
    copied_raw = matrix.json_bytes(copied)
    reports.read(
        output / "build_reverification/producer_source_provenance_custody.json",
        matrix.sha(copied_raw),
        len(copied_raw),
    )
    producer_report_pin = copied["producer_reverification"]
    reports.read(
        Path(producer_report_pin["path"]),
        producer_report_pin["sha256"],
        producer_report_pin["size_bytes"],
    )
    entries = {path: portable.BundleReader(root).body(pin) for path, pin in files.items()} | {
        path + "/": b"" for path in dirs
    }
    encoded = archive.encode(entries)
    zipped = output / "producer_provenance.zip"
    zipped.write_bytes(encoded)
    verify_spec = {
        "schema": INPUT_SCHEMA,
        "archive": {"path": str(zipped), "sha256": matrix.sha(encoded), "size_bytes": len(encoded)},
        "capsule_manifest_sha256": matrix.sha(header_raw),
        **{key: copied[key] for key in BINDINGS},
    }
    verify_raw = matrix.json_bytes(verify_spec)
    verify_path = output / "archive_input.json"
    verify_path.write_bytes(verify_raw)
    written = archive.PinnedReader()
    matrix.need(
        written.read(zipped, archive.MAX_ARCHIVE_BYTES, matrix.sha(encoded), len(encoded))
        == encoded
        and written.read(
            verify_path, archive.MAX_MANIFEST_BYTES, matrix.sha(verify_raw), len(verify_raw)
        )
        == verify_raw,
        "written provenance archive/input copy differs",
    )
    final = portable.BundleReader(root)
    for pin in files.values():
        final.body(pin)
    matrix.need(
        capture.stability()["unchanged"]
        and reader.stability()["unchanged"]
        and old_reader.stability()["unchanged"]
        and final.stability()["unchanged"]
        and reports.stability()["unchanged"]
        and written.stability()["unchanged"],
        "final original/copy/archive provenance drift",
    )
    archive.exact_seals(producer_root, producer_files, producer_dirs, reader)
    archive.exact_seals(child_root, child_files, child_dirs, old_reader)
    archive.exact_seals(root, files, dirs, final)
    result = {
        **copied,
        "schema": "codebase-ir-producer-source-provenance-build@1",
        "manifest_sha256": matrix.sha(raw),
        "archive_sha256": matrix.sha(encoded),
        "archive_bytes": len(encoded),
        "archive_roundtrip_verified": False,
    }
    matrix.need(
        capture.stability()["unchanged"]
        and reader.stability()["unchanged"]
        and old_reader.stability()["unchanged"]
        and final.stability()["unchanged"]
        and reports.stability()["unchanged"]
        and written.stability()["unchanged"],
        "late provenance build drift",
    )
    archive.exact_seals(root, files, dirs, final)
    (output / "producer_source_provenance_build.json").write_bytes(matrix.json_bytes(result))
    return result


def verify(manifest: Path, output: Path) -> dict:
    manifest = matrix.canonical(str(manifest))
    reader = archive.PinnedReader()
    raw = reader.read(manifest, archive.MAX_MANIFEST_BYTES)
    spec = matrix.document(raw)
    matrix.fields(
        spec,
        {"schema", "archive", "capsule_manifest_sha256", *BINDINGS},
        "provenance archive input",
    )
    matrix.need(
        spec["schema"] == INPUT_SCHEMA
        and all(matrix.exact_hex(spec[key]) for key in ("capsule_manifest_sha256", *BINDINGS)),
        "provenance verify schema/bindings differ",
    )
    pin = archive.descriptor(spec["archive"])
    path = matrix.canonical(pin["path"])
    child_capsule.fresh(output, [manifest.parent, path.parent])
    encoded = reader.read(path, archive.MAX_ARCHIVE_BYTES, pin["sha256"], pin["size_bytes"])
    entries = archive.decode(encoded)
    cap, files, dirs = inventory(entries[CAPSULE_FILENAME], spec["capsule_manifest_sha256"])
    matrix.need(
        set(entries) == set(files) | {p + "/" for p in dirs}
        and all(
            matrix.sha(entries[p]) == row["sha256"] and len(entries[p]) == row["size_bytes"]
            for p, row in files.items()
        ),
        "provenance archive exact file population/bytes differs",
    )
    matrix.need(
        all(
            cap[name]["sha256"] == spec[key]
            for name, key in (
                ("producer_capsule_manifest", "producer_capsule_manifest_sha256"),
                ("custody_capsule_manifest", "custody_capsule_manifest_sha256"),
                ("producer_source_input", "producer_source_input_sha256"),
                ("producer_source_report", "producer_source_report_sha256"),
            )
        ),
        "independent provenance header/input/report pins differ",
    )
    protected = [Path(path).parent for path in cap["original_input_paths"].values()]
    oldcap = matrix.document(entries[cap["producer_capsule_manifest"]["path"]])
    oldmap = {row["original_relative_path"]: entries[row["path"]] for row in cap["producer_files"]}
    data = producer_data(oldcap, lambda pin: oldmap[pin["path"]])
    protected.extend(data["scopes"])
    protected.extend(Path(p).parent for p in oldcap["original_input_paths"].values())
    child_capsule.fresh(output, protected)
    output.mkdir()
    root = output / "capsule"
    root.mkdir()
    for name in sorted(dirs, key=lambda x: len(Path(x).parts)):
        (root / name).mkdir()
    for name in files:
        with (root / name).open("xb") as out:
            out.write(entries[name])
    seal(root, files, dirs)
    restored = capsule_verify(
        root, spec["capsule_manifest_sha256"], output / "restored_verification"
    )
    final = portable.BundleReader(root)
    for row in files.values():
        final.body(row)
    report_path = output / "restored_verification/producer_source_provenance_custody.json"
    reports = matrix.Capture()
    restored_raw = matrix.json_bytes(restored)
    report_raw = reports.read(report_path, matrix.sha(restored_raw), len(restored_raw))
    producer_report_pin = restored["producer_reverification"]
    reports.read(
        Path(producer_report_pin["path"]),
        producer_report_pin["sha256"],
        producer_report_pin["size_bytes"],
    )
    matrix.need(
        report_raw == matrix.json_bytes(restored), "restored provenance report copy differs"
    )
    result = {
        **restored,
        "schema": REPORT_SCHEMA,
        "manifest_sha256": matrix.sha(raw),
        "archive_sha256": pin["sha256"],
        "archive_bytes": len(encoded),
        "archive_roundtrip_verified": True,
        "restored_verification": {
            "path": str(report_path),
            "sha256": matrix.sha(report_raw),
            "size_bytes": len(report_raw),
        },
    }
    matrix.need(
        reader.stability()["unchanged"]
        and final.stability()["unchanged"]
        and reports.stability()["unchanged"],
        "final provenance archive/restored drift",
    )
    archive.exact_seals(root, files, dirs, final)
    matrix.need(
        reader.stability()["unchanged"]
        and final.stability()["unchanged"]
        and reports.stability()["unchanged"],
        "late provenance archive/restored drift",
    )
    archive.exact_seals(root, files, dirs, final)
    (output / "producer_source_provenance.json").write_bytes(matrix.json_bytes(result))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    for operation in ("build", "verify"):
        p = sub.add_parser(operation)
        p.add_argument("--manifest", type=Path, required=True)
        p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = (
            build(args.manifest, args.output)
            if args.operation == "build"
            else verify(args.manifest, args.output)
        )
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        print("producer source provenance refused: " + str(exc), file=sys.stderr)
        return 2
    print(
        matrix.json_bytes(
            {
                key: result[key]
                for key in (
                    "status",
                    "archive_sha256",
                    "capsule_manifest_sha256",
                    "historical_dispositions",
                )
            }
        ).decode(),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
