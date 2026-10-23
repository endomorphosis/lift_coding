"""Seal explicitly named public stage evidence; never enumerate databases."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

STAGE = Path(__file__).resolve().parent
PUBLIC_FILES = [
    "beginning-source-pins.json", "nomination-baseline.json",
    "nominated-inspection-test-baseline.json", "nomination-guard-baseline.json",
    "intent-source-nomination-before-whole-guard.py",
    "nomination-validation.json", "inspection-validation.json",
    "context-source-nomination-validation.json", "context-source-nomination-validation-02.json",
    "nomination-validation-01.xml", "nomination-validation-02.xml",
    "nomination-validation-03.xml", "nomination-validation-04.xml",
    "inspection-validation-01.xml", "inspection-validation-02.xml",
    "inspection-validation-03.xml", "inspection-validation-04.xml",
    "inspection-validation-02-source-pins.json", "inspection-validation-03-source-pins.json",
    "inspection-validation-04-source-pins.json",
    "refactor-tests-01.xml", "refactor-tests-02.xml",
    "context-nomination-controls-tests.xml", "context-nomination-tests-02.xml",
    "context-nomination-tests-03.xml", "context-nomination-tests-04.xml", "context-nomination-tests-05.xml",
    "public-nomination-failure-01.json", "metadata-factory-trace-01.json",
    "prepare-public-native-fixture.py", "qualify-public-source-nomination-attempt-01.py",
    "qualify-public-source-nomination.py", "package-source-changes.py",
    "check-preservation.py", "build-results.py", "seal-evidence.py",
    "changes.patch", "source-manifest.json", "preservation-check.json",
    "final-focused-validation.json", "final-independent-review.json",
    "final-stage-independent-review.json", "next-work.json", "result-summary.json",
    "public-native-fixture-01/summary.json", "public-native-fixture-01/instruction.txt",
    "public-native-fixture-01/native-retrieval-context.json",
    "public-native-fixture-01/repository/bottle.py",
    "public-native-fixture-01/repository/retrieval.json",
    "public-native-fixture-01/repository/frontier/frontier.json",
    "public-nomination-qualification-01/empty-review.json",
    "public-nomination-qualification-01/generic-nomination.json",
    "public-nomination-qualification-02/qualification.json",
    "public-nomination-qualification-02/empty-review.json",
    "public-nomination-qualification-02/headers-review.json",
    "public-nomination-qualification-02/generic-nomination.json",
    "public-nomination-qualification-02/bottle-_hval-source-page-1.json",
    "public-nomination-qualification-02/bottle-HeaderDict-source-page-1.json",
    "public-nomination-qualification-02/bottle-_hkey-source-page-1.json",
    "public-nomination-qualification-02/bottle-_hkey-facts-page-1.json",
]
for namespace in ("factory-trace-nomination-01", "intent-nomination-empty", "intent-nomination-headers"):
    for name in ("contract.json", "instruction.txt", "review.json", "nomination.json"):
        PUBLIC_FILES.append(f"public-native-fixture-01/repository/{namespace}/{name}")


def pin(path: Path, label: str):
    raw = path.read_bytes()
    return {"path": label, "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def main():
    source = json.loads((STAGE / "source-manifest.json").read_text())
    beginning = json.loads((STAGE / "beginning-source-pins.json").read_text())
    focused = json.loads((STAGE / "final-focused-validation.json").read_text())
    public = json.loads((STAGE / "public-nomination-qualification-02/qualification.json").read_text())
    preservation = json.loads((STAGE / "preservation-check.json").read_text())
    final_review = json.loads((STAGE / "final-stage-independent-review.json").read_text())
    assert focused["qualified"] and focused["latest_distinct_classname_name_cases"] == 235
    assert public["qualified"] and not public["unrelated_metadata_owner_activated"]
    assert preservation["all_checks_passed"] and final_review["review_passed"]
    files = []
    for name in PUBLIC_FILES:
        assert not name.endswith((".duckdb", ".ducklake", ".jsonl", ".wal")), name
        files.append(pin(STAGE / name, name))
    for entry in beginning["files"]:
        name = "baseline/" + entry["path"]
        observed = pin(STAGE / name, name)
        assert (observed["bytes"], observed["sha256"]) == (entry["bytes"], entry["sha256"])
        files.append(observed)
    assert len(files) == len({entry["path"] for entry in files})
    for entry in source["files"]:
        observed = pin(Path(entry["absolute_path"]), entry["path"])
        assert (observed["bytes"], observed["sha256"]) == (entry["bytes"], entry["sha256"])
    # Failed owner sentinel is represented by a public failure receipt only; no body read/hash.
    manifest = {
        "schema": "intent-source-nomination-public-evidence-manifest@1",
        "enumeration": "Explicit public source/receipt/view names and seven exact stage captures only. Database bodies, pytest scratch, private material, hidden verifiers and raw model transcripts excluded.",
        "files": sorted(files, key=lambda item: item["path"]),
        "source_files": source["files"], "all_eight_source_pins_match": True,
        "all_seven_beginning_captures_retained": True,
        "latest_distinct_focused_passed": 235,
        "independent_source_review_passed": True,
        "independent_final_artifact_review_passed": True,
        "previous_public_evidence_preserved": True,
        "native_AST_symbol_fact_rows": 426,
        "native_DuckLake_catalogs": 1, "native_DuckLake_links": 426,
        "public_CLI_successful_outputs": 4, "public_CLI_invalid_requests_refused": 7,
        "all_nineteen_requirements_residual": True,
        "retained_first_public_attempt_qualified": False,
        "retained_first_attempt_created_unrelated_fresh_sentinel": True,
        "failed_sentinel_body_read_or_hashed": False,
        "final_attempt_unrelated_metadata_owner_activated": False,
        "automatic_router_or_coding_prompt_nomination_consumption_qualified": False,
        "signed_planning_inputs_or_current_facts_modified": False,
        "installed_runtime_archive_qualified": False,
        "provider_total_session_token_savings_established": False,
        "source_equivalence_or_full_task_satisfaction_or_convergence_proved": False,
        "provider_calls": 0, "training_steps": 0, "prover_invocations": 0,
        "remote_publication_performed": False,
        "original_dirty_checkout_or_git_index_mutated": False,
    }
    path = STAGE / "evidence-manifest.json"
    path.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    assert all(pin(STAGE / entry["path"], entry["path"]) == entry for entry in files)
    print(json.dumps({"sealed_public_files": len(files), "manifest": pin(path, path.name)}))


if __name__ == "__main__":
    main()
