from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as seal
import codebase_ir_locked_final_evaluation as locked
from codebase_ir_final_targets import derive_source


class FinalLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / "bundle"
        shutil.copytree(Path(__file__).parent / "fixtures/final_protocol", self.bundle)
        self.manifest = self.bundle / "manifest.json"
        self.lockdir = self.root / "lock"
        self.receipt_report = seal.seal(self.manifest, self.lockdir)
        self.receipt = self.lockdir / "final_lock.json"
        self.sha = self.receipt_report["lock_sha256"]
        self.output = self.root / "result"

    def document(self, path):
        return json.loads(path.read_bytes())

    def write(self, path, value):
        raw = audit._canonical(value) + b"\n"
        path.write_bytes(raw)
        return {"path": path.relative_to(self.bundle).as_posix(), "sha256": audit._sha(raw), "size_bytes": len(raw)}

    def change(self, key, value):
        spec = self.document(self.manifest)
        spec[key] = self.write(self.bundle / spec[key]["path"], value)
        self.write(self.manifest, spec)

    def evaluate(self, **kwargs):
        return locked.evaluate(self.manifest, self.receipt, self.sha, self.output, **kwargs)

    def refused_before_output(self, **kwargs):
        with self.assertRaises((audit.AuditInputError, OSError, ValueError, TypeError, KeyError)):
            self.evaluate(**kwargs)
        self.assertFalse(self.output.exists())

    def unlocked_passes(self):
        report = final.evaluate(self.manifest, self.root / "unlocked")
        self.assertEqual(report["status"], "passed", report)

    def test_lock_retains_exact_fixed_bytes_and_excludes_predictions(self):
        original = self.document(self.manifest)
        self.assertFalse((self.lockdir / "inputs" / original["predictions"]["path"]).exists())
        self.assertFalse(self.receipt_report["prediction_bodies_read"])
        self.assertEqual(audit._sha(self.receipt.read_bytes()), self.sha)
        for row in self.receipt_report["input_files"]:
            self.assertEqual((self.bundle / row["path"]).read_bytes(), (self.lockdir / "inputs" / row["path"]).read_bytes())
        receipt = self.document(self.receipt)
        self.assertEqual(len(receipt["sources"]), 7)
        self.assertTrue(all(len(row["normalized_ast_sha256"]) == 64 for row in receipt["sources"]))
        self.assertTrue(all(receipt["claims"][key] is False for key in final.FALSE_FLAGS))

    def test_valid_locked_scoring_preserves_original_claim_limits(self):
        report = self.evaluate()
        self.assertEqual(report["status"], "passed", report)
        self.assertTrue(report["lock_enforced"])
        self.assertEqual(report["lock_sha256"], self.sha)
        self.assertEqual(report["manifest_sha256"], audit._sha(self.manifest.read_bytes()))
        self.assertTrue(report["input_files_unchanged"])
        self.assertTrue(report["raw_outputs_retained_unmodified"])
        self.assertTrue(report["unknown_pretraining_exposure"])
        self.assertFalse(report["independence_verified"])
        self.assertEqual(report["finding_count"], 18)
        self.assertEqual((self.output / "lock_receipt/inputs/final_lock.json").read_bytes(), self.receipt.read_bytes())
        self.assertTrue(all(report[key] is False for key in final.FALSE_FLAGS))

    def test_later_predictions_and_manifest_name_may_change(self):
        predictions = self.document(self.bundle / "simulated_predictions.json")
        predictions["rows"][0]["raw"]["target"]["body"]["right"]["value"] = 987
        predictions["producer"]["producer_id"] = "separately-authored-export"
        self.change("predictions", predictions)
        later = self.bundle / "later-export.json"
        shutil.copyfile(self.manifest, later)
        report = locked.evaluate(later, self.receipt, self.sha, self.output)
        self.assertEqual(report["status"], "passed", report)
        self.assertNotEqual(report["manifest_sha256"], self.receipt_report["manifest_sha256"])
        self.assertEqual(report["locked_identity_sha256"], self.receipt_report["locked_identity_sha256"])
        self.assertEqual((self.output / "evaluation/inputs/simulated_predictions.json").read_bytes(),
                         (self.bundle / "simulated_predictions.json").read_bytes())

    def test_changed_desired_intent_with_same_protocol_id_is_locked(self):
        targets = self.document(self.bundle / "targets.json")
        targets["cases"][0]["desired_intent"] = "a different intent, still not the source label"
        self.change("targets", targets)
        self.unlocked_passes()
        self.refused_before_output()

    def test_cohort_role_and_template_changes_remain_locked(self):
        for field, value in (("role", "tune"), ("template_family", "new family"), ("dependencies", ["missing-parent"])):
            with self.subTest(field=field):
                cohort = self.document(self.lockdir / "inputs/cohort.json")
                cohort["units"][4][field] = value
                self.change("cohort", cohort)
                self.refused_before_output()

    def test_coherent_source_and_label_repin_passes_unlocked_but_not_locked(self):
        path = self.bundle / "source/final_delta.py"
        path.write_bytes(path.read_bytes().replace(b"+ 19", b"+ 20"))
        raw = path.read_bytes()
        cohort = self.document(self.bundle / "cohort.json")
        cohort["units"][0]["source"].update(sha256=audit._sha(raw), size_bytes=len(raw))
        self.change("cohort", cohort)
        binding, target, _ = derive_source(raw)
        targets = self.document(self.bundle / "targets.json")
        targets["cases"][0].update(source_binding=binding, target=target)
        self.change("targets", targets)
        self.unlocked_passes()
        self.refused_before_output()

    def test_coherent_removed_case_cannot_shrink_locked_final_population(self):
        cohort = self.document(self.bundle / "cohort.json")
        targets = self.document(self.bundle / "targets.json")
        unit_id = targets["cases"][2]["unit_id"]
        cohort["units"] = [row for row in cohort["units"] if row["id"] != unit_id]
        targets["cases"] = [row for row in targets["cases"] if row["case_id"] != "flag"]
        predictions = self.document(self.bundle / "simulated_predictions.json")
        predictions["rows"] = [row for row in predictions["rows"] if row["case_id"] != "flag"]
        for key, value in (("cohort", cohort), ("targets", targets), ("predictions", predictions)):
            self.change(key, value)
        self.unlocked_passes()
        self.refused_before_output()

    def test_coherent_new_case_cannot_expand_locked_final_population(self):
        cohort = self.document(self.bundle / "cohort.json")
        targets = self.document(self.bundle / "targets.json")
        predictions = self.document(self.bundle / "simulated_predictions.json")
        unit = copy.deepcopy(cohort["units"][0])
        unit.update(id="new-final-unit", path="new_final.py", template_family="new family")
        unit["source"]["path"] = "source/new_final.py"
        shutil.copyfile(self.bundle / "source/final_delta.py", self.bundle / unit["source"]["path"])
        cohort["units"].append(unit)
        case = copy.deepcopy(targets["cases"][0])
        case.update(case_id="new-case", unit_id=unit["id"])
        targets["cases"].append(case)
        prediction = copy.deepcopy(predictions["rows"][0])
        prediction.update(prediction_id="new-prediction", case_id=case["case_id"])
        predictions["rows"].append(prediction)
        for key, value in (("cohort", cohort), ("targets", targets), ("predictions", predictions)):
            self.change(key, value)
        self.unlocked_passes()
        self.refused_before_output()

    def test_raw_json_format_is_locked_even_when_canonical_json_matches(self):
        path = self.bundle / "protocol.json"
        value = self.document(path)
        raw = json.dumps(value, indent=7).encode()
        path.write_bytes(raw)
        spec = self.document(self.manifest)
        spec["protocol"].update(sha256=audit._sha(raw), size_bytes=len(raw))
        self.write(self.manifest, spec)
        self.refused_before_output()

    def test_metrics_policy_and_label_tamper_refuse(self):
        for field, value in (("metrics", []), ("final_selection_forbidden", False), ("unknown_pretraining_exposure", False)):
            with self.subTest(field=field):
                protocol = self.document(self.lockdir / "inputs/protocol.json")
                protocol[field] = value
                self.change("protocol", protocol)
                self.refused_before_output()

    def test_wrong_missing_or_malformed_raw_lock_sha_creates_nothing(self):
        for value in ("0" * 64, "bad", None, True):
            with self.subTest(value=value):
                with self.assertRaises(audit.AuditInputError):
                    locked.evaluate(self.manifest, self.receipt, value, self.output)
                self.assertFalse(self.output.exists())

    def test_modified_receipt_cannot_keep_original_raw_pin(self):
        self.receipt.write_bytes(self.receipt.read_bytes() + b" ")
        self.refused_before_output()

    def test_repinning_modified_lock_inventory_cannot_replace_retained_baseline(self):
        receipt = self.document(self.receipt)
        receipt["sources"].pop()
        self.receipt.write_bytes(audit._canonical(receipt) + b"\n")
        self.sha = audit._sha(self.receipt.read_bytes())
        self.refused_before_output()

    def test_retained_source_drift_or_missing_file_invalidates_lock(self):
        path = self.lockdir / "inputs/source/final_delta.py"
        original = path.read_bytes()
        path.write_bytes(original.replace(b"+ 19", b"+ 20"))
        self.refused_before_output()
        path.unlink()
        self.refused_before_output()

    def test_unsigned_lock_cannot_claim_authority(self):
        receipt = self.document(self.receipt)
        receipt["claims"]["current_authority_claimed"] = True
        self.receipt.write_bytes(audit._canonical(receipt) + b"\n")
        self.sha = audit._sha(self.receipt.read_bytes())
        self.refused_before_output()

    def test_duplicate_keys_and_nonfinite_lock_json_refuse(self):
        original = self.receipt.read_bytes()
        for raw in (b'{"schema":1,"schema":2}', b'{"schema":NaN}'):
            self.receipt.write_bytes(raw)
            self.sha = audit._sha(raw)
            self.refused_before_output()
        self.receipt.write_bytes(original)

    def test_source_or_lock_symlinks_and_traversal_refuse(self):
        path = self.lockdir / "inputs/source/final_delta.py"
        path.unlink()
        path.symlink_to(self.bundle / "source/final_delta.py")
        self.refused_before_output()
        receipt = self.document(self.receipt)
        receipt["original_manifest"]["path"] = "../manifest.json"
        self.receipt.write_bytes(audit._canonical(receipt) + b"\n")
        self.sha = audit._sha(self.receipt.read_bytes())
        self.refused_before_output()

    def test_output_inside_either_original_bundle_never_writes(self):
        for parent in (self.bundle, self.lockdir):
            output = parent / "unsafe"
            with self.assertRaises(audit.AuditInputError):
                locked.evaluate(self.manifest, self.receipt, self.sha, output)
            self.assertFalse(output.exists())
        with self.assertRaises(audit.AuditInputError):
            seal.seal(self.manifest, self.bundle / "unsafe")
        self.assertFalse((self.bundle / "unsafe").exists())

    def test_original_manifest_and_aggregate_bounds_precede_allocation(self):
        path = self.lockdir / "inputs/manifest.json"
        maximum = path.stat().st_size
        path.write_bytes(path.read_bytes() + b" " * 100)
        with patch.object(seal.Capture, "regular", wraps=final.Capture.regular) as reader:
            self.refused_before_output()
        calls = [call.args[1] for call in reader.call_args_list if call.args[0] == path]
        self.assertEqual(calls, [maximum])
        with patch.object(seal.Capture, "regular", wraps=final.Capture.regular) as reader:
            self.refused_before_output(limits=seal.Limits(max_total_bytes=1))
        self.assertEqual(reader.call_args.args[1], 1)
        with self.assertRaises(audit.AuditInputError):
            seal.Limits(max_files=True)

    def test_mutable_predictions_cannot_overlap_fixed_sources(self):
        spec = self.document(self.manifest)
        spec["predictions"] = copy.deepcopy(spec["cohort"])
        self.write(self.manifest, spec)
        self.refused_before_output()

    def test_sealing_does_not_need_or_read_prediction_body(self):
        (self.bundle / "simulated_predictions.json").unlink()
        report = seal.seal(self.manifest, self.root / "without-predictions")
        self.assertEqual(report["locked_identity_sha256"], self.receipt_report["locked_identity_sha256"])
        self.refused_before_output()

    def test_lock_and_current_source_races_cannot_publish_success(self):
        real = final.evaluate
        def change_after_scoring(manifest, output):
            report = real(manifest, output)
            self.receipt.write_bytes(self.receipt.read_bytes() + b" ")
            return report
        with patch.object(locked.final, "evaluate", side_effect=change_after_scoring):
            report = self.evaluate()
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["input_files_unchanged"])

    def test_check_use_race_keeps_first_bytes_and_refuses_changed_original(self):
        validate = seal.validate_locked
        original = self.manifest.read_bytes()
        def change_after_validation(*args, **kwargs):
            result = validate(*args, **kwargs)
            self.manifest.write_bytes(original + b" ")
            return result
        with patch.object(locked.lock_tool, "validate_locked", side_effect=change_after_validation):
            report = self.evaluate()
        self.assertEqual(report["status"], "refused")
        self.assertEqual(report["manifest_sha256"], audit._sha(original))
        self.assertEqual((self.output / "evaluation/inputs/manifest.json").read_bytes(), original)
        self.assertFalse(report["input_files_unchanged"])

    def test_current_source_drift_after_scoring_refuses_and_retains_first_bytes(self):
        real = final.evaluate
        path = self.bundle / "source/final_delta.py"
        original = path.read_bytes()
        def change_after_scoring(manifest, output):
            report = real(manifest, output)
            path.write_bytes(original.replace(b"+ 19", b"+ 20"))
            return report
        with patch.object(locked.final, "evaluate", side_effect=change_after_scoring):
            report = self.evaluate()
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["input_files_unchanged"])
        self.assertEqual((self.output / "evaluation/inputs/source/final_delta.py").read_bytes(), original)

    def test_private_scorer_population_must_equal_first_capture(self):
        real = final.evaluate
        def substitute_report(manifest, output):
            report = real(manifest, output)
            report["input_files"][0]["sha256"] = "0" * 64
            return report
        with patch.object(locked.final, "evaluate", side_effect=substitute_report):
            report = self.evaluate()
        self.assertEqual(report["status"], "refused")
        self.assertFalse(report["input_files_unchanged"])

    def test_seals_and_locked_reports_are_deterministic(self):
        second = seal.seal(self.manifest, self.root / "second-lock")
        self.assertEqual(second, self.receipt_report)
        first = self.evaluate()
        other = locked.evaluate(self.manifest, self.receipt, self.sha, self.root / "second-result")
        self.assertEqual(first, other)


if __name__ == "__main__":
    unittest.main()
