"""Bounded failure diagnostics; fake owner only, no listener or database open."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import errno
import importlib.util
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("paper_owner_failure_test", ROOT / "scripts/paper_state_owner.py")
OWNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OWNER)


class OwnerFailureDiagnosticsTests(unittest.TestCase):
    def exercise(self, primary, *, fail_publication=True, secondary_publication=None,
                 cleanup_error=None, stop_immediately=False):
        lifecycle = SimpleNamespace(READY=object(), STOPPED=object())
        identity = SimpleNamespace(listen_uri="quack:127.0.0.1:1", secret_handle="handle:test",
                                   store_id="test", generation=1, schema_revision=1,
                                   to_dict=lambda: {"server_id": "server:test"})
        server = SimpleNamespace(lifecycle=lifecycle.READY, start=Mock(return_value=identity),
                                 ready=Mock(), _vault=SimpleNamespace(assert_absent_from=Mock()),
                                 stop_control_path=lambda: SimpleNamespace(is_file=lambda: stop_immediately))
        def stop():
            if cleanup_error is not None:
                raise cleanup_error
            server.lifecycle = lifecycle.STOPPED
        server.stop = Mock(side_effect=stop)
        records, calls = [], []
        def publish(_path, payload):
            calls.append(copy.deepcopy(payload))
            if fail_publication and len(calls) == 2:
                raise primary
            if secondary_publication is not None and len(calls) == 3:
                raise secondary_publication
            records.append(copy.deepcopy(payload))
        probe = {"checked_at": "2026-09-11T00:00:00+00:00", "network_query": True,
                 "identity_checked": True, "task_count": 25}
        remote = Mock(side_effect=[probe, probe] if fail_publication else [probe, primary])
        stderr, stdout = io.StringIO(), io.StringIO()
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            marker = Path(directory) / "existing-input-marker"
            marker.write_text("fixture marker; never opened as a database")
            stack.enter_context(patch.object(OWNER, "_native", return_value=(lambda **_: server, lifecycle, None)))
            stack.enter_context(patch.object(OWNER, "remote_readiness", remote))
            stack.enter_context(patch.object(OWNER, "_atomic_json", side_effect=publish))
            stack.enter_context(patch.object(OWNER.signal, "signal", return_value=None))
            stack.enter_context(patch.object(OWNER.time, "monotonic", side_effect=[0, 6]))
            stack.enter_context(patch.object(OWNER.time, "sleep"))
            stack.enter_context(redirect_stderr(stderr))
            stack.enter_context(redirect_stdout(stdout))
            with self.assertRaises(type(primary)) as captured:
                OWNER.serve(marker, Path(directory) / "owner", "test", "handle:test")
        self.assertIs(captured.exception, primary)
        server.stop.assert_called_once()
        self.assertNotIn("secret-query-canary", stderr.getvalue() + stdout.getvalue() + json.dumps(calls))
        return records, calls, [json.loads(line) for line in stderr.getvalue().splitlines()], remote

    def test_periodic_publication_enospc_preserves_phase_errno_and_original_exception(self):
        error = OSError(errno.ENOSPC, "secret-query-canary")
        records, calls, events, remote = self.exercise(error)
        self.assertEqual(remote.call_count, 2)
        self.assertTrue(calls[1]["remote_health"]["network_query"])
        final = records[-1]
        self.assertEqual(final["error_type"], "OSError")
        self.assertEqual(final["failure_phase"], "periodic_readiness_publication")
        self.assertEqual(final["error_errno"], errno.ENOSPC)
        self.assertEqual(final["error_errno_name"], "ENOSPC")
        self.assertFalse(final["ready"])
        self.assertTrue(final["stopped"])
        self.assertEqual(events[0]["error_errno"], errno.ENOSPC)

    def test_secondary_publication_and_cleanup_failures_do_not_mask_primary(self):
        error = OSError(errno.ENOSPC, "secret-query-canary")
        _, _, events, _ = self.exercise(error, secondary_publication=OSError(errno.EIO, "secret-query-canary"),
                                       cleanup_error=OSError(errno.EACCES, "secret-query-canary"))
        self.assertEqual([(event["failure_phase"], event["error_errno"]) for event in events],
                         [("periodic_readiness_publication", errno.ENOSPC),
                          ("failure_readiness_publication", errno.EIO), ("server_stop", errno.EACCES)])

    def test_remote_failure_keeps_non_oserror_class_without_raw_message(self):
        error = RuntimeError("secret-query-canary")
        records, _, events, _ = self.exercise(error, fail_publication=False)
        self.assertEqual(records[-1]["error_type"], "RuntimeError")
        self.assertEqual(records[-1]["failure_phase"], "periodic_remote_readiness")
        self.assertIsNone(events[0]["error_errno"])
        self.assertIsNone(events[0]["error_errno_name"])

    def test_first_shutdown_failure_is_not_suppressed(self):
        error = OSError(errno.EIO, "secret-query-canary")
        records, _, events, _ = self.exercise(error, fail_publication=False,
                                            cleanup_error=error, stop_immediately=True)
        self.assertEqual(records[-1]["failure_phase"], "server_stop")
        self.assertFalse(records[-1]["ready"])
        self.assertFalse(records[-1].get("stopped", False))
        self.assertEqual(events[0]["error_errno_name"], "EIO")


if __name__ == "__main__":
    unittest.main()
