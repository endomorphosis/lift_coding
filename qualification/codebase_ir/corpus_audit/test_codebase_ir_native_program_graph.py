"""Structural mutations of an inert released graph inside authored mode fixtures."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebase_ir_corpus_audit as audit
import codebase_ir_final_evaluation as final
import codebase_ir_native_program_graph as graph_tool
import codebase_ir_native_source_comparison as comparison
import test_codebase_ir_native_source_comparison as fixtures


def released_graph_fixture():
    relative = Path("artifacts/codebase_ir_parallel_qualification/release_audit/evidence-children-retained-20261003-01/children/datasets/8de37ba8d216cd21a5d7134292de01d9e12c9a56/docs/autoencoders/evidence/codebase-source384-acceptance-20261002/public")
    for root in (Path.cwd().resolve(), *Path(__file__).resolve().parents):
        path = root / relative / "actual-learned.json"
        if path.is_file():
            raw = final.Capture.regular(path, 104400)
            audit._require(len(raw) == 104400 and audit._sha(raw) == "5a8debf045fede552318e6a58e2a634a302fbd08860a5cfc41903be34ebac324", "released graph fixture pin differs")
            return audit._load_json(raw, audit.DEFAULT_LIMITS)["result"]["inference"]["rows"][0]["source_contract"]
    raise FileNotFoundError("inert released native graph fixture unavailable")


class NativeProgramGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.released_contract = released_graph_fixture()

    def setUp(self):
        self.case = fixtures.NativeSourceComparisonTests("test_exact_source_fragment_and_custody_are_rederived_without_model_truth_claims")
        self.case.setUp()
        self.addCleanup(self.case.doCleanups)
        self.root = self.case.root
        self.output = self.root / "graph-output"
        directory = self.root / "graph-input"
        directory.mkdir()
        self.manifest = directory / "graph-input.json"
        for role in ("learned", "source_label_baseline"):
            contract = self.contract(role)
            contract["projections"] = copy.deepcopy(self.released_contract["projections"])
            contract["source_binding"] = copy.deepcopy(self.released_contract["source_binding"])
        self.repair("source_label_baseline")
        self.prepare()

    def contract(self, role="learned"):
        if role == "source_label_baseline":
            return self.case.documents[role]["lake"]["rows"][0]["source_qualification"]
        return self.case.row(role)["source_contract"]

    def graph(self, role="learned"):
        return self.contract(role)["projections"][0]["native_document"]

    def repair(self, role="learned"):
        projection = self.contract(role)["projections"][0]
        graph = projection["native_document"]
        projection["bridge"]["expression"]["root"]["extension"]["payload"]["document"] = copy.deepcopy(graph)
        projection["bridge"]["expression"]["root"]["extension"]["payload"]["domain_identity"] = graph["program_id"]
        projection["bridge"]["domain_identity"] = graph["program_id"]
        if role == "source_label_baseline":
            row = self.case.documents[role]["lake"]["rows"][0]
            row["program_sha256"] = audit._sha(audit._canonical(graph))
            row["lowering"] = {"program_sha256": row["program_sha256"], "original_program_id": graph["program_id"],
                               "actual_reads": graph["functions"][0]["effects"]["reads"], "actual_writes": graph["functions"][0]["effects"]["writes"]}

    def prepare(self):
        self.case.write_all()
        destination = self.root / ("comparison-" + str(self.case.serial))
        self.prior = comparison.evaluate(self.case.manifest, destination)
        self.assertEqual(self.prior["status"], "passed")
        self.spec = {"schema": graph_tool.INPUT_SCHEMA, "source_comparison_input": self.case.pin(self.case.manifest),
                     "source_comparison": self.case.pin(destination / "native_source_comparison.json")}
        self.case.write(self.manifest, self.spec)

    def refused(self, **kwargs):
        try:
            report = graph_tool.evaluate(self.manifest, self.output, **kwargs)
        except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError):
            return
        self.assertEqual(report["status"], "refused")
        self.assertTrue(report["unknown_pretraining_exposure"])
        self.assertTrue(all(report[key] is False for key in graph_tool.FALSE_FLAGS | (graph_tool.TRUE_FLAGS - {"unknown_pretraining_exposure"})))

    def test_independent_source_graph_conformance_retains_missing_zero_and_all_false_truth_claims(self):
        report = graph_tool.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "passed")
        self.assertTrue(all(report[key] is True for key in graph_tool.TRUE_FLAGS))
        self.assertTrue(all(report[key] is False for key in graph_tool.FALSE_FLAGS))
        self.assertEqual((report["historical_case_count"], report["source_graph_count"], report["source_byte_count"]), (1, 2, 85))
        self.assertEqual(report["role_graph_metrics"]["zero_head"], {"present_count": 0, "conformant_count": 0, "missing_count": 1, "unsupported_count": 0})
        roles = report["records"][0]["role_graphs"]
        self.assertFalse(roles["zero_head"]["graph_created"])
        self.assertEqual(roles["learned"]["syntactic_reads"], ["symbol:calculate.capacity.parameter", "symbol:calculate.threshold.parameter"])
        self.assertEqual(roles["learned"]["syntactic_writes"], [])
        self.assertFalse(roles["learned"]["recorded_base_effect_program_verified"])
        self.assertFalse(roles["learned"]["source_uri_opened"])
        self.assertEqual(roles["source_label_baseline"]["candidate_origin"], "deterministic_source_label_baseline")
        self.assertIn("not_learned_full_program_output", report["native_graph_stage"])
        for pin in report["retained_files"]:
            raw = (self.output / pin["path"]).read_bytes()
            self.assertEqual((audit._sha(raw), len(raw)), (pin["sha256"], pin["size_bytes"]))
        self.assertEqual((self.output / "source-comparison-rederived/native_source_comparison.json").read_bytes(), Path(self.spec["source_comparison"]["path"]).read_bytes())

    def test_coherent_operator_and_bridge_rehash_does_not_replace_exact_source(self):
        next(x for x in self.graph()["expressions"] if x["kind"] == "binary")["operator"] = "sub"
        self.contract()["source_binding"]["operator_mapping"]["native"] = "sub"
        self.repair()
        self.prepare()
        self.refused()

    def test_coherent_operand_and_evaluation_order_change_refuses_even_for_commutative_addition(self):
        root = next(x for x in self.graph()["expressions"] if x["kind"] == "binary")
        root["operand_ids"].reverse()
        root["evaluation_order"].reverse()
        self.repair()
        self.prepare()
        self.refused()

    def test_wrong_parameter_resolution_cannot_be_repaired_with_reference_maps(self):
        leaves = [x for x in self.graph()["expressions"] if x["kind"] == "symbol"]
        leaves[0]["symbol_ids"] = leaves[1]["symbol_ids"][:]
        self.repair()
        self.prepare()
        self.refused()

    def test_unresolved_cycle_and_return_reference_are_refused(self):
        root = next(x for x in self.graph()["expressions"] if x["kind"] == "binary")
        root["operand_ids"][0] = root["expression_id"]
        root["evaluation_order"] = root["operand_ids"][:]
        self.repair()
        self.prepare()
        self.refused()

    def test_typed_parameter_name_and_return_function_forgeries_refuse(self):
        mutations = [("symbols", "type_ref", "boolean"), ("symbols", "name", "borrowed_name"), ("functions", "return_type", "boolean"),
                     ("functions", "name", "borrowed_function")]
        original = copy.deepcopy(self.graph())
        for collection, field, value in mutations:
            with self.subTest(field=field):
                self.contract()["projections"][0]["native_document"] = copy.deepcopy(original)
                self.graph()[collection][0][field] = value
                self.repair()
                self.prepare()
                self.output = self.root / ("mutation-" + str(self.case.serial))
                self.refused()

    def test_duplicate_graph_members_and_extra_statements_are_refused(self):
        self.graph()["commands"].append(copy.deepcopy(self.graph()["commands"][0]))
        self.repair()
        self.prepare()
        self.refused()

    def test_ast_graph_span_membership_is_independent_of_correct_source_hash(self):
        span = self.graph()["spans"][0]
        span["start_byte"] += 1
        recorded = next(x for x in self.contract()["source_binding"]["spans"] if x["span_id"] == span["span_id"])
        recorded["start_byte"] = span["start_byte"]
        recorded["sha256"] = audit._sha(fixtures.SOURCE[span["start_byte"]:span["end_byte"]])
        self.repair()
        self.prepare()
        self.refused()

    def test_graph_member_span_substitution_refuses_with_valid_span_inventory(self):
        self.graph()["commands"][0]["span_ids"] = self.graph()["functions"][0]["span_ids"][:]
        self.repair()
        self.prepare()
        self.refused()

    def test_coherent_effect_footprint_and_audit_change_cannot_override_source_reads(self):
        value = self.graph()
        for collection in ("commands", "functions"):
            value[collection][0]["effects"]["reads"].pop()
            value["metadata"]["effect_summary_audit"][collection][0]["after"]["reads"].pop()
        self.contract()["source_binding"]["effect_summary_refinements"] = copy.deepcopy(value["metadata"]["effect_summary_audit"])
        self.repair()
        self.prepare()
        self.refused()

    def test_cfg_and_return_command_must_cover_exact_source_statement(self):
        self.graph()["functions"][0]["cfg"]["blocks"][0]["command_ids"] = []
        self.repair()
        self.prepare()
        self.refused()

    def test_source_sha_and_byte_length_cannot_be_borrowed_from_other_graph(self):
        self.graph()["sources"][0]["metadata"]["byte_length"] = 84
        self.repair()
        self.prepare()
        self.refused()

    def test_source_reference_mapping_and_type_refinements_bind_actual_graph_ids(self):
        self.contract()["source_binding"]["expression_references"]["expr:capacity"] = "invented:reference"
        self.prepare()
        self.refused()

    def test_type_refinement_cannot_claim_another_after_type(self):
        self.contract()["source_binding"]["type_refinements"][0]["after"] = "boolean"
        self.prepare()
        self.refused()

    def test_syntax_bridge_document_cannot_replace_native_graph(self):
        payload = self.contract()["projections"][0]["bridge"]["expression"]["root"]["extension"]["payload"]
        payload["document"]["commands"][0]["target_symbol_ids"] = ["invented:write"]
        self.prepare()
        self.refused()

    def test_baseline_program_digest_and_lowering_footprint_are_separate_joins(self):
        self.case.documents["source_label_baseline"]["lake"]["rows"][0]["lowering"]["actual_reads"] = []
        self.prepare()
        self.refused()

    def test_missing_and_unknown_native_graph_profiles_remain_explicit(self):
        self.contract()["projections"] = []
        self.prepare()
        report = graph_tool.evaluate(self.manifest, self.output)
        self.assertEqual(report["role_graph_metrics"]["learned"]["missing_count"], 1)
        self.assertEqual(report["source_graph_count"], 1)
        self.contract()["projections"] = copy.deepcopy(self.released_contract["projections"])
        self.graph()["schema_version"] = "unsupported-program-ir/v2"
        self.prepare()
        report = graph_tool.evaluate(self.manifest, self.root / "unsupported-output")
        self.assertEqual(report["role_graph_metrics"]["learned"]["unsupported_count"], 1)
        self.assertFalse(report["records"][0]["role_graphs"]["learned"]["graph_created"])

    def test_non_object_native_document_is_explicitly_unsupported(self):
        self.contract()["projections"][0]["native_document"] = None
        self.prepare()
        report = graph_tool.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["role_graph_metrics"]["learned"]["unsupported_count"], 1)

    def test_supported_source_literal_outside_graph_profile_has_no_conformant_graph(self):
        self.case.source = b"def calculate(capacity: int, threshold: int) -> int:\n    return capacity + 1\n"
        self.case.bind_source()
        self.prepare()
        report = graph_tool.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["source_graph_count"], 0)
        self.assertFalse(report["source_projection_graph_conformance_available"])
        self.assertEqual(report["role_graph_metrics"]["learned"]["unsupported_count"], 1)
        self.assertFalse(report["source_semantics_verified"])

    def test_graph_projection_cannot_elevate_source_or_completion_authority(self):
        self.contract()["projections"][0]["source_semantics_verified"] = True
        self.prepare()
        self.refused()

    def test_missing_learned_candidate_cannot_be_filled_from_source_label(self):
        binding, target, node, _ = graph_tool._source(fixtures.SOURCE, graph_tool.DEFAULT_LIMITS)
        with self.assertRaisesRegex(audit.AuditInputError, "returned candidate required"):
            graph_tool._graph(self.graph(), binding, target, node, fixtures.SOURCE, self.contract()["source_binding"], None, None, "learned", graph_tool.DEFAULT_LIMITS)

    def test_wrong_returned_candidate_cannot_be_replaced_by_teacher_program(self):
        candidate = self.case.row("learned")["candidate_ir"]
        candidate["document"]["operator"] = "-"
        self.contract()["candidate_sha256"] = audit._sha(audit._canonical(candidate))
        self.prepare()
        self.assertFalse(self.prior["records"][0]["returned_mode_comparisons"]["learned"]["exact_fragment_match"])
        self.refused()

    def test_coherently_repinned_source_comparison_report_needs_full_reproduction(self):
        self.prior["native_output_stage"] = "invented_free_running_full_program"
        self.spec["source_comparison"] = self.case.write(Path(self.spec["source_comparison"]["path"]), self.prior)
        self.case.write(self.manifest, self.spec)
        self.refused()

    def test_nested_budget_reserved_before_evaluation_and_graph_walk_is_bounded(self):
        for limits in (replace(graph_tool.DEFAULT_LIMITS, max_files=19), replace(graph_tool.DEFAULT_LIMITS, max_total_bytes=16*1024*1024)):
            with self.subTest(limits=limits), patch.object(comparison, "evaluate", side_effect=AssertionError("must reserve nested budget first")):
                self.refused(limits=limits)
                self.assertFalse(self.output.exists())
        self.refused(limits=replace(graph_tool.DEFAULT_LIMITS, max_graph_items=2))

    def test_late_graph_copy_mutation_refuses_all_conformance_flags(self):
        original = comparison._copy
        def mutate(path, raw):
            original(path, raw)
            if path.parent.name == "graphs":
                path.write_bytes(b"{}\n")
        with patch.object(comparison, "_copy", side_effect=mutate):
            self.refused()

    def test_late_original_native_mutation_refuses_after_graph_derivation(self):
        original = comparison._copy
        def mutate(path, raw):
            original(path, raw)
            if path.parent.name == "graphs":
                Path(self.case.native_spec["exports"]["learned"]["path"]).write_bytes(b"{}\n")
        with patch.object(comparison, "_copy", side_effect=mutate):
            self.refused()

    def test_output_inside_transitive_original_input_scope_is_refused_before_writes(self):
        with self.assertRaises(audit.AuditInputError):
            graph_tool.evaluate(self.manifest, self.case.inputs / "unwritten-graph-output")
        self.assertFalse((self.case.inputs / "unwritten-graph-output").exists())

    def test_closed_input_and_stale_outer_pins_are_refused(self):
        self.spec["unexpected"] = True
        self.case.write(self.manifest, self.spec)
        self.refused()
        self.spec.pop("unexpected")
        self.spec["source_comparison"]["sha256"] = "0" * 64
        self.case.write(self.manifest, self.spec)
        self.refused()

    def test_original_source_comparison_record_and_native_body_bytes_are_unchanged(self):
        original_report = Path(self.spec["source_comparison"]["path"])
        original_body = Path(self.case.native_spec["exports"]["learned"]["path"])
        before = original_report.read_bytes(), original_body.read_bytes()
        self.assertEqual(graph_tool.evaluate(self.manifest, self.output)["status"], "passed")
        self.assertEqual(before, (original_report.read_bytes(), original_body.read_bytes()))
        self.assertEqual(json.loads(original_body.read_bytes())["result"]["inference"]["rows"][0]["source_contract"]["projections"][0]["native_document"], self.graph())


if __name__ == "__main__":
    unittest.main()
