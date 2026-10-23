"""Pure diagnostic/cleanup control tests extracted from the authored harness.

The fixture classes contain only diagnostic data and a call tracer. They are
never native authorities, and no native runtime, claim, fence, budget owner,
worker, provider or prover module is imported or reconstructed.
"""
import ast
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import stat
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest


STAGE = Path(__file__).resolve().parent
OWNER_SOURCE = STAGE / "container_run_admitted_01.py"
HELPERS = {"snapshot_pending_attempt_logs", "capture_prepared_diagnostic", "capture_pending_failure",
    "capture_pending_failure_safely", "capture_cleanup_json"}


class DiagnosticFixtureError(ValueError):
    pass


class DiagnosticCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix=".test-native-diagnostic-cleanup-", dir=STAGE)
        self.root = Path(self.temporary.name)
        self.saved = []
        self.tree = ast.parse(OWNER_SOURCE.read_text(), filename=str(OWNER_SOURCE))
        definitions = [node for node in self.tree.body if isinstance(node, ast.FunctionDef) and node.name in HELPERS]
        self.assertEqual({node.name for node in definitions}, HELPERS)

        def save(name, value):
            raw = json.dumps(value, sort_keys=True).encode()
            path = self.root / name
            with path.open("xb") as stream:
                stream.write(raw)
            self.saved.append(name)
            return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

        def save_bytes(name, raw):
            path = self.root / name
            with path.open("xb") as stream:
                stream.write(raw)
            self.saved.append(name)
            return {"path": str(path), "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}

        self.namespace = {"__builtins__": __builtins__, "Path": Path, "os": os, "stat": stat,
            "re": re, "time": time, "signal": signal, "sys": sys, "hashlib": hashlib,
            "CheckedObserverBudgetError": DiagnosticFixtureError,
            "PUBLIC_NAMES": self.saved, "save": save, "save_bytes": save_bytes,
            "bounded_diagnostic": lambda callback: callback(), "DIAGNOSTIC_CAPTURE_COUNT": 0,
            "started_ns": time.monotonic_ns(), "CASE": "exceeded-budget"}
        module = ast.Module(body=deepcopy(definitions), type_ignores=[])
        exec(compile(ast.fix_missing_locations(module), str(OWNER_SOURCE), "exec"), self.namespace)

        class UnpreparedDiagnostic:
            calls = 0

            @property
            def prepared_record(instance):
                instance.calls += 1
                raise DiagnosticFixtureError("no original coding dispatch has been prepared")

        self.scope = UnpreparedDiagnostic()
        self.budget_data = {"records": [], "totals": {"events": 0}}
        self.namespace["SCOPE"] = self.scope
        self.namespace["LIVE"] = SimpleNamespace(snapshot=lambda: deepcopy(self.budget_data))
        self.broker = SimpleNamespace(diagnostic_snapshot=lambda: {"pending": False}, observations=[])
        self.runtime = SimpleNamespace(checked_context_dispatch_broker=self.broker, state=self.root / "state")

    def tearDown(self):
        self.temporary.cleanup()

    def capture(self):
        errors = []
        self.namespace["capture_pending_failure_safely"](self.runtime, errors, task_id="fixture-task")
        return errors

    def test_expected_budget_zero_unprepared_record_is_data_not_diagnostic_error(self):
        self.assertEqual(self.capture(), [])
        self.assertEqual(self.scope.calls, 1)
        path = self.root / "diagnostic-00-expected-unprepared-checked-dispatch.json"
        value = json.loads(path.read_bytes())
        self.assertIs(value["prepared_record_available"], False)
        self.assertIs(value["expected_budget_zero_state"], True)
        self.assertIs(value["diagnostic_only"], True)
        self.assertIs(value["proof_authority"], False)
        self.assertIs(value["completion_authority"], False)
        self.assertEqual(value["budget_events"], 0)
        self.assertFalse(any(name.endswith("native-dispatch-prepared-record.json") for name in self.saved))

    def test_repeated_captures_and_actual_log_snapshots_use_distinct_names(self):
        logs = self.runtime.state / "run/admitted_database_portal_attempts" / ("a" * 24) / "implementation-logs"
        logs.mkdir(parents=True)
        raw = b"Authored diagnostic log fixture only; no native observation.\n"
        (logs / ("fixture-task-attempt-1-" + "b" * 32 + ".log")).write_bytes(raw)
        self.assertEqual(self.capture(), [])
        self.assertEqual(self.capture(), [])
        self.assertEqual(len(self.saved), len(set(self.saved)))
        self.assertEqual(self.namespace["DIAGNOSTIC_CAPTURE_COUNT"], 2)
        self.assertEqual((self.root / "diagnostic-00-pending-implementation-00.log").read_bytes(), raw)
        self.assertEqual((self.root / "diagnostic-01-pending-implementation-00.log").read_bytes(), raw)
        self.assertTrue((self.root / "diagnostic-00-capture-timing.json").exists())
        self.assertTrue((self.root / "diagnostic-01-capture-timing.json").exists())

    def test_unprepared_other_case_is_retained_as_unexpected_error(self):
        self.namespace["CASE"] = "modified-artifact"
        errors = self.capture()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]["phase"], "public_prepared_diagnostic")
        self.assertFalse(any("expected-unprepared" in name for name in self.saved))

    def test_nonzero_budget_is_never_reclassified_as_expected_unprepared(self):
        self.budget_data = {"records": [{"status": "aborted", "fixture_only": True}], "totals": {"events": 1}}
        original = deepcopy(self.budget_data)
        errors = self.capture()
        self.assertEqual(len(errors), 1)
        self.assertFalse(any("expected-unprepared" in name for name in self.saved))
        self.assertEqual(self.budget_data, original)

    def test_boolean_zero_is_not_the_exact_expected_budget_event_count(self):
        self.budget_data = {"records": [], "totals": {"events": False}}
        errors = self.capture()
        self.assertEqual(len(errors), 1)
        self.assertFalse(any("expected-unprepared" in name for name in self.saved))

    def test_unrelated_scope_error_is_never_reclassified_as_expected_absence(self):
        class OtherScopeDiagnostic:
            @property
            def prepared_record(instance):
                raise DiagnosticFixtureError("authored unrelated scope identity failure")

        self.namespace["SCOPE"] = OtherScopeDiagnostic()
        errors = self.capture()
        self.assertEqual(len(errors), 1)
        self.assertFalse(any("expected-unprepared" in name for name in self.saved))

    def test_pending_broker_never_invokes_lock_bearing_prepared_getter(self):
        self.broker.diagnostic_snapshot = lambda: {"pending": True}
        self.assertEqual(self.capture(), [])
        self.assertEqual(self.scope.calls, 0)
        value = json.loads((self.root / "diagnostic-00-locked-getters-skipped.json").read_bytes())
        self.assertIs(value["prepared_record_getter_called"], False)
        self.assertIs(value["observations_getter_called"], False)

    def test_repeated_broker_diagnostic_failures_still_capture_distinct_timing(self):
        def fail():
            raise OSError("authored diagnostic getter failure")

        self.broker.diagnostic_snapshot = fail
        for _ in range(2):
            errors = self.capture()
            self.assertEqual(errors[0]["phase"], "public_broker_diagnostic")
        self.assertTrue((self.root / "diagnostic-00-capture-timing.json").exists())
        self.assertTrue((self.root / "diagnostic-01-capture-timing.json").exists())
        self.assertEqual(self.scope.calls, 0)

    def test_actual_finally_prefix_reaches_stop_after_repeated_escaped_diagnostics(self):
        candidates = [node for node in ast.walk(self.tree) if isinstance(node, ast.Try) and node.finalbody
            and isinstance(node.finalbody[0], ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "primary_failure" for target in node.finalbody[0].targets)
            and any(isinstance(child, ast.If) and isinstance(child.test, ast.Compare)
                and isinstance(child.test.left, ast.Name) and child.test.left.id == "RUNTIME" for child in node.finalbody)]
        self.assertEqual(len(candidates), 1)
        finalbody = candidates[0].finalbody
        stop_index = next(index for index, node in enumerate(finalbody)
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name) and node.test.left.id == "RUNTIME")
        stop_if = finalbody[stop_index]
        self.assertIsInstance(stop_if.body[0], ast.Try)
        stop_assignment = stop_if.body[0].body[0]
        self.assertIsInstance(stop_assignment, ast.Assign)
        self.assertEqual(ast.unparse(stop_assignment), "stop = RUNTIME.stop().to_dict()")
        # Execute the unchanged authored finally prefix up to its original STOP
        # invocation. No status, fence or receipt is invented or asserted here.
        prefix = deepcopy(finalbody[:stop_index])
        prefix.append(ast.If(test=deepcopy(stop_if.test), body=[deepcopy(stop_assignment)], orelse=[]))
        program = compile(ast.fix_missing_locations(ast.Module(body=prefix, type_ignores=[])), str(OWNER_SOURCE), "exec")
        calls = []

        def fail_diagnostic(*args, **kwargs):
            calls.append("diagnostic-failed")
            raise FileExistsError("authored repeated diagnostic export failure")

        class CleanupCallTracer:
            def stop(instance):
                calls.append("STOP-call-reached")
                return SimpleNamespace(to_dict=lambda: None)

        self.namespace.update({"capture_pending_failure": fail_diagnostic,
            "RUNTIME": CleanupCallTracer(), "LIVE": None, "runtime_created": True,
            "task": SimpleNamespace(task_key="fixture-task"), "save_failure_trace": lambda *args: None})
        for _ in range(2):
            try:
                raise ValueError("authored primary fixture failure")
            except ValueError:
                exec(program, self.namespace)
            self.assertEqual(self.namespace["cleanup_errors"][0]["phase"], "public_failure_diagnostic_exception")
        self.assertEqual(calls, ["diagnostic-failed", "STOP-call-reached", "diagnostic-failed", "STOP-call-reached"])


if __name__ == "__main__":
    unittest.main()
