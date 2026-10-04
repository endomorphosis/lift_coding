#!/usr/bin/env python3
"""Read-only selected producer provenance and retained trial inventory."""

from __future__ import annotations

import argparse
import ast
import collections
import json
import math
import os
import stat
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from audit import SourceBoundError, digest, git, json_bytes, make_repositories

SCHEMA = "codebase-ir-retained-source-provenance/v1"
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
MAX_FILES = 256
MAX_CASES = 4096


class ProvenanceRefusal(ValueError):
    pass


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ProvenanceRefusal(message)


def exact_sha(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def unique_pairs(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        need(key not in result, "duplicate JSON key")
        result[key] = value
    return result


def finite_float(value: str) -> float:
    result = float(value)
    need(math.isfinite(result), "nonfinite JSON number")
    return result


def reject_constant(value: str) -> None:
    raise ProvenanceRefusal("nonfinite JSON value: " + value)


def document(raw: bytes) -> dict:
    try:
        value = json.loads(raw, object_pairs_hook=unique_pairs, parse_float=finite_float,
                           parse_constant=reject_constant)
    except (ValueError, RecursionError, UnicodeError) as exc:
        raise ProvenanceRefusal("bounded strict JSON document required: " + str(exc)) from exc
    need(type(value) is dict, "JSON object required")
    return value


def resolve_path(value: str, workspace: Path) -> Path:
    need(type(value) is str and value and ".." not in Path(value).parts,
         "exact artifact/source path required")
    path = Path(value)
    path = path if path.is_absolute() else workspace / path
    need(str(path) == str(path.resolve(strict=True)), "canonical path spelling required")
    return path


def pin_row(row: object, *, size_field: str = "bytes", extra: set[str] | None = None) -> None:
    need(type(row) is dict and set(row) == {"path", "sha256", size_field} | (extra or set())
         and type(row["path"]) is str and exact_sha(row["sha256"])
         and type(row[size_field]) is int and 0 <= row[size_field] <= MAX_FILE_BYTES,
         "exact source pin fields/digest/byte size required")


class Reader:
    """Bounded regular-file custody without executing any selected source."""
    def __init__(self, roots: list[Path]):
        self.roots = roots
        self.cache: dict[Path, bytes] = {}
        self.total_bytes = 0
        self.blob_bytes = 0

    @staticmethod
    def _identity(value: os.stat_result) -> tuple:
        return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)

    def _read(self, path: Path, limit: int) -> bytes:
        need(path.is_absolute() and path.resolve(strict=True) == path
             and any(path.is_relative_to(root) for root in self.roots)
             and not any(p.is_symlink() for p in (path, *path.parents))
             and path.suffix in {".py", ".json", ".xml"},
             "artifact/source path outside explicit read scope")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(descriptor, "rb") as stream:
            before = os.fstat(stream.fileno())
            need(stat.S_ISREG(before.st_mode) and before.st_size <= limit,
                 "regular artifact/source within byte ceiling required")
            raw = stream.read(limit + 1)
            after = os.fstat(stream.fileno())
            current = path.stat(follow_symlinks=False)
        need(len(raw) <= limit, "artifact/source grew past byte ceiling")
        need(self._identity(before) == self._identity(after) == self._identity(current)
             and len(raw) == before.st_size and path.resolve(strict=True) == path,
             "artifact/source changed during descriptor read")
        return raw

    def read(self, path: Path, expected: dict | None = None, *, size_field: str = "bytes") -> bytes:
        if path not in self.cache:
            need(len(self.cache) < MAX_FILES, "distinct artifact/source ceiling reached")
            raw = self._read(path, min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - self.total_bytes))
            self.cache[path] = raw
            self.total_bytes += len(raw)
        raw = self.cache[path]
        if expected is not None:
            need(digest(raw) == expected["sha256"] and len(raw) == expected[size_field],
                 "retained artifact/source differs from exact declared pin")
        return raw

    def tree_bytes(self, repo, path: str) -> bytes:
        limit = min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - self.total_bytes)
        try:
            raw = repo.read_tree(path, limit)
        except SourceBoundError as exc:
            raise ProvenanceRefusal("reference source exceeds remaining byte ceiling") from exc
        self.total_bytes += len(raw)
        self.blob_bytes += len(raw)
        return raw

    def stability(self) -> dict:
        observations = []
        for path, before in self.cache.items():
            try:
                raw = self._read(path, len(before))
                after = digest(raw)
            except (OSError, ValueError) as exc:
                after = None
                observations.append({"path": str(path), "before_sha256": digest(before),
                                     "after_sha256": None, "unchanged": False, "error": str(exc)})
                continue
            observations.append({"path": str(path), "before_sha256": digest(before),
                                 "after_sha256": after, "unchanged": after == digest(before)})
        return {"stable": all(row["unchanged"] for row in observations), "files": observations,
                "scope": "sequential exact-byte rereads; no atomic or process-origin claim"}


