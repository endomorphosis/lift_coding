#!/usr/bin/env python3
"""Bind selected public producer inventories to immutable source bodies and portable Git proofs."""

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
import release_matrix as matrix

BUILD_INPUT_SCHEMA = "codebase-ir-producer-source-bindings-build-input@1"
INPUT_SCHEMA = "codebase-ir-producer-source-bindings-input@1"
CAPSULE_SCHEMA = "codebase-ir-producer-source-bindings-capsule@1"
REPORT_SCHEMA = "codebase-ir-producer-source-bindings-verification@1"
CAPSULE_FILENAME = "producer_source_capsule.json"
EVIDENCE_IDS = {"behavioral-repository-admission", "behavioral-native-supervision"}
TOOL_FILES = {*child_capsule.TOOL_FILES, "tools/producer_source_bindings.py"}
MAX_OBJECTS, MAX_FILES, MAX_DIRECTORIES, MAX_CLAIMS = 128, 256, 256, 32
FALSE_FLAGS = (
    *child_capsule.FALSE_FLAGS,
    "producer_source_imports_performed",
    "current_working_source_compared",
    "source_semantics_verified",
    "producer_execution_authenticated",
    "source_dependency_closure_qualified",
)
OMISSIONS = {
    "unlisted_source_dependencies": True,
    "runtime_environment": True,
    "producer_authentication": True,
    "source_execution": True,
    "commit_ancestry": True,
    "unselected_evidence_children": True,
}


def selections(rows: list) -> None:
    matrix.need(type(rows) is list and len(rows) == 2, "exact two producer receipt selections required")
    seen = set()
    for row in rows:
        matrix.fields(
            row,
            {"evidence_id", "receipt_relative_path", "sha256", "size_bytes"},
            "producer receipt selection",
        )
        matrix.need(
            row["evidence_id"] in EVIDENCE_IDS
            and row["evidence_id"] not in seen
            and row["receipt_relative_path"] == "producer-sources.json"
            and matrix.exact_hex(row["sha256"])
            and type(row["size_bytes"]) is int
            and 0 <= row["size_bytes"] <= children.MAX_MANIFEST_BYTES,
            "exact bounded receipt selection refused",
        )
        seen.add(row["evidence_id"])


def build_spec(raw: bytes) -> dict:
    value = matrix.document(raw)
    matrix.fields(value, {"schema", "custody_capsule_manifest", "selected_receipts"}, "producer build input")
    matrix.need(value["schema"] == BUILD_INPUT_SCHEMA, "producer build schema differs")
    selections(value["selected_receipts"])
    pin = value["custody_capsule_manifest"]
    matrix.fields(pin, {"path", "sha256", "size_bytes"}, "custody capsule pin")
    matrix.need(
        matrix.exact_hex(pin["sha256"])
        and type(pin["size_bytes"]) is int
        and 0 <= pin["size_bytes"] <= child_capsule.MAX_CAPSULE_MANIFEST_BYTES,
        "bounded exact custody capsule pin required",
    )
    return value


def source_claims(raw: bytes, repository: str, evidence_id: str) -> list[dict]:
    matrix.need(len(raw) <= children.MAX_MANIFEST_BYTES, "producer inventory byte ceiling reached")
    value = matrix.document(raw)
    expected_schema = (
        "repository-behavioral-admission-sources@1"
        if evidence_id == "behavioral-repository-admission"
        else "qualified-source-inventory@1"
    )
    matrix.need(value.get("schema") == expected_schema, "producer receipt schema differs from selected role")
    if value.get("schema") == "repository-behavioral-admission-sources@1":
        matrix.fields(value, {"schema", "repository", "sources"}, "admission source inventory")
        matrix.need(value["repository"] == repository, "producer inventory repository differs from custody")
        rows, sized = value["sources"], True
    else:
        matrix.fields(value, {"schema", "files"}, "supervision source inventory")
        matrix.need(
            value["schema"] == "qualified-source-inventory@1",
            "unsupported producer inventory schema",
        )
        rows, sized = value["files"], False
    matrix.need(
        type(rows) is list and 1 <= len(rows) <= MAX_CLAIMS,
        "bounded nonempty source claims required",
    )
    result = []
    for row in rows:
        matrix.fields(
            row,
            {"path", "sha256", *({"size_bytes"} if sized else set())},
            "declared producer source",
        )
        path = archive.name(row["path"])
        matrix.relative(path)
        matrix.need(matrix.exact_hex(row["sha256"]), "exact declared source digest required")
        size = row.get("size_bytes")
        matrix.need(
            not sized or type(size) is int and 0 <= size <= matrix.MAX_FILE_BYTES,
            "bounded declared source size required",
        )
        result.append({"path": path, "sha256": row["sha256"], "size_bytes": size})
    return result


