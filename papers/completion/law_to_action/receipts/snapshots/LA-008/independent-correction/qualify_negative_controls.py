#!/usr/bin/env python3
"""Retain real child-process deny-all, timeout, and failure qualification controls."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path.cwd()
BASE = ROOT / "papers/completion/law_to_action"
sys.path.insert(0, str(BASE / "benchmark"))
import run


def main():
    target = BASE / "receipts/snapshots/LA-008/independent-correction/negative-controls"
    records_path = target / "records.jsonl"
    denied = []
    for index in range(2):
        case = copy.deepcopy(run.smoke_cases()[0])
        case["case_id"] = f"induced-reject-all-control-{index}"
        case["grant"]["authorized"] = False
        # Keep the declared allowed-work oracle: this intentionally faulty
        # fixture setup must report lost allowed work, not a safety success.
        denied.append(run.run_attempt(case, seed=104729, timeout_seconds=5,
                                      trace_root=target / "traces", records_path=records_path))
    metrics = run.allowed_work_metrics(denied)
    assert metrics["reject_all_detected"] is True and metrics["allowed_work_successful"] == 0
    assert all(r["terminal_outcome"] == "denied" and not r["expected_measurement_matched"] for r in denied)
    timeout = run.run_attempt(run.smoke_cases()[0], seed=104729, timeout_seconds=0.01,
                              worker_delay_seconds=1, trace_root=target / "traces", records_path=records_path)
    assert timeout["actual_process"]["timed_out"] is True and timeout["actual_process"]["signal"] == 9
    failing = copy.deepcopy(run.smoke_cases()[0])
    failing["case_id"] = "actual-oversized-handler-failure"
    for key in ("declared_intent", "generated_code"):
        failing[key]["payload"] = "x" * 65536
    failure = run.run_attempt(failing, seed=104729, timeout_seconds=5,
                              trace_root=target / "traces", records_path=records_path)
    assert failure["actual_process"]["returncode"] == 2 and failure["terminal_outcome"] == "execution_failure"
    records = [*denied, timeout, failure]
    assert len({r["run_id"] for r in records}) == 4
    assert all(r["fixture"] and not r["empirical_eligible"] for r in records)
    assert all((Path(r["raw_trace"]["directory"]) / name).is_file()
               for r in records for name in ("request.json", "worker.stdout.raw", "worker.stderr.raw", "trace.json"))
    print(json.dumps({"passed": True, "scope": "Induced trusted-fixture measurement controls; no empirical benchmark result",
                      "empirical_benchmark_result": False, "reject_all": metrics,
                      "actual_timeout": timeout["actual_process"], "actual_handler_failure": failure["actual_process"],
                      "unique_run_ids": [r["run_id"] for r in records], "raw_traces_retained": True,
                      "network_isolation_claimed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
