#!/usr/bin/env python3
"""Nominate bounded retained imports for one recorded snapshot frontier.

Legacy capture bytes remain an earlier static source basis, without a claim that
the original producer or a runtime dependency closure has been reproduced.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import os
import stat
from collections import deque
from pathlib import Path

from audit import digest, json_bytes
from retained_provenance import document, exact_sha, need
from snapshot_verify import verify_snapshot

SCHEMA = "codebase-ir-retained-static-supplement/v1"
MAX_MANIFEST_BYTES = 4 * 1024 * 1024
MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_INPUT_BYTES = 64 * 1024 * 1024
MAX_STATIC_FILES = 2400
MAX_STATIC_BYTES = 64 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_FILES = 512
MAX_BYTES = 16 * 1024 * 1024
MAX_AST_NODES = 100000
MAX_IMPORTS = 8192
MAX_RETAINED_METADATA_FILES = 4096


class Capture:
    """Retain selected descriptor reads; reread their exact pins separately."""
    def __init__(self):
        self.records = {}
        self.total = 0

    @staticmethod
    def read_regular(path: Path, limit: int) -> bytes:
        need(path.is_absolute() and path.resolve(strict=True) == path
             and not any(p.is_symlink() for p in (path, *path.parents)),
             "canonical non-symlink retained path required")
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            need(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
                 "bounded regular retained source/artifact required")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            current = path.stat(follow_symlinks=False)
        def identity(value):
            return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns
        need(identity(before) == identity(after) == identity(current) and len(raw) == before.st_size
             and path.resolve(strict=True) == path, "retained source/artifact changed during read")
        return raw

    def read(self, path: Path, limit: int, sha256: str, size: int | None = None) -> bytes:
        need(exact_sha(sha256), "explicit retained artifact SHA256 required")
        if path not in self.records:
            need(len(self.records) < MAX_FILES + 5, "supplement input file cap exceeded")
            raw = self.read_regular(path, min(limit, MAX_INPUT_BYTES - self.total))
            self.total += len(raw)
            self.records[path] = raw
        raw = self.records[path]
        need(len(raw) <= limit and digest(raw) == sha256 and (size is None or len(raw) == size),
             "supplement retained bytes differ from explicit pin")
        return raw

    def stability(self) -> dict:
        rows = []
        for path, raw in sorted(self.records.items()):
            try:
                after = digest(self.read_regular(path, len(raw)))
                rows.append({"path": str(path), "before_sha256": digest(raw), "after_sha256": after,
                             "unchanged": after == digest(raw)})
            except (ValueError, OSError) as exc:
                rows.append({"path": str(path), "before_sha256": digest(raw), "after_sha256": None,
                             "unchanged": False, "error": str(exc)})
        return {"stable": all(row["unchanged"] for row in rows), "files": rows,
                "scope": "selected inputs sequentially reread; first captures capped at64MiB; rereads bounded by captured sizes"}


def module_paths(module: str, owners: dict) -> list[tuple[str, str]]:
    need(type(module) is str and module and all(part.isidentifier() for part in module.split(".")),
         "exact Python module name required")
    package = module.split(".", 1)[0]
    if package not in owners:
        return []
    prefix = module.replace(".", "/")
    return [(owners[package], prefix + ".py"), (owners[package], prefix + "/__init__.py")]


def _pin(row: dict, specs: dict, *, require_package: bool = True) -> tuple[str, str]:
    need(type(row) is dict and set(row) == {"repository", "path", "sha256", "bytes"}
         and type(row["repository"]) is str and row["repository"] in specs
         and type(row["path"]) is str and exact_sha(row["sha256"])
         and type(row["bytes"]) is int and 0 <= row["bytes"] <= MAX_FILE_BYTES,
         "exact bounded legacy source pin required")
    path = Path(row["path"])
    need(not path.is_absolute() and path.as_posix() == row["path"] and path.parts
         and all(part not in {".", ".."} and not part.startswith(".") for part in path.parts)
         and (not require_package or path.parts[0] in specs[row["repository"]]["packages"]) and path.suffix == ".py",
         "legacy source lacks exact package ownership")
    return row["repository"], row["path"]


def retained_copy_inventory(*, before_path: Path, before_sha256: str, after_path: Path,
                            after_sha256: str, workspace: Path, specs: dict, capture: Capture) -> dict:
    """Validate original copied-source metadata without reading all its bodies."""
    need(workspace.is_absolute() and workspace.resolve(strict=True) == workspace,
         "canonical retained-copy workspace required")
    need(before_path.parent == after_path.parent, "original retained copy before/after artifacts must share exact scope")
    before = document(capture.read(before_path, MAX_MANIFEST_BYTES, before_sha256))
    after = document(capture.read(after_path, MAX_MANIFEST_BYTES, after_sha256))
    fields = {"schema", "scope", "source_count", "sources"}
    need(set(before) == fields and set(after) == fields | {"changes"}
         and before["schema"] == after["schema"] == "finite-admission-selected-source-snapshot@1"
         and type(before["scope"]) is str and type(after["scope"]) is str
         and type(before["source_count"]) is int and type(after["source_count"]) is int
         and type(before["sources"]) is list and type(after["sources"]) is list
         and 0 < len(before["sources"]) == len(after["sources"]) == before["source_count"] == after["source_count"] <= MAX_RETAINED_METADATA_FILES
         and after["changes"] == [], "stable exact original copied-source metadata required")
    def normalize(row, extra):
        need(type(row) is dict and set(row) == {"path", "sha256", "size_bytes"} | extra
             and type(row["path"]) is str and exact_sha(row["sha256"])
             and type(row["size_bytes"]) is int and 0 <= row["size_bytes"] <= MAX_INPUT_BYTES,
             "exact original copied-source pin required")
        original = Path(row["path"])
        need(original.is_absolute() and str(original) == row["path"] and original.is_relative_to(workspace)
             and not any(part in {".", ".."} or part.startswith(".") for part in original.parts),
             "exact original source path required")
        owners = [(name, original.relative_to(Path(spec["root"]).resolve(strict=True)).as_posix())
                  for name, spec in specs.items() if original.is_relative_to(Path(spec["root"]).resolve(strict=True))]
        need(len(owners) == 1 and original.suffix == ".py", "original copied source lacks unique repository ownership")
        if extra:
            need(type(row["retained_source"]) is str, "exact retained source path required")
            retained = Path(row["retained_source"])
            need(str(retained) == row["retained_source"] and retained == before_path.parent / "sources" / original.relative_to(workspace),
                 "retained copy does not bind exact original source path")
        return owners[0]
    ending = {}
    for row in after["sources"]:
        key = normalize(row, set())
        need(key not in ending, "duplicate original ending source path")
        ending[key] = row
    result = {}
    for row in before["sources"]:
        key = normalize(row, {"retained_source"})
        need(key not in result and key in ending and all(row[field] == ending[key][field] for field in ("path", "sha256", "size_bytes")),
             "original copied-source before/after conflict")
        result[key] = {"repository": key[0], "path": key[1], "sha256": row["sha256"], "bytes": row["size_bytes"],
                       "source_path": row["retained_source"], "before": row, "after": ending[key]}
    need(set(result) == set(ending), "original copied-source populations differ")
    return result


def build_profile(*, snapshot_root: Path, snapshot_manifest_sha256: str, source_report: Path,
                  source_report_sha256: str, frontier_report: Path, frontier_report_sha256: str,
                  module: str, initial_snapshot: Path, initial_snapshot_sha256: str,
                  config: dict, retained_before: Path | None = None, retained_before_sha256: str | None = None,
                  retained_after: Path | None = None, retained_after_sha256: str | None = None,
                  workspace: Path | None = None) -> tuple[dict, Capture]:
    specs = {spec["name"]: spec for spec in config["repositories"]}
    need(len(specs) == len(config["repositories"]), "unique supplemental owners required")
    owners = {package: name for name, spec in specs.items() for package in spec["packages"]}
    need(len(owners) == sum(len(spec["packages"]) for spec in specs.values()), "unique package ownership required")
    need(snapshot_root.resolve(strict=True) == snapshot_root and snapshot_root.is_dir()
         and not snapshot_root.stat().st_mode & 0o222, "canonical sealed legacy snapshot root required")
    capture = Capture()
    manifest_raw = capture.read(snapshot_root / "snapshot.json", MAX_MANIFEST_BYTES, snapshot_manifest_sha256)
    manifest = document(manifest_raw)
    need(set(manifest) == {"schema", "source", "files", "manifest_sha256"}
         and manifest["schema"] == "codebase-ir-release-audit/v1"
         and manifest["source"] == "captured_closure_bytes" and type(manifest["files"]) is list
         and 0 < len(manifest["files"]) <= MAX_STATIC_FILES
         and manifest["manifest_sha256"] == digest(json_bytes(manifest["files"])),
         "exact legacy captured manifest required")
    rows = {}
    total = 0
    for row in manifest["files"]:
        key = _pin(row, specs, require_package=False)
        need(key not in rows, "duplicate legacy source path")
        rows[key] = row
        total += row["bytes"]
        need(total <= MAX_STATIC_BYTES, "legacy captured byte cap exceeded")
    # Verify the precise legacy file/directory population and seals without
    # treating unselected source bytes as independently requalified.
    expected_files = {snapshot_root / repo / path for repo, path in rows} | {snapshot_root / "snapshot.json"}
    expected_directories = {snapshot_root}
    for path in expected_files:
        expected_directories.update(p for p in path.parents if p.is_relative_to(snapshot_root))
    actual_files, actual_directories = set(), {snapshot_root}
    for path in snapshot_root.rglob("*"):
        need(len(actual_files) + len(actual_directories) <= MAX_STATIC_FILES * 12,
             "legacy filesystem entry cap exceeded")
        metadata = path.stat(follow_symlinks=False)
        need(path.resolve(strict=True) == path and not stat.S_ISLNK(metadata.st_mode)
             and not metadata.st_mode & 0o222, "legacy snapshot alias or writable entry refused")
        if stat.S_ISREG(metadata.st_mode):
            actual_files.add(path)
        elif stat.S_ISDIR(metadata.st_mode):
            actual_directories.add(path)
        else:
            need(False, "legacy non-regular filesystem entry refused")
    need(actual_files == expected_files and actual_directories == expected_directories,
         "legacy exact filesystem population differs from manifest")
    report_raw = capture.read(source_report, MAX_REPORT_BYTES, source_report_sha256)
    report = document(report_raw)
    need(report.get("schema") == manifest["schema"] and report.get("runtime_closure_proven") is False
         and type(report.get("static_closure_complete")) is bool and type(report.get("files")) is list
         and len(report["files"]) == len(rows), "original static capture report required")
    recorded = {}
    for row in report["files"]:
        need(type(row) is dict and {"repository", "path", "sha256", "bytes"} <= set(row),
             "original capture source pin required")
        pin = {key: row[key] for key in ("repository", "path", "sha256", "bytes")}
        key = _pin(pin, specs, require_package=False)
        need(key not in recorded and key in rows and pin == rows[key], "original report/source manifest pin mismatch")
        recorded[key] = row
    stable_rows = {}
    for field in ("source_stability", "source_stability_after_probes"):
        stability = report.get(field)
        need(type(stability) is dict and stability.get("stable") is True
             and type(stability.get("files")) is list and type(stability.get("heads")) is list,
             "original before/after capture stability required")
        observed = {}
        for item in stability["files"]:
            need(type(item) is dict and set(item) == {"repository", "path", "before_sha256", "after_sha256", "stable"},
                 "exact original stability row required")
            key = item["repository"], item["path"]
            need(key not in observed and key in rows and item["stable"] is True
                 and item["before_sha256"] == item["after_sha256"] == rows[key]["sha256"],
                 "original selected source stability conflict")
            observed[key] = item
        need(set(observed) == set(rows) and len(stability["heads"]) == len(specs)
             and {row.get("repository") for row in stability["heads"] if type(row) is dict} == set(specs)
             and all(type(row) is dict and set(row) == {"repository", "before", "after"}
                     and type(row["before"]) is str and len(row["before"]) == 40
                     and all(c in "0123456789abcdef" for c in row["before"])
                     and row["before"] == row["after"] for row in stability["heads"]),
             "original stability population or Git HEAD drift")
        stable_rows[field] = observed
    prior = verify_snapshot(initial_snapshot, initial_snapshot_sha256)
    prior_rows = {(row["repository"], row["path"]): row for row in prior["files"]}
    supplied = (retained_before, retained_before_sha256, retained_after, retained_after_sha256, workspace)
    need(all(value is None for value in supplied) or all(value is not None for value in supplied),
         "original retained copy supplement requires both input paths/pins and workspace")
    retained_rows, retained_pair = {}, None
    if retained_before is not None:
        retained_rows = retained_copy_inventory(before_path=retained_before, before_sha256=retained_before_sha256,
            after_path=retained_after, after_sha256=retained_after_sha256, workspace=workspace, specs=specs, capture=capture)
        retained_pair = {"before": {"path": str(retained_before), "sha256": retained_before_sha256},
                         "after": {"path": str(retained_after), "sha256": retained_after_sha256},
                         "workspace": str(workspace), "metadata_source_count": len(retained_rows),
                         "all_metadata_source_bytes_requalified": False}
    frontier_raw = capture.read(frontier_report, MAX_MANIFEST_BYTES, frontier_report_sha256)
    frontier = document(frontier_raw)
    need(frontier.get("schema") == "codebase-ir-owner-local-historical-replay@1"
         and frontier.get("status") == "unavailable"
         and frontier.get("runtime_source_mode") == "sealed_snapshot_read_only"
         and frontier.get("blocker") == "ImportError: historical core import unavailable: " + module
         and frontier.get("requested_runtime_snapshot_sha256") == initial_snapshot_sha256
         and frontier.get("runtime_snapshot_identity_stable") is True
         and json_bytes(frontier.get("runtime_snapshot_before")) == json_bytes(frontier.get("runtime_snapshot_after"))
         and type(frontier.get("runtime_snapshot_before")) is dict
         and frontier["runtime_snapshot_before"].get("verified") is True
         and frontier["runtime_snapshot_before"].get("snapshot_sha256") == initial_snapshot_sha256
         and frontier.get("observed_current") is False and frontier.get("worker_launched") is False
         and frontier.get("native_observation_or_proof_invoked") is False
         and type(frontier.get("training_steps")) is int and frontier["training_steps"] == 0
         and frontier.get("read_files_unchanged") is True, "recorded stable sealed import frontier required")
    need(all(json_bytes(frontier["runtime_snapshot_before"].get(field)) == json_bytes(prior[field])
             for field in ("snapshot_root", "snapshot_roots", "generation", "file_count", "bytes", "files", "namespace_directories")),
         "recorded frontier snapshot scope differs from verified prior generation")
    selected, existing, unresolved, external = {}, {}, [], []
    pending = deque([(module, {"kind": "recorded_missing_module", "module": module})])
    seen = set()
    def nominate(name: str, reason: dict, *, attribute: bool = False) -> None:
        need(len(external) + len(unresolved) + len(existing) + len(selected) + len(pending) <= MAX_IMPORTS,
             "supplement import nomination cap exceeded")
        candidates = module_paths(name, owners)
        if not candidates:
            if not attribute:
                external.append({"module": name, **reason})
            return
        found = [key for key in candidates if key in rows or key in prior_rows or key in retained_rows]
        need(len(found) <= 1, "ambiguous retained module/package source")
        if not found:
            if not attribute:
                unresolved.append({"module": name, "reason": "local module absent from explicit retained sources", **reason})
            return
        key = found[0]
        if key in prior_rows:
            existing[key] = {**prior_rows[key], "module": name}
        else:
            pending.append((name, reason))
    while pending:
        name, reason = pending.popleft()
        if name in seen:
            continue
        seen.add(name)
        found = [key for key in module_paths(name, owners) if key in rows or key in prior_rows or key in retained_rows]
        need(len(found) == 1 and found[0] not in prior_rows, "frontier must select a new retained source module")
        key = found[0]
        row = retained_rows.get(key, rows.get(key))
        pin = {field: row[field] for field in ("repository", "path", "sha256", "bytes")}
        _pin(pin, specs)
        source_path = Path(row["source_path"]) if key in retained_rows else snapshot_root / key[0] / key[1]
        raw = capture.read(source_path, MAX_FILE_BYTES, row["sha256"], row["bytes"])
        if key not in retained_rows:
            need(not source_path.stat().st_mode & 0o222, "selected retained legacy source is writable")
        need(len(selected) + len(prior_rows) < MAX_FILES
             and sum(item["bytes"] for item in selected.values()) + sum(item["bytes"] for item in prior_rows.values()) + len(raw) <= MAX_BYTES,
             "supplement union file/byte bound exceeded")
        selected[key] = {**pin, "module": name, "reason": reason, "source_path": str(source_path),
                         "origin": "original_retained_dependency_copy" if key in retained_rows else "earlier_static_capture",
                         "original_capture": {"before": row["before"], "after": row["after"]} if key in retained_rows
                             else {field: stable_rows[field][key] for field in stable_rows},
                         "git_status_at_capture": recorded.get(key, {}).get("git_status")}
        for parent in Path(key[1]).parents:
            if parent == Path("."):
                break
            nominate(parent.as_posix().replace("/", "."), {"kind": "ancestor_initializer", "source_module": name})
        package = name if key[1].endswith("/__init__.py") else name.rpartition(".")[0]
        try:
            tree = ast.parse(raw)
        except (SyntaxError, ValueError, RecursionError) as exc:
            need(False, "retained supplemental syntax unavailable: " + str(exc))
        for index, node in enumerate(ast.walk(tree)):
            need(index < MAX_AST_NODES, "supplement AST node cap exceeded")
            why = {"kind": "all_scope_static_import", "source_module": name, "line": getattr(node, "lineno", 0)}
            if isinstance(node, ast.Import):
                for alias in node.names:
                    nominate(alias.name, why)
            elif isinstance(node, ast.ImportFrom):
                target = importlib.util.resolve_name("." * node.level + (node.module or ""), package) if node.level else node.module
                if target:
                    nominate(target, why)
                    for alias in node.names:
                        if alias.name == "*":
                            unresolved.append({"module": target, "reason": "star import scope unresolved", **why})
                        else:
                            nominate(target + "." + alias.name, why, attribute=True)
            elif isinstance(node, ast.Call) and (isinstance(node.func, ast.Name) and node.func.id == "__import__"
                    or isinstance(node.func, ast.Attribute) and node.func.attr == "import_module"):
                unresolved.append({"module": name, "reason": "dynamic import demand remains unqualified", **why})
    need(selected and not [row for row in unresolved if row["reason"].startswith("local module")],
         "supplement retained local import frontier is unresolved")
    stable = capture.stability()
    need(stable["stable"], "supplement captured source changed during inventory")
    profile = {"schema": SCHEMA, "source_basis": "original_retained_dependency_copies_and_earlier_static_capture_selected_imports"
                   if retained_pair else "earlier_static_capture_selected_imports",
               "legacy_snapshot": {"root": str(snapshot_root), "manifest_sha256": snapshot_manifest_sha256},
               "source_report": {"path": str(source_report), "sha256": source_report_sha256},
               "frontier_report": {"path": str(frontier_report), "sha256": frontier_report_sha256, "module": module},
               "initial_snapshot_sha256": initial_snapshot_sha256,
               "retained_source_pair": retained_pair,
               "selected_files": [selected[key] for key in sorted(selected)],
               "required_existing_files": [existing[key] for key in sorted(existing)],
               "external_imports": sorted(external, key=json_bytes), "unresolved_import_scopes": sorted(unresolved, key=json_bytes),
               "static_closure_complete_at_original_capture": report["static_closure_complete"],
               "runtime_closure_proven": False, "original_whole_producer_closure_replayed": False,
               "counts": {"selected_files": len(selected), "selected_bytes": sum(row["bytes"] for row in selected.values()),
                          "existing_required_files": len(existing), "union_files": len(selected) + len(prior_rows),
                          "union_bytes": sum(row["bytes"] for row in selected.values()) + sum(row["bytes"] for row in prior_rows.values())}}
    need(len(json_bytes(profile)) <= MAX_MANIFEST_BYTES, "supplement profile byte cap exceeded")
    return profile, capture


def verify_profile(profile: dict, *, initial_snapshot: Path, initial_snapshot_sha256: str, config: dict) -> tuple[dict, Capture]:
    need(type(profile) is dict and set(profile) == {"schema", "source_basis", "legacy_snapshot", "source_report", "frontier_report",
         "initial_snapshot_sha256", "retained_source_pair", "selected_files", "required_existing_files", "external_imports", "unresolved_import_scopes",
         "static_closure_complete_at_original_capture", "runtime_closure_proven", "original_whole_producer_closure_replayed", "counts"},
         "exact supplemental profile fields required")
    for field, keys in (("legacy_snapshot", {"root", "manifest_sha256"}), ("source_report", {"path", "sha256"}),
                        ("frontier_report", {"path", "sha256", "module"})):
        need(type(profile[field]) is dict and set(profile[field]) == keys, "exact supplemental input reference required")
        need(all(type(value) is str for value in profile[field].values()), "exact string supplemental reference types required")
    pair = profile["retained_source_pair"]
    extra = {}
    if pair is not None:
        need(type(pair) is dict and set(pair) == {"before", "after", "workspace", "metadata_source_count", "all_metadata_source_bytes_requalified"}
             and type(pair["workspace"]) is str, "exact original retained-copy reference required")
        for field in ("before", "after"):
            need(type(pair[field]) is dict and set(pair[field]) == {"path", "sha256"}
                 and all(type(value) is str for value in pair[field].values()), "exact original retained-copy artifact pin required")
        extra = {"retained_before": Path(pair["before"]["path"]), "retained_before_sha256": pair["before"]["sha256"],
                 "retained_after": Path(pair["after"]["path"]), "retained_after_sha256": pair["after"]["sha256"],
                 "workspace": Path(pair["workspace"])}
    rebuilt, capture = build_profile(snapshot_root=Path(profile["legacy_snapshot"]["root"]),
        snapshot_manifest_sha256=profile["legacy_snapshot"]["manifest_sha256"], source_report=Path(profile["source_report"]["path"]),
        source_report_sha256=profile["source_report"]["sha256"], frontier_report=Path(profile["frontier_report"]["path"]),
        frontier_report_sha256=profile["frontier_report"]["sha256"], module=profile["frontier_report"]["module"],
        initial_snapshot=initial_snapshot, initial_snapshot_sha256=initial_snapshot_sha256, config=config, **extra)
    need(json_bytes(profile) == json_bytes(rebuilt), "supplement profile differs from independently derived retained import scope")
    return rebuilt, capture


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("snapshot-root", "source-report", "frontier-report", "initial-snapshot", "config", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    for name in ("snapshot-manifest-sha256", "source-report-sha256", "frontier-report-sha256", "initial-snapshot-sha256", "module"):
        parser.add_argument("--" + name, required=True)
    for name in ("retained-before", "retained-after", "workspace"):
        parser.add_argument("--" + name, type=Path)
    for name in ("retained-before-sha256", "retained-after-sha256"):
        parser.add_argument("--" + name)
    args = parser.parse_args()
    created = False
    try:
        args.output.mkdir(parents=True, exist_ok=False)
        created = True
        config = document(Capture.read_regular(args.config.absolute(), MAX_MANIFEST_BYTES))
        profile, capture = build_profile(snapshot_root=args.snapshot_root.absolute(), snapshot_manifest_sha256=args.snapshot_manifest_sha256,
            source_report=args.source_report.absolute(), source_report_sha256=args.source_report_sha256,
            frontier_report=args.frontier_report.absolute(), frontier_report_sha256=args.frontier_report_sha256, module=args.module,
            initial_snapshot=args.initial_snapshot.absolute(), initial_snapshot_sha256=args.initial_snapshot_sha256, config=config,
            retained_before=args.retained_before.absolute() if args.retained_before else None,
            retained_before_sha256=args.retained_before_sha256, retained_after=args.retained_after.absolute() if args.retained_after else None,
            retained_after_sha256=args.retained_after_sha256, workspace=args.workspace.absolute() if args.workspace else None)
        (args.output / "supplement.json").write_bytes(json_bytes(profile))
        (args.output / "inventory.json").write_bytes(json_bytes({"schema": "codebase-ir-retained-static-supplement-inventory/v1",
            "profile_sha256": digest(json_bytes(profile)), "counts": profile["counts"], "source_stability": capture.stability(),
            "native_execution_performed": False, "live_missing_module_read": False}))
    except (ValueError, OSError, KeyError, TypeError, RecursionError) as exc:
        if created and not any(args.output.iterdir()):
            (args.output / "refusal.json").write_bytes(json_bytes({"schema": "codebase-ir-retained-static-supplement-refusal/v1",
                "error": f"{type(exc).__name__}: {exc}", "native_execution_performed": False}))
        parser.exit(2, f"retained supplemental inventory refused: {exc}\n")
    print(json_bytes({"profile": str(args.output / "supplement.json"), "sha256": digest(json_bytes(profile)), "counts": profile["counts"]}).decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