def source_owner(path: Path, config: dict) -> tuple[str, str]:
    candidates = []
    for spec in config["repositories"]:
        root = Path(spec["root"]).resolve(strict=True)
        if path.is_relative_to(root):
            relative = path.relative_to(root)
            prefixes = set(spec["packages"]) | {"benchmarks", "test", "tests"}
            if relative.parts and relative.parts[0] in prefixes:
                candidates.append((spec["name"], relative.as_posix()))
    need(len(candidates) == 1 and path.suffix == ".py"
         and not any(part.startswith(".") for part in path.parts),
         "selected source has no unique configured producer owner")
    return candidates[0]


def constants(raw: bytes) -> dict:
    names = {"SCHEMA", "PROFILE", "DECLARATION_SCHEMA", "RECEIPT_SCHEMA", "MANIFEST_SCHEMA",
             "MANIFEST_SCHEMA_V2", "MANIFEST_SCHEMA_V3", "INTENT_MANIFEST_SCHEMA", "_CAPACITY_SCHEMA"}
    result = {}
    try:
        tree = ast.parse(raw)
        for statement in tree.body:
            if isinstance(statement, ast.Assign) and isinstance(statement.value, ast.Constant):
                for target in statement.targets:
                    if isinstance(target, ast.Name) and target.id in names and type(statement.value.value) is str:
                        result[target.id] = statement.value.value
    except (SyntaxError, ValueError, RecursionError, UnicodeError) as exc:
        return {"static_parse_unavailable": str(exc)}
    return result


def normalize_sources(before: dict, after: dict, workspace: Path, config: dict, reader: Reader,
                      retained_root: Path) -> list[dict]:
    fields = {"schema", "scope", "source_count", "sources"}
    need(set(before) == fields and set(after) == fields | {"changed_paths"}
         and before["schema"] == after["schema"] == "finite-admission-critical-producer-snapshot@1"
         and type(before["sources"]) is list and type(after["sources"]) is list
         and type(before["source_count"]) is int and type(after["source_count"]) is int
         and len(before["sources"]) == before["source_count"] <= 128
         and len(after["sources"]) == after["source_count"], "critical source snapshot schema/count differs")
    ending = {}
    for row in after["sources"]:
        pin_row(row, size_field="size_bytes")
        path = resolve_path(row["path"], workspace)
        need(path not in ending, "duplicate ending source")
        ending[path] = row
    records, seen, changed = [], set(), []
    for row in before["sources"]:
        pin_row(row, size_field="size_bytes", extra={"retained_source"})
        path = resolve_path(row["path"], workspace)
        need(path not in seen and path in ending, "duplicate/missing source population")
        seen.add(path)
        repo, relative = source_owner(path, config)
        copy = resolve_path(row["retained_source"], workspace)
        need(path.is_relative_to(workspace)
             and copy == retained_root / path.relative_to(workspace),
             "critical retained source does not bind exact copied source path")
        raw = reader.read(copy, row, size_field="size_bytes")
        end = ending[path]
        stable = (row["sha256"], row["size_bytes"]) == (end["sha256"], end["size_bytes"])
        if not stable:
            changed.append(str(path))
        current = reader.read(path)
        records.append({"repository": repo, "path": relative, "original_path": str(path),
                        "retained_source": str(copy), "before": row, "after": end,
                        "recorded_before_after_stable": stable, "retained_copy_matches_before": True,
                        "current_sha256": digest(current), "current_bytes": len(current),
                        "current_matches_recorded_before": digest(current) == row["sha256"] and len(current) == row["size_bytes"],
                        "retained_source_constants": constants(raw), "current_source_constants": constants(current)})
    need(seen == set(ending) and sorted(after["changed_paths"]) == sorted(changed),
         "critical ending population or changed-path declaration differs")
    return records


