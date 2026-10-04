#!/usr/bin/env python3
"""Retain explicitly listed released evidence children without executing them."""

from __future__ import annotations

import argparse
import collections
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_matrix as matrix

INPUT_SCHEMA = "codebase-ir-released-evidence-children-input@1"
SCHEMA = "codebase-ir-released-evidence-children-audit@1"
POLICY = "one_level_explicit_files@1"
SUPPORTED = {"repository-evidence-files@1": "bytes", "codebase-source384-acceptance-evidence@1": "bytes",
             "closed-local-evidence-manifest@1": "size_bytes", "retained-evidence-manifest@1": "size_bytes"}
MAX_MANIFEST_BYTES = 256 * 1024
MAX_MANIFESTS = 16
MAX_CHILDREN = 256
MAX_DECLARED_BYTES = 32 * 1024 * 1024
FALSE_FLAGS = (*matrix.FALSE_FLAGS, "producer_signatures_authenticated", "checker_executions_replayed",
               "numerical_outputs_replayed", "runtime_dependency_closure_qualified",
               "runtime_environment_qualified", "transitive_child_expansion_performed")


def input_spec(value: dict) -> None:
    matrix.fields(value, {"schema", "repositories", "ledger", "selected_evidence", "expansion_policy"},
                  "released child input")
    matrix.need(value["schema"] == INPUT_SCHEMA and value["expansion_policy"] == POLICY,
                "unsupported child input schema/expansion policy")
    matrix.need(type(value["repositories"]) is list and 1 <= len(value["repositories"]) <= 4,
                "bounded repository population required")
    names, roots = set(), set()
    for row in value["repositories"]:
        matrix.fields(row, {"name", "root", "commit", "package_roots"}, "repository")
        matrix.need(matrix.text(row["name"]) and row["name"].isidentifier()
                    and matrix.exact_hex(row["commit"], 40), "immutable repository identity required")
        root = matrix.canonical(row["root"], directory=True)
        matrix.need(row["name"] not in names and root not in roots, "duplicate repository identity")
        names.add(row["name"])
        roots.add(root)
        matrix.need(type(row["package_roots"]) is list and 1 <= len(row["package_roots"]) <= 8
                    and all(type(x) is str and x.isidentifier() for x in row["package_roots"])
                    and len(set(row["package_roots"])) == len(row["package_roots"]),
                    "bounded exact package roots required")
    matrix.fields(value["ledger"], {"repository", "path", "sha256"}, "ledger pin")
    ledger = value["ledger"]
    matrix.need(type(ledger["repository"]) is str and ledger["repository"] in names
                and matrix.exact_hex(ledger["sha256"]), "ledger pin malformed")
    matrix.need(matrix.relative(ledger["path"]).startswith("docs/"), "public ledger path required")
    selected = value["selected_evidence"]
    matrix.need(type(selected) is list and 1 <= len(selected) <= MAX_MANIFESTS
                and all(type(x) is str and x and len(x) <= 128
                        and all(c.isascii() and (c.isalnum() or c in "-_") for c in x) for x in selected)
                and len(set(selected)) == len(selected), "bounded unique evidence IDs required")


def preflight(manifest: Path, spec: dict, output: Path) -> None:
    input_spec(spec)
    matrix.need(output.is_absolute() and str(output) == str(output.resolve())
                and output.parent.resolve(strict=True) == output.parent and not output.exists()
                and not any(p.is_symlink() for p in output.parents), "fresh canonical output required")
    protected = [manifest.parent, *(matrix.canonical(r["root"], directory=True) for r in spec["repositories"])]
    matrix.need(not any(output.is_relative_to(root) for root in protected),
                "output lies inside an original input scope")
    matrix.need(all(stat.S_IMODE(p.stat().st_mode) & 0o222 for p in output.parents),
                "output descends from a sealed directory")


