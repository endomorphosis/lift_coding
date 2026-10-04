"""Authored mode packets carrying inert released graph/Lean fixture fragments.

Fixtures are embedded so retained implementation snapshots need no .lean file,
owner path lookup, compiler import, numerical inference or runtime execution.
"""
from __future__ import annotations

import base64
import copy
import json
import sys
import unittest
import zlib
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codebase_ir_corpus_audit as audit
import codebase_ir_native_lean_projection as projection
import codebase_ir_native_program_graph as graph_tool
import codebase_ir_native_source384_diagnostics as native
import codebase_ir_native_source_comparison as comparison
import test_codebase_ir_native_program_graph as graph_fixtures

# Exact inert values extracted from public actual-learned.json SHA5a8debf0...,
# learned-lake/receipt.json SHAdb930094... and SecuritySourcePrograms.lean SHA02dfdf2c... .
# These are codec fixtures inside newly authored envelopes, not model evaluations.
FIXTURE_SHA256 = '53b366500a425cce989918500dcb044a4c278ad13a90acfe54e976a9d1419e3f'
FIXTURE_B64 = (
    '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'
)


class NativeLeanProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = zlib.decompress(base64.b64decode(FIXTURE_B64))
        if audit._sha(raw) != FIXTURE_SHA256:
            raise AssertionError("embedded inert fixture changed")
        cls.fixture = json.loads(raw)

    def setUp(self):
        self.graph_case = graph_fixtures.NativeProgramGraphTests("test_independent_source_graph_conformance_retains_missing_zero_and_all_false_truth_claims")
        self.graph_case.released_contract = self.fixture["contract"]
        self.graph_case.setUp()
        self.addCleanup(self.graph_case.doCleanups)
        self.base = self.graph_case.case
        self.root = self.base.root
        inputs = self.root / "lean-inputs"
        inputs.mkdir()
        self.manifest = inputs / "manifest.json"
        self.output = self.root / "lean-output"
        self.leans, self.receipts = {}, {}
        for role in ("learned", "source_label_baseline"):
            self.leans[role] = self.fixture["lean"]
            self.receipts[role] = copy.deepcopy(self.fixture["receipt"])
            row = copy.deepcopy(self.fixture["row"])
            contract = self.graph_case.contract(role)
            row.update(id="a" * 64, source_qualification=copy.deepcopy(contract), candidate_sha256=contract["candidate_sha256"])
            self.receipts[role].update(rows=[row], count=1, supported_count=1)
        self.prepare()

    def prepare(self, *, refresh_public=True, rebuild_graph=True):
        # Recompute raw pins and all enclosing authored public/input/report
        # commitments. The exact graph is never rebuilt from mutated Lean text.
        descriptors = {}
        for role in ("learned", "source_label_baseline"):
            body = self.leans[role].encode("utf-8")
            self.receipts[role].update(lean_source=self.leans[role], lean_source_sha256=audit._sha(body))
            lean_path = self.manifest.parent / (role + ".source")
            lean_path.write_bytes(body)
            descriptors[role + "_lean"] = self.base.pin(lean_path)
            descriptors[role + "_lake_receipt"] = self.base.write(self.manifest.parent / (role + "-receipt.json"), self.receipts[role])
        if refresh_public:
            public_path = self.base.inputs / "public-manifest.json"
            public = json.loads(public_path.read_bytes())
            public["files"] = [row for row in public["files"] if row["path"] not in projection.PUBLIC_PATHS.values()]
            public["files"] += [{"path": projection.PUBLIC_PATHS[role], "sha256": pin["sha256"], "bytes": pin["size_bytes"]}
                                for role, pin in descriptors.items()]
            public_pin = self.base.write(public_path, public)
            self.base.native_spec["public_manifest"] = public_pin
            native_input = self.base.write(self.base.inputs / "native-input.json", self.base.native_spec)
            self.base.serial += 1
            native_out = self.root / ("lean-diagnostics-" + str(self.base.serial))
            result = native.evaluate(Path(native_input["path"]), native_out)
            self.assertEqual(result["status"], "passed", result.get("error"))
            self.base.spec.update(diagnostics_input=native_input, diagnostics=self.base.pin(native_out / "native_source384_diagnostics.json"), public_manifest=public_pin)
            self.base.write(self.base.manifest, self.base.spec)
        if rebuild_graph:
            self.base.serial += 1
            comparison_out = self.root / ("lean-comparison-" + str(self.base.serial))
            result = comparison.evaluate(self.base.manifest, comparison_out)
            self.assertEqual(result["status"], "passed", result.get("error"))
            graph_input = {"schema": graph_tool.INPUT_SCHEMA, "source_comparison_input": self.base.pin(self.base.manifest),
                           "source_comparison": self.base.pin(comparison_out / "native_source_comparison.json")}
            self.base.write(self.graph_case.manifest, graph_input)
            self.graph_output = self.root / ("lean-graph-" + str(self.base.serial))
            result = graph_tool.evaluate(self.graph_case.manifest, self.graph_output)
            self.assertEqual(result["status"], "passed", result.get("error"))
        self.spec = {"schema": projection.INPUT_SCHEMA, "program_graph_input": self.base.pin(self.graph_case.manifest),
                     "program_graph_report": self.base.pin(self.graph_output / "native_program_graph.json"), **descriptors}
        self.base.write(self.manifest, self.spec)

    def refused(self, **kwargs):
        try:
            report = projection.evaluate(self.manifest, self.output, **kwargs)
        except (audit.AuditInputError, OSError, ValueError, TypeError, KeyError, RecursionError):
            return
        self.assertEqual(report["status"], "refused")
        self.assertTrue(report["unknown_pretraining_exposure"])
        self.assertTrue(all(report[key] is False for key in projection.FALSE_FLAGS | (projection.TRUE_FLAGS - {"unknown_pretraining_exposure"})))

    def test_closed_projection_matches_exact_embedded_native_text_and_preserves_losses(self):
        report = projection.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "passed", report.get("error"))
        self.assertTrue(all(report[key] is True for key in projection.TRUE_FLAGS))
        self.assertTrue(all(report[key] is False for key in projection.FALSE_FLAGS))
        self.assertEqual((report["historical_case_count"], report["source_byte_count"]), (1, 85))
        self.assertEqual(report["role_projection_metrics"]["zero_head"], {"present_count": 0, "conformant_count": 0, "missing_count": 1, "unsupported_count": 0})
        self.assertTrue(report["compiler_output_body_equal"])
        value = report["records"][0]["role_projections"]["learned"]
        self.assertEqual(value["symbol_slot_map"], {"symbol:calculate.capacity.parameter": "v0", "symbol:calculate.result.result": "v1", "symbol:calculate.threshold.parameter": "v2"})
        self.assertEqual(value["expression_definition_map"], {"expr:10": "expression_0", "expr:7": "expression_1", "expr:9": "expression_2"})
        self.assertEqual((value["syntactic_expression_count"], value["store_slot_count"], value["return_definition_count"], value["evidence_definition_count"]), (3, 3, 1, 17))
        self.assertFalse(value["recorded_compiler_declaration_digest_semantics_verified"])
        self.assertEqual(report["projection_losses"]["semantic_loss_assessment"], "unavailable")
        self.assertEqual(report["projection_coverage"]["source_span_occurrences_individually_emitted"], 0)
        for row in report["retained_files"]:
            body = (self.output / row["path"]).read_bytes()
            self.assertEqual((audit._sha(body), len(body)), (row["sha256"], row["size_bytes"]))
        self.assertEqual((self.output / "program-graph-rederived/native_program_graph.json").read_bytes(), Path(self.spec["program_graph_report"]["path"]).read_bytes())

    def test_coherent_lean_operator_receipt_public_outer_rehash_cannot_replace_pinned_graph(self):
        self.leans["learned"] = self.leans["learned"].replace("current.v0 + current.v2", "current.v0 - current.v2")
        self.prepare()
        self.refused()

    def test_coherent_operand_order_changes_refuse_even_for_commutative_addition(self):
        self.leans["learned"] = self.leans["learned"].replace("current.v0 + current.v2", "current.v2 + current.v0")
        self.prepare()
        self.refused()

    def test_coherent_store_slot_and_parameter_reference_substitution_refuses(self):
        self.leans["learned"] = self.leans["learned"].replace("current.v2", "current.v1")
        self.prepare()
        self.refused()

    def test_coherent_return_expression_change_refuses(self):
        self.leans["learned"] = self.leans["learned"].replace("Outcome.returned current (expression_0", "Outcome.returned current (expression_1")
        self.prepare()
        self.refused()

    def test_coherent_typed_store_and_return_outcome_change_refuses(self):
        self.leans["learned"] = self.leans["learned"].replace("v0 : Int", "v0 : Bool").replace("(value : Int)", "(value : Bool)")
        self.prepare()
        self.refused()

    def test_coherent_graph_commitment_evidence_cannot_bind_a_different_source(self):
        self.leans["learned"] = self.leans["learned"].replace(self.fixture["row"]["source_sha256"], "0" * 64)
        self.prepare()
        self.refused()

    def test_coherent_effect_evidence_empty_reads_and_metadata_erasure_refuse(self):
        self.leans["learned"] = self.leans["learned"].replace('def sourceEvidence_commands_reads : List (String × List String) := [("command:11", ["symbol:calculate.capacity.parameter", "symbol:calculate.threshold.parameter"])]',
                                                            'def sourceEvidence_commands_reads : List (String × List String) := [("command:11", [])]')
        self.prepare()
        self.refused()

    def test_coherent_metadata_source_reference_or_span_laundering_refuses(self):
        self.receipts["learned"]["rows"][0]["lowering"]["original_source_references"][0]["metadata"]["byte_length"] = 84
        self.prepare()
        self.refused()

    def test_lean_authority_elevation_is_not_a_checked_lemma(self):
        self.leans["learned"] = self.leans["learned"].replace("sourceEvidence_proof_authority : Bool := false", "sourceEvidence_proof_authority : Bool := true")
        self.prepare()
        self.refused()

    def test_receipt_authority_escalation_and_integer_false_refuse(self):
        self.receipts["learned"]["proof_authority"] = 0
        self.prepare()
        self.refused()

    def test_native_lowering_read_write_forgery_refuses_after_all_hashes_refresh(self):
        self.receipts["learned"]["rows"][0]["lowering"]["actual_reads"] = []
        self.prepare()
        self.refused()

    def test_extracted_operational_view_hash_must_match_exact_graph_with_metadata_removed(self):
        self.receipts["learned"]["rows"][0]["lowering"]["operational_view_sha256"] = "0" * 64
        self.prepare()
        self.refused()

    def test_namespace_omission_duplicate_and_invented_axiom_cannot_be_hidden_by_byte_pins(self):
        self.leans["learned"] = self.leans["learned"].replace("namespace Candidate_0", "namespace Candidate_1")
        self.prepare()
        self.refused()

    def test_unsupported_typed_expression_is_explicitly_refused_without_teacher_fallback(self):
        self.leans["learned"] = self.leans["learned"].replace("current.v0 + current.v2", "opaque_source_guess")
        self.prepare()
        self.refused()

    def test_missing_or_duplicate_native_ids_cannot_shrink_denominators(self):
        self.receipts["learned"]["rows"].append(copy.deepcopy(self.receipts["learned"]["rows"][0]))
        self.receipts["learned"].update(count=2, supported_count=2)
        self.prepare()
        self.refused()

    def test_false_supported_disposition_cannot_certify_emitted_graph(self):
        self.receipts["learned"]["rows"][0]["semantic_lowering_supported"] = False
        self.receipts["learned"]["supported_count"] = 0
        self.prepare()
        self.refused()

    def test_original_candidate_qualification_cannot_be_substituted_by_teacher_graph(self):
        self.receipts["learned"]["rows"][0]["source_qualification"]["candidate_sha256"] = "0" * 64
        self.prepare()
        self.refused()

    def test_public_child_commitment_refuses_only_local_repinning(self):
        self.leans["learned"] = self.leans["learned"].replace("current.v0 + current.v2", "current.v0 - current.v2")
        self.prepare(refresh_public=False, rebuild_graph=False)
        self.refused()

    def test_repinned_entire_program_graph_report_must_independently_reproduce(self):
        path = Path(self.spec["program_graph_report"]["path"])
        report = json.loads(path.read_bytes())
        report["source_byte_count"] = 84
        self.spec["program_graph_report"] = self.base.write(path, report)
        self.base.write(self.manifest, self.spec)
        self.refused()

    def test_original_source_drift_is_refused_under_frozen_graph_input_report_pins(self):
        self.base.replay["rows"][0]["source_text"] = self.base.source.decode().replace(" + ", " - ")
        self.base.write(self.base.inputs / "replay-identity.json", self.base.replay)
        self.refused()

    def test_nested_budget_is_reserved_before_any_graph_rederivation(self):
        with patch.object(projection.graph_tool, "evaluate", side_effect=AssertionError("nested budget read too early")):
            self.refused(limits=replace(projection.DEFAULT_LIMITS, max_files=8))
        self.assertFalse(self.output.exists())

    def test_lean_body_and_line_limits_bound_parser_before_textual_projection(self):
        self.refused(limits=replace(projection.DEFAULT_LIMITS, max_lean_bytes=1024))
        self.output = self.root / "line-limit-output"
        self.refused(limits=replace(projection.DEFAULT_LIMITS, max_lean_lines=10))

    def test_late_retained_lean_copy_growth_withholds_conformance(self):
        original = comparison._copy

        def altered(path, raw):
            original(path, raw)
            if path.name == "learned_lean.source":
                path.write_bytes(raw + b"x")

        with patch.object(comparison, "_copy", side_effect=altered):
            self.refused()

    def test_late_original_compiler_body_change_is_detected_after_projection(self):
        original = projection._join

        def altered(*args):
            result = original(*args)
            Path(self.spec["learned_lake_receipt"]["path"]).write_bytes(b"{}\n")
            return result

        with patch.object(projection, "_join", side_effect=altered):
            self.refused()

    def test_late_nested_native_export_copy_change_is_detected_after_projection(self):
        original = projection._join

        def altered(*args):
            result = original(*args)
            path = self.output / "program-graph-rederived/source-comparison-rederived/native-diagnostics-rederived/inputs/learned.json"
            path.write_bytes(b"{}\n")
            return result

        with patch.object(projection, "_join", side_effect=altered):
            self.refused()

    def test_late_nested_public_parent_copy_growth_withholds_conformance(self):
        original = projection._join

        def altered(*args):
            result = original(*args)
            path = self.output / "program-graph-rederived/source-comparison-rederived/native-diagnostics-rederived/inputs/public_manifest.json"
            path.write_bytes(path.read_bytes() + b"x")
            return result

        with patch.object(projection, "_join", side_effect=altered):
            self.refused()

    def test_output_protects_transitive_source_and_compiler_input_scopes(self):
        for parent in (self.base.inputs, self.graph_output, self.manifest.parent):
            self.output = parent / "unwritten-output"
            self.refused()
            self.assertFalse(self.output.exists())

    def test_original_lean_native_receipts_sources_and_prior_modules_remain_unmodified(self):
        before = {Path(pin["path"]): Path(pin["path"]).read_bytes() for key, pin in self.spec.items() if key != "schema"}
        report = projection.evaluate(self.manifest, self.output)
        self.assertEqual(report["status"], "passed", report.get("error"))
        self.assertEqual(before, {p: p.read_bytes() for p in before})


if __name__ == "__main__":
    unittest.main()