def custody(spec: dict, old_raw: bytes, read) -> dict:
    """Read only selected inert capsule views; fresh Git proofs independently bind ledger, parents and receipts."""
    old_pin = spec["custody_capsule_manifest"]
    matrix.need(
        len(old_raw) == old_pin["size_bytes"] and matrix.sha(old_raw) == old_pin["sha256"],
        "selected prior capsule raw binding differs",
    )
    cap, selected, _dirs = child_capsule.inventory(old_raw, old_pin["sha256"])
    used = set()

    def body(pin):
        matrix.need(pin == selected.get(pin["path"]), "custody view differs from prior capsule file pin")
        raw = read(pin)
        matrix.need(
            len(raw) == pin["size_bytes"] and matrix.sha(raw) == pin["sha256"],
            "selected custody body differs",
        )
        used.add(pin["path"])
        return raw

    views = {row["relative_path"]: child_capsule.descriptor_from(row) for row in cap["retained_views"]}
    matrix.need(len(views) == len(cap["retained_views"]), "duplicate prior custody view")
    source_raw, report_raw = body(cap["source_manifest"]), body(cap["source_report"])
    source, report = matrix.document(source_raw), matrix.document(report_raw)
    child_capsule.prior_report(report, source_raw)
    scopes = child_capsule.original_scopes(source, cap["original_inputs"])
    ledger_raw = body(views["inputs/ledger.json"])
    ledger = matrix.document(ledger_raw)
    matrix.validate_ledger(ledger)
    matrix.need(
        matrix.sha(ledger_raw) == report["ledger_sha256"] == source["ledger"]["sha256"],
        "producer ledger differs from existing custody",
    )
    parents = {row["id"]: row for row in report["manifests"]}
    matrix.need(len(parents) == len(report["manifests"]), "duplicate prior parent identity")
    receipts, total = [], 0
    for choice in spec["selected_receipts"]:
        parent = parents[choice["evidence_id"]]
        parent_raw = body(views["manifests/" + choice["evidence_id"] + ".json"])
        matrix.need(
            parent["disposition"] == "expanded"
            and matrix.sha(parent_raw)
            == parent["expected_sha256"]
            == ledger["evidence"][choice["evidence_id"]]["sha256"],
            "producer parent ledger/raw binding differs",
        )
        matching = [
            row for row in parent["children"] if row["declared_relative_path"] == choice["receipt_relative_path"]
        ]
        matrix.need(len(matching) == 1, "producer receipt must have one exact parent membership")
        child = matching[0]
        matrix.need(
            child["disposition"] == "verified"
            and child["expected_sha256"] == child["sha256"] == choice["sha256"]
            and child["expected_size_bytes"] == child["size_bytes"] == choice["size_bytes"]
            and child["repository"] == parent["repository"]
            and child["commit"] == parent["commit"],
            "producer receipt pin/commit differs from qualified custody",
        )
        _schema, files = children.explicit_files(parent_raw)
        matrix.need(
            files is not None
            and sum(
                row["path"] == choice["receipt_relative_path"]
                and row["sha256"] == choice["sha256"]
                and row["bytes"] == choice["size_bytes"]
                for row in files
            )
            == 1,
            "producer receipt declared membership differs from public parent",
        )
        relative = "children/" + child["repository"] + "/" + child["commit"] + "/" + child["path"]
        receipt_raw = body(views[relative])
        claims = source_claims(receipt_raw, child["repository"], choice["evidence_id"])
        total += len(claims)
        matrix.need(total <= MAX_CLAIMS, "aggregate source claim ceiling reached before source reads")
        receipts.append(
            {
                "evidence_id": choice["evidence_id"],
                "parent": {
                    key: parent[key] for key in ("repository", "commit", "path", "sha256", "size_bytes", "git_blob")
                },
                "receipt": {
                    key: child[key] for key in ("repository", "commit", "path", "sha256", "size_bytes", "git_blob")
                },
                "claims": claims,
            }
        )
    names = {row["receipt"]["repository"] for row in receipts}
    matrix.need(
        len(names) == 1 and source["ledger"]["repository"] in names,
        "one ledger/producer repository scope required",
    )
    repo = next(row for row in source["repositories"] if row["name"] in names)
    matrix.need(
        all(row["receipt"]["commit"] == repo["commit"] for row in receipts),
        "producer release commit differs",
    )
    return {
        "repository": repo,
        "receipts": receipts,
        "ledger_pin": source["ledger"],
        "ledger_raw": ledger_raw,
        "scopes": scopes,
        "used": used,
        "source_manifest_sha256": matrix.sha(source_raw),
        "source_report_sha256": matrix.sha(report_raw),
    }


