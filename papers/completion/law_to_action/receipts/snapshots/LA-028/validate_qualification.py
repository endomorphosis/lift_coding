#!/usr/bin/python3.12
"""Check LA-028 development qualification receipts without scoring gold."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers" / "completion" / "law_to_action").is_dir():
    ROOT = ROOT.parent
LIVE = ROOT / "papers" / "completion" / "law_to_action"
OUT = LIVE / "results" / "development_qualification"
BENCHMARK = LIVE / "benchmark"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main() -> int:
    errors: list[str] = []
    summary = load(OUT / "qualification_summary.json")
    pipeline = load(OUT / "source_pipeline_summary.json")
    freeze = load(OUT / "frozen_budgets.json")
    inputs = load(OUT / "frozen_inputs.json")
    manifest = load(BENCHMARK / "runtime_manifest.json")
    results_manifest = load(OUT / "runtime_manifest.json")
    admission = load(OUT / "final_admission.json")
    analysis = load(OUT / "final_analysis.json")
    review = load(OUT / "review_import_refusal.json")
    e2e = load(OUT / "e2e_handler_trace.json")
    ledger = load(OUT / "model_provider_ledger.json")
    records = jsonl(OUT / "source_records.jsonl")
    predictions = jsonl(OUT / "source_predictions.jsonl")
    failures = jsonl(OUT / "source_failures.jsonl")

    if summary.get("empirical_benchmark_result") is not False:
        errors.append("qualification claimed an empirical benchmark result")
    if summary.get("production_claim") is not False:
        errors.append("qualification claimed production")
    if summary.get("fixture_only_routes_represented_as_production") is not False:
        errors.append("fixture routes represented as production")
    if summary.get("final_labels_inspected") is not False:
        errors.append("final labels were inspected")
    if freeze.get("frozen_before_evaluated_predictions") is not True:
        errors.append("budgets were not frozen before predictions")
    if inputs.get("inspect_final_labels") is not False:
        errors.append("frozen inputs inspect final labels")
    if freeze.get("selected_arm") != "A4" or freeze.get("selected_arm_model_calls") != 0:
        errors.append("selected arm/budget mismatch")
    if manifest != results_manifest:
        errors.append("live runtime_manifest.json differs from qualification copy")
    if manifest.get("production_claim") is not False:
        errors.append("runtime manifest claims production")
    if manifest.get("fixture_routes", {}).get("la008_trusted_fixture_harness", {}).get("production") is not False:
        errors.append("LA-008 harness marked production")
    if pipeline.get("counts", {}).get("cases") != 12:
        errors.append("pipeline did not retain 12 development cases")
    if len(records) != 12 or len(predictions) + len(failures) != 12:
        errors.append("prediction/failure population is incomplete")
    if any(row.get("split") != "development" for row in records):
        errors.append("non-development records in pipeline output")
    if any(row.get("scored") or row.get("gold_inspected") for row in records):
        errors.append("pipeline scored or inspected gold")
    populations = {row["population"] for row in records}
    if populations != {"legal", "cve", "skill"}:
        errors.append("pipeline populations incomplete")
    if not predictions:
        errors.append("no retained predictions")
    if review.get("import", {}).get("admitted") is not False:
        errors.append("missing review was admitted")
    if review.get("import", {}).get("code") != "missing_independent_review_return":
        errors.append("review import did not refuse missing return")
    if admission.get("admitted") is not False or admission.get("scored") is not False:
        errors.append("final admission did not refuse")
    if "missing_independent_labels" not in admission.get("reasons", []):
        errors.append("final admission missing independent-label reason")
    if analysis.get("status") != "refused" or analysis.get("scored") is not False:
        errors.append("analysis did not refuse")
    if e2e.get("handler_boundary_reached") is not True:
        errors.append("handler boundary not reached")
    if e2e.get("proof_route_executed") is not True:
        errors.append("SAT proof route not executed")
    if e2e.get("capability_route_executed") is not True:
        errors.append("UCAN capability route not executed")
    if e2e.get("enforce_route_executed") is not True:
        errors.append("ENFORCE route not executed")
    if e2e.get("la008_run_py_represented_as_production") is not False:
        errors.append("fixture harness represented as production in e2e")
    if e2e.get("allow_decision") != "allow" or e2e.get("deny_decision") != "deny":
        errors.append("A4 allow/deny boundary did not execute as recorded")
    if ledger.get("requires_model_calls") is not False or ledger.get("call_count") != 0:
        errors.append("model ledger does not match selected A4 arm")
    for name in (
        "source_pipeline.py",
        "review_import.py",
        "qualify_final_runtime.py",
        "runtime_manifest.json",
        "FINAL_RUN.md",
    ):
        path = BENCHMARK / name
        if not path.is_file():
            errors.append(f"missing deliverable {name}")
    if not (BENCHMARK / "FINAL_RUN.md").read_text(encoding="utf-8").strip():
        errors.append("FINAL_RUN.md is empty")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "cases": len(records),
        "predictions": len(predictions),
        "failures": len(failures),
        "runtime_manifest_sha256": sha256_file(BENCHMARK / "runtime_manifest.json"),
        "qualification_summary_sha256": sha256_file(OUT / "qualification_summary.json"),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
