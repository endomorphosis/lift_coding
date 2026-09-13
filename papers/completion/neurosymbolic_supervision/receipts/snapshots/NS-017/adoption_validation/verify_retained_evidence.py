#!/usr/bin/python3.12
"""Ordinary NS-017 retained-evidence check. No grants, providers, scorers, or reruns."""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve()
while not (ROOT / "scripts" / "paper_supervisors.py").is_file():
    if ROOT.parent == ROOT:
        raise SystemExit("repository root not found")
    ROOT = ROOT.parent

TEMPLATE = ROOT / (
    "papers/completion/neurosymbolic_supervision/qualification/operator_inputs/"
    "NS-017/pending_receipt.template.json"
)
BUNDLE = ROOT / (
    "papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-016/"
    "post32_completion_v1/actual_bundle_manifest.json"
)
FREEZE = ROOT / "papers/completion/neurosymbolic_supervision/artifacts/final_experiment_freeze.json"
OBJECTS = ROOT / (
    "papers/completion/neurosymbolic_supervision/qualification/operator_inputs/NS-017/objects"
)
TEMPLATE_SHA = "384f24146bdd10e93b690a21e6a987c8d8329691482d0e4d36d0314fd60576d6"
BUNDLE_SHA = "f8488d8e69f097a8332ec6ae41aded6b260e5ad8df90531bd539d6f9e85b4f46"
FREEZE_FILE_SHA = "7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a"
FREEZE_CANONICAL_SHA = "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d"
ANALYSIS_SHA = "824366e7fb10725be884b04448d5b4a8dd2ff5c478af5df7a8c98721f4641766"
INCOMPLETE_HIDDEN_CELL = "5b9fa96eca823dc3ffd30cbb91900160bc9cfa53476b5fe5bb462b114b47b1a1"
FAMILIES = (
    "ns-hist-09-tomlkit",
    "ns-hist-10-installer",
    "ns-hist-11-tornado",
    "ns-hist-12-more-itertools",
    "ns-hist-13-charset_normalizer",
    "ns-hist-14-iniconfig",
    "ns-hist-15-wheel",
    "ns-hist-16-jinja",
)
REPS = (104729, 130363)
CRITERIA = (
    "All planned task-arm-repeat units have an actual terminal record or explicitly documented missingness; denominator changes are prohibited after outcomes.",
    "Useful completions are independently validated and linked to admitted publication where the arm requires it.",
    "Actual provider and stage measurements support the final cost fields; estimated/unavailable data remain distinct.",
    "Raw records and deviations bind the immutable final experiment freeze and are sufficient for independent rescoring.",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path):
    return json.loads(path.read_bytes())


def load_jsonl(path: Path):
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(message)