def scan(data: dict, objects) -> tuple[dict, dict[str, bytes]]:
    def pinned(pin, raw=None):
        observed, body = objects.blob(pin["path"])
        matrix.need(
            body is not None
            and observed["sha256"] == pin["sha256"]
            and ("size_bytes" not in pin or observed["size_bytes"] == pin["size_bytes"])
            and ("git_blob" not in pin or observed["git_blob"] == pin["git_blob"])
            and (raw is None or body == raw),
            "selected ledger/parent/receipt Git custody differs",
        )

    pinned(data["ledger_pin"], data["ledger_raw"])
    memberships, bodies, global_memberships = [], {}, set()
    for receipt in data["receipts"]:
        pinned(receipt["parent"])
        pinned(receipt["receipt"])
        local = set()
        for index, claim in enumerate(receipt["claims"]):
            path = claim["path"]
            row = {
                "evidence_id": receipt["evidence_id"],
                "index": index,
                "repository": objects.name,
                "commit": objects.commit,
                "path": path,
                "expected_sha256": claim["sha256"],
                "expected_size_bytes": claim["size_bytes"],
                "shared_source": path in global_memberships,
                "size_check_disposition": "undeclared" if claim["size_bytes"] is None else "unavailable",
            }
            if path in local:
                row.update(disposition="repeated_entry", sha_check_disposition="not_checked")
            else:
                local.add(path)
                global_memberships.add(path)
                observed, body = objects.blob(path)
                row.update(observed)
                row["sha_check_disposition"] = (
                    "unavailable"
                    if body is None
                    else ("matching" if observed["sha256"] == claim["sha256"] else "different")
                )
                if claim["size_bytes"] is not None and body is not None:
                    row["size_check_disposition"] = "matching" if len(body) == claim["size_bytes"] else "different"
                if body is not None:
                    row["disposition"] = (
                        "verified"
                        if row["sha_check_disposition"] == "matching"
                        and row["size_check_disposition"] in {"matching", "undeclared"}
                        else "different"
                    )
                    bodies[path] = body
            memberships.append(row)
    summary = {
        "release_commit": objects.commit,
        "repository": objects.name,
        "ledger_sha256": data["ledger_pin"]["sha256"],
        "source_manifest_sha256": data["source_manifest_sha256"],
        "source_report_sha256": data["source_report_sha256"],
        "receipt_count": len(data["receipts"]),
        "claim_membership_count": len(memberships),
        "unique_source_path_count": len(global_memberships),
        "captured_source_count": len(bodies),
        "verified_source_membership_count": sum(r["disposition"] == "verified" for r in memberships),
        "source_dispositions": dict(Counter(r["disposition"] for r in memberships)),
        "all_selected_sources_verified": all(r["disposition"] == "verified" for r in memberships),
        "declared_size_membership_count": sum(r["expected_size_bytes"] is not None for r in memberships),
        "undeclared_size_membership_count": sum(r["expected_size_bytes"] is None for r in memberships),
        "receipts": data["receipts"],
        "source_memberships": memberships,
    }
    return summary, bodies


