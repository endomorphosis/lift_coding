#!/usr/bin/python3.12
"""Ordinary NS-018 withdrawn-ablation scope check. No grants, providers, scorers, or reruns."""
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

ABLATIONS = ROOT / "papers/completion/neurosymbolic_supervision/runs/ablations"
SNAP = ROOT / "papers/completion/neurosymbolic_supervision/receipts/snapshots/NS-018/scope_record_v1"
ORIGINAL192 = ROOT / (
    "papers/completion/neurosymbolic_supervision/pilot/recovery/final_input_source/"
    "original192.private.json"
)
FREEZE = ROOT / "papers/completion/neurosymbolic_supervision/artifacts/final_experiment_freeze.json"
POLICY = ROOT / (
    "papers/completion/neurosymbolic_supervision/pilot/recovery/final_input_source/"
    "analysis_policy.json"
)
SCOPE = ROOT / "papers/completion/neurosymbolic_supervision/protocol/final32_adoption_scope.json"
MAIN = ROOT / "papers/completion/neurosymbolic_supervision/runs/main"
NS017 = ROOT / "papers/completion/neurosymbolic_supervision/receipts/NS-017.json"

FREEZE_FILE_SHA = "7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a"
FREEZE_CANONICAL_SHA = "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d"
ORIGINAL192_SHA = "6ed6e590479d7d71bdcc9cc67fc7cccf51b05230c0f6761fcd7c520bece2ac80"
POLICY_SHA = "a0edbc1cdf13f1d5aab4170dd60fcb3a3b2ef26d192f6dbbdce9b6a26ff700d3"
EMPTY_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
MAIN_HASHES = {
    "manifest.json": "0891bee6e3a556f5448250bbf11815ac255958a2f02add848d4e0934f23aeeac",
    "attempts.jsonl": "7d3471f965cc9bd6c024e1fd9c528b9797c40601e5083eb8f1f506d78094716f",
    "deviations.md": "af86395218d147f7a9707bce476cf7aa002fe3af87df8a0a1b3f658608ff0c24",
    "provider_receipts.jsonl": "8448634cb9dd6569a46dc9a90dbd48f99f047a798014df7f461c19d93b7bd55a",
    "resource_measurements.jsonl": "97e9a1bb9503886c3a609322cab8dbe1e927854df10bee5805be16240eec17ee",
}
ARMS_AB = ("A", "B")
REPS = (104729, 130363)
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
CRITERIA = (
    "Each retained efficiency mechanism has a matched isolated comparison or an explicit non-attributable limitation.",
    "Controls differ only in declared factors; enabled checks and acceptance standards are recorded.",
    "Deny-all contributes only diagnostic safety/cost evidence and cannot satisfy useful-progress promotion.",
    "Ablation failures, extra fallback, proof/index/setup/training costs, and slower workloads remain in outputs.",
)
REQUIRED_DEVIATION_PHRASES = (
    "32-cell A/B comparison with local-cold caches",
    "160 removed cells comprise 128 non-A/B cells plus 32 A/B local-warm cells",
    "Root-admitted main evidence now exists under NS-017",
    "does not copy those 32 terminal rows",
    "does not isolate arbitrary internal subcomponents",
    "No isolated experiment performed or authorized",
    "cannot establish useful completion or satisfy useful-progress promotion",
    "real zero-byte files, representing zero measured ablation rows",
    "not evidence that experimental or setup costs are zero",
    "unmeasured for isolated ablations and remains null, not zero",
    "does not launch translation, routing, reuse, warm-cache, sealer, parallel, or procedure experiments",
    "human semantic fidelity remains unmeasured",
)


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canon(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def cell_id(unit: str, arm: str, cache: str, repetition: int) -> str:
    return hashlib.sha256(
        canon(
            {
                "unit": unit,
                "arm": arm,
                "cache": cache,
                "repetition": repetition,
                "record_kind": "final",
            }
        )
    ).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_bytes())


def load_jsonl(path: Path):
    text = path.read_text(encoding="utf-8")
    if text == "":
        return []
    rows = []
    for line in text.splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def require(ok: bool, message: str) -> None:
    if not ok:
        raise SystemExit(message)


