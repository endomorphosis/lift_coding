"""Offline batch receiving tests over a pinned public native export closure."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inventory_query_controls import native_batch_receiver as receiver


def retained_fixture_input():
    relative = Path("artifacts/codebase_ir_parallel_qualification/acceptance/20261003-native-batch-query-input-01")
    for root in (Path.cwd().resolve(), *Path(__file__).resolve().parents):
        candidate = root / relative
        if (candidate / "native_batch_query_input.json").is_file():
            return candidate
    raise FileNotFoundError("retained native batch receiving fixture is unavailable")


INPUT = retained_fixture_input()


class NativeBatchReceiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = receiver.codec.document((INPUT / "native_batch_query_input.json").read_bytes())
        cls.bodies = {}
        for role in receiver.ROLES:
            raw = (INPUT / (role + ".json")).read_bytes()
            pin = cls.spec[role]
            if len(raw) != pin["bytes"] or receiver.codec.sha(raw) != pin["sha256"]:
                raise AssertionError("selected native batch fixture changed")
            cls.bodies[role] = receiver.codec.document(raw)

    def packet(self):
        return [copy.deepcopy(self.bodies[role]) for role in receiver.ROLES]

    def query(self, index=0):
        return copy.deepcopy(self.bodies["native_result"]["supervisor"]["batch"]["matches"][index]["match"]["query"])

    def repair_query(self, query, doc=None):
        if doc is not None:
            query["intent_document_json"] = json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            query["native_document_sha256"] = receiver.codec.sha(query["intent_document_json"].encode("utf-8"))
        query["query_cid"] = receiver.codec.cid(receiver.without(query, "query_cid"))

    def test_actual_batch_pages_clauses_and_partial_resume_have_golden_counts(self):
        value = receiver.receive(*self.packet())
        self.assertEqual([row["selector_count"] for row in value["observations"]], [1, 8, 32, 1, 8, 32])
        self.assertEqual(sum(row["page_count"] for row in value["observations"]), 82)
        self.assertEqual(len(value["cold_response_page_cids"]), 32)
        self.assertEqual(value["epoch"], 9)
        self.assertEqual(value["resume_frontier"], "partial")
        self.assertIsNotNone(value["next_cursor"])
        self.assertEqual((len(value["requirements"]), len(value["clause_ledger"]), len(value["residual_requirements"])), (4, 8, 8))
        self.assertEqual(value["batch_cid"], "baguqeera5tvuih7ypcvf5pi4czrqod27ack364ztlkym473acq2fsphzwiea")

    def test_proved_refuted_vacuous_and_unsupported_do_not_resolve_runtime(self):
        value = receiver.receive(*self.packet())
        self.assertEqual([row["recorded_match_status"] for row in value["requirements"]],
                         ["recorded_conditional_proved", "recorded_conditional_refuted", "recorded_conditional_vacuous", "unknown"])
        self.assertEqual([row["mathematical_lookup_supported"] for row in value["requirements"]], [True, True, True, False])
        self.assertTrue(all(row["runtime_behavior"] == "unknown" for row in value["requirements"]))
        self.assertEqual({row["status"] for row in value["residual_requirements"]}, {"runtime_behavior_unresolved"})

    def test_original_clauses_preserve_exact_text_and_native_character_byte_spans(self):
        rows = receiver.custody(self.query())
        self.assertEqual([row["statement_id"] for row in rows], ["mathematical-goal", "runtime-goal"])
        self.assertEqual([row["original_clause_texts"] for row in rows],
                         [["Reviewed mathematical offset clause."], ["Return an exact Python int at runtime."]])
        self.assertEqual([row["original_source_spans"][0]["byte_span"] for row in rows],
                         [{"start_byte": 0, "end_byte": 36}, {"start_byte": 37, "end_byte": 75}])
        self.assertEqual([row["modality"] for row in rows], ["required", "required"])

    def test_authored_unicode_character_offsets_rederive_distinct_utf8_byte_offsets(self):
        # An authored codec control only: the actual native archive stays ASCII.
        query = self.query()
        pieces = ["Μαθηματική ρήτρα.", "返回精确整数。"]
        text = "\n".join(pieces)
        query["intent_source_text"] = text
        query["intent_source_sha256"] = receiver.codec.sha(text.encode("utf-8"))
        doc = receiver.codec.document(query["intent_document_json"].encode())
        start = 0
        for index, (source, ledger) in enumerate(zip(doc["sources"], query["intent_source_ledger"], strict=True)):
            source["content_sha256"] = query["intent_source_sha256"]
            source["span"] = {"start_char": start, "end_char": start + len(pieces[index])}
            ledger["original_text"] = pieces[index]
            ledger["reference_json"] = json.dumps(source, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            doc["statements"][index]["normalized_text"] = pieces[index]
            start += len(pieces[index]) + 1
        self.repair_query(query, doc)
        rows = receiver.custody(query)
        second = rows[1]["original_source_spans"][0]
        self.assertGreater(second["byte_span"]["start_byte"], second["character_span"]["start_char"])
        self.assertEqual(second["byte_span"], {"start_byte": len((pieces[0] + "\n").encode()), "end_byte": len(text.encode())})
        raw = text.encode()[second["byte_span"]["start_byte"]:second["byte_span"]["end_byte"]]
        self.assertEqual(receiver.codec.sha(raw), second["source_slice_sha256"])
        wrong = copy.deepcopy(query)
        wrong_doc = receiver.codec.document(wrong["intent_document_json"].encode())
        wrong_doc["sources"][1]["span"]["end_char"] = len(text.encode())
        wrong["intent_source_ledger"][1]["reference_json"] = json.dumps(wrong_doc["sources"][1])
        self.repair_query(wrong, wrong_doc)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "span end"):
            receiver.custody(wrong)

    def test_rehashed_original_span_text_must_match_preserved_source(self):
        query = self.query()
        query["intent_source_ledger"][0]["original_text"] = "Changed original clause."
        self.repair_query(query)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "span text"):
            receiver.custody(query)

    def test_duplicate_and_reordered_statement_source_refs_are_unambiguous(self):
        query = self.query()
        doc = receiver.codec.document(query["intent_document_json"].encode())
        doc["statements"].append(copy.deepcopy(doc["statements"][0]))
        self.repair_query(query, doc)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "statement identity"):
            receiver.custody(query)
        query = self.query()
        doc = receiver.codec.document(query["intent_document_json"].encode())
        doc["sources"].reverse()
        self.repair_query(query, doc)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "original reference"):
            receiver.custody(query)

    def test_selected_statement_is_checked_against_complete_original_document(self):
        query = self.query()
        query["statement_id"] = "runtime-goal"
        self.repair_query(query)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "selected statement corresponds"):
            receiver.custody(query)

    def test_original_clause_omission_cannot_hide_behind_recomputed_query_cid(self):
        query = self.query()
        query["requirement_ids"].pop()
        self.repair_query(query)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "complete original clause"):
            receiver.custody(query)

    def test_recorded_human_review_status_cannot_grant_review_custody(self):
        query = self.query()
        query["review_custody_verified"] = True
        self.repair_query(query)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "authority ceiling"):
            receiver.custody(query)

    def test_batch_preserves_repeated_receipts_and_full_tuple_order(self):
        result, request, response, snapshot = self.packet()
        values = result["measurements"][-1]["batch"]["pages"]
        self.assertEqual(len(values), 32)
        self.assertLess(len({row["page_cid"] for row in values}), 32)
        values.reverse()
        result["measurements"][-1]["individual"]["pages"].reverse()
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "ordered fixture request"):
            receiver.receive(result, request, response, snapshot)

    def test_independent_original_individual_requirement_anchor_remains_fixed(self):
        result, request, response, snapshot = self.packet()
        match = result["supervisor"]["batch"]["matches"][0]["match"]
        match["query"]["intent_source_ledger"][0]["original_text"] = "Changed clause."
        receiver.rehash_match(match)
        batch = result["supervisor"]["batch"]
        batch["batch_cid"] = receiver.codec.cid(receiver.without(batch, "batch_cid"))
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "individual requirement equivalence"):
            receiver.receive(result, request, response, snapshot)

    def test_independent_cold_request_and_stdout_cannot_be_replaced_with_warm_result(self):
        for mutate in (lambda packet: packet[1]["pages"].reverse(), lambda packet: packet[2]["measurements"]["pages"].pop()):
            packet = self.packet()
            mutate(packet)
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.receive(*packet)

    def test_cursor_binds_source_selector_inventory_epoch_and_continuation(self):
        _, request, response, _ = self.packet()
        retained = response["resumed_page"]
        for field, value in (("head_cid", receiver.codec.cid({"other": "head"})), ("inventory_cid", receiver.codec.cid({"other": "inventory"})),
                             ("epoch", 10), ("selector_cid", receiver.codec.cid({"other": "selector"}))):
            with self.subTest(field=field):
                start = copy.deepcopy(request["cursor"])
                start[field] = value
                changed = copy.deepcopy(retained)
                changed["start_cursor"] = start
                changed["page_cid"] = receiver.codec.cid(receiver.without(changed, "page_cid"))
                with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "cursor source"):
                    receiver.page(changed, request["head"], retained["inventory_cid"], 9, start)

    def test_unselected_integrity_failure_withholds_whole_export_receiving_result(self):
        for mutate in (lambda result: result.update(completed=False),
                       lambda result: result["checks"].update(integrity_and_source_controls=False),
                       lambda result: result["errors"].append({"message": "late error"})):
            packet = self.packet()
            mutate(packet[0])
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "whole historical operation"):
                receiver.receive(*packet)

    def test_eight_runtime_residuals_cannot_be_omitted_or_marked_proved(self):
        for mutate in (lambda value: value["residual_requirements"].pop(),
                       lambda value: value["residual_requirements"][0].update(status="proved")):
            packet = self.packet()
            batch = packet[0]["supervisor"]["batch"]
            mutate(batch)
            batch["batch_cid"] = receiver.codec.cid(receiver.without(batch, "batch_cid"))
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "eight runtime clauses"):
                receiver.receive(*packet)

    def test_integer_false_cannot_grant_authority_or_substitute_for_boolean(self):
        packet = self.packet()
        batch = packet[0]["supervisor"]["batch"]
        batch["proof_authority"] = 0
        batch["batch_cid"] = receiver.codec.cid(receiver.without(batch, "batch_cid"))
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "authority ceiling"):
            receiver.receive(*packet)

    def test_all_26_coherent_controls_preserve_every_original_anchor(self):
        packet = self.packet()
        before = receiver.codec.wire(packet)
        controls = receiver.controls(*packet)
        self.assertEqual(len(controls), 26)
        self.assertEqual(len({row["name"] for row in controls}), 26)
        self.assertTrue(all(row["container_cids_recomputed"] is True and row["rejected"] is True for row in controls))
        self.assertEqual(receiver.codec.wire(packet), before)

    def test_primary_qualification_raw_anchor_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "manifest.json"
            spec = copy.deepcopy(self.spec)
            spec["prior_qualification"]["sha256"] = "0" * 64
            manifest.write_bytes(receiver.codec.wire(spec))
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "fixed independent"):
                receiver.load_input(manifest)

    def test_repinned_selected_result_still_needs_independent_public_commitment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = copy.deepcopy(self.spec)
            changed = copy.deepcopy(self.bodies["native_result"])
            changed["completed"] = False
            raw = receiver.codec.wire(changed)
            body = root / "result.json"
            body.write_bytes(raw)
            spec["native_result"].update(path=str(body), sha256=receiver.codec.sha(raw), bytes=len(raw))
            manifest = root / "manifest.json"
            manifest.write_bytes(receiver.codec.wire(spec))
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "role/anchor"):
                receiver.load_input(manifest)

    def test_read_budget_binds_actual_allocation_to_pin_and_remaining_total(self):
        with tempfile.TemporaryDirectory() as directory:
            body = Path(directory) / "body.json"
            body.write_bytes(b'123456')
            pin = {"bytes": 6, "sha256": receiver.codec.sha(b'123456')}
            with patch.object(receiver, "MAX_TOTAL", 4), patch.object(receiver.codec.OriginalCapture, "read", wraps=receiver.codec.OriginalCapture.read) as read:
                with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "before allocation"):
                    receiver.Capture().take(body, pin)
                self.assertEqual(read.call_args.args[1], 4)
            capture = receiver.Capture()
            capture.take(body, pin)
            body.write_bytes(b'1234567')
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "before allocation"):
                capture.stable()

    def test_all_five_independent_raw_bindings_and_scope_flags_are_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_bytes(receiver.codec.wire(self.spec) + b'\n')
            report = receiver.audit(manifest, root / "output")
            self.assertEqual(report["status"], "passed")
            self.assertEqual((report["input_file_count"], report["batch_page_count"], report["clause_count"], report["mutation_control_count"]), (6, 82, 8, 26))
            self.assertEqual(report["manifest_sha256"], receiver.codec.sha(manifest.read_bytes()))
            self.assertEqual(report["prior_qualification_sha256"], "4583941a4b6e5e557549c5627b3111cd8d4640b9ad5885bc5b809a52506c4cbe")
            for role in receiver.ROLES:
                self.assertEqual(report[role + "_sha256"], self.spec[role]["sha256"])
            for field in receiver.FALSE_FLAGS:
                self.assertIs(report[field], False)
            for field in ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"):
                self.assertIs(type(report[field]), int)
                self.assertEqual(report[field], 0)
            self.assertTrue(report["original_requirement_custody_reconciled"])
            self.assertTrue(report["restart_request_response_bindings_reconciled"])
            self.assertEqual(report["recorded_producer_effort"]["qualification_status"], "historical_producer_claims_only")
            for row in report["input_files"]:
                self.assertEqual(Path(row["path"]).read_bytes(), Path(row["retained_path"]).read_bytes())

    def test_copied_manifest_allows_sibling_output_but_selected_scope_is_protected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_bytes(receiver.codec.wire(self.spec))
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "outside selected"):
                receiver.audit(manifest, INPUT / "unwritten-test-output")
            self.assertFalse((INPUT / "unwritten-test-output").exists())
            (root / "existing").mkdir()
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "fresh output"):
                receiver.audit(manifest, root / "existing")


if __name__ == "__main__":
    unittest.main()