def explicit_files(raw: bytes) -> tuple[str | None, list[dict] | None]:
    matrix.need(len(raw) <= MAX_MANIFEST_BYTES, "evidence manifest byte ceiling reached")
    value = matrix.document(raw)
    schema = value.get("schema")
    if type(schema) is not str or schema not in SUPPORTED:
        return schema if type(schema) is str else None, None
    matrix.fields(value, {"schema", "files"}, "explicit evidence manifest")
    rows = value["files"]
    matrix.need(type(rows) is list and len(rows) <= MAX_CHILDREN,
                "explicit child population ceiling reached")
    size_field = SUPPORTED[schema]
    normalized = []
    for row in rows:
        matrix.fields(row, {"path", "sha256", size_field}, "explicit child pin")
        matrix.relative(row["path"])
        matrix.need("\\" not in row["path"] and ":" not in row["path"]
                    and not any(ord(c) < 32 for c in row["path"]), "platform/path control alias refused")
        matrix.need(matrix.exact_hex(row["sha256"]) and type(row[size_field]) is int
                    and 0 <= row[size_field] <= matrix.MAX_FILE_BYTES, "bounded exact child pins required")
        normalized.append({"path": row["path"], "sha256": row["sha256"], "bytes": row[size_field]})
    return schema, normalized


def cycle_edges(graph: dict[str, set[str]]) -> set[tuple[str, str]]:
    result = set()
    for start, successors in graph.items():
        for successor in successors:
            frontier, visited = [successor], set()
            while frontier:
                node = frontier.pop()
                if node == start:
                    result.add((start, successor))
                    break
                if node not in visited:
                    visited.add(node)
                    frontier.extend(graph.get(node, set()) - visited)
    return result


def retained_view(output: Path, copies: dict[str, bytes], capture: matrix.Capture) -> list[dict]:
    rows = []
    for relative, raw in sorted(copies.items()):
        capture.time_check()
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        path.chmod(0o444)
        rows.append({"path": str(path), "relative_path": relative,
                     "sha256": matrix.sha(raw), "size_bytes": len(raw)})
    directories = {output / prefix for prefix in ("inputs", "manifests", "children") if (output / prefix).exists()}
    for row in rows:
        path = Path(row["path"]).parent
        while path != output:
            directories.add(path)
            path = path.parent
    for path in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        path.chmod(0o555)
    return rows


def verify_retained(output: Path, copies: dict[str, bytes], capture: matrix.Capture) -> dict:
    expected_files = set(copies)
    expected_dirs = set()
    for name in expected_files:
        parent = Path(name).parent
        while parent != Path("."):
            expected_dirs.add(parent.as_posix())
            parent = parent.parent
    files, dirs, frontier = set(), set(), [output]
    while frontier:
        capture.time_check()
        directory = frontier.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                name = Path(entry.path).relative_to(output).as_posix()
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    matrix.need(name in expected_dirs and stat.S_IMODE(info.st_mode) == 0o555,
                                "retained directory population/seal differs")
                    dirs.add(name)
                    frontier.append(Path(entry.path))
                else:
                    matrix.need(name in expected_files and stat.S_ISREG(info.st_mode)
                                and stat.S_IMODE(info.st_mode) == 0o444, "retained file population/type/seal differs")
                    files.add(name)
                    matrix.need(capture.read_body(Path(entry.path), len(copies[name])) == copies[name],
                                "retained evidence bytes changed")
    matrix.need(files == expected_files and dirs == expected_dirs, "retained exact population differs")
    return {"unchanged": True, "files": len(files), "directories": len(dirs),
            "bytes": sum(len(raw) for raw in copies.values())}


def git_stability(spec: dict, capture: matrix.Capture, original: dict) -> dict:
    rows = []
    for repo_spec in spec["repositories"]:
        before = original[repo_spec["name"]]
        after = matrix.GitObjects(repo_spec, capture)
        matrix.need(before.root_tree == after.root_tree, "pinned commit root changed")
        for path, (observed, raw) in before.cache.items():
            now, body = after.blob(path)
            matrix.need(now == observed and body == raw, "selected Git evidence changed during audit")
            rows.append({"repository": before.name, "commit": before.commit, "path": path,
                         "unchanged": True, "disposition": observed["disposition"]})
    return {"unchanged": True, "selected_paths": rows,
            "scope": "fresh independently hashed commit/tree/blob reads at the same immutable pins"}