def case_rows(rows: object) -> dict[tuple[str, str], dict]:
    need(type(rows) is list and len(rows) <= MAX_CASES, "bounded trial cases required")
    result = {}
    for row in rows:
        need(type(row) is dict and {"classname", "name", "seconds", "status"} <= set(row)
             and set(row) <= {"classname", "name", "seconds", "status", "diagnostic", "message"}
             and type(row["classname"]) is str and type(row["name"]) is str
             and row["status"] in {"passed", "failure", "error", "skipped"}
             and all(type(row[key]) is str for key in ("diagnostic", "message") if key in row)
             and type(row["seconds"]) in {int, float} and math.isfinite(row["seconds"]) and row["seconds"] >= 0,
             "exact trial case identity/status required")
        key = (row["classname"], row["name"])
        need(key not in result, "duplicate trial case identity")
        result[key] = row
    return result


def parse_xml(raw: bytes) -> dict[tuple[str, str], dict]:
    need(b"<!DOCTYPE" not in raw and b"<!ENTITY" not in raw, "XML declarations/entities refused")
    try:
        root = ET.fromstring(raw)
    except (ET.ParseError, RecursionError) as exc:
        raise ProvenanceRefusal("bounded trial XML required") from exc
    rows = []
    for case in root.iter("testcase"):
        statuses = [child.tag for child in case if child.tag in {"failure", "error", "skipped"}]
        need(len(statuses) <= 1, "multiple trial statuses refused")
        rows.append({"classname": case.attrib.get("classname", ""), "name": case.attrib.get("name", ""),
                     "seconds": finite_float(case.attrib.get("time", "0")),
                     "status": statuses[0] if statuses else "passed"})
    return case_rows(rows)


def trial_coverage(ledger: dict, workspace: Path, reader: Reader) -> dict:
    required = {"current_boundary", "current_capacity_failed_case_retry", "current_capacity_initial",
                "current_capacity_latest", "earlier_31_boundary_history", "historical_full_compatibility_run",
                "historical_legacy_coupling", "native_sampler_injected", "pressure_guards_changed",
                "recorded_at_utc", "schema", "scope"}
    need(set(ledger) == required and ledger["schema"] == "finite-admission-selected-test-ledger@1"
         and ledger["native_sampler_injected"] is False and ledger["pressure_guards_changed"] is False,
         "selected test ledger schema or intervention flags differ")
    trials, normalized = {}, {}
    for name in ("current_boundary", "current_capacity_initial", "current_capacity_failed_case_retry", "historical_full_compatibility_run"):
        group = ledger[name]
        need(type(group) is dict and set(group) == {"cases", "counts", "suite_attributes", "xml"},
             "exact retained trial fields required")
        pin_row(group["xml"])
        path = resolve_path(group["xml"]["path"], workspace)
        need(path.suffix == ".xml", "trial provenance must name an XML artifact")
        xml = parse_xml(reader.read(path, group["xml"]))
        declared = case_rows(group["cases"])
        need(set(xml) == set(declared) and all(xml[key]["status"] == row["status"] for key, row in declared.items()),
             "trial ledger case population/status differs from pinned XML")
        counts = {status: sum(row["status"] == status for row in xml.values()) for status in ("error", "failure", "passed", "skipped")}
        need(group["counts"] == counts and all(type(n) is int for n in group["counts"].values()),
             "trial counts differ from actual retained XML")
        normalized[name] = declared
        trials[name] = {"counts": counts, "distinct_cases": len(xml), "xml": group["xml"],
                        "case_ids_and_status": [{"classname": key[0], "name": key[1], "status": xml[key]["status"]} for key in sorted(xml)],
                        "historical": name.startswith("historical"),
                        "executed_producer_closure_attested": False}
    latest = dict(normalized["current_capacity_initial"])
    retry = normalized["current_capacity_failed_case_retry"]
    need(set(retry) <= set(latest), "retry adds foreign capacity cases")
    latest.update(retry)
    claimed = ledger["current_capacity_latest"]
    need(type(claimed) is dict and set(claimed) == {"cases", "distinct_cases", "errors", "failures", "passed", "skipped"}
         and case_rows(claimed["cases"]) == latest and type(claimed["distinct_cases"]) is int
         and claimed["distinct_cases"] == len(latest), "latest capacity projection differs from preserved initial+retry")
    latest_counts = {key: sum(row["status"] == status for row in latest.values())
                     for key, status in (("errors", "error"), ("failures", "failure"), ("passed", "passed"), ("skipped", "skipped"))}
    need(all(type(claimed[key]) is int and claimed[key] == value for key, value in latest_counts.items()),
         "latest capacity counts differ")
    legacy = ledger["historical_legacy_coupling"]
    need(type(legacy) is dict and set(legacy) == {"cases", "distinct_cases", "passed", "scope", "xml"},
         "historical subset fields differ")
    subset = case_rows(legacy["cases"])
    full = normalized["historical_full_compatibility_run"]
    need(set(subset) <= set(full) and all(row == full[key] and row["status"] == "passed" for key, row in subset.items())
         and type(legacy["passed"]) is int and legacy["passed"] == len(subset)
         and type(legacy["distinct_cases"]) is int and legacy["distinct_cases"] == len(subset)
         and legacy["xml"] == ledger["historical_full_compatibility_run"]["xml"],
         "historical subset cannot become current or erase failures")
    trials["capacity_latest_retry_overlay"] = {"distinct_cases": len(latest), **latest_counts,
                                               "single_clean_run": False}
    trials["historical_legacy_subset"] = {"distinct_cases": len(subset), "passed": len(subset),
                                         "scope": legacy["scope"], "current_qualification": False}
    return {"trials": trials, "earlier_boundary_history": ledger["earlier_31_boundary_history"],
            "single_clean_combined_run": False, "scope": ledger["scope"]}


