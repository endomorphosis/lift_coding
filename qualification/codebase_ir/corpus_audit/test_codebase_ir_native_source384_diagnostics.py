from __future__ import annotations

import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_native_source384_diagnostics as native


def contract(source_sha, candidate_sha):
    value = dict.fromkeys(native.CONTRACT_FIELDS, None)
    value.update(schema="security-source-program-binding-384/v2", source_sha256=source_sha, candidate_sha256=candidate_sha,
                 base_qualification_sha256="e" * 64, assumptions=[], qualification_gaps=[], projections=[], checks=[],
                 status="recorded_authored_test_contract", qualified=True, provider_calls=0, solver_calls=0)
    for key in ("executes_source", "completion_authority", "execution_authority", "proof_authority",
                "security_specification_inferred", "source_semantics_verified", "whole_program_semantics_verified"):
        value[key] = False
    return value


def inference(role):
    candidate = {"kind": "program_expression", "document": {"kind": "binary", "attributes": {}, "expression_id": "result",
        "operator": "+" if role == "learned" else "!=", "type_ref": "integer" if role == "learned" else "boolean",
        "operand_ids": ["left", "right"], "evaluation_order": ["left", "right"], "source_ref_ids": ["source"], "span_ids": [], "symbol_ids": []}}
    row = {key: False for key in native.INFERENCE_FLAGS}
    row.update(id="a" * 64, source_sha256="b" * 64, head_sha256="c" * 64, projection_sha256="d" * 64, candidate_ir=candidate,
               predicted_classes=[0, 0, 1, 1], projected_embedding=[0.0] * 384, continue_planning=True, reason=None,
               status="authored_native_codec_example", source_contract=contract("b" * 64, audit._sha(audit._canonical(candidate))),
               target_access=False, teacher_forcing=False, weight_ablation="zero_head" if role == "zero_head" else None)
    inf = {key: False for key in native.INFERENCE_FLAGS}
    inf.update(schema="structured-source-384-autoencoder/v1", dimension=384, domain_id="security_ir", checkpoint_sha256="f" * 64,
               source_contracts_checked=True, rows=[row])
    return {"result": {"inference": inf, "producer": {"scope": "authored_test_no_model_execution"}, "embedding_assets": [], "training_executed": False},
            "worker_receipt": {"device": "cpu", "elapsed_ms": 100, "input_sha256": "1" * 64, "output_sha256": "2" * 64,
                "memory_enforcement": "unverified_recorded_example", "memory_mb": 64, "provider_calls": 0,
                "returncode": 0, "workspace_cleaned": True}}


def baseline(candidate):
    row = dict.fromkeys(native.BASELINE_ROW_FIELDS, False)
    row.update(id="a" * 64, source_sha256="b" * 64, candidate_sha256=audit._sha(audit._canonical(candidate)),
               lean_declarations_sha256="3" * 64, program_sha256="4" * 64, reason=None,
               source_qualification=contract("b" * 64, audit._sha(audit._canonical(candidate))),
               parser_status="recorded_pass", lake_status="recorded_pass", lowering={})
    lake_fields = {"admitted", "all_candidates_compiled", "assumptions", "backend_executed", "claim_proved", "completion_authority",
        "count", "execution", "execution_authority", "formalized", "input_sha256", "lean_source", "lean_source_sha256", "library",
        "producer", "promotion_performed", "proof_authority", "rows", "schema", "scope", "security_specification_inferred",
        "source_replay_passed", "source_semantics_verified", "status", "supported_count", "tool_binary_sha256", "tool_pin_scope",
        "whole_program_semantics_verified"}
    lake = dict.fromkeys(lake_fields, False)
    lake.update(schema="source-program-384-lake/v1", count=1, supported_count=1, rows=[row], status="recorded_pass")
    return {"embeddings_executed": False, "lake": lake, "learned_prediction_claimed": False, "model_executed": False,
            "route": "deterministic_source_label_baseline_not_model_inference", "source_head": {"schema": "authored_test_head"},
            "target_origin": "authored_test_source_label_not_independent_truth", "training_executed": False}


