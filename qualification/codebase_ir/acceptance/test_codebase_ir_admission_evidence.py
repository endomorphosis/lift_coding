"""Independent refusal controls against recorded public admission assertions."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import codebase_ir_admission_evidence as evidence
import codebase_ir_admission_history as history


class AdmissionCorrelationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        reference = json.loads(Path(__file__).with_name("admission_regression_reference.json").read_bytes())
        if reference["authority"] != "assertion_reference_only":
            raise AssertionError("regression data cannot become native evidence")
        cls.reference = reference["records"]

    def setUp(self):
        self.records = copy.deepcopy(self.reference)
        self.admission = self.records["before-admission.json"]

    def rehash(self, record_name="before-admission.json"):
        admission = self.records[record_name]
        local = admission["local_admission"]
        if local is not None:
            local["graph"] = copy.deepcopy(admission["graph"])
            local["manifest"] = copy.deepcopy(admission["declaration"]["payload"]["manifest"])
        receipt = admission["receipt"]["payload"]
        receipt.update({"declaration_cid": evidence.cid(admission["declaration"]), "graph_cid": evidence.cid(admission["graph"]),
            "evidence_cid": evidence.cid(admission["evidence"]), "semantic_context_cid": evidence.cid(receipt["semantic_context"]),
            "local_admission_cid": evidence.cid(local)})
        if record_name == "before-admission.json":
            self.records["before-declaration.json"] = copy.deepcopy(admission["declaration"])
            self.records["referenced_admission"] = copy.deepcopy(admission)

    def assert_refused(self):
        self.rehash()
        with self.assertRaises(evidence.AdmissionEvidenceError):
            evidence.assert_fixture(self.records)

    def test_original_population_and_successor_scope_preserved(self):
        result = evidence.assert_fixture(self.records)
        self.assertEqual(result["actual_preserved_task_population"]["task_keys"], ["FINITE-OFFSET", "FINITE-TYPE"])
        self.assertFalse(result["actual_preserved_task_population"]["native_task_store_reopened"])
        self.assertTrue(result["successor"]["no_work_review_only"])

    def test_all_authored_corruptions_refused_after_correlating_unsigned_links(self):
        controls = evidence.mutation_controls(self.records)
        self.assertEqual(len(controls), 29)
        self.assertTrue(all(row["outcome"] == "refused" for row in controls))

    def test_foreign_executable_rejected_even_with_recomputed_validation_identity(self):
        validation = self.admission["graph"]["tasks"][0]["validations"][0]
        validation["argv"][0] = "/foreign/python"
        validation["content_id"] = evidence.cid({k: v for k, v in validation.items() if k != "content_id"})
        task = self.admission["graph"]["tasks"][0]
        task["content_id"] = evidence.cid(evidence._workflow_payload({k: v for k, v in task.items() if k != "content_id"}))
        with self.assertRaisesRegex(evidence.AdmissionEvidenceError, "complete signed validations"):
            evidence.assert_admission(self.admission, successor=False)

    def test_foreign_validation_policy_refused(self):
        self.admission["graph"]["tasks"][0]["validations"][0]["policy_cid"] = "foreign:policy"
        self.assert_refused()

    def test_missing_required_authority_field_refused(self):
        self.admission["receipt"]["payload"].pop("execution_authority")
        self.assert_refused()

    def test_inner_local_receipt_cannot_grant_execution(self):
        self.admission["local_admission"]["receipt"]["payload"]["execution_authority"] = True
        self.assert_refused()

    def test_false_fact_is_not_satisfied_context(self):
        self.admission["evidence"]["match"]["current_facts"][0]["truth"] = "false"
        self.assert_refused()

    def test_fact_property_cannot_be_relabelled(self):
        self.admission["evidence"]["match"]["current_facts"][0]["predicate"]["property_id"] = "finite_integer_offset"
        self.assert_refused()

    def test_correlated_predicate_mapping_cannot_relabel_original_requirement(self):
        match = self.admission["evidence"]["match"]
        match["typed_intent"]["metadata"]["requirement_predicate_ids"][evidence.TYPE_CLAUSE] = "foreign:predicate"
        match["current_facts"][0]["predicate"]["predicate_id"] = "foreign:predicate"
        self.assert_refused()

    def test_correlated_source_labels_cannot_replace_observed_artifact_identity(self):
        self.admission["evidence"]["match"]["source_cid"] = "foreign:source"
        self.admission["receipt"]["payload"]["semantic_context"]["source_cid"] = "foreign:source"
        self.assert_refused()

    def test_all_admission_profiles_require_exact_selected_source_population(self):
        for record_name in ("before-admission.json", "successor-admission.json", "cold-admission.json"):
            for group in evidence.SOURCE_PIN_MODULES:
                for mutation in ("empty", "partial", "extra"):
                    with self.subTest(record=record_name, group=group, mutation=mutation):
                        self.records = copy.deepcopy(self.reference)
                        pins = evidence.source_pin_groups(self.records[record_name])[group]
                        if mutation == "empty":
                            pins.clear()
                        elif mutation == "partial":
                            pins.pop(next(iter(pins)))
                        else:
                            pins["foreign.extra_module"] = "a" * 64
                        self.rehash(record_name)
                        with self.assertRaisesRegex(evidence.AdmissionEvidenceError, "exact selected source pin population"):
                            evidence.assert_fixture(self.records)

    def test_all_admission_profiles_require_lowercase_sha256_source_values(self):
        for record_name in ("before-admission.json", "successor-admission.json", "cold-admission.json"):
            for group in evidence.SOURCE_PIN_MODULES:
                for invalid in (None, True, 0, ["a" * 64], "a" * 63, "a" * 65, "A" * 64, "g" * 64):
                    with self.subTest(record=record_name, group=group, invalid=invalid):
                        self.records = copy.deepcopy(self.reference)
                        pins = evidence.source_pin_groups(self.records[record_name])[group]
                        pins[next(iter(pins))] = invalid
                        self.rehash(record_name)
                        with self.assertRaisesRegex(evidence.AdmissionEvidenceError, "lowercase SHA256 source pins"):
                            evidence.assert_fixture(self.records)

    def test_cold_comparison_cannot_claim_agreement_after_dropping_fields(self):
        self.records["cold-comparison.json"]["agreement"] = False
        self.records["cold-comparison.json"]["compared_fields"] = []
        self.assert_refused()

    def test_query_retargeting_cannot_select_same_name_decoy(self):
        self.admission["receipt"]["payload"]["semantic_context"]["query"]["contract"]["path"] = "decoy.py"
        self.assert_refused()

    def test_original_source_clause_span_cannot_change(self):
        declaration = self.admission["declaration"]["payload"]
        document = json.loads(declaration["intent_json"])
        document["sources"][0]["span"]["start_char"] += 1
        declaration["intent_json"] = evidence.canonical(document).decode()
        self.assert_refused()

    def test_workflow_identity_cannot_hide_changed_acceptance(self):
        self.admission["graph"]["tasks"][0]["acceptance"][0]["criterion"] = "Always passes"
        self.assert_refused()


class BoundedAdmissionInputTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.path = self.root / "input.json"

    def test_remaining_total_budget_applies_before_allocation(self):
        self.path.write_bytes(b'{}')
        reader = evidence.ArtifactReader(self.root)
        with patch.object(evidence, "MAX_TOTAL_BYTES", 1):
            with self.assertRaises(ValueError):
                reader.read(self.path)
        self.assertEqual(reader.pins, {})

    def test_file_count_refused_before_open(self):
        self.path.write_bytes(b'{}')
        reader = evidence.ArtifactReader(self.root)
        with patch.object(evidence, "MAX_FILES", 0), patch.object(evidence, "_bounded_document") as read:
            with self.assertRaisesRegex(ValueError, "count"):
                reader.read(self.path)
        read.assert_not_called()

    def test_changed_artifact_refused_on_recheck(self):
        self.path.write_bytes(b'{}')
        reader = evidence.ArtifactReader(self.root)
        reader.read(self.path)
        self.path.write_bytes(b'[]')
        with self.assertRaisesRegex(ValueError, "changed"):
            reader.recheck()

    def test_symlink_and_fifo_refused(self):
        real = self.root / "real.json"
        real.write_bytes(b'{}')
        self.path.symlink_to(real)
        reader = evidence.ArtifactReader(self.root)
        with self.assertRaises(ValueError):
            reader.read(self.path)
        self.path.unlink()
        os.mkfifo(self.path)
        with self.assertRaises(ValueError):
            reader.read(self.path)

    def test_duplicate_nonfinite_and_overdeep_json_refused(self):
        for raw in (b'{"verified":false,"verified":true}', b'{"v":1e999}', b'[' * 65 + b'0' + b']' * 65):
            with self.subTest(raw=raw[:40]):
                with self.assertRaises(ValueError):
                    evidence.parse_document(raw)

    def test_historical_guard_refuses_writes_and_process_launch(self):
        trace = history.ReadOnlyTrace([self.root], [])
        for event, args in (("open", (str(self.path), "w", os.O_WRONLY | os.O_CREAT)),
                            ("subprocess.Popen", (sys.executable,)), ("os.mkdir", (str(self.path), 0o700, -1)),
                            ("socket.connect", ())):
            with self.subTest(event=event):
                with self.assertRaises(history.HistoricalReplayRefusal):
                    trace.audit(event, args)
        self.assertFalse(self.path.exists())

    def test_historical_directory_relative_read_is_scoped_and_pinned(self):
        raw = b'{"public":"authored-test"}'
        self.path.write_bytes(raw)
        trace = history.ReadOnlyTrace([self.root], [])
        descriptor = trace.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            child = trace.open("input.json", os.O_RDONLY, dir_fd=descriptor)
            try:
                self.assertEqual(os.read(child, 100), raw)
            finally:
                os.close(child)
        finally:
            os.close(descriptor)
        self.assertEqual(trace.before[str(self.path)]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertIn(str(self.root), trace.directories)
        foreign = self.root / "foreign"
        foreign.mkdir()
        restricted = history.ReadOnlyTrace([foreign], [])
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY)
        try:
            with self.assertRaises(history.HistoricalReplayRefusal):
                restricted.open("input.json", os.O_RDONLY, dir_fd=descriptor)
        finally:
            os.close(descriptor)

    def test_relocated_replay_child_uses_explicit_workspace(self):
        script = self.root / "child.py"
        script.write_text('import json; print(json.dumps({"status":"passed","observed_current":False,"current_launch_permission_claimed":False}))\n')
        output = self.root / "output"
        output.mkdir()
        with patch.object(history, "__file__", str(script)):
            report = history.launch_historical_replay(self.root, output, python=Path(sys.executable),
                expected_result_sha256=hashlib.sha256(b'{}').hexdigest(), workspace=self.root)
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["command"][-2:], ["--workspace", str(self.root)])

    def test_sealed_historical_roots_require_identity_and_exact_binding(self):
        roots = [self.root / "accelerate", self.root / "datasets"]
        for selected, digest in ((roots, None), (None, "a" * 64), ([], ""), (None, "")):
            with self.assertRaisesRegex(history.HistoricalReplayRefusal, "both exact roots"):
                history.select_runtime_roots(self.root, selected, digest)
        expected = {"snapshot_sha256": "a" * 64, "verified": True}
        with patch.object(history, "verify_snapshot_binding", return_value=expected) as verify:
            actual_roots, observation = history.select_runtime_roots(self.root, roots, "a" * 64)
        self.assertEqual(actual_roots, roots)
        self.assertEqual(observation, expected)
        verify.assert_called_once_with(roots, "a" * 64)

    def test_sealed_history_imports_refuse_missing_module_and_live_fallback(self):
        roots = [self.root / "sealed"]
        finder = history.ObservedCoreFinder(roots, history.ReadOnlyTrace(roots, []))
        with patch.object(history.importlib.machinery.PathFinder, "find_spec", return_value=None):
            with self.assertRaisesRegex(ImportError, "unavailable"):
                finder.find_spec("ipfs_accelerate_py.absent")
        live = SimpleNamespace(origin="/workspace/live/ipfs_accelerate_py/__init__.py", submodule_search_locations=[])
        with patch.object(history.importlib.machinery.PathFinder, "find_spec", return_value=live):
            with self.assertRaisesRegex(history.HistoricalReplayRefusal, "escaped"):
                finder.find_spec("ipfs_accelerate_py")

    def test_sealed_replay_launcher_forwards_exact_snapshot_identity(self):
        script = self.root / "snapshot-child.py"
        script.write_text('import json; print(json.dumps({"status":"unavailable","observed_current":False,"current_launch_permission_claimed":False,"blocker":"authored missing module"}))\n')
        output = self.root / "snapshot-output"
        output.mkdir()
        roots = [self.root / "accelerate", self.root / "datasets"]
        with patch.object(history, "__file__", str(script)):
            report = history.launch_historical_replay(self.root, output, python=Path(sys.executable),
                expected_result_sha256=hashlib.sha256(b'{}').hexdigest(), workspace=self.root,
                snapshot_roots=roots, snapshot_sha256="a" * 64)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["command"][-6:], ["--snapshot-root", str(roots[0]), "--snapshot-root", str(roots[1]), "--snapshot-sha256", "a" * 64])
        self.assertFalse(report["observed_current"])

    def test_missing_or_drifting_selected_producer_pin_is_explicit(self):
        records = json.loads(Path(__file__).with_name("admission_regression_reference.json").read_bytes())["records"]
        finder = history.ObservedCoreFinder([self.root], history.ReadOnlyTrace([self.root], []))
        groups = evidence.source_pin_groups(records["before-admission.json"])
        for pins in groups.values():
            for module, digest in pins.items():
                finder.observations[str(self.root / (module + ".py"))] = {"module_names": [module], "before": {"sha256": digest, "size_bytes": 1}}
        comparison = history.retained_producer_comparison(records, finder)
        self.assertTrue(comparison["signed_producer"]["all_match"])
        self.assertTrue(comparison["model_frontend"]["all_match"])
        self.assertEqual(comparison["signed_producer"]["expected_count"], 6)
        self.assertEqual(comparison["model_frontend"]["expected_count"], 9)
        module = "ipfs_datasets_py.logic.backends.process"
        path = str(self.root / (module + ".py"))
        del finder.observations[path]
        comparison = history.retained_producer_comparison(records, finder)
        self.assertFalse(comparison["model_frontend"]["all_match"])
        finder.observations[path] = {"module_names": [module], "before": {"sha256": "c" * 64, "size_bytes": 1}}
        comparison = history.retained_producer_comparison(records, finder)
        self.assertFalse(comparison["model_frontend"]["all_match"])

    def test_historical_precheck_refuses_empty_partial_extra_and_invalid_source_pins(self):
        original = json.loads(Path(__file__).with_name("admission_regression_reference.json").read_bytes())["records"]
        finder = history.ObservedCoreFinder([self.root], history.ReadOnlyTrace([self.root], []))
        for group in evidence.SOURCE_PIN_MODULES:
            for mutation in ("empty", "partial", "extra", "invalid"):
                with self.subTest(group=group, mutation=mutation):
                    records = copy.deepcopy(original)
                    pins = evidence.source_pin_groups(records["before-admission.json"])[group]
                    if mutation == "empty":
                        pins.clear()
                    elif mutation == "partial":
                        pins.pop(next(iter(pins)))
                    elif mutation == "extra":
                        pins["foreign.extra_module"] = "a" * 64
                    else:
                        pins[next(iter(pins))] = True
                    with self.assertRaises(evidence.AdmissionEvidenceError):
                        history.retained_producer_comparison(records, finder)


if __name__ == "__main__":
    unittest.main()
