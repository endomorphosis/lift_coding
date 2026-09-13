#!/usr/bin/python3.12
"""Ordinary NS-020 boundary-reconciliation check. No grants, providers, scorers, or reruns."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while not (ROOT / "scripts" / "paper_supervisors.py").is_file():
    if ROOT.parent == ROOT:
        raise SystemExit("repository root not found")
    ROOT = ROOT.parent

P = ROOT / "papers/completion/neurosymbolic_supervision"
SNAP = P / "receipts/snapshots/NS-020"
RECONCILED = SNAP / "reconciled_final32"
PREP = P / "writing_inputs/ns020_boundary_preparation_v2"
MAIN = P / "runs/main"
ABLATIONS = P / "runs/ablations"

ANALYZER_SHA = "16da76bbe3fe032cde70599790ad8ad1e52d9eb1baf4ea799cf4856d23410251"
RESULTS_SHA = "6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e"
MAIN_MANIFEST_SHA = "0891bee6e3a556f5448250bbf11815ac255958a2f02add848d4e0934f23aeeac"
ABLATION_MANIFEST_SHA = "15c8fb2d05ffcd02ecb105f6498288f43ef2717ea3db5605d95d277c0195e5d0"
POLICY_SHA = "a0edbc1cdf13f1d5aab4170dd60fcb3a3b2ef26d192f6dbbdce9b6a26ff700d3"
FREEZE_FILE_SHA = "7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a"
FREEZE_CANONICAL_SHA = "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d"
WITNESS_SHA = "dfe49703613e3a2d19eff8cbf85c608ea25f1b1360477be5ef510e752141f6c0"
TABLE18_SHA = "3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495"
MATRIX_SHA = "2c2528f5fbed0d784c9cb09509f1979e12ad06107610804757ae8b96b8aa15b7"
FAILURE_SHA = "eb580e020477267a7cd2ca23e67a66280f14237cf7d68e64f7c69afd4aedbe48"
REBIND_SHA = "780d9417ff88d4178b185a6d8a9281b0d0d44cb00ac3e8d58af5bbfdbd0b7bae"
PATCH_SHA = "ccc6dd28a82455228780355b63a0812e911833730ad8df94e7bbcadd3ec3254d"
CURRENT_HELPER_SHA = "e58609d5123df6d959ba2d9a70c01dd2b4c3e715d46d5137de8b10919cbc4b14"
OLD_RENDERER_SHA = "1aa277d0539216b7071ec81ba8f6b6b44acbb0dece9c00894d4b4b8c8d031363"
PREP_WITNESS_SHA = "d4c402839086e2eb6b089a58ccfe775947caa7cfcb3f9647e19c621dfa83ad90"
PREP_FAILURE_SHA = "ad3f954f1a337d377f0ae71d7748450980c319f3dba2d2909a88ffe5ea539016"
PREP_MATRIX_SHA = "b8f850530295251187d4760c71ed551dc3c95d40f113050056201c27212d2d5e"
PREP_SOURCE_SHA = "2d2edeede2454e431cfd5fec227c9189f09ae14eee8e142f49821e6e53bd2b25"
PREP_README_SHA = "ded611c18a7a04caf8a6edc5548b758b0dc279c2ce4f8986cd0d14b05a0d6053"

BOUNDARY_IDS = ("F-HTTP", "F-custody", "F-score", "F-lease", "F-failure")
TABLE18_IDS = ("B-provider", "B-translation", "B-native", "B-reuse", "B-restart", "B-world")
CLAIM_IDS = (
    "C-ABS-01", "C-ABS-02", "C-ABS-03", "C-01", "C-02", "C-T1-SEMANTIC", "C-T1-OPERATIONAL",
    "C-T1-DURABLE", "C-03", "C-04", "C-05", "C-T2", "C-06", "C-07", "C-08", "C-09", "C-10",
    "C-11", "C-12", "C-13", "C-14", "C-T3", "C-15", "C-16", "C-17", "C-18", "C-19", "C-T4",
    "C-T5-CONTEXT", "C-T5-SEALER", "C-T5-SOURCE", "C-20",
)
OUTCOMES = {
    "full_cold_pass": 9,
    "hidden_acceptance_failed": 7,
    "known_proposal_failure": 2,
    "proposal_child_deadline": 14,
}
EMPIRICAL_CLAIMS = {"C-ABS-01", "C-19"}
CRITERIA = (
    "Every Table 18 cell has an evidence-backed outcome/ID or explicit untested/unavailable scope; no TBD or synthetic proof of progress remains.",
    "All retained claims point to code/runtime/population and reproducible measured artifacts.",
    "False-admission, false-reuse, inability to dispatch, and recovery failures remain visible and trigger narrowed conclusions where required.",
    "Author-only plans and old campaign success labels cannot override current evidence.",
)

CURRENT = {
    P / "analysis/boundary_witnesses.json": WITNESS_SHA,
    P / "manuscript/generated/table18.tex": TABLE18_SHA,
    P / "audit/final_claim_evidence_matrix.json": MATRIX_SHA,
    P / "analysis/failure_cases.md": FAILURE_SHA,
}
SNAPSHOTS = {
    RECONCILED / "analysis/boundary_witnesses.json": WITNESS_SHA,
    RECONCILED / "manuscript/generated/table18.tex": TABLE18_SHA,
    RECONCILED / "audit/final_claim_evidence_matrix.json": MATRIX_SHA,
    RECONCILED / "analysis/failure_cases.md": FAILURE_SHA,
    SNAP / "reconcile_boundaries.py": REBIND_SHA,
    SNAP / "source.patch": PATCH_SHA,
}
PREPARATION = {
    PREP / "README.md": PREP_README_SHA,
    PREP / "boundary_witnesses.json": PREP_WITNESS_SHA,
    PREP / "failure_cases.md": PREP_FAILURE_SHA,
    PREP / "final_claim_evidence_matrix.json": PREP_MATRIX_SHA,
    PREP / "source_evidence.json": PREP_SOURCE_SHA,
    PREP / "table18.tex": TABLE18_SHA,
}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(message)


def load_json(path: Path):
    return json.loads(path.read_bytes())


def cell_has_scope(payload) -> bool:
    if isinstance(payload, list) and payload and all(isinstance(x, str) and x.startswith("NS-") for x in payload):
        return True
    if not isinstance(payload, dict):
        return False
    status = str(payload.get("status") or "")
    if "untested" in status or "unavailable" in status or "out_of_scope" in status:
        return True
    cases = payload.get("cases")
    if isinstance(cases, list) and cases:
        return all(isinstance(case, dict) and case.get("case_id") for case in cases)
    current = payload.get("current_cases")
    if isinstance(current, list) and current and all(isinstance(x, str) and x for x in current):
        return True
    if payload.get("case_id"):
        return True
    return False


def main() -> int:
    require(sys.version_info[:2] == (3, 12), "Python 3.12 required")
    for path, expected in {**CURRENT, **SNAPSHOTS, **PREPARATION}.items():
        require(path.is_file() and sha(path) == expected, "hash mismatch: " + str(path.relative_to(ROOT)))
    require(sha(P / "analysis/analyze.py") == ANALYZER_SHA, "NS019 analyzer hash changed")
    require(sha(P / "analysis/results.json") == RESULTS_SHA, "NS019 results hash changed")
    require(sha(MAIN / "manifest.json") == MAIN_MANIFEST_SHA, "NS017 manifest hash changed")
    require(sha(ABLATIONS / "manifest.json") == ABLATION_MANIFEST_SHA, "NS018 ablation manifest hash changed")
    require(sha(P / "analysis/reconcile_boundaries.py") == CURRENT_HELPER_SHA, "current helper changed")
    print("output_snapshot_pairs", len(CURRENT))

    current_helper = (P / "analysis/reconcile_boundaries.py").read_text(encoding="utf-8")
    rebound = (SNAP / "reconcile_boundaries.py").read_text(encoding="utf-8")
    old_pin = "RENDERER_SHA256 = '" + OLD_RENDERER_SHA + "'"
    new_pin = "RENDERER_SHA256 = '" + ANALYZER_SHA + "'"
    require(old_pin in current_helper and new_pin not in current_helper, "current helper pin is not the pre-rebind SHA")
    require(new_pin in rebound and old_pin not in rebound, "executed helper is not the NS019 renderer rebind")
    require(current_helper.replace(old_pin, new_pin, 1) == rebound, "rebind changed reconciliation logic besides RENDERER_SHA256")
    patch = (SNAP / "source.patch").read_text(encoding="utf-8")
    require(old_pin in patch and new_pin in patch, "source.patch does not record the renderer rebind")
    require(patch.count("RENDERER_SHA256") == 2, "source.patch is not limited to the renderer pin")
    analyzer = (P / "analysis/analyze.py").read_text(encoding="utf-8")
    require("item['label'] not in by_label or by_label[item['label']] == item" in analyzer,
            "qualified identical-label exception absent")
    require("Ambiguous retained label" in analyzer, "conflicting-label failure absent")
    print("renderer_sha256", ANALYZER_SHA)

    manifest = load_json(MAIN / "manifest.json")
    require(manifest["planned_cells"] == 32 and manifest["terminal_cells"] == 32, "fixed32 denominator changed")
    require(manifest["independent_families"] == 8, "family count changed")
    require(manifest["nested_repetitions_per_family_arm"] == 2, "nested repetition count changed")
    require(manifest["freeze_file_sha256"] == FREEZE_FILE_SHA, "freeze file identity changed")
    require(manifest["freeze_canonical_sha256"] == FREEZE_CANONICAL_SHA, "canonical freeze identity changed")
    require(len(manifest["ordered_cells"]) == 32 and len(set(manifest["ordered_cells"])) == 32, "cell order/identity changed")
    ablation = load_json(ABLATIONS / "manifest.json")
    require(ablation["population"]["original_planned_factor_cells"] == 192, "original192 lineage changed")
    require(ablation["population"]["retained_main_cells"] == 32, "retained main count changed")
    require(ablation["population"]["withdrawn_planned_factor_cells"] == 160, "withdrawn cell count changed")
    require(ablation["population"]["unrecruited_families"] == 8, "unrecruited family count changed")
    print("ns017_manifest_sha256", MAIN_MANIFEST_SHA)

    witness = load_json(P / "analysis/boundary_witnesses.json")
    prep_witness = load_json(PREP / "boundary_witnesses.json")
    require(witness["schema"] == "ns020-complete32-boundary-reconciliation/v1", "witness schema changed")
    require(witness["preparation_only"] is False and witness["final_claim_reconciliation_complete"] is True,
            "reconciliation not marked complete")
    require(witness["native_completion_claimed"] is False, "native completion claimed")
    require(witness["criteria_exact"] == list(CRITERIA), "criteria text changed")
    require([row["id"] for row in witness["table18_rows"]] == list(TABLE18_IDS), "Table 18 row identities changed")
    require(witness["table18_rows"] == prep_witness["table18_rows"], "historical Table 18 rows changed")
    require(len(witness["table18_rows"]) == 6, "Table 18 row count changed")
    for row in witness["table18_rows"]:
        for column in ("safe_rejection", "valid_progress", "evidence_ids"):
            require(cell_has_scope(row[column]), "Table 18 cell lacks evidence or explicit scope: " + row["id"] + "/" + column)
            blob = json.dumps(row[column])
            require("TBD" not in blob and "TO BE FILLED" not in blob, "TBD remains in Table 18 cell: " + row["id"])
    joins = witness["final_empirical_boundary_joins"]
    require([item["id"] for item in joins] == list(BOUNDARY_IDS), "final boundary identities changed")
    provenance = witness["actual_final32_reconciliation"]
    require(provenance["NS019_renderer_source_sha256"] == ANALYZER_SHA, "witness renderer pin differs")
    require(provenance["NS019_results"]["sha256"] == RESULTS_SHA, "witness results pin differs")
    require(provenance["NS017_manifest"]["sha256"] == MAIN_MANIFEST_SHA, "witness manifest pin differs")
    require(provenance["actual_terminal_cells"] == 32, "terminal cell count changed")
    require(provenance["historical_table_rows_changed"] is False, "historical table rows marked changed")
    require(provenance["original_claim_ids_and_text_changed"] is False, "claim identities marked changed")
    require(provenance["new_provider_calls"] == 0 and provenance["new_scorer_calls"] == 0 and provenance["new_native_calls"] == 0,
            "new scientific call claimed")
    require(provenance["human_annotation"] is False and provenance["publication_authorized"] is False,
            "human annotation or publication claimed")
    require(provenance["original_ordered_cells"] == manifest["ordered_cells"], "ordered cells differ from NS017")
    require(provenance["NS019_reverified_provenance"]["signatures_reverified"] == 48, "signature reverify count changed")
    require(provenance["NS019_reverified_provenance"]["analysis_policy_sha256"] == POLICY_SHA, "policy pin differs")
    for boundary in joins:
        rows = boundary["empirical_final_rows"]
        require(len(rows) == 32, "final join lacks 32 cells: " + boundary["id"])
        require([row["cell_id"] for row in rows] == manifest["ordered_cells"], "final join order differs: " + boundary["id"])
        require(all(row["terminal"] is True for row in rows), "nonterminal cell in " + boundary["id"])
        require(boundary["empirical_final_evidence_status"] == "actual_complete32_root_reviewed_and_NS019_recomputed",
                "join status is not actual complete32")
        require(boundary["scientific_success_inferred_from_controls"] is False, "controls promoted to scientific success")
        require(sum(row["useful_completion"] is True for row in rows) == 9, "useful count changed in " + boundary["id"])
        counted = {}
        for row in rows:
            counted[row["outcome"]] = counted.get(row["outcome"], 0) + 1
        require(counted == OUTCOMES, "outcome accounting changed in " + boundary["id"])
    print("final_joins", len(joins), "cells_each", 32)

    recipe = witness["envelope_recipe"]
    require(recipe["kind"] == "compact_sha256_pointer_recipe", "witness is not a compact SHA256 recipe")
    require(recipe["full_envelopes_reemitted"] is False, "full envelopes were re-emitted")
    require(recipe["private_original_paths_omitted"] is True, "private original paths were not omitted")
    require(recipe["generator_snapshot"] == "papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-020/reconcile_boundaries.py",
            "generator snapshot path changed")
    require(recipe["retained_population"]["NS017_manifest_sha256"] == MAIN_MANIFEST_SHA, "recipe manifest pin differs")
    require(recipe["retained_population"]["NS019_results_sha256"] == RESULTS_SHA, "recipe results pin differs")
    require(recipe["retained_population"]["NS019_renderer_sha256"] == ANALYZER_SHA, "recipe renderer pin differs")
    mapped = witness["empirical_final_cells"]
    require(len(mapped) == 32, "compact cell index lacks 32 cells")
    require([cell["cell_id"] for cell in mapped] == manifest["ordered_cells"], "compact cell order differs")
    require((P / "analysis/boundary_witnesses.json").stat().st_size < 1048576, "witness exceeds admission file budget")
    require(all(cell["terminal"] is True for cell in mapped), "nonterminal compact cell")
    require(sum(cell["useful_completion"] is True for cell in mapped) == 9, "compact useful count changed")
    compact_outcomes = {}
    for cell in mapped:
        compact_outcomes[cell["outcome"]] = compact_outcomes.get(cell["outcome"], 0) + 1
        rec = cell["references"]["original_signed_receipt"]
        require(rec.get("body_read_and_hash_verified") is True and rec.get("sha256"),
                "signed receipt mapping missing: " + cell["cell_id"])
        require(cell["references"]["signed_terminal"].get("sha256"), "signed terminal mapping missing: " + cell["cell_id"])
        require("actual_provider_posts" in cell["http"], "HTTP mapping missing: " + cell["cell_id"])
        require("actual_cold_completed" in cell["score"] or "raw_cold_classification" in cell["score"],
                "cold-score mapping missing: " + cell["cell_id"])
        candidate = cell["candidate"]
        require(candidate.get("candidate_code_or_patch_read") is not True, "candidate body was read")
        if candidate.get("candidate_present"):
            require(candidate.get("signed_candidate_inventory_sha256") and candidate.get("candidate_binding_metadata", {}).get("sha256"),
                    "candidate custody mapping missing: " + cell["cell_id"])
            review = candidate.get("candidate_review")
            if review:
                require(review.get("human_annotation") is False, "human annotation introduced")
                require(review.get("comprehensive_adversarial_scorer_qualification") is False,
                        "adversarial scorer guarantee invented")
                require(review.get("reference", {}).get("sha256"), "candidate review mapping missing: " + cell["cell_id"])
        clocks = cell["time_and_resources"]
        require(clocks.get("clock_grand_total") is None and clocks.get("overlapping_clocks_summed") is False,
                "clocks were totaled")
        require(clocks.get("signed_resource_compliance") is not None, "lease/time compliance mapping missing: " + cell["cell_id"])
        failure = cell["failure_accounting"]
        if failure is not None:
            require(failure.get("success_credit") is False and failure.get("retry_allowed") is False,
                    "failure credited or retried: " + cell["cell_id"])
            require(failure.get("signed_disposition", {}).get("sha256"), "failure disposition mapping missing: " + cell["cell_id"])
        require(cell["runtime"]["cooperative_lease_not_physical_exclusivity"] is True, "physical exclusivity claimed")
        require(cell["runtime"]["current_liveness_rechecked"] is False, "current lease liveness claimed")
        require(cell["human_annotation"] is False, "human annotation on compact cell")
        require(cell["runtime"]["source_files"], "runtime source mapping missing: " + cell["cell_id"])
    require(compact_outcomes == OUTCOMES, "compact outcome accounting changed")
    witness_blob = json.dumps(witness)
    require("original_paths_provenance_only" not in witness_blob, "private original paths were re-emitted")
    require("/home/barberb/lift_coding" not in witness_blob, "author-host paths were re-emitted")
    print("compact_cells", len(mapped), "witness_bytes", (P / "analysis/boundary_witnesses.json").stat().st_size)

    matrix = load_json(P / "audit/final_claim_evidence_matrix.json")
    prep_matrix = load_json(PREP / "final_claim_evidence_matrix.json")
    require(matrix["schema"] == "ns020-complete32-final-claim-evidence-matrix/v1", "matrix schema changed")
    require(matrix["preparation_only"] is False and matrix["all_final_claims_resolved"] is True, "claims not resolved")
    require(matrix["final_scientific_results_deferred"] is False, "final results still deferred")
    require(matrix["outside_reviewers_are_not_completion_gate"] is True, "outside review introduced as a gate")
    require([claim["original_claim_id"] for claim in matrix["claims"]] == list(CLAIM_IDS), "claim identities changed")
    require(len(matrix["claims"]) == 32, "claim count changed")
    for prepared, claim in zip(prep_matrix["claims"], matrix["claims"]):
        require(prepared["original_claim_id"] == claim["original_claim_id"], "claim id reordered")
        require(prepared["original_claim"] == claim["original_claim"], "original claim text changed")
        require(claim["final_disposition"], "claim lacks final disposition: " + claim["original_claim_id"])
        require("TBD" not in claim["final_disposition"] and "TBD" not in (claim.get("allowed_current_wording") or ""),
                "TBD remains in claim: " + claim["original_claim_id"])
        if claim["original_claim_id"] in EMPIRICAL_CLAIMS:
            outcome = claim["empirical_final_outcome"]
            require(isinstance(outcome, dict), "aggregate claim lacks copied NS019 outcome")
            require(outcome["fixed_cells"] == 32 and outcome["independent_families"] == 8, "copied population changed")
            require(outcome["nested_repetitions_per_family_arm"] == 2, "copied nested repetitions changed")
            require(outcome["useful_completions"] == 9, "copied useful count changed")
            require(outcome["outcomes"] == OUTCOMES, "copied outcomes changed")
            require(outcome["isolated_false_admission_estimate"] is None, "false-admission estimate invented")
            require(outcome["net_cost_grand_total"] is None, "net cost invented")
            require(outcome["human_semantic_fidelity"] is None, "human fidelity invented")
            require(claim["final_evidence"]["NS019_results"]["sha256"] == RESULTS_SHA, "claim results pin differs")
        else:
            require(claim["empirical_final_outcome"] is None, "broad claim acquired fabricated final outcome: " + claim["original_claim_id"])
    require([item["id"] for item in matrix["narrow_final_boundary_observations"]] == list(BOUNDARY_IDS),
            "narrow observations changed")
    require(all(item["actual_ordered_cell_count"] == 32 and item["scientific_success_inferred_from_controls"] is False
                for item in matrix["narrow_final_boundary_observations"]),
            "narrow observations overclaim success")
    print("claims", len(matrix["claims"]))

    table = (P / "manuscript/generated/table18.tex").read_text(encoding="utf-8")
    require(table == (PREP / "table18.tex").read_text(encoding="utf-8"), "historical Table 18 bytes changed")
    require("TBD" not in table and "TO BE FILLED" not in table, "TBD remains in Table 18")
    require("Untested: no admitted native proof profile." in table, "native untested scope missing")
    require("Unavailable: no genuine proof or measured prove/verify run." in table, "native unavailable scope missing")
    require("Untested/out of scope." in table and "no retained paired pre/post consumption." in table,
            "world/procedure untested scope missing")
    require("Prior false reuse 1/26 retained" in table, "false-reuse count missing from Table 18")
    require("no admitted positive reuse or speedup" in table, "reuse efficacy not withdrawn")
    require("no production routing claim" in table, "routing claim not withdrawn")
    failures = (P / "analysis/failure_cases.md").read_text(encoding="utf-8")
    require(failures.startswith("# Actual complete32 failure and boundary reconciliation\n"), "failure report header missing")
    require("| 1 | ns-hist-09-tomlkit | B | proposal_child_deadline | False | False |" in failures, "cell 1 failure missing")
    require("full_cold_pass" in failures and "hidden_acceptance_failed" in failures, "signed failure classes missing")
    require("known_proposal_failure" in failures and "proposal_child_deadline" in failures, "deadline/proposal failures missing")
    require("Historical false reuse remains one of all 26 attempts." in failures, "false-reuse 1/26 missing")
    require("48 attempted cases and 47 completed rows" in failures, "NS027 recovery accounting missing")
    require("incomplete_hidden_validation_import_failure" in failures, "incomplete hidden collection missing")
    require("thin helper did not forward required plan/doctor/obligation views" in failures, "dispatch limitation missing")
    require("No passing control becomes a repair result" in failures, "controls promoted to repair results")
    require(failures.endswith((PREP / "failure_cases.md").read_text(encoding="utf-8")),
            "historical preparation failure text was not preserved exactly")
    combined = table + failures + json.dumps(matrix["claims"]) + json.dumps(witness["table18_rows"])
    for phrase in ("noninferiority margin", "sixteen independent families", "32 independent repositories",
                   "publication-comparison efficacy", "human-time estimate"):
        require(phrase not in combined, "forbidden claim present: " + phrase)
    print("table18_sha256", TABLE18_SHA)
    print("boundary_witnesses_sha256", WITNESS_SHA)
    print("claim_matrix_sha256", MATRIX_SHA)
    print("failure_cases_sha256", FAILURE_SHA)
    print("scientific_calls", 0)
    print("status reconciled_fixed32_boundaries_verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