def main() -> int:
    require(sha(ORIGINAL192) == ORIGINAL192_SHA, "original192 hash changed")
    require(sha(FREEZE) == FREEZE_FILE_SHA, "freeze file hash changed")
    freeze = load_json(FREEZE)
    require(freeze.get("freeze_sha256") == FREEZE_CANONICAL_SHA, "canonical freeze hash changed")
    require(sha(POLICY) == POLICY_SHA, "analysis policy hash changed")
    original = load_json(ORIGINAL192)
    units = original["units"]
    require(len(units) == 192, "original192 lineage is not 192 units")
    require(freeze.get("retained_executable_arms") == ["A", "B"], "retained arms changed")
    require(sorted(freeze.get("removed_arms", {})) == ["C", "C-no-reuse", "C-no-route", "D"], "removed arms changed")
    require(len(freeze.get("planned_cells", [])) == 32, "freeze planned cells are not 32")
    scope = load_json(SCOPE)
    require(scope.get("final_cell_count") == 32 and scope.get("removed_factor_cells") == 160, "adoption scope counts differ")
    require(scope.get("nested_repetitions") == [104729, 130363], "adoption scope repetitions differ")

    ns017 = load_json(NS017)
    require(ns017.get("task_id") == "NS-017" and ns017.get("status") == "complete", "NS-017 main evidence is not complete")
    for name, expected in MAIN_HASHES.items():
        require(sha(MAIN / name) == expected, "NS-017 current output hash changed: " + name)
    main_attempts = load_jsonl(MAIN / "attempts.jsonl")
    require(len(main_attempts) == 32, "NS-017 main attempts are not 32")

    names = ("manifest.json", "attempts.jsonl", "resource_measurements.jsonl", "deviations.md")
    for name in names:
        current = ABLATIONS / name
        snapshot = SNAP / name
        require(current.is_file() and snapshot.is_file(), "missing ablation file: " + name)
        require(sha(current) == sha(snapshot), "current/snapshot mismatch: " + name)

    attempts = load_jsonl(ABLATIONS / "attempts.jsonl")
    resources = load_jsonl(ABLATIONS / "resource_measurements.jsonl")
    require(len(attempts) == 0 and (ABLATIONS / "attempts.jsonl").stat().st_size == 0, "ablation attempts are not empty")
    require(len(resources) == 0 and (ABLATIONS / "resource_measurements.jsonl").stat().st_size == 0, "ablation resources are not empty")
    require(sha(ABLATIONS / "attempts.jsonl") == EMPTY_SHA, "attempts.jsonl hash is not empty")
    require(sha(ABLATIONS / "resource_measurements.jsonl") == EMPTY_SHA, "resource_measurements.jsonl hash is not empty")
    require(attempts != main_attempts, "ablation attempts copied main outcomes")

    manifest = load_json(ABLATIONS / "manifest.json")
    require(manifest.get("schema") == "ns018-withdrawn-ablations-manifest/v1", "manifest schema differs")
    require(manifest.get("task_id") == "NS-018", "manifest task_id differs")
    require(manifest.get("freeze_file_sha256") == FREEZE_FILE_SHA, "manifest freeze file hash differs")
    require(manifest.get("freeze_sha256") == FREEZE_CANONICAL_SHA, "manifest canonical freeze hash differs")
    require(manifest.get("measured_ablation_attempt_rows") == 0, "measured ablation attempt rows are not 0")
    require(manifest.get("measured_ablation_resource_rows") == 0, "measured ablation resource rows are not 0")
    require(manifest.get("main_outcome_rows_included") == 0, "main outcome rows were included")
    require(manifest.get("uses_final_outcomes_or_partial_results") is False, "ablation record claims to use final outcomes")
    require(manifest.get("new_scientific_execution_authorized") is False, "new scientific execution was authorized")
    require(manifest.get("native_completion_authorized") is False, "native completion was authorized")
    require(manifest.get("off_live_preparation") is True, "off-live preparation flag missing")
    require(manifest.get("overall_experimental_cost_total") is None, "pooled experimental cost was invented")
    require(manifest.get("native_task_acceptance_criteria_exact") == list(CRITERIA), "acceptance criteria changed")

    population = manifest["population"]
    require(population["original_planned_factor_cells"] == 192, "original 192 count differs")
    require(population["withdrawn_planned_factor_cells"] == 160, "withdrawn 160 count differs")
    require(population["retained_main_cells"] == 32, "retained 32 count differs")
    require(population["retained_independent_families"] == 8, "family count differs")
    require(population["unrecruited_families"] == 8, "unrecruited family count differs")
    require(population["unrecruited_family_identities"] is None, "unrecruited family identities were invented")
    require(population["nested_repetition_identifiers"] == [104729, 130363], "repetition identifiers differ")
    require(population["identifiers_are_claimed_served_api_random_seeds"] is False, "repetitions claimed as API seeds")
    require(population["original_family_target"] == 16, "original 16-family target missing")
    require(population["withdrawn_disjoint_partition"] == {"AB_local_warm": 32, "non_AB_arm": 128}, "160-cell partition differs")

    retained = manifest["retained_main_planned_cells"]
    withdrawn = manifest["withdrawn_planned_cells"]
    require(len(retained) == 32 and len(withdrawn) == 160, "retained/withdrawn lengths differ")
    require([row["final_cell_id"] for row in retained] == freeze["planned_cells"], "retained cell order differs from freeze")
    require(all(row["cache"] == "local_cold" and row["arm"] in ARMS_AB for row in retained), "retained cells are not A/B local-cold")
    require(all(row["observed_outcome_included"] is False for row in retained), "retained cells include copied outcomes")
    require(all(row["disposition"] == "retained_main_comparison_not_ablation" for row in retained), "retained disposition differs")
    require(all(row["repetition"] in REPS for row in retained), "retained repetition identifiers differ")
    require(sorted({row["task_id"] for row in retained}) == list(FAMILIES), "retained families differ")
    require(
        all(sum(row["task_id"] == unit and row["arm"] == arm for row in retained) == 2 for unit in FAMILIES for arm in ARMS_AB),
        "family-arm-repeat coverage differs",
    )

    selected = []
    leftover = []
    for index, unit in enumerate(units):
        keep = unit["arm"] in ARMS_AB and unit["cache"] == "local_cold"
        (selected if keep else leftover).append((index, unit))
    require(len(selected) == 32 and len(leftover) == 160, "original192 filter lengths differ")
    for row, (index, unit) in zip(retained, selected):
        cid = cell_id(unit["task_id"], unit["arm"], unit["cache"], unit["repetition"])
        require(row["final_cell_id"] == cid, "retained cell identity recompute differs")
        require(row["original_schedule_index"] == index, "retained original order differs")
        require(row["order_key"] == unit["order_key"], "retained order_key differs")
        require(row["task_id"] == unit["task_id"] and row["arm"] == unit["arm"] and row["repetition"] == unit["repetition"], "retained unit identity differs")
    for row, (index, unit) in zip(withdrawn, leftover):
        cid = cell_id(unit["task_id"], unit["arm"], unit["cache"], unit["repetition"])
        require(row["identity_cell_id"] == cid, "withdrawn identity recompute differs")
        require(row["original_schedule_index"] == index, "withdrawn original order differs")
        require(row["measured_ablation_attempt"] is False, "withdrawn cell claimed a measured attempt")
        require(row["disposition"] == "withdrawn_from_final_ablation_scope", "withdrawn disposition differs")
        expected_partition = "AB_local_warm" if unit["arm"] in ARMS_AB else "non_AB_arm"
        require(row["removal_partition"] == expected_partition, "withdrawn partition differs")
    require(sum(row["removal_partition"] == "AB_local_warm" for row in withdrawn) == 32, "warm withdrawn count differs")
    require(sum(row["removal_partition"] == "non_AB_arm" for row in withdrawn) == 128, "non-A/B withdrawn count differs")

    factor = manifest["retained_factor_comparison"]
    require(factor["name"] == "source_linked_native_semantic_context", "retained factor name differs")
    require(factor["matched_public_raw_selection"] is True, "matched public raw selection missing")
    require(factor["isolates_arbitrary_subcomponents"] is False, "subcomponent isolation claimed")
    require(factor["matched_isolated_component_comparison"] is False, "isolated component comparison claimed")
    require(factor["attribution"] == "explicit_non_attributable_limitation", "non-attributable limitation missing")

    deny = manifest["deny_all"]
    require(deny["can_satisfy_useful_progress_promotion"] is False, "deny-all was allowed to promote")
    require(deny["useful_completion_claimed"] is False, "deny-all useful completion claimed")
    require(deny["measured_ablation_attempt"] is False, "deny-all ablation observation claimed")
    require(deny["role"] == "diagnostic_safety_cost_evidence_only", "deny-all role differs")

    auth = manifest["execution_authorization"]
    require(
        all(auth.get(key) is False for key in (
            "translation_experiment",
            "routing_experiment",
            "reuse_experiment",
            "warm_cache_experiment",
            "sealer_experiment",
            "parallel_experiment",
            "procedure_experiment",
            "new_model_or_scorer_calls",
            "native_completion_authorized",
        )),
        "a withdrawn experiment was authorized",
    )

    costs = manifest["unmeasured_isolated_cost_attribution"]
    require(
        all(costs.get(key) is None for key in ("proof", "index", "setup", "training", "fallback", "cleanup", "review", "workload_specific")),
        "unmeasured isolated cost was zeroed or invented",
    )

    components = manifest["unperformed_component_ablations"]
    require(len(components) >= 12, "component-ablation missingness record is incomplete")
    require(all(item.get("measured_ablation_attempt") is False for item in components), "fabricated component-ablation attempt present")
    require(all(item.get("non_attributable_limitation") is True for item in components), "component limitation missing")
    names = {item["mechanism"] for item in components}
    require(
        {
            "source_linked_native_semantic_context",
            "C_D_routing_and_governance",
            "local_warm_cache",
            "test_proof_reuse",
            "publication_comparison_efficacy",
            "translation_checks",
            "sealer_sequential_or_parallel",
            "parallel_preparation",
            "procedure_components",
            "deny_all",
        }
        <= names,
        "required withdrawn mechanisms missing",
    )

    main_bind = manifest["root_admitted_main_evidence"]
    require(main_bind.get("bound_after_existence") is True, "main evidence was not bound after it existed")
    require(main_bind.get("copied_into_ablation_rows") is False, "main evidence was copied into ablation rows")
    require(main_bind.get("ns017_status") == "complete", "bound NS-017 status differs")
    for rel, meta in main_bind["files"].items():
        require(sha(ROOT / rel) == meta["sha256"], "bound main file hash differs: " + rel)

    files_meta = manifest["files"]
    require(files_meta["attempts.jsonl"]["sha256"] == EMPTY_SHA and files_meta["attempts.jsonl"]["bytes"] == 0, "manifest attempts hash differs")
    require(files_meta["resource_measurements.jsonl"]["sha256"] == EMPTY_SHA and files_meta["resource_measurements.jsonl"]["bytes"] == 0, "manifest resources hash differs")
    require(files_meta["deviations.md"]["sha256"] == sha(ABLATIONS / "deviations.md"), "manifest deviations hash differs")
    require(files_meta["deviations.md"]["bytes"] == (ABLATIONS / "deviations.md").stat().st_size, "manifest deviations size differs")

    deviations = (ABLATIONS / "deviations.md").read_text(encoding="utf-8")
    for phrase in REQUIRED_DEVIATION_PHRASES:
        require(phrase in deviations, "deviations missing phrase: " + phrase)

    evidence = manifest["criterion_evidence"]
    require([item["criterion"] for item in evidence] == [1, 2, 3, 4], "criterion evidence order differs")
    require(evidence[0]["status"] == "explicit_non_attributable_limitation", "criterion 1 status differs")
    require(evidence[2]["status"] == "diagnostic_only_no_deny_all_observation_claimed", "criterion 3 status differs")
    require("null" in evidence[3]["evidence"] or "null" in json.dumps(costs), "criterion 4 does not keep costs null")

    print("original192_sha256", ORIGINAL192_SHA)
    print("freeze_file_sha256", FREEZE_FILE_SHA)
    print("freeze_sha256", FREEZE_CANONICAL_SHA)
    print("original_planned_factor_cells", 192)
    print("retained_main_cells", 32)
    print("withdrawn_planned_cells", 160)
    print("unrecruited_families", 8)
    print("measured_ablation_attempt_rows", 0)
    print("measured_ablation_resource_rows", 0)
    print("main_outcome_rows_included", 0)
    print("ns017_main_bound", True)
    print("ns017_main_copied", False)
    print("deny_all_can_promote", False)
    print("new_experiments_authorized", False)
    print("isolated_costs_null", True)
    print("status", "withdrawn_ablation_scope_verified")
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
