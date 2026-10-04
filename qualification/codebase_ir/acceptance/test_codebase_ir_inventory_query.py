"""Independent golden outcomes and rehashed receiver/population corruptions."""

from __future__ import annotations

import copy
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from inventory_query_controls import receiver

REFERENCE = Path(__file__).parent / "inventory_query_controls" / "fixtures"


def pin(path):
    raw = path.read_bytes()
    return {"path": str(path), "sha256": receiver.sha(raw), "bytes": len(raw)}


def reference():
    fixture = receiver.document((REFERENCE / "receiver_fixture.json").read_bytes(), receiver.MAX_FIXTURE)
    sources = {row["unit_id"]: (row["path"], (REFERENCE / row["path"]).read_bytes())
               for row in fixture["inventory"]["entries"] if row["source_sha256"] is not None}
    return fixture, sources


class InventoryQueryGoldenTests(unittest.TestCase):
    def setUp(self):
        self.fixture, self.sources = reference()
        self.result = receiver.validate_fixture(self.fixture, self.sources)
        self.cases = {row["query_id"]: row for row in self.result["query_cases"]}

    def test_complete_population_is_seven_units_six_retained_sources_three_inferred(self):
        self.assertEqual(self.result["inventory_unit_count"], 7)
        self.assertEqual(self.result["retained_source_count"], 6)
        self.assertEqual(self.result["inferred_unit_count"], 3)
        self.assertEqual(self.result["deferred_unit_count"], 1)
        self.assertEqual(self.result["opaque_unit_count"], 1)
        self.assertEqual(self.fixture["shards"], [{"shard_id": "shard-0", "unit_ids": ["proved", "refuted_empty"]},
                                                 {"shard_id": "shard-1", "unit_ids": ["ambiguous"]}])

    def test_full_query_preserves_six_records_in_three_pages_and_every_member(self):
        full = self.cases["full"]
        self.assertEqual([page["offset"] for page in full["pages"]], [0, 2, 4])
        self.assertEqual([len(page["records"]) for page in full["pages"]], [2, 2, 2])
        self.assertEqual([member["unit_id"] for member in full["member_summaries"]], list(receiver.UNIT_IDS))
        self.assertEqual([member["evidence_disposition"] for member in full["member_summaries"]],
                         ["matched_complete"] * 5 + ["no_exact_indexed_conditional_evidence"] * 2)
        self.assertTrue(full["complete"])
        self.assertIsNone(full["next_cursor"])

    def test_partial_query_has_two_matched_members_and_five_unknown_members(self):
        partial = self.cases["partial"]
        self.assertFalse(partial["complete"])
        self.assertEqual(len(partial["pages"]), 1)
        self.assertEqual(partial["retained_query_bytes"], 1378)
        self.assertEqual(partial["next_cursor"]["next_offset"], 2)
        self.assertEqual([member["evidence_disposition"] for member in partial["member_summaries"]],
                         ["matched_partial"] * 2 + ["unknown_budget"] * 5)

    def test_first_page_budget_refusal_means_zero_bytes_no_cursor_and_no_absence(self):
        empty = self.cases["empty_budget"]
        self.assertEqual(empty["pages"], [])
        self.assertEqual(empty["retained_query_bytes"], 0)
        self.assertIsNone(empty["next_cursor"])
        self.assertFalse(empty["complete"])
        self.assertEqual({member["evidence_disposition"] for member in empty["member_summaries"]}, {"unknown_budget"})

    def test_complete_empty_membership_and_wrong_contract_are_distinct_from_budget_unknown(self):
        for name in ("empty_complete", "wrong_contract"):
            with self.subTest(case=name):
                case = self.cases[name]
                self.assertTrue(case["complete"])
                self.assertEqual(case["pages"], [])
                self.assertEqual(case["stop_reason"], "complete")
                self.assertEqual({row["evidence_disposition"] for row in case["member_summaries"]},
                                 {"no_exact_indexed_conditional_evidence"})

    def test_ambiguous_records_preserve_both_contradictory_conditional_verdicts(self):
        row = self.cases["full"]["member_summaries"][2]
        self.assertEqual(row["record_ids"], ["ambiguous-proved", "ambiguous-refuted"])
        self.assertEqual(row["conditional_verdicts"], ["proved", "refuted"])
        self.assertTrue(row["ambiguous"])
        self.assertEqual(self.result["ambiguous_member_count"], 1)

    def test_base_refutation_and_empty_requested_domain_are_kept_separate(self):
        row = self.cases["full"]["member_summaries"][1]
        self.assertEqual(row["conditional_verdicts"], ["refuted"])
        self.assertEqual(row["applicability"], [{"record_id": "refuted-empty-domain",
                                               "premises": "satisfiable", "requested_domain": "empty"}])
        self.assertEqual(self.cases["full"]["planning_materials"]["observed_runtime_facts"], [])

    def test_deferred_inference_does_not_hide_independently_indexed_conditional_evidence(self):
        case = self.cases["deferred_evidence"]
        self.assertTrue(case["complete"])
        self.assertEqual(case["member_summaries"][0]["record_ids"], ["deferred-conditional"])
        self.assertEqual(case["member_summaries"][0]["evidence_disposition"], "matched_complete")
        self.assertEqual(self.fixture["inventory"]["entries"][3]["inference_disposition"], "deferred_budget")

    def test_every_case_preserves_both_original_requirements_tasks_and_zero_runtime_facts(self):
        for case in self.cases.values():
            with self.subTest(case=case["query_id"]):
                planning = case["planning_materials"]
                self.assertEqual(planning["task_ids"], ["TASK-TYPE", "TASK-OFFSET"])
                self.assertEqual([row["clause_id"] for row in planning["requirement_dispositions"]], ["FINITE-TYPE", "FINITE-OFFSET"])
                self.assertEqual({row["disposition"] for row in planning["requirement_dispositions"]}, {"residual"})
                self.assertEqual(planning["observed_runtime_facts"], [])
                self.assertEqual(planning["omitted_task_ids"], [])
                self.assertIs(planning["execution_authority"], False)

    def test_all_thirty_eight_corruptions_refuse_after_raw_fixture_rehashing(self):
        controls = receiver.controls(self.fixture, self.sources)
        self.assertEqual(len(controls), 38)
        self.assertTrue(all(row["refused"] for row in controls))
        self.assertEqual(len({row["control"] for row in controls}), 38)
        self.assertTrue(all(len(row["rehashed_fixture_sha256"]) == 64 for row in controls))

    def test_correlated_status_summary_and_byte_rebinding_still_disagree_with_independent_ledger(self):
        changed = dict(receiver.mutations(self.fixture))["correlated_record_summary_forgery"]
        response = changed["query_cases"][0]["response"]
        self.assertEqual(response["pages"][0]["records"][0]["conditional_verdict"], "refuted")
        self.assertEqual(response["member_summaries"][0]["conditional_verdicts"], ["refuted"])
        self.assertEqual(response["retained_query_bytes"], sum(len(receiver.wire(page)) for page in response["pages"]))
        self.assertEqual(changed["evidence_ledger"]["records"][0]["conditional_verdict"], "proved")
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "response rederivation"):
            receiver.validate_fixture(changed, self.sources)

    def test_unhashable_status_values_are_typed_refusals(self):
        for section in ("inference", "verdict", "applicability"):
            changed = copy.deepcopy(self.fixture)
            if section == "inference":
                changed["inventory"]["entries"][0]["inference_disposition"] = []
            elif section == "verdict":
                changed["evidence_ledger"]["records"][0]["conditional_verdict"] = []
            else:
                changed["evidence_ledger"]["records"][0]["applicability"]["premises"] = []
            with self.subTest(section=section), self.assertRaises(receiver.ReceiverRefusal):
                receiver.validate_fixture(changed, self.sources)


class InventoryQueryInputTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.input = self.root / "input"
        shutil.copytree(REFERENCE, self.input)
        self.fixture = json.loads((self.input / "receiver_fixture.json").read_bytes())
        self.spec = {"schema": receiver.INPUT_SCHEMA, "fixture_origin": receiver.ORIGIN,
                     "fixture": pin(self.input / "receiver_fixture.json"),
                     "sources": [{"unit_id": row["unit_id"], **pin(self.input / row["path"])}
                                 for row in self.fixture["inventory"]["entries"] if row["source_sha256"] is not None]}
        self.manifest = self.input / "input.json"
        self.save()

    def save(self):
        self.manifest.write_bytes(receiver.wire(self.spec) + b"\n")

    def test_actual_report_pins_original_and_retained_inputs_and_has_exact_authority_ceiling(self):
        report = receiver.run(self.manifest, self.root / "output")
        self.assertEqual(report["manifest_sha256"], pin(self.manifest)["sha256"])
        self.assertEqual(report["fixture_sha256"], self.spec["fixture"]["sha256"])
        self.assertEqual(report["fixture_origin"], receiver.ORIGIN)
        self.assertIs(report["input_files_unchanged"], True)
        self.assertIs(report["authored_receiver_conformance"], True)
        for key in ("native_execution_performed", "training_executed", "current_authority_claimed",
                    "owner_database_opened", "profile_keys_read", "production_acceptance_claimed",
                    "native_export_adoption_qualified", "signature_authentication_performed", "numerical_state_replayed"):
            self.assertIs(report[key], False)
        for key in ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"):
            self.assertIs(type(report[key]), int)
            self.assertEqual(report[key], 0)
        self.assertEqual(report["input_file_count"], 8)
        for row in report["selected_input_pins"]:
            self.assertEqual(Path(row["original_path"]).read_bytes(), Path(row["retained_path"]).read_bytes())

    def test_copied_absolute_manifest_allows_sibling_runner_output(self):
        parent = self.root / "joined"
        parent.mkdir()
        copied = parent / "retained-input.json"
        copied.write_bytes(self.manifest.read_bytes())
        report = receiver.run(copied, parent / "workflow-output")
        self.assertEqual(report["manifest_sha256"], pin(self.manifest)["sha256"])

    def test_selected_source_drift_refuses_before_output_creation(self):
        Path(self.spec["sources"][0]["path"]).write_bytes(b"changed")
        with self.assertRaises(receiver.ReceiverRefusal):
            receiver.run(self.manifest, self.root / "output")
        self.assertFalse((self.root / "output").exists())

    def test_rehashed_fixture_response_forgery_passes_outer_pin_and_refuses_independent_ledger(self):
        changed = dict(receiver.mutations(self.fixture))["correlated_record_summary_forgery"]
        path = self.input / "receiver_fixture.json"
        path.write_bytes(receiver.wire(changed) + b"\n")
        self.spec["fixture"] = pin(path)
        self.save()
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "response rederivation"):
            receiver.run(self.manifest, self.root / "output")
        self.assertFalse((self.root / "output").exists())

    def test_missing_extra_reordered_and_aliased_source_descriptors_refuse(self):
        for change in ("missing", "extra", "reorder", "alias"):
            original = copy.deepcopy(self.spec)
            if change == "missing":
                self.spec["sources"].pop()
            elif change == "extra":
                self.spec["sources"].append(copy.deepcopy(self.spec["sources"][0]))
            elif change == "reorder":
                self.spec["sources"].reverse()
            else:
                self.spec["sources"][0]["path"] = self.spec["fixture"]["path"]
            self.save()
            with self.subTest(change=change), self.assertRaises(receiver.ReceiverRefusal):
                receiver.run(self.manifest, self.root / "output")
            self.assertFalse((self.root / "output").exists())
            self.spec = original

    def test_existing_input_scope_symlink_and_noncanonical_outputs_refuse(self):
        existing = self.root / "existing"
        existing.mkdir()
        alias = self.root / "alias"
        alias.symlink_to(self.input, target_is_directory=True)
        for output in (existing, self.input / "output", alias / "output", self.root / "x" / ".." / "output"):
            with self.subTest(output=output), self.assertRaises(receiver.ReceiverRefusal):
                receiver.run(self.manifest, output)

    def test_symlink_and_fifo_inputs_are_not_read(self):
        path = Path(self.spec["sources"][0]["path"])
        raw = path.read_bytes()
        original = self.root / "original"
        original.write_bytes(raw)
        path.unlink()
        path.symlink_to(original)
        with self.assertRaises(receiver.ReceiverRefusal):
            receiver.run(self.manifest, self.root / "symlink-output")
        path.unlink()
        os.mkfifo(path)
        with self.assertRaises(receiver.ReceiverRefusal):
            receiver.run(self.manifest, self.root / "fifo-output")

    def test_duplicate_nonfinite_float_nonobject_deep_and_surrogate_json_refuse(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":1.0}', b'[]', b'{"a":"\\ud800"}',
                    b'{"a":' + b'[' * 40 + b'0' + b']' * 40 + b'}'):
            with self.subTest(raw=raw[:40]), self.assertRaises(receiver.ReceiverRefusal):
                receiver.document(raw, receiver.MAX_MANIFEST)
        with self.assertRaises(receiver.ReceiverRefusal):
            receiver.string("\ud800", "surrogate")

    def test_descriptor_growth_is_rejected_before_remaining_aggregate_allocation(self):
        capture = receiver.Capture()
        first, second = self.root / "first", self.root / "second"
        first.write_bytes(b"x")
        second.write_bytes(b"y")
        opened = receiver.os.open

        def grow_before_open(path, flags):
            if Path(path) == second:
                second.write_bytes(b"yyy")
            return opened(path, flags)

        with mock.patch.object(receiver, "MAX_TOTAL", 3):
            capture.take(first, 10)
            with mock.patch.object(receiver.os, "open", side_effect=grow_before_open):
                with self.assertRaisesRegex(receiver.ReceiverRefusal, "before allocation"):
                    capture.take(second, 10)
        self.assertEqual(capture.total, 1)

    def test_declared_pin_size_is_actual_read_limit_and_stability_uses_captured_size(self):
        capture = receiver.Capture()
        path = self.root / "tiny"
        path.write_bytes(b"x")
        capture.take(path, 100, pin(path))
        self.assertEqual(capture.raw[path][1], 1)
        path.write_bytes(b"xx")
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "before allocation"):
            capture.stable()

    def test_selected_file_count_and_manifest_size_bounds_prevent_later_reads(self):
        capture = receiver.Capture()
        with mock.patch.object(receiver, "MAX_FILES", 1):
            capture.take(self.manifest, receiver.MAX_MANIFEST)
            with self.assertRaisesRegex(receiver.ReceiverRefusal, "population bound"):
                capture.take(self.input / "receiver_fixture.json", receiver.MAX_FIXTURE)
        with mock.patch.object(receiver, "MAX_MANIFEST", 1):
            with self.assertRaisesRegex(receiver.ReceiverRefusal, "before allocation"):
                receiver.run(self.manifest, self.root / "output")

    def test_late_original_drift_refuses_passing_publication(self):
        stable = receiver.Capture.stable
        count = 0

        def drift(capture):
            nonlocal count
            count += 1
            if count == 2:
                Path(self.spec["sources"][0]["path"]).write_bytes(b"drift")
            stable(capture)

        with mock.patch.object(receiver.Capture, "stable", drift):
            with self.assertRaises(receiver.ReceiverRefusal):
                receiver.run(self.manifest, self.root / "output")
        self.assertFalse((self.root / "output" / "inventory_query_controls.json").exists())

    def test_retained_copy_tamper_refuses_passing_publication(self):
        read = receiver.Capture.read
        seen = set()

        def corrupt(path, limit):
            if path.parent.name == "retained":
                if path in seen:
                    path.write_bytes(b"corrupt")
                seen.add(path)
            return read(path, limit)

        with mock.patch.object(receiver.Capture, "read", side_effect=corrupt):
            with self.assertRaises(receiver.ReceiverRefusal):
                receiver.run(self.manifest, self.root / "output")
        self.assertFalse((self.root / "output" / "inventory_query_controls.json").exists())


if __name__ == "__main__":
    unittest.main()
