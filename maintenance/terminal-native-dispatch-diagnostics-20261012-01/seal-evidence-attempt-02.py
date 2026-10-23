"""Seal only explicitly named public stage-N evidence after final review.

No discovery, archive/database/key/raw-worker-log body reads, production imports,
provider calls, tests or Git writes. All three failed actual runs stay retained.
Run only when the root supplies the independently pinned final documents.
"""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import xml.etree.ElementTree as ET

N = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("stage_n_explicit_public_guards", N / "check-preservation.py")
guards = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guards)
C, M = guards.C, guards.M
MAX_FILES = 250
MAX_TOTAL_BYTES = 96_000_000
MAX_FILE_BYTES = 8_000_000
MAX_METADATA_BYTES = 8_000_000
PRODUCER = "ipfs_accelerate_py/agent_supervisor/runtime/native_dispatch_diagnostics.py"
DAEMON = "ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py"
PRODUCER_TEST = "test/api/test_native_dispatch_diagnostics.py"
DRIVER_TEST = "benchmarks/agent_supervisor/container_coding/test_terminal_native_dispatch_diagnostics.py"
REQUIRED_NAMES = (
    "source-manifest.json", "changes.patch", "patch-qualification.json", "preservation-check.json",
    "final-source-pins.json", "final-focused-validation.json", "result-summary.json", "next-work.json",
    "final-review.json", "beginning-source-pins.json", "native-gap-analysis.json",
    "generation-03-additional-baseline.json", "generation-03-production-pins-final.json",
    "diagnostic-owned-baseline.json", "driver-diagnostic-test-baseline.json",
    "diagnostic-producer-validation.json", "diagnostic-producer-validation-02.json",
    "diagnostic-producer-validation-03.json", "driver-diagnostics-validation.json",
    "driver-diagnostics-validation-02.json", "driver-diagnostics-validation-03.json",
    "generation-01-owned-retention.json", "generation-02-owned-retention.json",
    "generation-02-all-source-pins.json", "generation-02-production-pins.json",
    "generation-02-peer-validation-review.json", "driver-diagnostics-generation2-test-before.json",
    "driver-diagnostics-generation3-test-before.json", "package-stage.py", "check-preservation.py",
    "check-preservation-before-mixed-inventory-fix.py", "preservation-prewrite-failure-01.json",
    "qualify-retained-harbor.py", "qualifier-generation01.py", "seal-evidence.py",
    "seal-evidence-attempt-01.py", "seal-prewrite-failure-01.json",
    "runtime-archive/manifest.json", "runtime-archive-final-02/manifest.json",
    "runtime-archive-fixed-03/manifest.json", "runtime-archive-verification.json",
    "runtime-archive-final-02-verification.json", "runtime-archive-fixed-03-verification.json",
)
PRODUCER_ATTEMPTS = (
    "producer-tests-01", "producer-tests-02", "producer-tests-03", "producer-tests-04",
)
PRODUCER_ATTEMPT_NAMES = (
    "argv.json", "pins-before.json", "pins-after.json", "stdout.txt", "stderr.txt", "tests.xml",
)
LIFECYCLE_NAMES = (
    "controller-result.json", "template.json", "baseline.json", "authored-review.json",
    "prepare_only-public-report.json", "resume-public-report.json", "prepare_only-attempt.json",
    "resume-attempt.json", "prepare_only-execution.json", "resume-execution.json",
)
ACTUAL_NAMES = (
    "qualification.json", "named-owner-public-metadata.stdout", "named-owner-public-metadata.stderr",
    "installed-import-provenance.stdout", "installed-import-provenance.stderr", "original-head.txt",
    "deployment/deployment.json", "worker-boundary/deployment.json",
    "worker-boundary/installation/installation.json", "worker-boundary/qualification/qualification.json",
)
OPTIONAL_NAMES = (
    "generation-03-production-pins.json", "public-task-metadata.json", "public-task-image.json",
    "public-task-inputs/instruction.md", "public-task-inputs/task.toml",
    "public-task-inputs/environment/Dockerfile", "public-task-inputs/reviewed-intent-contract.json",
    "build-pinned-runtime.py", "build-stage-results.py", "capture-fresh-driver-diagnostics.py",
    "package.stdout", "package.stderr", "preservation.stdout", "preservation.stderr",
    "packaging.stdout", "packaging.stderr", "preservation-failed-01.stdout", "preservation-failed-01.stderr",
    "final-stats.json", "root-final-stats.json",
    "actual-01.stdout", "actual-01.stderr", "actual-02.stdout", "actual-02.stderr",
    "actual-03.stdout", "actual-03.stderr", "native-dispatch-gap-analysis.json",
    "native-dispatch-cause-review-01.json", "native-dispatch-cause-review-02.json",
    "native-dispatch-cause-review-03.json", "installed-qualification-review.json",
    "generation-03-packaging-before/package-stage.py", "generation-03-packaging-before/check-preservation.py",
)
ARCHIVE_NAMES = ("runtime-archive", "runtime-archive-final-02", "runtime-archive-fixed-03")
EXPLICIT_NAMES = set(REQUIRED_NAMES)
for attempt in PRODUCER_ATTEMPTS:
    EXPLICIT_NAMES.update(attempt + "/" + name for name in PRODUCER_ATTEMPT_NAMES)
    EXPLICIT_NAMES.update(attempt + "/sources/" + name for name in (PRODUCER, DAEMON, PRODUCER_TEST))
