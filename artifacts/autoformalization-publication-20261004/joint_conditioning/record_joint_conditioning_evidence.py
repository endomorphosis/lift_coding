"""Record completed, pinned source-only conditioning results without model calls."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
INPUTS = {
    "plan": ("run-plan-02.json", "7503d736aa53f62961487c3354974b384f21a20ae70311a779456b68edc61e68"),
    "batch": ("run-01/batch-report.json", "c1b0891e9bdc8649615a522a6f6aa7004ae84b8668e38fdd8f1fd5ae150d501d"),
    "summary": ("results-01/summary-01.json", "87a05b6e014e725758710261f7b16d5d9cc57c5620dd24861c000f94eef7e851"),
    "audit": ("independent-audit-01.json", "da298d60692580e8afcd07e7d14eb28c71b8b3e98494387e579f337b31764372"),
}


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def binding(path):
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def save(path, value):
    payload = {**value, "content_sha256": hashlib.sha256(raw(value)).hexdigest()}
    with path.open("xb") as stream:
        stream.write(json.dumps(payload, indent=2, sort_keys=True,
                                ensure_ascii=False, allow_nan=False).encode() + b"\n")
    return binding(path)


def main():
    values, pins = {}, {}
    for name, (relative, digest) in INPUTS.items():
        path = BASE / relative
        pin = binding(path)
        if pin["sha256"] != digest:
            raise ValueError("selected completed input changed")
        pins[name] = pin
        values[name] = json.loads(path.read_bytes())
    summary, audit = values["summary"], values["audit"]
    if summary["status"] != "completed" or audit["status"] != "passed":
        raise ValueError("completed summary and independent passed audit required")
    if summary["actual_counts"]["actual_model_forward_calls"] != 1152:
        raise ValueError("exact completed model-call denominator required")
    copies = []
    for row in summary["worker_evidence_bindings"]:
        source = Path(row["report_binding"]["path"])
        if binding(source) != row["report_binding"]:
            raise ValueError("completed worker report changed")
        destination = BASE / f"seed{row['seed']}-worker-report-01.json"
        with destination.open("xb") as stream:
            stream.write(source.read_bytes())
        copies.append({"seed": row["seed"], "original_binding": row["report_binding"],
                       "public_copy_binding": binding(destination)})
    batch_copy = BASE / "batch-report-01.json"
    with batch_copy.open("xb") as stream:
        stream.write((BASE / INPUTS["batch"][0]).read_bytes())
    engineering = {
        "schema": "joint-conditioning-engineering-validation/v1", "status": "passed",
        "plan_binding": pins["plan"],
        "superseded_preexecution_plan_binding": binding(BASE / "run-plan-01.json"),
        "superseded_reason": "Fixed-decision ambiguity may abstain before selection: forward/outcome denominator remains complete while selector-call count is conditional. Superseded before model execution.",
        "fixture_tests": {"passed": 72, "failed": 0, "elapsed_seconds": 0.540,
                          "worker": 29, "summary": 13, "independent_auditor": 30,
                          "command": ".venv/bin/python -I -B -m unittest discover -s artifacts/autoformalization-publication-20261004/joint_conditioning -p 'test_*.py'"},
        "ruff_passed": True,
        "ruff_command": ".venv/bin/ruff check artifacts/autoformalization-publication-20261004/joint_conditioning --exclude 'run-*'",
        "source_only_readiness": {"previous_control_panels": 36, "source_condition_seed_joins": 1152,
                                  "model_calls": 0, "target_calls": 0},
        "runtime_pins": {p.name: binding(p) for p in sorted(BASE.glob("*.py"))},
        "accepted": False, "proof_authority": False, "semantic_accuracy_measured": False,
    }
    engineering_pin = save(BASE / "engineering-validation-01.json", engineering)
    comparison = {}
    for control, aggregate in summary["aggregate_controls"].items():
        comparison[control] = {
            "request_count": aggregate["request_count"],
            "greedy_proposals": aggregate["greedy_proposals"],
            "joint_proposals": aggregate["joint_proposals"],
            "joint_proposals_per_seed": [row["controls"][control]["joint_proposals"] for row in summary["seeds"]],
            "vs_raw_changed_counts": aggregate["vs_raw"]["changed_counts"],
        }
    continuation = {
        "schema": "joint-conditioning-continuation-evidence/v1",
        "status": "completed_experiment_publication_recorded_separately",
        "input_bindings": pins, "engineering_validation_binding": engineering_pin,
        "public_worker_report_copies": copies, "public_batch_copy_binding": binding(batch_copy),
        "public_ledger_bindings": summary["public_ledger_bindings"],
        "actual_runtime_counts": summary["actual_counts"], "aggregate": summary["aggregate"],
        "conditioning_comparison": comparison, "resources": summary["resources"],
        "independent_audit": {"checked_file_count": audit["checked_file_count"],
                              "policy_outcomes_checked": audit["policy_outcomes_checked"],
                              "audit_model_calls": audit["audit_model_calls"],
                              "public_results_checked": True},
        "limitations": summary["limitations"], "semantic_masks": summary["semantic_masks"],
        "new_model_weights": False, "huggingface_upload_needed_for_this_round": False,
        "training_executed": False, "independent_semantic_review_completed": False,
        "accepted": False, "qualified": False, "proof_authority": False,
        "semantic_accuracy_measured": False, "source_fidelity_established": False,
        "git_publication_policy": "Overlay only explicit source/scalar/ledger/doc files on exact current origin/main; preserve every other blob, mode and Gitlink; ordinary fast-forward push with active hooks.",
    }
    print(json.dumps({"engineering_binding": engineering_pin,
                      "continuation_binding": save(BASE / "continuation-evidence-01.json", continuation)}))


if __name__ == "__main__":
    main()
