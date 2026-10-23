"""Seal explicitly named public call-model evidence; never traverse databases.

Run only after the actual qualification and independent review are complete.
The seal binds bytes and retained file witnesses, not loaded-code attestation,
process origin, Python runtime/import equivalence, or training convergence.
"""
import hashlib
import json
import os
from pathlib import Path
import stat


T = Path(__file__).resolve().parent
C = T.parent / "terminal-token-reduction-20261007-01/checkout"
DEPENDENCIES = T.parent / "terminal-compact-retrieval-20261011-01/pinned-dependencies-v10"
ACTUAL_PREFIX = "actual-public-call-"
MAX_BYTES = 16 * 1024**2
PUBLIC_SUFFIXES = {".json", ".jsonl", ".lean", ".olean", ".py", ".stdout", ".stderr"}
NAMES = (
    "baseline-manifest.json", "runtime-source-pins.json", "source-manifest.json",
    "changes.patch", "patch-validation.json", "predecessor-preservation.json",
    "experiment-plan.json", "next-work.json", "result.json", "actual-qualification.json",
    "actual-run.json", "actual.stdout", "actual.stderr",
    "actual-02-run.json", "actual-02.stdout", "actual-02.stderr", "independent-review.json",
    "excluded-history.json", "tests.xml", "tests-run.json", "tests.stdout", "tests.stderr",
    "projection-tests-01.xml", "projection-tests-01-run.json", "projection-tests-01.stdout",
    "projection-tests-01.stderr", "projection-tests-02.xml", "projection-tests-02-run.json",
    "projection-tests-02.stdout", "projection-tests-02.stderr",
    "agent-call-composition-01.xml", "agent-call-composition-01-run.json",
    "agent-call-composition-02.xml", "agent-call-composition-02-run.json",
    "qualify-public-call-ir.py", "qualify-public-call-ir-02.py",
    "cold-validate-call-ir.py", "seal-call-ir-evidence.py",
)
CANDIDATE01_NAMES = (
    "runtime-source-pins.json", "source-manifest.json", "changes.patch", "patch-validation.json",
    "predecessor-preservation.json", "tests.xml", "tests-run.json", "tests.stdout", "tests.stderr",
    "original-runtime-source-pins.json", "original-source-manifest.json", "original-changes.patch",
    "original-patch-validation.json", "original-predecessor-preservation.json",
    "original-tests.xml", "original-tests-run.json", "original-tests.stdout", "original-tests.stderr",
)
FAILED_ACTUAL01_NAMES = (
    "head.json", "tool-policy.json", "repository/callee.py", "repository/caller.py", "repository/dynamic.py",
)
STAGE_PUBLIC_EXCEPTIONS = {T / name for name in (
    "qualify-public-call-ir.py", "qualify-public-call-ir-02.py", "cold-validate-call-ir.py",
    "runtime-source-pins.json", "actual-qualification.json",
)}


def need(value, message):
    if not value:
        raise ValueError(message)


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False).encode("utf-8")


def signature(value):
    return tuple(getattr(value, field) for field in (
        "st_dev", "st_ino", "st_mode", "st_uid", "st_gid", "st_nlink",
        "st_size", "st_mtime_ns", "st_ctime_ns",
    ))


