#!/usr/bin/env python3
"""Validate AF-016 pipeline-comparison artifacts against acceptance criteria."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parents[2]
EVAL_DIR = PAPER_ROOT / "evaluation"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))
import run_benchmark as harness  # noqa: E402

ARMS = ("A", "B", "C", "D", "E")
COLUMNS = ("sources_covered", "fidelity_uncertainty", "correct_transfers", "cost_latency")
CHECKER_DIGEST = "0d22c6e92be47a464452266e1a09d3b1d072f98ce3e5fec19bdbe9f47273f052"
CHECKER_ID = "AF-010-shared-target-checker/v1"
FORBIDDEN_CELL_TOKENS = ("TBD", "tbd", "TODO", "dry-run", "dry_run", "fixture_success")
Q1_SOURCE = "AF016-DEV-Q1-protected-write"
Q1_GOAL = "Q1_protected_and_not_approved_implies_not_write"
Q1_PREMISES = ["Protected", "Approved", "Write"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def main() -> int:
    manifest_path = PAPER_ROOT / "runs" / "pipeline_comparison" / "manifest.json"
    results_path = PAPER_ROOT / "runs" / "pipeline_comparison" / "results.jsonl"
    manifest = load_json(manifest_path)
    rows = load_jsonl(results_path)
    errors: list[str] = []

    if manifest.get("schema") != "autoformalization-pipeline-comparison-manifest/v1":
        errors.append("manifest schema mismatch")
    if manifest.get("task_id") != "AF-016":
        errors.append("manifest task_id mismatch")
    cells = manifest.get("table6", {}).get("cells") or []
    if len(cells) != 20:
        errors.append(f"expected 20 Table 6 cells, got {len(cells)}")
    cell_ids = [cell.get("cell_id") for cell in cells]
    expected_ids = [f"{arm}:{column}" for arm in ARMS for column in COLUMNS]
    if cell_ids != expected_ids:
        errors.append(f"Table 6 cell order drifted: {cell_ids}")

    for cell in cells:
        if cell.get("denominator") != 1913:
            errors.append(f"{cell.get('cell_id')} denominator is not 1913")
        if cell.get("population") != "final_test.natural_source_units":
            errors.append(f"{cell.get('cell_id')} is not bound to final-test natural units")
        if cell.get("status") not in {"unrun", "unmeasured", "unavailable"}:
            errors.append(f"{cell.get('cell_id')} status {cell.get('status')} is not an allowed Table 6 status")
        if cell.get("value") is not None or cell.get("numerator") is not None:
            errors.append(f"{cell.get('cell_id')} inserted a numeric Table 6 value")
        if not str(cell.get("definition") or "").strip():
            errors.append(f"{cell.get('cell_id')} missing definition")
        if not str(cell.get("narrowed_claim") or "").strip():
            errors.append(f"{cell.get('cell_id')} missing narrowed claim")
        blob = json.dumps(cell, sort_keys=True)
        for token in FORBIDDEN_CELL_TOKENS:
            if token in blob:
                errors.append(f"{cell.get('cell_id')} contains forbidden token {token}")
        if cell["column"] == "fidelity_uncertainty" and cell.get("status") != "unmeasured":
            errors.append("fidelity cells must remain unmeasured")
        if cell["column"] == "sources_covered" and cell.get("status") != "unrun":
            errors.append("coverage cells must remain unrun for locked final-test")
        if cell["column"] == "cost_latency" and cell.get("status") != "unrun":
            errors.append("cost cells must remain unrun for locked final-test")

    if manifest.get("matched_comparison", {}).get("private_final_ids_disclosed"):
        errors.append("final-test identities were disclosed")
    if manifest.get("claim_policy", {}).get("synthetic_success_forbidden") is not True:
        errors.append("synthetic success is not forbidden")

    probe = manifest.get("capability_probe") or {}
    path = probe.get("path") or probe.get("native_binaries", {}).get("path")
    if path != "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin":
        errors.append(f"capability probe PATH is not sealed: {path}")
    tools = ((probe.get("native_binaries") or {}).get("tools") or {})
    for name in ("lean", "z3", "cvc5"):
        if tools.get(name, {}).get("usable"):
            errors.append(f"sealed probe unexpectedly found {name}")
    if (probe.get("direct_model") or {}).get("runnable"):
        errors.append("direct-model was reported runnable under sealed env")
    if (probe.get("learned_guidance") or {}).get("runnable"):
        errors.append("arm E was reported runnable")

    if not rows:
        errors.append("results.jsonl is empty")
    selection = [row for row in rows if row.get("split") == "selection"]
    constructed = [row for row in rows if row.get("constructed_control")]
    if len(selection) != 75:
        errors.append(f"expected 75 selection records, got {len(selection)}")
    if any(row.get("fixture") for row in rows):
        errors.append("fixture records entered results.jsonl")
    if any(row.get("split") == "final_test" for row in rows):
        errors.append("final-test records were emitted")

    for row in rows:
        try:
            harness.validate_record(row)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"schema/accounting failure {row.get('record_id')}: {exc}")
            continue
        if row.get("source_facets", {}).get("independent_gold_present"):
            errors.append(f"independent gold claimed: {row.get('record_id')}")
        if row.get("source_facets", {}).get("all_facet_match") is not None:
            errors.append(f"all_facet_match filled without gold: {row.get('record_id')}")
        if row.get("proof", {}).get("useful"):
            errors.append(f"useful proof claimed: {row.get('record_id')}")
        if row.get("result_kind") == "native_checked_proof":
            errors.append(f"native_checked_proof without kernel: {row.get('record_id')}")
        identities = row.get("identities") or {}
        if identities.get("checker_digest") != CHECKER_DIGEST or identities.get("checker_id") != CHECKER_ID:
            errors.append(f"checker identity drifted: {row.get('record_id')}")
        if identities.get("source_id") != row.get("source_id"):
            errors.append(f"source_id mismatch: {row.get('record_id')}")
        request = identities.get("checker_request") or {}
        if request.get("pin_sha256") != identities.get("identity_pin_sha256"):
            errors.append(f"candidate/checker pin mismatch: {row.get('record_id')}")
        if not request.get("identical_to_candidate_pin"):
            errors.append(f"checker request not identical to candidate pin: {row.get('record_id')}")
        if identities.get("experiment_arm") != row.get("experiment_arm"):
            errors.append(f"arm identity mismatch: {row.get('record_id')}")

    by_arm = Counter(row["experiment_arm"] for row in selection)
    if dict(by_arm) != {arm: 15 for arm in ARMS}:
        errors.append(f"selection arm counts drifted: {dict(by_arm)}")

    for row in selection:
        if row["experiment_arm"] == "A" and row["execution_status"] != "unavailable":
            errors.append(f"selection A not unavailable: {row['record_id']}")
        if row["experiment_arm"] == "E":
            if row["execution_status"] != "unavailable":
                errors.append(f"selection E not unavailable: {row['record_id']}")
            if row["identities"].get("learned_advice_applied") or row["identities"].get("checker_mutated"):
                errors.append(f"E applied advice or mutated checker: {row['record_id']}")
            if row["identities"].get("checker_digest_equals_D") is not True:
                errors.append("E checker is not pinned to D")
        if row["experiment_arm"] == "C":
            dumped = json.dumps(row, sort_keys=True)
            if row["identities"].get("checked_bridges") or row["identities"].get("proof_transfer_admitted"):
                errors.append(f"C admitted transfer: {row['record_id']}")
            if "checked_property_bridges" in dumped or "translation_receipts" in dumped:
                errors.append(f"C contains D bridge keys: {row['record_id']}")
        if row["experiment_arm"] == "D":
            if row["execution_status"] != "unsupported":
                errors.append(f"selection D should be unsupported: {row['record_id']}")
            if row["proof"].get("false_transfer"):
                errors.append(f"unsupported D counted as false transfer: {row['record_id']}")
            if row["identities"].get("looked_up_bridge_source_id") != row["source_id"]:
                errors.append(f"D lookup used a different source_id: {row['record_id']}")
        if row["experiment_arm"] == "B" and row["execution_status"] not in {"measured", "abstained"}:
            errors.append(f"selection B unexpected status: {row['record_id']} {row['execution_status']}")

    q1_guarded = next((row for row in rows if row.get("record_id") == f"D:{Q1_SOURCE}:guarded"), None)
    q1_unguarded = next((row for row in rows if row.get("record_id") == f"D:{Q1_SOURCE}:unguarded"), None)
    if q1_guarded is None or q1_unguarded is None:
        errors.append("missing constructed Q1 D records")
    else:
        for row in (q1_guarded, q1_unguarded):
            if row.get("split") != "constructed_control" or not row.get("constructed_control"):
                errors.append(f"Q1 record not labeled constructed_control: {row['record_id']}")
            if row["identities"].get("evidence_source_id") != Q1_SOURCE:
                errors.append(f"Q1 evidence source drifted: {row['record_id']}")
            if row["identities"].get("evidence_goal_id") != Q1_GOAL:
                errors.append(f"Q1 evidence goal drifted: {row['record_id']}")
            if row["identities"].get("evidence_premise_ids") != Q1_PREMISES:
                errors.append(f"Q1 evidence premises drifted: {row['record_id']}")
            if row["proof"].get("theorem") != Q1_GOAL:
                errors.append(f"Q1 theorem drifted: {row['record_id']}")
            if row["identities"].get("checker_request", {}).get("pin_sha256") != row["identities"].get("policy_identity_pin_sha256"):
                errors.append(f"Q1 candidate/evidence pin mismatch: {row['record_id']}")
            if row["result_kind"] == "native_checked_proof" or row["proof"].get("useful"):
                errors.append(f"Q1 claimed a native useful proof: {row['record_id']}")
        if q1_guarded["identities"].get("bridge_status") != "accepted_transfer":
            errors.append("guarded Q1 was not an accepted transfer")
        if q1_unguarded["result_kind"] != "countermodel":
            errors.append("unguarded Q1 was not a countermodel")
        if q1_guarded["identities"].get("policy_identity_pin_sha256") != q1_unguarded["identities"].get("policy_identity_pin_sha256"):
            errors.append("guarded and unguarded Q1 do not share the same goal/premise/source pin")

    c_constructed = [row for row in constructed if row["experiment_arm"] == "C"]
    for row in c_constructed:
        if row["identities"].get("checked_bridges"):
            errors.append("constructed C consumed D bridges")

    frozen_recipe = {
        "schema": "autoformalization-population-recipe/v1",
        "arms": list(ARMS),
        "default_execution_status": "no_run",
        "default_result_kind": "no_run",
        "eligible_basis": {
            "corpus_manifest_sha256": harness.sha256_file(PAPER_ROOT / "data" / "corpus_manifest.json"),
            "count": 1913,
            "experiment_plan_sha256": harness.sha256_file(PAPER_ROOT / "config" / "experiment_plan.json"),
            "field": "natural_source_units",
            "manifest_path": "papers/completion/autoformalization/data/splits.json",
            "manifest_sha256": harness.sha256_file(PAPER_ROOT / "data" / "splits.json"),
            "private_final_ids_disclosed": False,
            "split": "final_test",
        },
        "notes": "Compact Table 6 unrun recipe. Individual final-test identities remain undisclosed.",
        "records": [],
    }
    tables = harness.regenerate_tables(frozen_recipe)
    if tables["tables_sha256"] != manifest["table6"]["unrun_tables_sha256"]:
        errors.append("Table 6 unrun accounting digest drifted")
    for arm in ARMS:
        accounted = tables["arms"][arm]
        if accounted["eligible"] != 1913 or accounted["coverage_statuses"]["no_run"] != 1913:
            errors.append(f"unrun denominator drifted for {arm}")
        fidelity = accounted["metrics"]["all_facet_source_fidelity"]
        if fidelity["value"] is not None or fidelity["numerator"] is not None:
            errors.append(f"unrun fidelity for {arm} is not null")
        native = accounted["metrics"]["native_checked_useful_proof_coverage"]
        if native["value"] is not None:
            errors.append(f"unrun native coverage for {arm} is not null")
        cost = accounted["metrics"]["total_cost"]
        if cost["status"] != "unrun" or cost["value"] is not None:
            errors.append(f"unrun cost for {arm} is not an unrun null")

    inspected = manifest.get("inspected_not_imported") or {}
    if any(item.get("imported") for item in inspected.values()):
        errors.append("inspected project sources were imported")

    if errors:
        print("AF-016 check_outputs: FAIL")
        for item in errors:
            print(" -", item)
        return 1
    print(json.dumps({
        "ok": True,
        "constructed_records": len(constructed),
        "selection_records": len(selection),
        "table6_cells": len(cells),
        "table6_statuses": sorted({cell["status"] for cell in cells}),
        "unrun_tables_sha256": tables["tables_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