class NativeSource384DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inputs = self.root / "input"
        self.inputs.mkdir()
        learned = inference("learned")
        qualification = dict.fromkeys(native.QUALIFICATION_FIELDS, None)
        qualification.update(schema="codebase-source384-acceptance@1", criterion="RPI-011", profile="codebase_ir/source_conditioned_384_v1",
            checkpoint={"artifact": {"bytes": 1, "sha256": "5" * 64}, "checkpoint_sha256": "f" * 64, "child_id": "authored:child", "parent_id": "authored:parent"},
            training_executed=False, scope_limits=["authored schema test, not numerical output"], production_acceptance="open", blocking_dependencies=[],
            seconds=0.5, tests=1, skips=0)
        self.documents = {"learned": learned, "zero_head": inference("zero_head"),
                          "source_label_baseline": baseline(learned["result"]["inference"]["rows"][0]["candidate_ir"]),
                          "qualification": qualification}
        self.manifest = self.inputs / "input.json"
        self.output = self.root / "output"
        self.write_all()

    def write(self, path, value):
        raw = audit._canonical(value) + b"\n"
        path.write_bytes(raw)
        return {"path": str(path), "sha256": audit._sha(raw), "size_bytes": len(raw)}

    def write_all(self):
        exports = {role: self.write(self.inputs / (role + ".json"), value) for role, value in self.documents.items()}
        public = {"schema": "codebase-source384-acceptance-evidence@1", "files": [
            {"path": native.SELECTORS[role], "sha256": pin["sha256"], "bytes": pin["size_bytes"]} for role, pin in exports.items()]}
        public["files"].append({"path": "other/unselected.json", "sha256": "9" * 64, "bytes": 9_999_999})
        self.spec = {"schema": native.INPUT_SCHEMA, "release": {"repository": "datasets", "commit": "0" * 40},
                     "public_manifest": self.write(self.inputs / "public_manifest.json", public), "exports": exports}
        self.write(self.manifest, self.spec)

    def row(self, role):
        return self.documents[role]["result"]["inference"]["rows"][0]

    def refused(self, **kwargs):
        with self.assertRaises((audit.AuditInputError, OSError, ValueError, TypeError, KeyError)):
            native.evaluate(self.manifest, self.output, **kwargs)
        self.assertFalse(self.output.exists())

    def test_returns_recorded_native_candidates_with_no_accuracy_or_execution_claim(self):
        report = native.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["row_counts"], {"learned": 1, "zero_head": 1, "source_label_baseline": 1})
        self.assertEqual(report["complete_three_role_record_count"], 1)
        row = report["paired_records"][0]
        self.assertFalse(row["returned_learned_zero_candidates_equal"])
        self.assertTrue(row["learned_matches_source_label_candidate_digest"])
        self.assertFalse(row["zero_matches_source_label_candidate_digest"])
        self.assertIsNone(row["source_derived_accuracy"])
        self.assertTrue(row["rows"]["learned"]["recorded_source_contract"]["qualified_claim"])
        self.assertFalse(row["rows"]["learned"]["recorded_source_contract"]["claim_truth_verified"])
        self.assertTrue(report["source_label_baseline_separate"])
        self.assertFalse(report["mode_summaries"]["source_label_baseline"]["mapped_to_final_scorer_model_off"])
        self.assertTrue(all(report[key] is False for key in native.FALSE_FLAGS))
        self.assertTrue(report["unknown_pretraining_exposure"])
        self.assertEqual(len(report["unselected_public_children"]), 1)
        for desc in report["retained_files"]:
            self.assertEqual(audit._sha((self.output / desc["path"]).read_bytes()), desc["sha256"])

    def test_public_manifest_commitment_cannot_be_replaced_by_child_only_repin(self):
        self.row("learned")["status"] = "edited"
        self.spec["exports"]["learned"] = self.write(self.inputs / "learned.json", self.documents["learned"])
        self.write(self.manifest, self.spec)
        self.refused()

    def test_correlated_candidate_and_contract_changes_are_visible_without_truth_upgrade(self):
        row = self.row("learned")
        row["candidate_ir"]["document"]["operator"] = "-"
        row["source_contract"]["candidate_sha256"] = audit._sha(audit._canonical(row["candidate_ir"]))
        self.write_all()
        report = native.evaluate(self.manifest, self.output)
        self.assertFalse(report["paired_records"][0]["learned_matches_source_label_candidate_digest"])
        self.assertFalse(report["source_derived_accuracy_available"])

    def test_candidate_repin_without_internal_digest_join_is_refused(self):
        self.row("learned")["candidate_ir"]["document"]["operator"] = "-"
        self.write_all()
        self.refused()

    def test_correlated_wrong_source_with_same_id_refuses_cross_role_join(self):
        row = self.row("zero_head")
        row["source_sha256"] = row["source_contract"]["source_sha256"] = "8" * 64
        self.write_all()
        self.refused()

    def test_wrong_contract_source_refuses_even_after_all_external_pins_change(self):
        self.row("learned")["source_contract"]["source_sha256"] = "8" * 64
        self.write_all()
        self.refused()

    def test_source_generation_and_projection_pairing_are_exact(self):
        for field in ("head_sha256", "projection_sha256"):
            with self.subTest(field=field):
                old = self.row("zero_head")[field]
                self.row("zero_head")[field] = "8" * 64
                self.write_all()
                self.refused()
                self.row("zero_head")[field] = old

    def test_checkpoint_must_join_qualification_and_both_mode_exports(self):
        self.documents["qualification"]["checkpoint"]["checkpoint_sha256"] = "8" * 64
        self.write_all()
        self.refused()

    def test_duplicate_native_id_cannot_inflate_population(self):
        rows = self.documents["learned"]["result"]["inference"]["rows"]
        rows.append(copy.deepcopy(rows[0]))
        self.write_all()
        self.refused()

    def test_missing_mode_record_is_explicit_without_inventing_pair_success(self):
        row = self.row("zero_head")
        row["id"] = "8" * 64
        self.write_all()
        report = native.evaluate(self.manifest, self.output)
        self.assertEqual(report["record_count"], 2)
        self.assertEqual(report["complete_three_role_record_count"], 0)
        self.assertTrue(all(row["missing_roles"] for row in report["paired_records"]))

    def test_missing_target_teacher_and_ablation_metadata_remain_unknown(self):
        for key in native.OPTIONAL_METADATA:
            self.row("learned").pop(key)
        self.write_all()
        report = native.evaluate(self.manifest, self.output)
        row = report["paired_records"][0]["rows"]["learned"]
        self.assertEqual(row["metadata"]["target_access"]["disposition"], "unknown")
        self.assertEqual(row["metadata"]["teacher_forcing"]["disposition"], "unknown")
        self.assertEqual(row["ablation"]["disposition"], "unknown")

    def test_recorded_teacher_access_and_wrong_ablation_are_adverse_metadata(self):
        row = self.row("learned")
        row.update(target_access=True, teacher_forcing=True, weight_ablation="zero_head")
        self.write_all()
        report = native.evaluate(self.manifest, self.output)
        row = report["paired_records"][0]["rows"]["learned"]
        self.assertIn("recorded_target_access", row["findings"])
        self.assertIn("recorded_teacher_forcing", row["findings"])
        self.assertIn("recorded_ablation_role_mismatch", row["findings"])
        self.assertFalse(report["learned_weight_dependence_verified"])

    def test_unsupported_candidate_codec_is_retained_with_explicit_disposition(self):
        row = self.row("learned")
        row["candidate_ir"] = {"kind": "future_native_form", "document": {"unsupported": "retained"}}
        row["source_contract"]["candidate_sha256"] = audit._sha(audit._canonical(row["candidate_ir"]))
        self.write_all()
        report = native.evaluate(self.manifest, self.output)
        self.assertEqual(report["codec_counts"]["learned"]["unsupported_codec"], 1)
        self.assertEqual(report["paired_records"][0]["rows"]["learned"]["returned_candidate"], row["candidate_ir"])

    def test_baseline_is_never_relabeled_as_numerical_model_off(self):
        self.documents["source_label_baseline"]["model_executed"] = True
        self.write_all()
        self.refused()

    def test_baseline_count_boolean_or_excess_population_is_refused(self):
        for value in (True, 2):
            with self.subTest(value=value):
                self.documents["source_label_baseline"]["lake"]["count"] = value
                self.write_all()
                self.refused()

    def test_authority_flags_and_metadata_types_are_strict(self):
        self.row("learned")["admitted"] = 0
        self.write_all()
        self.refused()
        self.row("learned")["admitted"] = False
        self.row("learned")["target_access"] = 0
        self.write_all()
        self.refused()

    def test_declared_native_layout_is_not_inferred_from_dimensions(self):
        self.row("learned")["projected_embedding"].pop()
        self.write_all()
        self.refused()

    def test_huge_json_integer_is_a_typed_refusal_without_float_overflow(self):
        self.row("learned")["projected_embedding"][0] = 10**400
        self.write_all()
        self.refused()
        self.row("learned")["projected_embedding"][0] = 0.0
        self.documents["qualification"]["seconds"] = 10**400
        self.write_all()
        self.refused()

    def test_strict_json_duplicate_unknown_and_nonfinite_inputs_refuse(self):
        original = self.manifest.read_bytes()
        for raw in (b'{"schema":"x","schema":"y"}', b'{"schema":NaN}', original[:-2] + b',"extra":1}\n'):
            with self.subTest(raw=raw[:40]):
                self.manifest.write_bytes(raw)
                self.refused()

    def test_alias_symlink_and_fifo_inputs_are_refused(self):
        path = self.inputs / "learned.json"
        original = path.read_bytes()
        path.unlink()
        path.symlink_to(self.inputs / "zero_head.json")
        self.refused()
        path.unlink()
        os.mkfifo(path)
        self.refused()
        path.unlink()
        path.write_bytes(original)
        self.spec["exports"]["zero_head"] = self.spec["exports"]["learned"]
        self.write(self.manifest, self.spec)
        self.refused()

    def test_descriptor_and_total_budgets_refuse_before_output(self):
        self.spec["exports"]["learned"]["size_bytes"] = 1
        self.write(self.manifest, self.spec)
        self.refused()
        self.write_all()
        self.refused(limits=native.Limits(max_total_bytes=100))
        self.refused(limits=native.Limits(max_files=5))

    def test_output_cannot_overwrite_inputs_or_existing_reports(self):
        with self.assertRaises(audit.AuditInputError):
            native.evaluate(self.manifest, self.inputs / "nested-output")
        self.assertFalse((self.inputs / "nested-output").exists())
        self.output.mkdir()
        with self.assertRaises(audit.AuditInputError):
            native.evaluate(self.manifest, self.output)

    def test_late_original_drift_cannot_publish_success(self):
        original = native.Pins.recheck
        calls = 0
        def changed(pins):
            nonlocal calls
            calls += 1
            if calls == 2:
                path = self.inputs / "learned.json"
                path.write_bytes(path.read_bytes() + b" ")
            return original(pins)
        with patch.object(native.Pins, "recheck", changed):
            report = native.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["input_files_unchanged"])

    def test_late_retained_copy_drift_cannot_publish_success(self):
        regular = final.Capture.regular
        changed = False
        def read(path, maximum):
            nonlocal changed
            if path == self.output / "inputs/learned.json" and not changed:
                changed = True
                path.write_bytes(path.read_bytes() + b" ")
            return regular(path, maximum)
        with patch.object(final.Capture, "regular", read):
            report = native.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["native_outputs_retained_unmodified"])

    def test_reports_and_raw_retention_are_deterministic(self):
        native.evaluate(self.manifest, self.output)
        other = self.root / "second"
        native.evaluate(self.manifest, other)
        for path in self.output.rglob("*"):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (other / path.relative_to(self.output)).read_bytes())


if __name__ == "__main__":
    unittest.main()