def inventory(raw: bytes, digest: str) -> tuple[dict, dict, set]:
    matrix.need(
        matrix.exact_hex(digest) and matrix.sha(raw) == digest and len(raw) <= child_capsule.MAX_CAPSULE_MANIFEST_BYTES,
        "producer capsule raw manifest differs",
    )
    value = matrix.document(raw)
    matrix.fields(
        value,
        {
            "schema",
            "source_manifest",
            "custody_files",
            "repository",
            "objects",
            "source_files",
            "implementation",
            "expected_review",
            "files",
            "directories",
            "original_input_paths",
            "custody_capsule_manifest_sha256",
            "omissions",
            *FALSE_FLAGS,
        },
        "producer capsule",
    )
    matrix.need(
        value["schema"] == CAPSULE_SCHEMA
        and value["omissions"] == OMISSIONS
        and all(type(item) is bool for item in value["omissions"].values())
        and all(value[flag] is False for flag in FALSE_FLAGS),
        "producer capsule authority/omissions differ",
    )
    matrix.need(
        type(value["files"]) is list
        and len(value["files"]) < MAX_FILES
        and type(value["directories"]) is list
        and len(value["directories"]) <= MAX_DIRECTORIES
        and type(value["objects"]) is list
        and len(value["objects"]) <= MAX_OBJECTS
        and type(value["custody_files"]) is list
        and len(value["custody_files"]) <= 10
        and type(value["source_files"]) is list
        and len(value["source_files"]) <= MAX_CLAIMS
        and type(value["implementation"]) is list
        and len(value["implementation"]) == len(TOOL_FILES),
        "producer capsule population ceiling reached before body reads",
    )
    selected, total = {CAPSULE_FILENAME: portable.pin(CAPSULE_FILENAME, raw)}, len(raw)
    for row in value["files"]:
        matrix.fields(row, {"path", "sha256", "size_bytes"}, "producer capsule file")
        path = archive.name(row["path"])
        matrix.need(
            path not in selected
            and matrix.exact_hex(row["sha256"])
            and type(row["size_bytes"]) is int
            and 0 <= row["size_bytes"] <= matrix.MAX_FILE_BYTES,
            "producer duplicate/type/digest/file ceiling refused",
        )
        total += row["size_bytes"]
        matrix.need(total <= portable.MAX_BYTES, "producer capsule byte ceiling reached")
        selected[path] = row
    directories = set()
    for path in value["directories"]:
        archive.name(path + "/", directory=True)
        matrix.need(
            path not in directories and path not in selected,
            "producer directory duplicate/file alias",
        )
        directories.add(path)
    matrix.need(
        directories == child_capsule.required_directories(set(selected), {value["repository"]["name"]}),
        "producer capsule directory population differs",
    )
    return value, selected, directories


