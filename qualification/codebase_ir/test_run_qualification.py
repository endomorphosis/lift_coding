"""Controls for retaining independent evidence without ambiguous or blocking input."""
from __future__ import annotations

import copy
import hashlib
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_qualification as runner


class ReportInputTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.report = self.root / "report.json"

    def test_exact_retained_bytes_and_hash_preserve_unknown_scope(self):
        raw = b'{ "status": "incomplete", "native_closure_certification_verified": false }\n'
        self.report.write_bytes(raw)
        target = self.root / "retained.json"
        pin = runner.retain_input(self.report, target)
        self.assertEqual(target.read_bytes(), raw)
        self.assertEqual(pin["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertFalse(runner.read_report(target)[1]["native_closure_certification_verified"])

    def test_nested_duplicate_authority_claim_is_refused(self):
        self.report.write_bytes(b'{"scope":{"verified":false,"verified":true}}')
        with self.assertRaisesRegex(ValueError, "duplicate"):
            runner.read_report(self.report)

    def test_nonfinite_and_nonobject_reports_are_refused(self):
        for raw in (b'{"value":NaN}', b'{"value":Infinity}', b'{"value":-Infinity}',
                    b'{"value":1e999}', b'[]'):
            with self.subTest(raw=raw):
                self.report.write_bytes(raw)
                with self.assertRaises(ValueError):
                    runner.read_report(self.report)

    def test_symbolic_link_report_is_refused(self):
        real = self.root / "real.json"
        real.write_bytes(b'{}')
        self.report.symlink_to(real)
        with self.assertRaises(OSError):
            runner.read_report(self.report)

    def test_fifo_report_is_refused_without_a_writer(self):
        os.mkfifo(self.report)
        with self.assertRaisesRegex(ValueError, "regular"):
            runner.read_report(self.report)

    def test_oversized_report_refused_before_read(self):
        with self.report.open("wb") as stream:
            stream.truncate(runner.MAX_REPORT_BYTES + 1)
        with self.assertRaisesRegex(ValueError, "16 MiB"):
            runner.read_report(self.report)

    def test_metadata_change_during_read_does_not_retain_report(self):
        self.report.write_bytes(b'{"verified":false}')
        native_fstat = os.fstat
        calls = 0

        def changed_fstat(descriptor):
            nonlocal calls
            calls += 1
            observed = native_fstat(descriptor)
            if calls == 2:
                # Same size and inode, but the producer changed its observation.
                values = list(observed)
                values[8] += 1
                return os.stat_result(values)
            return observed

        with patch.object(runner.os, "fstat", changed_fstat):
            with self.assertRaisesRegex(ValueError, "changed"):
                runner.retain_input(self.report, self.root / "retained.json")
        self.assertFalse((self.root / "retained.json").exists())

    def test_incomplete_workflow_arguments_refuse_before_execution(self):
        for arguments in (["--closure-response", str(self.report)],
                          ["--closure-cohort-inventory"],
                          ["--admission-historical-replay"],
                          ["--admission-replay-python", sys.executable],
                          ["--admission-snapshot-root", str(self.root)],
                          ["--admission-snapshot-sha256", "0" * 64],
                          ["--admission-snapshot-root", str(self.root),
                           "--admission-snapshot-sha256", "0" * 64],
                          ["--admission-historical-replay", "--admission-retained-fixture", str(self.root),
                           "--admission-snapshot-root", str(self.root),
                           "--admission-snapshot-sha256", "not-a-generation"],
                          ["--locked-final-evaluation-manifest", str(self.report)],
                          ["--final-protocol-lock", str(self.report)],
                          ["--final-protocol-lock-sha256", "1" * 64],
                          ["--final-protocol-lock", str(self.report),
                           "--final-protocol-lock-sha256", "1" * 64],
                          ["--locked-final-evaluation-manifest", str(self.report),
                           "--final-protocol-lock", str(self.report),
                           "--final-protocol-lock-sha256", "invalid-lock-pin"]):
            with self.subTest(arguments=arguments):
                output = self.root / "never-created"
                completed = subprocess.run(
                    [sys.executable, "-I", "-B", runner.__file__, "--output", str(output), *arguments],
                    capture_output=True, timeout=5, check=False)
                self.assertEqual(completed.returncode, 2)
                self.assertIn(b"requires", completed.stderr)
                self.assertFalse(output.exists())

    def sealed_history(self):
        roots = [self.root / "accelerate", self.root / "datasets"]
        identity = "1" * 64
        verification = {"verified": True, "snapshot_sha256": identity,
                        "snapshot_roots": [str(root) for root in roots]}
        history = {"status": "passed", "observed_current": False,
                   "current_launch_permission_claimed": False, "task_store_opened": False,
                   "native_observation_or_proof_invoked": False, "worker_launched": False,
                   "training_steps": 0, "runtime_source_mode": "sealed_snapshot_read_only",
                   "runtime_snapshot_roots": verification["snapshot_roots"],
                   "requested_runtime_snapshot_sha256": identity, "runtime_snapshot_identity_stable": True,
                   "read_files_unchanged": True, "runtime_snapshot_before": verification,
                   "runtime_snapshot_after": copy.deepcopy(verification), "retained_producer_comparison": {}}
        for name, count in (("signed_producer", 6), ("model_frontend", 9)):
            pins = [{"matches_retained_pin": True, "expected_sha256": "2" * 64,
                     "module": f"{name}.module_{index}",
                     "actual_preexec_pin": {"sha256": "2" * 64}} for index in range(count)]
            history["retained_producer_comparison"][name] = {"expected_count": count, "all_match": True, "pins": pins}
        return history, roots, identity

    def test_sealed_history_requires_requested_generation_and_complete_producer_pins(self):
        history, roots, identity = self.sealed_history()
        self.assertTrue(runner.historical_replay_passed(history, roots, identity))
        for field, changed in (("runtime_snapshot_roots", []), ("runtime_snapshot_identity_stable", False),
                               ("runtime_snapshot_after", {"verified": True}),
                               ("requested_runtime_snapshot_sha256", "3" * 64)):
            with self.subTest(field=field):
                mutated = copy.deepcopy(history)
                mutated[field] = changed
                self.assertFalse(runner.historical_replay_passed(mutated, roots, identity))
        for group in ("signed_producer", "model_frontend"):
            with self.subTest(group=group):
                mutated = copy.deepcopy(history)
                mutated["retained_producer_comparison"][group]["pins"] = []
                self.assertFalse(runner.historical_replay_passed(mutated, roots, identity))
                mutated["retained_producer_comparison"][group]["pins"] = [history["retained_producer_comparison"][group]["pins"][0]] * len(
                    history["retained_producer_comparison"][group]["pins"])
                self.assertFalse(runner.historical_replay_passed(mutated, roots, identity))
        mutated = copy.deepcopy(history)
        mutated["retained_producer_comparison"]["signed_producer"]["pins"][0]["actual_preexec_pin"]["sha256"] = "3" * 64
        self.assertFalse(runner.historical_replay_passed(mutated, roots, identity))

    def test_historical_refusal_and_authority_changes_cannot_pass_the_join(self):
        history, roots, identity = self.sealed_history()
        for field, changed in (("status", "unavailable"), ("status", "refused"),
                               ("observed_current", True), ("worker_launched", True),
                               ("task_store_opened", True), ("training_steps", False),
                               ("native_observation_or_proof_invoked", True)):
            with self.subTest(field=field, changed=changed):
                mutated = copy.deepcopy(history)
                mutated[field] = changed
                self.assertFalse(runner.historical_replay_passed(mutated, roots, identity))

    def isolated_result(self, workflow):
        identity = "a" * 64
        profile = runner.ISOLATED_WORKFLOWS[workflow]
        payload = {"schema": profile["schema"], "status": "passed",
                   "input_files_unchanged": True, "native_execution_performed": False,
                   "training_executed": False, "current_authority_claimed": False}
        payload[profile.get("manifest_binding_field", "manifest_sha256")] = identity
        payload.update({field: False for field in profile["false_flags"]})
        payload.update({field: True for field in profile.get("true_flags", ())})
        payload.update({field: 0 for field in profile.get("zero_fields", ())})
        payload.update({field: "c" * 64 for field in profile.get("binding_fields", ())})
        if "report_binding_roles" in profile:
            payload["selected_files"] = [{"role": role, "sha256": "c" * 64} for role in profile["report_binding_roles"]]
        return payload, identity

    def scoped_result_passed(self, payload, workflow, identity):
        bindings = {field: "c" * 64 for field in runner.ISOLATED_WORKFLOWS[workflow].get("binding_fields", ())}
        return runner.isolated_workflow_passed(payload, workflow, identity, bindings)

    def test_offline_findings_do_not_require_successful_model_or_clean_release(self):
        for workflow in runner.ISOLATED_WORKFLOWS:
            with self.subTest(workflow=workflow):
                payload, identity = self.isolated_result(workflow)
                payload["findings"] = {"rejected_predictions": 2, "unavailable_evidence": 1,
                                       "incomplete_historical_attempts": 3}
                self.assertTrue(self.scoped_result_passed(payload, workflow, identity))

    def test_isolated_results_require_exact_manifest_and_workflow_identity(self):
        for workflow in runner.ISOLATED_WORKFLOWS:
            payload, identity = self.isolated_result(workflow)
            binding_field = runner.ISOLATED_WORKFLOWS[workflow].get("manifest_binding_field", "manifest_sha256")
            for field, changed in ((binding_field, "b" * 64), ("schema", "foreign@1"),
                                   ("status", "refused"), ("input_files_unchanged", False)):
                with self.subTest(workflow=workflow, field=field):
                    altered = dict(payload, **{field: changed})
                    self.assertFalse(self.scoped_result_passed(altered, workflow, identity))
            self.assertFalse(self.scoped_result_passed(payload, workflow, "not-a-pin"))

    def test_offline_audit_cannot_claim_execution_or_current_authority(self):
        for workflow in runner.ISOLATED_WORKFLOWS:
            payload, identity = self.isolated_result(workflow)
            flags = ("native_execution_performed", "training_executed", "current_authority_claimed",
                     *runner.ISOLATED_WORKFLOWS[workflow]["false_flags"])
            for field in flags:
                for changed in (True, 0, None):
                    with self.subTest(workflow=workflow, field=field, changed=changed):
                        altered = dict(payload, **{field: changed})
                        self.assertFalse(self.scoped_result_passed(altered, workflow, identity))
                altered = dict(payload)
                del altered[field]
                self.assertFalse(self.scoped_result_passed(altered, workflow, identity))

    def test_retained_offline_result_preserves_its_authored_input_scope(self):
        payload, identity = self.isolated_result("final_evaluation")
        payload["prediction_origin"] = "independently_authored_demonstration"
        import json
        self.report.write_text(json.dumps(payload))
        pin = runner.retain_input(self.report, self.root / "retained.json")
        raw, retained = runner.read_report(self.root / "retained.json")
        self.assertEqual(pin["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(retained["prediction_origin"], "independently_authored_demonstration")
        self.assertTrue(self.scoped_result_passed(retained, "final_evaluation", identity))

    def test_relative_bundle_manifest_cannot_change_after_retention(self):
        self.report.write_bytes(b'{"protocol":{"path":"protocol.json"}}')
        pin = runner.retain_input(self.report, self.root / "retained.json")
        self.assertTrue(runner.input_pin_unchanged(pin))
        self.report.write_bytes(b'{"protocol":{"path":"other.json"}}')
        self.assertFalse(runner.input_pin_unchanged(pin))
        self.report.unlink()
        self.assertFalse(runner.input_pin_unchanged(pin))

    def test_final_export_cannot_certify_parent_exposure_or_rewrite_raw_predictions(self):
        payload, identity = self.isolated_result("final_evaluation")
        for field in runner.ISOLATED_WORKFLOWS["final_evaluation"]["true_flags"]:
            for changed in (False, 1, None):
                with self.subTest(field=field, changed=changed):
                    altered = dict(payload, **{field: changed})
                    self.assertFalse(self.scoped_result_passed(altered, "final_evaluation", identity))

    def test_locked_final_result_requires_independent_expected_lock_hash(self):
        payload, identity = self.isolated_result("locked_final_evaluation")
        self.assertTrue(self.scoped_result_passed(payload, "locked_final_evaluation", identity))
        for binding in (None, {}, {"lock_sha256": "b" * 64}, {"lock_sha256": "not-a-pin"},
                        {"lock_sha256": True}, {"unexpected_sha256": "c" * 64}):
            with self.subTest(binding=binding):
                self.assertFalse(runner.isolated_workflow_passed(payload, "locked_final_evaluation", identity, binding))
        altered = dict(payload, lock_sha256="b" * 64)
        self.assertFalse(self.scoped_result_passed(altered, "locked_final_evaluation", identity))
        altered = dict(payload, lock_enforced=False)
        self.assertFalse(self.scoped_result_passed(altered, "locked_final_evaluation", identity))
        ordinary, spec_pin = self.isolated_result("final_evaluation")
        self.assertFalse(runner.isolated_workflow_passed(ordinary, "final_evaluation", spec_pin,
                                                       {"lock_sha256": "c" * 64}))

    def test_portable_review_must_bind_the_actual_bundle_manifest(self):
        payload, identity = self.isolated_result("portable_release_review")
        self.assertTrue(self.scoped_result_passed(payload, "portable_release_review", identity))
        payload.pop("bundle_manifest_sha256")
        payload["manifest_sha256"] = identity
        self.assertFalse(self.scoped_result_passed(payload, "portable_release_review", identity))

    def test_final_protocol_lock_is_rechecked_at_aggregate_completion(self):
        self.report.write_bytes(b'{"locked_identity":"original"}')
        pin = runner.retain_input(self.report, self.root / "retained-lock.json")
        pins = {"final_protocol_lock": pin}
        self.assertEqual(runner.changed_workflow_pins(pins), [])
        self.report.write_bytes(b'{"locked_identity":"changed"}')
        self.assertEqual(runner.changed_workflow_pins(pins), ["final_protocol_lock"])
        self.report.unlink()
        self.assertEqual(runner.changed_workflow_pins(pins), ["final_protocol_lock"])

    def test_frozen_body_verification_cannot_count_copied_epochs_as_new_training(self):
        payload, identity = self.isolated_result("frozen_auxiliary_evidence")
        self.assertTrue(self.scoped_result_passed(payload, "frozen_auxiliary_evidence", identity))
        for changed in (16, False, 0.0, None):
            with self.subTest(changed=changed):
                altered = dict(payload, additional_attempted_training_epochs=changed)
                self.assertFalse(self.scoped_result_passed(altered, "frozen_auxiliary_evidence", identity))

    def test_paired_comparison_lock_pin_is_taken_from_retained_input(self):
        payload, identity = self.isolated_result("paired_final_evaluation")
        manifest = {"lock": {"sha256": "c" * 64}}
        bindings = runner.workflow_manifest_bindings("paired_final_evaluation", manifest)
        self.assertTrue(runner.isolated_workflow_passed(payload, "paired_final_evaluation", identity, bindings))
        # A report cannot replace the caller's locked cohort with its own new pin.
        payload["lock_sha256"] = "d" * 64
        self.assertFalse(runner.isolated_workflow_passed(payload, "paired_final_evaluation", identity, bindings))

    def test_archive_and_inner_bundle_pins_are_independently_required(self):
        payload, identity = self.isolated_result("portable_release_archive")
        manifest = {"archive": {"sha256": "c" * 64}, "bundle_manifest_sha256": "c" * 64}
        bindings = runner.workflow_manifest_bindings("portable_release_archive", manifest)
        self.assertTrue(runner.isolated_workflow_passed(payload, "portable_release_archive", identity, bindings))
        for field in bindings:
            altered = dict(payload, **{field: "d" * 64})
            self.assertFalse(runner.isolated_workflow_passed(altered, "portable_release_archive", identity, bindings))
        self.assertFalse(runner.isolated_workflow_passed(payload, "portable_release_archive", identity,
                                                       {"archive_sha256": "c" * 64}))

    def test_protocol_response_custody_cannot_substitute_the_public_worker_source(self):
        payload, identity = self.isolated_result("worker_protocol_evidence")
        manifest = {"protocol_worker_source": {"sha256": "c" * 64}}
        bindings = runner.workflow_manifest_bindings("worker_protocol_evidence", manifest)
        self.assertTrue(runner.isolated_workflow_passed(payload, "worker_protocol_evidence", identity, bindings))
        payload["protocol_worker_source_sha256"] = "d" * 64
        self.assertFalse(runner.isolated_workflow_passed(payload, "worker_protocol_evidence", identity, bindings))

    def test_receiver_control_fixture_cannot_grant_native_adoption_or_runtime_facts(self):
        payload, identity = self.isolated_result("inventory_query_controls")
        bindings = runner.workflow_manifest_bindings("inventory_query_controls", {"fixture": {"sha256": "c" * 64}})
        self.assertTrue(runner.isolated_workflow_passed(payload, "inventory_query_controls", identity, bindings))
        for field, value in (("fixture_sha256", "d" * 64), ("native_export_adoption_qualified", True),
                             ("signature_authentication_performed", True), ("numerical_state_replayed", True),
                             ("runtime_fact_count", 1), ("tasks_omitted_count", 1),
                             ("additional_attempted_training_epochs", False)):
            with self.subTest(field=field):
                altered = dict(payload, **{field: value})
                self.assertFalse(runner.isolated_workflow_passed(altered, "inventory_query_controls", identity, bindings))

    def test_child_evidence_inventory_preserves_missing_bodies_and_pinned_ledger(self):
        payload, identity = self.isolated_result("released_evidence_children")
        bindings = runner.workflow_manifest_bindings("released_evidence_children", {"ledger": {"sha256": "c" * 64}})
        payload.update(all_selected_children_verified=False, child_dispositions={"missing": 1})
        self.assertTrue(runner.isolated_workflow_passed(payload, "released_evidence_children", identity, bindings))
        for field, value in (("ledger_sha256", "d" * 64), ("producer_signatures_authenticated", True),
                             ("checker_executions_replayed", True), ("runtime_dependency_closure_qualified", True),
                             ("transitive_child_expansion_performed", True)):
            with self.subTest(field=field):
                altered = dict(payload, **{field: value})
                self.assertFalse(runner.isolated_workflow_passed(altered, "released_evidence_children", identity, bindings))

    def test_native_diagnostic_parent_pin_cannot_be_replaced_by_source_truth_claims(self):
        payload, identity = self.isolated_result("native_source384_diagnostics")
        bindings = runner.workflow_manifest_bindings("native_source384_diagnostics",
                                                    {"public_manifest": {"sha256": "c" * 64}})
        payload.update(source_derived_accuracy=None, source_bytes_available=False)
        self.assertTrue(runner.isolated_workflow_passed(payload, "native_source384_diagnostics", identity, bindings))
        for field, value in (("public_manifest_sha256", "d" * 64), ("source_derived_accuracy_available", True),
                             ("source_label_baseline_separate", False), ("git_object_custody_verified", True),
                             ("preconstraint_raw_output_available", True), ("producer_authentication_verified", True)):
            with self.subTest(field=field):
                altered = dict(payload, **{field: value})
                self.assertFalse(runner.isolated_workflow_passed(altered, "native_source384_diagnostics", identity, bindings))

    def test_missing_or_ambiguous_manifest_result_pins_are_refused(self):
        for manifest in ({}, {"lock": None}, {"lock": [{"sha256": "c" * 64}]},
                         {"lock": {}}, {"lock": {"sha256": True}},
                         {"lock": {"sha256": "C" * 64}}, {"lock": {"sha256": "foreign"}}):
            with self.subTest(manifest=manifest):
                with self.assertRaises(ValueError):
                    runner.workflow_manifest_bindings("paired_final_evaluation", manifest)

    def test_exact_source_comparison_requires_all_four_independent_anchor_pins(self):
        payload, identity = self.isolated_result("native_source_comparison")
        manifest = {field: {"sha256": "c" * 64} for field in
                    ("diagnostics_input", "diagnostics", "source_replay", "public_manifest")}
        bindings = runner.workflow_manifest_bindings("native_source_comparison", manifest)
        payload.update(scores={"learned": {"returned_fragment_match": 3}, "zero_head": {"returned_fragment_match": 0}})
        self.assertTrue(runner.isolated_workflow_passed(payload, "native_source_comparison", identity, bindings))
        for field in bindings:
            with self.subTest(field=field):
                altered = dict(payload, **{field: "d" * 64})
                self.assertFalse(runner.isolated_workflow_passed(altered, "native_source_comparison", identity, bindings))
        for field in ("source_semantics_verified", "heldout_independence_verified", "model_head_state_validated",
                      "learned_quality_improvement_verified", "preconstraint_raw_output_available"):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: True}),
                                                               "native_source_comparison", identity, bindings))

    def test_portable_child_capsule_requires_both_archive_and_inner_manifest_pins(self):
        payload, identity = self.isolated_result("portable_evidence_children")
        manifest = {"archive": {"sha256": "c" * 64}, "capsule_manifest_sha256": "c" * 64}
        bindings = runner.workflow_manifest_bindings("portable_evidence_children", manifest)
        payload.update(child_dispositions={"missing": 1}, all_selected_children_verified=False)
        self.assertTrue(runner.isolated_workflow_passed(payload, "portable_evidence_children", identity, bindings))
        for field, value in (("archive_sha256", "d" * 64), ("capsule_manifest_sha256", "d" * 64),
                             ("git_executable_invoked", True), ("original_paths_read", True),
                             ("transitive_child_expansion_performed", True), ("runtime_dependency_closure_qualified", True)):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               "portable_evidence_children", identity, bindings))

    def test_native_receiver_conformance_requires_independent_audit_and_zero_work_counts(self):
        payload, identity = self.isolated_result("native_inventory_query")
        manifest = {"prior_primary_audit": {"sha256": "c" * 64}}
        bindings = runner.workflow_manifest_bindings("native_inventory_query", manifest)
        payload.update(profile_summaries={"partial": {"unknown_budget": 27}})
        self.assertTrue(runner.isolated_workflow_passed(payload, "native_inventory_query", identity, bindings))
        for field, value in (("prior_primary_audit_sha256", "d" * 64), ("live_eligibility_qualified", True),
                             ("native_export_adoption_qualified", True), ("checker_executions_replayed", True),
                             ("runtime_fact_count", 1), ("tasks_omitted_count", 1),
                             ("additional_attempted_training_epochs", False)):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               "native_inventory_query", identity, bindings))

    def test_native_batch_receiver_requires_all_public_anchors_and_no_execution_claims(self):
        payload, identity = self.isolated_result("native_batch_query")
        manifest = {name: {"sha256": "c" * 64} for name in
                    ("prior_qualification", "native_result", "restart_request", "restart_response", "source_snapshot")}
        bindings = runner.workflow_manifest_bindings("native_batch_query", manifest)
        self.assertEqual(set(bindings), {"prior_qualification_sha256", "native_result_sha256", "restart_request_sha256",
                                        "restart_response_sha256", "source_snapshot_sha256"})
        payload.update(runtime_residual_count=8, unsupported_lookup_requirement_count=1)
        self.assertTrue(runner.isolated_workflow_passed(payload, "native_batch_query", identity, bindings))
        for field in bindings:
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: "d" * 64}),
                                                               "native_batch_query", identity, bindings))
        for field, value in (("request_execution_custody_verified", True), ("throughput_improvement_qualified", True),
                             ("batch_resource_execution_qualified", True), ("runtime_fact_count", 1),
                             ("tasks_omitted_count", 1), ("additional_attempted_training_epochs", False)):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               "native_batch_query", identity, bindings))

    def test_source_graph_conformance_binds_prior_input_and_report_without_promoting_graphs(self):
        payload, identity = self.isolated_result("native_program_graph")
        manifest = {"source_comparison_input": {"sha256": "c" * 64}, "source_comparison": {"sha256": "c" * 64}}
        bindings = runner.workflow_manifest_bindings("native_program_graph", manifest)
        self.assertEqual(set(bindings), {"source_comparison_input_sha256", "source_comparison_report_sha256"})
        payload.update(role_graph_metrics={"zero_head": {"missing": 3}})
        self.assertTrue(runner.isolated_workflow_passed(payload, "native_program_graph", identity, bindings))
        for field in (*bindings, "learned_full_program_prediction_verified", "graph_effect_runtime_truth_verified",
                      "complete_ancestral_exposure_verified", "native_compiler_execution_performed",
                      "checker_execution_performed"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               "native_program_graph", identity, bindings))

    def test_producer_source_capsule_requires_three_independent_pins_and_preserves_source_gaps(self):
        payload, identity = self.isolated_result("producer_source_bindings")
        manifest = {"archive": {"sha256": "c" * 64}, "capsule_manifest_sha256": "c" * 64,
                    "custody_capsule_manifest_sha256": "c" * 64}
        bindings = runner.workflow_manifest_bindings("producer_source_bindings", manifest)
        self.assertEqual(set(bindings), {"archive_sha256", "capsule_manifest_sha256", "custody_capsule_manifest_sha256"})
        payload.update(source_dispositions={"missing": 1}, all_selected_sources_verified=False)
        self.assertTrue(runner.isolated_workflow_passed(payload, "producer_source_bindings", identity, bindings))
        for field in (*bindings, "producer_source_imports_performed", "current_working_source_compared",
                      "source_semantics_verified", "producer_execution_authenticated", "source_dependency_closure_qualified"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               "producer_source_bindings", identity, bindings))

    def test_claimed_offline_integrity_requires_exact_true_fields(self):
        for workflow, profile in runner.ISOLATED_WORKFLOWS.items():
            payload, identity = self.isolated_result(workflow)
            for field in profile.get("true_flags", ()):
                for changed in (False, 1, None):
                    with self.subTest(workflow=workflow, field=field, changed=changed):
                        altered = dict(payload, **{field: changed})
                        self.assertFalse(self.scoped_result_passed(altered, workflow, identity))

    def test_lean_projection_requires_all_prior_and_emitted_body_pins_without_quality_promotion(self):
        workflow = "native_lean_projection"
        payload, identity = self.isolated_result(workflow)
        manifest = {name: {"sha256": "c" * 64} for name in (
            "program_graph_input", "program_graph_report", "learned_lake_receipt", "learned_lean",
            "source_label_baseline_lake_receipt", "source_label_baseline_lean")}
        bindings = runner.workflow_manifest_bindings(workflow, manifest)
        self.assertEqual(len(bindings), 6)
        payload.update(compiler_output_body_equal=True, projection_losses={"runtime_semantics": "unavailable"},
                       role_projection_metrics={"zero_head": {"missing_count": 3}})
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "compiler_output_semantics_verified", "operational_semantics_verified",
                      "native_checker_results_replayed", "universal_semantics_verified",
                      "semantic_projection_loss_certified", "producer_execution_authenticated"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               workflow, identity, bindings))

    def test_smt_custody_binds_every_frozen_body_and_refuses_execution_or_fact_promotion(self):
        workflow = "smt_v2_custody"
        payload, identity = self.isolated_result(workflow)
        roles = ("prior_qualification", "native_result", "native_command", "launch_audit", "lifecycle_audit",
                 "control_audit", "wire_before", "wire_after", "wire_comparison", "runtime_before", "runtime_after")
        manifest = {role: {"sha256": "c" * 64} for role in roles}
        bindings = runner.workflow_manifest_bindings(workflow, manifest)
        self.assertEqual(set(bindings), {role + "_sha256" for role in roles})
        payload.update(interruption_control_count=6, raw_stdin_status="unavailable")
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "solver_verdict_authenticated", "runtime_resource_enforcement_verified",
                      "raw_phase_stdin_custody_verified", "raw_caller_request_custody_verified",
                      "unique_phase_execution_attestation_verified", "behavioral_evidence_admission_qualified"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               workflow, identity, bindings))
        for field, value in (("runtime_fact_count", 1), ("tasks_omitted_count", 1),
                             ("additional_attempted_training_epochs", False)):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               workflow, identity, bindings))

    def test_historical_source_recovery_preserves_committed_mismatches_and_unavailable_bodies(self):
        workflow = "producer_source_provenance"
        payload, identity = self.isolated_result(workflow)
        fields = ("capsule_manifest_sha256", "producer_capsule_manifest_sha256", "custody_capsule_manifest_sha256",
                  "producer_source_input_sha256", "producer_source_report_sha256")
        manifest = {"archive": {"sha256": "c" * 64}, **{field: "c" * 64 for field in fields}}
        bindings = runner.workflow_manifest_bindings(workflow, manifest)
        self.assertEqual(set(bindings), {"archive_sha256", *fields})
        payload.update(committed_source_dispositions={"different": 2}, committed_all_selected_sources_verified=False,
                       historical_dispositions={"recovered": 1, "unavailable": 1})
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "historical_source_substitution_performed", "historical_source_execution_authenticated",
                      "historical_original_path_commit_authenticated", "producer_source_imports_performed"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               workflow, identity, bindings))

    def test_feature_collisions_remain_representation_findings_under_all_export_pins(self):
        workflow = "native_feature_coverage"
        payload, identity = self.isolated_result(workflow)
        roles = ("provenance_input", "parent_export", "child_export")
        bindings = runner.workflow_manifest_bindings(workflow, {role: {"sha256": "c" * 64} for role in roles})
        self.assertEqual(set(bindings), {role + "_sha256" for role in roles})
        payload.update(out_of_vocabulary_target_count=5, distinguishing_collision_group_count=1,
                       unknown_sort_occurrence_count=18)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "native_feature_vector_execution_replayed", "model_predictions_evaluated",
                      "optimizer_state_replayed", "training_absence_certified", "heldout_quality_verified",
                      "feature_model_decoder_qualified", "normalized_feature_vectors_rederived"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               workflow, identity, bindings))

        for field in ("additional_attempted_training_epochs", "new_final_assignments"):
            for value in (1, False):
                with self.subTest(field=field, value=value):
                    self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                                   workflow, identity, bindings))

    def test_jvm_custody_requires_all_body_pins_and_withholds_model_check_and_runtime_authority(self):
        workflow = "jvm_probe_custody"
        payload, identity = self.isolated_result(workflow)
        roles = runner.SMT_V2_INPUT_ROLES
        bindings = runner.workflow_manifest_bindings(workflow, {role: {"sha256": "c" * 64} for role in roles})
        self.assertEqual(set(bindings), {role + "_sha256" for role in roles})
        payload.update(successful_probe_count=32, interruption_control_count=4, support_only=True)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "model_checker_execution_qualified", "jvm_binary_identity_authenticated",
                      "launcher_body_custody_verified", "parent_constructor_propagation_qualified",
                      "runtime_resource_enforcement_verified", "throughput_improvement_qualified",
                      "native_deadline_expiry_observed", "native_pressure_backoff_observed"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               workflow, identity, bindings))
        for field, value in (("runtime_fact_count", 1), ("tasks_omitted_count", 1),
                             ("additional_attempted_training_epochs", False)):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               workflow, identity, bindings))

    def test_finite_proof_custody_preserves_missing_dependency_frontiers_under_exact_capsule_pin(self):
        workflow = "finite_proof_toolchain_custody"
        payload, identity = self.isolated_result(workflow)
        bindings = runner.workflow_manifest_bindings(workflow, {"custody_capsule_manifest": {"sha256": "c" * 64}})
        self.assertEqual(bindings, {"custody_capsule_manifest_sha256": "c" * 64})
        payload.update(group_count=3, dependency_frontiers=[{"dependency": "Init", "disposition": "unretained"}])
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "native_tool_bytes_available", "transitive_toolchain_dependencies_attested",
                      "checker_execution_authenticated", "kernel_proof_replayed", "proof_reuse_eligibility_qualified",
                      "source_semantics_verified", "source_execution_replayed", "owner_sources_imported",
                      "domain_cid_recipe_qualified"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}),
                                                               workflow, identity, bindings))


    def test_finite_requirement_matches_preserve_tasks_without_live_or_proof_authority(self):
        workflow = "finite_match_controls"
        payload, identity = self.isolated_result(workflow)
        roles = ("requirements", "prior_manifest", "prior_report", "prior_selected_custody")
        bindings = runner.workflow_manifest_bindings(workflow, {role: {"sha256": "c" * 64} for role in roles})
        self.assertEqual(set(bindings), {role + "_sha256" for role in roles})
        payload.update(disposition_counts={"recorded_supported": 3, "recorded_refuted": 2, "uncovered": 3,
                                           "unsupported": 2, "runtime_deferred": 2})
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "proof_reuse_eligibility_qualified", "runtime_behavior_verified",
                      "producer_signatures_authenticated", "source_semantics_verified", "original_request_authenticated"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))
        for field in ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"):
            for value in (1, False):
                with self.subTest(field=field, value=value):
                    self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))

    def test_feature_augmentation_witnesses_cannot_become_applied_model_or_universal_claims(self):
        workflow = "feature_separation"
        payload, identity = self.isolated_result(workflow)
        roles = ("feature_coverage_input", "feature_coverage_report")
        bindings = runner.workflow_manifest_bindings(workflow, {role: {"sha256": "c" * 64} for role in roles})
        self.assertEqual(set(bindings), {role + "_sha256" for role in roles})
        payload.update(minimal_extra_column_count=2, full_oov_extra_column_count=3, exhaustive_subset_count=8)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "feature_basis_modified", "augmentation_applied_to_native_feature_space",
                      "candidate_tensors_modified", "model_quality_gain_verified", "heldout_quality_verified",
                      "universal_source_label_separation_verified", "open_world_literal_coverage_verified"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))
        for field in ("additional_attempted_training_epochs", "new_final_assignments"):
            for value in (1, False):
                with self.subTest(field=field, value=value):
                    self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))

    def test_released_admission_declarations_keep_missing_envelopes_and_adverse_history_unqualified(self):
        workflow = "admission_declaration_custody"
        payload, identity = self.isolated_result(workflow)
        bindings = runner.workflow_manifest_bindings(workflow, {"custody_capsule_manifest": {"sha256": "c" * 64}})
        self.assertEqual(bindings, {"custody_capsule_manifest_sha256": "c" * 64})
        payload.update(recorded_run_count=9, adverse_recorded_run_count=8, fresh_checker_per_control=False,
                       envelope_frontiers=[{"role": "signed_admission", "disposition": "missing_body"}])
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "signature_envelope_custody_verified", "signed_admission_bindings_complete",
                      "signature_authentication_performed", "owner_authorization_authenticated",
                      "native_task_population_verified", "live_admission_eligibility_verified",
                      "training_absence_certified", "full_daemon_lifecycle_custody_verified", "producer_source_bodies_retained"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))
        for field in ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"):
            for value in (1, False):
                with self.subTest(field=field, value=value):
                    self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))


    def test_resumed_inventory_binds_failed_history_and_composed_reuse_without_current_authority(self):
        workflow = "resumed_inventory_controls"
        payload, identity = self.isolated_result(workflow)
        roles = ("historical_scan_audit", "historical_scan_result", "composed_worker_result")
        bindings = runner.workflow_manifest_bindings(workflow, {role: {"sha256": "c" * 64} for role in roles})
        self.assertEqual(set(bindings), {role + "_sha256" for role in roles})
        payload.update(inventory_member_count=300, page_count=10, historical_resumption_count=4,
                       historical_scan_overall_qualified=False, composed_worker_overall_qualified=True)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "process_origin_attested", "numerical_state_replayed", "live_eligibility_qualified",
                      "native_export_adoption_qualified", "source_execution_replayed"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))
        for field in ("runtime_fact_count", "tasks_omitted_count", "additional_attempted_training_epochs"):
            for value in (False, 1):
                with self.subTest(field=field, value=value):
                    self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))

    def test_resumed_source_cohort_cannot_equate_inference_members_with_training_or_independence(self):
        workflow = "resumed_cohort_audit"
        payload, identity = self.isolated_result(workflow)
        roles = ("qualification_review", "native_result")
        bindings = runner.workflow_manifest_bindings(workflow, {role: {"sha256": "c" * 64} for role in roles})
        self.assertEqual(set(bindings), {role + "_sha256" for role in roles})
        payload.update(inventory_member_count=300, inferred_row_count=205, recorded_inherited_setup_epochs=2)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "training_population_equals_inventory", "heldout_independence_verified",
                      "complete_pretraining_exposure_verified", "model_predictions_evaluated", "source_ast_semantics_verified",
                      "native_target_recipe_replayed"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))
        for field in ("additional_attempted_training_epochs", "new_final_assignments"):
            for value in (False, 1):
                with self.subTest(field=field, value=value):
                    self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))

    def test_ordered_manifest_arrays_reject_missing_slots_and_boolean_aliases(self):
        profile = {"manifest_binding_paths": {"result_sha256": ("attempts", 1, "result", "sha256")}}
        spec = {"attempts": [{"result": {"sha256": "a" * 64}}, {"result": {"sha256": "b" * 64}}]}
        with patch.dict(runner.ISOLATED_WORKFLOWS, ordered_receipt_control=profile):
            self.assertEqual(runner.workflow_manifest_bindings("ordered_receipt_control", spec), {"result_sha256": "b" * 64})
            reversed_spec = {"attempts": list(reversed(spec["attempts"]))}
            self.assertEqual(runner.workflow_manifest_bindings("ordered_receipt_control", reversed_spec), {"result_sha256": "a" * 64})
            for malformed in ({"attempts": spec["attempts"][:1]}, {"attempts": True},
                              {"attempts": {"1": spec["attempts"][1]}}, {"attempts": [{}, {"result": {"sha256": True}}]}):
                with self.subTest(malformed=malformed), self.assertRaises(ValueError):
                    runner.workflow_manifest_bindings("ordered_receipt_control", malformed)
            profile["manifest_binding_paths"]["result_sha256"] = ("attempts", True, "result", "sha256")
            with self.assertRaises(ValueError):
                runner.workflow_manifest_bindings("ordered_receipt_control", spec)

    def test_new_manifest_cli_arguments_parse_and_have_optional_defaults(self):
        original_parse = runner.argparse.ArgumentParser.parse_args
        captured = []

        class ParsingComplete(Exception):
            pass

        def capture(parser, *args, **kwargs):
            captured.append(original_parse(parser, *args, **kwargs))
            raise ParsingComplete

        names = ("resumed_inventory_controls", "resumed_cohort_audit", "dispatch_attempt_custody",
                 "tla_operation_controls", "source_delta_analysis", "current_runtime_cleanup_custody",
                 "apalache_admission_controls", "successor_cohort_audit", "successor_planning_custody",
                 "foreign_outcome_controls", "full_successor_cohort_audit", "successor_receiving_custody",
                 "artifact_payload_controls", "trace_binding_audit", "registry_operation_deadline_custody",
                 "signed_worker_acceptance_controls", "publication_dependency_audit",
                 "native_operation_inheritance_custody")
        manifest = self.root / "selected-input.json"
        for selected in (False, True):
            argv = [str(Path(runner.__file__))]
            if selected:
                for name in names:
                    argv.extend(["--" + name.replace("_", "-") + "-manifest", str(manifest)])
            with self.subTest(selected=selected), patch.object(sys, "argv", argv), patch.object(
                runner.argparse.ArgumentParser, "parse_args", autospec=True, side_effect=capture
            ), self.assertRaises(ParsingComplete):
                runner.main()
            for name in names:
                self.assertEqual(getattr(captured[-1], name + "_manifest"), manifest if selected else None)

    def test_failed_tla_operations_bind_each_attempt_without_promoting_partial_results(self):
        workflow = "tla_operation_controls"
        payload, identity = self.isolated_result(workflow)
        attempts = [{role: {"sha256": str(index + 1) * 64} for role in ("result", "command_result", "source_freeze")}
                    for index in range(3)]
        bindings = runner.workflow_manifest_bindings(workflow, {"attempts": attempts})
        payload.update(bindings)
        self.assertEqual(len(bindings), 9)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        reversed_bindings = runner.workflow_manifest_bindings(workflow, {"attempts": list(reversed(attempts))})
        self.assertFalse(runner.isolated_workflow_passed(payload, workflow, identity, reversed_bindings))
        for field in ("aggregate_operation_success_qualified", "original_request_custody_qualified", "model_check_authority_qualified"):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: True}), workflow, identity, bindings))
        for field in runner.ISOLATED_WORKFLOWS[workflow]["zero_fields"]:
            self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: False}), workflow, identity, bindings))

    def test_apalache_failures_bind_before_any_registry_or_witness_claim(self):
        workflow = "apalache_admission_controls"
        payload, identity = self.isolated_result(workflow)
        manifest = {"qualification": {"sha256": "a" * 64}, "attempts": [
            {role: {"sha256": str(index + 1) * 64} for role in ("result", "command_result")}
            for index in range(4)]}
        bindings = runner.workflow_manifest_bindings(workflow, manifest)
        self.assertEqual(len(bindings), 9)
        payload.update(bindings)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        changed = dict(manifest, attempts=list(reversed(manifest["attempts"])))
        self.assertFalse(runner.isolated_workflow_passed(
            payload, workflow, identity, runner.workflow_manifest_bindings(workflow, changed)))
        for field in ("registry_native_success_qualified", "counterexample_replay_qualified",
                      "whole_install_cancellation_qualified", "hard_aggregate_containment_qualified"):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: True}), workflow, identity, bindings))
        for field in runner.ISOLATED_WORKFLOWS[workflow]["zero_fields"]:
            self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: False}), workflow, identity, bindings))
        with self.assertRaises(ValueError):
            runner.workflow_manifest_bindings(workflow, dict(manifest, attempts=manifest["attempts"][:3]))

    def test_successor_prefix_exposure_cannot_promote_ancestry_or_complete_scan(self):
        workflow = "successor_cohort_audit"
        payload, identity = self.isolated_result(workflow)
        roles = ("review", "native_result", "independent_audit", "failed_result")
        manifest = {role: {"sha256": "c" * 64} for role in roles}
        bindings = runner.workflow_manifest_bindings(workflow, manifest)
        self.assertEqual(len(bindings), 4)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "root_training_population_verified", "replay_population_verified", "complete_scan_verified",
                      "snapshot_schema_verified", "optimizer_state_replayed", "inference_correctness_verified"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))
        for field in runner.ISOLATED_WORKFLOWS[workflow]["zero_fields"]:
            self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: False}), workflow, identity, bindings))
        with self.assertRaises(ValueError):
            runner.workflow_manifest_bindings(workflow, {role: manifest[role] for role in roles[:-1]})

    def test_successor_plan_requires_complete_bindings_without_solver_or_cold_restart_claims(self):
        workflow = "successor_planning_custody"
        payload, identity = self.isolated_result(workflow)
        pins = [{"sha256": str(index % 8 + 1) * 64} for index in range(10)]
        bindings = runner.workflow_manifest_bindings(workflow, {"selected_files": pins})
        payload.update(bindings)
        self.assertEqual(len(bindings), 10)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "whole_planner_solver_free_qualified", "cold_process_restart_qualified", "critic_body_closure_qualified",
                      "semantic_meanings_independently_replayed", "two_prefixes_are_64_distinct_members_qualified"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))
        self.assertFalse(runner.isolated_workflow_passed(
            dict(payload, runtime_fact_count=False), workflow, identity, bindings))
        with self.assertRaises(ValueError):
            runner.workflow_manifest_bindings(workflow, {"selected_files": pins[:9]})

    def test_foreign_conversion_requires_ordered_attempts_and_no_generic_authority(self):
        workflow = "foreign_outcome_controls"
        payload, identity = self.isolated_result(workflow)
        manifest = {"qualification": {"sha256": "a" * 64}, "source_evolution": {"sha256": "b" * 64},
                    "attempts": [{role: {"sha256": str(index + 1) * 64}
                                  for role in ("result", "command_result")} for index in range(2)]}
        bindings = runner.workflow_manifest_bindings(workflow, manifest)
        payload.update(bindings)
        self.assertEqual(len(bindings), 6)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        self.assertFalse(runner.isolated_workflow_passed(payload, workflow, identity,
            runner.workflow_manifest_bindings(workflow, dict(manifest, attempts=list(reversed(manifest["attempts"]))))))
        for field in ("proof_authority_qualified", "registry_native_success_qualified", "output_digest_algorithm_rederived"):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: True}), workflow, identity, bindings))
        self.assertFalse(runner.isolated_workflow_passed(dict(payload, runtime_fact_count=False), workflow, identity, bindings))
        with self.assertRaises(ValueError):
            runner.workflow_manifest_bindings(workflow, dict(manifest, attempts=manifest["attempts"][:1]))

    def test_full_default_cohort_cannot_promote_reference_coverage_or_numerical_truth(self):
        workflow = "full_successor_cohort_audit"
        payload, identity = self.isolated_result(workflow)
        pins = [{"role": role, "sha256": hashlib.sha256(str(index).encode()).hexdigest()}
                for index, role in enumerate(runner.ISOLATED_WORKFLOWS[workflow]["report_binding_roles"])]
        bindings = runner.workflow_manifest_bindings(workflow, {"selected_files": pins})
        payload.update(bindings)
        payload["selected_files"] = pins
        self.assertEqual(len(bindings), 42)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in ("full_reference_scan_verified", "all_members_numerically_inferred", "inference_correctness_verified",
                      "root_training_population_verified", "heldout_independence_verified", "semantic_state_identity_rederived",
                      "production_default_activated"):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: True}), workflow, identity, bindings))
        for field in runner.ISOLATED_WORKFLOWS[workflow]["zero_fields"]:
            self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: False}), workflow, identity, bindings))
        altered = [*pins[:-1], {"sha256": "e" * 64}]
        self.assertFalse(runner.isolated_workflow_passed(payload, workflow, identity,
            runner.workflow_manifest_bindings(workflow, {"selected_files": altered})))
        with self.assertRaises(ValueError):
            runner.workflow_manifest_bindings(workflow, {"selected_files": pins[:-1]})

    def test_nested_report_bindings_require_all_original_selected_digests(self):
        workflow = "full_successor_cohort_audit"
        payload, identity = self.isolated_result(workflow)
        pins = [{"role": role, "sha256": hashlib.sha256(str(index).encode()).hexdigest()}
                for index, role in enumerate(runner.ISOLATED_WORKFLOWS[workflow]["report_binding_roles"])]
        bindings = runner.workflow_manifest_bindings(workflow, {"selected_files": pins})
        payload["selected_files"] = pins
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for rows in (pins[:-1], {"0": pins[0]}, [None, *pins[1:]], [{"sha256": False}, *pins[1:]],
                     [{**pins[0], "sha256": "f" * 64}, *pins[1:]], list(reversed(pins)), [*pins, pins[0]],
                     [{**pins[0], "role": "unselected"}, *pins[1:]]):
            forged = dict(payload, selected_files=rows, **bindings)
            self.assertFalse(runner.isolated_workflow_passed(forged, workflow, identity, bindings))
        self.assertFalse(runner.isolated_workflow_passed(dict(payload, **bindings, selected_files=[]),
                                                       workflow, identity, bindings))

    def test_report_binding_paths_reject_boolean_negative_and_wrong_container_selectors(self):
        workflow = "full_successor_cohort_audit"
        profile = runner.ISOLATED_WORKFLOWS[workflow]
        field = profile["binding_fields"][0]
        payload = {"selected_files": [{"sha256": "a" * 64}]}
        for path in (("selected_files", False, "sha256"), ("selected_files", -1, "sha256"),
                     ("selected_files", 0.0, "sha256"), ("selected_files", "0", "sha256"),
                     ("selected_files", 1, "sha256"), ("selected_files", 0, "missing")):
            with self.subTest(path=path), patch.dict(profile, report_binding_paths={field: path}):
                self.assertIsNone(runner.workflow_report_binding(workflow, payload, field))
        self.assertEqual(runner.workflow_report_binding(workflow, payload, field), "a" * 64)
        self.assertEqual(runner.workflow_report_binding("successor_receiving_custody", {"full_scan_native_sha256": "b" * 64},
                                                       "full_scan_native_sha256"), "b" * 64)

    def test_unsigned_receiving_cannot_admit_failed_signed_worker_or_deep_archive(self):
        workflow = "successor_receiving_custody"
        payload, identity = self.isolated_result(workflow)
        pins = [{"sha256": hashlib.sha256(str(index).encode()).hexdigest()} for index in range(10)]
        bindings = runner.workflow_manifest_bindings(workflow, {"selected_files": pins})
        payload.update(bindings)
        self.assertEqual(len(bindings), 10)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in ("signed_successor_worker_qualified", "signed_admission_qualified", "worker_dispatch_qualified",
                      "complete_archive_body_closure", "model_bodies_verified", "database_bodies_verified",
                      "signature_authentication_performed", "live_cleanup_reobserved"):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: True}), workflow, identity, bindings))
        self.assertFalse(runner.isolated_workflow_passed(dict(payload, tasks_omitted_count=False), workflow, identity, bindings))
        reordered = [*pins[:6], pins[8], pins[9], pins[6], pins[7]]
        self.assertFalse(runner.isolated_workflow_passed(payload, workflow, identity,
            runner.workflow_manifest_bindings(workflow, {"selected_files": reordered})))
        with self.assertRaises(ValueError):
            runner.workflow_manifest_bindings(workflow, {"selected_files": pins[:9]})

    def assert_retained_metadata_profile(self, workflow, role_count, authority_fields):
        payload, identity = self.isolated_result(workflow)
        profile = runner.ISOLATED_WORKFLOWS[workflow]
        roles = profile.get("report_binding_roles")
        if roles is None:
            roles = tuple(field.removesuffix("_sha256") for field in profile["binding_fields"])
        pins = [{"role": role, "sha256": hashlib.sha256(str(index).encode()).hexdigest()}
                for index, role in enumerate(roles)]
        self.assertEqual(len(pins), role_count)
        bindings = runner.workflow_manifest_bindings(workflow, {"selected_files": pins})
        self.assertEqual(len(bindings), role_count)
        payload["selected_files"] = pins
        if not profile.get("report_binding_paths"):
            payload.update(bindings)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in authority_fields:
            with self.subTest(authority_field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: True}), workflow, identity, bindings))
        for field in profile["zero_fields"]:
            with self.subTest(zero_field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: False}), workflow, identity, bindings))
        for field in bindings:
            changed = dict(bindings, **{field: "f" * 64})
            self.assertFalse(runner.isolated_workflow_passed(payload, workflow, identity, changed))
        reordered = runner.workflow_manifest_bindings(workflow, {"selected_files": list(reversed(pins))})
        self.assertFalse(runner.isolated_workflow_passed(payload, workflow, identity, reordered))
        with self.assertRaises(ValueError):
            runner.workflow_manifest_bindings(workflow, {"selected_files": pins[:-1]})

    def test_serialized_artifact_custody_cannot_promote_translation_or_native_v2(self):
        self.assert_retained_metadata_profile("artifact_payload_controls", 16, (
            "translation_correctness_qualified", "source_map_semantic_truth_qualified",
            "native_v2_execution_qualified", "default_registry_operation_budget_qualified"))

    def test_trace_binding_custody_cannot_promote_semantic_replay_or_source_truth(self):
        self.assert_retained_metadata_profile("trace_binding_audit", 17, (
            "semantic_counterexample_replay_qualified", "source_map_semantics_verified",
            "transition_semantics_verified", "invariant_semantics_verified"))

    def test_registry_deadline_custody_cannot_promote_current_behavior_or_native_cancellation(self):
        self.assert_retained_metadata_profile("registry_operation_deadline_custody", 18, (
            "automatic_current_registry_behavior_qualified", "native_cancellation_execution_qualified",
            "hard_callback_preemption_qualified", "hard_aggregate_containment_qualified"))

    def test_signed_worker_metadata_cannot_promote_crypto_or_current_worker_authority(self):
        self.assert_retained_metadata_profile("signed_worker_acceptance_controls", 20, (
            "signature_authentication_performed", "process_origin_attested", "source_semantics_verified"))

    def test_publication_dependency_frontier_cannot_promote_behavior_or_native_invalidation(self):
        self.assert_retained_metadata_profile("publication_dependency_audit", 13, (
            "behavioral_equivalence_verified", "behavioral_difference_verified",
            "native_invalidation_completeness_verified", "unresolved_dependency_frontiers_closed"))

    def test_python_transport_controls_cannot_qualify_native_solver_interruption(self):
        self.assert_retained_metadata_profile("native_operation_inheritance_custody", 27, (
            "native_kernel_cancellation_qualified", "current_admitted_runner_behavior_qualified",
            "hard_callback_preemption_qualified", "hard_aggregate_containment_qualified"))

    def test_source_delta_bindings_cannot_transfer_exposure_or_numerical_reuse(self):
        workflow = "source_delta_analysis"
        payload, identity = self.isolated_result(workflow)
        roles = ("review", "source_result", "source_audit", "ignored_result", "failed_ignore_result",
                 "historical_cohort_report", "checkpoint_result")
        bindings = runner.workflow_manifest_bindings(workflow, {role: {"sha256": "c" * 64} for role in roles})
        self.assertEqual(len(bindings), 7)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "physical_absence_verified", "semantic_rename_verified", "numerical_reuse_authorized",
                      "current_training_roles_transferred", "historical_exposure_roles_transferred", "current_model_eligibility_qualified"):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: "d" * 64 if field in bindings else True}),
                                                                workflow, identity, bindings))
        self.assertFalse(runner.isolated_workflow_passed(dict(payload, new_final_assignments=False), workflow, identity, bindings))

    def test_runtime_cleanup_metadata_cannot_claim_current_execution_or_source_custody(self):
        workflow = "current_runtime_cleanup_custody"
        payload, identity = self.isolated_result(workflow)
        pins = [{"sha256": "c" * 64} for _ in range(35)]
        bindings = runner.workflow_manifest_bindings(workflow, {"selected_files": pins})
        self.assertEqual(len(bindings), 8)
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "current_resource_cleanup_verified", "current_live_eligibility_verified",
                      "selected_source_bodies_replayed", "checkpoint_state_reconstructed", "historical_process_origin_authenticated"):
            with self.subTest(field=field):
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: "d" * 64 if field in bindings else True}),
                                                                workflow, identity, bindings))
        for field in runner.ISOLATED_WORKFLOWS[workflow]["zero_fields"]:
            self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: False}), workflow, identity, bindings))
        with self.assertRaises(ValueError):
            runner.workflow_manifest_bindings(workflow, {"selected_files": pins[:34]})

    def test_dispatch_attempt_ledger_cannot_promote_driver_success_or_cost_sums_to_native_authority(self):
        workflow = "dispatch_attempt_custody"
        payload, identity = self.isolated_result(workflow)
        roles = ("machine_review", "attempt_ledger", "postledger_supplement")
        bindings = runner.workflow_manifest_bindings(workflow, {role: {"sha256": "c" * 64} for role in roles})
        self.assertEqual(set(bindings), {role + "_sha256" for role in roles})
        payload.update(host_attempt_count=11, docker_attempt_count=9, stream_attempt_count=2,
                       matched_generation12_recorded_outcomes={"positive07": "completed", "child-proof02": "UNKNOWN",
                                                             "child-epoch02": "UNKNOWN"})
        self.assertTrue(runner.isolated_workflow_passed(payload, workflow, identity, bindings))
        for field in (*bindings, "native_publication_reconstructed", "external_effect_absence_qualified",
                      "whole_same_generation_host_suite_qualified", "unique_cpu_time_measured", "total_elapsed_wall_time_measured"):
            with self.subTest(field=field):
                value = "d" * 64 if field in bindings else True
                self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))
        for field in ("new_native_jobs_launched", "additional_attempted_training_epochs"):
            for value in (False, 1):
                with self.subTest(field=field, value=value):
                    self.assertFalse(runner.isolated_workflow_passed(dict(payload, **{field: value}), workflow, identity, bindings))


if __name__ == "__main__":
    unittest.main()