class Readers:
    """Retain each selected regular-file descriptor until sealing is finished."""

    def __init__(self):
        self.records = []

    def capture(self, path, expected=None):
        path = Path(path)
        need(path.is_absolute() and path.resolve(strict=True) == path,
             "canonical absolute selected file required")
        parent = path.parent.lstat()
        need(stat.S_ISDIR(parent.st_mode), "regular selected file parent required")
        parent_identity = (parent.st_dev, parent.st_ino, parent.st_mode, parent.st_uid, parent.st_gid)
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        try:
            before = os.fstat(descriptor)
            need(stat.S_ISREG(before.st_mode) and before.st_nlink == 1
                 and 0 <= before.st_size <= MAX_BYTES, "bounded regular single-link file required")
            with os.fdopen(os.dup(descriptor), "rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
            need(len(raw) <= MAX_BYTES and signature(before) == signature(os.fstat(descriptor))
                 == signature(path.lstat()), "selected file changed during capture")
            pin = {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
            if expected is not None:
                need(pin == {key: expected[key] for key in pin}, "selected pinned bytes differ")
            self.records.append((path, descriptor, signature(before), parent_identity, raw, pin))
            return pin, raw
        except BaseException:
            os.close(descriptor)
            raise

    def json(self, path):
        _, raw = self.capture(path)
        value = json.loads(raw.decode("utf-8"))
        wire(value)  # Finite UTF8 JSON only; no native imports or callbacks.
        need(type(value) is dict, "selected JSON object required")
        return value

    def verify(self):
        for path, descriptor, before, parent_identity, original, _ in self.records:
            parent = path.parent.lstat()
            need((parent.st_dev, parent.st_ino, parent.st_mode, parent.st_uid, parent.st_gid)
                 == parent_identity and path.resolve(strict=True) == path,
                 "selected parent or canonical file custody changed")
            need(signature(os.fstat(descriptor)) == before == signature(path.lstat()),
                 "selected retained inode/stat witness changed")
            os.lseek(descriptor, 0, os.SEEK_SET)
            with os.fdopen(os.dup(descriptor), "rb") as stream:
                raw = stream.read(MAX_BYTES + 1)
            need(raw == original and signature(os.fstat(descriptor)) == before
                 == signature(path.lstat()), "selected retained bytes or stat witness changed")

    def close(self):
        for _, descriptor, *_ in reversed(self.records):
            os.close(descriptor)


def main():
    destination = T / "evidence-manifest.json"
    need(not destination.exists() and not destination.is_symlink(), "fresh evidence seal required")
    selected = Readers()
    try:
        baseline = selected.json(T / "baseline-manifest.json")
        need(baseline["schema"] == "terminal-call-ir-composition-baseline@1"
             and len(baseline["dependencies"]) == 11 and len(baseline["new_sources"]) == 4
             and all(row["exists"] is False for row in baseline["new_sources"]), "baseline population differs")
        selected.capture(baseline["sealed_predecessor"]["path"], baseline["sealed_predecessor"])
        predecessor = selected.json(baseline["sealed_predecessor"]["path"])
        need(predecessor["schema"] == "terminal-source-ir-evidence-seal@1"
             and predecessor["explicit_named_file_count"] == len(predecessor["files"]) == 172,
             "selected predecessor population differs")
        preserved = []
        for group, entries in (
            ("sealed_predecessor_named_file", predecessor["files"]),
            ("sealed_predecessor_manifest", [baseline["sealed_predecessor"]]),
            ("baseline_dependency", baseline["dependencies"]),
        ):
            for ordinal, entry in enumerate(entries, 1):
                pin, _ = selected.capture(entry["path"], entry)
                preserved.append({"group": group, "ordinal": ordinal, "expected": entry,
                    "actual": pin, "matched": True})
        need(len(preserved) == 184, "184 nondeduplicated preservation occurrences required")
        preservation = selected.json(T / "predecessor-preservation.json")
        need(preservation["occurrence_count"] == 184 and preservation["occurrences_deduplicated"] is False
             and preservation["all_pinned_bytes_preserved"] is True
             and wire(preservation["checks"]) == wire(preserved), "packaged preservation checks differ")
        runtime_manifest = selected.json(T / "runtime-source-pins.json")
        runtime = runtime_manifest["files"]
        need(runtime_manifest.get("candidate") == 2 and len(runtime) == 4 and {row["path"] for row in runtime}
             == {row["path"] for row in baseline["new_sources"]}, "four frozen sources required")
        for row in runtime:
            pin, raw = selected.capture(row["path"], row)
            snapshot = T / "final" / Path(row["path"]).relative_to(C)
            _, retained = selected.capture(snapshot)
            need(raw == retained, "final source snapshot differs")
        result = selected.json(T / "result.json")
        actual = selected.json(T / "actual-qualification.json")
        tests = selected.json(T / "tests-run.json")
        review = selected.json(T / "independent-review.json")
        need(result.get("qualified") is True and actual.get("qualified") is True
             and review.get("qualified") is True, "final qualified result, actual run and review required")
        actual_root = Path(actual["output"])
        attempt = actual_root.name.removeprefix(ACTUAL_PREFIX)
        need(actual["schema"] == "terminal-call-ir-public-qualification@1"
             and actual_root.is_absolute() and actual_root.parent == T
             and actual_root.name.startswith(ACTUAL_PREFIX) and len(attempt) == 2
             and attempt.isascii() and attempt.isdigit() and int(attempt) >= 2
             and actual_root.resolve(strict=True) == actual_root,
             "selected public actual qualification must stay in a fresh qualified stage attempt")
        need(tests["schema"] == "terminal-call-ir-final-tests@1"
             and type(tests["unique_tests"]) is int and tests["unique_tests"] == 164
             and type(tests["tests"]) is int and tests["tests"] == 164,
             "164 unique final tests required")
        need(all(type(tests[name]) is int and tests[name] == 0
                 for name in ("returncode", "failure", "error", "skipped")), "final test status differs")
        need(tests["pins_unchanged_at_endpoints"] is True
             and wire(tests["before_source_pins"]) == wire(runtime)
             == wire(tests["after_source_pins"]), "final test source pins differ")
        need(wire(actual["runtime_source_pins_before"]) == wire(runtime)
             == wire(actual["runtime_source_pins_after"]), "actual frozen source pins differ")
        need(actual["metadata"]["fresh_process_readback"]["verified"] is True,
             "actual native metadata readback required")
        cold = actual["fresh_process_cold_validation"]
        need(cold["data_validated"] is True and cold["cache_status"] == "hit"
             and cold["native_callee_cold_validation_passed"] is True
             and cold["caller_record_origin_verified"] is False and cold["checker_reinvoked"] is False,
             "fresh cold data and origin limits differ")
        need(type(actual["native_lean_processes"]) is int and actual["native_lean_processes"] == 6
             and type(actual["native_callee_prover_calls"]) is int and actual["native_callee_prover_calls"] == 1,
             "selected native process inventory differs")
        for value in (result, actual):
            need(all(value.get(key) is False for key in ("proof_authority", "source_semantics_verified",
                "python_import_resolution_proved", "training_convergence_proved", "source_body_executed")),
                "seal cannot promote runtime or convergence authority")
            need(all(type(value.get(key)) is int and value[key] == 0 for key in ("training_steps", "provider_calls")),
                 "zero training and provider counters required")
        public = actual["public_artifact_paths"]
        need(type(public) is list and 1 <= len(public) <= 1024 and all(type(path) is str for path in public)
             and len(public) == len(set(public)), "bounded unique explicit public artifact paths required")
        paths = {T / name for name in NAMES}
        archive = T / "candidate-01"
        paths.update(archive / name for name in CANDIDATE01_NAMES)
        paths.update(T / "actual-public-call-01" / name for name in FAILED_ACTUAL01_NAMES)
        archived_runtime = selected.json(archive / "runtime-source-pins.json")["files"]
        need(len(archived_runtime) == 4 and {row["path"] for row in archived_runtime}
             == {row["path"] for row in runtime}, "archived candidate source population differs")
        for row in archived_runtime:
            snapshot = archive / "final" / Path(row["path"]).relative_to(C)
            selected.capture(snapshot, {**row, "path": str(snapshot)})
            paths.add(snapshot)
        for text in public:
            path = Path(text)
            need(path.is_absolute() and path.resolve(strict=True) == path
                 and path.suffix in PUBLIC_SUFFIXES, "canonical explicit public artifact required")
            if path not in STAGE_PUBLIC_EXCEPTIONS:
                need(path.is_relative_to(actual_root) and path != actual_root
                     and not any(part.startswith(".") or part.lower() in {"cas", "lake", "ducklake", "parquet"}
                                 for part in path.relative_to(actual_root).parts),
                     "public artifact must stay in selected actual scope without private storage bodies")
            paths.add(path)
        for row in runtime:
            path = Path(row["path"])
            paths.update((path, T / "final" / path.relative_to(C)))
        projection_path, qualified_path = actual_root / "qualified/projection.json", actual_root / "qualified/result.json"
        need(str(projection_path) in public and str(qualified_path) in public,
             "selected public projection and caller record required")
        projection = selected.json(projection_path)
        qualified = selected.json(qualified_path)
        producer_pins = [*projection["producer"]["files"],
            *projection["callee_projection"]["producer"]["files"], *qualified["adapter_pins"].values()]
        need(len(producer_pins) <= 256, "selected direct producer inventory bound exceeded")
        for row in producer_pins:
            path = Path(row["path"])
            need(path.suffix == ".py" and (path.is_relative_to(C) or path.is_relative_to(DEPENDENCIES)),
                 "selected direct producer must remain in explicit source/dependency roots")
            selected.capture(path, row)
        rows = [selected.capture(path)[0] for path in sorted(paths, key=str)]
        selected.verify()
        need([selected.capture(path)[0] for path in sorted(paths, key=str)] == rows,
             "final named artifact recapture differs")
        for row in runtime:
            selected.capture(row["path"], row)
        selected.verify()
        seal = {"schema": "terminal-call-ir-evidence-seal@1", "stage": str(T), "files": rows,
            "explicit_named_file_count": len(rows), "predecessor_preservation_occurrences": 184,
            "preservation_occurrences_deduplicated": False, "selected_direct_producer_pin_occurrences": len(producer_pins),
            "retained_inode_stat_witnesses_rechecked": True, "recursive_traversal": False,
            "database_and_cas_bodies_hashed": False, "ducklake_and_parquet_bodies_hashed": False,
            "native_storage_verified_by_actual_readback": True, "public_json_exports_and_batches_hashed": True,
            "private_database_or_auth_data_included": False, "raw_worker_or_model_transcripts_included": False,
            "selected_qualification": actual_root.name, "selected_candidate": 2,
            "development_failures_retained_and_excluded": True,
            "prior_candidate_source_snapshots_retained_and_excluded": True,
            "archived_candidate01_master_report_copies": len(CANDIDATE01_NAMES),
            "failed_actual01_named_public_files": len(FAILED_ACTUAL01_NAMES),
            "selected_native_lean_processes": 6, "unique_tests": 164, "training_steps": 0, "provider_calls": 0,
            "source_body_executed": False, "proof_authority": False, "source_semantics_verified": False,
            "python_import_resolution_proved": False, "training_convergence_proved": False,
            "loaded_module_code_attested": False, "transitive_dependency_closure_attested": False,
            "caller_record_origin_verified": False}
        raw = wire(seal)
        selected.verify()
        descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(descriptor)
        finally:
            os.close(descriptor)
        selected.verify()
        print(json.dumps({"sealed_files": len(rows), "seal_sha256": hashlib.sha256(raw).hexdigest(),
            "qualified": True, "unique_tests": 164, "preservation_occurrences": 184}, sort_keys=True))
    finally:
        selected.close()


if __name__ == "__main__":
    main()
