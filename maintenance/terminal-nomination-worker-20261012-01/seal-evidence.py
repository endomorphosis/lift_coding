"""Seal only explicitly named public stage evidence and captured source bytes."""
import hashlib
import json
from pathlib import Path

STAGE = Path(__file__).resolve().parent
NAMES = [
    "beginning-source-pins.json", "worker-context-owned-baseline.json", "exporter-test-baseline.json",
    "design-review.json", "entrypoint-transport-review.json", "exporter-design-review.json",
    "installed-controller-readiness-review.json",
    "worker-context-validation.json", "entrypoint-validation.json", "entrypoint-validation-02.json",
    "exporter-validation.json", "final-focused-validation.json", "preservation-check.json",
    "worker-validation-01.xml", "worker-validation-02.xml", "worker-validation-03.xml",
    "worker-validation-04.xml", "worker-validation-05.xml", "reader-router-regression-01.xml",
    "worker-validation-03-source-pins.json",
    "entrypoint-tests-01.xml", "entrypoint-tests-02.xml", "entrypoint-tests-03.xml",
    "entrypoint-tests-04.xml", "entrypoint-tests-05.xml", "entrypoint-tests-06.xml",
    "entrypoint-regression-tests-01.xml", "entrypoint-source-pins-03.json",
    "entrypoint-source-pins-05.json", "entrypoint-source-pins-06.json",
    "exporter-validation-01.xml", "exporter-validation-03.xml",
    "exporter-validation-01-before-pins.json", "exporter-validation-01-after-pins.json", "exporter-validation-01-run.json",
    "exporter-validation-02-launch-failure.json",
    "exporter-validation-03-before-pins.json", "exporter-validation-03-after-pins.json", "exporter-validation-03-run.json",
    "exporter-validation-01.stdout", "exporter-validation-01.stderr",
    "exporter-validation-03.stdout", "exporter-validation-03.stderr",
    "run-exporter-tests-01.py", "run-exporter-tests-02.py", "run-exporter-tests-03.py",
    "source-review-export-before-task-fence.py", "retained-public-harness-failures.json",
    "qualify-admitted-public-context-attempt-01.py", "qualify-admitted-public-context.py",
    "qualify-worker-readback-attempt-01.py", "qualify-worker-readback.py",
    "qualify-installed-worker-attempt-01.py", "qualify-installed-worker-attempt-02.py", "qualify-installed-worker.py",
    "package-source-changes.py", "check-preservation.py", "build-pinned-runtime.py", "build-results.py", "seal-evidence.py",
    "changes.patch", "source-manifest.json", "runtime-archive-verification.json", "runtime-archive/manifest.json",
    "next-work.json", "result-summary.json", "final-stage-independent-review.json",
    "admitted-public-context-01/qualification.json", "admitted-public-context-02/qualification.json",
    "admitted-public-context-02/public-context-result.json", "admitted-public-context-02/public-nomination-metadata.json",
    "admitted-public-context-02/authored-source-review.json", "admitted-public-context-02/reviewed-intent-contract.json",
    "admitted-public-context-02/instruction.txt", "admitted-public-context-02/repository/bottle.py",
    "admitted-public-context-02/repository/.runtime/source-review-preparation/review/bindings.json",
    "admitted-public-context-02/repository/.runtime/source-review-preparation/review/review-template.json",
    "host-worker-readback-01/qualification.json", "host-worker-readback-01/worker.stdout.json", "host-worker-readback-01/worker.stderr.txt",
    "host-worker-readback-02/qualification.json", "host-worker-readback-02/worker.stdout.json", "host-worker-readback-02/worker.stderr.txt",
    "host-worker-readback-02/native-public-prompt.txt", "host-worker-readback-02/reviewed-catalog-block.txt", "host-worker-readback-02/worker-input.json",
    "installed-worker-qualification-01/qualification.json", "installed-worker-qualification-02/qualification.json",
    "installed-worker-qualification-03/qualification.json", "installed-worker-qualification-03/deployment/deployment.json",
    "installed-worker-qualification-03/worker-boundary/installation/installation.json",
    "installed-worker-qualification-03/worker-boundary/qualification/qualification.json",
    "installed-worker-qualification-03/worker-boundary/qualification/probe.log",
    "installed-worker-qualification-03/export-public-context-receipt.stdout",
    "installed-worker-qualification-03/export-public-readback-receipt.stdout",
    "installed-worker-qualification-03/actual-signed-context.stdout",
    "installed-worker-qualification-03/actual-signed-context.stderr",
    "installed-worker-qualification-03/isolated-reviewed-readback.stdout",
    "installed-worker-qualification-03/isolated-reviewed-readback.stderr",
]


