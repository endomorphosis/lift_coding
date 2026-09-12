#!/usr/bin/env python3
"""Validate AF-018 planning and proof-assistance artifacts against acceptance criteria."""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
REPO_ROOT = PAPER_ROOT.parents[2]

SCHEMA_PLAN = "autoformalization-planning-result/v1"
SCHEMA_ASSIST = "autoformalization-proof-assistance-result/v1"
SCHEMA_RECEIPT = "autoformalization-native-checker-receipt/v1"
LEANSTRAL_MODEL_ID = "Frosty40/Leanstral-1.5-119B-A6B-GGUF-NVFP4"
LEANSTRAL_REVISION = "abcc5ce2528c6375148d41dac6dce20f06c339f4"
REPLAYS = 3
PLAN_GOALS = 8
ASSIST_GOALS = 5
SEALED_TOOLS = ("lean", "lake", "elan", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle")


def load_jsonl(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    planning_path = PAPER_ROOT / "runs" / "planning" / "results.jsonl"
    assistance_path = PAPER_ROOT / "runs" / "proof_assistance" / "results.jsonl"
    receipts_path = PAPER_ROOT / "evidence" / "native_checker_receipts.jsonl"
    planning = load_jsonl(planning_path)
    assistance = load_jsonl(assistance_path)
    receipts = load_jsonl(receipts_path)
    errors: list[str] = []

    plan_obs = [row for row in planning if row.get("kind") == "observation"]
    plan_sum = [row for row in planning if row.get("kind") == "summary"]
    assist_obs = [row for row in assistance if row.get("kind") == "observation"]
    assist_sum = [row for row in assistance if row.get("kind") == "summary"]
    receipt_sum = [row for row in receipts if row.get("kind") == "summary" or row.get("receipt_id") == "summary:native_checker"]
    receipt_obs = [row for row in receipts if row.get("schema") == SCHEMA_RECEIPT and row.get("receipt_id") != "summary:native_checker"]

    if len(plan_sum) != 1:
        errors.append(f"expected one planning summary, got {len(plan_sum)}")
    if len(assist_sum) != 1:
        errors.append(f"expected one assistance summary, got {len(assist_sum)}")
    if len(receipt_sum) != 1:
        errors.append(f"expected one receipt summary, got {len(receipt_sum)}")

    for row in plan_obs:
        if row.get("schema") != SCHEMA_PLAN:
            errors.append(f"bad planning schema {row.get('record_id')}")
        if row.get("counts_as_executed_proof") or row.get("counts_as_native_checked_proof"):
            errors.append(f"plan counted as proof: {row.get('record_id')}")
        if row.get("result_kind") == "native_checked_proof":
            errors.append(f"plan used native_checked_proof: {row.get('record_id')}")
        if row.get("plan", {}).get("semantic_authority") or row.get("plan", {}).get("proof_execution_allowed"):
            errors.append(f"plan claimed proof/semantic authority: {row.get('record_id')}")
        if row.get("n_goals") != PLAN_GOALS or row.get("n_replays") != REPLAYS:
            errors.append(f"planning row missing full goal/replay counts: {row.get('record_id')}")

    by_arm_goal: dict[tuple[str, str], list[str]] = defaultdict(list)
    selected_by_arm: dict[tuple[str, str], list[list[str]]] = defaultdict(list)
    for row in plan_obs:
        arm = row["experiment_arm"]
        goal = row["goal_id"]
        by_arm_goal[(arm, goal)].append(row["plan"]["plan_id"])
        selected_by_arm[(arm, goal)].append(list(row["plan"]["selected_source_ids"]))

    expected_arms = {"plan.unguided", "plan.guided_pinned_ranker", "plan.llm_nominated"}
    arms = {arm for arm, _goal in by_arm_goal}
    if arms != expected_arms:
        errors.append(f"unexpected planning arms {arms}")
    goals = {goal for _arm, goal in by_arm_goal}
    if len(goals) != PLAN_GOALS:
        errors.append(f"expected {PLAN_GOALS} planning goals, got {len(goals)}")

    for (arm, goal), plan_ids in by_arm_goal.items():
        if len(plan_ids) != REPLAYS:
            errors.append(f"{arm} {goal} replay count {len(plan_ids)} != {REPLAYS}")
        if arm != "plan.llm_nominated" and len(set(plan_ids)) != 1:
            errors.append(f"nondeterministic replay for {arm} {goal}: {plan_ids}")
        if arm == "plan.llm_nominated":
            statuses = {row["execution_status"] for row in plan_obs if row["experiment_arm"] == arm and row["goal_id"] == goal}
            if statuses != {"unavailable"}:
                errors.append(f"LLM arm not unavailable for {goal}: {statuses}")
            if any(row["plan"]["llm_guidance_applied"] for row in plan_obs if row["experiment_arm"] == arm and row["goal_id"] == goal):
                errors.append(f"invented LLM guidance on {goal}")

    for goal in goals:
        unguided = set(by_arm_goal[("plan.unguided", goal)])
        guided = set(by_arm_goal[("plan.guided_pinned_ranker", goal)])
        if unguided == guided:
            errors.append(f"guided plan identity matches unguided for {goal}")
        ung_sel = selected_by_arm[("plan.unguided", goal)][0]
        gui_sel = selected_by_arm[("plan.guided_pinned_ranker", goal)][0]
        if ung_sel == gui_sel:
            errors.append(f"guided selected sources match unguided for {goal}")

    guided_rows = [row for row in plan_obs if row["experiment_arm"] == "plan.guided_pinned_ranker"]
    if not guided_rows:
        errors.append("missing guided rows")
    else:
        digest = guided_rows[0]["guidance"]["digest"]
        if not digest.startswith("sha256:"):
            errors.append("guided digest is not pinned")
        if any(row["guidance"].get("model_call") or row["guidance"].get("trained") for row in guided_rows):
            errors.append("guided ranker claimed as a model call or trained artifact")
        if not all(row["plan"]["learned_guidance_applied"] for row in guided_rows):
            errors.append("pinned guidance did not apply")

    if plan_sum:
        summary = plan_sum[0]
        if summary.get("counts_as_executed_proof"):
            errors.append("planning summary counts as executed proof")
        if not summary.get("deterministic_replay"):
            errors.append("planning summary missing deterministic_replay")
        if "plan.llm_nominated" not in summary.get("unavailable_arms", []):
            errors.append("LLM planning arm not listed as unavailable")
        costs = summary.get("all_attempt_costs") or {}
        if "elapsed_seconds" not in costs or "n_attempts" not in costs:
            errors.append("planning summary missing all-attempt costs")

    for row in assist_obs:
        if row.get("schema") != SCHEMA_ASSIST:
            errors.append(f"bad assistance schema {row.get('record_id')}")
        if row.get("counts_as_native_checked_proof") or row.get("accepted_proof"):
            errors.append(f"assistance claimed accepted native proof: {row.get('record_id')}")
        if row.get("result_kind") == "native_checked_proof":
            errors.append(f"assistance used native_checked_proof: {row.get('record_id')}")
        model = row.get("model") or {}
        if model.get("calls_executed"):
            errors.append(f"invented model call: {row.get('record_id')}")
        if model.get("invented_model_call") or model.get("fine_tuning_claimed"):
            errors.append(f"fine-tuning or invented-call flag: {row.get('record_id')}")
        if row["experiment_arm"] == "leanstral":
            if model.get("model_id") != LEANSTRAL_MODEL_ID or model.get("revision") != LEANSTRAL_REVISION:
                errors.append(f"Leanstral identity missing on {row.get('record_id')}")
            settings = row.get("prompt_settings") or (row.get("detail") or {})
            if row["stage"] == "candidate_generation" and row["goal_id"].startswith("h."):
                prompt = row.get("prompt_settings") or {}
                forbidden = prompt.get("forbidden") or []
                if "sorry" not in forbidden or "admit" not in forbidden or "axiom" not in forbidden:
                    errors.append(f"Leanstral prompt settings missing sorry/admit/axiom forbid on {row.get('record_id')}")

    hammer_h = [row for row in assist_obs if row["experiment_arm"] == "hammer" and str(row.get("goal_id", "")).startswith("h.")]
    leanstral_h = [row for row in assist_obs if row["experiment_arm"] == "leanstral" and str(row.get("goal_id", "")).startswith("h.")]
    h_goals = {row["goal_id"] for row in hammer_h}
    if len(h_goals) != ASSIST_GOALS:
        errors.append(f"expected {ASSIST_GOALS} hammer goals, got {len(h_goals)}")
    for goal in h_goals:
        stages = {row["stage"] for row in hammer_h if row["goal_id"] == goal}
        if stages != {"candidate_generation", "solver_response", "native_reconstruction"}:
            errors.append(f"hammer stages incomplete for {goal}: {stages}")
        stages_l = {row["stage"] for row in leanstral_h if row["goal_id"] == goal}
        if stages_l != {"candidate_generation", "solver_response", "native_reconstruction"}:
            errors.append(f"leanstral stages incomplete for {goal}: {stages_l}")

    unsupported = [row for row in hammer_h if row["stage"] == "candidate_generation" and row["execution_status"] == "unsupported"]
    encoded = [row for row in hammer_h if row["stage"] == "candidate_generation" and row.get("encoding_produced")]
    if len(unsupported) < 2:
        errors.append("expected unsupported dependent/HO Hammer goals")
    if len(encoded) < 3:
        errors.append("expected measured FOL encodings")
    if any(row.get("candidate_produced") for row in hammer_h):
        errors.append("Hammer solver candidates were invented")
    if any(row.get("candidate_produced") for row in leanstral_h):
        errors.append("Leanstral candidates were invented")
    if any(row["execution_status"] != "unavailable" for row in leanstral_h):
        errors.append("Leanstral assistance arm is not entirely unavailable")
    if any(row["stage"] == "solver_response" and row["execution_status"] not in {"unavailable", "unsupported"} for row in hammer_h):
        errors.append("Hammer solver responses were not recorded as unavailable/unsupported")
    if any(row["stage"] == "native_reconstruction" and row["execution_status"] not in {"unavailable", "unsupported"} for row in hammer_h):
        errors.append("Hammer native reconstruction was not unavailable/unsupported")

    policy_rows = [row for row in assist_obs if row["stage"] == "policy_scan"]
    kinds = {(row["experiment_arm"], (row.get("detail") or {}).get("fixture_kind") or (row.get("policy") or {}).get("reasons")) for row in policy_rows}
    if len(policy_rows) != 8:
        errors.append(f"expected 8 policy-scan rows (4 fixtures x 2 arms), got {len(policy_rows)}")
    for row in policy_rows:
        policy = row.get("policy") or {}
        kind = (row.get("detail") or {}).get("fixture_kind")
        if kind in {"sorry", "admit", "unapproved_axiom"}:
            if not policy.get("policy_rejected") or row.get("execution_status") != "invalid":
                errors.append(f"{kind} was not rejected: {row.get('record_id')}")
            if kind == "sorry" and not policy.get("sorry_present"):
                errors.append("sorry fixture missing sorry_present")
            if kind == "admit" and not policy.get("admit_present"):
                errors.append("admit fixture missing admit_present")
            if kind == "unapproved_axiom" and not policy.get("unapproved_axiom_present"):
                errors.append("axiom fixture missing unapproved_axiom_present")
        if kind == "clean_rfl":
            if policy.get("policy_rejected"):
                errors.append("clean rfl incorrectly policy-rejected")
            if row.get("accepted_proof") or row.get("counts_as_native_checked_proof"):
                errors.append("clean rfl counted as native proof without a kernel")
        if (row.get("detail") or {}).get("not_a_model_output") is not True:
            errors.append(f"policy fixture not labeled as non-model output: {row.get('record_id')}")

    if assist_sum:
        summary = assist_sum[0]
        cand = summary.get("candidate_rate") or {}
        acc = summary.get("accepted_proof_rate") or {}
        cov = summary.get("native_coverage") or {}
        cats = summary.get("failure_categories") or {}
        costs = summary.get("all_attempt_costs") or {}
        if cand.get("hammer") != 0.0 or cand.get("leanstral") != 0.0:
            errors.append(f"nonzero candidate rate {cand}")
        if acc.get("hammer") != 0.0 or acc.get("leanstral") != 0.0:
            errors.append(f"nonzero accepted-proof rate {acc}")
        if cov.get("native_checked_proofs") != 0 or cov.get("hammer") != 0.0 or cov.get("leanstral") != 0.0:
            errors.append(f"nonzero native coverage {cov}")
        required_cats = {
            "unavailable_solver",
            "unavailable_native_checker",
            "unavailable_model_service",
            "unsupported_translation",
            "policy_rejected_sorry",
            "policy_rejected_admit",
            "policy_rejected_unapproved_axiom",
        }
        missing_cats = required_cats - set(cats)
        if missing_cats:
            errors.append(f"failure categories missing {sorted(missing_cats)}")
        if not {"elapsed_seconds", "cpu_seconds", "gpu_seconds", "provider_units", "memory_gib", "human_review_seconds"} <= set(costs):
            errors.append("assistance summary missing separated all-attempt cost fields")
        ident = summary.get("model_identity") or {}
        if ident.get("model_id") != LEANSTRAL_MODEL_ID or ident.get("revision") != LEANSTRAL_REVISION:
            errors.append("summary missing Leanstral identity")
        if ident.get("calls_executed") or ident.get("invented_model_call") or ident.get("fine_tuning_claimed"):
            errors.append("summary claims a model call or fine-tuning")
        if "leanstral.model_service" not in (summary.get("unavailable_arms") or []):
            errors.append("Leanstral model service not listed as unavailable")
        policy = summary.get("sorry_admit_axiom_policy") or {}
        if not (policy.get("sorry_rejected") and policy.get("admit_rejected") and policy.get("unapproved_axiom_rejected")):
            errors.append("summary does not record sorry/admit/axiom rejection")

    probed = {row.get("checker_name") for row in receipt_obs if row.get("experiment_arm") == "environment_probe"}
    if set(SEALED_TOOLS) - probed:
        errors.append(f"native probe missing tools {sorted(set(SEALED_TOOLS) - probed)}")
    for row in receipt_obs:
        if row.get("schema") != SCHEMA_RECEIPT:
            errors.append(f"bad receipt schema {row.get('receipt_id')}")
        if row.get("accepted") or row.get("counts_as_native_checked_proof"):
            errors.append(f"receipt accepted a native proof: {row.get('receipt_id')}")
        if row.get("experiment_arm") == "environment_probe" and row.get("checker_name") in SEALED_TOOLS:
            if row.get("usable_in_sealed_validation"):
                errors.append(f"sealed PATH unexpectedly has {row.get('checker_name')}")
            if row.get("execution_status") != "unavailable":
                errors.append(f"probe for {row.get('checker_name')} is not unavailable")
        if row.get("policy_rejected"):
            reasons = row.get("policy_rejection_reasons") or []
            if not reasons:
                errors.append(f"policy rejection without reasons: {row.get('receipt_id')}")

    sorry_receipts = [row for row in receipt_obs if row.get("sorry_present") and row.get("policy_rejected")]
    admit_receipts = [row for row in receipt_obs if row.get("admit_present") and row.get("policy_rejected")]
    axiom_receipts = [row for row in receipt_obs if row.get("unapproved_axiom_present") and row.get("policy_rejected")]
    if len(sorry_receipts) < 2 or len(admit_receipts) < 2 or len(axiom_receipts) < 2:
        errors.append("policy rejection receipts missing for sorry/admit/axiom on both arms")

    print(json.dumps({
        "ok": not errors,
        "n_planning": len(planning),
        "n_planning_obs": len(plan_obs),
        "n_assistance": len(assistance),
        "n_assistance_obs": len(assist_obs),
        "n_receipts": len(receipts),
        "n_receipt_obs": len(receipt_obs),
        "plan_goals": len(goals),
        "assist_goals": len(h_goals),
        "errors": errors,
        "paths": {
            "planning": str(planning_path.relative_to(REPO_ROOT)),
            "assistance": str(assistance_path.relative_to(REPO_ROOT)),
            "receipts": str(receipts_path.relative_to(REPO_ROOT)),
        },
    }, indent=2, sort_keys=True))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
