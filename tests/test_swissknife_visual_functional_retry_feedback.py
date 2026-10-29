"""Rejected code is a bounded retry hint, never an applied or accepted result."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import swissknife_visual_functional_llm as llm
import swissknife_visual_functional_worker as worker


class RetryFeedbackTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        mock_root = patch.object(worker, "ROOT", self.root)
        mock_root.start(); self.addCleanup(mock_root.stop)
        self.source = self.root / "app.js"
        self.source.write_text("export const answer = 50;\n")
        self.profile = {"runtimeRoot": "data/agent_supervisor/swissknife_visual_functional",
                        "humanPlanPath": "plan.md", "taskSpecPath": "tasks.json", "appContractPath": "contracts.json",
                        "llm": {"provider": "grok_cli", "model": "grok-4.7"}}
        self.task = {"task_id": "SVF-099", "title": "Repair an actual result", "kind": "implementation",
                     "acceptance": "Actual returned result is correct", "edit_paths": ["app.js"]}
        self.directory = worker.runtime_root(self.profile) / "tasks/SVF-099"
        self.directory.mkdir(parents=True)
        self.output = self.directory / "proposal-1.json"
        self.candidate = {"schema": llm.RESPONSE_SCHEMA, "task_id": "SVF-099", "mode": "repair",
                          "decision": "needs_changes", "summary": "An exact anchor requires correction.",
                          "inspected_screenshots": [], "findings": [],
                          "edits": [{"path": "app.js", "before_sha256": worker.sha(self.source),
                                     "old": "not present", "new": "export const answer = 51;"}]}
        self.receipt = {"schema": llm.RECEIPT_SCHEMA, "task_id": "SVF-099", "mode": "repair", "success": False,
                        "input_files": [{"path": "app.js", "sha256": worker.sha(self.source)}],
                        "failure_diagnostics": {"codes": ["provider_or_response_contract_failure"]},
                        "edit_validation_error": {"code": "edit_anchor_match_count", "path": "app.js", "hunk_index": 1, "match_count": 0},
                        "rejected_response": self.candidate,
                        "rejected_response_sha256": llm._sha(llm._json(self.candidate).encode())}

    def remember(self):
        self.output.write_text(json.dumps(self.receipt))
        worker.remember_repair_failure(self.profile, self.task, source_hashes=worker.repair_target_hashes(self.task), output=self.output)
        return worker.load_repair_feedback(self.profile, self.task)

    def test_exact_rejected_candidate_survives_retry_without_source_change_or_success(self):
        original = self.source.read_bytes()
        hint = self.remember()
        self.assertEqual(hint["error"]["match_count"], 0)
        retained = self.root / hint["rejected_response"]["path"]
        self.assertEqual(json.loads(retained.read_text()), self.candidate)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertIs(hint["completion_authority"], False)
        self.assertNotIn("success", hint)

    def test_next_model_call_receives_bound_diagnostic_and_candidate_read_path(self):
        hint = self.remember()
        (self.root / "profile.json").write_text(json.dumps(self.profile))
        (self.root / "contracts.json").write_text('{"apps": []}')
        (self.root / "tasks.json").write_text('{"tasks": []}')
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            self.assertEqual(context["last_repair_error"], hint)
            self.assertIn("exact preceding failure", context["retry_instruction"])
            self.assertIn(hint["rejected_response"]["path"], json.dumps(context))
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            worker.model("profile.json", self.task, "repair", [], [], self.directory / "proposal-2.json")
        self.assertFalse(worker.repair_feedback_path(self.profile, self.task).exists())

    def test_changed_task_source_or_tampered_candidate_is_ignored(self):
        self.remember()
        changed_task = dict(self.task, acceptance="A different contract")
        self.assertIsNone(worker.load_repair_feedback(self.profile, changed_task))
        self.source.write_text("// concurrent source\n")
        self.assertIsNone(worker.load_repair_feedback(self.profile, self.task))
        self.source.write_text("export const answer = 50;\n")
        hint = worker.load_repair_feedback(self.profile, self.task)
        (self.root / hint["rejected_response"]["path"]).write_text("{}")
        self.assertIsNone(worker.load_repair_feedback(self.profile, self.task))

    def test_app_verification_repair_always_receives_readonly_scenario_grammar(self):
        self.task.update(kind="verify", app_id="demo")
        contract = "swissknife/docs/visual-functional-driver-contract.md"
        path = self.root / contract
        path.parent.mkdir(parents=True)
        path.write_text("Exact input scenario grammar: fixture_scope, phases, backend_bindings.\n")
        (self.root / "profile.json").write_text(json.dumps(self.profile))
        (self.root / "contracts.json").write_text(json.dumps({"apps": [{"app_id": "demo"}]}))
        (self.root / "tasks.json").write_text('{"tasks": []}')
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            self.assertEqual(context["scenario_input_contract"]["path"], contract)
            self.assertIn(contract, kwargs["input_paths"])
            self.assertEqual(kwargs["predicted_files"], ["app.js"])
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            worker.model("profile.json", self.task, "repair", [], [], self.directory / "verification-repair.json")

    def test_unallowlisted_proposal_and_provider_bodies_are_not_retry_inputs(self):
        self.receipt["rejected_response"] = copy.deepcopy(self.candidate)
        self.receipt["rejected_response"]["edits"][0]["path"] = "foreign.js"
        self.receipt["reason"] = "UNSAFE_PROVIDER_BODY"
        self.receipt["native_observation"] = {"stderr": "UNSAFE_PROVIDER_BODY", "thought": "UNSAFE_PROVIDER_BODY"}
        hint = self.remember()
        self.assertNotIn("rejected_response", hint)
        self.assertNotIn("UNSAFE_PROVIDER_BODY", json.dumps(hint))
        for value in [{"match_count": {"raw": "UNSAFE_PROVIDER_BODY"}}, {"hunk_index": True}, {"path": "foreign.js"}]:
            error = dict(self.receipt["edit_validation_error"], **value)
            self.assertIsNone(worker.repair_error_hint(error, worker.repair_target_hashes(self.task)))

    def test_malformed_feedback_cannot_smuggle_untyped_bodies(self):
        self.remember()
        path = worker.repair_feedback_path(self.profile, self.task)
        data = json.loads(path.read_text()); data["raw_provider_body"] = "untrusted"
        path.write_text(json.dumps(data))
        self.assertIsNone(worker.load_repair_feedback(self.profile, self.task))
        data.pop("raw_provider_body"); data["error"]["match_count"] = "untrusted"
        path.write_text(json.dumps(data))
        self.assertIsNone(worker.load_repair_feedback(self.profile, self.task))

    def test_apply_and_check_failures_have_distinct_body_free_retry_codes(self):
        hashes = worker.repair_target_hashes(self.task)
        worker.remember_repair_failure(self.profile, self.task, source_hashes=hashes, apply_failed=True)
        self.assertEqual(worker.load_repair_feedback(self.profile, self.task)["error"]["code"], "source_apply_failed")
        worker.remember_repair_failure(self.profile, self.task, source_hashes=hashes, validation_failed=True)
        self.assertEqual(worker.load_repair_feedback(self.profile, self.task)["error"]["code"], "task_validation_failed")

    def test_model_exception_records_feedback_before_propagating_failure(self):
        (self.root / "profile.json").write_text(json.dumps(self.profile))
        (self.root / "contracts.json").write_text('{"apps": []}')
        (self.root / "tasks.json").write_text('{"tasks": []}')
        def reject(*_args, **kwargs):
            (self.root / kwargs["output_path"]).write_text(json.dumps(self.receipt))
            raise llm.EditProposalError("edit_anchor_match_count", "app.js", 1, "exact anchor rejected", match_count=0)
        with patch.object(llm, "invoke_task_model", side_effect=reject):
            with self.assertRaises(llm.EditProposalError):
                worker.model("profile.json", self.task, "repair", [], [], self.output)
        hint = worker.load_repair_feedback(self.profile, self.task)
        self.assertEqual(hint["error"]["match_count"], 0)
        self.assertIn("rejected_response", hint)

    def test_execute_apply_and_repeated_check_failures_persist_for_next_worker(self):
        task = dict(self.task, checks=[["node", "--check", "app.js"]])
        proposal = {"response": {"edits": []}}
        with patch.object(worker, "ensure_lease"), patch.object(worker, "check_owned_sources"), patch.object(worker, "model", return_value=proposal):
            with patch.object(llm, "apply_validated_edits", side_effect=RuntimeError("owned apply refused")):
                with self.assertRaisesRegex(RuntimeError, "owned apply refused"):
                    worker.execute("profile.json", self.profile, {}, task)
            self.assertEqual(worker.load_repair_feedback(self.profile, task)["error"]["code"], "source_apply_failed")
            with patch.object(llm, "apply_validated_edits", return_value={"applied": []}), patch.object(worker, "run", side_effect=RuntimeError("check refused")) as run:
                with self.assertRaisesRegex(RuntimeError, "check refused"):
                    worker.execute("profile.json", self.profile, {}, task)
                self.assertEqual(run.call_count, 3)
            self.assertEqual(worker.load_repair_feedback(self.profile, task)["error"]["code"], "task_validation_failed")

    def test_blocked_or_empty_repair_cannot_complete_even_when_checks_would_pass(self):
        (self.root / "profile.json").write_text(json.dumps(self.profile))
        (self.root / "contracts.json").write_text('{"apps": []}')
        (self.root / "tasks.json").write_text('{"tasks": []}')
        task = dict(self.task, checks=[["node", "--check", "app.js"]])
        for decision in ("blocked", "needs_changes"):
            with self.subTest(decision=decision), patch.object(worker, "ensure_lease"), patch.object(worker, "check_owned_sources"), \
                    patch.object(llm, "invoke_task_model", return_value={"response": {"decision": decision, "edits": []}}), \
                    patch.object(llm, "validate_model_receipt"), patch.object(llm, "apply_validated_edits") as apply, patch.object(worker, "run") as checks:
                with self.assertRaisesRegex(ValueError, "declined"):
                    worker.execute("profile.json", self.profile, {}, task)
                apply.assert_not_called(); checks.assert_not_called()
                self.assertEqual(worker.load_repair_feedback(self.profile, task)["error"]["code"], "model_declined_scope")


if __name__ == "__main__":
    unittest.main()