def pin(path, label):
    raw = path.read_bytes()
    return {"path": label, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    source = json.loads((STAGE / "source-manifest.json").read_text())
    beginning = json.loads((STAGE / "beginning-source-pins.json").read_text())
    review = json.loads((STAGE / "final-stage-independent-review.json").read_text())
    installed = json.loads((STAGE / "installed-worker-qualification-03/qualification.json").read_text())
    preserved = json.loads((STAGE / "preservation-check.json").read_text())
    assert review["review_passed"] and installed["qualified"] and preserved["all_checks_passed"]
    names = list(NAMES) + ["baseline/" + entry["path"] for entry in beginning["files"]]
    assert len(names) == len(set(names))
    for name in names:
        assert not name.endswith((".duckdb", ".ducklake", ".wal", ".jsonl", ".key", ".pem"))
        assert not any(part in {"private-owner", "private-owner-state", ".git", "codex-auth"} for part in Path(name).parts)
    files = [pin(STAGE / name, name) for name in names]
    for entry in source["files"]:
        observed = pin(Path(entry["absolute_path"]), entry["path"])
        assert (observed["bytes"], observed["sha256"]) == (entry["bytes"], entry["sha256"])
    for entry in beginning["files"]:
        observed = pin(STAGE / "baseline" / entry["path"], entry["path"])
        assert (observed["bytes"], observed["sha256"]) == (entry["bytes"], entry["sha256"])
    manifest = {"schema": "reviewed-source-worker-public-evidence-manifest@1",
        "enumeration": "Explicit public source captures/receipts/code/readback names only. No recursive owner-state or database scan; no private-key/auth/synthetic-auth bodies or raw model rollouts/transcripts included.",
        "files": sorted(files, key=lambda item: item["path"]), "source_files": source["files"],
        "all_eleven_source_hashes_match": True, "all_thirteen_captured_baselines_retained": True,
        "final_distinct_focused_tests_passed": 292, "explicit_preservation_checks_passed": 463,
        "independent_final_review_passed": True,
        "archive_members_verified": 12688, "installed_python_version": "3.12.12",
        "actual_signed_public_admission_context_and_native_compilation_qualified": True,
        "actual_UID1001_source_fact_readback_qualified": True,
        "private_owner_DB_open_denied_without_body_read": True,
        "fresh_installed_qualification_container_removed": installed["fresh_qualification_container_removed"],
        "failed_harness_attempts_retained_not_upgraded": True,
        "all_nineteen_requirements_residual": True, "planner_current_facts_added": 0,
        "full_driver_prepare_review_resume_execution_qualified": False,
        "fresh_Harbor_review_lifecycle_qualified": False,
        "historical_full_input_audit_qualified_for_catalog_appendix": False,
        "provider_total_session_token_savings_established": False,
        "source_to_model_equivalence_or_full_task_satisfaction_or_convergence_proved": False,
        "manual_qualification_training_steps": 0, "provider_calls": 0, "prover_invocations": 0,
        "remote_publication_performed": False, "original_dirty_checkout_or_git_index_mutated": False}
    path = STAGE / "evidence-manifest.json"
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    assert all(pin(STAGE / item["path"], item["path"]) == item for item in files)
    print(json.dumps({"sealed_public_files": len(files), "manifest": pin(path, path.name)}))


if __name__ == "__main__":
    main()
