#!/usr/bin/env python3
"""Validate LA-003 protocol arithmetic/definitions with synthetic checks only.

This program reads protocol documents and constructs synthetic family/decision
records. It does not load source corpora, labels, benchmark outcomes, models,
providers, solvers, network services, or supervisor state.
"""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random


def require(condition, message):
    if not condition:
        raise ValueError(message)


def assign_families(families, protocol, *, salt=None):
    rules = protocol["split_rules"]
    salt = salt or rules["salt"]
    populations = rules["population_order"]
    identifiers = [family["lineage_family_id"] for family in families]
    require(all(isinstance(value, str) and value for value in identifiers), "empty family ID")
    require(len(set(identifiers)) == len(identifiers), "duplicate/cross-population family ID")
    require(all(family["population"] in populations for family in families), "unknown population")
    assignment = {}
    for population in populations:
        members = [family for family in families if family["population"] == population]
        require(len(members) == protocol["population"]["families"][population], "cohort shortfall/excess")
        def rank(family):
            identifier = family["lineage_family_id"]
            encoded = json.dumps([salt, population, identifier], ensure_ascii=False,
                                 separators=(",", ":")).encode("utf-8")
            return hashlib.sha256(encoded).digest(), identifier.encode("utf-8")
        ranked = sorted(members, key=rank)
        cursor = 0
        for split in rules["split_order"]:
            count = protocol["population"]["split_families"][split][population]
            for family in ranked[cursor:cursor + count]:
                assignment[family["lineage_family_id"]] = split
            cursor += count
        require(cursor == len(ranked), "split quotas do not consume cohort")
    return assignment


def decision_metrics(records):
    observed = [record for record in records if record["decision"] is not None]
    require(all(record["decision"] in {"allow", "deny", "abstain"} for record in observed),
            "one final decision is required")
    allowed_observed = [record for record in observed if record["oracle"] == "allowed"]
    denial = sum(record["decision"] == "deny" for record in allowed_observed)
    abstention = sum(record["decision"] == "abstain" for record in allowed_observed)
    denominator = len(allowed_observed)
    ratio = lambda numerator, total: Fraction(numerator, total) if total else None
    return {
        "false_denial": ratio(denial, denominator),
        "allowed_abstention": ratio(abstention, denominator),
        "withholding": ratio(denial + abstention, denominator),
        "scheduled_abstention": ratio(sum(record["decision"] == "abstain" for record in records), len(records)),
        "conditional_abstention": ratio(sum(record["decision"] == "abstain" for record in observed), len(observed)),
    }


def must_reject(callback, message):
    try:
        callback()
    except (ValueError, TypeError):
        return
    raise ValueError(message)


