#!/usr/bin/env python3
"""Verify exact additive workflow clarification and replay frozen design checks.

Reads only protocol documents, historical receipts and retained task contracts.
No source data, labels, models, experiments, providers or supervisor state.
"""
import argparse
import hashlib
import json
import runpy
from pathlib import Path

PRIOR_RECEIPT_SHA = "fad876022b0e53833a8741c677b91b296a2b409af99c3b1e90eccee041756ad0"
OLD_PARAGRAPH = """LA-004 must first freeze an eligible cohort with exactly these population
counts and two cases per family, including lawful source access, immutable
source pins, and independently reviewed labels. It must assign unique opaque
lineage-family IDs across all populations. An original source and every"""
NEW_PARAGRAPH = """LA-004 freezes the source manifests and reserves the planned source-family
splits with exactly these population counts and two planned cases per family,
including lawful source access and immutable source pins. This source freeze
is not admission to evaluation: the independently reviewed legal labels,
real CVE pairs and controls, and skill labels and variants remain mandatory
LA-005, LA-006, and LA-007 outputs. Those downstream tasks depend on LA-004;
their unfinished reviews do not by themselves prevent completion of LA-004's
source-manifest contract. No case may enter a scored evaluation until all
required independent reviews, lineage checks, and other admission gates pass.
Any discovered ineligibility remains recorded and keeps the affected study
unrun; it does not authorize replacement after outcomes or silent quota changes.
LA-004 must assign unique opaque lineage-family IDs across all populations.
An original source and every"""
WORKFLOW = {
    "LA-004": "Freeze source manifests, lawful access and immutable pins; reserve exact planned source-family splits and case counts. Source-manifest task completion does not assert that cases are independently labeled, executable, or admitted to evaluation.",
    "LA-005": "Produce and independently review legal applicability and fidelity labels after the source freeze.",
    "LA-006": "Construct and review real vulnerable/fixed pairs and unrelated-code controls after the source freeze.",
    "LA-007": "Annotate and review real skill intent and adversarial variants after the source freeze.",
    "evaluation_gate": "Scored evaluation requires all downstream independent reviews, source-family and leakage checks, mechanism qualifications and existing admission gates. Preserve every shortfall and rejection; keep affected studies unrun until a documented pre-outcome amendment resolves them. Do not silently replace sources or change quotas.",
    "unchanged": "Population quotas, split hashing, denominator rules, scientific acceptance standards and every LA-004 through LA-025 obligation remain unchanged.",
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate(directory):
    here = Path(__file__).resolve().parent
    root = directory.resolve().parents[3]
    previous = here / "previous-receipt.json"
    assert digest(previous) == PRIOR_RECEIPT_SHA, "historical receipt changed"
    receipt = json.loads(previous.read_text())
    for name, sha in receipt["artifacts"].items():
        assert digest(root / name) == sha, "historical snapshot changed: " + name
    prior_json = json.loads((root / receipt["outputs"]["papers/completion/law_to_action/benchmark/protocol.json"]).read_text())
    current_json = json.loads((directory / "protocol.json").read_text())
    assert current_json.pop("source_freeze_and_evaluation_admission") == WORKFLOW
    assert current_json == prior_json, "frozen protocol changed outside workflow explanation"
    prior_md = (root / receipt["outputs"]["papers/completion/law_to_action/benchmark/protocol.md"]).read_text()
    assert prior_md.count(OLD_PARAGRAPH) == 1
    assert (directory / "protocol.md").read_text() == prior_md.replace(OLD_PARAGRAPH, NEW_PARAGRAPH)
    old_resources = root / receipt["outputs"]["papers/completion/law_to_action/benchmark/resource_plan.json"]
    assert (directory / "resource_plan.json").read_bytes() == old_resources.read_bytes()
    contract = json.loads((here / "task-dependency-contract.json").read_text())
    task_source = root / "papers/completion/law_to_action/tasks.json"
    assert digest(task_source) == contract["source_tasks_sha256"], "task source context changed"
    tasks = {t["id"]: t for t in contract["tasks"]}
    current_tasks = {t["id"]: t for t in json.loads(task_source.read_text())["tasks"]}
    assert tasks == {key: current_tasks[key] for key in ["LA-004", "LA-005", "LA-006", "LA-007"]}
    assert tasks["LA-004"]["depends_on"] == ["LA-003"]
    assert all(tasks[t]["depends_on"] == ["LA-004"] for t in ["LA-005", "LA-006", "LA-007"])
    # Use the prior immutable validator as code, not copied or weakened logic.
    validator = root / receipt["commands"][0]["script_artifact"]
    namespace = runpy.run_path(str(validator))
    frozen_design_validation = namespace["validate"](directory)
    assert frozen_design_validation["status"] == "pass"
    return {
        "status": "pass",
        "scope": "Narrow dependency wording and frozen protocol/synthetic arithmetic checks only",
        "prior_receipt_sha256": PRIOR_RECEIPT_SHA,
        "historical_artifacts_verified": len(receipt["artifacts"]),
        "prior_protocol_json_preserved_except_one_additive_workflow_field": True,
        "prior_markdown_preserved_except_one_workflow_paragraph": True,
        "resource_plan_byte_identical": True,
        "native_task_dependencies_unchanged": True,
        "independent_review_and_evaluation_admission_gates_preserved": True,
        "frozen_design_validation": frozen_design_validation,
        "source_corpora_loaded": False,
        "benchmark_results_loaded": False,
        "independent_labels_loaded": False,
        "experiments_executed": 0,
        "provider_invoked": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol-dir", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(validate(args.protocol_dir), indent=2))


if __name__ == "__main__":
    main()
