from __future__ import annotations

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
from codebase_ir_final_targets import derive_source


class FinalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        shutil.copytree(Path(__file__).parent / "fixtures/final_protocol", self.bundle)
        self.spec = self.bundle / "manifest.json"
        self.sequence = 0

    def document(self, name):
        return json.loads((self.bundle / name).read_bytes())

    def save(self, name, value):
        raw = audit._canonical(value) + b"\n"
        (self.bundle / name).write_bytes(raw)
        return {"path": name, "sha256": audit._sha(raw), "size_bytes": len(raw)}

    def change(self, field, value):
        spec = self.document("manifest.json")
        spec[field] = self.save(spec[field]["path"], value)
        self.save("manifest.json", spec)

    def run_evaluation(self, limits=final.DEFAULT_LIMITS):
        self.sequence += 1
        output = self.root / f"output-{self.sequence}"
        return final.evaluate(self.spec, output, limits), output

    def assert_refused(self):
        report, _ = self.run_evaluation()
        self.assertEqual(report["status"], "refused", report)
        self.assertFalse(report["input_files_unchanged"])
        self.assertTrue(all(report[name] is False for name in final.FALSE_FLAGS))
        return report

    def test_authored_demonstration_preserves_raw_and_unknowns(self):
        report, output = self.run_evaluation()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual((report["case_count"], report["supported_case_count"], report["unsupported_case_count"]), (4, 3, 1))
        self.assertEqual(report["prediction_count"], 15)
        self.assertEqual(report["prediction_origin"], "authored_simulation")
        self.assertTrue(report["input_files_unchanged"])
        self.assertTrue(report["raw_outputs_retained_unmodified"])
        self.assertTrue(report["unknown_pretraining_exposure"])
        self.assertFalse(report["candidate_model_qualified"])
        self.assertFalse(report["independence_verified"])
        self.assertEqual(report["split_audit_status"], "incomplete")
        self.assertFalse(report["final_exposure_observed"])
        self.assertTrue(all(report[name] is False for name in final.FALSE_FLAGS))
        for descriptor in report["input_files"]:
            path = Path(descriptor["path"])
            self.assertEqual((self.bundle / path).read_bytes(), (output / "inputs" / path).read_bytes())
        self.assertFalse((output / "inputs/README.md").exists())
        raw = json.loads((output / "raw_outputs.json").read_bytes())
        predictions = self.document("simulated_predictions.json")
        self.assertEqual(raw["rows"], [{"prediction_id": row["prediction_id"], "raw": row["raw"]} for row in predictions["rows"]])
        self.assertEqual(report["scores"]["learned/raw"]["metrics"]["exact_reconstruction"]["correct"], 1)
        self.assertEqual(report["scores"]["learned/constrained"]["metrics"]["exact_reconstruction"]["correct"], 3)

    def test_wrong_source_teacher_substitution_and_model_off_cannot_score(self):
        report, _ = self.run_evaluation()
        rows = {row["prediction_id"]: row for row in report["prediction_results"]}
        for name, stage, finding in (("control-wrong-source", "raw", "wrong_source_binding"),
                                     ("control-teacher-replacement", "constrained", "teacher_substitution"),
                                     ("control-model-off-illegal", "raw", "model_off_emitted_candidate")):
            self.assertIn(finding, rows[name][stage]["findings"])
            self.assertFalse(rows[name][stage]["correct"]["exact_reconstruction"])
        self.assertTrue(rows["control-zero-head-window"]["raw"]["correct"]["exact_reconstruction"])
        self.assertFalse(rows["control-zero-head-window"]["raw"]["learned_weight_dependence_verified"])

    def test_changed_literal_operator_order_and_sort_do_not_conflate(self):
        original = self.document("simulated_predictions.json")
        gold = self.document("targets.json")["cases"][0]["target"]
        for mutation in ("literal", "operator", "order", "bool_as_int", "return_sort", "reference"):
            predictions = copy.deepcopy(original)
            row = predictions["rows"][0]
            candidate = copy.deepcopy(gold)
            if mutation == "literal":
                candidate["body"]["right"]["value"] = 20
            elif mutation == "operator":
                candidate["body"]["left"]["operator"] = "Mult"
            elif mutation == "order":
                candidate["body"]["left"]["left"], candidate["body"]["left"]["right"] = candidate["body"]["left"]["right"], candidate["body"]["left"]["left"]
            elif mutation == "bool_as_int":
                candidate["body"]["right"]["value"] = True
            elif mutation == "return_sort":
                candidate["function"]["returns"] = "Bool"
            else:
                candidate["body"]["left"]["left"]["name"] = "undeclared"
            row["raw"]["target"] = candidate
            row["constrained"] = {**copy.deepcopy(row["raw"]), "mechanism": "none"}
            self.change("predictions", predictions)
            with self.subTest(mutation=mutation):
                report, _ = self.run_evaluation()
                self.assertEqual(report["status"], "passed", report)
                self.assertFalse(report["prediction_results"][0]["raw"]["correct"]["exact_reconstruction"])
                metric = {"literal": "literals", "operator": "operators", "order": "references"}.get(mutation)
                if metric:
                    self.assertFalse(report["prediction_results"][0]["raw"]["correct"][metric])
                if mutation in {"bool_as_int", "return_sort", "reference"}:
                    self.assertFalse(report["prediction_results"][0]["raw"]["valid_typed_candidate"])

    def test_unicode_byte_spans_and_lf_profile(self):
        case = self.document("targets.json")["cases"][1]
        raw = (self.bundle / "source/final_window.py").read_bytes()
        binding, target, reason = derive_source(raw)
        self.assertIsNone(reason)
        self.assertEqual(binding, case["source_binding"])
        self.assertEqual(target, case["target"])
        self.assertEqual(raw[binding["start_byte"]:binding["end_byte"]].decode(), raw.decode().split("\n", 1)[1].rstrip("\n"))
        for changed in (raw.replace(b"\n", b"\r\n"), raw.replace(b"\n", b"\r")):
            with self.assertRaisesRegex(audit.AuditInputError, "physical LF"):
                derive_source(changed)

    def test_target_tampering_and_desired_intent_label_refuse(self):
        original = self.document("targets.json")
        for mutation in ("desired_value", "label_flag", "source_span", "unsupported_target"):
            targets = copy.deepcopy(original)
            if mutation == "desired_value":
                targets["cases"][0]["target"]["body"]["right"]["value"] = 23
            elif mutation == "label_flag":
                targets["cases"][0]["intent_used_as_label"] = True
            elif mutation == "source_span":
                targets["cases"][1]["source_binding"]["end_byte"] -= 1
            else:
                targets["cases"][3]["target"] = targets["cases"][0]["target"]
                targets["cases"][3]["status"] = "supported"
            self.change("targets", targets)
            with self.subTest(mutation=mutation):
                self.assert_refused()

    def test_desired_intent_can_change_without_changing_source_truth(self):
        targets = self.document("targets.json")
        targets["cases"][0]["desired_intent"] = "The desired change is +1000; captured source stays +19."
        self.change("targets", targets)
        report, _ = self.run_evaluation()
        self.assertEqual(report["status"], "passed", report)

    def test_final_dependency_revision_template_and_clone_connections_visible(self):
        original = self.document("cohort.json")
        for relationship in ("dependency", "revision", "template", "clone"):
            cohort = copy.deepcopy(original)
            final_row, train_row = cohort["units"][0], cohort["units"][4]
            if relationship == "dependency":
                final_row["dependencies"] = [train_row["id"]]
            elif relationship == "revision":
                final_row["related_revisions"] = [train_row["id"]]
            elif relationship == "template":
                train_row["template_family"] = final_row["template_family"]
            else:
                train_row["source"] = copy.deepcopy(final_row["source"])
            self.change("cohort", cohort)
            with self.subTest(relationship=relationship):
                report, _ = self.run_evaluation()
                self.assertEqual(report["status"], "passed", report)
                self.assertTrue(report["final_exposure_observed"])
                self.assertFalse(report["independence_verified"])

    def test_missing_dependency_and_pretraining_unknown_are_not_clean(self):
        cohort = self.document("cohort.json")
        cohort["units"][0]["dependencies"] = ["absent:owner-source"]
        self.change("cohort", cohort)
        report, output = self.run_evaluation()
        self.assertEqual(report["status"], "passed", report)
        screen = json.loads((output / "split_screen.json").read_bytes())
        self.assertTrue(any(issue["code"] == "unresolved_dependencies" for issue in screen["issues"]))
        self.assertTrue(report["unknown_pretraining_exposure"])
        self.assertFalse(report["native_closure_certified"])

    def test_missing_mode_rows_remain_explicit(self):
        predictions = self.document("simulated_predictions.json")
        predictions["rows"] = [row for row in predictions["rows"] if not (row["case_id"] == "flag" and row["mode"] == "zero_head")]
        self.change("predictions", predictions)
        report, _ = self.run_evaluation()
        self.assertEqual(report["status"], "passed", report)
        self.assertFalse(report["prediction_coverage"]["all_case_modes_present"])
        self.assertEqual(report["prediction_coverage"]["modes"]["zero_head"]["missing_case_ids"], ["flag"])

    def test_missing_final_case_predictions_refuses(self):
        predictions = self.document("simulated_predictions.json")
        predictions["rows"] = [row for row in predictions["rows"] if row["case_id"] != "dynamic"]
        self.change("predictions", predictions)
        self.assert_refused()

    def test_duplicate_cases_predictions_and_units_refuse(self):
        for field, filename, key in (("targets", "targets.json", "cases"), ("predictions", "simulated_predictions.json", "rows"), ("cohort", "cohort.json", "units")):
            value = self.document(filename)
            value[key].append(copy.deepcopy(value[key][0]))
            self.change(field, value)
            self.assert_refused()
            shutil.copyfile(Path(__file__).parent / "fixtures/final_protocol" / filename, self.bundle / filename)
            original_spec = json.loads((Path(__file__).parent / "fixtures/final_protocol/manifest.json").read_bytes())
            self.save("manifest.json", original_spec)

    def test_malformed_enums_and_numeric_policy_flags_refuse(self):
        protocol = self.document("protocol.json")
        protocol["teacher_semantics_certified"] = 0
        self.change("protocol", protocol)
        self.assert_refused()
        self.change("protocol", self.document("protocol.json") | {"teacher_semantics_certified": False})
        predictions = self.document("simulated_predictions.json")
        predictions["protocol_sha256"] = self.document("manifest.json")["protocol"]["sha256"]
        for path in ("mode", "origin", "mechanism"):
            changed = copy.deepcopy(predictions)
            if path == "mode":
                changed["rows"][0][path] = []
            elif path == "origin":
                changed["rows"][0]["raw"][path] = {}
            else:
                changed["rows"][0]["constrained"][path] = []
            self.change("predictions", changed)
            with self.subTest(path=path):
                self.assert_refused()

    def test_none_constraint_cannot_hide_changed_raw_output(self):
        predictions = self.document("simulated_predictions.json")
        predictions["rows"][0]["constrained"]["mechanism"] = "none"
        self.change("predictions", predictions)
        self.assert_refused()

    def test_unverified_native_export_stays_unverified(self):
        predictions = self.document("simulated_predictions.json")
        predictions["producer"].update(origin="unverified_export", checkpoint_sha256="a" * 64)
        for row in predictions["rows"]:
            for stage in ("raw", "constrained"):
                if row[stage]["origin"] == "authored_simulation":
                    row[stage]["origin"] = "model_output"
        self.change("predictions", predictions)
        report, _ = self.run_evaluation()
        self.assertEqual(report["status"], "passed", report)
        self.assertFalse(report["numerical_provenance_verified"])
        self.assertFalse(report["learned_weight_dependence_verified"])

    def test_unverified_learned_export_requires_claimed_checkpoint(self):
        predictions = self.document("simulated_predictions.json")
        predictions["producer"]["origin"] = "unverified_export"
        self.change("predictions", predictions)
        report = self.assert_refused()
        self.assertIn("claimed checkpoint digest", report["error"])

    def test_candidate_work_budget_and_wrong_operator_type_are_scored_findings(self):
        original = self.document("simulated_predictions.json")
        for mutation in ("deep", "operator_type"):
            predictions = copy.deepcopy(original)
            row = predictions["rows"][1]
            target = row["raw"]["target"]
            if mutation == "deep":
                for _ in range(40):
                    target["body"] = {"kind": "unary", "operator": "Not", "operand": target["body"]}
            else:
                target["body"]["operator"] = []
            row["constrained"] = {**copy.deepcopy(row["raw"]), "mechanism": "none"}
            self.change("predictions", predictions)
            report, _ = self.run_evaluation()
            with self.subTest(mutation=mutation):
                self.assertEqual(report["status"], "passed", report)
                self.assertFalse(report["prediction_results"][1]["raw"]["valid_typed_candidate"])

    def test_descriptor_drift_boolean_size_duplicate_keys_and_nonfinite_refuse(self):
        original = self.document("manifest.json")
        for mutation in ("digest", "size_bool", "duplicate", "nonfinite"):
            spec = copy.deepcopy(original)
            if mutation == "digest":
                spec["targets"]["sha256"] = "0" * 64
                self.save("manifest.json", spec)
            elif mutation == "size_bool":
                spec["targets"]["size_bytes"] = True
                self.save("manifest.json", spec)
            elif mutation == "duplicate":
                self.spec.write_bytes(b'{"schema":"wrong","schema":"duplicate"}')
            else:
                self.spec.write_bytes(b'{"schema":NaN}')
            with self.subTest(mutation=mutation):
                self.assert_refused()
        self.save("manifest.json", original)

    def test_path_traversal_symlink_and_fifo_refuse(self):
        spec = self.document("manifest.json")
        spec["targets"]["path"] = "../outside.json"
        self.save("manifest.json", spec)
        self.assert_refused()
        shutil.copyfile(Path(__file__).parent / "fixtures/final_protocol/manifest.json", self.spec)
        source = self.bundle / "source/final_delta.py"
        original = source.read_bytes()
        for kind in ("symlink", "fifo"):
            source.unlink()
            if kind == "symlink":
                outside = self.root / "outside.py"
                outside.write_bytes(original)
                source.symlink_to(outside)
            else:
                os.mkfifo(source)
            with self.subTest(kind=kind):
                self.assert_refused()
            source.unlink()
            source.write_bytes(original)

    def test_output_inside_bundle_is_rejected_without_mutation(self):
        output = self.bundle / "new-output"
        with self.assertRaisesRegex(audit.AuditInputError, "outside immutable"):
            final.evaluate(self.spec, output)
        self.assertFalse(output.exists())

    def test_known_descriptor_size_caps_read_before_allocation(self):
        target = self.bundle / "targets.json"
        expected = target.stat().st_size
        target.write_bytes(target.read_bytes() + b" " * 1000)
        original = final.Capture.regular
        calls = []
        def tracked(path, maximum):
            calls.append((path, maximum))
            return original(path, maximum)
        with patch.object(final.Capture, "regular", staticmethod(tracked)):
            self.assert_refused()
        self.assertEqual(next(limit for path, limit in calls if path == target), expected)

    def test_limits_and_input_read_race_refuse(self):
        for limits in (final.Limits(max_files=1), final.Limits(max_total_bytes=100), final.Limits(max_cases=1),
                       final.Limits(max_predictions=1), final.Limits(max_expression_nodes=1)):
            report, _ = self.run_evaluation(limits)
            self.assertEqual(report["status"], "refused")
        with self.assertRaises(audit.AuditInputError):
            final.Limits(max_files=True)
        original = final.Capture.recheck
        def drift(capture):
            path = self.bundle / "simulated_predictions.json"
            path.write_bytes(path.read_bytes() + b" ")
            return original(capture)
        with patch.object(final.Capture, "recheck", drift):
            self.assert_refused()

    def test_reports_are_deterministic(self):
        one, output_one = self.run_evaluation()
        two, output_two = self.run_evaluation()
        self.assertEqual(one, two)
        self.assertEqual((output_one / "final_evaluation.json").read_bytes(), (output_two / "final_evaluation.json").read_bytes())


if __name__ == "__main__":
    unittest.main()