def validate(directory):
    protocol = json.loads((directory / "protocol.json").read_text())
    resources = json.loads((directory / "resource_plan.json").read_text())
    prose = (directory / "protocol.md").read_text()
    require(protocol["schema"] == "law-to-action-benchmark-protocol/v2", "protocol schema")
    require(protocol["protocol_revision"] == resources["protocol_revision"] == "LA-003/v3",
            "resource-correction revision mismatch")
    require(protocol["status"] == "predeclared_protocol_no_empirical_runs", "unrun state")
    require(protocol["scope"]["protocol_completion_is_paper_completion"] is False, "paper completion overclaim")
    require(set(protocol["scope"]["other_paper_obligations_remain_open"]) ==
            {f"LA-{number:03}" for number in range(4, 26)}, "remaining paper scope omitted")
    require(protocol["population"]["families"] == {"legal": 6, "cve": 12, "skill": 12, "total": 30},
            "family totals")
    require(protocol["population"]["cases"] == {"legal": 12, "cve": 24, "skill": 24, "total": 60},
            "paired-case totals")
    quotas = protocol["population"]["split_families"]
    require(quotas == {
        "development": {"legal": 2, "cve": 2, "skill": 2, "total": 6},
        "calibration": {"legal": 1, "cve": 3, "skill": 2, "total": 6},
        "final": {"legal": 3, "cve": 7, "skill": 8, "total": 18}}, "exact stratified quotas")
    require(protocol["split_rules"]["canonical_json"] == {
        "ensure_ascii": False, "separators": [",", ":"], "encoding": "UTF-8",
        "unicode_normalization": "none; lineage IDs must be frozen exact opaque strings"}, "rank encoding")
    families = [{"population": population, "lineage_family_id": f"synthetic-{population}-{index}-é"}
                for population in ("legal", "cve", "skill")
                for index in range(protocol["population"]["families"][population])]
    assignment = assign_families(families, protocol)
    require(assignment == assign_families(list(reversed(families)), protocol), "input-order-sensitive splits")
    for population in ("legal", "cve", "skill"):
        for split in ("development", "calibration", "final"):
            count = sum(family["population"] == population and
                        assignment[family["lineage_family_id"]] == split for family in families)
            require(count == quotas[split][population], "ranked split quota mismatch")
    # Both synthetic derivatives resolve through their one parent assignment.
    variants = [{"variant": index, "parent": family["lineage_family_id"]}
                for family in families for index in (0, 1)]
    require(len(variants) == 60 and all(assignment[v["parent"]] in quotas for v in variants),
            "derivative assignment")
    must_reject(lambda: assign_families(families[:-1], protocol), "short cohort accepted")
    must_reject(lambda: assign_families(families + [families[0]], protocol), "duplicate lineage accepted")
    mixed = [dict(family) for family in families]
    mixed[-1]["lineage_family_id"] = mixed[0]["lineage_family_id"]
    must_reject(lambda: assign_families(mixed, protocol), "cross-population lineage accepted")
    formulas = protocol["outcomes"]["formulas"]
    require(formulas["decision_false_denial_rate"] == "|D ∩ L| / |L ∩ O_decision|", "denial includes abstention")
    require(formulas["allowed_decision_abstention_rate"] == "|A ∩ L| / |L ∩ O_decision|", "abstention formula")
    require(formulas["allowed_decision_withholding_rate"] == "|(D ∪ A) ∩ L| / |L ∩ O_decision|", "union formula")
    synthetic = [{"oracle": "allowed", "decision": value}
                 for value in ("deny", "abstain", "allow", None, None)]
    metrics = decision_metrics(synthetic)
    require(metrics == {"false_denial": Fraction(1, 3), "allowed_abstention": Fraction(1, 3),
                        "withholding": Fraction(2, 3), "scheduled_abstention": Fraction(1, 5),
                        "conditional_abstention": Fraction(1, 3)}, "denial/abstention synthetic arithmetic")
    require(decision_metrics([])["false_denial"] is None, "undefined denominator turned into zero")
    require(len(set(protocol["outcomes"]["terminal_categories"])) == 7, "terminal categories")
    require(len(protocol["mutation_taxonomy"]) == 13, "mutation coverage")
    arms = {arm["id"]: arm for arm in protocol["arms"]}
    require(set(arms) == {"A0", "A1", "A2", "A3", "A4"}, "five arms missing")
    require(all(arm["model_calls"] == 0 for arm in arms.values()), "fixed-action model inference")
    require(all(arms[name]["contrast_role"] == "negative_control_equivalent_to_A0" for name in ("A1", "A2")),
            "model-free controls mislabelled as model comparisons")
    require(all(arms[name]["required_qualifications"] and "unrun" in arms[name]["when_unavailable"]
                for name in ("A3", "A4")), "qualification bypass")
    fixed = protocol["fixed_action_plan"]
    require(fixed["seeds"] == [104729, 104759, 104761] and fixed["repetitions_per_case_arm"] == 3, "seeds/repetitions")
    require(fixed["scheduled_attempts"] == {"development": 180, "calibration": 180, "final": 540, "total": 900},
            "fixed schedule totals")
    case_ids = sorted(f"synthetic-case-{number:02}" for number in range(60))
    for seed in fixed["seeds"]:
        generator = random.Random(seed)
        shuffled_cases, order = case_ids[:], sorted(arms)
        generator.shuffle(shuffled_cases)
        generator.shuffle(order)
        positions = {arm: [0] * 5 for arm in order}
        for index, _case in enumerate(shuffled_cases):
            shift = index % 5
            rotated = order[shift:] + order[:shift]
            for position, arm in enumerate(rotated):
                positions[arm][position] += 1
        require(all(counts == [12] * 5 for counts in positions.values()), "unbalanced arm schedule")
    fixed_budget = resources["fixed_action_budget"]
    group = fixed_budget["per_attempt_resource_group"]
    require(group == protocol["resources"]["per_attempt_resource_group"], "group controls differ across documents")
    require(group["logical_cpu_affinity_count"] == group["cpu_quota_cores"] == 1,
            "single-core CPU enforcement missing")
    require(group["maximum_processes_and_threads"] == 16 and
            group["maximum_native_threads_per_tool"] == 1, "solver children or thread bound missing")
    require(group["thread_environment"] == {
        "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1", "VECLIB_MAXIMUM_THREADS": "1", "RAYON_NUM_THREADS": "1"},
        "pinned native thread settings missing")
    require(group["aggregate_memory_gib"] * (1024 ** 3) == group["aggregate_memory_bytes"] == 2147483648
            and group["additional_swap_bytes"] == 0, "aggregate group memory budget")
    require(group["wall_timeout_seconds"] == group["aggregate_cpu_budget_seconds"] == 20,
            "distinct wall/CPU group stopping thresholds")
    require(fixed_budget["maximum_concurrent_attempts"] == protocol["resources"]["maximum_concurrent_attempts"] == 1,
            "unaccounted concurrent attempt")
    require(fixed_budget["attempts"] * group["wall_timeout_seconds"] ==
            fixed_budget["nominal_aggregate_attempt_wall_seconds"] == 18000, "nominal wall schedule arithmetic")
    require(fixed_budget["attempts"] * group["aggregate_cpu_budget_seconds"] ==
            fixed_budget["aggregate_attempt_cpu_stopping_budget_seconds"] == 18000 and
            fixed_budget["aggregate_attempt_cpu_stopping_budget_hours"] == 5, "accounted CPU stopping budget")
    require("all current/exited descendants" in group["accounting"] and
            "entire group" in group["termination"] and "overshoot" in group["enforcement_overshoot"] and
            "before scored attempts" in group["qualification_gate"], "aggregate containment/accounting qualification")
    # Synthetic accounting example: CPU counters from a runner and two children
    # total one second while elapsed wall time is two seconds. Neither each
    # child's allowance nor elapsed wall time is a measured group CPU total.
    synthetic_group_cpu = [Fraction(1, 4), Fraction(1, 2), Fraction(1, 4)]
    require(sum(synthetic_group_cpu) == 1 and sum(synthetic_group_cpu) != 2,
            "group CPU was substituted with wall time")
    require((18000 - Fraction(20001, 1000)) // 20 == 898,
            "accounting discarded real enforcement overshoot")
    model = protocol["closed_loop_plan"]
    require(model["task"] == "LA-016" and model["actual_model_required"] and
            model["pool_with_fixed_action"] is False, "actual-model separation")
    require(model["runs_executed"] == model["currently_dispatchable_runs"] == 0, "invented model runs")
    require(model["planned_case_count"] * len(model["planned_arms"]) * len(model["seeds"]) == 900,
            "conditional model schedule arithmetic")
    require(model["planned_attempts"] == fixed["scheduled_attempts"], "conditional model split counts")
    budget = model["budget"]
    require(900 * budget["maximum_model_calls_per_attempt"] == budget["maximum_total_model_calls"] == 7200,
            "conditional model call ceiling")
    require(7200 * (budget["maximum_input_tokens_per_call"] + budget["maximum_output_tokens_per_call"]) ==
            budget["maximum_total_input_output_tokens"] == 22118400, "conditional model token ceiling")
    require(900 * budget["maximum_wall_seconds_per_attempt"] ==
            budget["maximum_aggregate_attempt_wall_hours"] * 3600 == 108000, "conditional model time ceiling")
    require(budget["paid_provider_budget"] == 0 and resources["model_study_budget"] == budget, "resource plan mismatch")
    require(protocol["statistics"]["bootstrap_resamples"] == 2000 and
            protocol["statistics"]["no_power_or_significance_guarantee"] is True, "uncertainty specification")
    for phrase in ("ranked allocation", "False denial counts D only", "Equivalence control",
                   "No model study is currently dispatchable", "LA-004–LA-025", "fixture",
                   "Solver and checker subprocesses are allowed", "singleton cpuset",
                   "not substituted for measured CPU", "never truncate cost records"):
        require(phrase in prose, f"prose missing {phrase}")
    return {"status": "pass", "scope": "protocol document and synthetic arithmetic validation only",
            "source_corpora_loaded": False, "benchmark_results_loaded": False,
            "provider_invoked": False, "experiments_executed": 0,
            "synthetic_checks": ["exact ranked strata and reversed-input invariance", "short/duplicate/cross-population cohorts rejected",
                                 "family-derived case membership", "distinct denial/abstention/withholding and undefined denominator",
                                 "balanced fixed schedule", "real-mechanism and model-study separation", "independent budget arithmetic",
                                 "group resource scope and separate CPU/wall accounting; no live enforcement qualification"],
            "documents_sha256": {name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
                                 for name in ("protocol.json", "protocol.md", "resource_plan.json")}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(validate(args.protocol_dir), indent=2))


if __name__ == "__main__":
    main()