def audit_fixture(fixture: Path, output: Path, *, workspace: Path, config: dict,
                 source_before: Path, source_after: Path) -> dict:
    need(fixture.resolve(strict=True) == fixture and fixture.is_dir(), "canonical retained fixture required")
    output.mkdir(parents=True, exist_ok=False)
    roots = [fixture, fixture.parent, source_before.parent, source_after.parent]
    roots += [Path(spec["root"]).resolve(strict=True) for spec in config["repositories"]]
    roots += [Path(spec["released_checkout"]).resolve(strict=True) for spec in config["repositories"]
              if "released_checkout" in spec]
    reader = Reader(roots)
    report = {"schema": SCHEMA, "scope": "read-only selected source custody and retained trial comparison",
              "fixture": str(fixture), "production_qualified": False, "signature_verification_performed": False,
              "current_freshness_verified": False, "native_execution_performed": False,
              "runtime_closure_proven": False, "process_origin_attested": False,
              "bounds": {"max_file_bytes": MAX_FILE_BYTES, "max_total_bytes": MAX_TOTAL_BYTES,
                         "max_distinct_files": MAX_FILES, "max_trial_cases": MAX_CASES,
                         "total_byte_scope": "first distinct filesystem captures plus reference Git source bodies; stability rereads separately bounded per file"}}
    repos = []
    try:
        inputs = {}
        def load(role: str, path: Path) -> dict:
            raw = reader.read(path)
            inputs[role] = {"path": str(path), "sha256": digest(raw), "bytes": len(raw)}
            return document(raw)
        result = load("fixture_result", fixture / "result.json")
        report["raw_result_sha256"] = inputs["fixture_result"]["sha256"]
        need(result.get("schema") == "finite-repository-admission-qualification@1" and result.get("status") == "completed",
             "completed retained finite fixture required")
        report["selected_sources"] = normalize_sources(load("source_before", source_before),
                                                       load("source_after", source_after), workspace, config, reader,
                                                       source_before.parent / "sources")
        selected = {(row["repository"], row["path"]): row for row in report["selected_sources"]}
        copies = result.get("selected_source_copies")
        need(type(copies) is list and 1 <= len(copies) <= 128, "nonempty bounded selected fixture producer copies required")
        need(result.get("execution_sources") == [row.get("original") for row in copies if type(row) is dict],
             "fixture execution-source population differs from retained producer originals")
        producer_copies, modules = [], {}
        extra_sources = []
        for row in copies:
            need(type(row) is dict and set(row) == {"module", "original", "retained"}
                 and type(row["module"]) is str and row["module"] not in modules,
                 "unique exact fixture producer copy rows required")
            pin_row(row["original"])
            pin_row(row["retained"])
            original = resolve_path(row["original"]["path"], workspace)
            owner, relative = source_owner(original, config)
            need(row["module"] == relative[:-3].replace("/", ".").removesuffix(".__init__"),
                 "fixture module name does not bind exact original producer path")
            overlaps = (owner, relative) in selected
            if overlaps:
                need(row["original"]["sha256"] == selected[(owner, relative)]["before"]["sha256"]
                     and row["original"]["bytes"] == selected[(owner, relative)]["before"]["size_bytes"],
                     "fixture producer differs from overlapping critical source")
            retained = resolve_path(row["retained"]["path"], workspace)
            need(retained.is_relative_to(fixture / "selected-source-snapshot")
                 and retained.name == row["module"] + ".py", "fixture producer copy outside exact retained population")
            raw = reader.read(retained, row["retained"])
            need(digest(raw) == row["original"]["sha256"] and len(raw) == row["original"]["bytes"],
                 "fixture source copy differs from declared producer")
            if not overlaps:
                current = reader.read(original)
                extra_sources.append({"repository": owner, "path": relative,
                                      "source_basis": "fixture_selected_copy_only; outside critical before/after population",
                                      "original_path": str(original), "retained_source": str(retained),
                                      "before": {"sha256": row["original"]["sha256"], "size_bytes": row["original"]["bytes"]},
                                      "current_sha256": digest(current), "current_bytes": len(current),
                                      "current_matches_recorded_before": digest(current) == digest(raw),
                                      "retained_source_constants": constants(raw), "current_source_constants": constants(current)})
            modules[row["module"]] = (owner, relative)
            producer_copies.append({**row, "verified_retained_copy": True, "critical_source_overlap": overlaps})
        report["producer_copies"] = producer_copies
        report["fixture_only_sources"] = extra_sources
        declarations, signed_pins = [], {}
        for role in ("before", "successor"):
            declaration = load(role + "_declaration", fixture / (role + "-declaration.json"))
            need(set(declaration) == {"binding", "payload"} and type(declaration["payload"]) is dict,
                 "retained signed declaration shape differs")
            payload = declaration["payload"]
            implementation = payload.get("implementation", {})
            pins = implementation.get("source_sha256")
            need(payload.get("schema") == "supervisor-finite-repository-declaration@1"
                 and implementation.get("schema") == "finite-repository-admission-implementation@1"
                 and type(pins) is dict and 1 <= len(pins) <= 128
                 and all(type(name) is str and exact_sha(value) for name, value in pins.items()),
                 "retained declaration producer pins differ")
            if signed_pins:
                need(pins == signed_pins, "before/successor signed producer identity changed")
            signed_pins = pins
            manifest_schema = payload.get("manifest", {}).get("payload", {}).get("schema")
            declarations.append({"role": role, "manifest_schema_observed": manifest_schema,
                                 "declaration_schema": payload["schema"], "implementation": implementation,
                                 "signature_status": "retained assertion; not verified by this ledger"})
        signed_overlap = []
        for module, sha256 in signed_pins.items():
            relative = module.replace(".", "/") + ".py"
            candidates = [key for key in selected if key[1] == relative]
            need(len(candidates) == 1, "signed producer lacks unique selected source overlap")
            row = selected[candidates[0]]
            need(row["before"]["sha256"] == sha256, "signed producer differs from retained critical source")
            signed_overlap.append({"module": module, "repository": candidates[0][0], "path": relative,
                                   "signed_sha256": sha256, "fixture_copy_present": module in modules,
                                   "critical_retained_copy_matches": True,
                                   "current_source_matches": row["current_sha256"] == sha256})
        report["declarations"] = declarations
        report["signed_producer_overlap"] = signed_overlap
        report["trial_coverage"] = trial_coverage(load("test_ledger", fixture / "test-ledger.json"), workspace, reader)
        comparisons = {}
        for mode in ("working", "head", "released_ref", "released_checkout"):
            view_repos = make_repositories(config, mode)
            repos.extend(view_repos)
            views = {repo.name: repo for repo in view_repos}
            observations = []
            for row in report["selected_sources"] + extra_sources:
                repo = views[row["repository"]]
                path = row["path"]
                if not repo.has(path):
                    disposition, sha256, size = "missing", None, None
                else:
                    raw = reader.read(repo.root / path) if mode in {"working", "released_checkout"} else reader.tree_bytes(repo, path)
                    sha256, size = digest(raw), len(raw)
                    disposition = "identical" if sha256 == row["before"]["sha256"] else "different_bytes"
                observations.append({"repository": repo.name, "path": path, "disposition": disposition,
                                     "sha256": sha256, "bytes": size,
                                     "tracked_in_tree": path in repo.tree, "git_index_entries": repo.index.get(path, [])})
            comparisons[mode] = {"counts": dict(collections.Counter(row["disposition"] for row in observations)),
                                 "files": observations, "repositories": [repo.identity() for repo in view_repos]}
        report["source_views"] = comparisons
        report["recorded_historical_assertions"] = result.get("fresh_process_historical_replay")
        report["counts"] = {"selected_sources": len(selected), "fixture_producer_copies": len(producer_copies),
                            "fixture_producer_overlap_with_selected_sources": sum(row["critical_source_overlap"] for row in producer_copies),
                            "source_view_population": len(selected) + len(extra_sources),
                            "signed_producer_pins": len(signed_overlap),
                            "signed_producers_with_fixture_copy": sum(row["fixture_copy_present"] for row in signed_overlap),
                            "signed_producers_with_critical_copy": len(signed_overlap)}
        report["disposition"] = "ledger_produced"
    except (OSError, ValueError, KeyError, TypeError, RecursionError) as exc:
        report["disposition"] = "retained_provenance_refused"
        report["error"] = f"{type(exc).__name__}: {exc}"
    finally:
        report["git_head_stability"] = []
        for repo in repos:
            try:
                after_head = git(repo.root, "rev-parse", "HEAD").decode().strip()
            except (OSError, ValueError) as exc:
                after_head = str(exc)
            report["git_head_stability"].append({"repository": repo.name, "root": str(repo.root),
                                                 "before": repo.head, "after": after_head,
                                                 "stable": repo.head == after_head})
            repo.close()
        report["input_artifacts"] = locals().get("inputs", {})
        report["read_bytes"] = reader.total_bytes
        report["source_stability"] = reader.stability()
        if not report["source_stability"]["stable"] or any(not row["stable"] for row in report["git_head_stability"]):
            report["disposition"] = "input_drift_refused"
        (output / "ledger.json").write_bytes(json_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("runtime_service.json"))
    parser.add_argument("--source-before", type=Path)
    parser.add_argument("--source-after", type=Path)
    args = parser.parse_args()
    workspace, fixture = args.workspace.resolve(), args.fixture.resolve()
    source_root = fixture.parent / fixture.name.replace("finite-admission-qualification-", "finite-admission-tests-")
    before = (args.source_before or source_root / "critical-source-before.json").absolute()
    after = (args.source_after or source_root / "critical-source-after.json").absolute()
    try:
        config_path = args.config.absolute()
        config = document(Reader([config_path.parent]).read(config_path))
        started = time.monotonic()
        report = audit_fixture(fixture, args.output.resolve(), workspace=workspace, config=config,
                               source_before=before, source_after=after)
    except (OSError, ValueError) as exc:
        parser.exit(2, f"retained provenance input refused: {exc}\n")
    print(json.dumps({"ledger": str(args.output.resolve() / "ledger.json"), "raw_result_sha256": report.get("raw_result_sha256"),
                      "disposition": report["disposition"], "counts": report.get("counts"),
                      "source_stability": report["source_stability"]["stable"],
                      "seconds": round(time.monotonic() - started, 6), "production_qualified": False}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