for tag in ("01", "02", "03"):
    base = "actual-harbor-lifecycle-" + tag
    EXPLICIT_NAMES.update(base + "/" + name for name in ACTUAL_NAMES)
    EXPLICIT_NAMES.update(base + "/lifecycle/" + name for name in LIFECYCLE_NAMES)
for tag in ("01", "02", "03", "04", "05", "06"):
    EXPLICIT_NAMES.add("driver-diagnostics-tests-" + tag + ".xml")
    EXPLICIT_NAMES.add("driver-diagnostics-source-pins-before-" + tag + ".json")
    EXPLICIT_NAMES.add("driver-diagnostics-source-pins-after-" + tag + ".json")
OPTIONAL_NAMES = set(OPTIONAL_NAMES)
for attempt in PRODUCER_ATTEMPTS:
    OPTIONAL_NAMES.update(attempt + "/" + name for name in ("run.json", "environment.json"))
for archive in ARCHIVE_NAMES:
    OPTIONAL_NAMES.update(archive + "-build." + suffix for suffix in ("stdout", "stderr"))
for generation in ("01", "02"):
    EXPLICIT_NAMES.update("generation-" + generation + "-owned-sources/" + name
        for name in (PRODUCER, DAEMON, PRODUCER_TEST))
EXPLICIT_NAMES.add("driver-diagnostics-generation1-snapshot/" + DRIVER_TEST)
EXPLICIT_NAMES.add("generation-02/sources/" + DRIVER_TEST)
# These source pin reports were candidate-only; absence is retained explicitly.
OPTIONAL_NAMES.update(EXPLICIT_NAMES - set(REQUIRED_NAMES))
EXPLICIT_NAMES = set(REQUIRED_NAMES)
FILES, CATEGORIES, PIN_JOINS = {}, {}, []


def nominate(path, category, *, expected_sha=None, expected_bytes=None):
    path = guards.public_path(path)
    guards.require(path.is_relative_to(N) or path.is_relative_to(C), "Only named new-stage/source files")
    guards.require(not str(path).endswith((".tar", ".tar.gz", ".tgz", ".zip")) and path.suffix != ".log"
        and path.name not in {"synthetic-auth.json", "auth.json"}, "Archive/auth/raw log body excluded")
    if str(path) not in FILES:
        observed, _ = guards.capture(path, maximum=MAX_FILE_BYTES)
        FILES[str(path)] = observed
    observed = FILES[str(path)]
    CATEGORIES.setdefault(str(path), set()).add(category)
    guards.require(len(FILES) <= MAX_FILES and sum(row["bytes"] for row in FILES.values()) <= MAX_TOTAL_BYTES,
        "Explicit evidence census or byte budget exceeded")
    if expected_sha is not None:
        guards.require(observed["sha256"] == guards.digest(expected_sha), "Named evidence SHA differs: " + str(path))
    if expected_bytes is not None:
        guards.require(observed["bytes"] == guards.count(expected_bytes), "Named evidence bytes differ: " + str(path))
    if expected_sha is not None or expected_bytes is not None:
        PIN_JOINS.append({"path": str(path), "expected_sha256": expected_sha,
            "expected_bytes": expected_bytes, "matched": True})
    return observed


def document(name, expected_sha=None):
    name = guards.relative(name)
    path = N / name
    pin = nominate(path, "named-public-document", expected_sha=expected_sha)
    captured = guards.witnesses[str(path)]
    value = guards.document(path, expected_sha)
    guards.require(guards.cache[str(path)] == pin and guards.witnesses[str(path)] == captured,
        "Named document changed between nomination and parse")
    return value