def capsule_verify(root: Path, digest: str, output: Path) -> dict:
    child_capsule.fresh(output, [root])
    reader = portable.BundleReader(root)
    raw = reader.read_body(root / CAPSULE_FILENAME, child_capsule.MAX_CAPSULE_MANIFEST_BYTES)
    reader.reserve(len(raw))
    reader.cache[root / CAPSULE_FILENAME] = raw
    cap, selected, dirs = inventory(raw, digest)
    archive.exact_seals(root, selected, dirs, reader)
    bodies = {path: reader.body(pin) for path, pin in selected.items()}
    referenced = {CAPSULE_FILENAME}

    def body(pin):
        matrix.fields(pin, {"path", "sha256", "size_bytes"}, "producer selected body")
        matrix.need(pin == selected.get(pin["path"]), "producer body descriptor differs")
        referenced.add(pin["path"])
        return bodies[pin["path"]]

    source_raw = body(cap["source_manifest"])
    spec = build_spec(source_raw)
    originals = {}
    for row in cap["custody_files"]:
        matrix.fields(
            row,
            {"original_relative_path", "path", "sha256", "size_bytes"},
            "selected custody provenance",
        )
        original = archive.name(row["original_relative_path"])
        matrix.need(
            original not in originals and row["path"] == "custody/" + original,
            "custody provenance alias/duplicate",
        )
        originals[original] = body(child_capsule.descriptor_from(row))
    used_provenance = set()

    def read(pin):
        used_provenance.add(pin["path"])
        return originals[pin["path"]]

    old_raw = originals[child_capsule.CAPSULE_FILENAME]
    data = custody(spec, old_raw, read)
    matrix.need(
        set(originals) == used_provenance | {child_capsule.CAPSULE_FILENAME},
        "unused custody provenance refused",
    )
    matrix.need(
        cap["custody_capsule_manifest_sha256"] == spec["custody_capsule_manifest"]["sha256"],
        "producer prior capsule binding differs",
    )
    labels = cap["original_input_paths"]
    matrix.fields(labels, {"build_manifest", "custody_capsule_manifest"}, "producer original input labels")
    scopes = list(data["scopes"])
    for path in labels.values():
        matrix.need(
            type(path) is str and Path(path).is_absolute() and str(Path(path)) == path and ".." not in Path(path).parts,
            "canonical absolute original label required",
        )
        scopes.append(Path(path).parent)
    child_capsule.fresh(output, scopes)
    repo = data["repository"]
    matrix.need(
        cap["repository"] == {key: repo[key] for key in ("name", "commit", "package_roots")},
        "producer repository identity differs",
    )
    store, used = {}, set()
    for row in cap["objects"]:
        matrix.fields(
            row,
            {"repository", "oid", "kind", "path", "sha256", "size_bytes"},
            "producer Git object",
        )
        matrix.need(
            row["repository"] == repo["name"]
            and matrix.exact_hex(row["oid"], 40)
            and row["kind"] in {"commit", "tree", "blob"}
            and row["path"] == "git_objects/" + row["repository"] + "/" + row["oid"],
            "producer Git object scope differs",
        )
        raw = body(child_capsule.descriptor_from(row))
        matrix.need(
            hashlib.sha1(row["kind"].encode() + b" " + str(len(raw)).encode() + b"\0" + raw).hexdigest() == row["oid"],
            "producer exact Git object identity differs",
        )
        key = row["repository"], row["oid"]
        matrix.need(key not in store, "producer duplicate Git identity")
        store[key] = {"kind": row["kind"], "raw": raw}

    class StoreObjects(child_capsule.OfflineObjects):
        pass

    StoreObjects.store, StoreObjects.used = store, used
    rebased = {**repo, "root": str(root / "repository_roots" / repo["name"])}
    capture = matrix.Capture()
    review, captured = scan(data, StoreObjects(rebased, capture))
    fresh_review, fresh_bodies = scan(data, StoreObjects(rebased, capture))
    matrix.need(
        review == fresh_review and captured == fresh_bodies and used == set(store),
        "producer offline rechecks/used object population differ",
    )
    matrix.need(
        review == cap["expected_review"],
        "producer offline source decisions differ from pinned build review",
    )
    source_files = {}
    for row in cap["source_files"]:
        matrix.fields(row, {"source_path", "path", "sha256", "size_bytes"}, "captured producer source")
        matrix.need(
            row["source_path"] not in source_files
            and row["path"] == "sources/" + repo["name"] + "/" + row["source_path"],
            "producer source view alias/duplicate",
        )
        source_files[row["source_path"]] = body(child_capsule.descriptor_from(row))
    matrix.need(source_files == captured, "producer source body population differs from Git rederivation")
    tools = set()
    for pin in cap["implementation"]:
        body(pin)
        matrix.need(pin["path"] not in tools, "duplicate producer tool")
        tools.add(pin["path"])
    matrix.need(
        tools == TOOL_FILES and referenced == set(selected),
        "unused/incorrect producer implementation/file population",
    )
    stability = reader.stability()
    matrix.need(stability["unchanged"], "producer capsule input bytes drifted")
    archive.exact_seals(root, selected, dirs, reader)
    output.mkdir()
    result = {
        "schema": "codebase-ir-producer-source-bindings-capsule-verification@1",
        "status": "passed",
        "capsule_manifest_sha256": digest,
        "custody_capsule_manifest_sha256": cap["custody_capsule_manifest_sha256"],
        "producer_source_inventory_produced": True,
        "portable_producer_scope_complete": True,
        "git_object_verification_performed": True,
        "input_files_unchanged": True,
        "input_stability": stability,
        "file_count": len(selected),
        "directory_count": len(dirs),
        "object_count": len(store),
        "capsule_bytes": sum(row["size_bytes"] for row in selected.values()),
        "scope": "two public source receipts and their exact committed producer paths; no source imports or dependency closure",
        "omissions": OMISSIONS,
        **review,
        **dict.fromkeys(FALSE_FLAGS, False),
    }
    matrix.need(reader.stability()["unchanged"], "final producer capsule drift refused")
    archive.exact_seals(root, selected, dirs, reader)
    (output / "producer_source_custody.json").write_bytes(matrix.json_bytes(result))
    return result


