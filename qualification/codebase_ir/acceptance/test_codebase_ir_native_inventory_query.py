"""Receiving regressions against a fixed, selected public native export closure.

Only inert retained bodies are read. These tests neither import nor execute the
native catalog, query producer, model, solver, compiler or planner.
"""
from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory_query_controls import native_receiver as receiver


def retained_fixture_input():
    relative = Path("artifacts/codebase_ir_parallel_qualification/acceptance/20261003-native-inventory-query-input-01")
    # The runner keeps implementation snapshots below the workspace and runs
    # discovery from the workspace. Also support discovery from another cwd.
    for root in (Path.cwd().resolve(), *Path(__file__).resolve().parents):
        candidate = root / relative
        if (candidate / "native_inventory_query_input.json").is_file():
            return candidate
    raise FileNotFoundError("retained native inventory receiving fixture is unavailable")


INPUT = retained_fixture_input()


class NativeInventoryReceiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = receiver.document((INPUT / "native_inventory_query_input.json").read_bytes())
        # Resolve retained fixture bodies by role, not historical absolute paths.
        cls.native = {}
        for pin in cls.spec["native_files"]:
            raw = (INPUT / pin["name"]).read_bytes()
            if len(raw) != pin["bytes"] or receiver.sha(raw) != pin["sha256"]:
                raise AssertionError("retained native fixture changed")
            cls.native[pin["name"]] = receiver.document(raw)
        cls.protocol = {pin["name"]: pin["sha256"] for pin in cls.spec["protocol_sources"]}
        cls.proofs, cls.apps = receiver.proof_inventory(cls.native)

    def join(self, profile="complete"):
        return copy.deepcopy(self.native[f"{profile}-join.json"])

    def receive(self, value):
        return receiver.receive_join(value, self.proofs, self.apps, self.protocol)

    def test_native_cid_golden_codecs_and_unicode(self):
        self.assertEqual(receiver.cid_bytes(receiver.wire(self.native["complete-join.json"])),
                         "bafkreiapsagkpfg2ir6vvchtj7udkh6mw44ci5jty4pxz6fu4jebf3awyq")
        self.assertEqual(receiver.cid(self.native["complete-join.json"]["head"]),
                         "baguqeera2zmdjc3xcb7cxgbwg6tp35ikoepxegvzxmx2l2ipjnw5w24vkqzq")
        self.assertNotEqual(receiver.cid({"text": "é"}), receiver.cid({"text": "e"}))
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "unsupported"):
            receiver.cid({"number": 1.0})

    def test_actual_complete_partial_empty_exact_golden_counts(self):
        results, previews = receiver.receive_profiles(self.native, self.protocol)
        expected = {"complete": (5, 4, 24, 0, 5, True), "partial": (1, 1, 0, 27, 1, False),
                    "empty-budget": (0, 0, 0, 28, 0, False), "deferred": (5, 4, 24, 0, 5, True),
                    "exact-key": (1, 1, 27, 0, 1, True)}
        for name, golden in expected.items():
            with self.subTest(name=name):
                self.assertEqual(tuple(results[name][field] for field in ("evidence_record_count", "matched_member_count", "complete_absence_member_count", "unknown_member_count", "page_count", "complete")), golden)
                self.assertEqual(results[name]["inventory_member_count"], 28)
        self.assertEqual(results["empty-budget"]["query_bytes_charged"], 0)
        self.assertEqual(len(previews), 3)

    def test_actual_conditional_refutation_and_empty_domain_are_distinct(self):
        result = self.receive(self.join())
        rows = result["conditional_verdicts"]
        refuted = next(row for row in rows if row["path"] == "source01.py")
        empty = next(row for row in rows if row["path"] == "source02.py")
        self.assertEqual(refuted["recorded_verification_status"], "recorded_conditional_refuted")
        self.assertTrue(refuted["conditional_refuted_for_requested_domain"])
        self.assertEqual(empty["recorded_verification_status"], "recorded_conditional_proved")
        self.assertEqual(empty["recorded_applicability_status"], "empty_domain")
        self.assertFalse(empty["conditional_proved_for_requested_domain"])
        self.assertFalse(empty["conditional_refuted_for_requested_domain"])
        self.assertTrue(all(row["runtime_behavior"] == "unknown" for row in rows))

    def test_ambiguity_keeps_both_record_ids(self):
        result = self.receive(self.join())
        self.assertEqual(result["ambiguous_members"], ["source03.py"])
        rows = [row for row in result["conditional_verdicts"] if row["path"] == "source03.py"]
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({row["query_entry_id"] for row in rows}), 2)

    def test_deferred_inference_keeps_independent_proof_ledger(self):
        result = self.receive(self.join("deferred"))
        self.assertEqual((result["inferred_row_count"], result["deferred_row_count"]), (4, 18))
        self.assertEqual(self.native["deferred-join.json"]["evidence"], self.native["complete-join.json"]["evidence"])
        self.assertEqual(result["evidence_record_count"], 5)

    def test_partial_dispositions_are_unknown_for_every_unmatched_member(self):
        value = self.join("partial")
        unknown = [row for row in value["entries"] if not row["evidence_entry_ids"]]
        self.assertEqual(len(unknown), 27)
        self.assertEqual({row["evidence_disposition"] for row in unknown}, {"unknown_budget"})
        unknown[0]["evidence_disposition"] = "no_exact_indexed_conditional_evidence"
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "disposition ledger"):
            self.receive(value)

    def test_empty_budget_cannot_claim_complete_empty_evidence(self):
        value = self.join("empty-budget")
        value["query"]["complete"] = True
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "complete/resume"):
            self.receive(value)

    def test_member_reorder_rehash_does_not_restore_native_order(self):
        value = self.join()
        value["scan"]["record"]["entries"].reverse()
        receiver.repair_join(value)
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "ordered unique"):
            self.receive(value)

    def test_shard_digest_order_is_bound_to_exact_source_rows(self):
        value = self.join()
        self.assertEqual([shard["row_count"] for shard in value["scan"]["record"]["shards"]], [16, 6])
        value["scan"]["record"]["shards"][0]["target_source_digests"].reverse()
        receiver.repair_join(value)
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "shard source order"):
            self.receive(value)

    def test_rehashed_cursor_is_bound_to_each_context(self):
        for field, changed in (("epoch", 7), ("head_cid", receiver.cid({"wrong": "head"})),
                               ("inventory_cid", receiver.cid({"wrong": "inventory"})),
                               ("selector_cid", receiver.cid({"wrong": "selector"})),
                               ("after", receiver.cid({"wrong": "position"}))):
            with self.subTest(field=field):
                value = self.join("partial")
                value["query"]["pages"][0]["page"]["next_cursor"][field] = changed
                receiver.repair_join(value)
                with self.assertRaisesRegex(receiver.ReceiverRefusal, "cursor binding"):
                    self.receive(value)

    def test_page_row_duplicate_rehash_cannot_hide_order_regression(self):
        value = self.join()
        value["query"]["pages"].insert(1, copy.deepcopy(value["query"]["pages"][0]))
        receiver.repair_join(value)
        with self.assertRaises(receiver.ReceiverRefusal):
            self.receive(value)

    def test_self_consistent_key_rehash_still_needs_independent_native_key(self):
        value = self.join()
        item = value["evidence"][0]
        receiver._mutate_key(item)
        value["query"]["pages"][0]["page"]["entries"][0] = copy.deepcopy(item["query_entry"])
        receiver.repair_join(value)
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "independent canonical key"):
            self.receive(value)

    def test_rehashed_summary_verdict_cannot_replace_original_verdict(self):
        value = self.join()
        value["evidence"][0]["verification_status"] = "recorded_conditional_proved"
        receiver.repair_join(value)
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "independent proof"):
            self.receive(value)

    def test_rehashed_empty_domain_cannot_establish_conditional_property(self):
        value = self.join()
        item = next(item for item in value["evidence"] if item["applicability_status"] == "empty_domain")
        item["applicability_summary"]["conditional_proved"] = True
        receiver.repair_join(value)
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "independent applicability"):
            self.receive(value)

    def test_native_proof_cannot_be_substituted_with_other_source_record(self):
        value = self.join()
        value["evidence"][0]["query_entry"]["verification_cid"] = list(self.proofs)[0]
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "independent proof source"):
            self.receive(value)

    def test_authority_zero_is_not_false(self):
        value = self.join()
        value["authority"]["proof_authority"] = 0
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "mistyped false"):
            self.receive(value)

    def test_query_byte_budget_counts_full_page_and_summary_bodies(self):
        value = self.join()
        result = self.receive(value)
        self.assertGreater(result["query_bytes_charged"], 100000)
        value["limits"]["max_query_bytes"] = result["query_bytes_charged"] - 1
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "aggregate byte"):
            self.receive(value)

    def test_actual_preview_preserves_authored_material_and_four_residual_tasks(self):
        value = self.native["complete-plan-preview.json"]
        result = receiver.receive_preview(value, self.native["complete-join.json"], self.native["independent-authored-plan-preview.json"], self.protocol[receiver.PROTOCOL_NAMES[-1]])
        self.assertEqual((result["runtime_requirement_count"], result["runtime_task_count"], result["runtime_fact_count"], result["tasks_omitted_count"]), (4, 4, 0, 0))
        self.assertEqual(result["authored_material_fields_preserved"], ["intent", "producers", "task_candidates", "frozen_goal", "predicates", "current_facts"])

    def test_rehashed_preview_cannot_omit_task_resolve_requirement_or_change_goal(self):
        for name, mutate in (("task", lambda value: value["removed_task_ids"].append(receiver.TASKS[0])),
                             ("requirement", lambda value: value["residual_requirements"][0].update(status="proved")),
                             ("goal", lambda value: value["repository_preview"]["input_snapshot"]["material_binding"]["field_digests"].update(frozen_goal="sha256:" + "0" * 64))):
            with self.subTest(name=name):
                value = copy.deepcopy(self.native["complete-plan-preview.json"])
                mutate(value)
                value["result_cid"] = receiver.cid({key: child for key, child in value.items() if key != "result_cid"})
                with self.assertRaises(receiver.ReceiverRefusal):
                    receiver.receive_preview(value, self.native["complete-join.json"], self.native["independent-authored-plan-preview.json"], self.protocol[receiver.PROTOCOL_NAMES[-1]])

    def test_correlated_controls_reject_all_36_and_keep_originals_unchanged(self):
        before = receiver.wire(self.native)
        controls = receiver.mutation_controls(self.native, self.protocol)
        self.assertEqual(len(controls), 36)
        self.assertEqual(len({row["name"] for row in controls}), 36)
        self.assertTrue(all(row["container_cids_recomputed"] is True and row["rejected"] is True for row in controls))
        self.assertEqual(receiver.wire(self.native), before)

    def test_strict_json_rejects_duplicates_surrogates_nonfinite_and_huge_integers(self):
        cases = [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e309}', b'{"x":"\\ud800"}',
                 b'{"\\udfff":0}', b'{"x":9223372036854775808}', b'{}\x00']
        for raw in cases:
            with self.subTest(raw=raw), self.assertRaises(receiver.ReceiverRefusal):
                receiver.document(raw)
        self.assertEqual(receiver.document(b'{"value":1.25}'), {"value": 1.25})

    def test_strict_json_bounds_depth_and_encoding_before_use(self):
        with self.assertRaises(receiver.ReceiverRefusal):
            receiver.document(b'{"x":' + b'[' * 66 + b'0' + b']' * 66 + b'}')
        with self.assertRaises(receiver.ReceiverRefusal):
            receiver.document('{"x":1}'.encode("utf-16"))
        with self.assertRaisesRegex(receiver.ReceiverRefusal, "byte bound"):
            receiver.document(b'{}', limit=1)

    def test_descriptor_read_bounds_by_remaining_aggregate_and_declared_pin(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.json"
            path.write_bytes(b'123456')
            capture = receiver.Capture()
            pin = {"bytes": 6, "sha256": receiver.sha(b'123456')}
            with patch.object(receiver, "MAX_TOTAL", 4), patch.object(receiver.OriginalCapture, "read", wraps=receiver.OriginalCapture.read) as read:
                with self.assertRaisesRegex(receiver.ReceiverRefusal, "before allocation"):
                    capture.take(path, pin)
                self.assertEqual(read.call_args.args[1], 4)
            with patch.object(receiver.OriginalCapture, "read", wraps=receiver.OriginalCapture.read) as read:
                capture.take(path, pin)
                self.assertEqual(read.call_args.args[1], 6)

    def test_descriptor_pin_drift_duplicate_and_reread_growth_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.json"
            raw = b'{}'
            path.write_bytes(raw)
            capture = receiver.Capture()
            with self.assertRaisesRegex(receiver.ReceiverRefusal, "pin mismatch"):
                capture.take(path, {"bytes": 2, "sha256": "0" * 64})
            capture.take(path, {"bytes": 2, "sha256": receiver.sha(raw)})
            with self.assertRaisesRegex(receiver.ReceiverRefusal, "duplicate input"):
                capture.take(path)
            path.write_bytes(b'{"x":1}')
            with self.assertRaisesRegex(receiver.ReceiverRefusal, "before allocation"):
                capture.stable()

    def test_regular_input_and_canonical_path_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "body.json"
            path.write_bytes(b'{}')
            link = Path(directory) / "link.json"
            link.symlink_to(path)
            with self.assertRaises(receiver.ReceiverRefusal):
                receiver.Capture().take(link)
            with self.assertRaises(receiver.ReceiverRefusal):
                receiver.Capture().take(Path(directory))

    def test_fixed_raw_audit_anchor_cannot_be_correlatedly_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            spec = copy.deepcopy(self.spec)
            spec["prior_primary_audit"]["sha256"] = "0" * 64
            path.write_bytes(receiver.wire(spec))
            with self.assertRaisesRegex(receiver.ReceiverRefusal, "fixed independent primary audit"):
                receiver.load_input(path)

    def test_full_audit_retains_stable_raw_bindings_and_all_false_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            spec = copy.deepcopy(self.spec)
            for pin in [spec["prior_primary_audit"], spec["generation_inputs"], *spec["native_files"], *spec["protocol_sources"]]:
                pin["path"] = str(INPUT / Path(pin["path"]).name)
            manifest.write_bytes(receiver.wire(spec) + b'\n')
            report = receiver.audit(manifest, root / "output")
            self.assertEqual((report["input_file_count"], report["retained_page_count"], report["mutation_control_count"]), (28, 12, 36))
            self.assertEqual(report["manifest_sha256"], receiver.sha(manifest.read_bytes()))
            self.assertEqual(report["prior_primary_audit_sha256"], "46f73d7b64af1e320655cbb0f26ccc3b7cf1f08d9d0b0d2396b5f1c554a40fba")
            self.assertTrue(report["input_files_unchanged"])
            self.assertTrue(report["native_export_receiving_conformance"])
            for field in receiver.FALSE_FLAGS:
                self.assertIs(report[field], False)
            for field in ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"):
                self.assertIs(type(report[field]), int)
                self.assertEqual(report[field], 0)
            for row in report["input_files"]:
                retained = Path(row["retained_path"]).read_bytes()
                self.assertEqual(retained, Path(row["path"]).read_bytes())
                self.assertEqual(receiver.sha(retained), row["sha256"])

    def test_output_refuses_existing_and_selected_body_scope_before_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            manifest.write_bytes(receiver.wire(self.spec))
            existing = Path(directory) / "existing"
            existing.mkdir()
            with self.assertRaisesRegex(receiver.ReceiverRefusal, "fresh and outside"):
                receiver.audit(manifest, existing)
            with self.assertRaisesRegex(receiver.ReceiverRefusal, "fresh and outside"):
                receiver.audit(manifest, INPUT / "unwritten-test-output")
            self.assertFalse((INPUT / "unwritten-test-output").exists())


if __name__ == "__main__":
    unittest.main()
