"""Qualification oracle and input-integrity controls; no synthetic proofs."""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import codebase_ir_acceptance as fixture


def shaped_result(case):
    """Inert shape for comparator regressions, never authenticated evidence."""
    clauses = case["expected"]["preserved_clause_ids"]
    mapping = {clause: f"authored-shape-predicate:{clause}" for clause in clauses}
    eligible = case["expected"]["eligible_clause_ids_after_fresh_native_check"]
    return {
        **{name: False for name in fixture.FALSE_AUTHORITY},
        "scope": "explicit_finite_domain_only", "unbounded_behavior_status": "unresolved",
        "eligible_clause_ids": eligible, "residual_clause_ids": case["expected"]["residual_clause_ids"],
        "removed_task_ids": [], "typed_intent": {"metadata": {"requirement_predicate_ids": mapping}},
        "clause_results": [{"statement_id": clause, "predicate_id": mapping[clause]} for clause in clauses],
        "current_root_id": "inert-shaped-root-with-no-authority",
        "current_facts": [{"predicate": {"predicate_id": mapping[clause]}, "authority": "bounded_observation",
            "truth": "true", "current_root_id": "inert-shaped-root-with-no-authority"} for clause in eligible],
        "observation": {"source_path": case["selected"]["path"], "source_sha256": case["selected"]["source_sha256"],
            "domain_inputs": case["requirements"]["domain_inputs"],
            "contract": dict(case["requirements"]["target"], offset=case["requirements"]["desired_offset"]),
            "status": "observed", "observations": [dict(row, input_type="int", output_type="int")
                for row in case["expected"]["reference_rows"]]},
        "finite_counterexamples": case["expected"]["counterexamples"],
    }


