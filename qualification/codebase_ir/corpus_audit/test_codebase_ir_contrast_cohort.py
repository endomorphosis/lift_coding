from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebase_ir_contrast_cohort as contrast
import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_final_lock as seal
import codebase_ir_locked_final_evaluation as locked
from codebase_ir_final_targets import derive_source


class ContrastCohortTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.bundle = self.root / "bundle"
        self.report = contrast.build(self.bundle)
        self.targets = json.loads((self.bundle / "targets.json").read_bytes())
        self.cases = {case["case_id"]: case for case in self.targets["cases"]}

    def write(self, path, value):
        raw = audit._canonical(value) + b"\n"
        path.write_bytes(raw)
        return {"path": path.name, "sha256": audit._sha(raw), "size_bytes": len(raw)}

    def authored_predictions(self, bundle):
        spec = json.loads((bundle / "manifest.json").read_bytes())
        rows = []
        for case in self.targets["cases"]:
            for mode in ("learned", "model_off", "zero_head"):
                candidate = case["status"] == "supported" and mode != "model_off"
                raw = {"state": "candidate" if candidate else "unsupported" if case["status"] == "unsupported" else "abstained",
                       "origin": "authored_simulation" if candidate else "no_output", "target": copy.deepcopy(case["target"]) if candidate else None}
                rows.append({"prediction_id": "authored:" + mode + ":" + case["case_id"], "case_id": case["case_id"],
                             "mode": mode, "source_binding": case["source_binding"], "raw": raw,
                             "constrained": {**copy.deepcopy(raw), "mechanism": "none"}})
        predictions = {"schema": final.PREDICTIONS_SCHEMA, "protocol_sha256": spec["protocol"]["sha256"],
                       "producer": {"producer_id": "qualification:authored-contrast-validation-only", "origin": "authored_simulation",
                                    "checkpoint_sha256": None, "numerical_provenance_verified": False}, "rows": rows}
        spec["predictions"] = self.write(bundle / "authored_predictions.json", predictions)
        self.write(bundle / "manifest.json", spec)

    def test_complete_source_only_generation_has_no_prediction_body(self):
        self.assertEqual((self.report["case_count"], self.report["source_unit_count"]), (28, 31))
        self.assertEqual((self.report["supported_case_count"], self.report["unsupported_case_count"]), (21, 7))
        self.assertFalse((self.bundle / "future_predictions.json").exists())
        self.assertFalse(self.report["prediction_bodies_created"])
        self.assertFalse(self.report["prediction_bodies_read"])
        self.assertTrue(self.report["unknown_pretraining_exposure"])
        self.assertFalse(self.report["independence_verified"])
        self.assertEqual(self.report["native_vocabulary_coverage"], "unknown")
        self.assertEqual(self.report["split_audit_status"], "incomplete")
        self.assertEqual(self.report["split_leaks"], [])

    def test_each_source_label_and_span_is_rederived_from_exact_bytes(self):
        cohort = json.loads((self.bundle / "cohort.json").read_bytes())
        units = {row["id"]: row for row in cohort["units"]}
        for case in self.cases.values():
            raw = (self.bundle / units[case["unit_id"]]["source"]["path"]).read_bytes()
            binding, target, reason = derive_source(raw)
            self.assertEqual((binding, target, reason), (case["source_binding"], case["target"], case["unsupported_reason"]))
            self.assertFalse(case["intent_used_as_label"])

    def test_literal_guard_operand_symbol_and_sort_changes_have_distinct_labels(self):
        for pair in self.report["contrast_pairs"]:
            left, right = (self.cases[name] for name in pair["case_ids"])
            if pair["kind"] != "normalized_clone":
                self.assertNotEqual(left["target"], right["target"], pair)
        self.assertEqual(self.cases["literal_integer"]["target"]["body"]["sort"], "Int")
        self.assertEqual(self.cases["literal_boolean"]["target"]["body"]["sort"], "Bool")

    def test_normalized_clone_group_preserves_both_exact_distinct_source_bodies(self):
        left = (self.bundle / "source/clone_plain.py").read_bytes()
        right = (self.bundle / "source/clone_comment.py").read_bytes()
        self.assertNotEqual(audit._sha(left), audit._sha(right))
        self.assertEqual(audit.normalized_ast_digest(left), audit.normalized_ast_digest(right))
        groups = [group["unit_ids"] for group in self.report["connected_groups"]]
        self.assertIn(["final:clone_comment", "final:clone_plain"], groups)
        self.assertIn("normalized_ast", {edge["kind"] for edge in self.report["explaining_edges"]})

    def test_related_revision_and_dependency_groups_keep_full_population(self):
        groups = [group["unit_ids"] for group in self.report["connected_groups"]]
        self.assertIn(["final:revision_after", "final:revision_before"], groups)
        self.assertIn(["final:dependency_consumer", "final:dependency_helper"], groups)
        self.assertEqual(sum(len(group) for group in groups), 31)
        self.assertIn("repository_path", {edge["kind"] for edge in self.report["explaining_edges"]})
        self.assertIn("related_revision", {edge["kind"] for edge in self.report["explaining_edges"]})
        self.assertIn("dependency", {edge["kind"] for edge in self.report["explaining_edges"]})

    def test_unsupported_effect_call_defaults_branch_unknown_type_and_division_remain_missing_targets(self):
        unsupported = [case for case in self.cases.values() if case["status"] == "unsupported"]
        self.assertEqual(len(unsupported), 7)
        for case in unsupported:
            self.assertIsNone(case["target"])
            self.assertIsInstance(case["unsupported_reason"], str)
        self.assertEqual(self.cases["dependency_consumer"]["status"], "unsupported")

    def test_unicode_source_spans_are_utf8_byte_spans(self):
        case = self.cases["unicode_forward"]
        raw = (self.bundle / "source/unicode_forward.py").read_bytes()
        binding = case["source_binding"]
        selected = raw[binding["start_byte"]:binding["end_byte"]]
        self.assertEqual(audit._sha(selected), binding["source_slice_sha256"])
        self.assertTrue(selected.decode().startswith("def 差分"))
        self.assertGreater(len(selected), len(selected.decode()))

    def test_lock_precedes_authored_validation_without_changing_original_generation(self):
        before = {path.relative_to(self.bundle): path.read_bytes() for path in self.bundle.rglob("*") if path.is_file()}
        report = seal.seal(self.bundle / "manifest.json", self.root / "lock")
        self.assertFalse(report["prediction_bodies_read"])
        export = self.root / "authored-export"
        shutil.copytree(self.bundle, export)
        self.authored_predictions(export)
        lock = self.root / "lock/final_lock.json"
        scored = locked.evaluate(export / "manifest.json", lock, audit._sha(lock.read_bytes()), self.root / "scored")
        self.assertEqual(scored["status"], "passed", scored)
        self.assertEqual(scored["prediction_count"], 84)
        self.assertEqual(scored["prediction_origin"], "authored_simulation")
        self.assertFalse(scored["candidate_model_qualified"])
        self.assertEqual(before, {path.relative_to(self.bundle): path.read_bytes() for path in self.bundle.rglob("*") if path.is_file()})

    def test_correlated_source_and_label_edit_is_a_different_locked_baseline(self):
        seal.seal(self.bundle / "manifest.json", self.root / "lock")
        self.authored_predictions(self.bundle)
        source = self.bundle / "source/literal_small.py"
        source.write_text("def offset(n: int) -> int:\n    return n + 11\n")
        cohort = json.loads((self.bundle / "cohort.json").read_bytes())
        row = next(row for row in cohort["units"] if row["id"] == "final:literal_small")
        raw = source.read_bytes()
        row["source"].update(sha256=audit._sha(raw), size_bytes=len(raw))
        case = next(case for case in self.targets["cases"] if case["case_id"] == "literal_small")
        case["source_binding"], case["target"], case["unsupported_reason"] = derive_source(raw)
        spec = json.loads((self.bundle / "manifest.json").read_bytes())
        spec["cohort"] = self.write(self.bundle / "cohort.json", cohort)
        spec["targets"] = self.write(self.bundle / "targets.json", self.targets)
        self.write(self.bundle / "manifest.json", spec)
        lock = self.root / "lock/final_lock.json"
        with self.assertRaises(audit.AuditInputError):
            seal.validate_locked(self.bundle / "manifest.json", lock, audit._sha(lock.read_bytes()))

    def test_generation_is_deterministic_and_refuses_existing_or_protected_outputs(self):
        contrast.build(self.root / "second")
        for path in self.bundle.rglob("*"):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (self.root / "second" / path.relative_to(self.bundle)).read_bytes())
        with self.assertRaises(audit.AuditInputError):
            contrast.build(self.bundle)
        with self.assertRaises(audit.AuditInputError):
            contrast.build(Path(contrast.__file__).parent / "forbidden-output")


if __name__ == "__main__":
    unittest.main()