def members(entries: dict, digest: str):
    cap, selected, dirs = inventory(entries[CAPSULE_FILENAME], digest)
    matrix.need(
        set(entries) == set(selected) | {name + "/" for name in dirs},
        "producer archive exact population differs",
    )
    matrix.need(
        all(
            len(entries[name]) == pin["size_bytes"] and matrix.sha(entries[name]) == pin["sha256"]
            for name, pin in selected.items()
        ),
        "producer archive file pin differs",
    )
    return cap, selected, dirs


def build(manifest: Path, output: Path) -> dict:
    capture = matrix.Capture()
    manifest = matrix.canonical(str(manifest))
    raw = capture.read_body(manifest, archive.MAX_MANIFEST_BYTES)
    capture.reserve(len(raw))
    capture.cache[manifest] = raw
    spec = build_spec(raw)
    old_pin = spec["custody_capsule_manifest"]
    old_path = matrix.canonical(old_pin["path"])
    old_root = old_path.parent
    old_reader = portable.BundleReader(old_root)
    old_raw = old_reader.read_body(old_path, child_capsule.MAX_CAPSULE_MANIFEST_BYTES)
    old_reader.reserve(len(old_raw))
    old_reader.cache[old_path] = old_raw
    _cap, old_files, old_dirs = child_capsule.inventory(old_raw, old_pin["sha256"])
    archive.exact_seals(old_root, old_files, old_dirs, old_reader)
    data = custody(spec, old_raw, old_reader.body)
    repo = data["repository"]
    matrix.canonical(repo["root"], directory=True)
    child_capsule.fresh(output, [manifest.parent, old_root, *data["scopes"]])
    objects = {}

    class TraceObjects(matrix.GitObjects):
        def command(self, args, limit):
            selected = len(args) == 3 and args[:2] in (
                ["cat-file", "commit"],
                ["cat-file", "tree"],
                ["cat-file", "blob"],
            )
            key = self.name, args[2] if len(args) == 3 else None
            if selected:
                matrix.need(
                    key in objects or len(objects) < MAX_OBJECTS,
                    "producer object count reached before body read",
                )
            body = super().command(args, limit)
            if selected:
                value = {"kind": args[1], "raw": body}
                matrix.need(key not in objects or objects[key] == value, "producer Git identity drifted")
                objects[key] = value
            return body

    git_capture = matrix.Capture()
    review, source_bodies = scan(data, TraceObjects(repo, git_capture))
    after, after_bodies = scan(data, TraceObjects(repo, git_capture))
    matrix.need(
        review == after and source_bodies == after_bodies,
        "producer selected Git source stability differs",
    )
    output.mkdir()
    root = output / "capsule"
    root.mkdir()
    writer = portable.Writer(root)
    source_manifest = writer.put("provenance/build_input.json", raw)
    custody_files = []
    for original in sorted(data["used"] | {child_capsule.CAPSULE_FILENAME}):
        body = old_raw if original == child_capsule.CAPSULE_FILENAME else old_reader.body(old_files[original])
        custody_files.append({"original_relative_path": original, **writer.put("custody/" + original, body)})
    object_rows = []
    for (name, oid), value in sorted(objects.items()):
        object_rows.append(
            {
                "repository": name,
                "oid": oid,
                "kind": value["kind"],
                **writer.put("git_objects/" + name + "/" + oid, value["raw"]),
            }
        )
    source_files = [
        {"source_path": path, **writer.put("sources/" + repo["name"] + "/" + path, body)}
        for path, body in sorted(source_bodies.items())
    ]
    tools = []
    for relative in sorted(TOOL_FILES):
        path = Path(__file__).resolve().parent / Path(relative).name
        tools.append(writer.put(relative, capture.read(path)))
    dirs = child_capsule.required_directories(set(writer.files), {repo["name"]})
    for name in sorted(dirs, key=lambda n: (len(Path(n).parts), n)):
        (root / name).mkdir(exist_ok=True)
    value = {
        "schema": CAPSULE_SCHEMA,
        "source_manifest": source_manifest,
        "custody_files": custody_files,
        "repository": {key: repo[key] for key in ("name", "commit", "package_roots")},
        "objects": object_rows,
        "source_files": source_files,
        "implementation": tools,
        "expected_review": review,
        "files": sorted(writer.files.values(), key=lambda r: r["path"]),
        "directories": sorted(dirs),
        "custody_capsule_manifest_sha256": old_pin["sha256"],
        "original_input_paths": {
            "build_manifest": str(manifest),
            "custody_capsule_manifest": str(old_path),
        },
        "omissions": OMISSIONS,
        **dict.fromkeys(FALSE_FLAGS, False),
    }
    capsule_raw = matrix.json_bytes(value)
    digest = matrix.sha(capsule_raw)
    _cap, selected, dirs = inventory(capsule_raw, digest)
    (root / CAPSULE_FILENAME).write_bytes(capsule_raw)
    for name in selected:
        (root / name).chmod(0o444)
    for name in dirs:
        (root / name).chmod(0o555)
    root.chmod(0o555)
    verified = capsule_verify(root, digest, output / "source_verification")
    copied = portable.BundleReader(root)
    entries = {name + "/": b"" for name in dirs}
    entries.update({name: copied.body(pin) for name, pin in selected.items()})
    encoded = archive.encode(entries)
    members(archive.decode(encoded), digest)
    matrix.need(
        capture.stability()["unchanged"] and old_reader.stability()["unchanged"] and copied.stability()["unchanged"],
        "producer original/copied input drift refused",
    )
    archive.exact_seals(old_root, old_files, old_dirs, old_reader)
    archive.exact_seals(root, selected, dirs, copied)
    archive_path = output / "producer_sources.zip"
    with archive_path.open("xb") as stream:
        stream.write(encoded)
    archive_path.chmod(0o444)
    pin = {"path": str(archive_path), "sha256": matrix.sha(encoded), "size_bytes": len(encoded)}
    verify_spec = {
        "schema": INPUT_SCHEMA,
        "archive": pin,
        "capsule_manifest_sha256": digest,
        "custody_capsule_manifest_sha256": old_pin["sha256"],
    }
    spec_path = output / "archive_input.json"
    spec_raw = matrix.json_bytes(verify_spec)
    spec_path.write_bytes(spec_raw)
    written = archive.PinnedReader()
    written.read(archive_path, len(encoded), pin["sha256"], len(encoded))
    written.read(spec_path, len(spec_raw), matrix.sha(spec_raw), len(spec_raw))
    matrix.need(
        capture.stability()["unchanged"]
        and old_reader.stability()["unchanged"]
        and copied.stability()["unchanged"]
        and written.stability()["unchanged"],
        "final producer build drift refused",
    )
    archive.exact_seals(old_root, old_files, old_dirs, old_reader)
    archive.exact_seals(root, selected, dirs, copied)
    result = {
        **verified,
        "schema": "codebase-ir-producer-source-bindings-build@1",
        "manifest_sha256": matrix.sha(raw),
        "archive_sha256": pin["sha256"],
        "archive_bytes": len(encoded),
        "archive_roundtrip_verified": False,
        "build_read_only_git_invoked": True,
    }
    for flag in ("git_executable_invoked", "original_paths_read"):
        result.pop(flag)
    (output / "producer_source_bindings_build.json").write_bytes(matrix.json_bytes(result))
    return result