class AcceptanceFixtureTests(unittest.TestCase):
    def setUp(self):
        self.cases = {case["scenario_id"]: case for case in fixture.scenarios()}
        self.baseline = self.cases["baseline"]

    def test_baseline_and_successor_have_compatible_complete_requirements(self):
        base, next_case = self.baseline, self.cases["successor"]
        self.assertEqual(base["expected"]["eligible_clause_ids_after_fresh_native_check"], [fixture.TYPE_CLAUSE])
        self.assertEqual(base["expected"]["residual_clause_ids"], [fixture.OFFSET_CLAUSE])
        self.assertEqual(len(base["expected"]["counterexamples"]), 5)
        self.assertEqual(next_case["expected"]["eligible_clause_ids_after_fresh_native_check"], sorted([fixture.TYPE_CLAUSE, fixture.OFFSET_CLAUSE]))
        self.assertEqual(next_case["expected"]["residual_clause_ids"], [])
        self.assertEqual(base["requirements"], next_case["requirements"])
        self.assertEqual(base["training_truth"]["body_offset"], 1)
        self.assertEqual(next_case["training_truth"]["body_offset"], 2)
        self.assertEqual(base["requirements"]["desired_offset"], 2)
        self.assertNotEqual(base["source_snapshot_sha256"], next_case["source_snapshot_sha256"])

    def test_same_name_decoy_has_a_different_exact_selector(self):
        records = {row["path"]: row for row in self.baseline["sources"]}
        selected, decoy = records["calc.py"], records["decoy.py"]
        self.assertEqual(selected["symbols"][0]["symbol_name"], decoy["symbols"][0]["symbol_name"])
        self.assertNotEqual(selected["sha256"], decoy["sha256"])
        self.assertNotEqual(selected["symbols"][0]["selector_id"], decoy["symbols"][0]["selector_id"])
        self.assertEqual(self.cases["wrong_named_target"]["expected"]["residual_clause_ids"], [])
        self.assertEqual(self.baseline["selected"]["path"], "calc.py")

    def test_dependencies_and_unsupported_inventory_are_retained(self):
        records = {row["path"]: row for row in self.baseline["sources"]}
        self.assertEqual(set(records), {"calc.py", "decoy.py", "helpers.py", "consumer.py", "effectful.py"})
        self.assertEqual(records["consumer.py"]["dependencies"], ["calc.py", "helpers.py"])
        self.assertIn("effectful.py", self.baseline["expected"]["unsupported_inventory_paths"])
        with self.assertRaises(ValueError):
            fixture.authored_reference_rows(self.baseline["source_bytes"]["effectful.py"], fixture.INPUTS)

    def test_raw_unicode_and_crlf_symbol_spans_preserve_exact_bytes(self):
        for case_id in ("unicode_span", "crlf_span", "unicode_crlf_span", "formatting"):
            with self.subTest(case=case_id):
                case = self.cases[case_id]
                raw = case["source_bytes"]["calc.py"]
                selector = case["selected"]["selector"]
                selected = raw[selector["start_byte"]:selector["end_byte"]]
                self.assertTrue(selected.startswith(b"def increment("))
                self.assertTrue(selected.endswith(b"return n + 1"))
                self.assertEqual(fixture.sha256(selected), selector["source_slice_sha256"])
                self.assertEqual(fixture.sha256(raw), case["selected"]["source_sha256"])
        combined = self.cases["unicode_crlf_span"]
        raw = combined["source_bytes"]["calc.py"]
        self.assertNotEqual(raw.index(b"def increment"), raw.decode("utf-8").index("def increment"))
        self.assertIn(b"\r\n", raw)

    def test_guard_changes_preserve_training_truth_and_unsupported_disposition(self):
        positive, negative = self.cases["changed_guard"], self.cases["changed_guard_polarity"]
        self.assertNotEqual(positive["training_truth"]["source_sha256"], negative["training_truth"]["source_sha256"])
        self.assertIsNone(positive["training_truth"]["body_offset"])
        self.assertNotEqual(positive["expected"]["reference_rows"], negative["expected"]["reference_rows"])
        for case in (positive, negative):
            self.assertEqual(case["expected"]["route_disposition"], "unsupported_source")
            self.assertEqual(case["expected"]["eligible_clause_ids_after_fresh_native_check"], [])
            self.assertEqual(case["expected"]["counterexamples"], [])
            self.assertEqual(case["expected"]["residual_clause_ids"], sorted([fixture.TYPE_CLAUSE, fixture.OFFSET_CLAUSE]))

    def test_negative_meaning_keeps_every_original_clause_and_span(self):
        for case in self.cases.values():
            prompt = case["requirements"]["original_prompt"]
            raw = prompt.encode("utf-8")
            for clause in case["requirements"]["clauses"]:
                self.assertEqual(prompt[clause["start_char"]:clause["end_char"]], clause["text"])
                self.assertEqual(raw[clause["start_byte"]:clause["end_byte"]].decode("utf-8"), clause["text"])
            if case["expected"]["route_disposition"] == "refusal_invalid_cnl":
                self.assertEqual(case["expected"]["eligible_clause_ids_after_fresh_native_check"], [])
                self.assertEqual(case["expected"]["residual_clause_ids"], case["expected"]["preserved_clause_ids"])
                self.assertTrue(case["expected"]["parser_refusal_must_preserve_original_ledger"])
        self.assertEqual(len(self.cases["effect_requirement"]["requirements"]["clauses"]), 3)

    def test_changed_requirement_and_domain_change_binding_without_relabeling_source(self):
        for name in ("changed_requirement", "changed_domain"):
            case = self.cases[name]
            self.assertEqual(case["training_truth"], self.baseline["training_truth"])
            self.assertNotEqual(case["requirements"]["ledger_sha256"], self.baseline["requirements"]["ledger_sha256"])
        self.assertTrue(self.baseline["training_truth"]["desired_requirement_excluded"])
        self.assertFalse(self.baseline["requirements"]["training_truth_is_requirement_input"])

    def test_generator_is_deterministic_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as temporary:
            first, second = Path(temporary) / "one", Path(temporary) / "two"
            initial, repeated = fixture.generate(first), fixture.generate(second)
            self.assertEqual(initial, repeated)
            self.assertEqual((first / "manifest.json").read_bytes(), (second / "manifest.json").read_bytes())
            fixture.validate_materialized_sources(first, initial)
            with self.assertRaisesRegex(ValueError, "fresh"):
                fixture.generate(first)
            (first / "scenarios/baseline/source/calc.py").write_bytes(fixture.source_function(2))
            with self.assertRaisesRegex(ValueError, "exact source"):
                fixture.validate_materialized_sources(first, initial)

    def test_manifest_hash_and_snapshot_bind_file_bytes_and_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fixtures"
            manifest = fixture.generate(output)
            manifest["scenarios"][0]["selected"]["path"] = "decoy.py"
            with self.assertRaisesRegex(ValueError, "manifest identity"):
                fixture.validate_materialized_sources(output, manifest)
        for path in ("../calc.py", "/calc.py", "nested/../calc.py"):
            with self.assertRaises(ValueError):
                fixture.source_record(path, fixture.source_function())

    def test_evidence_mutations_are_specifications_without_fake_authority(self):
        specs = fixture.evidence_mutation_specs(self.baseline)
        self.assertIn("wrong_checkpoint", {row["mutation_id"] for row in specs})
        self.assertIn("same_head_source_edit", {row["mutation_id"] for row in specs})
        self.assertIn("caller_preview_admission", {row["mutation_id"] for row in specs})
        self.assertTrue(all(row["expected_disposition"] == "refusal" for row in specs))
        self.assertTrue(all(row["evidence_generated"] is False for row in specs))

    def test_corpus_cohort_exports_real_clone_revision_and_dependency_leaks(self):
        corpus = fixture.corpus_audit_input(list(self.cases.values()))
        units = {row["id"]: row for row in corpus["units"]}
        self.assertEqual(units["baseline:consumer.py"]["dependencies"], ["baseline:calc.py", "baseline:helpers.py"])
        self.assertEqual(units["baseline:consumer.py"]["role"], "final")
        self.assertEqual(units["baseline:calc.py"]["role"], "train")
        self.assertIn("baseline:calc.py", units["successor:calc.py"]["related_revisions"])
        for unit in units.values():
            raw = bytes.fromhex(unit["source"]["bytes_hex"])
            self.assertEqual(fixture.sha256(raw), unit["content_sha256"])

    @unittest.skipUnless(shutil.which("git"), "same-HEAD control requires git")
    def test_real_git_same_head_edit_changes_source_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary)
            environment = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
            def git(*arguments):
                return subprocess.check_output(["git", "-C", str(repository), *arguments],
                    text=True, env=environment, stderr=subprocess.STDOUT, timeout=20).strip()
            (repository / "calc.py").write_bytes(fixture.source_function())
            git("init", "-q")
            git("add", "calc.py")
            git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", "commit", "-qm", "source")
            commit = git("rev-parse", "HEAD")
            before = fixture.source_record("calc.py", (repository / "calc.py").read_bytes())
            (repository / "calc.py").write_bytes(fixture.source_function(2))
            after = fixture.source_record("calc.py", (repository / "calc.py").read_bytes())
            self.assertEqual(git("rev-parse", "HEAD"), commit)
            self.assertNotEqual(before["sha256"], after["sha256"])
            self.assertNotEqual(before["symbols"][0]["selector_id"], after["symbols"][0]["selector_id"])