def main() -> int:
    template_raw = TEMPLATE.read_bytes()
    require(hashlib.sha256(template_raw).hexdigest() == TEMPLATE_SHA, "operator pending-receipt template hash changed")
    template = json.loads(template_raw)
    require(template.get("task_id") == "NS-017", "template task_id is not NS-017")
    require(template.get("schema") == "paper-task-evidence/v1", "template schema mismatch")
    require([c.get("criterion") for c in template.get("criteria", [])] == list(CRITERIA), "original NS-017 criteria changed")
    print("pending_receipt_template_sha256", TEMPLATE_SHA)

    matched = 0
    for current, snapshot in template["outputs"].items():
        expected = template["artifacts"][snapshot]
        current_path = ROOT / current
        snapshot_path = ROOT / snapshot
        require(sha(current_path) == expected and sha(snapshot_path) == expected, "hash mismatch: " + current)
        matched += 1
    print("retained_output_snapshot_pairs", matched)

    bundle_sha = sha(BUNDLE)
    require(bundle_sha == BUNDLE_SHA, "actual32 bundle manifest hash changed")
    bundle = load_json(BUNDLE)
    require(
        bundle.get("schema") == "ns017-actual-final32-preinstallation-bundle/v1"
        and bundle.get("success") is True
        and bundle.get("fixture", False) is not True
        and bundle.get("actual_terminal_cells") == 32
        and bundle.get("current_output_count") == 5
        and bundle.get("scientific_calls") == 0
        and bundle.get("native_writes") == 0
        and bundle.get("pending_receipt_template", {}).get("sha256") == TEMPLATE_SHA,
        "actual32 bundle admission fields differ",
    )
    files = bundle.get("files")
    require(isinstance(files, dict) and len(files) == 631, "actual32 bundle file count differs")
    hashed = 0
    for rel, meta in files.items():
        path = ROOT / rel
        require(path.is_file() and sha(path) == meta["sha256"] and path.stat().st_size == meta["bytes"], "bundle file mismatch: " + rel)
        hashed += 1
    print("actual32_bundle_sha256", BUNDLE_SHA)
    print("actual32_bundle_files_verified", hashed)
    print("scientific_calls", bundle["scientific_calls"])
    print("native_writes", bundle["native_writes"])

    freeze_sha = sha(FREEZE)
    require(freeze_sha == FREEZE_FILE_SHA, "freeze file hash changed")
    freeze = load_json(FREEZE)
    require(freeze.get("freeze_sha256") == FREEZE_CANONICAL_SHA, "canonical freeze hash changed")
    require(freeze.get("retained_executable_arms") == ["A", "B"], "retained arms are not the pre-outcome A/B design")
    require(sorted(freeze.get("removed_arms", {})) == ["C", "C-no-reuse", "C-no-route", "D"], "withdrawn arms changed")
    require(len(freeze.get("planned_cells", [])) == 32, "planned final cells are not 32")
    print("freeze_file_sha256", FREEZE_FILE_SHA)
    print("freeze_sha256", FREEZE_CANONICAL_SHA)
    print("planned_final_cells", len(freeze["planned_cells"]))
    print("removed_arms", sorted(freeze["removed_arms"]))
    print("historical_first_final_attempt_started_marker", freeze.get("first_final_attempt_started"))

    snap = ROOT / "papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-017/operator_adoption_v1"
    manifest = load_json(snap / "manifest.json")
    attempts = load_jsonl(snap / "attempts.jsonl")
    providers = load_jsonl(snap / "provider_receipts.jsonl")
    resources = load_jsonl(snap / "resource_measurements.jsonl")
    deviations = (snap / "deviations.md").read_text(encoding="utf-8")
    require(manifest.get("schema") == "ns017-actual-final32-main-adoption/v1", "adoption manifest schema differs")
    require(manifest.get("planned_cells") == 32 and manifest.get("terminal_cells") == 32, "manifest denominator is not 32")
    require(manifest.get("ordered_cells") == freeze["planned_cells"], "adopted cell order differs from freeze")
    require(manifest.get("freeze_file_sha256") == FREEZE_FILE_SHA, "manifest freeze file hash differs")
    require(manifest.get("freeze_canonical_sha256") == FREEZE_CANONICAL_SHA, "manifest canonical freeze hash differs")
    require(manifest.get("publication_required_by_retained_arms") is False, "publication requirement was added")
    require(manifest.get("anonymous_release_admitted") is False, "anonymous release was admitted")
    require(manifest.get("native_task_completion_claimed") is False, "native task completion was claimed")
    require(manifest.get("independent_families") == 8, "independent family count differs")
    require(manifest.get("nested_repetitions_per_family_arm") == 2, "nested repetition count differs")
    require(manifest.get("actual_useful_completions") == 9, "useful completion count differs")
    require(manifest.get("arm_useful_fixed16") == {"A": {"planned": 16, "useful": 5}, "B": {"planned": 16, "useful": 4}}, "arm useful counts differ")
    continuation = manifest.get("runtime_continuation") or {}
    require(
        continuation.get("consumed_original_cells") == 7
        and continuation.get("prospective_continuation_cells") == 25
        and continuation.get("new_runtime_is_not_original_source") is True
        and continuation.get("same_original_batch_and_freeze") is True,
        "mixed runtime provenance fields differ",
    )

    require(len(attempts) == len(providers) == len(resources) == 32, "row counts are not 32")
    require([row["cell_id"] for row in attempts] == manifest["ordered_cells"], "attempt order differs")
    require([row["cell_id"] for row in providers] == manifest["ordered_cells"], "provider order differs")
    require([row["cell_id"] for row in resources] == manifest["ordered_cells"], "resource order differs")
    require(all(row.get("terminal") is True for row in attempts), "nonterminal attempt present")
    require(all(row.get("record_kind") == "final" for row in attempts), "non-final attempt present")
    require(all(row.get("cache") == "local_cold" for row in attempts), "non-cold cache present")
    require(all(row.get("human_annotation") is False for row in attempts), "human annotation claimed")
    require(sorted({row["unit"] for row in attempts}) == list(FAMILIES), "final families differ")
    require(sorted({row["repetition"] for row in attempts}) == list(REPS), "repetition identifiers differ")
    require(all(sum(row["unit"] == unit and row["arm"] == arm for row in attempts) == 2 for unit in FAMILIES for arm in ("A", "B")), "family-arm-repeat coverage differs")
    useful = Counter((row["arm"], row["useful_completion"]) for row in attempts)
    require(useful[("A", True)] == 5 and useful[("B", True)] == 4, "useful A/B counts differ")
    outcomes = Counter(row["outcome"] for row in attempts)
    require(
        outcomes == {"full_cold_pass": 9, "hidden_acceptance_failed": 7, "proposal_child_deadline": 14, "known_proposal_failure": 2},
        "terminal outcome census differs",
    )
    epochs = Counter(row["runtime_source_provenance"]["epoch"] for row in attempts)
    require(epochs["original_resource_lease"] == 7 and epochs["prospective_resource_lease_continuation"] == 25, "runtime epoch counts differ")
    require(sum(row["actual_cold_completed"] is True for row in attempts) == 15, "completed cold validations differ")
    require(sum(row["raw_scorer_success"] is True for row in attempts) == 9, "independent cold-pass count differs")

    incomplete = next(row for row in attempts if row["cell_id"] == INCOMPLETE_HIDDEN_CELL)
    require(
        incomplete["outcome"] == "hidden_acceptance_failed"
        and incomplete["useful_completion"] is False
        and incomplete["hidden_collected"] == 0
        and incomplete["hidden_passed"] == 0
        and incomplete["visible_passed"] == 28
        and incomplete["visible_collected"] == 28,
        "incomplete hidden-validation cell was rewritten",
    )
    incomplete_disclosures = [d for d in incomplete.get("validation_disclosures") or [] if d.get("category") == "incomplete_hidden_validation_import_failure"]
    require(len(incomplete_disclosures) == 1, "incomplete hidden-validation disclosure missing")
    require(
        incomplete_disclosures[0].get("hidden_assertion_failure_observed") is False
        and incomplete_disclosures[0].get("infrastructure_fault_proven") is False
        and incomplete_disclosures[0].get("signed_outcome") == "hidden_acceptance_failed",
        "incomplete hidden-validation disclosure was weakened",
    )
    executed_hidden_failures = [
        row
        for row in attempts
        if row["outcome"] == "hidden_acceptance_failed" and row["cell_id"] != INCOMPLETE_HIDDEN_CELL
    ]
    require(len(executed_hidden_failures) == 6 and all(row["hidden_collected"] for row in executed_hidden_failures), "executed hidden-check failures differ")

    require(all(row["actual_provider_posts"] == 1 for row in providers), "provider POST census differs")
    require(all(row["unknown_external_charge"] is True for row in providers), "unsettled provider charges were zeroed")
    require(all((row.get("settled_provider_cost") or {}).get("status") == "unavailable" for row in providers), "settled cost status is not unavailable")
    require(all(row["operator_review_effort_cost"] is None for row in resources), "operator review effort was zeroed")
    require(all(row["resource_compliance"]["missing_is_zero"] is False for row in resources), "missing resource clocks were treated as zero")
    require(sum(row["gateway_score_elapsed_seconds"] is None for row in resources) == 16, "missing scorer clocks were filled")
    require(sum(row["resource_compliance"]["compliant"] is False for row in resources) == 14, "child-deadline overrun census differs")
    require("mixed actual runtime provenance" in deviations, "mixed-runtime deviation text missing")
    require(
        "missing hidden collection or import failure is not an observed hidden assertion failure" in deviations,
        "incomplete hidden-validation deviation text missing",
    )
    require("All 32 original A/B cold cells retain terminal outcomes and the fixed denominator" in deviations, "fixed-denominator deviation text missing")

    analysis = load_json(OBJECTS / ANALYSIS_SHA)
    require(sha(OBJECTS / ANALYSIS_SHA) == ANALYSIS_SHA, "strict complete32 analysis hash differs")
    require(
        analysis.get("schema") == "ns-final32-retained-evidence-analysis/v1"
        and analysis.get("complete") is True
        and analysis.get("planned_cells") == 32
        and analysis.get("terminal_cells") == 32
        and analysis.get("missing_or_nonterminal") == 0
        and analysis.get("useful_completions") == 9
        and analysis.get("actual_cold_completed") == 15
        and analysis.get("new_provider_calls") == 0
        and analysis.get("new_scorer_calls") == 0
        and analysis.get("unrecruited_original_families") == 8
        and analysis.get("unknown_external_charge_cells") == 32
        and analysis.get("freeze_sha256") == FREEZE_FILE_SHA,
        "strict complete32 analysis fields differ",
    )

    useful_rows = [row for row in attempts if row["useful_completion"] is True]
    require(len(useful_rows) == 9, "useful row census differs")
    for row in attempts:
        receipt_path = OBJECTS / row["original_signed_receipt_sha256"]
        require(receipt_path.is_file() and sha(receipt_path) == row["original_signed_receipt_sha256"], "original signed receipt missing: " + row["cell_id"])
        wrapped = load_json(receipt_path)
        inner = wrapped["receipt"]
        require(inner["cell_id"] == row["cell_id"], "signed receipt cell mismatch")
        require(inner["final_freeze_sha256"] == FREEZE_FILE_SHA, "signed receipt freeze mismatch")
        require(inner["unknown_external_charge"] is True, "signed receipt settled a provider charge")
        require(inner["record_kind"] == "final" and inner["cache"] == "local_cold", "signed receipt design mismatch")
        if row["useful_completion"] is True:
            require(inner["status"] == "completed", "useful cell is not a completed signed receipt")
            require(inner.get("human_annotation") is False, "useful cell claims human annotation")
            require(inner.get("operator_review_kind") == "ai_operator", "useful cell lacks bound AI/operator review")
            require((OBJECTS / inner["operator_review_sha256"]).is_file(), "operator review object missing")
            host = inner.get("scorer") or {}
            scalar = host.get("scorer") or {}
            require(host.get("success") is True and scalar.get("success") is True and scalar.get("classification") == "passed", "useful cell lacks independent cold pass")
            require(host.get("provider_invoked") is False, "retained scorer invoked a provider")
            require(inner.get("new_provider_calls_during_score") == 0, "score phase issued a provider call")
        if row["cell_id"] == INCOMPLETE_HIDDEN_CELL:
            scalar = ((inner.get("scorer") or {}).get("scorer") or {})
            require(
                scalar.get("classification") == "hidden_acceptance_failed"
                and scalar.get("hidden_collected") == 0
                and scalar.get("hidden_exit") == 4
                and scalar.get("visible_passed") == 28,
                "incomplete hidden-validation signed scorer fields differ",
            )

    print("terminal_cells", 32)
    print("useful_witnesses", json.dumps({"A": 5, "B": 4}, separators=(",", ":")))
    print("outcomes", json.dumps(dict(outcomes), sort_keys=True, separators=(",", ":")))
    print("incomplete_hidden_validation_cell", INCOMPLETE_HIDDEN_CELL)
    print("executed_hidden_check_failures", 6)
    print("proposal_child_deadlines", 14)
    print("known_proposal_failures", 2)
    print("runtime_epochs", json.dumps({"original_resource_lease": 7, "prospective_resource_lease_continuation": 25}, separators=(",", ":")))
    print("publication_required_by_retained_arms", False)
    print("unknown_external_charge_cells", 32)
    print("missing_scorer_clocks", 16)
    print("original_signed_receipts", 32)
    print("analysis_sha256", ANALYSIS_SHA)
    print("new_effects", "none")
    print("status", "retained_evidence_verified")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