def audit(manifest: Path, output: Path) -> dict:
    capture = matrix.Capture()
    manifest = matrix.canonical(str(manifest))
    raw_input = capture.read_body(manifest, MAX_MANIFEST_BYTES)
    capture.reserve(len(raw_input))
    capture.cache[manifest] = raw_input
    spec = matrix.document(raw_input)
    preflight(manifest, spec, output)
    repos = {row["name"]: matrix.GitObjects(row, capture) for row in spec["repositories"]}
    aliases = {package: name for name, repo in repos.items() for package in repo.packages}
    matrix.need(len(aliases) == sum(len(repo.packages) for repo in repos.values())
                and all(package not in repos or package == name for package, name in aliases.items()),
                "ambiguous package ownership")
    ledger_pin = spec["ledger"]
    ledger_observed, ledger_raw = repos[ledger_pin["repository"]].blob(ledger_pin["path"])
    matrix.need(ledger_raw is not None and matrix.sha(ledger_raw) == ledger_pin["sha256"],
                "released ledger absent/unread/different")
    ledger = matrix.document(ledger_raw)
    matrix.validate_ledger(ledger)
    selected = spec["selected_evidence"]
    matrix.need(all(eid in ledger["evidence"] for eid in selected), "unknown selected evidence ID")
    copies = {"inputs/manifest.json": raw_input, "inputs/ledger.json": ledger_raw}
    manifests, prepared, root_keys = [], {}, {}
    for eid in selected:
        pin = ledger["evidence"][eid]
        declared_repo = pin.get("repository", ledger_pin["repository"])
        repo_name = aliases.get(declared_repo, declared_repo)
        matrix.need(repo_name in repos, "unknown evidence repository")
        path = matrix.relative(pin["path"])
        matrix.need(path.startswith("docs/") and path.endswith(".json"), "public JSON evidence manifest required")
        key = repo_name, path
        matrix.need(key not in root_keys, "selected manifest alias refused")
        root_keys[key] = eid
        observed, raw = repos[repo_name].blob(path)
        row = {"id": eid, **observed, "expected_sha256": pin["sha256"], "children": []}
        if raw is None:
            row["disposition"] = observed["disposition"]
        elif matrix.sha(raw) != pin["sha256"]:
            row["disposition"] = "different"
        else:
            copies[f"manifests/{eid}.json"] = raw
            schema, children = explicit_files(raw)
            row.update(schema=schema, disposition="expanded" if children is not None else "unsupported_schema")
            if children is not None:
                prepared[eid] = (repo_name, path, children)
        manifests.append(row)
    declared_count = sum(len(item[2]) for item in prepared.values())
    declared_bytes = sum(child["bytes"] for item in prepared.values() for child in item[2])
    matrix.need(declared_count <= MAX_CHILDREN and declared_bytes <= MAX_DECLARED_BYTES,
                "aggregate declared child population/byte ceiling reached")
    graph = {eid: set() for eid in selected}
    global_memberships = collections.defaultdict(list)
    by_id = {r["id"]: r for r in manifests}
    for eid, (repo_name, parent, children) in prepared.items():
        local = set()
        for index, pin in enumerate(children):
            capture.time_check()
            path = matrix.relative((Path(parent).parent / pin["path"]).as_posix())
            key = repo_name, path
            child = {"index": index, "declared_relative_path": pin["path"], "path": path,
                     "repository": repo_name, "commit": repos[repo_name].commit,
                     "expected_sha256": pin["sha256"], "expected_size_bytes": pin["bytes"],
                     "retained_copy": None, "shared_body": key in global_memberships}
            if pin["path"] in local:
                child["disposition"] = "repeated_entry"
            else:
                local.add(pin["path"])
                global_memberships[key].append(eid)
                if key in root_keys:
                    child.update(disposition="selected_manifest_reference_not_expanded", referenced_manifest=root_keys[key])
                    graph[eid].add(root_keys[key])
                else:
                    observed, body = repos[repo_name].blob(path)
                    child.update(observed)
                    if body is not None:
                        child["disposition"] = "verified" if len(body) == pin["bytes"] and matrix.sha(body) == pin["sha256"] else "different"
                        name = f"children/{repo_name}/{repos[repo_name].commit}/{path}"
                        copies[name] = body
                        child["retained_copy"] = {"path": str(output / name), "sha256": matrix.sha(body),
                                                  "size_bytes": len(body)}
            by_id[eid]["children"].append(child)
    cyclic = cycle_edges(graph)
    for parent in manifests:
        for child in parent["children"]:
            if (parent["id"], child.get("referenced_manifest")) in cyclic:
                child["disposition"] = "cyclic_manifest_reference"
    before_copy = capture.stability()
    matrix.need(before_copy["unchanged"], "original input changed before retention")
    output.mkdir()
    retained = retained_view(output, copies, capture)
    retained_before = verify_retained(output, copies, capture)
    git_after = git_stability(spec, capture, repos)
    stability = capture.stability()
    matrix.need(stability["unchanged"], "original input changed before publication")
    retained_after = verify_retained(output, copies, capture)
    children = [child for row in manifests for child in row["children"]]
    verified = all(row["disposition"] == "expanded" for row in manifests) and all(c["disposition"] == "verified" for c in children)
    report = {"schema": SCHEMA, "status": "passed", "manifest_sha256": matrix.sha(raw_input),
              "ledger_sha256": ledger_pin["sha256"], "ledger": ledger_observed,
              "scope": "one-level declared released public child byte custody; no recursive or semantic replay",
              "expansion_policy": POLICY, "supported_manifest_schemas": sorted(SUPPORTED),
              "repositories": [{"name": r.name, "root": str(r.root), "commit": r.commit} for r in repos.values()],
              "manifests": manifests, "manifest_dispositions": dict(collections.Counter(r["disposition"] for r in manifests)),
              "child_dispositions": dict(collections.Counter(c["disposition"] for c in children)),
              "manifest_count": len(manifests), "declared_child_count": declared_count,
              "verified_child_count": sum(c["disposition"] == "verified" for c in children),
              "unique_child_body_count": len([name for name in copies if name.startswith("children/")]),
              "declared_child_bytes": declared_bytes, "retained_copies": retained,
              "retained_before": retained_before, "retained_after": retained_after,
              "all_selected_children_verified": verified, "child_evidence_custody_inventory_produced": True,
              "git_object_verification_performed": True, "read_only_git_invoked": True,
              "input_files_unchanged": True, "input_stability": stability, "git_input_stability": git_after,
              "bounds": {"max_manifest_bytes": MAX_MANIFEST_BYTES, "max_manifests": MAX_MANIFESTS,
                         "max_child_rows": MAX_CHILDREN, "max_declared_child_bytes": MAX_DECLARED_BYTES,
                         "max_file_bytes": matrix.MAX_FILE_BYTES,
                         "max_aggregate_input_git_read_bytes": matrix.MAX_TOTAL_BYTES,
                         "max_git_commands": matrix.MAX_COMMANDS, "max_seconds": matrix.MAX_SECONDS,
                         "aggregate_input_git_read_bytes": capture.total_bytes,
                         "aggregate_input_git_read_scope": "original manifest plus initial and fresh Git object bodies; local stability and retained-copy checks have separate equal-size budgets",
                         "local_stability_bytes_per_check": len(raw_input),
                         "retained_bytes_per_check": retained_after["bytes"],
                         "git_commands": capture.git_commands},
              **dict.fromkeys(FALSE_FLAGS, False)}
    capture.time_check()
    (output / "evidence_children.json").write_bytes(matrix.json_bytes(report))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = audit(args.manifest, args.output)
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        print("released child evidence refused: " + str(exc), file=sys.stderr)
        return 2
    print(matrix.json_bytes({key: report[key] for key in ("status", "manifest_sha256", "manifest_count",
                                                         "verified_child_count", "child_dispositions")}).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
