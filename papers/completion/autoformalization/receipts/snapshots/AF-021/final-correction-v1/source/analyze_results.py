#!/usr/bin/env python3
"""AF-021 analysis of frozen autoformalization evidence.

Regenerates Table 6 (A-E), Table 11 (T0-T5) and Table 13 from retained
run records and compact unrun accounting. Independent human agreement
and source-semantic fidelity stay unmeasured. Unrun/unavailable cells
are not measured zeros. Teacher/prover/reconstruction scores are not
original-source gold. Zero observed false transfers on a finite
constructed set is not universal soundness.

This script does not train models, call providers, open final-test
bodies, or invent confidence intervals for unmeasured populations.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

def find_repo_root(start: Path) -> Path:
    marker = Path("papers/completion/autoformalization/config/environment_manifest.json")
    for path in (start, *start.parents):
        if (path / marker).is_file():
            return path
    raise SystemExit("cannot locate repository root from analyze_results.py")


HERE = Path(__file__).resolve().parent
REPO_ROOT = find_repo_root(HERE)
PAPER_ROOT = REPO_ROOT / "papers/completion/autoformalization"
EVAL_DIR = PAPER_ROOT / "evaluation"
if str(EVAL_DIR) not in sys.path:
    sys.path.insert(0, str(EVAL_DIR))

import run_benchmark as harness  # noqa: E402

SCHEMA = "autoformalization-results-analysis/v1"
TASK_ID = "AF-021"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PIPELINE_ARMS = ("A", "B", "C", "D", "E")
TRAINING_ARMS = ("T0", "T1", "T2", "T3", "T4", "T5")
TABLE6_COLUMNS = (
    "sources_covered",
    "fidelity_uncertainty",
    "correct_transfers",
    "cost_latency",
)
TABLE11_COLUMNS = (
    "source_split_counts",
    "held_out_fidelity",
    "proof_route_benefit",
    "total_cost",
)
TABLE6_HEADINGS = {
    "sources_covered": "Sources / covered",
    "fidelity_uncertainty": "Fidelity / uncertainty",
    "correct_transfers": "Correct transfers",
    "cost_latency": "Cost / latency",
}
TABLE11_HEADINGS = {
    "source_split_counts": "Source/split counts",
    "held_out_fidelity": "Held-out fidelity",
    "proof_route_benefit": "Proof/route benefit",
    "total_cost": "Total cost",
}
REVISED_TABLE6_HEADINGS = {
    "sources_covered": "Coverage / abstention on eligible final-test natural units (unrun is not zero)",
    "fidelity_uncertainty": "Independent source-semantic fidelity / uncertainty (unmeasured; not prover or teacher agreement)",
    "correct_transfers": "Exact-goal native-checked useful proof / correct transfer (semantic false-transfer remains unmeasured)",
    "cost_latency": "Total measured cost / latency on the Table 6 population (unrun is not a zero-cost success)",
}
REVISED_TABLE11_HEADINGS = {
    "source_split_counts": "Frozen split inventory and executed development counts (final-test remains locked)",
    "held_out_fidelity": "Held-out independent source-semantic fidelity (unmeasured; not teacher cosine or reconstruction)",
    "proof_route_benefit": "Native-checked proof / route benefit on the Table 11 population",
    "total_cost": "Total measured cost on the Table 11 final-test population (unrun is not zero)",
}
FORBIDDEN_CELL_TOKENS = ("TBD", "[TBD]", "TODO", "[TODO]", "To complete")
CI_METHOD = (
    "95% source-family/time-group cluster bootstrap, 10000 resamples; "
    "seed summaries separate."
)
NATIVE_TOOLS = (
    "lean", "lake", "elan", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle",
)


def paper_root() -> Path:
    return PAPER_ROOT


def repo_root() -> Path:
    return REPO_ROOT


def results_dir() -> Path:
    return PAPER_ROOT / "results"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def sha256_obj(value: Any) -> str:
    return sha256_bytes(harness.canonical_dumps(value).encode("utf-8"))


def latex_escape(text: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in text)


def cluster_bootstrap_interval(
    group_values: Sequence[float],
    *,
    n_resamples: int = 10000,
    alpha: float = 0.05,
    seed: int = 104729,
) -> dict[str, Any]:
    """Prespecified group-cluster bootstrap. Empty input is not a zero interval."""
    method = CI_METHOD
    if not group_values:
        return {
            "status": "not_computed",
            "reason": "no measured group-level observations on the prespecified final-test population",
            "method": method,
            "n_groups": 0,
            "n_resamples": n_resamples,
            "alpha": alpha,
            "seed": seed,
            "low": None,
            "high": None,
            "point": None,
        }
    finite = [float(value) for value in group_values if isinstance(value, (int, float)) and math.isfinite(float(value))]
    if len(finite) != len(group_values):
        return {
            "status": "not_computed",
            "reason": "non-finite group values cannot enter the interval",
            "method": method,
            "n_groups": len(group_values),
            "n_resamples": n_resamples,
            "alpha": alpha,
            "seed": seed,
            "low": None,
            "high": None,
            "point": None,
        }
    rng = random.Random(seed)
    n = len(finite)
    stats: list[float] = []
    for _ in range(n_resamples):
        sample = [finite[rng.randrange(n)] for _ in range(n)]
        stats.append(sum(sample) / n)
    stats.sort()
    lo_index = int(math.floor((alpha / 2.0) * n_resamples))
    hi_index = min(n_resamples - 1, int(math.ceil((1.0 - alpha / 2.0) * n_resamples) - 1))
    point = sum(finite) / n
    return {
        "status": "computed",
        "reason": "cluster bootstrap over the supplied group means",
        "method": method,
        "n_groups": n,
        "n_resamples": n_resamples,
        "alpha": alpha,
        "seed": seed,
        "low": stats[lo_index],
        "high": stats[hi_index],
        "point": point,
    }


def require_scope(scope: Mapping[str, Any]) -> None:
    if scope.get("schema") != "af-automated-structural-evidence-scope/v1":
        raise SystemExit("structural_evidence_scope.json schema mismatch")
    if scope.get("human_fidelity_status") != "unmeasured_not_collected":
        raise SystemExit("human fidelity is not recorded as unmeasured")
    if scope.get("independent_human_semantic_labels_available") is not False:
        raise SystemExit("independent human labels must remain unavailable")
    if scope["denominator_policy"]["final_test_natural_units"] != 1913:
        raise SystemExit("final-test denominator drifted")
    if not scope["denominator_policy"]["unrun_is_not_zero"]:
        raise SystemExit("unrun-is-not-zero policy missing")
    if not scope["denominator_policy"]["unavailable_is_not_zero"]:
        raise SystemExit("unavailable-is-not-zero policy missing")


def split_counts(splits: Mapping[str, Any]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for name in ("train", "selection", "fixed_canary", "final_test"):
        block = splits["counts"][name]
        out[name] = {
            "natural_source_units": int(block["natural_source_units"]),
            "natural_source_records": int(block["natural_source_records"]),
            "operational_connected_components": int(block["operational_connected_components"]),
        }
    return out


def gold_inventory(path: Path) -> dict[str, Any]:
    rows = load_jsonl(path)
    valued = 0
    for row in rows:
        if row.get("label_status") not in {None, "pending_independent_review", "unmeasured"}:
            valued += 1
        facets = row.get("facets") or {}
        for facet in facets.values():
            if isinstance(facet, dict) and facet.get("values"):
                valued += 1
                break
    return {
        "prepared_blank_packets": len(rows),
        "gold_records_with_values": valued,
        "independent_gold_present": valued > 0,
        "zero_agreement_is_missing_record_inventory": True,
    }


def aggregate_training(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    aggregates = [row for row in rows if row.get("record_kind") == "aggregate"]
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in aggregates:
        by_arm[str(row.get("arm_id"))].append(dict(row))
    summary: dict[str, Any] = {}
    for arm, items in sorted(by_arm.items()):
        seed_rows = [row for row in items if row.get("seed") is not None]
        replay_rows = [row for row in items if row.get("replay") is not None and row.get("seed") is None]
        train = [row for row in items if row.get("split") == "train"]
        selection = [row for row in items if row.get("split") == "selection"]
        final_test = [row for row in items if row.get("split") == "final_test"]

        def cosine(subset: Sequence[Mapping[str, Any]]) -> list[float]:
            values: list[float] = []
            for row in subset:
                metrics = row.get("metrics") or {}
                value = metrics.get("vector_cosine")
                if isinstance(value, (int, float)) and math.isfinite(float(value)):
                    values.append(float(value))
            return values

        def fidelity(subset: Sequence[Mapping[str, Any]]) -> set[Any]:
            return {(row.get("metrics") or {}).get("source_fidelity") for row in subset}

        summary[arm] = {
            "aggregate_rows": len(items),
            "seeds": sorted({row.get("seed") for row in seed_rows if row.get("seed") is not None}),
            "replays": sorted({row.get("replay") for row in replay_rows if row.get("replay") is not None}),
            "claim_admissible": any(row.get("claim_admissible") is True for row in items),
            "embedding_models": sorted({str(row.get("embedding_model")) for row in items if row.get("embedding_model")}),
            "teacher_targets": sorted({(row.get("counts") or {}).get("teacher_targets") for row in items}),
            "update_counts": sorted({row.get("update_count") for row in items if "update_count" in row}),
            "train_vector_cosine": cosine(train),
            "selection_vector_cosine": cosine(selection),
            "final_test_rows": len(final_test),
            "source_fidelity_values": sorted(fidelity(items), key=lambda value: str(value)),
            "native_proof_values": sorted(
                {(row.get("metrics") or {}).get("native_proof_coverage") for row in items},
                key=lambda value: str(value),
            ),
        }
    return summary


def retrieval_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    observations = [row for row in rows if row.get("schema") == "autoformalization-retrieval-result/v1"]
    by_route: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in observations:
        if int(row.get("k") or 0) != 5:
            continue
        by_route[str(row.get("route_id"))].append(dict(row))
    routes: dict[str, Any] = {}
    for route, items in sorted(by_route.items()):
        recalls = [float((row.get("metrics") or {}).get("relevance_recall_at_k") or 0.0) for row in items]
        yields = [float((row.get("metrics") or {}).get("admitted_premise_yield_at_k") or 0.0) for row in items]
        routes[route] = {
            "n_queries": len(items),
            "mean_relevance_recall_at_5": (sum(recalls) / len(recalls)) if recalls else None,
            "mean_admitted_premise_yield_at_5": (sum(yields) / len(yields)) if yields else None,
            "constructed_control": True,
            "fills_table13_natural_cells": False,
        }
    docs = sorted({row.get("corpus_n_documents") for row in observations if row.get("corpus_n_documents") is not None})
    queries = sorted({row.get("query_n") for row in observations if row.get("query_n") is not None})
    return {
        "n_observation_rows": len(observations),
        "corpus_n_documents": docs[0] if len(docs) == 1 else docs,
        "query_n": queries[0] if len(queries) == 1 else queries,
        "routes_k5": routes,
        "fills_table13_natural_cells": False,
    }


def premise_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    observations = [row for row in rows if isinstance(row, dict)]
    kinds = Counter(str(row.get("schema") or row.get("kind") or "unknown") for row in observations)
    return {
        "n_rows": len(observations),
        "schemas": dict(kinds),
        "fills_table13_natural_cells": False,
        "hand_authored_selector_weights": True,
        "trained": False,
    }


def planning_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    observations = [row for row in rows if row.get("kind") != "summary"]
    summaries = [row for row in rows if row.get("kind") == "summary"]
    arms = Counter(str(row.get("experiment_arm") or row.get("arm_id")) for row in observations)
    proofs = [row for row in observations if row.get("counts_as_executed_proof") is True]
    return {
        "n_observation_rows": len(observations),
        "n_summary_rows": len(summaries),
        "arms": dict(arms),
        "executed_proofs": len(proofs),
        "fills_table13_natural_cells": False,
        "constructed_control": True,
    }


def assistance_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summaries = [row for row in rows if row.get("kind") == "summary"]
    observations = [row for row in rows if row.get("kind") != "summary"]
    native = [row for row in observations if row.get("counts_as_native_checked_proof") is True]
    payload = summaries[0] if summaries else {}
    return {
        "n_observation_rows": len(observations),
        "n_summary_rows": len(summaries),
        "candidate_rate": payload.get("candidate_rate"),
        "accepted_proof_rate": payload.get("accepted_proof_rate"),
        "failure_categories": payload.get("failure_categories"),
        "claim_narrowing": payload.get("claim_narrowing") or [],
        "native_checked_proofs": len(native),
        "fills_table13_natural_cells": False,
        "constructed_control": True,
    }


def selection_structural(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    selection = [row for row in rows if row.get("split") == "selection"]
    constructed = [row for row in rows if row.get("constructed_control")]
    final_test = [row for row in rows if row.get("split") == "final_test"]
    by_arm: dict[str, Counter[str]] = defaultdict(Counter)
    for row in selection:
        by_arm[str(row.get("experiment_arm"))][str(row.get("execution_status"))] += 1
    false_transfers = [
        row for row in rows
        if (row.get("proof") or {}).get("false_transfer") is True
    ]
    useful = [
        row for row in rows
        if (row.get("proof") or {}).get("useful") is True
    ]
    native = [row for row in rows if row.get("result_kind") == "native_checked_proof"]
    return {
        "selection_records": len(selection),
        "constructed_control_records": len(constructed),
        "final_test_records": len(final_test),
        "selection_status_by_arm": {arm: dict(counts) for arm, counts in sorted(by_arm.items())},
        "false_transfer_true_count": len(false_transfers),
        "useful_true_count": len(useful),
        "native_checked_proof_count": len(native),
        "not_table6": True,
    }


def cost_human_review(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    measured = 0
    unmeasured = 0
    zeros = 0
    for row in rows:
        cell = row.get("human_review_seconds")
        if isinstance(cell, dict):
            if cell.get("kind") == "unmeasured" or cell.get("value") is None:
                unmeasured += 1
            elif cell.get("value") == 0.0:
                zeros += 1
            else:
                measured += 1
        elif cell == 0.0:
            zeros += 1
        elif cell is None:
            unmeasured += 1
    return {
        "measured_review_rows": measured,
        "unmeasured_review_rows": unmeasured,
        "zero_placeholders_not_used_as_review_time": zeros,
        "table_value": None,
        "table_status": "unmeasured",
        "note": "Human-review seconds remain unmeasured. A recorded 0.0 on a sealed probe is not timed independent review.",
    }


def native_training_notes(manifest: Mapping[str, Any], scalars: Mapping[str, Any]) -> dict[str, Any]:
    arms = manifest["arms"]; aggregates = scalars["aggregates"]
    packed = arms["T2"]["packed_cpu"]; attempts = scalars["t3_attempts"]
    seeds = [104729, 130363, 155921]
    if [r["seed"] for r in packed] != seeds or [r["seed"] for r in attempts] != seeds:
        raise ValueError("Actual native seed population differs")
    if not all(r["accepted_epochs"] == 1 and r["applied_packed_updates"] == 5 and r["parameter_changed"] for r in packed):
        raise ValueError("Actual native update evidence differs")
    if not all(r["detail"]["protected_parameters_unchanged"] and r["detail"]["feedback_scope"] == "native_compiler_structural_contracts_only" for r in attempts):
        raise ValueError("Actual T3 scope/isolation differs")
    return {
        "dataset_id": manifest["dataset_id"], "config_id": manifest["config_id"],
        "executed_arms": sorted(k for k,v in arms.items() if isinstance(v,dict) and v.get("executed")),
        "t2_packed_cpu_reports": len(packed), "t2_parameter_changed": True,
        "aggregate_rows":len(aggregates), "claim_admissible":False,
        "claim_admissible_scope":"original primary final-test/fidelity flag only; actual training execution is independently retained and byte-qualified",
        "saved_training_completed":scalars["saved_training_completed"],
        "original_container_success":scalars["original_container_success"],
        "separate_retained_byte_checker_succeeded":scalars["separate_retained_byte_checker_succeeded"],
        "t2_by_seed":[{"seed":r["seed"],"accepted_epochs":r["accepted_epochs"],"applied_packed_updates":r["applied_packed_updates"],"changed_numeric_parameters":r["shared_parameter_change"]["changed_numeric_parameter_count"]} for r in packed],
        "t3_by_seed":[{"seed":r["seed"],"eligible_structural_labels":r["detail"]["eligible_count"],"applied_updates":r["detail"]["applied_count"],"protected_parameters_unchanged":r["detail"]["protected_parameters_unchanged"],"training_calibration_diagnostic":r["metrics"]["calibration_error"]} for r in attempts],
        "metric_limit":"T2 cosine=1/MSE=0 is target-assisted projection, not source-free reconstruction or generalization; family CE is unchanged from T0. T3 labels are compiler-structural contracts, not independent semantic gold.",
        "fills_table11_held_out_fidelity":False,
        "population":"AF-004 train 69 + selection 15; final-test locked",
    }


def cell(
    *,
    table: str,
    arm: str,
    column: str,
    original_heading: str,
    revised_heading: str,
    status: str,
    display: str,
    definition: str,
    narrowed_claim: str,
    backing: str,
    blockers: list[str],
    denominator: int | None,
    numerator: int | float | None,
    value: Any,
    population: str,
    interval: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "table": table,
        "arm": arm,
        "column": column,
        "cell_id": f"{arm}:{column}",
        "original_heading": original_heading,
        "revised_heading": revised_heading,
        "status": status,
        "display": display,
        "definition": definition,
        "narrowed_claim": narrowed_claim,
        "backing": backing,
        "blockers": blockers,
        "denominator": denominator,
        "numerator": numerator,
        "value": value,
        "population": population,
        "interval": dict(interval or cluster_bootstrap_interval([])),
        "replaces_original_placeholder": True,
    }
    blob = json.dumps(payload, sort_keys=True)
    for token in FORBIDDEN_CELL_TOKENS:
        if token in blob:
            raise SystemExit(f"forbidden token {token} entered cell {payload['cell_id']}")
    if status in {"unrun", "unavailable", "unmeasured"} and value is not None:
        raise SystemExit(f"{payload['cell_id']} inserted a numeric value under {status}")
    if column in {"fidelity_uncertainty", "held_out_fidelity"} and status != "unmeasured":
        raise SystemExit(f"{payload['cell_id']} fidelity cell is not unmeasured")
    return payload


def build_table6(ctx: Mapping[str, Any]) -> list[dict[str, Any]]:
    tables = ctx["unrun_tables"]
    interval = cluster_bootstrap_interval([])
    cells: list[dict[str, Any]] = []
    extra_blockers = {
        "A": ["direct-model credential absent on sealed PATH", "native Lean/Z3/CVC5 absent from sealed PATH"],
        "B": ["native Lean/Z3/CVC5 absent from sealed PATH"],
        "C": ["native Lean/Z3/CVC5 absent from sealed PATH"],
        "D": ["native Lean/Z3/CVC5 absent from sealed PATH"],
        "E": ["T4 unactivated; e_locked; learned features not applied", "native Lean/Z3/CVC5 absent from sealed PATH"],
    }
    for arm in PIPELINE_ARMS:
        accounted = tables["arms"][arm]
        coverage = accounted["metrics"]["coverage"]
        fidelity = accounted["metrics"]["all_facet_source_fidelity"]
        native = accounted["metrics"]["native_checked_useful_proof_coverage"]
        cost = accounted["metrics"]["total_cost"]
        cells.append(cell(
            table="6",
            arm=arm,
            column="sources_covered",
            original_heading=TABLE6_HEADINGS["sources_covered"],
            revised_heading=REVISED_TABLE6_HEADINGS["sources_covered"],
            status="unrun",
            display="unrun 0/1913 measured (not a zero-score success)",
            definition=(
                "Count of eligible final-test natural source units with execution_status=measured, "
                "divided by 1913. Unavailable, unsupported, abstained, timeout, invalid, failure, "
                "partial, and no_run remain in the denominator and are not scored as zero coverage."
            ),
            narrowed_claim=(
                "No Table 6 coverage claim. Final-test identities remain locked. Selection-split "
                f"structural counts ({ctx['selection_structural']['selection_status_by_arm'].get(arm, {})}) "
                "are a separate non-Table-6 diagnostic."
            ),
            backing="AF-007 compact unrun recipe over splits.json counts.final_test.natural_source_units=1913",
            blockers=extra_blockers[arm] + ["final_test_locked"],
            denominator=coverage["denominator"],
            numerator=None,
            value=None,
            population="final_test.natural_source_units",
            interval=interval,
        ))
        cells.append(cell(
            table="6",
            arm=arm,
            column="fidelity_uncertainty",
            original_heading=TABLE6_HEADINGS["fidelity_uncertainty"],
            revised_heading=REVISED_TABLE6_HEADINGS["fidelity_uncertainty"],
            status="unmeasured",
            display="unmeasured (no independent gold; not a 0% or 0.0 interval)",
            definition=(
                "All-facet independent source-semantic fidelity requires independent gold and a "
                "definite judgment on every eligible unit. Primary numerator is null until that "
                "population is complete. Uncertainty is not imputed from missing labels."
            ),
            narrowed_claim=(
                "Independent human agreement and source-semantic fidelity are unmeasured. Parse, "
                "elaboration, teacher agreement, reconstruction, and prover success are not this "
                "cell and are not original-source gold."
            ),
            backing="AF-005 gold_facets remain pending_independent_review; AF-028 human_fidelity_status=unmeasured_not_collected",
            blockers=["independent_human_semantic_labels_available=false"],
            denominator=fidelity["denominator"],
            numerator=None,
            value=None,
            population="final_test.natural_source_units",
            interval=interval,
        ))
        cells.append(cell(
            table="6",
            arm=arm,
            column="correct_transfers",
            original_heading=TABLE6_HEADINGS["correct_transfers"],
            revised_heading=REVISED_TABLE6_HEADINGS["correct_transfers"],
            status="unavailable",
            display="unavailable (no native checker on sealed PATH; not 0/1913 soundness)",
            definition=(
                "Native-checked useful-proof coverage requires result_kind=native_checked_proof, "
                "proof.useful=true, checker_class=native, and receipt_sha256 naming the same "
                "source/goal/premise/checker identities as the candidate. Semantic false-transfer "
                "is a separate unmeasured quantity."
            ),
            narrowed_claim=(
                "No Table 6 correct-transfer or native useful-proof claim. Sealed PATH has no "
                "Lean/Z3/CVC5. Constructed Q1 finite witnesses are labeled constructed_control and "
                "do not fill this cell. Zero observed false transfers on that finite set is not "
                "universal soundness."
            ),
            backing="sealed-PATH binary probe plus compact 1913-unit no_run recipe",
            blockers=extra_blockers[arm],
            denominator=native["denominator"],
            numerator=None,
            value=None,
            population="final_test.natural_source_units",
            interval=interval,
        ))
        cells.append(cell(
            table="6",
            arm=arm,
            column="cost_latency",
            original_heading=TABLE6_HEADINGS["cost_latency"],
            revised_heading=REVISED_TABLE6_HEADINGS["cost_latency"],
            status="unrun",
            display="unrun (final-test not executed; not 0 s; human review unmeasured)",
            definition=(
                "Sum of observed elapsed/cpu/gpu/provider/human-review costs over the 1913-unit "
                "final-test population, including failed and unrun attempts attributed to that "
                "population. A deterministically emitted formula does not have zero total cost. "
                "Human-review seconds stay unmeasured, not 0.0."
            ),
            narrowed_claim=(
                "No Table 6 cost/latency figure. Final-test was not executed, so the cell is unrun "
                "rather than 0. AF-020 retained historical costs and AF-016 selection elapsed times "
                "are not this cell."
            ),
            backing="compact unrun recipe total_cost.status=unrun with retained_cost_records=0",
            blockers=["final_test_locked"],
            denominator=cost["denominator"],
            numerator=None,
            value=None,
            population="final_test.natural_source_units",
            interval=interval,
        ))
        if accounted["coverage_statuses"]["no_run"] != 1913:
            raise SystemExit(f"arm {arm} no_run count drifted")
    return cells


def build_table11(ctx: Mapping[str, Any]) -> list[dict[str, Any]]:
    tables = ctx["unrun_tables"]
    counts = ctx["split_counts"]
    interval = cluster_bootstrap_interval([])
    train_n = counts["train"]["natural_source_units"]
    sel_n = counts["selection"]["natural_source_units"]
    canary_n = counts["fixed_canary"]["natural_source_units"]
    final_n = counts["final_test"]["natural_source_units"]
    inventory_display = (
        f"train {train_n} / selection {sel_n} / canary {canary_n} / "
        f"final-test {final_n} locked"
    )
    t0t2_note = {
        "T0": "AF-011/AF-029 T0 codec ran on train/selection only; 3 deterministic replays; update_count=0.",
        "T1": "AF-011/AF-029 T1 sample-memory ran on train/selection only; seeds 104729/130363/155921; memorization diagnostic, not generalization.",
        "T2": "AF-029 completed three actual T2 seeds, one accepted epoch and five packed updates per seed. Earlier AF-011 zero-update attempts remain historical; no final-test or fidelity claim follows.",
        "T3": "AF-029 applied 256 compiler-structural feedback updates from 2606 eligible labels per seed; three matched T2-to-T3 reloads completed. Final-test route benefit remains unrun.",
        "T4": "AF-013 T4 unactivated/unavailable; e_locked; export identity is not applied learned guidance.",
        "T5": "AF-014 T5 accepted compiler-contract repair on constructed witnesses; unseen fidelity and native coverage remain unrun.",
    }
    proof_status = {
        "T0": "unrun",
        "T1": "unrun",
        "T2": "unrun",
        "T3": "unrun",
        "T4": "unavailable",
        "T5": "unrun",
    }
    proof_display = {
        "T0": "unrun on 1913 final-test units; teacher diagnostics are not route benefit",
        "T1": "unrun on 1913; T1 is a memorization diagnostic, not proof/route benefit",
        "T2": "unrun on 1913; no shared-learner native-proof gain is admitted",
        "T3": "unrun on 1913; 256 structural-feedback updates per seed are not final route benefit",
        "T4": "unavailable (T4 unactivated; consumer load is not applied learning)",
        "T5": "unrun (no measured held-out improvement; constructed compile is not this cell)",
    }
    cells: list[dict[str, Any]] = []
    for arm in TRAINING_ARMS:
        accounted = tables["arms"][arm]
        fidelity = accounted["metrics"]["all_facet_source_fidelity"]
        native = accounted["metrics"]["native_checked_useful_proof_coverage"]
        cost = accounted["metrics"]["total_cost"]
        cells.append(cell(
            table="11",
            arm=arm,
            column="source_split_counts",
            original_heading=TABLE11_HEADINGS["source_split_counts"],
            revised_heading=REVISED_TABLE11_HEADINGS["source_split_counts"],
            status="measured_inventory",
            display=inventory_display,
            definition=(
                "Frozen AF-004 split inventory: train/selection/fixed-canary/final-test natural "
                "source units and operational groups. Executed development diagnostics used only "
                "train 69 plus selection 15. Final-test 1913 remains locked."
            ),
            narrowed_claim=(
                f"{t0t2_note[arm]} Split counts are inventory, not held-out performance."
            ),
            backing="data/splits.json SHA-256 " + ctx["provenance"]["splits_sha256"],
            blockers=["final_test_locked"] if arm in {"T0", "T1", "T2", "T3", "T4", "T5"} else [],
            denominator=final_n,
            numerator=train_n + sel_n + canary_n,
            value={
                "train": train_n,
                "selection": sel_n,
                "fixed_canary": canary_n,
                "final_test": final_n,
                "final_test_groups": counts["final_test"]["operational_connected_components"],
            },
            population="af004_split_inventory",
            interval=interval,
        ))
        cells.append(cell(
            table="11",
            arm=arm,
            column="held_out_fidelity",
            original_heading=TABLE11_HEADINGS["held_out_fidelity"],
            revised_heading=REVISED_TABLE11_HEADINGS["held_out_fidelity"],
            status="unmeasured",
            display="unmeasured (independent gold absent; teacher cosine is not this cell)",
            definition=(
                "Held-out all-facet independent source-semantic fidelity on the 1913-unit "
                "final-test population. Teacher vector cosine, family CE, reconstruction, and "
                "checker success are incompatible denominators and are not this metric."
            ),
            narrowed_claim=(
                "No Table 11 held-out fidelity claim. AF-011 mock:stable-sha256 and AF-029 "
                "MiniLM teacher diagnostics remain claim_admissible=false and do not fill this cell."
            ),
            backing="AF-005/AF-028 unmeasured human fidelity; AF-007 unrun all_facet_source_fidelity",
            blockers=["independent_human_semantic_labels_available=false", "final_test_locked"],
            denominator=fidelity["denominator"],
            numerator=None,
            value=None,
            population="final_test.natural_source_units",
            interval=interval,
        ))
        cells.append(cell(
            table="11",
            arm=arm,
            column="proof_route_benefit",
            original_heading=TABLE11_HEADINGS["proof_route_benefit"],
            revised_heading=REVISED_TABLE11_HEADINGS["proof_route_benefit"],
            status=proof_status[arm],
            display=proof_display[arm],
            definition=(
                "Native-checked useful-proof coverage or isolated route-value on the 1913-unit "
                "final-test population, with the same checker identity as the candidate. "
                "Predicted proof success is not certification."
            ),
            narrowed_claim=t0t2_note[arm] + " This cell is not filled from constructed isolation probes.",
            backing="AF-007 unrun native_checked_useful_proof_coverage plus AF-012/013/014 receipts",
            blockers=["native checkers unavailable on sealed PATH", "final_test_locked"],
            denominator=native["denominator"],
            numerator=None,
            value=None,
            population="final_test.natural_source_units",
            interval=interval,
        ))
        cells.append(cell(
            table="11",
            arm=arm,
            column="total_cost",
            original_heading=TABLE11_HEADINGS["total_cost"],
            revised_heading=REVISED_TABLE11_HEADINGS["total_cost"],
            status="unrun",
            display="unrun on 1913 final-test units (AF-011/AF-020/AF-029 costs are not this cell)",
            definition=(
                "Total observed cost on the Table 11 final-test population, including failed "
                "attempts. Human-review seconds remain unmeasured. GPU seconds are unmeasured "
                "when CUDA training was not executed, not a measured 0.0."
            ),
            narrowed_claim=(
                "No Table 11 total-cost figure for the locked final-test set. AF-020 retained "
                "historical phase costs and AF-029 failed encoder-preparation attempts are "
                "reported separately without double counting."
            ),
            backing="AF-007 total_cost.status=unrun; AF-020/AF-029 retained separately",
            blockers=["final_test_locked"],
            denominator=cost["denominator"],
            numerator=None,
            value=None,
            population="final_test.natural_source_units",
            interval=interval,
        ))
    return cells


def build_table13(ctx: Mapping[str, Any]) -> list[dict[str, Any]]:
    retrieval = ctx["retrieval"]
    assistance = ctx["assistance"]
    planning = ctx["planning"]
    rows = [
        {
            "row_id": "lexical_vector_graph",
            "comparison": "Lexical / vector / graph",
            "controlled_variable": "Same constructed corpus, queries, target interpretation and budget",
            "required_outcome": "Independently judged relevant context and accepted-premise yield",
            "status": "constructed_automatic_labels_only",
            "display": (
                f"constructed {retrieval['corpus_n_documents']} docs x {retrieval['query_n']} queries; "
                "FAISS/MiniLM unavailable; automatic citation labels; does not fill natural cells"
            ),
            "value": retrieval["routes_k5"],
            "narrowed_claim": (
                "AF-017 completed retrieval diagnostics may be reused only within automatic-label/"
                "structural scope. Independently judged natural relevance is unmeasured. FAISS-library "
                "and MiniLM encoder quality are unavailable, not zero."
            ),
            "fills_natural_table13": False,
            "prespecified": True,
        },
        {
            "row_id": "baseline_graph_selector",
            "comparison": "Baseline / graph selector",
            "controlled_variable": "Same goal and candidate corpus",
            "required_outcome": "Recall against stated labels; proxy status; actual useful proof coverage",
            "status": "constructed_hand_authored_weights",
            "display": (
                "hand-authored weights trained=false; proxy import-overlap is a separate metric; "
                "useful native-proof coverage unavailable"
            ),
            "value": ctx["premise"],
            "narrowed_claim": (
                "Selector weights are disclosed as hand-authored with no independent train/split. "
                "Proxy overlap is not usefulness gold. Native useful-proof coverage is unavailable."
            ),
            "fills_natural_table13": False,
            "prespecified": True,
        },
        {
            "row_id": "unguided_guided_plan",
            "comparison": "Unguided / guided plan",
            "controlled_variable": "Same admitted sources and route budget",
            "required_outcome": "Deterministic replay, subgoal coverage, abstention and total cost",
            "status": "constructed_replay",
            "display": (
                f"{planning['n_observation_rows']} constructed planning observations; "
                f"executed_proofs={planning['executed_proofs']}; LLM nomination unavailable"
            ),
            "value": planning,
            "narrowed_claim": (
                "Plans replay deterministically and never count as executed proofs. Guided ranker "
                "digest is a disclosed hand-authored reorder, not a model call."
            ),
            "fills_natural_table13": False,
            "prespecified": True,
        },
        {
            "row_id": "hammer_leanstral",
            "comparison": "Hammer / Leanstral assistance",
            "controlled_variable": "Same source goal, native checker and resource envelope",
            "required_outcome": "Candidate rate, reconstruction acceptance, unsupported and timeout rates",
            "status": "unavailable",
            "display": (
                "sealed-PATH Lean, Z3, CVC5, Vampire, E, Coq, Isabelle unavailable; "
                f"native_checked_proofs={assistance['native_checked_proofs']}; "
                "sorry/admit rejected before any kernel claim"
            ),
            "value": None,
            "numerator": None,
            "narrowed_claim": (
                "Hammer solver portfolio, Leanstral model service, and native reconstruction are "
                "unavailable. Candidate rates 0/5 are unavailability, not measured solver failure "
                "as a success table. Constructed rates do not fill natural Table 13 cells."
            ),
            "fills_natural_table13": False,
            "prespecified": True,
            "blockers": list(NATIVE_TOOLS),
        },
        {
            "row_id": "proof_heads_off_on",
            "comparison": "Proof heads off / on",
            "controlled_variable": "Same representation checkpoint and isolated update policy",
            "required_outcome": "Calibration, route value, protected-objective invariance",
            "status": "unavailable",
            "display": "T3 applied 256 structural-feedback updates per seed; held-out calibration and route benefit unrun",
            "value": None,
            "narrowed_claim": (
                "AF-012 calibration_error, route_value, and native coverage are null because "
                "eligible_native_label_count=0. Isolation-probe head metrics are appendix constructed "
                "controls; AF-029 actual updates preserve protected parameters. Train feedback is not held-out route efficacy."
            ),
            "fills_natural_table13": False,
            "prespecified": True,
        },
        {
            "row_id": "guidance_off_promoted",
            "comparison": "Guidance off / promoted",
            "controlled_variable": "Same compiler profile and frozen source families",
            "required_outcome": "Actual consumer activation, independent source fidelity, regressions",
            "status": "unavailable",
            "display": "T4 unactivated/unavailable; e_locked; matching ingestion digest is not applied learning",
            "value": None,
            "narrowed_claim": (
                "Export alone earns no downstream credit. Independent source fidelity remains "
                "unmeasured. Arm E stays gated to AF-013 canary/consumer/rollback identities."
            ),
            "fills_natural_table13": False,
            "prespecified": True,
        },
    ]
    for row in rows:
        row["replaces_original_placeholder"] = False
        row["population"] = "constructed_or_unavailable_not_final_test"
        row["denominator_natural"] = 1913
        row["interval"] = cluster_bootstrap_interval([])
        blob = json.dumps(row, sort_keys=True)
        for token in FORBIDDEN_CELL_TOKENS:
            if token in blob:
                raise SystemExit(f"forbidden token {token} entered Table 13 row {row['row_id']}")
        if row.get("status") == "unavailable" and row.get("value") is not None:
            raise SystemExit(f"Table 13 row {row['row_id']} inserted a numeric unavailable value")
    return rows


def build_hypotheses(ctx: Mapping[str, Any]) -> list[dict[str, Any]]:
    claims = ctx["claim_map"]["claims"]
    training = ctx["training_aggregates"]
    t1 = training.get("T1") or {}
    t2 = training.get("T2") or {}
    t1_train = t1.get("train_vector_cosine") or []
    t1_sel = t1.get("selection_vector_cosine") or []
    t1_supported_diagnostic = bool(t1_train and t1_sel and min(t1_train) > max(t1_sel))
    hypotheses = []
    status_for = {
        "C1": "unrun",
        "C2": "unrun",
        "C3": "unrun",
        "C4": "unrun",
        "C5": "unrun",
        "C6": "unrun",
        "C7": "inconclusive",
    }
    rationale = {
        "C1": (
            "Independently adjudicated source-facet fidelity was not collected. Final-test 1913 "
            "units remain no_run. Teacher/prover/reconstruction scores are not this claim."
        ),
        "C2": (
            "Native-checked useful-proof coverage on natural held-out sources is unavailable. "
            "Constructed Q1 transfer and solver-local encodings are not this claim. Zero observed "
            "false transfers on a finite constructed set is not universal soundness."
        ),
        "C3": (
            "No held-out all-facet fidelity exists. Actual AF-029 T2 completed all three seeds. "
            "AF-029 packed_cpu updates are measured train/selection execution "
            "and do not support unseen source-family generalization."
        ),
        "C4": (
            "Actual AF-029 T3 applied 256 compiler-structural feedback updates per seed. Earlier AF-012 isolation "
            "probes remain constructed history. Protected parameters were preserved, but source fidelity remains unmeasured."
        ),
        "C5": (
            "AF-013 reports T4 unactivated/unavailable with e_locked. Export identity is not applied "
            "learned guidance. Independent source fidelity is unmeasured."
        ),
        "C6": (
            "AF-014 records T5-NO-MEASURED-IMPROVEMENT as no_run. The accepted exception-scoping "
            "compiler contract on constructed witnesses is not held-out fidelity or native coverage."
        ),
        "C7": (
            "AF-017/AF-018 provide constructed automatic-label/structural diagnostics only. Natural "
            "Table 13 cells remain unrun/unavailable. Hand-authored weights and proxy labels are "
            "disclosed; they were not represented as prespecified natural utility results."
        ),
    }
    for claim in claims:
        hid = claim["id"]
        hypotheses.append({
            "id": hid,
            "claim": claim["claim"],
            "status": status_for[hid],
            "prespecified": True,
            "exploratory": False,
            "primary_metrics": claim["primary_metrics"],
            "experiments": claim["experiments"],
            "controls": claim["controls"],
            "narrowing_rule": claim["narrowing_rule"],
            "rationale": rationale[hid],
            "human_dependent": hid in {"C1", "C3", "C4", "C5", "C6"} or "fidelity" in " ".join(claim["primary_metrics"]),
        })
    hypotheses.append({
        "id": "H-T1-memory-diagnostic",
        "claim": "Apparent T1 gain on seen sources is a sample-memory diagnostic rather than unseen generalization.",
        "status": "supported" if t1_supported_diagnostic else "inconclusive",
        "prespecified": True,
        "exploratory": False,
        "primary_metrics": ["seen-source teacher cosine", "selection teacher cosine"],
        "experiments": ["T1", "T2"],
        "controls": ["T1_vs_T2"],
        "narrowing_rule": "T1 is a memorization diagnostic; teacher cosine is not source-facet fidelity.",
        "rationale": (
            f"AF-011 T1 train vector-cosine values {t1_train} versus selection {t1_sel} on "
            "mock:stable-sha256 embeddings. This supports the prespecified memorization diagnostic "
            "only. It does not fill Table 11 held-out fidelity and is claim_admissible=false."
        ),
        "human_dependent": False,
        "claim_admissible_for_paper_primary": False,
    })
    hypotheses.append({
        "id": "H-T2-shared-learner",
        "claim": "Shared-parameter learning generalizes to unseen source-family/time groups.",
        "status": "unsupported",
        "prespecified": True,
        "exploratory": False,
        "primary_metrics": ["unseen all-facet fidelity"],
        "experiments": ["T0", "T2"],
        "controls": ["T2_vs_T0"],
        "narrowing_rule": "Actual trained checkpoints do not substitute for unperformed final-test source-fidelity measurement.",
        "rationale": (
            f"AF-011 T2 update_counts={t2.get('update_counts')} with claim_admissible="
            f"{t2.get('claim_admissible')}. Earlier no-update history is retained separately from the later successful native training. "
            "AF-029 packed_cpu parameter changes are not relabeled as this prespecified held-out test."
        ),
        "human_dependent": True,
        "claim_admissible_for_paper_primary": False,
    })
    return hypotheses


def render_table6(cells: Sequence[Mapping[str, Any]]) -> str:
    by_arm = {arm: {} for arm in PIPELINE_ARMS}
    for item in cells:
        by_arm[item["arm"]][item["column"]] = item
    lines = [
        "% AF-021 regenerated Table 6. All 20 original placeholder cells replaced.",
        "% Population: final_test.natural_source_units = 1913. Unrun/unavailable are not measured zeros.",
        "% Independent source-semantic fidelity is unmeasured and is not prover or teacher agreement.",
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{Matched A--E pipeline comparison on the locked 1913-unit final-test population. "
        "Unrun and unavailable are not measured zeros. Independent source-semantic fidelity is unmeasured.}",
        "\\label{tab:pipeline-results}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{lp{0.22\\linewidth}p{0.24\\linewidth}p{0.24\\linewidth}p{0.22\\linewidth}}",
        "\\hline",
        "Arm & Coverage / abstention & Independent fidelity / uncertainty & "
        "Native-checked useful proof / transfer & Total cost / latency \\\\",
        "\\hline",
    ]
    for arm in PIPELINE_ARMS:
        row = by_arm[arm]
        lines.append(
            f"{arm} & {latex_escape(row['sources_covered']['display'])} & "
            f"{latex_escape(row['fidelity_uncertainty']['display'])} & "
            f"{latex_escape(row['correct_transfers']['display'])} & "
            f"{latex_escape(row['cost_latency']['display'])} \\\\"
        )
    lines.extend([
        "\\hline",
        "\\end{tabular}}",
        "\\end{table}",
        "",
    ])
    text = "\n".join(lines)
    if "TBD" in text:
        raise SystemExit("Table 6 still contains TBD")
    return text


def render_table11(cells: Sequence[Mapping[str, Any]]) -> str:
    by_arm = {arm: {} for arm in TRAINING_ARMS}
    for item in cells:
        by_arm[item["arm"]][item["column"]] = item
    lines = [
        "% AF-021 regenerated Table 11. All 24 original placeholder cells replaced.",
        "% Held-out fidelity remains unmeasured. Teacher cosine/reconstruction do not fill that column.",
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{T0--T5 learning comparisons. Split counts are frozen inventory. Held-out independent "
        "fidelity is unmeasured. Proof/route benefit and final-test cost remain unrun or unavailable.}",
        "\\label{tab:training-results}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{lp{0.22\\linewidth}p{0.24\\linewidth}p{0.24\\linewidth}p{0.22\\linewidth}}",
        "\\hline",
        "Arm & Source/split counts & Held-out fidelity & Proof/route benefit & Total cost \\\\",
        "\\hline",
    ]
    for arm in TRAINING_ARMS:
        row = by_arm[arm]
        lines.append(
            f"{arm} & {latex_escape(row['source_split_counts']['display'])} & "
            f"{latex_escape(row['held_out_fidelity']['display'])} & "
            f"{latex_escape(row['proof_route_benefit']['display'])} & "
            f"{latex_escape(row['total_cost']['display'])} \\\\"
        )
    lines.extend([
        "\\hline",
        "\\end{tabular}}",
        "\\end{table}",
        "",
    ])
    text = "\n".join(lines)
    if "TBD" in text:
        raise SystemExit("Table 11 still contains TBD")
    return text


def render_table13(rows: Sequence[Mapping[str, Any]]) -> str:
    lines = [
        "% AF-021 regenerated Table 13. Constructed/automatic-label diagnostics are labeled as such.",
        "% Natural held-out Table 13 cells remain unrun or unavailable.",
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        "\\caption{Retrieval, planning, and proof-assistance comparisons. Constructed automatic-label "
        "diagnostics do not fill natural held-out cells. Unavailable native checkers are not measured zeros.}",
        "\\label{tab:assistance-results}",
        "\\resizebox{\\linewidth}{!}{%",
        "\\begin{tabular}{p{0.18\\linewidth}p{0.22\\linewidth}p{0.22\\linewidth}p{0.32\\linewidth}}",
        "\\hline",
        "Comparison & Controlled variable & Required outcome & Audited result / status \\\\",
        "\\hline",
    ]
    for row in rows:
        lines.append(
            f"{latex_escape(row['comparison'])} & {latex_escape(row['controlled_variable'])} & "
            f"{latex_escape(row['required_outcome'])} & {latex_escape(row['display'])} \\\\"
        )
    lines.extend([
        "\\hline",
        "\\end{tabular}}",
        "\\end{table}",
        "",
    ])
    text = "\n".join(lines)
    if "TBD" in text:
        raise SystemExit("Table 13 still contains TBD")
    return text


def render_hypothesis_report(ctx: Mapping[str, Any], hypotheses: Sequence[Mapping[str, Any]]) -> str:
    counts = Counter(item["status"] for item in hypotheses)
    lines = [
        "# AF-021 hypothesis report",
        "",
        "Prespecified claims from `evidence/claim_task_map.json` (AF-002/v1 freeze) and the AF-028/v1",
        "reporting amendment. Statuses are `supported`, `unsupported`, `inconclusive`, or `unrun`.",
        "Human-dependent hypotheses stay outside supported paper conclusions. Exploratory diagnostics",
        "are labeled as such and are not represented as prespecified natural held-out tests.",
        "",
        f"- Analysis identity: `{ctx['analysis_id']}`",
        f"- CI method (prespecified, not computed on the unrun final-test population): {CI_METHOD}",
        f"- Seeds: {ctx['seeds']}",
        f"- Grouping: {ctx['split_counts']['final_test']['operational_connected_components']} source-family/time groups on 1913 final-test units",
        f"- Hypothesis statuses: {dict(counts)}",
        "",
        "## Guardrails",
        "",
        "- Independent human agreement and source-semantic fidelity are unmeasured, not zeros.",
        "- Unrun and unavailable are not measured zeros.",
        "- Teacher agreement, reconstruction, and prover success are not original-source gold.",
        "- Zero observed false transfers is not generalized to universal soundness.",
        "- Negative and inconclusive results are retained.",
        "- Post-hoc test selection is not represented as prespecified.",
        "",
        "## Prespecified primary claims",
        "",
    ]
    for item in hypotheses:
        if item["id"].startswith("H-"):
            continue
        lines.extend([
            f"### {item['id']}: {item['status']}",
            "",
            f"**Claim.** {item['claim']}",
            "",
            f"- Prespecified: {item['prespecified']}",
            f"- Experiments: {', '.join(item['experiments'])}",
            f"- Controls: {', '.join(item['controls'])}",
            f"- Metrics: {', '.join(item['primary_metrics'])}",
            f"- Human-dependent: {item['human_dependent']}",
            "",
            item["rationale"],
            "",
            f"*Narrowing rule (frozen):* {item['narrowing_rule']}",
            "",
        ])
    lines.extend([
        "## Prespecified learning diagnostics (not Table 11 fidelity)",
        "",
    ])
    for item in hypotheses:
        if not item["id"].startswith("H-"):
            continue
        lines.extend([
            f"### {item['id']}: {item['status']}",
            "",
            f"**Claim.** {item['claim']}",
            "",
            item["rationale"],
            "",
            "This diagnostic is not a post-hoc substitute for held-out source-facet fidelity.",
            "",
        ])
    lines.extend([
        "## Per-family / facet / domain accounting",
        "",
        "Final-test natural units by domain (all unrun for Tables 6/11/13 primary metrics):",
        "",
    ])
    for domain, count in sorted((ctx["splits"]["counts"]["final_test"]["by_domain"] or {}).items()):
        lines.append(f"- `{domain}`: {count} units")
    lines.extend([
        "",
        "Facets (propositions, modality, negation, actor/recipient, quantifiers, exceptions,",
        "temporal interpretation, ambiguity, source spans, admissible assumptions) remain",
        "unmeasured. Zero agreement is an inventory of missing records, not a reliability statistic.",
        "",
        "## False transfer and abstention",
        "",
        f"- Table 6/11 false-transfer numerator: null (unrun/unavailable), denominator 1913.",
        f"- AF-016 selection false_transfer=true count: {ctx['selection_structural']['false_transfer_true_count']}.",
        f"- AF-016 selection useful=true count: {ctx['selection_structural']['useful_true_count']}.",
        f"- AF-016 native_checked_proof count: {ctx['selection_structural']['native_checked_proof_count']}.",
        f"- AF-016 selection statuses: {ctx['selection_structural']['selection_status_by_arm']}.",
        "",
        "Constructed Q1 records a guarded accepted transfer and an unguarded countermodel on a",
        "finite witness. That is not compiler soundness and is not Table 6. Zero observed false",
        "transfers there is not generalized to universal soundness.",
        "",
        "## AF-029 training and failed attempts (carried, not double-counted)",
        "",
        "AF-029 native training executed T0/T1/shared-only T2 and isolated T3 on train/selection",
        "with MiniLM teacher targets. Failed encoder-preparation attempts 1--4 are retained with",
        "their costs. Source fidelity remains null. These rows do not fill Table 11 held-out",
        "fidelity or native-proof cells. AF-020 already accounts retained historical costs;",
        "this analysis cites those totals and does not re-sum item rows into Table 6/11.",
        "",
        f"- AF-029 executed arms: {ctx['native_training']['executed_arms']}",
        f"- AF-029 claim_admissible: {ctx['native_training']['claim_admissible']}",
        f"- AF-020 measured elapsed across retained phases: {ctx['cost_elapsed_seconds']}",
        f"- Human-review table status: {ctx['human_review']['table_status']}",
        "",
    ])
    text = "\n".join(lines)
    if "TBD" in text:
        raise SystemExit("hypothesis report still contains TBD")
    return text


def build_summary(ctx: Mapping[str, Any]) -> dict[str, Any]:
    table6 = ctx["table6_cells"]
    table11 = ctx["table11_cells"]
    table13 = ctx["table13_rows"]
    hypotheses = ctx["hypotheses"]
    original_placeholders = [cell for cell in table6 + table11 if cell.get("replaces_original_placeholder")]
    if len(original_placeholders) != 44:
        raise SystemExit(f"expected 44 original placeholder cells, found {len(original_placeholders)}")
    remaining = [cell for cell in original_placeholders if cell["status"] in {None, "placeholder", "todo"}]
    if remaining:
        raise SystemExit("original placeholder cells were not replaced")
    summary = {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "analysis_id": ctx["analysis_id"],
        "scope_policy": {
            "path": "papers/completion/autoformalization/config/structural_evidence_scope.json",
            "sha256": ctx["provenance"]["structural_evidence_scope_sha256"],
            "policy_id": ctx["scope"]["policy_id"],
            "human_fidelity_status": ctx["scope"]["human_fidelity_status"],
            "independent_human_semantic_labels_available": False,
        },
        "original_placeholder_cells": 44,
        "replaced_placeholder_cells": 44,
        "remaining_placeholder_cells": 0,
        "original_manuscript_placeholder_inventory": {
            "table6": 20,
            "table11": 24,
            "table13_numeric_placeholders": 0,
            "total": 44,
        },
        "table6": {
            "cell_count": len(table6),
            "cells": table6,
        },
        "table11": {
            "cell_count": len(table11),
            "cells": table11,
        },
        "table13": {
            "row_count": len(table13),
            "rows": table13,
            "note": "Original Table 13 had proposed comparisons without numeric placeholders; results are retained with constructed/unavailable labels.",
        },
        "raw_counts": {
            "final_test_natural_source_units": 1913,
            "final_test_groups": ctx["split_counts"]["final_test"]["operational_connected_components"],
            "train_natural_source_units": ctx["split_counts"]["train"]["natural_source_units"],
            "selection_natural_source_units": ctx["split_counts"]["selection"]["natural_source_units"],
            "fixed_canary_natural_source_units": ctx["split_counts"]["fixed_canary"]["natural_source_units"],
            "prepared_blank_review_packets": ctx["gold"]["prepared_blank_packets"],
            "gold_records_with_values": ctx["gold"]["gold_records_with_values"],
            "af016_selection_records": ctx["selection_structural"]["selection_records"],
            "af016_constructed_records": ctx["selection_structural"]["constructed_control_records"],
            "af017_retrieval_rows": ctx["retrieval"]["n_observation_rows"],
            "af018_planning_rows": ctx["planning"]["n_observation_rows"],
            "af018_assistance_rows": ctx["assistance"]["n_observation_rows"],
            "unrun_no_run_per_arm": 1913,
        },
        "denominators": {
            "table6_final_test": 1913,
            "table11_final_test": 1913,
            "table13_natural_held_out": 1913,
            "coverage_rule": ctx["plan"]["population_and_statistics"]["coverage_rule"],
            "unrun_is_not_zero": True,
            "unavailable_is_not_zero": True,
        },
        "seeds": ctx["seeds"],
        "deterministic_replays": ctx["plan"]["population_and_statistics"]["deterministic_replays"],
        "grouping": {
            "unit": "source-family/time-group operational connected component",
            "final_test_groups": ctx["split_counts"]["final_test"]["operational_connected_components"],
            "assignment_seed": ctx["splits"]["assignment"]["seed"],
            "final_test_by_domain": ctx["splits"]["counts"]["final_test"]["by_domain"],
            "final_test_by_source_time": ctx["splits"]["counts"]["final_test"]["by_source_time"],
        },
        "missingness": {
            "independent_gold_present": False,
            "independent_gold_units": 0,
            "human_review_seconds": ctx["human_review"],
            "native_checkers_sealed_path": {name: False for name in NATIVE_TOOLS},
            "final_test_bodies_opened": False,
            "arm_E_activated": False,
            "t4_activated": False,
            "optional_author_feedback": False,
        },
        "confidence_interval_method": {
            "prespecified": CI_METHOD,
            "computed_on_final_test_primary_metrics": False,
            "interval": cluster_bootstrap_interval([]),
            "seed_summaries_separate": True,
            "note": "Intervals are not imputed for unmeasured or unrun cells.",
        },
        "false_transfer": {
            "table6_numerator": None,
            "table6_status": "unavailable",
            "observed_true_on_af016_rows": ctx["selection_structural"]["false_transfer_true_count"],
            "generalized_to_universal_soundness": False,
            "statement": "Zero observed false transfers is not generalized to universal soundness.",
        },
        "hypotheses": hypotheses,
        "hypothesis_status_counts": dict(Counter(item["status"] for item in hypotheses)),
        "negative_and_inconclusive_retained": True,
        "post_hoc_selection_represented_as_prespecified": False,
        "af029": ctx["native_training"],
        "corrected_actual_execution": ctx["actual_execution"],
        "training_aggregates": ctx["training_aggregates"],
        "cost_accounting": {
            "measured_elapsed_seconds": ctx["cost_elapsed_seconds"],
            "human_review": ctx["human_review"],
            "double_counted": False,
        },
        "unrun_tables": {
            "schema": ctx["unrun_tables"]["schema"],
            "tables_sha256": ctx["unrun_tables"]["tables_sha256"],
            "eligible_basis": ctx["unrun_tables"]["eligible_basis"],
        },
        "provenance": ctx["provenance"],
        "claim_limits": [
            "Independent human agreement and source-semantic fidelity are unmeasured.",
            "Unrun and unavailable are not measured zeros.",
            "Teacher, reconstruction, and prover success are not original-source gold.",
            "Zero observed false transfers is not universal soundness.",
            "Negative and inconclusive results are retained.",
            "Constructed and development diagnostics are not untouched final-distribution performance.",
            "Arm E is not promoted.",
        ],
    }
    return summary


def analyze() -> dict[str, Any]:
    paper = paper_root()
    scope = load_json(paper / "config/structural_evidence_scope.json")
    require_scope(scope)
    plan = load_json(paper / "config/experiment_plan.json")
    splits = load_json(paper / "data/splits.json")
    corpus = load_json(paper / "data/corpus_manifest.json")
    claim_map = load_json(paper / "evidence/claim_task_map.json")
    pipeline_manifest = load_json(paper / "runs/pipeline_comparison/manifest.json")
    training_manifest = load_json(paper / "runs/training_baselines/manifest.json")
    native_manifest = load_json(paper / "runs/native_training/manifest.json")
    native_scalars = load_json(paper / "evidence/native_training/adoption_scalar_summary.json")
    recipe = harness.frozen_unrun_recipe(repo_root())
    unrun_tables = harness.regenerate_tables(recipe)
    harness.assert_tables_deterministic(recipe, unrun_tables)
    if unrun_tables["eligible_basis"]["count"] != 1913:
        raise SystemExit("unrun recipe denominator drifted")
    seeds = list(plan["population_and_statistics"]["seeds"])
    if seeds != [104729, 130363, 155921]:
        raise SystemExit("frozen seeds drifted")
    gold = gold_inventory(paper / "data/gold_facets.jsonl")
    training_rows = load_jsonl(paper / "runs/training_baselines/results.jsonl")
    pipeline_rows = load_jsonl(paper / "runs/pipeline_comparison/results.jsonl")
    retrieval_rows = load_jsonl(paper / "runs/retrieval/results.jsonl")
    premise_rows = load_jsonl(paper / "runs/premise_selection/results.jsonl")
    planning_rows = load_jsonl(paper / "runs/planning/results.jsonl")
    assistance_rows = load_jsonl(paper / "runs/proof_assistance/results.jsonl")
    cost_rows = load_jsonl(paper / "runs/costs/results.jsonl")
    # AF020 source rows and phase totals are two projections of the same clocks.
    source_costs = [r for r in cost_rows if r.get("record_kind") == "source_usage"]
    phase_costs = [r for r in cost_rows if r.get("record_kind") == "phase_total"]
    def measured_total(rows):
        seen = set(); total = 0.0
        for row in rows:
            rid = row["record_id"]
            if rid in seen:
                raise ValueError("Duplicate retained cost record: " + rid)
            seen.add(rid)
            cell = row.get("elapsed_seconds") or {}
            if cell.get("kind") == "measured":
                total += float(cell["value"])
        return round(total, 9)
    cost_elapsed = measured_total(source_costs)
    if abs(cost_elapsed - measured_total(phase_costs)) > 1e-8:
        raise ValueError("Historical source/phase cost projections differ")
    ctx: dict[str, Any] = {
        "generated_at": None,
        "scope": scope,
        "plan": plan,
        "splits": splits,
        "split_counts": split_counts(splits),
        "seeds": seeds,
        "claim_map": claim_map,
        "gold": gold,
        "unrun_tables": unrun_tables,
        "pipeline_manifest": pipeline_manifest,
        "training_manifest": training_manifest,
        "training_aggregates": aggregate_training(training_rows),
        "selection_structural": selection_structural(pipeline_rows),
        "retrieval": retrieval_summary(retrieval_rows),
        "premise": premise_summary(premise_rows),
        "planning": planning_summary(planning_rows),
        "assistance": assistance_summary(assistance_rows),
        "human_review": cost_human_review(cost_rows),
        "native_training": native_training_notes(native_manifest, native_scalars),
        "actual_execution": load_json(paper / "evidence/final_correction/actual_execution.json"),
        "cost_elapsed_seconds": cost_elapsed,
        "provenance": {
            "splits_sha256": sha256_file(paper / "data/splits.json"),
            "corpus_sha256": sha256_file(paper / "data/corpus_manifest.json"),
            "experiment_plan_sha256": sha256_file(paper / "config/experiment_plan.json"),
            "metrics_sha256": sha256_file(paper / "config/metrics.json"),
            "structural_evidence_scope_sha256": sha256_file(paper / "config/structural_evidence_scope.json"),
            "claim_task_map_sha256": sha256_file(paper / "evidence/claim_task_map.json"),
            "pipeline_manifest_sha256": sha256_file(paper / "runs/pipeline_comparison/manifest.json"),
            "training_manifest_sha256": sha256_file(paper / "runs/training_baselines/manifest.json"),
            "native_training_manifest_sha256": sha256_file(paper / "runs/native_training/manifest.json"),
            "unrun_tables_sha256": unrun_tables["tables_sha256"],
            "analyze_results_sha256": sha256_file(Path(__file__)),
            "private_final_ids_disclosed": bool(corpus.get("private_final_ids_disclosed")),
            "checkpoint_baselines_sha256": sha256_file(paper / "checkpoints/baselines/manifest.json") if (paper / "checkpoints/baselines/manifest.json").is_file() else None,
            "checkpoint_native_sha256": sha256_file(paper / "checkpoints/native_training/manifest.json") if (paper / "checkpoints/native_training/manifest.json").is_file() else None,
        },
    }
    if ctx["provenance"]["splits_sha256"] != "d4989a3ea15f7035a4e85621bc220b4567828537733c4de4947fd17637bc0b27":
        raise SystemExit("splits.json digest drifted from AF-007/AF-028 pin")
    if ctx["provenance"]["corpus_sha256"] != "ca410804725f7e323551082243cea3ca5e381bcdc87b0726a0dd6f5dcfbb5ed6":
        raise SystemExit("corpus_manifest.json digest drifted from AF-007/AF-028 pin")
    if ctx["provenance"]["private_final_ids_disclosed"]:
        raise SystemExit("final-test identities were disclosed")
    ctx["analysis_id"] = sha256_obj({
        "provenance": ctx["provenance"],
        "unrun_tables_sha256": unrun_tables["tables_sha256"],
        "schema": SCHEMA,
        "task_id": TASK_ID,
    })
    ctx["table6_cells"] = build_table6(ctx)
    ctx["table11_cells"] = build_table11(ctx)
    ctx["table13_rows"] = build_table13(ctx)
    ctx["hypotheses"] = build_hypotheses(ctx)
    ctx["table6_tex"] = render_table6(ctx["table6_cells"])
    ctx["table11_tex"] = render_table11(ctx["table11_cells"])
    ctx["table13_tex"] = render_table13(ctx["table13_rows"])
    ctx["hypothesis_markdown"] = render_hypothesis_report(ctx, ctx["hypotheses"])
    ctx["summary"] = build_summary(ctx)
    return ctx


def write_outputs(ctx: Mapping[str, Any]) -> dict[str, Path]:
    out = results_dir()
    out.mkdir(parents=True, exist_ok=True)
    paths = {
        "table6": out / "table6_pipeline.tex",
        "table11": out / "table11_training.tex",
        "table13": out / "table13_assistance.tex",
        "summary": out / "summary.json",
        "hypothesis": out / "hypothesis_report.md",
    }
    paths["table6"].write_text(ctx["table6_tex"], encoding="utf-8")
    paths["table11"].write_text(ctx["table11_tex"], encoding="utf-8")
    paths["table13"].write_text(ctx["table13_tex"], encoding="utf-8")
    paths["summary"].write_text(harness.canonical_dumps(ctx["summary"]) + "\n", encoding="utf-8")
    paths["hypothesis"].write_text(ctx["hypothesis_markdown"], encoding="utf-8")
    return paths


def check_outputs(ctx: Mapping[str, Any] | None = None) -> dict[str, Any]:
    ctx = ctx or analyze()
    errors: list[str] = []
    paths = {
        "table6": results_dir() / "table6_pipeline.tex",
        "table11": results_dir() / "table11_training.tex",
        "table13": results_dir() / "table13_assistance.tex",
        "summary": results_dir() / "summary.json",
        "hypothesis": results_dir() / "hypothesis_report.md",
    }
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"missing {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if "[TBD]" in text or "[TODO]" in text or "[To complete" in text:
            errors.append(f"{name} still contains a manuscript placeholder token")
        if name == "table6" and text != ctx["table6_tex"]:
            errors.append("table6 tex is not a deterministic regeneration")
        if name == "table11" and text != ctx["table11_tex"]:
            errors.append("table11 tex is not a deterministic regeneration")
        if name == "table13" and text != ctx["table13_tex"]:
            errors.append("table13 tex is not a deterministic regeneration")
        if name == "hypothesis" and text != ctx["hypothesis_markdown"]:
            errors.append("hypothesis report is not a deterministic regeneration")
    summary = ctx["summary"]
    if summary["original_placeholder_cells"] != 44 or summary["remaining_placeholder_cells"] != 0:
        errors.append("placeholder replacement count is wrong")
    if len(summary["table6"]["cells"]) != 20:
        errors.append("Table 6 does not have 20 cells")
    if len(summary["table11"]["cells"]) != 24:
        errors.append("Table 11 does not have 24 cells")
    for item in summary["table6"]["cells"] + summary["table11"]["cells"]:
        if item["column"] in {"fidelity_uncertainty", "held_out_fidelity"}:
            if item["status"] != "unmeasured" or item["value"] is not None:
                errors.append(f"{item['cell_id']} fidelity is not an explicit unmeasured null")
            if item["interval"]["low"] is not None or item["interval"]["high"] is not None:
                errors.append(f"{item['cell_id']} invented a fidelity interval")
        if item["table"] == "6" and item["denominator"] != 1913 and item["column"] != "source_split_counts":
            errors.append(f"{item['cell_id']} denominator is not 1913")
        if item["status"] in {"unrun", "unavailable", "unmeasured"} and item["value"] is not None and item["column"] not in {"source_split_counts"}:
            errors.append(f"{item['cell_id']} has a value under {item['status']}")
    if summary["false_transfer"]["generalized_to_universal_soundness"] is not False:
        errors.append("false transfer was generalized")
    if "universal soundness" not in summary["false_transfer"]["statement"].lower() and "not generalized" not in summary["false_transfer"]["statement"].lower():
        errors.append("false-transfer non-generalization statement missing")
    if summary["post_hoc_selection_represented_as_prespecified"] is not False:
        errors.append("post-hoc selection marked as prespecified")
    if not summary["negative_and_inconclusive_retained"]:
        errors.append("negative/inconclusive results were dropped")
    statuses = {item["id"]: item["status"] for item in summary["hypotheses"]}
    for hid in ("C1", "C2", "C3", "C4", "C5", "C6"):
        if statuses.get(hid) == "supported":
            errors.append(f"{hid} is marked supported without independent/final-test evidence")
    if statuses.get("C7") not in {"inconclusive", "unrun", "unsupported"}:
        errors.append("C7 must remain inconclusive/unrun/unsupported")
    if statuses.get("H-T2-shared-learner") == "supported":
        errors.append("T2 generalization was marked supported")
    required = ["raw_counts", "denominators", "seeds", "grouping", "missingness", "confidence_interval_method"]
    for key in required:
        if key not in summary:
            errors.append(f"summary missing {key}")
    if summary["confidence_interval_method"]["computed_on_final_test_primary_metrics"] is not False:
        errors.append("CI claimed computed on unrun final-test metrics")
    if summary["missingness"]["human_review_seconds"]["table_status"] != "unmeasured":
        errors.append("human review was not kept unmeasured")
    if summary["missingness"]["arm_E_activated"] is not False:
        errors.append("Arm E was promoted")
    if "Zero observed false transfers is not generalized to universal soundness." not in ctx["hypothesis_markdown"]:
        errors.append("hypothesis report missing false-transfer guardrail")
    if "not represented as prespecified" not in ctx["hypothesis_markdown"]:
        errors.append("hypothesis report missing post-hoc guardrail")
    report = {
        "ok": not errors,
        "errors": errors,
        "original_placeholder_cells": 44,
        "replaced_placeholder_cells": summary["replaced_placeholder_cells"],
        "tables_sha256": {
            "table6": sha256_bytes(ctx["table6_tex"].encode("utf-8")),
            "table11": sha256_bytes(ctx["table11_tex"].encode("utf-8")),
            "table13": sha256_bytes(ctx["table13_tex"].encode("utf-8")),
            "summary": sha256_obj(summary),
            "hypothesis": sha256_bytes(ctx["hypothesis_markdown"].encode("utf-8")),
            "unrun_tables": ctx["unrun_tables"]["tables_sha256"],
        },
    }
    if errors:
        raise SystemExit("AF-021 check failed:\n- " + "\n- ".join(errors))
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Regenerate and verify outputs")
    args = parser.parse_args(argv)
    ctx = analyze()
    write_outputs(ctx)
    report = check_outputs(ctx)
    print(harness.canonical_dumps({
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "ok": report["ok"],
        "original_placeholder_cells": 44,
        "replaced_placeholder_cells": 44,
        "remaining_placeholder_cells": 0,
        "hypothesis_status_counts": ctx["summary"]["hypothesis_status_counts"],
        "unrun_tables_sha256": ctx["unrun_tables"]["tables_sha256"],
        "output_sha256": report["tables_sha256"],
        "false_transfer_generalized": False,
        "post_hoc_as_prespecified": False,
        "check_only": bool(args.check),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
