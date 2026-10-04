"""Smoke qualification tests for LA-008 measurement, never benchmark results."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


BENCHMARK = Path(__file__).resolve().parents[1]
if str(BENCHMARK) not in sys.path:
    sys.path.insert(0, str(BENCHMARK))

import run  # noqa: E402
from handlers import BoundedExportHandler, EffectObserver


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
            self.assertTrue(all(record["labels"]["network"] == "not_exercised_not_isolated" for record in records))
            self.assertTrue(all(record["execution_boundary"]["os_network_isolation"] is False for record in records))


class IndependentEffectTests(unittest.TestCase):
    run_id = "test-independent-observer"

    def case(self):
        return copy.deepcopy(run.smoke_cases()[0])

    def export(self, root):
        return BoundedExportHandler(root).execute(self.case()["generated_code"], run_id=self.run_id)

    def observe(self, root):
        return EffectObserver(root).observe(run_id=self.run_id)

    def journal(self, root, events):
        (root / "effects.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))

    def record(self, observation, case=None):
        return {"case": case or self.case(), "decision": {"decision": "allow"}, "run_id": self.run_id,
                "terminal_outcome": "success", "actual_process": {"returncode": 0, "timed_out": False},
                "expected_measurement_matched": True, "effect_observation": observation}

    def assert_no_allowed_credit(self, observed):
        record = self.record(observed)
        self.assertFalse(run.measurement_matches(record["case"], record["decision"], observed,
                                                record["actual_process"], run_id=self.run_id))
        self.assertEqual(0, run.allowed_work_metrics([record])["allowed_work_successful"])

    def test_observer_hashes_actual_bytes_and_sizes(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.export(root)
            observation = self.observe(root)
            payload = (root / "exports/result.json").read_bytes()
            self.assertTrue(observation["journal_consistent"])
            self.assertEqual(1, observation["observed_effect_count"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), observation["observed_effects"][0]["payload_sha256"])
            self.assertEqual(len(payload), observation["observed_effects"][0]["payload_bytes"])

    def test_unjournaled_file_is_an_effect_and_cannot_pass_denied_zero_effects(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "exports").mkdir()
            (root / "exports/result.json").write_bytes(b'{"ok":true}')
            observation = self.observe(root)
            self.assertEqual(1, observation["event_count"])
            self.assertEqual(0, observation["journal_event_count"])
            self.assertFalse(observation["journal_consistent"])
            denied = run.smoke_cases()[1]
            self.assertFalse(run.measurement_matches(denied, {"decision": "deny"}, observation,
                                                    {"returncode": 0, "timed_out": False}, run_id=self.run_id))
            self.assert_no_allowed_credit(observation)

    def test_wrong_digest_bytes_run_id_target_and_duplicate_entries_are_rejected(self):
        for kind in ("digest", "bytes", "boolean_bytes", "run_id", "target", "duplicate", "missing"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                event = self.export(root)
                if kind == "digest": event["payload_sha256"] = "0" * 64
                if kind == "bytes": event["payload_bytes"] = 0
                if kind == "boolean_bytes": event["payload_bytes"] = True
                if kind == "run_id": event["run_id"] = "foreign-run"
                if kind == "target": event["target"] = "exports/missing.json"
                self.journal(root, [] if kind == "missing" else [event, event] if kind == "duplicate" else [event])
                observation = self.observe(root)
                self.assertEqual(1, observation["observed_effect_count"])
                self.assertFalse(observation["journal_consistent"])
                self.assert_no_allowed_credit(observation)

    def test_journal_only_claim_missing_file_cannot_pass(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.export(root)
            (root / "exports/result.json").unlink()
            observation = self.observe(root)
            self.assertEqual(0, observation["observed_effect_count"])
            self.assertEqual(1, observation["journal_event_count"])
            self.assertFalse(observation["journal_consistent"])
            self.assert_no_allowed_credit(observation)

    def test_changed_actual_file_is_hashed_and_not_hidden_by_journal(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            event = self.export(root)
            payload = b'{"ok":false,"tampered":true}'
            (root / "exports/result.json").write_bytes(payload)
            observation = self.observe(root)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), observation["observed_effects"][0]["payload_sha256"])
            self.assertFalse(observation["journal_consistent"])
            self.assert_no_allowed_credit(observation)
            # Even a matching forged journal cannot satisfy the case's actual postcondition.
            event.update(payload_sha256=hashlib.sha256(payload).hexdigest(), payload_bytes=len(payload))
            self.journal(root, [event])
            observation = self.observe(root)
            self.assertTrue(observation["journal_consistent"])
            self.assert_no_allowed_credit(observation)

    def test_extra_consistently_journaled_export_cannot_earn_allowed_credit(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.export(root)
            second = self.case()["generated_code"]
            second["path"] = "exports/extra.json"
            BoundedExportHandler(root).execute(second, run_id=self.run_id)
            observation = self.observe(root)
            self.assertTrue(observation["journal_consistent"])
            self.assertEqual(2, observation["observed_effect_count"])
            self.assert_no_allowed_credit(observation)

    def test_unexpected_files_directories_and_links_are_not_zero_effect_successes(self):
        for kind in ("outside_exports", "empty_directory", "export_symlink", "journal_symlink", "hardlink", "fifo"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as raw:
                root = Path(raw) / "state"
                root.mkdir()
                outside = Path(raw) / "outside.json"
                outside.write_bytes(b'"outside-sentinel-not-an-export"')
                if kind == "outside_exports": (root / "unexpected.json").write_text("{}")
                elif kind == "empty_directory": (root / "exports/empty").mkdir(parents=True)
                elif kind == "export_symlink":
                    (root / "exports").mkdir()
                    (root / "exports/result.json").symlink_to(outside)
                elif kind == "journal_symlink": (root / "effects.jsonl").symlink_to(outside)
                elif kind == "fifo": os.mkfifo(root / "unexpected.fifo")
                else:
                    self.export(root)
                    os.link(root / "exports/result.json", Path(raw) / "outside-hardlink.json")
                observation = self.observe(root)
                self.assertFalse(observation["journal_consistent"])
                self.assertFalse(run.observed_postconditions(self.case(), observation, run_id=self.run_id)["zero_observed_state_effects"])
                self.assertNotIn("outside-sentinel-not-an-export", json.dumps(observation))
                self.assert_no_allowed_credit(observation)

    def test_state_root_symlink_is_not_followed(self):
        with tempfile.TemporaryDirectory() as raw:
            outside = Path(raw) / "outside"
            outside.mkdir()
            (outside / "private.txt").write_text("sentinel-not-observed")
            root = Path(raw) / "state"
            root.symlink_to(outside, target_is_directory=True)
            observed = self.observe(root)
            self.assertEqual(1, observed["observed_effect_count"])
            self.assertFalse(observed["journal_consistent"])
            self.assertNotIn("private.txt", json.dumps(observed))

    def test_malformed_journal_is_retained_as_measurement_failure(self):
        for text in ('not json\n', '[]\n', '{"run_id":"one","run_id":"two"}\n', '{"value":NaN}\n'):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as raw:
                root = Path(raw)
                self.export(root)
                (root / "effects.jsonl").write_text(text)
                observed = self.observe(root)
                self.assertFalse(observed["journal_consistent"])
                self.assertTrue(any("malformed" in e["code"] for e in observed["integrity_errors"]))
                self.assert_no_allowed_credit(observed)

    def test_oversized_export_is_not_silently_hashed_as_a_prefix(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self.export(root)
            (root / "exports/result.json").write_bytes(b"x" * 65537)
            observed = self.observe(root)
            self.assertEqual(65537, observed["observed_effects"][0]["payload_bytes"])
            self.assertIsNone(observed["observed_effects"][0]["payload_sha256"])
            self.assertFalse(observed["observation_complete"])
            self.assert_no_allowed_credit(observed)

    def test_nonfixtures_false_network_labels_and_noncanonical_paths_are_not_admitted(self):
        for kind in ("nonfixture", "network", "path", "boolean_count"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as raw:
                case = self.case()
                if kind == "nonfixture": case["fixture"] = False
                if kind == "network": case["labels"]["network"] = "disabled"
                if kind == "path": case["generated_code"]["path"] = "exports/a//result.json"
                if kind == "boolean_count": case["expected_effects"] = True
                with self.assertRaises(run.HarnessError):
                    run.run_attempt(case, seed=1, timeout_seconds=5, trace_root=Path(raw) / "traces")
                self.assertFalse((Path(raw) / "traces").exists())

    def test_generated_source_text_is_only_json_data_in_the_bounded_dsl(self):
        with tempfile.TemporaryDirectory() as raw:
            marker = Path(raw) / "should-not-execute"
            case = self.case()
            source_text = f"__import__('pathlib').Path({str(marker)!r}).write_text('executed')"
            case["generated_code"]["payload"] = source_text
            case["declared_intent"]["payload"] = source_text
            record = run.run_attempt(case, seed=1, timeout_seconds=5, trace_root=Path(raw) / "traces")
            self.assertTrue(record["expected_measurement_matched"])
            self.assertFalse(marker.exists())
            self.assertFalse(record["execution_boundary"]["arbitrary_generated_source_execution"])

    def test_real_handler_failure_retains_nonzero_exit_and_does_not_earn_credit(self):
        with tempfile.TemporaryDirectory() as raw:
            case = self.case()
            case["declared_intent"]["payload"] = "x" * 65536
            case["generated_code"]["payload"] = "x" * 65536
            record = run.run_attempt(case, seed=1, timeout_seconds=5, trace_root=Path(raw) / "traces")
            self.assertEqual("execution_failure", record["terminal_outcome"])
            self.assertEqual(2, record["actual_process"]["returncode"])
            self.assertFalse(record["expected_measurement_matched"])
            self.assertEqual(0, run.allowed_work_metrics([record])["allowed_work_successful"])
            self.assertIn(b"payload exceeds", (Path(record["raw_trace"]["directory"]) / "worker.stderr.raw").read_bytes())

    def test_handler_never_follows_a_preexisting_journal_symlink(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "state"
            root.mkdir()
            outside = Path(raw) / "outside-journal"
            outside.write_bytes(b"unchanged-outside-journal\n")
            (root / "effects.jsonl").symlink_to(outside)
            with self.assertRaises(OSError):
                self.export(root)
            self.assertEqual(b"unchanged-outside-journal\n", outside.read_bytes())
            self.assertFalse(self.observe(root)["journal_consistent"])


class AppendIntegrityTests(unittest.TestCase):
    def test_short_writes_are_completed_without_truncating_records(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "records.jsonl"
            real_write = os.write
            def short_write(fd, data):
                return real_write(fd, data[:3])
            records = [{"run_id": "one", "body": "a" * 37}, {"run_id": "two", "body": "b" * 29}]
            with patch.object(run.os, "write", side_effect=short_write):
                for record in records:
                    run.append_record(target, record)
            self.assertEqual(records, [json.loads(line) for line in target.read_bytes().splitlines()])

    def test_partial_write_failure_is_raised_preserved_and_blocks_future_append(self):
        with tempfile.TemporaryDirectory() as raw:
            target = Path(raw) / "records.jsonl"
            real_write = os.write
            calls = 0
            def fails_after_prefix(fd, data):
                nonlocal calls
                calls += 1
                return real_write(fd, data[:4]) if calls == 1 else 0
            with patch.object(run.os, "write", side_effect=fails_after_prefix):
                with self.assertRaises(OSError):
                    run.append_record(target, {"run_id": "incomplete"})
            partial = target.read_bytes()
            self.assertEqual(4, len(partial))
            with self.assertRaisesRegex(run.HarnessError, "incomplete prior append"):
                run.append_record(target, {"run_id": "must-not-append"})
            self.assertEqual(partial, target.read_bytes())


if __name__ == "__main__":
    unittest.main()