class NativeResultComparatorTests(unittest.TestCase):
    def setUp(self):
        self.case = fixture.scenarios()[0]
        self.record = shaped_result(self.case)

    def test_comparator_rejects_duplicate_clause_results(self):
        self.record["clause_results"].append(copy.deepcopy(self.record["clause_results"][0]))
        with self.assertRaisesRegex(ValueError, "unique clause"):
            fixture.validate_native_result(self.record, self.case)

    def test_same_length_duplicate_clauses_cannot_hide_missing_clause(self):
        self.record["clause_results"][1] = copy.deepcopy(self.record["clause_results"][0])
        with self.assertRaisesRegex(ValueError, "every clause"):
            fixture.validate_native_result(self.record, self.case)

    def test_bool_input_domain_cannot_equal_integer_domain(self):
        self.record["observation"]["domain_inputs"] = [-2, -1, False, True, 2]
        with self.assertRaisesRegex(ValueError, "finite domain"):
            fixture.validate_native_result(self.record, self.case)

    def test_bool_trace_input_or_output_cannot_equal_integer(self):
        for field, row_index, value in (("input", 2, False), ("input", 3, True), ("output", 2, True)):
            with self.subTest(field=field, row=row_index):
                record = copy.deepcopy(self.record)
                record["observation"]["observations"][row_index][field] = value
                with self.assertRaisesRegex(ValueError, "exact integer"):
                    fixture.validate_native_result(record, self.case)

    def test_bool_counterexample_cannot_equal_integer_witness(self):
        self.record["finite_counterexamples"] = copy.deepcopy(self.record["finite_counterexamples"])
        self.record["finite_counterexamples"][2]["input"] = False
        with self.assertRaisesRegex(ValueError, "exact integer witnesses"):
            fixture.validate_native_result(self.record, self.case)

    def test_current_root_predicate_binding_and_selected_source_are_exact(self):
        controls = ("root", "predicate", "path", "digest", "missing_fact", "extra_task", "authority")
        for control in controls:
            with self.subTest(control=control):
                record = copy.deepcopy(self.record)
                if control == "root":
                    record["current_facts"][0]["current_root_id"] = "foreign-root"
                elif control == "predicate":
                    record["clause_results"][0]["predicate_id"] = record["clause_results"][1]["predicate_id"]
                elif control == "path":
                    record["observation"]["source_path"] = "decoy.py"
                elif control == "digest":
                    record["observation"]["source_sha256"] = "0" * 64
                elif control == "missing_fact":
                    record["current_facts"] = []
                elif control == "extra_task":
                    record["removed_task_ids"] = ["task:invented"]
                else:
                    record["proof_authority"] = True
                with self.assertRaises(ValueError):
                    fixture.validate_native_result(record, self.case)

    def test_comparator_refuses_non_cnl_meaning_even_with_shaped_result(self):
        case = next(case for case in fixture.scenarios() if case["scenario_id"] == "unbounded")
        with self.assertRaisesRegex(ValueError, "parser refusal"):
            fixture.validate_native_result(self.record, case)

    def test_json_roundtrip_does_not_drop_negative_instruction(self):
        case = next(case for case in fixture.scenarios() if case["scenario_id"] == "prohibition")
        retained = json.loads(fixture.canonical_bytes(case["requirements"]))
        self.assertIn("must not", retained["original_prompt"])
        self.assertEqual(len(retained["clauses"]), 2)


if __name__ == "__main__":
    unittest.main()
