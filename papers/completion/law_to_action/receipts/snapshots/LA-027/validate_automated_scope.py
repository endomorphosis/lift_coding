#!/usr/bin/python3.12
"""Check LA-027 automated-scope qualification without scoring gold."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers" / "completion" / "law_to_action").is_dir():
    ROOT = ROOT.parent
LIVE = ROOT / "papers" / "completion" / "law_to_action"
OUT = LIVE / "results" / "automated_scope_qualification"
BENCHMARK = LIVE / "benchmark"
PYTHON = "/usr/bin/python3.12"
ORIGINAL_PROTOCOL = "ba03394cd66f51999d1b177a29558b6130429eb9fc3faebea5e57c780857940f"
ORIGINAL_RECEIPTS = {
    "LA-005": "d63c7184e5415d7594b25c9152b933a8b3f927600d307ad22b8fd5f402e42e62",
    "LA-007": "c9771b05898a283b7254a9159133576314da02aa452079a8c98796450e8ab8c8",
    "LA-026": "d79447296f4f77952bffbac39ae9726ea1808160abea7f25e1ac3cd7b548f883",
    "LA-028": "1d724b21352f77d494566df3bbb977ac2027fdcada0a1793b42bb70cf5706fe8",
}
BLANK_PACKETS = "6272e6a0d6f4905c6f0a727a2735d1ec94caf290cc107256fb53e7996d74ffa5"


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
    admission = load(OUT / "automated_admission.json")
    analysis = load(OUT / "final_analysis.json")
    amendment = load(BENCHMARK / "automated_evidence_amendment.json")
    manifest = load(BENCHMARK / "annotations" / "automated_reference_manifest.json")
    protocol = load(BENCHMARK / "protocol.json")
    e2e = load(OUT / "e2e_handler_trace.json")
    controls = load(OUT / "admission_controls.json")
    review = load(OUT / "review_import_refusal.json")
    freeze = load(OUT / "frozen_inputs.json")
    budgets = load(OUT / "frozen_budgets.json")
    records = jsonl(OUT / "source_records.jsonl")
    predictions = jsonl(OUT / "source_predictions.jsonl")
    failures = jsonl(OUT / "source_failures.jsonl")
    final_run = (BENCHMARK / "FINAL_RUN.md").read_text(encoding="utf-8")
    scope = (BENCHMARK / "AUTOMATED_EVIDENCE_SCOPE.md").read_text(encoding="utf-8")
    protocol_md = (BENCHMARK / "protocol.md").read_text(encoding="utf-8")

    if amendment.get("original_protocol", {}).get("sha256") != ORIGINAL_PROTOCOL:
        errors.append("amendment does not bind the original protocol hash")
    if amendment.get("original_population_budgets_unchanged") is not True:
        errors.append("amendment changed the source population or budgets")
    if amendment.get("external_human_review_required") is not False:
        errors.append("amendment still requires outside reviewers")
    if amendment.get("optional_author_review", {}).get("independent") is not False:
        errors.append("optional author review is not labeled non-independent")
    for task_id, expected in ORIGINAL_RECEIPTS.items():
        path = LIVE / "receipts" / f"{task_id}.json"
        if sha256_file(path) != expected:
            errors.append(f"original receipt {task_id} changed")
    if sha256_file(BENCHMARK / "annotations" / "review_packet_manifest.json") != BLANK_PACKETS:
        errors.append("blank review packets were modified")
    if protocol.get("automated_evidence_scope_amendment", {}).get("original_protocol_sha256") != ORIGINAL_PROTOCOL:
        errors.append("protocol metadata does not bind the original protocol hash")
    if protocol.get("population", {}).get("families", {}).get("total") != 30:
        errors.append("protocol population changed")
    if manifest.get("inventory", {}).get("case_count") != 60 or manifest.get("producer", {}).get("not_human_gold") is not True:
        errors.append("reference manifest is incomplete or claims human gold")
    if freeze.get("frozen_before_evaluated_predictions") is not True:
        errors.append("inputs were not frozen before predictions")
    if budgets.get("frozen_before_evaluated_predictions") is not True:
        errors.append("budgets were not frozen before predictions")
    if admission.get("admitted") is not True or admission.get("scored") is not False:
        errors.append("normal automated admission did not succeed unscored")
    if admission.get("human_fields", {}).get("reviewer_id") != "absent":
        errors.append("admission recorded a reviewer identity")
    if admission.get("human_fields", {}).get("independent_human_gold") is not False:
        errors.append("admission claimed independent human gold")
    if summary.get("optional_review_import", {}).get("used_as_automated_gate") is not False:
        errors.append("review import was used as the automated gate")
    if review.get("import", {}).get("admitted") is not False:
        errors.append("missing human return was admitted")
    if not controls.get("all_refused"):
        errors.append("focused controls did not all refuse")
    expected_controls = {
        "missing_runtime_binding",
        "missing_source_binding",
        "incomplete_case_accounting",
        "invalid_expectation_provenance",
        "self_reported_success",
        "stale_profile",
        "stale_budget",
        "automated_output_labeled_human_gold",
    }
    got = {row["control"] for row in controls.get("controls") or []}
    if got != expected_controls:
        errors.append("control set mismatch")
    for row in controls.get("controls") or []:
        if row.get("exit_status") != 2 or row.get("admitted") is not False:
            errors.append(f"control {row.get('control')} did not fail closed")
    if e2e.get("handler_boundary_reached") is not True or e2e.get("proof_route_executed") is not True:
        errors.append("proof/observer boundary was not executed")
    if e2e.get("capability_route_executed") is not True or e2e.get("enforce_route_executed") is not True:
        errors.append("capability/enforce route was not executed")
    if e2e.get("la008_run_py_represented_as_production") is not False:
        errors.append("fixture harness represented as production")
    if summary.get("held_out_result_inferred") is not False or summary.get("useful_work_success_inferred_from_fixtures") is not False:
        errors.append("qualification inferred held-out or useful-work success")
    if summary.get("empirical_benchmark_result") is not False:
        errors.append("qualification claimed an empirical benchmark result")
    if len(records) != 12 or len(predictions) + len(failures) != 12:
        errors.append("development case accounting is incomplete")
    if any(row.get("independent_human_gold") for row in records):
        errors.append("pipeline labeled automated output as human gold")
    if analysis.get("scored") is not False or analysis.get("held_out_scored") is not False:
        errors.append("analysis scored held-out examples")
    if "outside reviewers are not required" not in final_run.lower() and "not required for the automated evidence scope" not in final_run.lower():
        errors.append("FINAL_RUN.md still requires outside reviewers")
    if "outside reviewers" not in protocol_md.lower():
        errors.append("protocol.md does not describe the automated-scope reviewer change")
    if "never human/expert gold" not in scope.lower():
        errors.append("AUTOMATED_EVIDENCE_SCOPE.md missing gold disclaimer")
    completed = subprocess.run(
        [PYTHON, str(BENCHMARK / "automated_evidence.py"), "control", "--control", "missing_runtime_binding"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"},
    )
    if completed.returncode != 2:
        errors.append(f"failed admission process exit was {completed.returncode}, expected 2")
    else:
        payload = json.loads(completed.stdout)
        if payload.get("admitted") is not False or payload.get("exit_status") != 2:
            errors.append("failed admission payload was not a non-success result")
    report = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "cases": len(records),
        "predictions": len(predictions),
        "failures": len(failures),
        "original_protocol_sha256": ORIGINAL_PROTOCOL,
        "automated_admission_admitted": admission.get("admitted"),
        "failed_control_process_exit": completed.returncode,
        "qualification_summary_sha256": sha256_file(OUT / "qualification_summary.json"),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
