"""Authored finite model receipts test recovery admission; no provider is invoked."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import swissknife_visual_functional_recovery as recovery
import swissknife_visual_functional_llm as adapter


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.runtime = self.root / recovery.NAMESPACE
        self.runtime.mkdir(parents=True)
        self.target = self.root / "app.py"; self.target.write_text("value = 'before'\n")
        self.guard = self.root / "guard.py"; self.guard.write_text("# protected declared source\n")
        (self.root / "docs").mkdir(); (self.root / "docs/context.txt").write_text("Declared bounded source context.\n")
        self.feedback = self.runtime / "state/feedback.json"; self.feedback.parent.mkdir(); self.feedback.write_text('{"failure":"typed"}\n')
        self.profile = {"runtimeRoot": str(recovery.NAMESPACE), "todoPath": "board.todo.md", "taskSpecPath": "tasks.json",
                        "llm": {"repairReadPolicy": "inline_only", "modelContextBytes": 131072}}
        self.task = {"task_id": "SVF-005", "kind": "command", "edit_paths": ["app.py"], "context_paths": ["docs/context.txt"],
                     "checks": [["python3", "protected-checker.py"]], "llm_limits": {"modelContextBytes": 131072}}
        self.packet_path = self.runtime / "state/semantic-recovery-SVF-005-1.context.json"
        self.journal_path = self.runtime / "state/lane_resume_attempts.semantic-recovery.json"
        self.packet = {"schema": recovery.CONTEXT_SCHEMA, "task_id": "SVF-005", "producer_contract": "a" * 64,
            "qualification_fingerprint": "b" * 64, "admission_index": 1, "recovery_limit": 2,
            "source_before": {"app.py": self.sha(self.target), "guard.py": self.sha(self.guard)},
            "feedback_inputs": {self.relative(self.feedback): self.sha(self.feedback)},
            "failure_summary": {"semantic_failures": 6, "last_stage": "validation", "last_exit_code": 1},
            "requires_inherited_lease_validation": True, "observation_only": True, "work_complete": False, "completion_authority": False}
        self.save_packet()
        self.environment = patch.dict(os.environ, {recovery.CONTEXT_ENV: str(self.packet_path)})
        self.environment.start(); self.addCleanup(self.environment.stop)
        self.leases, self.ownership_checks, self.owned, self.model_calls = [], [], [], []
        self.change = lambda _receipt: None
        self.edits = lambda: [{"path": "app.py", "before_sha256": self.packet["source_before"]["app.py"], "old": "before", "new": "after"}]

    def sha(self, path):return hashlib.sha256(path.read_bytes()).hexdigest()
    def relative(self, path):return path.relative_to(self.root).as_posix()
    def save_packet(self):
        self.packet_path.write_text(json.dumps(self.packet))
        self.journal = {"schema": "agent-supervisor/semantic-recovery-journal@1", "tasks": {"SVF-005": {
            "spent": 1, "history": [{"state": "running", "producer_contract": self.packet["producer_contract"],
                "qualification_fingerprint": self.packet["qualification_fingerprint"], "context_path": self.relative(self.packet_path),
                "recovery_limit": self.packet["recovery_limit"], "source_before": self.packet["source_before"],
                "completion_authority": False}]}}}
        self.save_journal()
    def save_journal(self):self.journal_path.write_text(json.dumps(self.journal))
    def lease(self):self.leases.append(True)

    def invoke(self, inputs, output, context):
        self.model_calls.append((inputs, output, context))
        response = {"schema": adapter.RESPONSE_SCHEMA, "task_id": self.task["task_id"], "mode": "repair", "decision": "needs_changes",
                    "summary": "Authored unit fixture only; no actual provider call.", "inspected_screenshots": [], "findings": [], "edits": self.edits()}
        record = {"schema": adapter.RECEIPT_SCHEMA, "task_id": self.task["task_id"], "mode": "repair", "provider": "grok_cli",
            "model": "grok-4.7", "temperature": 0, "success": True, "allow_local_fallback": False,
            "allow_cross_provider_fallback": False, "disable_model_retry": True, "edits_applied": False,
            "work_complete": False, "completion_authority": False, "native_read_file_denied": True, "native_tool_allowlist": [],
            "effective_route": {"effective_provider_name": "grok_cli", "effective_model_name": "grok-4.7"},
            "native_observation": {"exit_code": 0, "native_grok_reason_code": "end_turn", "native_grok_error_observed": False,
                "native_grok_progress": {"response_usable": True, "tool_name_counts": {"read_file": 0, "run_terminal_cmd": 0, "unknown": 0}}},
            "screenshots": [], "response": response,
            "input_files": [{"path": name, "sha256": self.sha(self.root / name)} for name in inputs]}
        for key in ["source_contract_sha256", "prompt_sha256", "router_source_sha256", "output_sha256"]:record[key] = "c" * 64
        record["response_sha256"] = hashlib.sha256(adapter._json(response).encode()).hexdigest()
        self.change(record)
        output.write_text(json.dumps(record))
        return record

    def run_recovery(self, **changes):
        callbacks = {"ensure_lease": self.lease, "check_owned": self.ownership_checks.append,
                     "invoke_model": self.invoke, "remember_owned": self.owned.append}
        callbacks.update(changes)
        result = recovery.run_recovery(self.root, self.profile, self.task, **callbacks)
        # Authored fixture controller records the real generic post-command
        # transition. The recovery module never owns or changes this journal.
        row = self.journal["tasks"]["SVF-005"]["history"][-1]
        row.update(state="applied", source_after=recovery.current_hashes(self.root, self.packet["source_before"]))
        self.save_journal()
        return result

    def test_one_exact_proposal_applies_and_original_checks_still_own_completion(self):
        result = self.run_recovery()
        self.assertIn("after", self.target.read_text())
        self.assertEqual(len(self.model_calls), 1)
        self.assertGreaterEqual(len(self.leases), 3)
        self.assertEqual(self.owned, [["app.py"]])
        self.assertEqual(self.ownership_checks, [["app.py"], ["app.py"]])
        self.assertTrue(result["eligible"])
        self.assertFalse(result["grants_task_completion"])
        self.assertFalse(result["completion_authority"])
        self.assertEqual(recovery.qualified_recovery(self.root, self.profile, self.task), result)
        self.assertEqual(list((self.runtime / "tasks/SVF-005").glob("receipt.json")), [])
        self.assertEqual(self.guard.read_text(), "# protected declared source\n")

    def test_missing_packet_wrong_task_excess_admission_and_stale_feedback_fail_before_model(self):
        for key, value in [("task_id", "SVF-999"), ("admission_index", 3), ("recovery_limit", 3), ("completion_authority", True)]:
            original = self.packet[key]; self.packet[key] = value; self.save_packet()
            with self.subTest(key=key), self.assertRaises(recovery.RecoveryError):self.run_recovery()
            self.packet[key] = original
        self.save_packet(); self.feedback.write_text("changed")
        with self.assertRaises(recovery.RecoveryError):self.run_recovery()
        self.assertEqual(self.model_calls, [])

    def test_declared_file_reads_policy_is_not_silently_downgraded(self):
        self.profile["llm"]["repairReadPolicy"] = "declared_file_reads"
        with self.assertRaisesRegex(recovery.RecoveryError, "inline_only"):self.run_recovery()
        self.assertEqual(self.model_calls, [])

    def test_controllers_boards_profiles_validators_and_task_receipts_are_never_editable(self):
        for name in ["scripts/svf_recovery_canary.py", "scripts/swissknife_visual_functional_worker.py", "config/other-profile.json",
                     "board.todo.md", "tests/test_check.py", str(recovery.NAMESPACE / "tasks/SVF-005/receipt.json"), ".env.local"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                recovery.edit_paths(self.root, self.profile, {"edit_paths": [name]})

    def test_noop_fails_without_source_change_or_successful_manifest(self):
        self.edits = lambda: [{"path": "app.py", "before_sha256": self.sha(self.target), "old": "before", "new": "before"}]
        with self.assertRaisesRegex(recovery.RecoveryError, "no-op"):self.run_recovery()
        self.assertIn("before", self.target.read_text())
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))

    def test_native_failure_and_tool_use_cannot_qualify_recovery(self):
        for mutate in [lambda r:r["native_observation"].update(exit_code=1),
                       lambda r:r["native_observation"]["native_grok_progress"]["tool_name_counts"].update(read_file=1),
                       lambda r:r.update(model="other-model")]:
            self.change = mutate
            with self.assertRaises(ValueError):self.run_recovery()
            self.assertIn("before", self.target.read_text())
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))

    def test_hold_or_lost_lease_prevents_model_dispatch(self):
        def held():raise RuntimeError("operator_hold")
        with self.assertRaisesRegex(RuntimeError, "operator_hold"):self.run_recovery(ensure_lease=held)
        self.assertEqual(self.model_calls, [])

    def test_source_or_packet_mutation_during_model_prevents_apply(self):
        self.change = lambda _r:self.target.write_text("foreign source")
        with self.assertRaisesRegex(recovery.RecoveryError, "inputs changed"):self.run_recovery()
        self.assertEqual(self.target.read_text(), "foreign source")
        self.assertEqual(self.owned, [])

    def test_qualified_recovery_rejects_source_task_and_model_artifact_tamper(self):
        result = self.run_recovery(); model = Path(result["model_path"])
        raw = model.read_bytes(); model.write_bytes(raw + b" ")
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))
        model.write_bytes(raw)
        self.assertIsNotNone(recovery.qualified_recovery(self.root, self.profile, self.task))
        self.target.write_text("foreign after")
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))

    def test_packet_symlink_or_outside_runtime_is_rejected(self):
        linked = self.runtime / "packet-link.json"; linked.symlink_to(self.packet_path)
        with patch.dict(os.environ, {recovery.CONTEXT_ENV: str(linked)}), self.assertRaises(ValueError):self.run_recovery()
        outside = self.root / "packet.json"; outside.write_text(json.dumps(self.packet))
        with patch.dict(os.environ, {recovery.CONTEXT_ENV: str(outside)}), self.assertRaises(ValueError):self.run_recovery()

    def test_full_targets_are_sent_inline_and_budget_failure_precedes_provider(self):
        self.run_recovery()
        inputs, _output, context = self.model_calls[0]
        self.assertIn("app.py", inputs)
        self.assertIn("docs/context.txt", inputs)
        self.assertNotIn("guard.py", inputs)
        self.assertNotIn(self.relative(self.feedback), inputs)  # Only the immutable copy is supplied.
        copied = context["feedback_inputs"][self.relative(self.feedback)]
        self.assertIn(copied["path"], inputs)
        self.assertEqual((self.root / copied["path"]).read_bytes(), self.feedback.read_bytes())
        self.assertEqual(copied["sha256"], self.packet["feedback_inputs"][self.relative(self.feedback)])
        self.assertTrue(copied["included"])
        self.assertEqual(context["source_before"], self.packet["source_before"])
        self.assertEqual(context["producer_contract"], self.packet["producer_contract"])
        self.assertFalse(any(Path(name).name == "context.json" for name in inputs))
        attempt = _output.parent
        self.assertEqual((attempt / "context.json").read_bytes(), self.packet_path.read_bytes())
        self.assertTrue(context["read_policy"].startswith("inline_only"))
        self.assertFalse(context["completion_authority"])

    def test_actual_task_failure_diagnostic_reaches_model_with_original_identity(self):
        failure = self.runtime / "tasks/SVF-005/last-execution-failure.json"
        failure.parent.mkdir(parents=True)
        failure.write_text(json.dumps({"schema": "swissknife.visual-functional-execution-failure.v1",
            "task_id": "SVF-005", "error": {"code": "BrowserTransportFailure",
            "message": "Actual declared fixture retrieval returned missing CID"},
            "work_complete": False, "completion_authority": False}))
        self.packet["feedback_inputs"][self.relative(failure)] = self.sha(failure)
        self.save_packet()
        self.run_recovery()
        inputs, _, context = self.model_calls[0]
        value = context["feedback_inputs"][self.relative(failure)]
        self.assertIn(value["path"], inputs)
        self.assertEqual((self.root / value["path"]).read_bytes(), failure.read_bytes())
        self.assertEqual(value["sha256"], self.sha(failure))
        self.assertTrue(value["included"])

    def test_controller_feedback_is_retained_and_mapped_without_duplicate_source_body(self):
        self.packet["feedback_inputs"]["guard.py"] = self.sha(self.guard)
        self.save_packet()
        self.run_recovery()
        inputs, _, context = self.model_calls[0]
        value = context["feedback_inputs"]["guard.py"]
        self.assertNotIn(value["path"], inputs)
        self.assertFalse(value["included"])
        self.assertEqual(value["reason"], "already_bound_controller_or_source")
        self.assertEqual((self.root / value["path"]).read_bytes(), self.guard.read_bytes())

    def test_real_packet_unlisted_worker_and_driver_contract_bodies_do_not_consume_diagnostic_budget(self):
        for name, size in [("scripts/swissknife_visual_functional_worker.py", 99941),
                           ("swissknife/docs/visual-functional-driver-contract.md", 16274)]:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("x" * size)
            self.packet["feedback_inputs"][name] = self.sha(target)
        self.save_packet()
        self.run_recovery()
        inputs, _, context = self.model_calls[0]
        for name in self.packet["feedback_inputs"]:
            value = context["feedback_inputs"][name]
            self.assertEqual(value["sha256"], self.packet["feedback_inputs"][name])
            if Path(name).suffix in {".py", ".md"}:
                self.assertFalse(value["included"])
                self.assertNotIn(value["path"], inputs)

    def test_oversized_failure_feedback_is_never_silently_truncated_or_dispatched(self):
        self.feedback.write_text("x" * (recovery.MAX_FEEDBACK_CONTEXT_BYTES + 1))
        self.packet["feedback_inputs"][self.relative(self.feedback)] = self.sha(self.feedback)
        self.save_packet()
        with self.assertRaisesRegex(recovery.RecoveryError, "failure feedback.*budget"):
            self.run_recovery()
        self.assertEqual(self.model_calls, [])

    def test_mutated_feedback_copy_is_rejected_before_model(self):
        def lease():
            self.leases.append(True)
            if len(self.leases) == 2:
                next((self.runtime / "tasks/SVF-005/recovery").glob("attempt-*/feedback-0.source")).write_text("tampered")
        with self.assertRaisesRegex(recovery.RecoveryError, "artifact bytes changed"):
            self.run_recovery(ensure_lease=lease)
        self.assertEqual(self.model_calls, [])
        self.assertIn("before", self.target.read_text())

    def test_receipt_omitting_actual_feedback_cannot_apply(self):
        self.change = lambda receipt: receipt.update(input_files=[row for row in receipt["input_files"]
            if "/feedback-" not in row["path"]])
        with self.assertRaisesRegex(recovery.RecoveryError, "omits hash-bound.*feedback"):
            self.run_recovery()
        self.assertIn("before", self.target.read_text())

    def test_scoped_subset_preserves_all_original_unit_test_sources_and_manifest_hashes(self):
        checker = self.root / "tests/test_original.py"; checker.parent.mkdir(); checker.write_text("# unchanged independent check\n")
        self.task["edit_paths"].append("tests/test_original.py")
        self.task["recovery_edit_paths"] = ["app.py"]
        self.packet["source_before"]["tests/test_original.py"] = self.sha(checker); self.save_packet()
        result = self.run_recovery()
        self.assertEqual(result["approved_edit_paths"], ["app.py"])
        self.assertEqual(self.model_calls[0][2]["edit_paths"], ["app.py"])
        self.assertEqual(set(result["source_before"]), {"app.py", "tests/test_original.py"})
        self.assertEqual(result["source_before"]["tests/test_original.py"], result["source_after"]["tests/test_original.py"])
        self.assertEqual(checker.read_text(), "# unchanged independent check\n")
        self.assertIsNotNone(recovery.qualified_recovery(self.root, self.profile, self.task))
        checker.write_text("# foreign validator change\n")
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))

    def test_invalid_explicit_subset_rejects_whole_declaration(self):
        for subset in [["other.py"], ["app.py", "tests/test_forbidden.py"], [], "app.py"]:
            task = {**self.task, "edit_paths": ["app.py", "tests/test_forbidden.py"], "recovery_edit_paths": subset}
            with self.subTest(subset=subset), self.assertRaises(ValueError):
                recovery.edit_paths(self.root, self.profile, task)
        self.assertEqual(recovery.edit_paths(self.root, self.profile,
            {"edit_paths": ["app.py", "tests/test_forbidden.py"]}), ["app.py"])

    def test_declared_functional_workflow_json_and_canary_fixture_are_editable(self):
        scenario = "swissknife/test/e2e/functional-workflows/notes.json"
        canary = str(recovery.NAMESPACE / "fixtures/automatic-repair-canary.json")
        task = {"edit_paths": [scenario, canary], "recovery_edit_paths": [scenario, canary]}
        self.assertEqual(recovery.edit_paths(self.root, self.profile, task), [scenario, canary])

    def test_lease_lost_after_model_prevents_source_apply(self):
        def lease():
            if self.model_calls:raise RuntimeError("operator_hold_after_model")
        with self.assertRaisesRegex(RuntimeError, "operator_hold_after_model"):
            self.run_recovery(ensure_lease=lease)
        self.assertIn("before", self.target.read_text())
        self.assertEqual(self.owned, [])

    def test_explicit_context_budget_fails_before_model_dispatch(self):
        (self.root / "docs/context.txt").write_text("large complete source context\n" * 4000)
        self.task["llm_limits"]["modelContextBytes"] = 2048
        with self.assertRaisesRegex(recovery.RecoveryError, "context budget"):
            self.run_recovery()
        self.assertEqual(self.model_calls, [])

    def test_changed_original_context_and_task_cannot_reuse_qualification(self):
        self.run_recovery()
        self.task["title"] = "changed task contract"
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))
        del self.task["title"]
        self.assertIsNotNone(recovery.qualified_recovery(self.root, self.profile, self.task))
        self.packet_path.write_text(json.dumps({**self.packet, "qualification_fingerprint": "d" * 64}))
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))

    def test_failed_noop_applied_and_old_packets_cannot_replay_before_provider(self):
        row = self.journal["tasks"]["SVF-005"]["history"][-1]
        for state in ["failed", "no_op", "applied", "interrupted"]:
            row["state"] = state; self.save_journal()
            with self.subTest(state=state), self.assertRaises(recovery.RecoveryError):self.run_recovery()
        row["state"] = "running"
        second = {**row, "qualification_fingerprint": "d" * 64}
        self.journal["tasks"]["SVF-005"].update(spent=2, history=[row, second]); self.save_journal()
        with self.assertRaisesRegex(recovery.RecoveryError, "current finite"):self.run_recovery()
        self.assertEqual(self.model_calls, [])

    def test_journal_identity_budget_and_path_must_match_packet(self):
        row = self.journal["tasks"]["SVF-005"]["history"][-1]
        for key, value in [("producer_contract", "d" * 64), ("qualification_fingerprint", "d" * 64),
                           ("context_path", str(recovery.NAMESPACE / "state/foreign.json")), ("recovery_limit", 1)]:
            original = row[key]; row[key] = value; self.save_journal()
            with self.subTest(key=key), self.assertRaises(recovery.RecoveryError):self.run_recovery()
            row[key] = original
        self.save_journal(); self.journal_path.unlink()
        with self.assertRaises(ValueError):self.run_recovery()
        self.assertEqual(self.model_calls, [])

    def test_journal_state_change_during_model_fences_source_apply(self):
        def revoke(_receipt):
            self.journal["tasks"]["SVF-005"]["history"][-1]["state"] = "failed"
            self.save_journal()
        self.change = revoke
        with self.assertRaisesRegex(recovery.RecoveryError, "does not authorize"):self.run_recovery()
        self.assertIn("before", self.target.read_text())
        self.assertEqual(self.owned, [])

    def test_qualification_requires_current_applied_row_and_all_source_hashes(self):
        self.run_recovery()
        row = self.journal["tasks"]["SVF-005"]["history"][-1]
        row["state"] = "running"; self.save_journal()
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))
        row["state"] = "applied"; row["source_after"]["app.py"] = "0" * 64; self.save_journal()
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))
        row["source_after"]["app.py"] = self.sha(self.target); self.save_journal()
        self.assertIsNotNone(recovery.qualified_recovery(self.root, self.profile, self.task))

    def test_symlinked_journal_is_not_an_admission(self):
        original = self.runtime / "real-journal.json"; original.write_bytes(self.journal_path.read_bytes())
        self.journal_path.unlink(); self.journal_path.symlink_to(original)
        with self.assertRaises(ValueError):self.run_recovery()
        self.assertEqual(self.model_calls, [])

    def test_historical_canary_evidence_survives_readonly_controller_and_profile_changes(self):
        self.task["recovery_canary"] = True
        config = self.root / "config/profile.json"; config.parent.mkdir(); config.write_text(json.dumps(self.profile))
        self.packet["source_before"]["config/profile.json"] = self.sha(config); self.save_packet()
        self.run_recovery()
        self.guard.write_text("# changed readonly controller\n")
        self.profile["llm"]["repairReasoningEffort"] = "low"
        config.write_text(json.dumps(self.profile))
        self.assertIsNone(recovery.qualified_recovery(self.root, self.profile, self.task))
        evidence = recovery.historical_recovery_evidence(self.root, self.profile, self.task)
        self.assertIsNotNone(evidence)
        self.assertIs(evidence["evidence_only"], True)
        self.assertIs(evidence["eligible"], False)
        self.assertIs(evidence["grants_task_completion"], False)
        self.assertIs(evidence["completion_authority"], False)
        self.assertEqual(evidence["task_id"], "SVF-005")

    def test_historical_api_rejects_noncanary_tasks(self):
        self.run_recovery()
        self.assertIsNone(recovery.historical_recovery_evidence(self.root, self.profile, self.task))
        self.assertIsNotNone(recovery.qualified_recovery(self.root, self.profile, self.task))

    def test_historical_evidence_still_rejects_target_task_model_and_journal_tamper(self):
        self.task["recovery_canary"] = True
        result = self.run_recovery(); model = Path(result["model_path"])
        self.guard.write_text("# later unrelated controller change\n")
        historical = lambda: recovery.historical_recovery_evidence(self.root, self.profile, self.task)
        self.assertIsNotNone(historical())
        actual = self.target.read_bytes(); self.target.write_text("foreign target")
        self.assertIsNone(historical()); self.target.write_bytes(actual)
        self.task["acceptance"] = "changed task"
        self.assertIsNone(historical()); del self.task["acceptance"]
        raw = model.read_bytes(); model.write_bytes(raw + b" ")
        self.assertIsNone(historical()); model.write_bytes(raw)
        row = self.journal["tasks"]["SVF-005"]["history"][-1]
        row["state"] = "failed"; self.save_journal()
        self.assertIsNone(historical())
        row["state"] = "applied"; row["source_after"]["app.py"] = "0" * 64; self.save_journal()
        self.assertIsNone(historical())
        row["source_after"]["app.py"] = self.sha(self.target); self.save_journal()
        self.assertIsNotNone(historical())

    def test_historical_evidence_cannot_replay_applied_context_into_provider(self):
        self.task["recovery_canary"] = True
        self.run_recovery()
        before = len(self.model_calls)
        self.assertIsNotNone(recovery.historical_recovery_evidence(self.root, self.profile, self.task))
        with self.assertRaises(recovery.RecoveryError):self.run_recovery()
        self.assertEqual(len(self.model_calls), before)

    def real_verification_shape(self, *, admit_scenario):
        js = "swissknife/web/js/apps/calculator.js"
        scenario = "swissknife/test/e2e/functional-workflows/calculator.json"
        self.target = self.root / js; self.target.parent.mkdir(parents=True)
        self.target.write_text("export const state = 'stable';\n")
        workflow = self.root / scenario; workflow.parent.mkdir(parents=True)
        # JSON-only recovery still needs a genuinely valid canonical scenario.
        repository = Path(os.environ.get("SVF_FOUNDATION_REPOSITORY_ROOT", str(Path(__file__).resolve().parents[1])))
        value = json.loads((repository / scenario).read_bytes())
        value["description"] = "before"
        workflow.write_text(json.dumps(value, separators=(",", ":")) + "\n")
        contract = "swissknife/config/visual-functional-app-contracts.json"
        target = self.root / contract; target.parent.mkdir(parents=True)
        target.write_bytes((repository / contract).read_bytes())
        self.profile["appContractPath"] = contract
        for name in ("swissknife/scripts/run-visual-functional-workflow.mjs",
                     "swissknife/scripts/capture-visual-functional-baseline.mjs",
                     "swissknife/scripts/lib/pick-free-port.mjs"):
            target = self.root / name; target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((repository / name).read_bytes())
        self.task.update(kind="verify", app_id="calculator", edit_paths=[js, scenario], recovery_edit_paths=[js, scenario],
                         context_paths=[js, "docs/context.txt"], checks=[])
        self.packet["source_before"] = {js: self.sha(self.target), "guard.py": self.sha(self.guard)}
        if admit_scenario:self.packet["source_before"][scenario] = self.sha(workflow)
        self.save_packet()
        self.edits = lambda: [{"path": scenario, "before_sha256": self.packet["source_before"][scenario],
                              "old": '"description":"before"', "new": '"description":"after"'}]
        return js, scenario, workflow

    def test_real_verify_packet_missing_scenario_hash_fails_before_provider(self):
        _js, _scenario, workflow = self.real_verification_shape(admit_scenario=False)
        before = workflow.read_bytes()
        with self.assertRaisesRegex(recovery.RecoveryError, "packet omits original declared edit source hashes"):
            self.run_recovery()
        self.assertEqual(self.model_calls, [])
        self.assertEqual(workflow.read_bytes(), before)

    def test_real_verify_shape_can_apply_json_only_repair_after_generic_admission(self):
        js, scenario, workflow = self.real_verification_shape(admit_scenario=True)
        original_js = self.target.read_bytes()
        result = self.run_recovery()
        self.assertEqual(self.target.read_bytes(), original_js)
        self.assertEqual(json.loads(workflow.read_bytes())["description"], "after")
        self.assertEqual(result["source_before"][js], result["source_after"][js])
        self.assertNotEqual(result["source_before"][scenario], result["source_after"][scenario])
        self.assertEqual(self.owned, [[scenario]])
        self.assertIsNotNone(recovery.qualified_recovery(self.root, self.profile, self.task))

    def test_large_readonly_context_can_be_projected_by_trusted_model_callback(self):
        support = self.root / "docs/context.txt"
        support.write_text("read-only manifest across many unrelated applications\n" * 3000)
        self.assertGreater(support.stat().st_size, self.task["llm_limits"]["modelContextBytes"])
        seen = []
        def project(inputs, output, context):
            seen.append(inputs)
            synopsis = output.parent / "supporting-app-context.json"
            synopsis.write_text(json.dumps({"app": "fixture-app", "original_sha256": self.sha(support)}))
            return self.invoke([name if name != "docs/context.txt" else self.relative(synopsis) for name in inputs], output, context)
        self.run_recovery(invoke_model=project)
        self.assertEqual(len(seen), 1)
        self.assertIn("docs/context.txt", seen[0])
        self.assertIn("app.py", seen[0])
        self.assertIn("after", self.target.read_text())

    def test_oversized_edit_target_is_never_projected_or_sent_to_provider(self):
        self.target.write_text("before" + "x" * 150000)
        self.packet["source_before"]["app.py"] = self.sha(self.target); self.save_packet()
        with self.assertRaisesRegex(recovery.RecoveryError, "complete recovery sources exceed"):
            self.run_recovery()
        self.assertEqual(self.model_calls, [])
        self.assertEqual(self.owned, [])


if __name__ == "__main__":unittest.main()
