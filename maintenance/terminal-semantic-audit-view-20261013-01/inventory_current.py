"""Explicit public-file inventory and predecessor pin preservation; no jobs.

Only named public files are opened. No directory walk, native owner/database,
CAS, DuckLake/Parquet body, target import or checker operation is performed.
Outputs are exclusive mode-600 files; an existing report is never overwritten.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
import stat

V = Path(__file__).resolve().parent
U = V.parent / "terminal-native-semantic-capsule-20261013-01"
OLD_PUBLIC = U / "actual-public-semantic-01"
PUBLIC = V / "actual-public-audit-01"
BOUND = 16 * 1024 * 1024
FIELDS = ("st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
          "st_size", "st_mtime_ns", "st_ctime_ns")


def need(value, message):
    if not value:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def signature(value):
    return tuple(getattr(value, name) for name in FIELDS)


class Retained:
    def __init__(self):
        self.witnesses = []

    def read(self, path, expected=None):
        path = Path(path)
        need(path.is_absolute() and path.resolve(strict=True) == path,
             "canonical explicitly named regular file required")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        before = os.fstat(descriptor)
        self.witnesses.append((path, descriptor, before, None))
        need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
             and before.st_uid == os.geteuid() and 0 <= before.st_size <= BOUND,
             "bounded owned single-link regular file required")
        chunks, size = [], 0
        while True:
            block = os.read(descriptor, 65536)
            if not block:
                break
            chunks.append(block)
            size += len(block)
            need(size <= BOUND, "named file grew beyond bound")
        raw = b"".join(chunks)
        need(len(raw) == before.st_size
             and signature(before) == signature(os.fstat(descriptor)) == signature(path.lstat()),
             "named file custody changed during capture")
        pin = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        self.witnesses[-1] = (path, descriptor, before, pin["sha256"])
        if expected is not None:
            need(type(expected) is dict and set(expected) == {"path", "bytes", "sha256"}
                 and expected == pin, "baseline named file content differs")
        return pin, raw

    def recheck(self):
        for path, descriptor, before, digest in self.witnesses:
            need(path.resolve(strict=True) == path
                 and signature(before) == signature(os.fstat(descriptor)) == signature(path.lstat()),
                 "retained named file stat witness changed")
            os.lseek(descriptor, 0, os.SEEK_SET)
            sha, size = hashlib.sha256(), 0
            while True:
                block = os.read(descriptor, 65536)
                if not block:
                    break
                size += len(block)
                need(size <= BOUND, "retained file bound exceeded")
                sha.update(block)
            need(size == before.st_size and sha.hexdigest() == digest
                 and signature(before) == signature(os.fstat(descriptor)) == signature(path.lstat()),
                 "retained named file bytes/stat changed")

    def close(self):
        for _, descriptor, _, _ in self.witnesses:
            os.close(descriptor)


def safe_relative(value):
    need(type(value) is str and value and len(value) <= 4096,
         "bounded public relative path required")
    relative = Path(value)
    need(not relative.is_absolute() and str(relative) == value and ".." not in relative.parts,
         "canonical public relative path required")
    return relative


def write_exclusive(path, value):
    raw = wire(value)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    retained = Retained()
    try:
        helper_pin, _ = retained.read(Path(__file__).resolve())
        baseline_pin, baseline_raw = retained.read(V / "baseline-manifest.json")
        baseline = json.loads(baseline_raw)
        need(baseline["schema"] == "terminal-semantic-audit-view-baseline@1", "exact W baseline required")
        initial_pin, initial_raw = retained.read(V / "preservation-baseline.json", baseline["predecessor_preservation_baseline"])
        initial = json.loads(initial_raw)
        occurrences = []
        for ordinal, expected in enumerate(initial["sealed_previous_files"]):
            pin, _ = retained.read(expected["path"], expected)
            occurrences.append({"group": "sealed_W_named_files_and_seal", "ordinal": ordinal,
                                "expected": expected, "actual": pin, "unchanged": True})
        seal_pin = initial["sealed_previous_files"][-1]
        for ordinal, expected in enumerate(baseline["dependencies"]):
            pin, _ = retained.read(expected["path"], expected)
            occurrences.append({"group": "X_actual_direct_dependencies", "ordinal": ordinal,
                                "expected": expected, "actual": pin, "unchanged": True})
        need(len(initial["sealed_previous_files"]) == 240, "all sealed W pins plus seal required")

        pattern_pin, pattern_raw = retained.read(U / "actual-public-inventory.json")
        pattern = json.loads(pattern_raw)
        need(pattern["schema"] == "terminal-native-semantic-public-artifacts@1"
             and pattern["explicit_named_file_count"] == len(pattern["files"]) == 113,
             "exact explicit predecessor public path pattern required")
        relative_paths = []
        for row in pattern["files"]:
            old_path = Path(row["path"])
            need(old_path.is_relative_to(OLD_PUBLIC), "only declared predecessor public pattern allowed")
            relative = safe_relative(str(old_path.relative_to(OLD_PUBLIC)))
            need(relative.suffix in {".json", ".jsonl", ".py", ".lean", ".olean"}
                 or str(relative) in {"model/candidate-cache/artifact.bin", "model/callee/candidate-cache/artifact.bin"},
                 "private storage or unrecognized body excluded")
            need(not set(relative.parts) & {"cas", "lake"}
                 and relative.suffix not in {".duckdb", ".parquet", ".db"}, "private storage body excluded")
            relative_paths.append(relative)
        need(len(set(relative_paths)) == len(relative_paths) == 113, "unique explicit public paths required")
        files, raw_by_path = [], {}
        for relative in relative_paths:
            pin, raw = retained.read(PUBLIC / relative)
            files.append(pin)
            raw_by_path[pin["path"]] = raw
        by_path = {row["path"]: row for row in files}
        declared = set()

        def public(path):
            path = Path(path)
            need(path.is_relative_to(PUBLIC) and str(path) in by_path,
                 "current native public declaration outside explicit inventory")
            declared.add(str(path))
            return path

        def literal(path):
            path = public(path)
            return json.loads(raw_by_path[str(path)])

        def descriptor(row):
            path = public(row["path"])
            actual = by_path[str(path)]
            need(actual["bytes"] == row.get("bytes", row.get("size_bytes"))
                 and actual["sha256"] == row["sha256"], "current public artifact descriptor differs")

        model = literal(PUBLIC / "model/result.json")
        need(model["qualified"] is True and model["model_status"] == "model_proved",
             "selected current public model result required")
        child = literal(Path(model["callee"]["output"]) / "result.json")
        need(wire(child) == wire(model["callee"]), "callee result public copy differs")
        for record in (model, child):
            output = Path(record["output"])
            for name in ("cache-report.json", "cache-dimensions.json"):
                public(output / name)
            for name in ("projection", "generated", "source", "callee_object", "caller_object", "process", "native_proof"):
                if name in record:
                    descriptor(record[name])
            cache = record["advisory_cache"]
            descriptor(cache["artifact"])
            public(Path(cache["output"]) / "artifact.bin")
            cache_manifest = literal(Path(cache["output"]) / "manifest.json")
            need(by_path[str(Path(cache["output"]) / "manifest.json")]["sha256"] == cache["manifest_sha256"],
                 "current public candidate manifest differs")
            for report in (record["metadata"], cache["metadata"]):
                directory = Path(report["output"])
                path = public(directory / "manifest.json")
                manifest = literal(path)
                need("sha256:" + by_path[str(path)]["sha256"] == report["manifest_sha256"]
                     and manifest["output"] == str(directory), "current metadata manifest binding differs")
                for family, family_record in manifest["families"].items():
                    export = family_record["export"]
                    need(export == report["exports"][family], "metadata export/report declaration differs")
                    target = public(directory / safe_relative(export["relative_path"]))
                    pin = by_path[str(target)]
                    need(pin["bytes"] == export["bytes"] and "sha256:" + pin["sha256"] == export["sha256"],
                         "current public metadata export pin differs")
                for batch in manifest["batches"]:
                    target = public(directory / safe_relative(batch["relative_path"]))
                    pin = by_path[str(target)]
                    need(pin["bytes"] == batch["bytes"] and "sha256:" + pin["sha256"] == batch["sha256"],
                         "current public native batch pin differs")
        native = literal(child["native_proof"]["path"])
        literal(Path(native["output"]) / "result.json")
        for row in native["artifacts"].values():
            descriptor(row)
        public(Path(child["output"]) / "checked-object.olean")
        manifest = literal(Path(model["metadata"]["output"]) / "manifest.json")
        source_leaves = manifest["source_snapshot"]["revision"]["sources"]
        need(sorted(row["path"] for row in source_leaves) == model["paths"], "whole authored source scope differs")
        for row in source_leaves:
            target = public(PUBLIC / "repository" / safe_relative(row["path"]))
            pin = by_path[str(target)]
            need(pin["bytes"] == row["bytes"] and pin["sha256"] == row["sha256"], "authored source leaf differs")
        public(PUBLIC / "prepared.json")
        public(PUBLIC / "qualification-summary.json")
        need(declared == set(by_path), "explicit current public native closure differs from 113-file pattern")
        retained.recheck()
        preservation = {"schema": "terminal-semantic-audit-view-predecessor-preservation@1",
            "qualified": True, "baseline": baseline_pin, "predecessor_seal": seal_pin,
            "sealed_predecessor_named_files": 239, "sealed_predecessor_manifest_occurrences": 1,
            "baseline_dependency_occurrences": len(baseline["dependencies"]), "checked_occurrences": len(occurrences),
            "occurrences_deduplicated": False, "all_expected_pins_unchanged": True,
            "retained_nofollow_regular_singlelink_fd_stat_hash_witnesses_rechecked": True,
            "preservation_scope": "named bytes and captured-call stat custody; no previous mode/inode or recursive store claim",
            "legacy_source_modes_changed": False, "recursive_traversal": False,
            "database_bodies_included": False, "cas_bodies_included": False,
            "ducklake_parquet_bodies_included": False, "occurrences": occurrences, "producer": helper_pin}
        inventory = {"schema": "terminal-semantic-audit-view-public-artifacts@1",
            "explicit_named_file_count": len(files), "files": files, "recursive_traversal": False,
            "public_path_pattern": pattern_pin, "path_pattern_scope": "relative path selection only; all V pins freshly captured",
            "declared_native_public_closure_matched": True,
            "retained_nofollow_regular_singlelink_fd_stat_hash_witnesses_rechecked": True,
            "database_bodies_included": False, "cas_bodies_included": False,
            "ducklake_parquet_bodies_included": False, "public_fixture_source_included": True,
            "public_lean_objects_included": True, "public_candidate_cache_copies_included": True,
            "native_storage_validation": "actual before/after cold native readback; not inferred from this public hash inventory",
            "proof_authority": False, "source_origin_proved": False, "runtime_behavior_verified": False,
            "full_task_satisfaction": False, "convergence_proved": False, "producer": helper_pin}
        outputs = [write_exclusive(V / "actual-public-inventory.json", inventory),
                   write_exclusive(V / "preservation-before-package.json", preservation)]
        retained.recheck()
        print(json.dumps({"outputs": outputs, "public_files": len(files),
                          "preservation_occurrences": len(occurrences), "qualified": True}, sort_keys=True))
    finally:
        retained.close()


if __name__ == "__main__":
    main()
