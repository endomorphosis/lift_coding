"""Seal Stage AA's explicitly audited public files; never run project code.

Usage: python -B seal_evidence.py --config /absolute/AA/audit-config.json [--verify]
The root must finish the independent audit before invoking this script. The
only write is exclusive creation of evidence-manifest.json. Verification is
read-only. Public data does not recreate a live budget, runtime or proof owner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.dont_write_bytecode = True
STAGE = Path(__file__).absolute().parent
PREVIOUS = STAGE.parent / "terminal-checked-worker-context-20261013-01"
CHECKOUT = STAGE / "checkout"
MANIFEST = STAGE / "evidence-manifest.json"
MAX_BYTES = 8 * 1024 * 1024
MAX_FILES = 4096
MAX_TOTAL_BYTES = 512 * 1024 * 1024
SCHEMA = "terminal-admitted-context-evidence-manifest@1"
SYSTEM_INTERPRETER = "/usr/local/bin/python3.12"
FIXTURE_NAMES = frozenset({
    "source.gitbundle", "manifest.json", "graph.json", "admission.json",
    "materialization.json", "context-preparation.json", "task-readback.json",
    "native-prompt.txt", "native-capsule.json", "compilation-receipt.json",
    "instruction-descriptor.json", "context-bundle.json", "owner-receipt.json",
})


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def document(value):
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True,
                      allow_nan=False).encode("utf-8") + b"\n"


def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def parse(raw):
    def invalid(value):
        raise ValueError("nonfinite JSON number: " + value)
    return json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                      parse_constant=invalid)


def absolute(value):
    require(type(value) is str and 0 < len(value) <= 4096,
            "expected bounded absolute path")
    path = Path(value)
    require(path.is_absolute() and str(path) == value and ".." not in path.parts,
            "path must have one literal absolute spelling: " + value)
    return path


def owned(value):
    path = absolute(value)
    require(path.is_relative_to(STAGE) and path != MANIFEST,
            "expected explicitly named stage input: " + value)
    return path


def pin(value):
    require(type(value) is dict and set(value) >= {"path", "bytes", "sha256"},
            "expected explicit path/bytes/SHA256 pin")
    path = absolute(value["path"])
    size, sha = value["bytes"], value["sha256"]
    require(type(size) is int and 0 <= size <= MAX_TOTAL_BYTES,
            "invalid exact pin byte count: " + str(path))
    require(type(sha) is str and re.fullmatch(r"[0-9a-f]{64}", sha) is not None,
            "invalid exact pin SHA256: " + str(path))
    return {"path": str(path), "bytes": size, "sha256": sha}


def stamp(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_uid,
            value.st_gid, value.st_nlink, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def public_host(path):
    require(str(path) != SYSTEM_INTERPRETER,
            "container interpreter descriptor is never a host file")
    require(not set(path.parts) & {"cas", "lake", ".git"} and
            path.suffix.lower() not in {".duckdb", ".sqlite", ".sqlite3", ".db",
                                        ".wal", ".parquet"},
            "private storage is outside this public seal: " + str(path))
    require(path.is_relative_to(Path("/home/barberb/lift_coding")) or
            path.is_relative_to(Path("/home/barberb/.elan/toolchains/leanprover--lean4---v4.34.1")) or
            str(path) == "/tmp/data-gym-cache/fb374d419588a4632f3f557e76b4b70aebbca790",
            "not an explicit public host evidence namespace: " + str(path))


class Custody:
    """Retain exact regular-file descriptors, then hash and freshly reopen."""

    def __init__(self):
        self.captures = {}
        self.selected = {}
        self.total = 0
        self.directory_fd = os.open(STAGE, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.directory_identity = self._directory_identity()
        require(self.directory_identity[2] == os.geteuid(), "stage directory is not owned")

    def _directory_identity(self):
        info = os.fstat(self.directory_fd)
        current = STAGE.lstat()
        require(stat.S_ISDIR(info.st_mode) and stat.S_ISDIR(current.st_mode) and
                (info.st_dev, info.st_ino) == (current.st_dev, current.st_ino),
                "stage directory was replaced")
        return info.st_dev, info.st_ino, info.st_uid

    @staticmethod
    def _bytes(fd, expected_stamp):
        os.lseek(fd, 0, os.SEEK_SET)
        raw = bytearray()
        while len(raw) <= MAX_BYTES:
            block = os.read(fd, min(1024 * 1024, MAX_BYTES + 1 - len(raw)))
            if not block:
                break
            raw.extend(block)
        require(len(raw) == expected_stamp[6] and len(raw) <= MAX_BYTES and
                stamp(os.fstat(fd)) == expected_stamp,
                "bounded retained file bytes or metadata changed")
        return bytes(raw)

    def capture(self, path, expected=None, *, output=False):
        path = absolute(str(path))
        if not output:
            public_host(path)
            require(path != MANIFEST, "the final seal cannot name itself as input")
        key = str(path)
        if key not in self.captures:
            require(len(self.captures) < MAX_FILES, "too many explicit named files")
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                info = os.fstat(fd)
                require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
                        info.st_uid == os.geteuid() and 0 <= info.st_size <= MAX_BYTES,
                        "expected owned bounded single-link regular file: " + key)
                identity = stamp(info)
                raw = self._bytes(fd, identity)
                require(stamp(path.lstat()) == identity, "file path changed: " + key)
                self.total += len(raw)
                require(self.total <= MAX_TOTAL_BYTES, "total named evidence byte bound exceeded")
                row = {"path": key, "bytes": len(raw), "sha256": digest(raw)}
                self.captures[key] = {"fd": fd, "stamp": identity, "raw": raw, "pin": row}
            except BaseException:
                os.close(fd)
                raise
        item = self.captures[key]
        if expected is not None:
            require(pin(expected) == item["pin"], "exact expected file pin mismatch: " + key)
        return item["raw"]

    def select(self, path, expected=None):
        raw = self.capture(path, expected)
        self.selected[str(path)] = self.captures[str(path)]["pin"]
        return raw

    def load(self, path, expected=None):
        return parse(self.select(path, expected))

    def recheck(self):
        require(self._directory_identity() == self.directory_identity,
                "stage directory identity changed")
        for name, item in self.captures.items():
            require(stamp(os.fstat(item["fd"])) == item["stamp"] == stamp(Path(name).lstat()),
                    "retained FD/path identity changed: " + name)
            require(digest(self._bytes(item["fd"], item["stamp"])) == item["pin"]["sha256"],
                    "retained FD bytes changed: " + name)
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                require(stamp(os.fstat(fd)) == item["stamp"], "fresh reopen identity changed: " + name)
                require(digest(self._bytes(fd, item["stamp"])) == item["pin"]["sha256"] and
                        stamp(Path(name).lstat()) == item["stamp"],
                        "fresh reopen bytes or path changed: " + name)
            finally:
                os.close(fd)

    def close(self):
        for item in self.captures.values():
            os.close(item["fd"])
        os.close(self.directory_fd)


def build(custody, config_path):
    config = custody.load(config_path)
    require(type(config) is dict and config.get("ready") is True,
            "root final audit configuration must be explicitly ready")
    review_path = STAGE / "independent-review.json"
    review = custody.load(review_path)
    verdicts = [review[key] for key in ("passed", "qualified") if key in review]
    require(verdicts and all(value is True for value in verdicts) and
            type(review.get("failed_checks")) is int and review["failed_checks"] == 0 and
            type(review.get("check_count")) is int and 0 < review["check_count"] <= 500000,
            "final independent audit has not passed")
    require(type(review.get("checks")) is list and len(review["checks"]) == review["check_count"] and
            all(type(row) is dict and row.get("passed") is True for row in review["checks"]) and
            review.get("blockers", []) == [], "independent check census is inconsistent")

    def selected(key):
        require(key in config, "missing selected audit configuration field: " + key)
        return owned(config[key])

    # These are fixed, explicitly configured inventories. No nested descriptor
    # traversal is permitted; the independent report's read_pins is primary.
    model = custody.load(selected("model_result"))
    actual = custody.load(selected("actual_result"))
    require(model.get("qualified") is True and actual.get("qualified") is True,
            "selected actual/model result is unqualified")
    metadata = {}

    def metadata_pin(row, reason):
        value = pin(row)
        old = metadata.get(value["path"])
        require(old is None or {k: old[k] for k in value} == value,
                "conflicting metadata-only descriptors")
        metadata[value["path"]] = {**value, "reason": reason, "body_read_by_sealer": False}

    declared_bulk = config.get("metadata_only_bulk_archives", [])
    require(type(declared_bulk) is list and len(declared_bulk) <= 16 and
            len(set(declared_bulk)) == len(declared_bulk), "invalid explicit bulk archive list")
    for name in declared_bulk:
        path = owned(name)
        require(path.name == "public-source.tar.gz", "only explicitly named public source archives are metadata-only")
    audit_metadata = review.get("metadata_only_descriptors", [])
    require(type(audit_metadata) is list, "invalid audit metadata descriptor list")
    archive = model.get("archive")
    if archive is not None:
        value = pin(archive)
        require(owned(value["path"]).suffix in {".tar", ".gz"},
                "selected public model archive must be an explicit stage tar descriptor")
        metadata_pin(value, "selected-public-model-archive-descriptor-only")
    for row in audit_metadata:
        if type(row) is dict and row.get("path") in declared_bulk:
            metadata_pin(row, "explicit-public-source-archive-descriptor-only")
        elif type(row) is dict and row.get("path") == SYSTEM_INTERPRETER:
            metadata_pin(row, "container-system-interpreter-descriptor-not-host-file")
    for row in config.get("additional_public_pins", []):
        if row.get("policy") == "metadata-only-public-source-archive":
            require(row.get("path") in declared_bulk, "bulk metadata policy needs the exact configured archive")
            metadata_pin(row, "explicit-public-source-archive-descriptor-only")
    require(set(declared_bulk) <= set(metadata), "explicit bulk archive lacks an audited exact pin")
    for row in review.get("read_pins", []):
        require(type(row) is dict and set(row) == {"path", "bytes", "sha256"},
                "independent read pin is not closed")
        value = pin(row)
        if value["path"] in metadata:
            require({key: metadata[value["path"]][key] for key in value} == value,
                    "metadata-only archive differs from audited read pin")
        else:
            custody.select(value["path"], value)
    read_pins = review.get("read_pins")
    require(type(read_pins) is list and 1 <= len(read_pins) < MAX_FILES and
            len({row["path"] for row in read_pins}) == len(read_pins) and
            str(config_path) in {row["path"] for row in read_pins},
            "audit must retain the exact final configuration and unique named inputs")

    for key in ("final_reports", "final_scripts", "additional_json", "seal_extra_files"):
        values = config.get(key, [])
        require(type(values) is list and len(values) <= 256, "invalid explicit extra file list: " + key)
        for value in values:
            if type(value) is str:
                custody.select(owned(value))
            else:
                expected = pin(value)
                custody.select(owned(expected["path"]), expected)
    require(str(Path(__file__).absolute()) in custody.selected,
            "the frozen sealer must be named in final_scripts or seal_extra_files")
    for row in config.get("additional_public_pins", []):
        if row.get("policy") != "metadata-only-public-source-archive":
            value = pin(row)
            if value["path"] not in metadata:
                custody.select(value["path"], value)
    for row in config.get("explicit_exports", []):
        value = pin({"path": row["host_path"], "bytes": row["bytes"], "sha256": row["sha256"]})
        custody.select(owned(value["path"]), value)

    model_rows = model.get("public_files")
    require(type(model_rows) is list and len(model_rows) == 113 and
            len({row["path"] for row in model_rows}) == 113,
            "selected model inventory must name exactly 113 public files")
    model_root = selected("model_public")
    for row in model_rows:
        value = pin(row)
        require(owned(value["path"]).is_relative_to(model_root), "model public target escaped selected namespace")
        custody.select(value["path"], value)
    fixture_root = selected("fixture_public")
    for name in sorted(FIXTURE_NAMES):
        custody.select(fixture_root / name)
    actual_root = selected("actual_public")
    exports = actual.get("public_exports")
    execution = actual.get("owner_execution")
    require(type(exports) is list and 1 <= len(exports) <= 80 and type(execution) is dict and
            execution.get("qualified") is True and
            set(execution.get("public_files", [])) == {Path(row["path"]).name for row in exports} and
            len(execution.get("public_files", [])) == len(exports) == len({row["path"] for row in exports}),
            "actual public export inventory is not exact")
    for row in exports:
        value = pin(row)
        require(owned(value["path"]).parent == actual_root, "actual export escaped selected namespace")
        custody.select(value["path"], value)

    baseline = custody.load(STAGE / "preservation-baseline.json")
    dependencies = custody.load(PREVIOUS / "preservation-final.json")
    previous = baseline.get("sealed_previous_files")
    occurrences = dependencies.get("occurrences")
    require(type(previous) is list and len(previous) == baseline.get("verified_file_occurrences") == 650,
            "expected all 650 previous sealed file occurrences")
    require(type(occurrences) is list and len(occurrences) == dependencies.get("checked_occurrences") == 356 and
            dependencies.get("occurrences_deduplicated") is False,
            "expected all 356 dependency occurrences without deduplication")
    preservation = []
    for ordinal, row in enumerate(previous):
        value = pin(row)
        custody.select(value["path"], value)
        preservation.append({"group": "previous-sealed", "ordinal": ordinal, "expected": value})
    for ordinal, row in enumerate(occurrences):
        expected = pin(row["expected"])
        require(row.get("unchanged") is True and pin(row["actual"]) == expected,
                "dependency occurrence was not retained unchanged")
        custody.select(expected["path"], expected)
        preservation.append({"group": "previous-dependency", "ordinal": ordinal, "expected": expected})

    tests = custody.load(selected("tests_report"))
    custody.select(selected("tests_xml"))
    counts = review.get("counts", {})
    expected_tests = counts.get("final_unique_tests")
    require(type(expected_tests) is int and 1 <= expected_tests <= 10000,
            "independent audit must name the final exact unique test census")
    require(tests.get("qualified") is True and tests.get("exit_code") == 0 and
            tests.get("source_bytes_unchanged") is True and
            tests.get("counts") == {"tests": expected_tests, "unique_tests": expected_tests,
                                   "failures": 0, "errors": 0, "skips": 0} and
            tests.get("source_pins_before") == tests.get("source_pins_after") and
            len(tests.get("source_pins_after", [])) == 9, "final test qualification is not exact")
    for row in tests["source_pins_after"]:
        value = pin(row)
        require(absolute(value["path"]) == CHECKOUT / row["relative_path"], "test pin target differs from checkout")
        custody.select(value["path"], value)
    package = custody.load(selected("package_report"))
    require(package.get("qualified") is True and package.get("files") == 9 and
            package.get("exact_scratch_application") is True, "source package was not qualified")
    value = pin(package["patch"])
    custody.select(owned(value["path"]), value)
    require(len(package.get("sources", [])) == 9, "package must include all nine source/test rows")
    for row in package["sources"]:
        for key in ("current", "applied"):
            value = pin(row[key])
            custody.select(value["path"], value)

    summary = custody.load(actual_root / "summary.json")
    require(counts.get("native_admitted_benchmark_runtime_START_used") is True and
            counts.get("actual_native_worker_observer_invocations") == 1 and
            counts.get("actual_provider_calls") == 0 and summary.get("qualified") is True and
            summary.get("native_admitted_benchmark_runtime_START_used") is True and
            summary.get("actual_native_worker_observer_invocations") == 1 and summary.get("provider_calls") == 0,
            "actual START fact requires the selected qualified native evidence and passing audit")
    disposal = actual.get("container_disposal", {})
    require(disposal.get("container_absent") is True and disposal.get("only_exact_owned_container_removed") is True,
            "qualified owned container disposal is required")
    files = [custody.selected[name] for name in sorted(custody.selected)]
    result = {
        "schema": SCHEMA, "qualified": True,
        "files": files, "explicit_named_file_count": len(files),
        "file_set_sha256": digest(wire(files)),
        "independent_review": custody.selected[str(review_path)],
        "review_config": custody.selected[str(config_path)],
        "independent_check_count": review["check_count"],
        "metadata_only_descriptors": [metadata[name] for name in sorted(metadata)],
        "metadata_only_descriptor_count": len(metadata),
        "audit_metadata_preserved_as_report_data_only": True,
        "preservation_occurrences": preservation,
        "previous_sealed_occurrences": 650, "previous_dependency_occurrences": 356,
        "preservation_occurrences_deduplicated": False,
        "selected_model_public_files": 113, "selected_fixture_public_files": 13,
        "selected_actual_public_exports": len(exports), "selected_source_test_files": 9,
        "selected_unique_tests": expected_tests,
        "selected_qualification": {
            key: str(selected(key)) for key in ("actual_result", "actual_public", "model_result", "model_public",
                                                "fixture_public", "tests_report", "tests_xml", "package_report")},
        "native_admitted_benchmark_runtime_START_used": True,
        "actual_worker_observer_invocations": 1, "owned_experiment_container_removed": True,
        "process_outcome_scope": "Attributed to the pinned qualified native application evidence; public snapshots do not recreate original owner objects or prove receipt-emitter kernel provenance.",
        "retained_file_witnesses_rechecked": True, "fresh_reopen_required": True,
        "recursive_traversal": False, "provider_calls": 0, "training_steps": 0, "project_pushes": 0,
    }
    for key in (
        "full_supervisor_entrypoint_used", "Terminal_Bench_harness_used", "global_task_budget_enforced",
        "durable_budget_resume_supported", "provider_usage_measured", "provider_billing_savings_measured",
        "provider_or_task_billing_savings_measured", "full_task_satisfaction", "convergence_proved",
        "training_convergence_proved", "source_to_model_equivalence_proved", "source_body_executed",
        "proof_authority", "completion_authority", "omission_authority", "mutation_authority",
        "production_admitted", "loaded_module_code_attested", "transitive_dependency_closure_attested",
        "public_snapshots_reconstitute_original_owner_authority", "receipt_emitter_kernel_origin_proved",
        "database_bodies_included", "private_cas_bodies_included", "ducklake_parquet_bodies_included",
    ):
        result[key] = False
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--verify", action="store_true")
    options = parser.parse_args()
    config_path = owned(options.config)
    require(config_path.parent == STAGE, "final audit configuration must be a direct stage file")
    custody = Custody()
    try:
        retained_manifest = custody.capture(MANIFEST, output=True) if options.verify else None
        if not options.verify:
            require(not os.path.lexists(MANIFEST), "exclusive final evidence seal already exists")
        result = build(custody, config_path)
        raw = document(result)
        require(len(raw) <= MAX_BYTES, "final evidence manifest exceeds 8MiB")
        if options.verify:
            require(retained_manifest == raw, "sealed evidence/counts/hash differ from the exact rebuilt manifest")
            custody.recheck()
        else:
            custody.recheck()
            fd = os.open(MANIFEST.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                         0o600, dir_fd=custody.directory_fd)
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.fsync(custody.directory_fd)
        print(json.dumps({"qualified": True, "verified": options.verify, "files": len(result["files"]),
                          "manifest_bytes": len(raw), "manifest_sha256": digest(raw),
                          "file_set_sha256": result["file_set_sha256"]}, sort_keys=True))
    finally:
        custody.close()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"qualified": False, "error_type": type(error).__name__,
                          "error": str(error)}, sort_keys=True), file=sys.stderr)
        raise SystemExit(1)
