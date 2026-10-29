"""Observed failures survive retries; resource waits cannot request app edits."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as llm


class ExecutionFailureTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        replacement = patch.object(worker, "ROOT", self.root)
        replacement.start(); self.addCleanup(replacement.stop)
        self.profile = {"runtimeRoot": "data/agent_supervisor/swissknife_visual_functional",
                        "appContractPath": "contracts.json", "taskSpecPath": "tasks.json", "humanPlanPath": "plan.md",
                        "llm": {"repairReadPolicy": "inline_only", "provider": "grok_cli", "model": "grok-4.7",
                                "temperature": 0, "allowLocalFallback": False, "allowCrossProviderFallback": False}}
        self.task = {"task_id": "SVF-099", "app_id": "demo", "kind": "verify", "title": "Actual operation",
                     "acceptance": "Actual result", "edit_paths": ["swissknife/app.js"]}
        self.directory = self.root / self.profile["runtimeRoot"] / "tasks/SVF-099"
        self.attempt = self.directory / "verification/attempt-abcdefgh"
        self.attempt.mkdir(parents=True)
        self.write("swissknife/app.js", "// actual source\n")
        self.write("swissknife/scripts/run-visual-functional-workflow.mjs", "// runner\n")
        self.write("swissknife/docs/visual-functional-driver-contract.md", "Readonly grammar\n")
        self.write("profile.json", json.dumps(self.profile))
        self.write("tasks.json", json.dumps({"tasks": [self.task]}))
        self.write("contracts.json", json.dumps({"apps": [{"app_id": "demo"}]}))

    def write(self, name, value):
        p = self.root / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(value)
        return p

    def diagnostic(self):
        response = self.attempt / "backend-failure.json"
        response.write_text(json.dumps({"outcome": "executed", "actual": {"count": 0}}))
        value = {"schema": "swissknife.visual-functional-workflow-failure.v1", "app_id": "demo",
                 "error": {"code": "POSTCONDITION_FAILED", "message": "wrong result",
                           "details": {"actual": 0, "expected": 1}}, "phase": "primary_result", "step": 3,
                 "source_sha256": {"swissknife/app.js": worker.sha(self.root / "swissknife/app.js")},
                 "artifacts": [worker.artifact(response)], "work_complete": False, "completion_authority": False}
        (self.attempt / "failure.json").write_text(json.dumps(value))
        return response

    def test_exact_actual_values_and_hash_bound_owner_diagnostic_reach_model(self):
        self.diagnostic()
        archived = worker.remember_execution_failure(self.profile, self.task, ValueError("wrong result"), stage="workflow", attempt=self.attempt)
        def invoke(*args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            failure = context["latest_execution_failure"]["failure"]
            self.assertEqual(failure["diagnostic"]["error"]["details"], {"actual": 0, "expected": 1})
            self.assertEqual(failure["diagnostic"]["retained_observations"][0]["observation"]["actual"], {"count": 0})
            self.assertFalse(failure["completion_authority"])
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            worker.model("profile.json", self.task, "repair", ["swissknife/app.js"], [], self.directory / "repair.json")
        self.assertEqual(archived.read_bytes(), worker.execution_failure_path(self.profile, self.task).read_bytes())

    def test_stale_source_tampered_payload_and_wrong_task_are_not_repair_context(self):
        response = self.diagnostic()
        worker.remember_execution_failure(self.profile, self.task, ValueError("wrong"), stage="workflow", attempt=self.attempt)
        self.assertIsNotNone(worker.load_execution_failure(self.profile, self.task))
        response.write_text('{"actual":"tampered"}')
        self.assertIsNone(worker.load_execution_failure(self.profile, self.task))
        self.diagnostic()
        self.write("swissknife/app.js", "changed source")
        self.assertIsNone(worker.load_execution_failure(self.profile, self.task))
        self.assertIsNone(worker.load_execution_failure(self.profile, dict(self.task, task_id="SVF-OTHER")))

    def test_changed_shared_source_or_scenario_invalidates_browser_diagnostics(self):
        self.diagnostic()
        shared = self.write("swissknife/shared.css", "actual layout")
        scenario = self.write("swissknife/test/e2e/functional-workflows/demo.json", '{"actual":"scenario"}')
        report = self.attempt / "failure.json"
        data = json.loads(report.read_text())
        data.update(source_sha256={"swissknife/shared.css": worker.sha(shared)}, scenario_sha256=worker.sha(scenario))
        report.write_text(json.dumps(data))
        worker.remember_execution_failure(self.profile, self.task, ValueError("wrong"), stage="workflow", attempt=self.attempt)
        self.assertIsNotNone(worker.load_execution_failure(self.profile, self.task))
        shared.write_text("changed layout")
        self.assertIsNone(worker.load_execution_failure(self.profile, self.task))
        shared.write_text("actual layout")
        scenario.write_text("changed scenario")
        self.assertIsNone(worker.load_execution_failure(self.profile, self.task))

    def test_readonly_dependency_migration_preserves_failure_but_acceptance_change_does_not(self):
        worker.remember_execution_failure(self.profile, self.task, ValueError("wrong"), stage="workflow")
        self.assertIsNotNone(worker.load_execution_failure(self.profile, dict(self.task, execution_inputs=["new-readonly.js"])))
        self.assertIsNone(worker.load_execution_failure(self.profile, dict(self.task, acceptance="Different result")))

    def test_declined_model_does_not_erase_the_actual_execution_failure(self):
        original = worker.remember_execution_failure(self.profile, self.task, ValueError("actual assertion"), stage="workflow")
        worker.remember_repair_failure(self.profile, self.task, source_hashes=worker.repair_target_hashes(self.task), declined=True)
        self.assertEqual(original.read_bytes(), worker.execution_failure_path(self.profile, self.task).read_bytes())

    def test_failed_attempts_are_immutable_and_never_become_success_receipts(self):
        first = worker.remember_execution_failure(self.profile, self.task, ValueError("first"), stage="workflow")
        second = worker.remember_execution_failure(self.profile, self.task, ValueError("second"), stage="verification")
        self.assertNotEqual(first, second)
        self.assertEqual(json.loads(first.read_text())["error"]["message"], "first")
        self.assertEqual(second.read_bytes(), worker.execution_failure_path(self.profile, self.task).read_bytes())
        self.assertFalse((self.directory / "receipt.json").exists())

    def test_only_structured_browser_contention_becomes_resource_wait(self):
        cases = [('{"error":"BROWSER_CONTENTION"}', worker.BrowserContention),
                 ('a log mentions BROWSER_CONTENTION', worker.ValidationCommandError),
                 ('{"error":"POSTCONDITION_FAILED"}', worker.ValidationCommandError)]
        for stderr, expected in cases:
            with self.subTest(stderr=stderr), patch.object(worker, "run", side_effect=worker.ValidationCommandError([], 1, "", stderr)):
                with self.assertRaises(expected):
                    worker.workflow(self.profile, self.task, self.directory / "verification")

    def test_resource_wait_skips_model_repairs_and_main_exits75_with_task_identity(self):
        with patch.object(worker, "ensure_lease"), patch.object(worker, "check_owned_sources"), \
                patch.object(worker, "workflow", side_effect=worker.BrowserContention("owned elsewhere")), \
                patch.object(worker, "model") as model:
            with self.assertRaises(worker.BrowserContention):
                worker.execute("profile.json", self.profile, {"tasks": [self.task]}, self.task)
            model.assert_not_called()
        with patch.object(worker, "load", return_value=(self.profile, {"tasks": [self.task]})), \
                patch.object(worker, "execute", side_effect=worker.BrowserContention("owned elsewhere")), \
                patch.object(worker, "model") as model:
            self.assertEqual(worker.main(["--profile", "profile.json", "--task-id", "SVF-099"]), 75)
            model.assert_not_called()

    def test_recovery_feedback_is_full_readonly_context_never_an_edit_target(self):
        source = self.directory / "recovery/feedback-0.source"
        source.parent.mkdir(parents=True)
        source.write_text('{"actual":0,"expected":1}')
        name = str(source.relative_to(self.root))
        context = {"feedback_inputs": {"original-failure.json": {**worker.artifact(source), "included": True}}}
        def invoke(*args, **kwargs):
            inputs = kwargs["input_paths"]
            self.assertIn(name, inputs)
            supplied = json.loads((self.root / inputs[0]).read_text())
            self.assertNotIn(name, [x["path"] for x in supplied["complete_edit_targets"]])
            self.assertEqual(kwargs["predicted_files"], self.task["edit_paths"])
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            worker.model("profile.json", self.task, "repair", ["swissknife/app.js", name], [],
                         self.directory / "repair.json", recovery_context=context)

    def test_readonly_admission_identities_do_not_displace_complete_edit_source(self):
        bindings = {"swissknife/app.js": worker.sha(self.root / "swissknife/app.js"),
                    **{f"readonly/controller-{index}.py": "a" * 64 for index in range(100)}}
        def invoke(*args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())["bounded_recovery"]
            self.assertEqual(context["source_before"], {"swissknife/app.js": bindings["swissknife/app.js"]})
            self.assertEqual(context["original_source_identity"]["source_count"], 101)
            self.assertEqual(context["original_source_identity"]["sha256"], worker.stable(bindings))
            self.assertIn("swissknife/app.js", kwargs["input_paths"])
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            worker.model("profile.json", self.task, "repair", ["swissknife/app.js"], [],
                         self.directory / "repair.json", recovery_context={"source_before": bindings})

    def test_recovery_rejects_stale_failure_evidence_before_provider(self):
        worker.remember_execution_failure(self.profile, self.task, ValueError("wrong"), stage="workflow")
        recorded = worker.artifact(worker.execution_failure_path(self.profile, self.task))
        context = {"feedback_inputs": {recorded["path"]: {**recorded, "included": True}}}
        self.write("swissknife/app.js", "changed source after the failed run")
        with patch.object(llm, "invoke_task_model") as invoke:
            with self.assertRaisesRegex(ValueError, "stale"):
                worker.model("profile.json", self.task, "repair", ["swissknife/app.js"], [],
                             self.directory / "repair.json", recovery_context=context)
            invoke.assert_not_called()

    def test_outer_retry_preserves_the_inner_workflow_diagnostic_when_model_declines(self):
        self.diagnostic()
        error = RuntimeError("the actual browser assertion")
        original = worker.remember_execution_failure(self.profile, self.task, error, stage="workflow", attempt=self.attempt)
        error.execution_failure_recorded = True
        with patch.object(worker, "ensure_lease"), patch.object(worker, "check_owned_sources"), \
                patch.object(worker, "workflow", side_effect=error), \
                patch.object(worker, "model", side_effect=ValueError("model declined")):
            with self.assertRaisesRegex(ValueError, "declined"):
                worker.execute("profile.json", self.profile, {"tasks": [self.task]}, self.task)
        self.assertEqual(original.read_bytes(), worker.execution_failure_path(self.profile, self.task).read_bytes())
        self.assertEqual(worker.load_execution_failure(self.profile, self.task)["failure"]["diagnostic"]["error"]["details"]["actual"], 0)

    def test_final_visual_findings_survive_future_recovery_and_remain_hash_bound(self):
        review = self.attempt / "visual-review.json"
        review.write_text(json.dumps({"schema": llm.RECEIPT_SCHEMA, "task_id": self.task["task_id"],
            "mode": "review", "success": True, "response": {"decision": "needs_changes",
            "findings": [{"description": "Essential controls clip on mobile"}]}}))
        worker.remember_execution_failure(self.profile, self.task, ValueError("review requires changes"),
                                           stage="verification", review_output=review)
        loaded = worker.load_execution_failure(self.profile, self.task)
        self.assertEqual(loaded["failure"]["visual_review"]["response"]["findings"][0]["description"],
                         "Essential controls clip on mobile")
        review.write_text("changed review")
        self.assertIsNone(worker.load_execution_failure(self.profile, self.task))

    def test_source_change_during_model_call_invalidates_retained_failure_context(self):
        worker.remember_execution_failure(self.profile, self.task, ValueError("wrong"), stage="workflow")
        def invoke(*args, **kwargs):
            worker.execution_failure_path(self.profile, self.task).write_text("changed feedback")
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            with self.assertRaisesRegex(ValueError, "changed"):
                worker.model("profile.json", self.task, "repair", ["swissknife/app.js"], [], self.directory / "repair.json")


if __name__ == "__main__":
    unittest.main()
