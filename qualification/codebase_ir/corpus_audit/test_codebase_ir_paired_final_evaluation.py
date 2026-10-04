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
import codebase_ir_final_lock as seal
import codebase_ir_locked_final_evaluation as locked
import codebase_ir_paired_final_evaluation as paired


class PairedFinalEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixture = Path(__file__).parent / "fixtures/final_protocol"
        self.before, self.after = self.root / "before", self.root / "after"
        shutil.copytree(fixture, self.before)
        shutil.copytree(fixture, self.after)
        self.lockdir = self.root / "lock"
        seal.seal(self.before / "manifest.json", self.lockdir)
        self.lock = self.lockdir / "final_lock.json"
        self.sha = audit._sha(self.lock.read_bytes())
        self.report_counter = 0
        self.spec = {"schema": paired.INPUT_SCHEMA, "lock": self.pin(self.lock)}
        for name in ("before", "after"):
            bundle = getattr(self, name)
            self.spec[name] = {"manifest": self.pin(bundle / "manifest.json"), "report": self.score(bundle)}
        self.inputdir = self.root / "input"
        self.inputdir.mkdir()
        self.manifest = self.inputdir / "comparison.json"
        self.write_spec()
        self.output = self.root / "comparison"

    def document(self, path):
        return json.loads(path.read_bytes())

    def write(self, path, value):
        path.write_bytes(audit._canonical(value) + b"\n")
        return self.pin(path)

    def pin(self, path):
        raw = path.read_bytes()
        return {"path": str(path), "sha256": audit._sha(raw), "size_bytes": len(raw)}

    def score(self, bundle):
        self.report_counter += 1
        output = self.root / f"score-{self.report_counter}"
        report = locked.evaluate(bundle / "manifest.json", self.lock, self.sha, output)
        self.assertEqual(report["status"], "passed", report)
        return self.pin(output / "final_evaluation.json")

    def write_spec(self):
        self.write(self.manifest, self.spec)

    def change_predictions(self, mutate, *, score=True):
        path = self.after / "simulated_predictions.json"
        predictions = self.document(path)
        mutate(predictions)
        self.write(path, predictions)
        spec = self.document(self.after / "manifest.json")
        spec["predictions"] = {**self.pin(path), "path": path.name}
        self.write(self.after / "manifest.json", spec)
        self.spec["after"]["manifest"] = self.pin(self.after / "manifest.json")
        if score:
            self.spec["after"]["report"] = self.score(self.after)
        self.write_spec()

    def evaluate(self, **kwargs):
        return paired.evaluate(self.manifest, self.output, **kwargs)

    def refused_before_output(self, **kwargs):
        with self.assertRaises((audit.AuditInputError, OSError, ValueError, TypeError, KeyError)):
            self.evaluate(**kwargs)
        self.assertFalse(self.output.exists())

    def test_full_report_rederivation_and_all_authored_rows_are_preserved(self):
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["paired_record_count"], 15)
        self.assertEqual(report["row_count"], 15)
        self.assertTrue(report["source_reports_independently_rederived"])
        self.assertTrue(report["lock_enforced"])
        self.assertEqual(report["lock_sha256"], self.sha)
        self.assertEqual(report["changed_output_counts"], {"raw": 0, "constrained": 0})
        self.assertEqual(len(report["case_mode_populations"]), 12)
        self.assertEqual(report["unique_case_summaries"]["learned"]["status"], "unknown")
        self.assertEqual(report["unique_case_summaries"]["model_off"]["status"], "unknown")
        self.assertEqual(report["unique_case_summaries"]["zero_head"]["status"], "available")
        delta = next(row for row in report["case_mode_populations"] if row["case_id"] == "delta" and row["mode"] == "learned")
        self.assertEqual(delta["before_count"], 3)
        self.assertIn("multiple_controls", delta["unknown_reasons"])
        self.assertFalse(report["independent_samples_established"])
        self.assertFalse(report["learned_quality_improvement_verified"])
        for key in paired.CLAIMS:
            self.assertEqual(report[key], paired.CLAIMS[key])

    def test_changed_raw_literal_and_producer_do_not_invent_measured_gain(self):
        def change(value):
            value["rows"][0]["raw"]["target"]["body"]["right"]["value"] = 987
            value["producer"]["producer_id"] = "later-authored-only"
        self.change_predictions(change)
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["changed_output_counts"], {"raw": 1, "constrained": 0})
        self.assertFalse(report["learned_quality_improvement_verified"])
        for counts in report["record_metric_transitions"].values():
            for metric in counts.values():
                self.assertEqual(metric["gain"], 0)
                self.assertEqual(metric["regression"], 0)

    def test_gain_regression_and_raw_constrained_stages_remain_separate(self):
        def change(value):
            delta = value["rows"][0]
            delta["raw"]["target"] = copy.deepcopy(delta["constrained"]["target"])
            window = value["rows"][1]
            window["raw"]["target"]["body"]["op"] = "Sub"
            window["constrained"].update(copy.deepcopy(window["raw"]))
        self.change_predictions(change)
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        by_id = {row["prediction_id"]: row for row in report["prediction_pairs"]}
        delta = by_id["simulated-delta-literal"]
        window = by_id["simulated-window-match"]
        self.assertEqual(delta["raw"]["metrics"]["exact_reconstruction"]["transition"], "gain")
        self.assertEqual(delta["constrained"]["metrics"]["exact_reconstruction"]["transition"], "unchanged_correct")
        self.assertEqual(window["raw"]["metrics"]["exact_reconstruction"]["transition"], "regression")
        self.assertFalse(report["learned_quality_improvement_verified"])

    def test_missing_and_extra_ids_are_unpaired_without_success_inflation(self):
        def change(value):
            row = value["rows"].pop(0)
            row["prediction_id"] = "new-control-id"
            value["rows"].append(row)
        self.change_predictions(change)
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["paired_record_count"], 14)
        self.assertEqual(report["row_count"], 16)
        self.assertEqual(report["missing_before_prediction_ids"], ["new-control-id"])
        self.assertEqual(report["missing_after_prediction_ids"], ["simulated-delta-literal"])
        missing = next(row for row in report["prediction_pairs"] if row["prediction_id"] == "new-control-id")
        self.assertIsNone(missing["raw"]["metrics"]["exact_reconstruction"]["transition"])

    def test_missing_mode_is_explicit_and_unknown_even_when_cases_remain(self):
        self.change_predictions(lambda value: value["rows"].__setitem__(slice(None), [row for row in value["rows"] if not (row["case_id"] == "window" and row["mode"] == "zero_head")]))
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["unique_case_summaries"]["zero_head"]["status"], "unknown")
        window = next(row for row in report["case_mode_populations"] if row["case_id"] == "window" and row["mode"] == "zero_head")
        self.assertIn("missing_mode", window["unknown_reasons"])
        self.assertIn("unpaired_prediction_ids", window["unknown_reasons"])

    def test_unsupported_dispositions_have_separate_relevance(self):
        report = self.evaluate()
        row = next(row for row in report["prediction_pairs"] if row["prediction_id"] == "simulated-unsupported")
        self.assertEqual(row["source_status"], "unsupported")
        self.assertTrue(row["raw"]["metrics"]["unsupported_disposition"]["relevant"])
        self.assertFalse(row["raw"]["metrics"]["exact_reconstruction"]["relevant"])
        self.assertIsNone(row["raw"]["metrics"]["exact_reconstruction"]["transition"])

    def test_reordered_export_pairs_by_ids_and_preserves_population(self):
        self.change_predictions(lambda value: value["rows"].reverse())
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["paired_record_count"], 15)
        self.assertEqual(report["changed_output_counts"], {"raw": 0, "constrained": 0})

    def test_same_id_cannot_move_between_modes(self):
        self.change_predictions(lambda value: value["rows"][0].update(mode="zero_head"))
        report = self.evaluate()
        self.assertEqual(report["status"], "refused")
        self.assertIn("changes case or mode", report["error"])

    def test_same_id_cannot_move_between_cases_even_when_each_case_remains(self):
        self.change_predictions(lambda value: value["rows"][0].update(case_id="window"))
        report = self.evaluate()
        self.assertEqual(report["status"], "refused")
        self.assertIn("changes case or mode", report["error"])

    def test_source_binding_change_is_measured_and_original_binding_retained(self):
        def change(value):
            value["rows"][4]["source_binding"] = copy.deepcopy(value["rows"][0]["source_binding"])
        self.change_predictions(change)
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        row = next(row for row in report["prediction_pairs"] if row["prediction_id"] == "control-wrong-source")
        self.assertNotEqual(row["source_binding_before"], row["source_binding_after"])
        self.assertEqual(row["raw"]["metrics"]["source_binding"]["transition"], "gain")

    def test_teacher_and_model_off_findings_cannot_be_counted_as_learned_matches(self):
        report = self.evaluate()
        teacher = next(row for row in report["prediction_pairs"] if row["prediction_id"] == "control-teacher-replacement")
        off = next(row for row in report["prediction_pairs"] if row["prediction_id"] == "control-model-off-illegal")
        self.assertIn("teacher_substitution", teacher["constrained"]["findings_before"])
        self.assertIn("model_off_emitted_candidate", off["raw"]["findings_before"])
        self.assertEqual(off["mode"], "model_off")
        self.assertFalse(off["raw"]["metrics"]["exact_reconstruction"]["before_correct"])

    def test_pinned_but_forged_report_summary_is_refused_by_full_reconstruction(self):
        path = Path(self.spec["after"]["report"]["path"])
        report = self.document(path)
        report["scores"]["learned/raw"]["metrics"]["exact_reconstruction"]["correct"] = 99
        self.spec["after"]["report"] = self.write(path, report)
        self.write_spec()
        actual = self.evaluate()
        self.assertEqual(actual["status"], "refused")
        self.assertIn("full independently reconstructed", actual["error"])

    def test_report_population_or_boolean_type_tamper_is_not_hidden(self):
        path = Path(self.spec["after"]["report"]["path"])
        report = self.document(path)
        report["input_files_unchanged"] = 1
        report["prediction_results"].pop()
        self.spec["after"]["report"] = self.write(path, report)
        self.write_spec()
        self.assertEqual(self.evaluate()["status"], "refused")

    def test_stale_report_cannot_score_modified_prediction_body(self):
        self.change_predictions(lambda value: value["producer"].update(producer_id="changed"), score=False)
        self.assertEqual(self.evaluate()["status"], "refused")

    def test_wrong_lock_sha_or_replaced_lock_refuses_before_output(self):
        self.spec["lock"]["sha256"] = "0" * 64
        self.write_spec()
        self.refused_before_output()

    def test_changed_fixed_protocol_refuses_even_after_descriptor_repin(self):
        path = self.after / "protocol.json"
        protocol = self.document(path)
        protocol["protocol_id"] = "same-purpose-new-id"
        self.write(path, protocol)
        spec = self.document(self.after / "manifest.json")
        spec["protocol"] = {**self.pin(path), "path": path.name}
        self.write(self.after / "manifest.json", spec)
        self.spec["after"]["manifest"] = self.pin(self.after / "manifest.json")
        self.write_spec()
        self.refused_before_output()

    def test_duplicate_ids_refuse_before_output(self):
        self.change_predictions(lambda value: value["rows"].append(copy.deepcopy(value["rows"][0])), score=False)
        self.refused_before_output()

    def test_missing_entire_case_refuses_before_output(self):
        self.change_predictions(lambda value: value["rows"].__setitem__(slice(None), [row for row in value["rows"] if row["case_id"] != "dynamic"]), score=False)
        self.refused_before_output()

    def test_closed_schema_strict_json_and_exact_descriptor_types(self):
        original = self.manifest.read_bytes()
        self.manifest.write_bytes(b'{"schema": "a", "schema": "b"}')
        self.refused_before_output()
        self.manifest.write_bytes(original)
        self.spec["after"]["manifest"]["size_bytes"] = True
        self.write_spec()
        self.refused_before_output()
        self.spec["after"]["manifest"] = self.pin(self.after / "manifest.json")
        self.spec["unexpected"] = "field"
        self.write_spec()
        self.refused_before_output()

    def test_symlink_and_fifo_inputs_refuse_without_blocking(self):
        link = self.root / "report-link.json"
        link.symlink_to(Path(self.spec["after"]["report"]["path"]))
        self.spec["after"]["report"]["path"] = str(link)
        self.write_spec()
        self.refused_before_output()
        link.unlink()
        os.mkfifo(link)
        self.spec["after"]["report"].update(size_bytes=0, sha256=audit._sha(b""))
        self.write_spec()
        self.refused_before_output()

    def test_existing_or_input_scoped_output_is_refused(self):
        with self.assertRaises(audit.AuditInputError):
            paired.evaluate(self.manifest, self.before / "new-output")
        self.assertFalse((self.before / "new-output").exists())
        self.output.mkdir()
        with self.assertRaises(audit.AuditInputError):
            self.evaluate()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_output_protects_retained_lock_baseline_and_external_report_scopes(self):
        for scope in (self.lockdir / "inputs/source", Path(self.spec["before"]["report"]["path"]).parent):
            with self.subTest(scope=scope):
                with self.assertRaises(audit.AuditInputError):
                    paired.evaluate(self.manifest, scope / "new-output")
                self.assertFalse((scope / "new-output").exists())

    def test_raw_outer_manifest_and_external_report_pins_are_exact(self):
        path = Path(self.spec["before"]["report"]["path"])
        path.write_bytes(path.read_bytes() + b" ")
        self.refused_before_output()
        self.spec["before"]["report"] = self.pin(path)
        self.manifest.write_bytes(json.dumps(self.spec, indent=5).encode())
        raw = self.manifest.read_bytes()
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["manifest_sha256"], audit._sha(raw))
        self.assertEqual((self.output / "comparison_input.json").read_bytes(), raw)

    def test_file_descriptor_and_aggregate_budgets_precede_unbounded_reads(self):
        self.refused_before_output(limits=paired.Limits(max_files=1))
        self.refused_before_output(limits=paired.Limits(max_total_bytes=1))
        self.spec["after"]["report"]["size_bytes"] = paired.DEFAULT_LIMITS.max_json_bytes + 1
        self.write_spec()
        self.refused_before_output()

    def test_external_input_drift_after_reconstruction_refuses_success(self):
        original = locked.evaluate
        source = self.after / "source/final_delta.py"
        def drift(*args, **kwargs):
            report = original(*args, **kwargs)
            source.write_bytes(source.read_bytes() + b"\n")
            return report
        with patch.object(paired.locked, "evaluate", side_effect=drift):
            report = self.evaluate()
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["input_files_unchanged"])

    def test_late_retained_raw_copy_drift_refuses_unmodified_output_claim(self):
        original = locked.evaluate
        def drift(*args, **kwargs):
            report = original(*args, **kwargs)
            source = self.output / "captured-before/evaluation/inputs/simulated_predictions.json"
            source.write_bytes(b"[" + source.read_bytes()[1:])
            return report
        with patch.object(paired.locked, "evaluate", side_effect=drift):
            report = self.evaluate()
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["raw_outputs_retained_unmodified"])
        self.assertIn("retained raw copy", report["error"])

    def test_late_retained_report_or_private_scored_input_drift_refuses(self):
        original = locked.evaluate
        targets = ("captured-before/pinned_report.json", "rederived-before/scored/inputs/simulated_predictions.json")
        for index, name in enumerate(targets):
            with self.subTest(name=name):
                self.output = self.root / f"late-copy-{index}"
                def drift(*args, name=name, **kwargs):
                    report = original(*args, **kwargs)
                    path = self.output / name
                    path.write_bytes(path.read_bytes() + b" ")
                    return report
                with patch.object(paired.locked, "evaluate", side_effect=drift):
                    report = self.evaluate()
                self.assertEqual(report["status"], "refused")
                self.assertFalse(report["raw_outputs_retained_unmodified"])

    def test_reports_and_raw_retention_are_deterministic(self):
        raw = self.manifest.read_bytes()
        first = self.evaluate()
        second = paired.evaluate(self.manifest, self.root / "comparison-2")
        self.assertEqual(first, second)
        self.assertEqual((self.output / "captured-after/evaluation/inputs/simulated_predictions.json").read_bytes(),
                         (self.after / "simulated_predictions.json").read_bytes())
        self.assertEqual((self.output / "comparison_input.json").read_bytes(), raw)


if __name__ == "__main__":
    unittest.main()
