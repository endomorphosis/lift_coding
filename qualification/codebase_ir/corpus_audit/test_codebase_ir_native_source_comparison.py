from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebase_ir_corpus_audit as audit
import codebase_ir_native_source384_diagnostics as native
import codebase_ir_native_source_comparison as comparison
import test_codebase_ir_native_source384_diagnostics as fixtures

SOURCE = b"def calculate(capacity: int, threshold: int) -> int:\n    return capacity + threshold\n"
EXPECTED = {"kind": "program_expression", "document": {"attributes": {}, "evaluation_order": ["expr:capacity", "expr:threshold"],
    "expression_id": "expr:result", "kind": "binary", "operand_ids": ["expr:capacity", "expr:threshold"], "operator": "+",
    "source_ref_ids": ["source"], "span_ids": [], "symbol_ids": [], "type_ref": "integer"}}


class NativeSourceComparisonTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.comparison_inputs = self.root / "comparison-inputs"
        self.comparison_inputs.mkdir()
        self.manifest = self.comparison_inputs / "manifest.json"
        self.output = self.root / "output"
        self.source = SOURCE
        self.head = {"schema": "codebase-head@1", "repository_id": "repository:authored-test", "generation": 1,
                     "manifest_cid": "authored:manifest", "receipt_cid": "authored:receipt", "snapshot_cid": "authored:snapshot",
                     "ast_revision_id": "authored:revision"}
        learned, zero = fixtures.inference("learned"), fixtures.inference("zero_head")
        learned["result"]["inference"]["rows"][0]["candidate_ir"] = copy.deepcopy(EXPECTED)
        zero["result"]["inference"]["rows"][0]["candidate_ir"] = copy.deepcopy(EXPECTED)
        zero["result"]["inference"]["rows"][0]["candidate_ir"]["document"].update(operator="!=", type_ref="boolean")
        baseline = fixtures.baseline(EXPECTED)
        baseline["source_head"] = copy.deepcopy(self.head)
        qualification = dict.fromkeys(native.QUALIFICATION_FIELDS, None)
        qualification.update(schema="codebase-source384-acceptance@1", criterion="RPI-011", profile="codebase_ir/source_conditioned_384_v1",
            checkpoint={"artifact": {"bytes": 1, "sha256": "5" * 64}, "checkpoint_sha256": "f" * 64, "child_id": "authored:child", "parent_id": "authored:parent"},
            training_executed=False, scope_limits=["authored schema control, not a model execution"], production_acceptance="open",
            blocking_dependencies=[], seconds=0.5, tests=1, skips=0)
        self.documents = {"learned": learned, "zero_head": zero, "source_label_baseline": baseline, "qualification": qualification}
        self.replay = {"archived_owner_open_mode": "read_only", **qualification["checkpoint"], "source_head": copy.deepcopy(self.head),
            "producer": copy.deepcopy(learned["result"]["producer"]), "embedding_assets": [], "training_executed": False,
            "promotion_performed": False, "authority": dict.fromkeys({"admitted", "behavioral_satisfaction", "promotion_performed",
                "proof_authority", "source_runtime_semantics_verified"}, False), "rows": [{"id": "a" * 64, "source_text": SOURCE.decode()}]}
        self.serial = 0
        self.bind_source()
        self.write_all()

    def write(self, path, value):
        raw = audit._canonical(value) + b"\n"
        path.write_bytes(raw)
        return {"path": str(path), "sha256": audit._sha(raw), "size_bytes": len(raw)}

    def pin(self, path):
        raw = path.read_bytes()
        return {"path": str(path), "sha256": audit._sha(raw), "size_bytes": len(raw)}

    def row(self, role):
        return self.documents[role]["result"]["inference"]["rows"][0]

    def bind_source(self):
        sha = audit._sha(self.source)
        self.replay["rows"][0]["source_text"] = self.source.decode()
        for role in native.ROLES[:2]:
            row = self.row(role)
            row["source_sha256"] = row["source_contract"]["source_sha256"] = sha
            row["source_contract"]["candidate_sha256"] = audit._sha(audit._canonical(row["candidate_ir"]))
            row["source_contract"]["source_binding"] = {"source_sha256": sha, "spans": [
                {"span_id": "whole-function", "start_byte": 0, "end_byte": len(self.source) - 1, "sha256": audit._sha(self.source[:-1])}]}
        row = self.documents["source_label_baseline"]["lake"]["rows"][0]
        row["source_sha256"] = row["source_qualification"]["source_sha256"] = sha
        row["source_qualification"]["source_binding"] = copy.deepcopy(self.row("learned")["source_contract"]["source_binding"])

    def write_all(self):
        self.serial += 1
        exports = {role: self.write(self.inputs / (role + ".json"), value) for role, value in self.documents.items()}
        replay_path = self.inputs / "replay-identity.json"
        replay_pin = self.write(replay_path, self.replay)
        public = {"schema": "codebase-source384-acceptance-evidence@1", "files": [
            {"path": native.SELECTORS[role], "sha256": pin["sha256"], "bytes": pin["size_bytes"]} for role, pin in exports.items()]}
        public["files"].append({"path": comparison.REPLAY_SELECTOR, "sha256": replay_pin["sha256"], "bytes": replay_pin["size_bytes"]})
        public_pin = self.write(self.inputs / "public-manifest.json", public)
        self.native_spec = {"schema": native.INPUT_SCHEMA, "release": {"repository": "datasets", "commit": "0" * 40},
                            "public_manifest": public_pin, "exports": exports}
        native_input_pin = self.write(self.inputs / "native-input.json", self.native_spec)
        self.prior_output = self.root / ("prior-" + str(self.serial))
        self.prior = native.evaluate(Path(native_input_pin["path"]), self.prior_output)
        self.assertEqual(self.prior["status"], "passed")
        self.spec = {"schema": comparison.INPUT_SCHEMA, "diagnostics_input": native_input_pin,
                     "diagnostics": self.pin(self.prior_output / "native_source384_diagnostics.json"),
                     "source_replay": replay_pin, "public_manifest": public_pin}
        self.write(self.manifest, self.spec)

    def refused(self, **kwargs):
        try:
            report = comparison.evaluate(self.manifest, self.output, **kwargs)
        except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError):
            return
        self.assertEqual(report["status"], "refused")
        self.assertTrue(all(report[key] is False for key in comparison.FALSE_FLAGS | (comparison.TRUE_FLAGS - {"unknown_pretraining_exposure"})))
        self.assertTrue(report["unknown_pretraining_exposure"])

    def test_exact_source_fragment_and_custody_are_rederived_without_model_truth_claims(self):
        before = {path: path.read_bytes() for path in self.inputs.iterdir()}
        report = comparison.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(all(report[key] is True for key in comparison.TRUE_FLAGS))
        self.assertTrue(all(report[key] is False for key in comparison.FALSE_FLAGS))
        record = report["records"][0]
        self.assertEqual(record["expected_native_fragment"], EXPECTED)
        self.assertEqual(record["function_binding"]["end_byte"], 84)
        self.assertTrue(record["returned_mode_comparisons"]["learned"]["exact_fragment_match"])
        self.assertFalse(record["returned_mode_comparisons"]["zero_head"]["exact_fragment_match"])
        self.assertEqual(report["mode_metrics"]["learned"]["matched_fragment_count"], 1)
        self.assertEqual(report["mode_metrics"]["zero_head"]["matched_fragment_count"], 0)
        self.assertTrue(record["source_label_baseline"]["candidate_digest_matches_source_fragment"])
        self.assertFalse(record["source_label_baseline"]["mapped_to_final_scorer_model_off"])
        self.assertNotEqual(record["returned_mode_identity"]["learned"]["claimed_model_head_sha256"], report["captured_source_head_canonical_sha256"])
        self.assertEqual(record["source_target"]["function"]["parameters"], [{"name": "capacity", "sort": "Int"}, {"name": "threshold", "sort": "Int"}])
        self.assertIn("boundary unknown", record["native_output_stage"])
        self.assertEqual((self.output / record["source_export"]).read_bytes(), SOURCE)
        self.assertEqual((self.output / "native-diagnostics-rederived/native_source384_diagnostics.json").read_bytes(), Path(self.spec["diagnostics"]["path"]).read_bytes())
        for desc in report["retained_files"]:
            body = (self.output / desc["path"]).read_bytes()
            self.assertEqual((audit._sha(body), len(body)), (desc["sha256"], desc["size_bytes"]))
        self.assertEqual(before, {path: path.read_bytes() for path in self.inputs.iterdir()})

    def test_coherently_repinned_wrong_operator_operand_symbol_sort_and_context_are_visible(self):
        mutations = {"operator": "-", "operand_ids": ["expr:threshold", "expr:capacity"], "symbol_ids": ["invented:symbol"],
                     "type_ref": "boolean", "expression_id": "wrong:result", "source_ref_ids": ["other:source"], "attributes": {"invented": True}}
        for key, value in mutations.items():
            with self.subTest(field=key):
                original = copy.deepcopy(self.row("learned")["candidate_ir"])
                self.row("learned")["candidate_ir"]["document"][key] = value
                if key == "operand_ids":
                    self.row("learned")["candidate_ir"]["document"]["evaluation_order"] = value
                self.bind_source()
                self.write_all()
                destination = self.root / ("mutation-output-" + key)
                report = comparison.evaluate(self.manifest, destination)
                self.assertEqual(report["status"], "passed")
                result = report["records"][0]["returned_mode_comparisons"]["learned"]
                self.assertFalse(result["exact_fragment_match"])
                self.assertFalse(result["checks"][key + "_match"])
                self.assertFalse(report["source_semantics_verified"])
                self.row("learned")["candidate_ir"] = original

    def test_wrong_evaluation_order_is_unsupported_and_cannot_be_counted_as_match(self):
        self.row("learned")["candidate_ir"]["document"]["evaluation_order"].reverse()
        self.bind_source()
        self.write_all()
        report = comparison.evaluate(self.manifest, self.output)
        self.assertIsNone(report["records"][0]["returned_mode_comparisons"]["learned"]["exact_fragment_match"])
        self.assertEqual(report["mode_metrics"]["learned"]["unsupported_comparison_count"], 1)

    def test_unrecognized_native_envelope_is_retained_without_codec_conversion(self):
        self.row("learned")["candidate_ir"] = {"kind": "other_native_expression", "document": {"raw": "unchanged"}}
        self.bind_source()
        self.write_all()
        report = comparison.evaluate(self.manifest, self.output)
        self.assertEqual(report["records"][0]["returned_mode_identity"]["learned"]["returned_candidate"], self.row("learned")["candidate_ir"])
        self.assertEqual(report["records"][0]["returned_mode_comparisons"]["learned"]["status"], "unsupported_source_or_native_codec")

    def test_exact_multibyte_source_and_comparison_result_sort_are_independent_labels(self):
        self.source = "def calculate(café: int, threshold: int) -> bool:\n    return café < threshold\n".encode()
        candidate = self.row("learned")["candidate_ir"]["document"]
        candidate.update(operator="<", type_ref="boolean", operand_ids=["expr:café", "expr:threshold"],
                         evaluation_order=["expr:café", "expr:threshold"])
        baseline = self.documents["source_label_baseline"]["lake"]["rows"][0]
        baseline["candidate_sha256"] = baseline["source_qualification"]["candidate_sha256"] = audit._sha(audit._canonical(self.row("learned")["candidate_ir"]))
        self.bind_source()
        self.write_all()
        report = comparison.evaluate(self.manifest, self.output)
        record = report["records"][0]
        self.assertEqual(record["function_binding"]["end_byte"], len(self.source) - 1)
        self.assertEqual(record["source_target"]["function"]["returns"], "Bool")
        self.assertEqual(record["expected_native_fragment"]["document"]["operator"], "<")
        self.assertTrue(record["returned_mode_comparisons"]["learned"]["exact_fragment_match"])
        self.assertEqual((self.output / record["source_export"]).read_bytes(), self.source)

    def test_source_label_baseline_corruption_cannot_change_learned_source_comparison(self):
        baseline = self.documents["source_label_baseline"]["lake"]["rows"][0]
        baseline["candidate_sha256"] = baseline["source_qualification"]["candidate_sha256"] = "8" * 64
        self.write_all()
        report = comparison.evaluate(self.manifest, self.output)
        self.assertTrue(report["records"][0]["returned_mode_comparisons"]["learned"]["exact_fragment_match"])
        self.assertFalse(report["records"][0]["source_label_baseline"]["candidate_digest_matches_source_fragment"])
        self.assertEqual(report["source_label_baseline_metrics"]["candidate_digest_match_count"], 0)

    def test_literal_and_effectful_source_remain_explicitly_unsupported_by_native_adapter(self):
        for expression in ("capacity + 1", "effectful(capacity)"):
            with self.subTest(expression=expression):
                self.source = ("def calculate(capacity: int, threshold: int) -> int:\n    return " + expression + "\n").encode()
                self.bind_source()
                self.write_all()
                report = comparison.evaluate(self.manifest, self.root / ("unsupported-" + str(self.serial)))
                self.assertEqual(report["status"], "passed")
                self.assertFalse(report["source_structural_comparison_available"])
                self.assertEqual(report["records"][0]["native_fragment_projection_status"], "unsupported")
                self.assertEqual(report["mode_metrics"]["learned"]["supported_comparison_count"], 0)
                self.assertFalse(report["source_semantics_verified"])

    def test_missing_mode_is_explicit_and_duplicate_source_samples_are_not_independent(self):
        self.row("zero_head")["id"] = "8" * 64
        self.replay["rows"].append({"id": "8" * 64, "source_text": SOURCE.decode()})
        self.write_all()
        report = comparison.evaluate(self.manifest, self.output)
        self.assertEqual(report["historical_case_count"], 2)
        self.assertEqual(report["mode_metrics"]["learned"]["missing_mode_count"], 1)
        self.assertEqual(report["mode_metrics"]["zero_head"]["missing_mode_count"], 1)
        self.assertFalse(report["independent_samples_established"])

    def test_replay_missing_wrong_and_duplicate_ids_refuse_even_with_fresh_public_pins(self):
        original = copy.deepcopy(self.replay["rows"])
        for rows in ([], [{"id": "8" * 64, "source_text": SOURCE.decode()}], original + original):
            with self.subTest(rows=len(rows)):
                self.replay["rows"] = copy.deepcopy(rows)
                self.write_all()
                self.refused()

    def test_repinned_raw_source_change_without_native_source_join_refuses(self):
        self.replay["rows"][0]["source_text"] = SOURCE.decode().replace(" + ", " - ")
        self.write_all()
        self.refused()

    def test_correlated_native_source_sha_without_exact_replay_bytes_refuses(self):
        for role in native.ROLES[:2]:
            row = self.row(role)
            row["source_sha256"] = row["source_contract"]["source_sha256"] = "8" * 64
            row["source_contract"]["source_binding"]["source_sha256"] = "8" * 64
        baseline = self.documents["source_label_baseline"]["lake"]["rows"][0]
        baseline["source_sha256"] = baseline["source_qualification"]["source_sha256"] = "8" * 64
        baseline["source_qualification"]["source_binding"]["source_sha256"] = "8" * 64
        self.write_all()
        self.refused()

    def test_correlated_span_byte_hash_and_duplicate_span_changes_refuse(self):
        spans = self.row("learned")["source_contract"]["source_binding"]["spans"]
        original = copy.deepcopy(spans)
        for changed in ({**original[0], "start_byte": 1}, {**original[0], "end_byte": 86}, {**original[0], "sha256": "8" * 64}):
            with self.subTest(span=changed):
                spans[:] = [changed]
                self.write_all()
                self.refused()
        spans[:] = original + original
        self.write_all()
        self.refused()

    def test_public_child_and_outer_raw_pin_are_both_required(self):
        path = Path(self.spec["source_replay"]["path"])
        path.write_bytes(path.read_bytes() + b" ")
        self.refused()
        self.spec["source_replay"] = self.pin(path)
        self.write(self.manifest, self.spec)
        self.refused()

    def test_counterparty_report_repin_does_not_substitute_for_complete_rederivation(self):
        self.prior["source_bytes_available"] = True
        self.spec["diagnostics"] = self.write(Path(self.spec["diagnostics"]["path"]), self.prior)
        self.write(self.manifest, self.spec)
        self.refused()
        self.assertTrue(self.output.exists())

    def test_forged_counterparty_head_records_refuse_before_comparison(self):
        self.prior["paired_records"][0]["rows"]["learned"]["head_sha256"] = audit._sha(audit._canonical(self.head))
        self.spec["diagnostics"] = self.write(Path(self.spec["diagnostics"]["path"]), self.prior)
        self.write(self.manifest, self.spec)
        self.refused()

    def test_numerical_head_digest_equal_to_source_metadata_digest_does_not_change_domains(self):
        digest = audit._sha(audit._canonical(self.head))
        for role in native.ROLES[:2]:
            self.row(role)["head_sha256"] = digest
        self.write_all()
        report = comparison.evaluate(self.manifest, self.output)
        self.assertEqual(report["records"][0]["returned_mode_identity"]["learned"]["claimed_model_head_sha256"], digest)
        self.assertEqual(report["captured_source_head_canonical_sha256"], digest)
        self.assertFalse(report["source_head_authority_verified"])
        self.assertFalse(report["model_head_state_validated"])

    def test_source_head_metadata_checkpoint_and_producer_join_are_required(self):
        original = copy.deepcopy(self.replay)
        for key, value in (("source_head", {**self.head, "generation": 2}), ("checkpoint_sha256", "8" * 64), ("producer", {"other": True})):
            with self.subTest(field=key):
                self.replay = {**copy.deepcopy(original), key: value}
                self.write_all()
                self.refused()

    def test_unknown_exposure_and_recorded_target_access_cannot_upgrade_quality(self):
        self.row("learned").pop("teacher_forcing")
        self.row("learned")["target_access"] = True
        self.write_all()
        report = comparison.evaluate(self.manifest, self.output)
        row = report["records"][0]["returned_mode_identity"]["learned"]
        self.assertEqual(row["teacher_forcing"]["disposition"], "unknown")
        self.assertTrue(row["target_access"]["value"])
        self.assertFalse(row["target_access"]["independently_verified"])
        self.assertTrue(report["unknown_pretraining_exposure"])
        self.assertFalse(report["learned_quality_improvement_verified"])

    def test_old_retained_copy_is_checked_even_when_original_body_is_unchanged(self):
        (self.prior_output / "inputs/learned.json").write_bytes(b"{}\n")
        self.refused()

    def test_budgets_cover_nested_native_inputs_and_prior_retained_copies_before_allocation(self):
        for limits in (replace(comparison.DEFAULT_LIMITS, max_files=16), replace(comparison.DEFAULT_LIMITS, max_total_bytes=1),
                       replace(comparison.DEFAULT_LIMITS, max_source_bytes=84), replace(comparison.DEFAULT_LIMITS, max_total_source_bytes=84)):
            with self.subTest(limits=limits):
                with patch.object(comparison.native, "evaluate", side_effect=AssertionError("nested reader must not start")):
                    self.refused(limits=limits)
                self.assertFalse(self.output.exists())

    def test_declared_oversized_body_is_refused_without_opening_it(self):
        self.spec["source_replay"]["size_bytes"] = comparison.DEFAULT_LIMITS.max_file_bytes + 1
        self.write(self.manifest, self.spec)
        self.refused()
        self.assertFalse(self.output.exists())

    def test_late_source_copy_mutation_refuses_all_verified_flags(self):
        real_copy = comparison._copy
        def mutate(path, raw):
            real_copy(path, raw)
            if path.parent.name == "sources":
                path.write_bytes(raw[:-1] + b" ")
        with patch.object(comparison, "_copy", side_effect=mutate):
            self.refused()
        self.assertTrue(self.output.exists())

    def test_late_original_native_body_mutation_refuses_after_rederivation(self):
        real_copy = comparison._copy
        changed = False
        def mutate(path, raw):
            nonlocal changed
            real_copy(path, raw)
            if not changed:
                Path(self.native_spec["exports"]["learned"]["path"]).write_bytes(b"{}\n")
                changed = True
        with patch.object(comparison, "_copy", side_effect=mutate):
            self.refused()
        self.assertTrue(changed)

    def test_outer_manifest_closed_schema_and_input_aliases_refuse(self):
        self.spec["extra"] = "not allowed"
        self.write(self.manifest, self.spec)
        self.refused()
        self.spec.pop("extra")
        self.spec["source_replay"] = self.spec["public_manifest"]
        self.write(self.manifest, self.spec)
        self.refused()

    def test_non_utf8_source_text_is_typed_refusal(self):
        self.replay["rows"][0]["source_text"] = "\ud800"
        path = Path(self.spec["source_replay"]["path"])
        path.write_bytes((json.dumps(self.replay, ensure_ascii=True) + "\n").encode())
        replay_pin = self.pin(path)
        public_path = Path(self.spec["public_manifest"]["path"])
        public = json.loads(public_path.read_bytes())
        next(row for row in public["files"] if row["path"] == comparison.REPLAY_SELECTOR).update(sha256=replay_pin["sha256"], bytes=replay_pin["size_bytes"])
        public_pin = self.write(public_path, public)
        self.native_spec["public_manifest"] = public_pin
        native_pin = self.write(Path(self.spec["diagnostics_input"]["path"]), self.native_spec)
        self.serial += 1
        prior_output = self.root / ("prior-" + str(self.serial))
        native.evaluate(Path(native_pin["path"]), prior_output)
        self.spec.update(source_replay=replay_pin, public_manifest=public_pin, diagnostics_input=native_pin,
                         diagnostics=self.pin(prior_output / "native_source384_diagnostics.json"))
        self.write(self.manifest, self.spec)
        self.refused()

    def test_output_inside_immutable_source_scope_refuses(self):
        with self.assertRaises(audit.AuditInputError):
            comparison.evaluate(self.manifest, self.inputs / "new-output")
        self.assertFalse((self.inputs / "new-output").exists())


if __name__ == "__main__":
    unittest.main()
