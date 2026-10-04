"""Campaign owner lifecycle on fresh local test stores; no paper task runs."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("paper_materializer_for_owner_test", ROOT / "scripts/materialize_paper_database.py")
MAT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MAT)


class PaperStateOwnerTests(unittest.TestCase):
    def test_missing_database_is_rejected_without_listener_or_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "owner"
            result = subprocess.run([sys.executable, str(ROOT / "scripts/paper_state_owner.py"),
                                     "--database", str(Path(tmp) / "absent.duckdb"),
                                     "--state-dir", str(state), "--store-id", "owner-test",
                                     "--secret-handle", "handle:owner-test"],
                                    capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(state.exists())

    def test_native_owner_remote_readiness_auth_duplicate_and_sigterm_cleanup(self):
        MAT._native(ROOT)
        from ipfs_accelerate_py.agent_supervisor.task_sources.duckdb_state import open_quack_transport_connection
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            database, state = root / "control.duckdb", root / "owner"
            MAT.materialize("law_to_action", database, ROOT)
            argv = [sys.executable, str(ROOT / "scripts/paper_state_owner.py"),
                    "--database", str(database), "--state-dir", str(state),
                    "--store-id", "paper-owner-test", "--secret-handle", "handle:paper-owner-test"]
            proc = subprocess.Popen(argv, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            ready_path = state / "paper-owner.ready.json"
            ready, token, endpoint = None, None, None
            try:
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline and proc.poll() is None:
                    if ready_path.is_file():
                        observed = json.loads(ready_path.read_text())
                        if observed.get("ready"):
                            ready = observed
                            break
                    time.sleep(0.05)
                if ready is None:
                    if proc.poll() is None:
                        proc.terminate()
                    out, err = proc.communicate(timeout=10)
                    self.fail("temporary owner failed readiness; " + err + out)
                self.assertEqual(ready["identity"]["process_birth"]["pid"], proc.pid)
                self.assertTrue(ready["remote_probe"]["rollback_checked"])
                self.assertTrue(ready["remote_probe"]["identity_checked"])
                self.assertEqual(ready["remote_probe"]["task_count"], 25)
                endpoint = ready["quack_endpoint"]
                vault = state / "handle_paper-owner-test.quack-token"
                self.assertEqual(stat.S_IMODE(vault.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o700)
                token = vault.read_text()
                self.assertTrue(token not in json.dumps(ready), "public readiness leaked credential")
                connection = open_quack_transport_connection(endpoint, token=token)
                try:
                    self.assertEqual(connection.execute("SELECT count(*) FROM tasks").fetchone()[0], 25)
                    self.assertEqual(connection.execute("SELECT count(*) FROM health_samples WHERE subject_kind = 'paper-owner-readiness'").fetchone()[0], 0)
                finally:
                    connection.close()
                duplicate = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, timeout=15)
                self.assertNotEqual(duplicate.returncode, 0)
                self.assertEqual(json.loads(ready_path.read_text())["identity"]["server_id"], ready["identity"]["server_id"])
                self.assertIsNone(proc.poll())
                proc.send_signal(signal.SIGTERM)
                out, err = proc.communicate(timeout=15)
                self.assertEqual(proc.returncode, 0, err)
                self.assertTrue(token not in out + err, "owner diagnostics leaked credential")
                self.assertFalse(vault.exists())
                stopped = json.loads(ready_path.read_text())
                self.assertFalse(stopped["ready"])
                self.assertTrue(stopped["stopped"])
                port = int(endpoint.rsplit(":", 1)[1])
                with socket.socket() as probe:
                    probe.settimeout(1)
                    self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0)
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        proc.wait()
                proc.communicate()


if __name__ == "__main__":
    unittest.main()
