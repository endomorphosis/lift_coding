"""Independent receiving assertions over selected inert historical SMT@2 bytes."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from smt_v2_controls import receiver


def retained_fixture():
    relative = Path("artifacts/codebase_ir_parallel_qualification/acceptance/20261003-smt-v2-custody-input-01/smt_v2_custody_input.json")
    for root in (Path.cwd().resolve(), *Path(__file__).resolve().parents):
        candidate = root / relative
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("selected frozen SMT@2 receiving fixture unavailable")


INPUT = retained_fixture()


class SmtV2CustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = receiver.document(INPUT.read_bytes())
        cls.documents, cls.sources = {}, []
        for role in receiver.ROLES:
            descriptor = cls.spec[role]
            raw = Path(descriptor["path"]).read_bytes()
            if len(raw) != descriptor["bytes"] or receiver.codec.sha(raw) != descriptor["sha256"]:
                raise AssertionError("frozen SMT fixture pin drift")
            if role.startswith("runtime_"):
                cls.sources.append(raw)
            else:
                cls.documents[role] = receiver.document(raw)

    def packet(self):
        return copy.deepcopy(self.documents)

    def first(self, packet=None):
        return (packet or self.documents)["native_result"]["runs"][0]["cases"][0]

    def repair_outcome(self, value):
        evidence = value["evidence"]
        evidence["request_digest"] = receiver.hashed(value["request"])
        evidence["obligation_digest"] = receiver.hashed(value["request"]["obligation"])
        evidence["content_digest"] = receiver.hashed({key: evidence[key] for key in receiver.IDENTITY_FIELDS})

    def repair_audit(self, packet, role):
        packet["native_result"][receiver.ROLES[role].split("/")[-1] + "_sha256"] = receiver.hashed_raw_document(packet[role])

    def test_actual_golden_population_and_original_stop_dispositions(self):
        value = receiver.receive(self.packet(), self.sources)
        self.assertEqual((len(value["cases"]), len(value["stopped_calls"]), len(value["phase_receipts"]), len(value["wire_fixtures"])), (38, 6, 446, 12))
        self.assertEqual(sum(row["phase_count"] for row in value["cases"][:36]), 396)
        self.assertEqual(sum(row["phase_count"] for row in value["cases"][36:]), 30)
        self.assertEqual([row["phase_count"] for row in value["stopped_calls"]], [1, 1, 3, 3, 9, 3])
        self.assertEqual([row["recorded_stop_kind"] for row in value["stopped_calls"]], ["cancelled", "timeout", "cancelled", "cancelled", "cancelled", "cancelled"])
        self.assertTrue(all(row["returned_result"] is False and row["returned_replay_receipt"] is False for row in value["stopped_calls"]))

    def test_golden_request_and_evidence_hashes_are_independently_stated(self):
        first = self.first()
        value = receiver.outcome(first["outcome"], original_obligation=first["fixture"])
        self.assertEqual(value["request_sha256"], "c5511791f7797bb37e52b641556d46a79cbb95cde929b9cf9e6cf57f116c8097")
        self.assertEqual(value["obligation_sha256"], "2700b4297488af0159363cced4a22dee4234f4f716b96de4bbcd38887ff3b4a6")
        self.assertEqual(value["evidence_identity_sha256"], "0bd4e15f0ea877050116320affa88c48d073664b2922c2db1b4defaddd89181d")
        self.assertEqual(value["declared_bounds"], {"timeout_ms": 5000, "max_memory_bytes": 134217728, "max_steps": 100000, "max_output_bytes": 65536})

    def test_recorded_theorem_category_does_not_hide_disproved_sat_result(self):
        case = self.documents["native_result"]["runs"][0]["cases"][1]
        value = receiver.outcome(case["outcome"], original_obligation=case["fixture"])
        self.assertEqual((value["recorded_disposition"], value["recorded_verdict"]), ("disproved", "sat"))
        self.assertTrue(value["recorded_api_claim_categories"]["theorem_established"])
        self.assertFalse(value["recorded_api_claim_categories"]["is_proved"])
        self.assertFalse(value["solver_verdict_authenticated"])

    def test_separate_injected_wire_corpus_preserves_proved_and_satisfiable(self):
        value = receiver.wire_fixtures(self.documents["wire_before"], self.documents["wire_after"], self.documents["wire_comparison"], self.sources)
        self.assertEqual([row["recorded_disposition"] for row in value], ["proved"] * 6 + ["satisfiable"] * 6)
        self.assertTrue(all(row["caller_request_origin"] == "independent_outer_wire_fixture" for row in value))
        self.assertEqual(value[0]["request_sha256"], "3a32d61da32da47668cd04636c8352933d87d0dfdd096d776199dc224362b950")

    def test_rehashed_request_goal_cannot_replace_independent_original_obligation(self):
        original = self.first()
        changed = copy.deepcopy(original["outcome"])
        changed["request"]["obligation"]["goal"]["kind"] = "lt"
        self.repair_outcome(changed)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "independent original"):
            receiver.outcome(changed, original_obligation=original["fixture"])

    def test_correlated_request_and_evidence_ids_still_bind_original_native_case(self):
        packet = self.packet()
        case = self.first(packet)
        case["outcome"]["request"]["request_id"] = "req:swapped"
        case["outcome"]["evidence"]["request_id"] = "req:swapped"
        self.repair_outcome(case["outcome"])
        with self.assertRaises(receiver.codec.ReceiverRefusal):
            receiver.receive(packet, self.sources)

    def test_complete_original_case_matrix_rejects_omissions_and_duplicates(self):
        for mutate in (lambda rows: rows.pop(), lambda rows: rows.append(copy.deepcopy(rows[0]))):
            packet = self.packet()
            mutate(packet["native_result"]["runs"][-1]["cases"])
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "matrix|population"):
                receiver.receive(packet, self.sources)

    def test_explicit_and_automatic_replay_bind_original_request_and_script(self):
        packet = self.packet()
        self.first(packet)["explicit_replay"]["script_digest"] = "0" * 64
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "replay exact"):
            receiver.receive(packet, self.sources)
        value = copy.deepcopy(self.documents["native_result"]["runs"][0]["cases"][2]["outcome"])
        value["evidence"]["replay"] = None
        with self.assertRaises(receiver.codec.ReceiverRefusal):
            receiver.outcome(value)

    def test_differential_peer_cannot_borrow_primary_backend_identity(self):
        packet = self.packet()
        packet["native_result"]["runs"][0]["cases"][8]["outcome"]["differential_report"]["right"]["result"]["backend_id"] = "z3"
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "backend provider"):
            receiver.receive(packet, self.sources)

    def test_artifact_atoms_or_digest_change_cannot_hide_in_evidence_identity_subset(self):
        value = copy.deepcopy(self.first()["outcome"])
        value["evidence"]["unsat_core"]["atoms"] = ["borrowed_assumption"]
        self.repair_outcome(value)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "artifact content"):
            receiver.outcome(value)

    def test_numeric_boolean_alias_and_kernel_proof_claim_are_refused(self):
        for field, child in (("is_conclusive", 1), ("proof_established", True)):
            value = copy.deepcopy(self.first()["outcome"])
            value["evidence"][field] = child
            self.repair_outcome(value)
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.outcome(value)

    def test_rehashed_phase_audit_still_needs_all_independent_case_population(self):
        packet = self.packet()
        packet["lifecycle_audit"].pop()
        self.repair_audit(packet, "lifecycle_audit")
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "446 phase"):
            receiver.receive(packet, self.sources)

    def test_coherent_phase_memory_and_wrapper_limit_cannot_widen_original_request(self):
        packet = self.packet()
        packet["lifecycle_audit"][0]["request"].update(memory_bytes=268435456, resident_memory_bytes=268435456)
        packet["launch_audit"][0]["argv"][4] = "--as=268435456:268435456"
        for role in ("launch_audit", "lifecycle_audit"):
            self.repair_audit(packet, role)
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "successful case phase"):
            receiver.receive(packet, self.sources)

    def test_phase_output_budget_and_command_joins_are_independent(self):
        for mutate in (lambda value: value["request"].update(max_output_bytes=1),
                       lambda value: value["request"]["argv"].append("--other")):
            packet = self.packet()
            mutate(packet["lifecycle_audit"][0])
            self.repair_audit(packet, "lifecycle_audit")
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.receive(packet, self.sources)

    def test_valid_rehashed_stdin_claim_remains_structural_and_unauthenticated(self):
        # Without the original stdin body, this valid unsigned claim cannot be
        # independently refuted. Passing consistency must retain the gap.
        packet = self.packet()
        packet["lifecycle_audit"][0]["request"]["stdin_sha256"] = "0" * 64
        self.repair_audit(packet, "lifecycle_audit")
        value = receiver.receive(packet, self.sources)
        phase = value["phase_receipts"][0]
        self.assertEqual(phase["stdin_sha256_claim"], "0" * 64)
        self.assertFalse(phase["raw_stdin_available"])
        self.assertFalse(phase["unique_phase_execution_attestation_verified"])
        self.assertEqual(phase["join_basis"], "retained_case_local_order_and_command")

    def test_stop_controls_preserve_no_result_and_distinct_timeout(self):
        for index, field, child in ((0, "returned_result", True), (4, "returned_replay_receipt", True), (1, "expected_kind", "cancelled")):
            packet = self.packet()
            packet["native_result"]["controls"][index][field] = child
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "typed stop"):
                receiver.receive(packet, self.sources)

    def test_rehashed_stop_trigger_needs_independent_audit_counterpart(self):
        packet = self.packet()
        packet["native_result"]["controls"][0]["trigger"]["kind"] = "timeout"
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "independent stop"):
            receiver.receive(packet, self.sources)

    def test_whole_operation_failure_never_returns_partial_success(self):
        for mutate in (lambda value: value.update(status="failed"), lambda value: value["checks"].update(sources_stable=False)):
            packet = self.packet()
            mutate(packet["native_result"])
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "whole selected"):
                receiver.receive(packet, self.sources)

    def test_wire_definitions_unchanged_but_engine_evolution_is_separate(self):
        self.assertEqual(receiver.frozen_wire_sources(*self.sources), list(receiver.WIRE_CLASSES))
        changed = self.sources[1].replace(b"class SmtReplayReceiptV2:", b"class SmtReplayReceiptV2:\n    invented_wire_field = True")
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "wire definition"):
            receiver.frozen_wire_sources(self.sources[0], changed)

    def test_original_wire_order_and_before_anchor_are_independent(self):
        packet = self.packet()
        packet["wire_after"]["cases"].reverse()
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "original before/after"):
            receiver.receive(packet, self.sources)

    def test_all_37_correlated_controls_preserve_original_objects(self):
        packet = self.packet()
        original = copy.deepcopy(packet)
        controls = receiver.mutation_controls(packet, self.sources)
        self.assertEqual(len(controls), 37)
        self.assertEqual(len({row["name"] for row in controls}), 37)
        self.assertTrue(all(row["rejected"] is True and row["independent_anchors_preserved"] is True for row in controls))
        self.assertEqual(packet, original)

    def test_strict_json_rejects_duplicate_keys_nonfinite_and_surrogates(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'{"x":"\\ud800"}', b'{"x":9223372036854775808}'):
            with self.assertRaises(receiver.codec.ReceiverRefusal):
                receiver.document(raw)
        self.assertEqual(receiver.document(b'[1,{"x":0.5}]'), [1, {"x": 0.5}])

    def test_remaining_budget_bounds_read_and_stability_rejects_growth(self):
        capture = receiver.Capture()
        capture.total = receiver.MAX_TOTAL - 3
        path = Path("/bounded-opaque-peer-input")
        with patch.object(receiver.codec.OriginalCapture, "read", return_value=b"abc") as read:
            capture.take(path)
        read.assert_called_once_with(path, 3)
        with patch.object(receiver.codec.OriginalCapture, "read", return_value=b"abcd"):
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "drift"):
                capture.stable()

    def test_fixed_raw_qualification_anchor_rejects_correlated_descriptor_repin(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "manifest.json"
            spec = copy.deepcopy(self.spec)
            spec["prior_qualification"]["sha256"] = "0" * 64
            manifest.write_bytes(receiver.codec.wire(spec))
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "fixed independent"):
                receiver.load_input(manifest)

    def test_mutated_native_result_repin_cannot_replace_immutable_public_anchor(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest = Path(temporary) / "manifest.json"
            spec = copy.deepcopy(self.spec)
            spec["native_result"]["sha256"] = "0" * 64
            manifest.write_bytes(receiver.codec.wire(spec))
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "fixed independent"):
                receiver.load_input(manifest)

    def test_complete_actual_report_bindings_and_false_scope_flags(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            report = receiver.audit(INPUT, output)
            self.assertEqual(report["status"], "passed")
            self.assertTrue(all(report[name] is True for name in receiver.TRUE_FLAGS))
            self.assertTrue(all(report[name] is False for name in receiver.FALSE_FLAGS))
            self.assertEqual((report["input_file_count"], report["mutation_control_count"]), (12, 37))
            for name in ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"):
                self.assertIs(type(report[name]), int)
                self.assertEqual(report[name], 0)
            for role in receiver.ROLES:
                self.assertEqual(report[role + "_sha256"], self.spec[role]["sha256"])
            self.assertEqual(report["manifest_sha256"], receiver.codec.sha(INPUT.read_bytes()))
            self.assertEqual(json.loads((output / "smt_v2_custody.json").read_bytes()), report)
            for row in report["input_files"]:
                self.assertEqual(Path(row["path"]).read_bytes(), Path(row["retained_path"]).read_bytes())

    def test_historical_owner_paths_never_opened_during_receiving(self):
        original = receiver.codec.OriginalCapture.read
        private = INPUT.parent
        seen = []
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            def guarded(path, maximum):
                seen.append(path)
                self.assertTrue(private in path.parents or output in path.parents)
                return original(path, maximum)
            with patch.object(receiver.codec.OriginalCapture, "read", side_effect=guarded):
                receiver.audit(INPUT, output)
        self.assertTrue(seen)

    def test_copied_manifest_parent_allows_sibling_output_but_input_symlink_alias_refuses(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            manifest = base / "copied.json"
            manifest.write_bytes(INPUT.read_bytes())
            report = receiver.audit(manifest, base / "sibling-output")
            self.assertEqual(report["status"], "passed")
            alias = base / "input-alias"
            alias.symlink_to(INPUT.parent, target_is_directory=True)
            prohibited = alias / "must-not-write"
            with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "outside frozen|symlinked"):
                receiver.audit(manifest, prohibited)
            self.assertFalse(prohibited.exists())

    def test_late_retained_copy_drift_refuses_passed_report(self):
        original = receiver.codec.OriginalCapture.read
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "output"
            def drift(path, maximum):
                if output / "inputs" in path.parents:
                    return b"{}"
                return original(path, maximum)
            with patch.object(receiver.codec.OriginalCapture, "read", side_effect=drift):
                with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "retained raw"):
                    receiver.audit(INPUT, output)
            self.assertFalse((output / "smt_v2_custody.json").exists())

    def test_return_code_boolean_alias_cannot_replace_typed_native_zero(self):
        packet = self.packet()
        packet["lifecycle_audit"][0]["result"]["returncode"] = False
        self.repair_audit(packet, "lifecycle_audit")
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "exact recorded native return code"):
            receiver.receive(packet, self.sources)

    def test_differential_classification_and_authority_categories_are_closed(self):
        packet = self.packet()
        packet["native_result"]["runs"][0]["cases"][8]["outcome"]["evidence"]["differential"]["classification"] = "agree_disproved"
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "classification/provider"):
            receiver.receive(packet, self.sources)
        value = copy.deepcopy(self.first()["outcome"])
        value["evidence"]["authority_ceiling"] = "kernel"
        with self.assertRaisesRegex(receiver.codec.ReceiverRefusal, "authority category"):
            receiver.outcome(value)


if __name__ == "__main__":
    unittest.main()