def verify(manifest: Path, output: Path) -> dict:
    reader = archive.PinnedReader()
    manifest = matrix.canonical(str(manifest))
    raw = reader.read(manifest, archive.MAX_MANIFEST_BYTES)
    spec = matrix.document(raw)
    matrix.fields(
        spec,
        {"schema", "archive", "capsule_manifest_sha256", "custody_capsule_manifest_sha256"},
        "producer verification input",
    )
    matrix.need(
        spec["schema"] == INPUT_SCHEMA
        and matrix.exact_hex(spec["capsule_manifest_sha256"])
        and matrix.exact_hex(spec["custody_capsule_manifest_sha256"]),
        "producer verification pins/schema refused",
    )
    pin = archive.descriptor(spec["archive"])
    child_capsule.fresh(output, [manifest.parent, Path(pin["path"]).parent])
    encoded = reader.read(Path(pin["path"]), archive.MAX_ARCHIVE_BYTES, pin["sha256"], pin["size_bytes"])
    entries = archive.decode(encoded)
    cap, selected, dirs = members(entries, spec["capsule_manifest_sha256"])
    matrix.need(
        cap["custody_capsule_manifest_sha256"] == spec["custody_capsule_manifest_sha256"],
        "producer external custody capsule binding differs",
    )
    # Protect original labels before creating any restored file; they are never opened.
    source = build_spec(entries[cap["source_manifest"]["path"]])
    original_map = {row["original_relative_path"]: entries[row["path"]] for row in cap["custody_files"]}
    data = custody(source, original_map[child_capsule.CAPSULE_FILENAME], lambda row: original_map[row["path"]])
    labels = cap["original_input_paths"]
    matrix.fields(labels, {"build_manifest", "custody_capsule_manifest"}, "producer original labels")
    protected = list(data["scopes"])
    for value in labels.values():
        matrix.need(
            type(value) is str
            and Path(value).is_absolute()
            and str(Path(value)) == value
            and ".." not in Path(value).parts,
            "absolute lexical producer original label required",
        )
        protected.append(Path(value).parent)
    child_capsule.fresh(output, protected)
    output.mkdir()
    root = output / "capsule"
    root.mkdir()
    for name in sorted(dirs, key=lambda n: (len(Path(n).parts), n)):
        (root / name).mkdir()
    for name in selected:
        with (root / name).open("xb") as stream:
            stream.write(entries[name])
        (root / name).chmod(0o444)
    for name in dirs:
        (root / name).chmod(0o555)
    root.chmod(0o555)
    restored = capsule_verify(root, spec["capsule_manifest_sha256"], output / "restored_verification")
    report_path = output / "restored_verification/producer_source_custody.json"
    report_raw = matrix.Capture().read_body(report_path, matrix.MAX_FILE_BYTES)
    matrix.need(report_raw == matrix.json_bytes(restored), "producer restored report copy differs")
    final_reader = portable.BundleReader(root)
    for row in selected.values():
        final_reader.body(row)
    matrix.need(
        reader.stability()["unchanged"] and final_reader.stability()["unchanged"],
        "producer archive/restored drift refused",
    )
    archive.exact_seals(root, selected, dirs, final_reader)
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
        "input_stability": reader.stability(),
    }
    matrix.need(
        result["input_stability"]["unchanged"]
        and reader.stability()["unchanged"]
        and final_reader.stability()["unchanged"],
        "final producer archive/restored drift refused",
    )
    archive.exact_seals(root, selected, dirs, final_reader)
    (output / "producer_source_bindings.json").write_bytes(matrix.json_bytes(result))
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    for name in ("build", "verify"):
        item = sub.add_parser(name)
        item.add_argument("--manifest", type=Path, required=True)
        item.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build(args.manifest, args.output) if args.operation == "build" else verify(args.manifest, args.output)
    except (ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
        print("producer source bindings refused: " + str(exc), file=sys.stderr)
        return 2
    print(
        matrix.json_bytes(
            {
                key: result[key]
                for key in (
                    "status",
                    "archive_sha256",
                    "capsule_manifest_sha256",
                    "claim_membership_count",
                    "unique_source_path_count",
                    "verified_source_membership_count",
                )
            }
        ).decode(),
        end="",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
