"""Seal only named public source captures, reports and generated prompt fixtures."""
import hashlib
import json
import os
from pathlib import Path
import stat

stage = Path(__file__).resolve().parent
names = [
    "beginning-source-pins.json", "catalog-audit-owned-baseline.json", "design-review.json",
    "root-qualifier-review.json", "root-qualifier-review-fixed.json",
    "audit-helper-validation.json", "audit-helper-validation-02-source-pins.json",
    "audit-helper-validation-01.xml", "audit-helper-validation-02.xml", "audit-live-regression-01.xml",
    "auditor-tests-01.xml", "auditor-tests-02.xml",
    "final-focused-validation.json", "source-manifest.json", "changes.patch", "preservation-check.json",
    "qualify-admitted-public-context.py", "qualify-catalog-audit.py", "qualify-catalog-audit-attempt-01.py",
    "qualify-catalog-audit-observation-retention-02.py", "qualify-installed-audit.py",
    "qualify-catalog-audit-attempt-03.py", "retained-public-harness-failures-final.json",
    "qualify-installed-audit-attempt-01.py", "installed-audit-qualification-01/qualification.json",
    "retained-public-harness-failures-installed.json", "retain-installed-public-failure.py",
    "auditor-tests-03.xml",
    "auditor-validation.json", "auditor-validation-02.json", "auditor-tests-04.xml",
    "claim-scope-clarification.json",
    "build-pinned-runtime.py", "runtime-archive-verification.json", "runtime-archive/manifest.json",
    "measure-public-packet-tokens.py", "installed-local-packet-token-measurement.json",
    "host-local-packet-token-measurement.json", "retain-public-failures.py", "retained-public-harness-failures.json",
    "retain-final-public-failures.py", "root-qualifier-review-final.json",
    "package-source-changes.py", "check-preservation.py", "build-focused-validation.py", "build-results.py", "seal-evidence.py",
    "result-summary.json", "next-work.json", "final-stage-independent-review.json",
    "admitted-public-context-01/qualification.json", "admitted-public-context-02/qualification.json",
    "admitted-public-context-02/public-context-result.json", "admitted-public-context-02/public-nomination-metadata.json",
    "admitted-public-context-02/authored-source-review.json", "admitted-public-context-02/reviewed-intent-contract.json",
    "admitted-public-context-02/instruction.txt",
    "host-model-audit-01/qualification.json", "host-model-audit-02/qualification.json", "host-model-audit-03/qualification.json", "host-model-audit-04/qualification.json",
    "installed-audit-qualification-02/qualification.json", "installed-audit-qualification-02/deployment/deployment.json",
    "installed-audit-qualification-02/worker-boundary/installation/installation.json",
    "installed-audit-qualification-02/worker-boundary/qualification/qualification.json",
    "installed-audit-qualification-02/worker-boundary/qualification/probe.log",
    "installed-audit-qualification-02/export-public-context-receipt.stdout",
    "installed-audit-qualification-02/export-public-audit-receipt.stdout",
    "installed-audit-qualification-02/actual-signed-context.stdout",
    "installed-audit-qualification-02/actual-signed-context.stderr",
    "installed-audit-qualification-02/actual-historical-model-audit.stdout",
    "installed-audit-qualification-02/actual-historical-model-audit.stderr",
]

def pin(path, name):
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(descriptor)
        assert stat.S_ISREG(before.st_mode) and before.st_size <= 8 * 1024 * 1024
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            body = stream.read(before.st_size + 1)
        after = os.fstat(descriptor)
        witness = lambda value: (value.st_dev, value.st_ino, value.st_mode, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
        assert witness(before) == witness(after) == witness(path.lstat()) and len(body) == before.st_size
    finally:
        os.close(descriptor)
    return {"path": name, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}

def read(name):
    return json.loads((stage / name).read_bytes())

focused = read("final-focused-validation.json")
sources = read("source-manifest.json")
beginning = read("beginning-source-pins.json")
review = read("final-stage-independent-review.json")
installed = read("installed-audit-qualification-02/qualification.json")
preserved = read("preservation-check.json")
assert focused["all_selected_cases_passed"] and review["review_passed"] and installed["qualified"] and preserved["all_checks_passed"]
names += ["baseline/" + row["path"] for row in beginning["files"]]
for row in focused["selected_reports"]:
    names.append(Path(row["path"]).relative_to(stage).as_posix())
for mode in ("expanded", "compact_v2", "legacy_v1", "identifiers"):
    for suffix in ("-receipt.json", "-model-input.txt"):
        names += ["host-model-audit-04/" + mode + suffix,
            "installed-audit-qualification-02/public-model-input-fixtures/" + mode + suffix]
names = sorted(set(names))
for name in names:
    assert not Path(name).is_absolute() and ".." not in Path(name).parts
    assert not name.endswith((".duckdb", ".ducklake", ".db", ".wal", ".jsonl", ".key", ".pem"))
    assert not any(part in {"private-owner", "private-owner-state", ".git", "codex-auth"} for part in Path(name).parts)
files = [pin(stage / name, name) for name in names]
for row in sources["files"]:
    observed = pin(Path(row["absolute_path"]), row["path"])
    assert (observed["bytes"], observed["sha256"]) == (row["bytes"], row["sha256"])
result = {
    "schema": "catalog-audit-explicit-public-evidence-manifest@1", "files": files, "source_files": sources["files"],
    "enumeration": "Named public evidence and generated provider-free prompt fixtures only; no recursive owner-state/database/credential/model transcript discovery.",
    "all_six_current_source_pins_match": True, "all_nine_captured_baselines_retained": True,
    "independent_final_review_passed": True, "public_preservation_checks_passed": preserved["pin_checks"],
    "same_runtime_historical_complete_task_model_input_audit_qualified": True,
    "host_matrix_positive_cases": 12, "installed_matrix_positive_cases": 12,
    "host_matrix_negative_cases": 4, "installed_matrix_negative_cases": 4,
    "installed_actual_imported_producer_archive_hash_joins": 10,
    "local_offline_complete_packet_tokens_measured": True, "provider_session_token_savings_established": False,
    "all_nineteen_task_requirements_residual": True, "source_equivalence_full_task_satisfaction_or_convergence_proved": False,
    "cross_runtime_historical_replay_supported": False, "current_freshness_or_dispatch_authority_granted": False,
    "provider_calls": 0, "manual_training_steps": 0, "prover_invocations": 0,
    "remote_publication_performed": False, "original_dirty_checkout_or_git_index_mutated": False,
    "failed_attempts_retained_not_upgraded": True,
    "fresh_installed_container_removed": installed["fresh_qualification_container_removed"],
}
output = stage / "evidence-manifest.json"
assert not output.exists()
output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
assert all(pin(stage / row["path"], row["path"]) == row for row in files)
print(json.dumps({"files": len(files), "manifest": pin(output, output.name)}))
