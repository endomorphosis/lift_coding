#!/usr/bin/env python3
"""Validate AF-012 proof-head isolation artifacts against acceptance criteria."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
SEEDS = {104729, 130363, 155921}
SCHEMA_MANIFEST = "autoformalization-proof-feedback-manifest/v1"
SCHEMA_RESULT = "autoformalization-proof-head-result/v1"
SCHEMA_ISOLATION = "autoformalization-proof-head-isolation/v1"
PROTECTED = (
    "compiler_cross_entropy",
    "embedding_cosine",
    "structural_reconstruction",
    "provenance_alignment",
    "anti_copy",
)
NATIVE_TOOLS = (
    "lean",
    "lake",
    "elan",
    "z3",
    "cvc5",
    "vampire",
    "eprover",
    "coqc",
    "isabelle",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    manifest = load_json(PAPER_ROOT / "data" / "proof_feedback_manifest.json")
    results = load_jsonl(PAPER_ROOT / "runs" / "proof_heads" / "results.jsonl")
    isolation = load_json(PAPER_ROOT / "evidence" / "proof_head_isolation.json")
    errors: list[str] = []

    if manifest.get("schema") != SCHEMA_MANIFEST:
        errors.append("bad proof-feedback manifest schema")
    if isolation.get("schema") != SCHEMA_ISOLATION:
        errors.append("bad isolation schema")
    if manifest.get("admitted_count") != 0 or manifest.get("admitted_for_t3_training") != []:
        errors.append("T3 admitted native/version-matched labels must be empty under sealed PATH")
    if manifest.get("eligible_native_label_count") != 0:
        errors.append("eligible native labels must be zero")

    outcome = manifest.get("t3_outcome") or {}
    if outcome.get("status") not in {"unrun", "insufficient_labels"}:
        errors.append(f"T3 status is not unrun/limited-scope: {outcome.get('status')}")
    if "limited_scope" not in str(outcome.get("scope") or "") or "unrun" not in str(outcome.get("scope") or ""):
        errors.append("T3 scope is not documented as limited-scope unrun")
    if outcome.get("native_checker_usable"):
        errors.append("manifest claims a usable native checker")
    if (outcome.get("teacher_proof_feedback") or {}).get("records") not in {0, None}:
        errors.append("teacher proof_feedback records are not zero")

    probe = manifest.get("capability_probe") or {}
    binaries = probe.get("binaries") or {}
    if any(binaries.get(name) for name in NATIVE_TOOLS):
        errors.append("sealed-PATH native binaries were treated as present")
    if probe.get("any_native_checker_usable"):
        errors.append("any_native_checker_usable is true")

    partitions = manifest.get("permitted_partitions") or {}
    if partitions.get("train", {}).get("n_units") != 69:
        errors.append("train inventory count != 69")
    if partitions.get("selection", {}).get("n_units") != 15:
        errors.append("selection inventory count != 15")
    final_test = partitions.get("final_test") or {}
    if final_test.get("ids_inspected") or final_test.get("bodies_opened") or final_test.get("used_for") != "locked":
        errors.append("final test was opened or not locked")
    if (partitions.get("fixed_canary") or {}).get("used_for") != "unused":
        errors.append("fixed canary was used for T3 training")

    inventory = manifest.get("inventory") or []
    train_ids = {
        row["source_record_id"]
        for row in inventory
        if row.get("split") == "train" and row.get("record_kind") == "natural_source_candidate"
    }
    selection_ids = {
        row["source_record_id"]
        for row in inventory
        if row.get("split") == "selection" and row.get("record_kind") == "natural_source_candidate"
    }
    if len(train_ids) != 69:
        errors.append(f"train candidate coverage {len(train_ids)} != 69")
    if len(selection_ids) != 15:
        errors.append(f"selection candidate coverage {len(selection_ids)} != 15")
    if any(row.get("admitted_for_t3_training") for row in inventory):
        errors.append("inventory contains an admitted T3 training record")
    if not any(
        row.get("record_kind") == "isolation_contract_probe" and "isolation_probe_not_t3_label" in row.get("rejection_reasons", [])
        for row in inventory
    ):
        errors.append("isolation probes are not excluded from T3 labels")
    if not any("version_mismatch" in (row.get("rejection_reasons") or []) for row in inventory):
        errors.append("version-mismatched feedback was not tracked")
    if not any("holdout_partition" in (row.get("rejection_reasons") or []) for row in inventory):
        errors.append("holdout feedback was not tracked")
    if not any("untrusted" in (row.get("rejection_reasons") or []) for row in inventory):
        errors.append("untrusted feedback was not tracked")

    filt = manifest.get("filter_accounting") or {}
    if filt.get("duplicate_count", 0) < 1:
        errors.append("duplicate feedback was not tracked")
    if filt.get("skipped_version_mismatch_count", 0) < 1:
        errors.append("version mismatch skip count missing")
    if filt.get("skipped_holdout_count", 0) < 1:
        errors.append("holdout skip count missing")
    if filt.get("skipped_untrusted_count", 0) < 1:
        errors.append("untrusted skip count missing")
    if filt.get("skipped_invalid_count", 0) < 1:
        errors.append("invalid skip count missing")

    budget = manifest.get("matched_budget") or {}
    if not budget.get("matched_primary_envelope"):
        errors.append("T3/T2 route budgets are not matched")

    contract = isolation.get("isolation_contract") or {}
    if contract.get("proof_loss_weight_in_primary_objective") != 0.0:
        errors.append("proof loss leaks into the primary objective")
    if contract.get("protected_objectives") != list(PROTECTED):
        errors.append("protected objectives do not match the isolation contract")
    if not contract.get("separate_parameters") or not contract.get("anti_copy_protected"):
        errors.append("anti-copy/separate-parameter contract missing")
    if not isolation.get("held"):
        errors.append("isolation contract not marked held")
    if isolation.get("predicted_proof_success_used_as_certification"):
        errors.append("isolation evidence treats predicted success as certification")

    iso_seeds = {item.get("seed") for item in isolation.get("isolation_probes") or []}
    if iso_seeds != SEEDS:
        errors.append(f"isolation seeds {iso_seeds} != {SEEDS}")
    for item in isolation.get("isolation_probes") or []:
        if not item.get("protected_parameters_unchanged"):
            errors.append(f"protected parameters changed under isolation probe seed {item.get('seed')}")
        if not item.get("heads_changed"):
            errors.append(f"isolation probe did not update heads for seed {item.get('seed')}")
        if not item.get("not_t3_certification"):
            errors.append(f"isolation probe missing not_t3_certification for seed {item.get('seed')}")
        fields = item.get("protected_fields_unchanged") or {}
        if not fields or not all(fields.values()):
            errors.append(f"primary/anti-copy fields changed for seed {item.get('seed')}: {fields}")
        obj = item.get("objective_isolation") or {}
        if obj.get("proof_loss_weight_in_primary_objective") != 0.0:
            errors.append("isolation probe reports nonzero primary proof loss")
        if not obj.get("protected_parameters_unchanged"):
            errors.append("isolation probe objective_isolation.protected_parameters_unchanged is false")

    t3_emp = isolation.get("t3_empirical") or {}
    if t3_emp.get("admitted_records") != 0:
        errors.append("isolation evidence admits T3 records")
    if "unrun" not in str(t3_emp.get("scope") or "") and "unrun" not in str(t3_emp.get("status") or ""):
        errors.append("isolation evidence does not record unrun T3")
    cal = isolation.get("calibration_and_routing") or {}
    if cal.get("calibration_error") is not None or cal.get("route_value") is not None:
        errors.append("T3 calibration/route_value must be null without eligible labels")
    if cal.get("eligible_native_label_count") != 0:
        errors.append("isolation calibration used ineligible labels")
    if not cal.get("matched_route_budget"):
        errors.append("matched route budget missing")
    if not cal.get("isolation_probe_metrics_are_not_t3_certification"):
        errors.append("isolation-probe metrics were not excluded from T3 certification")

    by_kind: dict[str, list[dict]] = {}
    for row in results:
        if row.get("schema") != SCHEMA_RESULT:
            errors.append(f"bad result schema {row.get('record_id')}")
        if row.get("predicted_proof_success_used_as_certification"):
            errors.append(f"predicted success used as certification {row.get('record_id')}")
        if row.get("counts_as_native_checked_proof"):
            errors.append(f"row counted as native checked proof {row.get('record_id')}")
        if row.get("claim_admissible") is True:
            errors.append(f"claim_admissible true {row.get('record_id')}")
        by_kind.setdefault(row.get("record_kind"), []).append(row)

    t3_attempts = by_kind.get("t3_attempt") or []
    if {row.get("seed") for row in t3_attempts} != SEEDS:
        errors.append("T3 attempts missing seeds")
    for row in t3_attempts:
        if row.get("execution_status") not in {"unavailable", "unrun"}:
            errors.append(f"T3 attempt not unrun/unavailable {row.get('record_id')}")
        if row.get("result_kind") != "no_run":
            errors.append(f"T3 attempt is not no_run {row.get('record_id')}")
        metrics = row.get("metrics") or {}
        if metrics.get("calibration_error") is not None:
            errors.append(f"T3 attempt fabricated calibration {row.get('record_id')}")
        if metrics.get("native_checked_useful_proof_coverage") is not None:
            errors.append(f"T3 attempt fabricated native coverage {row.get('record_id')}")
        if metrics.get("route_value") is not None:
            errors.append(f"T3 attempt fabricated route value {row.get('record_id')}")
        if metrics.get("applied_count") not in {0, None}:
            errors.append(f"T3 attempt applied admitted records {row.get('record_id')}")
        if (row.get("checkpoint") or {}).get("matched_t2") is not True:
            errors.append(f"T3 attempt not matched to T2 {row.get('record_id')}")

    t2_baselines = by_kind.get("t2_baseline") or []
    if {row.get("seed") for row in t2_baselines} != SEEDS:
        errors.append("T2 baseline seeds missing")
    for row in t2_baselines:
        if (row.get("metrics") or {}).get("native_checked_useful_proof_coverage") is not None:
            errors.append(f"T2 baseline fabricated native coverage {row.get('record_id')}")

    iso_rows = by_kind.get("isolation") or []
    if {row.get("seed") for row in iso_rows} != SEEDS:
        errors.append("isolation result seeds missing")
    for row in iso_rows:
        if row.get("split") != "constructed_control":
            errors.append(f"isolation row not constructed_control {row.get('record_id')}")
        if row.get("execution_status") != "measured":
            errors.append(f"isolation row not measured {row.get('record_id')}")
        metrics = row.get("metrics") or {}
        if metrics.get("protected_parameters_unchanged") is not True:
            errors.append(f"isolation row lost protected state {row.get('record_id')}")
        if metrics.get("heads_changed") is not True:
            errors.append(f"isolation row heads did not change {row.get('record_id')}")
        if metrics.get("proof_loss_weight_in_primary_objective") != 0.0:
            errors.append(f"isolation row primary proof loss {row.get('record_id')}")

    cal_rows = by_kind.get("calibration") or []
    if len(cal_rows) != 1:
        errors.append("expected one calibration row")
    else:
        cal_row = cal_rows[0]
        metrics = cal_row.get("metrics") or {}
        if metrics.get("calibration_error") is not None:
            errors.append("calibration used a numeric value without eligible labels")
        if metrics.get("eligible_native_label_count") != 0:
            errors.append("calibration eligible native label count is not zero")
        if metrics.get("numerator_basis") != "actual_eligible_native_or_version_matched_verifier_labels":
            errors.append("calibration numerator is not actual eligible labels")
        if cal_row.get("execution_status") not in {"unavailable", "unrun"}:
            errors.append("calibration row should be unrun/unavailable")

    route_rows = by_kind.get("routing") or []
    if len(route_rows) != 1:
        errors.append("expected one routing row")
    else:
        route = route_rows[0]
        metrics = route.get("metrics") or {}
        if metrics.get("route_value") is not None:
            errors.append("route value fabricated")
        if metrics.get("predicted_proof_success_used_as_certification"):
            errors.append("routing used predicted success as certification")
        if not metrics.get("matched_route_budget"):
            errors.append("routing missing matched route budget")
        if metrics.get("actual_checker_outcomes") not in {0, None}:
            errors.append("routing claimed actual checker outcomes")
        if not (route.get("matched_budget") or {}).get("matched_primary_envelope"):
            errors.append("routing row missing matched T2/T3 envelope")

    locked = [row for row in by_kind.get("coverage") or [] if row.get("split") == "final_test"]
    if not locked:
        errors.append("missing final-test coverage row")
    for row in locked:
        if row.get("execution_status") != "unrun" or row.get("result_kind") != "no_run":
            errors.append("final test not unrun/no_run")
        if row.get("bodies_opened") or row.get("ids_inspected"):
            errors.append("final test opened")

    summary_rows = by_kind.get("summary") or []
    if len(summary_rows) != 1:
        errors.append("expected one summary row")
    else:
        summary = summary_rows[0]
        if summary.get("execution_status") not in {"unavailable", "unrun"}:
            errors.append("summary is not unrun/unavailable")
        if (summary.get("comparison") or {}).get("improvement_claimed"):
            errors.append("T3 vs T2 improvement was claimed")
        if (summary.get("metrics") or {}).get("isolation_contract_held") is not True:
            errors.append("summary missing isolation_contract_held")
        if (summary.get("metrics") or {}).get("t3_unrun_limited_scope") is not True:
            errors.append("summary missing t3_unrun_limited_scope")

    if "T3 training gain versus T2" not in (manifest.get("not_claimed") or []):
        errors.append("manifest does not exclude a T3 training-gain claim")
    if "predicted proof-head success as certification" not in (manifest.get("not_claimed") or []):
        errors.append("manifest does not exclude predicted-success certification")

    if errors:
        print("AF-012 check_outputs failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(
        json.dumps(
            {
                "ok": True,
                "admitted_count": 0,
                "isolation_held": True,
                "t3_scope": outcome.get("scope"),
                "train_candidates": len(train_ids),
                "selection_candidates": len(selection_ids),
                "result_rows": len(results),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
