"""Smoke qualification tests for LA-008 measurement, never benchmark results."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


BENCHMARK = Path(__file__).resolve().parents[1]
if str(BENCHMARK) not in sys.path:
    sys.path.insert(0, str(BENCHMARK))

import run  # noqa: E402


class MeasurementIntegrityTests(unittest.TestCase):
    def run_smokes(self, directory: Path):
        records = []
        for case in run.smoke_cases():
            records.append(run.run_attempt(case, seed=104729, timeout_seconds=5,
                                           trace_root=directory / "traces",
                                           records_path=directory / "records.jsonl"))
        return records

    def test_authorized_effect_and_rejected_non_effect_are_observed(self):
        with tempfile.TemporaryDirectory() as raw:
            records = self.run_smokes(Path(raw))
            allowed, rejected = records
            self.assertEqual("allow", allowed["decision"]["decision"])
            self.assertEqual("success", allowed["terminal_outcome"])
            self.assertEqual(1, allowed["effect_observation"]["event_count"])
            self.assertEqual(["exports/result.json"], allowed["effect_observation"]["export_files"])
            self.assertEqual("deny", rejected["decision"]["decision"])
            self.assertEqual("denied", rejected["terminal_outcome"])
            self.assertEqual(0, rejected["effect_observation"]["event_count"])
            self.assertEqual([], rejected["effect_observation"]["export_files"])
            self.assertTrue(all(record["expected_measurement_matched"] for record in records))

    def test_raw_trace_unique_ids_and_real_exit_statuses_are_retained(self):
        with tempfile.TemporaryDirectory() as raw:
            records = self.run_smokes(Path(raw))
            self.assertNotEqual(records[0]["run_id"], records[1]["run_id"])
            for record in records:
                self.assertEqual(0, record["actual_process"]["returncode"])
                self.assertFalse(record["actual_process"]["timed_out"])
                trace = Path(record["raw_trace"]["directory"])
                self.assertTrue((trace / "request.json").is_file())
                self.assertTrue((trace / "worker.stdout.raw").is_file())
                self.assertTrue((trace / "worker.stderr.raw").is_file())
                self.assertTrue((trace / "trace.json").is_file())

    def test_replay_has_same_semantic_outcome_but_new_run_id(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            first = run.run_attempt(run.smoke_cases()[0], seed=104759, timeout_seconds=5,
                                    trace_root=root / "first")
            replay = run.run_attempt(first["case"], seed=first["seed"], timeout_seconds=5,
                                     trace_root=root / "replay")
            self.assertNotEqual(first["run_id"], replay["run_id"])
            self.assertEqual(first["replay_fingerprint"], replay["replay_fingerprint"])
            self.assertEqual(first["semantic_replay_digest"], replay["semantic_replay_digest"])

    def test_timeout_is_an_actual_worker_timeout_with_raw_trace(self):
        with tempfile.TemporaryDirectory() as raw:
            record = run.run_attempt(run.smoke_cases()[0], seed=104761, timeout_seconds=0.01,
                                     worker_delay_seconds=1.0, trace_root=Path(raw) / "traces")
            self.assertEqual("timeout", record["terminal_outcome"])
            self.assertTrue(record["actual_process"]["timed_out"])
            self.assertIsNotNone(record["actual_process"]["signal"])
            self.assertTrue((Path(record["raw_trace"]["directory"]) / "worker.stdout.raw").is_file())

    def test_reject_all_is_reported_from_allowed_work_not_safety_effects(self):
        denied = {"case": {"expected_decision": "allow", "expected_effects": 1},
                  "decision": {"decision": "deny"}, "terminal_outcome": "denied",
                  "effect_observation": {"event_count": 0}}
        metrics = run.allowed_work_metrics([denied, denied])
        self.assertTrue(metrics["reject_all_detected"])
        self.assertEqual(0, metrics["allowed_work_successful"])
        self.assertEqual(1.0, metrics["allowed_decision_denials"] / metrics["allowed_scheduled"])

    def test_fixture_smokes_are_explicitly_excluded_from_empirical_results(self):
        with tempfile.TemporaryDirectory() as raw:
            records = self.run_smokes(Path(raw))
            self.assertTrue(all(record["fixture"] for record in records))
            self.assertTrue(all(not record["empirical_eligible"] for record in records))
            self.assertTrue(all(record["labels"]["crypto"] == "fixture_only" for record in records))


if __name__ == "__main__":
    unittest.main()