def exact_report(row):
    guards.require(type(row) is dict and type(row.get("path")) is str, "Explicit report pin required")
    path = guards.public_path(row["path"])
    guards.require(path.is_relative_to(N), "Validation report stays in stage namespace")
    relative = path.relative_to(N).as_posix()
    guards.require(relative in EXPLICIT_NAMES or relative in OPTIONAL_NAMES, "Unlisted validation report")
    return nominate(path, "validation-report", expected_sha=row["sha256"], expected_bytes=row["bytes"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--final-review-sha256", required=True)
    parser.add_argument("--source-manifest-sha256", required=True)
    parser.add_argument("--preservation-sha256", required=True)
    parser.add_argument("--result-summary-sha256", required=True)
    parser.add_argument("--next-work-sha256", required=True)
    args = parser.parse_args()
    output = N / "evidence-manifest.json"
    guards.require(not output.exists() and not output.is_symlink(), "Existing seal stays immutable")
    review = document("final-review.json", args.final_review_sha256)
    guards.require(review.get("schema") == "native-dispatch-diagnostics-final-independent-review@1"
        and review.get("review_passed") is True and review.get("blocking_summary_claim_findings") == [],
        "Pinned scoped independent review must pass")
    source = document("source-manifest.json", args.source_manifest_sha256)
    preservation = document("preservation-check.json", args.preservation_sha256)
    summary = document("result-summary.json", args.result_summary_sha256)
    next_work = document("next-work.json", args.next_work_sha256)
    guards.require(preservation["all_checks_passed"] is True, "Pinned prior-byte preservation required")
    guards.require(source["checkout"] == str(C) and source["existing_deltas"] == 4 and source["new_files"] == 3
        and source["runtime_source_files"] == 5 and source["host_test_files"] == 2
        and source["bridge_delta_explicitly_authorized"] is False, "Exact seven-file generation3 scope required")
    heads = guards.by_path(guards.rows(source["files"], 7))
    guards.require(set(heads) == guards.MANDATORY_EXISTING | guards.NEW, "Unexpected final source set")
    for name, row in heads.items():
        nominate(C / name, "final-source-head", expected_sha=row["sha256"], expected_bytes=row["bytes"])
    before = guards.beginning_sources()
    guards.require(len(before) == 5, "Exactly five original captures required")
    for row in before.values():
        nominate(Path(row["baseline"]), "original-source-capture", expected_sha=row["sha256"], expected_bytes=row["bytes"])
    nominate(N / "changes.patch", "clean-source-patch", expected_sha=source["patch_sha256"], expected_bytes=source["patch_bytes"])
    prior = guards.document(M / "evidence-manifest.json", guards.M_EVIDENCE_SHA)
    guards.require(prior["file_count"] == 261, "Fixed prior-stage inventory census differs")
    # Reading a fixed prior manifest is metadata-only. Its artifact bodies are
    # already rechecked by the separately pinned preservation receipt.
    all_names = EXPLICIT_NAMES | OPTIONAL_NAMES
    guards.require(len(all_names) + len(heads) + len(before) <= MAX_FILES, "Static named-file census exceeds bound")
    omitted_optional = []
    for name in sorted(EXPLICIT_NAMES):
        path = N / guards.relative(name)
        guards.require(path.name != "synthetic-auth.json", "Authentication file never selected")
        nominate(path, "explicit-public-stage-artifact")
    for name in sorted(OPTIONAL_NAMES - EXPLICIT_NAMES):
        path = N / guards.relative(name)
        try:
            optional_info = os.lstat(path)
        except FileNotFoundError:
            omitted_optional.append(name)
            continue
        if path.name.startswith("actual-") and path.name.endswith(".stderr") and optional_info.st_size != 0:
            omitted_optional.append(name)
            continue
        # Optional names are literal. No directory listing or arbitrary receipt
        # path is followed, and a linked/unsafe existing file still refuses.
        nominate(path, "explicit-optional-public-artifact")
    producer = document("diagnostic-producer-validation-03.json")
    driver = document("driver-diagnostics-validation-03.json")
    guards.require(producer["all_latest_passed"] is True and driver["all_latest_passed"] is True,
        "Latest producer/driver unit receipts must pass")
    all_keys, selected_reports = set(), []
    for label, receipt, expected_count in (("producer", producer, 183), ("driver", driver, 459)):
        guards.require(len(receipt["selected_reports"]) == 1, "One final report per suite required")
        row = receipt["selected_reports"][0]
        pin = exact_report(row)
        _, raw = guards.capture(Path(pin["path"]), maximum=2_000_000, retain=True)
        cases = list(ET.fromstring(raw).iter("testcase"))
        keys = {(case.attrib.get("classname", ""), case.attrib["name"]) for case in cases}
        guards.require(len(keys) == len(cases) == expected_count and not (keys & all_keys)
            and all(case.find("failure") is None and case.find("error") is None and case.find("skipped") is None
                for case in cases), "Final JUnit census/outcomes differ")
        all_keys.update(keys)
        selected_reports.append({"suite": label, **pin, "distinct_cases": len(keys)})
    guards.require(len(all_keys) == 642, "Exactly642 distinct final unit cases required")
    actual = []
    for tag, archive_name in zip(("01", "02", "03"), ARCHIVE_NAMES):
        qualification = document("actual-harbor-lifecycle-" + tag + "/qualification.json")
        archive = document(archive_name + "/manifest.json")
        verification = document(archive_name + "-verification.json")
        guards.require(qualification["runtime_archive_sha256"] == archive["archive_sha256"]
            == verification["archive_sha256"] and verification["all_members_match_declared_bytes_modes_and_digests"] is True
            and archive["credentials_in_archive"] is False and archive["task_inputs_in_archive"] is False,
            "Generation-specific archive verification/scalar custody joins differ")
        members = guards.by_path(archive["files"])
        imports = qualification["installed_import_provenance"]["records"]
        guards.require(type(imports) is list and len(imports) == 17
            and qualification["installed_import_provenance"]["all_actual_imports_join_archive"] is True
            and qualification["qualified"] is False
            and qualification["fresh_container_removed"] is True, "All actual failed runs retained with removed containers")
        for imported in imports:
            guards.require(type(imported) is dict and imported["uid"] == 0
                and imported["path"].startswith("/opt/ipfs-supervisor/source/"), "Protected imported source provenance required")
            member = "source/" + imported["path"].removeprefix("/opt/ipfs-supervisor/source/")
            row = members.get(member)
            guards.require(row is not None and row["sha256"] == imported["sha256"] and row["bytes"] == imported["bytes"],
                "Actual imported producer differs from that generation's archive manifest")
        actual.append({"attempt": tag, "qualified": False, "container_removed": True,
            "imported_producer_count": len(imports), "all_imported_producers_join_manifest": True,
            "runtime_archive_sha256_reported": qualification["runtime_archive_sha256"]})
    # Recheck only already-opened, explicitly named file witnesses. This does
    # not scan prior artifact trees or read any database/cache/secret body.
    for name, recorded in guards.witnesses.items():
        handle, parent, info = guards.opened(Path(name))
        try:
            guards.require(guards.witness(info) == recorded
                == guards.witness(os.stat(Path(name).name, dir_fd=parent, follow_symlinks=False)),
                "Named file witness changed before sealing")
        finally:
            os.close(handle)
            os.close(parent)
    rows = [{**FILES[name], "categories": sorted(CATEGORIES[name])} for name in sorted(FILES)]
    value = {"schema": "native-dispatch-diagnostics-explicit-public-evidence-seal@1", "stage": str(N),
        "checkout": str(C), "files": rows, "file_count": len(rows), "source_count": len(heads),
        "original_source_capture_count": len(before), "aggregate_public_bytes_hashed": sum(row["bytes"] for row in rows),
        "pin_joins": PIN_JOINS, "pin_join_count": len(PIN_JOINS), "all_named_file_and_reference_guards_passed": True,
        "final_review_sha256": args.final_review_sha256, "source_manifest_sha256": args.source_manifest_sha256,
        "preservation_receipt_sha256": args.preservation_sha256, "result_summary_sha256": args.result_summary_sha256,
        "next_work_sha256": args.next_work_sha256, "prior_m_manifest_sha256": guards.M_EVIDENCE_SHA,
        "prior_public_artifact_bodies_rehashed_by_this_sealer": False,
        "distinct_final_unit_cases": len(all_keys), "selected_validation_reports": selected_reports,
        "actual_failed_attempts_retained": actual, "all_three_actual_runs_qualified": False,
        "explicit_optional_names_absent": omitted_optional, "recursive_filesystem_discovery": False,
        "runtime_archive_bodies_reopened": False, "database_or_cache_or_key_or_auth_or_raw_worker_log_body_selected": False,
        "synthetic_auth_including_empty_payload_selected": False, "tests_or_providers_executed_here": False,
        "source_or_git_or_prior_artifact_mutation": False, "unsealed_cache_or_database_never_touched_claimed": False,
        "source_semantics_or_equivalence_proved": False, "model_convergence_proved": False,
        "actual_model_input_or_task_success_inferred_by_seal": False, "provider_population_or_billing_or_token_savings_certified": False}
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    with output.open("xb") as stream:
        stream.write(raw)
    print(json.dumps({"evidence_manifest": str(output), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
        "file_count": len(rows), "distinct_final_unit_cases": len(all_keys)}))


if __name__ == "__main__":
    main()
