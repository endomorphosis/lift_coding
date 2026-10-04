"""Authored inert controls; fixture pins are explicitly patched in tests only."""
import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from dataclasses import replace
from pathlib import Path
from unittest import mock

import codebase_ir_corpus_audit as audit
import codebase_ir_feature_separation as tool
import codebase_ir_native_feature_coverage as coverage
import test_codebase_ir_native_feature_coverage as fixtures


class FeatureSeparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.original, self.exports = fixtures.packets()
        fixtures.refresh(self.original, self.exports)
        spec = {"schema": coverage.INPUT_SCHEMA}
        for role, doc in {"provenance_input": self.original, **self.exports}.items():
            name = {"provenance_input": "input.json", "parent_export": "parent-export.json", "child_export": "child-export.json"}[role]
            spec[role] = self.write(self.inputs / name, doc)
        self.coverage_input = self.inputs / "coverage-input.json"
        self.write(self.coverage_input, spec)
        self.prior = coverage.evaluate(self.coverage_input, self.root / "coverage-retained")
        self.coverage_report = self.root / "coverage-retained/native_feature_coverage.json"
        self.spec = {"schema": tool.INPUT_SCHEMA,
                     "feature_coverage_input": self.pin(self.coverage_input),
                     "feature_coverage_report": self.pin(self.coverage_report)}
        self.manifest = self.inputs / "separation-input.json"
        self.write(self.manifest, self.spec)
        self.anchors = {"FROZEN_INPUT_SHA256": self.spec["feature_coverage_input"]["sha256"],
                        "FROZEN_INPUT_BYTES": self.spec["feature_coverage_input"]["size_bytes"],
                        "FROZEN_REPORT_SHA256": self.spec["feature_coverage_report"]["sha256"],
                        "FROZEN_REPORT_BYTES": self.spec["feature_coverage_report"]["size_bytes"]}

    @staticmethod
    def pin(path):
        raw = path.read_bytes()
        return {"path": str(path), "sha256": audit._sha(raw), "size_bytes": len(raw)}

    def write(self, path, document):
        path.write_bytes(audit._canonical(document) + b"\n")
        return self.pin(path)

    def run_case(self, *, limits=tool.DEFAULT_LIMITS, output=None):
        with mock.patch.multiple(tool, **self.anchors):
            return tool.evaluate(self.manifest, output or self.root / "result", limits)

    def diagnostic(self, *, prior=None, limits=tool.DEFAULT_LIMITS):
        return tool._diagnostic(self.original, self.exports, prior or self.prior, limits)

    def target(self):
        return self.exports["child_export"]["report"]["codebase_provenance"]["training_targets"][0]

    def test_exhaustive_independent_golden_minimum_and_tie_break(self):
        report = self.run_case()
        self.assertEqual([2, 3, 5], [json.loads(column[1])[1] for column in report["candidate_oov_columns"]])
        self.assertEqual(8, report["exhaustive_subset_count"])
        self.assertEqual([False] * 4 + [True] * 4,
                         [w["separates_all_distinct_source_labels_in_cohort"] for w in report["subset_witnesses"]])
        self.assertEqual(2, report["minimal_extra_column_count"])
        self.assertEqual([[0, 1], [0, 2], [1, 2]], report["minimal_separating_subsets"])
        self.assertEqual([0, 1], report["selected_minimal_column_indices"])
        self.assertEqual(3, report["full_oov_extra_column_count"])
        self.assertEqual(0, report["full_oov_unrepresented_atom_occurrence_count"])
        self.assertEqual(8, report["subset_witnesses"][0]["unseparated_distinct_label_pair_count"])

    def test_scope_keeps_roles_unknown_sorts_losses_and_selection_exposure(self):
        report = self.run_case()
        self.assertEqual(9, report["historical_target_count"])
        self.assertEqual(53, report["frozen_basis_column_count"])
        self.assertEqual(18, report["unknown_sort_occurrence_count"])
        self.assertEqual(54, report["projection_source_span_loss_count"])
        self.assertEqual({"train": 3, "tune": 2, "canary": 2, "replay": 2}, report["role_counts"])
        self.assertEqual(["canary", "replay", "train", "tune"], report["counterfactual_selection_exposure"]["roles"])
        self.assertFalse(report["counterfactual_selection_exposure"]["training_only_selection"])
        self.assertTrue(all(report[k] is True for k in tool.TRUE_FLAGS))
        self.assertTrue(all(report[k] is False for k in tool.FALSE_FLAGS))

    def test_authored_unseen_four_and_six_still_collide_after_both_proposals(self):
        report = self.run_case()
        a, b = report["open_world_ambiguity_witnesses"]
        self.assertEqual([4, 6], [a["literal"], b["literal"]])
        self.assertNotEqual(a["source_label"], b["source_label"])
        self.assertEqual(a["count_signature_sha256"], b["count_signature_sha256"])
        self.assertTrue(all(r["assigned_to_final"] is False and r["model_prediction_available"] is False
                            and r["origin"].startswith("authored_source_only") for r in (a, b)))

    def test_raw_originals_basis_and_tensor_envelopes_are_unchanged(self):
        before = {p: p.read_bytes() for p in self.inputs.iterdir()}
        self.run_case()
        self.assertEqual(before, {p: p.read_bytes() for p in self.inputs.iterdir()})
        self.assertEqual(self.exports["parent_export"]["feature_space"], self.exports["child_export"]["feature_space"])

    def test_projection_order_and_mapping_insertion_order_do_not_change_proposals(self):
        expected = self.diagnostic()
        for exported in self.exports.values():
            for batch in coverage.BATCH_ROLES:
                for target in exported["report"]["codebase_provenance"][batch]:
                    target["projections"].reverse()
                    for view in target["projections"]:
                        view["expression"] = dict(reversed(list(view["expression"].items())))
        fixtures.refresh(self.original, self.exports)
        prior = copy.deepcopy(self.prior)
        prior.update(coverage._coverage(self.original, self.exports, coverage.DEFAULT_LIMITS))
        actual = self.diagnostic(prior=prior)
        for key in ("candidate_oov_columns", "selected_minimal_columns", "subset_witnesses",
                    "open_world_ambiguity_witnesses", "role_counts"):
            self.assertEqual(expected[key], actual[key])

    def test_repaired_signature_and_count_are_refused(self):
        prior = copy.deepcopy(self.prior)
        prior["targets"][0]["frozen_basis_counts"][0] += 1
        prior["targets"][0]["frozen_basis_signature_sha256"] = audit._sha(audit._canonical(prior["targets"][0]["frozen_basis_counts"]))
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic(prior=prior)

    def test_forged_exposure_role_is_refused(self):
        prior = copy.deepcopy(self.prior)
        prior["targets"][0]["exposure_role"] = "canary"
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic(prior=prior)

    def test_forged_path_is_refused(self):
        prior = copy.deepcopy(self.prior)
        prior["targets"][0]["source_path_claim"] = "canary.py"
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic(prior=prior)

    def test_native_unknown_sort_is_not_repaired_from_source_annotation(self):
        prior = copy.deepcopy(self.prior)
        prior["targets"][0]["unknown_sort_inventory"] = []
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic(prior=prior)

    def test_coherent_selection_role_swap_is_refused(self):
        for item in self.exports["child_export"]["report"]["codebase_provenance"]["selections"]:
            if item["role"] in {"train", "canary"}:
                item["role"] = {"train": "canary", "canary": "train"}[item["role"]]
        fixtures.refresh(self.original, self.exports)
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic()

    def test_coherent_operand_and_projection_forgery_is_refused(self):
        target = self.target()
        graph = target["validation"][0]["details"]["native_program"]
        graph["expressions"][2]["operand_ids"].reverse()
        graph["expressions"][2]["evaluation_order"].reverse()
        target["projections"][0]["expression"] = coverage._program_view(graph)
        fixtures.refresh(self.original, self.exports)
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic()

    def test_coherent_boolean_literal_alias_is_refused(self):
        target = self.target()
        graph = target["validation"][0]["details"]["native_program"]
        graph["expressions"][1]["attributes"]["value"] = True
        target["projections"][0]["expression"] = coverage._program_view(graph)
        fixtures.refresh(self.original, self.exports)
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic()

    def test_coherent_raw_span_forgery_is_refused(self):
        self.target()["validation"][0]["details"]["native_program"]["spans"][0]["end_byte"] += 1
        fixtures.refresh(self.original, self.exports)
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic()

    def test_counterparty_body_repin_does_not_replace_fixed_report_anchor(self):
        prior = copy.deepcopy(self.prior)
        prior["historical_target_count"] = 8
        self.spec["feature_coverage_report"] = self.write(self.coverage_report, prior)
        self.write(self.manifest, self.spec)
        with self.assertRaisesRegex(audit.AuditInputError, "fixed prior"):
            self.run_case()

    def test_production_anchors_are_not_inferred_from_authored_fixture(self):
        self.assertEqual("98e6e5f23529a266fd6f2cab8ed86ac826c965cd9859df9f1cfb854a966b43e7", tool.FROZEN_INPUT_SHA256)
        self.assertEqual("0415670ebfb9d40015bc1b7268e51e3d85d78cfbc4a62bf45916be3e9748284c", tool.FROZEN_REPORT_SHA256)
        with self.assertRaisesRegex(audit.AuditInputError, "fixed prior"):
            tool.evaluate(self.manifest, self.root / "result")

    def test_missing_oov_column_budget_refuses_before_search(self):
        with self.assertRaisesRegex(audit.AuditInputError, "OOV column budget"):
            self.diagnostic(limits=replace(tool.DEFAULT_LIMITS, max_oov_columns=2))

    def test_exhaustive_subset_budget_refuses_without_skipping_minimality(self):
        with self.assertRaisesRegex(audit.AuditInputError, "subset budget"):
            self.diagnostic(limits=replace(tool.DEFAULT_LIMITS, max_subsets=7))

    def test_pairwise_work_allocation_is_bounded_before_enumeration(self):
        with self.assertRaisesRegex(audit.AuditInputError, "comparison budget"):
            self.diagnostic(limits=replace(tool.DEFAULT_LIMITS, max_comparisons=287))

    def test_target_population_budget_does_not_silently_drop_final_case(self):
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic(limits=replace(tool.DEFAULT_LIMITS, max_targets=8))

    def test_aggregate_input_allocation_refuses_before_large_body_read(self):
        with self.assertRaises(audit.AuditInputError):
            self.run_case(limits=replace(tool.DEFAULT_LIMITS, max_total_bytes=10))

    def test_duplicate_or_missing_historical_id_is_refused(self):
        prior = copy.deepcopy(self.prior)
        prior["targets"][1]["id"] = prior["targets"][0]["id"]
        with self.assertRaises(audit.AuditInputError):
            self.diagnostic(prior=prior)

    def test_future_final_assignment_or_authority_claim_is_refused(self):
        for field, value in (("new_final_assignments", 1), ("model_selection_performed", True),
                             ("new_final_assignments", False), ("additional_attempted_training_epochs", False)):
            with self.subTest(field=field):
                prior = copy.deepcopy(self.prior)
                prior[field] = value
                with self.assertRaises(audit.AuditInputError):
                    self.diagnostic(prior=prior)

    def test_output_cannot_overlap_a_prior_retained_scope(self):
        with self.assertRaises(audit.AuditInputError):
            self.run_case(output=self.coverage_report.parent / "child-result")

    def test_late_original_input_drift_is_refused(self):
        original = tool.native.Pins.recheck
        calls = 0

        def drift(pins):
            nonlocal calls
            calls += 1
            if calls == 2:
                selected = self.inputs / "child-export.json"
                selected.write_bytes(selected.read_bytes() + b" ")
            original(pins)

        with mock.patch.object(tool.native.Pins, "recheck", drift):
            with self.assertRaises(audit.AuditInputError):
                self.run_case()

    def test_late_retained_copy_drift_is_refused(self):
        original = tool.final.Capture.regular
        touched = False

        def drift(path, maximum):
            nonlocal touched
            raw = original(path, maximum)
            if Path(path).parent == self.root / "result" and not touched:
                touched = True
                Path(path).write_bytes(raw + b" ")
            return raw

        with mock.patch.object(tool.final.Capture, "regular", drift):
            with self.assertRaises(audit.AuditInputError):
                self.run_case()
        self.assertTrue(touched)

    def late_output_injection(self, mutate):
        guard = tool._output_population
        reached = False

        def inject(output, retained, limits):
            nonlocal reached
            reached = True
            self.assertEqual(10, len(retained))
            self.assertEqual(10, len(list(output.iterdir())))
            self.assertFalse((output / "feature_separation.json").exists())
            mutate(output, retained)
            return guard(output, retained, limits)

        with mock.patch.object(tool, "_output_population", inject):
            with self.assertRaises(audit.AuditInputError):
                self.run_case()
        self.assertTrue(reached, "late guard injection must be reachable after original/copy rereads")

    def test_late_unexpected_regular_file_is_refused(self):
        self.late_output_injection(lambda output, _: (output / "unexpected.json").write_text("{}"))

    def test_late_report_precreation_is_not_overwritten(self):
        self.late_output_injection(lambda output, _: (output / "feature_separation.json").write_text("{}"))
        self.assertEqual("{}", (self.root / "result/feature_separation.json").read_text())

    def test_late_unexpected_directory_is_refused(self):
        self.late_output_injection(lambda output, _: (output / "unexpected-directory").mkdir())

    def test_late_expected_member_symlink_is_refused(self):
        def symlink(output, retained):
            selected = Path(retained[0]["retained_path"])
            selected.unlink()
            selected.symlink_to(retained[0]["path"])
        self.late_output_injection(symlink)

    def test_late_output_root_alias_is_refused(self):
        def alias(output, _):
            moved = output.with_name("moved-output")
            output.rename(moved)
            output.symlink_to(moved, target_is_directory=True)
        self.late_output_injection(alias)
        self.assertFalse((self.root / "moved-output/feature_separation.json").exists())

    def test_late_output_root_regular_file_is_refused(self):
        def replace_root(output, _):
            output.rename(output.with_name("moved-output"))
            output.write_text("not a directory")
        self.late_output_injection(replace_root)

    def test_unknown_manifest_fields_and_boolean_limits_are_refused(self):
        self.spec["apply_to_model"] = False
        self.write(self.manifest, self.spec)
        with self.assertRaises(audit.AuditInputError):
            self.run_case()
        with self.assertRaises(audit.AuditInputError):
            replace(tool.DEFAULT_LIMITS, max_subsets=True)

    def test_cli_refusal_keeps_unknown_exposure_and_false_authority(self):
        error = io.StringIO()
        with redirect_stderr(error):
            self.assertEqual(3, tool.main(["--manifest", str(self.manifest), "--output", str(self.root / "result")]))
        report = json.loads(error.getvalue())
        self.assertTrue(report["unknown_pretraining_exposure"])
        self.assertTrue(all(report[k] is False for k in tool.FALSE_FLAGS))
        self.assertFalse((self.root / "result").exists())


if __name__ == "__main__":
    unittest.main()
