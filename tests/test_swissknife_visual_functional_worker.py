"""Independent SVF evidence refusal controls, with no browser/model/service calls."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import swissknife_visual_functional_worker as worker
import swissknife_visual_functional_llm as llm


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root_patch = patch.object(worker, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.profile = {"runtimeRoot": "data/agent_supervisor/swissknife_visual_functional", "appContractPath": "contracts.json"}
        self.directory = self.root / self.profile["runtimeRoot"] / "tasks/SVF-001/verification"
        self.directory.mkdir(parents=True)
        self.source = self.root / "swissknife/app.js"
        self.source.parent.mkdir()
        self.source.write_text("actual fixture source\n")
        driver_contract = self.root / "swissknife/docs/visual-functional-driver-contract.md"
        driver_contract.parent.mkdir()
        driver_contract.write_text("Authored readonly scenario input grammar for context tests.\n")
        self.image = self.directory / "desktop.png"
        self.image.write_bytes(b"retained authored artifact")
        self.app = {"app_id": "demo", "disposition": "browser_local", "source_paths": ["app.js"],
                    "primary_workflow": {"expected_results": ["Stored input reappears"],
                                         "persist_reopen": "Reopen retains input", "error": "A failed save preserves input",
                                         "recovery": "Retry stores input"}}
        self.contracts = self.root / "contracts.json"
        self.contracts.write_text(json.dumps({"apps": [self.app]}))
        self.task = {"task_id": "SVF-001", "kind": "verify", "app_id": "demo", "edit_paths": ["swissknife/app.js"]}
        predicate = {"operator": "equals", "actual": "observed value", "expected": "observed value"}
        self.data = {"schema": "swissknife.visual-functional-workflow.v1", "app_id": "demo", "passed": True,
                     "source_template": False, "actual_desktop": True, "contract_sha256": worker.sha(self.contracts),
                     "source_sha256": {"swissknife/app.js": worker.sha(self.source)},
                     "artifacts": [worker.artifact(self.image)],
                     "checks": [{"kind": kind, "passed": True, "observation": dict(predicate)} for kind in
                                ["primary_result", "keyboard", "desktop_layout", "mobile_layout", "error_recovery"]],
                     "semantic_assertions": [{"requirement_id": key, "requirement_text": text, "passed": True,
                                               "observed": dict(predicate)} for key, text in [
                          ("result_1", "Stored input reappears"), ("persist_reopen", "Reopen retains input"),
                          ("failure_recovery", "A failed save preserves input Recovery: Retry stores input")]],
                     "unexpected_backend_calls": 0, "backend_observations": []}
        self.report = self.directory / "workflow.json"

    def validate(self):
        self.report.write_text(json.dumps(self.data))
        worker.validate_workflow(self.profile, self.task, self.report)

    def backend(self):
        self.app["disposition"] = "tool_backed"
        self.contracts.write_text(json.dumps({"apps": [self.app]}))
        self.data["contract_sha256"] = worker.sha(self.contracts)
        call = {"app_id": "demo", "owner": "ipfs_kit_py", "tool_id": "read", "route": "/mcp/tools/call",
                "transport": "http", "correlation_id": "authored-call-1", "input": {"correlation_id": "authored-call-1"}}
        result = {"result": {"receipt": {"tool": "read"}, "content": [{"json": {"value": "stored fixture bytes"}}]}}
        observation = {"owner": "ipfs_kit_py", "tool_id": "read", "route": "/mcp/tools/call", "transport": "http",
                       "correlation_id": "authored-call-1", "outcome": "executed", "receipt_verified": True,
                       "semantic_result_verified": True,
                       "result_assertion": {"pointer": "/result/result/content/0/json/value", "operator": "equals",
                                            "actual": "stored fixture bytes", "expected": "stored fixture bytes"}}
        for kind, field in [("receipt", "receipt_id"), ("event", "event_dag_cid")]:
            raw = json.dumps({"kind": kind, "call": call, "result": result}, sort_keys=True, separators=(",", ":")).encode()
            path = self.directory / (kind + ".json")
            path.write_bytes(raw)
            self.data["artifacts"].append(worker.artifact(path))
            observation[field] = worker._raw_cid(raw)
            observation[kind + "_artifact"] = str(path.relative_to(self.root))
        self.data["backend_observations"] = [observation]
        return observation

    def test_dag_order_cycles_duplicates_and_unknown_dependencies(self):
        self.assertEqual(worker.validate_dag([{"task_id": "SVF-B", "dependencies": ["SVF-A"]}, {"task_id": "SVF-A"}]), ["SVF-A", "SVF-B"])
        invalid = [[], [{"task_id": "SVF-A"}, {"task_id": "SVF-A"}],
                   [{"task_id": "SVF-A", "dependencies": ["SVF-A"]}],
                   [{"task_id": "SVF-A", "dependencies": ["SVF-B"]}, {"task_id": "SVF-B", "dependencies": ["SVF-A"]}],
                   [{"task_id": "SVF-A", "dependencies": ["SVF-X"]}],
                   [{"task_id": "SVF-A", "dependencies": "SVF-B"}]]
        for tasks in invalid:
            with self.subTest(tasks=tasks), self.assertRaises(ValueError):
                worker.validate_dag(tasks)

    def test_positive_authored_workflow_contract_is_accepted(self):
        self.validate()

    def test_artifact_tamper_stale_source_and_stale_contract_fail(self):
        self.image.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "changed or missing"):
            self.validate()
        self.data["artifacts"] = [worker.artifact(self.image)]
        self.source.write_text("changed source")
        with self.assertRaisesRegex(ValueError, "source is stale"):
            self.validate()
        self.data["source_sha256"]["swissknife/app.js"] = worker.sha(self.source)
        self.contracts.write_text(self.contracts.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "contract is stale"):
            self.validate()

    def test_true_header_cannot_override_false_or_truthy_semantic_evidence(self):
        self.data["semantic_assertions"][0]["observed"]["actual"] = "wrong saved value"
        with self.assertRaisesRegex(ValueError, "contradict"):
            self.validate()
        self.data["semantic_assertions"][0]["observed"] = "looks good"
        with self.assertRaisesRegex(ValueError, "operator, actual"):
            self.validate()

    def test_typed_assertions_do_not_treat_false_as_zero_or_accept_nan(self):
        for observed in [{"operator": "equals", "actual": False, "expected": 0},
                         {"operator": "at_least", "actual": float("nan"), "expected": 1},
                         {"operator": "at_least", "actual": True, "expected": 1},
                         {"operator": "contains", "actual": "", "expected": ""}]:
            with self.subTest(observed=observed), self.assertRaises(ValueError):
                worker.validate_observed(observed)

    def test_missing_duplicate_and_wrong_semantic_requirement_fail(self):
        original = copy.deepcopy(self.data["semantic_assertions"])
        for assertions in [original[:-1], original + [original[0]], [dict(item, requirement_text="unrelated") for item in original]]:
            self.data["semantic_assertions"] = assertions
            with self.subTest(assertions=assertions), self.assertRaises(ValueError):
                self.validate()

    def test_missing_failed_or_duplicated_workflow_checks_fail(self):
        original = copy.deepcopy(self.data["checks"])
        for checks in [original[:-1], original + [original[0]], [dict(item, passed=False) for item in original]]:
            self.data["checks"] = checks
            with self.subTest(checks=checks), self.assertRaises(ValueError):
                self.validate()

    def test_local_boundary_requires_explicit_zero_and_no_owner_observation(self):
        for count in [None, False, "0", 1]:
            self.data["unexpected_backend_calls"] = count
            with self.subTest(count=count), self.assertRaisesRegex(ValueError, "boundary violated"):
                self.validate()
        self.data["unexpected_backend_calls"] = 0
        self.data["backend_observations"] = [{"outcome": "executed"}]
        with self.assertRaisesRegex(ValueError, "boundary violated"):
            self.validate()

    def test_artifact_prefix_lookalike_escape_symlink_and_duplicate_fail(self):
        fake = self.directory.with_name("verification-other")
        fake.mkdir()
        p = fake / "evidence.bin"; p.write_bytes(b"unrelated")
        with self.assertRaisesRegex(ValueError, "escaped"):
            worker.check_artifacts([worker.artifact(p)], allowed_prefix=self.directory)
        with self.assertRaises(ValueError):
            worker.path_in_root("../outside")
        (self.directory / "link").symlink_to(self.image)
        with self.assertRaisesRegex(ValueError, "symbolic-link"):
            worker.path_in_root(str((self.directory / "link").relative_to(self.root)))
        with self.assertRaisesRegex(ValueError, "duplicate"):
            worker.check_artifacts([worker.artifact(self.image)] * 2)
        with self.assertRaisesRegex(ValueError, "namespace"):
            worker.runtime_root({"runtimeRoot": "data/agent_supervisor/swissknife_visual_functional_other"})

    def test_backend_retains_and_revalidates_raw_cids_and_actual_result(self):
        self.backend()
        self.validate()

    def test_backend_flags_do_not_replace_retained_raw_artifacts(self):
        observation = self.backend()
        del observation["receipt_artifact"]
        with self.assertRaises((ValueError, KeyError)):
            self.validate()

    def test_rehashed_tampered_artifact_still_fails_independent_cid(self):
        self.backend()
        event = self.directory / "event.json"
        event.write_bytes(event.read_bytes() + b"\n")
        self.data["artifacts"] = [worker.artifact(self.root / item["path"]) for item in self.data["artifacts"]]
        with self.assertRaisesRegex(ValueError, "CID does not match"):
            self.validate()

    def test_backend_wrong_owner_correlation_and_detached_semantics_fail(self):
        observation = self.backend()
        for key, wrong in [("owner", "wrong-owner"), ("correlation_id", "wrong-call")]:
            original = observation[key]; observation[key] = wrong
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "does not match"):
                self.validate()
            observation[key] = original
        observation["result_assertion"]["actual"] = "invented response"
        with self.assertRaisesRegex(ValueError, "detached"):
            self.validate()

    def test_raw_native_failure_cannot_be_wrapped_as_executed(self):
        observation = self.backend()
        for kind, cid_field in [("receipt", "receipt_id"), ("event", "event_dag_cid")]:
            path = self.directory / (kind + ".json")
            payload = json.loads(path.read_text()); payload["result"]["result"]["success"] = False
            raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(); path.write_bytes(raw)
            observation[cid_field] = worker._raw_cid(raw)
        self.data["artifacts"] = [worker.artifact(self.root / item["path"]) for item in self.data["artifacts"]]
        with self.assertRaisesRegex(ValueError, "native owner result reports failure"):
            self.validate()

    def test_unowned_dirty_source_is_held_and_runtime_prefix_is_not_a_bypass(self):
        with patch.object(worker, "dirty_paths", return_value={"swissknife/app.js"}):
            with self.assertRaisesRegex(RuntimeError, "unowned dirty"):
                worker.check_owned_sources(self.profile, ["swissknife/app.js"])
            worker.remember_owned_sources(self.profile, ["swissknife/app.js"])
            worker.check_owned_sources(self.profile, ["swissknife/app.js"])
            self.source.write_text("foreign edit after ownership")
            with self.assertRaisesRegex(RuntimeError, "unowned dirty"):
                worker.check_owned_sources(self.profile, ["swissknife/app.js"])

    def test_task_validation_requires_native_model_receipt_beyond_success_headers(self):
        task = {"task_id": "SVF-001", "kind": "model-probe", "edit_paths": []}
        directory = self.directory.parent
        model_file = directory / "model.json"
        model_file.write_text(json.dumps({"success": True, "provider": "grok_cli", "model": "grok-4.7"}))
        receipt = {"schema": "swissknife.visual-functional-task.v1", "task_id": task["task_id"],
                   "kind": task["kind"], "task_spec_sha256": worker.stable(task), "artifacts": [worker.artifact(model_file)],
                   "work_complete": False, "completion_authority": False}
        (directory / "receipt.json").write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "validated model receipt"):
            worker.validate(self.profile, task)

    def test_task_receipt_kind_authority_and_model_failure_are_not_overridden(self):
        task = {"task_id": "SVF-001", "kind": "model-probe", "edit_paths": []}
        response = {"schema": llm.RESPONSE_SCHEMA, "task_id": "SVF-001", "mode": "probe", "decision": "pass",
                    "summary": "Authored finite model metadata fixture.", "inspected_screenshots": [], "findings": [], "edits": []}
        digest = "0" * 64
        model = {"schema": llm.RECEIPT_SCHEMA, "task_id": "SVF-001", "mode": "probe", "provider": "grok_cli", "model": "grok-4.7",
                 "temperature": 0, "success": True, "allow_local_fallback": False, "allow_cross_provider_fallback": False,
                 "disable_model_retry": True, "edits_applied": False, "work_complete": False, "completion_authority": False,
                 "effective_route": {"effective_provider_name": "grok_cli", "effective_model_name": "grok-4.7"},
                 "source_contract_sha256": digest, "prompt_sha256": digest, "router_source_sha256": digest, "output_sha256": digest,
                 "response_sha256": hashlib.sha256(llm._json(response).encode()).hexdigest(), "screenshots": [], "response": response,
                 "native_observation": {"exit_code": 1, "native_grok_reason_code": "end_turn", "native_grok_error_observed": False,
                                        "native_grok_progress": {"response_usable": True, "tool_name_counts": {"read_file": 0}}}}
        directory = self.directory.parent
        model_file = directory / "model.json"; model_file.write_text(json.dumps(model))
        receipt = {"schema": "swissknife.visual-functional-task.v1", "task_id": task["task_id"], "kind": task["kind"],
                   "task_spec_sha256": worker.stable(task), "artifacts": [worker.artifact(model_file)],
                   "work_complete": False, "completion_authority": False}
        path = directory / "receipt.json"; path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "completed native"):
            worker.validate(self.profile, task)
        receipt["completion_authority"] = True; path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "cannot grant"):
            worker.validate(self.profile, task)

    def test_legacy_aggregate_go_header_cannot_omit_cross_task_receipts(self):
        aggregate = {"task_id": "SVF-LEGACY-990", "kind": "aggregate", "regression_task": "SVF-LEGACY-900",
                     "dependencies": ["SVF-LEGACY-900", "SVF-910", "SVF-920", "SVF-930"], "edit_paths": []}
        tasks = [{"task_id": "SVF-LEGACY-900", "kind": "regression"}] + [
            {"task_id": task_id, "kind": "implementation", "dependencies": ["SVF-LEGACY-900"], "edit_paths": []}
            for task_id in aggregate["dependencies"][1:]] + [aggregate]
        self.profile["taskSpecPath"] = "tasks.json"
        (self.root / "tasks.json").write_text(json.dumps({"tasks": tasks}))
        directory = self.root / self.profile["runtimeRoot"] / "tasks/SVF-LEGACY-990"
        directory.mkdir()
        acceptance = directory / "acceptance.json"; acceptance.write_text(json.dumps({"decision": "GO"}))
        receipt = {"schema": "swissknife.visual-functional-task.v1", "task_id": "SVF-LEGACY-990", "kind": "aggregate",
                   "task_spec_sha256": worker.stable(aggregate), "artifacts": [worker.artifact(acceptance)],
                   "work_complete": False, "completion_authority": False}
        (directory / "receipt.json").write_text(json.dumps(receipt))
        with self.assertRaises(FileNotFoundError):
            worker.validate(self.profile, aggregate)

    def test_cross_workflow_false_semantics_are_rejected_independently(self):
        observation = self.backend()
        other = copy.deepcopy(self.app); other["app_id"] = "other"
        self.contracts.write_text(json.dumps({"apps": [self.app, other]}))
        directory = self.directory.parent / "cross-workflow"
        self.directory.rename(directory)
        self.directory = directory
        self.image = directory / "desktop.png"
        self.image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 150)
        mobile = directory / "mobile.png"; mobile.write_bytes(self.image.read_bytes())
        for kind in ["receipt", "event"]:
            observation[kind + "_artifact"] = str((directory / (kind + ".json")).relative_to(self.root))
        observation["app_id"] = "demo"
        task = {"task_id": "SVF-001", "kind": "implementation", "edit_paths": ["swissknife/app.js"], "acceptance": "Join actual app results"}
        predicate = {"operator": "equals", "actual": "joined actual value", "expected": "joined actual value"}
        data = {"schema": "swissknife.visual-functional-cross-workflow.v1", "task_id": "SVF-001",
                "task_spec_sha256": worker.stable(task), "contract_sha256": worker.sha(self.contracts),
                "passed": True, "actual_desktop": True, "source_template": False, "apps": ["demo", "other"],
                "source_sha256": {"swissknife/app.js": worker.sha(self.source)},
                "artifacts": [worker.artifact(path) for path in [self.image, mobile, directory / "receipt.json", directory / "event.json"]],
                "screenshots": {"desktop": str(self.image.relative_to(self.root)), "mobile": str(mobile.relative_to(self.root))},
                "semantic_assertions": [{"requirement_id": name, "requirement_text": task["acceptance"], "passed": True,
                                         "observed": dict(predicate)} for name in ["primary_result", "persist_reopen", "failure_recovery"]],
                "backend_observations": [observation]}
        report = directory / "workflow.json"; report.write_text(json.dumps(data))
        worker.validate_cross_workflow(self.profile, task)
        data["semantic_assertions"][0]["observed"]["actual"] = "wrong result"
        report.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, "contradict"):
            worker.validate_cross_workflow(self.profile, task)

    def test_baseline_retries_preserve_failures_and_review_uses_successful_receipt(self):
        task = {"task_id": "SVF-001", "kind": "baseline", "app_id": "demo", "edit_paths": []}
        base = self.directory.parent / "baseline"
        capture_calls = []

        def capture(argv, **_kwargs):
            if "--output-dir" not in argv:
                return {"argv": argv, "exit_code": 0, "output_tail": "independent baseline validator fixture"}
            directory = Path(argv[argv.index("--output-dir") + 1])
            self.assertEqual(list(directory.iterdir()), [])
            capture_calls.append(directory)
            if len(capture_calls) == 1:
                (directory / "failure.log").write_text("preserved failed capture")
                raise RuntimeError("authored first capture failure")
            views = []
            for name in ["desktop", "mobile"]:
                for suffix in [".png", "-primary.png"]:
                    (directory / (name + suffix)).write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 9000)
                (directory / (name + ".dom.json")).write_text("{}")
                views.append({"screenshot": name + ".png", "primary_screenshot": name + "-primary.png", "dom_file": name + ".dom.json"})
            (directory / "baseline.json").write_text(json.dumps({"schema": "swissknife.visual-functional-baseline.v1", "app_id": "demo",
                "baseline_only": True, "capture_complete": True, "acceptance_decision": "not_evaluated", "viewports": views}))
            return {"argv": argv, "exit_code": 0, "output_tail": "authored successful capture"}

        with patch.object(worker, "run", side_effect=capture):
            with self.assertRaisesRegex(RuntimeError, "first capture failure"):
                worker.baseline(self.profile, task, base)
            files = worker.baseline(self.profile, task, base)
            self.assertNotEqual(capture_calls[0], capture_calls[1])
            self.assertEqual((capture_calls[0] / "failure.log").read_text(), "preserved failed capture")
            self.assertEqual(len(files), 7)
            self.profile["taskSpecPath"] = "tasks.json"
            (self.root / "tasks.json").write_text(json.dumps({"tasks": [task]}))
            receipt = {"schema": "swissknife.visual-functional-task.v1", "task_id": "SVF-001", "kind": "baseline",
                       "task_spec_sha256": worker.stable(task), "artifacts": [worker.artifact(p) for p in files],
                       "work_complete": False, "completion_authority": False}
            (self.directory.parent / "receipt.json").write_text(json.dumps(receipt))
            report, images = worker.resolve_baseline(self.profile, "SVF-001")
            self.assertEqual(report, capture_calls[1] / "baseline.json")
            self.assertEqual(len(images), 4)
            self.assertTrue(all(str(capture_calls[1].relative_to(self.root)) in path for path in images))
            self.assertEqual(len(capture_calls), 2, "review validation must not start another browser")

    def write_authored_workflow(self, directory):
        """Finite evidence vector for orchestration tests; no real app GO."""
        directory.mkdir(parents=True, exist_ok=True)
        images = [directory / name for name in ["desktop.png", "mobile.png"]]
        for image in images:
            image.write_bytes(b"authored orchestration image fixture")
        data = copy.deepcopy(self.data)
        data["source_sha256"] = {"swissknife/app.js": worker.sha(self.source)}
        data["artifacts"] = [worker.artifact(image) for image in images]
        report = directory / "workflow.json"
        report.write_text(json.dumps(data))
        return report

    def authored_workflow_producer(self, report):
        return {"argv": ["node", "swissknife/scripts/run-visual-functional-workflow.mjs", "--app", "demo",
                         "--contracts", self.profile["appContractPath"], "--output-dir", str(report.parent)],
                "exit_code": 0, "output_tail": "authored finite producer fixture"}

    def test_workflow_retries_use_fresh_empty_attempts_and_preserve_failed_evidence(self):
        task = {**self.task, "kind": "regression"}  # Legacy V1 orchestration; fresh app verifies now require V2.
        runner = self.root / "swissknife/scripts/run-visual-functional-workflow.mjs"
        runner.parent.mkdir(); runner.write_text("// authored worker-call fixture; never executed\n")
        calls = []
        def produce(argv, **_kwargs):
            attempt = Path(argv[argv.index("--output-dir") + 1])
            self.assertEqual(list(attempt.iterdir()), [])
            calls.append(attempt)
            if len(calls) == 1:
                (attempt / "failure.log").write_text("retained real-failure analogue")
                raise RuntimeError("authored first workflow failure")
            self.write_authored_workflow(attempt)
            return {"argv": argv, "exit_code": 0, "output_tail": "authored successful workflow"}
        with patch.object(worker, "run", side_effect=produce):
            with self.assertRaisesRegex(RuntimeError, "first workflow failure"):
                worker.workflow(self.profile, task, self.directory)
            files, checks = worker.workflow(self.profile, task, self.directory)
        self.assertNotEqual(calls[0], calls[1])
        self.assertEqual((calls[0] / "failure.log").read_text(), "retained real-failure analogue")
        self.assertEqual(files[0], calls[1] / "workflow.json")
        self.assertEqual(checks[0]["argv"][-1], str(calls[1]))
        retained = {"artifacts": [worker.artifact(file) for file in files], "checks": checks}
        self.assertEqual(worker.retained_workflow_report(self.profile, task, retained, self.directory), files[0])

    def test_workflow_report_requires_exact_hashed_single_successful_attempt(self):
        first = self.write_authored_workflow(self.directory / "attempt-first123")
        second = self.write_authored_workflow(self.directory / "attempt-second12")
        retained = {"artifacts": [worker.artifact(first)], "checks": [self.authored_workflow_producer(first)]}
        self.assertEqual(worker.retained_workflow_report(self.profile, self.task, retained, self.directory), first)
        # A newer unrelated directory never changes receipt selection.
        self.assertTrue(second.exists())
        retained["artifacts"].append(worker.artifact(second))
        with self.assertRaisesRegex(ValueError, "exactly one"):
            worker.retained_workflow_report(self.profile, self.task, retained, self.directory)
        retained["artifacts"] = [worker.artifact(second)]
        with self.assertRaisesRegex(ValueError, "exact successful producer"):
            worker.retained_workflow_report(self.profile, self.task, retained, self.directory)
        retained["checks"] = [self.authored_workflow_producer(second)]
        self.source.write_text("changed source after retained workflow")
        with self.assertRaisesRegex(ValueError, "source is stale"):
            worker.retained_workflow_report(self.profile, self.task, retained, self.directory)

    def test_legacy_workflow_paths_need_retained_hash_and_original_producer_proof(self):
        report = self.write_authored_workflow(self.directory)
        retained = {"artifacts": [worker.artifact(report)], "checks": [self.authored_workflow_producer(report)]}
        self.assertEqual(worker.retained_workflow_report(self.profile, self.task, retained, self.directory), report)
        retained["checks"] = []
        with self.assertRaisesRegex(ValueError, "exact successful producer"):
            worker.retained_workflow_report(self.profile, self.task, retained, self.directory)
        retained["checks"] = [self.authored_workflow_producer(report)]
        report.write_text(report.read_text() + "\n")
        with self.assertRaisesRegex(ValueError, "changed or missing"):
            worker.retained_workflow_report(self.profile, self.task, retained, self.directory)

    def test_workflow_report_cannot_escape_attempt_scope_or_use_a_symlink(self):
        for relative in ["foreign/workflow.json", "verification/not-an-attempt/workflow.json", "verification/attempt-owned123/nested/workflow.json"]:
            report = self.write_authored_workflow(self.directory.parent / relative)
            retained = {"artifacts": [worker.artifact(report)], "checks": [self.authored_workflow_producer(report)]}
            with self.subTest(path=relative), self.assertRaises(ValueError):
                worker.retained_workflow_report(self.profile, self.task, retained, self.directory)
        real = self.write_authored_workflow(self.directory / "attempt-actual123")
        linked = self.directory / "attempt-linked123"; linked.symlink_to(real.parent, target_is_directory=True)
        retained = {"artifacts": [{**worker.artifact(real), "path": str((linked / "workflow.json").relative_to(self.root))}],
                    "checks": [self.authored_workflow_producer(linked / "workflow.json")]}
        with self.assertRaisesRegex(ValueError, "symbolic-link"):
            worker.retained_workflow_report(self.profile, self.task, retained, self.directory)

    def test_legacy_aggregate_reads_hashed_regression_attempts_through_original_receipt(self):
        regression = {"task_id": "SVF-LEGACY-900", "kind": "regression", "edit_paths": []}
        aggregate = {"task_id": "SVF-LEGACY-990", "kind": "aggregate", "regression_task": "SVF-LEGACY-900"}
        self.profile["taskSpecPath"] = "tasks.json"
        (self.root / "tasks.json").write_text(json.dumps({"tasks": [regression, aggregate]}))
        owner = worker.runtime_root(self.profile) / "tasks/SVF-LEGACY-900"
        report = self.write_authored_workflow(owner / "demo/attempt-success1")
        data = json.loads(report.read_text())
        files = [report, *[worker.path_in_root(item["path"]) for item in data["artifacts"]]]
        receipt = {"schema": "swissknife.visual-functional-task.v1", "task_id": "SVF-LEGACY-900", "kind": "regression",
                   "task_spec_sha256": worker.stable(regression), "artifacts": [worker.artifact(file) for file in files],
                   "checks": [self.authored_workflow_producer(report)], "work_complete": False, "completion_authority": False}
        (owner / "receipt.json").write_text(json.dumps(receipt))
        self.assertEqual(worker.regression_workflow_reports(self.profile, aggregate), {"demo": report})
        receipt["checks"][0]["argv"][-1] = str(owner / "demo/attempt-unrelated")
        (owner / "receipt.json").write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, "exact successful producer"):
            worker.regression_workflow_reports(self.profile, aggregate)

    def test_failed_visual_review_supplies_its_actual_findings_to_repair_then_recaptures(self):
        from test_svf_final_viewport_coverage import Fixture, final
        from test_svf_original_verify_v2 import copy_authored_dual_group
        self.image.unlink()  # Replace only this test's unused V1 artifact tree with the typed V2 fixture.
        for directory in (self.directory, self.directory.parent, self.directory.parent.parent,
                          self.root / self.profile['runtimeRoot']):
            directory.rmdir()
        fixture = Fixture(self.root)
        fixture.profile = self.profile; fixture.apps[0] = self.app; fixture.tasks[0] = self.task
        fixture.write('swissknife/test/e2e/functional-workflows/demo.json', fixture.scenario(self.app))
        with patch.object(final, '_node_source_snapshot', side_effect=fixture.source_vector):
            template = fixture.group()
        self.profile["humanPlanPath"] = "plan.md"
        calls, reviews, repairs = [], [], []
        def produce(argv, **_kwargs):
            self.assertEqual(argv[-1], '--independent-viewports')
            directory = Path(argv[argv.index('--output-dir') + 1]); self.assertEqual(list(directory.iterdir()), [])
            calls.append(directory)
            copy_authored_dual_group(fixture, template, self.task, directory)
            return {"argv": argv, "exit_code": 0}
        def model(_profile, task, mode, inputs, _screenshots, output):
            if mode == "review":
                reviews.append(output)
                self.assertEqual(output.parent, calls[-1])
                response = {"response": {"decision": "needs_changes" if len(reviews) == 1 else "pass",
                    "findings": [{"description": "The mobile Actions column is clipped."}] if len(reviews) == 1 else []}}
            else:
                repairs.append(inputs)
                self.assertIn(str(reviews[0].relative_to(self.root)), inputs)
                self.assertIn("Actions column is clipped", (self.root / inputs[-1]).read_text())
                response = {"response": {"edits": [{"path": "swissknife/app.js", "before_sha256": worker.sha(self.source),
                    "old": "actual fixture source", "new": "repaired fixture source"}]}}
            output.write_text(json.dumps(response))
            return response
        with patch.object(worker, "ensure_lease"), patch.object(worker, "check_owned_sources"), \
                patch.object(worker, "run", side_effect=produce), patch.object(worker, "model", side_effect=model), \
                patch.object(final, '_node_source_snapshot', side_effect=fixture.source_vector), \
                patch.object(worker, "validate") as final_acceptance:
            result = worker.execute("profile.json", self.profile, {}, self.task)
        self.assertEqual(len(calls), 2)
        self.assertNotEqual(calls[0], calls[1])
        self.assertEqual(len(repairs), 1)
        self.assertTrue(reviews[0].is_file(), "failed visual review remains immutable evidence")
        selected = [item["path"] for item in result["artifacts"] if Path(item["path"]).name == "workflow.json"
                    and (self.root / item["path"]).parent == calls[1]]
        self.assertEqual(selected, [str((calls[1] / "workflow.json").relative_to(self.root))])
        children = {item['path'] for item in result['artifacts'] if Path(item['path']).name == 'workflow.json'} - set(selected)
        self.assertEqual(children, {str((calls[1] / name / 'workflow.json').relative_to(self.root)) for name in ('desktop', 'mobile')})
        argv = result["checks"][0]["argv"]
        self.assertEqual(argv[argv.index('--output-dir') + 1], str(calls[1])); self.assertEqual(argv[-1], '--independent-viewports')
        self.assertIn('repaired fixture source', self.source.read_text())
        final_acceptance.assert_called_once()
        self.assertFalse(result["completion_authority"], "authored loop fixture does not grant app acceptance")

    def test_validation_timeout_allows_the_exact_owned_child_to_clean_up(self):
        script = self.root / "cleanup_child.py"
        script.write_text("import signal,time,pathlib,sys\n"
                          "def stop(*_):\n pathlib.Path('cleanup.txt').write_text('cleaned');sys.exit(0)\n"
                          "signal.signal(signal.SIGTERM,stop)\ntime.sleep(60)\n")
        with self.assertRaisesRegex(RuntimeError, "owned-child cleanup"):
            worker.run(["python3", str(script)], timeout=1)
        self.assertEqual((self.root / "cleanup.txt").read_text(), "cleaned")

    def test_review_projection_compacts_repeated_logs_and_binds_original_bytes(self):
        path = self.directory / "baseline.json"
        data = {"schema": "swissknife.visual-functional-baseline.v1", "app_id": "demo", "baseline_only": True,
                "capture_complete": True, "acceptance_decision": "not_evaluated", "boundary": {"tool_invocations": "blocked"},
                "viewports": [{"viewport": {"name": "desktop"}, "console_events": [{"type": "error", "text": "one repeated browser issue"}] * 1000,
                                "network_events": [{"method": "GET", "status": 200}] * 1000,
                                "keyboard_focus_observations": [{"name": "button"}] * 20}]}
        path.write_text(json.dumps(data))
        original = path.read_bytes()
        projection = worker._review_projection(path)
        self.assertEqual(projection["original"]["sha256"], hashlib.sha256(original).hexdigest())
        self.assertTrue(projection["projection_only"])
        viewport = projection["viewports"][0]
        self.assertEqual(viewport["console_summary"]["total_events"], 1000)
        self.assertEqual(viewport["console_summary"]["unique_events"], 1)
        self.assertEqual(viewport["console_summary"]["samples"][0]["count"], 1000)
        self.assertEqual(viewport["network_summary"]["methods"], {"GET": 1000})
        self.assertEqual(viewport["keyboard_focus_total"], 20)
        self.assertLess(len(json.dumps(projection)), 4000)
        self.assertEqual(path.read_bytes(), original)

    def test_review_context_is_app_scoped_and_immutable_across_attempts(self):
        baseline = self.directory / "baseline.json"
        baseline.write_text(json.dumps({"schema": "swissknife.visual-functional-baseline.v1", "app_id": "demo", "viewports": []}))
        human_plan = self.root / "plan.md"; human_plan.write_text("UNRELATED_CAMPAIGN_PLAN " * 5000)
        self.profile.update(humanPlanPath="plan.md", taskSpecPath="tasks.json")
        (self.root / "tasks.json").write_text(json.dumps({"tasks": []}))
        profile_path = self.root / "profile.json"; profile_path.write_text(json.dumps(self.profile))
        task = dict(self.task, kind="review", title="Review the app", acceptance="Inspect visible usability", context_paths=["do-not-inline"])
        self.app.update(title="Demo", primary_workflow=self.app["primary_workflow"], visual_checks=["visible text"],
                        launch={"window_selector": ".demo"}, backend_boundary="local", backend_roles=[{"bindings": ["LARGE_BINDING_TABLE"]}])
        self.contracts.write_text(json.dumps({"apps": [self.app]}))
        captures = []
        def invoke(*_args, **kwargs):
            captures.append(kwargs)
            content = "\n".join((self.root / path).read_text() for path in kwargs["input_paths"])
            self.assertNotIn("UNRELATED_CAMPAIGN_PLAN", content)
            self.assertNotIn("LARGE_BINDING_TABLE", content)
            self.assertNotIn("do-not-inline", content)
            self.assertIn("baseline_visual_triage", content)
            self.assertIn(worker.sha(baseline), content)
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            for _ in range(2):
                worker.model(str(profile_path.relative_to(self.root)), task, "review",
                    ["plan.md", "contracts.json", str(baseline.relative_to(self.root))], [], self.directory / "review.json")
        first, second = [call["input_paths"][0] for call in captures]
        self.assertNotEqual(first, second)
        self.assertTrue((self.root / first).is_file() and (self.root / second).is_file())

    def test_source_excerpts_are_explicit_whole_lines_with_full_identity(self):
        source = self.root / "large.py"
        source.write_text("".join(f"def function_{i}():\n    return {i}  # retained source\n" for i in range(1000)))
        raw = source.read_bytes()
        projection = worker._source_excerpt(source, 6000)
        self.assertTrue(projection["excerpt_only"])
        self.assertGreater(projection["omitted_line_count"], 0)
        self.assertEqual(projection["original"]["sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(projection["full_source_read_path"], "large.py")
        self.assertLessEqual(len(json.dumps(projection, indent=2, ensure_ascii=False).encode()), 6000)
        lines = raw.decode().splitlines(keepends=True)
        for window in projection["line_ranges"]:
            self.assertEqual(window["content"], "".join(lines[window["start_line"] - 1:window["end_line"]]))
        self.assertEqual(source.read_bytes(), raw)

    def test_repair_context_omits_whole_plan_and_uses_current_checkpoint_and_limits(self):
        task = {"task_id": "SVF-001", "kind": "implementation", "title": "One bounded stage", "acceptance": "Implement this stage",
                "edit_paths": ["checkpoint.py"], "checks": [["python3", "checkpoint.py"]],
                "llm_limits": {"maxTurns": 8, "maxOutputTokens": 12288, "modelContextBytes": 49152}}
        self.profile.update(humanPlanPath="plan.md", taskSpecPath="tasks.json", llm={"maxTurns": 24, "maxOutputTokens": 16384})
        (self.root / "plan.md").write_text("UNRELATED_WHOLE_PLAN " * 5000)
        (self.root / "checkpoint.py").write_text("# previously applied checkpoint\n" + "def existing():\n    return 'keep existing code'\n" * 2000)
        (self.root / "tasks.json").write_text(json.dumps({"tasks": []}))
        (self.root / "profile.json").write_text(json.dumps(self.profile))
        self.app.update(title="Demo")
        self.contracts.write_text(json.dumps({"apps": [self.app]}))
        captured = []
        def invoke(*_args, **kwargs):
            captured.append(kwargs)
            combined = "\n".join((self.root / path).read_text() for path in kwargs["input_paths"])
            self.assertNotIn("UNRELATED_WHOLE_PLAN", combined)
            self.assertIn("source-excerpt.v1", combined)
            self.assertIn("previously applied checkpoint", combined)
            self.assertIn(worker.sha(self.root / "checkpoint.py"), combined)
            self.assertEqual(kwargs["task_limits"], task["llm_limits"])
            self.assertLess(len(json.dumps(combined).encode()), 40000)
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            worker.model("profile.json", task, "repair", ["plan.md"], [], self.directory / "repair.json")
        self.assertEqual(len(captured), 1)

    def test_campaign_hold_blocks_new_model_before_context_or_provider_work(self):
        hold = self.root / self.profile["runtimeRoot"] / "HOLD"
        hold.write_text("maintenance")
        task = dict(self.task, kind="review")
        with patch.object(worker, "load", return_value=(self.profile, {})), patch.object(llm, "invoke_task_model") as invoke:
            with self.assertRaisesRegex(RuntimeError, "coordinator hold"):
                worker.model("profile.json", task, "review", [], [], self.directory / "review.json")
        invoke.assert_not_called()
        self.assertFalse((self.directory / "model-inputs").exists())
        with self.assertRaisesRegex(RuntimeError, "coordinator hold"):
            worker.ensure_lease(self.profile)

    def test_hold_arriving_during_context_preparation_blocks_the_paid_call(self):
        self.profile.update(humanPlanPath="plan.md", taskSpecPath="tasks.json")
        (self.root / "plan.md").write_text("local plan")
        (self.root / "tasks.json").write_text(json.dumps({"tasks": []}))
        (self.root / "profile.json").write_text(json.dumps(self.profile))
        self.app.update(title="Demo")
        self.contracts.write_text(json.dumps({"apps": [self.app]}))
        original = worker.atomic_json
        def hold_after_context(path, value, **kwargs):
            original(path, value, **kwargs)
            if path.name == "context.json":
                (self.root / self.profile["runtimeRoot"] / "HOLD").write_text("maintenance")
        with patch.object(worker, "atomic_json", side_effect=hold_after_context), patch.object(llm, "invoke_task_model") as invoke:
            with self.assertRaisesRegex(RuntimeError, "coordinator hold"):
                worker.model("profile.json", dict(self.task, kind="implementation"), "repair", [], [], self.directory / "repair.json")
        invoke.assert_not_called()

    def test_repair_allocation_keeps_complete_targets_before_secondary_context(self):
        target = self.root / "driver.mjs"; target.write_text("// target source line\n" * 1300)
        tests = self.root / "driver.test.mjs"; tests.write_text("// target test line\n" * 650)
        support = self.root / "support.mjs"; support.write_text("// large supporting source\n" * 10000)
        context = self.directory / "context.json"; context.write_text(json.dumps({"task_id": "SVF-001"}))
        task = {"task_id": "SVF-001", "edit_paths": ["driver.mjs", "driver.test.mjs"]}
        selected, records, complete = worker._repair_inputs({}, task, ["support.mjs", "driver.mjs", "driver.test.mjs"], context, self.directory, 98304)
        self.assertEqual(selected[:2], ["driver.mjs", "driver.test.mjs"])
        self.assertEqual([item["path"] for item in complete], task["edit_paths"])
        self.assertEqual({item["path"]: item["sha256"] for item in complete}, {path: worker.sha(self.root / path) for path in task["edit_paths"]})
        self.assertEqual(len(records), 3)
        supporting = json.loads((self.root / selected[2]).read_text())
        self.assertTrue(supporting["excerpt_only"])
        self.assertEqual(supporting["full_source_read_path"], "support.mjs")

    def test_repair_allocation_does_not_excerpt_fitting_complete_source_batch(self):
        paths = ["capture.mjs", "driver.mjs", "driver.test.mjs"]
        for path, size in zip(paths, [31325, 26550, 12501]):
            (self.root / path).write_text("x" * size)
        context = self.directory / "context.json"; context.write_text("{}")
        task = {"task_id": "SVF-001", "edit_paths": paths[1:]}
        selected, _records, complete = worker._repair_inputs({}, task, paths, context, self.directory, 98304)
        self.assertEqual(selected, paths[1:] + paths[:1])
        self.assertEqual([item["path"] for item in complete], paths[1:])
        self.assertEqual(list(self.directory.glob("source-*.json")), [])

    def test_oversized_targets_keep_explicit_excerpts_and_never_claim_complete(self):
        target = self.root / "huge.py"; target.write_text("def retained():\n    return 'original source'\n" * 10000)
        context = self.directory / "context.json"; context.write_text("{}")
        task = {"task_id": "SVF-001", "edit_paths": ["huge.py", "missing.py"]}
        selected, _records, complete = worker._repair_inputs({}, task, ["huge.py"], context, self.directory, 32768)
        self.assertEqual(complete, [])
        projection = json.loads((self.root / selected[0]).read_text())
        self.assertTrue(projection["excerpt_only"])
        self.assertEqual(projection["original"]["sha256"], worker.sha(target))
        self.assertGreater(projection["omitted_line_count"], 0)
        self.assertFalse((self.root / "missing.py").exists())
        self.assertLess(len(json.dumps({"path": selected[0], "content": (self.root / selected[0]).read_text()}).encode()), 32768)

    def test_model_context_marks_complete_targets_and_explains_read_policy(self):
        self.profile.update(humanPlanPath="plan.md", taskSpecPath="tasks.json", llm={"maxTurns": 24, "maxOutputTokens": 16384})
        (self.root / "plan.md").write_text("do not inline the full plan")
        (self.root / "tasks.json").write_text(json.dumps({"tasks": []}))
        (self.root / "profile.json").write_text(json.dumps(self.profile))
        self.app.update(title="Demo"); self.contracts.write_text(json.dumps({"apps": [self.app]}))
        task = dict(self.task, kind="implementation", llm_limits={"maxTurns": 16, "maxOutputTokens": 12288, "modelContextBytes": 98304})
        def invoke(*_args, **kwargs):
            context = json.loads((self.root / kwargs["input_paths"][0]).read_text())
            self.assertEqual(context["complete_edit_targets"], [worker.artifact(self.source)])
            self.assertIn("Do not reread complete targets", context["read_policy"])
            self.assertIn("swissknife/app.js", kwargs["input_paths"])
            return {"success": True}
        with patch.object(llm, "invoke_task_model", side_effect=invoke), patch.object(llm, "validate_model_receipt"):
            worker.model("profile.json", task, "repair", ["plan.md"], [], self.directory / "repair.json")


if __name__ == "__main__":
    unittest.main()
